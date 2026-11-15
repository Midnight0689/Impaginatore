"""Fedeltà anteprima ↔ Photoshop per geometria (ritaglio, zoom, angolo), bordo, ombra, opacità e testi (era
tests/fedelta_geometria.py della 1.5).

Una foto-campione a forme morbide, una cornice per spread con parametri diversi; esporta i PSD, li appiattisce in Photoshop
e confronta con l'anteprima: scarto medio, quota di pixel molto diversi (bordi fuori posto) e spostamento residuo migliore.
Per i testi confronta l'ingombro dell'inchiostro. Apre Photoshop: gira solo dove c'è (pytest -m photoshop).
Variabili: SOLO_TESTO=1 (una sola geometria), KT=<scala dei testi> (default 1.0)."""
import io
import os

import numpy as np
import pytest
from aiuti import attendi_log
from PIL import Image, ImageDraw, ImageFilter

from impaginatore.motore import photoshop as P
from impaginatore.piattaforma import photoshop as pps

pytestmark = [pytest.mark.photoshop, pytest.mark.skipif(not pps.disponibile(), reason="serve Photoshop")]
Image.MAX_IMAGE_PIXELS = None


def campione():
    W, H = 1800, 1200; im = Image.new("RGB", (W, H), (200, 190, 170)); d = ImageDraw.Draw(im)
    for k in range(12): d.rectangle([k * 150, 0, k * 150 + 75, H], fill=(40 + k * 15, 90, 200 - k * 12))
    d.ellipse([500, 300, 1300, 900], fill=(230, 60, 40)); d.rectangle([0, 0, 220, 160], fill=(10, 200, 10)); d.rectangle([W - 260, H - 200, W, H], fill=(255, 255, 0))
    d.polygon([(900, 50), (1100, 250), (700, 250)], fill=(0, 0, 0)); d.line([0, H // 2, W, H // 2], fill=(255, 255, 255), width=14)
    return im.filter(ImageFilter.GaussianBlur(5))


GEO = [("ritaglio", {}), ("zoom1.5", {"z": 1.5}), ("zoom2.5", {"z": 2.5}), ("angolo+12", {"a": 12}), ("angolo-30", {"a": -30}), ("angolo+20 zoom1.4", {"a": 20, "z": 1.4}),
       ("bordo3mm", {"bd": [3, "#ffffff"]}), ("bordo8mm nero", {"bd": [8, "#000000"]}), ("ombra40", {"sh": 40}), ("ombra100", {"sh": 100}), ("opacita50", {"oc": 50}),
       ("angolo15+bordo+ombra", {"a": 15, "bd": [4, "#ffffff"], "sh": 60}), ("angolo-10+zoom1.3+bordo", {"a": -10, "z": 1.3, "bd": [5, "#202020"]}), ("b/n+angolo", {"bw": True, "a": 8}),
       ("opacita60+ombra", {"oc": 60, "sh": 50})]
TXT = [("testo base", {"tx": "Battesimo di Serena"}), ("testo maiuscolo", {"tx": "Battesimo di Serena", "caps": True}), ("testo centrato", {"tx": "Battesimo di Serena", "al": "center"}),
       ("testo a destra", {"tx": "Battesimo di Serena", "al": "right"}), ("testo lungo 3 righe", {"tx": "Un giorno speciale per Serena, con tutta la famiglia riunita nella chiesa del paese per festeggiare insieme"}),
       ("testo interlinea 1.6", {"tx": "Un giorno speciale per Serena, con tutta la famiglia riunita nella chiesa", "lh": 1.6}), ("testo spaziato", {"tx": "Battesimo", "tr": 200}),
       ("testo grande", {"tx": "Serena", "size": 420}), ("testo colore", {"tx": "Battesimo di Serena", "col": [200, 30, 30]})]
if os.environ.get("SOLO_TESTO"): GEO = GEO[:1]
KT = float(os.environ.get("KT", 1.0))


def ink(a, thr=150):
    m = a.astype(int).sum(2) / 3 < thr; ys, xs = np.where(m)
    return (xs.min(), ys.min(), xs.max(), ys.max()) if xs.size else None


def shift(a, b, R=5):
    best = (1e9, 0, 0)
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            e = np.abs(np.roll(np.roll(a, dy, 0), dx, 1)[R:-R, R:-R] - b[R:-R, R:-R]).mean()
            if e < best[0]: best = (e, dx, dy)
    return best


def appiattisci(dest, ns, tmp):
    """apre i PSD in Photoshop e li salva come PNG piatti"""
    js = ('app.displayDialogs = DialogModes.NO; for (var k=1;k<=%d;k++){ var n=(k<10?"0":"")+k; var d=app.open(new File("%s/Spread_"+n+".psd")); var po=new PNGSaveOptions(); po.compression=0; '
          'd.saveAs(new File("%s/flat_"+n+".png"),po,true,Extension.LOWERCASE); d.close(SaveOptions.DONOTSAVECHANGES); } "ok";') % (ns, dest.replace("\\", "/"), dest.replace("\\", "/"))
    P.write_jsx(os.path.join(tmp, "flat.jsx"), js); r = P.run_jsx(os.path.join(tmp, "flat.jsx"), 3600); assert "ok" in r, r


def test_fedelta_geometria(home, apri_editor, tmp_path):
    p = home.nuovo({"nome": "Prova", "w": 70, "h": 25}); ch = campione()
    for k in range(len(GEO)): ch.save(os.path.join(p, "Foto", "G%03d.jpg" % k), quality=98, icc_profile=None)
    c = apri_editor(p)
    def op(o): o.update(cid="f", rev=c.get("/api/state")["rev"]); return c.post("/api/op", o)
    names = [x["n"] for x in c.get("/api/state")["photos"]]
    for k, nm in enumerate(names):
        t = c.post("/api/templates", {"photos": [nm]})["items"][0]; op({"op": "newspread", "pos": k, "L": t["L"], "R": t["R"]})
    st = c.get("/api/state")
    for si, (lab, prm) in enumerate(GEO):
        it = next(i for i in st["spreads"][si]["items"] if i["k"] != "t")
        op({"op": "free", "at": [si, it["side"], it["idx"]], "x": .15, "y": .15, "w": .6, "h": .6})
        o = {"op": "set", "at": [si, it["side"], it["idx"]]}; o.update(prm); op(o)
    n0 = len(GEO)
    for k, (lab, prm) in enumerate(TXT):
        op({"op": "blank", "pos": n0 + k}); op({"op": "addtext", "s": n0 + k, "fx": .1, "fy": .2, "fw": .35, "tx": prm["tx"]})
        it = next(i for i in c.get("/api/state")["spreads"][n0 + k]["items"] if i["k"] == "t"); o = {"op": "settext", "at": [n0 + k, it["side"], it["idx"]]}; o.update({a: b for a, b in prm.items() if a != "tx"})
        if len(o) > 2: op(o)
    c.post("/api/save"); ns = len(c.get("/api/state")["spreads"]); dest = str(tmp_path / "psd")
    c.post("/api/export", {"fmt": "psd", "range": f"1-{ns}", "dest": dest, "force": True}); L = attendi_log(c, 3600)
    assert all(os.path.exists(os.path.join(dest, "Spread_%02d.psd" % (k + 1))) for k in range(ns)), L[-5:]
    appiattisci(dest, ns, str(tmp_path))
    st = c.get("/api/state"); K = 0.5; fuori = []
    for si, (lab, prm) in enumerate(GEO):
        sp = st["spreads"][si]
        pv = Image.open(io.BytesIO(c.raw(f"/img/spread/{si}?k={K}&h={sp['h']}", timeout=600))).convert("RGB")
        ps = Image.open(os.path.join(dest, "flat_%02d.png" % (si + 1))).convert("RGB").resize(pv.size, Image.LANCZOS)
        a = np.asarray(pv).astype(np.int16); b = np.asarray(ps).astype(np.int16); df = np.abs(a - b).max(2)
        e, dx, dy = shift(a, b); bad = (df > 40).mean() * 100
        print("%-26s %7.2f %8.2f%% %6d,%d" % (lab, df.mean(), bad, dx, dy))
        if df.mean() > 3 or bad > 1.0 or abs(dx) + abs(dy) > 1: fuori.append(lab)
    K = KT
    for k, (lab, prm) in enumerate(TXT):
        si = n0 + k; sp = st["spreads"][si]
        pv = Image.open(io.BytesIO(c.raw(f"/img/spread/{si}?k={K}&h={sp['h']}", timeout=600))).convert("RGB")
        ps = Image.open(os.path.join(dest, "flat_%02d.png" % (si + 1))).convert("RGB").resize(pv.size, Image.LANCZOS)
        ia, ib = ink(np.asarray(pv), 170), ink(np.asarray(ps), 170)
        if not ia or not ib: fuori.append(lab + " (testo mancante)"); continue
        dd = [abs(int(u) - int(v)) for u, v in zip(ia, ib)]
        print("%-26s %s | %s | %s" % (lab, tuple(int(v) for v in ia), tuple(int(v) for v in ib), dd))
        if max(dd) > 8: fuori.append(lab)
    assert not fuori, f"casi fuori soglia: {fuori}"
