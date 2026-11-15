"""Fedeltà anteprima ↔ Photoshop: il programma deve mostrare quello che poi esce nei PSD.

python tests/fedelta_psd.py [--soglia 2.0]

Crea una foto-campione (tasselli piatti di colore: grigi, toni saturi e pelle), ne fa tante copie con una regolazione diversa
(esposizione, contrasto, alteluci, ombre, bianchi, neri, temperatura, tinta, vibranza, saturazione, bianco e nero, tono, combinazioni),
esporta i PSD, li apre e appiattisce in Photoshop e confronta pixel per pixel (solo dentro i tasselli piatti) con l'anteprima.
Apre Photoshop: ci vogliono alcuni minuti. Esce con errore se uno scarto supera la soglia (livelli su 255)."""
import os, sys, io, json, time, shutil, subprocess, tempfile, argparse, urllib.request
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ap = argparse.ArgumentParser(); ap.add_argument("--soglia", type=float, default=2.0, help="scarto medio massimo ammesso (su 255)"); ap.add_argument("--max", type=float, default=10.0, help="scarto massimo ammesso su un singolo pixel piatto"); ARG = ap.parse_args()
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SCR = os.path.join(os.path.dirname(HERE), "motore", "scripts"); sys.path.insert(0, SCR)
TMP = tempfile.mkdtemp(prefix="fedelta_"); PY = sys.executable; procs = []
env = dict(os.environ, IMPAGINATORE_PROGETTI=TMP)
HP, EP = 8795, 8896
def call(port, path, body=None):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", None if body is None else json.dumps(body).encode(), {"content-type": "application/json"}); return json.load(urllib.request.urlopen(r, timeout=600))
def tasselli():
    W, H, n = 1800, 1200, 60; im = np.zeros((H, W, 3), np.uint8); cols = []
    cols += [(g, g, g) for g in np.linspace(0, 255, 30).round()]
    import colorsys
    for sv in ((1, 1), (.7, .9), (.4, 1), (1, .5), (.5, .6), (.25, .85), (.15, .4), (.8, .25), (.3, .2), (.1, .95), (.6, .75), (.9, .8), (.2, .7), (.5, .35), (.35, .55), (.7, .45), (.05, .6)):
        for k in range(30): cols.append(tuple(round(c * 255) for c in colorsys.hsv_to_rgb(k / 30, *sv)))
    skin = [(255, 224, 189), (241, 194, 125), (224, 172, 105), (198, 134, 66), (141, 85, 36), (255, 205, 148), (234, 192, 134), (255, 173, 96), (210, 150, 120), (180, 120, 90)]
    cols += skin + [(30, 30, 30), (60, 60, 60), (200, 200, 200), (240, 240, 240), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255)]
    cols = (cols + [(128, 128, 128)] * 600)[:600]
    for k, c in enumerate(cols): r, q = divmod(k, 30); im[r * n:(r + 1) * n, q * n:(q + 1) * n] = c
    return Image.fromarray(im)
R = lambda **k: ("rit", k)
CASI = [("base", {})]
for ev in (-2, -1, -.5, .5, 1, 2): CASI.append((f"ev{ev:+g}", {"ev": ev}))
for k in ("con", "alt", "omb", "bia", "ner", "tmp", "tnt", "vib", "sat"):
    for v in (-100, -50, 50, 100): CASI.append((f"{k}{v:+d}", {"rit": {k: v}}))
CASI += [("bw", {"bw": True}), ("bw+con60", {"bw": True, "rit": {"con": 60}}), ("bw+sat80", {"bw": True, "rit": {"sat": 80}}), ("ev1+tmp50", {"ev": 1, "rit": {"tmp": 50}}),
         ("tutto", {"ev": .5, "rit": {"con": 40, "alt": -30, "omb": 40, "bia": 20, "ner": -20, "tmp": 20, "tnt": -20, "vib": 30, "sat": 20}}),
         ("livelli", {"tono": {"b": 20, "w": 230, "m": 1.3}}), ("curva", {"tono": {"c": [[64, 40], [192, 220]]}}), ("tono+rit", {"ev": -.5, "tono": {"b": 10, "w": 245, "m": .8, "c": [[100, 90], [180, 200]]}, "rit": {"con": 30, "sat": -30}})]
def avvia():
    procs.append(subprocess.Popen([PY, os.path.join(HERE, "home.py"), "--porta", str(HP)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)); time.sleep(3)
    call(HP, "/api/nuovo", {"nome": "Prova", "w": 70, "h": 25}); fd = os.path.join(TMP, "Prova", "Foto"); ch = tasselli()
    for k in range(len(CASI)): ch.save(os.path.join(fd, "C%03d.jpg" % k), quality=98, icc_profile=None)
    procs.append(subprocess.Popen([PY, os.path.join(HERE, "editor.py"), "--progetto", os.path.join(TMP, "Prova"), "--porta", str(EP)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)); time.sleep(5)
def op(o): o.update(cid="f", rev=call(EP, "/api/state")["rev"]); return call(EP, "/api/op", o)
try:
    avvia(); names = [p["n"] for p in call(EP, "/api/state")["photos"]]; assert len(names) == len(CASI), len(names)
    for k in range(0, len(names), 8):
        ch = names[k:k + 8]; d = call(EP, "/api/templates", {"photos": ch}); t = next((x for x in d["items"] if x["L"]["module"] == "G4" and x["R"]["module"] == "G4"), d["items"][0]); op({"op": "newspread", "pos": k // 8, "L": t["L"], "R": t["R"]})
    for nm, (lab, p) in zip(names, CASI):
        if "ev" in p: op({"op": "ev", "photo": nm, "value": p["ev"]})
        for key, v in (p.get("rit") or {}).items(): op({"op": "rit", "photo": nm, "key": key, "value": v})
        if "tono" in p: op({"op": "tono", "photo": nm, "value": p["tono"]})
        if p.get("bw"):
            st = call(EP, "/api/state")
            for si, s in enumerate(st["spreads"]):
                for it in s["items"]:
                    if it.get("name") == nm: op({"op": "set", "at": [si, it["side"], it["idx"]], "bw": True})
    call(EP, "/api/save", {}); ns = len(call(EP, "/api/state")["spreads"]); dest = os.path.join(TMP, "psd")
    call(EP, "/api/export", {"fmt": "psd", "range": f"1-{ns}", "dest": dest, "force": True})
    for _ in range(3600):
        L = call(EP, "/api/log")
        if "[finito]" in L: break
        time.sleep(1)
    assert all(os.path.exists(os.path.join(dest, "Spread_%02d.psd" % (k + 1))) for k in range(ns)), L[-5:]
    import photoshop as P
    js = 'app.displayDialogs = DialogModes.NO; for (var k=1;k<=%d;k++){ var n=(k<10?"0":"")+k; var d=app.open(new File("%s/Spread_"+n+".psd")); var po=new PNGSaveOptions(); po.compression=0; d.saveAs(new File("%s/flat_"+n+".png"),po,true,Extension.LOWERCASE); d.close(SaveOptions.DONOTSAVECHANGES);} "ok";' % (ns, dest, dest)
    P.write_jsx(os.path.join(TMP, "flat.jsx"), js); r = P.run_jsx(os.path.join(TMP, "flat.jsx"), 3600); assert "ok" in r, r
    st = call(EP, "/api/state"); lab = {nm: l for nm, (l, _) in zip(names, CASI)}; K = 0.5; rows = []
    for si, sp in enumerate(st["spreads"]):
        pv = Image.open(io.BytesIO(urllib.request.urlopen(f"http://127.0.0.1:{EP}/img/spread/{si}?k={K}&h={sp['h']}", timeout=600).read())).convert("RGB")
        ps = Image.open(os.path.join(dest, "flat_%02d.png" % (si + 1))).convert("RGB").resize(pv.size, Image.LANCZOS)
        A_ = np.asarray(pv).astype(np.int16); B_ = np.asarray(ps).astype(np.int16)
        for it in sp["items"]:
            if it["k"] == "t": continue
            x0, y0, x1, y1 = [int(round(v * K)) for v in (it["x"], it["y"], it["x"] + it["w"], it["y"] + it["h"])]; m = 8
            a, b = A_[y0 + m:y1 - m, x0 + m:x1 - m], B_[y0 + m:y1 - m, x0 + m:x1 - m]
            # solo dentro i tasselli piatti: nessuna variazione nell'intorno 7x7 dell'anteprima
            mx = a.copy(); mn = a.copy(); H_, W_ = a.shape[:2]
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    sh = np.roll(np.roll(a, dy, 0), dx, 1); mx = np.maximum(mx, sh); mn = np.minimum(mn, sh)
            flat = ((mx - mn).max(2) <= 2); flat[:4] = flat[-4:] = False; flat[:, :4] = flat[:, -4:] = False
            e = np.abs(a - b).max(2)[flat]; rows.append((lab[it["name"]], e.mean() if e.size else -1, np.percentile(e, 99) if e.size else -1, e.max() if e.size else -1, int(flat.sum())))
    rows.sort(key=lambda r: -r[1]); ko = 0
    print("%-12s %8s %8s %8s %8s" % ("caso", "medio", "p99", "max", "pixel"))
    for l, m, p, mxv, n in rows:
        flag = "  <-- FUORI" if (m > ARG.soglia or mxv > ARG.max or n < 2000) else ""; ko += bool(flag)
        print("%-12s %8.2f %8.1f %8.0f %8d%s" % (l, m, p, mxv, n, flag))
    print(f"\n{len(rows) - ko} casi su {len(rows)} entro soglia (medio ≤ {ARG.soglia}, max ≤ {ARG.max})"); sys.exit(1 if ko else 0)
finally:
    for p in procs: p.terminate()
    shutil.rmtree(TMP, ignore_errors=True)
