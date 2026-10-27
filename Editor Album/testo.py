"""Livelli di testo liberi (come lo strumento Testo di Photoshop): elenco dei font, misura e disegno.

Un testo è un elemento dello spread:  TEXT("Titolo", fx, fy, fw, fh, font="BodoniModa18pt-Italic", size=170, col=(58,54,51), al="left", tr=0)
fx, fy, fw, fh = posizione e misura in frazioni dell'area della pagina (come le cornici libere); size in pixel della pagina (come il resto del motore).
Solo libreria standard + Pillow: i nomi dei font si leggono direttamente dai file (.ttf .otf .ttc).
"""
import json, os, struct

DIRS = ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
CACHE = os.path.expanduser("~/.album-tools/font_cache.json")
_FONTS = None


def _names(path):
    """[(indice, famiglia, stile, nome postscript)] di un file font"""
    out = []
    try:
        with open(path, "rb") as f:
            head = f.read(12)
            if head[:4] == b"ttcf": n = struct.unpack(">I", head[8:12])[0]; offs = struct.unpack(">" + "I" * n, f.read(4 * n))
            else: offs = [0]
            for idx, off in enumerate(offs):
                f.seek(off); h = f.read(12); nt = struct.unpack(">H", h[4:6])[0]; tab = None
                for _ in range(nt):
                    r = f.read(16)
                    if r[:4] == b"name": tab = struct.unpack(">II", r[8:16])
                if not tab: continue
                f.seek(tab[0]); data = f.read(tab[1]); cnt, so = struct.unpack(">HH", data[2:6]); got = {}
                for i in range(cnt):
                    pid, eid, lid, nid, ln, o = struct.unpack(">HHHHHH", data[6 + 12 * i:18 + 12 * i]); raw = data[so + o:so + o + ln]
                    if nid not in (1, 2, 6, 16, 17): continue
                    try: txt = raw.decode("utf-16-be") if pid in (0, 3) else raw.decode("mac_roman")
                    except Exception: continue
                    if pid in (0, 3) or nid not in got: got[nid] = txt
                fam = got.get(16) or got.get(1); sty = got.get(17) or got.get(2) or "Regular"; ps = got.get(6)
                if fam and ps: out.append((idx, fam, sty, ps))
    except Exception:
        pass
    return out


def fonts():
    """tutti i font installati: [{fam, sty, ps, file, idx}] (con cache su disco, si rigenera se cambia il numero di file)"""
    global _FONTS
    if _FONTS is not None: return _FONTS
    files = []
    for d in DIRS:
        for root, _, fs in os.walk(d):
            files += [os.path.join(root, f) for f in fs if f.lower().endswith((".ttf", ".otf", ".ttc"))]
    stamp = len(files)
    try:
        c = json.load(open(CACHE))
        if c.get("n") == stamp: _FONTS = c["fonts"]; return _FONTS
    except Exception: pass
    out, seen = [], set()
    for p in sorted(files):
        for idx, fam, sty, ps in _names(p):
            if ps in seen or fam.startswith("."): continue
            seen.add(ps); out.append(dict(fam=fam, sty=sty, ps=ps, file=p, idx=idx))
    out.sort(key=lambda x: (x["fam"].lower(), x["sty"]))
    _FONTS = out
    try: os.makedirs(os.path.dirname(CACHE), exist_ok=True); json.dump(dict(n=stamp, fonts=out), open(CACHE, "w"))
    except Exception: pass
    return out


def font_file(ps):
    for f in fonts():
        if f["ps"] == ps: return f["file"], f["idx"]
    for f in fonts():                                              # ripiego: qualsiasi stile della stessa famiglia o Helvetica
        if ps and ps.split("-")[0] == f["ps"].split("-")[0]: return f["file"], f["idx"]
    return "/System/Library/Fonts/Helvetica.ttc", 0


_CACHE_F = {}


def _font(ps, px):
    from PIL import ImageFont
    k = (ps, round(px, 1))
    if k not in _CACHE_F:
        path, idx = font_file(ps)
        try: _CACHE_F[k] = ImageFont.truetype(path, max(1, round(px)), index=idx)
        except Exception: _CACHE_F[k] = ImageFont.load_default()
    return _CACHE_F[k]


def _width(text, font, size, tr):
    if not tr: return font.getlength(text)
    return sum(font.getlength(c) for c in text) + tr / 1000 * size * max(len(text) - 1, 0)


def shown(it):
    """testo come si vede (tutto maiuscolo se richiesto)"""
    t = str(it.get("tx", "")); return t.upper() if it.get("caps") else t


def lead(it):
    """interlinea come moltiplicatore del corpo (1.2 = come prima)"""
    try: return min(max(float(it.get("lh", 1.2)), 0.6), 3.0)
    except Exception: return 1.2


def wrap(it, box_w, K=1.0):
    """righe del testo dopo l'a capo automatico nella larghezza del riquadro (box_w in pixel della pagina)"""
    size = float(it.get("size", 100)); tr = float(it.get("tr", 0)); font = _font(it.get("font", ""), size * K); lines = []
    for para in shown(it).split("\n"):
        words = para.split(" "); cur = ""
        for w in words:
            t = (cur + " " + w) if cur else w
            if cur and _width(t, font, size * K, tr) > box_w * K: lines.append(cur); cur = w
            else: cur = t
        lines.append(cur)
    return lines


def fit_height(it, box_w):
    """altezza del riquadro che contiene tutto il testo (pixel della pagina)"""
    return len(wrap(it, box_w)) * float(it.get("size", 100)) * lead(it) + float(it.get("size", 100)) * 0.1


def render(it, K):
    """immagine RGBA del riquadro di testo (it['W'], it['H'] in pixel della pagina, scala K)"""
    from PIL import Image, ImageDraw
    Wd, Hd = max(1, round(it["W"] * K)), max(1, round(it["H"] * K)); im = Image.new("RGBA", (Wd, Hd), (255, 255, 255, 0)); d = ImageDraw.Draw(im)
    size = float(it.get("size", 100)); tr = float(it.get("tr", 0)); font = _font(it.get("font", ""), size * K); col = tuple(int(v) for v in (it.get("col") or (58, 54, 51)))[:3]
    lh = size * lead(it) * K; al = it.get("al", "left"); y = 0.0
    for line in wrap(it, it["W"], K):
        w = _width(line, font, size * K, tr); x = 0 if al == "left" else (Wd - w) / 2 if al == "center" else Wd - w
        if tr:
            for ch in line: d.text((x, y), ch, font=font, fill=col); x += font.getlength(ch) + tr / 1000 * size * K
        else: d.text((x, y), line, font=font, fill=col)
        y += lh
    return im


def job_x(it):
    """campi del testo per il PSD + posizione (gx, gy) del primo pixel d'inchiostro rispetto all'angolo del riquadro, come lo disegna l'anteprima:
    Photoshop e Pillow impostano la prima riga in modo diverso, così in Photoshop si allinea il livello a questo punto"""
    size = float(it.get("size", 100)); tr = float(it.get("tr", 0)); font = _font(it.get("font", ""), size); lh = size * lead(it); al = it.get("al", "left"); W = float(it["W"])
    gx = gy = None
    for i, line in enumerate(wrap(it, W)):
        if not line.strip(): continue
        w = _width(line, font, size, tr); x = 0 if al == "left" else (W - w) / 2 if al == "center" else W - w
        l, t, r, b = font.getbbox(line.strip()); sp0 = len(line) - len(line.lstrip()); x += l + (font.getlength(" ") * sp0 if sp0 else 0)
        gx = x if gx is None else min(gx, x); gy = i * lh + t if gy is None else min(gy, i * lh + t)
    d = {k: it[k] for k in ("tx", "font", "size", "col", "al", "tr")}; d.update(caps=bool(it.get("caps")), lh=lead(it), gx=gx or 0, gy=gy or 0); return d
