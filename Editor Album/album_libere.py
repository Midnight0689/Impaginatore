"""Cornici libere per il motore di impaginazione (album.py), senza modificare la skill.

Una cornice libera non sta sulla griglia 12 x 8: la sua posizione e la sua misura sono frazioni (0-1) dell'area della pagina
(immersiva: tutta la pagina; bianca: dentro il margine). Così funziona con qualunque formato.

In spec.py:   from album import *
              from album_libere import *
              ... FREE("_DSC1234", 0.10, 0.20, 0.35, 0.50, bw=True, z=1.2) ...

Importandolo, il motore impara a posizionare le cornici libere: anteprima.py, genera_psd.py, esporta_pdf.py ecc. restano invariati.
Nota: i controlli di anteprima.py sugli spazi uguali vedono le cornici libere come eccezioni volute e possono segnalarle.
"""
import album as _a


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


def TEXT(tx, fx, fy, fw, fh, font="AvenirNext-Regular", size=100, col=(58, 54, 51), al="left", tr=0, auto=True, zo=None, stile=None):
    """livello di testo libero (strumento Testo): vedi testo.py"""
    d = dict(k="t", kind="txt", tx=str(tx), fx=float(fx), fy=float(fy), fw=float(fw), fh=float(fh), c=0, r=0, w=1, h=1, font=font, size=float(size), col=list(col), al=al, tr=float(tr), auto=bool(auto))
    if zo is not None: d["zo"] = int(zo)
    if stile: d["stile"] = stile
    return d


def _text_scaled(_orig):
    def _text(it, K):
        if it.get("kind") == "txt":
            import testo
            return testo.render(it, K)
        s = it.get("ts") or 1.0
        return _orig(it, K) if abs(s - 1) < 1e-6 else _orig(dict(it, W=it["W"] / s, H=it["H"] / s), K * s)
    return _text


def ROT(it, deg):
    """inclina la foto dentro la cornice di deg gradi (positivo = in senso orario, come Photoshop); la foto si ingrandisce quanto serve a non lasciare angoli vuoti"""
    return dict(it, a=round(float(deg), 1))


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
        im = Image.open(os.path.join(_a.THUMBS, _a.M[it["i"]]["n"])).convert("RGB")
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


def tono_lut(t):
    """tabella 0-255 -> 0-255 per Livelli (neri b, bianchi w, mezzitoni m) + Curva (punti c, interpolazione monotona)"""
    import numpy as np
    x = np.arange(256, dtype=np.float64) / 255
    b, w, m = float(t.get("b", 0)) / 255, float(t.get("w", 255)) / 255, float(t.get("m", 1.0))
    y = np.clip((x - b) / max(w - b, 1e-3), 0, 1) ** (1 / max(m, 0.05))
    pts = sorted((float(a) / 255, float(c) / 255) for a, c in (t.get("c") or []))
    if pts:
        if pts[0][0] > 0: pts.insert(0, (0.0, pts[0][1]))
        if pts[-1][0] < 1: pts.append((1.0, pts[-1][1]))
        px, py = np.array([q[0] for q in pts]), np.array([q[1] for q in pts]); n = len(px)
        h = np.diff(px); d = np.diff(py) / np.maximum(h, 1e-9); mt = np.zeros(n); mt[0], mt[-1] = d[0], d[-1]
        for k in range(1, n - 1): mt[k] = 0 if d[k - 1] * d[k] <= 0 else (d[k - 1] + d[k]) / 2
        for k in range(n - 1):                                           # Fritsch-Carlson: niente sovraelongazioni
            if abs(d[k]) < 1e-12: mt[k] = mt[k + 1] = 0
            else:
                a_, b_ = mt[k] / d[k], mt[k + 1] / d[k]; r = a_ * a_ + b_ * b_
                if r > 9: tt = 3 / r ** .5; mt[k], mt[k + 1] = tt * a_ * d[k], tt * b_ * d[k]
        i = np.clip(np.searchsorted(px, y, side="right") - 1, 0, n - 2); u = (y - px[i]) / np.maximum(h[i], 1e-9)
        h00, h10, h01, h11 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u, -2 * u**3 + 3 * u**2, u**3 - u**2
        y = h00 * py[i] + h10 * h[i] * mt[i] + h01 * py[i + 1] + h11 * h[i] * mt[i + 1]
    return (np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8)


def tono_attivo(t): return bool(t) and (t.get("b", 0) > 0 or t.get("w", 255) < 255 or abs(t.get("m", 1.0) - 1) > 1e-3 or len(t.get("c") or []) > 0)


def tono_job(i):
    """per genera_psd: dizionario del tono della foto i (o None)"""
    t = _a.CFG.get("tono", {}).get(_a.name(i))
    return dict(b=t.get("b", 0), w=t.get("w", 255), m=t.get("m", 1.0), c=t.get("c") or []) if tono_attivo(t) else None


_CUR = [None]


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
    _a._photo = _photo_rot(_a._photo)
    _a._text = _text_scaled(_a._text)
    _ev0 = _a.apply_ev

    def apply_ev(im, ev, gains=None):                                   # il tono (livelli/curva) viene dopo l'esposizione e prima del bianco e nero
        out = _ev0(im, ev, gains)
        return _apply_tono(out, _CUR[0]) if _CUR[0] is not None else out
    _a.apply_ev = apply_ev
    _a.layout.__code__ = _layout.__code__     # stessa funzione: vale anche per gli script che hanno già importato "layout"


_install()
