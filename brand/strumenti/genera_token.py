"""Fonte unica dei colori e dei token di Impaginatore.

Uso (dalla cartella brand/, solo libreria standard):
    python3 strumenti/genera_token.py

Scrive:
  tokens.json   formato Design Tokens W3C (Format Module 2025.10, colori in OKLCH con HEX di riserva)
  tokens.css    custom properties --imp-*, tema chiaro e scuro (prefers-color-scheme e [data-theme])
  STYLEBOOK.md  aggiorna le tabelle tra i marcatori <!-- palette:inizio/fine --> e <!-- contrasti:inizio/fine -->

I colori sono definiti in OKLCH (L 0–1, C, h in gradi) e convertiti in sRGB con le formule di
Björn Ottosson. Il contrasto è quello WCAG 2.2: (L1 + 0,05) / (L2 + 0,05) sulla luminanza relativa.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

BRAND = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- conversioni


def _lin(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklch_rgb(L: float, C: float, h: float) -> tuple[int, int, int]:
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bb = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    out = []
    for v in (r, g, bb):
        v = _lin(v)
        assert -0.002 <= v <= 1.002, f"fuori gamut sRGB: oklch({L} {C} {h})"
        out.append(round(min(1, max(0, v)) * 255))
    return tuple(out)


def hexrgb(rgb) -> str:
    return "#" + "".join(f"{v:02X}" for v in rgb)


def luminanza(rgb) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrasto(a, b) -> float:
    la, lb = sorted((luminanza(a), luminanza(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---------------------------------------------------------------- palette (fonte unica)
# nome token: (L, C, h, nome italiano, uso)
H_CARTA = 85  # tinta calda della carta
PALETTE: dict[str, dict[str, tuple]] = {
    "carta": {  # neutri caldi: sito, stampa, materiali
        "0": (0.990, 0.004, H_CARTA, "Bianco carta", "Superfici sollevate, card"),
        "50": (0.965, 0.010, H_CARTA, "Carta", "Fondo pagina, colore primario chiaro"),
        "100": (0.935, 0.011, H_CARTA, "Velina", "Riempimenti tenui, righe alterne"),
        "200": (0.890, 0.012, H_CARTA, "Cartoncino", "Filetti e divisori"),
        "300": (0.820, 0.011, H_CARTA, "Feltro", "Bordi decorativi; testo secondario su scuro"),
        "400": (0.700, 0.010, H_CARTA, "Cenere", "Testo tenue su scuro"),
        "500": (0.520, 0.008, H_CARTA, "Piombo", "Testo tenue su chiaro; bordi dei campi"),
        "600": (0.440, 0.007, H_CARTA, "Ardesia", "Testo secondario su chiaro"),
        "700": (0.360, 0.006, H_CARTA, "Grafite", "Bordi su scuro"),
        "800": (0.275, 0.005, H_CARTA, "Fumo", "Superfici sollevate su scuro"),
        "900": (0.205, 0.005, H_CARTA, "Inchiostro", "Testo, colore primario scuro, fondo scuro"),
        "950": (0.165, 0.004, H_CARTA, "Nero seppia", "Fondo più profondo, ombre"),
    },
    "verde": {  # accento: Verde Bottega
        "50": (0.970, 0.018, 157, "Verde velina", "Fondo di badge e avvisi positivi"),
        "100": (0.930, 0.040, 157, "", ""),
        "200": (0.870, 0.070, 157, "", ""),
        "300": (0.780, 0.105, 157, "Verde Bottega chiaro", "Accento e link su fondo scuro"),
        "400": (0.700, 0.115, 157, "", "Pulsante primario su fondo scuro"),
        "500": (0.580, 0.110, 157, "", "Indicatori, grafici"),
        "600": (0.460, 0.090, 157, "Verde Bottega", "Accento: pulsante primario, link, fuoco"),
        "700": (0.400, 0.080, 157, "", "Pulsante primario premuto"),
        "800": (0.330, 0.065, 157, "", ""),
        "900": (0.260, 0.050, 157, "Verde profondo", "Fondo dell'icona in ombra"),
    },
    "ocra": {
        "300": (0.820, 0.110, 80, "", "Attenzione su fondo scuro"),
        "500": (0.680, 0.130, 75, "Ocra", "Indicatori di attenzione"),
        "600": (0.500, 0.100, 75, "Ocra scura", "Testo di attenzione su chiaro"),
        "50": (0.965, 0.025, 85, "", "Fondo avvisi di attenzione"),
    },
    "cinabro": {
        "300": (0.740, 0.130, 28, "", "Errore su fondo scuro"),
        "600": (0.520, 0.170, 28, "Cinabro", "Errore, azioni distruttive"),
        "50": (0.960, 0.020, 28, "", "Fondo avvisi di errore"),
    },
    "blu": {
        "300": (0.770, 0.090, 250, "", "Informazione su fondo scuro"),
        "600": (0.500, 0.110, 250, "Blu di Prussia", "Informazione, misure neutre"),
        "50": (0.965, 0.015, 250, "", "Fondo avvisi informativi"),
    },
    "grigio": {  # neutri puri (C = 0): area di lavoro dell'app, attorno alle foto
        "50": (0.970, 0, 0, "", "Pannelli app, tema chiaro"),
        "100": (0.930, 0, 0, "", ""),
        "200": (0.870, 0, 0, "", "Bordi app chiara"),
        "300": (0.780, 0, 0, "", "Testo secondario app scura"),
        "400": (0.680, 0, 0, "", "Testo tenue app scura"),
        "500": (0.560, 0, 0, "Grigio medio", "Tela neutra per giudicare il colore"),
        "600": (0.470, 0, 0, "", "Testo tenue app chiara"),
        "700": (0.380, 0, 0, "", "Bordi app scura"),
        "800": (0.310, 0, 0, "", "Pannelli sollevati app scura"),
        "850": (0.270, 0, 0, "", "Pannelli app scura"),
        "900": (0.235, 0, 0, "", "Tela app scura"),
        "950": (0.190, 0, 0, "", "Barra superiore app scura"),
    },
}
BIANCO = (255, 255, 255)

COL: dict[str, tuple[int, int, int]] = {}
for fam, scala in PALETTE.items():
    for k, (L, C, h, *_rest) in scala.items():
        COL[f"{fam}-{k}"] = oklch_rgb(L, C, h)
COL["bianco"] = BIANCO

# ---------------------------------------------------------------- temi semantici
# token semantico: (chiaro, scuro) — riferimenti ai primitivi
SEMANTICI = {
    "fondo": ("carta-50", "carta-900", "Fondo della pagina"),
    "fondo-tenue": ("carta-100", "carta-950", "Fasce alterne, aree secondarie"),
    "superficie": ("carta-0", "carta-800", "Card, pannelli, campi"),
    "testo": ("carta-900", "carta-50", "Testo principale"),
    "testo-secondario": ("carta-600", "carta-300", "Sottotitoli, descrizioni"),
    "testo-tenue": ("carta-500", "carta-400", "Note, didascalie, segnaposto"),
    "filetto": ("carta-200", "carta-700", "Divisori e bordi decorativi"),
    "bordo-campo": ("carta-500", "carta-400", "Bordo di campi e controlli (≥ 3:1)"),
    "accento": ("verde-600", "verde-300", "Link, fuoco, selezione, segni di piega"),
    "accento-fondo": ("verde-600", "verde-400", "Pulsante primario"),
    "accento-fondo-premuto": ("verde-700", "verde-300", "Pulsante primario premuto"),
    "su-accento": ("carta-50", "carta-950", "Testo su pulsante primario"),
    "accento-tenue": ("verde-50", "verde-900", "Fondo di badge e avvisi positivi"),
    "successo": ("verde-600", "verde-300", "Esito positivo, misure uguali"),
    "attenzione": ("ocra-600", "ocra-300", "Testo e icone di attenzione"),
    "attenzione-segno": ("ocra-500", "ocra-300", "Guide e indicatori di attenzione"),
    "errore": ("cinabro-600", "cinabro-300", "Errori, azioni distruttive"),
    "info": ("blu-600", "blu-300", "Informazioni, misure neutre"),
    "inverso-fondo": ("carta-900", "carta-50", "Pulsante secondario pieno, fasce invertite"),
    "inverso-testo": ("carta-50", "carta-900", "Testo su fondo inverso"),
}
# area di lavoro dell'app (neutri puri); la tela non cambia col tema del sito
APP = {
    "app-tela": ("grigio-100", "grigio-900", "Tela attorno allo spread"),
    "app-pannello": ("grigio-50", "grigio-850", "Pannelli laterali"),
    "app-barra": ("bianco", "grigio-950", "Barra superiore"),
    "app-sollevato": ("bianco", "grigio-800", "Menu, popover"),
    "app-bordo": ("grigio-200", "grigio-700", "Bordi e divisori"),
    "app-testo": ("carta-900", "grigio-50", "Testo"),
    "app-testo-tenue": ("grigio-600", "grigio-400", "Etichette, valori secondari"),
    "app-selezione": ("carta-900", "bianco", "Contorno dell'elemento selezionato"),
    "app-accento": ("verde-600", "verde-300", "Strumento attivo, fuoco, misure uguali"),
}

# ---------------------------------------------------------------- coppie di contrasto da verificare
COPPIE = [
    # (tema, testo, fondo, uso, soglia)
    ("chiaro", "carta-900", "carta-50", "Testo su Carta", 4.5),
    ("chiaro", "carta-900", "carta-0", "Testo su card", 4.5),
    ("chiaro", "carta-600", "carta-50", "Testo secondario su Carta", 4.5),
    ("chiaro", "carta-500", "carta-50", "Testo tenue su Carta", 4.5),
    ("chiaro", "carta-500", "carta-100", "Testo tenue su Velina", 4.5),
    ("chiaro", "verde-600", "carta-50", "Link verde su Carta", 4.5),
    ("chiaro", "carta-50", "verde-600", "Testo del pulsante primario", 4.5),
    ("chiaro", "carta-50", "verde-700", "Pulsante primario premuto", 4.5),
    ("chiaro", "verde-600", "verde-50", "Badge positivo", 4.5),
    ("chiaro", "ocra-600", "carta-50", "Attenzione su Carta", 4.5),
    ("chiaro", "ocra-600", "ocra-50", "Avviso di attenzione", 4.5),
    ("chiaro", "cinabro-600", "carta-50", "Errore su Carta", 4.5),
    ("chiaro", "carta-50", "cinabro-600", "Pulsante distruttivo", 4.5),
    ("chiaro", "blu-600", "carta-50", "Informazione su Carta", 4.5),
    ("chiaro", "carta-500", "carta-0", "Bordo dei campi (non testo)", 3.0),
    ("chiaro", "verde-600", "carta-0", "Anello di fuoco (non testo)", 3.0),
    ("scuro", "carta-50", "carta-900", "Testo su Inchiostro", 4.5),
    ("scuro", "carta-50", "carta-800", "Testo su card scura", 4.5),
    ("scuro", "carta-300", "carta-900", "Testo secondario su Inchiostro", 4.5),
    ("scuro", "carta-400", "carta-900", "Testo tenue su Inchiostro", 4.5),
    ("scuro", "carta-400", "carta-800", "Testo tenue su card scura", 4.5),
    ("scuro", "verde-300", "carta-900", "Link verde su Inchiostro", 4.5),
    ("scuro", "carta-950", "verde-400", "Testo del pulsante primario", 4.5),
    ("scuro", "verde-300", "verde-900", "Badge positivo", 4.5),
    ("scuro", "ocra-300", "carta-900", "Attenzione su Inchiostro", 4.5),
    ("scuro", "cinabro-300", "carta-900", "Errore su Inchiostro", 4.5),
    ("scuro", "blu-300", "carta-900", "Informazione su Inchiostro", 4.5),
    ("scuro", "carta-400", "carta-800", "Bordo dei campi (non testo)", 3.0),
    ("app", "grigio-50", "grigio-850", "Testo dei pannelli (app scura)", 4.5),
    ("app", "grigio-400", "grigio-850", "Etichette dei pannelli (app scura)", 4.5),
    ("app", "verde-300", "grigio-850", "Accento nei pannelli (app scura)", 4.5),
    ("app", "carta-900", "grigio-50", "Testo dei pannelli (app chiara)", 4.5),
    ("app", "grigio-600", "grigio-50", "Etichette dei pannelli (app chiara)", 4.5),
    ("app", "bianco", "grigio-900", "Contorno di selezione su tela (non testo)", 3.0),
    ("marchio", "carta-900", "carta-50", "Logo a colori: pagine su Carta", 3.0),
    ("marchio", "verde-600", "carta-50", "Logo a colori: segni di piega su Carta", 3.0),
    ("marchio", "verde-300", "carta-900", "Logo negativo: segni su Inchiostro", 3.0),
    ("marchio", "carta-50", "verde-600", "Icona: pagine su Verde Bottega", 3.0),
]


def fmt(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def oklch_css(L, C, h) -> str:
    return f"oklch({L * 100:.1f}% {C:.3f} {h:g})"


# ---------------------------------------------------------------- tokens.json (DTCG)


def colore_dtcg(fam, k):
    L, C, h, nome, uso = PALETTE[fam][k]
    rgb = COL[f"{fam}-{k}"]
    tok = {
        "$type": "color",
        "$value": {"colorSpace": "oklch", "components": [L, C, h], "alpha": 1, "hex": hexrgb(rgb).lower()},
    }
    desc = " — ".join(x for x in (nome, uso) if x)
    if desc:
        tok["$description"] = desc
    return tok


def ref(nome: str) -> str:
    if nome == "bianco":
        return "{colore.bianco}"
    fam, k = nome.rsplit("-", 1)
    return "{colore." + fam + "." + k + "}"


def dim(v, unit="px"):
    return {"value": v, "unit": unit}


FONT = {
    "titoli": ["Newsreader", "Iowan Old Style", "Georgia", "serif"],
    "testo": ["Instrument Sans", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"],
    "numeri": ["IBM Plex Mono", "SFMono-Regular", "Consolas", "monospace"],
}
# nome: (famiglia, dimensione px, peso, interlinea, spaziatura em, opsz)
SCALA_TIPO = {
    "display": ("titoli", 72, 480, 1.02, -0.022, 72),
    "titolo-1": ("titoli", 52, 480, 1.06, -0.018, 60),
    "titolo-2": ("titoli", 38, 500, 1.12, -0.012, 48),
    "titolo-3": ("titoli", 28, 500, 1.2, -0.008, 32),
    "titolo-4": ("testo", 20, 600, 1.3, -0.006, None),
    "attacco": ("testo", 19, 400, 1.5, -0.004, None),
    "testo": ("testo", 16, 400, 1.6, 0, None),
    "testo-piccolo": ("testo", 14, 400, 1.5, 0, None),
    "didascalia": ("testo", 12.5, 400, 1.4, 0.004, None),
    "etichetta": ("numeri", 11.5, 500, 1.3, 0.06, None),
    "misura": ("numeri", 13, 400, 1.3, 0, None),
    "app-testo": ("testo", 13, 400, 1.4, 0, None),
    "app-etichetta": ("testo", 11, 600, 1.3, 0.02, None),
    "app-misura": ("numeri", 12, 400, 1.3, 0, None),
}
SPAZI = {"0": 0, "1": 2, "2": 4, "3": 8, "4": 12, "5": 16, "6": 24, "7": 32, "8": 48, "9": 64, "10": 96, "11": 128}
RAGGI = {"nessuno": 0, "piccolo": 2, "medio": 4, "grande": 8, "pillola": 999}
DURATE = {"istante": 90, "breve": 160, "medio": 240, "lungo": 400}
CURVE = {"esce": [0.2, 0, 0, 1], "entra": [0.4, 0, 1, 1], "standard": [0.4, 0, 0.2, 1]}


def ombra(alpha_a, y_a, blur_a, alpha_b, y_b, blur_b, spread_b):
    return [
        {"color": {"colorSpace": "srgb", "components": [0.082, 0.078, 0.071], "alpha": alpha_a, "hex": "#151412"},
         "offsetX": dim(0), "offsetY": dim(y_a), "blur": dim(blur_a), "spread": dim(0)},
        {"color": {"colorSpace": "srgb", "components": [0.082, 0.078, 0.071], "alpha": alpha_b, "hex": "#151412"},
         "offsetX": dim(0), "offsetY": dim(y_b), "blur": dim(blur_b), "spread": dim(spread_b)},
    ]


def tokens_json() -> dict:
    colore = {fam: {k: colore_dtcg(fam, k) for k in sorted(scala, key=lambda s: int(s))} for fam, scala in PALETTE.items()}
    colore["bianco"] = {"$type": "color", "$value": {"colorSpace": "srgb", "components": [1, 1, 1], "alpha": 1, "hex": "#ffffff"}}
    colore["$description"] = "Primitivi. Fonte: strumenti/genera_token.py (OKLCH). Non usarli direttamente nei componenti: passa dai token di tema."

    def tema(i):
        t = {k: {"$type": "color", "$value": ref(v[i]), "$description": v[2]} for k, v in SEMANTICI.items()}
        t.update({k: {"$type": "color", "$value": ref(v[i]), "$description": v[2]} for k, v in APP.items()})
        return t

    tipo = {}
    for nome, (fam, px, w, lh, ls, opsz) in SCALA_TIPO.items():
        tipo[nome] = {
            "$type": "typography",
            "$value": {
                "fontFamily": "{font.famiglia." + fam + "}",
                "fontSize": dim(px),
                "fontWeight": w,
                "lineHeight": lh,
                "letterSpacing": dim(round(ls * px, 3)),
            },
            "$extensions": {"it.impaginatore": {"letter-spacing-em": ls}},
        }
        if opsz:
            tipo[nome]["$extensions"]["it.impaginatore"]["font-variation-settings"] = f"'opsz' {opsz}"
    return {
        "$description": "Design token di Impaginatore — formato W3C Design Tokens (Format Module 2025.10). Generato da strumenti/genera_token.py: non modificare a mano.",
        "colore": colore,
        "tema": {
            "$description": "Token semantici. 'chiaro' e 'scuro' hanno gli stessi nomi: cambia solo il valore.",
            "chiaro": tema(0),
            "scuro": tema(1),
        },
        "font": {
            "famiglia": {k: {"$type": "fontFamily", "$value": v} for k, v in FONT.items()},
            "peso": {k: {"$type": "fontWeight", "$value": v} for k, v in {"normale": 400, "medio": 500, "titolo": 480, "semigrassetto": 600, "logotipo": 540}.items()},
        },
        "tipografia": tipo,
        "spazio": {"$description": "Scala su base 4 px (con 2 px per i dettagli)", **{k: {"$type": "dimension", "$value": dim(v)} for k, v in SPAZI.items()}},
        "raggio": {k: {"$type": "dimension", "$value": dim(v)} for k, v in RAGGI.items()},
        "bordo": {"sottile": {"$type": "dimension", "$value": dim(1)}, "fuoco": {"$type": "dimension", "$value": dim(2)}},
        "ombra": {
            "appoggio": {"$type": "shadow", "$description": "Carta appoggiata sul tavolo", "$value": ombra(0.06, 1, 2, 0.08, 4, 12, -4)},
            "sollevato": {"$type": "shadow", "$description": "Menu, popover, finestre", "$value": ombra(0.08, 2, 6, 0.22, 16, 40, -12)},
        },
        "durata": {k: {"$type": "duration", "$value": dim(v, "ms")} for k, v in DURATE.items()},
        "curva": {k: {"$type": "cubicBezier", "$value": v} for k, v in CURVE.items()},
        "griglia": {
            "colonne": {"$type": "number", "$value": 12},
            "larghezza-massima": {"$type": "dimension", "$value": dim(1200)},
            "canale": {"$type": "dimension", "$value": dim(24)},
            "margine": {"$type": "dimension", "$value": dim(24), "$description": "16 px sotto i 480 px, 64 px sopra i 1200 px"},
            "linea-di-base": {"$type": "dimension", "$value": dim(8)},
        },
    }


# ---------------------------------------------------------------- tokens.css


def tokens_css() -> str:
    righe = [
        "/* Impaginatore — design token. Generato da strumenti/genera_token.py: non modificare a mano. */",
        "/* Font: Newsreader, Instrument Sans, IBM Plex Mono (SIL OFL 1.1) — file in brand/font/. */",
        "",
        ":root {",
        "  /* Primitivi: colori (OKLCH con HEX di riserva) */",
    ]
    for fam, scala in PALETTE.items():
        for k in sorted(scala, key=lambda s: int(s)):
            L, C, h, nome, _ = scala[k]
            hx = hexrgb(COL[f"{fam}-{k}"])
            commento = f" /* {nome} */" if nome else ""
            righe.append(f"  --imp-{fam}-{k}: {hx};{commento}")
    righe.append("  --imp-bianco: #FFFFFF;")
    righe.append("")
    righe.append("  /* Font */")
    for k, v in FONT.items():
        fam = ", ".join(f'"{x}"' if " " in x and x not in ("sans-serif",) else x for x in v)
        righe.append(f"  --imp-font-{k}: {fam};")
    righe.append("")
    righe.append("  /* Scala tipografica: dimensione / interlinea / peso / spaziatura */")
    for nome, (fam, px, w, lh, ls, opsz) in SCALA_TIPO.items():
        righe.append(f"  --imp-tipo-{nome}-dimensione: {px / 16:g}rem; --imp-tipo-{nome}-interlinea: {lh}; --imp-tipo-{nome}-peso: {w}; --imp-tipo-{nome}-spaziatura: {ls}em;")
    righe.append("")
    righe.append("  /* Spazi (base 4 px), raggi, bordi */")
    righe.append("  " + " ".join(f"--imp-spazio-{k}: {v}px;" for k, v in SPAZI.items()))
    righe.append("  " + " ".join(f"--imp-raggio-{k}: {v}px;" for k, v in RAGGI.items()))
    righe.append("  --imp-bordo-sottile: 1px; --imp-bordo-fuoco: 2px;")
    righe.append("")
    righe.append("  /* Movimento */")
    righe.append("  " + " ".join(f"--imp-durata-{k}: {v}ms;" for k, v in DURATE.items()))
    righe.append("  " + " ".join(f"--imp-curva-{k}: cubic-bezier({', '.join(f'{x:g}' for x in v)});" for k, v in CURVE.items()))
    righe.append("")
    righe.append("  /* Griglia */")
    righe.append("  --imp-griglia-colonne: 12; --imp-griglia-larghezza: 1200px; --imp-griglia-canale: 24px; --imp-griglia-margine: clamp(16px, 5vw, 64px); --imp-linea-di-base: 8px;")
    righe.append("")
    righe.append("  /* Tema chiaro (predefinito) */")
    righe.append("  color-scheme: light;")
    righe += semantici_css(0)
    righe.append("  --imp-ombra-appoggio: 0 1px 2px rgb(21 20 18 / .06), 0 4px 12px -4px rgb(21 20 18 / .08);")
    righe.append("  --imp-ombra-sollevato: 0 2px 6px rgb(21 20 18 / .08), 0 16px 40px -12px rgb(21 20 18 / .22);")
    righe.append("}")
    scuro = ["  color-scheme: dark;"] + semantici_css(1) + [
        "  --imp-ombra-appoggio: 0 0 0 1px rgb(255 255 255 / .06), 0 1px 2px rgb(0 0 0 / .4);",
        "  --imp-ombra-sollevato: 0 0 0 1px rgb(255 255 255 / .08), 0 16px 40px -12px rgb(0 0 0 / .6);",
    ]
    righe.append("")
    righe.append("@media (prefers-color-scheme: dark) {")
    righe.append("  :root:not([data-theme=\"light\"]) {")
    righe += ["  " + r for r in scuro]
    righe.append("  }")
    righe.append("}")
    righe.append("")
    righe.append(":root[data-theme=\"dark\"], [data-theme=\"dark\"] {")
    righe += scuro
    righe.append("}")
    righe.append("")
    righe.append("[data-theme=\"light\"] {")
    righe += ["  color-scheme: light;"] + semantici_css(0)
    righe.append("}")
    righe.append("")
    righe.append("@media (prefers-reduced-motion: reduce) {")
    righe.append("  :root { --imp-durata-istante: 0ms; --imp-durata-breve: 0ms; --imp-durata-medio: 0ms; --imp-durata-lungo: 0ms; }")
    righe.append("}")
    return "\n".join(righe) + "\n"


def semantici_css(i: int) -> list[str]:
    out = []
    for k, v in {**SEMANTICI, **APP}.items():
        out.append(f"  --imp-{k}: var(--imp-{v[i]});")
    return out


# ---------------------------------------------------------------- tabelle per lo stylebook


def tabella_palette() -> str:
    righe = ["| Token | Nome | HEX | RGB | OKLCH | Uso |", "|---|---|---|---|---|---|"]
    for fam, scala in PALETTE.items():
        for k in sorted(scala, key=lambda s: int(s)):
            L, C, h, nome, uso = scala[k]
            if not nome and fam not in ("grigio",):
                continue
            rgb = COL[f"{fam}-{k}"]
            righe.append(f"| `--imp-{fam}-{k}` | {nome or '—'} | `{hexrgb(rgb)}` | {rgb[0]} {rgb[1]} {rgb[2]} | `{oklch_css(L, C, h)}` | {uso or '—'} |")
    return "\n".join(righe)


def tabella_contrasti() -> str:
    righe = ["| Tema | Primo piano | Fondo | Uso | Rapporto | Soglia | Esito |", "|---|---|---|---|---|---|---|"]
    for tema, a, b, uso, soglia in COPPIE:
        c = contrasto(COL[a], COL[b])
        livello = "AAA" if soglia == 4.5 and c >= 7 else ("AA" if c >= soglia else "NO")
        if soglia == 3.0:
            livello = "≥ 3:1" if c >= 3 else "NO"
        righe.append(f"| {tema} | `{a}` {hexrgb(COL[a])} | `{b}` {hexrgb(COL[b])} | {uso} | **{fmt(c)}:1** | {fmt(soglia)}:1 | {livello} |")
        assert c >= soglia, f"contrasto insufficiente: {a} su {b} = {c:.2f}"
    return "\n".join(righe)


def aggiorna_blocco(testo: str, nome: str, contenuto: str) -> str:
    pat = re.compile(rf"(<!-- {nome}:inizio -->\n).*?(<!-- {nome}:fine -->)", re.S)
    if not pat.search(testo):
        return testo
    return pat.sub(lambda m: m.group(1) + contenuto + "\n" + m.group(2), testo)


def main() -> None:
    (BRAND / "tokens.json").write_text(json.dumps(tokens_json(), ensure_ascii=False, indent=2) + "\n")
    (BRAND / "tokens.css").write_text(tokens_css())
    sb = BRAND / "STYLEBOOK.md"
    if sb.exists():
        t = sb.read_text()
        t = aggiorna_blocco(t, "palette", tabella_palette())
        t = aggiorna_blocco(t, "contrasti", tabella_contrasti())
        sb.write_text(t)
    print(tabella_palette())
    print()
    print(tabella_contrasti())


if __name__ == "__main__":
    main()
