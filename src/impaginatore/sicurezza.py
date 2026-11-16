"""Protezione dei due server locali (schermata dei progetti ed editor) e dei client che li chiamano.

Ogni server ha un gettone di sessione casuale (secrets) e lo chiede a OGNI richiesta:
- le fetch della pagina e i client locali lo mandano nell'intestazione X-Impaginatore-Gettone;
- la pagina e le immagini (che non possono mandare intestazioni) usano il cookie «impaginatore_<porta>» (HttpOnly,
  SameSite=Strict). Il suo valore NON è il gettone ma un segreto derivato (valore_cookie), perché il browser manda i
  cookie di 127.0.0.1 a ogni porta, anche al server di un altro programma (VER-006): con il cookie si hanno la pagina
  (che non contiene il gettone) e le immagini, mai le API.
- l'URL di avvio monouso http://127.0.0.1:<porta>/avvio?c=<codice> (vale una volta sola e per DURATA_CODICE secondi)
  imposta il cookie e consegna il gettone alla scheda, che lo tiene in sessionStorage (pagina_avvio).
Il gettone non passa mai dalla riga di comando: un server che si riavvia da solo (os.execv, aggiornamento) lo ritrova
nella variabile d'ambiente VARIABILE; gli altri processi figli non la ricevono (piattaforma.processi.ambiente_figli).

Client locali fidati (l'altro server, il futuro server MCP; stessa macchina e stesso utente): ogni server in funzione
scrive <dati dell'utente>/sessioni/<tipo>-<porta>.json (cartella 0700, file 0600) con porta, gettone, pid e progetto.
Il progetto completo, con le alternative scartate, è in docs/architettura/SICUREZZA.md.
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
import urllib.request

INTESTAZIONE = "X-Impaginatore-Gettone"
VARIABILE = "IMPAGINATORE_GETTONE"
MAX_CORPO = 4 * 1024 * 1024                  # corpo massimo di una richiesta (byte): il più grande legittimo è un elenco di percorsi
DURATA_CODICE = 120                          # secondi di validità di un URL di avvio
TIPI = ("home", "editor")

log = logging.getLogger("impaginatore.sicurezza")

# intestazioni su tutte le risposte; la CSP (con il nonce dello script della pagina) solo sulle pagine HTML
INTESTAZIONI = (("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"), ("Cross-Origin-Resource-Policy", "same-origin"),
                ("Cross-Origin-Opener-Policy", "same-origin"), ("X-Frame-Options", "DENY"), ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"))


def csp(nonce=None):
    """Content-Security-Policy delle pagine: solo lo script con il nonce di questa risposta; stili in linea ammessi
    (attributi style="..." ovunque nell'interfaccia: vedi SICUREZZA.md, passo successivo)"""
    script = f"'nonce-{nonce}'" if nonce else "'none'"
    return (f"default-src 'none'; script-src {script}; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; font-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def nuovo_gettone():
    return secrets.token_urlsafe(32)


def uguali(a, b):
    """confronto a tempo costante (False se uno dei due non è una stringa o è vuoto)"""
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b: return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def nome_cookie(porta):
    """i cookie non distinguono le porte: ogni server ha il suo nome"""
    return f"impaginatore_{porta}"


def valore_cookie(gettone, porta):
    """valore del cookie della pagina: HMAC del gettone, diverso per ogni porta. Chi lo riceve (ogni server di 127.0.0.1
    che il browser visita) non ne ricava il gettone (VER-006)"""
    return hmac.new(gettone.encode("utf-8"), f"impaginatore-pagina:{int(porta)}".encode("ascii"), hashlib.sha256).hexdigest()


CHIAVE_SESSIONE = "impaginatore_gettone"         # chiave di sessionStorage dove la pagina tiene il gettone delle API


def pagina_avvio(gettone, nonce):
    """pagina che l'URL di avvio restituisce una volta sola: lascia il gettone nella sessionStorage della scheda (che
    nessun server riceve) e apre la pagina vera. json.dumps con «<» protetto: il gettone resta una stringa JS"""
    g = json.dumps(gettone).replace("<", "\\u003c")
    return ("<!doctype html><html lang=\"it\"><head><meta charset=\"utf-8\"><title>Impaginatore</title></head><body>"
            f"<script nonce=\"{nonce}\">try {{ sessionStorage.setItem({json.dumps(CHIAVE_SESSIONE)}, {g}); }} catch (e) {{}} location.replace(\"/\");</script>"
            "</body></html>")


def gettone_del_processo():
    """gettone del server di questo processo: quello ereditato da un riavvio (VARIABILE) o uno nuovo, che resta
    nell'ambiente per i riavvii successivi"""
    g = os.environ.get(VARIABILE) or nuovo_gettone()
    os.environ[VARIABILE] = g
    return g


class Sessione:
    """gettone di un server e i suoi codici di avvio monouso"""

    def __init__(self, gettone=None):
        self.gettone = gettone or nuovo_gettone()
        self._codici = {}
        self._lock = threading.Lock()

    def _pulisci(self):
        ora = time.monotonic()
        for c in [c for c, t in self._codici.items() if t < ora]: del self._codici[c]

    def codice(self):
        """un codice di avvio nuovo (vale una volta, per DURATA_CODICE secondi)"""
        c = secrets.token_urlsafe(24)
        with self._lock:
            self._pulisci(); self._codici[c] = time.monotonic() + DURATA_CODICE
        return c

    def usa(self, codice):
        """True se il codice è valido; da quel momento non vale più"""
        with self._lock:
            self._pulisci()
            trovato = None
            for c in list(self._codici):                     # tutti confrontati a tempo costante
                if uguali(c, codice): trovato = c
            if trovato is not None: del self._codici[trovato]
        return trovato is not None


# ---------------------------------------------------------------- file di sessione (client locali fidati)
def cartella_sessioni():
    from .piattaforma import cartelle
    return os.path.join(cartelle.dati_utente(), "sessioni")


def _file(tipo, porta):
    if tipo not in TIPI: raise ValueError("tipo di server sconosciuto")
    return os.path.join(cartella_sessioni(), f"{tipo}-{int(porta)}.json")


def scrivi_sessione(tipo, porta, gettone, **info):
    """scrive il file di sessione (0600, in una cartella 0700) in modo atomico; restituisce il percorso"""
    d = cartella_sessioni()
    os.makedirs(d, mode=0o700, exist_ok=True)
    try: os.chmod(d, 0o700)
    except OSError as e: log.warning("permessi della cartella delle sessioni non impostati: %s", e.strerror)
    p = _file(tipo, porta); tmp = f"{p}.{os.getpid()}.tmp"
    dati = dict(tipo=tipo, porta=int(porta), gettone=gettone, pid=os.getpid(), creato=time.time(), **info)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(dati, f)
    os.replace(tmp, p)
    return p


def leggi_sessione(tipo, porta):
    """dati della sessione del server tipo/porta, o None"""
    try:
        with open(_file(tipo, porta), encoding="utf-8") as f: d = json.load(f)
    except (OSError, ValueError): return None
    return d if isinstance(d, dict) and isinstance(d.get("gettone"), str) else None


def gettone_di(tipo, porta):
    d = leggi_sessione(tipo, porta)
    return d["gettone"] if d else None


def sessioni(tipo):
    """[dati] delle sessioni di quel tipo presenti su disco (anche di server che non ci sono più), per porta"""
    out = []
    try: nomi = sorted(os.listdir(cartella_sessioni()))
    except OSError: return out
    for n in nomi:
        if n.startswith(tipo + "-") and n.endswith(".json") and n[len(tipo) + 1:-5].isdigit():
            d = leggi_sessione(tipo, int(n[len(tipo) + 1:-5]))
            if d: out.append(d)
    return sorted(out, key=lambda d: d["porta"])


def togli_sessione(tipo, porta, gettone):
    """toglie il file di sessione, solo se è ancora il nostro (un server nuovo sulla stessa porta l'ha già riscritto)"""
    d = leggi_sessione(tipo, porta)
    if d and uguali(d["gettone"], gettone):
        try: os.remove(_file(tipo, porta))
        except OSError as e: log.debug("file di sessione non tolto: %s", e)


# ---------------------------------------------------------------- client
# client per i server del programma, SENZA proxy: urlopen userebbe HTTP_PROXY (o il proxy di sistema) anche per 127.0.0.1
# quando NO_PROXY non lo esclude, e il gettone andrebbe al proxy. Solo http://127.0.0.1:<porta>, mai indirizzi da fuori
APRI_LOCALE = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def chiedi(porta, percorso, gettone, corpo=None, timeout=3):
    """richiesta JSON a un server locale (GET, o POST se c'è un corpo), con il gettone"""
    dati = None if corpo is None else json.dumps(corpo).encode("utf-8")
    r = urllib.request.Request(f"http://127.0.0.1:{int(porta)}{percorso}", dati, {INTESTAZIONE: gettone or "", "Content-Type": "application/json"})
    with APRI_LOCALE.open(r, timeout=timeout) as f: return json.load(f)


def indirizzo_avvio(tipo, porta, timeout=3):
    """URL di avvio monouso del server tipo/porta (chiesto al server con il gettone del suo file di sessione), o None"""
    g = gettone_di(tipo, porta)
    if not g: return None
    try: return chiedi(porta, "/api/avvio", g, {}, timeout)["indirizzo"]
    except Exception as e:                                  # server spento o sessione vecchia: lo dice il chiamante
        log.debug("URL di avvio di %s:%s non ottenuto: %s", tipo, porta, e)
        return None
