"""Editor: i servizi attorno alle operazioni. Riparazione dei percorsi all'apertura, modelli (anche di una pagina sola),
Tono (cornici bianche, scene chiare o scure, ritocchi), foto «live» e miniature con i valori di prova, anteprima con una
cornice nascosta, foto modificate fuori dall'editor, dati EXIF, esportazioni JPG/PDF/PSD con i loro errori, copie di
sicurezza e versioni, ricollegamento ed esportazione del progetto, avvio come programma.

Il progetto di partenza (10 foto, miniature e volti già fatti) si prepara una volta per il modulo; ogni prova ne apre
una copia. Photoshop e il processo che fa i PSD sono finti: il finto registra il comando e scrive i file che direbbe."""
import errno
import io
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from collections import namedtuple

import numpy as np
import pytest
from aiuti import Client, attendi, attendi_log
from PIL import Image, ImageCms, ImageDraw

from impaginatore import formato
from impaginatore.editor import server as E
from impaginatore.motore import album as A
from impaginatore.piattaforma import dialoghi, processi
from impaginatore.piattaforma import font as pfont
from impaginatore.piattaforma import photoshop as pps

VUOTA = dict(mode="W", module="BLANK", mirror=False, photos=[])
Disco = namedtuple("Disco", "total used free")
POSIX = pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="cartelle senza permessi (chmod) e collegamenti simbolici come su macOS e Linux, con un utente normale")


def _casa(mp, h):
    """come la fixture casa di conftest, per la preparazione del modulo (che gira prima delle fixture di ogni prova)"""
    h.mkdir()
    for k, v in dict(HOME=h, USERPROFILE=h, APPDATA=h / "AppData" / "Roaming", LOCALAPPDATA=h / "AppData" / "Local", XDG_DATA_HOME=h / ".local" / "share",
                     XDG_CACHE_HOME=h / ".cache", XDG_CONFIG_HOME=h / ".config", IMPAGINATORE_DATI=h / "dati", IMPAGINATORE_CACHE=h / "cache").items():
        mp.setenv(k, str(v))


@pytest.fixture(scope="module")
def base(tmp_path_factory, foto_campione):
    """progetto «Prova» (60 x 22,5 cm, come quello di conftest) con le 10 foto, miniature, misure e volti già pronti"""
    d = tmp_path_factory.mktemp("servizi"); p = d / "Prova"; os.makedirs(p / "Foto")
    for f in sorted(os.listdir(foto_campione)): shutil.copy2(os.path.join(foto_campione, f), p / "Foto" / f)
    cfg = dict(nome="Prova", foto=str(p / "Foto"), foto_extra=[], tolte=[], formato_cm=[60, 22.5], dimensioni_esatte=False, ppi=300, abbondanza_mm=0, spazio_mm=2.5,
               margine_mm=10, uscita_psd=str(p / "PSD"), testo=dict(nome="Prova", sottotitolo="", data=""), esposizione=dict(globale=0.0, per_cartella={}, per_foto={}),
               bilanciamento_bianco={}, centri_volto={})
    formato.scrivi_json(str(p / "progetto.json"), cfg, indent=2, ensure_ascii=False); formato.scrivi_atomico(str(p / formato.ALBUM), formato.album_vuoto())
    with pytest.MonkeyPatch.context() as mp:
        _casa(mp, d / "casa"); A.carica_progetto(str(p))
    return str(p)


def _copia(base, dove):
    """copia del progetto di partenza con i percorsi (progetto.json, cache delle misure) che puntano alla copia"""
    shutil.copytree(base, dove)
    pj = os.path.join(dove, "progetto.json"); c = formato.leggi_json(pj); c.update(foto=os.path.join(dove, "Foto"), uscita_psd=os.path.join(dove, "PSD"))
    formato.scrivi_json(pj, c, indent=2, ensure_ascii=False)
    mp = os.path.join(dove, "_cache", "meta.json"); m = formato.leggi_json(mp)
    for x in m: x["src"] = os.path.join(dove, "Foto", x["n"])
    formato.scrivi_json(mp, m)
    return dove


@pytest.fixture
def apri(base, tmp_path, monkeypatch):
    """apre l'editor su una copia del progetto di partenza; foto = {nome: immagine} sostituisce delle foto (stesse misure),
    prepara(cartella) cambia la copia prima dell'apertura. Riavvio finto: conta le richieste"""
    aperti = []

    def apri(foto=None, prepara=None):
        p = _copia(base, str(tmp_path / "Prova"))
        for n, im in (foto or {}).items():
            im.save(os.path.join(p, "Foto", n + ".jpg"), quality=95); os.remove(os.path.join(p, "_cache", "thumbs", n + ".jpg"))
        if prepara: prepara(p)
        riavvii = []; monkeypatch.setattr(E, "riavvia_processo", lambda: riavvii.append(1))
        E.RADICI.scelte.clear(); E.inizializza(p, home="http://127.0.0.1:9")
        srv = E.crea_server(0); threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True).start()          # si ferma in fretta alla fine
        c = Client(srv.server_address[1], srv.sessione.gettone); c.progetto = p; c.srv = srv; c.riavvii = riavvii
        aperti.append(c); return c
    yield apri
    for c in aperti: c.srv.shutdown(); c.srv.server_close()
    E.ferma()


class Finti(dialoghi.Dialoghi):
    """finestre di sistema finte: rispondono con i percorsi dati, uno per volta"""
    def __init__(self, *risposte): self.risposte = list(risposte)

    def _scegli(self, tipo, messaggio): return [self.risposte.pop(0)] if self.risposte else []


class Passi:
    """al posto dell'evento che ferma i cicli di sottofondo: `giri` giri senza aspettare, poi si ferma"""
    def __init__(self, giri): self.giri = giri

    def wait(self, secondi): self.giri -= 1; return self.giri < 0


def _op(c, o): return c.post("/api/op", dict(cid="s", rev=c.get("/api/state")["rev"], **o))


def _ix(c): return {p["n"]: k for k, p in enumerate(c.get("/api/state")["photos"])}


def _pag(c, modulo, *nomi, modo="I"):
    ix = _ix(c); return dict(mode=modo, module=modulo, mirror=False, photos=[ix[n] for n in nomi])


def _spread(c, L, R, pos=None):
    return _op(c, dict(op="newspread", pos=len(c.get("/api/state")["spreads"]) if pos is None else pos, L=L, R=R))


def _img(b): return Image.open(io.BytesIO(b)).convert("RGB")


def _luce(b): return float(np.asarray(_img(b).convert("L")).mean())


def _q(o): return urllib.parse.quote(json.dumps(o))


def _rosso(px): return px[0] > 200 and px[1] < 70 and px[2] < 70


def _verde(px): return px[1] > 200 and px[0] < 90 and px[2] < 90


def _foto(w, h, colore=(120, 120, 120)): return Image.new("RGB", (w, h), colore)


# ---------------------------------------------------------------- apertura: percorsi riparati
def _sposta_foto(p, cartella, vecchia):
    """le foto passano da Foto a <cartella> e progetto.json e cache le cercano ancora in <vecchia> (un altro disco)"""
    if cartella != "Foto": shutil.move(os.path.join(p, "Foto"), os.path.join(p, cartella))
    pj = os.path.join(p, "progetto.json"); c = formato.leggi_json(pj)
    c.update(foto=vecchia, esposizione=dict(globale=0.0, per_cartella={vecchia + "/": 0.3, "/altro/disco": -0.2}, per_foto={}))
    formato.scrivi_json(pj, c, indent=2, ensure_ascii=False)
    mp = os.path.join(p, "_cache", "meta.json"); m = formato.leggi_json(mp)
    for x in m: x["src"] = os.path.join(vecchia, x["n"])
    formato.scrivi_json(mp, m)


def test_progetto_spostato_ritrova_la_cartella_delle_foto(apri):
    """progetto copiato da un altro computer: la cartella delle foto (che sul vecchio disco si chiamava Matrimonio) si
    ritrova dentro il progetto con lo stesso nome; con lei l'esposizione per cartella e i percorsi delle foto nella cache
    (anche di una foto finita nella cartella Foto del progetto, che si aggiunge alle foto del progetto)"""
    def prepara(p):
        _sposta_foto(p, "Matrimonio", "/Volumes/Vecchio/Matrimonio"); os.mkdir(os.path.join(p, "Foto"))
        shutil.move(os.path.join(p, "Matrimonio", "V10.jpg"), os.path.join(p, "Foto", "V10.jpg"))
    c = apri(prepara=prepara); d, fd = os.path.join(c.progetto, "Matrimonio"), os.path.join(c.progetto, "Foto")
    cfg = formato.leggi_json(os.path.join(c.progetto, "progetto.json"))
    assert cfg["foto"] == d and cfg["esposizione"]["per_cartella"] == {d: 0.3, "/altro/disco": -0.2} and cfg["foto_extra"] == [os.path.join(fd, "V10.jpg")]
    meta = {m["n"]: os.path.dirname(m["src"]) for m in formato.leggi_json(os.path.join(c.progetto, "_cache", "meta.json"))}
    assert meta.pop("V10.jpg") == fd and set(meta.values()) == {d}
    st = c.get("/api/state"); assert st["mancanti"] == [] and len(st["photos"]) == 10


def test_progetto_spostato_foto_nella_cartella_foto(apri):
    """se dentro il progetto non c'è una cartella con il vecchio nome, le foto si cercano in Foto; le foto che non ci sono
    restano mancanti (si ricollegano a mano), quelle aggiunte da un'altra cartella si ritrovano anche lì"""
    def prepara(p):
        _sposta_foto(p, "Foto", "/Volumes/Vecchio/Selezione"); os.remove(os.path.join(p, "Foto", "Q09.jpg"))
        pj = os.path.join(p, "progetto.json"); c = formato.leggi_json(pj); c["foto_extra"] = ["/Volumes/Vecchio/Altre/V10.jpg", "/Volumes/Vecchio/Altre/Z99.jpg"]
        formato.scrivi_json(pj, c, indent=2, ensure_ascii=False)
    c = apri(prepara=prepara); fd = os.path.join(c.progetto, "Foto")
    cfg = formato.leggi_json(os.path.join(c.progetto, "progetto.json"))
    assert cfg["foto"] == fd and cfg["esposizione"]["per_cartella"] == {fd: 0.3, "/altro/disco": -0.2}
    assert cfg["foto_extra"] == [os.path.join(fd, "V10.jpg"), "/Volumes/Vecchio/Altre/Z99.jpg"]
    meta = {m["n"]: m["src"] for m in formato.leggi_json(os.path.join(c.progetto, "_cache", "meta.json"))}
    assert meta["Q09.jpg"] == os.path.join("/Volumes/Vecchio/Selezione", "Q09.jpg") and meta["H01.jpg"] == os.path.join(fd, "H01.jpg")
    assert c.get("/api/state")["mancanti"] == ["Q09.jpg"]


def test_progetto_spostato_senza_foto(apri):
    """nessuna cartella da ritrovare (né quella con il vecchio nome né Foto): progetto.json resta com'è e le foto sono tutte da ricollegare"""
    c = apri(prepara=lambda p: _sposta_foto(p, "Altrove", "/Volumes/Vecchio/Selezione"))
    assert formato.leggi_json(os.path.join(c.progetto, "progetto.json"))["foto"] == "/Volumes/Vecchio/Selezione"
    assert len(c.get("/api/state")["mancanti"]) == 10


@POSIX
def test_riparazioni_con_cache_rovinata_e_cartella_illeggibile(apri, tmp_path, caplog):
    """le riparazioni all'apertura non fermano l'editor: una cache delle misure rovinata (si rifà) e una cartella Foto che
    non si legge (il progetto prende le foto da un'altra cartella) si annotano e basta"""
    altre = tmp_path / "Selezione"

    def prepara(p):
        shutil.copytree(os.path.join(p, "Foto"), altre); pj = os.path.join(p, "progetto.json"); c = formato.leggi_json(pj); c["foto"] = str(altre)
        formato.scrivi_json(pj, c, indent=2, ensure_ascii=False)
        with open(os.path.join(p, "_cache", "meta.json"), "w", encoding="utf-8") as f: f.write('[{"n": "H01.jpg", rotto')
        os.chmod(os.path.join(p, "Foto"), 0o000)
    try:
        caplog.set_level(logging.DEBUG, logger="impaginatore.editor")
        c = apri(prepara=prepara); out = [r.getMessage() for r in caplog.records if r.name == "impaginatore.editor"]
        assert "percorsi del progetto non riparati (JSONDecodeError)" in out and "foto di Foto non raccolte (PermissionError)" in out, out
        assert any(re.match(r"raccogli foto: .*Permission denied", r) for r in out), "il dettaglio (con il percorso) solo a DEBUG"
        st = c.get("/api/state"); assert len(st["photos"]) == 10 and st["mancanti"] == []
        assert formato.leggi_json(os.path.join(c.progetto, "progetto.json")).get("foto_extra") == []
    finally: os.chmod(os.path.join(str(tmp_path / "Prova"), "Foto"), 0o755)


# ---------------------------------------------------------------- modelli
def test_modelli_per_una_pagina_sola(apri):
    """l'altra pagina è di solo testo: i modelli cambiano solo questa (le cornici stanno tutte a destra) e un modello salvato
    da qui vale solo per una pagina; quelli dello spread intero non si propongono, e viceversa"""
    c = apri()
    _spread(c, VUOTA, _pag(c, "DUO", "H01", "H02")); _op(c, dict(op="addtext", s=0, fx=.1, fy=.1, fw=.3, fh=0, tx="Titolo"))
    st = _spread(c, _pag(c, "FULL", "V03"), _pag(c, "FULL", "V04"))
    t = c.get("/api/templates?s=0")
    assert t["lato"] == "R" and t["n"] == 2 and t["items"], t
    assert all("R" in x and "L" not in x for x in t["items"]) and all(f["x"] >= st["fold"] - 1 for x in t["items"] for f in x["frames"])
    assert all(sorted(f["n"] for f in x["frames"]) == ["H01", "H02"] for x in t["items"]) and any(x["cur"] for x in t["items"]), "c'è quello di adesso"
    c.post("/api/modelli", {"azione": "salva", "s": 0, "nome": "Destra"}); c.post("/api/modelli", {"azione": "salva", "s": 1, "nome": "Tutto"})
    m = {x["nome"]: x for x in E.ut_load()}
    assert m["Destra"]["lato"] == "R" and m["Destra"]["pages"][0]["items"] == [] and len(m["Destra"]["pages"][1]["items"]) == 2 and m["Tutto"]["lato"] is None
    u = c.get("/api/templates?s=0")["utente"]
    assert [x["nome"] for x in u] == ["Destra"] and "R" in u[0] and all(f["x"] >= st["fold"] - 1 for f in u[0]["frames"])
    assert [x["nome"] for x in c.get("/api/templates?s=1")["utente"]] == ["Tutto"]


def test_modelli_con_tante_foto(apri):
    """dieci foto: l'abbinamento foto-cornici veloce (la cornice più grande sceglie per prima); ogni foto in una cornice sola"""
    c = apri(); nomi = list(_ix(c))
    d = c.post("/api/templates", {"photos": nomi})
    assert d["n"] == 10 and d["items"]
    for x in d["items"]:
        assert sorted(x["L"]["photos"] + x["R"]["photos"]) == list(range(10)) and sorted(f["n"] for f in x["frames"]) == sorted(nomi)


def test_modello_inservibile_si_salta(apri):
    """un modello arrivato con un progetto, valido ma con una cornice alta un decimillesimo di pagina, non si può usare:
    si tralascia (e si annota) senza togliere gli altri modelli"""
    sottile = {"id": "s1", "nome": "Sottile", "n": 1, "lato": None, "pages": [{"mode": "I", "items": [{"k": "f", "x": .1, "y": .1, "w": .5, "h": .00001}]}, {"mode": "I", "items": []}]}
    buono = {"id": "b1", "nome": "Buono", "n": 1, "lato": None, "pages": [{"mode": "I", "items": [{"k": "p", "c": 0, "r": 0, "w": 6, "h": 8}]}, {"mode": "I", "items": []}]}
    c = apri(prepara=lambda p: formato.scrivi_json(os.path.join(p, "modelli_utente.json"), [sottile, buono]))
    d = c.post("/api/templates", {"photos": ["H01"]})
    assert [x["nome"] for x in d["utente"]] == ["Buono"]
    assert [x for x in c.get("/api/log") if "Sottile" in x] == ["modello «Sottile» non applicabile: division by zero"]


def test_modelli_errori(apri):
    """i casi in cui un modello non si salva, non si rinomina o non si propone: lo dice il messaggio"""
    c = apri()
    _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    _op(c, dict(op="blank", pos=1)); _op(c, dict(op="addtext", s=1, fx=.1, fy=.1, fw=.3, fh=0, tx="A")); _op(c, dict(op="addtext", s=1, fx=.6, fy=.1, fw=.3, fh=0, tx="B"))
    _op(c, dict(op="blank", pos=2))
    errore = lambda b: c.prova("/api/modelli", b)[1]["errore"]
    assert errore({"azione": "salva", "s": 1, "nome": "Testi"}) == "le due pagine sono di solo testo: non c'è nessun layout di foto da salvare"
    assert errore({"azione": "salva", "s": 2, "nome": "Vuoto"}) == "lo spread non ha foto: non c'è nessun layout da salvare"
    assert errore({"azione": "salva", "s": 0, "nome": "  "}) == "scrivi un nome per il modello"
    c.post("/api/modelli", {"azione": "salva", "s": 0, "nome": "Uno"}); c.post("/api/modelli", {"azione": "salva", "s": 0, "nome": "Due"})
    ids = {x["nome"]: x["id"] for x in E.ut_load()}
    assert errore({"azione": "rinomina", "id": ids["Uno"], "nome": ""}) == "scrivi un nome"
    assert errore({"azione": "rinomina", "id": ids["Uno"], "nome": "due"}) == "esiste già un modello con questo nome"
    assert errore({"azione": "copia", "id": ids["Uno"]}) == "azione sconosciuta"
    assert [x["nome"] for x in E.ut_load()] == ["Uno", "Due"]
    assert c.get("/api/templates?s=1") == {"items": [], "utente": [], "nota": "Le due pagine sono di solo testo: non ci sono foto da impaginare."}
    ok, r = c.prova("/api/templates", {"photos": ["V03", "H01"]}); assert not ok and r["errore"] == "H01 è già in uno spread"


# ---------------------------------------------------------------- Tono
def _cornice(interno, colore, bordo=120):
    """foto 900 x 600 di un grigio con tutt'attorno una cornice bianca o nera (come una scansione con il passe-partout)"""
    im = _foto(900, 600, colore); ImageDraw.Draw(im).rectangle([bordo, bordo, 899 - bordo, 599 - bordo], fill=interno)
    return im


def _righe(w, h, livelli, alto=40):
    """righe orizzontali dei livelli di grigio dati, ripetute (la distribuzione non cambia con il ritaglio della cornice)"""
    a = np.zeros((h, w, 3), np.uint8)
    for y in range(h): a[y] = livelli[(y // alto) % len(livelli)]
    return Image.fromarray(a)


def test_tono_senza_la_cornice_bianca_della_foto(apri):
    """la cornice bianca o nera della foto stessa non conta nel tono: la foto con il passe-partout misura come quella senza.
    Una foto quasi tutta bianca (soggetto piccolo nel mezzo) non si riduce al soggetto: si toglie al massimo il 30 % per lato"""
    grigio = (110, 110, 110); bianca = _foto(1000, 560, (255, 255, 255)); ImageDraw.Draw(bianca).rectangle([400, 224, 600, 336], fill=grigio)
    c = apri(foto={"H01": _cornice(grigio, (255, 255, 255)), "H08": _cornice(grigio, (0, 0, 0)), "H02": _foto(900, 600, grigio), "H06": bianca})
    _spread(c, _pag(c, "FULL", "H01", modo="W"), _pag(c, "FULL", "H02", modo="W")); _spread(c, _pag(c, "FULL", "H08", modo="W"), _pag(c, "FULL", "H06", modo="W"))
    t = {x["name"]: x for s in (0, 1) for x in c.get(f"/api/tono?s={s}")["items"]}
    for n in ("H01", "H08"):
        assert abs(t[n]["d"] - t["H02"]["d"]) < 2.5, (n, t[n], t["H02"])           # con la cornice nel tono: +20 (bianca) o -15 (nera)
    assert t["H01"]["B"] == 0.0, "niente bianchi bruciati: il bianco della cornice non è nella foto"
    assert t["H06"]["d"] > t["H02"]["d"] + 15 and t["H06"]["B"] > 50, t["H06"]


def test_tono_scene_chiare_e_scure(apri):
    """una scena chiara di proposito (alte luci piene, niente ombre, niente bruciato) e una scura (luci accese, ombre nere):
    il tono le riconosce e allarga la zona giusta della metà"""
    chiara = _righe(900, 600, [(v, v, v) for v in (100, 130, 160, 190, 215, 232)])
    scura = _righe(900, 600, [(26, 26, 26)] * 6 + [(222, 222, 222)])
    c = apri(foto={"H01": chiara, "H02": scura, "H08": _foto(900, 600, (118, 118, 118))})
    _spread(c, _pag(c, "DUO", "H01", "H02"), _pag(c, "FULL", "H08"))
    t = {x["name"]: x for x in c.get("/api/tono?s=0")["items"]}
    assert (t["H01"]["scena"], t["H02"]["scena"], t["H08"]["scena"]) == ("hk", "lk", None), t
    assert (t["H01"]["ze"], t["H02"]["ze"], t["H08"]["ze"]) == (18.0, 18.0, 12.0)


def test_tono_con_ritocchi_e_valori_di_prova(apri):
    """la misura con i valori di prova (cursori in movimento) usa quelli e lascia i ritocchi salvati come sono"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    _op(c, dict(op="rit", photo="H01", key="bia", value=40))
    prima = {x["name"]: x for x in c.get("/api/tono?s=0")["items"]}
    prova = {x["name"]: x for x in c.get("/api/tono?s=0&o=" + _q({"H01": {"ev": 1.0, "rit": {"bia": -40}}}))["items"]}
    assert prova["H01"]["d"] > prima["H01"]["d"] + 3 and prova["H02"]["d"] == prima["H02"]["d"]
    assert prima["H01"]["rit0"] == {"bia": 40} and prova["H01"]["rit0"] == {"bia": -40}
    st = c.get("/api/state"); assert next(p for p in st["photos"] if p["n"] == "H01")["rit"] == {"bia": 40}
    assert {x["name"]: x["d"] for x in c.get("/api/tono?s=0")["items"]} == {n: x["d"] for n, x in prima.items()}


def test_tono_spread_senza_foto_e_vicini_esclusi(apri):
    """uno spread con solo testo non ha niente da misurare (punteggio pieno); i testi non contano tra le foto; il confronto
    con lo spread vicino manca se lì le foto sono tutte escluse dalla misura; la mappa dei bruciati di una cornice che non c'è
    è un errore"""
    c = apri()
    _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); _spread(c, _pag(c, "FULL", "V03"), _pag(c, "FULL", "V04"))
    _op(c, dict(op="addtext", s=1, fx=.1, fy=.1, fw=.3, fh=0, tx="Titolo")); _op(c, dict(op="blank", pos=2)); _op(c, dict(op="addtext", s=2, fx=.1, fy=.1, fw=.3, fh=0, tx="Fine"))
    assert c.get("/api/tono?s=2") == {"s": 2, "items": [], "score": 100, "prev": None, "next": None, "rif": 52.0}
    t1 = c.get("/api/tono?s=1"); assert [x["name"] for x in t1["items"]] == ["V03", "V04"] and t1["prev"] is not None and t1["next"] is None
    _op(c, dict(op="tono_escl", photos=["H01", "H02"], value=True))
    assert c.get("/api/tono?s=1")["prev"] is None
    assert c.get("/api/tono?s=0")["score"] == 100 and {x["stato"] for x in c.get("/api/tono?s=0")["items"]} == {"escl"}
    ok, r = c.prova("/img/bruc?s=1&side=L&idx=5"); assert not ok and r["errore"] == "foto non trovata"


# ---------------------------------------------------------------- foto «live», miniature corrette, anteprima
def test_foto_live_con_i_valori_di_prova(apri):
    """la foto della cornice con i valori dei cursori: esposizione, ritocchi, angolo e bordo di prova; quelli salvati restano"""
    c = apri(); st = _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    _op(c, dict(op="ev", photo="H01", value=1.0)); _op(c, dict(op="rit", photo="H01", key="con", value=30)); _op(c, dict(op="set", at=[0, "L", 0], bd=[3, "#00ff00"]))
    e = next(x for x in st["spreads"][0]["items"] if x["side"] == "L")
    live = lambda o, k="0.05": c.raw(f"/img/live?s=0&side=L&idx=0&k={k}&o=" + _q(o))
    salvata = live({}); im = _img(salvata)
    assert im.size == (round(e["w"] * .05), round(e["h"] * .05)) and _img(live({}, "0.001")).size == im.size, "scala almeno 0,05"
    bordo = (0, im.height // 4); assert _verde(im.getpixel(bordo)), "bordo verde salvato"
    senza_ev = live({"ev": 0.001}); assert _luce(senza_ev) < _luce(salvata) - 10
    assert _luce(live({"ev": 2})) > _luce(salvata) + 5
    assert not _verde(_img(live({"bd": None})).getpixel(bordo)), "bordo tolto per prova"
    assert _rosso(_img(live({"bd": [3, "#ff0000"]})).getpixel(bordo))
    assert live({"rit": {}}) != salvata and live({"rit": {"con": 30, "xyz": 5, "tmp": 0.2}}) == salvata, "solo i ritocchi noti e non trascurabili"
    girata = np.asarray(_img(live({"a": 12}))).astype(int); assert np.abs(girata - np.asarray(im).astype(int)).mean() > 8
    st = c.get("/api/state"); h = next(p for p in st["photos"] if p["n"] == "H01")
    assert h["rit"] == {"con": 30} and E.CFG["esposizione"]["per_foto"] == {"H01": 1.0}, "i valori di prova non restano"
    _op(c, dict(op="ev", photo="H01", value=0)); _op(c, dict(op="rit", photo="H01", reset=True))
    assert live({"ev": 1.0, "rit": {"con": 30}}) == salvata and E.CFG["ritocco"] == {} and E.CFG["esposizione"]["per_foto"] == {}


def test_foto_live_di_una_cornice_che_non_ce(apri):
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), VUOTA); _op(c, dict(op="addtext", s=0, fx=.6, fy=.1, fw=.3, fh=0, tx="Testo"))
    for side, idx in (("L", 3), ("R", 0)):
        ok, r = c.prova(f"/img/live?s=0&side={side}&idx={idx}"); assert not ok and r["errore"] == "cornice non trovata", (side, idx)


def test_miniatura_corretta_con_i_valori_di_prova(apri):
    """la foto intera del riquadro Design con esposizione e ritocchi di prova; quelli salvati restano"""
    c = apri(); _op(c, dict(op="ev", photo="H01", value=-1.0)); _op(c, dict(op="rit", photo="H01", key="sat", value=-100))
    corr = lambda o: c.raw("/img/corr?n=H01&w=120&o=" + _q(o))
    salvata = corr({}); assert _img(salvata).size == (120, 80)
    assert _luce(corr({"ev": 0.001})) > _luce(salvata) + 10 and _luce(corr({"ev": 1})) > _luce(corr({"ev": 0.001}))
    a = np.asarray(_img(salvata)).astype(int); assert np.abs(a[..., 0] - a[..., 2]).max() < 25, "saturazione -100: grigi"
    b = np.asarray(_img(corr({"rit": {}}))).astype(int); assert np.abs(b[..., 0] - b[..., 2]).max() > 60, "senza ritocchi: i colori"
    assert corr({"rit": {"sat": -100, "boh": 3}}) == salvata
    assert E.CFG["ritocco"] == {"H01": {"sat": -100}} and E.CFG["esposizione"]["per_foto"] == {"H01": -1.0}
    _op(c, dict(op="ev", photo="H01", value=0)); _op(c, dict(op="rit", photo="H01", reset=True))
    assert corr({"ev": -1.0, "rit": {"sat": -100}}) == salvata and E.CFG["ritocco"] == {} and E.CFG["esposizione"]["per_foto"] == {}


def test_anteprima_senza_la_cornice_trascinata(apri):
    """mentre si trascina una cornice libera l'anteprima la nasconde (lì si vede il fondo); le cornici del modello e quelle che
    non esistono non si nascondono"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    st = _op(c, dict(op="free", at=[0, "L", 0], x=.1, y=.1, w=.5, h=.5))
    e = next(x for x in st["spreads"][0]["items"] if x["side"] == "L"); assert e["free"]
    K = 0.05; centro = (round((e["x"] + e["w"] / 2) * K), round((e["y"] + e["h"] / 2) * K))
    tutto = c.raw(f"/img/spread/0?k={K}")
    assert sum(_img(tutto).getpixel(centro)) < 700 and sum(_img(c.raw(f"/img/spread/0?k={K}&hide=L:0")).getpixel(centro)) > 750
    assert c.raw(f"/img/spread/0?k={K}&hide=R:0") == tutto and c.raw(f"/img/spread/0?k={K}&hide=L:7") == tutto


# ---------------------------------------------------------------- foto modificate fuori dall'editor
def _tocca(p, secondi):
    t = time.time() + secondi; os.utime(p, (t, t))


def test_foto_modificate_che_non_si_aprono(apri):
    """una foto riscritta male non si aggiorna (lo dice), una sparita non conta come modificata: niente aggiornamento"""
    c = apri(); fd = os.path.join(c.progetto, "Foto")
    with open(os.path.join(fd, "H02.jpg"), "wb") as f: f.write(b"non sono una foto")
    _tocca(os.path.join(fd, "H02.jpg"), 30); os.rename(os.path.join(fd, "H01.jpg"), os.path.join(fd, "H01.bak"))
    assert c.post("/api/aggiorna_foto") == {"aggiornate": [], "proporzioni": [], "errori": ["H02.jpg"]}
    assert any(x.startswith("H02.jpg: non aggiornata (") for x in c.get("/api/log")) and c.get("/api/state")["agg"]["n"] == 0


def test_foto_modificata_senza_volti(apri, monkeypatch):
    """se la ricerca dei volti non riesce la foto si aggiorna lo stesso (miniatura e misure) e il registro lo dice"""
    c = apri(); f = os.path.join(c.progetto, "Foto", "H01.jpg")
    _foto(900, 600, (10, 200, 10)).save(f, quality=90); _tocca(f, 30)
    monkeypatch.setattr(A, "_build_faces", lambda m: (_ for _ in ()).throw(RuntimeError("OpenCV non disponibile")))
    assert c.post("/api/aggiorna_foto") == {"aggiornate": ["H01.jpg"], "proporzioni": [], "errori": []}
    assert "volti di H01.jpg non rifatti: OpenCV non disponibile" in c.get("/api/log")
    assert _img(c.raw("/img/thumb/H01?w=60")).getpixel((30, 20))[1] > 150 and c.get("/api/state")["agg"]["nomi"] == ["H01.jpg"]


def test_controllo_delle_foto_modificate(apri, monkeypatch):
    """il ciclo di sottofondo aggiorna una foto modificata quando è ferma da due giri; un errore nel controllo si annota e il ciclo continua"""
    c = apri(); f = os.path.join(c.progetto, "Foto", "H01.jpg")
    _foto(900, 600, (230, 20, 20)).save(f, quality=90); _tocca(f, -10); _tocca(os.path.join(c.progetto, "_cache", "thumbs", "H01.jpg"), -100)
    E.foto_watch_loop(Passi(1)); assert E.AGG["n"] == 0, "al primo giro la foto potrebbe essere ancora in scrittura"
    E.foto_watch_loop(Passi(2)); assert E.AGG["n"] == 1 and E.AGG["nomi"] == ["H01.jpg"]
    assert _rosso(_img(c.raw("/img/thumb/H01?w=60")).getpixel((30, 20)))
    giri = []
    def guasto(): giri.append(1); raise OSError("disco scollegato")
    monkeypatch.setattr(E, "foto_cambiate", guasto)
    E.foto_watch_loop(Passi(2)); assert len(giri) == 2 and E.LOG.count("controllo foto modificate: disco scollegato") == 2


# ---------------------------------------------------------------- informazioni della foto
def test_informazioni_exif_della_foto(apri):
    """dati di scatto della foto originale: profilo colore, tempo (frazione o secondi), diaframma, ISO (anche in elenco),
    focale e data (dello scatto o del file); se l'originale non si apre, l'errore al posto dei dati"""
    def exif(tempo, iso, data_scatto=None, data=None):
        ex = Image.Exif(); s = ex.get_ifd(0x8769)
        s[33434] = tempo; s[33437] = 2.8; s[34855] = iso; s[37386] = 85.0
        if data_scatto: s[36867] = data_scatto
        if data: ex[306] = data
        return ex.tobytes()
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    c = apri()
    fd = os.path.join(c.progetto, "Foto")
    _foto(900, 600).save(os.path.join(fd, "H01.jpg"), quality=90, icc_profile=icc, exif=exif(1 / 250, 400, data_scatto="2026:05:23 10:00:01"))
    _foto(900, 600).save(os.path.join(fd, "H02.jpg"), quality=90, exif=exif(2.0, (100, 200), data="2026:06:01 08:00:00"))
    os.remove(os.path.join(fd, "H08.jpg"))
    i1 = c.get("/api/info/H01")
    assert i1 == {"dim": [900, 600], "profilo": i1["profilo"], "tempo": "1/250", "diaframma": "f/2.8", "iso": 400, "focale": "85 mm", "data": "2026:05:23 10:00:01"} and "sRGB" in i1["profilo"]
    assert c.get("/api/info/H02") == {"dim": [900, 600], "tempo": "2 s", "diaframma": "f/2.8", "iso": 100, "focale": "85 mm", "data": "2026:06:01 08:00:00"}
    i8 = c.get("/api/info/H08"); assert set(i8) == {"dim", "errore"} and "H08.jpg" in i8["errore"]
    os.remove(os.path.join(fd, "H01.jpg")); assert c.get("/api/info/H01") == i1, "letti una volta sola"


# ---------------------------------------------------------------- salvataggio
def test_pulizia_copie_e_autosalvataggio_che_non_riesce(apri, monkeypatch, tmp_path):
    """se la pulizia delle copie di sicurezza non riesce lo si annota; se l'autosalvataggio non riesce l'errore va nella
    barra in alto (saveerr) e il ciclo continua"""
    c = apri(); f = tmp_path / "non-una-cartella"; f.write_text("x", encoding="utf-8")
    E._pota_backup(str(f)); assert E.LOG[-1].startswith("pulizia copie non riuscita: ")
    _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); E.LAST["op"] = 0
    monkeypatch.setattr(formato, "scrivi_atomico", lambda p, t: (_ for _ in ()).throw(PermissionError(13, "negato", p)))
    E.autosave_loop(Passi(2))
    assert [x for x in E.LOG if x.startswith("autosalvataggio non riuscito: [Errno 13] negato: ")] == E.LOG[-2:] and len(E.LOG) >= 2
    st = c.get("/api/state"); assert st["dirty"] and "negato" in st["saveerr"]


# ---------------------------------------------------------------- esportazioni
def test_intervallo_di_spread():
    assert E.parse_range("", 3) == [1, 2, 3] and E.parse_range("3-1;; 5,", 6) == [1, 2, 3, 5] and E.parse_range("2, 2-3", 4) == [2, 3]
    with pytest.raises(ValueError, match=r"spread inesistenti: \[0, 7\] \(l'album ne ha 6\)"): E.parse_range("0, 7", 6)


def test_spiegazioni_degli_errori():
    """errori tecnici -> frasi per l'utente"""
    assert E._spiega(PermissionError(13, "Permission denied", "/Volumes/Chiavetta")) == "non posso scrivere nella cartella di destinazione (/Volumes/Chiavetta): scegline un'altra"
    assert E._spiega(PermissionError(13, "Permission denied")) == "non posso scrivere nella cartella di destinazione (): scegline un'altra"
    assert E._spiega(OSError(errno.ENOSPC, "No space left on device")) == "il disco è pieno: libera spazio o scegli un altro disco"
    assert E._spiega(FileNotFoundError(2, "No such file", "/x/foto.jpg")) == "file non trovato: /x/foto.jpg"
    assert E._spiega(MemoryError()) == "memoria insufficiente: prova a esportare meno spread alla volta"
    assert E._spiega(ValueError("strano")) == "strano" and E._spiega(KeyError("x")) == "errore imprevisto (KeyError: 'x')"


def test_pdf_con_il_profilo_del_sistema(monkeypatch, tmp_path):
    """il profilo sRGB del sistema (quando c'è) va nel PDF, letto una volta sola; una pagina per immagine"""
    p = tmp_path / "sRGB Profile.icc"; p.write_bytes(b"profilo sRGB del sistema")
    monkeypatch.setattr(pfont, "profilo_srgb", lambda: str(p)); monkeypatch.setattr(E, "_ICC", None)
    assert E.srgb_icc() == b"profilo sRGB del sistema"
    p.unlink(); assert E.srgb_icc() == b"profilo sRGB del sistema", "letto una volta sola"
    b = io.BytesIO(); _foto(300, 120, (200, 10, 10)).save(b, "JPEG"); j = b.getvalue()
    E.write_pdf(str(tmp_path / "b.pdf"), [(j, 300, 120), (j, 300, 120)], dpi=150)
    pdf = (tmp_path / "b.pdf").read_bytes()
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF") and b"/Type /Pages /Count 2 " in pdf and len(re.findall(rb"/Type /Page ", pdf)) == 2
    assert b"<< /N 3 /Alternate /DeviceRGB /Length 24 >>\nstream\nprofilo sRGB del sistema\nendstream" in pdf and pdf.count(j) == 2
    assert b"/MediaBox [0 0 144.000 57.600]" in pdf, "300 x 120 px a 150 dpi"


def test_controlli_prima_di_esportare(apri, monkeypatch):
    """prima di partire: album vuoto, intervallo vuoto, spread tolto nel frattempo, disco pieno"""
    c = apri(); errore = lambda **o: c.prova("/api/export", o)[1]["errore"]
    assert errore(fmt="jpg") == "Non c'è nessuno spread da esportare"
    _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); _spread(c, _pag(c, "FULL", "V03"), _pag(c, "FULL", "V04"))
    assert errore(fmt="jpg", range=" , ;") == "Nessuno spread nell'intervallo scelto"
    with pytest.raises(ValueError, match="^Lo spread 3 non esiste: gli spread sono 2$"): E.preflight({}, [1, 3], c.progetto, "jpg")
    monkeypatch.setattr(shutil, "disk_usage", lambda p: Disco(10**9, 10**9, 2 * 10**7))
    assert errore(fmt="jpg") == "Spazio insufficiente: servono circa 0,1 GB e ne restano 0,0 GB. Libera spazio o scegli un altro disco"
    assert c.get("/api/log") == [], "niente è partito"


def test_jpg_con_spread_non_scritti(apri, monkeypatch):
    """un JPG rimasto vuoto (disco di rete che perde i dati) e un disco pieno: gli spread si saltano con il motivo e
    l'esportazione finisce con l'errore; niente RISULTATO se non è uscito niente"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); _spread(c, _pag(c, "FULL", "V03"), _pag(c, "FULL", "V04"))
    scritti = []

    def scrivi(im, f, **kw):
        scritti.append(os.path.basename(f))
        if len(scritti) == 1: open(f, "wb").close()
        else: raise OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(E, "_scrivi_img", scrivi)
    c.post("/api/export", {"fmt": "jpg", "res": "bozza"}); L = attendi_log(c)
    dest = os.path.join(c.progetto, "Esportazioni", "JPG")
    assert L == [f"Esporto 2 spread in JPG → {dest}", "SALTATO spread 1 -> file vuoto", "SALTATO spread 2 -> il disco è pieno: libera spazio o scegli un altro disco",
                 "ESPORTATI 0 spread su 2", "ERRORE: 2 spread non esportati (vedi sopra)", "[finito]"]
    assert scritti == ["Prova - Spread 01.jpg", "Prova - Spread 02.jpg"]


def test_pdf_rimasto_vuoto(apri, monkeypatch):
    """un PDF che sul disco risulta vuoto è un errore, non un risultato"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    monkeypatch.setattr(E, "write_pdf", lambda path, jpegs, dpi=150: open(path, "wb").close())
    c.post("/api/export", {"fmt": "pdf", "width": 400, "range": "1"}); L = attendi_log(c)
    assert L[-2:] == ["ERRORE: il PDF risulta vuoto", "[finito]"] and not any(x.startswith("RISULTATO:") for x in L)


def _psd_finto(monkeypatch, dest, crea=(), righe=(), codice=0):
    """processo dei PSD finto (al posto di genera_psd_angolo con Photoshop): registra il comando, scrive i PSD degli spread
    in `crea` e risponde con le righe e il codice d'uscita dati"""
    chiamate = []

    class Processo:
        def __init__(self, cmd, **kw):
            chiamate.append(dict(kw, cmd=cmd))
            for k in crea:
                with open(os.path.join(dest, f"Spread_{k:02d}.psd"), "wb") as f: f.write(b"8BPS" + bytes(200_000))
            self.stdout = iter([r + "\n" for r in righe])

        def wait(self): return codice
    monkeypatch.setattr(subprocess, "Popen", Processo)
    return chiamate


ESITI_PSD = {
    "tutti": (dict(crea=(1, 2), righe=["spread 1 ok", "spread 2 ok"]), ["PSD creati: 2 su 2"], True),
    "uno a mano": (dict(crea=(1,), righe=["spread 1 ok", "@@SALTATO 2 modificato", "SALTATO spread 2: modificato a mano dopo la generazione -> usa modifica_psd.py"]), ["PSD creati: 1 su 2 (1 lasciati com'erano perché modificati a mano)"], True),
    "nessuno": (dict(), ["SALTATO spread 1 -> il PSD non è stato creato", "SALTATO spread 2 -> il PSD non è stato creato", "PSD creati: 0 su 2"], False),
    "photoshop": (dict(righe=["Error 8800: General Photoshop error occurred."], codice=1),
                  ["SALTATO spread 1 -> il PSD non è stato creato", "SALTATO spread 2 -> il PSD non è stato creato",
                   "ERRORE: Photoshop ha dato un errore. Controlla che sia aperto, senza finestre di dialogo in attesa, e riprova", "PSD creati: 0 su 2"], False),
    "fermo": (dict(crea=(1, 2), righe=["Traceback (most recent call last):"], codice=2), ["ERRORE: lo script dei PSD si è fermato (codice 2): vedi sopra", "PSD creati: 2 su 2"], True),
}


@pytest.mark.parametrize("esito", ESITI_PSD)
def test_psd_con_il_processo_dei_psd(apri, monkeypatch, esito):
    """PSD: lo script dei PSD gira come processo a parte (questo Python, argomenti in lista); il registro dice quali PSD sono
    stati creati, quali lasciati perché modificati a mano, quali mancano (anche se c'è un PSD vecchio) e gli errori"""
    kw, attese, risultato = ESITI_PSD[esito]
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); _spread(c, _pag(c, "FULL", "V03"), _pag(c, "FULL", "V04"))
    dest = os.path.join(c.progetto, "PSD"); os.makedirs(dest)
    vecchio = os.path.join(dest, "Spread_01.psd")
    with open(vecchio, "wb") as f: f.write(bytes(200_000))
    _tocca(vecchio, -3600)
    monkeypatch.setattr(pps, "trova", lambda: dict(nome="Adobe Photoshop 2026", percorso="/Applications/Adobe Photoshop 2026/Adobe Photoshop 2026.app"))
    monkeypatch.setattr(shutil, "disk_usage", lambda p: Disco(10**12, 0, 10**12))
    chiamate = _psd_finto(monkeypatch, dest, **kw)
    assert c.post("/api/export", {"fmt": "psd", "force": esito == "tutti"}) == {"spread": 2}
    L = attendi_log(c)
    visibili = [r for r in kw.get("righe", ()) if not r.startswith("@@")]            # le righe di protocollo non entrano nel registro
    assert L[0] == f"Esporto 2 spread in PSD → {dest}" and L[1:1 + len(visibili)] == visibili
    resto = L[1 + len(visibili):]
    assert resto == attese + ([f"RISULTATO:{dest}"] if risultato else []) + ["[finito]"], L
    (ch,) = chiamate
    assert ch["cmd"] == [sys.executable, "-m", "impaginatore.motore.genera_psd_angolo", "--spread", "1,2", "--progetto", c.progetto] + (["--forza"] if esito == "tutti" else [])
    assert ch["cwd"] == processi.cartella_pacchetto() and ch["env"]["ALBUM_PROGETTO"] == c.progetto and ch["stdout"] == subprocess.PIPE and "shell" not in ch
    assert formato.leggi_json(os.path.join(c.progetto, "progetto.json"))["uscita_psd"] == dest


# ---------------------------------------------------------------- selettore, ricollegamento, esportazione del progetto
@POSIX
def test_selettore_salta_i_collegamenti_rotti(apri, tmp_path):
    c = apri(); fd = os.path.join(c.progetto, "Foto"); os.symlink(str(tmp_path / "sparita.jpg"), os.path.join(fd, "rotta.jpg"))
    r = c.get("/api/ls?p=" + urllib.parse.quote(fd)); nomi = [f["n"] for f in r["files"]]
    assert "rotta.jpg" not in nomi and len(nomi) == 10


def test_miniatura_del_selettore_fatta_una_volta(apri, monkeypatch):
    c = apri(); u = "/api/fthumb?w=80&p=" + urllib.parse.quote(os.path.join(c.progetto, "Foto", "H01.jpg"))
    prima = c.raw(u); assert _img(prima).size == (80, 53)
    monkeypatch.setattr(A, "apri_foto", lambda f: (_ for _ in ()).throw(AssertionError("riaperta")))
    assert c.raw(u) == prima


def _selezione_di_collegamenti(p, originali):
    """come le selezioni fatte dalle versioni 1.x: la cartella Foto del progetto ha collegamenti alle foto originali"""
    fd = os.path.join(p, "Foto"); shutil.move(fd, originali); os.mkdir(fd)
    for f in sorted(os.listdir(originali)): os.symlink(os.path.join(originali, f), os.path.join(fd, f))


@POSIX
@pytest.mark.parametrize("sola_lettura", [False, True])
def test_ricollega_rifa_i_collegamenti(apri, tmp_path, sola_lettura):
    """originali spostati: ricollegando la loro nuova cartella i collegamenti rotti della selezione si rifanno (se la cartella
    si può scrivere; altrimenti restano rotti ma le foto si trovano lo stesso); quelle che non ci sono restano mancanti"""
    orig, nuova = tmp_path / "Originali", tmp_path / "Spostati"
    c = apri(prepara=lambda p: _selezione_di_collegamenti(p, str(orig))); fd = os.path.join(c.progetto, "Foto")
    os.rename(orig, nuova); os.remove(nuova / "Q09.jpg")
    assert len(c.get("/api/state")["mancanti"]) == 10
    if sola_lettura: os.chmod(fd, 0o555)
    try:
        dialoghi.imposta(Finti(str(nuova)))
        assert c.post("/api/ricollega", {}) == {"trovate": 9, "mancanti": ["Q09.jpg"], "totale": 10, "diverse": [], "proposte": []}
    finally: os.chmod(fd, 0o755)
    assert os.readlink(os.path.join(fd, "H01.jpg")) == (str(orig / "H01.jpg") if sola_lettura else str(nuova / "H01.jpg"))
    assert os.path.exists(os.path.join(fd, "H01.jpg")) != sola_lettura and not os.path.exists(os.path.join(fd, "Q09.jpg"))
    assert c.get("/api/state")["mancanti"] == ["Q09.jpg"]
    assert {m["n"]: m["src"] for m in formato.leggi_json(os.path.join(c.progetto, "_cache", "meta.json"))}["H01.jpg"] == str(nuova / "H01.jpg")


def test_ricollega_senza_la_cartella_della_selezione(apri, tmp_path):
    """la cartella della selezione è sparita del tutto: le foto si ritrovano nella cartella scelta; una cartella che non c'è è un errore"""
    sel, nuova = tmp_path / "Selezione", tmp_path / "Nuova"

    def prepara(p):
        shutil.move(os.path.join(p, "Foto"), sel); pj = os.path.join(p, "progetto.json"); c = formato.leggi_json(pj); c["foto"] = str(sel)
        formato.scrivi_json(pj, c, indent=2, ensure_ascii=False)
    c = apri(prepara=prepara); os.rename(sel, nuova)
    ok, r = c.prova("/api/ricollega", {"cartella": os.path.join(c.progetto, "non-esiste")}); assert not ok and r["errore"] == "cartella non trovata"
    dialoghi.imposta(Finti(str(nuova)))
    assert c.post("/api/ricollega", {}) == {"trovate": 10, "mancanti": [], "totale": 10, "diverse": [], "proposte": []} and c.get("/api/state")["mancanti"] == []


def test_esporta_progetto_con_foto_mancanti(apri, tmp_path):
    """nel pacchetto vanno le foto che ci sono (le altre si annotano); una destinazione che non c'è è un errore"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    ok, r = c.prova("/api/prj_esporta", {"dest": os.path.join(c.progetto, "non-esiste")}); assert not ok and r["errore"] == "scegli una cartella di destinazione"
    os.rename(os.path.join(c.progetto, "Foto", "H02.jpg"), os.path.join(c.progetto, "H02.bak"))
    dest = tmp_path / "uscita"; dest.mkdir(); dialoghi.imposta(Finti(str(dest)))
    out = c.post("/api/prj_esporta", {"foto": True})["cartella"]; L = attendi_log(c)
    assert "  ATTENZIONE: H02.jpg non trovata, non è nel pacchetto" in L and L[-2] == "RISULTATO:" + out, L
    assert sorted(os.listdir(os.path.join(out, "Foto"))) == sorted(f"{n}.jpg" for n in _ix(c) if n != "H02")


@POSIX
def test_cartella_di_sola_lettura(apri):
    """esportazioni e progetto esportato in una cartella dove non si può scrivere: l'esportazione non parte e lo dice, il
    progetto esportato si ferma con l'errore e non lascia niente"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    ro = os.path.join(c.progetto, "sola lettura"); os.mkdir(ro); os.chmod(ro, 0o555)
    try:
        ok, r = c.prova("/api/export", {"fmt": "pdf", "dest": ro})
        assert not ok and r["errore"] == f"Non posso scrivere in «{ro}»: Permission denied. Scegli un'altra cartella"
        c.post("/api/prj_esporta", {"dest": ro}); L = attendi_log(c)
    finally: os.chmod(ro, 0o755)
    assert re.fullmatch(r"ERRORE: \[Errno 13\] Permission denied: .*", L[-2]) and L[-1] == "[finito]" and os.listdir(ro) == []


# ---------------------------------------------------------------- versioni
def test_versioni_tante_doppie_e_con_data_strana(apri):
    """al massimo 80 versioni, dalla più recente; due copie identiche di fila sono una versione sola; una data che non si legge
    resta com'è nell'etichetta"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); c.post("/api/save")
    bk = os.path.join(c.progetto, "_backup_editor")
    for f in os.listdir(bk): os.remove(os.path.join(bk, f))
    with open(os.path.join(c.progetto, "album.json"), encoding="utf-8") as f: testo = f.read()

    def copia(ts, extra=""):
        with open(os.path.join(bk, f"{ts}_album.json"), "w", encoding="utf-8") as f: f.write(testo + extra)
    for k in range(85): copia("20250101-%02d%02d00" % divmod(k, 60), " " * (k + 1))
    copia("20251231-235958", "\n"); copia("20251231-235959", "\n"); copia("20251399-000000")
    v = c.get("/api/versioni")
    assert len(v) == 80 and v[0] == {"ts": "20251399-000000", "spread": 1, "label": "20251399-000000"}
    assert [x["ts"] for x in v[1:3]] == ["20251231-235959", "20250101-012400"] and v[1]["label"] == "31/12 23:59:59"


# ---------------------------------------------------------------- avvio come programma
def test_editor_come_programma(base, tmp_path):
    """python -m impaginatore.editor.server: apre il progetto, scrive l'indirizzo e risponde con il gettone del processo"""
    p = _copia(base, str(tmp_path / "Prova")); g = secrets.token_urlsafe(32)
    pr = subprocess.Popen([sys.executable, "-m", "impaginatore.editor.server", "--progetto", p, "--porta", "0", "--home", "http://127.0.0.1:9"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=dict(processi.ambiente_figli(), IMPAGINATORE_GETTONE=g))
    try:
        righe = []
        def riga():
            r = pr.stdout.readline(); righe.append(r)
            return re.search(r"^Editor album: http://127\.0\.0\.1:(\d+)  \| progetto: (.*)$", r) or (not r and pr.poll() is not None and "uscito")
        m = attendi(riga, 120, 0)
        assert m != "uscito" and m.group(2) == p, righe
        e = Client(int(m.group(1)), g); assert e.get("/api/ping")["path"] == p and len(e.get("/api/state")["photos"]) == 10
    finally:
        pr.terminate(); pr.wait(30)


# ---------------------------------------------------------------- lingua (T-206): testi del server e esito strutturato
def test_inglese_errore_http_conflitto_e_passo_d_annulla(apri, monkeypatch):
    """un errore HTTP esce nella lingua in uso; il nome del passo si salva come chiave e si traduce quando esce: scritto in
    italiano, letto in inglese dopo il cambio di lingua; il conflitto fra schede ha il testo nella lingua e il codice"""
    c = apri(); assert c.prova("/api/export", {"fmt": "jpg"})[1]["errore"] == "Non c'è nessuno spread da esportare"
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    assert c.prova("/api/export", {"fmt": "jpg"}) == (False, {"errore": "There's no spread to export"})
    assert c.prova("/api/inesistente") == (False, {"errore": "Not found"})
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")
    _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    st = c.post("/api/op", dict(op="evg", value=0.5, cid="a", rev=c.get("/api/state")["rev"]))
    assert st["annulla"]["nome"] == "Esposizione dell'album" and E.UNDO[-1]["chiave"] == "server.op_evg"
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    assert c.get("/api/state")["annulla"]["nome"] == "Album exposure"
    ok, r = c.prova("/api/op", dict(op="evg", value=0.7, cid="b", rev=0))
    assert not ok and r["codice"] == "altra_scheda" and r["errore"].startswith("Another tab changed this project")
    r = c.post("/api/op", dict(op="undo"))
    assert r["annullato"]["nome"] == "Album exposure" and r["ripeti"]["nome"] == "Album exposure"
    assert c.post("/api/op", dict(op="addtext", s=0, fx=0.1, fy=0.1, fw=0.2))["annulla"]["nome"] == "Add text"
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it"); assert c.get("/api/state")["annulla"]["nome"] == "Aggiungi testo"


def test_inglese_controllo_dell_album(apri, monkeypatch):
    """«Controlla» dice i problemi nella lingua in uso, con «Spread N: » davanti come sempre"""
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en"); c = apri()
    _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); os.remove(os.path.join(c.progetto, "Foto", "H02.jpg"))
    testi = [p["testo"] for p in c.post("/api/controlla", {})["problemi"]]
    assert "Spread 1: photo H02 can't be found: relink it" in testi and "V03 isn't in the album" in testi and "Spread 1: H01 is too small for this frame (68 ppi, it needs at least 150)" in testi, testi
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")
    assert "Spread 1: la foto H02 non si trova: ricollegala" in [p["testo"] for p in c.post("/api/controlla", {})["problemi"]]


def test_esito_riuscita_e_registro_in_inglese(apri, monkeypatch):
    """/api/esito: prima di ogni esportazione è vuoto; una JPG riuscita dice destinazione, formato, spread fatti e risultato"""
    c = apri(); vuoto = dict(dest="", formato="", totale=0, fatti=0, saltati=[], errori=[], risultato=None, finito=False)
    assert c.get("/api/esito") == vuoto
    _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); _spread(c, _pag(c, "FULL", "V03"), _pag(c, "FULL", "V04"))
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    c.post("/api/export", {"fmt": "jpg", "res": "bozza"}); L = attendi_log(c); dest = os.path.join(c.progetto, "Esportazioni", "JPG")
    assert L == [f"Exporting 2 spreads as JPG → {dest}", "  spread 1: Prova - Spread 01.jpg", "  spread 2: Prova - Spread 02.jpg", "Exported 2 of 2 spreads", f"RISULTATO:{dest}", "[finito]"]
    assert c.get("/api/esito") == dict(vuoto, dest=dest, formato="jpg", totale=2, fatti=2, risultato=dest, finito=True)
    c.post("/api/export", {"fmt": "jpg", "res": "bozza", "range": "1"}); L = attendi_log(c)
    assert L[0] == f"Exporting 1 spread as JPG → {dest}" and c.get("/api/esito")["totale"] == 1


def test_esito_con_spread_saltati_in_inglese(apri, monkeypatch):
    """due spread non scritti (file vuoto, disco pieno): righe del registro in inglese, saltati e errori nell'esito, niente risultato"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); _spread(c, _pag(c, "FULL", "V03"), _pag(c, "FULL", "V04"))
    scritti = []

    def scrivi(im, f, **kw):
        scritti.append(f)
        if len(scritti) == 1: open(f, "wb").close()
        else: raise OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(E, "_scrivi_img", scrivi); monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    c.post("/api/export", {"fmt": "jpg", "res": "bozza"}); L = attendi_log(c); dest = os.path.join(c.progetto, "Esportazioni", "JPG")
    assert L == [f"Exporting 2 spreads as JPG → {dest}", "Skipped spread 1: file is empty", "Skipped spread 2: the disk is full: free up space or choose another disk",
                 "Exported 0 of 2 spreads", "Error: 2 spreads weren't exported (see above)", "[finito]"]
    assert c.get("/api/esito") == dict(dest=dest, formato="jpg", totale=2, fatti=0, risultato=None, finito=True, errori=["2 spreads weren't exported (see above)"],
                                       saltati=[dict(spread=1, motivo="file is empty"), dict(spread=2, motivo="the disk is full: free up space or choose another disk")])
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it"); c.post("/api/export", {"fmt": "jpg", "res": "bozza", "range": "1"}); attendi_log(c)
    assert c.get("/api/esito")["saltati"] == [dict(spread=1, motivo="il disco è pieno: libera spazio o scegli un altro disco")]
    assert c.get("/api/esito")["errori"] == ["1 spread non esportati (vedi sopra)"]


def test_esito_errore_del_pdf_e_progetto_esportato(apri, monkeypatch, tmp_path):
    """un PDF vuoto è un errore nell'esito; l'esportazione del progetto azzera l'esito e dice cartella, foto copiate e risultato"""
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    monkeypatch.setattr(E, "write_pdf", lambda path, jpegs, dpi=150: open(path, "wb").close()); monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    c.post("/api/export", {"fmt": "pdf", "width": 400, "range": "1"}); L = attendi_log(c)
    assert L[-2:] == ["Error: the PDF is empty", "[finito]"]
    assert c.get("/api/esito") == dict(dest=os.path.join(c.progetto, "Esportazioni", "PDF"), formato="pdf", totale=1, fatti=0, saltati=[], errori=["the PDF is empty"], risultato=None, finito=True)
    dest = tmp_path / "uscita"; dest.mkdir(); dialoghi.imposta(Finti(str(dest)))
    out = c.post("/api/prj_esporta", {"foto": True, "zip": True})["cartella"]; L = attendi_log(c)
    assert L[0] == f"Exporting the project to {out}" and "  creating the ZIP…" in L and L[-3].startswith("Done: ") and L[-2] == f"RISULTATO:{out}.zip"
    assert c.get("/api/esito") == dict(dest=out, formato="progetto", totale=10, fatti=10, saltati=[], errori=[], risultato=out + ".zip", finito=True)
    leggimi = open(os.path.join(out, "LEGGIMI.txt"), encoding="utf-8").read()
    assert "choose the ⋯ menu › “Open existing album…”" in leggimi and "(or “Import ZIP…” if you have the .zip file)" in leggimi and "The photos are in the Foto folder" in leggimi
    assert open(os.path.join(out, "font_usati.txt"), encoding="utf-8").read().startswith("Fonts used in the text (install them on the computer where you open the project):\n")
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it"); dialoghi.imposta(Finti(str(dest)))
    out = c.post("/api/prj_esporta", {"foto": False})["cartella"]; attendi_log(c)
    assert "Le foto NON sono incluse" in open(os.path.join(out, "LEGGIMI.txt"), encoding="utf-8").read() and c.get("/api/esito")["totale"] == 0


@pytest.mark.parametrize("lg, aperto, esiste", [("it", "è aperto in Photoshop", "esiste e non l'ho generato io"), ("en", "it's open in Photoshop", "it exists and I didn't generate it")])
def test_psd_saltati_riconosciuti_in_tutte_e_due_le_lingue(apri, monkeypatch, lg, aperto, esiste):
    """il processo dei PSD dice quali spread ha lasciato con righe di protocollo fisse: il server le riconosce con qualunque
    lingua, non le mostra, e nell'esito mette il motivo nella lingua in uso"""
    monkeypatch.setenv("IMPAGINATORE_LINGUA", lg)
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02")); _spread(c, _pag(c, "FULL", "V03"), _pag(c, "FULL", "V04"))
    dest = os.path.join(c.progetto, "PSD"); os.makedirs(dest)
    monkeypatch.setattr(pps, "trova", lambda: dict(nome="Adobe Photoshop 2026", percorso="/Applications/Adobe Photoshop 2026/Adobe Photoshop 2026.app"))
    monkeypatch.setattr(shutil, "disk_usage", lambda p: Disco(10**12, 0, 10**12))
    chiamate = _psd_finto(monkeypatch, dest, righe=["@@SALTATO 1 aperto", "una riga del processo", "@@SALTATO 2 esiste"])
    c.post("/api/export", {"fmt": "psd"}); L = attendi_log(c)
    assert "una riga del processo" in L and not any(x.startswith("@@") for x in L)
    e = c.get("/api/esito")
    assert e["saltati"] == [dict(spread=1, motivo=aperto), dict(spread=2, motivo=esiste)] and e["fatti"] == 0 and e["formato"] == "psd" and e["finito"] and e["risultato"] == dest
    assert chiamate[0]["env"]["IMPAGINATORE_PROTOCOLLO"] == "1"


@pytest.mark.parametrize("righe, codice, errore", [(["Error 8800: General Photoshop error occurred."], 1, "Photoshop reported an error. Check that it's open with no dialogue boxes waiting, then try again"),
                                                   (["Traceback (most recent call last):"], 2, "the PSD script stopped (code 2): see above")])
def test_esito_psd_con_errori_in_inglese(apri, monkeypatch, righe, codice, errore):
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    c = apri(); _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    dest = os.path.join(c.progetto, "PSD"); os.makedirs(dest)
    monkeypatch.setattr(pps, "trova", lambda: dict(nome="Adobe Photoshop 2026", percorso="/x")); monkeypatch.setattr(shutil, "disk_usage", lambda p: Disco(10**12, 0, 10**12))
    _psd_finto(monkeypatch, dest, righe=righe, codice=codice, crea=(1,) if codice == 2 else ())
    c.post("/api/export", {"fmt": "psd"}); L = attendi_log(c); e = c.get("/api/esito")
    assert e["errori"] == [errore] and f"Error: {errore}" in L
    assert e["fatti"] == (1 if codice == 2 else 0) and e["saltati"] == ([] if codice == 2 else [dict(spread=1, motivo="the PSD wasn't created")])


def test_inglese_modelli_foto_e_cartelle(apri, monkeypatch):
    """messaggi di errore di modelli, appunti, ricollegamento, foto e operazioni, nella lingua in uso"""
    c = apri(); monkeypatch.setenv("IMPAGINATORE_LINGUA", "en"); errore = lambda p, o=None: c.prova(p, o)[1]["errore"]
    assert errore("/api/ricollega", {"cartella": os.path.join(c.progetto, "non-esiste")}) == "Folder not found"
    assert errore("/api/ricollega", {"cartella": os.path.join(c.progetto, "_cache")}).startswith("This folder belongs to Impaginatore")
    assert errore("/api/ricollega", {"cartella": c.progetto, "scelte": [1]}) == "Invalid choices: a list of “photo name: suggested file”"
    assert errore("/api/ricollega", {"cartella": c.progetto, "scelte": {"H01.jpg": "x.jpg"}}) == "H01.jpg: “x.jpg” isn't one of the suggested photos"
    assert errore("/api/ripristina", {"ts": "no"}) == "Version not found"
    assert errore("/api/info/XXX") == "Photo not found" and errore("/img/thumb/XXX") == "Photo not found"
    assert errore("/api/op", dict(op="incolla", s=0)) == "No such spread: 0"
    _spread(c, _pag(c, "FULL", "H01"), _pag(c, "FULL", "H02"))
    assert errore("/api/modelli", dict(azione="salva", s=0, nome="")) == "Enter a name for the template"
    assert errore("/api/op", dict(op="incolla", s=0)) == "The clipboard is empty: copy something first"
    assert errore("/api/op", dict(op="newspreadsel", names=[], pos=0)) == "A spread takes 1 to 10 photos"
    assert errore("/api/op", dict(op="boh", s=0)) == "Unknown operation: boh"
    assert errore("/api/op", dict(op="swap", a=[0, "X", 0], b=[0, "L", 0])) == "Invalid page: 'X'"
    assert errore("/api/op", dict(op="settext", at=[0, "L", 0], tx="x")) == "This isn't a text layer"
    assert errore("/api/op", dict(op="disposizione", s=0, passo=3)) == "Invalid step: 1 (forward) or -1 (back)"
    assert errore("/api/op", dict(op="spazi", s=0, modo="x")) == "Invalid spacing mode: std, freq or custom"
    assert errore("/api/op", dict(op="bozza", ritmo="x")) == "Invalid rhythm: use alterna, piene or bianche"
    assert errore("/api/op", dict(op="evg", value=1.0, gruppo=5)) == "Invalid group: text of at most 100 characters"
    assert errore("/api/export", dict(fmt="jpg", range="9")) == "spreads that don't exist: [9] (the album has 1)"
