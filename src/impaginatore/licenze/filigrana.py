"""Filigrana delle esportazioni JPG e PDF durante la prova gratuita (tier.json, prova.filigrana_export).

Testo grigio semitrasparente su righe diagonali che coprono tutta l'immagine: si vede sulle pagine bianche e sulle foto
scure, lascia giudicare l'impaginazione e non si toglie ritagliando un angolo. Il testo si disegna una volta sola, in una
maschera piccola già ruotata, e si incolla sui punti di una griglia ruotata: niente copie dell'immagine intera in RGBA,
anche sugli spread da stampa.
"""
import math

from PIL import Image, ImageDraw

from ..piattaforma import font as pfont

TESTO = "IMPAGINATORE · PROVA GRATUITA"
COLORE = (128, 128, 128)
OPACITA = 90                          # su 255: circa 35 %
ANGOLO = 30                           # gradi, in senso antiorario


def piastrella(corpo):
    """(maschera in modo L con il testo ruotato, larghezza del testo diritto) per un testo alto `corpo` pixel"""
    f = pfont.pil_ripiego(corpo)
    larga = max(1, int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(TESTO, font=f)))
    m = Image.new("L", (larga + corpo * 2, corpo * 3), 0)
    ImageDraw.Draw(m).text((corpo, corpo), TESTO, font=f, fill=OPACITA)
    return m.rotate(ANGOLO, expand=True, resample=Image.Resampling.BICUBIC), larga


def applica(im):
    """copia RGB dell'immagine con la filigrana (l'originale non cambia)"""
    out = im.convert("RGB") if im.mode != "RGB" else im.copy()
    corpo = max(12, max(out.size) // 36)
    m, larga = piastrella(corpo)
    tinta = Image.new("RGB", m.size, COLORE)
    a = math.radians(ANGOLO)
    u, v = (math.cos(a), -math.sin(a)), (math.sin(a), math.cos(a))           # lungo il testo e di traverso
    passo_u, passo_v = larga + corpo * 4, corpo * 6
    angoli = [(0, 0), (out.width, 0), (0, out.height), (out.width, out.height)]
    su = [x * u[0] + y * u[1] for x, y in angoli]; sv = [x * v[0] + y * v[1] for x, y in angoli]
    for j in range(math.floor(min(sv) / passo_v) - 1, math.ceil(max(sv) / passo_v) + 2):
        sfasa = (j % 2) * passo_u / 2                                         # righe sfalsate: niente colonne di testo allineate
        for i in range(math.floor(min(su) / passo_u) - 1, math.ceil(max(su) / passo_u) + 2):
            s, t = i * passo_u + sfasa, j * passo_v
            x, y = s * u[0] + t * v[0], s * u[1] + t * v[1]
            out.paste(tinta, (round(x - m.width / 2), round(y - m.height / 2)), m)
    return out
