"""Verifica i PSD come sono sul disco (anche se modificati a mano).

python verifica_psd.py --progetto <cartella> [--confronta-spec]

Per ogni PSD: dimensioni in px e cm, ppi, cornici, spazi tra le cornici (devono essere tutti = spazio di progetto,
a parte i margini bianchi voluti), foto a cavallo della piega, cornici fuori pagina, esposizioni, BN.
Su tutto l'album: foto doppie, foto della selezione non usate.
--confronta-spec: confronta anche le cornici con la spec (solo per PSD non toccati a mano: quelli modificati divergono apposta).
"""
import sys, os, glob, re
from collections import Counter
from psd_tools import PSDImage


if __name__ == "__main__":
    from impaginatore.motore import album as _album
    _album.carica_progetto(_album.progetto_da_argv())      # --progetto, ALBUM_PROGETTO o cartella corrente (come nelle 1.x)
    from impaginatore.motore.album import *
    OUT = CFG.get("uscita_psd") or os.path.join(PROJ, "PSD")
    cmp_spec = "--confronta-spec" in sys.argv
    SP = load_spec() if cmp_spec else None
    names_all = []; bad = 0
    for P in sorted(glob.glob(os.path.join(OUT, "Spread_*.psd"))):
        n = int(re.findall(r"(\d+)\.psd", P)[0]); psd = PSDImage.open(P); Wd, Hd = psd.size
        r = psd.image_resources.get_data(1005); ppi = r.horizontal / 65536 if r else 0
        fr = {}; info = []
        for g in psd.descendants():
            if g.is_group() and g.has_vector_mask() and not g.name.startswith("Pagina"):
                pts = [(q.anchor[1] * Wd, q.anchor[0] * Hd) for p in g.vector_mask.paths for q in p]
                fr[g.name] = tuple(round(v) for v in (min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)))
        for g in psd:
            if not g.is_group(): continue
            ls = list(g)
            for k, L in enumerate(ls):
                if L.is_group() and L.name in fr:
                    tags = []
                    for q in ls[k + 1:]:
                        if not q.clipping: break
                        tags.append(f"{q.exposure:+.2f}" if q.kind == "exposure" else ("BN" if q.kind == "blackandwhite" else ("WB" if q.kind == "channelmixer" else q.kind)))
                    info.append(L.name + (f" [{' '.join(tags)}]" if tags else ""))
        names_all += list(fr)
        issues = []
        R = list(fr.items())
        for na, a in R:
            if a[0] < FOLD < a[2] and (min(a[2], FOLD + G) - max(a[0], FOLD - G)) > G: issues.append(f"{na} a cavallo della piega")
            if a[0] < -2 or a[1] < -2 or a[2] > Wd + 2 or a[3] > Hd + 2: issues.append(f"{na} esce dalla pagina")
            for nb, b in R:
                if b[0] > a[2] and min(a[3], b[3]) > max(a[1], b[1]):
                    gap = b[0] - a[2]
                    if gap != G and gap < 400 and not (a[2] <= FOLD <= b[0] and gap in (2 * MG, MG + G // 2, MG + G - G // 2)): issues.append(f"spazio {gap}px {na}|{nb}")
                if b[1] > a[3] and min(a[2], b[2]) > max(a[0], b[0]):
                    gap = b[1] - a[3]
                    if gap != G and gap < 400: issues.append(f"spazio {gap}px {na}/{nb}")
        if (Wd, Hd) != (CW, CH): issues.append(f"misura {Wd}x{Hd} invece di {CW}x{CH}")
        if cmp_spec and n <= len(SP):
            exp = sorted((i["x"], i["y"], i["x"] + i["W"], i["y"] + i["H"]) for i in layout(SP[n - 1]) if i["k"] != "t")
            if sorted(fr.values()) != exp: issues.append("cornici diverse dalla spec (normale se modificato a mano)")
        if issues: bad += 1
        print(f"Spread {n:02d}: {Wd}x{Hd}px {Wd / ppi * 2.54:.2f}x{Hd / ppi * 2.54:.2f}cm @{ppi:.2f} | {', '.join(info)}" + (f"\n   <-- CONTROLLA: {'; '.join(issues)}" if issues else ""))
    dup = [k for k, v in Counter(names_all).items() if v > 1]
    unused = [name(i) for i in range(len(M)) if name(i) not in names_all and name(i) not in set(CFG.get("tolte", []))]
    print(f"\nfoto nei PSD {len(names_all)} | doppie {dup} | non usate {unused} | spread con problemi {bad}")
