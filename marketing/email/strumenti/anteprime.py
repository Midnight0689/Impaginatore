"""Rende ogni email con Chrome senza interfaccia: 600 e 375 px, tema chiaro e scuro, e compone una tavola.

Uso, dalla cartella marketing/email/:
    uv run --with pillow python strumenti/anteprime.py [nome …]

Riempie i segnaposto con gli esempi di converti.py (più strumenti/dati-esempio.json), punta
{{base_immagini}} alla cartella immagini/ locale e salva anteprime/<nome>.png con quattro colonne:
600 chiaro · 600 scuro · 375 chiaro · 375 scuro. I file intermedi vanno in una cartella temporanea.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import converti  # noqa: E402

CARTELLA = Path(__file__).resolve().parents[1]
CHROME = os.environ.get("CHROME", "google-chrome")
ALTEZZA_FINESTRA = 7000


def valori(nome: str) -> dict[str, str]:
    v = converti.esempi(nome)
    esempio = CARTELLA / "strumenti" / "dati-esempio.json"
    if esempio.exists():
        v.update(converti.per_lingua(converti.carica_json(esempio), nome))
    v["base_immagini"] = (CARTELLA / "immagini").as_uri()
    return v


def scatta(html: Path, larghezza: int, scuro: bool, uscita: Path) -> Image.Image:
    # Chrome senza interfaccia non stringe la finestra sotto i 500 px circa: l'email si rende quindi
    # in un iframe largo esattamente quanto il telefono o il client, e le media query lo seguono.
    cornice = uscita.with_suffix(".cornice.html")
    cornice.write_text(
        '<!doctype html><html><body style="margin:0;background:#808080">'
        f'<iframe src="{html.as_uri()}" width="{larghezza}" height="{ALTEZZA_FINESTRA}" '
        'style="border:0;display:block"></iframe></body></html>', encoding="utf-8")
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
        "--allow-file-access-from-files", f"--blink-settings=preferredColorScheme={0 if scuro else 1}",
        f"--window-size=800,{ALTEZZA_FINESTRA}", f"--screenshot={uscita}", cornice.as_uri(),
    ], check=True, capture_output=True, timeout=120)
    im = Image.open(uscita).convert("RGB")
    im = im.crop((0, 0, larghezza, im.height))
    # Taglia in basso due fasce uniformi: il grigio sotto l'iframe, poi il fondo vuoto dell'email.
    px = im.load()
    y = im.height - 1
    for _ in range(2):
        fondo = px[0, y]
        while y > 0 and all(px[x, y] == fondo for x in range(0, im.width, 3)):
            y -= 1
    return im.crop((0, 0, im.width, min(im.height, y + 32)))


def tavola(nome: str, immagini: list[tuple[str, Image.Image]]) -> Image.Image:
    margine, testata = 24, 40
    larghezza = sum(i.width for _, i in immagini) + margine * (len(immagini) + 1)
    altezza = max(i.height for _, i in immagini) + testata + margine
    t = Image.new("RGB", (larghezza, altezza), "#808080")
    d = ImageDraw.Draw(t)
    try:
        f = ImageFont.truetype(str(CARTELLA.parents[1] / "brand" / "font" / "IBMPlexMono-Medium.ttf"), 16)
    except OSError:
        f = ImageFont.load_default()
    x = margine
    for etichetta, im in immagini:
        d.text((x, 12), f"{nome} · {etichetta}", font=f, fill="#FFFFFF")
        t.paste(im, (x, testata))
        x += im.width + margine
    return t


def main(nomi: list[str]) -> None:
    uscita = CARTELLA / "anteprime"
    uscita.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for h in sorted((CARTELLA / "html").glob("*.html")):
            if nomi and h.stem not in nomi:
                continue
            reso = tmp / h.name
            reso.write_text(converti.riempi(h.read_text(encoding="utf-8"), valori(h.stem), True), encoding="utf-8")
            pannelli = []
            for larghezza in (600, 375):
                for scuro in (False, True):
                    im = scatta(reso, larghezza, scuro, tmp / f"{h.stem}-{larghezza}-{int(scuro)}.png")
                    pannelli.append((f"{larghezza} px {'scuro' if scuro else 'chiaro'}", im))
            t = tavola(h.stem, pannelli)
            t = t.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            t.save(uscita / f"{h.stem}.png", optimize=True)
            print(f"anteprime/{h.stem}.png  {t.width}×{t.height}  {(uscita / f'{h.stem}.png').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1:])
