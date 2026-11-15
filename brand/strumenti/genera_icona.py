"""Icona dell'applicazione e favicon di Impaginatore.

Uso (dalla cartella brand/):
    uv run --with pillow --with cairosvg python strumenti/genera_icona.py

Scrive in brand/icona/:
  icona-1024.svg        master (griglia macOS: forma 824 × 824 centrata, angoli continui, ombra)
  icona-piccola.svg     disegno ridotto per 16 e 32 px, allineato ai pixel (griglia 32)
  icona-16.svg          disegno a 16 px allineato ai pixel
  icona-{16..1024}.png  rendering (Chrome headless per ≥ 64 px, cairosvg per 16 e 32)
  icona.ico             Windows: 16, 24, 32, 48, 64, 128, 256
  icona.icns            macOS (voci PNG da 16 a 1024 px; su Mac si può rifare con crea_icns_mac.sh)
  favicon.svg, favicon-32.png

Il disegno: lo spread (due pagine Carta) con i segni di piega, appoggiato sul tappetino da taglio
Verde Bottega con la sua griglia a centimetri.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

BRAND = Path(__file__).resolve().parent.parent
OUT = BRAND / "icona"

CARTA = "#F6F3EC"
VERDE = "#236743"       # --imp-verde-600
VERDE_SCURO = "#195436"  # --imp-verde-700
GRIGLIA = "#378E60"     # --imp-verde-500: linee del tappetino


def n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def squircle(x: float, y: float, lato: float, raggio_rel: float = 0.225, smussatura: float = 0.6) -> str:
    """Quadrato ad angoli continui (algoritmo di «corner smoothing» di Figma, come le icone macOS):
    lati dritti e curvatura che cresce gradualmente, raggio 22,5 % del lato, smussatura 60 %."""
    R = lato * raggio_rel
    p = min((1 + smussatura) * R, lato / 2)
    misura_arco = 90 * (1 - smussatura)
    arco = math.sin(math.radians(misura_arco / 2)) * R * math.sqrt(2)
    alfa = (90 - misura_arco) / 2
    p3p4 = R * math.tan(math.radians(alfa / 2))
    beta = 45 * smussatura
    c = p3p4 * math.cos(math.radians(beta))
    d = c * math.tan(math.radians(beta))
    b = (p - arco - c - d) / 3
    a = 2 * b
    W = H = lato
    q = lambda *v: " ".join(n(x) for x in v)
    return (
        f"M{q(x + W - p, y)}"
        f"c{q(a, 0, a + b, 0, a + b + c, d)}a{q(R, R)} 0 0 1 {q(arco, arco)}c{q(d, c, d, b + c, d, a + b + c)}"
        f"L{q(x + W, y + H - p)}"
        f"c{q(0, a, 0, a + b, -d, a + b + c)}a{q(R, R)} 0 0 1 {q(-arco, arco)}c{q(-c, d, -(b + c), d, -(a + b + c), d)}"
        f"L{q(x + p, y + H)}"
        f"c{q(-a, 0, -(a + b), 0, -(a + b + c), -d)}a{q(R, R)} 0 0 1 {q(-arco, -arco)}c{q(-d, -c, -d, -(b + c), -d, -(a + b + c))}"
        f"L{q(x, y + p)}"
        f"c{q(0, -a, 0, -(a + b), d, -(a + b + c))}a{q(R, R)} 0 0 1 {q(arco, -arco)}c{q(c, -d, b + c, -d, a + b + c, -d)}Z"
    )


def spread(cx: float, cy: float, pagina: float, piega: float, distacco: float, segno: float, col_pag: str, col_segni: str) -> str:
    x0 = cx - pagina - piega / 2
    top = cy - pagina / 2
    gx = x0 + pagina
    p = f'<path fill="{col_pag}" d="M{n(x0)} {n(top)}h{n(pagina)}v{n(pagina)}h{n(-pagina)}zM{n(gx + piega)} {n(top)}h{n(pagina)}v{n(pagina)}h{n(-pagina)}z"/>'
    s = (f'<path fill="{col_segni}" d="M{n(gx)} {n(top - distacco - segno)}h{n(piega)}v{n(segno)}h{n(-piega)}z'
         f'M{n(gx)} {n(top + pagina + distacco)}h{n(piega)}v{n(segno)}h{n(-piega)}z"/>')
    return p + s


def icona_1024() -> str:
    forma = squircle(100, 100, 824)
    # griglia del tappetino: celle da 824/20, una linea più marcata ogni 5
    cella = 824 / 20
    linee_sottili, linee_forti = [], []
    for i in range(1, 20):
        v = 100 + i * cella
        dest = linee_forti if i % 5 == 0 else linee_sottili
        dest.append(f"M{n(v)} 100V924M100 {n(v)}H924")
    # unità del simbolo: u = 22 (pagina 12u = 264, piega 2u = 44, distacco 1,5u = 33, segno 3,5u = 77)
    u = 22
    disegno = spread(512, 512, 12 * u, 2 * u, 1.5 * u, 3.5 * u, CARTA, CARTA)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<title>Impaginatore</title>
<defs>
<clipPath id="f"><path d="{forma}"/></clipPath>
<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{VERDE}"/><stop offset="1" stop-color="{VERDE_SCURO}"/></linearGradient>
<filter id="o" x="-10%" y="-10%" width="120%" height="125%"><feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#000" flood-opacity=".28"/></filter>
<filter id="c" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#06180E" flood-opacity=".35"/></filter>
</defs>
<path d="{forma}" fill="url(#g)" filter="url(#o)"/>
<g clip-path="url(#f)" fill="none" stroke="{GRIGLIA}">
<path stroke-width="2" stroke-opacity=".55" d="{''.join(linee_sottili)}"/>
<path stroke-width="4" stroke-opacity=".7" d="{''.join(linee_forti)}"/>
</g>
<g filter="url(#c)">{disegno}</g>
</svg>
"""


def livello_fondo() -> str:
    """Livello di fondo per Icon Composer (macOS 26+): tappetino a tutto campo, la forma la applica il sistema."""
    cella = 1024 / 24
    sottili = "".join(f"M{n(i * cella)} 0V1024M0 {n(i * cella)}H1024" for i in range(1, 24) if i % 6)
    forti = "".join(f"M{n(i * cella)} 0V1024M0 {n(i * cella)}H1024" for i in range(1, 24) if i % 6 == 0)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">'
            f'<rect width="1024" height="1024" fill="{VERDE}"/><g fill="none" stroke="{GRIGLIA}">'
            f'<path stroke-width="2" stroke-opacity=".55" d="{sottili}"/><path stroke-width="4" stroke-opacity=".7" d="{forti}"/></g></svg>\n')


def livello_segno() -> str:
    """Livello del segno per Icon Composer: lo spread su fondo trasparente."""
    u = 22
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">{spread(512, 512, 12 * u, 2 * u, 1.5 * u, 3.5 * u, CARTA, CARTA)}</svg>\n'


def icona_piccola() -> str:
    """Griglia 32: forma 30 × 30, pagine 10 × 10, piega 2, distacco 1, segno 3; tutto su pixel interi."""
    forma = squircle(1, 1, 30)
    d = spread(16, 16, 10, 2, 1, 3, CARTA, CARTA)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32"><title>Impaginatore</title><path d="{forma}" fill="{VERDE}"/>{d}</svg>\n'


def icona_24() -> str:
    """Griglia 24 (solo per l'.ico di Windows): pagine 8 × 8, piega 2, distacco 1, segno 3."""
    forma = squircle(0.5, 0.5, 23, raggio_rel=0.21)
    d = spread(12, 12, 8, 2, 1, 3, CARTA, CARTA)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path d="{forma}" fill="{VERDE}"/>{d}</svg>\n'


def icona_16() -> str:
    """Griglia 16: pagine 6 × 6, piega 2, distacco 1, segno 2."""
    forma = squircle(0, 0, 16, raggio_rel=0.2)
    d = spread(8, 8, 6, 2, 1, 2, CARTA, CARTA)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16"><title>Impaginatore</title><path d="{forma}" fill="{VERDE}"/>{d}</svg>\n'


def chrome_png(svg: Path, png: Path, lato: int) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "i.html"
        html.write_text(f'<!doctype html><style>html,body{{margin:0;background:transparent}}img{{display:block;width:{lato}px;height:{lato}px}}</style><img src="{svg.as_uri()}">')
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--force-device-scale-factor=1",
             "--default-background-color=00000000", "--allow-file-access-from-files", f"--window-size={lato},{lato}",
             f"--screenshot={png}", html.as_uri()],
            check=True, capture_output=True,
        )


def scrivi_icns(dest: Path) -> None:
    """Formato ICNS: intestazione «icns» + lunghezza, poi voci (tipo, lunghezza, PNG)."""
    import struct

    voci = [("icp4", 16), ("icp5", 32), ("icp6", 64), ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024),
            ("ic11", 32), ("ic12", 64), ("ic13", 256), ("ic14", 512)]
    corpo = b""
    for tipo, lato in voci:
        dati = (OUT / f"icona-{lato}.png").read_bytes()
        corpo += tipo.encode() + struct.pack(">I", len(dati) + 8) + dati
    dest.write_bytes(b"icns" + struct.pack(">I", len(corpo) + 8) + corpo)


def main() -> None:
    import cairosvg
    from PIL import Image

    OUT.mkdir(exist_ok=True)
    master = OUT / "icona-1024.svg"
    master.write_text(icona_1024())
    piccola = OUT / "icona-piccola.svg"
    piccola.write_text(icona_piccola())
    sedici = OUT / "icona-16.svg"
    sedici.write_text(icona_16())
    shutil.copy(piccola, OUT / "favicon.svg")
    livelli = OUT / "livelli"
    livelli.mkdir(exist_ok=True)
    (livelli / "fondo.svg").write_text(livello_fondo())
    (livelli / "segno.svg").write_text(livello_segno())

    # rendering
    big = OUT / "icona-1024.png"
    chrome_png(master, big, 1024)
    src = Image.open(big).convert("RGBA")
    for lato in (512, 256, 128, 64):
        src.resize((lato, lato), Image.LANCZOS).save(OUT / f"icona-{lato}.png", optimize=True)
    src.save(big, optimize=True)
    cairosvg.svg2png(url=str(piccola), write_to=str(OUT / "icona-32.png"), output_width=32, output_height=32)
    cairosvg.svg2png(url=str(sedici), write_to=str(OUT / "icona-16.png"), output_width=16, output_height=16)
    shutil.copy(OUT / "icona-32.png", OUT / "favicon-32.png")

    # Windows: i formati piccoli usano il disegno allineato ai pixel
    tmp24 = OUT / ".icona-24.png"
    tmp48 = OUT / ".icona-48.png"
    cairosvg.svg2png(url=str(piccola), write_to=str(tmp48), output_width=48, output_height=48)
    cairosvg.svg2png(bytestring=icona_24().encode(), write_to=str(tmp24), output_width=24, output_height=24)
    imgs = {16: OUT / "icona-16.png", 24: tmp24, 32: OUT / "icona-32.png", 48: tmp48, 64: OUT / "icona-64.png", 128: OUT / "icona-128.png", 256: OUT / "icona-256.png"}
    base = Image.open(imgs[256]).convert("RGBA")
    base.save(OUT / "icona.ico", format="ICO", sizes=[(s, s) for s in imgs],
              append_images=[Image.open(p).convert("RGBA") for s, p in imgs.items() if s != 256])
    tmp24.unlink()
    tmp48.unlink()

    # macOS: .icns scritto a mano (voci PNG), così 16 e 32 px usano i disegni allineati ai pixel
    scrivi_icns(OUT / "icona.icns")
    print("fatto:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
