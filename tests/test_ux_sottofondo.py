"""UX-012: l'editor si apre con i soli metadati e prepara miniature e volti mentre si lavora; l'import a caldo aggiunge le
foto senza riavviare e senza perdere annulla e ripeti. Le immagini a schermo mostrano un riquadro grigio finché la
miniatura non c'è; la stampa non ne è toccata (legge gli originali)."""
import io
import json
import os
import threading

import pytest
from aiuti import attendi, crea_foto
from PIL import Image

from impaginatore.editor import server as E
from impaginatore.motore import album as A
from impaginatore.motore import album_libere as FL


def grigio(dati, quota=0.95):
    """almeno questa quota dell'immagine è del grigio dei segnaposto (a meno della compressione JPEG)"""
    import numpy as np
    a = np.asarray(Image.open(io.BytesIO(dati)).convert("RGB"), dtype=np.int16)
    return float((np.abs(a - np.array(A.GRIGIO_SEGNAPOSTO)).max(axis=2) <= 6).mean()) >= quota


@pytest.fixture
def aperto(home, monkeypatch):
    """progetto con 10 foto aperto in sottofondo; la preparazione aspetta il via (cancello) per essere osservata"""
    p = home.nuovo({"nome": "Sottofondo", "w": "30", "h": "20"}); crea_foto(os.path.join(p, "Foto"))
    with open(os.path.join(p, "Foto", "rotta.jpg"), "wb") as f:
        b = io.BytesIO(); Image.new("RGB", (800, 600), (9, 9, 9)).save(b, "JPEG"); f.write(b.getvalue()[:len(b.getvalue()) // 3])
    via = threading.Event(); vera = A.prepara_miniatura
    monkeypatch.setattr(A, "prepara_miniatura", lambda m, cartella=None: (via.wait(30), vera(m, cartella))[1])
    E.inizializza(p, sottofondo=True)
    yield p, via
    via.set(); E.ferma()


def test_editor_subito_e_foto_dopo(aperto):
    p, via = aperto; thumbs = os.path.join(p, "_cache", "thumbs")
    assert len(A.M) == 11 and not [f for f in os.listdir(thumbs) if not f.startswith(".")], "niente miniature: solo i metadati"
    assert E.prep_stato() == dict(fatte=0, totale=11, volti=False, attivo=True) and E.state()["prep"]["totale"] == 11
    ordine = [m["n"] for m in A.da_preparare()[0]]; assert ordine == [m["n"] for m in sorted(A.M, key=lambda m: m["dt"])], "in ordine di scatto"
    assert grigio(E.thumb_jpg("H01", 200)) and E.TH == {}, "riquadro grigio, che non si tiene in cache"
    E.do_op(dict(op="newspreadsel", names=["H01", "V03"], pos=0)); assert grigio(E.spread_jpg(0, 0.1), 0.3), "si lavora intanto"
    E.do_op(dict(op="set", at=[0, "L", 0], a=5)); assert E.spread_jpg(0, 0.1)
    assert E.tono_spread(0, light=True)["items"] and E.corr_thumb("H01", 120, {}), "tono e riquadro Design sul riquadro grigio"
    via.set(); attendi(lambda: not E.PREP["attivo"], 60)
    assert E.prep_stato() == dict(fatte=11, totale=11, volti=True, attivo=False)
    assert not grigio(E.thumb_jpg("H01", 200)) and not grigio(E.spread_jpg(0, 0.1), 0.3), "la miniatura pronta si vede subito (PV cambiata)"
    with open(os.path.join(p, "_cache", "faces.json"), encoding="utf-8") as f: assert set(json.load(f)) == {m["n"] for m in A.M}
    assert "rotta.jpg" in A.DANNEGGIATE and dict(n="rotta.jpg", motivo=A.danneggiata()) in A.SCARTATE, "in sottofondo la foto rovinata resta, segnata"
    assert not [f for f in os.listdir(thumbs) if f.startswith(".")], "nessun file a metà"
    E.prepara_in_sottofondo(); assert E.PREP["attivo"] is False, "niente da fare: non parte"


def test_cambio_di_progetto_ferma_la_preparazione(aperto):
    p, via = aperto; gen = E.PREP["gen"]
    t = threading.Thread(target=E.ferma_preparazione); t.start()
    attendi(lambda: E.PREP["gen"] != gen, 10); via.set(); t.join(30)
    assert not t.is_alive() and E.PREP_FILO[0] is None and E.PREP["fatte"] == 0, "le miniature finite dopo il cambio non si pubblicano"


def test_volti_trovati_rifanno_le_anteprime(aperto, monkeypatch):
    p, via = aperto
    monkeypatch.setattr(A, "_build_faces", lambda meta: {m["n"]: [[0.4, 0.4, 0.6, 0.6]] if m["n"] == "H01.jpg" else [] for m in meta})
    via.set(); attendi(lambda: not E.PREP["attivo"], 60)
    assert A.F["H01.jpg"] == [[0.4, 0.4, 0.6, 0.6]] and E.PV["H01"] == 2 and E.PV["H02"] == 1, "solo le foto con volti nuovi"


def test_progetto_cambiato_mentre_si_cercano_i_volti(aperto, monkeypatch):
    p, via = aperto; dentro = threading.Event(); avanti = threading.Event()
    monkeypatch.setattr(A, "_build_faces", lambda meta: (dentro.set(), avanti.wait(30), {m["n"]: [] for m in meta})[2])
    via.set(); assert dentro.wait(30); filo = E.PREP_FILO[0]
    with E.LOCK: E.PREP["gen"] += 1
    avanti.set(); filo.join(30)
    assert not filo.is_alive() and E.PREP["volti"] is False and "H01.jpg" not in A.F, "volti di un progetto che non è più aperto: non si pubblicano"


def test_errore_inatteso_ferma_la_preparazione(aperto, monkeypatch):
    """un errore che non è di una foto (disco pieno…): la preparazione si ferma e lo dice, l'editor resta com'è"""
    p, via = aperto; monkeypatch.setattr(A, "segna_danneggiata", lambda m: (_ for _ in ()).throw(OSError(28, "disco pieno")))
    via.set(); attendi(lambda: not E.PREP["attivo"], 60)
    assert any(x.startswith("preparazione delle foto interrotta:") and "disco pieno" in x for x in E.LOG) and E.PREP["volti"] is False


def test_import_a_caldo(editor, casa):
    c = editor; nuove = os.path.join(c.progetto, "Nuove"); crea_foto(nuove, [("N01", 400, 300, "2026:05:23 11:00:00"), ("N02", 300, 400, None)])
    c.post("/api/op", dict(op="newspreadsel", names=["H01"], pos=0)); boot = c.get("/api/ping")["boot"]
    r = c.post("/api/import", {"paths": [nuove], "a_caldo": True})
    assert r == {"importate": 2, "saltate": 0, "riavvio": False, "aggiunte": 2}
    st = c.get("/api/state"); assert [x["n"] for x in st["photos"]][-2:] == ["N01", "N02"] and st["canundo"] and c.get("/api/ping")["boot"] == boot, "niente riavvio, annulla resta"
    assert A.IDX["N02"] == 12 and st["photos"][0]["n"] == "H01", "in coda: la numerazione non cambia"
    attendi(lambda: not c.get("/api/state")["prep"]["attivo"], 60)
    assert os.path.exists(os.path.join(c.progetto, "_cache", "thumbs", "N01.jpg")) and "N02.jpg" in A.F and c.get("/api/ping")["prep"] == 2
    r = c.post("/api/import", {"paths": [nuove], "a_caldo": True}); assert r == {"importate": 0, "saltate": 2, "riavvio": False, "aggiunte": 0}
    altra = os.path.join(c.progetto, "Altra"); crea_foto(altra, [("H01", 300, 200, None)], estensione=".png")
    r = c.post("/api/import", {"paths": [altra], "a_caldo": True}); assert r["aggiunte"] == 0 and r["importate"] == 1, "stesso nome di una foto che c'è: resta fuori"
    altra2 = os.path.join(c.progetto, "Altra2"); crea_foto(altra2, [("N09", 300, 200, None)])
    c.post("/api/import", {"paths": [altra2], "a_caldo": True})
    assert [x["n"] for x in c.get("/api/state")["scartate"]].count("H01.png") == 1, "il doppione si segnala una volta sola"
    ssh = casa / ".ssh"; crea_foto(str(ssh), [("chiave", 40, 30, None)]); E.CFG["foto_extra"].append(str(ssh / "chiave.jpg"))
    assert E.aggiungi_a_caldo() == 0 and not any(".ssh" in x for x in E.CFG["foto_extra"]), "cartelle riservate fuori, come alla riapertura (VER-004)"


def test_cornice_inclinata_con_il_motore_1x(editor, monkeypatch):
    """cornice inclinata: con il motore del pacchetto, se la miniatura non c'è ancora, il riquadro grigio; con il motore 1.x
    (progetto esportato per la 1.x, senza foto_rgb) legge la miniatura dal file, come prima"""
    E.do_op(dict(op="newspreadsel", names=["H01", "H02"], pos=0)); e = next(x for x in E.spread_view(0)["items"] if x["k"] != "t")
    E.do_op(dict(op="set", at=[0, e["side"], e["idx"]], a=6))
    L = next(x for x in A.layout(E.spread_tuple(0)) if x.get("a"))
    assert FL._a is A and A._photo(L, 0.05, True).size == A._photo(L, 0.05, True, originale=False).size
    os.remove(os.path.join(A.THUMBS, A.M[L["i"]]["n"]))
    im = A._photo(L, 0.05, True); assert im.getpixel((im.width // 2, im.height // 2))[:3] != (255, 255, 255)
    monkeypatch.delattr(A, "foto_rgb")
    with pytest.raises(FileNotFoundError): A._photo(L, 0.05, True)
