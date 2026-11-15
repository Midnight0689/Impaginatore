"""Chrome senza schermo pilotato dal protocollo DevTools su pipe (fd 3 e 4), solo libreria standard.

Serve a sito.py (istantanee, immagine Open Graph) e a schermate.py (editor con l'album dimostrativo).
Niente websocket e niente porte aperte: Chrome legge i comandi dal descrittore 3 e scrive le risposte sul 4,
un messaggio JSON per volta terminato da un byte nullo. Funziona su Linux e macOS (su Windows le pipe
ereditate con questi numeri non esistono: lì le istantanee vanno fatte da WSL o da un Mac).
"""
import base64
import fcntl
import json
import os
import shutil
import subprocess
import tempfile
import time

NOMI = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
MAC = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def trova_chrome():
    """percorso di Chrome o Chromium, oppure None"""
    for n in NOMI:
        p = shutil.which(n)
        if p: return p
    return MAC if os.path.exists(MAC) else None


class ErroreChrome(RuntimeError):
    pass


class Chrome:
    """una sessione di Chrome con una scheda; si usa con «with Chrome() as c:»"""

    def __init__(self, eseguibile=None, argomenti=()):
        self.eseguibile = eseguibile or trova_chrome()
        if not self.eseguibile: raise ErroreChrome("serve Chrome o Chromium (google-chrome, chromium)")
        self.argomenti = list(argomenti)
        self.id = 0; self.eventi = []; self.buffer = b""; self.sessione = None

    def __enter__(self):
        self.profilo = tempfile.mkdtemp(prefix="cromo-")
        r_cmd, w_cmd = os.pipe(); r_ris, w_ris = os.pipe()

        def figlio():                     # nel processo figlio: le due pipe diventano i descrittori 3 e 4, ereditabili
            a = fcntl.fcntl(r_cmd, fcntl.F_DUPFD, 10); b = fcntl.fcntl(w_ris, fcntl.F_DUPFD, 10)   # prima lontano da 3 e 4, per non sovrascriverle
            os.dup2(a, 3); os.dup2(b, 4); os.set_inheritable(3, True); os.set_inheritable(4, True)
        self.proc = subprocess.Popen([self.eseguibile, "--headless=new", "--remote-debugging-pipe", f"--user-data-dir={self.profilo}", "--no-first-run",
                                      "--no-default-browser-check", "--disable-extensions", "--disable-background-networking", "--disable-sync",
                                      "--disable-component-update", "--hide-scrollbars", "--mute-audio", "--font-render-hinting=none", *self.argomenti],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=figlio, close_fds=False)
        os.close(r_cmd); os.close(w_ris)
        self.scrivi, self.leggi = w_cmd, r_ris
        t = self.invia("Target.createTarget", {"url": "about:blank"}, sessione=False)["targetId"]
        self.sessione = self.invia("Target.attachToTarget", {"targetId": t, "flatten": True}, sessione=False)["sessionId"]
        self.invia("Page.enable"); self.invia("Runtime.enable")
        return self

    def __exit__(self, *_):
        try: self.invia("Browser.close", sessione=False, attesa=5)
        except Exception: pass
        try: self.proc.wait(10)
        except Exception: self.proc.kill()
        for fd in (self.scrivi, self.leggi):
            try: os.close(fd)
            except OSError: pass
        shutil.rmtree(self.profilo, ignore_errors=True)

    def _messaggio(self, scadenza):
        while b"\0" not in self.buffer:
            if time.time() > scadenza: raise ErroreChrome("Chrome non risponde")
            pezzo = os.read(self.leggi, 1 << 20)
            if not pezzo: raise ErroreChrome("Chrome si è chiuso")
            self.buffer += pezzo
        riga, self.buffer = self.buffer.split(b"\0", 1)
        return json.loads(riga)

    def invia(self, metodo, parametri=None, sessione=True, attesa=60):
        self.id += 1; mid = self.id
        m = {"id": mid, "method": metodo, "params": parametri or {}}
        if sessione and self.sessione: m["sessionId"] = self.sessione
        os.write(self.scrivi, json.dumps(m).encode() + b"\0")
        scadenza = time.time() + attesa
        while True:
            r = self._messaggio(scadenza)
            if r.get("id") == mid:
                if "error" in r: raise ErroreChrome(f"{metodo}: {r['error'].get('message')}")
                return r.get("result", {})
            if "method" in r: self.eventi.append(r)

    def aspetta_evento(self, nome, attesa=60):
        scadenza = time.time() + attesa
        while True:
            for k, e in enumerate(self.eventi):
                if e["method"] == nome: return self.eventi.pop(k)
            r = self._messaggio(scadenza)
            if "method" in r: self.eventi.append(r)

    def valuta(self, espressione, attesa=60):
        """valore di un'espressione JavaScript (le promesse si aspettano)"""
        r = self.invia("Runtime.evaluate", {"expression": espressione, "awaitPromise": True, "returnByValue": True}, attesa=attesa)
        if "exceptionDetails" in r: raise ErroreChrome(f"errore JavaScript: {r['exceptionDetails'].get('exception', {}).get('description') or r['exceptionDetails'].get('text')}")
        return r.get("result", {}).get("value")

    def vista(self, larghezza, altezza, scala=1, mobile=False, tema=None, movimento_ridotto=True):
        self.invia("Emulation.setDeviceMetricsOverride", {"width": larghezza, "height": altezza, "deviceScaleFactor": scala, "mobile": mobile})
        f = [{"name": "prefers-reduced-motion", "value": "reduce" if movimento_ridotto else "no-preference"}]
        if tema: f.append({"name": "prefers-color-scheme", "value": tema})
        self.invia("Emulation.setEmulatedMedia", {"media": "", "features": f})

    def apri(self, url, attesa=60):
        self.eventi = [e for e in self.eventi if e["method"] != "Page.loadEventFired"]
        self.invia("Page.navigate", {"url": url})
        self.aspetta_evento("Page.loadEventFired", attesa)
        self.valuta("document.fonts.ready.then(() => true)")

    def carica_immagini(self, attesa=30):
        """toglie il caricamento differito e aspetta che tutte le immagini siano pronte (per le istantanee della pagina intera)"""
        return self.valuta("(async () => { const im = [...document.images]; im.forEach(i => { i.loading = 'eager'; });"
                           " await Promise.all(im.map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));"
                           " return im.filter(i => !i.naturalWidth).map(i => i.currentSrc || i.src); })()", attesa)

    def foto(self, percorso, pagina_intera=True, ritaglio=None, formato="png", qualita=None):
        """salva un'istantanea; ritaglio = (x, y, larghezza, altezza) in px CSS"""
        p = {"format": formato, "captureBeyondViewport": pagina_intera}
        if qualita: p["quality"] = qualita
        if ritaglio:
            x, y, w, h = ritaglio; p["clip"] = {"x": x, "y": y, "width": w, "height": h, "scale": 1}
        elif pagina_intera:
            w, h = self.valuta("[document.documentElement.clientWidth, Math.ceil(document.documentElement.scrollHeight)]")
            p["clip"] = {"x": 0, "y": 0, "width": w, "height": h, "scale": 1}
        dati = base64.b64decode(self.invia("Page.captureScreenshot", p, attesa=120)["data"])
        with open(percorso, "wb") as f: f.write(dati)
        return percorso
