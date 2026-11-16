"""Consenso dell'utente a mandare immagini all'assistente AI: spento di serie.

Le immagini (miniature delle foto, anteprime degli spread e della bozza) che uno strumento MCP restituisce arrivano al
programma dell'assistente e da lì al suo fornitore, fuori dal computer. Per questo nessuno strumento restituisce pixel se
l'utente non l'ha permesso in uno di questi due modi, gli unici:

- l'opzione esplicita all'avvio del server MCP, scritta dall'utente nella configurazione dell'assistente:
  «impaginatore mcp --consenti-immagini»;
- l'impostazione del programma, salvata in <dati dell'utente>/assistente.json (0600) da imposta(): la scrive solo il
  programma quando l'utente accende l'interruttore (l'interfaccia arriva con T-205). Nessuno strumento MCP la cambia.

Solo libreria standard: questo modulo non usa l'SDK MCP.
"""
import json
import logging
import os

from .. import lingua
from ..piattaforma import cartelle

log = logging.getLogger("impaginatore.mcp")

FILE = "assistente.json"

def spiegazione():
    """perché le immagini sono spente e come si accendono (interruttore nella schermata Album, oppure opzione all'avvio),
    nella lingua in uso"""
    return lingua.t("mcp.spiegazione")


def percorso():
    return os.path.join(cartelle.dati_utente(), FILE)


def salvato():
    """l'utente ha acceso le immagini nelle impostazioni del programma? (file assente, illeggibile o diverso: no)"""
    try:
        with open(percorso(), encoding="utf-8") as f: d = json.load(f)
    except FileNotFoundError: return False
    except (OSError, ValueError) as e:
        log.warning("impostazioni dell'assistente illeggibili (%s): immagini spente", type(e).__name__); return False
    return isinstance(d, dict) and d.get("immagini") is True


def imposta(valore):
    """salva la scelta dell'utente (da chiamare solo dall'interfaccia del programma, mai da uno strumento MCP)"""
    d = os.path.dirname(percorso()); os.makedirs(d, mode=0o700, exist_ok=True)
    tmp = percorso() + f".{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump({"formato": 1, "immagini": valore is True}, f)
    os.replace(tmp, percorso())
    log.info("immagini per l'assistente %s", "accese" if valore is True else "spente")


def consentite(opzione_avvio):
    """immagini permesse: opzione all'avvio oppure impostazione del programma"""
    return opzione_avvio is True or salvato()
