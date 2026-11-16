"""VER-002: una foto rovinata o incompleta (JPEG troncato, copia a metà) non blocca l'apertura del progetto.
Una foto nuova che non si decodifica resta fuori (scartata, con il motivo) e si riprova all'apertura dopo; una foto che
il progetto usa già resta al suo posto con un riquadro grigio, l'esportazione la segnala, e quando il file torna buono
l'editor la rifà da solo."""
import io
import json
import os
import struct

import pytest
from aiuti import crea_foto
from PIL import Image

from impaginatore.motore import album as A


def tronca(path, frazione=3):
    b = io.BytesIO(); Image.new("RGB", (800, 600), (9, 9, 9)).save(b, "JPEG")
    with open(path, "wb") as f: f.write(b.getvalue()[:len(b.getvalue()) // frazione])


def nuovo_progetto(home):
    p = home.nuovo({"nome": "Rovinate", "w": "30", "h": "30"})
    crea_foto(os.path.join(p, "Foto"), [("H01", 600, 400, "2026:01:01 10:00:00"), ("H02", 600, 400, "2026:01:01 10:00:01")])
    return p


def test_foto_nuova_troncata_resta_fuori(home, apri_editor):
    p = nuovo_progetto(home); tronca(os.path.join(p, "Foto", "troncata.jpg"))
    c = apri_editor(p); st = c.get("/api/state")
    assert [x["n"] for x in st["photos"]] == ["H01", "H02"]
    assert st["scartate"] == [dict(n="troncata.jpg", motivo=A.DANNEGGIATA)]
    with open(os.path.join(p, "_cache", "meta.json"), encoding="utf-8") as f: assert "troncata.jpg" not in {m["n"] for m in json.load(f)}
    assert not os.path.exists(os.path.join(p, "_cache", "thumbs", "troncata.jpg"))


def test_foto_del_progetto_rovinata_dopo(home, apri_editor, tmp_path):
    p = nuovo_progetto(home)
    c = apri_editor(p); nomi = [x["n"] for x in c.get("/api/state")["photos"]]
    c.post("/api/op", dict(op="newspreadsel", names=nomi, pos=0)); c.post("/api/save", {})
    c.srv.shutdown(); c.srv.server_close(); c.E.ferma()
    os.remove(os.path.join(p, "_cache", "thumbs", "H01.jpg")); tronca(os.path.join(p, "Foto", "H01.jpg"))
    c = apri_editor(p); st = c.get("/api/state"); E = c.E
    assert [x["n"] for x in st["photos"]] == ["H01", "H02"] and len(st["spreads"]) == 1, "il progetto si apre com'era"
    assert st["scartate"] == [dict(n="H01.jpg", motivo=A.DANNEGGIATA)] and "H01.jpg" in A.DANNEGGIATE
    segnaposto = os.path.join(p, "_cache", "thumbs", "H01.jpg")
    with Image.open(segnaposto) as im: assert im.convert("RGB").getpixel((5, 5)) == A.GRIGIO_SEGNAPOSTO
    assert os.stat(segnaposto).st_mtime == 0 and E.foto_cambiate() == [], "finché il file non cambia non si riprova"
    assert c.codice("/img/thumb/H01?w=100") == 200 and c.codice("/img/spread/0?k=0.1") == 200
    ok, r = c.prova("/api/export", dict(fmt="jpg", range="1", res="anteprima"))
    assert not ok and "danneggiat" in r["errore"] and "H01.jpg" in r["errore"]
    crea_foto(str(tmp_path / "buona"), [("H01", 600, 400, "2026:01:01 10:00:00")])
    os.replace(tmp_path / "buona" / "H01.jpg", os.path.join(p, "Foto", "H01.jpg"))
    assert E.foto_cambiate() == [0]
    assert E.aggiorna_foto([0])[0] == ["H01.jpg"]
    assert "H01.jpg" not in A.DANNEGGIATE and c.get("/api/state")["scartate"] == []
    with Image.open(segnaposto) as im: assert im.convert("RGB").getpixel((5, 5)) != A.GRIGIO_SEGNAPOSTO


def test_foto_che_manca_e_miniatura_che_manca(home, apri_editor):
    p = nuovo_progetto(home)
    c = apri_editor(p); c.srv.shutdown(); c.srv.server_close(); c.E.ferma()
    os.remove(os.path.join(p, "_cache", "thumbs", "H02.jpg")); os.remove(os.path.join(p, "Foto", "H02.jpg"))
    c = apri_editor(p); st = c.get("/api/state")
    assert "H02" in [x["n"] for x in st["photos"]] and st["mancanti"] == ["H02.jpg"] and c.E.foto_cambiate() == []


def test_volti_di_una_miniatura_illeggibile(home, apri_editor):
    p = nuovo_progetto(home)
    c = apri_editor(p); c.srv.shutdown(); c.srv.server_close(); c.E.ferma()
    with open(os.path.join(p, "_cache", "thumbs", "H02.jpg"), "wb") as f: f.write(b"")
    os.remove(os.path.join(p, "_cache", "faces.json"))
    apri_editor(p)
    assert A.F["H02.jpg"] == [] and isinstance(A.F["H01.jpg"], list)


@pytest.mark.parametrize("errore", [struct.error("dati EXIF"), SyntaxError("non è un JPEG"), EOFError(), IndexError(), KeyError(274)])
def test_errori_di_pillow_alla_lettura_delle_misure(tmp_path, monkeypatch, errore):
    crea_foto(str(tmp_path), [("H01", 60, 40, None)])

    def rotta(f): raise errore
    monkeypatch.setattr(A, "_meta_one", rotta); A.SCARTATE.clear()
    assert A._nuove([str(tmp_path / "H01.jpg")], []) == [] and A.SCARTATE == [dict(n="H01.jpg", motivo="il file non si apre come foto")]


def test_aggiornamento_che_non_riesce_a_rifare_la_miniatura(editor, monkeypatch):
    """il file si legge ma la miniatura no (per esempio un profilo colore rotto): la foto risulta non aggiornata e danneggiata"""
    E = editor.E
    monkeypatch.setattr(A, "in_srgb", lambda im: (_ for _ in ()).throw(OSError("profilo rotto")))
    ok, ars, ko = E.aggiorna_foto([0])
    assert ok == [] and ko == [A.M[0]["n"]] and A.M[0]["n"] in A.DANNEGGIATE
