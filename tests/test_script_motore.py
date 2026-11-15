"""Script del motore (python -m impaginatore.motore.<script>) eseguiti nello stesso processo con aiuti.come_script:
analisi delle foto, verifica e modifica dei PSD, PDF dai PSD, abbinamento delle foto. Photoshop è finto (registra gli
script e risponde come lui); i PSD letti da psd-tools sono oggetti finti con la stessa forma (cornici, maschere vettoriali,
livelli di regolazione agganciati)."""
import json
import os
import re

import numpy as np
from aiuti import come_script
from PIL import Image

from impaginatore import formato


def _faces(prj, volti):
    """scrive _cache/faces.json prima del caricamento: niente OpenCV, volti dove dice la prova ({nome file: [riquadri]})"""
    os.makedirs(os.path.join(prj, "_cache"), exist_ok=True)
    tutti = {f: [] for f in os.listdir(os.path.join(prj, "Foto"))}
    formato.scrivi_json(os.path.join(prj, "_cache", "faces.json"), dict(tutti, **volti))


def _tinta(prj, nome, colore, misura=(900, 600)):
    """sostituisce una foto del progetto con una foto di un colore solo"""
    Image.new("RGB", misura, colore).save(os.path.join(prj, "Foto", nome + ".jpg"), quality=95)


def _rossi(im, soglia=60):
    a = np.asarray(im.convert("RGB")).astype(int)
    return int(((a[..., 0] > 200) & (a[..., 1] < soglia) & (a[..., 2] < soglia)).sum())


# ---------------------------------------------------------------- analizza
def test_analizza_provini(prj, monkeypatch, capsys):
    """provini: tutte le foto in miniatura, 20 per foglio (5 x 4), su fondo grigio; senza comando è quello predefinito"""
    _faces(prj, {})
    come_script(monkeypatch, "analizza", "--progetto", prj)
    p = os.path.join(prj, "_cache", "provini_1.jpg")
    assert capsys.readouterr().out.splitlines() == [p]
    with Image.open(p) as im:
        assert im.size == (5 * 310 + 10, 4 * 340 + 10)
        a = np.asarray(im.convert("RGB")).astype(int)
    pieno = lambda r, c: abs(a[10 + r * 340 + 150, 10 + c * 310 + 150] - (90, 90, 90)).sum() > 30       # centro della cella: foto o fondo?
    assert [pieno(r, c) for r in range(4) for c in range(5)] == [True] * 10 + [False] * 10, "le 10 foto nelle prime 10 celle, il resto vuoto"


def test_analizza_luminosita(prj, monkeypatch, capsys):
    """luminosità della pelle (L* dei volti): mediana dell'album e per cartella d'origine, foto fuori tono spread per spread;
    le foto in bianco e nero non contano"""
    _tinta(prj, "H01", (40, 30, 25)); _tinta(prj, "H02", (230, 190, 160)); _tinta(prj, "V03", (230, 190, 160)); _tinta(prj, "V04", (225, 185, 155))
    viso = [[0.3, 0.3, 0.7, 0.7]]
    _faces(prj, {"H01.jpg": viso, "H02.jpg": viso, "V03.jpg": viso, "V04.jpg": viso + [[0.0, 0.0, 0.05, 0.05]]})      # un volto piccolissimo non conta
    formato.scrivi_json(os.path.join(prj, "Foto", "origine.json"), {"H01.jpg": "/originali/Cerimonia", "H02.jpg": "/originali/Cerimonia"})
    come_script(monkeypatch, "analizza", "--progetto", prj, "luminosita")
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("pelle L* mediana album ") and out[0].endswith("foto con volti 4")
    gruppi = {re.match(r"  cartella (\S+): mediana [\d.]+ \(n=(\d)\)", r).groups() for r in out if r.startswith("  cartella")}
    assert gruppi == {("Cerimonia", "2"), ("Foto", "2")}
    spread = {r[:3]: r for r in out if re.match(r"S\d\d ", r)}
    assert set(spread) == {"S02", "S03", "S04"}, "solo gli spread con volti"
    assert "fuori tono" in spread["S02"] and "H01:" in spread["S02"].split("fuori tono")[1], "la foto scura accanto a una chiara"
    assert "fuori tono" not in spread["S03"] and "V03:" in spread["S03"] and "V04:" in spread["S03"]
    assert "V03" not in spread["S04"], "nello spread 4 V03 è in bianco e nero: non conta"
    assert out[-1].startswith("Nota:")


def test_analizza_luminosita_senza_impaginazione(prj, monkeypatch, capsys):
    """impaginazione che non si legge: le misure per foto e per cartella ci sono, quelle per spread no"""
    _faces(prj, {"H01.jpg": [[0.3, 0.3, 0.7, 0.7]]})
    with open(os.path.join(prj, "spec.py"), "w", encoding="utf-8") as f: f.write("SPREADS = [(\n")
    come_script(monkeypatch, "analizza", "--progetto", prj, "luminosita")
    out = capsys.readouterr().out
    assert "foto con volti 1" in out and "  cartella Foto:" in out and not re.search(r"^S\d\d ", out, re.M)


def test_analizza_ritagli(prj, monkeypatch, capsys):
    """ritagli: lo spread e sotto le foto intere con la finestra di ritaglio in rosso (i testi non hanno foto)"""
    _faces(prj, {})
    for n in ("H01", "H02", "V03", "V04", "Q05"): _tinta(prj, n, (120, 160, 200))
    come_script(monkeypatch, "analizza", "--progetto", prj, "ritagli", "2,3")
    fatti = capsys.readouterr().out.splitlines()
    assert fatti == [os.path.join(prj, "_cache", f"ritagli_0{n}.jpg") for n in (2, 3)]
    for f, foto in zip(fatti, (2, 3)):
        with Image.open(f) as im:
            sotto = im.crop((0, im.height - 400, im.width, im.height))
            assert _rossi(sotto) > 3 * 400 * foto, "un riquadro rosso per foto"


def test_analizza_colore(prj, monkeypatch, capsys):
    """colore: esposizione e zone neutre di ogni foto dello spread, con i guadagni proposti per il bilanciamento del bianco"""
    _faces(prj, {})
    _tinta(prj, "V10", (165, 160, 150)); _tinta(prj, "Q09", (220, 20, 30)); _tinta(prj, "H06", (150, 150, 150))
    come_script(monkeypatch, "analizza", "--progetto", prj, "colore", "1")
    righe = {r.split(":")[0]: r for r in capsys.readouterr().out.splitlines()}
    assert set(righe) == {"V10", "Q09", "H06"}
    assert "nessuna zona neutra" in righe["Q09"]
    g = json.loads(righe["V10"].split("guadagni proposti ")[1])
    assert g[2] > g[0], "una foto calda: più blu che rosso"
    assert righe["H06"].startswith("H06: EV +0.25 |") and "neutri a*=" in righe["H06"]


def test_analizza_comando_sconosciuto(prj, monkeypatch, capsys):
    _faces(prj, {})
    come_script(monkeypatch, "analizza", "--progetto", prj, "boh")
    assert "python analizza.py --progetto <cartella> provini" in capsys.readouterr().out
