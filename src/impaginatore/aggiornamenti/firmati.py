"""Aggiornamenti da pacchetti con un manifesto firmato Ed25519 (T-207, SEC-007).

Una release (come si pubblica: docs/architettura/AGGIORNAMENTI.md) ha tre file:
    manifesto.json       {"formato": 1, "prodotto": "impaginatore", "id_firma": 1, "versione": "2.0.1", "data": "2026-12-01",
                          "novita": {"it": [...], "en": [...]}, "python_minimo": "3.11",
                          "pacchetti": {"python": {"nome": "impaginatore-2.0.1-py3-none-any.whl", "dimensione": n, "sha256": "…"}},
                          "file": {"impaginatore/__init__.py": "<sha256>", …}}
    manifesto.json.sig   firma Ed25519 (128 cifre esadecimali) di DOMINIO + i byte esatti di manifesto.json
    il pacchetto         la wheel del programma (pacchetti.python); per il programma compilato, un pacchetto per sistema

Passi (PacchettiFirmati):
1. controlla   la sorgente dice qual è l'ultima release; si leggono manifesto e firma (piccoli, con un limite) e la firma si
               verifica con le chiavi pubbliche del programma (CHIAVI_FIDATE: la privata non entra mai nel repository).
               Firma sbagliata o campi che non tornano: il manifesto si scarta e lo stato dice perché. Una versione non
               strettamente più nuova di quella in uso, o di un'altra versione maggiore, non si propone. Mai scaricare il
               pacchetto da soli
2. aggiorna    solo su richiesta dell'utente dalla pagina (gettone): si scarica il pacchetto (limite = la misura firmata),
               si controllano misura e sha256 del manifesto, poi l'installazione (installazione.py) estrae solo i file
               elencati, ognuno con il suo sha256, prova ad avviarli e cambia il puntatore in un colpo; poi riavvia().
               Un'installazione «manuale» (il programma compilato) apre invece la pagina della release e basta
3. ripristina  torna alla versione precedente (resta installata accanto) e riavvia
Il controllo automatico (all'avvio, poi al massimo una volta al giorno) si spegne dalla schermata (aggiornamenti.automatico).
"""
import hashlib
import json
import logging
import os
import re
import secrets
import sys
import threading
import time

from .. import __version__, ed25519, lingua
from . import Aggiornamenti, Rifiutato, automatico, lanciatore, sorgenti

DOMINIO = b"IMPAGINATORE-AGGIORNAMENTO-v1\x00"
MANIFESTO, FIRMA = "manifesto.json", "manifesto.json.sig"
MAX_MANIFESTO = 1 << 20
MAX_FIRMA = 1024
MAX_PACCHETTO = 256 << 20
MAX_FILE = 5000
MAX_NOVITA, MAX_RIGA = 30, 300
GIORNO = 24 * 3600
ANNUNCIO = "annuncio.json"
FILE_PROVA = "chiave-prova.txt"         # chiave pubblica di prova accanto a una sorgente finta (solo versioni di sviluppo)

# ---------------------------------------------------------------------------------------------------------------------
# SEGNAPOSTO DA SOSTITUIRE AL RILASCIO, come per le licenze (licenze/chiave.py). Al posto del testo va la chiave pubblica
# Ed25519 dei rilasci, 64 cifre esadecimali (strumenti/aggiornamento.py genera-coppia). La chiave PRIVATA non entra mai
# nel repository. Con il segnaposto nessun manifesto è valido. Un rilascio con il segnaposto non passa i test:
# tests/test_aggiornamenti_firmati.py::test_un_rilascio_non_parte_con_il_segnaposto (vedi AGGIORNAMENTI.md).
SEGNAPOSTO = "SEGNAPOSTO-CHIAVE-PUBBLICA-DEGLI-AGGIORNAMENTI-DA-SOSTITUIRE-AL-RILASCIO"
CHIAVI_FIDATE = {1: SEGNAPOSTO}
# ---------------------------------------------------------------------------------------------------------------------

_ESA64 = re.compile(r"[0-9a-f]{64}")
_PEZZO = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}")
_RISERVATI = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(10)} | {f"lpt{i}" for i in range(10)}      # nomi che Windows non sa scrivere
log = logging.getLogger("impaginatore.aggiornamenti")


def pubblica(esadecimale):
    """32 byte della chiave pubblica, o None (segnaposto o testo non valido)"""
    try: b = bytes.fromhex(esadecimale) if isinstance(esadecimale, str) else b""
    except ValueError: return None
    return b if len(b) == 32 else None


def problemi_per_il_rilascio(chiavi=None):
    """motivi per cui queste chiavi non vanno in un rilascio (vuoto = pronte)"""
    chiavi = CHIAVI_FIDATE if chiavi is None else chiavi
    if not chiavi: return ["nessuna chiave pubblica degli aggiornamenti"]                       # non tradotto: lo legge chi prepara il rilascio
    return [f"la chiave degli aggiornamenti {i} è un segnaposto o non è valida" for i, k in sorted(chiavi.items()) if pubblica(k) is None]          # non tradotto: lo legge chi prepara il rilascio


def chiavi_con_prova(sorgente, chiavi=None):
    """chiavi fidate più quella di prova accanto alla sorgente finta (id 0): solo in una versione di sviluppo da sorgente,
    mai in un rilascio né nel programma compilato. Serve a provare a mano tutto il giro (AGGIORNAMENTI.md)"""
    chiavi = dict(CHIAVI_FIDATE if chiavi is None else chiavi)
    if getattr(sys, "frozen", False) or not lanciatore.di_sviluppo(__version__): return chiavi
    try:
        with open(os.path.join(sorgente.cartella, FILE_PROVA), encoding="utf-8") as f: k = f.read(200).strip()
    except OSError: return chiavi
    if pubblica(k): chiavi[0] = k
    return chiavi


def percorso_valido(n):
    """nome di un file del pacchetto: relativo, con «/», sotto impaginatore/, pezzi semplici (niente «..», nascosti, riservati)"""
    if not isinstance(n, str) or len(n) > 300: return False
    pezzi = n.split("/")
    return len(pezzi) >= 2 and pezzi[0] == "impaginatore" and all(_PEZZO.fullmatch(p) and p.split(".")[0].lower() not in _RISERVATI for p in pezzi)


def _testi(x):
    return isinstance(x, list) and len(x) <= MAX_NOVITA and all(isinstance(r, str) and len(r) <= MAX_RIGA for r in x)


def controlla_campi(m):
    """il manifesto (già firmato) ha la forma giusta? Rifiutato con il campo che non va"""
    def no(campo): raise Rifiutato("sistema.agg_manifesto_non_valido", campo=campo)
    if not isinstance(m, dict) or m.get("formato") != 1: no("formato")
    if m.get("prodotto") != "impaginatore": no("prodotto")
    if not lanciatore.valida(m.get("versione")): no("versione")
    if not isinstance(m.get("data"), str) or len(m["data"]) > 40: no("data")
    nv = m.get("novita")
    if not isinstance(nv, dict) or not all(isinstance(k, str) and re.fullmatch(r"[a-z]{2}", k) and _testi(v) for k, v in nv.items()): no("novita")
    if not isinstance(m.get("python_minimo"), str) or not re.fullmatch(r"3\.\d{1,2}", m["python_minimo"]): no("python_minimo")
    pk = m.get("pacchetti")
    if not isinstance(pk, dict) or not pk: no("pacchetti")
    for k, p in pk.items():
        if not (isinstance(p, dict) and isinstance(p.get("nome"), str) and sorgenti._NOME.fullmatch(p["nome"]) and type(p.get("dimensione")) is int
                and 0 < p["dimensione"] <= MAX_PACCHETTO and isinstance(p.get("sha256"), str) and _ESA64.fullmatch(p["sha256"])): no(f"pacchetti.{str(k)[:20]}")
    f = m.get("file")
    if not isinstance(f, dict) or not 0 < len(f) <= MAX_FILE or "impaginatore/__init__.py" not in f: no("file")
    for n, h in f.items():
        if not percorso_valido(n) or not (isinstance(h, str) and _ESA64.fullmatch(h)): no("file")
    return m


def verifica(dati, firma, chiavi=None):
    """manifesto (dict) se `firma` (testo esadecimale) è una firma valida di DOMINIO + dati per la chiave id_firma; Rifiutato altrimenti"""
    chiavi = CHIAVI_FIDATE if chiavi is None else chiavi
    if not isinstance(dati, bytes) or len(dati) > MAX_MANIFESTO: raise Rifiutato("sistema.agg_troppo_grande")
    try: f = bytes.fromhex(firma.decode("ascii").strip() if isinstance(firma, bytes) else str(firma).strip())
    except (UnicodeDecodeError, ValueError): f = b""
    try: m = json.loads(dati.decode("utf-8"))
    except (UnicodeDecodeError, ValueError): raise Rifiutato("sistema.agg_manifesto_non_valido", campo="json") from None
    idf = m.get("id_firma") if isinstance(m, dict) else None
    pub = pubblica(chiavi.get(idf)) if type(idf) is int else None
    if pub is None or not ed25519.verifica(pub, DOMINIO + dati, f): raise Rifiutato("sistema.agg_firma_non_valida")
    return controlla_campi(m)


def sha256_file(percorso):
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""): h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- annuncio dopo il riavvio
def _file_annuncio():
    return os.path.join(lanciatore.cartella(), ANNUNCIO)


def scrivi_annuncio(tipo, versione):
    """«Aggiornato alla versione X» / «Tornato alla versione X»: lo legge il programma riavviato (una volta)"""
    os.makedirs(lanciatore.cartella(), exist_ok=True)
    with open(_file_annuncio(), "w", encoding="utf-8") as f: json.dump(dict(tipo=tipo, versione=versione, id=secrets.token_hex(6)), f)


def prendi_annuncio():
    """l'annuncio per la versione in uso (e lo toglie: vale per un avvio), o None"""
    try:
        with open(_file_annuncio(), "rb") as f: testo = f.read(4096)
        os.remove(_file_annuncio())
        a = json.loads(testo.decode("utf-8"))
    except (OSError, ValueError): return None
    ok = isinstance(a, dict) and a.get("tipo") in ("aggiornato", "tornato") and a.get("versione") == __version__ and isinstance(a.get("id"), str)
    return dict(tipo=a["tipo"], versione=a["versione"], id=a["id"][:20]) if ok else None


class PacchettiFirmati(Aggiornamenti):
    """aggiornamenti da una Sorgente (sorgenti.py), installati da una Installazione (installazione.py)"""

    def __init__(self, sorgente, installazione, riavvia=None, chiavi=None):
        self.sorgente, self.installazione = sorgente, installazione
        self.riavvia = riavvia or (lambda: None)
        self.chiavi = dict(CHIAVI_FIDATE if chiavi is None else chiavi)
        self.agg = dict(da_aggiornare=False, novita=[], controllato=0, errore="", ultima=None, scartata=False)
        self.nuovo, self.asset = None, {}                        # manifesto verificato della versione nuova e file della sua release
        self.annuncio = prendi_annuncio()
        self._lock = threading.Lock()

    def motivo(self):
        """perché questa installazione non si aggiorna da sola (nella lingua in uso), o None"""
        if not self.installazione.disponibile: return lingua.t(self.installazione.motivo)
        if not self.sorgente.configurata: return lingua.t("sistema.agg_canale_non_configurato")
        return None

    def _info(self, v, m=None):
        return dict(n=v, codice="", data=(m or {}).get("data", ""), titolo=lingua.t("sistema.agg_versione_firmata"), rel="")

    def stato(self):
        s = dict(self.agg, disponibile=True, motivo=None, attuale=dict(self._info(__version__), titolo=lingua.t("sistema.agg_versione_installata")),
                 precedente=self.installazione.precedente(), annuncio=self.annuncio, manuale=self.installazione.manuale)
        if self.nuovo: s["novita"] = self._novita(self.nuovo)       # nella lingua in uso, anche se è cambiata dopo il controllo
        m = self.motivo()
        if m: s.update(disponibile=False, motivo=m, da_aggiornare=False)
        return s

    def _novita(self, m):
        nv = m["novita"]
        return list(nv.get(lingua.attuale()) or nv.get("en") or nv.get("it") or [])

    def controlla(self):
        if self.motivo(): return self.stato()
        try:
            r = self.sorgente.ultimo()
            m = self._manifesto(r) if r else None
            v = m["versione"] if m else None
            nuova = bool(v) and lanciatore.piu_nuova(v, __version__) and lanciatore.maggiore(v) == lanciatore.maggiore(__version__)
            if m and not nuova: log.info("versione pubblicata %s: niente di nuovo per la %s", v, __version__)
            self.nuovo, self.asset = (m, r.asset) if nuova else (None, {})
            self.agg.update(da_aggiornare=nuova, novita=self._novita(m) if nuova else [], ultima=self._info(v, m) if nuova else None, scartata=nuova and v == (lanciatore.leggi() or {}).get("scartata"),
                            controllato=time.time(), errore="")
        except (ValueError, OSError) as e:                       # Rifiutato (rete, firma, manifesto) o disco: il programma va avanti
            log.warning("controllo degli aggiornamenti non riuscito: %s", e)
            self.nuovo, self.asset = None, {}
            self.agg.update(da_aggiornare=False, ultima=None, novita=[], errore=str(e)[:300], controllato=time.time())
        return self.stato()

    def _manifesto(self, r):
        """manifesto verificato della release r (Rifiutato se mancano i file o la firma non va)"""
        a, s = r.asset.get(MANIFESTO), r.asset.get(FIRMA)
        if not a or not s: raise Rifiutato("sistema.agg_release_incompleta")
        return verifica(self.sorgente.leggi(a, MAX_MANIFESTO), self.sorgente.leggi(s, MAX_FIRMA), self.chiavi)

    def versioni(self, k=20):
        out = [dict(n=__version__, codice=__version__, data="", titolo=lingua.t("sistema.agg_versione_installata"), attuale=True)]
        p = self.installazione.precedente()
        if p: out.append(dict(n=p, codice=p, data="", titolo=lingua.t("sistema.agg_versione_precedente"), attuale=False))
        return out[:k]

    def aggiorna(self):
        m = self.motivo()
        if m: raise ValueError(m)
        if not self._lock.acquire(blocking=False): raise Rifiutato("sistema.agg_in_corso")
        try:
            if not self.nuovo: self.controlla()
            if not self.nuovo: raise Rifiutato("sistema.agg_nessuna_nuova")
            if self.installazione.manuale: return self.installazione.a_mano(self.nuovo, self.sorgente)        # programma compilato: la pagina dei download, nessun riavvio
            self._installa(self.nuovo)
        finally: self._lock.release()
        self.riavvia()
        return True

    def _installa(self, m):
        if not lanciatore.piu_nuova(m["versione"], __version__): raise Rifiutato("sistema.agg_nessuna_nuova")          # mai indietro (anche se controlla() cambiasse)
        if tuple(sys.version_info[:2]) < tuple(int(x) for x in m["python_minimo"].split(".")): raise Rifiutato("sistema.agg_python_vecchio", versione=m["python_minimo"])
        p = m["pacchetti"].get(self.installazione.pacchetto)
        a = self.asset.get(p["nome"]) if p else None
        if not a: raise Rifiutato("sistema.agg_release_incompleta")
        if a.digest and a.digest.startswith("sha256:") and a.digest[7:].lower() != p["sha256"]: raise Rifiutato("sistema.agg_pacchetto_diverso")     # GitHub dice già che non è quello firmato
        cartella = os.path.join(lanciatore.cartella(), "scarichi"); os.makedirs(cartella, exist_ok=True)
        for vecchio in os.listdir(cartella):                    # resti di uno scaricamento interrotto (programma chiuso a metà)
            try: os.remove(os.path.join(cartella, vecchio))
            except OSError as e: log.debug("scaricamento vecchio non tolto: %s", e)
        dest = os.path.join(cartella, f"{secrets.token_hex(6)}-{p['nome']}")
        try:
            n = self.sorgente.scarica(a, dest, p["dimensione"])
            if n != p["dimensione"] or sha256_file(dest) != p["sha256"]: raise Rifiutato("sistema.agg_pacchetto_diverso")
            self.installazione.installa(m, dest)
        finally:
            try: os.remove(dest)
            except OSError: pass  # nosec B110  # scaricamento non partito: non c'è niente da togliere
        scrivi_annuncio("aggiornato", m["versione"])
        self.nuovo = None

    def ripristina(self, codice):
        if not self.installazione.disponibile: raise Rifiutato(self.installazione.motivo)       # senza canale configurato si torna indietro lo stesso
        self.installazione.torna(codice)
        scrivi_annuncio("tornato", codice)
        self.riavvia()
        return dict(n=codice, caricato=True)

    def ciclo(self, fermo, ogni=GIORNO, passo=3600, primo=5):
        """controllo all'avvio (dopo `primo` secondi, per non rallentare la partenza) e poi al massimo ogni `ogni`
        secondi, se l'utente non l'ha spento; la scelta si rilegge ogni `passo` secondi"""
        if self.motivo(): return
        attesa, ultimo = primo, None
        while not fermo.wait(attesa):
            attesa = passo
            if automatico() and (ultimo is None or time.time() - ultimo >= ogni):
                self.controlla(); ultimo = time.time()
