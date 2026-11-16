"""Registro del programma: logger «impaginatore» su file a rotazione nella cartella dei dati dell'utente.

    <dati dell'utente>/registro/impaginatore.log   (5 file da 1 MB al massimo)

Regole: mai il contenuto delle foto; nomi delle foto e percorsi dei file dell'utente solo a livello DEBUG. Il registro lo
legge solo chi usa il programma: cartella 0700, file 0600 (anche quelli nati da una rotazione e quelli che una versione
precedente aveva creato con i permessi predefiniti; VER-013). IMPAGINATORE_REGISTRO sceglie il livello (DEBUG, INFO,
WARNING...; predefinito INFO).
"""
import logging
import logging.handlers
import os

NOME = "impaginatore"


def riservato(path):
    """apre (o crea) in aggiunta un file che legge e scrive solo l'utente (0600): registri e uscite dei processi.
    Restituisce il descrittore del file"""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try: os.chmod(path, 0o600)                     # file già esistente, nato con l'umask
    except OSError: pass                           # file di un altro utente: si scrive lo stesso (da qui non si può registrare: siamo dentro il registro)
    return fd


class _FileRiservato(logging.handlers.RotatingFileHandler):
    """registro a rotazione con i file 0600 (open() li creerebbe con l'umask: leggibili da altri utenti)"""

    def _open(self):
        return os.fdopen(riservato(self.baseFilename), "a", encoding=self.encoding, errors=self.errors)


def configura(processo):
    """attiva il registro su file per questo processo (home o editor); restituisce il percorso del file. Una volta sola per processo."""
    from .piattaforma import cartelle
    log = logging.getLogger(NOME)
    d = os.path.join(cartelle.dati_utente(), "registro"); f = os.path.join(d, "impaginatore.log")
    if any(getattr(h, "baseFilename", None) == f for h in log.handlers): return f
    os.makedirs(d, mode=0o700, exist_ok=True)
    try: os.chmod(d, 0o700)                        # cartella nata con l'umask (versioni precedenti)
    except OSError as e: log.warning("permessi della cartella del registro non impostati: %s", e.strerror)
    h = _FileRiservato(f, maxBytes=1_000_000, backupCount=4, encoding="utf-8")
    h.setFormatter(logging.Formatter(f"%(asctime)s {processo}[%(process)d] %(levelname)s %(name)s: %(message)s"))
    log.addHandler(h)
    log.setLevel(getattr(logging, os.environ.get("IMPAGINATORE_REGISTRO", "INFO").upper(), logging.INFO))
    return f
