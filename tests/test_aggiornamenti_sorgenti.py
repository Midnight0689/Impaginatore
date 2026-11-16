"""Da dove arrivano le versioni (T-207): API delle release di GitHub (con una rete finta: nessuna richiesta vera), cartella
finta, regole delle richieste (solo https, host ammessi, niente dati dell'utente, limiti di misura)."""
import email.message
import io
import json
import socket
import ssl
import urllib.error
import urllib.request

import pytest

from impaginatore import __version__
from impaginatore.aggiornamenti import Rifiutato, sorgenti

API = "https://api.github.com/repos/prova/impaginatore/releases/latest"


class Risposta(io.BytesIO):
    def __init__(self, corpo, lunghezza=None):
        super().__init__(corpo); self.headers = email.message.Message()
        if lunghezza is not None: self.headers["Content-Length"] = str(lunghezza)


class Rete:
    """APRI_RETE finto: registra le richieste e risponde da un dizionario {url: bytes | eccezione}"""

    def __init__(self, risposte): self.risposte, self.richieste = risposte, []

    def open(self, req, timeout=None):
        self.richieste.append((req, timeout))
        r = self.risposte[req.full_url]
        if isinstance(r, BaseException): raise r
        return Risposta(r)


def _release(**cambia):
    j = dict(tag_name="v2.0.1", draft=False, prerelease=False, published_at="2026-12-01T10:00:00Z", assets=[
        dict(name="manifesto.json", size=3, state="uploaded", browser_download_url="https://github.com/prova/impaginatore/releases/download/v2.0.1/manifesto.json", digest="sha256:" + "a" * 64),
        dict(name="../fuori", size=3, state="uploaded", browser_download_url="https://github.com/x"),
        dict(name="senza-url", size=3, state="uploaded"), dict(name="misura", size="3", state="uploaded", browser_download_url="https://github.com/x"),
        dict(name="a-meta", size=3, state="starter", browser_download_url="https://github.com/x"), "non un asset",
        dict(name="firma.sig", size=129, browser_download_url="https://github.com/prova/impaginatore/releases/download/v2.0.1/firma.sig", digest=None)])
    j.update(cambia)
    return json.dumps(j).encode()


@pytest.fixture
def rete(monkeypatch):
    r = Rete({})
    monkeypatch.setattr(sorgenti, "APRI_RETE", r)
    return r


def test_richieste_senza_dati_dell_utente(rete):
    """solo la versione del programma e il tipo accettato: niente gettone, cookie, nomi di file o percorsi"""
    rete.risposte[API] = _release()
    r = sorgenti.SorgenteGitHub("prova/impaginatore").ultimo()
    req, tempo = rete.richieste[0]
    assert dict(req.header_items()) == {"User-agent": f"Impaginatore/{__version__}", "Accept": "application/vnd.github+json", "X-github-api-version": sorgenti.VERSIONE_API}
    assert req.data is None and req.get_method() == "GET" and tempo == sorgenti.TEMPO
    assert r.etichetta == "v2.0.1" and r.pubblicata == "2026-12-01T10:00:00Z" and sorted(r.asset) == ["firma.sig", "manifesto.json"], "gli asset strani si ignorano"
    assert r.asset["manifesto.json"] == sorgenti.Asset("manifesto.json", "https://github.com/prova/impaginatore/releases/download/v2.0.1/manifesto.json", 3, "sha256:" + "a" * 64)
    assert r.asset["firma.sig"].digest is None
    rete.risposte[r.asset["manifesto.json"].url] = b"abc"
    assert sorgenti.SorgenteGitHub("prova/impaginatore").leggi(r.asset["manifesto.json"], 10) == b"abc"
    assert dict(rete.richieste[1][0].header_items()) == {"User-agent": f"Impaginatore/{__version__}", "Accept": "application/octet-stream"}


def test_canale_non_configurato_nessuna_richiesta(rete):
    assert sorgenti.REPOSITORY == "", "il repository delle release lo sceglie il titolare (AGGIORNAMENTI.md)"
    s = sorgenti.SorgenteGitHub()
    assert not s.configurata and s.ultimo() is None and rete.richieste == []
    assert sorgenti.SorgenteGitHub(" a/b ").repository == "a/b" and sorgenti.Sorgente.configurata is False
    for nome in ("a", "a/b/c", "-a/b", "a/b c", "a/" + "b" * 101, "../b"):
        with pytest.raises(Rifiutato, match="non è valido"): sorgenti.SorgenteGitHub(nome).ultimo()
    assert rete.richieste == []
    for m, a in (("ultimo", ()), ("scarica", (None, "", 1)), ("leggi", (None, 1))):
        with pytest.raises(NotImplementedError): getattr(sorgenti.Sorgente(), m)(*a)


@pytest.mark.parametrize("risposta, esito", [
    (urllib.error.HTTPError(API, 404, "Not Found", None, None), None),
    (_release(draft=True), None), (_release(prerelease=True), None),
    (urllib.error.HTTPError(API, 403, "rate limit", None, None), "Non riesco a raggiungere il server degli aggiornamenti (HTTP 403)"),
    (urllib.error.URLError(ssl.SSLCertVerificationError("certificate verify failed")), "certificate verify failed"),
    (urllib.error.URLError("rimando non https"), "rimando non https"), (socket.timeout(), "(TimeoutError)"), (ConnectionResetError(), "(ConnectionResetError)"),
    (b"\xff", "Risposta non valida"), (b"{non json", "Risposta non valida"), (b"[]", "Risposta non valida"), (json.dumps(dict(tag_name=1, assets=[])).encode(), "Risposta non valida"),
    (json.dumps(dict(tag_name="v", assets={})).encode(), "Risposta non valida"),
])
def test_risposte_dell_api(rete, risposta, esito):
    rete.risposte[API] = risposta
    s = sorgenti.SorgenteGitHub("prova/impaginatore")
    if esito is None: assert s.ultimo() is None
    else:
        with pytest.raises(Rifiutato, match=esito.replace("(", r"\(").replace(")", r"\)")): s.ultimo()


def test_risposta_troppo_grande(rete, monkeypatch):
    monkeypatch.setattr(sorgenti, "MAX_RISPOSTA", 10)
    rete.risposte[API] = b"x" * 11
    with pytest.raises(Rifiutato, match="più grande del previsto"): sorgenti.SorgenteGitHub("prova/impaginatore").ultimo()
    with pytest.raises(Rifiutato, match="più grande"): sorgenti.leggi_limitato(Risposta(b"", lunghezza=11), 10), "lo dice già l'intestazione"
    assert sorgenti.leggi_limitato(Risposta(b"abc", lunghezza="x"), 10) == b"abc"
    f = io.BytesIO(); assert sorgenti.leggi_limitato(Risposta(b"abcd" * 30000), 10 ** 6, f) == 120000 and f.getvalue() == b"abcd" * 30000


def test_scaricamento(rete, tmp_path):
    s = sorgenti.SorgenteGitHub("prova/impaginatore"); u = "https://github.com/prova/impaginatore/releases/download/v2.0.1/p.whl"
    rete.risposte[u] = b"12345"
    assert s.scarica(sorgenti.Asset("p.whl", u, 5), str(tmp_path / "p"), 5) == 5 and (tmp_path / "p").read_bytes() == b"12345"
    with pytest.raises(Rifiutato, match="più grande"): s.scarica(sorgenti.Asset("p.whl", u, 6), str(tmp_path / "q"), 5)
    with pytest.raises(Rifiutato, match="più grande"): s.scarica(sorgenti.Asset("p.whl", u, 4), str(tmp_path / "q"), 4), "GitHub dice 4, ne arrivano 5"
    rete.risposte[u] = urllib.error.HTTPError(u, 404, "x", None, None)
    with pytest.raises(Rifiutato, match="incompleta"): s.leggi(sorgenti.Asset("p.whl", u, 5), 5)
    for url in ("http://github.com/x", "https://esempio.it/x", "https://user:pw@github.com/x", "https://github.com:8443/x", "ftp://github.com/x", "https://github.com.esempio.it/x"):
        with pytest.raises(Rifiutato, match="non sicuro"): s.leggi(sorgenti.Asset("x", url, 1), 5)
    with pytest.raises(Rifiutato, match="non sicuro"): sorgenti.controlla_url(None)
    assert sorgenti.controlla_url("https://github.com:443/x").hostname == "github.com"
    assert len(rete.richieste) == 3, "gli indirizzi non ammessi non partono"


def test_rete_vera_configurata_bene():
    """certificato e nome dell'host verificati; i rimandi solo verso https (la CDN degli asset di GitHub)"""
    assert sorgenti.CONTESTO.verify_mode == ssl.CERT_REQUIRED and sorgenti.CONTESTO.check_hostname
    https = [h for h in sorgenti.APRI_RETE.handlers if isinstance(h, urllib.request.HTTPSHandler)]
    assert https and all(h._context is sorgenti.CONTESTO for h in https)
    rimandi = [h for h in sorgenti.APRI_RETE.handlers if isinstance(h, urllib.request.HTTPRedirectHandler)]
    assert len(rimandi) == 1 and isinstance(rimandi[0], sorgenti._SoloHttps)
    req = urllib.request.Request("https://github.com/x/releases/download/v1/a")
    nuova = rimandi[0].redirect_request(req, None, 302, "Found", {}, "https://objects.githubusercontent.com/a?firma=1")
    assert nuova.full_url.startswith("https://objects.githubusercontent.com/")
    with pytest.raises(urllib.error.URLError, match="non https"): rimandi[0].redirect_request(req, None, 302, "Found", {}, "http://objects.githubusercontent.com/a")


def test_sorgente_finta(tmp_path):
    s = sorgenti.SorgenteFinta(str(tmp_path))
    assert s.configurata and s.ultimo() is None, "nessuna release nella cartella"
    (tmp_path / "releases").mkdir(); (tmp_path / "releases" / "latest.json").write_bytes(_release())
    (tmp_path / "manifesto.json").write_bytes(b"abc")
    r = s.ultimo(); assert s.leggi(r.asset["manifesto.json"], 3) == b"abc"
    with pytest.raises(Rifiutato, match="incompleta"): s.leggi(r.asset["firma.sig"], 200)
    with pytest.raises(Rifiutato, match="non sicuro"): s.leggi(sorgenti.Asset("x", "https://github.com/x/..", 1), 5)
    with pytest.raises(Rifiutato, match="più grande"): s.leggi(r.asset["manifesto.json"]._replace(dimensione=2), 2)
