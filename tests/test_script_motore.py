"""Script del motore (python -m impaginatore.motore.<script>) eseguiti nello stesso processo con aiuti.come_script:
analisi delle foto, verifica e modifica dei PSD, PDF dai PSD, abbinamento delle foto. Photoshop è finto (registra gli
script e risponde come lui); i PSD letti da psd-tools sono oggetti finti con la stessa forma (cornici, maschere vettoriali,
livelli di regolazione agganciati)."""
import glob
import json
import os
import pathlib
import re
import shutil
import types

import numpy as np
import pytest
from aiuti import come_script
from PIL import Image, ImageDraw

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


# ---------------------------------------------------------------- motore (album.py)
def test_ritaglio_sui_volti_ed_esposizione_per_cartella(prj):
    """il ritaglio si centra sui volti grandi (un volto piccolissimo, sotto il 15 % del più grande, non conta); l'esposizione
    somma globale, cartella d'origine (da origine.json, se no la cartella della foto) e foto"""
    cfg = formato.leggi_json(os.path.join(prj, "progetto.json"))
    cfg["esposizione"]["per_cartella"] = {os.path.join(prj, "Foto"): 0.5, "/originali/Cerimonia": -1.0}
    formato.scrivi_json(os.path.join(prj, "progetto.json"), cfg)
    formato.scrivi_json(os.path.join(prj, "Foto", "origine.json"), {"H02.jpg": "/originali/Cerimonia"})
    _faces(prj, {"H01.jpg": [[0.7, 0.3, 0.9, 0.6], [0.0, 0.0, 0.02, 0.02]]})
    A = _carica(prj); i = A.IDX["H01"] - 1
    l, t, r, b = A.crop(i, 500, 1000)                      # foto 3:2 in una cornice 1:2: si tiene un terzo della larghezza
    assert (round(l, 4), t, round(r, 4), b) == (0.6333, 0, 0.9667, 1), "centrato sul volto grande (0.8), non a metà strada con quello piccolo"
    assert [A.ev_for(A.IDX[n] - 1) for n in ("H01", "H02", "V03")] == [0.75, -0.75, 1.25]


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


def test_analizza_luminosita_senza_volti(prj, monkeypatch, capsys):
    """senza nessun volto trovato lo dice ed esce senza errore (prima: IndexError di numpy su un elenco vuoto)"""
    _faces(prj, {})
    with pytest.raises(SystemExit) as e: come_script(monkeypatch, "analizza", "--progetto", prj, "luminosita")
    assert e.value.code == 0
    assert capsys.readouterr().out.strip() == "nessun volto trovato nelle foto: la luminosità della pelle non si può misurare"


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
    come_script(monkeypatch, "analizza", "--progetto", prj, "colore", "2")
    assert [r.split(":")[0] for r in capsys.readouterr().out.splitlines()] == ["H02", "H01"], "il testo dello spread 2 non è una foto"


def test_analizza_comando_sconosciuto(prj, monkeypatch, capsys):
    _faces(prj, {})
    come_script(monkeypatch, "analizza", "--progetto", prj, "boh")
    assert "python analizza.py --progetto <cartella> provini" in capsys.readouterr().out


# ---------------------------------------------------------------- PSD finti (forma di psd_tools) e Photoshop finto
class _Livello:
    """livello come lo dà psd_tools: i gruppi si scorrono, la maschera vettoriale ha i punti in frazioni (y, x) del documento,
    i livelli di regolazione hanno kind ed exposure e possono essere agganciati (clipping) al livello sotto"""

    def __init__(self, name, figli=(), rett=None, kind="group", clipping=False, exposure=0.0):
        self.name, self.figli, self.rett, self.kind, self.clipping, self.exposure = name, list(figli), rett, kind, clipping, exposure
        self.misura = None

    def is_group(self): return self.kind == "group"

    def has_vector_mask(self): return self.rett is not None

    @property
    def vector_mask(self):
        (x0, y0, x1, y1), (W, H) = self.rett, self.misura
        nodo = lambda x, y: types.SimpleNamespace(anchor=(y / H, x / W))
        return types.SimpleNamespace(paths=[[nodo(x0, y0), nodo(x1, y0), nodo(x1, y1), nodo(x0, y1)]])

    def __iter__(self): return iter(self.figli)


class _PSD:
    def __init__(self, misura, livelli, ppi=300):
        self.size, self.livelli = misura, livelli
        self.image_resources = types.SimpleNamespace(get_data=lambda k: types.SimpleNamespace(horizontal=ppi * 65536) if k == 1005 and ppi else None)
        for L in self.descendants(): L.misura = misura

    def __iter__(self): return iter(self.livelli)

    def descendants(self):
        def giu(ls):
            for L in ls: yield L; yield from giu(L.figli)
        return giu(self.livelli)


def _cornice(nome, rett, ev=None, bw=False, altro=()):
    """cornice di genera_psd: gruppo con maschera vettoriale (dentro la foto), sopra le regolazioni agganciate"""
    out = [_Livello(nome, [_Livello(nome, kind="smartobject")], rett=rett)]
    if ev is not None: out.append(_Livello("Esposizione", kind="exposure", clipping=True, exposure=ev))
    if bw: out.append(_Livello("Bianco e nero", kind="blackandwhite", clipping=True))
    out += [_Livello(k, kind=k, clipping=True) for k in altro]
    return out


def _psd_spread(A, n, ev=None):
    """il PSD dello spread n come lo scrive genera_psd dall'impaginazione (ev: {foto: esposizione}, se no ev_for)"""
    pagine = {"L": [], "R": []}
    for it in A.layout(A.load_spec()[n - 1]):
        if it["k"] == "t": pagine[it["side"]].append(_Livello("Testo", kind="type")); continue
        nm = A.name(it["i"])
        pagine[it["side"]] += _cornice(nm, (it["x"], it["y"], it["x"] + it["W"], it["y"] + it["H"]), (ev or {}).get(nm, A.ev_for(it["i"])), it.get("bw"))
    return _PSD((A.CW, A.CH), [_Livello("Sfondo", kind="pixel"), _Livello("Pagina sinistra", pagine["L"], rett=(0, 0, A.FOLD, A.CH)),
                                _Livello("Pagina destra", pagine["R"], rett=(A.FOLD, 0, A.CW, A.CH))])


def _carica(prj):
    """il motore con il progetto caricato (come lo vedono gli script), per costruire i PSD finti"""
    from impaginatore.motore import album
    return album.carica_progetto(prj)


def _psd_su_disco(prj, monkeypatch, psd):
    """{numero spread: _PSD o eccezione}: file Spread_NN.psd nella cartella dei PSD, psd_tools li «apre» da qui"""
    import psd_tools
    out = os.path.join(prj, "PSD"); os.makedirs(out, exist_ok=True)
    for n in psd:
        with open(os.path.join(out, f"Spread_{n:02d}.psd"), "wb") as f: f.write(b"8BPS" + bytes([n]) * 64)

    def apri(p):
        v = psd[int(re.findall(r"(\d+)\.psd", p)[0])]
        if isinstance(v, Exception): raise v
        return v
    monkeypatch.setattr(psd_tools.PSDImage, "open", staticmethod(apri))
    return out


class _Photoshop:
    """Photoshop finto: documenti aperti da esegui_js, script .jsx registrati; risponde con `risposta(script)`"""

    def __init__(self, monkeypatch, aperti="", risposta=lambda js: "fatto"):
        from impaginatore.piattaforma import photoshop
        self.aperti, self.risposta, self.jsx = aperti, risposta, []
        for n in ("trova", "esegui_js", "esegui_jsx"): monkeypatch.setattr(photoshop, n, getattr(self, n))

    def trova(self): return dict(nome="Adobe Photoshop 2026", percorso="/Applications/x.app")

    def esegui_js(self, codice): return self.aperti

    def esegui_jsx(self, path, timeout=3600):
        with open(path, encoding="ascii") as f: self.jsx.append(f.read())
        return self.risposta(self.jsx[-1])

    def var(self, nome, dopo):
        """valore JSON di «var NOME=...; var DOPO=» nell'ultimo script"""
        return json.loads(re.search(rf"var {nome}=(.*?); var {dopo}=", self.jsx[-1]).group(1))


# ---------------------------------------------------------------- verifica_psd
def test_verifica_psd_come_generati(prj, monkeypatch, capsys):
    """PSD uguali all'impaginazione: misure, cornici con le loro regolazioni, nessun problema; foto doppie e non usate
    (H08 nello spread 5 che non c'è; V07 è tolta) sull'album intero; uno spread oltre l'impaginazione non si confronta"""
    _faces(prj, {}); A = _carica(prj)
    psd = {n: _psd_spread(A, n) for n in (1, 2, 3, 4)}
    psd[9] = _PSD((A.CW, A.CH), [_Livello("Sfondo", kind="pixel")])
    _psd_su_disco(prj, monkeypatch, psd)
    come_script(monkeypatch, "verifica_psd", "--progetto", prj, "--confronta-spec")
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Spread 01: 7087x2657px 60.00x22.50cm @300.00 | V10 [+0.25], Q09 [+0.25], H06 [+0.25]"
    assert out[1] == "Spread 02: 7087x2657px 60.00x22.50cm @300.00 | H02 [+0.25], H01 [+0.25]"
    assert out[3] == "Spread 04: 7087x2657px 60.00x22.50cm @300.00 | V03 [+0.75 BN], V04 [+0.25], Q05 [+0.25]"
    assert out[4] == "Spread 09: 7087x2657px 60.00x22.50cm @300.00 | "
    assert "CONTROLLA" not in "\n".join(out)
    assert out[-1] == "foto nei PSD 11 | doppie ['V03', 'V04', 'Q05'] | non usate ['H08'] | spread con problemi 0"


def test_verifica_psd_segnala_i_problemi(prj, monkeypatch, capsys):
    """cornice a cavallo della piega, fuori pagina, spazi diversi da quello del progetto (in orizzontale e in verticale; i
    margini ai lati della piega vanno bene), misura del documento sbagliata, cornici diverse dall'impaginazione"""
    _faces(prj, {}); A = _carica(prj)
    G, MG, F = A.G, A.MG, round(A.FOLD)
    assert (G, MG) == (30, 118)
    sinistra = (_cornice("V03", (100, 100, 600, 900), 0.5, altro=("channelmixer", "curves")) + [_Livello("Testo", kind="type")]
                + _cornice("V04", (650, 100, 1000, 900)) + _cornice("Q05", (1500, 100, 1900, 500)) + _cornice("H06", (1500, 545, 1900, 900))
                + _cornice("H08", (2400, 100, F - MG, 900)))
    destra = _cornice("V10", (F + MG, 100, F + 1000, 900)) + _cornice("H02", (F - 150, 1400, F + 150, 1800), bw=True) + _cornice("H01", (6800, 2000, A.CW + 50, 2600))
    _psd_su_disco(prj, monkeypatch, {2: _PSD((A.CW + 10, A.CH), [_Livello("Pagina sinistra", sinistra), _Livello("Pagina destra", destra)])})
    come_script(monkeypatch, "verifica_psd", "--progetto", prj, "--confronta-spec")
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("Spread 02: 7097x2657px") and out[0].endswith("| V03 [+0.50 WB curves], V04, Q05, H06, H08, V10, H02 [BN], H01")
    problemi = out[1].split("<-- CONTROLLA: ")[1].split("; ")
    assert problemi == ["spazio 50px V03|V04", "spazio 45px Q05/H06", "H02 a cavallo della piega", "H01 esce dalla pagina",
                        "misura 7097x2657 invece di 7087x2657", "cornici diverse dalla spec (normale se modificato a mano)"]
    assert out[-1].endswith("spread con problemi 1")


def test_verifica_psd_senza_risoluzione(prj, monkeypatch, capsys):
    """un PSD senza la risoluzione scritta (risorsa 1005, facoltativa) si verifica lo stesso: misure in px, cm sconosciuti
    (prima: ZeroDivisionError)"""
    _faces(prj, {}); A = _carica(prj)
    _psd_su_disco(prj, monkeypatch, {1: _PSD((A.CW, A.CH), _psd_spread(A, 1).livelli, ppi=0)})
    come_script(monkeypatch, "verifica_psd", "--progetto", prj)
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Spread 01: 7087x2657px (risoluzione non scritta nel PSD) | V10 [+0.25], Q09 [+0.25], H06 [+0.25]"


# ---------------------------------------------------------------- modifica_psd
def _copre(op, rett, foto):
    """la foto messa nella cornice (left, top, width in px del PSD) copre tutta la cornice e ha le proporzioni della foto"""
    with Image.open(foto) as im: w, h = im.size
    x0, y0, x1, y1 = rett; alto = op["width"] * h / w
    return op["left"] <= x0 + 1e-6 and op["top"] <= y0 + 1e-6 and op["left"] + op["width"] >= x1 - 1e-6 and op["top"] + alto >= y1 - 1e-6


def _copie(prj):
    """{nome: contenuto} dei file nelle copie di sicurezza di modifica_psd"""
    return {f: pathlib.Path(d, f).read_bytes() for d in glob.glob(os.path.join(prj, "PSD_vecchi", "backup_*")) for f in os.listdir(d)}


def test_modifica_psd_scambia(prj, monkeypatch, capsys):
    """scambio di due foto tra spread diversi: l'esposizione regolata nel PSD segue la foto, la foto riempie la cornice
    dell'altra; prima di toccare i PSD se ne fa una copia; Photoshop riceve lo script e la sua risposta si stampa"""
    _faces(prj, {}); A = _carica(prj)
    out = _psd_su_disco(prj, monkeypatch, {3: _psd_spread(A, 3, ev={"V04": -0.3}), 4: _psd_spread(A, 4, ev={"Q05": 0.4})})
    prima = {f: pathlib.Path(out, f).read_bytes() for f in os.listdir(out)}
    ps = _Photoshop(monkeypatch, risposta=lambda js: "3: V04 -> Q05\n4: Q05 -> V04")
    come_script(monkeypatch, "modifica_psd", "--progetto", prj, "scambia", "3:V04", "4:Q05")
    ops = ps.var("OPS", "OUT"); foto = os.path.join(prj, "Foto")
    assert [{k: o[k] for k in ("op", "n", "frame", "photo", "ev")} for o in ops] == [dict(op="replace", n=3, frame="V04", photo="Q05", ev=0.4),
                                                                                    dict(op="replace", n=4, frame="Q05", photo="V04", ev=-0.3)]
    assert os.path.samefile(ops[0]["file"], os.path.join(foto, "Q05.jpg")) and _copre(ops[0], (1779, 0, 3528, 2657), os.path.join(foto, "Q05.jpg"))
    assert os.path.samefile(ops[1]["file"], os.path.join(foto, "V04.jpg")) and _copre(ops[1], (5052, 424, 6691, 2233), os.path.join(foto, "V04.jpg"))
    assert json.loads(re.search(r"var OUT=(.*?);\n", ps.jsx[-1]).group(1)) == out
    assert _copie(prj) == prima, "copia di sicurezza dei due PSD, uguali a prima"
    stampa = capsys.readouterr().out
    assert "copia di sicurezza: " + os.path.join(prj, "PSD_vecchi", "backup_") in stampa and stampa.endswith("3: V04 -> Q05\n4: Q05 -> V04\n")


def test_modifica_psd_una_cornice(prj, monkeypatch):
    """sostituisci (con l'esposizione del progetto per la foto nuova), colore, bn, esposizione: un'operazione sulla cornice"""
    _faces(prj, {}); A = _carica(prj)
    _psd_su_disco(prj, monkeypatch, {1: _psd_spread(A, 1), 4: _psd_spread(A, 4)})
    ps = _Photoshop(monkeypatch); fatti = []
    for comando in (["sostituisci", "1:H06", "H08"], ["colore", "4:V03"], ["bn", "1:Q09"], ["esposizione", "1:V10", "0.95"]):
        come_script(monkeypatch, "modifica_psd", "--progetto", prj, *comando)
        fatti.append(ps.var("OPS", "OUT"))
    h08 = os.path.join(prj, "Foto", "H08.jpg")
    assert {k: fatti[0][0][k] for k in ("op", "n", "frame", "photo", "ev")} == dict(op="replace", n=1, frame="H06", photo="H08", ev=0.25)
    assert os.path.samefile(fatti[0][0]["file"], h08) and _copre(fatti[0][0], (5338, 1344, 7087, 2657), h08)
    assert fatti[1:] == [[dict(op="colore", n=4, frame="V03")], [dict(op="bn", n=1, frame="Q09")], [dict(op="esposizione", n=1, frame="V10", ev=0.95)]]
    assert sorted(_copie(prj)) == ["Spread_01.psd", "Spread_04.psd"]


@pytest.mark.parametrize("salvato, motivo", [("false", "Spread_01.psd è aperto in Photoshop CON MODIFICHE NON SALVATE: chiedi all'utente di salvarlo e chiuderlo"),
                                             ("true", "Spread_01.psd è aperto in Photoshop: chiedi all'utente di salvarlo e chiuderlo")])
def test_modifica_psd_documento_aperto(prj, monkeypatch, salvato, motivo):
    """un PSD aperto in Photoshop non si tocca: nessuna copia, nessuno script, si dice perché"""
    _faces(prj, {}); A = _carica(prj)
    _psd_su_disco(prj, monkeypatch, {1: _psd_spread(A, 1), 2: _psd_spread(A, 2)})
    ps = _Photoshop(monkeypatch, aperti=f"Altro.psd|true\nSpread_01.psd|{salvato}")
    with pytest.raises(SystemExit) as e: come_script(monkeypatch, "modifica_psd", "--progetto", prj, "scambia", "2:H01", "1:V10")
    assert str(e.value) == motivo
    assert ps.jsx == [] and not os.path.exists(os.path.join(prj, "PSD_vecchi"))


def test_modifica_psd_rifai_pagina(prj, monkeypatch, capsys):
    """rifai-pagina ricostruisce solo la pagina chiesta dall'impaginazione attuale (i testi no): esposizioni già regolate
    nei PSD (anche di altri spread; un PSD che non si legge si salta), bilanciamento del bianco, bianco e nero"""
    cfg = formato.leggi_json(os.path.join(prj, "progetto.json")); cfg["bilanciamento_bianco"] = {"H02": [1.1, 1.0, 0.9]}
    formato.scrivi_json(os.path.join(prj, "progetto.json"), cfg)
    _faces(prj, {}); A = _carica(prj)
    out = _psd_su_disco(prj, monkeypatch, {2: _psd_spread(A, 2, ev={"H02": 0.9}), 4: _psd_spread(A, 4, ev={"V03": 1.2}), 7: ValueError("PSD rovinato")})
    ps = _Photoshop(monkeypatch, risposta=lambda js: "ok")
    come_script(monkeypatch, "modifica_psd", "--progetto", prj, "rifai-pagina", "2", "sinistra")
    (h02,) = ps.var("ITEMS", "F"); foto = os.path.join(prj, "Foto", "H02.jpg")
    assert {k: h02[k] for k in ("name", "rect", "ev", "bw", "wb")} == dict(name="H02", rect=[396, 424, 3147, 2233], ev=0.9, bw=False, wb=[104.4, 100.0, 95.3])
    assert os.path.samefile(h02["file"], foto) and _copre(h02, h02["rect"], foto)
    assert json.loads(re.search(r"var F=(.*?); var GROUP=(.*?);\n", ps.jsx[-1]).group(1)) == os.path.join(out, "Spread_02.psd")
    assert json.loads(re.search(r"var GROUP=(.*?);\n", ps.jsx[-1]).group(1)) == "Pagina sinistra"
    come_script(monkeypatch, "modifica_psd", "--progetto", prj, "rifai-pagina", "4", "sinistra")
    assert [{k: it[k] for k in ("name", "ev", "bw", "wb")} for it in ps.var("ITEMS", "F")] == [dict(name="V03", ev=1.2, bw=True, wb=None), dict(name="V04", ev=0.25, bw=False, wb=None)]
    assert sorted(_copie(prj)) == ["Spread_02.psd", "Spread_04.psd"] and capsys.readouterr().out.count("copia di sicurezza: ") == 2


# ---------------------------------------------------------------- esporta_pdf
COLORI = {"Spread_01": (200, 40, 40), "Spread_02": (40, 160, 60)}


def _esporta_jpg(js):
    """Photoshop finto per esporta_pdf: «salva come JPEG» gli spread chiusi nella cartella indicata dallo script; quello
    aperto lo salta"""
    cartella = json.loads(re.search(r'new File\((".*?")\+"/"\+nm', js).group(1))
    for nm, c in COLORI.items(): Image.new("RGB", (708, 265), c).save(os.path.join(cartella, nm + ".jpg"), quality=95)
    return "Spread_01.psd\nSALTATO (aperto): Spread_03.psd\nSpread_02.psd"


def _pagine_pdf(p):
    with open(p, "rb") as f: return len(re.findall(rb"/Type\s*/Page\b", f.read()))


def _colore(im, xy): return tuple(int(v) for v in im.convert("RGB").getpixel(xy))


def _vicino(c, atteso, tol=30): return all(abs(a - b) <= tol for a, b in zip(c, atteso))


@pytest.mark.parametrize("copertina", [None, "H01"])
def test_esporta_pdf(prj, monkeypatch, capsys, copertina):
    """PDF leggero dai PSD esportati da Photoshop: una pagina per spread (con la piega e il numero), in testa la copertina
    se chiesta; gli spread aperti in Photoshop si saltano e si dice; i JPEG di un'esportazione vecchia non entrano"""
    _faces(prj, {}); _tinta(prj, "H01", (30, 60, 220))
    vecchi = os.path.join(prj, "_cache", "export_pdf"); os.makedirs(vecchi); Image.new("RGB", (10, 10)).save(os.path.join(vecchi, "Spread_05.jpg"))
    ps = _Photoshop(monkeypatch, risposta=_esporta_jpg)
    come_script(monkeypatch, "esporta_pdf", "--progetto", prj, "--nome", "Prova àè", "--larghezza", "400", *(["--copertina", copertina] if copertina else []))
    pdf = os.path.join(prj, "Prova àè.pdf")
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "SALTATO (aperto): Spread_03.psd" and out[1] == pdf
    assert out[2].startswith(f"{3 if copertina else 2} pagine, ") and _pagine_pdf(pdf) == (3 if copertina else 2)
    assert "app.open(f[i])" in ps.jsx[-1] and json.loads(re.search(r"new Folder\((\".*?\")\)", ps.jsx[-1]).group(1)) == os.path.join(prj, "PSD")
    with Image.open(os.path.join(prj, "_cache", "pdf_pagina1.jpg")) as p1:
        assert p1.size == (400, round(400 * 2657 / 7087) + 60)
        if copertina:
            assert _vicino(_colore(p1, (200, 130)), (30, 60, 220)) and _colore(p1, (5, 130)) == (255, 255, 255), "la foto di copertina al centro, bordi bianchi"
        else:
            assert _vicino(_colore(p1, (100, 75)), COLORI["Spread_01"]) and _colore(p1, (100, 180)) == (255, 255, 255), "lo spread sopra, il numero sotto su bianco"


def test_esporta_pdf_ipotesi_di_copertina(prj, monkeypatch, capsys):
    """più foto di copertina (nomi del progetto o percorsi di file): una pagina «ipotesi di copertina» con le foto affiancate"""
    _faces(prj, {}); _tinta(prj, "H01", (30, 60, 220))
    altra = os.path.join(prj, "altra.jpg"); Image.new("RGB", (600, 900), (240, 200, 20)).save(altra)
    _Photoshop(monkeypatch, risposta=_esporta_jpg)
    come_script(monkeypatch, "esporta_pdf", "--progetto", prj, "--larghezza", "800", "--copertina", "H01," + altra)
    assert _pagine_pdf(os.path.join(prj, "Album - bozza.pdf")) == 3
    with Image.open(os.path.join(prj, "_cache", "pdf_pagina1.jpg")) as p1:
        assert _vicino(_colore(p1, (230, 180)), (30, 60, 220)) and _vicino(_colore(p1, (570, 180)), (240, 200, 20)), "A a sinistra, B a destra"


# ---------------------------------------------------------------- abbina
def _scatto(p, w, h, colore):
    """foto sintetica: fondo di un colore con un cerchio chiaro (a misure diverse resta «la stessa foto»)"""
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im = Image.new("RGB", (w, h), colore); ImageDraw.Draw(im).ellipse((w // 4, h // 4, 3 * w // 4, 3 * h // 4), fill=(240, 230, 200)); im.save(p, quality=92)


def test_abbina(tmp_path, monkeypatch, capsys):
    """per ogni foto scelta (versione web): trovata negli originali, nome in due cartelle (si sceglie quella con la foto
    uguale), originale identico alla versione web o piccolo (non si copia), visivamente diverso (si copia e si avvisa);
    un file già nella destinazione e diverso non si sovrascrive; origine.json dice da che cartella viene ogni foto"""
    web, cap1, cap2, dest = (str(tmp_path / n) for n in ("web", "cap1", "cap2", "dest"))
    for n, c in (("A1", (200, 60, 60)), ("A2", (60, 200, 60)), ("A3", (60, 60, 200)), ("A4", (120, 120, 30)), ("A5", (30, 120, 120)), ("A6", (150, 30, 150))):
        _scatto(os.path.join(web, n + ".jpg"), 300, 200, c)
    _scatto(os.path.join(web, ".A7.jpg"), 300, 200, (0, 0, 0)); open(os.path.join(web, "note.txt"), "w").close()
    _scatto(os.path.join(cap1, "A1.jpg"), 900, 600, (200, 60, 60))
    _scatto(os.path.join(cap1, "A3.jpg"), 900, 600, (60, 60, 200)); _scatto(os.path.join(cap2, "A3.jpg"), 900, 600, (230, 230, 30))
    shutil.copy(os.path.join(web, "A4.jpg"), os.path.join(cap1, "A4.jpg"))
    _scatto(os.path.join(cap1, "A5.jpg"), 500, 300, (30, 120, 120))
    _scatto(os.path.join(cap2, "A6.jpg"), 900, 600, (10, 10, 10)); _scatto(os.path.join(cap2, ".A1.jpg"), 900, 600, (0, 0, 0))
    _scatto(os.path.join(dest, "A6.jpg"), 50, 50, (1, 2, 3)); gia = pathlib.Path(dest, "A6.jpg").read_bytes()
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", Image.MAX_IMAGE_PIXELS)          # lo script lo cambia (limite del progetto): solo per lui
    come_script(monkeypatch, "abbina", "--web", web, "--originali", cap1, cap2, "--dest", dest, "--lato-minimo", "800")
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "selezione: 6 foto | pronte da copiare: 3 | da controllare: 5"
    assert out[1] == "  - A2.jpg: NON trovata negli originali"
    assert re.fullmatch(r"  - A3\.jpg: nome presente in 2 cartelle -> uso cap1 \(differenza [\d.]+\)", out[2])
    assert out[3] == "  - A4.jpg: l'originale è IDENTICO alla versione web -> forse non riesportato in alta"
    assert out[4] == "  - A5.jpg: originale piccolo (500x300) -> controlla l'esportazione"
    assert re.fullmatch(r"  - A6\.jpg: l'originale è visivamente diverso dalla scelta \(differenza [\d.]+\): post-produzione cambiata\?", out[5])
    assert out[6:] == ["per cartella: {'cap1': 2, 'cap2': 1}", "  esiste già diverso, non sovrascrivo: A6.jpg", "copiate e verificate: 2 | errori di copia: ['A6.jpg']"]
    assert sorted(os.listdir(dest)) == ["A1.jpg", "A3.jpg", "A6.jpg", "origine.json"] and pathlib.Path(dest, "A6.jpg").read_bytes() == gia
    assert pathlib.Path(dest, "A3.jpg").read_bytes() == pathlib.Path(cap1, "A3.jpg").read_bytes()
    assert formato.leggi_json(os.path.join(dest, "origine.json")) == {"A1.jpg": cap1, "A3.jpg": cap1, "A6.jpg": cap2}


def test_abbina_prova_non_copia(tmp_path, monkeypatch, capsys):
    web, orig, dest = (str(tmp_path / n) for n in ("web", "orig", "dest"))
    _scatto(os.path.join(web, "A1.jpg"), 300, 200, (200, 60, 60)); _scatto(os.path.join(orig, "A1.jpg"), 900, 600, (200, 60, 60))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", Image.MAX_IMAGE_PIXELS)
    come_script(monkeypatch, "abbina", "--web", web, "--originali", orig, "--dest", dest, "--lato-minimo", "800", "--prova")
    assert capsys.readouterr().out.splitlines() == ["selezione: 1 foto | pronte da copiare: 1 | da controllare: 0", "per cartella: {'orig': 1}"]
    assert not os.path.exists(dest)


# ---------------------------------------------------------------- anteprima
def test_anteprima_segnala_spazi_e_basta_il_foglio(prj, monkeypatch, capsys):
    """cornici libere a una distanza diversa dallo spazio del progetto: il controllo lo dice; senza --spread e --prima-dopo
    si fanno solo il foglio con tutti gli spread e la sequenza"""
    _faces(prj, {})
    with open(os.path.join(prj, "spec.py"), "w", encoding="utf-8") as f:
        f.write("from album import *\nfrom album_libere import *\nSPREADS = [\n    (W(FREE('H01', 0.0, 0.1, 0.4, 0.5), FREE('H02', 0.45, 0.1, 0.4, 0.5)), W()),\n]\n")
    come_script(monkeypatch, "anteprima", "--progetto", prj)
    out = capsys.readouterr().out
    assert re.search(r"^  S01 spazio \d+px tra H01 e H02$", out, re.M) and "problemi 1" in out
    assert sorted(os.listdir(os.path.join(prj, "Anteprime"))) == ["Anteprima - 1 spread.jpg", "Sequenza.txt"]
    with open(os.path.join(prj, "Anteprime", "Sequenza.txt"), encoding="utf-8") as f: assert f.read() == "Spread 01  sx: [bianca] H01, H02  |  dx: [bianca] \n"
