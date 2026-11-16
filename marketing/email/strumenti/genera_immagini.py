"""Genera le immagini delle email da brand/ (logo, simbolo, icone) e i segnaposto delle schermate.

Uso, dalla radice del repository:
    uv run --with cairosvg --with pillow --with fonttools --with brotli python marketing/email/strumenti/genera_immagini.py

Non modifica nulla fuori da marketing/email/immagini/. Tutte le immagini sono a 2x: nell'HTML
hanno width e height dimezzati.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

RADICE = Path(__file__).resolve().parents[3]
MARCA = RADICE / "brand"
USCITA = RADICE / "marketing" / "email" / "immagini"

# Colori dai token di marca (brand/tokens.css). Qui servono in chiaro perché finiscono nei PNG.
CARTA = "#F6F3EC"  # carta-50, fondo chiaro
INCHIOSTRO = "#181715"  # carta-900, fondo scuro
BIANCO_CARTA = "#FDFCF9"  # carta-0, superficie chiara
FUMO = "#292725"  # carta-800, superficie scura
CARTONCINO = "#DEDAD2"  # carta-200, filetto chiaro
GRAFITE = "#3E3D3A"  # carta-700, filetto scuro
VELINA = "#EDE9E1"  # carta-100
PIOMBO = "#6B6964"  # carta-500
ARDESIA = "#54524E"  # carta-600
VERDE = "#236743"  # verde-600
VERDE_CHIARO = "#7BCC9C"  # verde-300

# Area di rispetto del logo: 6u, con u = 10 nei file SVG (STYLEBOOK §7).
RISPETTO = 60


def svg_con_fondo(percorso: Path, fondo: str, margine: int) -> tuple[str, float, float]:
    """Restituisce l'SVG del logo con un fondo pieno e il margine di rispetto attorno."""
    testo = percorso.read_text(encoding="utf-8")
    vb = re.search(r'viewBox="([^"]+)"', testo)
    assert vb, percorso
    x, y, l, a = (float(v) for v in vb.group(1).split())
    nx, ny, nl, na = x - margine, y - margine, l + 2 * margine, a + 2 * margine
    testo = testo.replace(vb.group(0), f'viewBox="{nx:g} {ny:g} {nl:g} {na:g}"', 1)
    rett = f'<rect x="{nx:g}" y="{ny:g}" width="{nl:g}" height="{na:g}" fill="{fondo}"/>'
    testo = re.sub(r"(<svg[^>]*>)", r"\1" + rett, testo, count=1)
    return testo, nl, na


def logo(nome_svg: str, fondo: str, altezza_css: int, uscita: str) -> None:
    svg, larghezza, altezza = svg_con_fondo(MARCA / "logo" / nome_svg, fondo, RISPETTO)
    alt_px = altezza_css * 2
    larg_px = round(larghezza * alt_px / altezza)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(USCITA / uscita),
                     output_width=larg_px, output_height=alt_px)
    print(f"{uscita}: {larg_px}×{alt_px} px (nell'HTML {larg_px / 2:g}×{altezza_css})")


def simboli_icone() -> dict[str, str]:
    """Legge le icone della marca (<symbol id="i-…">) da brand/anteprima.html, fonte unica."""
    html = (MARCA / "anteprima.html").read_text(encoding="utf-8")
    return dict(re.findall(r'<symbol id="i-([a-z]+)" viewBox="0 0 24 24">(.*?)</symbol>', html))


def icona(nome: str, corpo: str, fondo: str, filetto: str, tratto: str, uscita: str) -> None:
    """Icona 24 px in un riquadro 40 × 40 con filetto (STYLEBOOK §16, card), a 2x."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 40 40">'
        f'<rect x="0" y="0" width="40" height="40" rx="4" fill="{fondo}"/>'
        f'<rect x="0.5" y="0.5" width="39" height="39" rx="3.5" fill="none" stroke="{filetto}"/>'
        f'<g transform="translate(8 8)" fill="none" stroke="{tratto}" stroke-width="1.5" '
        f'stroke-linecap="square" stroke-linejoin="miter">{corpo}</g></svg>'
    )
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(USCITA / "icone" / uscita))


def spunta(colore: str, uscita: str) -> None:
    """Spunta verde per gli elenchi delle card prezzo (STYLEBOOK §16): 18 px mostrati, 36 px reali, fondo trasparente."""
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24">'
           f'<path d="M4.5 12.5 9.5 17.5 19.5 7" fill="none" stroke="{colore}" stroke-width="2" stroke-linecap="square"/></svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(USCITA / "icone" / uscita))


def font(nome: str, dimensione: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(MARCA / "font" / nome), dimensione)


def segnaposto(nome: str, larghezza_css: int, altezza_css: int, titolo: str, descrizione: str) -> None:
    """Segnaposto ben riconoscibile per una schermata dell'app che arriverà dopo (T-501)."""
    l, a = larghezza_css * 2, altezza_css * 2
    im = Image.new("RGB", (l, a), VELINA)
    d = ImageDraw.Draw(im)
    # Tratteggio diagonale leggero: dice «vuoto» anche a colpo d'occhio.
    for x in range(-a, l, 28):
        d.line([(x, a), (x + a, 0)], fill="#E4DFD5", width=2)
    # Crocini agli angoli (segni di taglio), come .crocini in anteprima.html: 16 px di distanza, 10 di lunghezza.
    o, s = 32, 20
    for cx, cy, dx, dy in [(0, 0, 1, 1), (l, 0, -1, 1), (0, a, 1, -1), (l, a, -1, -1)]:
        d.line([(cx + dx * o, cy), (cx + dx * o, cy + dy * s)], fill=PIOMBO, width=2)
        d.line([(cx, cy + dy * o), (cx + dx * s, cy + dy * o)], fill=PIOMBO, width=2)
    d.rectangle([o, o, l - o - 1, a - o - 1], outline=CARTONCINO, width=2)

    etichetta = font("IBMPlexMono-Medium.ttf", 26)
    grande = font("Newsreader[opsz,wght].ttf", 46)
    testo = font("InstrumentSans[wdth,wght].ttf", 28)
    piccolo = font("IBMPlexMono-Regular.ttf", 24)
    # Il testo descrittivo va a capo entro il 76 % della larghezza.
    parole, riga, a_capo = descrizione.split(), "", []
    for p in parole:
        prova = f"{riga} {p}".strip()
        if d.textlength(prova, font=testo) > l * 0.76:
            a_capo.append(riga)
            riga = p
        else:
            riga = prova
    a_capo.append(riga)
    righe = (
        [(etichetta, "SEGNAPOSTO · SCHERMATA DA SOSTITUIRE", VERDE), (grande, titolo, INCHIOSTRO)]
        + [(testo, r, ARDESIA) for r in a_capo]
        + [(piccolo, f"{l} × {a} px · nell’email {larghezza_css} × {altezza_css}", PIOMBO),
           (piccolo, f"immagini/segnaposto/{nome}", PIOMBO)]
    )
    altezze = [f.getbbox("Ag")[3] + 22 for f, _, _ in righe]
    y = (a - sum(altezze)) // 2
    for (f, t, colore), h in zip(righe, altezze):
        d.text(((l - d.textlength(t, font=f)) // 2, y), t, font=f, fill=colore)
        y += h
    im.save(USCITA / "segnaposto" / nome, optimize=True)
    print(f"segnaposto/{nome}: {l}×{a} px")


# Schermate previste: nome del file, misure nell'email (px CSS; la colonna è larga 520 px; il file è il doppio), titolo, descrizione per chi le produce.
# Il testo alternativo definitivo sta nei sorgenti MJML ed è elencato in GUIDA-INVIO.md §7.
SCHERMATE = [
    ("lancio-spread.png", 520, 325, "Spread 07–08 nell’editor, con le quote",
     "Lo spread aperto nell’editor, tema chiaro, con una quota verde «5,0 mm» tra due foto. Album dimostrativo con foto in licenza."),
    ("benvenuto-primo-spread.png", 520, 293, "Il primo spread di un album",
     "Un album appena impaginato: primo spread, elenco degli spread a sinistra, nessuna filigrana."),
    ("prova-bozza-claude.png", 520, 325, "La bozza di un album",
     "La colonna degli spread a sinistra con la bozza completa; uno spread rifinito a mano evidenziato."),
    ("aggiornamento-novita.png", 520, 293, "La novità principale della versione",
     "Dettaglio della funzione nuova, ritagliato sul punto che si racconta, una sola annotazione."),
]


def font_email() -> None:
    """Font da ospitare accanto alle immagini: le email non chiamano Google Fonts.

    Newsreader e Instrument Sans (OFL senza nome riservato) vengono ridotti ai caratteri latini e ai
    pesi usati nelle email; IBM Plex Mono ha il nome riservato «Plex» e resta com'è (STYLEBOOK §10).
    """
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    cartella = USCITA / "font"
    cartella.mkdir(exist_ok=True)
    caratteri = "U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+2013-2014,U+2018-201E,U+2026,U+2032-2033,U+20AC,U+2192,U+2212,U+00D7"
    for sorgente, assi, uscita in [
        ("Newsreader[opsz,wght].ttf", {"wght": 500}, "newsreader-email.woff2"),
        ("InstrumentSans[wdth,wght].ttf", {"wdth": 100, "wght": (400, 600)}, "instrumentsans-email.woff2"),
    ]:
        f = instancer.instantiateVariableFont(TTFont(MARCA / "font" / sorgente), assi)
        opzioni = subset.Options()
        opzioni.flavor = "woff2"
        opzioni.layout_features = ["kern", "liga", "lnum", "tnum", "case"]
        s = subset.Subsetter(opzioni)
        s.populate(unicodes=subset.parse_unicodes(caratteri))
        s.subset(f)
        f.flavor = "woff2"
        f.save(cartella / uscita)
        print(f"font/{uscita}: {(cartella / uscita).stat().st_size // 1024} KB")
    for nome in ("IBMPlexMono-Regular.woff2", "IBMPlexMono-Medium.woff2"):
        shutil.copyfile(MARCA / "font" / nome, cartella / nome)
        print(f"font/{nome}: copiato senza modifiche")
    for licenza in ("OFL-Newsreader.txt", "OFL-InstrumentSans.txt", "OFL-IBMPlexMono.txt"):
        shutil.copyfile(MARCA / "font" / licenza, cartella / licenza)


def main() -> None:
    for sotto in ("", "icone", "segnaposto"):
        (USCITA / sotto).mkdir(parents=True, exist_ok=True)
    font_email()

    # Logo orizzontale alto 40 px compresa l'area di rispetto: il logotipo resta alto ≈ 26 px (minimo 24).
    logo("impaginatore-logotipo.svg", CARTA, 40, "logo.png")
    logo("impaginatore-logotipo-negativo.svg", INCHIOSTRO, 40, "logo-scuro.png")
    # Simbolo per il piè di pagina: 36 px con l'area di rispetto, simbolo ≈ 23 px.
    logo("impaginatore-simbolo.svg", CARTA, 36, "simbolo.png")
    logo("impaginatore-simbolo-negativo.svg", INCHIOSTRO, 36, "simbolo-scuro.png")
    # Icona dell'app (già resa dalla marca), mostrata a 64 px.
    shutil.copyfile(MARCA / "icona" / "icona-128.png", USCITA / "icona-app.png")
    print("icona-app.png: 128×128 px (nell'HTML 64×64)")

    simboli = simboli_icone()
    for nome in ("locale", "licenza", "misura", "bozza", "livelli", "scarica", "spread", "ok", "info", "esporta"):
        icona(nome, simboli[nome], BIANCO_CARTA, CARTONCINO, VERDE, f"{nome}.png")
        icona(nome, simboli[nome], FUMO, GRAFITE, VERDE_CHIARO, f"{nome}-scuro.png")
    # Una sola spunta, in verde-500: si legge sul fondo chiaro e su quello scuro (contrasto oltre 3:1).
    spunta("#378E60", "spunta.png")
    print(f"icone/: {len(simboli)} disponibili, 10 generate in chiaro e in scuro (80×80 px, nell'HTML 40×40)")

    for nome, l, a, titolo, descr in SCHERMATE:
        segnaposto(nome, l, a, titolo, descr)


if __name__ == "__main__":
    main()
