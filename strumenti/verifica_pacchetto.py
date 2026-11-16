#!/usr/bin/env python3
"""Prova il programma compilato vero (T-302), come lo usa un fotografo, senza rete e senza toccare i suoi dati.

    python strumenti/verifica_pacchetto.py PROGRAMMA [--finestra] [--rapporto file.json] [--immagini CARTELLA]

PROGRAMMA è l'eseguibile: build/compila/linux/Impaginatore/impaginatore-app, /usr/bin/impaginatore (dopo il .deb),
Impaginatore.app/Contents/MacOS/impaginatore-app, …\\Impaginatore\\impaginatore.exe. Tutto gira in una cartella temporanea
(IMPAGINATORE_DATI, IMPAGINATORE_CACHE, cartella dei progetti), con foto sintetiche create qui.

Controlli, in ordine:
    file          nessun .py del programma; tutti i file di dati del pacchetto del sorgente (pagine, testi, statistiche,
                  licenza beta…), copie del motore per la 1.x, licenze, file di OpenCV per i volti
    versione      «impaginatore --versione»
    avvio         la pagina della schermata di avvio («_avvio», la stessa della finestra) con versione e licenza: prova
                  gratuita, sola lettura dopo una prova finita, in italiano e in inglese
    copie         una «versione aggiornata» finta nella cartella dei dati: il programma compilato non la avvia mai
    schermata     la schermata dei progetti risponde (ping, licenza, aggiornamenti: si installano a mano, canale spento)
    editor        progetto nuovo con 6 foto, editor in un processo a parte (sottocomando «editor»), spread, JPG e PDF
    progetto 1.x  un progetto della 1.5.2 (spec.py) si apre e si esporta di nuovo per la 1.x (spec.py e copie del motore)
    psd           il sottocomando interno «_psd» (quello che l'editor lancia) carica l'album (anche i volti, con OpenCV) e
                  prepara gli spread, poi senza Photoshop si ferma con il suo messaggio (nella prova gratuita l'editor non
                  lo lancia: niente PSD)
    mcp           «impaginatore mcp» su stdio: initialize e tools/list (gli strumenti hanno nome e descrizione)
    chiusura      /api/esci chiude schermata ed editor
    finestra      (--finestra) la finestra del programma si apre (Linux: dentro xvfb-run) e si chiude con /api/esci; sotto
                  Xvfb fotografa la schermata di avvio (avvio-finestra.png in --immagini, di serie accanto al rapporto) e
                  poi la finestra del programma (finestra-programma.png), che deve vedersi
Esce con 0 se tutto va, 1 al primo controllo che non va (con il motivo). --rapporto scrive tempi e misure in JSON.
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess  # nosec B404  # lancia il programma da provare, con argomenti in lista
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "tests"))
RAPPORTO = {"controlli": [], "tempi": {}}


class NonVa(Exception):
    pass


def controllo(nome):
    def deco(f):
        def esegui(*a, **k):
            inizio = time.time()
            try: r = f(*a, **k)
            except NonVa as e: RAPPORTO["controlli"].append(dict(nome=nome, esito="no", motivo=str(e))); print(f"NO  {nome}: {e}", flush=True); raise
            RAPPORTO["controlli"].append(dict(nome=nome, esito="ok", secondi=round(time.time() - inizio, 2)))
            print(f"OK  {nome} ({time.time() - inizio:.1f} s)", flush=True)
            return r
        return esegui
    return deco


def deve(cond, motivo):
    if not cond: raise NonVa(motivo)


def attendi(f, secondi, passo=0.25):
    fine = time.time() + secondi
    while time.time() < fine:
        try:
            v = f()
            if v: return v
        except (OSError, ValueError, KeyError): pass
        time.sleep(passo)
    raise NonVa(f"tempo scaduto ({secondi} s)")


class Client:
    def __init__(self, porta, gettone): self.porta, self.gettone = porta, gettone

    def _r(self, path, body=None, timeout=120):
        h = {"Content-Type": "application/json", "X-Impaginatore-Gettone": self.gettone}
        r = urllib.request.Request(f"http://127.0.0.1:{self.porta}{path}", None if body is None else json.dumps(body).encode(), h)
        try:
            with urllib.request.urlopen(r, timeout=timeout) as f: return f.read()  # nosec B310  # solo 127.0.0.1
        except urllib.error.HTTPError as e: raise NonVa(f"{path}: {e.code} {e.read()[:500].decode('utf-8', 'replace')}") from None

    def get(self, path, **k): return json.loads(self._r(path, **k))

    def post(self, path, body=None, **k): return json.loads(self._r(path, {} if body is None else body, **k))

    def testo(self, path): return self._r(path).decode("utf-8")


class Prova:
    def __init__(self, exe, cartella):
        self.exe, self.dir = Path(exe).absolute(), Path(cartella)              # come lo lancia l'utente, anche dal collegamento /usr/bin/impaginatore
        self.dati, self.progetti = self.dir / "dati", self.dir / "Progetti"
        self.env = dict(os.environ, IMPAGINATORE_DATI=str(self.dati), IMPAGINATORE_CACHE=str(self.dir / "cache"), IMPAGINATORE_DIALOGHI="nessuno",
                        IMPAGINATORE_LINGUA="it", PYTHONUTF8="1")
        for k in ("IMPAGINATORE_AGGIORNAMENTI", "IMPAGINATORE_AGGIORNAMENTI_FINTI", "IMPAGINATORE_GETTONE", "IMPAGINATORE_FINESTRA", "PYTHONPATH", "PYTHONHOME"): self.env.pop(k, None)
        self.processi = []

    def lancia(self, *argomenti, prefisso=(), **k):
        p = subprocess.Popen([*prefisso, str(self.exe), *argomenti], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",  # nosec B603  # il programma da provare
                             env=self.env, cwd=str(self.dir), **k)
        self.processi.append(p)
        return p

    def avvia_schermata(self, *altri, prefisso=()):
        inizio = time.time()
        p = self.lancia("--porta", "0", "--progetti", str(self.progetti), *altri, prefisso=prefisso)
        righe = []
        while True:
            r = p.stdout.readline()
            if not r: raise NonVa("la schermata si è chiusa prima di aprire la porta:\n" + "".join(righe)[-3000:])
            righe.append(r); m = re.search(r"http://127\.0\.0\.1:(\d+)/", r)
            if m: break
        porta = int(m.group(1))
        sess = self.dati / "sessioni" / f"home-{porta}.json"
        attendi(sess.exists, 30)
        return p, Client(porta, json.loads(sess.read_text(encoding="utf-8"))["gettone"]), time.time() - inizio, righe

    def chiudi_tutto(self):
        for p in self.processi:
            if p.poll() is None: p.kill(); p.wait(10)


def programma_dir(exe):
    exe = Path(exe).resolve()
    return exe.parent.parent if exe.parent.name == "MacOS" else exe.parent


def dati_mancanti(sorgente, pacchetto):
    """file di dati del pacchetto `impaginatore` del sorgente (tutto tranne il codice) che non sono nel programma, nella
    cartella `pacchetto` (quella con risorse/)"""
    return sorted(p.relative_to(sorgente).as_posix() for p in sorgente.rglob("*")
                  if p.is_file() and p.suffix not in (".py", ".pyc") and "__pycache__" not in p.parts and not p.name.startswith(".") and not (pacchetto / p.relative_to(sorgente)).is_file())


@controllo("file")
def prova_file(exe):
    d = programma_dir(exe)
    sorgenti = [str(p.relative_to(d)) for p in d.rglob("*") if p.suffix in (".py", ".pyc") and "impaginatore" in p.relative_to(d).parts]
    deve(not sorgenti, f"file sorgente del programma nel pacchetto: {sorgenti[:5]}")
    for n in ("avvio.html", "home.html", "index.html", "album_libere.py.txt", "testo.py.txt", "componenti.json", "tier.json", "haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
        deve(any(d.rglob(n)), f"manca {n}")
    mancano = dati_mancanti(RADICE / "src" / "impaginatore", next(d.rglob("avvio.html")).parent.parent)
    deve(not mancano, f"file di dati del pacchetto che mancano nel programma: {mancano[:5]}")
    RAPPORTO["misure"] = dict(programma_mb=round(sum(p.stat().st_size for p in d.rglob("*") if p.is_file()) / 1e6, 1),
                              file=sum(1 for p in d.rglob("*") if p.is_file()), eseguibile_mb=round(Path(exe).stat().st_size / 1e6, 1))


@controllo("versione")
def prova_versione(pr, attesa):
    inizio = time.time()
    r = subprocess.run([str(pr.exe), "--versione"], capture_output=True, text=True, encoding="utf-8", env=pr.env, timeout=120)  # nosec B603
    RAPPORTO["tempi"]["versione_s"] = round(time.time() - inizio, 2)
    deve(r.returncode == 0 and r.stdout.strip() == f"Impaginatore {attesa}", f"«--versione» ha risposto {r.returncode} {r.stdout!r} {r.stderr[-500:]!r}")


@controllo("avvio")
def prova_avvio(pr, attesa):
    """la schermata di avvio del programma compilato legge versione e licenza. La beta privata («Beta privata») vuole una
    chiave firmata con la chiave vera: si prova nei test (tests/test_avvio.py), non qui"""
    def pagina(**env):
        r = subprocess.run([str(pr.exe), "_avvio"], capture_output=True, env=dict(pr.env, **env), timeout=120)  # nosec B603
        deve(r.returncode == 0, f"«_avvio»: {r.returncode} {r.stderr[-500:]!r}")
        return r.stdout.decode("utf-8")
    p = pagina()
    deve(f"Versione {attesa}" in p and re.search(r"base64,[A-Za-z0-9+/=]{10000,}\)", p), "versione o carattere mancanti nella schermata di avvio")
    deve('<span class="licenza prova">Prova gratuita · 30 giorni</span>' in p, "la schermata di avvio non dice «Prova gratuita · 30 giorni»")
    deve('<span class="licenza prova">Free trial · 30 days left</span>' in pagina(IMPAGINATORE_LINGUA="en"), "schermata di avvio in inglese")
    finita = pr.dir / "dati-prova-finita"; (finita / "licenza").mkdir(parents=True)
    t = time.time() - 40 * 86400
    (finita / "licenza" / "prova.json").write_text(json.dumps(dict(formato=1, inizio=t, visto=t)), encoding="utf-8")
    deve('<span class="licenza sola">Sola lettura</span>' in pagina(IMPAGINATORE_DATI=str(finita)), "prova finita: la schermata di avvio non dice «Sola lettura»")
    RAPPORTO["avvio"] = ["Prova gratuita · 30 giorni", "Free trial · 30 days left", "Sola lettura"]


def copia_finta(pr):
    """una «versione aggiornata» 9.9.9 completa nella cartella dei dati, come la lascerebbe un aggiornamento da Python:
    se partisse, scriverebbe un segno accanto a sé"""
    v = pr.dati / "programma" / "versioni" / "9.9.9"; (v / "impaginatore").mkdir(parents=True)
    segno = pr.dir / "COPIA-AVVIATA"
    (v / "impaginatore" / "__init__.py").write_text(f'__version__ = "9.9.9"\nopen({str(segno)!r}, "w").close()\n', encoding="utf-8")
    (v / ".completa").write_text('{"versione": "9.9.9", "file": 1}', encoding="utf-8")
    (pr.dati / "programma" / "attuale.json").write_text(json.dumps(dict(formato=1, versione="9.9.9", precedente=None, confermata=True, tentativi=0, scartata=None)), encoding="utf-8")
    return segno


@controllo("schermata")
def prova_schermata(c, attesa, segno):
    deve(c.get("/api/ping")["ok"] is True, "ping")
    a = c.get("/api/aggiornamento")
    deve(a["attuale"]["n"] == attesa, f"versione in uso {a['attuale']['n']}: è partita un'altra copia")
    deve(not segno.exists(), "il programma compilato ha eseguito codice dalla cartella dei dati")
    deve(a.get("manuale") is True and a["da_aggiornare"] is False, f"aggiornamenti: {a}")
    lic = c.get("/api/licenza"); deve(isinstance(lic, dict) and lic, "licenza")
    deve("<html" in c.testo("/").lower(), "la pagina della schermata")
    deve(isinstance(c.get("/api/progetti")["progetti"], list), "elenco degli album")


def crea_foto(cartella, n):
    from aiuti import FOTO_SCENARIO
    from aiuti import crea_foto as crea
    return crea(str(cartella), FOTO_SCENARIO[:n])


@controllo("editor")
def prova_editor(pr, c):
    p = c.post("/api/nuovo", {"nome": "Prova del pacchetto", "w": 30, "h": 30})["path"]
    crea_foto(Path(p) / "Foto", 6)
    inizio = time.time()
    ep = c.post("/api/apri", {"path": p})["porta"]
    attendi(lambda: c.get(f"/api/pronto?porta={ep}")["pronto"], 300, 0.5)
    RAPPORTO["tempi"]["editor_pronto_s"] = round(time.time() - inizio, 2)
    sess = pr.dati / "sessioni" / f"editor-{ep}.json"
    e = Client(ep, json.loads(sess.read_text(encoding="utf-8"))["gettone"])
    st = e.get("/api/state"); nomi = [f["n"] for f in st["photos"]]
    deve(len(nomi) == 6, f"foto viste dall'editor: {len(nomi)}")
    for k in range(3):
        t = e.post("/api/templates", {"photos": nomi[2 * k:2 * k + 2]})["items"][0]
        st = e.post("/api/op", dict(cid="verifica", rev=st["rev"], op="newspread", pos=k, L=t["L"], R=t["R"]))
    deve(len(st["spreads"]) == 3, "spread")
    for fmt, corpo, segno in (("jpg", {"fmt": "jpg", "res": "bozza"}, "ESPORTATI 3 spread su 3"), ("pdf", {"fmt": "pdf", "width": 600}, "RISULTATO:")):
        inizio = time.time()
        e.post("/api/export", corpo)
        L = attendi(lambda: (lambda x: x if "[finito]" in x else None)(e.get("/api/log")), 600, 0.25)
        RAPPORTO["tempi"][f"esporta_{fmt}_s"] = round(time.time() - inizio, 2)
        deve(any(segno in x for x in L), f"esportazione {fmt}: {L[-5:]}")
    jpg = sorted((Path(p) / "Esportazioni" / "JPG").glob("*.jpg"))
    deve(len(jpg) == 3, f"JPG esportati: {[j.name for j in jpg]}")
    return p, e


@controllo("progetto 1.x")
def prova_progetto_1x(pr, c):
    from aiuti import FOTO_SCENARIO
    d = pr.progetti / "Album della 1.5.2"; crea_foto(d / "Foto", len(FOTO_SCENARIO))
    dati = RADICE / "tests" / "dati" / "progetto_152"
    shutil.copy(dati / "spec.py", d / "spec.py")
    (d / "progetto.json").write_text((dati / "progetto.json").read_text(encoding="utf-8").replace("{PROGETTO}", str(d).replace("\\", "/")), encoding="utf-8")
    deve(any(x["path"] == str(d) for x in c.get("/api/progetti")["progetti"]), "il progetto della 1.5.2 non è in elenco")
    ep = c.post("/api/apri", {"path": str(d)})["porta"]
    attendi(lambda: c.get(f"/api/pronto?porta={ep}")["pronto"], 300, 0.5)
    e = Client(ep, json.loads((pr.dati / "sessioni" / f"editor-{ep}.json").read_text(encoding="utf-8"))["gettone"])
    st = e.get("/api/state")
    deve(len(st["spreads"]) > 0 and (d / "album.json").exists(), "il progetto della 1.5.2 non si è aperto (album.json)")
    dest = d / "Consegna"; dest.mkdir()
    out = Path(e.post("/api/prj_esporta", {"dest": str(dest), "v1x": True, "foto": False})["cartella"])
    attendi(lambda: (lambda x: x if "[finito]" in x else None)(e.get("/api/log")), 300, 0.25)
    for n in ("spec.py", "album_libere.py", "testo.py", "vib_lut.npz", "album.json"):
        deve((out / n).exists(), f"progetto esportato per la 1.x senza {n}")
    deve("def _zcrop" in (out / "album_libere.py").read_text(encoding="utf-8"), "la copia del motore non è il sorgente di album_libere.py")


@controllo("psd")
def prova_psd(pr, album):
    r = subprocess.run([str(pr.exe), "_psd", "--progetto", album, "--spread", "1"], capture_output=True, text=True, encoding="utf-8", env=pr.env, timeout=300)  # nosec B603
    if r.returncode == 0: RAPPORTO["psd"] = "Photoshop presente: PSD generato"; return
    deve("Photoshop" in r.stderr and "Traceback" not in r.stderr, f"«_psd»: {r.returncode} {r.stdout[-300:]!r} {r.stderr[-500:]!r}")
    RAPPORTO["psd"] = r.stderr.strip()[-200:]


@controllo("mcp")
def prova_mcp(pr):
    p = subprocess.Popen([str(pr.exe), "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=pr.env)  # nosec B603
    try:
        def manda(m): p.stdin.write(json.dumps(m) + "\n"); p.stdin.flush()
        def ricevi(i):
            while True:
                r = p.stdout.readline()
                if not r: raise NonVa("il server MCP si è chiuso: " + p.stderr.read()[-2000:])
                m = json.loads(r)
                if m.get("id") == i: return m
        manda(dict(jsonrpc="2.0", id=1, method="initialize", params=dict(protocolVersion="2025-06-18", capabilities={}, clientInfo=dict(name="verifica", version="1"))))
        r = ricevi(1); deve("result" in r, f"initialize: {r}")
        manda(dict(jsonrpc="2.0", method="notifications/initialized"))
        manda(dict(jsonrpc="2.0", id=2, method="tools/list"))
        t = ricevi(2)["result"]["tools"]
        deve(len(t) >= 5 and all(x.get("name") and x.get("description") for x in t), f"strumenti MCP senza nome o descrizione: {t[:2]}")
        RAPPORTO["mcp_strumenti"] = len(t)
    finally:
        p.stdin.close(); p.wait(30) if p.poll() is None else None
        if p.poll() is None: p.kill()


@controllo("chiusura")
def prova_chiusura(p, c, porte):
    deve(c.post("/api/esci") == {"ok": True}, "/api/esci")
    deve(p.wait(60) == 0, f"uscita {p.returncode}")
    import socket
    def chiusa(pt):
        with socket.socket() as s: return s.connect_ex(("127.0.0.1", pt)) != 0
    attendi(lambda: all(chiusa(x) for x in porte), 60)


def cattura(display):
    """lo schermo di Xvfb (xwd -root) come immagine RGB di Pillow, o None"""
    try: r = subprocess.run(["xwd", "-root", "-silent", "-display", display], capture_output=True, timeout=30)  # nosec B603, B607  # xwd del sistema
    except (OSError, subprocess.TimeoutExpired): return None
    d = r.stdout
    if r.returncode or len(d) < 100: return None
    h = struct.unpack(">25I", d[:100])                      # XWDFileHeader: dimensione, …, larghezza 4, altezza 5, ordine 7, bit 11, riga 12, colori 19
    modi = {32: ("BGRX", "XRGB"), 24: ("BGR", "RGB")}       # 24 bit (3 byte, righe lunghe come a 32) quando sullo schermo c'è una
    if h[11] not in modi: return None                       # finestra di profondità diversa, come la schermata di avvio
    from PIL import Image
    inizio = h[0] + h[19] * 12
    return Image.frombuffer("RGB", (h[4], h[5]), d[inizio:inizio + h[12] * h[5]], "raw", modi[h[11]][h[7] != 0], h[12], 1)


FONDO_AVVIO = (0x18, 0x17, 0x15)                            # desktop.avvio.FONDO


def con_avvio(img):
    """la schermata di avvio (480 × 300, al centro, fondo Inchiostro) è sullo schermo"""
    w, h = img.size; x0, y0 = (w - 480) // 2, (h - 300) // 2
    punti = [img.getpixel((x0 + 10 + i * 46, y0 + 6 + j * 28)) for i in range(10) for j in range(10)]
    return sum(all(abs(a - b) <= 3 for a, b in zip(px, FONDO_AVVIO)) for px in punti) >= 60


def con_programma(img):
    """la finestra del programma (più grande della schermata di avvio, al centro) è sullo schermo: fuori dal rettangolo
    della schermata di avvio non c'è solo il nero del fondo di Xvfb, e la schermata di avvio non c'è più"""
    w, h = img.size
    punti = [img.getpixel((w // 2 + dx, h // 2 + dy)) for dx in (-300, 0, 300) for dy in (-200, 200)]
    return sum(px != (0, 0, 0) for px in punti) >= 4 and not con_avvio(img)


def dettaglio(img):
    """quanti colori diversi ci sono sullo schermo: una pagina disegnata ne ha più del suo solo fondo"""
    return len(img.getcolors(1 << 20) or ())


def fotografa(cartella, nome, vede, secondi=20, finche=3.0):
    """sotto Xvfb: aspetta che lo schermo mostri `vede` e lo salva in <cartella>/<nome>. Fra le fotografie in cui si vede
    (per al massimo `finche` secondi, o finché non si vede più) tiene quella con più dettaglio: la pagina già disegnata,
    non il solo colore di fondo della finestra. Dice se l'ha visto; None se lo schermo non si può leggere qui"""
    display = os.environ.get("DISPLAY")
    if not (display and shutil.which("xwd") and cartella): return None
    fine, migliore, punti = time.time() + secondi, None, -1
    while time.time() < fine:
        img = cattura(display)
        if img is not None and vede(img):
            if migliore is None: fine = min(fine, time.time() + finche)
            p = dettaglio(img)
            if p > punti: migliore, punti = img, p
        elif migliore is not None: break                    # non si vede più: la schermata di avvio si è chiusa
        time.sleep(0.1)
    if migliore is None: return False
    Path(cartella).mkdir(parents=True, exist_ok=True); migliore.save(Path(cartella) / nome)
    return True


def fotografa_avvio(cartella, secondi=20):
    """la schermata di avvio, in avvio-finestra.png"""
    return fotografa(cartella, "avvio-finestra.png", con_avvio, secondi)


@controllo("finestra")
def prova_finestra(pr, immagini=None):
    prefisso = ("xvfb-run", "-a", "-s", "-screen 0 1280x800x24") if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") else ()
    pr.env.pop("IMPAGINATORE_DIALOGHI", None)
    p, c, secondi, righe = pr.avvia_schermata(prefisso=prefisso)
    RAPPORTO["tempi"]["finestra_porta_s"] = round(secondi, 2)
    if not prefisso:
        vista = fotografa_avvio(immagini)
        if vista is not None: RAPPORTO["schermata_avvio_vista"] = vista; print(f"    schermata di avvio {'vista e fotografata' if vista else 'NON vista'}", flush=True)
    c.get("/api/progetti")                                                       # la schermata Album è pronta: finisce la schermata di avvio
    if not prefisso:
        vista = fotografa(immagini, "finestra-programma.png", con_programma)
        if vista is not None: RAPPORTO["finestra_programma_vista"] = vista
        deve(vista is not False, "dopo la schermata di avvio la finestra del programma non si vede")
    time.sleep(3)
    deve(p.poll() is None, "il programma si è chiuso")
    c.post("/api/esci")
    try: p.wait(60)
    except subprocess.TimeoutExpired: raise NonVa("la finestra non si è chiusa con /api/esci") from None
    uscita = "".join(righe) + p.stdout.read()
    deve("non disponibile" not in uscita, "finestra non aperta: " + next((r for r in uscita.splitlines() if "non disponibile" in r), "")[-300:])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="verifica_pacchetto", description=__doc__.split("\n")[0])
    ap.add_argument("programma"); ap.add_argument("--finestra", action="store_true"); ap.add_argument("--rapporto")
    ap.add_argument("--immagini", help="dove salvare la fotografia della schermata di avvio (di serie la cartella del rapporto)")
    ap.add_argument("--versione", help="versione attesa (di serie quella di src/impaginatore/__init__.py)")
    a = ap.parse_args(argv)
    attesa = a.versione or re.search(r'__version__ = "([^"]+)"', (RADICE / "src" / "impaginatore" / "__init__.py").read_text(encoding="utf-8")).group(1)
    RAPPORTO.update(programma=str(Path(a.programma).resolve()), versione=attesa, sistema=sys.platform)
    esito = 0
    with tempfile.TemporaryDirectory(prefix="verifica-") as d:
        pr = Prova(a.programma, d)
        try:
            prova_file(a.programma)
            prova_versione(pr, attesa)
            prova_avvio(pr, attesa)
            segno = copia_finta(pr)
            p, c, secondi, _ = pr.avvia_schermata("--no-browser")
            RAPPORTO["tempi"]["schermata_porta_s"] = round(secondi, 2)
            prova_schermata(c, attesa, segno)
            album, e = prova_editor(pr, c)
            prova_progetto_1x(pr, c)
            prova_psd(pr, album)
            prova_mcp(pr)
            prova_chiusura(p, c, [c.porta, e.porta])
            if a.finestra: prova_finestra(pr, a.immagini or (str(Path(a.rapporto).resolve().parent) if a.rapporto else None))
        except NonVa: esito = 1
        finally: pr.chiudi_tutto()
    if a.rapporto: Path(a.rapporto).write_text(json.dumps(RAPPORTO, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(dict(tempi=RAPPORTO["tempi"], misure=RAPPORTO.get("misure")), ensure_ascii=False))
    print("Tutto a posto." if esito == 0 else "Un controllo non è andato.")
    return esito


if __name__ == "__main__":
    sys.exit(main())
