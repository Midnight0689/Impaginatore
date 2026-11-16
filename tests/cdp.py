"""Chrome/Chromium senza schermo pilotato con il Chrome DevTools Protocol (solo libreria standard): apre una pagina, esegue
JavaScript nella pagina e raccoglie errori della console, eccezioni e blocchi della Content-Security-Policy.

    with Browser(tmp_path) as b:
        b.apri(url, EDITOR); b.js("document.title"); assert not b.problemi()
        b.js("document.getElementById('save').click()")
        b.attendi("document.getElementById('toast').textContent.startsWith('Salvato')")

Niente pause fisse: si aspetta una condizione (attendi, attendi_rete), con un tempo massimo largo (30 s) che conta solo
quando la condizione non arriva; su una macchina carica il test aspetta di più, non fallisce. pausa() serve solo a
raccogliere gli ultimi eventi o a un controllo negativo («per un po' non succede»), sempre dopo aver aspettato la
condizione che lo rende sensato, e con il motivo accanto.

Controllo generale: un blocco della CSP visto durante il «with» fa fallire il test all'uscita, anche se il test non
guarda problemi() (una risorsa che la CSP blocca è un difetto della pagina, mai un caso previsto).
"""
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import time
import urllib.request



def trova_chrome():
    """Chrome o Chromium per i test del browser: IMPAGINATORE_CHROME se c'è, poi i comandi nel PATH (Linux), poi dove lo
    installano Windows (Programmi, anche solo per l'utente) e macOS (Applicazioni), che non lo mettono nel PATH. None se manca"""
    if os.environ.get("IMPAGINATORE_CHROME"): return os.environ["IMPAGINATORE_CHROME"]
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        if shutil.which(n): return shutil.which(n)
    posti = [os.path.join(os.environ[k], *parti) for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA") if os.environ.get(k)
             for parti in (("Google", "Chrome", "Application", "chrome.exe"), ("Chromium", "Application", "chrome.exe"))]
    posti += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    return next((p for p in posti if os.path.isfile(p)), None)


CHROME = trova_chrome()

ATTESA = 30                     # secondi: tempo massimo di ogni attesa di una condizione (conta solo se la condizione non arriva)
RISPOSTA = 120                  # secondi: tempo massimo di una chiamata al protocollo (anche una promessa della pagina che si aspetta)
PASSAGGI = ("/avvio",)          # pagine che passano subito a un'altra (l'URL di avvio lascia il gettone e va a «/»): non sono quella da aspettare

# stati delle pagine del programma, da aspettare con attendi() o apri(url, pronto)
EDITOR = "typeof S !== 'undefined' && !!S && !!S.photos"         # l'editor ha lo stato del progetto (e lo ha già disegnato)
HOME = "!!document.getElementById('where').textContent"          # la schermata ha la lista dei progetti (disegna() scrive anche dove sono salvati)
CONTROLLA = "CTL.aperto && !!CTL.d && !CTL.corre && CTL.rev === S.rev && !!document.getElementById('ctlsis')"      # «Controlla» aperto, con il controllo dell'album com'è adesso
BOZZA = "!!document.getElementById('bzok') && !document.getElementById('bzok').disabled"     # la bozza è arrivata (mentre la prepara il pulsante è spento)
PANNELLI = "new Promise(r => setTimeout(r, 30))"   # setPanels() ridisegna la tela con un timer di 30 ms: un timer uguale, messo dopo, scatta dopo il suo


class _WebSocket:
    """client WebSocket minimo (RFC 6455): frame di testo, mascherati in uscita; basta per il protocollo di Chrome. Quello che
    arriva resta in un buffer finché il messaggio non è completo: un tempo massimo scaduto a metà non perde niente"""

    def __init__(self, url, timeout=60):
        host, _, resto = url[len("ws://"):].partition("/")
        h, _, p = host.partition(":")
        self.s = socket.create_connection((h, int(p)), timeout=timeout)
        chiave = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{resto} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {chiave}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        risposta = b""
        while b"\r\n\r\n" not in risposta: risposta += self.s.recv(1)
        if b" 101 " not in risposta.split(b"\r\n")[0]: raise OSError(risposta.decode(errors="replace"))
        self.buf = bytearray(); self.parti = []

    def manda(self, testo):
        dati = testo.encode("utf-8"); n = len(dati); m = os.urandom(4)
        testa = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.s.sendall(testa + m + bytes(b ^ m[i % 4] for i, b in enumerate(dati)))

    def _frame(self):
        """(codice, ultimo, dati) del primo frame nel buffer, None se non è ancora arrivato tutto"""
        b = self.buf
        if len(b) < 2: return None
        n, i = b[1] & 0x7F, 2
        if n == 126: n, i = (struct.unpack(">H", b[2:4])[0], 4) if len(b) >= 4 else (None, 0)
        elif n == 127: n, i = (struct.unpack(">Q", b[2:10])[0], 10) if len(b) >= 10 else (None, 0)
        if n is None or len(b) < i + n: return None
        f = (b[0] & 0x0F, b[0] & 0x80, bytes(b[i:i + n])); del b[:i + n]
        return f

    def ricevi(self, secondi):
        """il prossimo messaggio di testo; TimeoutError se non arriva entro `secondi`"""
        fine = time.monotonic() + secondi
        while True:
            f = self._frame()
            if f is None:
                resto = fine - time.monotonic()
                if resto <= 0: raise TimeoutError("nessun messaggio da Chrome")
                self.s.settimeout(resto)
                try: x = self.s.recv(1 << 16)
                except socket.timeout as e: raise TimeoutError("nessun messaggio da Chrome") from e
                if not x: raise OSError("connessione chiusa")
                self.buf += x; continue
            op, ultimo, dati = f
            if op == 0x8: raise OSError("chiusa da Chrome")
            if op in (0x9, 0xA): continue
            self.parti.append(dati)
            if ultimo:
                testo = b"".join(self.parti).decode("utf-8"); self.parti = []
                return testo

    def chiudi(self):
        try: self.s.close()
        except OSError: pass


class Browser:
    """un Chrome senza schermo con il suo profilo nella cartella data; eventi della pagina raccolti in self.eventi,
    richieste in corso in self.in_corso (requestId → url)"""

    def __init__(self, cartella):
        self.cartella = str(cartella); self.n = 0; self.eventi = []; self.in_corso = {}; self.ultima_rete = time.monotonic()

    def __enter__(self):
        prof = os.path.join(self.cartella, "chrome-cdp"); os.makedirs(prof, exist_ok=True)
        # niente estensioni né app predefinite: Chrome le installa nel profilo nuovo qualche secondo dopo l'avvio e, quando
        # arrivano, le richieste della pagina già partite e non ancora consegnate alla rete finiscono in net::ERR_ABORTED
        # («Failed to fetch» nella pagina). Su una macchina carica capitava a metà di un test (la seconda «Altra
        # disposizione» persa: «Disposizione 2 di 50» invece di 3). Sono le opzioni che usano anche Puppeteer e Playwright
        self.p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={prof}",
                                   "--disable-extensions", "--disable-default-apps", "--disable-component-update",
                                   "--remote-debugging-port=0", "--window-size=1600,1000", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        f = os.path.join(prof, "DevToolsActivePort"); t = time.monotonic() + ATTESA
        while not (os.path.exists(f) and open(f, encoding="utf-8").read().strip()):
            if time.monotonic() > t: raise OSError("Chrome non parte")
            time.sleep(0.1)                                   # Chrome scrive il file quando è pronto: non c'è un evento da aspettare
        porta = int(open(f, encoding="utf-8").read().split()[0])
        t = time.monotonic() + ATTESA
        while True:
            try:
                pagine = [x for x in json.load(urllib.request.urlopen(f"http://127.0.0.1:{porta}/json/list", timeout=5)) if x["type"] == "page"]
                if pagine: break
            except OSError: pass
            if time.monotonic() > t: raise OSError("nessuna pagina in Chrome")
            time.sleep(0.1)                                   # la scheda iniziale compare nell'elenco poco dopo: si richiede l'elenco
        self.ws = _WebSocket(pagine[0]["webSocketDebuggerUrl"])
        for m in ("Page.enable", "Runtime.enable", "Log.enable", "Network.enable"): self.chiama(m)
        return self

    def __exit__(self, tipo, *a):
        if tipo is None:                              # ultimi eventi della pagina (errori, blocchi della CSP), poi il controllo generale della CSP
            try: self.pausa(0.2)                      # raccolta, non attesa di una condizione: quello che arriva dopo la fine del test non conta
            except OSError: pass
        self.ws.chiudi(); self.p.terminate()
        try: self.p.wait(10)
        except subprocess.TimeoutExpired: self.p.kill()
        v = self.violazioni_csp()
        if tipo is None and v: raise AssertionError("bloccato dalla Content-Security-Policy: " + " | ".join(v))

    # ------------------------------------------------------------ protocollo
    def _evento(self, m):
        """un evento della pagina: si tiene, e le richieste di rete si contano (partite, finite, fallite)"""
        self.eventi.append(m); metodo = m["method"]
        if metodo.startswith("Network."):
            p = m.get("params", {}); self.ultima_rete = time.monotonic()
            if metodo == "Network.requestWillBeSent": self.in_corso[p["requestId"]] = p["request"]["url"]
            elif metodo in ("Network.loadingFinished", "Network.loadingFailed"): self.in_corso.pop(p["requestId"], None)

    def _leggi(self, secondi):
        m = json.loads(self.ws.ricevi(secondi))
        if "method" in m: self._evento(m)
        return m

    def chiama(self, metodo, **parametri):
        self.n += 1; mio = self.n
        self.ws.manda(json.dumps(dict(id=mio, method=metodo, params=parametri)))
        fine = time.monotonic() + RISPOSTA
        while True:
            m = self._leggi(fine - time.monotonic())
            if m.get("id") == mio:
                if "error" in m: raise RuntimeError(f"{metodo}: {m['error']}")
                return m.get("result", {})

    def attendi_evento(self, nome, secondi=ATTESA):
        """il prossimo evento `nome` della pagina"""
        fine = time.monotonic() + secondi
        while True:
            try: m = self._leggi(fine - time.monotonic())
            except TimeoutError: raise TimeoutError(f"nessun evento {nome} in {secondi} s") from None
            if m.get("method") == nome: return m

    def pausa(self, secondi):
        """lascia passare `secondi` raccogliendo gli eventi. Non è un'attesa: per aspettare qualcosa c'è attendi(); qui solo
        per raccogliere gli ultimi eventi o per un controllo negativo, dopo aver aspettato la condizione che lo rende sensato"""
        fine = time.monotonic() + secondi
        while (resto := fine - time.monotonic()) > 0:
            try: self._leggi(resto)
            except TimeoutError: break

    # ------------------------------------------------------------ attese
    def attendi(self, codice, vero=bool, secondi=ATTESA):
        """aspetta che il valore dell'espressione JavaScript `codice` soddisfi `vero` (di base: che sia truthy) e lo
        restituisce. La si rivaluta finché non lo fa (un'eccezione, per esempio un elemento che non c'è ancora o la pagina
        che cambia, conta come «non ancora»); dopo `secondi` AssertionError con l'ultimo valore visto"""
        fine = time.monotonic() + secondi; ultimo = None
        while True:
            try:
                v = self.js(codice)
                if vero(v): return v
                ultimo = repr(v)[:300]
            except RuntimeError as e: ultimo = str(e)[:300]
            if time.monotonic() > fine: raise AssertionError(f"dopo {secondi} s non è ancora vero: {codice}\n  ultimo valore: {ultimo}")
            self.pausa(0.05)                                  # passo tra due controlli, raccogliendo gli eventi

    def attendi_che(self, condizione, secondi=ATTESA):
        """aspetta che la funzione Python `condizione` (che guarda gli eventi raccolti, per esempio violazioni_csp)
        restituisca un valore vero, e lo restituisce; dopo `secondi` AssertionError"""
        fine = time.monotonic() + secondi
        while not (v := condizione()):
            if time.monotonic() > fine: raise AssertionError(f"dopo {secondi} s non è ancora vero: {getattr(condizione, '__name__', condizione)}")
            self.pausa(0.05)                                  # passo tra due controlli, raccogliendo gli eventi
        return v

    def attendi_rete(self, quiete=0.5, secondi=ATTESA):
        """aspetta che la pagina non abbia richieste in corso (fetch, immagini, caratteri) da almeno `quiete` secondi"""
        fine = time.monotonic() + secondi
        while self.in_corso or time.monotonic() - self.ultima_rete < quiete:
            if time.monotonic() > fine: raise AssertionError(f"dopo {secondi} s la pagina ha ancora richieste in corso: {sorted(self.in_corso.values())[:5]}")
            self.pausa(0.05)                                  # passo tra due controlli, raccogliendo gli eventi

    def attendi_richiesta(self, parte, dopo=None, secondi=ATTESA):
        """aspetta che la pagina faccia una richiesta con `parte` nell'URL, partita dopo `dopo` (ora del sistema,
        time.time(); di base adesso), e che sia finita; ne restituisce l'URL. Serve ai controlli negativi: «la pagina ha
        chiesto /api/ping dopo la modifica, e non ha ridisegnato»"""
        dopo = time.time() if dopo is None else dopo; fine = time.monotonic() + secondi
        while True:
            partite = {p["requestId"]: p["request"]["url"] for m in self.eventi if m["method"] == "Network.requestWillBeSent"
                       for p in [m["params"]] if parte in p["request"]["url"] and p.get("wallTime", 0) > dopo}
            finite = [partite[m["params"]["requestId"]] for m in self.eventi
                      if m["method"] in ("Network.loadingFinished", "Network.loadingFailed") and m["params"]["requestId"] in partite]
            if finite: return finite[0]
            if time.monotonic() > fine: raise AssertionError(f"dopo {secondi} s la pagina non ha ancora finito una richiesta a {parte}")
            self.pausa(0.05)                                  # passo tra due controlli, raccogliendo gli eventi

    def segna(self):
        """segna il documento di adesso: attendi_pagina() aspetta quello che lo sostituisce (un clic che cambia pagina, un
        ricaricamento), che non ha il segno"""
        try: self.js("window.__cdp_prima = true")
        except RuntimeError: pass                             # nessun documento ancora (o uno che sta già cambiando): niente da segnare

    def attendi_pagina(self, pronto=None, secondi=ATTESA):
        """dopo segna(): aspetta il documento nuovo caricato (dopo le pagine di passaggio come /avvio), la condizione
        `pronto` se c'è (EDITOR, HOME o un'altra espressione JavaScript) e la rete ferma"""
        if pronto is not None and not isinstance(pronto, str): raise TypeError("pronto è un'espressione JavaScript, non una pausa")
        self.attendi(f"!window.__cdp_prima && document.readyState === 'complete' && !{json.dumps(list(PASSAGGI))}.includes(location.pathname)", secondi=secondi)
        if pronto: self.attendi(pronto, secondi=secondi)
        self.attendi_rete(secondi=secondi)

    def apri(self, url, pronto=None, secondi=ATTESA):
        """apre url e aspetta la pagina vera (vedi attendi_pagina)"""
        if pronto is not None and not isinstance(pronto, str): raise TypeError("apri(url, pronto): pronto è un'espressione JavaScript, non una pausa")
        self.segna(); self.chiama("Page.navigate", url=url); self.attendi_pagina(pronto, secondi)

    def js(self, codice, attendi=True):
        """valore (JSON) dell'espressione JavaScript valutata nella pagina (le promesse si aspettano)"""
        r = self.chiama("Runtime.evaluate", expression=codice, awaitPromise=attendi, returnByValue=True)
        if "exceptionDetails" in r: raise RuntimeError(f"{codice[:80]}: {r['exceptionDetails'].get('exception', {}).get('description') or r['exceptionDetails']}")
        return r.get("result", {}).get("value")

    def problemi(self):
        """errori visti finora: eccezioni non gestite, console.error, messaggi di errore del browser (tra cui i blocchi CSP)"""
        out = []
        for m in self.eventi:
            p = m.get("params", {})
            if m["method"] == "Runtime.exceptionThrown": out.append("eccezione: " + str(p["exceptionDetails"].get("exception", {}).get("description") or p["exceptionDetails"].get("text")))
            elif m["method"] == "Runtime.consoleAPICalled" and p.get("type") in ("error", "assert"): out.append("console: " + " ".join(str(a.get("value", a.get("description"))) for a in p.get("args", [])))
            elif m["method"] == "Log.entryAdded" and p["entry"].get("level") == "error": out.append(f"{p['entry'].get('source')}: {p['entry'].get('text')} {p['entry'].get('url', '')}")
        return out

    def violazioni_csp(self):
        """blocchi della Content-Security-Policy visti finora (immagini, script, stili, connessioni)"""
        return [p["entry"].get("text", "").strip() for m in self.eventi if m.get("method") == "Log.entryAdded"
                for p in [m["params"]] if "Content Security Policy" in p["entry"].get("text", "")]

    def risposte(self):
        """[(stato HTTP, url)] delle risposte ricevute dalla pagina"""
        return [(m["params"]["response"]["status"], m["params"]["response"]["url"]) for m in self.eventi if m["method"] == "Network.responseReceived"]
