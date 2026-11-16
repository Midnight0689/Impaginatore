"""UX-004 (A-23): «Ricollega foto» collega una foto mancante solo al suo originale. Salta le cartelle del programma (la
miniatura da 1200 px in _cache/thumbs), le uscite dei progetti, le cartelle nascoste e riservate e i collegamenti che
portano lì (VER-004); un file con lo stesso nome ma misure o data diverse non si collega; le foto rinominate si propongono
e si collegano solo se l'utente le sceglie."""
import os
import shutil

import pytest
from PIL import Image

from impaginatore.motore import album as A


def _sposta(c, n, dove):
    """la foto n esce da Foto e finisce in dove (percorso dentro il progetto o altrove); restituisce il nuovo percorso"""
    os.makedirs(os.path.dirname(dove), exist_ok=True); shutil.move(os.path.join(c.progetto, "Foto", n + ".jpg"), dove); return dove


@pytest.fixture
def sparse(editor, casa):
    """foto sparite da Foto e finite nei posti sbagliati (e una in quello giusto) dentro la cartella del progetto"""
    c = editor; P = c.progetto; L = os.path.join(P, "Lavoro")
    os.rename(os.path.join(P, "Foto", "H01.jpg"), os.path.join(P, "Foto", "H01 rinominata.jpg"))
    with Image.open(os.path.join(P, "Foto", "H02.jpg")) as im: im.resize((450, 300)).save(os.path.join(P, "Foto", "piccola.jpg"))
    os.remove(os.path.join(P, "Foto", "H02.jpg")); os.makedirs(L); os.rename(os.path.join(P, "Foto", "piccola.jpg"), os.path.join(L, "H02.jpg"))
    os.remove(os.path.join(P, "Foto", "V03.jpg")); os.symlink(os.path.join(P, "_cache", "thumbs", "V03.jpg"), os.path.join(L, "V03.jpg"))
    _sposta(c, "V04", str(casa / ".config" / "V04.jpg")); os.symlink(str(casa / ".config" / "V04.jpg"), os.path.join(L, "V04.jpg"))
    _sposta(c, "Q05", os.path.join(P, ".nascosta", "Q05.jpg"))
    _sposta(c, "H06", os.path.join(P, "Esportazioni", "JPG", "H06.jpg"))
    _sposta(c, "V07", os.path.join(L, "V07 copia.jpg"))
    _sposta(c, "Q09", os.path.join(L, "sotto", "Q09.jpg"))
    assert sorted(c.get("/api/state")["mancanti"]) == sorted(["H01.jpg", "H02.jpg", "V03.jpg", "V04.jpg", "Q05.jpg", "H06.jpg", "V07.jpg", "Q09.jpg"])
    return c


def test_ricollega_non_usa_miniature_ne_copie(sparse):
    c = sparse; P = c.progetto; L = os.path.join(P, "Lavoro")
    r = c.post("/api/ricollega", {"cartella": P, "prova": True})
    attese = dict(trovate=1, mancanti=["H01.jpg", "H02.jpg", "V03.jpg", "V04.jpg", "Q05.jpg", "H06.jpg", "V07.jpg"], totale=10,
                  diverse=[dict(n="H02.jpg", file=os.path.join(L, "H02.jpg"), motivo="misure diverse (450 × 300 invece di 900 × 600)")],
                  proposte=[dict(n="H01.jpg", file=os.path.join(P, "Foto", "H01 rinominata.jpg"))])
    assert sorted(r["mancanti"]) == sorted(attese["mancanti"]) and dict(r, mancanti=None) == dict(attese, mancanti=None), r
    assert len(c.get("/api/state")["mancanti"]) == 8, "con «prova» non cambia niente"
    r = c.post("/api/ricollega", {"cartella": P})
    assert r["trovate"] == 1 and A.M[A.IDX["Q09"] - 1]["src"] == os.path.join(L, "sotto", "Q09.jpg")
    assert not any(os.sep + "_cache" + os.sep in m["src"] for m in A.M), "mai una miniatura al posto di un originale (A-23)"
    ok, e = c.prova("/api/ricollega", {"cartella": P, "scelte": {"H01.jpg": os.path.join(L, "V07 copia.jpg")}})
    assert not ok and e["errore"] == "H01.jpg: «V07 copia.jpg» non è tra le foto proposte"
    ok, e = c.prova("/api/ricollega", {"cartella": P, "scelte": ["H01.jpg"]}); assert not ok and "scelte non valide" in e["errore"]
    r = c.post("/api/ricollega", {"cartella": P, "scelte": {"H01.jpg": os.path.join(P, "Foto", "H01 rinominata.jpg")}})
    assert r["trovate"] == 1 and r["proposte"] == [] and "H01.jpg" not in c.get("/api/state")["mancanti"]
    assert A.M[A.IDX["H01"] - 1]["src"] == os.path.join(P, "Foto", "H01 rinominata.jpg")


def test_ricollega_in_una_cartella_del_programma(sparse):
    c = sparse; P = c.progetto
    for d in (os.path.join(P, "_cache", "thumbs"), os.path.join(P, "_cache"), os.path.join(P, "Esportazioni")):
        ok, e = c.prova("/api/ricollega", {"cartella": d}); assert not ok and e["errore"].startswith("Questa cartella è del programma"), d
    assert len(c.get("/api/state")["mancanti"]) == 8


def test_foto_che_non_si_apre_con_lo_stesso_nome(sparse):
    """un file con il nome giusto che non è una foto: resta mancante, con il motivo; e non fa da proposta per le altre"""
    c = sparse; P = c.progetto
    with open(os.path.join(P, "Lavoro", "V10.jpg"), "wb") as f: f.write(b"non sono una foto")
    with open(os.path.join(P, "Lavoro", "zz.jpg"), "wb") as f: f.write(b"nemmeno io")
    os.remove(os.path.join(P, "Foto", "V10.jpg"))
    r = c.post("/api/ricollega", {"cartella": P, "prova": True})
    assert dict(n="V10.jpg", file=os.path.join(P, "Lavoro", "V10.jpg"), motivo="non si apre come foto") in r["diverse"]


def test_stessa_misura_ma_altra_data(editor, tmp_path):
    """stesso nome e stesse misure ma un'altra data di scatto: è un'altra foto"""
    from aiuti import crea_foto
    c = editor; os.remove(os.path.join(c.progetto, "Foto", "H01.jpg"))
    crea_foto(os.path.join(c.progetto, "Altre"), [("H01", 900, 600, "2020:01:01 08:00:00")])
    r = c.post("/api/ricollega", {"cartella": c.progetto})
    assert r["trovate"] == 0 and r["diverse"] == [dict(n="H01.jpg", file=os.path.join(c.progetto, "Altre", "H01.jpg"), motivo="data di scatto diversa")]
