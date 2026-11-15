"""Analisi delle foto del progetto.

python analizza.py --progetto <cartella> provini            -> _cache/provini_N.jpg: tutte le foto numerate in ordine di scatto (per guardarle e scegliere)
python analizza.py --progetto <cartella> luminosita         -> L* della pelle per foto, mediana per cartella/capitolo, foto fuori tono per spread
python analizza.py --progetto <cartella> ritagli 6,7,9      -> per ogni spread: le foto originali con la finestra di ritaglio in rosso (per controllare teste/piedi/persone tagliate)
python analizza.py --progetto <cartella> colore 20          -> esposizione e bilanciamento del bianco delle foto di uno spread (zone neutre a*/b*)
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageCms


if __name__ == "__main__":
    from impaginatore.motore import album as _album
    _album.carica_progetto(_album.progetto_da_argv())      # --progetto, ALBUM_PROGETTO o cartella corrente (come nelle 1.x)
    from impaginatore.motore.album import *
    args = [a for a in sys.argv[1:] if a != "--progetto" and os.path.abspath(a) != PROJ]
    cmd = args[0] if args else "provini"
    from impaginatore.piattaforma import font as _pfont
    FONT = _pfont.pil_ripiego                  # Helvetica sul Mac (come nelle 1.x), Arial su Windows, DejaVu su Linux
    _tr = ImageCms.buildTransformFromOpenProfiles(ImageCms.createProfile("sRGB"), ImageCms.createProfile("LAB"), "RGB", "LAB")
    def lab(im):
        # attenzione: in PIL a* e b* sono int8 complemento a due, NON uint8 con offset 128
        a = np.asarray(ImageCms.applyTransform(im.convert("RGB"), _tr))
        return a[..., 0].astype(float) * 100 / 255, a[..., 1].view(np.int8).astype(float), a[..., 2].view(np.int8).astype(float)
    def skin_L(im, i):
        fs = F.get(M[i]["n"], [])
        if not fs: return None
        W_, H_ = im.size; A = [(f[2] - f[0]) * (f[3] - f[1]) for f in fs]; big = max(A); vals = []
        for f, a in zip(fs, A):
            if a < big * 0.15: continue
            cx, cy = (f[0] + f[2]) / 2, (f[1] + f[3]) / 2; w, h = (f[2] - f[0]) * .25, (f[3] - f[1]) * .25
            vals.append(np.median(lab(im.crop((int((cx - w) * W_), int((cy - h) * H_), int((cx + w) * W_), int((cy + h) * H_))))[0]))
        return float(np.median(vals)) if vals else None
    def spreads_or_none():
        try: return load_spec()
        except Exception: return None

    if cmd == "provini":
        C = 300; per = 20
        for s in range(0, len(M), per):
            S = Image.new("RGB", (5 * (C + 10) + 10, 4 * (C + 40) + 10), (90, 90, 90)); d = ImageDraw.Draw(S)
            for k, m in enumerate(M[s:s + per]):
                t = Image.open(os.path.join(THUMBS, m["n"])); t.thumbnail((C, C)); x = 10 + (k % 5) * (C + 10); y = 10 + (k // 5) * (C + 40)
                S.paste(t, (x + (C - t.width) // 2, y + (C - t.height) // 2)); d.text((x, y + C + 6), f"{s + k + 1}  {m['n'].rsplit('.', 1)[0]}", fill=(255, 255, 0), font=FONT(20))
            p = os.path.join(CACHE, f"provini_{s // per + 1}.jpg"); S.save(p, quality=85); print(p)

    elif cmd == "luminosita":
        per_photo = {}
        for i, m in enumerate(M):
            v = skin_L(Image.open(os.path.join(THUMBS, m["n"])).convert("RGB"), i)
            if v is not None: per_photo[i] = v
        groups = {}
        for i, v in per_photo.items():
            groups.setdefault(os.path.basename(ORIGINE.get(M[i]["n"]) or os.path.dirname(M[i]["src"])), []).append(v)
        allv = list(per_photo.values())
        print(f"pelle L* mediana album {np.median(allv):.1f} (p10 {np.percentile(allv, 10):.1f}, p90 {np.percentile(allv, 90):.1f}), foto con volti {len(allv)}")
        for g, v in groups.items(): print(f"  cartella {g}: mediana {np.median(v):.1f} (n={len(v)})")
        SP = spreads_or_none()
        if SP:
            med = np.median(allv)
            for k, sp in enumerate(SP):
                v = [(name(it["i"]), per_photo[it["i"]]) for it in layout(sp) if it["k"] != "t" and not it.get("bw") and it["i"] in per_photo]
                if not v: continue
                sm = np.median([x for _, x in v]); out = [f"{a}:{x:.0f}" for a, x in v if abs(x - sm) > 8 or abs(x - med) > 14]
                print(f"S{k + 1:02d} pelle {sm:4.1f}  " + ", ".join(f"{a}:{x:.0f}" for a, x in v) + (f"   <== fuori tono: {out}" if out else ""))
        print("Nota: la lettura dei volti può sbagliare (falsi volti); conferma sempre guardando le immagini.")

    elif cmd == "ritagli":
        SP = load_spec()
        for n in [int(x) for x in args[1].split(",")]:
            S = render(SP[n - 1], 0.17); th = []
            for it in layout(SP[n - 1]):
                if it["k"] == "t": continue
                im = Image.open(os.path.join(THUMBS, M[it["i"]]["n"])).convert("RGB"); l, t, r, b = zcrop(it)
                im.thumbnail((400, 400)); d = ImageDraw.Draw(im)
                d.rectangle((l * im.width, t * im.height, r * im.width - 1, b * im.height - 1), outline=(255, 0, 0), width=3)
                d.text((5, 5), name(it["i"]), fill=(255, 255, 0), font=FONT(22)); th.append(im)
            w = max(S.width, sum(t.width + 10 for t in th)); h = max(t.height for t in th)
            R = Image.new("RGB", (w, S.height + h + 50), (90, 90, 90)); d = ImageDraw.Draw(R); d.text((5, 5), f"Spread {n}", fill="white", font=FONT(22))
            R.paste(S, (0, 30)); x = 0
            for t in th: R.paste(t, (x, S.height + 40)); x += t.width + 10
            p = os.path.join(CACHE, f"ritagli_{n:02d}.jpg"); R.save(p, quality=85); print(p)

    elif cmd == "colore":
        SP = load_spec(); n = int(args[1])
        for it in layout(SP[n - 1]):
            if it["k"] == "t": continue
            im = apply_ev(Image.open(os.path.join(THUMBS, M[it["i"]]["n"])).convert("RGB"), ev_for(it["i"]), WB.get(name(it["i"])))
            l, t, r, b = zcrop(it); im = im.crop((int(l * im.width), int(t * im.height), int(r * im.width), int(b * im.height))).resize((400, 400))
            L, A, Bb = lab(im); neu = (np.hypot(A, Bb) < 10) & (L > 50) & (L < 97)
            wb = f"neutri a*={A[neu].mean():+.1f} b*={Bb[neu].mean():+.1f}" if neu.any() else "nessuna zona neutra"
            # guadagni proposti (lineari) per portare i neutri a un grigio appena caldo, all'80% per non appiattire l'atmosfera
            if neu.any():
                lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
                rgb = lin(np.asarray(im).astype(float) / 255)[neu].mean(0); g = (np.array([1.012, 1.0, 0.985]) * rgb[1]) / rgb; g = 1 + (g - 1) * 0.8
                wb += f" -> guadagni proposti {[round(float(x), 3) for x in g]}"
            print(f"{name(it['i'])}: EV {ev_for(it['i']):+.2f} | L* medio {L.mean():.1f} | {wb}")
    else:
        print(__doc__)
