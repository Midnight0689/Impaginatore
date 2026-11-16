"""Collegamento del server MCP con Impaginatore in funzione: schermata dei progetti ed editor, come client locale fidato.

Il server MCP non apre progetti per conto suo: parla con i server HTTP del programma su 127.0.0.1, con il gettone che
ognuno scrive nel suo file di sessione (<dati dell'utente>/sessioni/<tipo>-<porta>.json, cartella 0700, file 0600:
docs/architettura/SICUREZZA.md, «Come un client locale fidato ottiene il gettone»). Così le modifiche passano dagli
stessi controlli della pagina (valida, transazioni, licenza, radici) e l'utente le vede nell'editor aperto.

Regole del client (SICUREZZA.md): solo http://127.0.0.1:<porta>, nessun «Origin», JSON nelle POST, mai un proxy (il
gettone non deve uscire da 127.0.0.1 nemmeno con HTTP_PROXY impostato), il gettone non va in registri, file o argomenti.
Solo libreria standard: questo modulo non usa l'SDK MCP.
"""
import json
import logging
import os
import subprocess  # nosec B404  # il programma si avvia con argomenti in lista, mai con la shell
import sys
import time
import urllib.error
import urllib.request

from .. import lingua, sicurezza
from ..piattaforma import processi, sistema

log = logging.getLogger("impaginatore.mcp")

PORTA_PROGRAMMA = 8765            # porta della schermata dei progetti quando la avvia il server MCP (la stessa del programma)
MAX_RISPOSTA = 64 * 2**20         # byte al massimo letti da una risposta (lo stato di un album con migliaia di foto sta sotto)
ATTESA_AVVIO = 30                 # secondi per vedere la schermata dei progetti in funzione dopo averla avviata
PASSO = 0.2                       # secondi tra due controlli mentre si aspetta


class NonRaggiungibile(Exception):
    """il server non risponde (spento, chiuso male, file di sessione rimasto)"""


class Errore(ValueError):
    """il server ha risposto con un errore: codice HTTP, messaggio per l'utente, licenza (403 di una funzione di fascia),
    causa (il «codice» che l'editor aggiunge ai rifiuti che il programma deve riconoscere senza leggere il testo: «altra_scheda»)"""

    def __init__(self, codice, messaggio, licenza=False, causa=None):
        super().__init__(messaggio); self.codice, self.licenza, self.causa = codice, licenza, causa


def chiedi(porta, gettone, percorso, corpo=None, timeout=30, binario=False):
    """richiesta a un server del programma: GET, o POST JSON se c'è un corpo. JSON (o byte con binario=True)"""
    dati = None if corpo is None else json.dumps(corpo).encode("utf-8")
    r = urllib.request.Request(f"http://127.0.0.1:{int(porta)}{percorso}", dati, {sicurezza.INTESTAZIONE: gettone or "", "Content-Type": "application/json"})
    try:
        with sicurezza.APRI_LOCALE.open(r, timeout=timeout) as f: b = f.read(MAX_RISPOSTA + 1)      # niente proxy: il gettone resta su 127.0.0.1
    except urllib.error.HTTPError as e:
        try: d = json.loads(e.read(65536))
        except ValueError: d = None
        d = d if isinstance(d, dict) else {}
        raise Errore(e.code, str(d.get("errore") or lingua.t("mcp.errore_http", codice=str(e.code))), d.get("licenza") is True, d.get("codice") if isinstance(d.get("codice"), str) else None) from None
    except (OSError, ValueError) as e: raise NonRaggiungibile(type(e).__name__) from None          # non tradotto: nome tecnico dell'errore, non arriva all'utente          # connessione rifiutata, tempo scaduto, porta di un altro programma
    if len(b) > MAX_RISPOSTA: raise Errore(413, lingua.t("mcp.risposta_troppo_grande"))
    if binario: return b
    try: return json.loads(b)
    except ValueError: raise NonRaggiungibile("risposta non JSON") from None          # non tradotto: motivo tecnico, non arriva all'utente


def _vivo(pid):
    """il processo pid c'è ancora? Su macOS e Linux lo si chiede al sistema (un file di sessione rimasto da un server chiuso male
    non riceve il gettone); su Windows os.kill chiuderebbe il processo: si prova la richiesta"""
    if sistema() == "windows" or not isinstance(pid, int): return True
    try: os.kill(pid, 0)
    except ProcessLookupError: return False
    except OSError: return True                   # c'è ma è di un altro utente: lo dirà la richiesta
    return True


class Server:
    """un server del programma che risponde: porta, gettone (dal file di sessione) e risposta di /api/ping"""

    def __init__(self, porta, gettone, ping):
        self.porta, self.gettone, self.ping = porta, gettone, ping

    def chiedi(self, percorso, corpo=None, timeout=30, binario=False):
        return chiedi(self.porta, self.gettone, percorso, corpo, timeout, binario)


def attivi(tipo):
    """[Server] di quel tipo («home», «editor») che rispondono, per porta"""
    out = []
    for s in sicurezza.sessioni(tipo):
        if not _vivo(s.get("pid")): continue
        try: p = chiedi(s["porta"], s["gettone"], "/api/ping", timeout=2)
        except (NonRaggiungibile, Errore): continue
        if isinstance(p, dict): out.append(Server(s["porta"], s["gettone"], p))
    return out


def programma():
    """la schermata dei progetti in funzione (Server) o None"""
    return next((s for s in attivi("home") if s.ping.get("ok") is True), None)


def editori():
    """{cartella reale del progetto: Server} degli editor in funzione"""
    return {reale(s.ping["path"]): s for s in attivi("editor") if isinstance(s.ping.get("path"), str)}


def reale(p):
    """forma confrontabile della cartella di un progetto"""
    return os.path.normcase(os.path.realpath(p))


def avvia_programma(attesa=ATTESA_AVVIO):
    """la schermata dei progetti, avviata se non è in funzione (senza aprire il browser, come un processo a sé che resta
    acceso dopo il server MCP). Server, oppure Errore con il motivo"""
    s = programma()
    if s: return s
    log.info("avvio di Impaginatore per l'assistente")
    p = subprocess.Popen([sys.executable, "-m", "impaginatore", "--no-browser", "--porta", str(PORTA_PROGRAMMA)],  # nosec B603  # questo stesso Python (sys.executable -m); argomenti in lista, senza shell
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=processi.cartella_pacchetto(), env=processi.ambiente_figli(), **processi.opzioni_staccato())
    fine = time.monotonic() + attesa
    while time.monotonic() < fine:
        s = programma()
        if s: return s
        if p.poll() is not None: raise Errore(503, lingua.t("mcp.non_partito", porta=str(PORTA_PROGRAMMA)))
        time.sleep(PASSO)
    raise Errore(503, lingua.t("mcp.non_risponde_ancora"))
