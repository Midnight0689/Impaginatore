"""Aiuti per le prove degli aggiornamenti (T-207): pacchetti piccoli, release finte firmate con una chiave di prova.
Niente rete: le release stanno in una cartella (SorgenteFinta)."""
import json
import os
import zipfile

from impaginatore import ed25519
from impaginatore.aggiornamenti import rilascio

SEME = bytes(range(32))                         # chiave privata di prova (solo i test)
PUB = ed25519.pubblica(SEME).hex()
ALTRO_SEME = bytes(range(1, 33))
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "impaginatore")
SENZA_COVERAGE = ("COVERAGE_PROCESS_START", "COVERAGE_PROCESS_CONFIG", "COV_CORE_SOURCE", "COV_CORE_CONFIG", "COV_CORE_DATAFILE")


def pacchetto(cartella, versione="2.0.1", file=None, nome=None):
    """wheel piccola: impaginatore/__init__.py con la versione, più `file` {nome: byte} (di serie un modulo)"""
    os.makedirs(cartella, exist_ok=True)
    p = os.path.join(cartella, nome or f"impaginatore-{versione}-py3-none-any.whl")
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("impaginatore/__init__.py", f'__version__ = "{versione}"\n')
        z.writestr("impaginatore/sotto/", b"")                       # una voce di cartella: non si estrae
        for n, b in ({"impaginatore/sotto/modulo.py": b"X = 1\n"} if file is None else file).items(): z.writestr(n, b)
        z.writestr(f"impaginatore-{versione}.dist-info/METADATA", "Name: impaginatore\n")
    return p


def release(cartella, versione="2.0.1", seme=SEME, id_firma=1, novita=None, file=None):
    """release finta firmata in `cartella` (per SorgenteFinta); restituisce la cartella"""
    pk = pacchetto(os.path.join(str(cartella), "_pacchetto"), versione, file)
    rilascio.release_finta(str(cartella), pk, seme, novita=novita or {"it": [f"Novità della {versione}"], "en": [f"New in {versione}"]}, id_firma=id_firma)
    return str(cartella)


def rifirma(cartella, cambia, seme=SEME):
    """cambia il manifesto della release (cambia(dict)), lo rifirma e aggiorna la risposta dell'API"""
    p = os.path.join(cartella, "manifesto.json")
    with open(p, encoding="utf-8") as f: m = json.load(f)
    cambia(m)
    dati = json.dumps(m).encode("utf-8")
    with open(p, "wb") as f: f.write(dati)
    with open(os.path.join(cartella, "manifesto.json.sig"), "w", encoding="utf-8") as f: f.write(rilascio.firma(seme, dati))
    api(cartella, lambda j: None)


def api(cartella, cambia):
    """riscrive la risposta dell'API finta (releases/latest.json) con i file che ci sono ora nella cartella (misure e
    impronte ricalcolate), poi la passa a cambia(dict)"""
    nomi = {n: os.path.join(cartella, n) for n in os.listdir(cartella) if os.path.isfile(os.path.join(cartella, n)) and n != "chiave-prova.txt"}
    nuova = rilascio.risposta_api("v2", nomi, "https://github.com/prova/impaginatore/releases/download")
    cambia(nuova)
    with open(os.path.join(cartella, "releases", "latest.json"), "w", encoding="utf-8") as f: json.dump(nuova, f)


def ambiente_senza_coverage(env=None):
    """ambiente per i processi che eseguono copie del programma fuori da src: coverage non li segue (sarebbero file estranei)"""
    e = dict(os.environ if env is None else env)
    for k in SENZA_COVERAGE: e.pop(k, None)
    return e


def firmato(m, seme=SEME):
    dati = json.dumps(m).encode("utf-8")
    return dati, rilascio.firma(seme, dati).encode("ascii")
