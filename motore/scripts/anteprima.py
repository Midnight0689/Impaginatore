"""Controllo e anteprime dell'impaginazione descritta in spec.py.

python anteprima.py --progetto <cartella> [--nome "v1"] [--spread 6,7,8] [--prima-dopo 3,4] [--tolte _DSC1234,_DSC5678]

Fa sempre il controllo: spazi tutti uguali a G (spazi più grandi solo se sono margini bianchi voluti), nessuna foto doppia,
foto della selezione non usate (escluse quelle tolte apposta con --tolte o "tolte" in progetto.json), ritagli molto forti.
Poi salva in <progetto>/Anteprime/:
- "Anteprima <nome>.jpg" con tutti gli spread (2 per riga), con le correzioni di luminosità applicate
- "Sequenza <nome>.txt" con le foto spread per spread (pagina immersiva / bianca, BN, al vivo)
- con --spread: un'immagine più grande solo di quegli spread (per mandare al cliente le modifiche)
- con --prima-dopo: confronto senza / con correzioni di esposizione e bilanciamento del bianco
"""
import sys, os, argparse
from collections import Counter
from album import *
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(); ap.add_argument("--progetto"); ap.add_argument("--nome", default="")
ap.add_argument("--spread", default=""); ap.add_argument("--prima-dopo", default=""); ap.add_argument("--tolte", default="")
a = ap.parse_args()
SP = load_spec(); OUT = os.path.join(PROJ, "Anteprime"); os.makedirs(OUT, exist_ok=True)
FONT = lambda s: ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", s)
tolte = set(CFG.get("tolte", [])) | {x for x in a.tolte.split(",") if x}

# ---------- controllo ----------
seen = []; probs = 0
for k, sp in enumerate(SP):
    lay = layout(sp); ph = [i for i in lay if i["k"] != "t"]; seen += [name(i["i"]) for i in ph]
    for i in lay:
        if i["x"] < 0 or i["y"] < 0 or i["x"] + i["W"] > CW or i["y"] + i["H"] > CH: probs += 1; print(f"  S{k + 1:02d} fuori pagina: {name(i['i']) if i['k'] != 't' else 'testo'}")
        if i["k"] != "t" and i["x"] < FOLD < i["x"] + i["W"]: probs += 1; print(f"  S{k + 1:02d} foto a cavallo della piega: {name(i['i'])}")
    for i in ph:
        c = max(i["W"] / i["H"] / M[i["i"]]["ar"], M[i["i"]]["ar"] / (i["W"] / i["H"])) * i.get("z", 1)
        if c > 1.25: print(f"  S{k + 1:02d} ritaglio forte x{c:.2f} su {name(i['i'])} (controlla con analizza.py ritagli {k + 1})")
    for p in ph:
        for q in ph:
            vo = min(p["y"] + p["H"], q["y"] + q["H"]) - max(p["y"], q["y"]); ho = min(p["x"] + p["W"], q["x"] + q["W"]) - max(p["x"], q["x"])
            for g, ok in ((q["x"] - p["x"] - p["W"], vo > 0 and q["x"] >= p["x"] + p["W"]), (q["y"] - p["y"] - p["H"], ho > 0 and q["y"] >= p["y"] + p["H"])):
                # spazi diversi da G: errore, salvo i margini bianchi attorno alla piega (pagina bianca accanto a un'altra pagina)
                if ok and g != G and g < 400 and not (p["side"] != q["side"] and g in (2 * MG, MG + G // 2, MG + G - G // 2)):
                    probs += 1; print(f"  S{k + 1:02d} spazio {g}px tra {name(p['i'])} e {name(q['i'])}")
dup = [n for n, v in Counter(seen).items() if v > 1]
unused = [name(i) for i in range(len(M)) if name(i) not in seen and name(i) not in tolte]
print(f"documento {CW}x{CH}px @ {PPI:.2f} ppi = {CW / PPI * 2.54:.2f} x {CH / PPI * 2.54:.2f} cm | spazio {G}px, margine {MG}px, abbondanza {B}px")
print(f"spread {len(SP)}, foto usate {len(seen)}, doppie {dup}, non usate {unused}, problemi {probs}")

# ---------- anteprime ----------
def strip_bleed(S, K): b = round(B * K); return S.crop((b, b, S.width - b, S.height - b)) if b else S
def sheet(nums, K, path, label="Spread", corrected=True):
    ims = [(n, strip_bleed(render(SP[n - 1], K, corrected), K)) for n in nums]
    w, h = ims[0][1].size; cols = 2 if len(ims) > 1 else 1; rows = (len(ims) + cols - 1) // cols
    O = Image.new("RGB", (cols * (w + 30) + 30, rows * (h + 50) + 30), (150, 150, 150)); d = ImageDraw.Draw(O)
    for k, (n, im) in enumerate(ims):
        x = 30 + (k % cols) * (w + 30); y = 30 + (k // cols) * (h + 50); d.text((x, y), f"{label} {n}", fill="white", font=FONT(20)); O.paste(im, (x, y + 26))
    O.save(path, quality=88); print(path)
suffix = f" {a.nome}" if a.nome else ""
sheet(list(range(1, len(SP) + 1)), 0.13, os.path.join(OUT, f"Anteprima{suffix} - {len(SP)} spread.jpg"))
lines = []
for k, sp in enumerate(SP):
    it = layout(sp)
    def nm(side):
        mode = sp[0 if side == "L" else 1][0]
        s = ", ".join(("TESTO" if i["k"] == "t" else name(i["i"]) + (" (BN)" if i.get("bw") else "") + (" (al vivo)" if i["k"] == "full" else "")) for i in it if i["side"] == side)
        return ("[bianca] " if mode == "W" else "[immersiva] ") + s
    lines.append(f"Spread {k + 1:02d}  sx: {nm('L')}  |  dx: {nm('R')}")
open(os.path.join(OUT, f"Sequenza{suffix}.txt"), "w").write("\n".join(lines) + "\n")
if a.spread:
    nums = [int(x) for x in a.spread.split(",")]
    sheet(nums, 0.2, os.path.join(OUT, f"Modifiche spread {'-'.join(map(str, nums))}.jpg"))
if a.prima_dopo:
    for n in [int(x) for x in a.prima_dopo.split(",")]:
        p, q = strip_bleed(render(SP[n - 1], 0.15, False), 0.15), strip_bleed(render(SP[n - 1], 0.15, True), 0.15)
        O = Image.new("RGB", (p.width, 2 * p.height + 70), (120, 120, 120)); d = ImageDraw.Draw(O)
        d.text((8, 4), f"Spread {n} PRIMA", fill="white", font=FONT(20)); O.paste(p, (0, 28)); d.text((8, p.height + 38), "DOPO", fill="white", font=FONT(20)); O.paste(q, (0, p.height + 62))
        path = os.path.join(OUT, f"Prima-dopo spread {n}.jpg"); O.save(path, quality=88); print(path)
