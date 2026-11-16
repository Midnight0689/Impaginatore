"""VER-014: le manopole di dimensione hanno un limite. Scala degli spread tra 0,02 e 1, miniature fino a 1200 px (600 nel
selettore di file), qualità JPEG tra 1 e 100, larghezza del PDF tra 500 e 6000 px; un valore che non è un numero (NaN,
infinito, testo) è 400, non un errore interno. Le cache delle immagini hanno un numero di voci e una misura massimi, e
abbina.py usa lo stesso limite di pixel delle foto del progetto."""
import io
import os
from urllib.parse import quote

import pytest
from aiuti import attendi_log, come_script
from PIL import Image

from impaginatore.editor import server as E
from impaginatore.motore import album as A


def _misura(b):
    with Image.open(io.BytesIO(b)) as im: return im.size


@pytest.fixture
def con_spread(editor):
    nomi = [p["n"] for p in editor.get("/api/state")["photos"]]
    editor.post("/api/op", dict(op="newspreadsel", names=nomi[:2], pos=0))
    return editor


@pytest.mark.parametrize("percorso", ["/img/spread/0?k=nan", "/img/spread/0?k=inf", "/img/spread/0?k=boh", "/img/thumb/{n}?w=nan", "/img/thumb/{n}?w=1e999",
                                      "/img/corr?n={n}&w=x", "/api/fthumb?p={p}&w=nan", "/img/live?s=0&side=L&idx=0&k=nan"])
def test_valori_che_non_sono_numeri(con_spread, percorso):
    c = con_spread; n = c.get("/api/state")["photos"][0]["n"]
    ok, r = c.prova(percorso.format(n=quote(n), p=quote(A.M[0]["src"])))
    assert not ok and "non è un numero" in r["errore"], r
    assert c.codice(percorso.format(n=quote(n), p=quote(A.M[0]["src"]))) == 400


def test_scala_degli_spread(con_spread):
    c = con_spread
    uno = _misura(c.raw("/img/spread/0?k=1"))
    assert _misura(c.raw("/img/spread/0?k=40")) == uno, "oltre 1 vale 1 (k=40 vorrebbe ~140 GB)"
    assert _misura(c.raw("/img/spread/0?k=-1")) == _misura(c.raw("/img/spread/0?k=0.02")), "sotto 0,02 vale 0,02 (prima: errore interno)"


def test_miniature(con_spread):
    c = con_spread; n = c.get("/api/state")["photos"][0]["n"]
    assert max(_misura(c.raw(f"/img/thumb/{quote(n)}?w=99999"))) <= 1200
    assert max(_misura(c.raw(f"/img/thumb/{quote(n)}?w=-5"))) == 16
    assert max(_misura(c.raw(f"/img/corr?n={quote(n)}&w=99999"))) <= 1200
    assert max(_misura(c.raw(f"/api/fthumb?p={quote(A.M[0]['src'])}&w=99999"))) <= 600
    assert {k[1] for k in E.TH} <= set(range(16, 1201)), "nella cache solo larghezze ammesse"


def test_cache_a_misura_fissa():
    c = {}
    for k in range(5): E.in_cache(c, k, b"x" * 10, 3, 1000)
    assert list(c) == [2, 3, 4], "al massimo 3 voci: escono le più vecchie"
    assert E.da_cache(c, 2) == b"x" * 10 and list(c) == [3, 4, 2], "chi viene letto torna in fondo (usato di recente)"
    assert E.da_cache(c, 99) is None
    E.in_cache(c, 5, b"y" * 25, 10, 40)
    assert list(c) == [2, 5] and sum(map(len, c.values())) <= 40, "al massimo 40 byte"
    E.in_cache(c, 6, b"z" * 100, 10, 40)
    assert list(c) == [6], "una voce sola più grande del limite resta (serve a chi l'ha chiesta)"


def test_cache_degli_spread_e_delle_miniature(con_spread, monkeypatch):
    c = con_spread; n = c.get("/api/state")["photos"][0]["n"]
    monkeypatch.setattr(E, "CACHE_VOCI", 3); monkeypatch.setattr(E, "TH_VOCI", 2)
    for k in ("0.05", "0.06", "0.07", "0.08", "0.09"): c.raw(f"/img/spread/0?k={k}")
    for w in (100, 110, 120, 130): c.raw(f"/img/thumb/{quote(n)}?w={w}")
    assert len(E.CACHE) == 3 and len(E.TH) == 2


def test_qualita_e_larghezza_dell_esportazione(con_spread, monkeypatch):
    c = con_spread; dest = os.path.join(c.progetto, "Esportazioni", "prova")
    ok, r = c.prova("/api/export", {"fmt": "jpg", "range": "1", "res": "anteprima", "q": "tanta", "dest": dest})
    assert not ok and r["errore"] == "q: non è un numero"
    ok, r = c.prova("/api/export", {"fmt": "pdf", "range": "1", "width": "larga", "dest": dest})
    assert not ok and r["errore"] == "width: non è un numero"
    usate = []
    monkeypatch.setattr(E, "_scrivi_img", lambda im, f, **kw: (usate.append(kw["quality"]), im.save(f, "JPEG", quality=kw["quality"])))
    c.post("/api/export", {"fmt": "jpg", "range": "1", "res": "anteprima", "q": 1000, "dest": dest}); attendi_log(c)
    assert usate == [100]
    pagine = []

    def pdf(path, jpegs, dpi=150):
        pagine.extend(w for _, w, _ in jpegs)
        with open(path, "wb") as f: f.write(b"%PDF finto" * 200)
    monkeypatch.setattr(E, "write_pdf", pdf)
    c.post("/api/export", {"fmt": "pdf", "range": "1", "width": 10**9, "dest": dest}); attendi_log(c)
    assert pagine and max(pagine) <= 6000


def test_abbina_con_il_limite_di_pixel(tmp_path, monkeypatch, capsys):
    """prima abbina.py toglieva il limite (Image.MAX_IMAGE_PIXELS = None): un PNG da 400 milioni di pixel in 2 KB bloccava la macchina"""
    web, orig = tmp_path / "web", tmp_path / "originali"; web.mkdir(); orig.mkdir()
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", None)
    come_script(monkeypatch, "abbina", "--web", str(web), "--originali", str(orig), "--dest", str(tmp_path / "dest"), "--prova")
    assert Image.MAX_IMAGE_PIXELS == A.limite_pixel() and capsys.readouterr().out.startswith("selezione: 0 foto")
