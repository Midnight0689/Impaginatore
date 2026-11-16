"""Cornici libere per il motore di impaginazione (album.py), senza modificare la skill.

Una cornice libera non sta sulla griglia 12 x 8: la sua posizione e la sua misura sono frazioni (0-1) dell'area della pagina
(immersiva: tutta la pagina; bianca: dentro il margine). Così funziona con qualunque formato.

In spec.py:   from album import *
              from album_libere import *
              ... FREE("_DSC1234", 0.10, 0.20, 0.35, 0.50, bw=True, z=1.2) ...

Importandolo, il motore impara a posizionare le cornici libere: anteprima.py, genera_psd.py, esporta_pdf.py ecc. restano invariati.
Nota: i controlli di anteprima.py sugli spazi uguali vedono le cornici libere come eccezioni volute e possono segnalarle.

L'editor ne copia una versione nella cartella di ogni progetto che ha cornici libere (fa parte del formato di salvataggio
1.x): per questo il modulo funziona sia dentro il pacchetto (impaginatore.motore.album_libere) sia da solo, accanto a
spec.py, con i vecchi script che hanno album.py nel percorso.
"""
try: from . import album as _a                   # dentro il pacchetto impaginatore
except ImportError: import album as _a           # copia nella cartella di un progetto, letta dagli script delle versioni 1.x


def FREE(n, x, y, w, h, bw=False, z=1.0, zo=None):
    d = dict(k="f", i=_a._p(n) - 1, x=float(x), y=float(y), w=float(w), h=float(h), bw=bw, z=z)
    if zo is not None: d["zo"] = int(zo)         # posizione tra le cornici libere (livelli): più alto = più sopra
    return d


def _layout(spread):                           # le cornici libere si disegnano sopra le altre (anche se a cavallo della piega)
    # attenzione: il codice gira nel modulo album, dove _place è quello già sostituito
    out = []
    for side, (mode, items) in zip("LR", spread): out += [_place(side, mode, i) for i in items]    # noqa: F821
    for n, it in enumerate(out): it["_o"] = n
    return sorted(out, key=lambda it: (bool(it.get("libera")), it["zo"] if "zo" in it else 1000 + it["_o"]))


def TXTF(kind, fx, fy, fw, fh, ts=1.0, zo=None):
    """blocco di testo libero (come un livello di testo): posizione e misura in frazioni della pagina, ts = scala dei caratteri"""
    d = dict(k="t", kind=kind, fx=float(fx), fy=float(fy), fw=float(fw), fh=float(fh), c=0, r=0, w=1, h=1, ts=float(ts))
    if zo is not None: d["zo"] = int(zo)
    return d


def TEXT(tx, fx, fy, fw, fh, font="AvenirNext-Regular", size=100, col=(58, 54, 51), al="left", tr=0, auto=True, zo=None, stile=None, lh=1.2, caps=False):
    """livello di testo libero (strumento Testo): vedi testo.py"""
    d = dict(k="t", kind="txt", tx=str(tx), fx=float(fx), fy=float(fy), fw=float(fw), fh=float(fh), c=0, r=0, w=1, h=1, font=font, size=float(size), col=list(col), al=al, tr=float(tr), auto=bool(auto), lh=float(lh), caps=bool(caps))
    if zo is not None: d["zo"] = int(zo)
    if stile: d["stile"] = stile
    return d


def _text_scaled(_orig):
    def _text(it, K):
        if it.get("kind") == "txt":
            try: from . import testo
            except ImportError: import testo
            return testo.render(it, K)
        s = it.get("ts") or 1.0
        return _orig(it, K) if abs(s - 1) < 1e-6 else _orig(dict(it, W=it["W"] / s, H=it["H"] / s), K * s)
    return _text


def ROT(it, deg):
    """inclina la foto dentro la cornice di deg gradi (positivo = in senso orario, come Photoshop); la foto si ingrandisce quanto serve a non lasciare angoli vuoti"""
    return dict(it, a=round(float(deg), 1))


def STY(it, bd=None, sh=0, oc=100):
    """bordo (millimetri, colore) e ombra (0-100) di una cornice"""
    d = dict(it)
    if bd: d["bd"] = [float(bd[0]), str(bd[1])]
    if sh: d["sh"] = int(sh)
    if oc is not None and int(oc) < 100: d["oc"] = int(oc)
    return d


def sty_job(it):
    """per genera_psd: bordo in pixel del documento e ombra, o None"""
    if not (it.get("bd") or it.get("sh") or it.get("oc", 100) < 100): return None
    bd = it.get("bd"); px = round(float(bd[0]) / 25.4 * _a.PPI, 1) if bd else 0
    col = [int(bd[1][k:k + 2], 16) for k in (1, 3, 5)] if bd else [255, 255, 255]
    return dict(bd=px, col=col, sh=int(it.get("sh") or 0), oc=int(it.get("oc", 100)), ppi=_a.PPI)


def _zcrop(it):                                # attenzione: il codice gira nel modulo album (crop e M sono suoi)
    l, t, r, b = crop(it["i"], it["W"], it["H"], it.get("z", 1.0))              # noqa: F821
    a = it.get("a") or 0
    if not a: return l, t, r, b
    import math
    th = math.radians(a); c, s = abs(math.cos(th)), abs(math.sin(th)); ar = M[it["i"]]["ar"]                   # noqa: F821
    wp, hp = (r - l) * ar, (b - t); bw, bh = wp * c + hp * s, wp * s + hp * c      # unità: altezza della foto = 1
    f = min(ar / bw, 1 / bh, 1.0); wp, hp, bw, bh = wp * f, hp * f, bw * f, bh * f
    cx = min(max((l + r) / 2 * ar, bw / 2), ar - bw / 2); cy = min(max((t + b) / 2, bh / 2), 1 - bh / 2)
    return (cx - wp / 2) / ar, cy - hp / 2, (cx + wp / 2) / ar, cy + hp / 2


def _photo_rot(_orig):
    from PIL import Image
    import math, os

    def _photo(it, K, corrected=False):
        a = it.get("a") or 0
        _CUR[0] = it["i"]
        if not a: return _orig(it, K, corrected)
        im = _a.leggi_rgb(os.path.join(_a.THUMBS, _a.M[it["i"]]["n"]))
        if corrected: im = _a.apply_ev(im, _a.ev_for(it["i"]), _a.WB.get(_a.name(it["i"])))
        l, t, r, b = _a.zcrop(it); Wo, Ho = max(1, round(it["W"] * K)), max(1, round(it["H"] * K)); iw, ih = im.size
        sc = (r - l) * iw / Wo; cx, cy = (l + r) / 2 * iw, (t + b) / 2 * ih; th = math.radians(a); c, s = math.cos(th), math.sin(th)
        data = (sc * c, sc * s, cx - sc * (c * Wo / 2 + s * Ho / 2), -sc * s, sc * c, cy - sc * (-s * Wo / 2 + c * Ho / 2))
        out = im.transform((Wo, Ho), Image.AFFINE, data, resample=Image.BICUBIC)
        if it.get("bw"):
            from PIL import ImageOps
            out = ImageOps.grayscale(out).convert("RGB")
        return out
    return _photo


def _photo_bordo(_orig):
    def _photo(it, K, corrected=False):
        out = _orig(it, K, corrected)
        bd = it.get("bd")
        if bd:
            from PIL import ImageDraw
            w = max(1, round(float(bd[0]) / 25.4 * _a.PPI * K)); d = ImageDraw.Draw(out); col = str(bd[1])
            for k in range(w): d.rectangle([k, k, out.width - 1 - k, out.height - 1 - k], outline=col)
        return out
    return _photo


def _render_ombre(spread, K, corrected=True):
    """come render del motore, con in più l'ombra morbida sotto le cornici che ce l'hanno (sh 0-100)"""
    from PIL import Image, ImageFilter
    S = Image.new("RGB", (round(_a.CW * K), round(_a.CH * K)), "white")
    for it in _a.layout(spread):
        pos = (round(it["x"] * K), round(it["y"] * K))
        if it["k"] == "t": t = _a._text(it, K); S.paste(t, pos, t); continue
        ph = _a._photo(it, K, corrected)
        sh = it.get("sh")
        if sh:
            blur = max(1.0, (1.5 + sh / 100 * 4.5) / 25.4 * _a.PPI * K); dy = round(blur * 0.55); m = round(blur * 3)
            mask = Image.new("L", (ph.width + 2 * m, ph.height + 2 * m), 0); mask.paste(255, (m, m, m + ph.width, m + ph.height))
            mask = mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * (0.15 + 0.5 * sh / 100)))
            S.paste(Image.new("RGB", mask.size, (0, 0, 0)), (pos[0] - m, pos[1] - m + dy), mask)
        oc = it.get("oc", 100)
        if sh and oc < 100: S.paste((255, 255, 255), (pos[0], pos[1], pos[0] + ph.width, pos[1] + ph.height))    # nel PSD l'ombra sta dietro un rettangolo bianco opaco: attraverso la foto trasparente non si vede
        if oc < 100: S.paste(ph, pos, Image.new("L", ph.size, round(255 * oc / 100)))
        else: S.paste(ph, pos)
    return S


def tono_lut(t):
    """tabella 0-255 -> 0-255 per Livelli (neri b, bianchi w, mezzitoni m) + Curva (punti c, spline cubica naturale come Photoshop)"""
    import numpy as np
    x = np.arange(256, dtype=np.float64) / 255
    b, w, m = float(t.get("b", 0)) / 255, float(t.get("w", 255)) / 255, float(t.get("m", 1.0))
    y = np.clip((x - b) / max(w - b, 1e-3), 0, 1) ** (1 / max(m, 0.05))
    pts = sorted((float(a) / 255, float(c) / 255) for a, c in (t.get("c") or []))
    if pts:
        if pts[0][0] > 0: pts.insert(0, (0.0, 0.0))                       # come nel PSD: la curva parte da (0,0) e arriva a (255,255)
        if pts[-1][0] < 1: pts.append((1.0, 1.0))
        px, py = np.array([q[0] for q in pts]), np.array([q[1] for q in pts]); n = len(px)
        h = np.maximum(np.diff(px), 1e-9)
        A = np.zeros((n, n)); r = np.zeros(n); A[0, 0] = A[-1, -1] = 1       # spline cubica naturale: e' quella di Photoshop (misurata)
        for k in range(1, n - 1):
            A[k, k - 1], A[k, k], A[k, k + 1] = h[k - 1], 2 * (h[k - 1] + h[k]), h[k]
            r[k] = 3 * ((py[k + 1] - py[k]) / h[k] - (py[k] - py[k - 1]) / h[k - 1])
        cc = np.linalg.solve(A, r)
        i = np.clip(np.searchsorted(px, y, side="right") - 1, 0, n - 2); t_ = y - px[i]
        bb = (py[i + 1] - py[i]) / h[i] - h[i] * (2 * cc[i] + cc[i + 1]) / 3; dd = (cc[i + 1] - cc[i]) / (3 * h[i])
        y = py[i] + bb * t_ + cc[i] * t_**2 + dd * t_**3
    return (np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8)


def tono_attivo(t): return bool(t) and (t.get("b", 0) > 0 or t.get("w", 255) < 255 or abs(t.get("m", 1.0) - 1) > 1e-3 or len(t.get("c") or []) > 0)


def tono_job(i):
    """per genera_psd: dizionario del tono della foto i (o None)"""
    t = _a.CFG.get("tono", {}).get(_a.name(i))
    return dict(b=t.get("b", 0), w=t.get("w", 255), m=t.get("m", 1.0), c=t.get("c") or []) if tono_attivo(t) else None


_CUR = [None]

# ---- ritocco stile Lightroom (per foto): tmp temperatura, tnt tinta, con contrasto, alt alteluci, omb ombre, bia bianchi, ner neri, vib vibranza, sat saturazione (tutti -100..100)
RIT_KEYS = ("tmp", "tnt", "con", "alt", "omb", "bia", "ner", "vib", "sat")


def rit(i):
    r = _a.CFG.get("ritocco", {}).get(_a.name(i))
    r = {k: float(v) for k, v in (r or {}).items() if k in RIT_KEYS and abs(float(v)) >= 0.5}
    return r or None


def rit_lut(r):
    """tabella 0-255 -> 0-255 per contrasto, alteluci, ombre, bianchi e neri (None se non serve); la stessa curva va in Photoshop come livello Curve"""
    import numpy as np
    if not r or not any(r.get(k) for k in ("con", "alt", "omb", "bia", "ner")): return None
    x = np.arange(256, dtype=np.float64) / 255
    g = lambda c, w: np.exp(-((x - c) / w) ** 2)
    y = x.copy(); c = r.get("con", 0) / 100
    y = y + c * (y * y * (3 - 2 * y) - y)
    y = y + 0.30 * r.get("omb", 0) / 100 * g(.25, .20) + 0.30 * r.get("alt", 0) / 100 * g(.78, .20) + 0.18 * r.get("bia", 0) / 100 * g(.95, .10) + 0.12 * r.get("ner", 0) / 100 * g(.04, .10)
    y = np.maximum.accumulate(np.clip(y, 0, 1))
    return (y * 255 + 0.5).astype(np.uint8)


RIT_X = (0, 4, 10, 18, 30, 48, 70, 95, 120, 145, 170, 195, 218, 238, 249, 255)       # 16 punti: il massimo che Photoshop accetta, più fitti vicino a neri e bianchi


def rit_curva(r):
    """punti (x, y) 0-255 della curva (estremi compresi: i neri possono essere alzati), per il livello Curve di Photoshop"""
    L = rit_lut(r)
    if L is None: return None
    return [[x, int(L[x])] for x in RIT_X]


def sat_matrice(sat):
    """saturazione = scala la distanza dal grigio (pesi 601): è una matrice 3x3, quindi identica in anteprima e nel Miscelatore canale di Photoshop (valori in %)"""
    k = 1 + sat / 100; w = (0.299, 0.587, 0.114)
    return [[100 * ((1 if c == j else 0) * k + (1 - k) * w[j]) for j in range(3)] for c in range(3)]


_VIB = [None]


def vib_lut():
    """tabella 3D misurata in Photoshop (livello Vibranza, -100..100, griglia 17x17x17): l'anteprima fa quello che farà il PSD"""
    if _VIB[0] is None:
        import numpy as np, os
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vib_lut.npz")                       # accanto al modulo: copia in un progetto
        if not os.path.exists(p): p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "risorse", "vib_lut.npz")     # nel pacchetto
        _VIB[0] = np.load(p)["lut"]
    return _VIB[0]


def vib_apply(a, v):
    """a: array uint8 (H, W, 3); v: vibranza intera -100..100 (interpolazione trilineare nella tabella)"""
    import numpy as np
    T = vib_lut()[int(v) + 100].astype(np.float32)
    f = a.astype(np.float32) * (16 / 255.0); i0 = np.minimum(f.astype(np.int32), 15); t = f - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]; tr, tg, tb = t[..., 0:1], t[..., 1:2], t[..., 2:3]
    out = 0
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (tr if dr else 1 - tr) * (tg if dg else 1 - tg) * (tb if db else 1 - tb)
                out = out + w * T[r0 + dr, g0 + dg, b0 + db]
    return (out + 0.5).clip(0, 255).astype(np.uint8)


def rit_gains(r):
    """guadagni lineari (r, g, b) di temperatura e tinta"""
    if not r or not (r.get("tmp") or r.get("tnt")): return None
    t, n = r.get("tmp", 0) / 100, r.get("tnt", 0) / 100
    return (2 ** (0.45 * t + 0.08 * n), 2 ** (-0.30 * n), 2 ** (-0.45 * t + 0.08 * n))


def wb_total(i):
    """bilanciamento del bianco della foto (se c'è) per temperatura e tinta: sono un'unica correzione, anche nel PSD"""
    g, q = _a.WB.get(_a.name(i)), rit_gains(rit(i))
    if not q: return g
    return tuple(a * b for a, b in zip(g or (1, 1, 1), q))


def rit_job(i):
    r = rit(i)
    if not r: return None
    vib, sat = int(round(r.get("vib", 0))), int(round(r.get("sat", 0)))
    return dict(c=rit_curva(r), vib=vib, sat=sat, satm=sat_matrice(sat) if sat else None) if (rit_lut(r) is not None or vib or sat) else None


def _apply_rit(im, i):
    r = rit(i)
    if not r: return im
    import numpy as np
    from PIL import Image
    a = np.asarray(im.convert("RGB"))
    L = rit_lut(r)
    if L is not None: a = L[a]
    sat, vib = int(round(r.get("sat", 0))), int(round(r.get("vib", 0)))
    if sat:
        M = np.array(sat_matrice(sat), dtype=np.float32) / 100
        a = (np.clip(a.astype(np.float32) @ M.T, 0, 255) + 0.5).astype(np.uint8)
    if vib: a = vib_apply(a, vib)
    return Image.fromarray(a)


def _apply_tono(im, i):
    t = _a.CFG.get("tono", {}).get(_a.name(i))
    if not tono_attivo(t): return im
    import numpy as np
    from PIL import Image
    a = np.asarray(im.convert("RGB")); return Image.fromarray(tono_lut(t)[a])


def _install():
    if getattr(_a._place, "_libere", False):
        return
    _orig = _a._place

    def _place(side, mode, it):
        if it.get("k") == "t" and "fx" in it:
            (x0, x1), (y0, y1) = _a._frame(side, mode)
            xa = round(x0 + it["fx"] * (x1 - x0)); xb = round(x0 + (it["fx"] + it["fw"]) * (x1 - x0))
            ya = round(y0 + it["fy"] * (y1 - y0)); yb = round(y0 + (it["fy"] + it["fh"]) * (y1 - y0))
            return dict(it, x=xa, y=ya, W=xb - xa, H=yb - ya, side=side, libera=True)
        if it.get("k") != "f":
            return _orig(side, mode, it)
        (x0, x1), (y0, y1) = _a._frame(side, mode)
        xa = round(x0 + it["x"] * (x1 - x0)); xb = round(x0 + (it["x"] + it["w"]) * (x1 - x0))
        ya = round(y0 + it["y"] * (y1 - y0)); yb = round(y0 + (it["y"] + it["h"]) * (y1 - y0))
        return dict(it, k="p", x=xa, y=ya, W=xb - xa, H=yb - ya, side=side, libera=True)

    _place._libere = True
    _a._place = _place

    _a.zcrop.__code__ = _zcrop.__code__        # ritaglio che tiene conto dell'angolo (anche per gli script che l'hanno già importato)
    _a._photo = _photo_bordo(_photo_rot(_a._photo))
    _a.render = _render_ombre
    _a._text = _text_scaled(_a._text)
    _ev0 = _a.apply_ev

    def apply_ev(im, ev, gains=None):                                   # il tono (livelli/curva) viene dopo l'esposizione e prima del bianco e nero
        if _CUR[0] is not None:
            q = rit_gains(rit(_CUR[0]))
            if q: gains = tuple(a * b for a, b in zip(gains or (1, 1, 1), q))
        out = _ev0(im, ev, gains)
        return _apply_rit(_apply_tono(out, _CUR[0]), _CUR[0]) if _CUR[0] is not None else out
    _a.apply_ev = apply_ev
    _a.layout.__code__ = _layout.__code__     # stessa funzione: vale anche per gli script che hanno già importato "layout"


_install()
