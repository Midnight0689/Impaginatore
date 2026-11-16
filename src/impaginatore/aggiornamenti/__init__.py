"""Aggiornamenti del programma, dietro un'interfaccia: la schermata dei progetti usa solo i metodi di Aggiornamenti.

Implementazioni:
    firmati.PacchettiFirmati   pacchetti con un manifesto firmato Ed25519, presi dalle release di GitHub (T-207):
                               controlla, scarica, verifica, installa accanto alla versione in uso e riavvia; «Torna alla
                               versione precedente». Sorgente (sorgenti.py) e installazione (installazione.py) intercambiabili
    git.Git                    il programma gira da un checkout git (com'era sul Mac di Stefano): controlla su GitHub, scarica le
                               novità (pull), torna a una versione precedente creando una nuova versione
    NonDisponibili             aggiornamenti spenti: niente rete, niente modifiche
predefiniti() sceglie: IMPAGINATORE_AGGIORNAMENTI=no (o 0/off/false) li spegne; IMPAGINATORE_AGGIORNAMENTI_FINTI=<cartella>
prende i pacchetti da una cartella locale (prove, docs/architettura/AGGIORNAMENTI.md); da un checkout git -> Git;
altrimenti PacchettiFirmati (programma compilato: InstallazioneCompilata, non ancora attiva).

Lo stato è il dizionario che la pagina si aspetta (home.html):
    da_aggiornare, novita [titoli], controllato (epoch), errore (testo, "" se ok: solo per i controlli falliti),
    disponibile (False = questa installazione non si aggiorna da sola; motivo dice perché, e non è un errore),
    attuale / ultima = {n, codice, data, titolo, rel} della versione in uso / di quella disponibile;
    PacchettiFirmati aggiunge precedente (versione a cui si può tornare) e annuncio ({tipo, versione, id}: il programma
    è appena stato aggiornato o riportato indietro)
Le richieste che cambiano il programma (aggiorna, ripristina) arrivano solo dalla pagina con il gettone della sessione
(servizio.Gestore): nessun'altra pagina web le può far partire (SEC-007).

Il controllo automatico (all'avvio e poi periodico) si spegne dalla schermata Album: automatico() / imposta_automatico(),
in <dati dell'utente>/aggiornamenti.json. Il controllo a mano («Controlla aggiornamenti») resta sempre.
"""
import json
import os
import secrets
import shutil
import sys

from .. import __version__, lingua

FILE_IMPOSTAZIONI = "aggiornamenti.json"


class Rifiutato(ValueError):
    """aggiornamento che non si fa: il messaggio è per l'utente (chiave della tabella, composto nella lingua in uso)"""

    def __init__(self, chiave, **param):
        super().__init__(lingua.t(chiave, **param)); self.chiave, self.param = chiave, param


# ---------------------------------------------------------------- impostazione del controllo automatico
def _file_impostazioni():
    from ..piattaforma import cartelle
    return os.path.join(cartelle.dati_utente(), FILE_IMPOSTAZIONI)


def automatico():
    """il programma controlla da solo se c'è una versione nuova? (di serie sì; un file illeggibile vale «sì»)"""
    try:
        with open(_file_impostazioni(), encoding="utf-8") as f: d = json.load(f)
    except (OSError, ValueError): return True
    return not (isinstance(d, dict) and d.get("automatico") is False)


def imposta_automatico(acceso):
    """salva la scelta dell'utente (scrittura atomica); restituisce la scelta salvata"""
    if not isinstance(acceso, bool): raise ValueError(lingua.t("sistema.agg_automatico_vero_falso"))
    p = _file_impostazioni(); os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = f"{p}.{secrets.token_hex(6)}.tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump({"formato": 1, "automatico": acceso}, f)
    os.replace(tmp, p)
    return acceso


class Aggiornamenti:
    """interfaccia"""

    def stato(self):
        """stato da mostrare (rilegge la versione in uso: può cambiare anche se si aggiorna a mano)"""
        raise NotImplementedError

    def controlla(self):
        """controlla se c'è una versione nuova (mai scaricarla da solo) e restituisce lo stato"""
        raise NotImplementedError

    def versioni(self, k=20):
        """[{n, codice, data, titolo, attuale}] delle ultime versioni, dalla più recente"""
        raise NotImplementedError

    def aggiorna(self):
        """scarica e installa la versione nuova, poi riavvia il programma"""
        raise NotImplementedError

    def ripristina(self, codice):
        """torna alla versione `codice`, poi riavvia il programma"""
        raise NotImplementedError

    def ciclo(self, fermo, ogni=10 * 60):
        """controllo periodico (se l'utente non l'ha spento), finché l'evento `fermo` non viene impostato"""
        while True:
            if automatico(): self.controlla()
            if fermo.wait(ogni): return


class NonDisponibili(Aggiornamenti):
    """nessun aggiornamento automatico: mostra la versione installata e lo dice"""

    def __init__(self, chiave="sistema.agg_non_disponibili"):
        self.chiave = chiave

    @property
    def motivo(self):
        """perché non ci sono aggiornamenti, nella lingua in uso (si compone a ogni richiesta)"""
        return lingua.t(self.chiave)

    def stato(self):
        return dict(da_aggiornare=False, novita=[], controllato=0, errore="", disponibile=False, motivo=self.motivo, ultima=None,      # non è un errore: la pagina mostra il motivo
                    attuale=dict(n=__version__, codice="", data="", titolo=lingua.t("sistema.agg_versione_installata"), rel=__version__))

    def controlla(self): return self.stato()

    def versioni(self, k=20): return []

    def aggiorna(self): raise ValueError(self.motivo)

    def ripristina(self, codice): raise ValueError(self.motivo)

    def ciclo(self, fermo, ogni=10 * 60): return


def predefiniti(riavvia=None):
    """aggiornamenti adatti a come è installato il programma; riavvia() viene chiamata dopo un aggiornamento riuscito"""
    if os.environ.get("IMPAGINATORE_AGGIORNAMENTI", "").strip().lower() in ("no", "0", "off", "false"):
        return NonDisponibili("sistema.agg_spenti")
    from . import firmati, installazione, lanciatore, sorgenti
    finta = os.environ.get(lanciatore.VAR_FINTI, "").strip()
    if finta:                                               # prove a mano di tutto il giro (AGGIORNAMENTI.md): la firma si controlla lo stesso
        s = sorgenti.SorgenteFinta(finta)
        return firmati.PacchettiFirmati(s, installazione.InstallazionePython(), riavvia, chiavi=firmati.chiavi_con_prova(s))
    if getattr(sys, "frozen", False):                       # programma compilato (T-302): si sostituisce tutto con l'installatore
        return firmati.PacchettiFirmati(sorgenti.SorgenteGitHub(), installazione.InstallazioneCompilata(), riavvia)
    from ..piattaforma import cartelle
    radice = cartelle.radice_checkout()
    if radice and shutil.which("git"):
        from .git import Git
        return Git(radice, riavvia)
    return firmati.PacchettiFirmati(sorgenti.SorgenteGitHub(), installazione.InstallazionePython(), riavvia)
