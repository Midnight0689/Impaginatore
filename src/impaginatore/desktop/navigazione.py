"""Dove può andare la finestra del programma: solo le sue pagine, http://127.0.0.1:<porta della schermata o di un editor>.

Un sito http o https si apre nel browser di sistema (senza il gettone nell'ambiente: processi.apri_browser); tutto il
resto (file:, data:, javascript:, blob:..., altri servizi di questo computer) non si apre affatto. Le porte del programma sono quella della
schermata e quelle degli editor in funzione, che hanno il loro file di sessione (0600, solo nostro: SICUREZZA.md).

Due difese:
1. il filtro del motore della finestra, che ferma la navigazione prima che parta: WebKitGTK («decide-policy») e WebView2
   (NavigationStarting). Le finestre nuove (target=_blank, window.open) non si aprono mai: pywebview, con
   OPEN_EXTERNAL_LINKS_IN_BROWSER spento, carica il link nella finestra stessa e passa di nuovo da qui;
2. il controllo dopo ogni caricamento (tutti i sistemi; su macOS l'unico: pywebview non lascia aggiungere un filtro a
   WKWebView): una pagina fuori dal programma si lascia subito e la finestra torna all'ultima pagina del programma.
"""
import logging
import threading
from urllib.parse import urlsplit

from .. import sicurezza
from ..piattaforma import processi

PROGRAMMA, ESTERNA, VIETATA, VUOTA = "programma", "esterna", "vietata", "vuota"
log = logging.getLogger("impaginatore.desktop")


def porte_programma(porta_home):
    """porte delle pagine del programma: la schermata e gli editor in funzione (file di sessione)"""
    return {int(porta_home)} | {s["porta"] for s in sicurezza.sessioni("editor")}


def _locale(host):
    """questo computer (o la rete locale vista da qui): localhost, 127.x, ::1, 0.0.0.0"""
    return host in ("localhost", "::1", "0.0.0.0") or host.endswith(".localhost") or host.startswith("127.")  # nosec B104  # si confronta, non si ascolta


def classifica(url, porte):
    """PROGRAMMA (pagina del programma), ESTERNA (sito http/https: va nel browser di sistema), VUOTA (about:blank, la
    pagina vuota prima del primo caricamento) o VIETATA (ogni altro schema, un altro servizio di questo computer,
    un indirizzo malformato)"""
    if not url or url == "about:blank": return VUOTA
    try: u = urlsplit(str(url)); porta = u.port
    except ValueError: return VIETATA
    if u.username is not None or u.password is not None: return VIETATA       # «http://127.0.0.1:8765@altro.sito/»: mai
    if u.scheme == "http" and u.hostname == "127.0.0.1" and porta in porte: return PROGRAMMA
    if u.scheme in ("http", "https") and u.hostname and not _locale(u.hostname): return ESTERNA
    return VIETATA                          # i servizi di questo computer non si aprono nemmeno nel browser: le pagine del programma non ci mandano


def origine(url):
    """http://127.0.0.1:<porta> di un indirizzo del programma"""
    u = urlsplit(url)
    return f"{u.scheme}://{u.netloc}"


class Navigazione:
    """decide se la finestra può aprire un indirizzo; porte: funzione che dà le porte del programma (si rileggono ogni
    volta: gli editor si aprono e si chiudono)"""

    def __init__(self, porte):
        self.porte = porte

    def consenti(self, url):
        """True se la finestra può aprire url; altrimenti lo annota (l'indirizzo solo a DEBUG) e, se è un sito web, lo
        apre nel browser di sistema (in un thread: il filtro gira nel thread della finestra)"""
        t = classifica(url, self.porte())
        if t in (PROGRAMMA, VUOTA): return True
        log.info("la finestra non apre un indirizzo %s", t)
        log.debug("indirizzo non aperto nella finestra: %s", url)
        if t == ESTERNA: threading.Thread(target=processi.apri_browser, args=(url,), daemon=True).start()
        return False


def filtro_gtk(finestra, nav):
    """WebKitGTK: «decide-policy» sulla vista di pywebview (collegato dopo il suo, che per i link _blank chiama load_url).
    Vale per le navigazioni della pagina e per quelle chieste da Python (load_url)"""
    from webview.platforms import gtk as G               # già caricato da motore() (guilib.initialize)
    tipi = G.webkit.PolicyDecisionType

    def decidi(_vista, decisione, tipo):
        if tipo == tipi.NEW_WINDOW_ACTION:
            decisione.ignore(); return True
        if tipo == tipi.NAVIGATION_ACTION and not nav.consenti(decisione.get_navigation_action().get_request().get_uri()):
            decisione.ignore(); return True
        return False                                       # risposte (download, tipi): decide pywebview
    G.BrowserView.instances[finestra.uid].webview.connect("decide-policy", decidi)


def filtro_webview2(finestra, nav):
    """WebView2: NavigationStarting del controllo WinForms che pywebview mette in finestra.native.webview (le finestre nuove
    le gestisce pywebview: NewWindowRequested → load_url → di nuovo qui)"""
    def avvio(_mittente, args):
        if not nav.consenti(str(args.Uri)): args.Cancel = True
    finestra.native.webview.NavigationStarting += avvio


FILTRI = {"gtkwebkit2": filtro_gtk, "edgechromium": filtro_webview2}       # wkwebview (macOS): solo il controllo dopo il caricamento


def installa_filtro(motore, finestra, nav):
    """filtro del motore della finestra, se c'è per questo motore; True se installato. Un errore lascia il solo controllo
    dopo il caricamento (che c'è sempre) e va nel registro"""
    f = FILTRI.get(motore)
    if f is None: return False
    try: f(finestra, nav)
    except Exception as e:                             # interni di pywebview cambiati: la finestra funziona lo stesso
        log.warning("filtro di navigazione della finestra non installato (%s): resta il controllo dopo il caricamento", e)
        return False
    return True
