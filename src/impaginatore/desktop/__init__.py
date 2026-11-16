"""Finestra del programma (T-201): schermata dei progetti ed editor in una finestra propria invece che in una scheda del
browser, su macOS (WebKit), Windows (WebView2) e Linux (WebKitGTK), con pywebview (dipendenza facoltativa «desktop»).

    impaginatore              la finestra, se c'è; altrimenti il browser come prima (il motivo va nel registro)
    impaginatore --browser    il browser anche se la finestra c'è

Come funziona (docs/architettura/ARCHITETTURA.md, «Finestra desktop»):
- la schermata dei progetti gira in un thread di questo processo; la finestra apre il suo indirizzo di avvio monouso
  dentro il processo (nessuna riga di comando, nessun browser: SICUREZZA.md);
- la pagina passa dalla schermata all'editor (processo a parte, porta sua) e ritorno come nel browser, nella stessa
  finestra: ogni passaggio usa un indirizzo di avvio monouso del server di arrivo;
- la finestra apre solo le pagine del programma (navigazione.py); i link esterni vanno nel browser di sistema;
- alla chiusura gli editor lanciati da qui salvano e si chiudono, poi si ferma la schermata (finestra.esegui);
- misura e posizione si ricordano (geometria.py); le finestre di scelta sono quelle di pywebview (dialoghi.py).
Nessuna API JavaScript→Python della pagina: pywebview parte senza js_api e senza funzioni esposte.

Importare il pacchetto non carica pywebview: lo carica motore(), solo quando serve la finestra.
"""
from .finestra import esegui, gettone, motore, ospite

__all__ = ["esegui", "gettone", "motore", "ospite"]
