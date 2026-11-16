"""Aggiornamenti firmati (T-207, SEC-007): manifesto e firma Ed25519, controllo, scaricamento, installazione, ritorno alla
versione precedente, annuncio dopo il riavvio. Le release sono cartelle finte (SorgenteFinta): nessuna rete."""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import types

import pytest
from aiuti_aggiornamenti import ALTRO_SEME, PUB, SEME, ambiente_senza_coverage, api, firmato, release, rifirma

from impaginatore import __version__, aggiornamenti, lingua
from impaginatore.aggiornamenti import Rifiutato, firmati, installazione, lanciatore, rilascio, sorgenti

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _manifesto(**cambia):
    m = dict(formato=1, prodotto="impaginatore", id_firma=1, versione="2.0.1", data="2026-12-01", novita={"it": ["a"], "en": ["b"]}, python_minimo="3.11",
             pacchetti={"python": dict(nome="impaginatore-2.0.1-py3-none-any.whl", dimensione=10, sha256="a" * 64)}, file={"impaginatore/__init__.py": "b" * 64})
    m.update(cambia)
    return m


def _pf(d, riavvii=None, chiavi=None, prova=None, installa=None):
    """PacchettiFirmati sulla release finta in d, con la prova di avvio finta (le prove vere: test_aggiornamenti_installazione)"""
    i = installa or installazione.InstallazionePython(prova=prova or (lambda r, v: None))
    return firmati.PacchettiFirmati(sorgenti.SorgenteFinta(d), i, (lambda: riavvii.append(1)) if riavvii is not None else None, chiavi={1: PUB} if chiavi is None else chiavi)


def _puntatore():
    with open(os.path.join(lanciatore.cartella(), "attuale.json"), encoding="utf-8") as f: return json.load(f)


# ---------------------------------------------------------------- firma e campi
def test_firma_valida_e_firme_che_non_valgono():
    m = _manifesto(); dati, f = firmato(m)
    assert firmati.verifica(dati, f, {1: PUB}) == m and firmati.verifica(dati, f.decode(), {1: PUB}) == m
    rifiutate = [
        (dati.replace(b"2.0.1", b"2.0.2", 1), f, {1: PUB}),                      # manifesto cambiato dopo la firma
        (dati, firmato(m, ALTRO_SEME)[1], {1: PUB}),                             # firmato con un'altra chiave
        (dati, f, {2: PUB}), (dati, f, {}), (dati, f, None),                      # chiave sconosciuta, nessuna, il segnaposto
        (dati, b"zz", {1: PUB}), (dati, b"\xff\xfe", {1: PUB}), (dati, f[:-2], {1: PUB}),
        (*firmato(dict(m, id_firma="1")), {1: PUB}), (*firmato([1, 2]), {1: PUB}),
    ]
    for d, s, k in rifiutate:
        with pytest.raises(Rifiutato) as e: firmati.verifica(d, s, k)
        assert e.value.chiave == "sistema.agg_firma_non_valida"
    import impaginatore.ed25519 as E
    senza_dominio = E.firma(SEME, dati).hex()                                    # la stessa chiave usata per altro (DOMINIO)
    with pytest.raises(Rifiutato, match="firma valida"): firmati.verifica(dati, senza_dominio, {1: PUB})
    for d in ("testo", b"x" * (firmati.MAX_MANIFESTO + 1)):
        with pytest.raises(Rifiutato) as e: firmati.verifica(d, f, {1: PUB})
        assert e.value.chiave == "sistema.agg_troppo_grande"
    for d in (b"\xff", b"{non json"):
        with pytest.raises(Rifiutato, match=r"\(json\)"): firmati.verifica(d, f, {1: PUB})


@pytest.mark.parametrize("campo, cambia", [
    ("formato", dict(formato=2)), ("prodotto", dict(prodotto="altro")), ("versione", dict(versione="2.0")), ("versione", dict(versione=None)),
    ("data", dict(data=5)), ("data", dict(data="x" * 41)),
    ("novita", dict(novita=[])), ("novita", dict(novita={"ita": []})), ("novita", dict(novita={"it": "testo"})), ("novita", dict(novita={"it": ["x" * 301]})),
    ("novita", dict(novita={"it": ["a"] * 31})), ("novita", dict(novita={"it": [3]})),
    ("python_minimo", dict(python_minimo=3.11)), ("python_minimo", dict(python_minimo="4.0")),
    ("pacchetti", dict(pacchetti={})), ("pacchetti", dict(pacchetti=[])),
    ("pacchetti.python", dict(pacchetti={"python": dict(nome="../x.whl", dimensione=1, sha256="a" * 64)})),
    ("pacchetti.python", dict(pacchetti={"python": dict(nome="x.whl", dimensione=0, sha256="a" * 64)})),
    ("pacchetti.python", dict(pacchetti={"python": dict(nome="x.whl", dimensione=True, sha256="a" * 64)})),
    ("pacchetti.python", dict(pacchetti={"python": dict(nome="x.whl", dimensione=firmati.MAX_PACCHETTO + 1, sha256="a" * 64)})),
    ("pacchetti.python", dict(pacchetti={"python": dict(nome="x.whl", dimensione=1, sha256="A" * 64)})),
    ("pacchetti.python", dict(pacchetti={"python": "x"})),
    ("file", dict(file={})), ("file", dict(file=[])), ("file", dict(file={"impaginatore/a.py": "b" * 64})),
    ("file", dict(file={"impaginatore/__init__.py": "b" * 64, "impaginatore/../fuori.py": "b" * 64})),
    ("file", dict(file={"impaginatore/__init__.py": "b" * 63})),
])
def test_campi_del_manifesto(campo, cambia):
    with pytest.raises(Rifiutato) as e: firmati.controlla_campi(_manifesto(**cambia))
    assert e.value.chiave == "sistema.agg_manifesto_non_valido" and e.value.param == {"campo": campo}
    with pytest.raises(Rifiutato, match=r"\(formato\)"): firmati.controlla_campi([])


def test_troppi_file(monkeypatch):
    monkeypatch.setattr(firmati, "MAX_FILE", 1)
    with pytest.raises(Rifiutato, match=r"\(file\)"): firmati.controlla_campi(_manifesto(file={"impaginatore/__init__.py": "b" * 64, "impaginatore/a.py": "b" * 64}))


@pytest.mark.parametrize("nome, ok", [
    ("impaginatore/__init__.py", True), ("impaginatore/risorse/testi/it/home.json", True), ("impaginatore/a-b_c.d.py", True),
    ("impaginatore", False), ("altro/x.py", False), ("/impaginatore/x.py", False), ("impaginatore/../x.py", False), ("impaginatore/./x.py", False),
    ("impaginatore//x.py", False), ("impaginatore/.nascosto", False), ("impaginatore\\x.py", False), ("impaginatore/con.py", False),
    ("impaginatore/sotto/LPT1", False), ("impaginatore/aux", False), ("impaginatore/" + "a" * 300, False), (None, False), ("impaginatore/a b.py", False),
])
def test_nomi_dei_file_del_pacchetto(nome, ok):
    assert firmati.percorso_valido(nome) is ok


def test_un_rilascio_non_parte_con_il_segnaposto():
    """versione finale (es. 2.0.0) con il segnaposto nel codice: nessun aggiornamento arriverebbe mai. Questo test la ferma.
    Nelle versioni di sviluppo (2.0.0.dev0, 2.0.0rc1) il segnaposto è atteso: gli aggiornamenti si provano con una release finta"""
    finale = re.fullmatch(r"\d+\.\d+\.\d+", __version__) is not None
    problemi = firmati.problemi_per_il_rilascio()
    assert not (finale and problemi), f"rilascio {__version__} con la chiave degli aggiornamenti di prova: {problemi} (docs/architettura/AGGIORNAMENTI.md, «Prima del rilascio»)"
    if not finale: assert problemi, "copia di sviluppo: la chiave pubblica vera arriva al rilascio"
    assert firmati.problemi_per_il_rilascio({}) == ["nessuna chiave pubblica degli aggiornamenti"] and firmati.problemi_per_il_rilascio({1: PUB}) == []
    assert firmati.pubblica(firmati.SEGNAPOSTO) is None and firmati.pubblica(None) is None and firmati.pubblica("ab") is None and firmati.pubblica(PUB) == bytes.fromhex(PUB)


def test_chiave_di_prova_solo_nelle_versioni_di_sviluppo(tmp_path, monkeypatch):
    d = release(tmp_path / "rel", id_firma=0); s = sorgenti.SorgenteFinta(d)
    assert firmati.chiavi_con_prova(s, {1: PUB}) == {1: PUB, 0: PUB}, "2.0.0.dev0: la chiave accanto alla release finta vale"
    assert firmati.chiavi_con_prova(s)[0] == PUB and firmati.chiavi_con_prova(s)[1] == firmati.SEGNAPOSTO
    assert firmati.chiavi_con_prova(sorgenti.SorgenteFinta(tmp_path / "manca"), {}) == {}
    (tmp_path / "rel" / "chiave-prova.txt").write_text("non una chiave", encoding="utf-8")
    assert firmati.chiavi_con_prova(s, {}) == {}
    (tmp_path / "rel" / "chiave-prova.txt").write_text(PUB, encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert firmati.chiavi_con_prova(s, {}) == {}, "programma compilato: mai"
    monkeypatch.delattr(sys, "frozen")
    monkeypatch.setattr(firmati, "__version__", "2.0.1")
    assert firmati.chiavi_con_prova(s, {}) == {}, "versione finale: mai"


# ---------------------------------------------------------------- il giro completo
def test_controlla_aggiorna_torna_indietro(tmp_path, monkeypatch):
    d = release(tmp_path / "rel"); riavvii = []
    p = _pf(d, riavvii)
    s = p.stato()
    assert isinstance(p, aggiornamenti.Aggiornamenti) and s["disponibile"] and s["motivo"] is None and not s["da_aggiornare"] and s["precedente"] is None
    assert s["attuale"] == dict(n=__version__, codice="", data="", titolo="versione installata", rel="") and s["annuncio"] is None and s["scartata"] is False
    c = p.controlla()
    assert c["da_aggiornare"] and c["ultima"]["n"] == "2.0.1" and c["ultima"]["titolo"] == "versione firmata" and c["novita"] == ["Novità della 2.0.1"] and c["errore"] == ""
    assert c["controllato"] > 0 and c["scartata"] is False
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    assert p.stato()["novita"] == ["New in 2.0.1"], "le novità nella lingua in uso, anche se è cambiata dopo il controllo"
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")
    assert p.versioni() == [dict(n=__version__, codice=__version__, data="", titolo="versione installata", attuale=True)]
    os.makedirs(os.path.join(lanciatore.cartella(), "scarichi", "resto-cartella"))
    with open(os.path.join(lanciatore.cartella(), "scarichi", "resto.whl"), "wb") as f: f.write(b"interrotto")
    assert p.aggiorna() is True and riavvii == [1]
    assert _puntatore() == dict(formato=1, versione="2.0.1", precedente=__version__, confermata=False, tentativi=0, scartata=None)
    copia = os.path.join(lanciatore.cartella(), "versioni", "2.0.1")
    assert lanciatore.copia("2.0.1") == copia and sorted(os.listdir(os.path.join(copia, "impaginatore"))) == ["__init__.py", "sotto"]
    assert os.listdir(os.path.join(lanciatore.cartella(), "scarichi")) == ["resto-cartella"], "lo scaricato e i resti si tolgono (una cartella resta: non è un nostro file)"
    assert p.nuovo is None and p.stato()["da_aggiornare"] is True, "fino al riavvio la pagina mostra ancora lo stato del controllo"
    # il programma riavviato (qui: la stessa classe con la versione nuova) annuncia l'aggiornamento, una volta
    for m in (firmati, installazione): monkeypatch.setattr(m, "__version__", "2.0.1")
    q = _pf(d, riavvii)
    assert q.stato()["annuncio"]["tipo"] == "aggiornato" and q.stato()["annuncio"]["versione"] == "2.0.1" and _pf(d).annuncio is None
    assert q.stato()["precedente"] == __version__ and q.versioni()[1] == dict(n=__version__, codice=__version__, data="", titolo="versione usata prima dell'ultimo aggiornamento", attuale=False)
    assert q.versioni(1) == q.versioni()[:1]
    assert not q.controlla()["da_aggiornare"], "la versione pubblicata è quella in uso"
    with pytest.raises(Rifiutato, match="solo alla versione usata prima"): q.ripristina("1.0.0")
    assert q.ripristina(__version__) == dict(n=__version__, caricato=True) and riavvii == [1, 1]
    assert _puntatore() == dict(formato=1, versione=__version__, precedente=None, confermata=True, tentativi=0, scartata="2.0.1")
    for m in (firmati, installazione): monkeypatch.setattr(m, "__version__", __version__)
    r = _pf(d)
    assert r.stato()["annuncio"]["tipo"] == "tornato" and r.controlla()["scartata"] is True, "la versione scartata si propone, ma senza avviso in pagina"


def test_controlli_che_non_trovano_niente_o_non_vanno(tmp_path, monkeypatch, caplog):
    d = release(tmp_path / "rel")
    p = _pf(d)
    def esito(): s = p.controlla(); return s["da_aggiornare"], s["errore"]
    rifirma(d, lambda m: m.update(versione=__version__)); assert esito() == (False, ""), "la stessa versione"
    rifirma(d, lambda m: m.update(versione="1.9.9")); assert esito() == (False, ""), "mai indietro"
    rifirma(d, lambda m: m.update(versione="3.0.0")); assert esito() == (False, ""), "un'altra versione maggiore: non da qui"
    rifirma(d, lambda m: m.update(versione="2.0.1"), seme=ALTRO_SEME)
    assert esito() == (False, "La versione pubblicata non ha una firma valida di Impaginatore: non è stata usata") and p.stato()["ultima"] is None
    rifirma(d, lambda m: m.update(versione="2.0.2"))
    assert esito() == (True, "")
    api(d, lambda j: j.update(assets=[a for a in j["assets"] if a["name"] != "manifesto.json.sig"]))
    assert esito() == (False, "La versione pubblicata è incompleta (mancano dei file): riprova più tardi") and p.nuovo is None
    api(d, lambda j: None); os.remove(os.path.join(d, "manifesto.json.sig"))
    assert esito()[1].startswith("La versione pubblicata è incompleta"), "l'API la elenca ma il file non c'è (404)"
    os.remove(os.path.join(d, "releases", "latest.json"))
    assert esito() == (False, ""), "nessuna release pubblicata"
    p.sorgente = types.SimpleNamespace(configurata=True, ultimo=lambda: (_ for _ in ()).throw(PermissionError("disco")))
    assert esito() == (False, "disco")


def test_non_disponibili_e_rifiuti(tmp_path, monkeypatch):
    chiamate = []
    monkeypatch.setattr(sorgenti.APRI_RETE, "open", lambda *a, **k: chiamate.append(a) or 1 / 0)
    g = firmati.PacchettiFirmati(sorgenti.SorgenteGitHub(""), installazione.InstallazionePython())
    s = g.controlla()
    assert s["disponibile"] is False and "non è configurato" in s["motivo"] and not s["da_aggiornare"] and chiamate == [], "canale non scelto: nessuna richiesta"
    with pytest.raises(ValueError, match="non è configurato"): g.aggiorna()
    assert g.ciclo(threading.Event()) is None and chiamate == []
    with pytest.raises(Rifiutato, match="solo alla versione"): g.ripristina("1.0.0")
    c = firmati.PacchettiFirmati(sorgenti.SorgenteGitHub("x/y"), installazione.InstallazioneCompilata(apri=lambda u: 1 / 0))
    assert c.stato()["manuale"] is True and c.stato()["motivo"] is None and c.versioni()[0]["attuale"] and len(c.versioni()) == 1
    with pytest.raises(Rifiutato, match="installatore"): c.ripristina("1.0.0")
    assert chiamate == []
    monkeypatch.setattr(sorgenti.APRI_RETE, "open", lambda *a, **k: chiamate.append(a[0].full_url) or (_ for _ in ()).throw(OSError("rete finta")))
    with pytest.raises(Rifiutato, match="Non c'è una versione più nuova"): c.aggiorna()           # il controllo non è riuscito: niente da aprire
    assert chiamate == ["https://api.github.com/repos/x/y/releases/latest"] and "rete finta" in c.stato()["errore"]


def test_programma_compilato_apre_la_pagina(tmp_path, monkeypatch):
    """T-302: il programma compilato controlla il manifesto firmato come gli altri, ma «aggiorna» apre la pagina della
    release nel browser: niente scaricamento, niente installazione, niente riavvio"""
    d = release(tmp_path / "rel"); riavvii, aperte = [], []
    i = installazione.InstallazioneCompilata(apri=lambda u: aperte.append(u) or True)
    p = _pf(d, riavvii, installa=i)
    scaricati = []; monkeypatch.setattr(p.sorgente, "scarica", lambda *a: scaricati.append(a))
    s = p.controlla()
    assert s["da_aggiornare"] and s["manuale"] is True and s["ultima"]["n"] == "2.0.1" and s["novita"] == ["Novità della 2.0.1"]
    assert p.aggiorna() == dict(pagina="https://github.com/prova/impaginatore/releases/tag/v2.0.1", versione="2.0.1")
    assert aperte == ["https://github.com/prova/impaginatore/releases/tag/v2.0.1"] and scaricati == [] and riavvii == []
    assert lanciatore.leggi() is None and not os.path.exists(os.path.join(lanciatore.cartella(), "scarichi")), "niente nella cartella dei dati"
    assert p.stato()["da_aggiornare"], "l'avviso resta finché non si installa la versione nuova"


def test_predefiniti_del_programma_compilato(tmp_path, monkeypatch):
    """compilato: sempre InstallazioneCompilata e solo le chiavi vere, anche con una release finta (la chiave di prova mai)"""
    monkeypatch.delenv("IMPAGINATORE_AGGIORNAMENTI", raising=False); monkeypatch.delenv(lanciatore.VAR_FINTI, raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    a = aggiornamenti.predefiniti()
    assert isinstance(a.installazione, installazione.InstallazioneCompilata) and type(a.sorgente) is sorgenti.SorgenteGitHub and a.chiavi == firmati.CHIAVI_FIDATE
    d = release(tmp_path / "rel"); monkeypatch.setenv(lanciatore.VAR_FINTI, d)
    a = aggiornamenti.predefiniti()
    assert isinstance(a.installazione, installazione.InstallazioneCompilata) and isinstance(a.sorgente, sorgenti.SorgenteFinta) and a.chiavi == firmati.CHIAVI_FIDATE
    assert a.controlla()["errore"].startswith("La versione pubblicata non ha una firma valida"), "la release di prova non vale nel programma compilato"


def test_aggiorna_rifiutato(tmp_path, monkeypatch):
    d = release(tmp_path / "rel")
    p = _pf(d)
    rifirma(d, lambda m: m.update(versione="1.0.0"))
    with pytest.raises(Rifiutato, match="Non c'è una versione più nuova"): p.aggiorna()
    rifirma(d, lambda m: m.update(versione="2.0.1"))
    p._lock.acquire()
    with pytest.raises(Rifiutato, match="già in corso"): p.aggiorna()
    p._lock.release()
    with open(os.path.join(d, "manifesto.json"), encoding="utf-8") as f: originale = json.load(f)
    def prova(cambia_m=None, cambia_api=None, dopo=None, **kw):
        q = _pf(d, **kw)
        if cambia_m: rifirma(d, cambia_m)
        if cambia_api: api(d, cambia_api)
        if dopo: dopo()
        q.controlla()
        with pytest.raises(Rifiutato) as e: q.aggiorna()
        rifirma(d, lambda m: (m.clear(), m.update(originale)))
        return e.value.chiave
    assert prova(lambda m: m.update(python_minimo="3.99")) == "sistema.agg_python_vecchio"
    assert prova(lambda m: m["pacchetti"].update(python=dict(m["pacchetti"]["python"], nome="altro.whl"))) == "sistema.agg_release_incompleta"
    assert prova(installa=types.SimpleNamespace(disponibile=True, pacchetto="mac", precedente=lambda: None, manuale=False)) == "sistema.agg_release_incompleta"
    nome = "impaginatore-2.0.1-py3-none-any.whl"
    def digest(j):
        for a in j["assets"]:
            if a["name"] == nome: a["digest"] = "sha256:" + "0" * 64
    assert prova(cambia_api=digest) == "sistema.agg_pacchetto_diverso", "GitHub dice già che il file non è quello firmato"
    def digest_altro(j):
        for a in j["assets"]: a["digest"] = "md5:x"
    with open(os.path.join(d, nome), "rb") as f: buono = f.read()
    def sostituisci():
        with open(os.path.join(d, nome), "wb") as f: f.write(buono[:-1] + bytes([buono[-1] ^ 1]))
    assert prova(cambia_api=digest_altro, dopo=sostituisci) == "sistema.agg_pacchetto_diverso", "stessa misura, contenuto diverso"
    senza_digest = lambda j: [a.pop("digest") for a in j["assets"]]
    with open(os.path.join(d, nome), "wb") as f: f.write(buono + b"x")
    assert prova(cambia_api=senza_digest) == "sistema.agg_troppo_grande", "più lungo della misura firmata: si ferma"
    with open(os.path.join(d, nome), "wb") as f: f.write(buono[:-5])
    assert prova(cambia_api=senza_digest) == "sistema.agg_pacchetto_diverso", "più corto"
    with open(os.path.join(d, nome), "wb") as f: f.write(buono)
    api(d, lambda j: None)
    assert prova(prova=lambda r, v: (_ for _ in ()).throw(Rifiutato("sistema.agg_non_si_avvia", dettaglio="ImportError"))) == "sistema.agg_non_si_avvia"
    assert lanciatore.leggi() is None and os.listdir(os.path.join(lanciatore.cartella(), "scarichi")) == [], "niente installato, niente resti"
    assert os.listdir(os.path.join(lanciatore.cartella(), "versioni")) == []
    q = _pf(d); q.controlla(); q.nuovo = dict(q.nuovo, versione=__version__)
    with pytest.raises(Rifiutato, match="Non c'è una versione più nuova"): q.aggiorna()
    q = _pf(d); q.controlla()
    q.sorgente.scarica = lambda a, dest, massimo: (_ for _ in ()).throw(Rifiutato("sistema.agg_rete", dettaglio="connessione caduta"))
    with pytest.raises(Rifiutato, match="connessione caduta"): q.aggiorna()
    assert lanciatore.leggi() is None, "lo scaricamento non è partito: niente da togliere, niente installato"


def test_annuncio_che_non_vale(tmp_path):
    os.makedirs(lanciatore.cartella())
    p = os.path.join(lanciatore.cartella(), firmati.ANNUNCIO)
    for testo in ("non json", json.dumps([1]), json.dumps(dict(tipo="altro", versione=__version__, id="x")), json.dumps(dict(tipo="aggiornato", versione="9.9.9", id="x")),
                  json.dumps(dict(tipo="aggiornato", versione=__version__, id=3))):
        with open(p, "w", encoding="utf-8") as f: f.write(testo)
        assert firmati.prendi_annuncio() is None and not os.path.exists(p)
    assert firmati.prendi_annuncio() is None


def test_ciclo_automatico(tmp_path, monkeypatch):
    p = _pf(release(tmp_path / "rel")); controlli, attese = [], []
    monkeypatch.setattr(p, "controlla", lambda: controlli.append(1))
    class Fermo:
        def __init__(self, n): self.n = n
        def wait(self, t):
            attese.append(t); self.n -= 1; return self.n < 0
    orologio = iter([0, 100, 100, 200, 200, 300, 400])
    monkeypatch.setattr(firmati.time, "time", lambda: next(orologio))
    p.ciclo(Fermo(4), ogni=150, passo=7, primo=5)
    assert attese == [5, 7, 7, 7, 7] and len(controlli) == 2, "subito dopo la partenza, poi al massimo ogni `ogni` secondi"
    aggiornamenti.imposta_automatico(False); controlli.clear(); attese.clear()
    p.ciclo(Fermo(3))
    assert controlli == [] and attese == [5, 3600, 3600, 3600], "spento: non controlla, ma rilegge la scelta"


def test_impostazione_del_controllo_automatico(tmp_path):
    assert aggiornamenti.automatico() is True
    assert aggiornamenti.imposta_automatico(False) is False and aggiornamenti.automatico() is False
    f = os.path.join(os.environ["IMPAGINATORE_DATI"], "aggiornamenti.json")
    with open(f, encoding="utf-8") as h: assert json.load(h) == {"formato": 1, "automatico": False}
    for v in ("no", 0, None):
        with pytest.raises(ValueError, match="vero o falso"): aggiornamenti.imposta_automatico(v)
    for testo in ("rotto", "[]", '{"automatico": 0}'):
        with open(f, "w", encoding="utf-8") as h: h.write(testo)
        assert aggiornamenti.automatico() is True, "un file strano vale «sì»"
    assert aggiornamenti.imposta_automatico(True) is True and aggiornamenti.automatico() is True
    controlli = []
    a = types.SimpleNamespace(controlla=lambda: controlli.append(1))
    class Fermo:
        n = 0
        def wait(self, t): self.n += 1; return self.n > 1
    aggiornamenti.Aggiornamenti.ciclo(a, Fermo()); assert controlli == [1, 1]
    aggiornamenti.imposta_automatico(False)
    aggiornamenti.Aggiornamenti.ciclo(a, Fermo()); assert controlli == [1, 1], "spento: niente controlli (anche con git)"


def test_rifiutato_ha_testo_e_chiave():
    e = Rifiutato("sistema.agg_rete", dettaglio="HTTP 500")
    assert isinstance(e, ValueError) and str(e) == "Non riesco a raggiungere il server degli aggiornamenti (HTTP 500)" and e.chiave == "sistema.agg_rete"
    assert lingua.t("sistema.agg_rete", "en", dettaglio="x") == "Can't reach the update server (x)"


def test_ogni_rifiuto_passa_i_parametri_del_testo():
    """Rifiutato("chiave", …) passa tutti i parametri che il testo chiede (come t() in test_lingua)"""
    import ast
    t = lingua.tabella("it"); errori = []
    cartella = os.path.dirname(firmati.__file__)
    for n in sorted(os.listdir(cartella)):
        if not n.endswith(".py"): continue
        with open(os.path.join(cartella, n), encoding="utf-8") as f: albero = ast.parse(f.read())
        for c in ast.walk(albero):
            if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "Rifiutato" and c.args and isinstance(c.args[0], ast.Constant):
                chiesti = set(re.findall(r"\{(\w+)\}", t[c.args[0].value])); dati = {k.arg for k in c.keywords}
                if chiesti != dati: errori.append((n, c.lineno, c.args[0].value))
    assert errori == []


# ---------------------------------------------------------------- strumento di chi pubblica
def test_strumento_della_release(tmp_path):
    """strumenti/aggiornamento.py: chiave dei rilasci, firma di una wheel, verifica, release finta"""
    s = os.path.join(RADICE, "strumenti", "aggiornamento.py"); env = dict(os.environ, IMPAGINATORE_NEGOZIO_DIR=str(tmp_path / "negozio"))
    def esegui(*a): return subprocess.run([sys.executable, s, *a], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    r = esegui("genera-coppia"); assert r.returncode == 0, r.stderr
    pub = re.search(r'CHIAVI_FIDATE = \{1: "([0-9a-f]{64})"\}', r.stdout).group(1)
    assert oct(os.stat(tmp_path / "negozio" / "aggiornamenti-privata-1.hex").st_mode & 0o777) == "0o600" or os.name == "nt"
    assert esegui("genera-coppia").returncode == 1, "una sola chiave per id"
    from aiuti_aggiornamenti import pacchetto
    pk = pacchetto(str(tmp_path / "dist"))
    r = esegui("firma", pk, "--novita-it", "Più veloce", "--novita-en", "Faster"); assert r.returncode == 0, r.stderr
    assert "manifesto.json.sig" in r.stdout and "v2.0.1" in r.stdout
    with open(tmp_path / "dist" / "manifesto.json", encoding="utf-8") as f: m = json.load(f)
    assert m["versione"] == "2.0.1" and m["novita"] == {"it": ["Più veloce"], "en": ["Faster"]} and set(m["file"]) == {"impaginatore/__init__.py", "impaginatore/sotto/modulo.py"}
    r = esegui("verifica", str(tmp_path / "dist"), "--pubblica", pub); assert r.returncode == 0 and "valide" in r.stdout, r.stderr
    r = esegui("verifica", str(tmp_path / "dist"), "--pubblica", PUB); assert r.returncode != 0 and "firma valida" in r.stderr
    r = esegui("firma", pk, "--id", "2"); assert r.returncode != 0 and "genera-coppia" in r.stderr
    r = subprocess.run([sys.executable, s, "genera-coppia", "--dir", RADICE], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode != 0 and "dentro il repository" in r.stderr
    # T-302: i pacchetti del programma compilato nello stesso manifesto, ognuno con misura e impronta
    (tmp_path / "dist" / "Impaginatore-2.0.1-linux.deb").write_bytes(b"deb"); (tmp_path / "dist" / "Impaginatore-2.0.1-windows.exe").write_bytes(b"exe!")
    r = esegui("firma", pk, "--compilato", f"linux={tmp_path / 'dist' / 'Impaginatore-2.0.1-linux.deb'}", "--compilato", f"windows={tmp_path / 'dist' / 'Impaginatore-2.0.1-windows.exe'}")
    assert r.returncode == 0 and "Impaginatore-2.0.1-linux.deb, Impaginatore-2.0.1-windows.exe" in r.stdout, r.stderr
    with open(tmp_path / "dist" / "manifesto.json", encoding="utf-8") as f: m = json.load(f)
    assert m["pacchetti"]["windows"] == dict(nome="Impaginatore-2.0.1-windows.exe", dimensione=4, sha256=hashlib.sha256(b"exe!").hexdigest()) and set(m["pacchetti"]) == {"python", "linux", "windows"}
    r = esegui("verifica", str(tmp_path / "dist"), "--pubblica", pub); assert r.returncode == 0 and "pacchetti linux, python, windows" in r.stdout, r.stderr
    (tmp_path / "dist" / "Impaginatore-2.0.1-linux.deb").write_bytes(b"altro")
    r = esegui("verifica", str(tmp_path / "dist"), "--pubblica", pub); assert r.returncode != 0 and "(linux) non è quello del manifesto" in r.stderr
    r = esegui("firma", pk, "--compilato", "android=x.apk"); assert r.returncode != 0 and "--compilato vuole chiave=file" in r.stderr
    r = esegui("finta", str(tmp_path / "finta"), "--versione", "2.0.3", "--seme", SEME.hex()); assert r.returncode == 0, r.stderr
    p = firmati.PacchettiFirmati(sorgenti.SorgenteFinta(tmp_path / "finta"), installazione.InstallazionePython(prova=lambda r, v: None), chiavi={0: PUB})
    assert p.controlla()["ultima"]["n"] == "2.0.3" and p.stato()["novita"] == ["Versione di prova 2.0.3"]


def test_manifesto_di_un_pacchetto_storto(tmp_path):
    from aiuti_aggiornamenti import pacchetto
    for file in ({"impaginatore/../x.py": b""}, {"impaginatore/.x": b""}):
        with pytest.raises(ValueError, match="non ammesso"): rilascio.manifesto(pacchetto(str(tmp_path / str(len(os.listdir(tmp_path)))), file=file))
    import zipfile
    p = str(tmp_path / "v.whl")
    with zipfile.ZipFile(p, "w") as z: z.writestr("impaginatore/__init__.py", "__version__ = 'due'\n")
    with pytest.raises(ValueError, match="__version__"): rilascio.manifesto(p)
    with pytest.raises(ValueError, match="versione non valida"): rilascio.pacchetto_da_sorgente(str(tmp_path), "2.x", str(tmp_path))


def test_pacchetto_senza_file_compilati(tmp_path):
    src = tmp_path / "src"; (src / "__pycache__").mkdir(parents=True)
    (src / "__init__.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8"); (src / "vecchio.pyc").write_bytes(b"x"); (src / "__pycache__" / "a.pyc").write_bytes(b"x")
    import zipfile
    with zipfile.ZipFile(rilascio.pacchetto_da_sorgente(str(src), "2.0.4", str(tmp_path / "out"))) as z:
        assert z.namelist() == ["impaginatore/__init__.py", "impaginatore-2.0.4.dist-info/METADATA"] and b'"2.0.4"' in z.read("impaginatore/__init__.py")


def test_pacchetto_dal_codice_sorgente(tmp_path):
    """la wheel di prova ha tutto il pacchetto (senza __pycache__) con la versione cambiata: il manifesto la accetta"""
    from aiuti_aggiornamenti import SRC
    pk = rilascio.pacchetto_da_sorgente(SRC, "2.0.1", str(tmp_path))
    m = json.loads(rilascio.manifesto(pk))
    assert m["versione"] == "2.0.1" and "impaginatore/aggiornamenti/firmati.py" in m["file"] and not any("__pycache__" in n or n.endswith(".pyc") for n in m["file"])
    assert "impaginatore/risorse/avvio.html" in m["file"] and len(m["file"]) < firmati.MAX_FILE
    assert ambiente_senza_coverage({"COVERAGE_PROCESS_START": "x", "A": "1"}) == {"A": "1"}
