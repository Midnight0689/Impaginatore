"""UX-011 (A-18, A-19): i JPG «Stampa · 300 dpi» si fanno dagli originali, alla misura vera e con l'abbondanza; le anteprime
a schermo restano sulle miniature. Foto sintetiche con un rumore fine (dettaglio che la miniatura da 1200 px non ha) e
quattro quadranti di colore (per confrontare la geometria del ritaglio con quella dell'anteprima)."""
import io
import os
import threading

import numpy as np
import pytest
from aiuti import attendi_log
from PIL import Image, ImageFilter

from impaginatore.motore import album as A
from impaginatore.motore import album_libere as FL


def originale(path, w, h, orientamento=None, seme=7):
    """foto «ad alta frequenza»: quadranti di colore e rumore a blocchi di 2 px, con data di scatto (e rotazione EXIF)"""
    a = np.zeros((h, w, 3), np.int32)
    a[:h // 2, :w // 2] = (200, 40, 40); a[:h // 2, w // 2:] = (40, 200, 40); a[h // 2:, :w // 2] = (40, 40, 200); a[h // 2:, w // 2:] = (220, 220, 60)
    rumore = np.random.default_rng(seme).integers(-70, 70, ((h + 1) // 2, (w + 1) // 2, 1)).repeat(2, 0).repeat(2, 1)[:h, :w]
    ex = Image.Exif(); ex.get_ifd(0x8769)[36867] = "2026:05:23 10:00:0%d" % seme
    if orientamento: ex[274] = orientamento
    Image.fromarray(np.clip(a + rumore, 0, 255).astype(np.uint8)).save(path, "JPEG", quality=95, exif=ex.tobytes())


def dettaglio(im):
    """energia dei bordi (alte frequenze) dell'immagine"""
    return float(np.asarray(im.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32).mean())


def scarto(a, b):
    """differenza media (0-255) fra l'immagine a e b ridotta alla stessa misura, tutte e due sfocate un poco: conta dove
    stanno i quadranti (la geometria), non il rumore fine"""
    sf = lambda im: np.asarray(im.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    return float(np.abs(sf(a) - sf(b.resize(a.size, Image.LANCZOS))).mean())


def confine(im, y):
    """dove (frazione della larghezza) il rosso del quadrante in alto a sinistra della foto di sinistra lascia il posto al
    verde, lungo la riga y (frazione dell'altezza): misura la geometria del ritaglio a meno di un pixel"""
    r = np.asarray(im.filter(ImageFilter.GaussianBlur(max(1, im.width // 400))), dtype=np.float32)[round(y * (im.height - 1)), :im.width // 2, 0]
    k = int(np.argmax(r[1:] < 120)); return (k + (r[k] - 120) / max(r[k] - r[k + 1], 1e-6)) / im.width


@pytest.fixture
def stampa(home, apri_editor):
    """album 20 × 10 cm con 3 mm di abbondanza; spread 1: due foto a tutta pagina (la seconda ruotata dall'EXIF);
    spread 2: le stesse, la prima inclinata di 4°"""
    p = home.nuovo({"nome": "Stampa", "w": "20", "h": "10", "abb": "3"})
    originale(os.path.join(p, "Foto", "A01.jpg"), 3000, 2000, seme=1)
    originale(os.path.join(p, "Foto", "B02.jpg"), 3000, 2000, orientamento=6, seme=2)
    c = apri_editor(p); E = c.E
    assert [(m["w"], m["h"]) for m in A.M] == [(3000, 2000), (2000, 3000)], "misure come la foto si vede"
    full = lambda i: dict(mode="I", module="FULL", mirror=False, photos=[i])
    E.do_op(dict(op="newspread", pos=0, L=full(0), R=full(1)))
    E.do_op(dict(op="dup", s=0)); E.do_op(dict(op="set", at=[1, "L", 0], a=4))
    return c


def test_jpg_di_stampa_dagli_originali_con_abbondanza(stampa):
    c = stampa; E = c.E
    assert A.B == 35 and E.BL == 35, "3 mm a 300 ppi"
    r = c.post("/api/export", {"fmt": "jpg", "res": "stampa", "q": 95, "range": "1-2"}); assert r == {"spread": 2}
    L = attendi_log(c); assert "ESPORTATI 2 spread su 2" in L, L
    cartella = os.path.join(c.progetto, "Esportazioni", "JPG")
    for s in (0, 1):
        with Image.open(os.path.join(cartella, f"Stampa - Spread {s + 1:02d}.jpg")) as f:
            st = f.convert("RGB"); assert f.size == (A.CW, A.CH), "l'abbondanza resta nel file (A-19)"
            assert round(f.info["dpi"][0]) == 300
        tup = E.spread_tuple(s)
        miniature = A.render(tup, 1.0, True)                      # come si faceva prima: miniature da 1200 px ingrandite
        assert dettaglio(st) > 1.6 * dettaglio(miniature), (dettaglio(st), dettaglio(miniature))
        # stessa geometria dell'anteprima: tutto lo spread (abbondanza compresa) e la parte che si vede a schermo
        piccola = A.render(tup, 0.3, True)
        assert scarto(piccola, st) < 6, scarto(piccola, st)
        vista = Image.open(io.BytesIO(E.spread_jpg(s, 0.3))).convert("RGB")
        senza = st.crop((A.B, A.B, A.CW - A.B, A.CH - A.B))
        assert scarto(vista, senza) < 6
        if s == 0:
            assert abs(confine(piccola, 0.3) - confine(st, 0.3)) < 0.0015, (confine(piccola, 0.3), confine(st, 0.3))
            assert abs(confine(vista, 0.3) - confine(senza, 0.3)) < 0.0015 < 0.005 < abs(confine(vista, 0.3) - confine(st, 0.3)), "l'abbondanza conta: senza toglierla i bordi non coincidono"


def test_anteprima_resta_sulle_miniature(stampa, monkeypatch):
    """a schermo (immagini dello spread, foto «live», JPG «schermo» e PDF) non si apre mai un originale"""
    c = stampa
    monkeypatch.setattr(A, "apri_foto", lambda f: (_ for _ in ()).throw(AssertionError("originale aperto")))
    assert c.codice("/img/spread/1?k=0.3") == 200 and c.codice("/img/live?s=1&side=L&idx=0&k=0.3") == 200
    c.post("/api/export", {"fmt": "jpg", "res": "bozza"}); assert "ESPORTATI 2 spread su 2" in attendi_log(c)
    with Image.open(os.path.join(c.progetto, "Esportazioni", "JPG", "Stampa - Spread 01.jpg")) as f: b = round(A.B * 0.25); assert f.size == (round(A.CW * 0.25) - 2 * b, round(A.CH * 0.25) - 2 * b), "schermo: senza abbondanza, come prima"
    c.post("/api/export", {"fmt": "pdf", "width": 600}); assert any(x.startswith("RISULTATO:") for x in attendi_log(c))


def test_originale_troppo_grande_o_che_non_si_legge(stampa, monkeypatch):
    """il limite di pixel vale anche per la stampa; un originale sparito o danneggiato dopo l'apertura non dà un file sbagliato"""
    c = stampa
    monkeypatch.setenv("IMPAGINATORE_MAX_MPIXEL", "1")
    c.post("/api/export", {"fmt": "jpg", "res": "stampa", "range": "1"}); L = attendi_log(c)
    assert any(x.startswith("SALTATO spread 1 -> A01.jpg: foto troppo grande") for x in L), L
    monkeypatch.delenv("IMPAGINATORE_MAX_MPIXEL")
    assert A.foto_rgb(1, originale=True).size == (2000, 3000), "senza una misura: tutta, raddrizzata dall'EXIF"
    assert A.foto_rgb(1, originale=True, serve=(700, 1000)).size == (1000, 1500), "ridotta già in decodifica (a metà: un quarto sarebbe sotto la misura chiesta)"
    with pytest.raises(ValueError, match="B02.jpg: l'originale non si trova"):
        os.rename(A.M[1]["src"], A.M[1]["src"] + ".via"); A.foto_rgb(1, originale=True)
    A.DANNEGGIATE["A01.jpg"] = 0
    with pytest.raises(ValueError, match="A01.jpg: file danneggiato"): A.foto_rgb(0, originale=True)


def test_miniatura_che_non_ce_ancora(monkeypatch, tmp_path):
    """una miniatura non ancora pronta (preparazione in sottofondo): riquadro grigio con le proporzioni della foto"""
    monkeypatch.setattr(A, "THUMBS", str(tmp_path)); monkeypatch.setattr(A, "M", [dict(n="x.jpg", w=600, h=300)])
    im = A.foto_rgb(0); assert im.size == (300, 150) and im.getpixel((10, 10)) == A.GRIGIO_SEGNAPOSTO


def test_foto_corrente_per_thread():
    """le correzioni (apply_ev) leggono la foto che si sta disegnando nel proprio thread: un'esportazione e un'anteprima
    nello stesso momento non si scambiano i ritocchi"""
    FL._CUR[0] = 3; visto = []
    t = threading.Thread(target=lambda: (visto.append(FL._CUR[0]), FL._CUR.__setitem__(0, 9), visto.append(FL._CUR[0]))); t.start(); t.join()
    assert visto == [None, 9] and FL._CUR[0] == 3
