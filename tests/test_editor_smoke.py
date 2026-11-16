"""Prova dell'editor (era tests/smoke.py della 1.5): progetto temporaneo, operazioni principali, salvataggio, riapertura,
Tono, esportazioni JPG e PDF ed errori. Gira nel processo dei test (editor su una porta libera); niente Photoshop."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request

import pytest
from aiuti import attendi_log
from PIL import Image

from impaginatore import formato
from impaginatore.piattaforma import dialoghi

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _op(c, st, o):
    return c.post("/api/op", dict(cid="smoke", rev=st["rev"], **o))


def _esporta(c, **o):
    ok, r = c.prova("/api/export", o)
    if not ok: return False, [r.get("errore", "")]
    L = attendi_log(c)
    return not any(x.startswith("ERRORE") for x in L), L


@pytest.mark.skipif(not shutil.which("node"), reason="serve node per controllare la sintassi")
@pytest.mark.parametrize("pagina", ["index.html", "home.html"])
def test_codice_della_pagina_senza_errori_di_sintassi(pagina):
    with open(os.path.join(RADICE, "src", "impaginatore", "risorse", pagina), encoding="utf-8") as f: js = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", f.read(), re.S))
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf: tf.write(js)
    try:
        r = subprocess.run(["node", "--check", tf.name], capture_output=True, text=True, encoding="utf-8")
    finally:
        os.unlink(tf.name)
    assert r.returncode == 0, r.stderr[:300]


def test_flusso_principale(editor):
    c, proj = editor, editor.progetto
    st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    assert len(names) == 10, "foto lette"
    t = c.post("/api/templates", {"photos": names[:2]})["items"][0]
    st = _op(c, st, {"op": "newspread", "pos": 0, "L": t["L"], "R": t["R"]}); assert len(st["spreads"]) == 1
    t3 = c.post("/api/templates", {"photos": names[2:5]})["items"][0]
    st = _op(c, st, {"op": "newspread", "pos": 1, "L": t3["L"], "R": t3["R"]}); assert len(st["spreads"]) == 2
    st = _op(c, st, {"op": "addtext", "s": 0, "fx": 0.1, "fy": 0.1, "fw": 0.4, "fh": 0, "tx": "Prova"})
    tx = [i for i in st["spreads"][0]["items"] if i.get("kind") == "txt"]; assert len(tx) == 1, "testo aggiunto"
    st = _op(c, st, {"op": "settext", "at": [0, tx[0]["side"], tx[0]["idx"]], "tx": "Ciao", "size": 150, "lh": 1.5, "caps": True, "tr": 40, "al": "center"})
    tx = [i for i in st["spreads"][0]["items"] if i.get("kind") == "txt"][0]
    assert tx["tx"] == "Ciao" and tx["caps"] and tx["lh"] == 1.5 and tx["al"] == "center", tx
    st = _op(c, st, {"op": "stella", "photo": names[0], "value": True}); assert any(p["n"] == names[0] and p["star"] for p in st["photos"])
    img = c.raw(f"/img/spread/0?k=0.05&h={st['spreads'][0]['h']}"); assert len(img) > 2000 and Image.open(__import__("io").BytesIO(img)).size[0] > 100
    assert st["canundo"]
    c.post("/api/save"); st = c.get("/api/state"); assert not st["dirty"] and not st.get("saveerr")
    doc = formato.leggi_album(os.path.join(proj, "album.json"))
    assert any(e.get("kind") == "txt" and e.get("caps") is True for sp in doc["spread"] for lato in ("sinistra", "destra") for e in sp[lato]["elementi"])
    assert not os.path.exists(os.path.join(proj, "spec.py")), "la 2.0 salva solo album.json"
    assert not [f for f in os.listdir(proj) if f.endswith(".tmp")], "nessun .tmp rimasto"
    assert "__pycache__" not in os.listdir(proj), "leggere il progetto non deve lasciare file nel progetto"
    with open(os.path.join(proj, "progetto.json"), encoding="utf-8") as f: json.load(f)
    prima = json.dumps([[(i.get("kind"), i.get("tx"), i.get("name")) for i in sp["items"]] for sp in st["spreads"]])
    # riapertura (stesso processo: inizializza rilegge tutto)
    c.E.inizializza(proj); st2 = c.get("/api/state")
    dopo = json.dumps([[(i.get("kind"), i.get("tx"), i.get("name")) for i in sp["items"]] for sp in st2["spreads"]])
    assert prima == dopo, "riapertura identica"
    assert any(p["star"] for p in st2["photos"]), "stella ricordata"
    assert st2["boot"] != st["boot"], "a ogni apertura la pagina deve vedere un avvio nuovo"


def test_tono(editor):
    c = editor; st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    for k in range(2):
        t = c.post("/api/templates", {"photos": names[3 * k:3 * k + 3]})["items"][0]; st = _op(c, st, {"op": "newspread", "pos": k, "L": t["L"], "R": t["R"]})
    T0 = c.get("/api/tono?s=1"); it0 = T0["items"]
    assert len(it0) >= 2 and all(k in it0[0] for k in ("d", "H", "S", "B", "stato", "stato_c")), it0[:1]
    assert len(c.get("/api/tono_all")) == len(st["spreads"])
    x0 = it0[0]; at0 = [1, x0["side"], x0["idx"]]
    st = _op(c, st, {"op": "set", "at": at0, "z": 1.5}); y1 = next(i for i in c.get("/api/tono?s=1")["items"] if i["name"] == x0["name"])
    assert (x0["d"], x0["H"], x0["S"]) == (y1["d"], y1["H"], y1["S"]), "il tono non cambia con la scala"
    st = _op(c, st, {"op": "set", "at": at0, "z": 1.0})
    st = _op(c, st, {"op": "tono_L", "value": 75}); T2 = c.get("/api/tono?s=1"); assert T2["rif"] == 75 and st["tono_L"] == 75
    fl = [i for i in T2["items"] if i["stato"] != "ok" and i.get("nuova") is not None]
    assert fl, "con lo standard 75 (il massimo) qualche foto va corretta (le foto di prova sono più scure)"
    f = fl[0]
    st = _op(c, st, {"op": "tono_fix", "items": [{"photo": f["name"], "ev": f["nuova"]}]}); g = next(i for i in c.get("/api/tono?s=1")["items"] if i["name"] == f["name"])
    assert abs(g["d"]) < abs(f["d"]) and abs(g["evp"] - f["evp"]) > 1e-6
    st = _op(c, st, {"op": "undo"}); h4 = next(i for i in c.get("/api/tono?s=1")["items"] if i["name"] == f["name"]); assert abs(h4["evp"] - f["evp"]) < 1e-6
    st = _op(c, st, {"op": "redo"}); st = _op(c, st, {"op": "undo"})
    st = _op(c, st, {"op": "tono_L", "value": 55}); st = _op(c, st, {"op": "tono_L", "value": 52})
    br = c.raw(f"/img/bruc?s=1&side={x0['side']}&idx={x0['idx']}&h=x"); assert br[:4] == b"\x89PNG"


def test_esportazioni_ed_errori(editor, tmp_path):
    c, proj = editor, editor.progetto; st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    for k in range(2):
        t = c.post("/api/templates", {"photos": names[2 * k:2 * k + 2]})["items"][0]; st = _op(c, st, {"op": "newspread", "pos": k, "L": t["L"], "R": t["R"]})
    dj = str(tmp_path / "out_jpg")
    assert c.codice("/api/export", dict(fmt="jpg", range="", dest=dj)) == 403, "destinazione mai scelta con la finestra di sistema"
    dialoghi.imposta(type("F", (dialoghi.Dialoghi,), {"_scegli": lambda self, t, m: [str(tmp_path)]})()); c.post("/api/pick", {"kind": "folder"})
    ok, L = _esporta(c, fmt="jpg", range="", dest=dj, res="bozza", q=80)
    jp = sorted(os.listdir(dj))
    assert ok and len(jp) == 2 and any(x.startswith("RISULTATO:") for x in L), L[-3:]
    assert all(Image.open(os.path.join(dj, f)).size[0] > 100 for f in jp) and not [f for f in jp if f.endswith(".tmp")]
    ok, L = _esporta(c, fmt="jpg", range="1", dest=dj, res="stampa", q=95); assert ok, L
    dp = str(tmp_path / "out_pdf"); ok, L = _esporta(c, fmt="pdf", range="", dest=dp, width=800, q=70, numeri=True)
    pdfs = os.listdir(dp)
    with open(os.path.join(dp, pdfs[0]), "rb") as f: assert ok and len(pdfs) == 1 and f.read(5) == b"%PDF-", L[-3:]
    ok, L = _esporta(c, fmt="jpg", range="99", dest=dj, res="bozza"); assert not ok and "inesistenti" in " ".join(L), L
    blocco = tmp_path / "file"; blocco.write_text("x", encoding="utf-8")
    ok, L = _esporta(c, fmt="jpg", range="", dest=str(blocco / "sotto"), res="bozza"); assert not ok and L and L[0], L
    ok, L = _esporta(c, fmt="gif", range="", dest=dj); assert not ok, L
    f0 = os.path.join(proj, "Foto", names[0] + ".jpg"); os.rename(f0, f0 + ".spostata")
    ok, L = _esporta(c, fmt="jpg", range="1", dest=dj, res="bozza"); assert not ok and "non si trovano" in " ".join(L) and names[0] in " ".join(L), L
    os.rename(f0 + ".spostata", f0)


def test_psd_senza_photoshop(editor, tmp_path, monkeypatch):
    """senza Photoshop l'export PSD si ferma subito con un messaggio chiaro (su Linux: Photoshop non esiste)"""
    from impaginatore.piattaforma import photoshop
    c = editor; st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    t = c.post("/api/templates", {"photos": names[:2]})["items"][0]; _op(c, st, {"op": "newspread", "pos": 0, "L": t["L"], "R": t["R"]})
    monkeypatch.setattr(photoshop, "trova", lambda: None)
    ok, r = c.prova("/api/export", {"fmt": "psd", "range": "1", "dest": os.path.join(c.progetto, "PSD")})
    assert not ok and r["errore"] == photoshop.motivo_assente()


def test_pagina_e_risorse(editor):
    c = editor
    html = c.raw("/").decode("utf-8"); assert '<script nonce="' in html and c.gettone not in html, "il gettone arriva dalla sessionStorage (VER-006)"
    assert c.get("/api/ping")["path"] == c.progetto
    assert c.get("/api/state")["home"] == "http://127.0.0.1:9"
    assert isinstance(c.get("/api/log"), list) and isinstance(c.get("/api/versioni"), list)
    fonts = c.get("/api/fonts")["fonts"]; assert isinstance(fonts, list)
    ok, r = c.prova("/api/nonesiste"); assert not ok and r["errore"] == "non trovato"
    ok, r = c.prova("/api/nonesiste", {}); assert not ok
    n = c.get("/api/state")["photos"][0]["n"]
    assert c.raw(f"/img/thumb/{n}?w=200")[:2] == b"\xff\xd8"
    req = urllib.request.Request(c.url(f"/img/thumb/{n}?w=200"), headers={"X-Impaginatore-Gettone": c.gettone})
    with urllib.request.urlopen(req) as r: et = r.headers["ETag"]
    req = urllib.request.Request(c.url(f"/img/thumb/{n}?w=200"), headers={"If-None-Match": et, "X-Impaginatore-Gettone": c.gettone})
    try: urllib.request.urlopen(req); assert False, "doveva rispondere 304"
    except urllib.error.HTTPError as e: assert e.code == 304
    assert "dim" in c.get(f"/api/info/{n}")
