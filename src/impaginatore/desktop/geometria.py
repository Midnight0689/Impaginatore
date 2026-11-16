"""Misura e posizione della finestra del programma: si leggono all'apertura, si seguono mentre la si usa, si salvano alla
chiusura in <dati dell'utente>/finestra.json ({larghezza, altezza, x, y, massimizzata}).

Misura minima 1024 × 700 (docs/prodotto/ux/ARCHITETTURA-INTERFACCIA.md). Una posizione che non cade su nessuno schermo
(monitor staccato) si scarta: la finestra si apre al centro. Gli eventi di pywebview (moved, resized) dicono solo che
qualcosa è cambiato: misura e posizione si rileggono poco dopo con le proprietà della finestra (x, y, width, height), che
pywebview calcola come le usa all'apertura (su GTK la posizione dell'evento è quella dell'area interna, non della cornice:
salvarla farebbe scendere la finestra a ogni avvio). Finestra massimizzata o ridotta a icona: si tiene la misura normale.
"""
import logging
import os
import threading

from .. import formato

MINIMA = (1024, 700)
MASSIMA = 20000                                     # pixel: oltre è un file rovinato
PREDEFINITA = (1280, 800)                          # senza schermi noti e senza file
log = logging.getLogger("impaginatore.desktop")


def _intero(v, minimo, massimo):
    return isinstance(v, int) and not isinstance(v, bool) and minimo <= v <= massimo


def _visibile(x, y, schermi):
    """l'angolo in alto a sinistra (dove si afferra la finestra) cade su uno schermo? Senza schermi noti: sì"""
    if not schermi: return True
    px, py = x + 40, y + 20
    return any(sx <= px < sx + sw and sy <= py < sy + sh for sx, sy, sw, sh in schermi)


class Geometria:
    """misura e posizione della finestra. schermi: [(x, y, larghezza, altezza)] degli schermi (il primo è il principale)"""

    def __init__(self, percorso, ritardo=0.4):
        self.percorso, self.ritardo = percorso, ritardo
        self.dati, self.stato, self.finestra = {}, "normale", None
        self._timer, self._lock = None, threading.Lock()

    def iniziale(self, schermi=()):
        """argomenti per create_window: width, height, x, y, maximized (dal file, controllati; altrimenti predefiniti)"""
        try:
            d = formato.leggi_json(self.percorso, 4096)
            if not isinstance(d, dict): raise ValueError("non è un oggetto")           # non tradotto: finisce solo nel registro
        except FileNotFoundError: d = {}
        except (OSError, ValueError) as e:                 # ErroreProgetto è un ValueError
            log.info("misura della finestra non letta (%s): uso quella predefinita", type(e).__name__); d = {}
        if schermi:
            sw, sh = schermi[0][2], schermi[0][3]
            pw, ph = max(MINIMA[0], min(1440, int(sw * .85))), max(MINIMA[1], min(900, int(sh * .85)))
        else: pw, ph = PREDEFINITA
        w = d["larghezza"] if _intero(d.get("larghezza"), MINIMA[0], MASSIMA) else pw
        h = d["altezza"] if _intero(d.get("altezza"), MINIMA[1], MASSIMA) else ph
        x, y = d.get("x"), d.get("y")
        if not (_intero(x, -MASSIMA, MASSIMA) and _intero(y, -MASSIMA, MASSIMA) and _visibile(x, y, schermi)): x = y = None
        self.dati = dict(larghezza=w, altezza=h, x=x, y=y)
        self.stato = "massimizzata" if d.get("massimizzata") is True else "normale"
        return dict(width=w, height=h, x=x, y=y, maximized=self.stato == "massimizzata")

    # ------------------------------------------------------------ eventi della finestra
    def collega(self, finestra):
        """segue gli eventi della finestra pywebview"""
        self.finestra = finestra
        e = finestra.events
        e.moved += self.cambiata; e.resized += self.cambiata
        e.maximized += self.massimizzata; e.minimized += self.ridotta; e.restored += self.ripristinata
        e.closing += self.chiusura

    def cambiata(self, *_):
        """la finestra si è mossa o ha cambiato misura: una rilettura sola, poco dopo, per una serie di eventi"""
        if self.stato != "normale": return
        with self._lock:
            if self._timer is None:
                self._timer = threading.Timer(self.ritardo, self.rileggi); self._timer.daemon = True; self._timer.start()

    def rileggi(self):
        with self._lock: self._timer = None
        f = self.finestra
        if self.stato != "normale" or f is None: return
        try: x, y, w, h = int(f.x), int(f.y), int(f.width), int(f.height)
        except Exception as e:                         # finestra già chiusa (pywebview: None o eccezione del motore)
            log.debug("misura della finestra non riletta: %s", e); return
        if self.stato != "normale": return                 # è cambiato mentre si leggeva
        self.dati.update(x=x, y=y)
        if w >= MINIMA[0] and h >= MINIMA[1]: self.dati.update(larghezza=w, altezza=h)

    def massimizzata(self): self.stato = "massimizzata"
    def ridotta(self): self.stato = "ridotta"
    def ripristinata(self): self.stato = "normale"; self.cambiata()

    def chiusura(self):
        """evento closing: niente più riletture (la finestra sta per sparire). Non annulla la chiusura"""
        self.finestra = None
        with self._lock:
            if self._timer is not None: self._timer.cancel(); self._timer = None

    def salva(self):
        """scrive finestra.json (scrittura atomica); un errore va nel registro"""
        d = dict(self.dati, massimizzata=self.stato == "massimizzata")
        try:
            os.makedirs(os.path.dirname(self.percorso), exist_ok=True)
            formato.scrivi_json(self.percorso, d)
        except OSError as e: log.warning("misura della finestra non salvata: %s", e)
        return d
