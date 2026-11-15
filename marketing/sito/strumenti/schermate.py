"""Schermate PROVVISORIE dell'editor attuale con l'album dimostrativo (marketing/demo), per la pagina di vendita.

L'interfaccia verrà ridisegnata (compito T-205): queste immagini servono finché non ci sono le definitive.
Lo script lavora su una COPIA delle foto in una cartella di lavoro e con una casa finta: non tocca né le foto
di marketing/demo né i progetti o le impostazioni dell'utente.

    .venv/bin/python marketing/sito/strumenti/schermate.py --lavoro /percorso/temporaneo

Cosa fa:
1. copia le 62 foto in <lavoro>/foto e crea un album 30 × 30 cm (spread 60 × 30 cm, abbondanza 3 mm);
2. avvia l'editor in questo processo e costruisce la bozza: le foto in ordine di scatto, a gruppi, ciascun
   gruppo nel primo modello che l'editor propone (lo stesso che vedi in «Modelli»); poi uniforma gli stacchi;
3. apre l'editor in Chrome senza schermo e salva le schermate in marketing/sito/img/originali/ (PNG grandi,
   esclusi da git); `sito.py immagini` ne ricava i WebP pubblicati.

Le foto restano nella cartella di lavoro: nessuna rete, nessun caricamento.
"""
import argparse
import json
import os
import shutil
import sys
import threading
import time

QUI = os.path.dirname(os.path.abspath(__file__))
SITO = os.path.dirname(QUI)
RADICE = os.path.dirname(os.path.dirname(SITO))
sys.path.insert(0, QUI)
import cromo  # noqa: E402

# gruppi di foto per spread, in ordine: alternano spread pieni, coppie e piccole sequenze (ritmo di un album vero)
RITMO = [2, 3, 4, 2, 3, 2, 4, 3, 2, 3, 4, 2]


def prepara_ambiente(lavoro):
    casa = os.path.join(lavoro, "casa")
    for k, v in dict(HOME=casa, USERPROFILE=casa, APPDATA=os.path.join(casa, "AppData"), LOCALAPPDATA=os.path.join(casa, "Local"),
                     XDG_DATA_HOME=os.path.join(casa, "share"), XDG_CACHE_HOME=os.path.join(casa, "cache"), XDG_CONFIG_HOME=os.path.join(casa, "config"),
                     IMPAGINATORE_PROGETTI=os.path.join(lavoro, "Progetti"), IMPAGINATORE_DATI=os.path.join(casa, "dati"),
                     IMPAGINATORE_CACHE=os.path.join(casa, "cache-imp")).items():
        os.makedirs(v, exist_ok=True) if k != "IMPAGINATORE_PROGETTI" else None
        os.environ[k] = v
    os.environ.update(IMPAGINATORE_DIALOGHI="nessuno", IMPAGINATORE_AGGIORNAMENTI="no", IMPAGINATORE_SENZA_RIAVVIO="1")


def costruisci_album(lavoro, foto):
    from impaginatore import aggiornamenti
    from impaginatore.home import server as H
    H.configura(os.path.join(lavoro, "Progetti"), 0, aggiornamenti.NonDisponibili())
    p = H.nuovo({"nome": "Album dimostrativo", "w": "60", "h": "30", "abb": "3", "spazio": "3", "margine": "10"})
    for f in sorted(os.listdir(foto)):
        if f.lower().endswith(".jpg"): shutil.copy(os.path.join(foto, f), os.path.join(p, "Foto", f))
    return p


def avvia_editor(progetto):
    from impaginatore.editor import server as E
    E.riavvia_processo = lambda: None
    E.inizializza(progetto, home="http://127.0.0.1:9")
    srv = E.crea_server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return E, srv


def scegli(proposte):
    """fra i modelli proposti dall'editor, il più adatto (costo minore) che riempie tutte e due le pagine, se c'è"""
    piene = [t for t in proposte if "BLANK" not in (t["L"]["module"], t["R"]["module"])]
    return min(piene or proposte, key=lambda t: t["cost"])


def bozza(E):
    """la bozza dell'album: foto in ordine di scatto, a gruppi (le panoramiche da sole), nel modello proposto più adatto"""
    st = E.state()
    foto = sorted(st["photos"], key=lambda f: (f["dt"] or "", f["n"]))
    nomi = [f["n"] for f in foto]; pano = {f["n"] for f in foto if f["ar"] >= 1.8}
    k = pos = r = 0
    while k < len(nomi):
        if nomi[k] in pano: n = 1
        else:
            n = min(RITMO[r % len(RITMO)], len(nomi) - k); r += 1
            fino = next((j for j in range(k, k + n) if nomi[j] in pano), k + n); n = max(1, fino - k)
        gruppo = nomi[k:k + n]
        d = E.templates_for(gruppo); prop = (d.get("items") or []) + (d.get("piu") or [])
        if not prop and n > 1:                       # nessun modello per questo gruppo: uno spread per foto
            gruppo = gruppo[:1]; d = E.templates_for(gruppo); prop = (d.get("items") or []) + (d.get("piu") or [])
        if not prop: k += len(gruppo); continue
        t = scegli(prop)
        E.do_op(dict(op="newspread", pos=pos, L=t["L"], R=t["R"]))
        pos += 1; k += len(gruppo)
    E.save()
    return E.state()


def rettangolo(c, selettore):
    """riquadro (x, y, larghezza, altezza) in px CSS di un elemento della pagina"""
    return c.valuta(f"(() => {{ const r = document.querySelector({json.dumps(selettore)}).getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }})()")


def schermate(url, uscita, spread_eroe, spread_dettaglio):
    os.makedirs(uscita, exist_ok=True)
    fatte = {}
    with cromo.Chrome() as c:
        # 1. l'editor intero, finestra 1440 × 900 a densità 2: lo spread dell'apertura in vista
        c.vista(1440, 900, 2)
        c.apri(url)
        time.sleep(2)
        c.valuta(f"(async () => {{ cur = {spread_eroe}; sel = null; render(); return true; }})()")
        time.sleep(4)
        fatte["editor-album"] = c.foto(os.path.join(uscita, "editor-album.png"), pagina_intera=False)
        # 2. controllo degli stacchi su tutto l'album: solo la finestra che elenca gli spread con spazi diversi
        c.valuta("(async () => { gapAll(); return true; })()")
        time.sleep(4)
        fatte["controllo-stacchi"] = c.foto(os.path.join(uscita, "controllo-stacchi.png"), pagina_intera=False, ritaglio=rettangolo(c, "#gapall .a_gc"))
        c.valuta("(async () => { const g = document.getElementById('gapall'); if (g) g.remove(); return true; })()")
        # 3. uno spread di dettaglio: solo la tela, con i righelli in centimetri
        c.valuta(f"(async () => {{ cur = {spread_dettaglio}; sel = null; render(); return true; }})()")
        time.sleep(4)
        fatte["editor-spread"] = c.foto(os.path.join(uscita, "editor-spread.png"), pagina_intera=False, ritaglio=rettangolo(c, "#stage"))
    return fatte


def spread_renderizzati(E, uscita, quali, larghezza=2000):
    """gli spread come li esporta il motore (stessa resa dell'export), lato lungo «larghezza» px"""
    from impaginatore.motore import album as A
    fatti = []
    for n, s in enumerate(quali, 1):
        K = larghezza / (A.CW if hasattr(A, "CW") and A.CW else larghezza)
        dati = E.spread_jpg(s, K)
        p = os.path.join(uscita, f"spread-{n:02d}.jpg")
        with open(p, "wb") as f: f.write(dati)
        fatti.append(p)
    return fatti


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lavoro", required=True, help="cartella temporanea (verrà creata): copia delle foto, progetto, casa finta")
    ap.add_argument("--foto", default=os.path.join(RADICE, "marketing", "demo", "foto"))
    ap.add_argument("--uscita", default=os.path.join(SITO, "img", "originali"))
    ap.add_argument("--eroe", type=int, default=None, help="indice dello spread per la schermata grande (da 0)")
    ap.add_argument("--dettaglio", type=int, default=None, help="indice dello spread di dettaglio (da 0)")
    ap.add_argument("--spread", default="", help="indici degli spread da rendere come immagini, separati da virgole")
    ap.add_argument("--solo-bozza", action="store_true", help="costruisce l'album e rende tutti gli spread in piccolo, per sceglierli")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.foto) or not any(f.endswith(".jpg") for f in os.listdir(a.foto)):
        sys.exit(f"mancano le foto dimostrative in {a.foto}: rigenerale con «uv run marketing/demo/scarica_demo.py»")
    lavoro = os.path.abspath(a.lavoro)
    if os.path.commonpath([lavoro, RADICE]) == RADICE: sys.exit("la cartella di lavoro deve stare fuori dal repository")
    prepara_ambiente(lavoro)
    sys.path.insert(0, os.path.join(RADICE, "src"))
    progetto = costruisci_album(lavoro, a.foto)
    E, srv = avvia_editor(progetto)
    try:
        st = bozza(E)
        n = len(st["spreads"])
        print(f"album: {progetto} · {n} spread · {len(st['photos'])} foto")
        if a.solo_bozza:
            prove = os.path.join(lavoro, "prove"); os.makedirs(prove, exist_ok=True)
            for s in range(n):
                with open(os.path.join(prove, f"spread-{s:02d}.jpg"), "wb") as f: f.write(E.spread_jpg(s, 0.12))
            print("spread in piccolo:", prove)
            return 0
        eroe = a.eroe if a.eroe is not None else min(3, n - 1)
        dett = a.dettaglio if a.dettaglio is not None else min(5, n - 1)
        url = f"http://127.0.0.1:{srv.server_address[1]}/"
        fatte = schermate(url, a.uscita, eroe, dett)
        quali = [int(x) for x in a.spread.split(",") if x.strip()] if a.spread else []
        if quali:
            for p in spread_renderizzati(E, a.uscita, quali): fatte[os.path.basename(p)] = p
        with open(os.path.join(a.uscita, "schermate.json"), "w", encoding="utf-8") as f:
            json.dump(dict(creato=time.strftime("%Y-%m-%d %H:%M"), progetto=progetto, spread=n, eroe=eroe, dettaglio=dett, spread_renderizzati=quali, file=sorted(fatte)), f, ensure_ascii=False, indent=2)
        for k, v in sorted(fatte.items()): print(k, "→", v)
    finally:
        srv.shutdown(); srv.server_close()
        try: E.ferma()
        except Exception: pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
