"""Da dove arrivano le versioni nuove (T-207): le release di un repository GitHub, o una cartella che le imita.

    Sorgente          interfaccia: ultimo() -> Rilascio | None (nessuna versione pubblicata), scarica(asset, percorso, massimo)
    SorgenteGitHub    API pubblica delle release: GET https://api.github.com/repos/<repository>/releases/latest
                      (l'ultima release pubblicata che non è una bozza né una «pre-release»), poi gli asset dai loro
                      browser_download_url. REPOSITORY è vuoto finché il titolare non lo sceglie: allora non parte nessuna
                      richiesta di rete (configurata è False)
    SorgenteFinta     la stessa cosa da una cartella locale: <cartella>/releases/latest.json con la risposta dell'API e gli
                      asset accanto (<cartella>/<nome>). Nessuna rete. Si accende con IMPAGINATORE_AGGIORNAMENTI_FINTI
                      (prove a mano) e la usano i test; la firma del manifesto si controlla lo stesso (firmati.py)

Quello che arriva da qui NON è fidato: nome della release, testo, URL e misure servono solo a trovare i file. Ciò che conta
(versione, novità, sha256, misure) sta nel manifesto firmato, che firmati.py verifica prima di usarlo.

Regole delle richieste (SICUREZZA.md, «Aggiornamenti»): solo https verso api.github.com e github.com, rimandi solo verso
https, certificato verificato (contesto ssl predefinito), tempo e misura massimi, intestazioni con la sola versione del
programma (User-Agent) e i tipi accettati: nessun gettone, nessun cookie, nessun dato dell'utente. Il proxy del sistema,
se c'è, vale per queste richieste (https da capo a capo); le richieste locali con il gettone non passano mai da un proxy
(sicurezza.APRI_LOCALE) e non partono da qui.
"""
import email.message
import http.client
import json
import os
import re
import ssl
import urllib.error
import urllib.request
import urllib.response
from typing import NamedTuple
from urllib.parse import urlparse

from .. import __version__
from . import Rifiutato

REPOSITORY = ""                                # «proprietario/nome» del repository delle release: vuoto = nessuna richiesta (docs/architettura/AGGIORNAMENTI.md)
API = "https://api.github.com"
VERSIONE_API = "2026-03-10"                    # X-GitHub-Api-Version (docs.github.com, «API versions»: la più recente il 16/11/2026)
HOST = ("api.github.com", "github.com")        # dove possono puntare le richieste; i rimandi (CDN degli asset) solo in https
MAX_RISPOSTA = 1 << 20                         # risposta dell'API: 1 MB
TEMPO = 30                                     # secondi per collegarsi e per ogni lettura
BLOCCO = 1 << 16
_REPOSITORY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}")
_NOME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,199}")


class Asset(NamedTuple):
    """file di una release: nome, URL di scaricamento, misura e impronta dichiarate da GitHub (non fidate)"""
    nome: str
    url: str
    dimensione: int
    digest: str = None


class Rilascio(NamedTuple):
    """ultima release: etichetta (tag), data di pubblicazione e asset per nome"""
    etichetta: str
    pubblicata: str
    asset: dict


class _SoloHttps(urllib.request.HTTPRedirectHandler):
    """i rimandi (gli asset di GitHub passano dalla sua CDN) solo verso https"""

    def redirect_request(self, req, fp, code, msg, headers, nuovo):
        if urlparse(nuovo).scheme != "https": raise urllib.error.URLError("rimando non https")          # non tradotto: va nel motivo tecnico dell'errore
        return super().redirect_request(req, fp, code, msg, headers, nuovo)


CONTESTO = ssl.create_default_context()        # certificato e nome dell'host verificati
APRI_RETE = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CONTESTO), _SoloHttps)


def intestazioni(accetta, api=False):
    """le uniche intestazioni delle richieste: versione del programma e tipo accettato (niente gettone, niente cookie)"""
    h = {"User-Agent": f"Impaginatore/{__version__}", "Accept": accetta}
    if api: h["X-GitHub-Api-Version"] = VERSIONE_API
    return h


def controlla_url(url):
    """solo https verso gli host ammessi; Rifiutato altrimenti"""
    u = urlparse(url) if isinstance(url, str) else None
    if not u or u.scheme != "https" or u.hostname not in HOST or u.username or u.password or u.port not in (None, 443):
        raise Rifiutato("sistema.agg_indirizzo_non_sicuro")
    return u


def leggi_limitato(risposta, massimo, verso=None):
    """legge al massimo `massimo` byte (Rifiutato oltre): in memoria, o nel file aperto `verso`. Restituisce i byte o la misura"""
    n = risposta.headers.get("Content-Length")
    if n and n.isdigit() and int(n) > massimo: raise Rifiutato("sistema.agg_troppo_grande")
    letti, parti = 0, []
    while True:
        b = risposta.read(BLOCCO)
        if not b: break
        letti += len(b)
        if letti > massimo: raise Rifiutato("sistema.agg_troppo_grande")
        if verso is None: parti.append(b)
        else: verso.write(b)
    return b"".join(parti) if verso is None else letti


class Sorgente:
    """interfaccia"""
    configurata = False

    def ultimo(self):
        """Rilascio dell'ultima versione pubblicata, o None se non ce n'è"""
        raise NotImplementedError

    def scarica(self, asset, percorso, massimo):
        """scrive l'asset nel file `percorso` (al massimo `massimo` byte); restituisce la misura"""
        raise NotImplementedError

    def leggi(self, asset, massimo):
        """l'asset in memoria (file piccoli: manifesto e firma)"""
        raise NotImplementedError


class SorgenteGitHub(Sorgente):
    """release di un repository GitHub pubblico, con l'API REST (nessuna autenticazione)"""

    def __init__(self, repository=None):
        self.repository = (REPOSITORY if repository is None else repository).strip()

    @property
    def configurata(self): return bool(self.repository)

    def _apri(self, url, accetta):
        """risposta (file-like con .headers) dell'URL: la rete vera"""
        u = controlla_url(url)
        r = urllib.request.Request(url, headers=intestazioni(accetta, api=u.hostname == "api.github.com"))
        return APRI_RETE.open(r, timeout=TEMPO)

    def _prendi(self, url, accetta, massimo, verso=None):
        try:
            with self._apri(url, accetta) as r: return leggi_limitato(r, massimo, verso)
        except urllib.error.HTTPError as e:
            if e.code == 404: raise FileNotFoundError(url) from None
            raise Rifiutato("sistema.agg_rete", dettaglio=f"HTTP {e.code}") from None
        except (OSError, http.client.HTTPException) as e:                          # URLError, certificato, tempo scaduto, connessione caduta
            raise Rifiutato("sistema.agg_rete", dettaglio=(str(getattr(e, "reason", None) or e) or type(e).__name__)[:120]) from None

    def ultimo(self):
        if not self.configurata: return None
        if not _REPOSITORY.fullmatch(self.repository): raise Rifiutato("sistema.agg_repository_non_valido")
        try: dati = self._prendi(f"{API}/repos/{self.repository}/releases/latest", "application/vnd.github+json", MAX_RISPOSTA)
        except FileNotFoundError: return None                                     # nessuna release pubblicata
        try: j = json.loads(dati.decode("utf-8"))
        except (UnicodeDecodeError, ValueError): raise Rifiutato("sistema.agg_risposta_non_valida") from None
        if not isinstance(j, dict) or not isinstance(j.get("tag_name"), str) or not isinstance(j.get("assets"), list): raise Rifiutato("sistema.agg_risposta_non_valida")
        if j.get("draft") or j.get("prerelease"): return None                    # l'API non le restituisce: per sicurezza non si usano
        asset = {}
        for a in j["assets"]:
            if not (isinstance(a, dict) and isinstance(a.get("name"), str) and _NOME.fullmatch(a["name"]) and isinstance(a.get("browser_download_url"), str)
                    and type(a.get("size")) is int and a.get("state", "uploaded") == "uploaded"): continue
            asset[a["name"]] = Asset(a["name"], a["browser_download_url"], a["size"], a.get("digest") if isinstance(a.get("digest"), str) else None)
        return Rilascio(j["tag_name"][:100], str(j.get("published_at") or "")[:40], asset)

    def _asset(self, asset, massimo, verso=None):
        if asset.dimensione > massimo: raise Rifiutato("sistema.agg_troppo_grande")
        try: return self._prendi(asset.url, "application/octet-stream", massimo, verso)
        except FileNotFoundError: raise Rifiutato("sistema.agg_release_incompleta") from None

    def scarica(self, asset, percorso, massimo):
        with open(percorso, "wb") as f: return self._asset(asset, massimo, f)

    def leggi(self, asset, massimo):
        return self._asset(asset, massimo)


class SorgenteFinta(SorgenteGitHub):
    """le release da una cartella: <cartella>/releases/latest.json (come la risposta dell'API) e gli asset accanto,
    per nome (l'ultimo pezzo del browser_download_url). Stessi controlli degli URL e delle misure, nessuna rete"""

    def __init__(self, cartella, repository="prova/impaginatore"):
        super().__init__(repository); self.cartella = os.path.abspath(os.path.expanduser(cartella))

    def _apri(self, url, accetta):
        u = controlla_url(url)
        if u.hostname == "api.github.com": nome = os.path.join("releases", "latest.json")
        else:
            nome = u.path.rsplit("/", 1)[-1]
            if not _NOME.fullmatch(nome): raise Rifiutato("sistema.agg_indirizzo_non_sicuro")
        p = os.path.join(self.cartella, nome)
        try: f = open(p, "rb")
        except FileNotFoundError: raise urllib.error.HTTPError(url, 404, "non trovato", None, None) from None          # non tradotto: come la risposta di GitHub
        h = email.message.Message(); h["Content-Length"] = str(os.fstat(f.fileno()).st_size)
        return urllib.response.addinfourl(f, h, url, 200)
