"""Abbina la selezione del cliente (spesso JPG web a bassa risoluzione) agli originali in alta e li copia in una cartella nuova.

uso: python abbina.py --web <cartella selezione> --originali <cartella1> [<cartella2> ...] --dest <cartella nuova>

Controlla, per ogni foto scelta:
- che esista negli originali (per nome file) e in quale cartella (capitolo);
- nomi doppi tra cartelle diverse (es. _DSC4141 in due capitoli: è successo!);
- che l'originale sia davvero in alta: se è identico byte per byte alla versione web o è piccolo,
  probabilmente non è stato riesportato da Lightroom -> lo segnala e NON copia;
- che sia la stessa immagine (confronto visivo su miniatura): se diversa, la segnala.
Scrive <dest>/origine.json con la cartella di origine di ogni file: album.py lo legge da lì
per sapere a quale capitolo appartiene ogni foto (serve per le correzioni di esposizione per cartella).
"""
import os, argparse, filecmp, shutil
from PIL import Image, ImageChops, ImageStat

from .. import formato


if __name__ == "__main__":
    from .album import limite_pixel
    Image.MAX_IMAGE_PIXELS = limite_pixel()          # come per le foto del progetto (VER-014): oltre, Pillow rifiuta il file

    ap = argparse.ArgumentParser(); ap.add_argument("--web", required=True); ap.add_argument("--originali", nargs="+", required=True)
    ap.add_argument("--dest", required=True); ap.add_argument("--lato-minimo", type=int, default=4000, help="lato lungo minimo in px per considerarla alta risoluzione")
    ap.add_argument("--prova", action="store_true", help="solo controllo, non copia niente")
    a = ap.parse_args()
    EXT = (".jpg", ".jpeg", ".tif", ".tiff", ".png")
    web = sorted(f for f in os.listdir(a.web) if f.lower().endswith(EXT) and not f.startswith("."))
    where = {}
    for d in a.originali:
        for f in os.listdir(d):
            if f.lower().endswith(EXT) and not f.startswith("."): where.setdefault(f, []).append(d)
    def thumb(p):
        with Image.open(p) as im: im.draft("L", (200, 200)); t = im.convert("L").resize((64, 64))          # file chiuso subito (VER-015)
        return t
    problems, ok, origine = [], [], {}
    for f in web:
        pw = os.path.join(a.web, f); cands = where.get(f, [])
        if not cands: problems.append(f"{f}: NON trovata negli originali"); continue
        if len(cands) > 1:
            # stesso nome in più cartelle: scegli quella visivamente uguale alla selezione
            diffs = sorted((ImageStat.Stat(ImageChops.difference(thumb(pw), thumb(os.path.join(d, f)))).mean[0], d) for d in cands)
            problems.append(f"{f}: nome presente in {len(cands)} cartelle -> uso {os.path.basename(diffs[0][1])} (differenza {diffs[0][0]:.1f})")
            src_dir = diffs[0][1]
        else: src_dir = cands[0]
        po = os.path.join(src_dir, f)
        with Image.open(po) as im: dim = im.size
        long_side = max(dim)
        if filecmp.cmp(pw, po, shallow=False):
            problems.append(f"{f}: l'originale è IDENTICO alla versione web -> forse non riesportato in alta"); continue
        if long_side < a.lato_minimo:
            problems.append(f"{f}: originale piccolo ({dim[0]}x{dim[1]}) -> controlla l'esportazione"); continue
        d = ImageStat.Stat(ImageChops.difference(thumb(pw), thumb(po))).mean[0]
        if d > 8: problems.append(f"{f}: l'originale è visivamente diverso dalla scelta (differenza {d:.1f}): post-produzione cambiata?")
        ok.append((f, po)); origine[f] = os.path.abspath(src_dir)
    print(f"selezione: {len(web)} foto | pronte da copiare: {len(ok)} | da controllare: {len(problems)}")
    for p in problems: print("  -", p)
    by = {}
    for f, d in origine.items(): by[os.path.basename(d)] = by.get(os.path.basename(d), 0) + 1
    print("per cartella:", by)
    if not a.prova and ok:
        os.makedirs(a.dest, exist_ok=True)
        for f, po in ok:
            dst = os.path.join(a.dest, f)
            if os.path.exists(dst) and not filecmp.cmp(dst, po, shallow=False): print("  esiste già diverso, non sovrascrivo:", f); continue
            shutil.copy2(po, dst)
        bad = [f for f, po in ok if not filecmp.cmp(os.path.join(a.dest, f), po, shallow=False)]
        formato.scrivi_json(os.path.join(a.dest, "origine.json"), origine, indent=1)          # atomico (BUG-005)
        print(f"copiate e verificate: {len(ok) - len(bad)} | errori di copia: {bad}")
