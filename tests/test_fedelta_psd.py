"""Fedeltà anteprima ↔ Photoshop dei colori: il programma deve mostrare quello che poi esce nei PSD (era tests/fedelta_psd.py
della 1.5).

Crea una foto-campione (tasselli piatti di colore: grigi, toni saturi e pelle), ne fa tante copie con una regolazione diversa
(esposizione, contrasto, alteluci, ombre, bianchi, neri, temperatura, tinta, vibranza, saturazione, bianco e nero, tono, combinazioni),
esporta i PSD, li apre e appiattisce in Photoshop e confronta pixel per pixel (solo dentro i tasselli piatti) con l'anteprima.
Apre Photoshop: gira solo dove c'è (pytest -m photoshop). Soglie: FEDELTA_SOGLIA (scarto medio, default 2.0 livelli su 255),
FEDELTA_MAX (scarto massimo su un pixel piatto, default 10)."""
import colorsys
import io
import os

import numpy as np
import pytest
from aiuti import attendi_log
from PIL import Image
from test_fedelta_geometria import appiattisci

from impaginatore.piattaforma import photoshop as pps

pytestmark = [pytest.mark.photoshop, pytest.mark.skipif(not pps.disponibile(), reason="serve Photoshop")]
Image.MAX_IMAGE_PIXELS = None
SOGLIA = float(os.environ.get("FEDELTA_SOGLIA", 2.0)); MAX = float(os.environ.get("FEDELTA_MAX", 10.0))


def tasselli():
    W, H, n = 1800, 1200, 60; im = np.zeros((H, W, 3), np.uint8); cols = []
    cols += [(g, g, g) for g in np.linspace(0, 255, 30).round()]
    for sv in ((1, 1), (.7, .9), (.4, 1), (1, .5), (.5, .6), (.25, .85), (.15, .4), (.8, .25), (.3, .2), (.1, .95), (.6, .75), (.9, .8), (.2, .7), (.5, .35), (.35, .55), (.7, .45), (.05, .6)):
        for k in range(30): cols.append(tuple(round(c * 255) for c in colorsys.hsv_to_rgb(k / 30, *sv)))
    skin = [(255, 224, 189), (241, 194, 125), (224, 172, 105), (198, 134, 66), (141, 85, 36), (255, 205, 148), (234, 192, 134), (255, 173, 96), (210, 150, 120), (180, 120, 90)]
    cols += skin + [(30, 30, 30), (60, 60, 60), (200, 200, 200), (240, 240, 240), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255)]
    cols = (cols + [(128, 128, 128)] * 600)[:600]
    for k, c in enumerate(cols): r, q = divmod(k, 30); im[r * n:(r + 1) * n, q * n:(q + 1) * n] = c
    return Image.fromarray(im)


CASI = [("base", {})]
for ev in (-2, -1, -.5, .5, 1, 2): CASI.append((f"ev{ev:+g}", {"ev": ev}))
for k in ("con", "alt", "omb", "bia", "ner", "tmp", "tnt", "vib", "sat"):
    for v in (-100, -50, 50, 100): CASI.append((f"{k}{v:+d}", {"rit": {k: v}}))
CASI += [("bw", {"bw": True}), ("bw+con60", {"bw": True, "rit": {"con": 60}}), ("bw+sat80", {"bw": True, "rit": {"sat": 80}}), ("ev1+tmp50", {"ev": 1, "rit": {"tmp": 50}}),
         ("tutto", {"ev": .5, "rit": {"con": 40, "alt": -30, "omb": 40, "bia": 20, "ner": -20, "tmp": 20, "tnt": -20, "vib": 30, "sat": 20}}),
         ("livelli", {"tono": {"b": 20, "w": 230, "m": 1.3}}), ("curva", {"tono": {"c": [[64, 40], [192, 220]]}}), ("tono+rit", {"ev": -.5, "tono": {"b": 10, "w": 245, "m": .8, "c": [[100, 90], [180, 200]]}, "rit": {"con": 30, "sat": -30}})]


def test_fedelta_colori(home, apri_editor, tmp_path):
    p = home.nuovo({"nome": "Prova", "w": 70, "h": 25}); ch = tasselli()
    for k in range(len(CASI)): ch.save(os.path.join(p, "Foto", "C%03d.jpg" % k), quality=98, icc_profile=None)
    c = apri_editor(p)
    def op(o): o.update(cid="f", rev=c.get("/api/state")["rev"]); return c.post("/api/op", o)
    names = [x["n"] for x in c.get("/api/state")["photos"]]; assert len(names) == len(CASI)
    for k in range(0, len(names), 8):
        d = c.post("/api/templates", {"photos": names[k:k + 8]}); t = next((x for x in d["items"] if x["L"]["module"] == "G4" and x["R"]["module"] == "G4"), d["items"][0])
        op({"op": "newspread", "pos": k // 8, "L": t["L"], "R": t["R"]})
    for nm, (lab, prm) in zip(names, CASI):
        if "ev" in prm: op({"op": "ev", "photo": nm, "value": prm["ev"]})
        for key, v in (prm.get("rit") or {}).items(): op({"op": "rit", "photo": nm, "key": key, "value": v})
        if "tono" in prm: op({"op": "tono", "photo": nm, "value": prm["tono"]})
        if prm.get("bw"):
            for si, s in enumerate(c.get("/api/state")["spreads"]):
                for it in s["items"]:
                    if it.get("name") == nm: op({"op": "set", "at": [si, it["side"], it["idx"]], "bw": True})
    c.post("/api/save"); ns = len(c.get("/api/state")["spreads"]); dest = str(tmp_path / "psd")
    c.post("/api/export", {"fmt": "psd", "range": f"1-{ns}", "dest": dest, "force": True}); L = attendi_log(c, 3600)
    assert all(os.path.exists(os.path.join(dest, "Spread_%02d.psd" % (k + 1))) for k in range(ns)), L[-5:]
    appiattisci(dest, ns, str(tmp_path))
    st = c.get("/api/state"); lab = {nm: lb for nm, (lb, _) in zip(names, CASI)}; K = 0.5; rows = []
    for si, sp in enumerate(st["spreads"]):
        pv = Image.open(io.BytesIO(c.raw(f"/img/spread/{si}?k={K}&h={sp['h']}", timeout=600))).convert("RGB")
        ps = Image.open(os.path.join(dest, "flat_%02d.png" % (si + 1))).convert("RGB").resize(pv.size, Image.LANCZOS)
        A_ = np.asarray(pv).astype(np.int16); B_ = np.asarray(ps).astype(np.int16)
        for it in sp["items"]:
            if it["k"] == "t": continue
            x0, y0, x1, y1 = [int(round(v * K)) for v in (it["x"], it["y"], it["x"] + it["w"], it["y"] + it["h"])]; m = 8
            a, b = A_[y0 + m:y1 - m, x0 + m:x1 - m], B_[y0 + m:y1 - m, x0 + m:x1 - m]
            mx = a.copy(); mn = a.copy()                      # solo dentro i tasselli piatti: nessuna variazione nell'intorno 7x7 dell'anteprima
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    sh = np.roll(np.roll(a, dy, 0), dx, 1); mx = np.maximum(mx, sh); mn = np.minimum(mn, sh)
            flat = ((mx - mn).max(2) <= 2); flat[:4] = flat[-4:] = False; flat[:, :4] = flat[:, -4:] = False
            e = np.abs(a - b).max(2)[flat]; rows.append((lab[it["name"]], e.mean() if e.size else -1, np.percentile(e, 99) if e.size else -1, e.max() if e.size else -1, int(flat.sum())))
    rows.sort(key=lambda r: -r[1]); fuori = []
    for lb, mval, pval, mxv, n in rows:
        print("%-12s %8.2f %8.1f %8.0f %8d" % (lb, mval, pval, mxv, n))
        if mval > SOGLIA or mxv > MAX or n < 2000: fuori.append(lb)
    assert not fuori, f"{len(fuori)} casi fuori soglia (medio ≤ {SOGLIA}, max ≤ {MAX}): {fuori}"
