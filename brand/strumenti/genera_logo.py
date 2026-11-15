"""Costruisce i file del logo di Impaginatore a partire dalla geometria del simbolo e da Newsreader.

Uso (dalla cartella brand/):
    uv run --with fonttools --with uharfbuzz python strumenti/genera_logo.py

Il simbolo «La Piega» è disegnato su una griglia di unità u = 10:
    pagina 12u × 12u, piega (gutter) 2u, distacco 1,5u, segno di piega 3,5u.
    Ingombro: 26u × 22u (260 × 220).
Il logotipo usa Newsreader (OFL) a peso 540, dimensione ottica 72, crenatura del font,
spaziatura −0,01 em, con il punto della «i» sostituito da un quadrato.
Il testo viene convertito in tracciati: i file finali non dipendono da alcun font.
"""
from __future__ import annotations

import io
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

BRAND = Path(__file__).resolve().parent.parent
FONT = BRAND / "font" / "Newsreader[opsz,wght].ttf"
OUT = BRAND / "logo"

# Colori (vedi tokens.json)
INCHIOSTRO = "#181715"
CARTA = "#F6F3EC"
BIANCO = "#FFFFFF"
VERDE = "#236743"        # Verde Bottega (--imp-verde-600)
VERDE_CHIARO = "#7BCC9C"  # Verde Bottega chiaro (--imp-verde-300)

U = 10
PAGINA, PIEGA, DISTACCO, SEGNO = 12 * U, 2 * U, 1.5 * U, 3.5 * U
SIM_W = 2 * PAGINA + PIEGA            # 260
SIM_H = PAGINA + 2 * (DISTACCO + SEGNO)  # 220

VARIANTI = {
    # nome: (pagine, segni, testo)
    "": (INCHIOSTRO, VERDE, INCHIOSTRO),
    "-negativo": (CARTA, VERDE_CHIARO, CARTA),
    "-mono-scuro": (INCHIOSTRO, INCHIOSTRO, INCHIOSTRO),
    "-mono-chiaro": (BIANCO, BIANCO, BIANCO),
}


def n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def simbolo(x: float, y: float, k: float, pagine: str, segni: str) -> str:
    """Rettangoli del simbolo; (x, y) = angolo in alto a sinistra dell'ingombro, k = scala."""
    p, s, d, t = PAGINA * k, PIEGA * k, DISTACCO * k, SEGNO * k
    top = y + t + d
    gx = x + p
    pag = f'<path fill="{pagine}" d="M{n(x)} {n(top)}h{n(p)}v{n(p)}h{n(-p)}zM{n(gx + s)} {n(top)}h{n(p)}v{n(p)}h{n(-p)}z"/>'
    seg = f'<path fill="{segni}" d="M{n(gx)} {n(y)}h{n(s)}v{n(t)}h{n(-s)}zM{n(gx)} {n(top + p + d)}h{n(s)}v{n(t)}h{n(-s)}z"/>'
    return pag + seg


class Parola:
    """«Impaginatore» composto in Newsreader e convertito in tracciati."""

    def __init__(self, testo="Impaginatore", wght=540, opsz=72, tracking=-0.01, punto_quadrato=True):
        f = TTFont(str(FONT))
        f = instantiateVariableFont(f, {"wght": wght, "opsz": opsz}, inplace=False)
        buf = io.BytesIO()
        f.save(buf)
        data = buf.getvalue()
        self.font = TTFont(io.BytesIO(data))
        self.upem = self.font["head"].unitsPerEm
        gs = self.font.getGlyphSet()
        order = self.font.getGlyphOrder()
        hbfont = hb.Font(hb.Face(data))
        b = hb.Buffer()
        b.add_str(testo)
        b.guess_segment_properties()
        hb.shape(hbfont, b, {"kern": True, "liga": True})
        self.glifi = []
        x = 0
        for info, pos in zip(b.glyph_infos, b.glyph_positions):
            self.glifi.append((order[info.codepoint], x + pos.x_offset, pos.y_offset))
            x += pos.x_advance + tracking * self.upem
        self.avanzamento = x - tracking * self.upem
        self.gs = gs
        self.punto_quadrato = punto_quadrato
        bp = BoundsPen(gs)
        gs["I"].draw(bp)
        self.cap = bp.bounds[3]  # altezza reale della maiuscola I
        # bounds complessivi (unità font)
        tb = BoundsPen(gs)
        for name, gx, gy in self.glifi:
            gs[name].draw(TransformPen(tb, (1, 0, 0, 1, gx, gy)))
        self.bounds = tb.bounds

    def _punto_i(self):
        """Contorno del punto della i: ritorna (cx, cy, larghezza)."""
        rp = RecordingPen()
        self.gs["i"].draw(rp)
        contorni, cur = [], []
        for op, args in rp.value:
            cur.append((op, args))
            if op in ("closePath", "endPath"):
                contorni.append(cur)
                cur = []
        best = None
        for c in contorni:
            pts = [p for _, a in c for p in a]
            ymin = min(p[1] for p in pts)
            if best is None or ymin > best[0]:
                best = (ymin, pts)
        pts = best[1]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs)

    def path(self, x0: float, baseline: float, scala: float) -> str:
        """d del tracciato; scala = unità SVG per unità font."""
        pen = SVGPathPen(self.gs, ntos=n)
        quadrati = []
        for name, gx, gy in self.glifi:
            g = name
            if self.punto_quadrato and name == "i":
                g = "dotlessi"
                cx, cy, w = self._punto_i()
                lato = w * 0.86
                quadrati.append((gx + cx - lato / 2, gy + cy - lato / 2, lato))
            self.gs[g].draw(TransformPen(pen, (scala, 0, 0, -scala, x0 + gx * scala, baseline - gy * scala)))
        d = pen.getCommands()
        for qx, qy, lato in quadrati:
            X, Y, L = x0 + qx * scala, baseline - (qy + lato) * scala, lato * scala
            d += f"M{n(X)} {n(Y)}h{n(L)}v{n(L)}h{n(-L)}z"
        return d


def svg(w: float, h: float, corpo: str, titolo: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n(w)} {n(h)}" role="img" aria-label="{titolo}">'
        f"<title>{titolo}</title>{corpo}</svg>\n"
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    parola = Parola()
    # Logotipo orizzontale: altezza della maiuscola = lato della pagina (120), linea di base = piede delle pagine.
    scala = PAGINA / parola.cap
    baseline = SEGNO + DISTACCO + PAGINA  # 170
    spazio = 7 * U  # distanza simbolo-parola: 7u
    x_parola = SIM_W + spazio
    w_logo = x_parola + parola.bounds[2] * scala
    # Verticale: simbolo a scala 2, parola centrata sotto; spazio = 1 pagina del simbolo piccolo (12u)
    k_v = 2.0
    sim_vw, sim_vh = SIM_W * k_v, SIM_H * k_v
    larg_parola = (parola.bounds[2] - parola.bounds[0]) * scala
    w_v = max(sim_vw, larg_parola)
    base_v = sim_vh + 12 * U + PAGINA  # cap top a sim_vh + 12u
    disc = -parola.bounds[1] * scala  # discendente sotto la linea di base
    h_v = base_v + disc

    for suff, (pag, seg, txt) in VARIANTI.items():
        nome = {"": "colore", "-negativo": "colore su fondo scuro", "-mono-scuro": "monocromo scuro", "-mono-chiaro": "monocromo chiaro"}[suff]
        # disegno allineati ai pixel per 16 × 13 px (barre di app, menu): pagine 7, piega 2, distacco 1, segno 2
        piccolo = f'<path fill="{pag}" d="M0 3h7v7H0zM9 3h7v7H9z"/><path fill="{seg}" d="M7 0h2v2H7zM7 11h2v2H7z"/>'
        (OUT / f"impaginatore-simbolo-16{suff}.svg").write_text(svg(16, 13, piccolo, f"Impaginatore, simbolo a 16 px ({nome})").replace("<svg ", '<svg width="16" height="13" ', 1))
        (OUT / f"impaginatore-simbolo{suff}.svg").write_text(
            svg(SIM_W, SIM_H, simbolo(0, 0, 1, pag, seg), f"Impaginatore, simbolo ({nome})")
        )
        corpo = simbolo(0, 0, 1, pag, seg) + f'<path fill="{txt}" d="{parola.path(x_parola - parola.bounds[0] * scala, baseline, scala)}"/>'
        (OUT / f"impaginatore-logotipo{suff}.svg").write_text(svg(w_logo, SIM_H, corpo, f"Impaginatore, logotipo ({nome})"))
        corpo = simbolo((w_v - sim_vw) / 2, 0, k_v, pag, seg)
        corpo += f'<path fill="{txt}" d="{parola.path((w_v - larg_parola) / 2 - parola.bounds[0] * scala, base_v, scala)}"/>'
        (OUT / f"impaginatore-verticale{suff}.svg").write_text(svg(w_v, h_v, corpo, f"Impaginatore, marchio verticale ({nome})"))
    print(f"logotipo {n(w_logo)}×{SIM_H}, verticale {n(w_v)}×{n(h_v)}, cap {n(parola.cap)} unità font")


if __name__ == "__main__":
    main()
