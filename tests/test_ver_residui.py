"""VER-015: residui di BUG-006 e BUG-007. Le foto e i file si aprono con «with» (chiusi anche quando la lettura non
riesce); le eccezioni che prima finivano in print o sparivano sono specifiche e vanno nel registro."""
import logging
import os

import pytest
from aiuti import come_script, crea_foto
from PIL import Image

from impaginatore import formato
from impaginatore.editor import server as E
from impaginatore.motore import album as A


@pytest.fixture
def aperte(monkeypatch):
    """immagini aperte con Image.open durante la prova: alla fine devono essere tutte chiuse"""
    viste, vero = [], Image.open

    def apri(*a, **k):
        im = vero(*a, **k); viste.append(im); return im
    monkeypatch.setattr(Image, "open", apri)
    return viste


def _chiuse(viste): return [im for im in viste if getattr(im, "fp", None) is not None]


def test_abbina_chiude_gli_originali(tmp_path, monkeypatch, capsys, aperte):
    """prima abbina.py apriva ogni originale per la misura e lo lasciava aperto (con centinaia di foto: troppi file aperti)"""
    web, orig = str(tmp_path / "web"), str(tmp_path / "originali")
    crea_foto(web, [("A1", 300, 200, None), ("A2", 300, 200, None)]); crea_foto(orig, [("A1", 900, 600, None), ("A2", 320, 200, None)])
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", Image.MAX_IMAGE_PIXELS)
    come_script(monkeypatch, "abbina", "--web", web, "--originali", orig, "--dest", str(tmp_path / "dest"), "--prova", "--lato-minimo", "800")
    out = capsys.readouterr().out
    assert "A2.jpg: originale piccolo (320x200)" in out and len(aperte) >= 4 and _chiuse(aperte) == []


def test_leggi_rgb_chiude_il_file(tmp_path, aperte, monkeypatch):
    crea_foto(str(tmp_path), [("H01", 60, 40, None)])
    im = A.leggi_rgb(str(tmp_path / "H01.jpg"))
    assert im.mode == "RGB" and im.size == (60, 40) and _chiuse(aperte) == []

    def rotta(self, *a, **k): raise OSError("decodifica non riuscita")
    monkeypatch.setattr(Image.Image, "convert", rotta)
    with pytest.raises(OSError): A.leggi_rgb(str(tmp_path / "H01.jpg"))
    assert _chiuse(aperte) == [], "chiuso anche quando la lettura non riesce"


def test_testi_del_pacchetto(tmp_path):
    p = str(tmp_path / "LEGGIMI.txt")
    E._scrivi_testo(p, "àè\n"); assert E._leggi_testo(p) == "àè\n"
    with open(p, "wb") as f: f.write(b"\xff ok")
    assert E._leggi_testo(p) == "� ok"


def test_registro_dei_progetti_illeggibile(home_srv, caplog):
    """senza registro (prima volta) nessun avviso; un registro rovinato si annota e la schermata riparte da un elenco vuoto"""
    H = home_srv.modulo; caplog.set_level(logging.WARNING, logger="impaginatore.home")
    if os.path.exists(H.REG): os.remove(H.REG)
    assert H.registro() == [] and caplog.records == []
    for rotto in ('{"rotto', "42", '[["non", "stringhe"]]'):
        with open(H.REG, "w", encoding="utf-8") as f: f.write(rotto)
        caplog.clear(); assert H.registro() == []
        assert [r.getMessage() for r in caplog.records][0].startswith("elenco dei progetti aggiunti illeggibile ("), rotto
    formato.scrivi_json(H.REG, [])

