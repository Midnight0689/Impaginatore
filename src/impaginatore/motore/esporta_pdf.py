"""PDF leggero da mandare al cliente (WhatsApp): esporta i PSD COME SONO (anche modificati a mano) tramite Photoshop
e li impagina in un PDF, con una prima pagina di copertina.

python esporta_pdf.py --progetto <cartella> --nome "Album Anita - definitivo" [--copertina _DSC8814] [--copertina _DSC9383,_DSC9376]
    una foto  -> pagina "copertina"; due o più -> pagina "ipotesi di copertina" con A, B, ...
    le foto di copertina possono essere nomi della selezione/foto_extra oppure percorsi completi di file

I PSD vengono solo aperti e chiusi SENZA salvare. Documenti aperti in Photoshop vengono saltati (e segnalati).
Risultato ~5 MB per 25 pagine (2000 px di larghezza, JPEG 72).
"""
import os, glob, argparse, json
from PIL import Image, ImageDraw, ImageFont, ImageOps


if __name__ == "__main__":
    from impaginatore.motore import album as _album
    _album.carica_progetto(_album.progetto_da_argv())      # --progetto, ALBUM_PROGETTO o cartella corrente (come nelle 1.x)
    from impaginatore.motore.album import *
    from impaginatore.motore import photoshop as PS
    ap = argparse.ArgumentParser(); ap.add_argument("--progetto"); ap.add_argument("--nome", default="Album - bozza"); ap.add_argument("--copertina", default="")
    ap.add_argument("--larghezza", type=int, default=2000)
    a = ap.parse_args()
    OUT = CFG.get("uscita_psd") or os.path.join(PROJ, "PSD")
    X = os.path.join(CACHE, "export_pdf"); os.makedirs(X, exist_ok=True)
    for f in glob.glob(os.path.join(X, "Spread_*.jpg")): os.remove(f)
    js = r"""
app.displayDialogs=DialogModes.NO; var out=[], open={};
for (var i=0;i<app.documents.length;i++) open[app.documents[i].name]=1;
var f=new Folder(""" + json.dumps(OUT) + r""").getFiles("Spread_*.psd"); f.sort();
for (var i=0;i<f.length;i++){ var nm=decodeURI(f[i].name); if (open[nm]) { out.push("SALTATO (aperto): "+nm); continue; }
  var d=app.open(f[i]); var o=new JPEGSaveOptions(); o.quality=10; o.embedColorProfile=true;
  d.saveAs(new File(""" + json.dumps(X) + r"""+"/"+nm.replace(".psd",".jpg")),o,true); d.close(SaveOptions.DONOTSAVECHANGES); out.push(nm); }
out.join("\n");
"""
    jsx = os.path.join(CACHE, "esporta.jsx"); PS.write_jsx(jsx, js); res = PS.run_jsx(jsx)
    for line in res.splitlines():
        if line.startswith("SALTATO"): print(line)
    files = sorted(glob.glob(os.path.join(X, "Spread_*.jpg")))
    Wp = a.larghezza; Hs = round(Wp * CH / CW); PH = Hs + 60
    T = CFG.get("testo", {}); INKc = tuple(T.get("colore", [58, 54, 51]))
    serif = ImageFont.truetype(T.get("file_font_titolo") or SERIF_FILE, 46)
    sans = ImageFont.truetype(T.get("file_font_testo") or SANS_FILE, 24, index=T.get("indice_font_testo", 7))
    pages = []
    covers = [c for c in a.copertina.split(",") if c]
    if covers:
        def cover_path(c): return c if os.path.exists(c) else M[IDX[c] - 1]["src"]
        pg = Image.new("RGB", (Wp, PH), "white"); d = ImageDraw.Draw(pg)
        title = (TITLE[0] + " · " if TITLE[0] else "") + ("copertina" if len(covers) == 1 else "ipotesi di copertina")
        d.text((Wp / 2, 28), title, font=serif, fill=INKc, anchor="mt")
        top, bottom, margin, gap = 105, PH - 55, 60, 60
        boxw = (Wp - 2 * margin - gap * (len(covers) - 1)) // len(covers)
        for k, c in enumerate(covers):
            im = ImageOps.exif_transpose(Image.open(cover_path(c))).convert("RGB"); im.thumbnail((boxw, bottom - top), Image.LANCZOS)
            x = margin + k * (boxw + gap) + (boxw - im.width) // 2; y = top + (bottom - top - im.height) // 2; pg.paste(im, (x, y))
            if len(covers) > 1: d.text((x + im.width / 2, y + im.height + 12), f"{chr(65 + k)}  ·  {os.path.basename(c).rsplit('.', 1)[0]}", font=sans, fill=INKc, anchor="mt")
        pages.append(pg)
    for k, f in enumerate(files):
        im = Image.open(f).convert("RGB"); im.draft("RGB", (Wp, Hs)); im = im.resize((Wp, Hs), Image.LANCZOS)
        p = Image.new("RGB", (Wp, PH), "white"); p.paste(im, (0, 0)); d = ImageDraw.Draw(p)
        d.line([(Wp // 2, 0), (Wp // 2, Hs)], fill=(225, 225, 225), width=1)
        d.text((Wp / 2, Hs + 18), f"Spread {k + 1} / {len(files)}", font=sans, fill=(140, 140, 140), anchor="mt"); pages.append(p)
    P = os.path.join(PROJ, a.nome + ".pdf")
    pages[0].save(P, save_all=True, append_images=pages[1:], quality=72, resolution=150, optimize=True)
    pages[0].save(os.path.join(CACHE, "pdf_pagina1.jpg"), quality=85)
    print(f"{P}\n{len(pages)} pagine, {os.path.getsize(P) / 1e6:.1f} MB (controlla {os.path.join(CACHE, 'pdf_pagina1.jpg')})")
