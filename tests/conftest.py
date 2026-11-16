"""Fixture comuni. Ogni test gira con una casa finta: niente di quello che fa tocca la cartella dell'utente, nessuna
finestra di sistema si apre (IMPAGINATORE_DIALOGHI=nessuno), né quella del programma (IMPAGINATORE_FINESTRA=no), nessun
aggiornamento parte, nessun riavvio vero."""
import os
import shutil
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aiuti import Client, crea_foto, progetto_152  # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATI = os.path.join(RADICE, "tests", "dati")


@pytest.fixture(autouse=True)
def casa(tmp_path, monkeypatch):
    """casa finta + variabili che tengono i test lontani da dati veri, finestre e rete"""
    h = tmp_path / "casa"; h.mkdir()
    for k, v in dict(HOME=h, USERPROFILE=h, APPDATA=h / "AppData" / "Roaming", LOCALAPPDATA=h / "AppData" / "Local",
                     XDG_DATA_HOME=h / ".local" / "share", XDG_CACHE_HOME=h / ".cache", XDG_CONFIG_HOME=h / ".config",
                     IMPAGINATORE_PROGETTI=tmp_path / "Progetti", IMPAGINATORE_DATI=h / "dati", IMPAGINATORE_CACHE=h / "cache").items():
        monkeypatch.setenv(k, str(v))
    monkeypatch.setenv("IMPAGINATORE_DIALOGHI", "nessuno")
    monkeypatch.setenv("IMPAGINATORE_FINESTRA", "no")                     # niente finestra del programma (desktop): il browser, intercettato
    monkeypatch.setenv("IMPAGINATORE_AGGIORNAMENTI", "no")
    monkeypatch.setenv("IMPAGINATORE_SENZA_RIAVVIO", "1")
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")                       # lingua «del sistema»: i test non dipendono dal computer (T-206)
    for k in ("IMPAGINATORE_GETTONE", "IMPAGINATORE_MAX_MPIXEL", "IMPAGINATORE_REGISTRO"):      # ogni server di prova ha il suo gettone
        monkeypatch.setenv(k, ""); monkeypatch.delenv(k)                    # (così anche quello che main() scrive nell'ambiente sparisce dopo il test)
    from impaginatore.piattaforma import dialoghi
    dialoghi.imposta(None)
    yield h
    dialoghi.imposta(None)


@pytest.fixture(scope="session")
def chiavi_prova():
    """coppia di firma delle licenze generata per questa sessione di test (licenze/chiave.py ha solo un segnaposto)"""
    import secrets
    from aiuti import Chiavi
    return Chiavi(secrets.token_bytes(32))


class Licenza:
    """licenza del test: cartella dei file della licenza (fuori dalla casa finta) e chiavi della sessione"""

    def __init__(self, cartella, chiavi, cartella_vera, pubbliche_vere):
        self.cartella, self.chiavi, self.cartella_vera, self.pubbliche_vere = cartella, chiavi, cartella_vera, pubbliche_vere

    def usa(self, testo):
        """salva questa chiave come se l'utente l'avesse attivata (None: nessuna chiave)"""
        f = self.cartella / "chiave.txt"
        if testo is None: f.unlink(missing_ok=True)
        else: f.write_text(testo + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def licenza(casa, monkeypatch, tmp_path_factory, chiavi_prova):
    """ogni test gira con una licenza Studio (tutte le funzioni, nessuna filigrana) firmata con la coppia della sessione.
    I file della licenza stanno in una cartella a parte: la casa finta resta come la vogliono i test che la guardano.
    Gli editor lanciati come processi a parte non vedono la chiave della sessione: per loro vale la prova gratuita."""
    from impaginatore import licenze
    from impaginatore.licenze import chiave as K
    d = tmp_path_factory.mktemp("licenza")
    lic = Licenza(d, chiavi_prova, licenze.cartella, K.CHIAVI_PUBBLICHE)
    monkeypatch.setattr(K, "CHIAVI_PUBBLICHE", {1: K.Pubblica(chiavi_prova.pubblica.hex())})
    monkeypatch.setattr(licenze, "cartella", lambda: str(d))
    lic.usa(chiavi_prova.studio)
    return lic


@pytest.fixture(scope="session")
def foto_campione(tmp_path_factory):
    """le 10 foto dello scenario, create una volta sola"""
    d = tmp_path_factory.mktemp("foto_campione")
    crea_foto(str(d))
    return str(d)


@pytest.fixture
def home(tmp_path):
    """modulo della schermata dei progetti, configurato su una cartella temporanea (senza server)"""
    from impaginatore import aggiornamenti
    from impaginatore.home import server as H
    H.configura(str(tmp_path / "Progetti"), 0, aggiornamenti.NonDisponibili())
    H.EDITORS.clear(); H.RADICI.scelte.clear()
    yield H
    for pr, _ in list(H.EDITORS.values()):
        try: pr.terminate(); pr.wait(10)
        except Exception: pass
    H.EDITORS.clear()


@pytest.fixture
def home_srv(home, monkeypatch):
    """schermata dei progetti in questo processo, su una porta libera"""
    uscite = []
    monkeypatch.setattr(home, "esci", lambda: uscite.append(1))
    srv = home.crea_server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = Client(srv.server_address[1], srv.sessione.gettone); c.modulo = home; c.uscite = uscite; c.srv = srv
    yield c
    srv.shutdown(); srv.server_close()


@pytest.fixture
def prj(tmp_path):
    """il progetto dello scenario 1.5.2 (cornici libere, angoli, testi), pronto per gli script del motore"""
    from impaginatore import formato
    p = tmp_path / "Album àè"; crea_foto(str(p / "Foto"))
    shutil.copy(os.path.join(DATI, "progetto_152", "spec.py"), p / "spec.py")
    formato.scrivi_json(str(p / "progetto.json"), progetto_152(p), indent=2, ensure_ascii=False)
    return str(p)


@pytest.fixture
def progetto(home, foto_campione):
    """progetto nuovo («Prova», 60 x 22,5 cm) con le 10 foto nella sua cartella Foto"""
    p = home.nuovo({"nome": "Prova", "w": "60", "h": "22,5"})
    for f in sorted(os.listdir(foto_campione)): shutil.copy2(os.path.join(foto_campione, f), os.path.join(p, "Foto", f))
    return p


def _avvia_editor(path, monkeypatch):
    from impaginatore.editor import server as E
    riavvii = []
    monkeypatch.setattr(E, "riavvia_processo", lambda: riavvii.append(1))
    E.RADICI.scelte.clear()                                   # cartelle scelte con le finestre: valgono per la sessione dell'editor
    E.inizializza(path, home="http://127.0.0.1:9")
    srv = E.crea_server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = Client(srv.server_address[1], srv.sessione.gettone); c.E = E; c.progetto = path; c.riavvii = riavvii; c.srv = srv
    return c


@pytest.fixture
def editor(progetto, monkeypatch):
    """editor del progetto in questo processo, su una porta libera (riavvio finto: conta le richieste)"""
    c = _avvia_editor(progetto, monkeypatch)
    yield c
    c.srv.shutdown(); c.srv.server_close(); c.E.ferma()


@pytest.fixture
def apri_editor(monkeypatch):
    """apre l'editor su un progetto qualsiasi (per i progetti preparati dal test)"""
    aperti = []

    def apri(path):
        c = _avvia_editor(path, monkeypatch); aperti.append(c); return c
    yield apri
    for c in aperti:
        c.srv.shutdown(); c.srv.server_close(); c.E.ferma()
