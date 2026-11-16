"""Finestra del programma (desktop, T-201) con un pywebview finto: nessuna finestra si apre, ogni sistema simulato con
sys.platform. La finestra vera (WebKitGTK sotto Xvfb) la prova test_finestra_vera in un processo a parte
(tests/prova_finestra.py), saltata se manca qualcosa. macOS e Windows veri non li prova nessun test."""
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import types

import pytest
from aiuti import attendi

from impaginatore import desktop, risorse, sicurezza
from impaginatore.desktop import dialoghi as D
from impaginatore.desktop import finestra as F
from impaginatore.desktop import geometria as G
from impaginatore.desktop import navigazione as N
from impaginatore.piattaforma import dialoghi, processi

SISTEMI = {"mac": "darwin", "windows": "win32", "linux": "linux"}
AVVIO = "http://127.0.0.1:8765/avvio?c=abc"


class Evento:
    """evento di pywebview: gestori aggiunti con +=; chiamarlo lo lancia"""

    def __init__(self): self.gestori = []

    def __iadd__(self, f):
        self.gestori.append(f); return self

    def __call__(self, *a): return [f(*a) for f in self.gestori]


class FintaFinestra:
    def __init__(self, titolo="t", **kw):
        self.titolo, self.kw, self.uid = titolo, kw, "master"
        self.events = types.SimpleNamespace(**{n: Evento() for n in ("before_show", "loaded", "moved", "resized", "maximized", "minimized", "restored", "closing")})
        self.localization, self.url, self.caricati, self.distrutta, self.scelte, self.risposta = {}, kw.get("url"), [], False, [], None
        self.x, self.y, self.width, self.height = 30, 40, 1300, 820

    def get_current_url(self): return self.url

    def load_url(self, u):
        self.caricati.append(u); self.url = u

    def destroy(self): self.distrutta = True

    def create_file_dialog(self, tipo, **kw):
        self.scelte.append((tipo, kw, dict(self.localization))); return self.risposta


@pytest.fixture
def sistema(monkeypatch):
    def imposta(nome): monkeypatch.setattr(sys, "platform", SISTEMI[nome])
    return imposta


@pytest.fixture
def wv(monkeypatch):
    """pywebview finto in sys.modules (anche dove quello vero è installato). start() lancia before_show, poi wv.durante(finestra)"""
    m = types.ModuleType("webview")
    m.settings = dict(OPEN_EXTERNAL_LINKS_IN_BROWSER=True, ALLOW_FILE_URLS=True, ALLOW_DOWNLOADS=True, IGNORE_SSL_ERRORS=True, REMOTE_DEBUGGING_PORT=9222)
    m.FileDialog = types.SimpleNamespace(OPEN=10, FOLDER=20, SAVE=30)
    m.finestre, m.avvii, m.durante, m.errore, m.gui = [], [], lambda f: None, None, None
    m.lib = types.SimpleNamespace(renderer="gtkwebkit2", get_screens=lambda: [types.SimpleNamespace(x=0, y=0, width=1920, height=1080)])

    def create_window(titolo, **kw):
        f = FintaFinestra(titolo, **kw); m.finestre.append(f); return f

    def start(**kw):
        m.avvii.append(kw); f = m.finestre[-1]; f.events.before_show(); m.durante(f)

    def initialize(gui):
        m.gui = gui
        if m.errore: raise m.errore
        return m.lib
    m.create_window, m.start = create_window, start
    guilib = types.ModuleType("webview.guilib"); guilib.initialize = initialize
    monkeypatch.setitem(sys.modules, "webview", m); monkeypatch.setitem(sys.modules, "webview.guilib", guilib)
    monkeypatch.setitem(sys.modules, "webview.platforms", None); monkeypatch.setitem(sys.modules, "webview.platforms.gtk", None)
    return m


@pytest.fixture
def gi(monkeypatch):
    """PyGObject finto: le versioni in gi.mancano non ci sono"""
    m = types.ModuleType("gi"); m.mancano, m.chieste = set(), []

    def require_version(nome, ver):
        m.chieste.append((nome, ver))
        if (nome, ver) in m.mancano: raise ValueError(f"{nome} {ver} non c'è")
    m.require_version = require_version
    monkeypatch.setitem(sys.modules, "gi", m)
    return m


@pytest.fixture
def accesa(monkeypatch, sistema):
    """finestra non spenta dall'ambiente dei test, su un Linux con uno schermo"""
    monkeypatch.delenv("IMPAGINATORE_FINESTRA"); monkeypatch.setenv("DISPLAY", ":0"); monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    sistema("linux")


@pytest.fixture
def aperti(monkeypatch):
    """indirizzi mandati al browser di sistema (non si apre)"""
    out = []
    monkeypatch.setattr(processi, "apri_browser", out.append)
    return out


# ------------------------------------------------------------------ motore(): finestra o browser
def test_spenta_dall_ambiente(capsys):
    assert F.motore() is None and "IMPAGINATORE_FINESTRA=no" in capsys.readouterr().err


def test_linux_senza_schermo(accesa, monkeypatch, capsys):
    monkeypatch.delenv("DISPLAY")
    assert F.motore() is None and "nessuno schermo" in capsys.readouterr().err


def test_senza_pywebview(accesa, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "webview", None)
    assert F.motore() is None and "extra «desktop»" in capsys.readouterr().err


def test_linux_senza_webkitgtk(accesa, wv, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "gi", None)
    assert F.motore() is None and "PyGObject e WebKit2GTK" in capsys.readouterr().err and wv.gui is None


def test_linux_webkit_4_0(accesa, wv, gi):
    gi.mancano.add(("WebKit2", "4.1"))
    m = F.motore()
    assert m.wv is wv and m.nome == "gtkwebkit2" and wv.gui == "gtk" and gi.chieste == [("Gtk", "3.0"), ("WebKit2", "4.1"), ("WebKit2", "4.0")]


def test_linux_senza_webkit(accesa, wv, gi, capsys):
    gi.mancano |= {("WebKit2", "4.1"), ("WebKit2", "4.0")}
    assert F.motore() is None and "PyGObject" in capsys.readouterr().err


def test_wayland_e_schermi(accesa, wv, gi, monkeypatch):
    monkeypatch.delenv("DISPLAY"); monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    m = F.motore()
    assert m.schermi() == [(0, 0, 1920, 1080)]
    m.lib.get_screens = lambda: 1 / 0
    assert m.schermi() == [], "senza schermi noti la posizione salvata non si controlla"


def test_windows(accesa, wv, sistema, capsys):
    sistema("windows")
    wv.lib.renderer = "edgechromium"
    assert F.motore().nome == "edgechromium" and wv.gui == "edgechromium"
    wv.lib.renderer = "mshtml"
    assert F.motore() is None and "mshtml non adatto" in capsys.readouterr().err, "mai Internet Explorer"
    wv.errore = RuntimeError("manca WebView2")
    assert F.motore() is None and "manca WebView2" in capsys.readouterr().err


def test_mac(accesa, wv, sistema, monkeypatch):
    sistema("mac"); monkeypatch.delenv("DISPLAY"); monkeypatch.setitem(sys.modules, "gi", None)
    wv.lib.renderer = "wkwebview"
    assert F.motore().nome == "wkwebview" and wv.gui == "cocoa", "su macOS niente schermo X né PyGObject"


def test_gettone_fuori_dall_ambiente(monkeypatch):
    monkeypatch.setenv(sicurezza.VARIABILE, "dal-riavvio")
    assert F.gettone() == "dal-riavvio" and sicurezza.VARIABILE not in os.environ, "i processi del motore della finestra non lo ereditano"
    g = F.gettone()
    assert len(g) >= 40 and sicurezza.VARIABILE not in os.environ


def test_strumenti_di_sviluppo(monkeypatch):
    assert not F.sviluppo()
    monkeypatch.setenv("IMPAGINATORE_FINESTRA_SVILUPPO", "1")
    assert F.sviluppo()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert not F.sviluppo(), "mai in un programma impacchettato"


# ------------------------------------------------------------------ navigazione
PORTE = {8765, 8860}


@pytest.mark.parametrize("url, tipo", [
    ("http://127.0.0.1:8765/", N.PROGRAMMA), ("http://127.0.0.1:8765/avvio?c=x", N.PROGRAMMA), ("http://127.0.0.1:8860/api/x", N.PROGRAMMA),
    ("about:blank", N.VUOTA), ("", N.VUOTA), (None, N.VUOTA),
    ("https://esempio.it/guida", N.ESTERNA), ("http://esempio.it", N.ESTERNA),
    ("http://127.0.0.1:9999/", N.VIETATA), ("http://127.0.0.1/", N.VIETATA), ("https://127.0.0.1:8765/", N.VIETATA),
    ("http://localhost:8765/", N.VIETATA), ("http://127.0.0.2:8765/", N.VIETATA), ("http://[::1]:8765/", N.VIETATA),
    ("http://0.0.0.0:8765/", N.VIETATA), ("http://app.localhost/", N.VIETATA), ("https://localhost/", N.VIETATA),
    ("http://127.0.0.1:8765@esempio.it/", N.VIETATA), ("http://u@127.0.0.1:8765/", N.VIETATA),
    ("http://127.0.0.1:99999/", N.VIETATA), ("http://[::1", N.VIETATA),
    ("file:///etc/passwd", N.VIETATA), ("javascript:alert(1)", N.VIETATA), ("data:text/html,x", N.VIETATA),
    ("blob:http://127.0.0.1:8765/x", N.VIETATA), ("https:///senza-host", N.VIETATA), ("ftp://esempio.it/", N.VIETATA),
])
def test_classifica(url, tipo):
    assert N.classifica(url, PORTE) == tipo


def test_porte_e_origine():
    sicurezza.scrivi_sessione("editor", 8860, "g")
    sicurezza.scrivi_sessione("home", 9000, "h")
    assert N.porte_programma("8765") == {8765, 8860}, "la schermata e gli editor in funzione, non le altre schermate"
    assert N.origine("http://127.0.0.1:8860/x?y=1") == "http://127.0.0.1:8860"


def test_consenti(aperti):
    nav = N.Navigazione(lambda: PORTE)
    assert nav.consenti("http://127.0.0.1:8765/") and nav.consenti("about:blank") and aperti == []
    assert not nav.consenti("file:///etc/passwd") and not nav.consenti("http://127.0.0.1:9999/") and aperti == []
    assert not nav.consenti("https://esempio.it/guida")
    attendi(lambda: aperti == ["https://esempio.it/guida"], 5, 0.01)


class Decisione:
    def __init__(self, uri): self.uri, self.ignorata = uri, False

    def ignore(self): self.ignorata = True

    def get_navigation_action(self):
        return types.SimpleNamespace(get_request=lambda: types.SimpleNamespace(get_uri=lambda: self.uri))


def test_filtro_gtk(monkeypatch, aperti):
    collegati = []
    tipi = types.SimpleNamespace(NAVIGATION_ACTION=0, NEW_WINDOW_ACTION=1, RESPONSE=2)
    gtk = types.ModuleType("webview.platforms.gtk")
    gtk.webkit = types.SimpleNamespace(PolicyDecisionType=tipi)
    gtk.BrowserView = types.SimpleNamespace(instances={"master": types.SimpleNamespace(webview=types.SimpleNamespace(connect=lambda s, f: collegati.append((s, f))))})
    piattaforme = types.ModuleType("webview.platforms"); piattaforme.gtk = gtk
    monkeypatch.setitem(sys.modules, "webview.platforms", piattaforme); monkeypatch.setitem(sys.modules, "webview.platforms.gtk", gtk)
    assert N.installa_filtro("gtkwebkit2", FintaFinestra(), N.Navigazione(lambda: PORTE))
    (segnale, decidi), = collegati
    assert segnale == "decide-policy"
    d = Decisione("http://127.0.0.1:8765/"); assert decidi(None, d, tipi.NAVIGATION_ACTION) is False and not d.ignorata
    d = Decisione("file:///etc/passwd"); assert decidi(None, d, tipi.NAVIGATION_ACTION) is True and d.ignorata
    d = Decisione("http://127.0.0.1:8765/"); assert decidi(None, d, tipi.NEW_WINDOW_ACTION) is True and d.ignorata, "finestre nuove: mai"
    d = Decisione("file:///x"); assert decidi(None, d, tipi.RESPONSE) is False and not d.ignorata, "le risposte le decide pywebview"
    assert aperti == []


def test_filtro_webview2(aperti):
    f = FintaFinestra(); f.native = types.SimpleNamespace(webview=types.SimpleNamespace(NavigationStarting=Evento()))
    assert N.installa_filtro("edgechromium", f, N.Navigazione(lambda: PORTE))
    a = types.SimpleNamespace(Uri="http://127.0.0.1:8860/", Cancel=False); f.native.webview.NavigationStarting(None, a)
    b = types.SimpleNamespace(Uri="http://127.0.0.1:1/", Cancel=False); f.native.webview.NavigationStarting(None, b)
    assert not a.Cancel and b.Cancel


def test_filtro_che_manca(wv, caplog):
    nav = N.Navigazione(lambda: PORTE)
    assert not N.installa_filtro("wkwebview", FintaFinestra(), nav), "macOS: solo il controllo dopo il caricamento"
    with caplog.at_level(logging.WARNING, logger="impaginatore.desktop"):
        assert not N.installa_filtro("gtkwebkit2", FintaFinestra(), nav)
        assert not N.installa_filtro("edgechromium", FintaFinestra(), nav)
    assert caplog.text.count("resta il controllo dopo il caricamento") == 2


# ------------------------------------------------------------------ geometria
def test_geometria_predefinita(tmp_path):
    g = G.Geometria(str(tmp_path / "finestra.json"))
    assert g.iniziale() == dict(width=1280, height=800, x=None, y=None, maximized=False)
    assert g.iniziale([(0, 0, 1920, 1080)]) == dict(width=1440, height=900, x=None, y=None, maximized=False)
    assert g.iniziale([(0, 0, 1280, 720)]) == dict(width=1088, height=700, x=None, y=None, maximized=False), "mai sotto la misura minima"


@pytest.mark.parametrize("contenuto, attesa", [
    (dict(larghezza=1500, altezza=950, x=100, y=50, massimizzata=True), dict(width=1500, height=950, x=100, y=50, maximized=True)),
    (dict(larghezza=1500, altezza=950, x=-1900, y=10), dict(width=1500, height=950, x=-1900, y=10, maximized=False)),     # secondo schermo a sinistra
    (dict(larghezza=True, altezza=500, x="1", y=2), dict(width=1440, height=900, x=None, y=None, maximized=False)),
    (dict(larghezza=30000, altezza=950, x=5000, y=50, massimizzata="sì"), dict(width=1440, height=950, x=None, y=None, maximized=False)),   # monitor staccato
    ([1, 2], dict(width=1440, height=900, x=None, y=None, maximized=False)),
])
def test_geometria_dal_file(tmp_path, contenuto, attesa):
    p = tmp_path / "finestra.json"; p.write_text(json.dumps(contenuto), encoding="utf-8")
    assert G.Geometria(str(p)).iniziale([(0, 0, 1920, 1080), (-1920, 0, 1920, 1080)]) == attesa


def test_geometria_senza_schermi_noti(tmp_path):
    p = tmp_path / "finestra.json"; p.write_text(json.dumps(dict(larghezza=1100, altezza=750, x=5000, y=50)), encoding="utf-8")
    assert G.Geometria(str(p)).iniziale() == dict(width=1100, height=750, x=5000, y=50, maximized=False)


def test_geometria_file_rovinato(tmp_path):
    p = tmp_path / "finestra.json"; p.write_text("{rotto", encoding="utf-8")
    assert G.Geometria(str(p)).iniziale()["width"] == 1280
    os.remove(p); p.mkdir()
    assert G.Geometria(str(p)).iniziale()["width"] == 1280, "illeggibile: si apre con la misura predefinita"


def test_geometria_segue_la_finestra(tmp_path):
    g = G.Geometria(str(tmp_path / "d" / "finestra.json"), ritardo=0.01); g.iniziale()
    f = FintaFinestra(); g.collega(f)
    f.events.moved(1, 2)
    attendi(lambda: g.dati == dict(larghezza=1300, altezza=820, x=30, y=40), 5, 0.01)
    f.width, f.x = 800, 70; f.events.resized(800, 820)
    attendi(lambda: g.dati["x"] == 70, 5, 0.01)
    assert g.dati["larghezza"] == 1300, "sotto la misura minima: si tiene la posizione, non la misura"
    f.events.maximized(); f.x = 0; f.events.moved(0, 0)
    assert g._timer is None and g.stato == "massimizzata", "massimizzata: si tiene la misura normale"
    f.events.minimized(); assert g.stato == "ridotta"
    f.events.restored(); assert g.stato == "normale"
    attendi(lambda: g.dati["x"] == 0, 5, 0.01)
    f.events.maximized()
    assert g.salva() == dict(larghezza=1300, altezza=820, x=0, y=40, massimizzata=True)
    assert json.loads((tmp_path / "d" / "finestra.json").read_text(encoding="utf-8"))["massimizzata"] is True
    assert G.Geometria(str(tmp_path / "d" / "finestra.json")).iniziale() == dict(width=1300, height=820, x=0, y=40, maximized=True)


def test_geometria_chiusura_e_riletture(tmp_path):
    g = G.Geometria(str(tmp_path / "finestra.json"), ritardo=60); g.iniziale()
    f = FintaFinestra(); g.collega(f)
    f.events.moved(); t = g._timer; f.events.resized()
    assert g._timer is t, "una rilettura sola per una serie di eventi"
    f.events.closing()
    assert g._timer is None and g.finestra is None and t.finished.is_set(), "chiusa: la rilettura in attesa si annulla"
    f.events.closing()                                          # senza rilettura in attesa
    g.rileggi(); assert g.dati["x"] is None, "finestra chiusa: niente da rileggere"

    class Rotta(FintaFinestra):
        @property
        def x(self): raise RuntimeError("finestra già chiusa")

        @x.setter
        def x(self, v): pass
    g.finestra = Rotta(); g.rileggi(); assert g.dati["x"] is None

    class CambiaStato(FintaFinestra):
        @property
        def height(self):
            g.stato = "massimizzata"; return 900

        @height.setter
        def height(self, v): pass
    g.finestra = CambiaStato(); g.rileggi(); assert g.dati["x"] is None, "massimizzata mentre si rileggeva: si scarta"
    g.stato = "ridotta"; g.finestra = FintaFinestra(); g.rileggi(); assert g.dati["x"] is None


def test_geometria_non_salvata(tmp_path, caplog):
    (tmp_path / "file").write_text("x", encoding="utf-8")
    g = G.Geometria(str(tmp_path / "file" / "finestra.json")); g.iniziale()
    with caplog.at_level(logging.WARNING, logger="impaginatore.desktop"):
        assert g.salva()["larghezza"] == 1280
    assert "non salvata" in caplog.text


# ------------------------------------------------------------------ la finestra
@pytest.fixture
def motore(wv):
    return F.Motore(wv, wv.lib)


def test_crea_e_avvia(motore, wv, home, sistema):
    sistema("linux")
    f = F.Finestra(motore, "8765")
    w = f.crea(AVVIO)
    assert wv.settings == dict(OPEN_EXTERNAL_LINKS_IN_BROWSER=False, ALLOW_FILE_URLS=False, ALLOW_DOWNLOADS=False, IGNORE_SSL_ERRORS=False, REMOTE_DEBUGGING_PORT=None)
    assert w.titolo == "Impaginatore" and w.kw == dict(url=AVVIO, min_size=(1024, 700), background_color="#2B2B2B", text_select=True, draggable=True, zoomable=False,
                                                     width=1440, height=900, x=None, y=None, maximized=False)
    assert F.ATTUALE[0] is f and w.events.before_show() == [False], "filtro del motore non installato (pywebview finto): resta il controllo dopo il caricamento"
    f.avvia()
    dati = os.environ["IMPAGINATORE_DATI"]
    assert wv.avvii == [dict(gui="gtk", debug=False, private_mode=False, storage_path=os.path.join(dati, "finestra"), icon=risorse.percorso("icona.png"))]
    assert os.path.isfile(risorse.percorso("icona.png")), "l'icona è nel pacchetto (brand/ non ci va)"
    f.chiudi(); assert w.distrutta
    F.ATTUALE[0] = None


def test_link_esterni_su_mac(motore, wv):
    motore.nome = "wkwebview"
    F.Finestra(motore, 8765).crea(AVVIO)
    assert wv.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] is True, "macOS: niente filtro del motore, i link _blank li apre pywebview nel browser"
    F.ATTUALE[0] = None


def test_controllo_dopo_il_caricamento(motore, aperti):
    sicurezza.scrivi_sessione("editor", 8860, "g")
    f = F.Finestra(motore, 8765); w = f.crea(AVVIO)
    w.url = "http://127.0.0.1:8860/"; w.events.loaded()
    assert f.ultima == "http://127.0.0.1:8860" and w.caricati == []
    w.url = "about:blank"; w.events.loaded(); assert w.caricati == []
    w.url = "file:///etc/passwd"; w.events.loaded()
    assert w.caricati == ["http://127.0.0.1:8860/"], "fuori dal programma: si torna all'ultima pagina del programma"
    w.url = "https://esempio.it/"; w.events.loaded()
    attendi(lambda: aperti == ["https://esempio.it/"], 5, 0.01)
    assert w.caricati[-1] == "http://127.0.0.1:8860/"
    w.get_current_url = lambda: 1 / 0; w.events.loaded()
    assert len(w.caricati) == 2, "finestra chiusa nel frattempo: niente"
    F.ATTUALE[0] = None
    F.Finestra(motore, 8765).chiudi()                            # nessuna finestra ancora: niente da chiudere


class Proc:
    def __init__(self, vivo=True, ostinato=False, rotto=False):
        self.vivo, self.ostinato, self.rotto, self.fatti = vivo, ostinato, rotto, []

    def poll(self): return None if self.vivo else 0

    def terminate(self):
        self.fatti.append("terminate")
        if self.rotto: raise OSError("già chiuso")

    def wait(self, t):
        self.fatti.append(("wait", t))
        if self.ostinato: raise subprocess.TimeoutExpired("editor", t)
        self.vivo = False

    def kill(self): self.fatti.append("kill")


def test_chiudi_editor(monkeypatch, caplog):
    chieste = []

    def chiedi(porta, percorso, gettone, corpo=None, timeout=3):
        chieste.append((porta, percorso, gettone, corpo, timeout))
        if porta == 3: raise OSError("rifiutata")
        return {"ok": True}
    monkeypatch.setattr(sicurezza, "chiedi", chiedi)
    for p in (1, 3): sicurezza.scrivi_sessione("editor", p, f"g{p}")
    a, b, c, d = Proc(), Proc(vivo=False), Proc(ostinato=True, rotto=True), Proc()
    with caplog.at_level(logging.WARNING, logger="impaginatore.desktop"):
        F.chiudi_editor({"/a": (a, 1), "/b": (b, 2), "/c": (c, 3), "/d": (d, 4)}, attesa=0.1)
    assert chieste == [(1, "/api/save", "g1", {}, 15), (3, "/api/save", "g3", {}, 15)], "salva chi ha il file di sessione"
    assert "porta 3 non salvato" in caplog.text
    assert a.fatti == ["terminate", ("wait", 0.1)] and b.fatti == [] and d.fatti == a.fatti
    assert c.fatti == ["terminate", ("wait", 0.1), "kill"], "chi non si chiude si ferma"


class FintoServer:
    server_address = ("127.0.0.1", 8765)

    def __init__(self): self.fatti = []

    def serve_forever(self): self.fatti.append("serve")

    def indirizzo_avvio(self): return AVVIO

    def shutdown(self): self.fatti.append("shutdown")

    def server_close(self): self.fatti.append("close")


def _esegui(motore, wv, home, monkeypatch, durante=None):
    import threading
    chiusi, visto = [], {}
    monkeypatch.setattr(F, "chiudi_editor", chiusi.append)
    esci = home.esci

    def guarda(f):
        visto.update(env=os.environ.get("IMPAGINATORE_DIALOGHI"), dialoghi=dialoghi.attuali(), finestra=home.FINESTRA, esci=home.esci)
        if durante: durante(f)
    wv.durante = guarda
    srv, fermo = FintoServer(), threading.Event()
    rc = None
    try: rc = F.esegui(motore, srv, fermo)
    finally:
        visto.update(rc=rc, chiusi=chiusi, srv=srv.fatti, fermo=fermo.is_set(), esci_dopo=home.esci is esci, finestra_dopo=home.FINESTRA,
                     env_dopo=os.environ.get("IMPAGINATORE_DIALOGHI", "-"), impostati=dialoghi._ATTUALE[0], attuale=F.ATTUALE[0])
    return visto


def test_esegui(motore, wv, home, monkeypatch):
    monkeypatch.delenv("IMPAGINATORE_DIALOGHI")
    v = _esegui(motore, wv, home, monkeypatch)
    assert v["env"] == "finestra:8765" and isinstance(v["dialoghi"], D.DialoghiFinestra) and v["finestra"] is True
    assert v["esci"].__self__.porta == 8765 and v["esci"].__name__ == "chiudi", "«Esci» nella pagina chiude la finestra"
    assert v["rc"] == 0 and v["chiusi"] == [home.EDITORS] and [x for x in v["srv"] if x != "serve"] == ["shutdown", "close"] and v["fermo"]
    assert v["esci_dopo"] and v["finestra_dopo"] is False and v["env_dopo"] == "-" and v["impostati"] is None and v["attuale"] is None
    assert os.path.isfile(os.path.join(os.environ["IMPAGINATORE_DATI"], "finestra.json"))


def test_esegui_dialoghi_scelti_a_mano(motore, wv, home, monkeypatch):
    v = _esegui(motore, wv, home, monkeypatch)
    assert v["env"] == "nessuno" and isinstance(v["dialoghi"], dialoghi.Nessuno) and v["env_dopo"] == "nessuno"


def test_esegui_windows_dialoghi_di_sistema(motore, wv, home, monkeypatch):
    monkeypatch.delenv("IMPAGINATORE_DIALOGHI"); motore.nome = "edgechromium"
    monkeypatch.setattr(dialoghi, "predefiniti", lambda finestra=True: dialoghi.Tk())
    v = _esegui(motore, wv, home, monkeypatch)
    assert v["env"] is None and isinstance(v["dialoghi"], dialoghi.Tk) and v["env_dopo"] == "-"


@pytest.mark.parametrize("nome, durante", [("gtkwebkit2", "finestra:8765"), ("edgechromium", None)])
def test_esegui_dopo_un_rilancio(motore, wv, home, monkeypatch, nome, durante):
    """IMPAGINATORE_DIALOGHI=finestra:<porta> ereditato dalla finestra di prima (rilancio dopo un aggiornamento) non è una
    scelta a mano: la schermata chiederebbe le finestre di scelta a sé stessa"""
    monkeypatch.setenv("IMPAGINATORE_DIALOGHI", "finestra:9999"); motore.nome = nome
    v = _esegui(motore, wv, home, monkeypatch)
    assert v["env"] == durante and not isinstance(v["dialoghi"], D.Ponte) and v["env_dopo"] == "finestra:9999"


def test_esegui_errore_della_finestra(motore, wv, home, monkeypatch):
    with pytest.raises(RuntimeError):
        _esegui(motore, wv, home, monkeypatch, durante=lambda f: (_ for _ in ()).throw(RuntimeError("motore caduto")))
    assert home.FINESTRA is False and F.ATTUALE[0] is None, "anche dopo un errore la schermata si chiude e tutto torna com'era"


def test_ospite(motore, wv, monkeypatch):
    monkeypatch.setenv(sicurezza.VARIABILE, "di-un-altro")
    assert F.ospite(motore, AVVIO, 8765) == 0
    assert wv.finestre[-1].kw["url"] == AVVIO and len(wv.avvii) == 1 and F.ATTUALE[0] is None and sicurezza.VARIABILE not in os.environ


# ------------------------------------------------------------------ finestre di scelta
def test_dialoghi_della_finestra(wv):
    f = FintaFinestra(); d = D.DialoghiFinestra(f, wv.FileDialog)
    f.risposta = ("/foto/cliente/",)
    assert d.scegli_cartella("Scegli la cartella con le foto") == os.path.normpath("/foto/cliente")
    f.risposta = ("/x/album.zip",)
    assert d.scegli_zip() == os.path.normpath("/x/album.zip")
    f.risposta = ("/f/a.jpg", "", "/f/b.png")
    assert d.scegli_percorsi() == [os.path.normpath("/f/a.jpg"), os.path.normpath("/f/b.png")]
    f.risposta = None
    assert d.scegli_cartella() == "" and d.scegli_percorsi() == [], "annullata"
    assert f.scelte[0] == (20, {}, {"linux.openFolder": "Scegli la cartella con le foto"})
    assert f.scelte[1] == (10, dict(file_types=("ZIP (*.zip;*.ZIP)",)), {"linux.openFolder": "Scegli la cartella con le foto", "linux.openFile": "Scegli il file ZIP del progetto"})
    assert f.scelte[2][:2] == (10, dict(allow_multiple=True, file_types=(D.FILTRO_FOTO,))) and f.scelte[2][2]["linux.openFiles"] == "Scegli le foto"
    assert "*.heic" in D.FILTRO_FOTO and D.FILTRO_FOTO.startswith("Foto (*.jpg;")


class Scelte(dialoghi.Dialoghi):
    def __init__(self, r): self.r, self.chieste = r, []

    def _scegli(self, tipo, messaggio):
        self.chieste.append((tipo, messaggio)); return list(self.r)


def test_scegli_per_gli_editor():
    s = Scelte(["/foto"]); dialoghi.imposta(s)
    assert D.scegli("cartella", "Cartella") == ["/foto"] and D.scegli("zip", None) == ["/foto"] and D.scegli("foto", "x" * 500) == ["/foto"]
    assert s.chieste == [("cartella", "Cartella"), ("zip", ""), ("foto", "x" * 200)]
    s.r = [""]
    assert D.scegli("cartella", "") == [] and D.scegli("zip", "") == []
    with pytest.raises(ValueError, match="sconosciuta"): D.scegli("tutto", "")
    dialoghi.imposta(D.Ponte(8765))
    with pytest.raises(ValueError, match="non apre finestre di scelta sue"): D.scegli("cartella", "")


def test_ponte(home_srv, monkeypatch, caplog):
    s = Scelte(["/foto/cliente"]); dialoghi.imposta(s)
    p = D.Ponte(home_srv.porta)
    with caplog.at_level(logging.WARNING, logger="impaginatore.desktop"):
        assert p.scegli_cartella("Cartella") == "", "finestra del programma non aperta: le finestre del sistema (qui: nessuna)"
    assert "uso quella del sistema" in caplog.text and s.chieste == []
    monkeypatch.setattr(home_srv.modulo, "FINESTRA", True)
    assert p.scegli_cartella("Cartella") == "/foto/cliente" and p.scegli_percorsi(messaggio="Foto") == ["/foto/cliente"]
    assert s.chieste == [("cartella", "Cartella"), ("foto", "Foto")], "la scelta la fa la schermata, con le sue finestre"
    assert D.Ponte(1).scegli_zip() == "", "nessuna schermata su quella porta: le finestre del sistema"


def test_api_dialogo(home_srv, monkeypatch):
    dialoghi.imposta(Scelte(["/a"]))
    ok, r = home_srv.prova("/api/dialogo", {"tipo": "cartella", "messaggio": "m"})
    assert not ok and "non è aperta" in r["errore"]
    monkeypatch.setattr(home_srv.modulo, "FINESTRA", True)
    assert home_srv.post("/api/dialogo", {"tipo": "foto", "messaggio": "m"}) == {"percorsi": ["/a"]}
    ok, r = home_srv.prova("/api/dialogo", {"tipo": "../x"})
    assert not ok and "sconosciuta" in r["errore"]
    assert home_srv.codice("/api/dialogo", {"tipo": "foto"}, **{"X-Impaginatore-Gettone": None}) == 401, "solo con il gettone"


def test_predefiniti_nell_editor(monkeypatch, sistema):
    monkeypatch.setenv("IMPAGINATORE_DIALOGHI", "finestra:8765")
    p = dialoghi.predefiniti()
    assert isinstance(p, D.Ponte) and p.porta == 8765 and isinstance(dialoghi.attuali(), D.Ponte)
    sistema("mac")
    assert isinstance(dialoghi.predefiniti(finestra=False), dialoghi.Mac), "il ripiego del Ponte: le finestre del sistema"
    monkeypatch.setenv("IMPAGINATORE_DIALOGHI", "finestra:abc")
    assert isinstance(dialoghi.predefiniti(), dialoghi.Mac)


# ------------------------------------------------------------------ il comando
def test_main_con_la_finestra(home, monkeypatch, tmp_path):
    chiamate = []

    def esegui(m, srv, fermo):
        chiamate.append((m, srv.sessione.gettone)); fermo.set(); srv.server_close(); return 0
    monkeypatch.setattr(desktop, "motore", lambda: "M"); monkeypatch.setattr(desktop, "gettone", lambda: "gettone-della-finestra")
    monkeypatch.setattr(desktop, "esegui", esegui)
    monkeypatch.setattr(home, "apri_browser", lambda u: pytest.fail("con la finestra il browser non si apre"))
    assert home.main(["--porta", "0", "--progetti", str(tmp_path / "P")]) == 0
    assert chiamate == [("M", "gettone-della-finestra")]
    assert sicurezza.VARIABILE not in os.environ, "con la finestra il gettone non resta nell'ambiente"


def test_main_con_il_browser(home, monkeypatch, tmp_path):
    from impaginatore.servizio import ServerLocale
    aperti = []
    monkeypatch.setattr(desktop, "motore", lambda: pytest.fail("--browser: la finestra non si cerca nemmeno"))
    monkeypatch.setattr(home, "apri_browser", aperti.append)
    monkeypatch.setattr(ServerLocale, "serve_forever", lambda self: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert home.main(["--porta", "0", "--progetti", str(tmp_path / "P"), "--browser"]) == 0 and len(aperti) == 1


def test_secondo_avvio_apre_un_altra_finestra(home_srv, monkeypatch):
    from impaginatore.home import server
    ospiti = []
    monkeypatch.setattr(desktop, "motore", lambda: "M")
    monkeypatch.setattr(desktop, "ospite", lambda m, a, p: ospiti.append((m, a, p)) or 0)
    monkeypatch.setattr(processi, "apri_browser", lambda u: pytest.fail("c'è la finestra"))
    assert server.main(["--porta", str(home_srv.porta)]) == 0
    (m, a, p), = ospiti
    assert m == "M" and a.startswith(f"http://127.0.0.1:{home_srv.porta}/avvio?c=") and p == home_srv.porta


def test_riavvio_con_la_finestra(home, monkeypatch):
    lanci = []
    monkeypatch.delenv("IMPAGINATORE_SENZA_RIAVVIO")
    monkeypatch.setattr(processi, "rilancia_dopo", lambda argv, r, gettone=None: lanci.append(argv))
    monkeypatch.setattr(home, "esci", lambda: None)
    monkeypatch.setattr(home.threading, "Thread", lambda target, daemon: types.SimpleNamespace(start=target))
    monkeypatch.setattr(home.time, "sleep", lambda s: None)
    monkeypatch.setattr(home, "FINESTRA", True)
    home.riavvia_programma()
    assert lanci and "--no-browser" not in lanci[0], "il programma riavviato riapre la sua finestra"


# ------------------------------------------------------------------ la finestra vera
XVFB = shutil.which("xvfb-run")
PRONTA = sys.platform.startswith("linux") and XVFB and importlib.util.find_spec("webview") and importlib.util.find_spec("gi")


@pytest.mark.finestra
@pytest.mark.skipif(not PRONTA, reason="serve Linux con xvfb-run, pywebview (extra «desktop») e PyGObject con WebKit2GTK")
def test_finestra_vera(tmp_path):
    """WebKitGTK sotto Xvfb: schermata, editor nella stessa finestra, finestre di scelta, pagine fuori dal programma
    fermate, chiusura ordinata (tests/prova_finestra.py)"""
    env = {k: v for k, v in os.environ.items() if k not in ("IMPAGINATORE_FINESTRA", "IMPAGINATORE_DIALOGHI")}
    env["BROWSER"] = "true"                                     # se qualcosa sfuggisse al finto apri_browser: nessun browser vero
    prova = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prova_finestra.py")
    r = subprocess.run([XVFB, "-a", sys.executable, prova, str(tmp_path)], env=env, capture_output=True, text=True, encoding="utf-8", timeout=600)
    righe = [x for x in r.stdout.splitlines() if x.startswith("ESITO ")]
    assert righe, r.stdout[-3000:] + r.stderr[-3000:]
    e = json.loads(righe[-1][6:])
    if "saltato" in e: pytest.skip(e["saltato"])
    assert "errore" not in e, e
    home = e["home"]
    assert e["titolo"] == "Impaginatore" and e["gettone_home"] == e["gettone_editor"] == 43, "le pagine sono collegate (gettone nella sessionStorage)"
    assert e["gettone_ambiente"] is False and e["gettone_figli"] and not any(e["gettone_figli"]), "i processi di WebKit non hanno il gettone"
    assert e["scelta_home"] == str(tmp_path) and e["titolo_scelta_home"] == ["Scegli la cartella di prova"]
    assert e["scelta_editor"] == [str(tmp_path)] and e["titolo_scelta_editor"] == ["Scegli la cartella"], "l'editor la chiede alla schermata"
    assert e["editor"] != home and all(e[k] == e["editor"] for k in ("dopo_0", "dopo_1", "dopo_2", "dopo_blank")), "la finestra resta nel programma"
    assert e["richieste_altro"] == [] and e["fuori"] == ["https://esempio.invalid/guida"], "i siti nel browser di sistema, gli altri servizi locali da nessuna parte"
    assert e["ritorno"] == home and e["rc"] == 0 and e["editor_chiusi"] == [True] and e["geometria"]
