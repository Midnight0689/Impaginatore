"""Registro del programma: logger «impaginatore» su file a rotazione nella cartella dei dati dell'utente.

    <dati dell'utente>/registro/impaginatore.log   (5 file da 1 MB al massimo)

Regole: mai il contenuto delle foto; i percorsi dei file dell'utente solo a livello DEBUG. IMPAGINATORE_REGISTRO sceglie
il livello (DEBUG, INFO, WARNING...; predefinito INFO).
"""
import logging
import logging.handlers
import os

NOME = "impaginatore"


def configura(processo):
    """attiva il registro su file per questo processo (home o editor); restituisce il percorso del file. Una volta sola per processo."""
    from .piattaforma import cartelle
    log = logging.getLogger(NOME)
    d = os.path.join(cartelle.dati_utente(), "registro"); f = os.path.join(d, "impaginatore.log")
    if any(getattr(h, "baseFilename", None) == f for h in log.handlers): return f
    os.makedirs(d, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(f, maxBytes=1_000_000, backupCount=4, encoding="utf-8")
    h.setFormatter(logging.Formatter(f"%(asctime)s {processo}[%(process)d] %(levelname)s %(name)s: %(message)s"))
    log.addHandler(h)
    log.setLevel(getattr(logging, os.environ.get("IMPAGINATORE_REGISTRO", "INFO").upper(), logging.INFO))
    return f
