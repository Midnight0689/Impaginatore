"""Chrome/Chromium senza schermo pilotato con il Chrome DevTools Protocol (solo libreria standard): apre una pagina, esegue
JavaScript nella pagina e raccoglie errori della console, eccezioni e blocchi della Content-Security-Policy.

    with Browser(tmp_path) as b:
        b.apri(url); b.js("document.title"); assert not b.problemi()

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


class _WebSocket:
    """client WebSocket minimo (RFC 6455): frame di testo, mascherati in uscita; basta per il protocollo di Chrome"""

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

    def _leggi(self, n):
        b = b""
        while len(b) < n:
            x = self.s.recv(n - len(b))
            if not x: raise OSError("connessione chiusa")
            b += x
        return b

    def manda(self, testo):
        dati = testo.encode("utf-8"); n = len(dati); m = os.urandom(4)
        testa = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.s.sendall(testa + m + bytes(b ^ m[i % 4] for i, b in enumerate(dati)))

    def ricevi(self):
        parti = []
        while True:
            b0, b1 = self._leggi(2); n = b1 & 0x7F
            if n == 126: n = struct.unpack(">H", self._leggi(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._leggi(8))[0]
            dati = self._leggi(n); op = b0 & 0x0F
            if op == 0x8: raise OSError("chiusa da Chrome")
            if op in (0x9, 0xA): continue
            parti.append(dati)
            if b0 & 0x80: return b"".join(parti).decode("utf-8")

    def chiudi(self):
        try: self.s.close()
        except OSError: pass


class Browser:
    """un Chrome senza schermo con il suo profilo nella cartella data; eventi della pagina raccolti in self.eventi"""

    def __init__(self, cartella):
        self.cartella = str(cartella); self.n = 0; self.eventi = []

    def __enter__(self):
        prof = os.path.join(self.cartella, "chrome-cdp"); os.makedirs(prof, exist_ok=True)
        # niente estensioni né app predefinite: Chrome le installa nel profilo nuovo qualche secondo dopo l'avvio e, quando
        # arrivano, le richieste della pagina già partite e non ancora consegnate alla rete finiscono in net::ERR_ABORTED
        # («Failed to fetch» nella pagina). Su una macchina carica capitava a metà di un test (la seconda «Altra
        # disposizione» persa: «Disposizione 2 di 50» invece di 3). Sono le opzioni che usano anche Puppeteer e Playwright
        self.p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={prof}",
                                   "--disable-extensions", "--disable-default-apps", "--disable-component-update",
                                   "--remote-debugging-port=0", "--window-size=1600,1000", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        f = os.path.join(prof, "DevToolsActivePort"); t = time.time() + 30
        while not (os.path.exists(f) and open(f, encoding="utf-8").read().strip()):
            if time.time() > t: raise OSError("Chrome non parte")
            time.sleep(0.1)
        porta = int(open(f, encoding="utf-8").read().split()[0])
        t = time.time() + 30
        while True:
            try:
                pagine = [x for x in json.load(urllib.request.urlopen(f"http://127.0.0.1:{porta}/json/list", timeout=5)) if x["type"] == "page"]
                if pagine: break
            except OSError: pass
            if time.time() > t: raise OSError("nessuna pagina in Chrome")
            time.sleep(0.1)
        self.ws = _WebSocket(pagine[0]["webSocketDebuggerUrl"])
        for m in ("Page.enable", "Runtime.enable", "Log.enable", "Network.enable"): self.chiama(m)
        return self

    def __exit__(self, tipo, *a):
        if tipo is None:                              # ultimi eventi della pagina, poi il controllo generale della CSP
            try: self.pausa(0.2)
            except OSError: pass
        self.ws.chiudi(); self.p.terminate()
        try: self.p.wait(10)
        except subprocess.TimeoutExpired: self.p.kill()
        v = self.violazioni_csp()
        if tipo is None and v: raise AssertionError("bloccato dalla Content-Security-Policy: " + " | ".join(v))

    def chiama(self, metodo, **parametri):
        self.n += 1; mio = self.n
        self.ws.manda(json.dumps(dict(id=mio, method=metodo, params=parametri)))
        while True:
            m = json.loads(self.ws.ricevi())
            if m.get("id") == mio:
                if "error" in m: raise RuntimeError(f"{metodo}: {m['error']}")
                return m.get("result", {})
            if "method" in m: self.eventi.append(m)

    def attendi_evento(self, nome, secondi=30):
        fine = time.time() + secondi; self.ws.s.settimeout(secondi)
        while time.time() < fine:
            m = json.loads(self.ws.ricevi())
            if "method" in m:
                self.eventi.append(m)
                if m["method"] == nome: return m
        raise TimeoutError(nome)

    def apri(self, url, attesa=1.0):
        self.chiama("Page.navigate", url=url); self.attendi_evento("Page.loadEventFired"); self.pausa(attesa)

    def pausa(self, secondi):
        """lascia lavorare la pagina (fetch, timer) raccogliendo gli eventi"""
        fine = time.time() + secondi
        while time.time() < fine:
            self.ws.s.settimeout(max(0.05, fine - time.time()))
            try: self.eventi.append(json.loads(self.ws.ricevi()))
            except (TimeoutError, socket.timeout): break
        self.ws.s.settimeout(60)

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
