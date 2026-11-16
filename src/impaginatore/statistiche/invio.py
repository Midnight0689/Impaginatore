"""Invio delle statistiche d'uso (T-204): dove vanno i lotti di eventi e come ci arrivano.

Oggi INDIRIZZO è vuoto: destinazione() è None e il programma non fa nessuna richiesta di rete per le statistiche
(tests/test_statistiche.py lo prova). Gli eventi restano nel registro sul computer e l'utente li manda a mano con
«Esporta le statistiche…». Quando ci sarà il server (docs/architettura/STATISTICHE.md, «Il server»), si mette qui il suo
indirizzo https://… e il giro d'invio parte da solo, solo per chi ha detto sì.

Destinazione è l'interfaccia: invia(eventi) manda un lotto (elenco di eventi già scritti nel registro) e cancella(ids)
chiede al server di togliere i dati di quegli identificativi; tutte e due sollevano ErroreInvio se non riesce.
    HTTPS     la destinazione vera: POST JSON a un indirizzo https://, certificato e nome del server verificati
              (ssl.create_default_context), nessun reindirizzamento seguito, nessun cookie, nessun gettone della sessione,
              e per un indirizzo di questo computer (127.0.0.1, localhost) nessun proxy
    Cartella  la destinazione finta delle prove: ogni lotto diventa un file JSON in una cartella

giro() manda la coda (coda.jsonl, che statistiche scrive solo se c'è una destinazione) in lotti piccoli, con pochi
tentativi; quello che non parte resta per il giro dopo. Non solleva mai: la rete che non va non ferma niente.
"""
import ipaddress
import json
import os
import ssl
import time
import urllib.request
from http.client import HTTPException
from urllib.parse import urlparse

from .. import __version__

INDIRIZZO = ""                       # https://… del server delle statistiche: vuoto = nessun invio (decisione del titolare: DA-DECIDERE.md)
LOTTO_EVENTI = 50                    # eventi al massimo in un lotto
LOTTO_BYTE = 64 * 1024               # e byte al massimo (JSON)
TENTATIVI = 3                        # per lotto, in un giro
ATTESE = (5, 30)                     # secondi tra un tentativo e il successivo
TIMEOUT = 15
CODA, IN_INVIO, PROGRESSO = "coda.jsonl", "coda-invio.jsonl", "coda-invio.json"


class ErroreInvio(Exception):
    """il lotto (o la richiesta di cancellazione) non è arrivato: si riprova più tardi"""


class Destinazione:
    """dove vanno le statistiche: le sottoclassi scrivono invia e cancella"""

    def invia(self, eventi):
        raise NotImplementedError

    def cancella(self, ids):
        raise NotImplementedError


def corpo(azione, **dati):
    """byte di una richiesta al server: {"formato": 1, "azione": …, …} in JSON compatto"""
    return json.dumps(dict(formato=1, azione=azione, **dati), ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


class Cartella(Destinazione):
    """destinazione finta per le prove: ogni richiesta è un file <n>-<azione>.json nella cartella"""

    def __init__(self, cartella):
        self.cartella = cartella

    def _scrivi(self, azione, **dati):
        os.makedirs(self.cartella, exist_ok=True)
        n = len(os.listdir(self.cartella)) + 1
        with open(os.path.join(self.cartella, f"{n:04d}-{azione}.json"), "wb") as f: f.write(corpo(azione, **dati))

    def invia(self, eventi): self._scrivi("eventi", eventi=eventi)
    def cancella(self, ids): self._scrivi("cancella", ids=sorted(ids))


class _SenzaReindirizzi(urllib.request.HTTPRedirectHandler):
    """un 3xx non si segue: potrebbe portare a http:// o a un altro server"""

    def redirect_request(self, *a, **k):
        return None


def locale(host):
    """l'indirizzo è di questo computer? (localhost, 127.x, ::1)"""
    if (host or "").lower() == "localhost": return True
    try: return ipaddress.ip_address(host).is_loopback
    except ValueError: return False


class HTTPS(Destinazione):
    """POST JSON all'indirizzo https:// del server (STATISTICHE.md, «Il server»). Solo https, con il certificato e il nome
    verificati; senza reindirizzamenti, cookie né gettoni; per un indirizzo di questo computer, senza proxy (il gettone
    delle richieste locali non deve mai passare da un proxy: SICUREZZA.md). apri: per le prove"""

    def __init__(self, indirizzo, contesto=None, apri=None):
        u = urlparse(indirizzo)
        if u.scheme != "https" or not u.hostname or u.username or u.password:
            raise ValueError("indirizzo delle statistiche non valido: serve https://server/percorso")  # non tradotto: lo legge chi prepara il rilascio, non l'utente
        self.indirizzo, self.host = indirizzo, u.hostname
        self.contesto = contesto or ssl.create_default_context()                 # CERT_REQUIRED e check_hostname
        gestori = [urllib.request.HTTPSHandler(context=self.contesto), _SenzaReindirizzi()]
        if locale(u.hostname): gestori.append(urllib.request.ProxyHandler({}))
        self._apri = apri or urllib.request.build_opener(*gestori).open

    def _manda(self, dati):
        rq = urllib.request.Request(self.indirizzo, data=dati, method="POST",
                                    headers={"Content-Type": "application/json", "User-Agent": f"Impaginatore/{__version__}"})
        try:
            with self._apri(rq, timeout=TIMEOUT) as r: codice = r.status
        except (OSError, ValueError, HTTPException) as e: raise ErroreInvio(type(e).__name__) from None
        if not 200 <= codice < 300: raise ErroreInvio(f"HTTP {codice}")

    def invia(self, eventi): self._manda(corpo("eventi", eventi=eventi))
    def cancella(self, ids): self._manda(corpo("cancella", ids=sorted(ids)))


def attivo():
    """c'è un server a cui mandare le statistiche? (oggi no)"""
    return bool(INDIRIZZO)


def destinazione():
    """la destinazione degli invii, o None (oggi: INDIRIZZO vuoto, nessun invio)"""
    return HTTPS(INDIRIZZO) if attivo() else None


def lotti(righe):
    """righe (testi JSON) a gruppi di LOTTO_EVENTI e al massimo LOTTO_BYTE"""
    lotto, peso = [], 0
    for r in righe:
        if lotto and (len(lotto) >= LOTTO_EVENTI or peso + len(r) > LOTTO_BYTE): yield lotto; lotto, peso = [], 0
        lotto.append(r); peso += len(r) + 1
    if lotto: yield lotto


def _leggi_progresso(p):
    try:
        with open(p, encoding="utf-8") as f: n = json.load(f).get("inviati")
    except (OSError, ValueError, AttributeError): return 0
    return n if type(n) is int and n >= 0 else 0


def _scrivi_progresso(p, n):
    with open(p, "w", encoding="utf-8") as f: json.dump({"formato": 1, "inviati": n, "quando": round(time.time())}, f)


def _attendi(fermo, secondi):
    """pausa tra due tentativi; True se intanto `fermo` dice di smettere"""
    if fermo is not None: return fermo.wait(secondi)
    time.sleep(secondi); return False


def con_tentativi(fn, fermo=None):
    """fn() con al massimo TENTATIVI tentativi e una pausa (ATTESE) tra l'uno e l'altro, che `fermo` interrompe; True se riesce"""
    for k in range(TENTATIVI - 1):
        try: fn(); return True
        except ErroreInvio:
            if _attendi(fermo, ATTESE[min(k, len(ATTESE) - 1)]): return False
    try: fn(); return True
    except ErroreInvio: return False


def giro(dest, cartella, fermo=None):
    """un giro d'invio della coda: la coda passa in coda-invio.jsonl (gli eventi nuovi vanno in una coda nuova), che parte
    a lotti; il progresso si salva lotto per lotto, così un lotto arrivato non si rimanda. Restituisce quanti eventi sono
    partiti. Righe che non sono JSON (un file rovinato) si saltano"""
    q, inv, prog = (os.path.join(cartella, x) for x in (CODA, IN_INVIO, PROGRESSO))
    if not os.path.exists(inv):
        if not os.path.exists(q): return 0
        os.replace(q, inv); _scrivi_progresso(prog, 0)
    with open(inv, encoding="utf-8", errors="replace") as f: righe = [r for r in f.read().split("\n") if r.strip()]
    fatti = _leggi_progresso(prog); partiti = 0
    for lotto in lotti(righe[fatti:]):
        eventi = []
        for r in lotto:
            try: eventi.append(json.loads(r))
            except ValueError: pass
        if eventi and not con_tentativi(lambda: dest.invia(eventi), fermo): return partiti
        fatti += len(lotto); partiti += len(eventi); _scrivi_progresso(prog, fatti)
    os.remove(inv); os.remove(prog)
    return partiti
