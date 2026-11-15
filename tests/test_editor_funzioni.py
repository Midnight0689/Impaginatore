"""Editor: funzioni oltre il flusso principale (importazione e ricollegamento delle foto, versioni salvate, esportazione del
progetto, modelli salvati, selettore di foto, cicli di sottofondo). Riavvii finti: contano le richieste."""
import json
import os
import shutil
import threading
import time
import zipfile

import pytest
from aiuti import attendi, attendi_log, crea_foto
from PIL import Image

from impaginatore.piattaforma import azioni, cartelle, dialoghi


def _op(c, st, o): return c.post("/api/op", dict(cid="t", rev=st["rev"], **o))


def _modello(id_, nome):
    """un modello come lo scrivono l'editor 1.x e 2.0 (una foto a mezza pagina a sinistra)"""
    return {"id": id_, "nome": nome, "n": 1, "lato": None, "pages": [{"mode": "I", "items": [{"k": "p", "c": 0, "r": 0, "w": 6, "h": 8}]}, {"mode": "I", "items": []}]}


def _due_spread(c):
    st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    for k in range(2):
        t = c.post("/api/templates", {"photos": names[2 * k:2 * k + 2]})["items"][0]; st = _op(c, st, {"op": "newspread", "pos": k, "L": t["L"], "R": t["R"]})
    return st, names


def test_importa_foto_e_riavvio(editor, tmp_path):
    c = editor; nuove = tmp_path / "nuove"; crea_foto(str(nuove), [("N01", 400, 300, None), ("N02", 300, 400, None)])
    (nuove / "nota.txt").write_text("x", encoding="utf-8")
    r = c.post("/api/import", {"paths": [str(nuove), str(nuove / "N01.jpg")]})
    assert r == {"importate": 2, "saltate": 2, "riavvio": True}
    attendi(lambda: c.riavvii == [1], 10)
    assert len(c.E.CFG["foto_extra"]) == 2
    assert c.post("/api/import", {"paths": [str(nuove)]}) == {"importate": 0, "saltate": 3, "riavvio": False}
    c.E.inizializza(c.progetto); assert len(c.get("/api/state")["photos"]) == 12


def test_ricollega(editor, tmp_path):
    c = editor; st, names = _due_spread(c)
    spostate = tmp_path / "spostate" / "sotto"; spostate.mkdir(parents=True)
    for n in names[:3]: shutil.move(os.path.join(c.progetto, "Foto", n + ".jpg"), spostate / (n + ".jpg"))
    assert sorted(c.get("/api/state")["mancanti"]) == sorted(n + ".jpg" for n in names[:3])
    assert c.post("/api/ricollega") == {"annullato": True}
    ok, r = c.prova("/api/ricollega", {"cartella": str(tmp_path / "no")}); assert not ok
    r = c.post("/api/ricollega", {"cartella": str(tmp_path / "spostate")})
    assert r == {"trovate": 3, "mancanti": [], "totale": 10} and c.get("/api/state")["mancanti"] == []


def test_foto_modificate_si_aggiornano(editor):
    c = editor; st, names = _due_spread(c)
    f = os.path.join(c.progetto, "Foto", names[0] + ".jpg")
    Image.new("RGB", (1200, 400), (10, 200, 10)).save(f, quality=90)
    futuro = time.time() + 30; os.utime(f, (futuro, futuro))
    assert c.E.foto_cambiate() == [0]
    r = c.post("/api/aggiorna_foto"); assert r["aggiornate"] == [names[0] + ".jpg"] and r["proporzioni"] == [names[0] + ".jpg"] and r["errori"] == []
    assert c.get("/api/state")["agg"]["n"] == 1


def test_cicli_si_fermano(editor, monkeypatch):
    c = editor; st, _ = _due_spread(c)
    fermo = threading.Event()
    c.E.LAST["op"] = 0
    t = threading.Thread(target=c.E.autosave_loop, args=(fermo,), daemon=True); t.start()
    attendi(lambda: not c.get("/api/state")["dirty"], 10)
    fermo.set(); t.join(5); assert not t.is_alive()
    f2 = threading.Event(); f2.set(); c.E.foto_watch_loop(f2)
    e = c.E.avvia_cicli(); c.E.ferma(); assert e.is_set()


def test_versioni_e_ripristino(editor):
    c = editor; st, names = _due_spread(c)
    c.post("/api/save"); time.sleep(1.1)
    st = _op(c, st, {"op": "blank", "pos": 2}); c.post("/api/save")
    v = c.get("/api/versioni"); assert len(v) >= 1 and v[0]["spread"] in (0, 2)
    ok, r = c.prova("/api/ripristina", {"ts": "nonvalido"}); assert not ok
    ts = v[0]["ts"]
    assert c.post("/api/ripristina", {"ts": ts}) == {"riavvio": True}
    attendi(lambda: c.riavvii == [1], 10)


def test_versioni_della_1x_e_copie_rovinate(editor):
    """le copie di spec.py fatte dalla 1.x restano tra le versioni (lette come testo) e si ripristinano convertendole senza
    eseguirle; una copia con codice non si ripristina; una copia di album.json rovinata non compare; le più vecchie si potano"""
    from impaginatore import formato
    c = editor; st, names = _due_spread(c)
    bk = os.path.join(c.progetto, "_backup_editor"); os.makedirs(bk, exist_ok=True)
    spec = '"""Prova: 1 spread."""\nfrom album import *\n\nSPREADS = [\n    # 1\n    (W(P(%r, 0, 0, 6, 8)),\n     W()),\n]\n' % names[0]
    for ts, testo in (("20250101-100000", spec), ("20250101-090000", spec.replace("1 spread.", "senza numero.")), ("20250101-080000", "import os\nSPREADS = []\n")):
        with open(os.path.join(bk, f"{ts}_spec.py"), "w", encoding="utf-8") as fh: fh.write(testo)
    with open(os.path.join(bk, "20250101-110000_album.json"), "w", encoding="utf-8") as fh: fh.write('{"formato": 2, "rotto"')
    v = [(x["ts"], x["spread"]) for x in c.get("/api/versioni") if x["ts"].startswith("2025")]
    assert v == [("20250101-100000", 1), ("20250101-090000", 1), ("20250101-080000", 0)]
    with open(os.path.join(c.progetto, "album.json"), "rb") as fh: prima = fh.read()
    ok, r = c.prova("/api/ripristina", {"ts": "20250101-080000"}); assert not ok and "istruzioni non riconosciute" in r["errore"]
    with open(os.path.join(c.progetto, "album.json"), "rb") as fh: assert c.riavvii == [] and fh.read() == prima, "la copia con codice non tocca il progetto"
    assert c.post("/api/ripristina", {"ts": "20250101-100000"}) == {"riavvio": True}
    attendi(lambda: c.riavvii == [1], 10)
    doc = formato.leggi_album(os.path.join(c.progetto, "album.json"))
    assert len(doc["spread"]) == 1 and doc["spread"][0]["sinistra"]["elementi"][0]["foto"] == names[0]
    c.E._pota_backup(bk, tieni=1)
    assert len({f.split("_", 1)[0] for f in os.listdir(bk)}) == 1, "resta solo la copia più recente"


def test_esporta_progetto_e_reimporta(editor, home_srv, tmp_path, casa):
    c = editor; st, names = _due_spread(c)
    f = [i for i in st["spreads"][0]["items"] if i["k"] != "t"][0]
    st = _op(c, st, {"op": "free", "at": [0, f["side"], f["idx"]], "x": .1, "y": .1, "w": .5, "h": .5})
    st = _op(c, st, {"op": "addtext", "s": 1, "fx": .1, "fy": .1, "fw": .4, "fh": 0, "tx": "Ciao"})
    assert c.post("/api/prj_esporta") == {"annullato": True}
    ok, r = c.prova("/api/prj_esporta", {"dest": str(tmp_path / "no")}); assert not ok
    dest = tmp_path / "uscita"; dest.mkdir()
    out = c.post("/api/prj_esporta", {"dest": str(dest), "zip": True, "foto": True})["cartella"]
    L = attendi_log(c); assert any(x.startswith("RISULTATO:") for x in L), L
    nomi = set(os.listdir(out)); assert {"album.json", "progetto.json", "Foto", "_cache", "LEGGIMI.txt", "font_usati.txt"} <= nomi
    assert not nomi & {"spec.py", "album_libere.py", "testo.py", "vib_lut.npz", "modelli_utente.json"}, "la 2.0 esporta solo dati (spec.py solo su richiesta)"
    with open(os.path.join(out, "LEGGIMI.txt"), encoding="utf-8") as fh: assert "«Prova»" in fh.read()
    zp = out + ".zip"; assert zipfile.is_zipfile(zp)
    # nella schermata dei progetti: Importa ZIP; poi l'editor lo apre e ritrova da solo le foto nella cartella Foto
    class Z(dialoghi.Dialoghi):
        def _scegli(self, tipo, m): return [zp]
    dialoghi.imposta(Z())
    p = home_srv.post("/api/importa-zip")["path"]; dialoghi.imposta(None)
    c.E.inizializza(p)
    s2 = c.get("/api/state"); assert len(s2["spreads"]) == 2 and s2["mancanti"] == [] and len(s2["photos"]) == 10
    with open(os.path.join(p, "progetto.json"), encoding="utf-8") as fh: assert json.load(fh)["foto"] == os.path.join(p, "Foto")


def test_esporta_per_la_versione_1x(editor, tmp_path):
    """«Aggiungi spec.py per la versione 1.x»: il pacchetto ha anche spec.py e le copie del motore che gli servono; il
    progetto resta in album.json e spec.py si rilegge senza eseguirlo"""
    from impaginatore import formato_1x
    c = editor; st, names = _due_spread(c)
    f = [i for i in st["spreads"][0]["items"] if i["k"] != "t"][0]
    st = _op(c, st, {"op": "free", "at": [0, f["side"], f["idx"]], "x": .1, "y": .1, "w": .5, "h": .5})
    dest = tmp_path / "uscita"; dest.mkdir()
    out = c.post("/api/prj_esporta", {"dest": str(dest), "foto": False, "v1x": True})["cartella"]
    L = attendi_log(c); assert any("spec.py per la versione 1.x" in x for x in L) and any(x.startswith("RISULTATO:") for x in L), L
    assert {"album.json", "spec.py", "album_libere.py", "testo.py", "vib_lut.npz"} <= set(os.listdir(out))
    with open(os.path.join(out, "spec.py"), "rb") as fh: sp = formato_1x.leggi(fh.read(), prova=True)
    assert len(sp) == 2 and not os.path.exists(os.path.join(c.progetto, "spec.py")), "nel progetto resta solo album.json"


def test_modelli_utente(editor, casa):
    """i modelli salvati vanno nella cartella dei dati dell'utente (prima: ~/.album-tools) e si possono usare per un nuovo spread"""
    c = editor; st, names = _due_spread(c)
    assert os.path.dirname(c.E.UT_FILE) == cartelle.dati_utente()
    c.post("/api/modelli", {"azione": "salva", "s": 0, "nome": "Mio"})
    with open(c.E.UT_FILE, encoding="utf-8") as fh: m = json.load(fh)
    assert m[0]["nome"] == "Mio"
    ok, r = c.prova("/api/modelli", {"azione": "salva", "s": 0, "nome": "mio"}); assert not ok and "esiste già" in r["errore"]
    c.post("/api/modelli", {"azione": "rinomina", "id": m[0]["id"], "nome": "Nuovo"}); c.post("/api/modelli", {"azione": "aggiorna", "id": m[0]["id"], "s": 1})
    assert c.E.ut_load()[0]["nome"] == "Nuovo"
    assert c.E.BUILD["U:%s:L" % m[0]["id"]]([1, 2, 3, 4, 5, 6], False) is not None
    c.post("/api/modelli", {"azione": "elimina", "id": m[0]["id"]}); assert c.E.ut_load() == []
    with pytest.raises(ValueError): c.E.BUILD["U:%s:L" % m[0]["id"]]
    ok, r = c.prova("/api/modelli", {"azione": "boh", "id": "x"}); assert not ok


def test_modelli_migrati_da_album_tools(progetto, apri_editor, casa):
    vecchi = casa / ".album-tools"; vecchi.mkdir()
    (vecchi / "modelli_utente.json").write_text(json.dumps([_modello("u1", "Vecchio")]), encoding="utf-8")
    shutil.copy(vecchi / "modelli_utente.json", os.path.join(progetto, "modelli_utente.json"))
    c = apri_editor(progetto)
    assert c.E.ut_load()[0]["nome"] == "Vecchio" and c.E.UT_FILE.startswith(os.environ["IMPAGINATORE_DATI"])


def test_modelli_arrivati_con_un_progetto(progetto, apri_editor, casa):
    """SEC-009: i modelli arrivati con un progetto valgono solo per quel progetto; entrano tra i tuoi solo se lo chiedi"""
    (casa / "dati").mkdir(); (casa / "dati" / "modelli_utente.json").write_text(json.dumps([_modello("a", "Mio")]), encoding="utf-8")
    with open(os.path.join(progetto, "modelli_utente.json"), "w", encoding="utf-8") as fh:
        json.dump([_modello("a", "Mio"), _modello("b", "mio"), _modello("c", "Altro")], fh)
    c = apri_editor(progetto)
    assert [t["nome"] for t in c.E.ut_load()] == ["Mio"], "i tuoi modelli non cambiano aprendo un progetto"
    assert [t["nome"] for t in c.E.ut_progetto()] == ["mio", "Altro"]
    st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    d = c.post("/api/templates", {"photos": names[:1]})
    assert {(t["id"], t["progetto"]) for t in d["utente"]} == {("a", False), ("b", True), ("c", True)}
    ok, r = c.prova("/api/modelli", {"azione": "rinomina", "id": "b", "nome": "X"}); assert not ok, "un modello del progetto non è tuo: non si modifica"
    c.post("/api/modelli", {"azione": "importa", "id": "b"}); c.post("/api/modelli", {"azione": "importa", "id": "c"})
    assert [t["nome"] for t in c.E.ut_load()] == ["Mio", "mio (importato)", "Altro"] and c.E.ut_progetto() == []
    ok, r = c.prova("/api/modelli", {"azione": "importa", "id": "zz"}); assert not ok and "non trovato" in r["errore"]


def test_selettore_di_foto(editor, casa, tmp_path, monkeypatch):
    c = editor; (casa / "Desktop").mkdir()
    r = c.get("/api/ls?p=" + str(tmp_path).replace(" ", "%20"))
    assert r["path"] == str(tmp_path) and "casa" in r["dirs"] and r["parent"] == os.path.dirname(str(tmp_path))
    assert any(x["n"] == "Scrivania" for x in r["places"])
    radice = c.get("/api/ls?p=/"); assert radice["parent"] is None
    assert c.get("/api/ls?p=/non/esiste")["path"] == str(casa)
    foto = os.path.join(c.progetto, "Foto", "H01.jpg")
    assert c.raw("/api/fthumb?p=" + foto.replace(" ", "%20"))[:2] == b"\xff\xd8"
    ok, r = c.prova("/api/fthumb?p=/etc/passwd"); assert not ok
    assert c.post("/api/pick", {"kind": "folder"}) == {"paths": []}
    fatti = []; monkeypatch.setattr(azioni, "mostra", lambda p: fatti.append(p))
    c.post("/api/reveal", {"foto": "H01"}); c.post("/api/reveal", {"path": "/x"})
    assert fatti == [foto, "/x"]


def test_errori_di_salvataggio(editor, monkeypatch):
    c = editor; st, _ = _due_spread(c)
    from impaginatore import formato
    monkeypatch.setattr(formato, "scrivi_atomico", lambda p, t: (_ for _ in ()).throw(PermissionError(13, "negato", p)))
    ok, r = c.prova("/api/save", {}); assert not ok and "negato" in r["errore"]


@pytest.mark.xfail(strict=True, reason="bug noto della 1.5.2 (non corretto in fase 1): con l'orientamento EXIF le proporzioni "
                                       "usano la misura grezza del file mentre la miniatura è già ruotata")
def test_foto_ruotata_da_exif(home, tmp_path, apri_editor):
    p = home.nuovo({"nome": "Ruotata", "w": 30, "h": 30})
    crea_foto(os.path.join(p, "Foto"), [("R01", 900, 600, "2026:01:01 10:00:00")], orientamento={"R01": 6})
    c = apri_editor(p)
    assert c.get("/api/state")["photos"][0]["ar"] == round(600 / 900, 3)
