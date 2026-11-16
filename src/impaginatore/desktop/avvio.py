"""Schermata di avvio della finestra del programma (T-207): logotipo, versione e stato della licenza mentre la schermata
Album si prepara.

È una piccola finestra senza bordi (LARGHEZZA × ALTEZZA, al centro, sopra le altre, senza prendere il fuoco) con una pagina
senza script (risorse/avvio.html): i testi li mette il programma, già tradotti e neutralizzati. La finestra del programma
nasce nascosta e si mostra quando la pagina degli album ha chiesto l'elenco (home.server.PRONTA), ma non prima di MINIMO
secondi dalla comparsa della schermata (niente lampi) e non dopo MASSIMO (se qualcosa va storto si vede comunque la
finestra). Solo con la finestra del programma: nel browser e nella seconda finestra (ospite) non c'è.

Licenza (licenze.stato(), sola lettura): «Licenza <fascia>» se è attiva, «Beta privata» per le chiavi beta (campo
`beta` vero, o fascia «beta»), «Prova · N giorni» durante la prova, «Sola lettura» altrimenti. Se lo stato non si legge
la riga della licenza non c'è: la schermata di avvio non ferma mai il programma.
"""
import base64
import html
import logging
import threading
import time

from .. import __version__, lingua, risorse

LARGHEZZA, ALTEZZA = 480, 300
FONDO = "#181715"                       # Inchiostro (brand/tokens.css, --imp-carta-900): niente lampo bianco prima della pagina
MINIMO = 1.0                            # secondi di schermata almeno (dalla sua comparsa)
MASSIMO = 20.0                          # secondi al massimo: poi la finestra si mostra comunque
FONT = "statici/IBMPlexMono-Regular.woff2"
log = logging.getLogger("impaginatore.desktop")


def licenza(st=None):
    """(testo, tipo) della riga della licenza, tipo tra attiva, beta, prova, sola; ("", "") se lo stato non si legge"""
    if st is None:
        from .. import licenze
        try: st = licenze.stato()
        except Exception as e:                          # qualunque problema della licenza si vede nella schermata Album, non qui
            log.warning("stato della licenza non letto per la schermata di avvio: %s", type(e).__name__); return "", ""
    if st.get("stato") == "attiva":
        if st.get("beta") is True or st.get("fascia") == "beta": return lingua.t("desktop.avvio_beta"), "beta"
        return lingua.t("desktop.avvio_licenza", fascia=st.get("nome_fascia") or st.get("fascia") or ""), "attiva"
    if not st.get("sola_lettura"):
        return lingua.tn("desktop.avvio_prova", int((st.get("prova") or {}).get("giorni_rimasti") or 0)), "prova"
    return lingua.t("desktop.avvio_sola_lettura"), "sola"


def pagina(st=None):
    """HTML della schermata di avvio nella lingua in uso"""
    testo, tipo = licenza(st)
    sost = {"__LINGUA__": lingua.attuale(), "__FONT__": base64.b64encode(risorse.leggi(FONT)).decode("ascii"),
            "__VERSIONE__": html.escape(lingua.t("desktop.avvio_versione", versione=__version__)), "__TIPO__": tipo, "__LICENZA__": html.escape(testo)}
    p = risorse.leggi("avvio.html").decode("utf-8")
    for k, v in sost.items(): p = p.replace(k, v)
    return p


class Avvio:
    """schermata di avvio: crea() prima della finestra del programma (pywebview mostra per prima la prima finestra creata),
    poi segui(finestra, pronta) mostra la finestra quando l'evento `pronta` è impostato e chiude la schermata"""

    def __init__(self, m):
        self.m, self.minimo, self.massimo = m, MINIMO, MASSIMO
        self.finestra, self.comparsa = None, threading.Event()
        self.visto = None                                   # time.monotonic() della comparsa

    def crea(self, titolo):
        f = self.m.wv.create_window(titolo, html=pagina(), width=LARGHEZZA, height=ALTEZZA, resizable=False, frameless=True, easy_drag=False,
                                    on_top=True, focus=False, background_color=FONDO, text_select=False, zoomable=False)
        f.events.shown += self.mostrata
        self.finestra = f
        return f

    def mostrata(self):
        self.visto = time.monotonic(); self.comparsa.set()

    def segui(self, principale, pronta):
        """in un thread: aspetta la pagina degli album (al massimo `massimo` secondi), poi mostra la finestra del programma e
        chiude la schermata di avvio"""
        def lavoro():
            inizio = time.monotonic()
            self.comparsa.wait(self.massimo)
            pronta.wait(max(0.0, self.massimo - (time.monotonic() - inizio)))
            if self.visto is not None: time.sleep(max(0.0, self.minimo - (time.monotonic() - self.visto)))
            self.chiudi(principale)
        t = threading.Thread(target=lavoro, daemon=True, name="avvio"); t.start()
        return t

    def chiudi(self, principale):
        """mostra la finestra del programma e chiude la schermata di avvio (se sono già state chiuse non succede niente)"""
        principale.hidden = False       # pywebview 6 su GTK: show() rinasconde subito una finestra nata nascosta se `hidden` resta vero
        for azione in (principale.show, self.finestra.destroy):
            try: azione()
            except Exception as e:                          # finestra già chiusa (l'utente è uscito prima) o motore che non risponde
                log.debug("schermata di avvio: %s", type(e).__name__)
