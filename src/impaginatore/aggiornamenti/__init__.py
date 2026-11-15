"""Aggiornamenti del programma, dietro un'interfaccia: la schermata dei progetti usa solo i metodi di Aggiornamenti.

Implementazioni:
    git.Git          il programma gira da un checkout git (com'era sul Mac di Stefano): controlla su GitHub, scarica le
                     novità (pull), torna a una versione precedente creando una nuova versione
    NonDisponibili   programma installato (pip / pacchetto) o aggiornamenti spenti: niente rete, niente modifiche
predefiniti() sceglie: IMPAGINATORE_AGGIORNAMENTI=no (o 0/off/false) li spegne; da un checkout git -> Git; altrimenti
NonDisponibili. Punto di estensione: un aggiornatore per i pacchetti firmati (fasi successive) implementa la stessa interfaccia;
il contratto (manifesto firmato Ed25519) è in firmati.PacchettiFirmati.

Lo stato è il dizionario che la pagina si aspetta (home.html):
    da_aggiornare, novita [titoli], controllato (epoch), errore (testo, "" se ok: solo per i controlli falliti),
    disponibile (False = questa installazione non si aggiorna da sola; motivo dice perché, e non è un errore),
    attuale / ultima = {n, codice, data, titolo, rel} della versione in uso / di quella disponibile
Le richieste che cambiano il programma (aggiorna, ripristina) arrivano solo dalla pagina con il gettone della sessione
(servizio.Gestore): nessun'altra pagina web le può far partire (SEC-007).
"""
import os
import shutil

from .. import __version__


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
        """controllo periodico, finché l'evento `fermo` non viene impostato"""
        while True:
            self.controlla()
            if fermo.wait(ogni): return


class NonDisponibili(Aggiornamenti):
    """nessun aggiornamento automatico: mostra la versione installata e lo dice"""

    def __init__(self, motivo="Aggiornamenti automatici non disponibili in questa installazione"):
        self.motivo = motivo

    def stato(self):
        return dict(da_aggiornare=False, novita=[], controllato=0, errore="", disponibile=False, motivo=self.motivo, ultima=None,      # non è un errore: la pagina mostra il motivo
                    attuale=dict(n=__version__, codice="", data="", titolo="versione installata", rel=__version__))

    def controlla(self): return self.stato()

    def versioni(self, k=20): return []

    def aggiorna(self): raise ValueError(self.motivo)

    def ripristina(self, codice): raise ValueError(self.motivo)

    def ciclo(self, fermo, ogni=10 * 60): return


def predefiniti(riavvia=None):
    """aggiornamenti adatti a come è installato il programma; riavvia() viene chiamata dopo un aggiornamento riuscito"""
    if os.environ.get("IMPAGINATORE_AGGIORNAMENTI", "").strip().lower() in ("no", "0", "off", "false"):
        return NonDisponibili("Aggiornamenti automatici spenti (IMPAGINATORE_AGGIORNAMENTI)")
    from ..piattaforma import cartelle
    radice = cartelle.radice_checkout()
    if radice and shutil.which("git"):
        from .git import Git
        return Git(radice, riavvia)
    return NonDisponibili()
