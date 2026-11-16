"""Schermate dell'interfaccia 2.0 (T-205) per docs/prodotto/ux/schermate/2.0/: avvia la schermata degli album e
l'editor in questo processo, su una casa finta e un album di foto sintetiche, li apre in Chrome senza schermo e salva
una PNG per scena, nei due temi e nelle due misure di riferimento (1280 × 800 e 1920 × 1080).

    python strumenti/schermate_ux.py [--uscita CARTELLA] [--solo home|editor] [SCENA ...]

Serve Chrome o Chromium. Non tocca i dati dell'utente: tutto sta in una cartella temporanea che si cancella alla fine.
Le scene dell'editor preparano lo stato con le stesse API della pagina (nessuna scorciatoia nel server)."""
import argparse
import base64
import math
import os
import shutil
import sys
import tempfile
import threading
import time

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RADICE, "src")); sys.path.insert(0, os.path.join(RADICE, "tests"))
MISURE = ((1280, 800), (1920, 1080))
TEMI = ("scuro", "chiaro")


def ambiente(casa):
    """come la fixture «casa» dei test: niente dati veri, finestre, rete, aggiornamenti o riavvii; licenza in prova"""
    for k, v in dict(HOME=casa, USERPROFILE=casa, APPDATA=os.path.join(casa, "AppData"), LOCALAPPDATA=os.path.join(casa, "AppData", "Local"),
                     XDG_DATA_HOME=os.path.join(casa, ".local", "share"), XDG_CACHE_HOME=os.path.join(casa, ".cache"), XDG_CONFIG_HOME=os.path.join(casa, ".config"),
                     IMPAGINATORE_PROGETTI=os.path.join(casa, "Progetti"), IMPAGINATORE_DATI=os.path.join(casa, "dati"), IMPAGINATORE_CACHE=os.path.join(casa, "cache"),
                     IMPAGINATORE_DIALOGHI="nessuno", IMPAGINATORE_AGGIORNAMENTI="no", IMPAGINATORE_SENZA_RIAVVIO="1").items():
        os.environ[k] = v


def foto_finte(cartella, n=36):
    """foto sintetiche dai toni calmi (cielo, terra, un soggetto chiaro), orizzontali, verticali e quadrate, con la data"""
    from PIL import Image, ImageDraw, ImageFilter
    os.makedirs(cartella, exist_ok=True)
    tinte = [((196, 206, 214), (120, 110, 96)), ((226, 214, 196), (96, 104, 82)), ((178, 190, 200), (70, 74, 80)), ((232, 222, 210), (150, 126, 104)),
             ((205, 196, 186), (88, 92, 70)), ((160, 172, 180), (60, 58, 54))]
    forme = [(1200, 800), (800, 1200), (1000, 1000), (1200, 800), (1200, 800), (800, 1200)]
    for k in range(n):
        w, h = forme[k % len(forme)]; cielo, terra = tinte[k % len(tinte)]
        im = Image.new("RGB", (w, h)); d = ImageDraw.Draw(im); orizz = int(h * (0.55 + 0.1 * math.sin(k)))
        for y in range(h):
            a = cielo if y < orizz else terra; t = (y / orizz) if y < orizz else (y - orizz) / max(1, h - orizz)
            d.line([0, y, w, y], fill=tuple(int(c * (1 - 0.18 * t)) for c in a))
        cx, cy, r = int(w * (0.3 + 0.4 * ((k * 37) % 10) / 10)), int(orizz - h * 0.08), int(min(w, h) * 0.13)
        d.ellipse([cx - r, cy - r * 2, cx + r, cy + r * 2], fill=(236, 228, 218)); d.ellipse([cx - r // 2, cy - r * 3, cx + r // 2, cy - r * 2], fill=(214, 186, 160))
        im = im.filter(ImageFilter.GaussianBlur(2))
        ex = Image.Exif(); ex.get_ifd(0x8769)[36867] = f"2026:06:13 {10 + k // 6:02d}:{(k * 7) % 60:02d}:00"
        im.save(os.path.join(cartella, f"IMG_{4100 + k}.jpg"), "JPEG", quality=85, exif=ex.tobytes())


def scatta(b, percorso, larghezza, altezza, tema, prima="", attesa=0.8):
    b.chiama("Emulation.setDeviceMetricsOverride", width=larghezza, height=altezza, deviceScaleFactor=1, mobile=False)
    valore = "dark" if tema == "scuro" else "light"
    b.js(f"document.documentElement.dataset.theme = '{valore}'; window.dispatchEvent(new Event('resize'))")
    if prima: b.js(prima)
    b.pausa(attesa)
    r = b.chiama("Page.captureScreenshot", format="png")
    with open(percorso, "wb") as f: f.write(base64.b64decode(r["data"]))
    print(percorso, flush=True)


# scene: nome -> (server, javascript che prepara la pagina; None = com'è all'apertura). Le scene dell'editor partono
# dall'album con alcuni spread (prepara_album) e tornano allo stato iniziale con un ricaricamento della pagina.
SCENE_HOME = {
    "home-album": None,
    "home-nuovo": "document.querySelector('[data-azione=nuovo]')?.click() || (typeof openNew === 'function' && openNew())",
    "home-licenza": "document.getElementById('lic').click()",
    "home-riga": "document.querySelectorAll('#grid .riga')[0].focus()",
    "home-menu": "document.querySelectorAll('#grid .riga')[0].focus(); document.querySelector('#grid .riga [data-a=altro]').click()",
    "home-cestino": "document.querySelectorAll('#grid .riga')[1].focus(); document.querySelectorAll('#grid .riga')[1].querySelector('[data-a=altro]').click(); [...document.querySelectorAll('#menu button')].find(b => b.className === 'pericolo').click()",
}
SCENE_EDITOR = {
    "editor-impagina": "go(1)",
    "editor-selezione": "go(1); (() => { const it = slotsOf(1).find(i => i.k !== 't'); sel = { s: 1, side: it.side, idx: it.idx }; msel = [it.side + ':' + it.idx]; render(); })()",
    "editor-controlla": "go(0); typeof apriControlla === 'function' && apriControlla()",
    "editor-bozza": "typeof apriBozza === 'function' && apriBozza()",
    "editor-foto": "document.getElementById('tabF').click()",
    "editor-scorciatoie": "typeof keysOpen === 'function' && keysOpen()",
}


def prepara_album(c, n_spread=4):
    """qualche spread con le prime foto, come li farebbe la pagina (modelli per le foto scelte)"""
    st = c.get("/api/state"); nomi = [p["n"] for p in st["photos"]]; k = 0
    for s, n in enumerate((3, 4, 2, 5)[:n_spread]):
        t = c.post("/api/templates", {"photos": nomi[k:k + n]})["items"][0]; k += n
        c.post("/api/op", dict(op="newspread", pos=s, L=t["L"], R=t["R"]))
    c.post("/api/save")                                         # la schermata degli album legge spread e foto dal disco


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--uscita", default=os.path.join(RADICE, "docs", "prodotto", "ux", "schermate", "2.0"))
    ap.add_argument("--solo", choices=("home", "editor"))
    ap.add_argument("scene", nargs="*")
    a = ap.parse_args(argv)
    tmp = tempfile.mkdtemp(prefix="sch-", dir="/tmp" if os.path.isdir("/tmp") else None)       # percorso corto: Chrome non parte con un TMPDIR lungo
    try:
        ambiente(tmp); os.makedirs(a.uscita, exist_ok=True)
        from aiuti import Client
        from cdp import Browser

        from impaginatore import aggiornamenti
        from impaginatore.editor import server as E
        from impaginatore.home import server as H
        H.configura(os.path.join(tmp, "Progetti"), 0, aggiornamenti.NonDisponibili())
        hs = H.crea_server(0); threading.Thread(target=hs.serve_forever, daemon=True).start()
        hc = Client(hs.server_address[1], hs.sessione.gettone)
        progetti = []
        for nome, w, h, nf in (("Matrimonio Rossi Bianchi", 60, 22.5, 36), ("Battesimo di Serena", 50, 20, 12), ("Comunione Luca", 40, 30, 0)):
            p = H.nuovo({"nome": nome, "w": w, "h": h}); progetti.append(p)
            if nf: foto_finte(os.path.join(p, "Foto"), nf)
        E.inizializza(progetti[0], home=f"http://127.0.0.1:{hs.server_address[1]}")
        es = E.crea_server(0); threading.Thread(target=es.serve_forever, daemon=True).start()
        ec = Client(es.server_address[1], es.sessione.gettone); prepara_album(ec)
        os.utime(progetti[1], (time.time() - 86400 * 3,) * 2)
        with Browser(tmp) as b:
            for gruppo, scene, srv in (("home", SCENE_HOME, hs), ("editor", SCENE_EDITOR, es)):
                if a.solo and a.solo != gruppo: continue
                for nome, js in scene.items():
                    if a.scene and nome not in a.scene: continue
                    for tema in TEMI:
                        for w, h in MISURE:
                            b.apri(srv.indirizzo_avvio(), 2.5)
                            scatta(b, os.path.join(a.uscita, f"{nome}-{tema}-{w}x{h}.png"), w, h, tema, js or "", 1.2)
                    if b.problemi(): print("problemi nella pagina:", *b.problemi(), sep="\n  ", flush=True)
                    b.eventi.clear()
        es.shutdown(); es.server_close(); E.ferma(); hs.shutdown(); hs.server_close(); assert hc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
