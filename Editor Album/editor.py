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
CFG.setdefault("tono", {}); CFG.setdefault("tono_escl", []); CFG.setdefault("tolte", []); CFG.setdefault("colori", {}); CFG.setdefault("ritocco", {}); CFG.setdefault("stelle", []); CFG.setdefault("testo", {}); CFG.setdefault("stili", {})

# ------------------------------------------------------------------ stato
NPH = {"BLANK": 0, "FULL": 1, "DUO": 2, "VLL": 3, "V4": 5, "G4": 4, "CV": 1, "SV": 1, "PP": 1, "COL2": 2, "BAND2": 2, "STRIP3": 3,
       "PANO": 1, "ANG": 1, "D2H": 2, "D2B": 2, "T1_2": 3, "T3B": 3, "T3C": 3, "Q4C": 4, "Q1_3": 4, "F5": 5, "S6": 6}
BUILD = {
    "BLANK": lambda p, m: [],
    "FULL": lambda p, m: [A.FULL(p[0])], "DUO": lambda p, m: A.DUO(*p), "VLL": lambda p, m: A.VLL(*p, mirror=m),
    "V4": lambda p, m: A.V4(*p, mirror=m), "G4": lambda p, m: A.G4(*p), "CV": lambda p, m: A.CV(*p), "SV": lambda p, m: A.SV(*p),
    "PP": lambda p, m: A.PP(*p), "COL2": lambda p, m: A.COL2(*p), "BAND2": lambda p, m: A.BAND2(*p), "STRIP3": lambda p, m: A.STRIP3(*p),
    # ---- varianti in più (griglia 12x8 per pagina; colonna, riga, larghezza, altezza)
    "PANO": lambda p, m: [A.P(p[0], 0, 2, 12, 4)],                                          # 1 foto: fascia panoramica a tutta larghezza
    "ANG": lambda p, m: [A.P(p[0], 1, 1, 6, 6)] if m else [A.P(p[0], 5, 1, 6, 6)],           # 1 foto: quadrata spostata su un lato
    "D2H": lambda p, m: [A.P(p[0], 0, 0, 12, 4), A.P(p[1], 0, 4, 12, 4)],                    # 2 foto: una sopra l'altra, a tutta larghezza
    "D2B": lambda p, m: [A.P(p[0], 4, 0, 8, 8), A.P(p[1], 0, 0, 4, 8)] if m else [A.P(p[0], 0, 0, 8, 8), A.P(p[1], 8, 0, 4, 8)],   # 2 foto: una grande e una stretta
    "T1_2": lambda p, m: [A.P(p[0], 0, 4, 12, 4), A.P(p[1], 0, 0, 6, 4), A.P(p[2], 6, 0, 6, 4)] if m else [A.P(p[0], 0, 0, 12, 4), A.P(p[1], 0, 4, 6, 4), A.P(p[2], 6, 4, 6, 4)],   # 3 foto: una larga + due
    "T3B": lambda p, m: [A.P(p[0], 4, 0, 8, 8), A.P(p[1], 0, 0, 4, 4), A.P(p[2], 0, 4, 4, 4)] if m else [A.P(p[0], 0, 0, 8, 8), A.P(p[1], 8, 0, 4, 4), A.P(p[2], 8, 4, 4, 4)],   # 3 foto: una grande + due piccole
    "T3C": lambda p, m: [A.P(p[0], 0, 0, 6, 8), A.P(p[1], 6, 0, 3, 8), A.P(p[2], 9, 0, 3, 8)] if not m else [A.P(p[0], 6, 0, 6, 8), A.P(p[1], 0, 0, 3, 8), A.P(p[2], 3, 0, 3, 8)],   # 3 foto: tre colonne
    "Q4C": lambda p, m: [A.P(p[j], 3 * j, 0, 3, 8) for j in range(4)],                       # 4 foto: quattro colonne
    "Q1_3": lambda p, m: [A.P(p[0], 0, 3, 12, 5), A.P(p[1], 0, 0, 4, 3), A.P(p[2], 4, 0, 4, 3), A.P(p[3], 8, 0, 4, 3)] if m else [A.P(p[0], 0, 0, 12, 5), A.P(p[1], 0, 5, 4, 3), A.P(p[2], 4, 5, 4, 3), A.P(p[3], 8, 5, 4, 3)],   # 4 foto: una larga + tre
    "F5": lambda p, m: [A.P(p[0], 4, 0, 8, 5), A.P(p[1], 0, 0, 4, 5), A.P(p[2], 0, 5, 4, 3), A.P(p[3], 4, 5, 4, 3), A.P(p[4], 8, 5, 4, 3)] if m else [A.P(p[0], 0, 0, 8, 5), A.P(p[1], 8, 0, 4, 5), A.P(p[2], 0, 5, 4, 3), A.P(p[3], 4, 5, 4, 3), A.P(p[4], 8, 5, 4, 3)],   # 5 foto
    "S6": lambda p, m: [A.P(p[j], 4 * (j % 3), 4 * (j // 3), 4, 4) for j in range(6)],       # 6 foto: griglia 3x2
}

# ---- modelli «d'autore» pensati sullo spread intero (cornici libere): alcuni attraversano la piega o hanno margini bianchi
def _sp_split(a, b, n, g):
    t = (b - a - g * (n - 1)) / n; return [(a + i * (t + g), a + i * (t + g) + t) for i in range(n)]
def _sp_stack(x0, x1, n, y0, y1, g):
    t = (y1 - y0 - g * (n - 1)) / n; return [(x0, y0 + i * (t + g), x1, y0 + i * (t + g) + t) for i in range(n)]
def _sp_models(CW, CH, G):
    F = CW / 2; PL, PR = F - G / 2, F + G / 2; M = {}
    M["X1"] = [(0, 0, PL, .62 * CH)] + [(a, .62 * CH + G, b, CH) for a, b in _sp_split(0, PL, 2, G)] + [(a, 0, b, CH) for a, b in _sp_split(PR, CW, 2, G)]
    M["X2"] = [(0, 0, .24 * CW, CH)] + _sp_stack(.24 * CW + G, PL, 2, 0, CH, G) + [(PR, 0, CW, CH)]
    M["X3"] = [(0, 0, PL, CH)] + [r for a, b in _sp_split(PR, CW, 2, G) for r in _sp_stack(a, b, 2, 0, CH, G)]
    M["X4"] = [(0, 0, PL, .6 * CH)] + [(a, .6 * CH + G, b, CH) for a, b in _sp_split(0, PL, 2, G)] + [r for a, b in _sp_split(PR, CW, 2, G) for r in _sp_stack(a, b, 2, 0, CH, G)]
    M["X5"] = [(0, 0, PL, CH), (.66 * CW, .12 * CH, .84 * CW, .88 * CH)]
    M["X6"] = [(0, 0, PL, CH)] + [r for a, b in _sp_split(PR, CW, 3, G) for r in _sp_stack(a, b, 2, 0, CH, G)]
    M["X7"] = [(.03 * CW, .12 * CH, .97 * CW, .88 * CH)]
    M["X8"] = [(0, 0, CW, .6 * CH)] + [(a, .6 * CH + G, b, CH) for a, b in _sp_split(0, CW, 4, G)]
    M["X9"] = [(.08 * CW, .1 * CH, .27 * CW, .9 * CH), (.29 * CW, .1 * CH, .48 * CW, .9 * CH), (.52 * CW, .1 * CH, .71 * CW, .9 * CH), (.73 * CW, .1 * CH, .92 * CW, .9 * CH)]
    M["X10"] = [(0, 0, .62 * CW, CH)] + [(a, 0, b, CH) for a, b in _sp_split(.62 * CW + G, CW, 2, G)]
    M["X11"] = [(0, 0, .25 * CW - G / 2, CH)] + _sp_stack(.25 * CW + G / 2, PL, 3, 0, CH, G) + _sp_stack(PR, .75 * CW - G / 2, 2, 0, CH, G) + [(.75 * CW + G / 2, 0, CW, CH)]
    M["X12"] = [(0, 0, PL, CH), (.76 * CW, .3 * CH, .9 * CW, .93 * CH)]
    M["X13"] = [(.1 * CW, .05 * CH, .27 * CW, .75 * CH), (.29 * CW, .2 * CH, .46 * CW, .9 * CH), (.54 * CW, .1 * CH, .71 * CW, .8 * CH), (.73 * CW, .25 * CH, .9 * CW, .95 * CH)]
    M["X14"] = [(.25 * CW, .18 * CH, .75 * CW, .82 * CH), (.03 * CW, .07 * CH, .2 * CW, .45 * CH), (.8 * CW, .07 * CH, .97 * CW, .45 * CH), (.03 * CW, .55 * CH, .2 * CW, .93 * CH), (.8 * CW, .55 * CH, .97 * CW, .93 * CH)]
    M["X16"] = [(a, 0, b, CH) for a, b in _sp_split(0, CW, 5, G)]
    M["X17"] = [(0, 0, .75 * CW, CH)] + _sp_stack(.75 * CW + G, CW, 3, 0, CH, G)
    M["X20"] = [(0, 0, PL, CH)] + _sp_stack(.56 * CW, .94 * CW, 3, .2 * CH, .8 * CH, G)
    M["X21"] = [(0, .32 * CH, CW, .68 * CH)] + [r for a, b in _sp_split(0, CW, 2, G) for r in ((a, 0, b, .32 * CH - G), (a, .68 * CH + G, b, CH))]
    M["X23"] = [(0, 0, .25 * CW, CH), (.25 * CW + G, 0, .75 * CW - G, CH), (.75 * CW, 0, CW, CH)]
    M["X25"] = [r for a, b in _sp_split(0, CW, 6, G) for r in _sp_stack(a, b, 2, 0, CH, G)]
    M["X27"] = [(a, (.12 if i % 2 else .04) * CH, b, (.96 if i % 2 else .88) * CH) for i, (a, b) in enumerate(_sp_split(.04 * CW, .96 * CW, 6, G))]
    M["X28"] = [(0, 0, .6 * CW, CH), (.6 * CW + G, 0, CW, .5 * CH - G / 2)] + [(a, .5 * CH + G / 2, b, CH) for a, b in _sp_split(.6 * CW + G, CW, 2, G)]
    M["X29"] = [(.3 * CW, .04 * CH, .7 * CW, .34 * CH), (.12 * CW, .38 * CH, .48 * CW, .66 * CH), (.52 * CW, .38 * CH, .88 * CW, .66 * CH)] + [(a, .7 * CH, b, .96 * CH) for a, b in _sp_split(.06 * CW, .94 * CW, 3, G)]
    return M
def _sp_isL(c, CW): return c < CW / 2 - 0.5       # una cornice centrata sulla piega (entro mezzo pixel) conta per la pagina destra, sempre
def _sp_build(key, side, m):
    def build(p, _m=False):
        CW, CH, G = A.CW, A.CH, A.G; F = CW / 2; R = _sp_models(CW, CH, G)[key]
        if m: R = [(CW - xb, ya, CW - xa, yb) for xa, ya, xb, yb in R]
        x0, x1 = (0, F - G / 2) if side == "L" else (F + G / 2, CW)
        mine = sorted((r for r in R if _sp_isL((r[0] + r[2]) / 2, CW) == (side == "L")), key=lambda r: (round(r[0] / 50), round(r[1] / 50)))
        return [dict(k="f", i=p[j] - 1, x=round((r[0] - x0) / (x1 - x0), 4), y=round(r[1] / CH, 4), w=round((r[2] - r[0]) / (x1 - x0), 4), h=round((r[3] - r[1]) / CH, 4), bw=False, z=1.0) for j, r in enumerate(mine)]
    return build
SPM_KEYS = ["X%d" % k for k in range(1, 15)] + ["X16", "X17", "X20", "X21", "X23", "X25", "X27", "X28", "X29"]
for _k in SPM_KEYS:
    for _m in (False, True):
        for _sd in "LR":
            _n = _k + ("M" if _m else "") + _sd; BUILD[_n] = _sp_build(_k, _sd, _m)       # la versione specchiata ha un altro numero di foto per pagina: modulo a parte
            NPH[_n] = sum(1 for r in _sp_models(A.CW, A.CH, A.G)[_k] if _sp_isL(((A.CW - r[2] + A.CW - r[0]) if _m else (r[0] + r[2])) / 2, A.CW) == (_sd == "L"))
COUPLED = [((k + ("M" if m else "") + "L", "I", False), (k + ("M" if m else "") + "R", "I", False)) for k in SPM_KEYS for m in (False, True)]

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
        ("STRIP3", "W", False), ("BLANK", "W", False), ("CV", "W", False), ("SV", "W", False), ("PP", "W", False), ("COL2", "W", False), ("BAND2", "W", False),
        ("PANO", "W", False), ("ANG", "W", False), ("ANG", "W", True), ("D2H", "I", False), ("D2H", "W", False), ("D2B", "I", False), ("D2B", "I", True), ("D2B", "W", False),
        ("T1_2", "I", False), ("T1_2", "I", True), ("T1_2", "W", False), ("T3B", "I", False), ("T3B", "I", True), ("T3B", "W", False), ("T3C", "I", False), ("T3C", "W", False),
        ("Q4C", "I", False), ("Q4C", "W", False), ("Q1_3", "I", False), ("Q1_3", "I", True), ("Q1_3", "W", False), ("F5", "I", False), ("F5", "I", True), ("F5", "W", False), ("S6", "I", False), ("S6", "W", False)]
SP = [[[mode, [dict(it) for it in items]] for (mode, items) in sp] for sp in A.load_spec()]
GD = [dict(v=list(g.get("v", [])), h=list(g.get("h", []))) for g in CFG.get("guide", [])][:len(SP)]       # linee guida di ogni spread (px della vista)
GD += [dict(v=[], h=[]) for _ in range(len(SP) - len(GD))]
UNDO, REDO = [], []
CLIP = []                                           # appunti: copia/incolla di elementi tra spread
LOG = []

def _ver_programma():       # numero di rilascio (file VERSION nella cartella del programma): serve a vedere quale versione sta girando
    try: return open(os.path.join(os.path.dirname(HERE), "VERSION")).read().strip()
    except Exception: return ""

def snap(): return json.dumps({"sp": SP, "ev": CFG["esposizione"], "ff": CFG["centri_volto"], "gd": GD, "tn": CFG["tono"], "tl": CFG["tolte"], "cl": CFG["colori"], "rt": CFG["ritocco"], "sr": CFG["stelle"], "te": CFG["tono_escl"], "tx": CFG["testo"], "st": CFG["stili"]})
SAVED = snap()                                       # stato dell'ultimo salvataggio: serve a sapere se ci sono modifiche vere
def restore(s):
    global SP, GD
    d = json.loads(s); SP = d["sp"]; GD = d["gd"]
    CFG["esposizione"].clear(); CFG["esposizione"].update(d["ev"])
    CFG["centri_volto"].clear(); CFG["centri_volto"].update(d["ff"])
    A.FACE_FIX.clear(); A.FACE_FIX.update({k: tuple(v) for k, v in d["ff"].items()})
    CFG["tono"].clear(); CFG["tono"].update(d.get("tn", {})); CFG["tolte"][:] = d.get("tl", []); CFG["colori"].clear(); CFG["colori"].update(d.get("cl", {})); CFG["ritocco"].clear(); CFG["ritocco"].update(d.get("rt", {})); CFG["stelle"][:] = d.get("sr", []); CFG["tono_escl"][:] = d.get("te", []); CFG["testo"].clear(); CFG["testo"].update(d.get("tx", {})); CFG["stili"].clear(); CFG["stili"].update(d.get("st", {})); sync_testo()

def sync_testo():                                     # il motore legge i testi una volta sola: li rimetto in A.TITLE
    t = CFG["testo"]; A.TITLE = (t.get("nome", ""), t.get("sottotitolo", ""), t.get("data", ""))

def keep(it): return {k: it[k] for k in ("a", "zo", "ts", "stile", "bd", "sh", "oc") if it.get(k) is not None}

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

def _zprep(s, sel):
    """prima di spostare i livelli: le foto scelte (e quelle che le toccano) che sono ancora cornici del modello diventano cornici libere (stessa posizione),
    altrimenti restano sempre SOTTO le libere e non si possono più portare davanti/dietro. Restituisce l'ordine dal fondo alla cima."""
    R = _rects(s); free = _draw_order(s); fs = set(free)
    rs = [R[k] for k in sel if k in R]
    hit = lambda L: any(L["x"] < r["x"] + r["W"] and r["x"] < L["x"] + L["W"] and L["y"] < r["y"] + r["H"] and r["y"] < L["y"] + L["H"] for r in rs)
    conv = [(side, idx) for side, idx, it in _flat(s) if (side, idx) not in fs and it["k"] != "t" and (side, idx) in R and ((side, idx) in sel or hit(R[(side, idx)]))]
    for side, idx in conv:
        L = R[(side, idx)]; _put_px(s, side, idx, L["x"], L["y"], L["W"], L["H"])
    return conv + free

def _put_px(s, side, idx, x, y, W, H):
    pg = SP[s][0 if side == "L" else 1]; it = pg[1][idx]; (x0, x1), (y0, y1) = A._frame(side, pg[0]); w, h = W / (x1 - x0), H / (y1 - y0)
    fx, fy = (x - x0) / (x1 - x0), (y - y0) / (y1 - y0)
    pg[1][idx] = mkfree(it, min(max(fx, -1.0), 2 - w), min(max(fy, -0.5), 1.5 - h), w, h)

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
        if "bd" in o:                                     # bordo: [millimetri, "#rrggbb"] oppure null
            v = o["bd"]
            if v and float(v[0]) > 0 and re.fullmatch(r"#[0-9a-fA-F]{6}", str(v[1])): a["bd"] = [round(min(float(v[0]), 40.0), 1), str(v[1]).lower()]
            else: a.pop("bd", None)
        if "oc" in o:
            v = int(round(min(max(float(o["oc"]), 0), 100)))
            if v < 100: a["oc"] = v
            else: a.pop("oc", None)
        if "sh" in o:
            v = int(round(min(max(float(o["sh"] or 0), 0), 100)))
            if v: a["sh"] = v
            else: a.pop("sh", None)
    elif t == "tono_fix":                                # correzioni del tono di una volta sola (un solo annulla): [{photo, ev, rit:{alt,omb,bia}}]
        for c in o["items"]:
            n = c["photo"]; v = round(min(max(float(c["ev"]), -2.0), 2.0), 2)
            if abs(v) < 0.005: CFG["esposizione"]["per_foto"].pop(n, None)
            else: CFG["esposizione"]["per_foto"][n] = v
            if c.get("rit") is not None:
                r = CFG["ritocco"].setdefault(n, {})
                for k, val in c["rit"].items():
                    if k not in ("alt", "omb", "bia"): continue
                    val = round(min(max(float(val), -100), 100))
                    if val: r[k] = val
                    else: r.pop(k, None)
                if not r: CFG["ritocco"].pop(n, None)
    elif t == "tono_L":                                  # riferimento standard del tono (L* medio) e ampiezza della zona giusta
        if "value" in o:
            v = round(min(max(float(o["value"]), 30.0), 75.0), 1)
            if abs(v - TONO_L0) < 0.05: CFG.pop("tono_L", None)
            else: CFG["tono_L"] = v
        if "zona" in o:
            z = round(min(max(float(o["zona"]), 4.0), 30.0), 1)
            if abs(z - TONO_Z0) < 0.05: CFG.pop("tono_Z", None)
            else: CFG["tono_Z"] = z
    elif t == "tono_escl":                               # foto escluse dalla misura del tono (scure o chiare di proposito)
        for n in o.get("photos") or [o["photo"]]:
            if o.get("value", True):
                if n not in CFG["tono_escl"]: CFG["tono_escl"].append(n)
            elif n in CFG["tono_escl"]: CFG["tono_escl"].remove(n)
    elif t == "stella":                                  # foto preferite
        for n in o.get("photos") or [o["photo"]]:
            if o.get("value", True):
                if n not in CFG["stelle"]: CFG["stelle"].append(n)
            elif n in CFG["stelle"]: CFG["stelle"].remove(n)
    elif t == "ratio":                                   # cornici alla proporzione r (larghezza/altezza): stessa area, stesso centro
        s_ = o["s"]; R = _rects(s_); r_ = float(o["r"])
        for a in o["ats"]:
            key = (a[0], int(a[1])); L = R.get(key); pg_ = SP[s_][0 if key[0] == "L" else 1]; it = pg_[1][key[1]]
            if L is None or it["k"] == "t": continue
            (x0, x1), (y0, y1) = A._frame(key[0], pg_[0]); area = L["W"] * L["H"]; W = (area * r_) ** 0.5; H = W / r_
            f = min(1.0, (x1 - x0) / W, (y1 - y0) / H); W, H = W * f, H * f
            _put_px(s_, key[0], key[1], L["x"] + L["W"] / 2 - W / 2, L["y"] + L["H"] / 2 - H / 2, W, H); pg_[1][key[1]]["z"] = 1.0
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
        if "lh" in o: it["lh"] = round(min(max(float(o["lh"]), 0.6), 3.0), 2)
        if "caps" in o: it["caps"] = bool(o["caps"])
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
        for n in o.get("photos") or [o["photo"]]:
            if o.get("value", True):
                if n not in CFG["tolte"]: CFG["tolte"].append(n)
            elif n in CFG["tolte"]: CFG["tolte"].remove(n)
    elif t == "colore":                                # etichetta colore (come Lightroom) su una o più foto
        v = o.get("value")
        if v is not None and v not in COLORI: raise ValueError("colore sconosciuto")
        for n in o.get("photos") or [o["photo"]]:
            if v: CFG["colori"][n] = v
            else: CFG["colori"].pop(n, None)
    elif t == "rit":                                   # ritocco stile Lightroom: {photo, key, value} oppure {photo, reset:true}; "photos" per più foto
        for n in o.get("photos") or [o["photo"]]:
            if o.get("reset"): CFG["ritocco"].pop(n, None); CFG["tono"].pop(n, None); continue
            if o.get("copia"): CFG["ritocco"][n] = dict(o["copia"]); continue
            if o["key"] not in FL.RIT_KEYS: raise ValueError("regolazione sconosciuta")
            r = CFG["ritocco"].setdefault(n, {}); v = round(min(max(float(o["value"]), -100), 100))
            if v: r[o["key"]] = v
            else: r.pop(o["key"], None)
            if not r: CFG["ritocco"].pop(n, None)
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
    elif t == "newspreadsel":                             # foto trascinate sulla fila degli spread: nuovo spread nel punto scelto, col modello che rispetta meglio le proporzioni
        names = list(o["names"]); ph = []
        for n in names:
            if n not in A.IDX: raise ValueError(f"foto sconosciuta: {n}")
            if A.IDX[n] - 1 not in ph: ph.append(A.IDX[n] - 1)
        if not 1 <= len(ph) <= 10: raise ValueError("per uno spread servono da 1 a 10 foto")
        best = next((x for x in tpl_options(ph)["items"] if x.get("L") and x.get("R")), None)
        if best is None: raise ValueError("nessun modello adatto a queste foto")
        gone = set(ph)
        for sp in SP:
            for pg in sp: pg[1][:] = [it for it in pg[1] if it["k"] == "t" or it["i"] not in gone]       # le foto spostate escono dal vecchio spread (restano le altre e i testi)
        pos = min(max(int(o.get("pos", len(SP))), 0), len(SP))
        SP.insert(pos, [[best[side]["mode"], [dict(x) for x in BUILD[best[side]["module"]]([i + 1 for i in best[side]["photos"]], bool(best[side].get("mirror")))]] for side in "LR"])
        GD.insert(pos, dict(v=[], h=[]))
    elif t == "addtospread":                              # foto lasciate sulla miniatura di uno spread esistente: entrano lì (cornici libere) e, a richiesta, lo spread si riorganizza con un altro modello
        s_ = o["s"]; ph = []
        for n in o["names"]:
            if n not in A.IDX: raise ValueError(f"foto sconosciuta: {n}")
            if A.IDX[n] - 1 not in ph: ph.append(A.IDX[n] - 1)
        here = {it["i"] for pg in SP[s_] for it in pg[1] if it["k"] != "t"}; new = [i for i in ph if i not in here]
        gone = set(new)
        for k, sp in enumerate(SP):
            if k == s_: continue
            for pg in sp: pg[1][:] = [it for it in pg[1] if it["k"] == "t" or it["i"] not in gone]
        for j, i in enumerate(new): apply(dict(op="putfree", s=s_, photo=A.name(i), fx=0.27 + 0.46 * (j % 2), fy=0.42 + 0.08 * ((j // 2) % 3)))
        if o.get("how") == "reorg":
            alt = [x for x in templates(s_)["items"] if not x["cur"]]
            if not alt: raise ValueError("nessun altro modello adatto a queste foto")
            apply(dict(op="template", s=s_, **{k: alt[0][k] for k in "LR" if k in alt[0]}))
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
        w, h = max(w, 0.03), max(h, 0.03); x, y = min(max(x, -1.0), 2 - w), min(max(y, -0.5), 1.5 - h)     # x oltre 0..1: la cornice passa sull'altra pagina
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
        w, h = max(w, 0.03), max(h, 0.03); x, y = min(max(x, -1.0), 2 - w), min(max(y, -0.5), 1.5 - h)
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
        s_ = o["s"]; sel = {(a[0], int(a[1])) for a in o["ats"]}; order = _zprep(s_, sel)
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
            (x0, x1), (y0, y1) = A._frame(side, "I"); _put_px(s_, side, idx, x0, y0, x1 - x0, y1 - y0)       # tutta la pagina, fino al bordo
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
        s_ = o["s"]; R = _rects(s_); mv = []
        for a in o["ats"]:
            key = (a[0], int(a[1])); L = R.get(key); pg = SP[s_][0 if key[0] == "L" else 1][1]
            if L is None or key[1] >= len(pg) or pg[key[1]]["k"] == "t": continue
            mv.append((pg[key[1]], L))
        for it, L in mv: _put_obj(s_, it, L["x"] + float(o["dx"]), L["y"] + float(o["dy"]), L["W"], L["H"])         # ognuna passa all'altra pagina se il suo centro ci arriva
    elif t == "setrects":                                 # più foto: nuova posizione e misura (px della vista), un solo annulla — usato dalla correzione delle spaziature
        s_ = o["s"]
        for side, idx, x, y, w, h in o["rects"]:
            if side not in ("L", "R") or not 0 <= int(idx) < len(SP[s_][0 if side == "L" else 1][1]): continue
            if SP[s_][0 if side == "L" else 1][1][int(idx)]["k"] == "t": continue
            _put_px(s_, side, int(idx), float(x) + BL, float(y) + BL, float(w), float(h))
    elif t == "gscale":                                   # allargamento di gruppo: le foto scelte si ingrandiscono/rimpiccioliscono insieme attorno a un punto fisso (px della vista)
        s_ = o["s"]; R = _rects(s_); sx, sy = min(max(float(o["sx"]), 0.1), 10.0), min(max(float(o["sy"]), 0.1), 10.0); ax, ay = float(o["ax"]) + BL, float(o["ay"]) + BL
        for a in o["ats"]:
            key = (a[0], int(a[1])); L = R.get(key)
            if L is None or SP[s_][0 if key[0] == "L" else 1][1][key[1]]["k"] == "t": continue
            _put_px(s_, key[0], key[1], ax + (L["x"] - ax) * sx, ay + (L["y"] - ay) * sy, L["W"] * sx, L["H"] * sy)
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
    elif t == "swappages":                                # inverte le due pagine: quello che stava a sinistra va a destra e viceversa (stesse posizioni dentro la pagina)
        s_ = o["s"]
        if not 0 <= s_ < len(SP): raise ValueError("spread inesistente")
        SP[s_][0], SP[s_][1] = SP[s_][1], SP[s_][0]; GD[s_]["v"] = [round(VW - x, 1) for x in GD[s_]["v"]]
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
                    {A.name(it["i"]): CFG["ritocco"].get(A.name(it["i"])) for pg in SP[s] for it in pg[1] if it["k"] != "t"},
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
                if is_txt(it): e.update(tx=it["tx"], font=it["font"], size=it["size"], col=it["col"], al=it["al"], tr=it["tr"], lh=TX.lead(it), caps=bool(it.get("caps")), auto=bool(it.get("auto", True)), stile=it.get("stile"))
            else:
                n = A.name(it["i"]); ar = A.M[it["i"]]["ar"]; fa = L["W"] / L["H"]
                e.update(crop=round(max(fa / ar, ar / fa) * it.get("z", 1.0), 2))
                l_, t_, r_, b_ = A.zcrop(L); m_ = A.M[it["i"]]
                e.update(box=[round(l_, 4), round(t_, 4), round(r_, 4), round(b_, 4)], cm=[round(L["W"] / A.PPI * 2.54, 2), round(L["H"] / A.PPI * 2.54, 2)],
                         ppi=round(m_["w"] * (r_ - l_) / (L["W"] / A.PPI)), dim=[m_["w"], m_["h"]], uses=sum(1 for x in SP for pg_ in x for y in pg_[1] if y["k"] != "t" and y["i"] == it["i"]))
                n = A.name(it["i"]); e.update(name=n, bw=bool(it.get("bw")), z=it.get("z", 1.0), a=it.get("a") or 0, ar=A.M[it["i"]]["ar"],
                                              ev=A.ev_for(it["i"]), evp=CFG["esposizione"]["per_foto"].get(n, 0.0), tono=CFG["tono"].get(n), rit=CFG["ritocco"].get(n), bd=it.get("bd"), sh=it.get("sh") or 0, oc=it.get("oc", 100), face=list(A._faces_center(it["i"]) or []))
            out.append(e)
    return dict(h=spread_hash(s), guides=GD[s], L=SP[s][0][0], R=SP[s][1][0], items=out, grid=dict(L=dict(page_grid("L", SP[s][0][0]), full=page_grid("L", "I")), R=dict(page_grid("R", SP[s][1][0]), full=page_grid("R", "I"))))

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
        far = [f["w"] / f["h"] for f in fr]; mis = [[abs(math.log(far[j] / A.M[photos[q]]["ar"])) for q in range(N)] for j in range(N)]
        dp = {0: (0.0, [])}                      # abbinamento ottimo foto-cornici (programmazione dinamica sulle foto già usate)
        if N > 9:                                 # tantissime foto: abbinamento veloce (la cornice più grande sceglie per prima)
            left = list(range(N)); asg = [None] * N; cost = 0.0
            for j in sorted(range(N), key=lambda j: -fr[j]["w"] * fr[j]["h"]):
                c, p = min((mis[j][q] + 0.02 * abs(q - j), q) for q in left); asg[j] = p; left.remove(p); cost += c
            dp = {(1 << N) - 1: (cost, asg)}
        for j in range(N if N <= 9 else 0):
            nx = {}
            for mask, (c0, ch) in dp.items():
                for q in range(N):
                    if mask >> q & 1: continue
                    c1 = c0 + mis[j][q] + 0.02 * abs(q - j); m1 = mask | 1 << q
                    if m1 not in nx or c1 < nx[m1][0]: nx[m1] = (c1, ch + [q])
            dp = nx
        cost, asg = dp[(1 << N) - 1]; worst = max((mis[j][asg[j]] for j in range(N)), default=0.0)
        for j, f in enumerate(fr): f["n"] = A.name(photos[asg[j]])
        okc = cur is not None and sorted((round(f["x"]), round(f["y"]), f["w"], f["h"]) for f in fr) == cur
        if side is not None: return dict(cost=round(cost, 3), worst=round(worst, 3), frames=fr, cur=okc, **{side: dict(mode=a[1], module=a[0], mirror=a[2], photos=[photos[q] for q in asg])})
        na = NPH_(a[0])
        return dict(cost=round(cost, 3), worst=round(worst, 3), frames=fr, cur=okc, L=dict(mode=a[1], module=a[0], mirror=a[2], photos=[photos[q] for q in asg[:na]]),
                    R=dict(mode=b[1], module=b[0], mirror=b[2], photos=[photos[q] for q in asg[na:]]))

    out = []
    if side is None:
        for a in LAYS:
            for b in LAYS:
                if NPH[a[0]] + NPH[b[0]] != N or (a[0] == "BLANK" and b[0] == "BLANK"): continue
                out.append(build(a, b))
        for a, b in COUPLED:
            if NPH[a[0]] + NPH[b[0]] == N: out.append(build(a, b))
        seen = set(); dd = []       # uno stesso schema ottenuto in due modi (modulo di pagina o modello d'autore) si mostra una volta sola
        for t in out:
            k = tuple(sorted((round(f["x"] / 40), round(f["y"] / 40), round(f["w"] / 40), round(f["h"] / 40)) for f in t["frames"]))
            if k in seen and not t["cur"]: continue
            seen.add(k); dd.append(t)
        out = dd
    else:
        for a in LAYS:
            if N and NPH[a[0]] == N and a[0] != "BLANK": out.append(build(a))
    out.sort(key=lambda t: (not t["cur"], t["cost"]))
    TOLL = 0.28       # oltre questa differenza di proporzioni (≈ 1/5 della foto tagliata) il modello non rispecchia le foto: si propone solo se non c'è di meglio
    buoni = [t for t in out if t["cur"] or t["worst"] <= TOLL]
    if not any(not t["cur"] for t in buoni): buoni = buoni + sorted((t for t in out if not t["cur"]), key=lambda t: (t["worst"], t["cost"]))[:3]       # nessuna alternativa rispetta le foto: solo i meno peggio
    piu = sorted((t for t in out if t not in buoni and t["worst"] <= 0.55), key=lambda t: (t["worst"], t["cost"]))       # modelli che tagliano di più le foto: si mostrano solo se li chiedi
    out = buoni
    ut = []
    for t in ut_load():
        if t["n"] != N or t.get("lato") != side: continue
        try:
            if side is None: d = build(("U:%s:L" % t["id"], t["pages"][0]["mode"], False), ("U:%s:R" % t["id"], t["pages"][1]["mode"], False))
            else: d = build(("U:%s:%s" % (t["id"], side), t["pages"][0 if side == "L" else 1]["mode"], False))
            d.update(id=t["id"], nome=t["nome"]); ut.append(d)
        except Exception as ex: LOG.append(f"modello «{t.get('nome')}» non applicabile: {ex}")
    return dict(items=out[:90], piu=piu, n=N, tot=len(out), utente=ut, lato=side)

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
COLORI = ("rosso", "arancio", "giallo", "verde", "azzurro", "viola", "rosa")
def photo_list():
    where = {}
    for k, sp in enumerate(SP):
        for pg in sp:
            for it in pg[1]:
                if it["k"] != "t": where.setdefault(it["i"], k)
    tolte = set(CFG.get("tolte", [])); col = CFG.get("colori", {})
    return [dict(n=A.name(i), ar=A.M[i]["ar"], dt=A.M[i]["dt"][:19], sp=where.get(i), tolta=A.name(i) in tolte, col=col.get(A.name(i)), rit=CFG.get("ritocco", {}).get(A.name(i)), star=A.name(i) in CFG["stelle"]) for i in range(len(A.M))]

def foto_mancanti(): return [m["n"] for m in A.M if not os.path.exists(m.get("src", ""))]

def state():
    with LOCK:
        return dict(nome=CFG.get("nome", os.path.basename(PROJ)), W=VW, H=VH, testo=CFG['testo'], stili=CFG['stili'], fold=A.FOLD - BL, dirty=snap() != SAVED, saveerr=SAVE_ERR[0], rev=REV, canundo=bool(UNDO), canredo=bool(REDO),
                    globale=CFG["esposizione"].get("globale", 0.0), spreads=[spread_view(s) for s in range(len(SP))],
                    photos=photo_list(), tono_escl=list(CFG["tono_escl"]), tono_L=_tono_L0(), tono_Z=_tono_Z(), home=ARGS.home, boot=BOOT, unused=unused(), tolte=CFG.get("tolte", []),
                    modules={k: v for k, v in NPH.items()}, gap=A.G, ppi=A.PPI, mancanti=foto_mancanti(), agg=dict(AGG), ver=_ver_programma())

TONO_C = {}; TONO_IM = {}
TONO_L0 = 52.0                                                       # riferimento standard: L* medio (grigio al 18% = L* 50; ritratti e bambini leggermente sopra)
TONO_Z0 = 12.0                                                       # zona giusta attorno al riferimento (L*): ±12 (nel tuo album mezza foto su due sta tra L* 46 e 59); oltre +6 da correggere
TONO_HZ = (82.0, 97.0)                                               # zona giusta delle alte luci (95° percentile, L*): sotto 82 piatte, sopra 97 bruciate
TONO_SZ = (26.0, 34.0)                                               # ombre (5° percentile, L*): fino a 26 ok (scelta di Stefano), oltre «milky»
TONO_MAX = 1.0                                                       # correzione di esposizione al massimo ±1 EV per volta
def _tono_L0(): return float(CFG.get("tono_L", TONO_L0))
def _tono_Z(): return float(CFG.get("tono_Z", TONO_Z0))
def _tono_img(L):
    """la foto in piccolo (112 px), inquadrata nella cornice ma SENZA lo zoom (Scala): serve a provare le correzioni senza rifare le anteprime, e il tono non cambia se la ingrandisci"""
    i = L["i"]; l, t, r, b = A.crop(i, L["W"], L["H"], 1.0); key = (i, round(l, 4), round(t, 4), round(r, 4), round(b, 4), PV.get(A.name(i), 0))
    if key not in TONO_IM:
        if len(TONO_IM) > 400: TONO_IM.clear()
        im = Image.open(os.path.join(A.THUMBS, A.M[i]["n"])).convert("RGB"); W, H = im.size; bw_, bh_ = max(1.0, (r - l) * W), max(1.0, (b - t) * H)
        sm = im.resize((112, max(16, round(112 * bh_ / bw_))), Image.LANCZOS, box=(l * W, t * H, r * W, b * H)); import numpy as np
        a = np.asarray(sm); w, h = sm.size; x0, x1, y0, y1 = 0, w, 0, h                  # bordo bianco (o nero) della foto stessa: non fa parte del tono
        for edge in range(4):
            for _ in range(int(0.3 * (h if edge < 2 else w))):
                ln = (a[y0, x0:x1] if edge == 0 else a[y1 - 1, x0:x1] if edge == 1 else a[y0:y1, x0] if edge == 2 else a[y0:y1, x1 - 1]).astype(int)
                if not (ln.min() >= 235 or ln.max() <= 20): break
                if edge == 0: y0 += 1
                elif edge == 1: y1 -= 1
                elif edge == 2: x0 += 1
                else: x1 -= 1
        TONO_IM[key] = sm.crop((x0, y0, x1, y1)) if x1 - x0 >= 24 and y1 - y0 >= 16 else sm
    return TONO_IM[key]
def _tono_sim(i, im, evp, rit, bw=False):
    """la foto com'è con esposizione evp e ritocchi rit (stessa pipeline dell'anteprima e del PSD), come mappa di L* (CIE Lab, sRGB)"""
    import numpy as np
    n = A.name(i); R = CFG["ritocco"]; old = R.get(n); eo = A.ev_for(i) - CFG["esposizione"]["per_foto"].get(n, 0.0) + evp
    FL._CUR[0] = i
    try:
        if rit: R[n] = dict(rit)
        else: R.pop(n, None)
        out = A.apply_ev(im, eo, A.WB.get(n))
    finally:
        if old is None: R.pop(n, None)
        else: R[n] = old
    if bw: out = ImageOps.grayscale(out)                                     # in bianco e nero conta la luminosità del grigio, come nell'anteprima
    c = np.asarray(out.convert("RGB"), dtype=np.float32) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4); Y = lin[..., 0] * .2126 + lin[..., 1] * .7152 + lin[..., 2] * .0722
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)
def _tono_pesi(im):
    """peso di ogni pixel nella luce media: il centro conta di più dei bordi, la pelle il doppio (in un ritratto conta il viso, non lo sfondo)"""
    import numpy as np
    a = np.asarray(im.convert("YCbCr"), dtype=np.float32); h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]; r2 = ((xx + .5) / w - .5) ** 2 + ((yy + .5) / h - .5) ** 2
    W = 0.4 + 0.6 * np.exp(-r2 / (2 * 0.3 ** 2))
    skin = (a[..., 1] >= 77) & (a[..., 1] <= 127) & (a[..., 2] >= 135) & (a[..., 2] <= 173) & (a[..., 0] >= 50)
    return W * np.where(skin, 2.0, 1.0)
def _tono_stat(Lm, W=None):
    import numpy as np
    p = np.percentile(Lm, (5, 95)); M = float(Lm.mean()) if W is None or W.shape != Lm.shape else float((Lm * W).sum() / W.sum())
    return dict(M=M, H=float(p[1]), S=float(p[0]), B=float((Lm > 96).mean()), U=float(Lm.mean()))
def _tono_st(m, e, rit): return _tono_stat(_tono_sim(m["i"], m["im"], e, rit, m["bw"]), m["w"])
def _tono_scena(st):
    """scena chiara o scura di proposito (abito bianco, luce alta; interno con luci accese): il tono medio è lontano dallo standard ma la foto è giusta"""
    if st["U"] > _tono_L0() + 4 and st["H"] >= 88 and st["S"] >= 26 and st["B"] < 0.04: return "hk"
    if st["U"] < _tono_L0() - 6 and st["H"] >= 78 and st["S"] <= 12: return "lk"
    return None
def _tono_misure(s):
    key = spread_hash(s)
    if key in TONO_C: return TONO_C[key]
    lay = sorted(A.layout(spread_tuple(s)), key=lambda L: L.get("_o", 0)); out = []; k = 0
    for side, pg in zip("LR", SP[s]):
        for idx, it in enumerate(pg[1]):
            L = lay[k]; k += 1
            if it["k"] == "t": continue
            n = A.name(it["i"]); evp = CFG["esposizione"]["per_foto"].get(n, 0.0); rit = dict(CFG["ritocco"].get(n) or {}); im = _tono_img(L)
            bw = bool(it.get("bw")); w = _tono_pesi(im); st = _tono_stat(_tono_sim(it["i"], im, evp, rit, bw), w); sc = _tono_scena(st)
            out.append(dict(side=side, idx=idx, name=n, i=it["i"], im=im, w=w, evp=evp, rit=rit, bw=bw, st=st, sc=sc, ze=_tono_Z() * (1.5 if sc else 1.0)))
    if len(TONO_C) > 600: TONO_C.clear()
    TONO_C[key] = out; return out

def _tono_stato(d, z, g): return "ok" if abs(d) <= z else "att" if abs(d) <= g else "no"
def _tono_fuori(v, lo, hi): return max(0.0, lo - v, v - hi)                 # quanto un valore esce dalla zona [lo, hi]

def _tono_solo_ev(m):
    """Semplice: la correzione più piccola di esposizione (±1 EV al massimo) che riporta la luce media dentro la zona giusta, senza bruciare altre luci"""
    st0 = m["st"]; L0 = _tono_L0(); zin = max(0.0, m["ze"] - 3); best = (max(0.0, abs(st0["M"] - L0) - zin), 0.0); q = 0.0
    for sgn in (1, -1):
        v = sgn * 0.05
        while abs(v) <= TONO_MAX + 1e-9:
            e = min(max(m["evp"] + v, -2.0), 2.0); st = _tono_st(m, e, m["rit"])
            j = max(0.0, abs(st["M"] - L0) - zin) + 100 * max(0.0, st["B"] - st0["B"] - 0.02)
            if j < best[0] - 1e-9: best = (j, round(v, 2))
            v += sgn * 0.05
    return round(min(max(m["evp"] + best[1], -2.0), 2.0) * 20) / 20

def _tono_ottimizza(m):
    """Completa: prova esposizione, alteluci, ombre e bianchi e sceglie i valori che portano luce media, alte luci e ombre nelle zone giuste (tetti prudenti, penalità sulle correzioni grandi, mai più luci bruciate)"""
    st0 = m["st"]; L0 = _tono_L0(); base = m["rit"]; zin = max(0.0, m["ze"] - 3)
    lim = dict(ev=(-TONO_MAX, TONO_MAX, .05), alt=(-20, 20, 5), omb=(-20, 20, 5), bia=(-15, 15, 5)); p = dict(ev=0.0, alt=0, omb=0, bia=0)
    def rit_of(q):
        r = dict(base)
        for k in ("alt", "omb", "bia"):
            v = round(min(max(base.get(k, 0) + q[k], -100), 100))
            if v: r[k] = v
            else: r.pop(k, None)
        return r
    def J(q):
        e = min(max(m["evp"] + q["ev"], -2.0), 2.0); st = _tono_st(m, e, rit_of(q))
        dm = max(0.0, abs(st["M"] - L0) - zin) / 8; dh = _tono_fuori(st["H"], *TONO_HZ) / 10; ds = _tono_fuori(st["S"], 0, TONO_SZ[0]) / 10
        j = 3 * dm * dm + dh * dh + .5 * ds * ds + 0.05 * (q["ev"] ** 2 + (q["alt"] / 20) ** 2 + (q["omb"] / 20) ** 2 + (q["bia"] / 15) ** 2)
        return j + 4000 * max(0.0, st["B"] - st0["B"] - 0.02) ** 2, st
    best, _ = J(p)
    for _ in range(3):
        for k in ("ev", "alt", "omb", "bia"):
            lo, hi, step = lim[k]; v = lo
            while v <= hi + 1e-9:
                q = dict(p, **{k: round(v, 2)}); j, _s = J(q)
                if j < best - 1e-9: best, p = j, q
                v += step
    j, st = J(p); e = round(min(max(m["evp"] + p["ev"], -2.0), 2.0) * 20) / 20
    return dict(ev=e, rit={k: round(min(max(base.get(k, 0) + p[k], -100), 100)) for k in ("alt", "omb", "bia") if p[k]}, dopo=st, bruc=bool(st["B"] > st0["B"] + 0.02))

def tono_spread(s, over=None, light=False):
    """misura il tono delle foto dello spread s rispetto a un riferimento STANDARD (L* medio, uguale per tutto l'album) e propone le correzioni:
    solo esposizione («semplice») o anche alteluci/ombre/bianchi («completa»). over = {foto: {ev, rit}}: valori di prova (cursore in movimento)"""
    with LOCK:
        ms = _tono_misure(s); items = []; pen = []; L0 = _tono_L0()
        if over: ms = [dict(m, evp=over[m["name"]].get("ev", m["evp"]), rit=over[m["name"]].get("rit", m["rit"]), st=_tono_st(m, over[m["name"]].get("ev", m["evp"]), over[m["name"]].get("rit", m["rit"]))) if m["name"] in over else m for m in ms]
        if not ms: return dict(s=s, items=[], score=100, prev=None, next=None, rif=L0)
        for j, m in enumerate(ms):
            st = m["st"]; esc = m["name"] in CFG["tono_escl"]; d = st["M"] - L0
            ze = m["ze"]; stato = "escl" if esc else _tono_stato(d, ze, ze + 6)
            fh = _tono_fuori(st["H"], *TONO_HZ); sh = "ok" if fh == 0 else "att" if fh <= 8 else "no"; ss = "ok" if st["S"] <= TONO_SZ[0] else "att" if st["S"] <= TONO_SZ[1] else "no"
            sc_ = "escl" if esc else max((stato, "att" if sh != "ok" else "ok"), key=("ok", "att", "no").index)    # le alte luci fuori zona al massimo «da guardare»; le ombre solo informative
            e = dict(side=m["side"], idx=m["idx"], name=m["name"], n=j + 1, d=round(d, 1), H=round(st["H"], 1), S=round(st["S"], 1), B=round(st["B"] * 100, 1), sh=sh, ss=ss, stato=stato, stato_c=sc_, scena=m["sc"], ze=round(ze, 1), evp=m["evp"], rit0={k: m["rit"][k] for k in ("alt", "omb", "bia") if k in m["rit"]})
            if not esc and stato != "ok" and not over and not light:
                ck = (spread_hash(s), m["name"], L0, _tono_Z(), tuple(CFG["tono_escl"]))
                if ck not in TONO_C: TONO_C[ck] = (_tono_solo_ev(m), _tono_ottimizza(m))
                ev1, c = TONO_C[ck]; e["nuova"] = ev1; e["compl"] = dict(ev=c["ev"], rit=c["rit"], bruc=c["bruc"], d=round(c["dopo"]["M"] - L0, 1))
                e["bruc"] = bool(ev1 > m["evp"] and _tono_st(m, ev1, m["rit"])["B"] > st["B"] + 0.02)
            if not esc: pen.append(min(max(0.0, abs(d) - ze) / 12, 1.0))
            items.append(e)
        def vic(t):
            if not (0 <= t < len(SP)): return None
            mm = [m["st"]["M"] for m in _tono_misure(t) if m["name"] not in CFG["tono_escl"]]
            if not mm: return None
            import statistics
            return round(statistics.median(mm) - statistics.median([m["st"]["M"] for m in ms if m["name"] not in CFG["tono_escl"]] or [L0]), 1)
        return dict(s=s, items=items, score=round(100 * (1 - sum(pen) / len(pen))) if pen else 100, prev=vic(s - 1), next=vic(s + 1), rif=L0, zona=_tono_Z(), giallo=_tono_Z() + 6, hz=TONO_HZ, sz=TONO_SZ)

def tono_all():
    """vista d'insieme: per ogni spread punteggio e stato di ogni foto (senza calcolare le correzioni)"""
    out = []
    for s in range(len(SP)):
        d = tono_spread(s, light=True)
        out.append(dict(s=s, score=d["score"], n=len(d["items"]), a=[x["stato"] for x in d["items"]], c=[x["stato_c"] for x in d["items"]], sc=[x["scena"] for x in d["items"]]))
    return out

def bruc_img(s, side, idx):
    """la foto (la parte visibile, in piccolo) con i bianchi bruciati (L* oltre 96) in rosso: serve a vedere DOVE sono; con le correzioni attuali"""
    import io as _io, numpy as np
    with LOCK:
        m = next((x for x in _tono_misure(s) if x["side"] == side and x["idx"] == idx), None)
        if m is None: raise ValueError("foto non trovata")
        Lm = _tono_sim(m["i"], m["im"], m["evp"], m["rit"], m["bw"]); base = np.asarray(m["im"].convert("L"), dtype=np.float32)
    if base.shape != Lm.shape: base = np.asarray(m["im"].convert("L").resize((Lm.shape[1], Lm.shape[0])), dtype=np.float32)
    rgb = np.stack([base * .45] * 3, axis=-1); msk = (Lm > 96)[..., None]
    out = np.where(msk, np.array([255, 69, 58], dtype=np.float32), rgb).astype(np.uint8)
    im = Image.fromarray(out); im = im.resize((im.width * 3, im.height * 3), Image.NEAREST); b = _io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

def live_photo(q):
    """la foto della cornice (side, idx) dello spread s, in piccolo, con valori di prova al posto di quelli salvati (cursori in movimento): stessa pipeline dell'anteprima"""
    import io as _io
    s = int(q["s"]); side, idx, K = q["side"], int(q["idx"]), min(max(float(q.get("k", "0.3")), 0.05), 0.8); over = json.loads(q.get("o", "{}"))
    with LOCK:
        lay = sorted(A.layout(spread_tuple(s)), key=lambda L: L.get("_o", 0)); k = 0; L = it = None
        for sd, pg in zip("LR", SP[s]):
            for j, x in enumerate(pg[1]):
                if sd == side and j == idx: L, it = dict(lay[k]), x
                k += 1
        if L is None or it["k"] == "t": raise ValueError("cornice non trovata")
        n = A.name(it["i"]); R, E = CFG["ritocco"], CFG["esposizione"]["per_foto"]; old = (R.get(n), E.get(n))
        try:
            if "rit" in over:
                if over["rit"]: R[n] = {kk: float(v) for kk, v in over["rit"].items() if kk in FL.RIT_KEYS and abs(float(v)) >= 0.5}
                else: R.pop(n, None)
            if "ev" in over:
                if abs(float(over["ev"])) >= 0.005: E[n] = float(over["ev"])
                else: E.pop(n, None)
            if "a" in over: L["a"] = float(over["a"])
            if "bd" in over: L["bd"] = [float(over["bd"][0]), str(over["bd"][1])] if over["bd"] else None
            im = A._photo(L, K, True)
        finally:
            for D, v in ((R, old[0]), (E, old[1])):
                if v is None: D.pop(n, None)
                else: D[n] = v
        b = _io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=82); return b.getvalue()

def corr_thumb(n, w, over):
    """la foto intera (non ritagliata) con esposizione e ritocchi: serve al riquadro Design; over = valori di prova dei cursori"""
    i = A.IDX[n] - 1; R, E = CFG["ritocco"], CFG["esposizione"]["per_foto"]
    with LOCK:
        old = (R.get(n), E.get(n))
        try:
            if "rit" in over:
                if over["rit"]: R[n] = {k: float(v) for k, v in over["rit"].items() if k in FL.RIT_KEYS and abs(float(v)) >= 0.5}
                else: R.pop(n, None)
            if "ev" in over:
                if abs(float(over["ev"])) >= 0.005: E[n] = float(over["ev"])
                else: E.pop(n, None)
            im = Image.open(os.path.join(A.THUMBS, A.M[i]["n"])).convert("RGB"); im.thumbnail((w, w)); FL._CUR[0] = i
            im = A.apply_ev(im, A.ev_for(i), A.WB.get(n))
        finally:
            for D, v in ((R, old[0]), (E, old[1])):
                if v is None: D.pop(n, None)
                else: D[n] = v
    b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=82); return b.getvalue()

CACHE = {}
PV = {}                                              # versione di ogni foto: sale quando l'originale cambia (es. riesportata da Lightroom), così anteprime e cache si rifanno
AGG = dict(n=0, t=0, nomi=[], ar=[])               # ultimo aggiornamento automatico delle foto modificate
def spread_jpg(s, K, hide=None):
    """immagine dello spread; hide = (side, idx) di una cornice libera da NON disegnare (serve mentre la si trascina)"""
    with LOCK:
        key = (spread_hash(s), K, hide)
        if key in CACHE: return CACHE[key]
        tup = spread_tuple(s)
        if hide:
            pi = 0 if hide[0] == "L" else 1; its = SP[s][pi][1]
            if 0 <= hide[1] < len(its) and (its[hide[1]]["k"] == "f" or "fx" in its[hide[1]]):             # solo cornici libere: togliendo una cella del modello si sposterebbero le altre
                tup = tuple((pg[0], [it for j, it in enumerate(pg[1]) if not (n == pi and j == hide[1])]) for n, pg in enumerate(SP[s]))
        im = A.render(tup, K, True)
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
    if it["k"] != "t" and (it.get("bd") or it.get("sh") or it.get("oc", 100) < 100): x = f'STY({x}, bd={tuple(it["bd"]) if it.get("bd") else None!r}, sh={int(it.get("sh") or 0)}, oc={int(it.get("oc", 100))})'
    return f'ROT({x}, {it["a"]})' if it["k"] != "t" and it.get("a") else x
def fmt0(it):
    if is_txt(it):
        return ("TEXT(%r, %s, %s, %s, %s, font=%r, size=%s, col=%r, al=%r, tr=%s, auto=%s" % (it["tx"], it["fx"], it["fy"], it["fw"], it["fh"], it["font"], it["size"], tuple(it["col"]), it["al"], it["tr"], bool(it.get("auto", True)))) + (f', lh={TX.lead(it)}' if TX.lead(it) != 1.2 else "") + (", caps=True" if it.get("caps") else "") + (f', zo={it["zo"]}' if it.get("zo") is not None else "") + (f', stile={it["stile"]!r}' if it.get("stile") else "") + ")"
    if it["k"] == "t":
        if "fx" in it: return f'TXTF({it["kind"]!r}, {it["fx"]}, {it["fy"]}, {it["fw"]}, {it["fh"]}, ts={it.get("ts", 1.0)}' + (f', zo={it["zo"]}' if it.get("zo") is not None else "") + ")"
        return f'TXT({it["kind"]!r}, {it["c"]}, {it["r"]}, {it["w"]}, {it["h"]})'
    n = A.name(it["i"]); ex = (", bw=True" if it.get("bw") else "") + (f', z={it["z"]}' if it.get("z", 1.0) != 1.0 else "") + (f', zo={it["zo"]}' if it["k"] == "f" and it.get("zo") is not None else "")
    if it["k"] == "full": return f"FULL({n!r}{ex})"
    if it["k"] == "f": return f'FREE({n!r}, {it["x"]}, {it["y"]}, {it["w"]}, {it["h"]}{ex})'
    return f'P({n!r}, {it["c"]}, {it["r"]}, {it["w"]}, {it["h"]}{ex})'

LAST = dict(op=0.0, backup=0.0)
SAVE_ERR = [""]                                       # ultimo errore di salvataggio (vuoto = tutto a posto): lo mostra la barra in alto

def _scrivi(path, testo):
    """scrive il file in modo sicuro: prima in un file temporaneo, poi lo sostituisce, così un blocco a metà non lo rovina"""
    tmp = path + ".tmp"
    with open(tmp, "w") as f: f.write(testo); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def _pota_backup(bk, tieni=200):
    """tiene le ultime `tieni` copie di sicurezza e toglie le più vecchie"""
    try:
        ts = sorted({f.split("_", 1)[0] for f in os.listdir(bk) if re.match(r"^\d{8}-\d{6}_(spec\.py|progetto\.json)$", f)})
        for t in ts[:-tieni]:
            for f in ("spec.py", "progetto.json"):
                try: os.remove(os.path.join(bk, f"{t}_{f}"))
                except OSError: pass
    except Exception as e: LOG.append(f"pulizia copie non riuscita: {e}")
def save(backup=True):
    global SAVED
    with LOCK:
        ts = time.strftime("%Y%m%d-%H%M%S"); bk = os.path.join(PROJ, "_backup_editor"); os.makedirs(bk, exist_ok=True)
        if backup:
            LAST["backup"] = time.time()
            for f in ("spec.py", "progetto.json"):
                p = os.path.join(PROJ, f)
                if os.path.exists(p): shutil.copy2(p, os.path.join(bk, f"{ts}_{f}"))
        has_free = any(it["k"] == "f" or it.get("a") or it.get("bd") or it.get("sh") or it.get("oc", 100) < 100 or "fx" in it for sp in SP for pg in sp for it in pg[1])
        if has_free: shutil.copy2(os.path.join(HERE, "album_libere.py"), os.path.join(PROJ, "album_libere.py")); shutil.copy2(os.path.join(HERE, "testo.py"), os.path.join(PROJ, "testo.py")); shutil.copy2(os.path.join(HERE, "vib_lut.npz"), os.path.join(PROJ, "vib_lut.npz"))
        lines = [f'"""{CFG.get("nome", "Album")}: {len(SP)} spread. Salvato dall\'editor il {time.strftime("%d/%m/%Y %H:%M")}."""', "from album import *"]
        if has_free: lines.append("from album_libere import *     # cornici libere FREE(...) e angoli ROT(...): serve questo file, sta nella cartella del progetto")
        lines += ["", "SPREADS = ["]
        for k, sp in enumerate(SP, 1):
            pages = [f'{pg[0]}(' + ", ".join(fmt(it) for it in pg[1]) + ")" for pg in sp]
            lines.append(f"    # {k}\n    ({pages[0]},\n     {pages[1]}),")
        lines.append("]")
        _scrivi(os.path.join(PROJ, "spec.py"), "\n".join(lines) + "\n")
        out = {k: v for k, v in json.load(open(os.path.join(PROJ, "progetto.json"))).items()}
        out["esposizione"] = CFG["esposizione"]; out["centri_volto"] = CFG["centri_volto"]; out["tono"] = CFG["tono"]; out["tolte"] = CFG["tolte"]; out["colori"] = CFG["colori"]; out["ritocco"] = CFG["ritocco"]; out["stelle"] = CFG["stelle"]; out["tono_escl"] = CFG["tono_escl"]; out["testo"] = CFG["testo"]; out["stili"] = CFG["stili"]; out["foto_extra"] = CFG.get("foto_extra", [])
        out.pop("tono_rif", None)
        for k_ in ("tono_L", "tono_Z"):
            if k_ in CFG: out[k_] = CFG[k_]
            else: out.pop(k_, None)
        if CFG.get("uscita_psd"): out["uscita_psd"] = CFG["uscita_psd"]
        if any(g["v"] or g["h"] for g in GD): out["guide"] = GD
        else: out.pop("guide", None)
        _scrivi(os.path.join(PROJ, "progetto.json"), json.dumps(out, indent=2, ensure_ascii=False))
        SAVED = snap(); SAVE_ERR[0] = ""
        if backup: _pota_backup(bk)
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

def _spiega(e):
    """errore tecnico -> frase che si capisce"""
    import errno
    if isinstance(e, PermissionError): return f"non posso scrivere nella cartella di destinazione ({e.filename or ''}): scegline un'altra"
    if isinstance(e, OSError) and e.errno == errno.ENOSPC: return "il disco è pieno: libera spazio o scegli un altro disco"
    if isinstance(e, FileNotFoundError): return f"file non trovato: {e.filename or e}"
    if isinstance(e, MemoryError): return "memoria insufficiente: prova a esportare meno spread alla volta"
    return f"{type(e).__name__}: {e}"

def _scrivi_img(im, f, **kw):
    """salva l'immagine in un file temporaneo e poi la sposta: se l'export si interrompe non resta un file a metà né si perde quello vecchio"""
    tmp = f + ".tmp"; im.save(tmp, "JPEG", **kw); os.replace(tmp, f)

def preflight(o, nums, dest, fmt):
    """controlli prima di esportare: se qualcosa non va l'utente lo sa subito, non dopo minuti di lavoro"""
    n = len(SP)
    if n == 0: raise ValueError("Non c'è nessuno spread da esportare")
    if not nums: raise ValueError("Nessuno spread nell'intervallo scelto")
    fuori = [k for k in nums if not 1 <= k <= n]
    if fuori: raise ValueError(f"Lo spread {fuori[0]} non esiste: gli spread sono {n}")
    usati = {it["i"] for k in nums for pg in SP[k - 1] for it in pg[1] if it.get("k") != "t" and "i" in it}
    manca = [m["n"] for ix, m in enumerate(A.M) if ix in usati and not os.path.exists(m.get("src", ""))]
    if manca: raise ValueError(f"{len(manca)} foto di questi spread non si trovano più ({', '.join(manca[:4])}{'…' if len(manca) > 4 else ''}): ricollegale da Progetto → Ricollega foto")
    try:
        t = os.path.join(dest, ".prova_scrittura"); open(t, "w").write("x"); os.remove(t)
    except OSError as e: raise ValueError(f"Non posso scrivere in «{dest}»: {e.strerror or e}. Scegli un'altra cartella")
    stima = {"jpg": 35e6 * len(nums), "pdf": 8e6 + 2e6 * len(nums), "psd": 450e6 * len(nums)}[fmt]
    libero = shutil.disk_usage(dest).free
    if libero < stima * 1.2: raise ValueError(f"Spazio insufficiente: servono circa {stima / 1e9:.1f} GB e ne restano {libero / 1e9:.1f} GB. Libera spazio o scegli un altro disco")
    if fmt == "psd":
        try: sys.path.insert(0, SCRIPTS); import photoshop as _ps; _ps.app_name()
        except SystemExit: raise ValueError("Photoshop non è stato trovato in /Applications: serve per creare i PSD (JPG e PDF funzionano anche senza)")

def run_export(o):
    """un solo punto per esportare: JPG (un file per spread), PDF (bozza per il cliente) o PSD (Photoshop)"""
    with LOCK: n = len(SP)
    nums = parse_range(o.get("range", ""), n); fmt = o["fmt"]
    dflt = (CFG.get("uscita_psd") or os.path.join(PROJ, "PSD")) if fmt == "psd" else os.path.join(PROJ, "Esportazioni", fmt.upper())
    dest = os.path.expanduser(o.get("dest") or dflt)
    if fmt not in ("jpg", "pdf", "psd"): raise ValueError(f"Formato sconosciuto: {fmt}")
    try: os.makedirs(dest, exist_ok=True)
    except OSError as e: raise ValueError(f"Non riesco a creare la cartella «{dest}»: {e.strerror or e}")
    preflight(o, nums, dest, fmt)
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
                fatti = []
                for k in nums:
                    try:
                        with LOCK: tup = spread_tuple(k - 1)
                        im = A.render(tup, K, True); b = round(A.B * K)
                        if b: im = im.crop((b, b, im.width - b, im.height - b))
                        f = os.path.join(dest, f"{nome} - Spread {k:02d}.jpg"); _scrivi_img(im, f, quality=q, dpi=(A.PPI * K, A.PPI * K), icc_profile=icc, subsampling=0 if q >= 90 else 2)
                        if os.path.getsize(f) < 1000: raise ValueError("file vuoto")
                        fatti.append(k); LOG.append(f"  spread {k}: {os.path.basename(f)}")
                    except Exception as ex: LOG.append(f"SALTATO spread {k} -> {_spiega(ex)}")
                LOG.append(f"ESPORTATI {len(fatti)} spread su {len(nums)}")
                if fatti: LOG.append("RISULTATO:" + dest)
                if len(fatti) < len(nums): LOG.append(f"ERRORE: {len(nums) - len(fatti)} spread non esportati (vedi sopra)")
            elif fmt == "pdf":
                from PIL import ImageDraw, ImageFont
                Wp = int(o.get("width", 2000)); K = Wp / VW; pages = []
                try: font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", max(14, Wp // 80))
                except Exception: font = ImageFont.load_default()
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
                write_pdf(f + ".tmp", jp, 150); os.replace(f + ".tmp", f)
                if os.path.getsize(f) < 1000: raise ValueError("il PDF risulta vuoto")
                LOG.append(f"{len(pages)} pagine, {os.path.getsize(f) / 1e6:.1f} MB"); LOG.append("RISULTATO:" + f)
            else:
                cmd = [sys.executable, os.path.join(HERE, "genera_psd_angolo.py"), "--spread", ",".join(map(str, nums)), "--progetto", PROJ] + (["--forza"] if o.get("force") else [])
                p = subprocess.Popen(cmd, cwd=SCRIPTS, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(os.environ, ALBUM_PROGETTO=PROJ, ALBUM_SCRIPTS=SCRIPTS))
                t0 = time.time() - 2; out = []
                for line in p.stdout: out.append(line.rstrip()); LOG.append(line.rstrip())
                rc = p.wait(); testo = "\n".join(out)
                skip = {int(m) for m in re.findall(r"SALTATO spread (\d+)", testo)}
                nuovi = [k for k in nums if k not in skip and not (os.path.exists(os.path.join(dest, f"Spread_{k:02d}.psd")) and os.path.getmtime(os.path.join(dest, f"Spread_{k:02d}.psd")) >= t0 and os.path.getsize(os.path.join(dest, f"Spread_{k:02d}.psd")) > 1e5)]
                for k in nuovi: LOG.append(f"SALTATO spread {k} -> il PSD non è stato creato")
                if re.search(r"errore generale|general error|8800|Photoshop got an error|not running|isn.t running", testo, re.I): LOG.append("ERRORE: Photoshop ha dato un errore. Controlla che sia aperto, senza finestre di dialogo in attesa, e riprova")
                elif rc != 0 and not nuovi: LOG.append(f"ERRORE: lo script dei PSD si è fermato (codice {rc}): vedi sopra")
                LOG.append(f"PSD creati: {len(nums) - len(skip) - len(nuovi)} su {len(nums)}" + (f" ({len(skip)} lasciati com'erano perché modificati a mano)" if skip else ""))
                if len(nums) - len(nuovi) > 0 or skip: LOG.append("RISULTATO:" + dest)
        except Exception as e: LOG.append(f"ERRORE: {_spiega(e)}")
        LOG.append("[finito]")
    threading.Thread(target=go, daemon=True).start()
    return len(nums)

def autosave_loop():
    """salva da solo 2 secondi dopo l'ultima modifica; copia di sicurezza al massimo ogni 10 minuti"""
    while True:
        time.sleep(1)
        try:
            if time.time() - LAST["op"] > 2 and snap() != SAVED: save(backup=time.time() - LAST["backup"] > 600)
        except Exception as e: LOG.append(f"autosalvataggio non riuscito: {e}"); SAVE_ERR[0] = str(e)[:160]

def pick(kind):
    if kind == "folder": sc = 'POSIX path of (choose folder with prompt "Scegli la cartella")'
    else: sc = ('set fs to choose file with prompt "Scegli le foto" of type {"public.jpeg"} with multiple selections allowed\nset out to ""\n'
                'repeat with f in fs\nset out to out & POSIX path of f & linefeed\nend repeat\nreturn out')
    r = subprocess.run(["osascript", "-e", sc], capture_output=True, text=True)
    return [x for x in r.stdout.split("\n") if x.strip()] if r.returncode == 0 else []

LASTDIR = [None]
def ls_dir(path):
    """elenco di una cartella per il selettore di foto del programma (solo sottocartelle e JPEG)"""
    home = os.path.expanduser("~")
    path = os.path.abspath(os.path.expanduser(path or LASTDIR[0] or os.path.dirname(CFG.get("foto", "")) or home + "/Desktop"))
    if not os.path.isdir(path): path = home
    LASTDIR[0] = path; dirs, files = [], []
    for n in sorted(os.listdir(path), key=str.lower):
        if n.startswith("."): continue
        p = os.path.join(path, n)
        try:
            if os.path.isdir(p): dirs.append(n)
            elif n.lower().endswith((".jpg", ".jpeg")): files.append(dict(n=n, s=os.path.getsize(p)))
        except OSError: pass
    places = [dict(n=n, p=p) for n, p in (("Scrivania", home + "/Desktop"), ("Documenti", home + "/Documents"), ("Immagini", home + "/Pictures"), ("Download", home + "/Downloads"), ("Home", home)) if os.path.isdir(p)]
    try: places += [dict(n=v, p="/Volumes/" + v) for v in sorted(os.listdir("/Volumes")) if not v.startswith(".") and os.path.isdir("/Volumes/" + v) and not os.path.islink("/Volumes/" + v)]
    except OSError: pass
    return dict(path=path, parent=os.path.dirname(path) if path != "/" else None, dirs=dirs, files=files, places=places)

FT = {}
def file_thumb(path, w):
    path = os.path.abspath(path)
    if not path.lower().endswith((".jpg", ".jpeg")) or not os.path.isfile(path): raise ValueError("non è una foto JPEG")
    k = (path, w, os.path.getmtime(path))
    if k not in FT:
        from PIL import Image, ImageOps
        im = Image.open(path); im.draft("RGB", (w * 2, w * 2)); im = ImageOps.exif_transpose(im).convert("RGB"); im.thumbnail((w, w))
        b = io.BytesIO(); im.save(b, "JPEG", quality=80)
        if len(FT) > 600: FT.clear()
        FT[k] = b.getvalue()
    return FT[k]

def do_import(paths):
    """aggiunge le foto al progetto SENZA copiarle: il progetto punta ai file originali (foto_extra)"""
    files = []
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                files += [os.path.join(root, f) for f in sorted(fs)]
        else: files.append(p)
    fd = CFG.get("foto", ""); have = {f.lower() for f in os.listdir(fd)} if os.path.isdir(fd) else set()
    have |= {os.path.basename(x).lower() for x in CFG.get("foto_extra", [])}
    n = skipped = 0; new = []
    for f in files:
        base, ext = os.path.splitext(os.path.basename(f))
        if ext.lower() not in (".jpg", ".jpeg") or base.startswith("."): skipped += 1; continue
        if os.path.basename(f).lower() in have: skipped += 1; continue
        have.add(os.path.basename(f).lower()); n += 1; new.append(os.path.abspath(f))
    if new:
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
            for f in ("spec.py", "album_libere.py", "testo.py", "vib_lut.npz"):
                src = os.path.join(PROJ, f) if f == "spec.py" and os.path.exists(os.path.join(PROJ, f)) else os.path.join(HERE, f)       # i file del programma si prendono sempre dalla versione attuale (una copia vecchia nel progetto darebbe un PSD diverso dall'anteprima)
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
            elif u.path == "/api/tono_all": self.send(tono_all())
            elif u.path == "/api/tono": self.send(tono_spread(int(q.get("s", ["0"])[0]), json.loads(q["o"][0]) if q.get("o") else None))
            elif u.path == "/img/corr": self.send(corr_thumb(q["n"][0], min(int(q.get("w", ["500"])[0]), 1200), json.loads(q["o"][0]) if q.get("o") else {}), "image/jpeg")
            elif u.path == "/img/bruc": self.send(bruc_img(int(q["s"][0]), q["side"][0], int(q["idx"][0])), "image/png")
            elif u.path == "/img/live": self.send(live_photo({k: v[0] for k, v in q.items()}), "image/jpeg")
            elif u.path == "/api/templates": self.send(templates(int(q.get("s", ["0"])[0])))
            elif u.path.startswith("/api/info/"): self.send(photo_info(u.path.rsplit("/", 1)[1]))
            elif u.path == "/api/fonts": self.send(dict(fonts=[dict(fam=f["fam"], sty=f["sty"], ps=f["ps"]) for f in TX.fonts()]))
            elif u.path == "/api/ping": self.send({"boot": BOOT, "agg": AGG["n"], "path": os.path.abspath(ARGS.progetto)})
            elif u.path == "/api/log": self.send(LOG[-200:])
            elif u.path == "/api/ls": self.send(ls_dir(q.get("p", [""])[0]))
            elif u.path == "/api/fthumb": self.send(file_thumb(q["p"][0], min(int(q.get("w", ["200"])[0]), 600)), "image/jpeg")
            elif u.path == "/api/versioni": self.send(versioni())
            elif u.path.startswith("/img/spread/"): self.send(spread_jpg(int(u.path.rsplit("/", 1)[1]), float(q.get("k", ["0.2"])[0]), ((q["hide"][0][0], int(q["hide"][0][2:])) if q.get("hide") else None)), "image/jpeg")
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
            elif u.path == "/api/reveal": subprocess.run(["open", "-R", body["path"] if "path" in body else A.M[A.IDX[body["foto"]] - 1]["src"]]); self.send({"ok": True})
            else: self.send({"errore": "non trovato"}, code=404)
        except Exception as e: self.send({"errore": str(e)}, code=400)

if __name__ == "__main__":
    threading.Thread(target=autosave_loop, daemon=True).start(); threading.Thread(target=foto_watch_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.porta), H)
    print(f"Editor album: http://127.0.0.1:{ARGS.porta}  | progetto: {PROJ}  | script: {SCRIPTS}", flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
