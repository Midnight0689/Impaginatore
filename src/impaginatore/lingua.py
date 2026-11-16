"""Lingua dei testi che l'utente vede (T-206): italiano e inglese, una sola tabella per le pagine e per i server.

Tabella: risorse/testi/<lingua>/<area>.json, {chiave: testo}. Ogni chiave comincia con il nome del suo file
(«editor.…» sta in editor.json) e c'è in tutte le lingue con gli stessi parametri: lo controlla tests/test_lingua.py, che
fallisce anche se una pagina o un modulo scrive un testo visibile fuori dalla tabella.

    t("server.foto_mancanti", n=2, nomi="A, B")        parametri nominati, «{n}» nel testo; i numeri secondo la lingua
    tn("licenze.giorni", 3)                            plurale: «licenze.giorni_1» se n è 1, altrimenti «licenze.giorni_n»
    num(22.5) -> «22,5» / «22.5»     data(ts) -> «16/11/2026»     ora(ts) -> «10:42»     elenco(["Pro", "Studio"]) -> «Pro e Studio»

Lingua in uso (attuale()): quella scelta dall'utente nella schermata Album, salvata in <dati dell'utente>/preferenze.json;
finché non c'è, quella del sistema (italiano se il sistema parla italiano, altrimenti inglese; italiano se il sistema non
lo dice). La schermata la salva al primo avvio (prima_volta()), così resta quella anche se il sistema cambia. La variabile
IMPAGINATORE_LINGUA prende il posto della lingua del sistema (prove, sviluppo). Ogni processo (schermata, editor, server
MCP) rilegge il file quando cambia: una scelta nuova vale per i messaggi successivi e per le pagine che si riaprono.
"""
import datetime as dt
import json
import logging
import os
import re
import threading

from . import risorse
from .piattaforma import cartelle
from .piattaforma import lingua as lingua_sistema

log = logging.getLogger("impaginatore")

LINGUE = {"it": "Italiano", "en": "English"}          # nome di ogni lingua nella lingua stessa (il selettore li mostra così)
PREDEFINITA = "it"
LOCALI = {"it": "it-IT", "en": "en-GB"}                # per Intl nelle pagine: inglese britannico (date 16/11/2026, 24 ore), come i documenti legali
FILE = "preferenze.json"
SEGNAPOSTO = re.compile(r"\{(\w+)\}")

_LOCK = threading.Lock()
_TABELLE = {}
_SCELTA = {"firma": None, "lingua": None}


# ---------------------------------------------------------------- tabella
def tabella(lingua):
    """tutti i testi di una lingua: {chiave: testo} (letti una volta per processo)"""
    with _LOCK:
        if lingua not in _TABELLE: _TABELLE[lingua] = risorse.testi(lingua)
        return _TABELLE[lingua]


def _formatta(v, lingua):
    if isinstance(v, bool) or not isinstance(v, (int, float)): return str(v)
    return num(v, lingua=lingua)


def t(chiave, lingua=None, **param):
    """testo della chiave nella lingua (di serie quella in uso), con i parametri al loro posto. Una chiave che manca
    restituisce la chiave stessa e va nel registro (i test controllano che non succeda)"""
    lingua = lingua or attuale()
    s = tabella(lingua).get(chiave)
    if s is None:
        log.error("testo mancante: %s (%s)", chiave, lingua); return chiave
    if not param: return s
    return SEGNAPOSTO.sub(lambda m: _formatta(param[m.group(1)], lingua) if m.group(1) in param else m.group(0), s)


def tn(chiave, n, lingua=None, **param):
    """plurale: chiave_1 per n == 1, chiave_n per gli altri; n arriva anche come parametro"""
    return t(f"{chiave}_{'1' if n == 1 else 'n'}", lingua, n=n, **param)


# ---------------------------------------------------------------- numeri, date, elenchi
def num(v, decimali=2, fissi=False, lingua=None):
    """numero per l'utente: virgola decimale in italiano, punto in inglese; le migliaia si separano da 10.000 in italiano
    e da 1,000 in inglese (come Intl nelle pagine). fissi=True tiene gli zeri finali («3,0»)"""
    lingua = lingua or attuale()
    s = f"{v:,.{decimali if isinstance(v, float) or fissi else 0}f}"
    if "." in s and not fissi: s = s.rstrip("0").rstrip(".")
    if abs(v) < (10000 if lingua == "it" else 1000): s = s.replace(",", "")
    if s in ("-0", "-0.0"): s = s[1:]
    return s.translate(str.maketrans(",.", ".,")) if lingua == "it" else s


def data(ts):
    """giorno di un istante (secondi), «16/11/2026» in tutte e due le lingue (inglese britannico)"""
    return dt.datetime.fromtimestamp(ts).strftime("%d/%m/%Y")


def ora(ts):
    """ora di un istante (secondi), «10:42» (24 ore in tutte e due le lingue)"""
    return dt.datetime.fromtimestamp(ts).strftime("%H:%M")


def elenco(voci, lingua=None):
    """«A, B e C» / «A, B and C»"""
    voci = [str(v) for v in voci]
    if len(voci) < 2: return "".join(voci)
    return t("comune.elenco", lingua, primi=", ".join(voci[:-1]), ultimo=voci[-1])


# ---------------------------------------------------------------- lingua in uso
def da_codice(codice):
    """«it_IT», «it-CH», «IT» -> «it»; ogni altra lingua conosciuta o no -> «en»; niente -> None"""
    c = (codice or "").strip().lower().replace("-", "_")
    if not c: return None
    return "it" if c.split("_")[0] == "it" else "en"


def di_sistema():
    """lingua per un utente che non ha ancora scelto: IMPAGINATORE_LINGUA, poi il sistema, poi l'italiano"""
    return da_codice(os.environ.get("IMPAGINATORE_LINGUA")) or da_codice(lingua_sistema.del_sistema()) or PREDEFINITA


def percorso():
    return os.path.join(cartelle.dati_utente(), FILE)


def _leggi_preferenze():
    try:
        with open(percorso(), encoding="utf-8") as f: d = json.load(f)
    except FileNotFoundError: return {}
    except (OSError, ValueError) as e:
        log.warning("preferenze illeggibili (%s): lingua del sistema", type(e).__name__); return {}
    return d if isinstance(d, dict) else {}


def scelta():
    """lingua salvata nelle preferenze, o None. Il file si rilegge solo quando cambia (un altro processo l'ha scritto)"""
    try: st = os.stat(percorso()); firma = (st.st_ino, st.st_mtime_ns, st.st_size)          # imposta() sostituisce il file: inode nuovo
    except OSError: firma = None
    with _LOCK: vista, v = firma is not None and firma == _SCELTA["firma"], _SCELTA["lingua"]
    if vista: return v
    v = _leggi_preferenze().get("lingua") if firma else None
    v = v if v in LINGUE else None
    with _LOCK: _SCELTA.update(firma=firma, lingua=v)
    return v


def attuale():
    """lingua in uso: scelta dell'utente, altrimenti quella del sistema"""
    return scelta() or di_sistema()


def imposta(lingua):
    """salva la scelta dell'utente (dalla schermata Album). ValueError se la lingua non c'è"""
    if lingua not in LINGUE: raise ValueError(t("comune.lingua_sconosciuta"))
    d = _leggi_preferenze(); d.update(formato=1, lingua=lingua)
    os.makedirs(os.path.dirname(percorso()), exist_ok=True)
    tmp = percorso() + f".{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(d, f)
    os.replace(tmp, percorso())
    log.info("lingua: %s", lingua)


def prima_volta():
    """al primo avvio della schermata: salva la lingua del sistema, così resta quella. Un errore non ferma niente"""
    if scelta(): return
    try: imposta(di_sistema())
    except OSError as e: log.warning("lingua non salvata: %s", e.strerror)


def per_pagina():
    """lingua in uso, codice per Intl e tabella delle lingue: quello che il server mette nelle pagine"""
    lingua = attuale()
    return lingua, LOCALI[lingua]
