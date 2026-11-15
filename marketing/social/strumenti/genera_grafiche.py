"""Rende in PNG i modelli grafici dei social (marketing/social/modelli/*.html e modelli/uscite/*.html).

Uso, dalla radice del repository:
    uv run --no-project --with pillow python marketing/social/strumenti/genera_grafiche.py            # tutto
    uv run --no-project --with pillow python marketing/social/strumenti/genera_grafiche.py post-verticale scheda-prezzo
    uv run --no-project --with pillow python marketing/social/strumenti/genera_grafiche.py --solo-anteprime

Serve Google Chrome (o Chromium; variabile CHROME per un percorso diverso). Come in brand/strumenti, Chrome
senza interfaccia rende la pagina; qui la finestra è più alta di 87 px perché la vista di --headless=new è
più bassa della finestra (STYLEBOOK §18), e il PNG si ritaglia alla misura esatta della tela.

Ogni modello dichiara nella testa:
    <meta name="tela"   content="1080x1350">        misura del PNG, in pixel
    <meta name="temi"   content="chiaro scuro">     varianti di tema (predefinito: chiaro)
    <meta name="lingue" content="it en">            varianti di lingua (predefinito: it)
    <meta name="zone"   content="griglia-3x4">       zone di sicurezza da controllare nelle anteprime
    <meta name="uso"    content="…">                 dove si usa (finisce nell'indice del README)
    <meta name="mcp"    content="sì">                solo per i contenuti sulla bozza con Claude

Nei modelli i numeri del listino non si scrivono a mano: un elemento con data-valore="pro.lancio" riceve
il valore da docs/mercato/tier.json (strumenti/listino.py), e così i {{segnaposto}} nel testo.

Uscite:
    grafiche/<nome>[-scuro][.en].png          un file per tema e lingua
    anteprime/telefono-<gruppo>.png             tavole alla misura di un telefono (430 px di larghezza utile)
    anteprime/zone-<gruppo>.png                 le stesse tavole con le zone di sicurezza disegnate sopra
    anteprime/contrasti.txt                     coppie di colori usate nei modelli e rapporto WCAG
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import listino  # noqa: E402

RADICE = listino.RADICE
SOCIAL = listino.SOCIAL
MODELLI = SOCIAL / "modelli"
GRAFICHE = SOCIAL / "grafiche"
ANTEPRIME = SOCIAL / "anteprime"
FONTE_CARATTERI = RADICE / "brand" / "font"
SCARTO_VISTA = 87  # px che --headless=new toglie alla vista rispetto alla finestra
PESO_MASSIMO = 1000 * 1024  # oltre 1 MB lo script lo dice: conta per il caricamento, non per git

# Zone di sicurezza, in frazioni della tela o in pixel su 1080 di larghezza. Fonti in STRATEGIA.md §6.
ZONE = {
    # Storie e reel 1080 × 1920: 250 px in alto e 340 px in basso coperti dall'interfaccia (Sprout Social, 2/11/2026).
    "storia": [("alto", 0, 0, 1, 250 / 1920), ("basso", 0, 1 - 340 / 1920, 1, 1)],
    # Griglia del profilo Instagram in 3:4: da un 4:5 si perdono 34 px per lato; da un 1:1, 135 px per lato.
    "griglia-3x4": ["ritaglio-3x4"],
    # Copertina del reel: nella griglia si vede il 3:4 centrale (1080 × 1440 di 1080 × 1920).
    "reel-griglia": ["ritaglio-3x4"],
    # Immagine del profilo: si vede il cerchio inscritto.
    "cerchio": ["cerchio"],
    # Banner YouTube 2560 × 1440: si vede ovunque solo il centro 1546 × 423.
    "youtube-banner": ["centro:1546x423"],
    # Copertina Facebook 851 × 315 (qui a 2x): sul telefono si vede il 640 × 360, cioè il centro largo 560/851.
    "facebook-mobile": ["centro-larghezza:0.658"],
    # Miniatura video: in basso a destra YouTube mette la durata.
    "miniatura": [("durata", 0.82, 0.86, 0.98, 0.96)],
}

# Coppie di colori usate nei modelli (primo piano, fondo, uso, soglia): controllate con la formula WCAG 2.2.
COPPIE = [
    ("carta-900", "carta-50", "chiaro: titoli e testo su Carta", 4.5),
    ("carta-600", "carta-50", "chiaro: testo secondario su Carta", 4.5),
    ("carta-500", "carta-50", "chiaro: etichette su Carta", 4.5),
    ("verde-600", "carta-50", "chiaro: etichetta verde, cifre su Carta", 4.5),
    ("carta-50", "verde-600", "chiaro: pulsante verde", 4.5),
    ("carta-50", "carta-900", "chiaro: «una volta» su Inchiostro", 4.5),
    ("carta-900", "carta-0", "chiaro: testo nelle card", 4.5),
    ("carta-600", "carta-0", "chiaro: testo secondario nelle card", 4.5),
    ("verde-600", "carta-0", "quote verdi sullo spread (anche in scuro: lo spread è carta)", 4.5),
    ("ocra-600", "carta-0", "quote ocra sullo spread", 4.5),
    ("carta-50", "carta-900", "scuro: titoli e testo su Inchiostro", 4.5),
    ("carta-300", "carta-900", "scuro: testo secondario su Inchiostro", 4.5),
    ("carta-400", "carta-900", "scuro: etichette su Inchiostro", 4.5),
    ("verde-300", "carta-900", "scuro: etichetta verde, cifre su Inchiostro", 4.5),
    ("carta-950", "verde-400", "scuro: pulsante verde", 4.5),
    ("carta-900", "carta-50", "scuro: «una volta» su Carta", 4.5),
    ("carta-50", "carta-800", "scuro: testo nelle card", 4.5),
    ("carta-300", "carta-800", "scuro: testo secondario nelle card", 4.5),
    ("verde-300", "carta-900", "scuro: segni di piega su Inchiostro (grafica)", 3.0),
    ("verde-600", "carta-50", "chiaro: segni di piega su Carta (grafica)", 3.0),
]


def chrome() -> str:
    c = os.environ.get("CHROME") or shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not c:
        sys.exit("Serve Google Chrome o Chromium (oppure la variabile CHROME).")
    return c


def meta(html: str, nome: str, predefinito: str = "") -> str:
    m = re.search(rf'<meta\s+name="{nome}"\s+content="([^"]*)"', html)
    return m.group(1).strip() if m else predefinito


def modelli(nomi: list[str]) -> list[Path]:
    tutti = sorted(p for p in MODELLI.glob("*.html") if not p.name.startswith("_"))
    tutti += sorted(p for p in (MODELLI / "uscite").glob("*.html") if not p.name.startswith("_"))
    if nomi:
        tutti = [p for p in tutti if p.stem in nomi]
        mancanti = set(nomi) - {p.stem for p in tutti}
        if mancanti:
            sys.exit(f"modelli inesistenti: {', '.join(sorted(mancanti))}")
    return tutti


def prepara(html: str, sorgente: Path, lingua: str, tema: str) -> tuple[str, list[str]]:
    """Valori del listino, lingua, tema, base per i percorsi relativi; segnala le foto che mancano."""
    v = listino.valori(lingua)
    avvisi: list[str] = []

    def valore(m: re.Match) -> str:
        chiave = m.group(3)
        if chiave not in v:
            raise KeyError(f"{sorgente.name}: data-valore sconosciuto «{chiave}»")
        # Un valore ancora vuoto (es. prezzi Rosetta da approvare) si vede come segnaposto, non come prezzo.
        testo = v[chiave] or f'<span class="segnaposto-valore">{{{{{chiave}}}}}</span>'
        return f"{m.group(1)}{testo}{m.group(5)}"

    html = re.sub(r'(<(\w+)\b[^>]*\bdata-valore="([^"]+)"[^>]*>)(.*?)(</\2>)', valore, html, flags=re.S)
    html = listino.sostituisci(html, lingua)
    tema_attr = ' data-theme="dark"' if tema == "scuro" else ' data-theme="light"'
    html = re.sub(r"<html\b[^>]*>", f'<html lang="{lingua}"{tema_attr}>', html, count=1)
    html = html.replace("<head>", f'<head><base href="{sorgente.parent.as_uri()}/">', 1)

    def foto(m: re.Match) -> str:
        src = m.group(2)
        if src.startswith(("data:", "http")):
            return m.group(0)
        if not (sorgente.parent / src).resolve().exists():
            avvisi.append(f"foto mancante: {src} (rigenerala con marketing/demo/scarica_demo.py)")
            return m.group(1) + m.group(2) + '" data-mancante="1'
        return m.group(0)

    html = re.sub(r'(<img\b[^>]*\bsrc=")([^"]+)', foto, html)
    return html, avvisi


def rendi(html: str, larghezza: int, altezza: int, uscita: Path, cartella: Path) -> None:
    from PIL import Image

    pagina = cartella / "pagina.html"
    pagina.write_text(html, encoding="utf-8")
    grezzo = cartella / "grezzo.png"
    subprocess.run(
        [chrome(), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--no-first-run",
         "--force-device-scale-factor=1", "--allow-file-access-from-files", "--virtual-time-budget=4000",
         f"--window-size={max(larghezza, 500)},{altezza + SCARTO_VISTA}", f"--screenshot={grezzo}", pagina.as_uri()],
        check=True, capture_output=True, timeout=180,
    )
    im = Image.open(grezzo).convert("RGB")
    if im.width < larghezza or im.height < altezza:
        raise RuntimeError(f"{uscita.name}: Chrome ha reso {im.width}×{im.height}, servono {larghezza}×{altezza}")
    im = im.crop((0, 0, larghezza, altezza))
    uscita.parent.mkdir(parents=True, exist_ok=True)
    im.save(uscita, optimize=True)
    if uscita.stat().st_size > PESO_MASSIMO:
        # grafiche/ non si versiona (vedi .gitignore): i PNG restano pieni, senza perdere qualità sulle foto.
        # Il limite più stretto fra i canali scelti è il banner YouTube, 6 MB.
        print(f"   {uscita.name}: {uscita.stat().st_size // 1024} KB (sotto i 6 MB del banner YouTube: va bene per caricarlo)")


def nome_uscita(sorgente: Path, tema: str, lingua: str) -> Path:
    sotto = "uscite/" if sorgente.parent.name == "uscite" else ""
    nome = sorgente.stem + ("-scuro" if tema == "scuro" else "") + (".en" if lingua == "en" else "")
    return GRAFICHE / f"{sotto}{nome}.png"


def genera(nomi: list[str]) -> list[dict]:
    fatti = []
    with tempfile.TemporaryDirectory(prefix="social-") as tmp:
        cartella = Path(tmp)
        for sorgente in modelli(nomi):
            html = sorgente.read_text(encoding="utf-8")
            tela = meta(html, "tela")
            if not re.fullmatch(r"\d+x\d+", tela):
                sys.exit(f"{sorgente.name}: manca <meta name=\"tela\" content=\"LxA\">")
            larghezza, altezza = map(int, tela.split("x"))
            for tema in meta(html, "temi", "chiaro").split():
                for lingua in meta(html, "lingue", "it").split():
                    pronto, avvisi = prepara(html, sorgente, lingua, tema)
                    uscita = nome_uscita(sorgente, tema, lingua)
                    rendi(pronto, larghezza, altezza, uscita, cartella)
                    for a in dict.fromkeys(avvisi):
                        print(f"   attenzione, {sorgente.name}: {a}")
                    print(f"{uscita.relative_to(SOCIAL)}  {larghezza}×{altezza}  {uscita.stat().st_size // 1024} KB")
                    fatti.append({"file": uscita, "l": larghezza, "a": altezza, "zone": meta(html, "zone").split(),
                                  "gruppo": meta(html, "gruppo", "varie"), "modello": sorgente.stem})
    return fatti


def elenco_esistenti() -> list[dict]:
    """Per rifare le anteprime senza rendere: rilegge i PNG già in grafiche/."""
    from PIL import Image

    fatti = []
    for sorgente in modelli([]):
        html = sorgente.read_text(encoding="utf-8")
        for tema in meta(html, "temi", "chiaro").split():
            for lingua in meta(html, "lingue", "it").split():
                f = nome_uscita(sorgente, tema, lingua)
                if f.exists():
                    w, h = Image.open(f).size
                    fatti.append({"file": f, "l": w, "a": h, "zone": meta(html, "zone").split(),
                                  "gruppo": meta(html, "gruppo", "varie"), "modello": sorgente.stem})
    return fatti


def disegna_zone(im, zone: list[str]):
    """Disegna sopra la miniatura le zone che l'interfaccia del canale copre o taglia."""
    from PIL import Image, ImageDraw

    w, h = im.size
    velo = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(velo)
    rosso = (182, 50, 43, 120)  # cinabro-600 semitrasparente: ciò che resta coperto o tagliato
    for z in zone:
        for parte in ZONE.get(z, []):
            if isinstance(parte, tuple):
                _, x0, y0, x1, y1 = parte
                d.rectangle([x0 * w, y0 * h, x1 * w, y1 * h], fill=rosso)
            elif parte == "ritaglio-3x4":
                if w / h > 3 / 4:  # più larga del 3:4: si tagliano i lati
                    vis = h * 3 / 4
                    m = (w - vis) / 2
                    d.rectangle([0, 0, m, h], fill=rosso)
                    d.rectangle([w - m, 0, w, h], fill=rosso)
                else:  # più alta: si tagliano sopra e sotto
                    vis = w * 4 / 3
                    m = (h - vis) / 2
                    d.rectangle([0, 0, w, m], fill=rosso)
                    d.rectangle([0, h - m, w, h], fill=rosso)
            elif parte == "cerchio":
                maschera = Image.new("L", im.size, 255)
                ImageDraw.Draw(maschera).ellipse([0, 0, w - 1, h - 1], fill=0)
                velo.paste(Image.new("RGBA", im.size, rosso), (0, 0), maschera)
            elif parte.startswith("centro:"):
                cw, ch = map(int, parte.split(":")[1].split("x"))
                fx, fy = cw / 2560 * w, ch / 1440 * h
                x0, y0 = (w - fx) / 2, (h - fy) / 2
                for r in ([0, 0, w, y0], [0, y0 + fy, w, h], [0, y0, x0, y0 + fy], [x0 + fx, y0, w, y0 + fy]):
                    d.rectangle(r, fill=rosso)
            elif parte.startswith("centro-larghezza:"):
                f = float(parte.split(":")[1])
                m = w * (1 - f) / 2
                d.rectangle([0, 0, m, h], fill=rosso)
                d.rectangle([w - m, 0, w, h], fill=rosso)
    return Image.alpha_composite(im.convert("RGBA"), velo).convert("RGB")


def tavole(fatti: list[dict]) -> None:
    """Tavole alla misura del telefono: ogni tela larga 1080 px diventa larga 430 px (iPhone grande, vista 1:1)."""
    from PIL import Image, ImageDraw, ImageFont

    ANTEPRIME.mkdir(exist_ok=True)
    for vecchia in ANTEPRIME.glob("*.png"):
        vecchia.unlink()
    carattere = ImageFont.truetype(str(FONTE_CARATTERI / "IBMPlexMono-Medium.ttf"), 14)
    gruppi: dict[str, list[dict]] = {}
    for f in fatti:
        gruppi.setdefault(f["gruppo"], []).append(f)
    for gruppo, voci in gruppi.items():
        for con_zone in (False, True):
            celle = []
            for v in voci:
                im = Image.open(v["file"]).convert("RGB")
                scala = 430 / 1080
                lw = round(v["l"] * scala) if v["l"] <= 1920 else 860
                la = round(v["a"] * lw / v["l"])
                im = im.resize((lw, la), Image.LANCZOS)
                if con_zone:
                    im = disegna_zone(im, v["zone"])
                celle.append((v["file"].relative_to(GRAFICHE).as_posix(), im))
            margine, testata, colonne_max = 24, 26, 1800
            righe, riga, x = [], [], margine
            for nome, im in celle:
                if riga and x + im.width + margine > colonne_max:
                    righe.append(riga)
                    riga, x = [], margine
                riga.append((nome, im))
                x += im.width + margine
            righe.append(riga)
            larghezza = max(sum(im.width + margine for _, im in r) + margine for r in righe)
            altezza = sum(max(im.height for _, im in r) + testata + margine for r in righe) + margine
            tavola = Image.new("RGB", (larghezza, altezza), "#808080")
            d = ImageDraw.Draw(tavola)
            y = margine
            for r in righe:
                x = margine
                for nome, im in r:
                    d.text((x, y), nome, font=carattere, fill="#FFFFFF")
                    tavola.paste(im, (x, y + testata))
                    x += im.width + margine
                y += max(im.height for _, im in r) + testata + margine
            nome = f"{'zone' if con_zone else 'telefono'}-{gruppo}.png"
            tavola = tavola.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
            tavola.save(ANTEPRIME / nome, optimize=True)
            print(f"anteprime/{nome}  {tavola.width}×{tavola.height}  {(ANTEPRIME / nome).stat().st_size // 1024} KB")


def contrasti() -> int:
    sys.path.insert(0, str(RADICE / "brand" / "strumenti"))
    import genera_token as T

    righe = ["Contrasti delle coppie di colori usate nei modelli social (WCAG 2.2, calcolati da brand/strumenti/genera_token.py)", ""]
    errori = 0
    for a, b, uso, soglia in COPPIE:
        c = T.contrasto(T.COL[a], T.COL[b])
        esito = "ok" if c >= soglia else "SOTTO SOGLIA"
        errori += c < soglia
        righe.append(f"{c:5.2f}:1  (soglia {soglia:.1f})  {esito:12}  {a} su {b}  ·  {uso}")
    ANTEPRIME.mkdir(exist_ok=True)
    (ANTEPRIME / "contrasti.txt").write_text("\n".join(righe) + "\n", encoding="utf-8")
    print(f"anteprime/contrasti.txt  {len(COPPIE)} coppie, {errori} sotto soglia")
    return errori


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("nomi", nargs="*", help="nomi dei modelli da rendere (senza .html); vuoto = tutti")
    p.add_argument("--solo-anteprime", action="store_true", help="rifà solo tavole e contrasti dai PNG esistenti")
    a = p.parse_args()
    errori = contrasti()
    if not a.solo_anteprime:
        genera(a.nomi)
    tavole(elenco_esistenti())
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
