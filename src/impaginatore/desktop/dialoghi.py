"""Finestre di scelta (cartelle, foto, ZIP) quando c'è la finestra del programma.

- Nella schermata dei progetti (lo stesso processo della finestra): DialoghiFinestra, le finestre native di pywebview
  (Finder, Esplora file, GTK) aperte sopra la finestra del programma, una per volta. Si impostano con
  piattaforma.dialoghi.imposta.
- Nell'editor (processo a parte, senza finestra sua): Ponte chiede la scelta alla schermata (POST /api/dialogo, con il
  gettone del suo file di sessione), che la apre nella finestra. L'editor lo trova con IMPAGINATORE_DIALOGHI=finestra:<porta>
  (la mette nell'ambiente la finestra, i processi degli editor la ereditano). Se la schermata non risponde, Ponte usa
  le finestre del sistema come senza finestra.
Il percorso scelto diventa una radice consentita come prima: lo fa chi chiede (editor.pick, home /api/scegli-foto).

Limite di pywebview: create_file_dialog non ha un titolo. Il messaggio («Scegli la cartella con le foto del cliente») si
mette nel testo che GTK usa come titolo; macOS e Windows mostrano il loro titolo generico.
"""
import logging
import os
import threading

from .. import lingua, sicurezza
from ..piattaforma import dialoghi

TIPI = ("cartella", "zip", "foto")
FILTRO_FOTO = "{nome} (" + ";".join(dialoghi.TIPI_FOTO) + ")"           # il nome nella lingua in uso: filtro_foto()
FILTRO_ZIP = "ZIP (*.zip;*.ZIP)"
_TITOLO_GTK = {"cartella": "linux.openFolder", "zip": "linux.openFile", "foto": "linux.openFiles"}
log = logging.getLogger("impaginatore.desktop")


class DialoghiFinestra(dialoghi.Dialoghi):
    """finestre di scelta di pywebview sopra la finestra del programma. tipi: webview.FileDialog. Si chiamano da un thread
    del server, mai da quello della finestra (pywebview aspetta la risposta del thread della finestra)"""
    nome = "finestra"

    def __init__(self, finestra, tipi):
        self.finestra, self.tipi = finestra, tipi
        self._lock = threading.Lock()

    def _scegli(self, tipo, messaggio):
        f, T = self.finestra, self.tipi
        with self._lock:                                    # una finestra di scelta per volta
            f.localization[_TITOLO_GTK[tipo]] = str(messaggio)
            if tipo == "cartella": r = f.create_file_dialog(T.FOLDER)
            elif tipo == "zip": r = f.create_file_dialog(T.OPEN, file_types=(FILTRO_ZIP,))
            else: r = f.create_file_dialog(T.OPEN, allow_multiple=True, file_types=(filtro_foto(),))
        return [os.path.normpath(p) for p in (r or ()) if p]          # None: annullata (o errore del motore, che pywebview annota)


def filtro_foto():
    """filtro delle foto per le finestre di scelta: «Foto (*.jpg;…)» / «Photos (*.jpg;…)»"""
    return FILTRO_FOTO.format(nome=lingua.t("desktop.filtro_foto"))


def scegli(tipo, messaggio):
    """POST /api/dialogo della schermata: percorsi scelti con le finestre di scelta di questo processo ([] se annullata)"""
    if tipo not in TIPI: raise ValueError("finestra di scelta sconosciuta")        # non tradotto: risposta all'editor (Ponte), che non la mostra
    if isinstance(dialoghi.attuali(), Ponte): raise ValueError("questa schermata non apre finestre di scelta sue")       # non tradotto: come sopra; chiederebbe a sé stessa
    m = str(messaggio or "")[:200]
    if tipo == "cartella": return [p for p in [dialoghi.scegli_cartella(m)] if p]
    if tipo == "zip": return [p for p in [dialoghi.scegli_zip(m)] if p]
    return dialoghi.scegli_percorsi(False, m)


class Ponte(dialoghi.Dialoghi):
    """nell'editor: la finestra di scelta la apre la schermata sulla porta `porta`, nella finestra del programma"""
    nome = "finestra"

    def __init__(self, porta):
        self.porta = porta

    def _scegli(self, tipo, messaggio):
        g = sicurezza.gettone_di("home", self.porta)
        if g:
            try:
                r = sicurezza.chiedi(self.porta, "/api/dialogo", g, {"tipo": tipo, "messaggio": messaggio}, timeout=None)       # l'utente sceglie con calma
                return [str(p) for p in r["percorsi"]]
            except (OSError, ValueError, KeyError, TypeError) as e:
                log.warning("finestra di scelta non aperta dalla schermata (%s): uso quella del sistema", type(e).__name__)
        return dialoghi.predefiniti(finestra=False)._scegli(tipo, messaggio)
