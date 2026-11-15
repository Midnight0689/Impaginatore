"""Compone brand/anteprima.html dal modello, dai token e dai file del logo.

Uso (dalla cartella brand/, dopo genera_token.py e genera_logo.py):
    python3 strumenti/genera_anteprima.py

La pagina risultante è autosufficiente: CSS e SVG in linea; solo i font arrivano da Google Fonts
(con ripiego su Georgia/Helvetica se manca la rete). Le immagini dell'icona sono lette da icona/.
"""
from __future__ import annotations

import base64
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genera_token as T  # noqa: E402

BRAND = Path(__file__).resolve().parent.parent
LOGO = BRAND / "logo"


def simbolo_sprite(file: Path, ident: str) -> str:
    s = file.read_text()
    vb = re.search(r'viewBox="([^"]+)"', s).group(1)
    corpo = re.sub(r"<title>.*?</title>", "", s.split(">", 1)[1].rsplit("</svg>", 1)[0])
    corpo = corpo.replace('fill="#181715"', "").replace('fill="#236743"', 'style="fill:var(--segno,currentColor)"')
    return f'<symbol id="{ident}" viewBox="{vb}">{corpo.strip()}</symbol>'


def sprite() -> str:
    parti = [
        simbolo_sprite(LOGO / "impaginatore-logotipo.svg", "imp-logotipo"),
        simbolo_sprite(LOGO / "impaginatore-simbolo.svg", "imp-simbolo"),
        simbolo_sprite(LOGO / "impaginatore-verticale.svg", "imp-verticale"),
    ]
    return '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>' + "".join(parti) + "</defs></svg>"


def costruzione() -> str:
    """Schema del simbolo su griglia di unità u, con quote e area di rispetto (6u)."""
    u = 20  # px per unità nello schema
    m = 7 * u  # margine attorno per area di rispetto e quote
    W, H = 26 * u + 2 * m + 60, 22 * u + 2 * m
    x0, y0 = m, m
    righe = []
    a = lambda **k: " ".join(f'{key.replace("_", "-")}="{v}"' for key, v in k.items())
    # griglia
    g = []
    for i in range(-6, 33):
        x = x0 + i * u
        if 0 <= x <= W - 60:
            g.append(f"M{x} 0V{H}")
    for j in range(-6, 29):
        y = y0 + j * u
        if 0 <= y <= H:
            g.append(f"M0 {y}H{W - 60}")
    righe.append(f'<path d="{"".join(g)}" style="stroke:var(--imp-filetto)" stroke-width="1" fill="none"/>')
    # area di rispetto: 6u attorno all'ingombro
    righe.append(f'<rect {a(x=x0 - 6 * u, y=y0 - 6 * u, width=38 * u, height=34 * u)} fill="none" style="stroke:var(--imp-errore)" stroke-width="1.5" stroke-dasharray="6 5"/>')
    # simbolo
    p, s, d, t = 12 * u, 2 * u, 1.5 * u, 3.5 * u
    top = y0 + t + d
    righe.append(f'<path d="M{x0} {top}h{p}v{p}h{-p}zM{x0 + p + s} {top}h{p}v{p}h{-p}z" style="fill:var(--imp-testo)" fill-opacity=".92"/>')
    righe.append(f'<path d="M{x0 + p} {y0}h{s}v{t}h{-s}zM{x0 + p} {top + p + d}h{s}v{t}h{-s}z" style="fill:var(--imp-accento)"/>')

    def quota_h(x1, x2, y, testo):
        return (f'<path d="M{x1} {y}H{x2}M{x1} {y - 5}v10M{x2} {y - 5}v10" style="stroke:var(--imp-accento)" stroke-width="1.5"/>'
                f'<text x="{(x1 + x2) / 2}" y="{y - 12}" text-anchor="middle" style="fill:var(--imp-accento);font:500 22px var(--imp-font-numeri)">{testo}</text>')

    def quota_v(y1, y2, x, testo, sinistra=False):
        tx = x - 12 if sinistra else x + 12
        anc = "end" if sinistra else "start"
        return (f'<path d="M{x} {y1}V{y2}M{x - 5} {y1}h10M{x - 5} {y2}h10" style="stroke:var(--imp-accento)" stroke-width="1.5"/>'
                f'<text x="{tx}" y="{(y1 + y2) / 2 + 7}" text-anchor="{anc}" style="fill:var(--imp-accento);font:500 22px var(--imp-font-numeri)">{testo}</text>')

    righe.append(quota_h(x0, x0 + p, top + p + d + t + 40, "12u"))
    righe.append(quota_h(x0 + p, x0 + p + s, top + p + d + t + 40, "2u"))
    righe.append(quota_v(y0, y0 + t, x0 + 26 * u + 22, "3,5u"))
    righe.append(quota_v(y0 + t, top, x0 + 26 * u + 22, "1,5u"))
    righe.append(quota_v(top, top + p, x0 + 26 * u + 22, "12u"))
    righe.append(quota_v(y0 - 6 * u, y0, x0 - 6 * u - 14, "6u", sinistra=True))
    righe.append(f'<text x="{x0 - 6 * u + 8}" y="{y0 - 6 * u - 10}" style="fill:var(--imp-errore);font:500 18px var(--imp-font-numeri);letter-spacing:.06em">AREA DI RISPETTO = 6u (MEZZA PAGINA)</text>')
    return (f'<svg viewBox="-70 -40 {W + 90} {H + 60}" role="img" aria-label="Costruzione del simbolo su griglia di unità">'
            + "".join(righe) + "</svg>")


def concept() -> str:
    voci = [
        ("concept-1-la-piega.svg", "1 · La Piega", "Lo spread visto dall'alto con i segni di piega del tipografo. Racconta il punto più delicato di un album, contiene la I, si legge a 16 px. Nessun concorrente usa le pagine piene o i segni di stampa.", True, "260 220"),
        ("concept-2-il-crocino.svg", "2 · Il Crocino", "I segni di taglio attorno a una I: precisione di stampa e mirino della fotocamera nello stesso segno. Bello in grande, ma sotto i 32 px diventa polvere e ricorda l'icona «cattura schermo».", False, "240 240"),
        ("concept-3-l-angolino.svg", "3 · L'Angolino", "Gli angoli portafoto degli album di una volta. Caldo e riconoscibile per chi fa matrimoni, ma guarda indietro: parla di album incollati, non di impaginazione né di precisione.", False, "240 240"),
    ]
    out = []
    for f, titolo, testo, scelto, vb in voci:
        s = (LOGO / "concept" / f).read_text()
        corpo = s.split(">", 1)[1].rsplit("</svg>", 1)[0]
        corpo = re.sub(r"<title>.*?</title>", "", corpo)
        svg = f'<svg viewBox="0 0 {vb}">{corpo}</svg>'
        piccoli = "".join(f'<svg viewBox="0 0 {vb}" style="height:{h}px;width:auto">{corpo}</svg>' for h in (32, 16))
        cls = ' class="scelto"' if scelto else ""
        stato = '<span class="badge verde">Scelto</span>' if scelto else '<span class="badge">Scartato</span>'
        out.append(f'<figure{cls}><div class="disegno">{svg}</div><div class="piccoli">{piccoli}<span style="margin-left:auto">{stato}</span></div>'
                   f'<h3>{titolo}</h3><p class="piccolo secondario" style="margin:0">{testo}</p></figure>')
    return "".join(out)


def campione(token: str, nome: str, grande=False, nota="") -> str:
    fam, k = token.rsplit("-", 1)
    L, C, h, *_ = T.PALETTE[fam][k]
    rgb = T.COL[token]
    hx = T.hexrgb(rgb)
    testo = "#FFFFFF" if T.luminanza(rgb) < 0.25 else "#181715"
    cls = "campione grande" if grande else "campione"
    return (f'<div class="{cls}"><div class="tinta" style="background:{hx};color:{testo}">--imp-{token}</div>'
            f'<div class="dati"><b>{nome}</b>{hx}<br>RGB {rgb[0]} {rgb[1]} {rgb[2]}<br>{T.oklch_css(L, C, h)}{("<br>" + nota) if nota else ""}</div></div>')


def scala(fam: str) -> str:
    celle = []
    chiavi = sorted(T.PALETTE[fam], key=int)
    for k in chiavi:
        rgb = T.COL[f"{fam}-{k}"]
        testo = "#FFFFFF" if T.luminanza(rgb) < 0.25 else "#181715"
        nome = T.PALETTE[fam][k][3]
        celle.append(f'<div style="background:{T.hexrgb(rgb)};color:{testo}"><span>{k}</span><span>{nome}<br>{T.hexrgb(rgb)}</span></div>')
    stile = f' style="--n:{len(chiavi)}"'
    return f'<div class="scala"{stile}>' + "".join(celle) + "</div>"


def palette() -> str:
    h = ['<div class="blocco" style="margin-top:0"><span class="etichetta">Primari</span><div class="primari">']
    h.append(campione("carta-50", "Carta", True, "Fondo, superfici, pagine del simbolo in negativo"))
    h.append(campione("carta-900", "Inchiostro", True, "Testo, logo, fondo del tema scuro"))
    h.append(campione("verde-600", "Verde Bottega", True, "Accento: azione principale, link, fuoco, segni di piega"))
    h.append("</div></div>")
    h.append('<div class="blocco"><span class="etichetta">Neutri caldi · scala Carta (sito, stampa, materiali)</span>' + scala("carta") + "</div>")
    h.append('<div class="blocco"><span class="etichetta">Accento · scala Verde Bottega</span>' + scala("verde") + "</div>")
    h.append('<div class="blocco"><span class="etichetta">Semantici · chiaro e scuro</span><div class="campioni">')
    for tok, nome in [("verde-600", "Successo"), ("verde-300", "Successo · scuro"), ("ocra-600", "Attenzione"), ("ocra-300", "Attenzione · scuro"),
                      ("cinabro-600", "Errore · Cinabro"), ("cinabro-300", "Errore · scuro"), ("blu-600", "Info · Blu di Prussia"), ("blu-300", "Info · scuro"), ("ocra-500", "Ocra · segni e guide")]:
        h.append(campione(tok, nome))
    h.append("</div></div>")
    h.append('<div class="blocco"><span class="etichetta">Grigi neutri (C = 0) · solo per l\'area di lavoro dell\'app</span>' + scala("grigio") + "</div>")
    return "".join(h)


def contrasti() -> str:
    gruppi = [("chiaro", "Tema chiaro"), ("scuro", "Tema scuro"), ("app", "Area di lavoro dell'app"), ("marchio", "Marchio e icona")]
    out = ['<div class="contrasti">']
    for chiave, titolo in gruppi:
        righe = [f'<div><h4>{titolo}</h4><table class="tabella"><thead><tr><th>Prova</th><th>Coppia</th><th>Uso</th><th>Rapporto</th><th>Esito</th></tr></thead><tbody>']
        for tema, a, b, uso, soglia in T.COPPIE:
            if tema != chiave:
                continue
            c = T.contrasto(T.COL[a], T.COL[b])
            esito = "≥ 3:1" if soglia == 3.0 else ("AAA" if c >= 7 else "AA")
            fa, fb = T.hexrgb(T.COL[a]), T.hexrgb(T.COL[b])
            righe.append(
                f'<tr><td><span class="prova" style="color:{fa};background:{fb}">Aa</span></td>'
                f'<td class="coppia">{fa}<br>su {fb}</td><td>{uso}</td>'
                f'<td class="num"><b>{T.fmt(c)}:1</b></td><td><span class="esito">{esito}</span></td></tr>'
            )
        righe.append("</tbody></table></div>")
        out.append("".join(righe))
    out.append("</div>")
    out.append('<p class="piccolo secondario" style="margin-top:16px">Soglie WCAG 2.2: testo normale 4,5:1 (AA) e 7:1 (AAA); elementi grafici e bordi dei controlli 3:1.</p>')
    return "".join(out)


def apostrofi(html: str) -> str:
    """Apostrofo tipografico (’) nei nodi di testo; lascia stare stili, script e attributi."""
    parti = re.split(r"(<style.*?</style>|<script.*?</script>|<[^>]+>)", html, flags=re.S)
    return "".join(p if p.startswith("<") else re.sub(r"(?<=\w)'(?=\w)", "\u2019", p) for p in parti)


def main() -> None:
    modello = (BRAND / "strumenti" / "anteprima.modello.html").read_text()
    css = (BRAND / "tokens.css").read_text()
    out = (modello.replace("/*@@TOKENS@@*/", css)
           .replace("<!--@@SPRITE@@-->", sprite())
           .replace("<!--@@COSTRUZIONE@@-->", costruzione())
           .replace("<!--@@CONCEPT@@-->", concept())
           .replace("<!--@@PALETTE@@-->", palette())
           .replace("<!--@@CONTRASTI@@-->", contrasti()))
    # immagini dell'icona in linea: la pagina funziona anche copiata da sola
    for nome in ("icona-16.png", "icona-32.png", "icona-128.png"):
        dati = base64.b64encode((BRAND / "icona" / nome).read_bytes()).decode()
        out = out.replace(f'src="icona/{nome}"', f'src="data:image/png;base64,{dati}"')
    fav = (BRAND / "icona" / "favicon.svg").read_text().strip()
    out = out.replace('href="icona/favicon.svg"', 'href="data:image/svg+xml,' + urllib.parse.quote(fav) + '"')
    assert "@@" not in out, "segnaposto non sostituito"
    out = apostrofi(out)
    (BRAND / "anteprima.html").write_text(out)
    print(f"anteprima.html: {len(out) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
