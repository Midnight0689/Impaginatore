"""Schermate della versione 2.0 per il sito di vendita (T-501), in italiano e in inglese.

Avvia la schermata degli album e l'editor in questo processo, su una casa finta in una cartella temporanea, con un album di
foto SINTETICHE (le stesse forme di strumenti/schermate_ux.py, ingrandite tre volte perché la risoluzione basti alla stampa:
nessuna persona vera, nessuna foto di marketing/demo). Apre le pagine in Chrome senza schermo a densità 2, tema chiaro, e
salva un PNG per scena in marketing/sito/img/originali/ (esclusa da git); `sito.py immagini` ne ricava i WebP pubblicati.

    .venv/bin/python marketing/sito/strumenti/schermate.py [--lingua it|en|tutte] [--uscita CARTELLA] [SCENA ...]

Lo stato dell'album si prepara con le stesse API della pagina: la bozza è quella vera di «Prepara la bozza», applicata
così com'è. Niente rete, niente dati dell'utente: la cartella temporanea si cancella alla fine. Con un TMPDIR lungo Chrome
non parte: lo script usa /tmp.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
import time

QUI = os.path.dirname(os.path.abspath(__file__))
SITO = os.path.dirname(QUI)
RADICE = os.path.dirname(os.path.dirname(SITO))
for p in (os.path.join(RADICE, "src"), os.path.join(RADICE, "tests"), os.path.join(RADICE, "strumenti")):
    sys.path.insert(0, p)

FINESTRA = (1280, 800)              # la misura più comune di un portatile; densità 2: PNG da 2560 × 1600
DENSITA = 2
SPREAD_EROE = 2                     # spread in vista nella schermata grande (da 0)

# scene: nome -> (schermata «editor» o «home», JavaScript che prepara la pagina, ritaglio: selettore CSS o None = finestra intera)
SCENE = {
    # prima che la bozza entri nell'album: la finestra «Prepara la bozza» con la proposta
    "bozza": ("editor", "apriBozza()", "#bozd .dlg"),
    # dopo: l'editor con l'album, una disposizione alternativa, il controllo, l'esportazione
    "editor-album": ("editor", f"go({SPREAD_EROE})", None),
    "disposizione": ("editor", "go(1); altraDisp(1)", ("#stage", "#side")),
    "esporta-psd": ("editor", "openExp(); setFmt('psd')", "#exp .dlg"),
    # dopo due modifiche a mano (vedi ritocchi()): il controllo trova spazi e tono da sistemare
    "controlla": ("editor", "go(2); apriControlla(true)", None),
    # schermata degli album: un album nuovo con un prodotto del catalogo Generico, le impostazioni dell'assistente AI
    "nuovo-album": ("home", "openNew(); cataloghi().then(() => { const s = document.getElementById('prod'); s.value = 'generico/orizzontale-30x22'; prodotto(); })", "#vnew .dlg"),
    "assistente": ("home", "apriAssistente()", "#vassist .dlg"),
}


def foto_sintetiche(cartella, n=36, scala=3):
    """le foto di schermate_ux.foto_finte, ingrandite «scala» volte con la stessa data di scatto (EXIF)"""
    from PIL import Image
    from schermate_ux import foto_finte
    foto_finte(cartella, n)
    for f in sorted(os.listdir(cartella)):
        p = os.path.join(cartella, f); im = Image.open(p); exif = im.info.get("exif", b"")
        im.resize((im.width * scala, im.height * scala), Image.LANCZOS).save(p, "JPEG", quality=88, exif=exif)


def licenza_pro():
    """una licenza Pro attivata nella casa finta, firmata con una coppia di chiavi nata qui e buttata alla fine (come nei
    test): le schermate mostrano il programma come lo vede chi ha comprato il Pro (PSD compresi, niente filigrana)"""
    import secrets

    from aiuti import Chiavi

    from impaginatore import licenze
    from impaginatore.licenze import chiave as K
    ch = Chiavi(secrets.token_bytes(32))
    K.CHIAVI_PUBBLICHE = {1: K.Pubblica(ch.pubblica.hex())}
    os.makedirs(licenze.cartella(), exist_ok=True)
    with open(os.path.join(licenze.cartella(), "chiave.txt"), "w", encoding="utf-8") as f:
        f.write(ch.chiave(fascia="pro", computer=2, intestatario="Studio di prova") + "\n")


def ritocchi(c):
    """due modifiche a mano, come capitano lavorando: una foto più chiara (+0,9 EV) e una foto spostata di qualche
    millimetro nello spread 05–06. Così «Controlla» ha qualcosa da far sistemare a «Sistema»"""
    st = c.get("/api/state"); usate = [p["n"] for p in st["photos"] if p.get("sp") is not None]
    c.post("/api/op", {"op": "ev", "photo": usate[4], "value": 0.9})
    c.post("/api/op", {"op": "nudge", "s": 2, "ats": [["L", 1]], "dx": 0, "dy": 8})
    c.post("/api/save")


def scatta(b, percorso, js, ritaglio, attesa):
    w, h = FINESTRA
    b.chiama("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=DENSITA, mobile=False)
    b.js("document.documentElement.dataset.theme = 'light'; window.dispatchEvent(new Event('resize'))")
    if js: b.js(js)
    b.pausa(attesa)
    clip = None
    if ritaglio:              # un selettore, o più selettori: la larghezza di tutti, l'altezza del primo
        sel = [ritaglio] if isinstance(ritaglio, str) else list(ritaglio)
        r = b.js(f"(() => {{ const q = {json.dumps(sel)}.map(s => document.querySelector(s)); if (q.some(e => !e)) return null; const r = q.map(e => e.getBoundingClientRect()); "
                 "return [Math.min(...r.map(x => x.left)), r[0].top, Math.max(...r.map(x => x.right)) - Math.min(...r.map(x => x.left)), r[0].height]; })()")
        if not r: raise RuntimeError(f"{os.path.basename(percorso)}: non trovo {ritaglio}")
        clip = dict(x=r[0], y=r[1], width=r[2], height=r[3], scale=1)
    import base64
    d = b.chiama("Page.captureScreenshot", format="png", **({"clip": clip} if clip else {}))
    with open(percorso, "wb") as f: f.write(base64.b64decode(d["data"]))
    print(" ", os.path.relpath(percorso, RADICE), flush=True)


def una_lingua(lingua, uscita, scelte):
    from schermate_ux import ambiente
    tmp = tempfile.mkdtemp(prefix="sito-", dir="/tmp" if os.path.isdir("/tmp") else None)
    try:
        ambiente(tmp, lingua); licenza_pro()
        from aiuti import Client
        from cdp import Browser

        from impaginatore import aggiornamenti
        from impaginatore.editor import server as E
        from impaginatore.home import server as H
        H.configura(os.path.join(tmp, "Progetti"), 0, aggiornamenti.NonDisponibili())
        hs = H.crea_server(0); threading.Thread(target=hs.serve_forever, daemon=True).start()
        nomi = ("Matrimonio Rossi Bianchi", "Battesimo di Serena", "Comunione Luca") if lingua == "it" else ("Wedding Smith Jones", "Serena's christening", "Luke's communion")
        progetti = []
        for k, nome in enumerate(nomi):
            dati = {"nome": nome, "w": 60, "h": 22.5}
            if k == 0: dati["prodotto"] = "generico/orizzontale-30x22"
            progetti.append(H.nuovo(dati))
        foto_sintetiche(os.path.join(progetti[0], "Foto"))
        E.inizializza(progetti[0], home=f"http://127.0.0.1:{hs.server_address[1]}")
        es = E.crea_server(0); threading.Thread(target=es.serve_forever, daemon=True).start()
        ec = Client(es.server_address[1], es.sessione.gettone)
        suff = "" if lingua == "it" else "-en"
        voglio = lambda n: not scelte or n in scelte
        with Browser(tmp) as b:
            # 1. la bozza, prima di applicarla
            if voglio("bozza"):
                b.apri(es.indirizzo_avvio(), 2.5)
                scatta(b, os.path.join(uscita, f"bozza{suff}.png"), SCENE["bozza"][1], SCENE["bozza"][2], 4)
            # 2. la bozza vera nell'album, poi le altre scene dell'editor
            r = ec.post("/api/op", {"op": "bozza", "pos": 0}); ec.post("/api/save")
            print(f"  bozza applicata: {len(ec.get('/api/state')['spreads'])} spread", r.get("ok", ""), flush=True)
            for nome, (dove, js, rit) in SCENE.items():
                if nome == "bozza" or not voglio(nome): continue
                if nome == "controlla": ritocchi(ec)
                srv = es if dove == "editor" else hs
                b.apri(srv.indirizzo_avvio(), 2.5)
                scatta(b, os.path.join(uscita, f"{nome}{suff}.png"), js, rit, 4)
            if b.problemi(): print("  problemi nella pagina:", *b.problemi(), sep="\n    ", flush=True)
        es.shutdown(); es.server_close(); E.ferma(); hs.shutdown(); hs.server_close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lingua", choices=("it", "en", "tutte"), default="tutte")
    ap.add_argument("--uscita", default=os.path.join(SITO, "img", "originali"))
    ap.add_argument("scene", nargs="*", help=f"scene da rifare (di serie tutte): {', '.join(SCENE)}")
    a = ap.parse_args(argv)
    os.makedirs(a.uscita, exist_ok=True)
    for lingua in (("it", "en") if a.lingua == "tutte" else (a.lingua,)):
        print(f"lingua {lingua}:", flush=True)
        # ogni lingua in un processo a parte: editor e schermata tengono uno stato globale (progetto, lingua)
        if a.lingua == "tutte":
            import subprocess
            r = subprocess.run([sys.executable, os.path.abspath(__file__), "--lingua", lingua, "--uscita", a.uscita, *a.scene])
            if r.returncode: return r.returncode
        else:
            una_lingua(lingua, a.uscita, set(a.scene))
    with open(os.path.join(a.uscita, "schermate.json"), "w", encoding="utf-8") as f:
        json.dump(dict(creato=time.strftime("%Y-%m-%d %H:%M"), finestra=FINESTRA, densita=DENSITA, scene=list(SCENE)), f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
