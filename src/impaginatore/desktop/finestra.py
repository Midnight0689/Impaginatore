"""La finestra del programma con pywebview: scelta tra finestra e browser, apertura, chiusura ordinata.

motore()  pywebview pronto con il motore giusto per il sistema, oppure None (motivo nel registro: si apre il browser)
esegui()  la finestra di chi ha avviato la schermata dei progetti: alla chiusura salva e chiude gli editor, poi la schermata
ospite()  una seconda finestra sulla schermata già in funzione (secondo avvio del comando): alla chiusura non ferma niente
"""
import logging
import os
import subprocess  # nosec B404  # solo per TimeoutExpired: qui non si lancia nessun processo
import sys
import threading

from .. import risorse, sicurezza
from ..piattaforma import cartelle, dialoghi, sistema
from . import dialoghi as dialoghi_finestra
from .geometria import MINIMA, Geometria
from .navigazione import PROGRAMMA, Navigazione, classifica, installa_filtro, origine, porte_programma

TITOLO = "Impaginatore"
SFONDO = "#2B2B2B"                                  # fondo della schermata dei progetti: niente lampo bianco prima della pagina
GUI = {"linux": "gtk", "windows": "edgechromium", "mac": "cocoa"}
MOTORI = ("gtkwebkit2", "edgechromium", "wkwebview")     # WebKitGTK, WebView2, WKWebView. Mai Internet Explorer (mshtml) né Qt
SPENTA = ("no", "0", "browser")                     # IMPAGINATORE_FINESTRA: il browser anche se la finestra c'è (i test)
# finestre di scelta di pywebview: dove pywebview le apre dal thread giusto (GTK: provate sotto Xvfb; macOS: le apre nel
# thread principale). Su Windows pywebview le apre dal thread che le chiede (qui un thread del server) e un errore
# sembra un «Annulla»: finché non sono provate su Windows restano quelle di sempre (tkinter in un processo a parte)
DIALOGHI_PROPRI = ("gtkwebkit2", "wkwebview")
ATTUALE = [None]                                    # la Finestra aperta in questo processo (prove)
log = logging.getLogger("impaginatore.desktop")


class Motore:
    """pywebview pronto: wv è il modulo webview, lib il modulo del motore caricato (gtk, cocoa, winforms), nome il motore"""

    def __init__(self, wv, lib):
        self.wv, self.lib, self.nome = wv, lib, lib.renderer

    def schermi(self):
        """[(x, y, larghezza, altezza)] degli schermi, il principale per primo; [] se il motore non li sa dire"""
        try: return [(int(s.x), int(s.y), int(s.width), int(s.height)) for s in self.lib.get_screens()]
        except Exception as e:                          # senza schermi noti la posizione salvata non si controlla
            log.debug("schermi non letti: %s", e); return []


def _no(motivo):
    log.info("finestra del programma non disponibile: %s. Apro il browser", motivo)
    print(f"Finestra del programma non disponibile ({motivo}): apro il browser", file=sys.stderr, flush=True)
    return None


def _gtk():
    """PyGObject con GTK 3 e WebKit2GTK (4.1 o 4.0), come li vuole pywebview: pacchetti del sistema"""
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        try: gi.require_version("WebKit2", "4.1")
        except ValueError: gi.require_version("WebKit2", "4.0")
        return True
    except (ImportError, ValueError): return False


def motore():
    """Motore pronto, oppure None (e il motivo nel registro)"""
    if os.environ.get("IMPAGINATORE_FINESTRA", "").strip().lower() in SPENTA: return _no("IMPAGINATORE_FINESTRA=no")
    s = sistema()
    if s == "linux" and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")): return _no("nessuno schermo")
    try:
        import webview as wv
        from webview.guilib import initialize               # non «webview.guilib.initialize»: nel pacchetto «guilib» è una variabile (None)
    except ImportError: return _no("pywebview non è installato: serve l'extra «desktop»")
    if s == "linux" and not _gtk(): return _no("mancano PyGObject e WebKit2GTK del sistema")
    try: lib = initialize(GUI[s])
    except Exception as e: return _no(f"il motore della finestra non parte: {e}")       # WebViewException e gli errori del sistema (.NET...)
    if lib.renderer not in MOTORI: return _no(f"motore {lib.renderer} non adatto: serve WebView2 su Windows, WebKit su macOS e Linux")
    return Motore(wv, lib)


def gettone():
    """gettone della schermata quando c'è la finestra: quello di un riavvio (variabile d'ambiente) o uno nuovo, che NON
    resta nell'ambiente: i processi che nascono da qui (il motore della finestra, il browser per i link esterni) non lo
    ereditano. La schermata non si riavvia con os.execv: non le serve nell'ambiente (rilancia_dopo lo passa esplicito)"""
    return os.environ.pop(sicurezza.VARIABILE, None) or sicurezza.nuovo_gettone()


def sviluppo():
    """strumenti di sviluppo della vista web: solo con IMPAGINATORE_FINESTRA_SVILUPPO=1 e mai in un programma impacchettato"""
    return os.environ.get("IMPAGINATORE_FINESTRA_SVILUPPO") == "1" and not getattr(sys, "frozen", False)


class Finestra:
    """la finestra pywebview del programma. m: Motore; porta: quella della schermata dei progetti"""

    def __init__(self, m, porta):
        self.m, self.porta = m, int(porta)
        self.nav = Navigazione(lambda: porte_programma(self.porta))
        self.geo = Geometria(os.path.join(cartelle.dati_utente(), "finestra.json"))
        self.ultima = f"http://127.0.0.1:{self.porta}"      # origine dell'ultima pagina del programma (per tornarci)
        self.finestra = None

    def crea(self, indirizzo):
        """crea la finestra sull'indirizzo di avvio (che non passa da nessuna riga di comando)"""
        s = self.m.wv.settings
        s["ALLOW_DOWNLOADS"] = False; s["ALLOW_FILE_URLS"] = False; s["IGNORE_SSL_ERRORS"] = False; s["REMOTE_DEBUGGING_PORT"] = None
        s["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = self.m.nome == "wkwebview"      # dove c'è il filtro del motore i link _blank passano da lì
        g = self.geo.iniziale(self.m.schermi())
        f = self.m.wv.create_window(TITOLO, url=indirizzo, min_size=MINIMA, background_color=SFONDO, text_select=True, draggable=True, zoomable=False, **g)
        f.events.before_show += lambda: installa_filtro(self.m.nome, f, self.nav)
        f.events.loaded += self.caricata
        self.geo.collega(f)
        self.finestra = f; ATTUALE[0] = self
        return f

    def caricata(self):
        """dopo ogni caricamento: una pagina fuori dal programma (sfuggita al filtro del motore, o su macOS) si lascia e si
        torna all'ultima pagina del programma (la sua pagina «/», che si ricollega con il cookie e la sessionStorage)"""
        f = self.finestra
        try: url = f.get_current_url()
        except Exception as e:                          # finestra chiusa nel frattempo
            log.debug("indirizzo della finestra non letto: %s", e); return
        if classifica(url, self.nav.porte()) == PROGRAMMA: self.ultima = origine(url)
        elif not self.nav.consenti(url): f.load_url(self.ultima + "/")

    def avvia(self):
        """apre la finestra e aspetta che si chiuda (thread principale: lo vuole pywebview)"""
        self.m.wv.start(gui=GUI[sistema()], debug=sviluppo(), private_mode=False, storage_path=os.path.join(cartelle.dati_utente(), "finestra"),
                        icon=risorse.percorso("icona.png"))

    def chiudi(self):
        """chiude la finestra da un altro thread («Esci» nella pagina, riavvio dopo un aggiornamento)"""
        if self.finestra is not None: self.finestra.destroy()


def chiudi_editor(editors, attesa=5):
    """chiusura ordinata degli editor lanciati da questa schermata ({progetto: (Popen, porta)}): ognuno salva (POST /api/save
    con il gettone del suo file di sessione), poi si termina; chi non si chiude entro `attesa` secondi si ferma"""
    vivi = [(pr, pt) for pr, pt in list(editors.values()) if pr.poll() is None]
    for pr, pt in vivi:
        g = sicurezza.gettone_di("editor", pt)
        try:
            if g: sicurezza.chiedi(pt, "/api/save", g, {}, timeout=15)
        except (OSError, ValueError) as e: log.warning("editor sulla porta %s non salvato alla chiusura: %s", pt, type(e).__name__)
    for pr, _ in vivi:
        try: pr.terminate()
        except OSError: pass  # nosec B110  # già chiuso
    for pr, _ in vivi:
        try: pr.wait(attesa)
        except subprocess.TimeoutExpired: pr.kill()


def esegui(m, srv, fermo):
    """finestra della schermata dei progetti `srv` (già creata, non ancora in ascolto). Restituisce quando la finestra si
    chiude, dopo aver chiuso editor e schermata"""
    from ..home import server as H
    f = Finestra(m, srv.server_address[1])
    esci, env = H.esci, os.environ.get("IMPAGINATORE_DIALOGHI")
    a_mano = bool(env) and not env.strip().lower().startswith("finestra:")      # «finestra:» ereditato: di una finestra di prima (rilancio dopo un aggiornamento)
    proprie = not a_mano and m.nome in DIALOGHI_PROPRI    # chi le ha scelte a mano (IMPAGINATORE_DIALOGHI) le tiene
    if proprie: os.environ["IMPAGINATORE_DIALOGHI"] = f"finestra:{f.porta}"                # per gli editor (Ponte)
    elif not a_mano: os.environ.pop("IMPAGINATORE_DIALOGHI", None)
    H.esci, H.FINESTRA = f.chiudi, True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        w = f.crea(srv.indirizzo_avvio())
        if proprie: dialoghi.imposta(dialoghi_finestra.DialoghiFinestra(w, m.wv.FileDialog))
        f.avvia()
    finally:
        f.geo.salva()
        chiudi_editor(H.EDITORS)
        fermo.set(); srv.shutdown(); srv.server_close()
        H.esci, H.FINESTRA = esci, False; dialoghi.imposta(None); ATTUALE[0] = None
        if env is None: os.environ.pop("IMPAGINATORE_DIALOGHI", None)
        else: os.environ["IMPAGINATORE_DIALOGHI"] = env
    return 0


def ospite(m, indirizzo, porta):
    """seconda finestra sulla schermata già in funzione sulla porta `porta` (il comando lanciato di nuovo): alla chiusura
    non ferma niente, la schermata è di un altro processo"""
    os.environ.pop(sicurezza.VARIABILE, None)
    f = Finestra(m, porta)
    f.crea(indirizzo)
    try: f.avvia()
    finally: f.geo.salva(); ATTUALE[0] = None
    return 0
