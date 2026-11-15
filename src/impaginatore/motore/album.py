"""Motore di impaginazione album (stile Stefano).

Uso: ogni album ha una cartella di progetto con `progetto.json` e `album.json` (le 1.x avevano `spec.py`).
Il progetto si carica in modo esplicito con carica_progetto(cartella); gli script da riga di comando trovano la cartella con
--progetto <cartella>, con la variabile ALBUM_PROGETTO o nella cartella corrente (progetto_da_argv).
L'impaginazione (SPREADS: lista di coppie pagina sinistra / destra, fatte con i costruttori qui sotto) la legge
formato.carica: dati JSON, mai codice eseguito.

Griglia: ogni pagina 12 colonne x 8 righe, un solo spazio tra le foto (default 2,5 mm) ovunque, anche sulla piega.
Pagine "I" immersive (la griglia arriva al bordo, look flush) e "W" bianche (margine uguale sui 4 lati, default 10 mm).
Nessuna foto attraversa la piega: ogni pagina si compone da sola.

Stato: un progetto per processo. carica_progetto riempie le variabili del modulo (CFG, M, CW, IDX...) che il resto del motore,
gli script e l'editor leggono; importare il modulo non legge niente dal disco.
"""
import os, sys, glob
from fractions import Fraction
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .. import formato as _formato
from .. import validazione as _V
from ..piattaforma import font as _pfont

# ---------------- progetto ----------------
PROJ = CFG = SRC = CACHE = THUMBS = None             # riempiti da carica_progetto()
CW = CH = PPI = B = G = MG = FOLD = TW = TH = None
M, F, IDX, ORIGINE, FACE_FIX, WB, _ESP, TXTCFG = [], {}, {}, {}, {}, {}, {}, {}
TITLE, INK = ("", "", ""), (58, 54, 51)
SERIF_FILE = SANS_FILE = None


def progetto_da_argv(argv=None):
    """cartella del progetto per gli script: --progetto <cartella> negli argomenti, poi ALBUM_PROGETTO, poi la cartella corrente"""
    argv = sys.argv if argv is None else argv
    for k, a in enumerate(argv):
        if a == "--progetto" and k + 1 < len(argv): return os.path.abspath(argv[k + 1])
    if os.environ.get("ALBUM_PROGETTO"): return os.path.abspath(os.environ["ALBUM_PROGETTO"])
    if os.path.exists("progetto.json"): return os.getcwd()
    raise SystemExit("Progetto non trovato: passa --progetto <cartella con progetto.json> o imposta ALBUM_PROGETTO")


def carica_progetto(cartella):
    """legge progetto.json, aggiorna l'elenco delle foto (metadati, miniature, volti) e prepara geometria, correzioni e testi.
    Restituisce il modulo stesso. Si può richiamare per passare a un altro progetto (un progetto alla volta per processo)."""
    global PROJ, CFG, SRC, CACHE, THUMBS, CW, CH, PPI, B, G, MG, FOLD, TW, TH, M, F, IDX, ORIGINE, FACE_FIX, _ESP, WB, TXTCFG, TITLE, INK, SERIF_FILE, SANS_FILE
    Image.MAX_IMAGE_PIXELS = None
    PROJ = os.path.abspath(cartella)
    CFG = _V.progetto(_leggi_json(os.path.join(PROJ, "progetto.json")))
    SRC = CFG["foto"]                                   # cartella con le foto scelte in alta risoluzione
    CACHE = os.path.join(PROJ, "_cache"); THUMBS = os.path.join(CACHE, "thumbs")
    os.makedirs(THUMBS, exist_ok=True)
    CW, CH, PPI, B, G, MG = _geometry()
    FOLD = CW / 2; TW, TH = CW - 2 * B, CH - 2 * B
    # ---- foto: metadati, miniature, volti
    mp, fp = os.path.join(CACHE, "meta.json"), os.path.join(CACHE, "faces.json")
    M = _cache_valida(mp, _V.meta, [])                  # cache rovinata o non valida: si ricostruisce dalle foto
    known = {m["n"] for m in M}
    files = sorted(set(glob.glob(os.path.join(SRC, "*.jpg")) + glob.glob(os.path.join(SRC, "*.JPG")) + glob.glob(os.path.join(SRC, "*.jpeg"))))     # set: su Windows *.jpg e *.JPG trovano gli stessi file
    new = [_meta_one(f) for f in files if os.path.basename(f) not in known]
    # foto aggiunte dopo, prese dalle cartelle complete (non nella selezione del cliente): vanno in coda, la numerazione non cambia
    new += [_meta_one(f) for f in CFG.get("foto_extra", []) if os.path.basename(f) not in known | {m["n"] for m in new}]
    if new:
        first = not M
        M += sorted(new, key=lambda x: x["dt"]) if first else new
        _scrivi_json(mp, M)
    _build_thumbs(M)
    F = _cache_valida(fp, _V.volti, {})
    missing = [m for m in M if m["n"] not in F]
    if missing: F.update(_build_faces(missing)); _scrivi_json(fp, F)
    IDX = {m["n"].rsplit(".", 1)[0]: k + 1 for k, m in enumerate(M)}      # nome file senza estensione -> numero foto
    # origine di ogni foto (cartella completa da cui viene): scritta da abbina.py, serve per le correzioni per capitolo
    ORIGINE = {}
    for op in (os.path.join(SRC, "origine.json"), os.path.join(CACHE, "origine.json")):
        o = _cache_valida(op, lambda d: _V.dizionario(d, "origine.json"), {})
        ORIGINE.update({k: v for k, v in o.items() if isinstance(v, str)})
    FACE_FIX = {k: tuple(v) for k, v in CFG.get("centri_volto", {}).items()}   # {"_DSC3885": [x, y]} centro a mano (0-1)
    _ESP = CFG.get("esposizione", {})
    WB = CFG.get("bilanciamento_bianco", {})     # {"_DSC1406": [r, g, b]} guadagni lineari
    TXTCFG = CFG.get("testo", {})
    TITLE = (TXTCFG.get("nome", ""), TXTCFG.get("sottotitolo", ""), TXTCFG.get("data", ""))
    INK = tuple(TXTCFG.get("colore", [58, 54, 51]))
    SERIF_FILE, SANS_FILE = _pfont.serif_predefinito(), _pfont.sans_predefinito()      # Didot e Avenir Next sul Mac
    return sys.modules[__name__]


def _leggi_json(p):
    return _formato.leggi_json(p)


def _scrivi_json(p, dati):
    _formato.scrivi_json(p, dati)                       # atomico: un'interruzione non lascia un JSON troncato


def _cache_valida(p, controlla, vuota):
    """contenuto di un file di cache controllato; se manca, è rovinato o non è valido si riparte da `vuota` (la cache si
    ricostruisce dalle foto: niente blocca l'apertura del progetto)"""
    if not os.path.exists(p): return vuota
    try: return controlla(_leggi_json(p))
    except (OSError, ValueError, RecursionError) as e:
        print(f"{os.path.basename(p)} non valido, lo ricostruisco: {e}", flush=True)
        return vuota


# ---------------- geometria ----------------
def _geometry():
    wcm, hcm = CFG["formato_cm"]; ppi_target = CFG.get("ppi", 300); bleed_mm = CFG.get("abbondanza_mm", 0)
    wcm_t, hcm_t = wcm + 2 * bleed_mm / 10, hcm + 2 * bleed_mm / 10
    if CFG.get("dimensioni_esatte", True):
        # pixel con lo stesso rapporto esatto del formato, ppi aggiustati di poco: Photoshop mostra la misura esatta in cm
        r = Fraction(wcm_t).limit_denominator(1000) / Fraction(hcm_t).limit_denominator(1000)
        a, b = r.numerator, r.denominator
        n = max(1, round(wcm_t / 2.54 * ppi_target / a))
        W, H = a * n, b * n
        ppi = W / (wcm_t / 2.54)
    else:
        W, H = round(wcm_t / 2.54 * ppi_target), round(hcm_t / 2.54 * ppi_target); ppi = ppi_target
    mm = lambda v: round(v / 25.4 * ppi)
    return W, H, ppi, mm(bleed_mm), mm(CFG.get("spazio_mm", 2.5)), mm(CFG.get("margine_mm", 10))
NC, NR = 12, 8

# ---------------- foto: metadati, miniature, volti ----------------
def _meta_one(f):
    im = Image.open(f); ex = im.getexif(); sub = ex.get_ifd(0x8769); w, h = im.size
    return dict(n=os.path.basename(f), dt=f"{sub.get(36867) or ex.get(306)}.{sub.get(37521, '00')}", w=w, h=h, ar=round(w / h, 3), src=os.path.abspath(f))
def _build_thumbs(meta):
    for m in meta:
        p = os.path.join(THUMBS, m["n"])
        if not os.path.exists(p):
            im = Image.open(m["src"]); im.draft("RGB", (1200, 1200)); im = ImageOps.exif_transpose(im).convert("RGB"); im.thumbnail((1200, 1200)); im.save(p, quality=85)
def _build_faces(meta):
    import cv2
    d = cv2.data.haarcascades
    fr = cv2.CascadeClassifier(d + "haarcascade_frontalface_default.xml"); pr = cv2.CascadeClassifier(d + "haarcascade_profileface.xml")
    out = {}
    for m in meta:
        g = cv2.cvtColor(cv2.imread(os.path.join(THUMBS, m["n"])), cv2.COLOR_BGR2GRAY); H, W = g.shape; mn = int(min(W, H) * 0.04)
        bx = list(fr.detectMultiScale(g, 1.1, 6, minSize=(mn, mn))) + list(pr.detectMultiScale(g, 1.1, 6, minSize=(mn, mn))) + \
             [(W - x - w, y, w, h) for x, y, w, h in pr.detectMultiScale(cv2.flip(g, 1), 1.1, 6, minSize=(mn, mn))]
        out[m["n"]] = [[float(x / W), float(y / H), float((x + w) / W), float((y + h) / H)] for x, y, w, h in bx]
    return out

def name(i): return M[i]["n"].rsplit(".", 1)[0]

# ---------------- ritaglio ----------------
def _faces_center(i):
    if name(i) in FACE_FIX: return FACE_FIX[name(i)]
    fs = F.get(M[i]["n"], [])
    if not fs: return None
    A = [(f[2] - f[0]) * (f[3] - f[1]) for f in fs]; big = max(A); fs = [f for f, a in zip(fs, A) if a > big * 0.15]
    return (min(f[0] for f in fs) + max(f[2] for f in fs)) / 2, (min(f[1] for f in fs) + max(f[3] for f in fs)) / 2
def crop(i, cw, ch, z=1.0):
    """finestra di ritaglio normalizzata (l,t,r,b) perché la foto i riempia cw x ch; tiene i volti; z>1 stringe sui volti"""
    ar = M[i]["ar"]; ca = cw / ch; fc = _faces_center(i); fx, fy = fc if fc else (0.5, 0.42)
    if ar > ca: fw = ca / ar; l = min(max(fx - fw / 2, 0), 1 - fw); l, t, r, b = l, 0, l + fw, 1
    else: fh = ar / ca; t = min(max(fy - fh * 0.42, 0), 1 - fh); l, t, r, b = 0, t, 1, t + fh
    if z > 1:
        cx, cy = fc if fc else ((l + r) / 2, (t + b) / 2); w, h = (r - l) / z, (b - t) / z
        nl = min(max(cx - w / 2, l), r - w); nt = min(max(cy - h * 0.42, t), b - h); l, t, r, b = nl, nt, nl + w, nt + h
    return l, t, r, b

# ---------------- griglia e moduli ----------------
def _p(n): return IDX[n] if isinstance(n, str) else n
def P(n, c, r, w, h, bw=False, z=1.0): return dict(k="p", i=_p(n) - 1, c=c, r=r, w=w, h=h, bw=bw, z=z)
def FULL(n, bw=False, z=1.0): return dict(k="full", i=_p(n) - 1, bw=bw, z=z)
def TXT(kind, c, r, w, h): return dict(k="t", kind=kind, c=c, r=r, w=w, h=h)
def _frame(side, mode):
    if mode == "I": return ((0, FOLD - G / 2) if side == "L" else (FOLD + G / 2, CW)), (0, CH)
    return ((B + MG, FOLD - MG) if side == "L" else (FOLD + MG, B + TW - MG)), (B + MG, B + TH - MG)
def _place(side, mode, it):
    if it["k"] == "full":
        x0, x1 = (0, FOLD - G / 2) if side == "L" else (FOLD + G / 2, CW); return dict(it, x=round(x0), y=0, W=round(x1) - round(x0), H=CH, side=side)
    (x0, x1), (y0, y1) = _frame(side, mode); cw = (x1 - x0 - (NC - 1) * G) / NC; rh = (y1 - y0 - (NR - 1) * G) / NR
    # linee della griglia su pixel interi prima di tutto: così ogni spazio è esattamente G
    colx = lambda c: round(x0 + c * (cw + G)); rowy = lambda r: round(y0 + r * (rh + G))
    xa, ya = colx(it["c"]), rowy(it["r"])
    xb = round(x1) if it["c"] + it["w"] == NC else colx(it["c"] + it["w"]) - G
    yb = round(y1) if it["r"] + it["h"] == NR else rowy(it["r"] + it["h"]) - G
    return dict(it, x=xa, y=ya, W=xb - xa, H=yb - ya, side=side)
def layout(spread):
    out = []
    for side, (mode, items) in zip("LR", spread): out += [_place(side, mode, i) for i in items]
    return out
def zcrop(it): return crop(it["i"], it["W"], it["H"], it.get("z", 1.0))
def _flat(items): return [x for it in items for x in (it if isinstance(it, list) else [it])]
def I(*items): return ("I", _flat(items))      # pagina immersiva
def W(*items): return ("W", _flat(items))      # pagina bianca con margine
# moduli di pagina (n = nome file "_DSC1234" o numero foto)
def DUO(a, b, bw=(False, False), z=(1, 1)): return [P(a, 0, 0, 6, 8, bw[0], z[0]), P(b, 6, 0, 6, 8, bw[1], z[1])]          # 2 verticali
def VLL(v, a, b, mirror=False, bw=False):                                                                                   # 1 verticale + 2 orizzontali
    return [P(v, 6, 0, 6, 8, bw), P(a, 0, 0, 6, 4, bw), P(b, 0, 4, 6, 4, bw)] if mirror else [P(v, 0, 0, 6, 8, bw), P(a, 6, 0, 6, 4, bw), P(b, 6, 4, 6, 4, bw)]
def V4(v, a, b, c, d, mirror=False, z=1.0):                                                                                 # 1 verticale grande + 4 piccole verticali
    o, vx = (0, 6) if mirror else (6, 0)
    return [P(v, vx, 0, 6, 8, z=z), P(a, o, 0, 3, 4), P(b, o + 3, 0, 3, 4), P(c, o, 4, 3, 4), P(d, o + 3, 4, 3, 4)]
def G4(a, b, c, d, bw=False): return [P(a, 0, 0, 6, 4, bw), P(b, 6, 0, 6, 4, bw), P(c, 0, 4, 6, 4, bw), P(d, 6, 4, 6, 4, bw)]  # 4 orizzontali
def CV(v, bw=False, z=1.0): return [P(v, 3, 0, 6, 8, bw, z)]          # 1 verticale centrata (su pagina bianca)
def SV(v, bw=False, z=1.0): return [P(v, 4, 1, 4, 6, bw, z)]          # 1 verticale piccola centrata: un sussurro
def PP(l, bw=False): return [P(l, 1, 1, 10, 6, bw)]                   # 1 orizzontale con passe-partout bianco
def COL2(a, b, bw=False): return [P(a, 3, 0, 6, 4, bw), P(b, 3, 4, 6, 4, bw)]
def BAND2(a, b, bw=False): return [P(a, 0, 2, 6, 4, bw), P(b, 6, 2, 6, 4, bw)]
def STRIP3(a, b, c, bw=False): return [P(a, 0, 1, 4, 6, bw), P(b, 4, 1, 4, 6, bw), P(c, 8, 1, 4, 6, bw)]

# ---------------- correzioni di luminosità e colore ----------------
def ev_for(i):
    """EV totale della foto i: globale + base del capitolo (cartella di origine) + correzione della singola foto"""
    n = name(i); ev = _ESP.get("globale", 0.0)
    orig = ORIGINE.get(M[i]["n"]) or os.path.dirname(M[i]["src"])
    for folder, v in _ESP.get("per_cartella", {}).items():
        if os.path.normpath(orig) == os.path.normpath(folder): ev += v
    return round(ev + _ESP.get("per_foto", {}).get(n, 0.0), 2)
def apply_ev(im, ev, gains=None):
    """esposizione come il livello Esposizione di Photoshop (gamma 2.2, nessuna spalla: identica nel PSD); poi i guadagni del bilanciamento bianco in luce lineare"""
    import numpy as np
    if abs(ev) < 1e-3 and not gains: return im
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    if abs(ev) >= 1e-3: a = np.clip(a ** 2.2 * (2 ** ev), 0, 1) ** (1 / 2.2)
    if gains:
        lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4) * np.array(gains, dtype=np.float32)
        lin = np.clip(lin, 0, 1)
        a = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8))

# ---------------- testi ----------------
def _font(path_key, default, size, index=0):
    p = TXTCFG.get(path_key) or default
    try: return ImageFont.truetype(p, size, index=index)
    except Exception: return _pfont.pil_ripiego(size)          # Helvetica sul Mac, Arial su Windows, DejaVu su Linux
def _spaced(d, xy, text, font, track, center=None):
    w = sum(font.getlength(ch) for ch in text) + track * (len(text) - 1); x, y = xy
    if center is not None: x = center - w / 2
    for ch in text: d.text((x, y), ch, font=font, fill=INK); x += font.getlength(ch) + track
def _text(it, K):
    Wd, Hd = max(1, round(it["W"] * K)), max(1, round(it["H"] * K)); im = Image.new("RGBA", (Wd, Hd), (255, 255, 255, 0)); d = ImageDraw.Draw(im)
    small = _font("file_font_testo", SANS_FILE, round(62 * K), TXTCFG.get("indice_font_testo", 7))
    if it["kind"] == "title":
        big = _font("file_font_titolo", SERIF_FILE, round(380 * K)); cx = Wd / 2; y = Hd / 2 - round(260 * K)
        d.text((cx - big.getlength(TITLE[0]) / 2, y), TITLE[0], font=big, fill=INK); y += round(520 * K)
        _spaced(d, (0, y), TITLE[1], small, round(22 * K), cx); y += round(110 * K); _spaced(d, (0, y), TITLE[2], small, round(22 * K), cx)
    else:
        mid = _font("file_font_titolo", SERIF_FILE, round(170 * K)); y = Hd - round(400 * K)
        d.text((0, y), TITLE[0], font=mid, fill=INK); y += round(230 * K)
        _spaced(d, (round(6 * K), y), TITLE[1], small, round(14 * K)); y += round(90 * K); _spaced(d, (round(6 * K), y), TITLE[2], small, round(14 * K))
    return im

# ---------------- rendering anteprime ----------------
def _photo(it, K, corrected=False):
    im = Image.open(os.path.join(THUMBS, M[it["i"]]["n"])).convert("RGB")
    if corrected: im = apply_ev(im, ev_for(it["i"]), WB.get(name(it["i"])))
    l, t, r, b = zcrop(it)
    out = im.resize((max(1, round(it["W"] * K)), max(1, round(it["H"] * K))), Image.LANCZOS, box=(l * im.width, t * im.height, r * im.width, b * im.height))
    return ImageOps.grayscale(out).convert("RGB") if it.get("bw") else out
def render(spread, K, corrected=True):
    S = Image.new("RGB", (round(CW * K), round(CH * K)), "white")
    for it in layout(spread):
        pos = (round(it["x"] * K), round(it["y"] * K))
        if it["k"] == "t": t = _text(it, K); S.paste(t, pos, t)
        else: S.paste(_photo(it, K, corrected), pos)
    return S

def load_spec(modname="spec"):
    """SPREADS del progetto caricato, da album.json (un progetto 1.x con spec.py si converte, senza eseguirlo); modname
    resta per compatibilità con gli script 1.x e non si usa"""
    return _formato.carica(PROJ)
