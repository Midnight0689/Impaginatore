#!/usr/bin/env python
"""Editor leggero per gli album: server locale + pagina nel browser.

    python editor.py --progetto "<cartella con progetto.json e spec.py>" [--scripts <cartella degli script della skill>] [--porta 8765]

Usa il motore di impaginazione della skill (album.py): stessi moduli, stessa griglia, stesse anteprime.
Le modifiche stanno in memoria (con annulla/ripeti) finché non premi Salva: allora riscrive spec.py e progetto.json,
dopo aver copiato le versioni precedenti in <progetto>/_backup_editor/.
"""
import argparse, copy, glob, hashlib, io, json, os, re, shutil, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ap = argparse.ArgumentParser()
ap.add_argument("--progetto", required=True)
ap.add_argument("--scripts")
ap.add_argument("--porta", type=int, default=8765)
ap.add_argument("--home", default="")
ARGS = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(ARGS.progetto)

def _scripts():
    if ARGS.scripts: return os.path.abspath(ARGS.scripts)
    inc = os.path.join(os.path.dirname(HERE), "motore", "scripts")                 # il motore incluso nella cartella del programma (stessa versione su ogni Mac)
    if os.path.exists(os.path.join(inc, "album.py")): return inc
    base = os.path.expanduser("~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/*/*/skills/impaginazione-album-stefano/scripts")
    found = sorted(glob.glob(base), key=os.path.getmtime)
    if not found: raise SystemExit("Script della skill non trovati: passa --scripts <cartella>")
    return found[-1]
SCRIPTS = _scripts()
sys.path.insert(0, SCRIPTS)
os.environ["ALBUM_PROGETTO"] = PROJ
def _raccogli_foto():                                # foto importate in <progetto>/Foto quando il progetto legge un'altra cartella: le aggiungo, così compaiono sempre
    try:
        pj = os.path.join(PROJ, "progetto.json"); c = json.load(open(pj)); d = os.path.join(PROJ, "Foto")
        if not os.path.isdir(d) or os.path.abspath(d) == os.path.abspath(c.get("foto", "")): return
        have = set(c.get("foto_extra", [])); new = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith((".jpg", ".jpeg")) and not f.startswith(".") and os.path.join(d, f) not in have]
        if new: c["foto_extra"] = list(c.get("foto_extra", [])) + new; json.dump(c, open(pj, "w"), indent=2, ensure_ascii=False)
    except Exception as e: print("raccogli foto:", e, flush=True)
def _ripara_percorsi():
    """progetto spostato o copiato (altro Mac, disco esterno): ritrova da solo le cartelle e le foto che stanno dentro la cartella del progetto (…/Foto);
    quelle altrove si ricollegano dal pulsante «Progetto» dell'editor"""
    try:
        pj = os.path.join(PROJ, "progetto.json"); c = json.load(open(pj)); ch = False; base = os.path.join(PROJ, "Foto"); pc = c.get("esposizione", {}).get("per_cartella", {})
        foto = c.get("foto")
        if not foto:                                                              # progetto esportato: le foto stanno nella sua cartella Foto
            os.makedirs(base, exist_ok=True); c["foto"] = base; ch = True
        elif not os.path.isdir(foto):
            for cand in (os.path.join(PROJ, os.path.basename(foto.rstrip("/"))), base):
                if os.path.isdir(cand):
                    for k in list(pc):
                        if os.path.normpath(k) == os.path.normpath(foto): pc[cand] = pc.pop(k)
                    c["foto"] = cand; ch = True; break
        ex = [p if os.path.exists(p) or not os.path.exists(os.path.join(base, os.path.basename(p))) else os.path.join(base, os.path.basename(p)) for p in c.get("foto_extra", [])]
        if ex != c.get("foto_extra", []): c["foto_extra"] = ex; ch = True
        u = c.get("uscita_psd")
        if not u or not os.path.isdir(os.path.dirname(u.rstrip("/"))): c["uscita_psd"] = os.path.join(PROJ, "PSD"); ch = True
        if ch: json.dump(c, open(pj, "w"), indent=2, ensure_ascii=False)
        mp = os.path.join(PROJ, "_cache", "meta.json")
        if os.path.exists(mp):
            m = json.load(open(mp)); dirs = [d for d in (c.get("foto"), base) if d and os.path.isdir(d)]; mc = False
            for x in m:
                if not os.path.exists(x.get("src", "")):
                    for d in dirs:
                        if os.path.exists(os.path.join(d, x["n"])): x["src"] = os.path.join(d, x["n"]); mc = True; break
            if mc: json.dump(m, open(mp, "w"))
    except Exception as ex: print("ripara percorsi:", ex, flush=True)
_ripara_percorsi()
_raccogli_foto()
import album as A                                    # carica progetto.json, foto, miniature, volti
sys.path.insert(0, HERE)
import testo as TX
import album_libere as FL                            # insegna al motore le cornici libere (FREE), senza toccare la skill
from PIL import Image, ImageOps

LOCK = threading.RLock()
CFG = A.CFG
CFG.setdefault("esposizione", {}).setdefault("per_foto", {})
CFG.setdefault("centri_volto", {})
CFG.setdefault("tono", {}); CFG.setdefault("tolte", []); CFG.setdefault("testo", {}); CFG.setdefault("stili", {})

# ------------------------------------------------------------------ stato
NPH = {"BLANK": 0, "FULL": 1, "DUO": 2, "VLL": 3, "V4": 5, "G4": 4, "CV": 1, "SV": 1, "PP": 1, "COL2": 2, "BAND2": 2, "STRIP3": 3}
BUILD = {
    "BLANK": lambda p, m: [],
    "FULL": lambda p, m: [A.FULL(p[0])], "DUO": lambda p, m: A.DUO(*p), "VLL": lambda p, m: A.VLL(*p, mirror=m),
    "V4": lambda p, m: A.V4(*p, mirror=m), "G4": lambda p, m: A.G4(*p), "CV": lambda p, m: A.CV(*p), "SV": lambda p, m: A.SV(*p),
    "PP": lambda p, m: A.PP(*p), "COL2": lambda p, m: A.COL2(*p), "BAND2": lambda p, m: A.BAND2(*p), "STRIP3": lambda p, m: A.STRIP3(*p),
}
# ---- modelli dell'utente: layout di uno spread salvato per riusarlo (file nella cartella degli strumenti, valgono per tutti gli album)
UT_FILE = os.path.expanduser("~/.album-tools/modelli_utente.json")
UT_KEEP = ("k", "c", "r", "w", "h", "x", "y", "a", "zo")          # solo la geometria: foto, zoom e bianco/nero restano quelli della foto che ci va dentro

def ut_load():
    try: return json.load(open(UT_FILE))
    except Exception: return []

def ut_save(lst):
    os.makedirs(os.path.dirname(UT_FILE), exist_ok=True); tmp = UT_FILE + ".tmp"
    json.dump(lst, open(tmp, "w"), ensure_ascii=False, indent=1); os.replace(tmp, UT_FILE)

class _Build(dict):
    def __missing__(self, key):
        if isinstance(key, str) and key.startswith("U:"):
            _, tid, side = key.split(":"); t = next((x for x in ut_load() if x["id"] == tid), None)
            if not t: raise ValueError("modello non trovato (forse è stato eliminato)")
            items = t["pages"][0 if side == "L" else 1]["items"]
            return lambda p, m: [dict(it, i=p[j] - 1, bw=False, z=1.0) for j, it in enumerate(items)]
        raise KeyError(key)
BUILD = _Build(BUILD)

# modelli di pagina (modulo, modo, specchiato) usati dalla galleria "Modelli"
LAYS = [("FULL", "I", False), ("DUO", "I", False), ("VLL", "I", False), ("VLL", "I", True), ("V4", "I", False), ("V4", "I", True), ("G4", "I", False),
        ("STRIP3", "W", False), ("BLANK", "W", False), ("CV", "W", False), ("SV", "W", False), ("PP", "W", False), ("COL2", "W", False), ("BAND2", "W", False)]
SP = [[[mode, [dict(it) for it in items]] for (mode, items) in sp] for sp in A.load_spec()]
GD = [dict(v=list(g.get("v", [])), h=list(g.get("h", []))) for g in CFG.get("guide", [])][:len(SP)]       # linee guida di ogni spread (px della vista)
GD += [dict(v=[], h=[]) for _ in range(len(SP) - len(GD))]
UNDO, REDO = [], []
CLIP = []                                           # appunti: copia/incolla di elementi tra spread
LOG = []

def snap(): return json.dumps({"sp": SP, "ev": CFG["esposizione"], "ff": CFG["centri_volto"], "gd": GD, "tn": CFG["tono"], "tl": CFG["tolte"], "tx": CFG["testo"], "st": CFG["stili"]})
SAVED = snap()                                       # stato dell'ultimo salvataggio: serve a sapere se ci sono modifiche vere
def restore(s):
    global SP, GD
    d = json.loads(s); SP = d["sp"]; GD = d["gd"]
    CFG["esposizione"].clear(); CFG["esposizione"].update(d["ev"])
    CFG["centri_volto"].clear(); CFG["centri_volto"].update(d["ff"])
    A.FACE_FIX.clear(); A.FACE_FIX.update({k: tuple(v) for k, v in d["ff"].items()})
    CFG["tono"].clear(); CFG["tono"].update(d.get("tn", {})); CFG["tolte"][:] = d.get("tl", []); CFG["testo"].clear(); CFG["testo"].update(d.get("tx", {})); CFG["stili"].clear(); CFG["stili"].update(d.get("st", {})); sync_testo()

def sync_testo():                                     # il motore legge i testi una volta sola: li rimetto in A.TITLE
    t = CFG["testo"]; A.TITLE = (t.get("nome", ""), t.get("sottotitolo", ""), t.get("data", ""))

def keep(it): return {k: it[k] for k in ("a", "zo", "ts", "stile") if it.get(k) is not None}

def mkfree(it, x, y, w, h):
    """cornice libera (foto) o blocco di testo libero (stessa posizione in frazioni della pagina)"""
    x, y, w, h = round(x, 4), round(y, 4), round(w, 4), round(h, 4)
    if it["k"] == "t":
        return dict(it, fx=x, fy=y, fw=w, fh=h) if it.get("kind") == "txt" else dict(k="t", kind=it["kind"], fx=x, fy=y, fw=w, fh=h, c=it.get("c", 0), r=it.get("r", 0), w=it.get("w", 1), h=it.get("h", 1), **keep(it))
    return dict(k="f", i=it["i"], x=x, y=y, w=w, h=h, bw=it.get("bw", False), z=it.get("z", 1.0), **keep(it))

def _flat(s): return [(side, idx, it) for side, pg in zip("LR", SP[s]) for idx, it in enumerate(pg[1])]

def _draw_order(s):
    """cornici libere dal fondo alla cima, come le disegna il motore"""
    fl = _flat(s); return [fl[L["_o"]][:2] for L in A.layout(spread_tuple(s)) if L.get("libera")]

def _put_px(s, side, idx, x, y, W, H):
    pg = SP[s][0 if side == "L" else 1]; it = pg[1][idx]; (x0, x1), (y0, y1) = A._frame(side, pg[0]); w, h = W / (x1 - x0), H / (y1 - y0)
    fx, fy = (x - x0) / (x1 - x0), (y - y0) / (y1 - y0)
    pg[1][idx] = mkfree(it, min(max(fx, -1.0), 2 - w), min(max(fy, 0.0), 1 - h), w, h)

def _put_obj(s, it, x, y, W, H):
    """come _put_px, ma per l'elemento `it` (oggetto): se dopo lo spostamento il suo centro è nell'altra metà dello spread passa all'altra pagina"""
    old = next(i for i, pg in enumerate(SP[s]) if any(z is it for z in pg[1])); new = 0 if x + W / 2 < A.FOLD else 1
    if new != old: SP[s][old][1][:] = [z for z in SP[s][old][1] if z is not it]; SP[s][new][1].append(it)
    idx = next(i for i, z in enumerate(SP[s][new][1]) if z is it); _put_px(s, "LR"[new], idx, x, y, W, H)

def _rects(s):
    fl = _flat(s); return {fl[L["_o"]][:2]: L for L in A.layout(spread_tuple(s))}

def old_text(it): return it["k"] == "t" and it.get("kind") != "txt"           # i vecchi blocchi titolo/crediti
STILE_K = ("font", "size", "col", "al", "tr")

def fit_it(side, pg, it):                             # il riquadro del testo segue il contenuto in altezza
    (x0, x1), (y0, y1) = A._frame(side, pg[0]); it["fh"] = round(TX.fit_height(it, it["fw"] * (x1 - x0)) / (y1 - y0), 4)

def fit_stile(nm):                                    # applica lo stile a tutti i testi che lo usano
    for sp in SP:
        for i, pg in enumerate(sp):
            for it in pg[1]:
                if it.get("stile") == nm and is_txt(it):
                    it.update(copy.deepcopy(CFG["stili"][nm]))
                    if it.get("auto", True): fit_it("L" if i == 0 else "R", pg, it)

def is_txt(it): return it["k"] == "t" and it.get("kind") == "txt"                # livelli di testo (strumento Testo)

def used_set(): return {it["i"] for sp in SP for pg in sp for it in pg[1] if it["k"] != "t"}
def unused(): u = used_set(); return [A.name(i) for i in range(len(A.M)) if i not in u]
def item(ref):
    s, side, idx = ref; it = SP[s][0 if side == "L" else 1][1][idx]
    if it["k"] == "t": raise ValueError("elemento di testo")
    return it
def find_use(i):
    for s, sp in enumerate(SP):
        for side, pg in zip("LR", sp):
            for idx, it in enumerate(pg[1]):
                if it["k"] != "t" and it["i"] == i: return [s, side, idx]

def cell_of(it):
    """celle (c, r, w, h) occupate da una cornice sulla griglia; None per le cornici libere"""
    if it["k"] == "f" or "fx" in it: return None
    return (0, 0, A.NC, A.NR) if it["k"] == "full" else (it["c"], it["r"], it["w"], it["h"])
def overlap(a, b): return a is not None and b is not None and a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
def biggest_free(pg):
    """rettangolo libero più grande (in celle) della pagina: dove mettere una cornice nuova"""
    busy = [[False] * A.NC for _ in range(A.NR)]
    for it in pg[1]:
        if it["k"] == "f":                        # una cornice libera occupa le celle il cui centro cade dentro
            for y in range(A.NR):
                for x in range(A.NC):
                    if it["x"] <= (x + .5) / A.NC <= it["x"] + it["w"] and it["y"] <= (y + .5) / A.NR <= it["y"] + it["h"]: busy[y][x] = True
            continue
        c, r, w, h = cell_of(it)
        for y in range(r, r + h):
            for x in range(c, c + w): busy[y][x] = True
    best, rect = 0, None
    for r in range(A.NR):
        for c in range(A.NC):
            for h in range(1, A.NR - r + 1):
                for w in range(1, A.NC - c + 1):
                    if any(busy[y][x] for y in range(r, r + h) for x in range(c, c + w)): break
                    if w * h > best: best, rect = w * h, (c, r, w, h)
    return rect

def apply(o):
    t = o["op"]
    if t == "swap":
        a, b = item(o["a"]), item(o["b"])
        for k in ("i", "bw", "z", "a"): a[k], b[k] = b.get(k, 1.0 if k == "z" else 0), a.get(k, 1.0 if k == "z" else 0)
    elif t == "replace":
        a = item(o["at"]); n = A.IDX[o["photo"]] - 1; other = find_use(n)
        if other and other != o["at"]:
            b = item(other); a["i"], b["i"] = b["i"], a["i"]
        else: a["i"] = n
    elif t == "set":
        a = item(o["at"])
        if "bw" in o: a["bw"] = bool(o["bw"])
        if "z" in o: a["z"] = round(float(o["z"]), 2)
        if "a" in o: a["a"] = round(max(-45.0, min(45.0, float(o["a"]))), 1)
    elif t == "blank":
        pos = min(max(int(o.get("pos", len(SP))), 0), len(SP)); SP.insert(pos, [["W", []], ["W", []]]); GD.insert(pos, dict(v=[], h=[]))
    elif t == "evg":
        v = round(float(o["value"]), 2)
        if v: CFG["esposizione"]["globale"] = v
        else: CFG["esposizione"].pop("globale", None)
    elif t == "ev":
        pf = CFG["esposizione"]["per_foto"]; v = round(float(o["value"]), 2)
        if abs(v) < 0.005: pf.pop(o["photo"], None)
        else: pf[o["photo"]] = v
    elif t == "testo":
        for k in ("nome", "sottotitolo", "data"):
            if k in o: CFG["testo"][k] = str(o[k]).strip()
        sync_testo()
    elif t == "addtext":                                  # nuovo livello di testo: rettangolo (frazioni dello spread) trascinato con lo strumento Testo
        s_ = o["s"]; fx0, fy0 = min(max(float(o["fx"]), 0.0), 0.98), min(max(float(o["fy"]), 0.0), 0.98); fw0 = min(max(float(o.get("fw", 0)), 0.0), 1.0 - fx0)
        side = "L" if fx0 + fw0 / 2 < 0.5 else "R"; pg = SP[s_][0 if side == "L" else 1]; (x0, x1), (y0, y1) = A._frame(side, pg[0])
        size = round(A.CH * 0.035); wpx = (fw0 * A.CW) if fw0 > 0.01 else 0.28 * (x1 - x0)
        it = dict(k="t", kind="txt", tx=o.get("tx", "Testo"), fx=0, fy=0, fw=0, fh=0, c=0, r=0, w=1, h=1, font=CFG["testo"].get("font_testo_ps", "AvenirNext-Regular"), size=size,
                  col=list(CFG["testo"].get("colore", [58, 54, 51])), al="left", tr=0, auto=True)
        hpx = max(float(o.get("fh", 0)) * A.CH, TX.fit_height(it, wpx)); hpx = TX.fit_height(it, wpx) if o.get("fh") in (None, 0) else hpx
        pg[1].append(mkfree(it, (fx0 * A.CW - x0) / (x1 - x0), (fy0 * A.CH - y0) / (y1 - y0), wpx / (x1 - x0), hpx / (y1 - y0)))
    elif t == "settext":                                  # modifica contenuto / carattere / corpo / colore / allineamento
        s_, side, idx = o["at"]; pg = SP[s_][0 if side == "L" else 1]; it = pg[1][idx]
        if not is_txt(it): raise ValueError("non è un livello di testo")
        for k in ("tx", "font", "al"):
            if k in o: it[k] = str(o[k])
        if "size" in o: it["size"] = round(min(max(float(o["size"]), 8), 2000), 1)
        if "tr" in o: it["tr"] = round(min(max(float(o["tr"]), -200), 2000), 1)
        if "col" in o: it["col"] = [int(min(max(float(v), 0), 255)) for v in o["col"]][:3]
        if "auto" in o: it["auto"] = bool(o["auto"])
        if it.get("stile") in CFG["stili"] and any(k in o for k in STILE_K):      # il testo ha uno stile: la modifica vale per tutti i testi con quello stile
            CFG["stili"][it["stile"]] = {k: it[k] for k in STILE_K}; fit_stile(it["stile"])
        elif it.get("auto", True): fit_it(side, pg, it)
    elif t == "stile_salva":                              # crea/aggiorna lo stile dal testo scelto e lo collega
        s_, side, idx = o["at"]; it = SP[s_][0 if side == "L" else 1][1][idx]; nm = str(o["nome"]).strip()[:40]
        if not is_txt(it) or not nm: raise ValueError("serve un testo e un nome")
        CFG["stili"][nm] = {k: it[k] for k in STILE_K}; it["stile"] = nm; fit_stile(nm)
    elif t == "stile_applica":
        s_, side, idx = o["at"]; pg = SP[s_][0 if side == "L" else 1]; it = pg[1][idx]; nm = o["nome"]
        if not is_txt(it) or nm not in CFG["stili"]: raise ValueError("stile inesistente")
        it.update(copy.deepcopy(CFG["stili"][nm])); it["stile"] = nm
        if it.get("auto", True): fit_it(side, pg, it)
    elif t == "stile_scollega":
        s_, side, idx = o["at"]; SP[s_][0 if side == "L" else 1][1][idx].pop("stile", None)
    elif t == "stile_elimina":
        nm = o["nome"]; CFG["stili"].pop(nm, None)
        for sp in SP:
            for pg in sp:
                for it in pg[1]:
                    if it.get("stile") == nm: it.pop("stile")
    elif t == "t2x":                                      # trasforma il vecchio blocco titolo/crediti in livelli di testo modificabili (uno per riga)
        s_, side, idx = o["at"]; pg = SP[s_][0 if side == "L" else 1]; it = pg[1][idx]
        if not old_text(it): return
        R = _rects(s_)[(side, idx)]; (x0, x1), (y0, y1) = A._frame(side, pg[0]); T = CFG["testo"]
        serif, sans, col = T.get("font_titolo_ps", "Didot-Italic"), T.get("font_testo_ps", "AvenirNext-Regular"), T.get("colore", [58, 54, 51])
        sc = it.get("ts") or 1.0; title = it.get("kind") == "title"; X, Y, W, H = R["x"], R["y"], R["W"], R["H"]; rows = []
        if title: rows = [(T.get("nome", ""), serif, 380 * sc, 0, "center", Y + H / 2 - 260 * sc), (T.get("sottotitolo", ""), sans, 62 * sc, 355, "center", Y + H / 2 + 260 * sc), (T.get("data", ""), sans, 62 * sc, 355, "center", Y + H / 2 + 370 * sc)]
        else: rows = [(T.get("nome", ""), serif, 170 * sc, 0, "left", Y + H - 400 * sc), (T.get("sottotitolo", ""), sans, 62 * sc, 225, "left", Y + H - 170 * sc), (T.get("data", ""), sans, 62 * sc, 225, "left", Y + H - 80 * sc)]
        pg[1].pop(idx)
        for tx, font, size, tr, al, ytop in rows:
            if not tx: continue
            n_ = dict(k="t", kind="txt", tx=tx, fx=0, fy=0, fw=0, fh=0, c=0, r=0, w=1, h=1, font=font, size=round(size, 1), col=list(col), al=al, tr=tr, auto=True)
            h_ = TX.fit_height(n_, W); pg[1].append(mkfree(n_, (X - x0) / (x1 - x0), (ytop - y0) / (y1 - y0), W / (x1 - x0), h_ / (y1 - y0)))
    elif t == "tscale":
        s_, side, idx = o["at"]; it = SP[s_][0 if side == "L" else 1][1][idx]
        if it["k"] != "t": raise ValueError("non è un testo")
        ts = round(min(max(float(o["ts"]), 0.2), 6.0), 3)
        if abs(ts - 1) < 1e-6: it.pop("ts", None)
        else: it["ts"] = ts
    elif t == "tolta":
        n = o["photo"]
        if o.get("value", True):
            if n not in CFG["tolte"]: CFG["tolte"].append(n)
        elif n in CFG["tolte"]: CFG["tolte"].remove(n)
    elif t == "tono":
        n = o["photo"]; v = o.get("value")
        if not v: CFG["tono"].pop(n, None)
        else:
            c = [[int(min(max(round(float(x)), 1), 254)), int(min(max(round(float(y)), 0), 255))] for x, y in (v.get("c") or [])]
            b = int(min(max(round(float(v.get("b", 0))), 0), 253)); w = int(min(max(round(float(v.get("w", 255))), b + 2), 255)); m = round(min(max(float(v.get("m", 1)), 0.1), 5), 2)
            t_ = {k: x for k, x in (("b", b), ("w", w), ("m", m), ("c", sorted(c))) if (k == "b" and x) or (k == "w" and x < 255) or (k == "m" and x != 1) or (k == "c" and x)}
            if t_: CFG["tono"][n] = t_
            else: CFG["tono"].pop(n, None)
    elif t == "face":
        CFG["centri_volto"][o["photo"]] = [round(float(o["x"]), 3), round(float(o["y"]), 3)]
        A.FACE_FIX[o["photo"]] = (round(float(o["x"]), 3), round(float(o["y"]), 3))
    elif t == "module":
        pg = SP[o["s"]][0 if o["side"] == "L" else 1]
        if any(old_text(it) for it in pg[1]): raise ValueError("la pagina ha un testo: cambia solo le foto")
        need = NPH[o["module"]]; cur = [it["i"] for it in pg[1]]
        pool = [i for i in range(len(A.M)) if i not in used_set() and i not in cur]
        ph = (cur + pool)[:need]
        if len(ph) < need: raise ValueError("non ci sono abbastanza foto libere")
        pg[1] = [dict(x) for x in BUILD[o["module"]]([i + 1 for i in ph], bool(o.get("mirror")))]
    elif t == "pan":                      # sposta l'immagine dentro la cornice: la finestra di ritaglio parte da (l, t) in frazioni della foto
        s_, side, idx = o["at"]; it = item(o["at"]); rc = A.layout(spread_tuple(s_))
        L = next(x for x in rc if x["side"] == side and x["k"] != "t" and x["i"] == it["i"])
        l0, t0, r0, b0 = A.zcrop(L); w, h = r0 - l0, b0 - t0
        l, tt = min(max(float(o["l"]), 0.0), 1 - w), min(max(float(o["t"]), 0.0), 1 - h)
        n = A.name(it["i"]); fc = [round(l + w / 2, 4), round(tt + 0.42 * h, 4)]
        CFG["centri_volto"][n] = fc; A.FACE_FIX[n] = tuple(fc)
    elif t == "newspread":
        used = used_set()
        for side in "LR":
            if any(i in used for i in o[side]["photos"]): raise ValueError("una di queste foto è già in uno spread")
        pos = min(max(int(o.get("pos", len(SP))), 0), len(SP))
        SP.insert(pos, [[o[side]["mode"], [dict(x) for x in BUILD[o[side]["module"]]([i + 1 for i in o[side]["photos"]], bool(o[side].get("mirror")))]] for side in "LR"])
        GD.insert(pos, dict(v=[], h=[]))
    elif t == "guides":
        g = GD[o["s"]]
        g["v"] = sorted({round(float(x)) for x in o["v"]}); g["h"] = sorted({round(float(y)) for y in o["h"]})
    elif t == "template":
        sp = SP[o["s"]]
        for k, side in enumerate("LR"):
            if side not in o: continue                                           # pagina di solo testo: resta com'è
            keep_t = [it for it in sp[k][1] if is_txt(it)]                       # i livelli di testo restano
            d = o[side]; sp[k] = [d["mode"], [dict(x) for x in BUILD[d["module"]]([i + 1 for i in d["photos"]], bool(d.get("mirror")))] + keep_t]
    elif t == "frame":
        s, side, idx = o["at"]; pg = SP[s][0 if side == "L" else 1]; it = pg[1][idx]
        if it["k"] == "t": raise ValueError("il testo non si ridimensiona")
        c, r, w, h = (int(o[k]) for k in ("c", "r", "w", "h"))
        if w < 1 or h < 1 or c < 0 or r < 0 or c + w > A.NC or r + h > A.NR: raise ValueError("la cornice esce dalla pagina")
        for j, other in enumerate(pg[1]):
            if j != idx and overlap((c, r, w, h), cell_of(other)): raise ValueError("si sovrappone a un'altra cornice")
        pg[1][idx] = dict(k="p", i=it["i"], c=c, r=r, w=w, h=h, bw=it.get("bw", False), z=it.get("z", 1.0))
    elif t == "free":
        s, side, idx = o["at"]; pg = SP[s][0 if side == "L" else 1]; it = pg[1][idx]
        x, y, w, h = (float(o[k]) for k in ("x", "y", "w", "h"))
        w, h = max(w, 0.03), max(h, 0.03); x, y = min(max(x, -1.0), 2 - w), min(max(y, 0.0), 1 - h)     # x oltre 0..1: la cornice passa sull'altra pagina
        old = it
        if it["k"] == "t" and o.get("ts") is not None: it = dict(it, ts=round(min(max(float(o["ts"]), 0.2), 6.0), 3))
        pg[1][idx] = mkfree(it, x, y, w, h)
        if is_txt(it):
            if o.get("autoh") is False: pg[1][idx]["auto"] = False
            if pg[1][idx].get("auto", True): (x0, x1), (y0, y1) = A._frame(side, pg[0]); pg[1][idx]["fh"] = round(TX.fit_height(pg[1][idx], w * (x1 - x0)) / (y1 - y0), 4)
    elif t == "crosspage":
        s, side, idx = o["at"]; src = SP[s][0 if side == "L" else 1]; it = src[1][idx]; to = o["to"]
        if to == side: raise ValueError("stessa pagina")
        if it["k"] == "t" and o.get("ts") is not None: it = dict(it, ts=round(min(max(float(o["ts"]), 0.2), 6.0), 3))
        dst = SP[s][0 if to == "L" else 1]
        x, y, w, h = (float(o[k]) for k in ("x", "y", "w", "h"))
        w, h = max(w, 0.03), max(h, 0.03); x, y = min(max(x, -1.0), 2 - w), min(max(y, 0.0), 1 - h)
        src[1].pop(idx)
        dst[1].append(mkfree(it, x, y, w, h))
    elif t == "snap":
        s, side, idx = o["at"]; pg = SP[s][0 if side == "L" else 1]; it = pg[1][idx]
        if it["k"] != "f": return
        gr = page_grid(side, pg[0]); rc = A.layout(spread_tuple(s))
        L = next(x for x in rc if x["side"] == side and x.get("libera") and x["i"] == it["i"])
        n = lambda arr, v: min(range(len(arr)), key=lambda j: abs(arr[j] - v))
        c, r = n(gr["xs"], L["x"] - BL), n(gr["ys"], L["y"] - BL)
        w = max(n(gr["xe"], L["x"] - BL + L["W"]), c) - c + 1; h = max(n(gr["ye"], L["y"] - BL + L["H"]), r) - r + 1
        for j, other in enumerate(pg[1]):
            if j != idx and overlap((c, r, w, h), cell_of(other)): raise ValueError("agganciata alla griglia si sovrapporrebbe a un'altra cornice")
        pg[1][idx] = dict(k="p", i=it["i"], c=c, r=r, w=w, h=h, bw=it.get("bw", False), z=it.get("z", 1.0))
    elif t == "addframe":
        s, side = o["s"], o["side"]; pg = SP[s][0 if side == "L" else 1]; rect = biggest_free(pg)
        if not rect: raise ValueError("la pagina è piena: riduci una cornice prima")
        free = [i for i in range(len(A.M)) if i not in used_set()]
        if o.get("photo"): n = A.IDX[o["photo"]] - 1; free = [n] if n not in used_set() else []
        if not free: raise ValueError("non ci sono foto libere")
        pg[1].append(A.P(free[0] + 1, *rect))
    elif t == "putfree":                                  # foto trascinata su un punto vuoto dello spread: cornice libera centrata lì
        s_, n = o["s"], A.IDX[o["photo"]] - 1
        if n in used_set(): raise ValueError("la foto è già in uno spread")
        side = "L" if float(o["fx"]) < 0.5 else "R"; pg = SP[s_][0 if side == "L" else 1]
        (x0, x1), (y0, y1) = A._frame(side, pg[0]); ar = A.M[n]["ar"]
        wpx = 0.55 * (x1 - x0); hpx = wpx / ar
        if hpx > 0.85 * (y1 - y0): hpx = 0.85 * (y1 - y0); wpx = hpx * ar
        w, h = wpx / (x1 - x0), hpx / (y1 - y0)
        cx = (float(o["fx"]) * A.CW - x0) / (x1 - x0); cy = (float(o["fy"]) * A.CH - y0) / (y1 - y0)
        pg[1].append(FL.FREE(o["photo"], round(min(max(cx - w / 2, 0), 1 - w), 4), round(min(max(cy - h / 2, 0), 1 - h), 4), round(w, 4), round(h, 4)))
    elif t == "zorder":                                   # livelli come in Photoshop: davanti / dietro
        s_ = o["s"]; sel = {(a[0], int(a[1])) for a in o["ats"]}; order = _draw_order(s_)
        if o["dir"] == "front": order = [x for x in order if x not in sel] + [x for x in order if x in sel]
        elif o["dir"] == "back": order = [x for x in order if x in sel] + [x for x in order if x not in sel]
        elif o["dir"] == "forward":
            for i in range(len(order) - 2, -1, -1):
                if order[i] in sel and order[i + 1] not in sel: order[i], order[i + 1] = order[i + 1], order[i]
        else:
            for i in range(1, len(order)):
                if order[i] in sel and order[i - 1] not in sel: order[i], order[i - 1] = order[i - 1], order[i]
        for z_, (side, idx) in enumerate(order): SP[s_][0 if side == "L" else 1][1][idx]["zo"] = z_
    elif t == "equalize":                                 # tutte le foto scelte con la stessa larghezza e altezza di quella di riferimento (il centro resta dov'è)
        s_ = o["s"]; R = _rects(s_); ref = R[(o["ref"][0], int(o["ref"][1]))]; rw, rh = ref["W"], ref["H"]
        for a in o["ats"]:
            key = (a[0], int(a[1])); L = R.get(key)
            if L is None or SP[s_][0 if key[0] == "L" else 1][1][key[1]]["k"] == "t": continue
            _put_px(s_, key[0], key[1], L["x"] + L["W"] / 2 - rw / 2, L["y"] + L["H"] / 2 - rh / 2, rw, rh)
    elif t == "origar":                                   # proporzioni originali della foto: stessa larghezza, altezza giusta, centro fermo
        s_ = o["s"]; R = _rects(s_)
        for a in o["ats"]:
            key = (a[0], int(a[1])); L = R.get(key); it = SP[s_][0 if key[0] == "L" else 1][1][key[1]]
            if L is None or it["k"] == "t": continue
            ar = A.M[it["i"]]["ar"]; W, H = L["W"], L["W"] / ar; (y0, y1) = A._frame(key[0], SP[s_][0 if key[0] == "L" else 1][0])[1]
            if H > y1 - y0: H = y1 - y0; W = H * ar
            _put_px(s_, key[0], key[1], L["x"] + L["W"] / 2 - W / 2, L["y"] + L["H"] / 2 - H / 2, W, H)
            SP[s_][0 if key[0] == "L" else 1][1][key[1]].pop("z", None); SP[s_][0 if key[0] == "L" else 1][1][key[1]]["z"] = 1.0
    elif t == "fullpage":                                 # la foto occupa tutta la propria pagina
        s_ = o["s"]
        for a in o["ats"]:
            side, idx = a[0], int(a[1]); pg = SP[s_][0 if side == "L" else 1]
            if pg[1][idx]["k"] == "t": continue
            (x0, x1), (y0, y1) = A._frame(side, pg[0]); _put_px(s_, side, idx, x0, y0, x1 - x0, y1 - y0)
    elif t == "orient":                                   # cornici tutte verticali o tutte orizzontali: scambia larghezza e altezza se serve (centro fermo)
        s_ = o["s"]; R = _rects(s_)
        for a in o["ats"]:
            side, idx = a[0], int(a[1]); pg = SP[s_][0 if side == "L" else 1]; L = R.get((side, idx))
            if L is None or pg[1][idx]["k"] == "t": continue
            W, H = L["W"], L["H"]
            if (o["dir"] == "v" and W > H) or (o["dir"] == "h" and H > W): W, H = H, W
            else: continue
            (x0, x1), (y0, y1) = A._frame(side, pg[0]); f = min(1.0, (y1 - y0) / H, (x1 - x0) / W); W, H = W * f, H * f
            _put_px(s_, side, idx, L["x"] + L["W"] / 2 - W / 2, L["y"] + L["H"] / 2 - H / 2, W, H)
    elif t == "nudge":                                    # spostamento di gruppo (in pixel della pagina)
        s_ = o["s"]; R = _rects(s_)
        for a in o["ats"]:
            key = (a[0], int(a[1])); L = R.get(key)
            if L is None or SP[s_][0 if key[0] == "L" else 1][1][key[1]]["k"] == "t": continue
            _put_px(s_, key[0], key[1], L["x"] + float(o["dx"]), L["y"] + float(o["dy"]), L["W"], L["H"])
    elif t == "dup":                                      # spread identico subito dopo (le foto compaiono due volte: si usa per fare varianti)
        s_ = o["s"]
        if not 0 <= s_ < len(SP): raise ValueError("spread inesistente")
        SP.insert(s_ + 1, copy.deepcopy(SP[s_])); GD.insert(s_ + 1, copy.deepcopy(GD[s_]))
    elif t == "copia":                                    # appunti dell'editor (non cambiano il progetto): elementi scelti con la loro posizione
        R = _rects(o["s"]); CLIP.clear()
        for a in o["ats"]:
            key = (a[0], int(a[1])); L = R.get(key); it = SP[o["s"]][0 if key[0] == "L" else 1][1][key[1]]
            if L is None or (it["k"] == "t" and not is_txt(it)): continue
            CLIP.append(dict(item=copy.deepcopy(it), x=L["x"], y=L["y"], W=L["W"], H=L["H"]))
        if not CLIP: raise ValueError("niente da copiare: scegli foto o testi")
    elif t == "incolla":                                  # nello stesso spread con un piccolo scarto, in un altro spread nella stessa posizione
        s_ = o["s"]
        if not CLIP: raise ValueError("gli appunti sono vuoti: copia prima qualcosa")
        dx = dy = (A.CW * 0.02) if o.get("scarto") else 0.0; here = {x["i"] for pg in SP[s_] for x in pg[1] if x["k"] != "t"}; new = []; skipped = 0
        for c in CLIP:
            it = copy.deepcopy(c["item"]); it.pop("zo", None)
            if it["k"] != "t" and it["i"] in here: skipped += 1; continue
            cx = c["x"] + dx + c["W"] / 2; side = "L" if cx < A.FOLD else "R"; pg = SP[s_][0 if side == "L" else 1]
            pg[1].append(it); idx = len(pg[1]) - 1; _put_px(s_, side, idx, c["x"] + dx, c["y"] + dy, c["W"], c["H"]); new.append([side, idx])
            if it["k"] != "t": here.add(it["i"])
        if not new: raise ValueError("queste foto sono già in questo spread")
        apply(dict(op="zorder", s=s_, ats=new, dir="front"))
    elif t == "align":                                    # allinea (a sinistra/centro/destra, in alto/in mezzo/in basso) o distribuisci con spazi uguali (dh/dv)
        s_ = o["s"]; R = _rects(s_); items = []
        for a in o["ats"]:
            key = (a[0], int(a[1])); L = R.get(key); it = SP[s_][0 if key[0] == "L" else 1][1][key[1]]
            if L is None or (it["k"] == "t" and not is_txt(it)): continue
            items.append((key, L, it))
        m = o["mode"]
        if not items: return
        if m in ("dh", "dv"):
            if len(items) < 3: raise ValueError("per distribuire servono almeno 3 elementi")
            p, d_ = ("x", "W") if m == "dh" else ("y", "H"); items.sort(key=lambda kv: kv[1][p])
            first, last = items[0][1], items[-1][1]; gap = ((last[p] + last[d_]) - first[p] - sum(L[d_] for _, L, _ in items)) / (len(items) - 1); pos = first[p]
            for key, L, it in items:
                _put_obj(s_, it, pos if m == "dh" else L["x"], pos if m == "dv" else L["y"], L["W"], L["H"]); pos += L[d_] + gap
        else:
            if len(items) >= 2: bx0, bx1 = min(L["x"] for _, L, _ in items), max(L["x"] + L["W"] for _, L, _ in items); by0, by1 = min(L["y"] for _, L, _ in items), max(L["y"] + L["H"] for _, L, _ in items)
            else:                                         # un solo elemento: si allinea alla sua pagina
                side = items[0][0][0]; (bx0, bx1), (by0, by1) = A._frame(side, SP[s_][0 if side == "L" else 1][0])
            for key, L, it in items:
                nx, ny = L["x"], L["y"]
                if m == "l": nx = bx0
                elif m == "ch": nx = (bx0 + bx1) / 2 - L["W"] / 2
                elif m == "r": nx = bx1 - L["W"]
                elif m == "t": ny = by0
                elif m == "cv": ny = (by0 + by1) / 2 - L["H"] / 2
                elif m == "b": ny = by1 - L["H"]
                else: raise ValueError("allineamento sconosciuto")
                _put_obj(s_, it, nx, ny, L["W"], L["H"])
    elif t == "delframe":
        s, side, idx = o["at"]; pg = SP[s][0 if side == "L" else 1]
        if old_text(pg[1][idx]): raise ValueError("questo testo non si rimuove da qui")
        pg[1].pop(idx)
    elif t == "mode": SP[o["s"]][0 if o["side"] == "L" else 1][0] = o["mode"]
    elif t == "move":
        s, to = o["s"], max(0, min(len(SP) - 1, o["to"]))
        if not 0 <= s < len(SP): raise ValueError("spread inesistente")
        SP.insert(to, SP.pop(s)); GD.insert(to, GD.pop(s))
    elif t == "delete":
        if not 0 <= o["s"] < len(SP): raise ValueError("spread inesistente")
        if len(SP) > 1: SP.pop(o["s"]); GD.pop(o["s"])
    elif t == "new":
        u = [i for i in range(len(A.M)) if i not in used_set()]
        if len(u) < 2: raise ValueError("servono almeno 2 foto libere")
        GD.insert(o["s"] + 1, dict(v=[], h=[]))
        SP.insert(o["s"] + 1, [["W", [dict(x) for x in A.CV(u[0] + 1)]], ["I", [A.FULL(u[1] + 1)]]])
    else: raise ValueError("operazione sconosciuta: " + t)

REV, LASTC = 0, None          # contatore delle modifiche e scheda che ha fatto l'ultima: evita che una scheda lavori (o annulli) su uno stato che non ha visto

def do_op(o):
    global REV, LASTC
    with LOCK:
        cid, rev = o.pop("cid", None), o.pop("rev", None)
        if cid and rev is not None and cid != LASTC and rev != REV and LASTC is not None:
            raise ValueError("Questo progetto è stato modificato da un'altra scheda: ho ricaricato lo stato, riprova.")
        before = snap()
        if o["op"] == "undo":
            if UNDO: REDO.append(snap()); restore(UNDO.pop()); REV += 1; LASTC = cid
            return
        if o["op"] == "redo":
            if REDO: UNDO.append(snap()); restore(REDO.pop()); REV += 1; LASTC = cid
            return
        apply(o); LAST["op"] = time.time()
        if snap() != before: UNDO.append(before); REDO.clear(); del UNDO[:-200]; REV += 1; LASTC = cid

# ------------------------------------------------------------------ vista
BL = round(A.B)
VW, VH = A.CW - 2 * BL, A.CH - 2 * BL

def spread_tuple(s): return tuple((pg[0], pg[1]) for pg in SP[s])
def spread_hash(s):
    d = json.dumps([SP[s], CFG["testo"], [CFG["esposizione"]["globale"] if "globale" in CFG["esposizione"] else 0, {A.name(it["i"]): CFG["esposizione"]["per_foto"].get(A.name(it["i"])) for pg in SP[s] for it in pg[1] if it["k"] != "t"},
                    {A.name(it["i"]): CFG["centri_volto"].get(A.name(it["i"])) for pg in SP[s] for it in pg[1] if it["k"] != "t"},
                    {A.name(it["i"]): CFG["tono"].get(A.name(it["i"])) for pg in SP[s] for it in pg[1] if it["k"] != "t"},
                    {A.name(it["i"]): PV.get(A.name(it["i"]), 0) for pg in SP[s] for it in pg[1] if it["k"] != "t"}]], sort_keys=True)
    return hashlib.md5(d.encode()).hexdigest()[:10]

def page_grid(side, mode):
    """linee della griglia di una pagina, in pixel dell'anteprima, identiche a quelle di album._place:
    xs/ys = bordo sinistro/alto di ogni colonna/riga, xe/ye = bordo destro/basso"""
    (x0, x1), (y0, y1) = A._frame(side, mode); G, NC, NR = A.G, A.NC, A.NR
    cw = (x1 - x0 - (NC - 1) * G) / NC; rh = (y1 - y0 - (NR - 1) * G) / NR
    colx = lambda c: round(x0 + c * (cw + G)); rowy = lambda r: round(y0 + r * (rh + G))
    return dict(bx=[x0 - BL, x1 - BL], by=[y0 - BL, y1 - BL], xs=[colx(c) - BL for c in range(NC)], xe=[(round(x1) if c == NC - 1 else colx(c + 1) - G) - BL for c in range(NC)],
                ys=[rowy(r) - BL for r in range(NR)], ye=[(round(y1) if r == NR - 1 else rowy(r + 1) - G) - BL for r in range(NR)])

def spread_view(s):
    lay = sorted(A.layout(spread_tuple(s)), key=lambda L: L.get("_o", 0)); out = []; k = 0
    zr = {key: r for r, key in enumerate(_draw_order(s))}
    for side, pg in zip("LR", SP[s]):
        for idx, it in enumerate(pg[1]):
            L = lay[k]; k += 1
            e = dict(side=side, idx=idx, k=it["k"], x=L["x"] - BL, y=L["y"] - BL, w=L["W"], h=L["H"], cell=list(cell_of(it)) if cell_of(it) else None, free=it["k"] == "f" or (it["k"] == "t" and "fx" in it), ts=it.get("ts", 1.0))
            e["zr"] = zr.get((side, idx), 0)
            if it["k"] == "t":
                e["kind"] = it.get("kind")
                if is_txt(it): e.update(tx=it["tx"], font=it["font"], size=it["size"], col=it["col"], al=it["al"], tr=it["tr"], auto=bool(it.get("auto", True)), stile=it.get("stile"))
            else:
                n = A.name(it["i"]); ar = A.M[it["i"]]["ar"]; fa = L["W"] / L["H"]
                e.update(crop=round(max(fa / ar, ar / fa) * it.get("z", 1.0), 2))
                l_, t_, r_, b_ = A.zcrop(L); m_ = A.M[it["i"]]
                e.update(box=[round(l_, 4), round(t_, 4), round(r_, 4), round(b_, 4)], cm=[round(L["W"] / A.PPI * 2.54, 2), round(L["H"] / A.PPI * 2.54, 2)],
                         ppi=round(m_["w"] * (r_ - l_) / (L["W"] / A.PPI)), dim=[m_["w"], m_["h"]], uses=sum(1 for x in SP for pg_ in x for y in pg_[1] if y["k"] != "t" and y["i"] == it["i"]))
                n = A.name(it["i"]); e.update(name=n, bw=bool(it.get("bw")), z=it.get("z", 1.0), a=it.get("a") or 0, ar=A.M[it["i"]]["ar"],
                                              ev=A.ev_for(it["i"]), evp=CFG["esposizione"]["per_foto"].get(n, 0.0), tono=CFG["tono"].get(n), face=list(A._faces_center(it["i"]) or []))
            out.append(e)
    return dict(h=spread_hash(s), guides=GD[s], L=SP[s][0][0], R=SP[s][1][0], items=out, grid=dict(L=page_grid("L", SP[s][0][0]), R=page_grid("R", SP[s][1][0])))

def locked_sides(s):
    """pagine che non si toccano con i modelli: quelle con un vecchio blocco titolo/crediti o con solo testo (senza foto)"""
    out = []
    for side, pg in zip("LR", SP[s]):
        if any(old_text(it) for it in pg[1]) or (any(it["k"] == "t" for it in pg[1]) and not any(it["k"] != "t" for it in pg[1])): out.append(side)
    return out

def tpl_options(photos, cur=None, side=None, s=None):
    """modelli di spread per queste foto, con le foto già assegnate alle cornici (come «Rearrange» di Smart Albums); in più i modelli salvati dall'utente con lo stesso numero di foto.
    side = "L"/"R": l'altra pagina è di testo e resta com'è (s = lo spread): si cambia solo questa"""
    import math
    N = len(photos); sides = "LR" if side is None else side

    def NPH_(mod):
        if mod in NPH: return NPH[mod]
        t = next(t for t in ut_load() if t["id"] == mod.split(":")[1]); return len(t["pages"][0 if mod.endswith(":L") else 1]["items"])

    def build(a, b=None):
        if side is None: tup = tuple((m, BUILD[mod](list(range(1, NPH_(mod) + 1)), mir)) for (mod, m, mir) in (a, b))
        else:
            mod, m, mir = a; new = (m, BUILD[mod](list(range(1, NPH_(mod) + 1)), mir)); fixed = SP[s][1 if side == "L" else 0]
            tup = (new, (fixed[0], fixed[1])) if side == "L" else ((fixed[0], fixed[1]), new)
        lay = sorted((L for L in A.layout(tup) if L["k"] != "t" and L["side"] in sides), key=lambda L: L.get("_o", 0))
        fr = [dict(x=L["x"] - BL, y=L["y"] - BL, w=L["W"], h=L["H"]) for L in lay]
        left = list(range(N)); asg = [None] * N; cost = 0.0
        for j in sorted(range(N), key=lambda j: -fr[j]["w"] * fr[j]["h"]):
            far = fr[j]["w"] / fr[j]["h"]
            c, p = min(((abs(math.log(far / A.M[photos[q]]["ar"])) + 0.02 * abs(q - j), q) for q in left))
            asg[j] = p; left.remove(p); cost += c
        for j, f in enumerate(fr): f["n"] = A.name(photos[asg[j]])
        okc = cur is not None and sorted((round(f["x"]), round(f["y"]), f["w"], f["h"]) for f in fr) == cur
        if side is not None: return dict(cost=round(cost, 3), frames=fr, cur=okc, **{side: dict(mode=a[1], module=a[0], mirror=a[2], photos=[photos[q] for q in asg])})
        na = NPH_(a[0])
        return dict(cost=round(cost, 3), frames=fr, cur=okc, L=dict(mode=a[1], module=a[0], mirror=a[2], photos=[photos[q] for q in asg[:na]]),
                    R=dict(mode=b[1], module=b[0], mirror=b[2], photos=[photos[q] for q in asg[na:]]))

    out = []
    if side is None:
        for a in LAYS:
            for b in LAYS:
                if NPH[a[0]] + NPH[b[0]] != N or (a[0] == "BLANK" and b[0] == "BLANK"): continue
                out.append(build(a, b))
    else:
        for a in LAYS:
            if N and NPH[a[0]] == N and a[0] != "BLANK": out.append(build(a))
    out.sort(key=lambda t: (not t["cur"], t["cost"]))
    ut = []
    for t in ut_load():
        if t["n"] != N or t.get("lato") != side: continue
        try:
            if side is None: d = build(("U:%s:L" % t["id"], t["pages"][0]["mode"], False), ("U:%s:R" % t["id"], t["pages"][1]["mode"], False))
            else: d = build(("U:%s:%s" % (t["id"], side), t["pages"][0 if side == "L" else 1]["mode"], False))
            d.update(id=t["id"], nome=t["nome"]); ut.append(d)
        except Exception as ex: LOG.append(f"modello «{t.get('nome')}» non applicabile: {ex}")
    return dict(items=out[:60], n=N, tot=len(out), utente=ut, lato=side)

def tpl_from_spread(s):
    """(pagine, n, lato): se una pagina è di solo testo si salva solo l'altra (lato = quella), altrimenti tutto lo spread (lato = None)"""
    lk = locked_sides(s)
    if len(lk) == 2: raise ValueError("le due pagine sono di solo testo: non c'è nessun layout di foto da salvare")
    lato = None if not lk else next(x for x in "LR" if x not in lk)
    pages = [dict(mode=pg[0], items=[{k: v for k, v in it.items() if k in UT_KEEP} for it in pg[1] if it["k"] != "t"] if lato in (None, side) else [])
             for side, pg in zip("LR", SP[s])]
    n = sum(len(p["items"]) for p in pages)
    if not n: raise ValueError("lo spread non ha foto: non c'è nessun layout da salvare")
    return pages, n, lato

def modelli(o):
    """salva / aggiorna / rinomina / elimina un modello dell'utente (non fa parte di annulla/ripeti)"""
    with LOCK:
        lst = ut_load(); a = o["azione"]; nome = str(o.get("nome", "")).strip()[:60]
        if a == "salva":
            if not nome: raise ValueError("scrivi un nome per il modello")
            if any(t["nome"].lower() == nome.lower() for t in lst): raise ValueError("esiste già un modello con questo nome: usa «Aggiorna» su quello")
            pages, n, lato = tpl_from_spread(o["s"]); lst.append(dict(id=os.urandom(4).hex(), nome=nome, n=n, lato=lato, pages=pages))
        else:
            t = next((x for x in lst if x["id"] == o["id"]), None)
            if not t: raise ValueError("modello non trovato")
            if a == "aggiorna": t["pages"], t["n"], t["lato"] = tpl_from_spread(o["s"])
            elif a == "rinomina":
                if not nome: raise ValueError("scrivi un nome")
                if any(x is not t and x["nome"].lower() == nome.lower() for x in lst): raise ValueError("esiste già un modello con questo nome")
                t["nome"] = nome
            elif a == "elimina": lst.remove(t)
            else: raise ValueError("azione sconosciuta")
        ut_save(lst)

def templates(s):
    with LOCK:
        lk = locked_sides(s)
        if len(lk) == 2: return dict(items=[], utente=[], nota="Le due pagine sono di solo testo: non ci sono foto da impaginare.")
        side = None if not lk else next(x for x in "LR" if x not in lk); sides = "LR" if side is None else side
        photos = [it["i"] for k, x in enumerate("LR") if x in sides for it in SP[s][k][1] if it["k"] != "t"]
        cur = sorted((round(e["x"]), round(e["y"]), e["w"], e["h"]) for e in spread_view(s)["items"] if e["k"] != "t" and e["side"] in sides)
        d = tpl_options(photos, cur, side, s)
        if side and not photos: d["nota"] = "La pagina senza testo non ha foto: aggiungine una per vedere i modelli."
        return d

def templates_for(names):
    with LOCK:
        used = used_set(); ph = []
        for n in names:
            i = A.IDX[n] - 1
            if i in used: raise ValueError(f"{n} è già in uno spread")
            ph.append(i)
        return tpl_options(ph) if ph else dict(items=[], n=0, tot=0)

BOOT = str(time.time())
def photo_list():
    where = {}
    for k, sp in enumerate(SP):
        for pg in sp:
            for it in pg[1]:
                if it["k"] != "t": where.setdefault(it["i"], k)
    tolte = set(CFG.get("tolte", []))
    return [dict(n=A.name(i), ar=A.M[i]["ar"], dt=A.M[i]["dt"][:19], sp=where.get(i), tolta=A.name(i) in tolte) for i in range(len(A.M))]

def foto_mancanti(): return [m["n"] for m in A.M if not os.path.exists(m.get("src", ""))]

def state():
    with LOCK:
        return dict(nome=CFG.get("nome", os.path.basename(PROJ)), W=VW, H=VH, testo=CFG['testo'], stili=CFG['stili'], fold=A.FOLD - BL, dirty=snap() != SAVED, rev=REV, canundo=bool(UNDO), canredo=bool(REDO),
                    globale=CFG["esposizione"].get("globale", 0.0), spreads=[spread_view(s) for s in range(len(SP))],
                    photos=photo_list(), home=ARGS.home, boot=BOOT, unused=unused(), tolte=CFG.get("tolte", []),
                    modules={k: v for k, v in NPH.items()}, gap=A.G, ppi=A.PPI, mancanti=foto_mancanti(), agg=dict(AGG))

CACHE = {}
PV = {}                                              # versione di ogni foto: sale quando l'originale cambia (es. riesportata da Lightroom), così anteprime e cache si rifanno
AGG = dict(n=0, t=0, nomi=[], ar=[])               # ultimo aggiornamento automatico delle foto modificate
def spread_jpg(s, K):
    with LOCK:
        key = (spread_hash(s), K)
        if key in CACHE: return CACHE[key]
        im = A.render(spread_tuple(s), K, True)
        b = round(A.B * K)
        if b: im = im.crop((b, b, im.width - b, im.height - b))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=86); CACHE[key] = buf.getvalue()
        if len(CACHE) > 400: CACHE.pop(next(iter(CACHE)))
        return CACHE[key]

def _mt(p):
    try: return os.stat(p).st_mtime
    except OSError: return None

def foto_cambiate():
    """indici delle foto il cui originale è più recente della miniatura nella cache (modificato dopo: Lightroom, Photoshop…)"""
    out = []
    for i, m in enumerate(A.M):
        s, t = _mt(m.get("src", "")), _mt(os.path.join(A.THUMBS, m["n"]))
        if s is not None and t is not None and s > t + 1: out.append(i)
    return out

def aggiorna_foto(idx):
    """rifà miniatura, misure e volti delle foto indicate; le correzioni fatte a mano (esposizione, Tono, zoom, centro volto) restano. Ritorna ([nomi aggiornati], [nomi con proporzioni cambiate], [non riuscite])"""
    ok, ars, ko = [], [], []
    with LOCK:
        for i in idx:
            m = A.M[i]
            try:
                im = Image.open(m["src"]); im.load(); im.close()                      # file completo (Lightroom può essere ancora a scrivere)
                new = A._meta_one(m["src"]); old_ar = m.get("ar", new["ar"])
                m.update(dt=new["dt"], w=new["w"], h=new["h"], ar=new["ar"])
                tp = os.path.join(A.THUMBS, m["n"])
                if os.path.exists(tp): os.remove(tp)
                A._build_thumbs([m])
                try: A.F.update(A._build_faces([m])); json.dump(A.F, open(os.path.join(A.CACHE, "faces.json"), "w"))
                except Exception as ex: LOG.append(f"volti di {m['n']} non rifatti: {ex}")
                n = A.name(i); PV[n] = PV.get(n, 0) + 1; INFO.pop(n, None)
                for k in [k for k in TH if k[0] == n]: TH.pop(k)
                ok.append(m["n"])
                if abs(new["ar"] - old_ar) > 0.003: ars.append(m["n"])
            except Exception as ex: ko.append(m["n"]); LOG.append(f"{m['n']}: non aggiornata ({ex})")
        if ok:
            json.dump(A.M, open(os.path.join(A.CACHE, "meta.json"), "w")); CACHE.clear()
            AGG.update(n=AGG["n"] + 1, t=time.time(), nomi=ok, ar=ars)
    return ok, ars, ko

def foto_watch_loop():
    """ogni pochi secondi guarda se qualche originale è cambiato (anche ad editor aperto); aspetta che il file sia fermo da un paio di cicli, poi aggiorna da solo"""
    seen = {}
    while True:
        time.sleep(4)
        try:
            cand = {i: (_mt(A.M[i]["src"]), os.path.getsize(A.M[i]["src"])) for i in foto_cambiate()}
            pronte = [i for i, v in cand.items() if seen.get(i) == v and time.time() - v[0] > 2]; seen = cand
            if pronte: aggiorna_foto(pronte)
        except Exception as ex: LOG.append(f"controllo foto modificate: {ex}")

TH = {}
def thumb_jpg(n, w):
    key = (n, w)
    if key not in TH:
        im = Image.open(os.path.join(A.THUMBS, n + ".jpg") if os.path.exists(os.path.join(A.THUMBS, n + ".jpg")) else os.path.join(A.THUMBS, A.M[A.IDX[n] - 1]["n"]))
        im = im.convert("RGB"); im.thumbnail((w, w)); buf = io.BytesIO(); im.save(buf, "JPEG", quality=82); TH[key] = buf.getvalue()
    return TH[key]

INFO = {}
def photo_info(n):
    if n in INFO: return INFO[n]
    m = A.M[A.IDX[n] - 1]; d = dict(dim=[m["w"], m["h"]])
    try:
        im = Image.open(m["src"]); ex = im.getexif(); sub = ex.get_ifd(0x8769)
        icc = im.info.get("icc_profile")
        if icc:
            from PIL import ImageCms
            d["profilo"] = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip()
        sh, ap = sub.get(33434), sub.get(33437)
        if sh: d["tempo"] = f"1/{round(1 / float(sh))}" if float(sh) < 1 else f"{float(sh):g} s"
        if ap: d["diaframma"] = f"f/{float(ap):g}"
        if sub.get(34855): d["iso"] = sub.get(34855) if not isinstance(sub.get(34855), tuple) else sub.get(34855)[0]
        if sub.get(37386): d["focale"] = f"{float(sub.get(37386)):g} mm"
        dt = sub.get(36867) or ex.get(306)
        if dt: d["data"] = str(dt)
    except Exception as e: d["errore"] = str(e)
    INFO[n] = d; return d

# ------------------------------------------------------------------ salvataggio
def fmt(it):
    x = fmt0(it)
    return f'ROT({x}, {it["a"]})' if it["k"] != "t" and it.get("a") else x
def fmt0(it):
    if is_txt(it):
        return ("TEXT(%r, %s, %s, %s, %s, font=%r, size=%s, col=%r, al=%r, tr=%s, auto=%s" % (it["tx"], it["fx"], it["fy"], it["fw"], it["fh"], it["font"], it["size"], tuple(it["col"]), it["al"], it["tr"], bool(it.get("auto", True)))) + (f', zo={it["zo"]}' if it.get("zo") is not None else "") + (f', stile={it["stile"]!r}' if it.get("stile") else "") + ")"
    if it["k"] == "t":
        if "fx" in it: return f'TXTF({it["kind"]!r}, {it["fx"]}, {it["fy"]}, {it["fw"]}, {it["fh"]}, ts={it.get("ts", 1.0)}' + (f', zo={it["zo"]}' if it.get("zo") is not None else "") + ")"
        return f'TXT({it["kind"]!r}, {it["c"]}, {it["r"]}, {it["w"]}, {it["h"]})'
    n = A.name(it["i"]); ex = (", bw=True" if it.get("bw") else "") + (f', z={it["z"]}' if it.get("z", 1.0) != 1.0 else "") + (f', zo={it["zo"]}' if it["k"] == "f" and it.get("zo") is not None else "")
    if it["k"] == "full": return f"FULL({n!r}{ex})"
    if it["k"] == "f": return f'FREE({n!r}, {it["x"]}, {it["y"]}, {it["w"]}, {it["h"]}{ex})'
    return f'P({n!r}, {it["c"]}, {it["r"]}, {it["w"]}, {it["h"]}{ex})'

LAST = dict(op=0.0, backup=0.0)
def save(backup=True):
    global SAVED
    with LOCK:
        ts = time.strftime("%Y%m%d-%H%M%S"); bk = os.path.join(PROJ, "_backup_editor"); os.makedirs(bk, exist_ok=True)
        if backup:
            LAST["backup"] = time.time()
            for f in ("spec.py", "progetto.json"):
                p = os.path.join(PROJ, f)
                if os.path.exists(p): shutil.copy2(p, os.path.join(bk, f"{ts}_{f}"))
        has_free = any(it["k"] == "f" or it.get("a") or "fx" in it for sp in SP for pg in sp for it in pg[1])
        if has_free: shutil.copy2(os.path.join(HERE, "album_libere.py"), os.path.join(PROJ, "album_libere.py")); shutil.copy2(os.path.join(HERE, "testo.py"), os.path.join(PROJ, "testo.py"))
        lines = [f'"""{CFG.get("nome", "Album")}: {len(SP)} spread. Salvato dall\'editor il {time.strftime("%d/%m/%Y %H:%M")}."""', "from album import *"]
        if has_free: lines.append("from album_libere import *     # cornici libere FREE(...) e angoli ROT(...): serve questo file, sta nella cartella del progetto")
        lines += ["", "SPREADS = ["]
        for k, sp in enumerate(SP, 1):
            pages = [f'{pg[0]}(' + ", ".join(fmt(it) for it in pg[1]) + ")" for pg in sp]
            lines.append(f"    # {k}\n    ({pages[0]},\n     {pages[1]}),")
        lines.append("]")
        open(os.path.join(PROJ, "spec.py"), "w").write("\n".join(lines) + "\n")
        out = {k: v for k, v in json.load(open(os.path.join(PROJ, "progetto.json"))).items()}
        out["esposizione"] = CFG["esposizione"]; out["centri_volto"] = CFG["centri_volto"]; out["tono"] = CFG["tono"]; out["tolte"] = CFG["tolte"]; out["testo"] = CFG["testo"]; out["stili"] = CFG["stili"]; out["foto_extra"] = CFG.get("foto_extra", [])
        if CFG.get("uscita_psd"): out["uscita_psd"] = CFG["uscita_psd"]
        if any(g["v"] or g["h"] for g in GD): out["guide"] = GD
        else: out.pop("guide", None)
        json.dump(out, open(os.path.join(PROJ, "progetto.json"), "w"), indent=2, ensure_ascii=False)
        SAVED = snap()
        return ts

def parse_range(txt, n):
    if not txt.strip(): return list(range(1, n + 1))
    out = []
    for part in txt.replace(";", ",").split(","):
        part = part.strip()
        if not part: continue
        if "-" in part:
            a_, b_ = (int(x) for x in part.split("-", 1)); out += list(range(min(a_, b_), max(a_, b_) + 1))
        else: out.append(int(part))
    bad = [x for x in out if not 1 <= x <= n]
    if bad: raise ValueError(f"spread inesistenti: {bad} (l'album ne ha {n})")
    return list(dict.fromkeys(out))

_ICC = None
def srgb_icc():
    """profilo sRGB IEC61966-2.1 vero (quello di sistema, lo stesso delle foto); se manca, quello interno di Pillow"""
    global _ICC
    if _ICC is None:
        p = "/System/Library/ColorSync/Profiles/sRGB Profile.icc"
        if os.path.exists(p): _ICC = open(p, "rb").read()
        else:
            from PIL import ImageCms
            _ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    return _ICC

def write_pdf(path, jpegs, dpi=150):
    """PDF con un'immagine JPEG per pagina e il profilo sRGB incorporato (ICCBased): senza, i lettori usano il profilo del monitor e i colori cambiano.
    jpegs = [(dati jpeg, larghezza px, altezza px)]"""
    icc = srgb_icc(); objs = []
    def add(b): objs.append(b); return len(objs)
    cat = add(b""); pages_id = add(b""); icc_id = add(b"<< /N 3 /Alternate /DeviceRGB /Length %d >>\nstream\n" % len(icc) + icc + b"\nendstream")
    kids = []
    for data, w, h in jpegs:
        im = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace [/ICCBased %d 0 R] /BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n" % (w, h, icc_id, len(data)) + data + b"\nendstream")
        pw, ph = w * 72 / dpi, h * 72 / dpi; cs = ("q %.3f 0 0 %.3f 0 0 cm /Im0 Do Q" % (pw, ph)).encode()
        ct = add(b"<< /Length %d >>\nstream\n" % len(cs) + cs + b"\nendstream")
        kids.append(add(("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.3f %.3f] /Resources << /XObject << /Im0 %d 0 R >> >> /Contents %d 0 R >>" % (pages_id, pw, ph, im, ct)).encode()))
    objs[cat - 1] = ("<< /Type /Catalog /Pages %d 0 R >>" % pages_id).encode()
    objs[pages_id - 1] = ("<< /Type /Pages /Count %d /Kids [%s] >>" % (len(kids), " ".join("%d 0 R" % k for k in kids))).encode()
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"); offs = []
    for i, b in enumerate(objs, 1): offs.append(len(out)); out += b"%d 0 obj\n" % i + b + b"\nendobj\n"
    x = len(out); out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, cat, x)
    open(path, "wb").write(out)

def run_export(o):
    """un solo punto per esportare: JPG (un file per spread), PDF (bozza per il cliente) o PSD (Photoshop)"""
    with LOCK: n = len(SP)
    nums = parse_range(o.get("range", ""), n); fmt = o["fmt"]
    dflt = (CFG.get("uscita_psd") or os.path.join(PROJ, "PSD")) if fmt == "psd" else os.path.join(PROJ, "Esportazioni", fmt.upper())
    dest = os.path.expanduser(o.get("dest") or dflt); os.makedirs(dest, exist_ok=True)
    nome = CFG.get("nome", "Album")
    with LOCK:
        if o.get("ev") is not None and abs(float(o["ev"]) - CFG["esposizione"].get("globale", 0.0)) > 1e-6: apply(dict(op="evg", value=o["ev"]))
        if fmt == "psd": CFG["uscita_psd"] = dest
        save(backup=False)
    def go():
        try:
            LOG.append(f"Esporto {len(nums)} spread in {fmt.upper()} → {dest}")
            if fmt == "jpg":
                K = 1.0 if o.get("res", "stampa") == "stampa" else 0.25; q = int(o.get("q", 92)); icc = srgb_icc()
                for k in nums:
                    with LOCK: tup = spread_tuple(k - 1)
                    im = A.render(tup, K, True); b = round(A.B * K)
                    if b: im = im.crop((b, b, im.width - b, im.height - b))
                    f = os.path.join(dest, f"{nome} - Spread {k:02d}.jpg"); im.save(f, "JPEG", quality=q, dpi=(A.PPI * K, A.PPI * K), icc_profile=icc, subsampling=0 if q >= 90 else 2)
                    LOG.append(f"  spread {k}: {os.path.basename(f)}")
                LOG.append("RISULTATO:" + dest)
            elif fmt == "pdf":
                from PIL import ImageDraw, ImageFont
                Wp = int(o.get("width", 2000)); K = Wp / VW; pages = []
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", max(14, Wp // 80))
                for k in nums:
                    with LOCK: tup = spread_tuple(k - 1)
                    im = A.render(tup, K, True); b = round(A.B * K)
                    if b: im = im.crop((b, b, im.width - b, im.height - b))
                    pg = Image.new("RGB", (im.width, im.height + 60), "white"); pg.paste(im, (0, 0)); d = ImageDraw.Draw(pg)
                    d.line([(im.width // 2, 0), (im.width // 2, im.height)], fill=(225, 225, 225), width=1)
                    if o.get("numeri", True): d.text((im.width / 2, im.height + 18), f"Spread {k} / {n}", font=font, fill=(140, 140, 140), anchor="mt")
                    pages.append(pg); LOG.append(f"  spread {k}")
                f = os.path.join(dest, f"{nome} - bozza.pdf"); jp = []
                for pg in pages:
                    bio = io.BytesIO(); pg.save(bio, "JPEG", quality=int(o.get("q", 80)), optimize=True, icc_profile=srgb_icc()); jp.append((bio.getvalue(), pg.width, pg.height))
                write_pdf(f, jp, 150)
                LOG.append(f"{len(pages)} pagine, {os.path.getsize(f) / 1e6:.1f} MB"); LOG.append("RISULTATO:" + f)
            else:
                cmd = [sys.executable, os.path.join(HERE, "genera_psd_angolo.py"), "--spread", ",".join(map(str, nums)), "--progetto", PROJ] + (["--forza"] if o.get("force") else [])
                p = subprocess.Popen(cmd, cwd=SCRIPTS, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(os.environ, ALBUM_PROGETTO=PROJ, ALBUM_SCRIPTS=SCRIPTS))
                for line in p.stdout: LOG.append(line.rstrip())
                if p.wait() == 0: LOG.append("RISULTATO:" + dest)
                else: LOG.append("Photoshop o lo script hanno dato errore (vedi sopra)")
        except Exception as e: LOG.append(f"ERRORE: {e}")
        LOG.append("[finito]")
    threading.Thread(target=go, daemon=True).start()
    return len(nums)

def autosave_loop():
    """salva da solo 2 secondi dopo l'ultima modifica; copia di sicurezza al massimo ogni 10 minuti"""
    while True:
        time.sleep(1)
        try:
            if time.time() - LAST["op"] > 2 and snap() != SAVED: save(backup=time.time() - LAST["backup"] > 600)
        except Exception as e: LOG.append(f"autosalvataggio non riuscito: {e}")

def pick(kind):
    if kind == "folder": sc = 'POSIX path of (choose folder with prompt "Scegli la cartella")'
    else: sc = ('set fs to choose file with prompt "Scegli le foto" of type {"public.jpeg"} with multiple selections allowed\nset out to ""\n'
                'repeat with f in fs\nset out to out & POSIX path of f & linefeed\nend repeat\nreturn out')
    r = subprocess.run(["osascript", "-e", sc], capture_output=True, text=True)
    return [x for x in r.stdout.split("\n") if x.strip()] if r.returncode == 0 else []

def do_import(paths):
    dst = os.path.join(PROJ, "Foto"); os.makedirs(dst, exist_ok=True); files = []
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                files += [os.path.join(root, f) for f in sorted(fs)]
        else: files.append(p)
    n = skipped = 0; new = []; have = {f.lower() for f in os.listdir(dst)}
    for f in files:
        base, ext = os.path.splitext(os.path.basename(f))
        if ext.lower() not in (".jpg", ".jpeg") or base.startswith("."): skipped += 1; continue
        name = base + ".jpg"
        if name.lower() in have: skipped += 1; continue
        try: os.link(f, os.path.join(dst, name))
        except OSError: shutil.copy2(f, os.path.join(dst, name))
        have.add(name.lower()); n += 1; new.append(os.path.join(dst, name))
    if new and os.path.abspath(dst) != os.path.abspath(CFG.get("foto", "")):          # il progetto legge un'altra cartella: aggiungo i file nuovi, altrimenti non comparirebbero
        with LOCK: CFG["foto_extra"] = list(dict.fromkeys(list(CFG.get("foto_extra", [])) + new)); save(backup=False)
    return n, skipped

def ricollega(cartella):
    """ricollega le foto mancanti: cerca per nome (anche nelle sottocartelle) nella cartella scelta e aggiorna i percorsi; non tocca le foto già trovate"""
    cartella = os.path.expanduser(cartella)
    if not os.path.isdir(cartella): raise ValueError("cartella non trovata")
    idx = {}
    for root, _, fs in os.walk(cartella):
        for f in fs:
            if f.lower().endswith((".jpg", ".jpeg")) and not f.startswith("."): idx.setdefault(f.lower(), os.path.join(root, f))
    with LOCK:
        trovate = 0; ancora = []; nuovi = {}
        for m in A.M:
            if os.path.exists(m.get("src", "")): continue
            p = idx.get(m["n"].lower())
            if p: m["src"] = p; nuovi[m["n"]] = p; trovate += 1
            else: ancora.append(m["n"])
        fd = CFG.get("foto", "")
        if os.path.isdir(fd):                                  # la cartella della selezione è fatta di collegamenti: quelli rotti si rifanno puntando alla foto ritrovata
            for f in os.listdir(fd):
                p = os.path.join(fd, f)
                if os.path.islink(p) and not os.path.exists(p) and f in nuovi:
                    try: os.remove(p); os.symlink(nuovi[f], p)
                    except OSError: pass
        CFG["foto_extra"] = [nuovi.get(os.path.basename(p), p) if not os.path.exists(p) else p for p in CFG.get("foto_extra", [])]
        json.dump(A.M, open(os.path.join(A.CACHE, "meta.json"), "w")); save(backup=False)
        return dict(trovate=trovate, mancanti=ancora, totale=len(A.M))

def esporta_progetto(o):
    """pacchetto autonomo del progetto (cartella, e volendo ZIP): spec, impostazioni, cache, modelli, elenco font e le foto; percorsi riparati da soli all'apertura"""
    dest = os.path.expanduser(o.get("dest") or "")
    if not os.path.isdir(dest): raise ValueError("scegli una cartella di destinazione")
    nome = re.sub(r'[\\/:*?"<>|]', "-", CFG.get("nome", "Album")).strip(" .") or "Album"; out = os.path.join(dest, f"{nome} - progetto"); k = 2
    while os.path.exists(out): out = os.path.join(dest, f"{nome} - progetto {k}"); k += 1
    with LOCK: save(backup=False); metas = copy.deepcopy(A.M); cfg = json.load(open(os.path.join(PROJ, "progetto.json")))
    con_foto = bool(o.get("foto", True)); zipf = bool(o.get("zip"))
    def go():
        try:
            LOG.append(f"Esporto il progetto in {out}"); os.makedirs(os.path.join(out, "_cache"))
            for f in ("spec.py", "album_libere.py", "testo.py"):
                src = os.path.join(PROJ, f) if os.path.exists(os.path.join(PROJ, f)) else os.path.join(HERE, f)
                if os.path.exists(src): shutil.copy2(src, os.path.join(out, f))
            for f in ("faces.json", "origine.json"):
                if os.path.exists(os.path.join(PROJ, "_cache", f)): shutil.copy2(os.path.join(PROJ, "_cache", f), os.path.join(out, "_cache", f))
            if os.path.isdir(os.path.join(PROJ, "_cache", "thumbs")): shutil.copytree(os.path.join(PROJ, "_cache", "thumbs"), os.path.join(out, "_cache", "thumbs"))
            LOG.append("  impostazioni, anteprime e correzioni copiate")
            if con_foto:
                os.makedirs(os.path.join(out, "Foto")); tot = len(metas)
                for n, m in enumerate(metas, 1):
                    if os.path.exists(m.get("src", "")): shutil.copy2(m["src"], os.path.join(out, "Foto", m["n"])); m["src"] = "Foto/" + m["n"]                    # relativo: all'apertura diventa quello della cartella dove sta il progetto
                    else: LOG.append(f"  ATTENZIONE: {m['n']} non trovata, non è nel pacchetto")
                    if n % 10 == 0 or n == tot: LOG.append(f"  foto {n} / {tot}")
            json.dump(metas, open(os.path.join(out, "_cache", "meta.json"), "w"))
            cfg["foto"] = ""; cfg["foto_extra"] = []; cfg["uscita_psd"] = ""             # vuoti = quelli del progetto stesso (Foto, PSD), li riempie l'editor all'apertura
            json.dump(cfg, open(os.path.join(out, "progetto.json"), "w"), indent=2, ensure_ascii=False)
            if os.path.exists(UT_FILE): shutil.copy2(UT_FILE, os.path.join(out, "modelli_utente.json")); LOG.append("  modelli salvati copiati")
            usati = sorted({it["font"] for sp in SP for pg in sp for it in pg[1] if it.get("kind") == "txt" and it.get("font")} | {cfg.get("testo", {}).get("font_testo_ps", "")} - {""})
            fam = {f["ps"]: f["fam"] + " " + f["sty"] for f in TX.fonts()}
            open(os.path.join(out, "font_usati.txt"), "w").write("Font usati nei testi (da installare sul computer dove apri il progetto):\n" + "\n".join(f"  {fam.get(p, p)}  [{p}]" for p in usati) + "\n")
            open(os.path.join(out, "LEGGIMI.txt"), "w").write(f"Progetto «{cfg.get('nome', nome)}» esportato dall'Impaginatore.\n\nPer aprirlo: nell'Impaginatore, Progetti → Apri progetto esistente → scegli questa cartella"
                + (" (o Importa ZIP se hai il file .zip)" if zipf else "") + ".\n" + ("Le foto sono nella cartella Foto: i percorsi si sistemano da soli." if con_foto else "Le foto NON sono incluse: all'apertura premi «Progetto» → «Ricollega foto» e scegli la cartella con gli originali.")
                + "\nI PSD già generati non sono inclusi: si rigenerano con Esporta → PSD.\nInstalla i font elencati in font_usati.txt.\n")
            res = out
            if zipf:
                import zipfile
                LOG.append("  creo lo ZIP…"); res = out + ".zip"
                with zipfile.ZipFile(res, "w", zipfile.ZIP_STORED) as z:
                    for root, _, fs in os.walk(out):
                        for f in fs: p = os.path.join(root, f); z.write(p, os.path.relpath(p, dest))
            LOG.append(f"Fatto: {sum(len(f) for _, _, f in os.walk(out))} file"); LOG.append("RISULTATO:" + res)
        except Exception as ex: LOG.append(f"ERRORE: {ex}")
        LOG.append("[finito]")
    LOG.clear(); threading.Thread(target=go, daemon=True).start()
    return out

def importa_modelli_progetto():
    """modelli salvati arrivati insieme a un progetto esportato: si aggiungono ai tuoi (stesso id = già presenti)"""
    p = os.path.join(PROJ, "modelli_utente.json")
    try:
        if not os.path.exists(p): return
        mine = ut_load(); ids = {t["id"] for t in mine}; names = {t["nome"].lower() for t in mine}; add = 0
        for t in json.load(open(p)):
            if t["id"] in ids: continue
            if t["nome"].lower() in names: t["nome"] += " (importato)"
            mine.append(t); names.add(t["nome"].lower()); add += 1
        if add: ut_save(mine); print(f"modelli importati dal progetto: {add}", flush=True)
    except Exception as ex: print("importa modelli:", ex, flush=True)
importa_modelli_progetto()

def versioni():
    """backup di spec.py fatti dall'editor, dal più recente: [{ts, spread, label}] (senza doppioni identici di fila)"""
    bk = os.path.join(PROJ, "_backup_editor"); out = []; prev = None
    if not os.path.isdir(bk): return out
    for f in sorted(os.listdir(bk), reverse=True):
        if not f.endswith("_spec.py"): continue
        ts = f[:-8]; txt = open(os.path.join(bk, f), errors="replace").read(); h = hashlib.md5(txt.encode()).hexdigest()
        if h == prev: continue
        prev = h; m = re.search(r"(\d+) spread", txt.split("\n", 1)[0])
        try: lab = time.strftime("%d/%m %H:%M:%S", time.strptime(ts, "%Y%m%d-%H%M%S"))
        except Exception: lab = ts
        out.append(dict(ts=ts, spread=int(m.group(1)) if m else len(re.findall(r"^\s*# \d+\s*$", txt, re.M)), label=lab))
        if len(out) >= 80: break
    return out

def ripristina(ts):
    """rimette la versione ts di spec.py/progetto.json (prima salva lo stato attuale come backup) e riavvia l'editor senza risalvare"""
    bk = os.path.join(PROJ, "_backup_editor"); src, srcj = os.path.join(bk, f"{ts}_spec.py"), os.path.join(bk, f"{ts}_progetto.json")
    if not re.fullmatch(r"\d{8}-\d{6}", ts) or not os.path.exists(src): raise ValueError("versione non trovata")
    with LOCK:
        save(backup=True)
        shutil.copy2(src, os.path.join(PROJ, "spec.py"))
        if os.path.exists(srcj):
            old = json.load(open(srcj)); cur = json.load(open(os.path.join(PROJ, "progetto.json")))
            for k in ("foto", "foto_extra", "uscita_psd"):                       # i percorsi restano quelli di adesso
                if k in cur: old[k] = cur[k]
            json.dump(old, open(os.path.join(PROJ, "progetto.json"), "w"), indent=2, ensure_ascii=False)
    def go(): time.sleep(.6); os.execv(sys.executable, sys.orig_argv)
    threading.Thread(target=go, daemon=True).start()

def restart():
    """riavvia l'editor (il motore legge le foto all'avvio): prima salva"""
    def go():
        time.sleep(.6); save(backup=False)
        os.execv(sys.executable, sys.orig_argv)
    threading.Thread(target=go, daemon=True).start()

# ------------------------------------------------------------------ http
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, body, ctype="application/json", code=200, etag=None):
        if isinstance(body, (dict, list)): body = json.dumps(body).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        if etag: self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache" if etag else "max-age=3600" if ctype == "image/jpeg" else "no-store"); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        try:
            if u.path == "/": self.send(open(os.path.join(HERE, "index.html"), "rb").read(), "text/html; charset=utf-8")
            elif u.path == "/api/state": self.send(state())
            elif u.path == "/api/templates": self.send(templates(int(q.get("s", ["0"])[0])))
            elif u.path.startswith("/api/info/"): self.send(photo_info(u.path.rsplit("/", 1)[1]))
            elif u.path == "/api/fonts": self.send(dict(fonts=[dict(fam=f["fam"], sty=f["sty"], ps=f["ps"]) for f in TX.fonts()]))
            elif u.path == "/api/ping": self.send({"boot": BOOT, "agg": AGG["n"]})
            elif u.path == "/api/log": self.send(LOG[-200:])
            elif u.path == "/api/versioni": self.send(versioni())
            elif u.path.startswith("/img/spread/"): self.send(spread_jpg(int(u.path.rsplit("/", 1)[1]), float(q.get("k", ["0.2"])[0])), "image/jpeg")
            elif u.path.startswith("/img/thumb/"):
                n = u.path.rsplit("/", 1)[1]; w = int(q.get("w", ["260"])[0]); et = '"%s-%d-%d"' % (n, w, PV.get(n, 0))
                if self.headers.get("If-None-Match") == et: self.send_response(304); self.send_header("ETag", et); self.end_headers()
                else: self.send(thumb_jpg(n, w), "image/jpeg", etag=et)
            else: self.send({"errore": "non trovato"}, code=404)
        except Exception as e: self.send({"errore": str(e)}, code=500)
    def do_POST(self):
        u = urlparse(self.path); n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        try:
            if u.path == "/api/op": do_op(body); self.send(state())
            elif u.path == "/api/templates": self.send(templates_for(body["photos"]))
            elif u.path == "/api/pick": self.send({"paths": pick(body["kind"])})
            elif u.path == "/api/import":
                n, sk = do_import(body["paths"])
                if n: restart()
                self.send({"importate": n, "saltate": sk, "riavvio": n > 0})
            elif u.path == "/api/modelli": modelli(body); self.send({"ok": True})
            elif u.path == "/api/aggiorna_foto":
                ok, ars, ko = aggiorna_foto(foto_cambiate()); self.send(dict(aggiornate=ok, proporzioni=ars, errori=ko))
            elif u.path == "/api/ricollega":
                c = body.get("cartella") or (pick("folder") or [""])[0]
                if not c: self.send({"annullato": True})
                else: self.send(ricollega(c))
            elif u.path == "/api/prj_esporta":
                d = body.get("dest") or (pick("folder") or [""])[0]
                if not d: self.send({"annullato": True})
                else: self.send({"cartella": esporta_progetto(dict(body, dest=d))})
            elif u.path == "/api/ripristina": ripristina(body["ts"]); self.send({"riavvio": True})
            elif u.path == "/api/save": ts = save(); self.send(dict(state(), salvato=ts))
            elif u.path == "/api/export": LOG.clear(); self.send({"spread": run_export(body)})
            elif u.path == "/api/reveal": subprocess.run(["open", "-R", body["path"]]); self.send({"ok": True})
            else: self.send({"errore": "non trovato"}, code=404)
        except Exception as e: self.send({"errore": str(e)}, code=400)

if __name__ == "__main__":
    threading.Thread(target=autosave_loop, daemon=True).start(); threading.Thread(target=foto_watch_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.porta), H)
    print(f"Editor album: http://127.0.0.1:{ARGS.porta}  | progetto: {PROJ}  | script: {SCRIPTS}", flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
