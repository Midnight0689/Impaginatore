# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow==13.0.0"]
# ///
"""Ricostruisce le foto dimostrative di Impaginatore a partire da FONTI.csv.

Per ogni riga del CSV lo script:
1. scarica l'originale dall'indirizzo pubblico della fonte (colonna url_download);
2. applica l'eventuale ritaglio (colonna ritaglio, frazioni x0,y0,x1,y1);
3. porta il lato lungo a 3000 px e converte in sRGB;
4. scrive l'EXIF (DateTimeOriginal dalla colonna data_scatto, autore e fonte);
5. salva foto/DEMO_nnnn.jpg e ne controlla lo sha256 con quello del CSV.

Usa solo la libreria standard e Pillow (versione fissata qui sopra, così la
codifica JPEG è identica da un computer all'altro). Uso:

    uv run marketing/demo/scarica_demo.py            # rigenera foto/ e provini.jpg
    uv run marketing/demo/scarica_demo.py --solo DEMO_0003.jpg
    uv run marketing/demo/scarica_demo.py --aggiorna-hash   # riscrive sha256 nel CSV

Esce con codice 1 se un download fallisce o se uno sha256 non corrisponde.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageCms, ImageDraw, ImageOps

QUI = Path(__file__).resolve().parent
LATO_LUNGO = 3000
QUALITA = 85
USER_AGENT = "Mozilla/5.0 (compatible; scarica-demo/1.0)"
COLONNE = [
    "file", "fonte", "url_pagina", "autore", "licenza", "data_scaricamento", "note",
    "url_download", "ritaglio", "data_scatto", "sha256",
]
SRGB = ImageCms.createProfile("sRGB")


def scarica(url: str, cache: Path | None) -> bytes:
    nome = hashlib.sha1(url.encode()).hexdigest() + ".jpg"
    if cache and (cache / nome).exists():
        return (cache / nome).read_bytes()
    richiesta = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for tentativo in range(4):
        try:
            with urllib.request.urlopen(richiesta, timeout=120) as risposta:
                dati = risposta.read()
            break
        except OSError:
            if tentativo == 3:
                raise
            time.sleep(2 ** tentativo)
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / nome).write_bytes(dati)
    return dati


def in_srgb(img: Image.Image) -> Image.Image:
    profilo = img.info.get("icc_profile")
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if profilo:
        sorgente = ImageCms.ImageCmsProfile(io.BytesIO(profilo))
        img = ImageCms.profileToProfile(img, sorgente, SRGB, outputMode="RGB")
    return img.convert("RGB")


def elabora(dati: bytes, riga: dict) -> bytes:
    img = Image.open(io.BytesIO(dati))
    profilo = img.info.get("icc_profile")
    img = ImageOps.exif_transpose(img)
    if profilo:
        img.info["icc_profile"] = profilo
    img = in_srgb(img)
    if riga["ritaglio"].strip():
        x0, y0, x1, y1 = (float(v) for v in riga["ritaglio"].split(","))
        w, h = img.size
        img = img.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
    if max(img.size) > LATO_LUNGO:
        fattore = LATO_LUNGO / max(img.size)
        img = img.resize((round(img.width * fattore), round(img.height * fattore)), Image.LANCZOS)

    quando = riga["data_scatto"].replace("-", ":")  # "AAAA:MM:GG HH:MM:SS"
    exif = Image.Exif()
    exif[0x010E] = riga["url_pagina"]  # ImageDescription
    exif[0x013B] = riga["autore"]  # Artist
    exif[0x8298] = f"{riga['autore']} / {riga['fonte']} - {riga['licenza']}"  # Copyright
    exif[0x0131] = "scarica_demo.py"  # Software
    exif[0x0132] = quando  # DateTime
    sotto = exif.get_ifd(0x8769)
    sotto[0x9003] = quando  # DateTimeOriginal
    sotto[0x9004] = quando  # DateTimeDigitized
    sotto[0x9291] = "00"  # SubSecTimeOriginal
    sotto[0x9011] = "+02:00"  # OffsetTimeOriginal

    uscita = io.BytesIO()
    img.save(uscita, "JPEG", quality=QUALITA, optimize=True, exif=exif.tobytes())
    return uscita.getvalue()


def provini(file: list[Path], destinazione: Path) -> None:
    colonne, cella, margine = 8, 300, 6
    righe = (len(file) + colonne - 1) // colonne
    foglio = Image.new("RGB", (colonne * (cella + margine) + margine,
                               righe * (cella + 24 + margine) + margine), "white")
    disegno = ImageDraw.Draw(foglio)
    for i, percorso in enumerate(file):
        with Image.open(percorso) as img:
            img.thumbnail((cella, cella))
            x = margine + (i % colonne) * (cella + margine)
            y = margine + (i // colonne) * (cella + 24 + margine)
            foglio.paste(img, (x + (cella - img.width) // 2, y + (cella - img.height) // 2))
            disegno.text((x + 2, y + cella + 4), percorso.stem, fill="black")
    foglio.save(destinazione, "JPEG", quality=80, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=QUI / "FONTI.csv")
    parser.add_argument("--uscita", type=Path, default=QUI / "foto")
    parser.add_argument("--provini", type=Path, default=QUI / "provini.jpg")
    parser.add_argument("--cache", type=Path, help="cartella dove tenere gli originali scaricati")
    parser.add_argument("--solo", help="elenco di file separati da virgola")
    parser.add_argument("--aggiorna-hash", action="store_true",
                        help="scrive nel CSV lo sha256 dei file prodotti invece di controllarlo")
    args = parser.parse_args()

    with args.csv.open(newline="", encoding="utf-8") as f:
        righe = list(csv.DictReader(f))
    solo = set(args.solo.split(",")) if args.solo else None
    args.uscita.mkdir(parents=True, exist_ok=True)

    errori = 0
    for riga in righe:
        if solo and riga["file"] not in solo:
            continue
        try:
            jpeg = elabora(scarica(riga["url_download"], args.cache), riga)
        except Exception as e:  # noqa: BLE001 - si segnala e si prosegue con le altre
            print(f"ERRORE {riga['file']}: {e}", file=sys.stderr)
            errori += 1
            continue
        (args.uscita / riga["file"]).write_bytes(jpeg)
        impronta = hashlib.sha256(jpeg).hexdigest()
        if args.aggiorna_hash:
            riga["sha256"] = impronta
            esito = "hash aggiornato"
        elif riga["sha256"] and riga["sha256"] != impronta:
            esito = "DIVERSO dal CSV"
            errori += 1
        else:
            esito = "ok"
        print(f"{riga['file']}  {len(jpeg) / 1e6:5.2f} MB  {esito}")

    if args.aggiorna_hash:
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            scrittore = csv.DictWriter(f, fieldnames=COLONNE, lineterminator="\n")
            scrittore.writeheader()
            scrittore.writerows(righe)

    if not solo:
        presenti = [args.uscita / r["file"] for r in righe if (args.uscita / r["file"]).exists()]
        provini(presenti, args.provini)
        print(f"provini: {args.provini} ({len(presenti)} foto)")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
