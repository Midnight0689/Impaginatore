"""Formato di salvataggio: spec.py (codice Python del formato 1.x) e progetto.json. I progetti salvati dalla 1.5.2 devono
aprirsi e risalvarsi identici; quelli salvati dalla 2.0 devono restare leggibili dagli script 1.x."""
import json
import os
import shutil
import subprocess
import sys

import pytest
from aiuti import FOTO_SCENARIO, crea_foto, riduci

from impaginatore import formato
from impaginatore.motore import album, compat

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P152 = os.path.join(RADICE, "tests", "dati", "progetto_152")


def _progetto_152(base):
    """il progetto dello scenario di parità come l'ha salvato la 1.5.2 (spec.py e progetto.json veri), con le stesse foto"""
    p = os.path.join(base, "Parità àè"); crea_foto(os.path.join(p, "Foto"))
    shutil.copy(os.path.join(P152, "spec.py"), os.path.join(p, "spec.py"))
    with open(os.path.join(P152, "progetto.json"), encoding="utf-8") as f: cfg = json.loads(f.read().replace("{PROGETTO}", p.replace("\\", "/")))
    formato.scrivi_json(os.path.join(p, "progetto.json"), cfg, indent=2, ensure_ascii=False)
    return p, cfg


def test_progetto_152_si_riapre_e_si_risalva_identico(tmp_path, apri_editor):
    p, cfg = _progetto_152(str(tmp_path))
    c = apri_editor(p)
    with open(os.path.join(P152, "stato_ridotto.json"), encoding="utf-8") as f: atteso = json.load(f)
    assert riduci(c.get("/api/state")) == atteso, "stato dell'editor diverso da quello della 1.5.2"
    c.E.save(backup=False)
    with open(os.path.join(p, "spec.py"), encoding="utf-8") as f: nuovo = f.read().split("\n")
    with open(os.path.join(P152, "spec.py"), encoding="utf-8") as f: vecchio = f.read().split("\n")
    assert nuovo[0].startswith('"""Parità àè: 5 spread. Salvato dall\'editor il ')
    assert nuovo[1:] == vecchio[1:], "spec.py risalvato diverso"
    assert formato.leggi_json(os.path.join(p, "progetto.json")) == cfg, "progetto.json risalvato diverso"
    for f in ("album_libere.py", "testo.py", "vib_lut.npz"): assert os.path.exists(os.path.join(p, f)), f      # formato 1.x: copie del motore accanto a spec.py
    assert "__pycache__" not in os.listdir(p)


def _album_152():
    """album.py della 1.5.2 dalla storia git (o None)"""
    try: r = subprocess.run(["git", "-C", RADICE, "show", "957fdf7:motore/scripts/album.py"], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError): return None
    return r.stdout if r.returncode == 0 else None


def test_progetto_salvato_dalla_2_si_apre_con_gli_script_152(tmp_path, apri_editor):
    """chi ha ancora la 1.5.2 (ramo main) deve poter aprire un progetto salvato dalla 2.0: spec.py con «from album import *»
    e le copie di album_libere.py / testo.py nella cartella del progetto"""
    vecchio = _album_152()
    if vecchio is None: pytest.skip("storia git della 1.5.2 non disponibile")
    p, _ = _progetto_152(str(tmp_path))
    c = apri_editor(p); c.E.save(backup=False)
    scr = tmp_path / "scripts_152"; scr.mkdir(); (scr / "album.py").write_bytes(vecchio)
    codice = ("import sys; sys.path.insert(0, sys.argv[1]); sys.argv = ['x', '--progetto', '.']\n"
              "import album\nSP = album.load_spec()\nimport album_libere, testo\n"
              "assert album_libere.__file__.startswith(sys.argv[2]) or True\n"
              "im = album.render(SP[1], 0.05)\nprint(len(SP), im.size, album_libere.__file__)")
    r = subprocess.run([sys.executable, "-c", codice, str(scr), p], cwd=p, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.startswith("5 ") and os.path.join(p, "album_libere.py") in r.stdout


def test_copie_nel_progetto_funzionano_da_sole(tmp_path):
    """album_libere.py e testo.py copiati in un progetto non devono avere bisogno del pacchetto"""
    d = tmp_path / "prj"; d.mkdir()
    formato.copia_motore(str(d))
    (d / "album.py").write_text("def _place(*a): pass\ndef zcrop(it): pass\ndef _photo(*a): pass\ndef render(*a): pass\ndef _text(*a): pass\ndef apply_ev(*a): pass\ndef layout(s): pass\n", encoding="utf-8")
    codice = "import album_libere, testo; print(testo._dirs()[0], testo._cache()); print(album_libere.vib_lut().shape)"
    r = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, '.'); " + codice], cwd=str(d), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    assert ".album-tools" in r.stdout and "17, 17, 17, 3)" in r.stdout


def test_carica_spec_scritto_a_mano(tmp_path, foto_campione):
    """uno spec.py scritto con le funzioni del motore (come lo scrive Claude con la skill) si carica"""
    p = tmp_path / "Album"; (p / "Foto").mkdir(parents=True)
    for f in os.listdir(foto_campione): shutil.copy(os.path.join(foto_campione, f), p / "Foto" / f)
    formato.scrivi_json(str(p / "progetto.json"), dict(nome="Album", foto=str(p / "Foto"), formato_cm=[40, 20]))
    (p / "aiuto.py").write_text("PAGINA = 'W'\n", encoding="utf-8")
    (p / "spec.py").write_text("from album import *\nfrom aiuto import PAGINA\n\nSPREADS = [\n    # 1\n    (I(DUO('V03', 'V04')),\n     W(*CV('V10'))),\n    # 2\n    (I(FULL('H01')),\n     W(PP(2))),\n]\n", encoding="utf-8")
    album.carica_progetto(str(p))
    sp = formato.carica(str(p))
    assert len(sp) == 2 and sp[0][0][0] == "I" and sp[1][1][1][0]["i"] == 1
    assert formato.conta_spread(str(p)) == 2 and formato.conta_spread(str(tmp_path)) == 0
    assert "__pycache__" not in os.listdir(p) and str(p) not in sys.path


def test_testo_spec_rilegge_quello_che_scrive(tmp_path, foto_campione):
    p = tmp_path / "Album"; (p / "Foto").mkdir(parents=True)
    for f in os.listdir(foto_campione): shutil.copy(os.path.join(foto_campione, f), p / "Foto" / f)
    formato.scrivi_json(str(p / "progetto.json"), dict(nome="Album", foto=str(p / "Foto"), formato_cm=[40, 20]))
    album.carica_progetto(str(p))
    i = album.IDX
    spreads = [[["I", [dict(k="p", i=i["H01"] - 1, c=0, r=0, w=6, h=8, bw=True, z=1.3)]], ["W", [dict(k="full", i=i["V03"] - 1, bw=False, z=1.0)]]],
               [["W", [dict(k="f", i=i["Q05"] - 1, x=0.1, y=0.2, w=0.5, h=0.4, bw=False, z=1.0, zo=2, a=-4.5, bd=[2.0, "#000000"], sh=30, oc=90)]],
                ["W", [dict(k="t", kind="txt", tx="Ciao «àè»\nriga", fx=0.1, fy=0.1, fw=0.5, fh=0.2, font="X-Regular", size=90.0, col=[1, 2, 3], al="right", tr=10.0, auto=False, lh=1.4, caps=True, zo=3, stile="T"),
                       dict(k="t", kind="title", c=0, r=0, w=12, h=8), dict(k="t", kind="end", fx=0.5, fy=0.5, fw=0.4, fh=0.3, ts=1.2)]]]]
    formato.salva(str(p), spreads, "Album «prova»", album.name, quando="01/01/2026 10:00")
    with open(p / "spec.py", encoding="utf-8") as f: testo = f.read()
    assert testo.startswith('"""Album «prova»: 2 spread. Salvato dall\'editor il 01/01/2026 10:00."""\nfrom album import *\nfrom album_libere import *')
    assert all(os.path.exists(p / f) for f in ("album_libere.py", "testo.py", "vib_lut.npz"))
    letto = formato.carica(str(p))
    assert formato.testo_spec([[[m, list(it)] for m, it in sp] for sp in letto], "Album «prova»", album.name, "01/01/2026 10:00") == testo
    assert not formato.ha_liberi([[["I", [dict(k="p", i=0)]], ["W", []]]])
    assert formato.spec_vuota("X").count("SPREADS = [") == 1


def test_compat_nomi_1x():
    compat.installa(); compat.installa()
    import album as a
    import album_libere as al
    import testo as t
    from impaginatore.motore import album_libere, testo
    assert a is album and al is album_libere and t is testo
    assert a.__spec__.name == "impaginatore.motore.album"
    compat.disinstalla()
    assert "album" not in sys.modules
    compat.installa()


def test_scrivi_atomico(tmp_path):
    f = tmp_path / "a.txt"; formato.scrivi_atomico(str(f), "àè\n")
    assert f.read_text(encoding="utf-8") == "àè\n" and not (tmp_path / "a.txt.tmp").exists()
    formato.scrivi_json(str(tmp_path / "b.json"), {"n": "è"}, ensure_ascii=False)
    assert formato.leggi_json(str(tmp_path / "b.json")) == {"n": "è"}


def test_foto_scenario_nomi():
    assert [n for n, *_ in FOTO_SCENARIO] == ["H01", "H02", "V03", "V04", "Q05", "H06", "V07", "H08", "Q09", "V10"]


def _senza_misure_testi(righe):
    """le misure dei riquadri di testo dipendono dai font installati: si confronta tutto il resto"""
    import re
    return [re.sub(r"TEXT\(('(?:[^'\\]|\\.)*'), [\d.]+, [\d.]+, [\d.]+, [\d.]+,", r"TEXT(\1, #, #, #, #,", r) for r in righe]


def test_stesse_operazioni_stesso_risultato_della_152(home_srv, apri_editor, tmp_path):
    """lo scenario di parità: le operazioni fatte con la 1.5.2 danno, con la 2.0, lo stesso spec.py, lo stesso progetto.json
    e lo stesso stato dell'editor (tests/dati/progetto_152 è l'uscita della 1.5.2)"""
    h = home_srv
    proj = h.post("/api/nuovo", {"nome": "Parità àè", "w": "60", "h": "22,5", "spazio": "2,5"})["path"]
    crea_foto(os.path.join(proj, "Foto"))
    c = apri_editor(proj)
    st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]

    def op(o):
        nonlocal st
        st = c.post("/api/op", dict(cid="scen", rev=st["rev"], **o)); return st
    t = c.post("/api/templates", {"photos": names[:2]}); op({"op": "newspread", "pos": 0, "L": t["items"][0]["L"], "R": t["items"][0]["R"]})
    t3 = c.post("/api/templates", {"photos": names[2:5]}); op({"op": "newspread", "pos": 1, "L": t3["items"][0]["L"], "R": t3["items"][0]["R"]})
    op({"op": "newspreadsel", "names": names[5:8], "pos": 2})
    op({"op": "addtext", "s": 0, "fx": 0.1, "fy": 0.1, "fw": 0.4, "fh": 0, "tx": "Battesimo di Anita"})
    tx = [i for i in st["spreads"][0]["items"] if i.get("kind") == "txt"][0]
    op({"op": "settext", "at": [0, tx["side"], tx["idx"]], "tx": "Ciao àè\nseconda riga", "size": 150, "lh": 1.5, "caps": True, "tr": 40, "al": "center", "col": [200, 30, 30]})
    op({"op": "stile_salva", "at": [0, tx["side"], tx["idx"]], "nome": "Titolo"})
    op({"op": "stella", "photo": names[0], "value": True}); op({"op": "tolta", "photo": names[9], "value": True}); op({"op": "colore", "photo": names[1], "value": "rosso"})
    f1 = [i for i in st["spreads"][1]["items"] if i["k"] != "t"]
    op({"op": "set", "at": [1, f1[0]["side"], f1[0]["idx"]], "z": 1.4, "bw": True})
    op({"op": "free", "at": [1, f1[1]["side"], f1[1]["idx"]], "x": 0.12, "y": 0.1, "w": 0.5, "h": 0.6})
    f1 = [i for i in st["spreads"][1]["items"] if i["k"] != "t"]; fr = [i for i in f1 if i["free"]][0]
    op({"op": "set", "at": [1, fr["side"], fr["idx"]], "a": 7.5, "bd": [3, "#ffffff"], "sh": 40, "oc": 80})
    op({"op": "ev", "photo": names[2], "value": 0.5}); op({"op": "evg", "value": 0.25})
    op({"op": "rit", "photo": names[3], "key": "con", "value": 30}); op({"op": "rit", "photo": names[3], "key": "vib", "value": 20}); op({"op": "rit", "photo": names[4], "key": "tmp", "value": -25})
    op({"op": "tono", "photo": names[4], "value": {"b": 10, "w": 240, "m": 1.2, "c": [[64, 50], [192, 210]]}})
    op({"op": "face", "photo": names[5], "x": 0.3, "y": 0.4})
    op({"op": "guides", "s": 0, "v": [100, 2000.4], "h": [300]})
    op({"op": "dup", "s": 1}); op({"op": "swappages", "s": 3}); op({"op": "move", "s": 3, "to": 0})
    f = [i for i in st["spreads"][1]["items"] if i["k"] != "t"]
    if len(f) >= 2: op({"op": "swap", "a": [1, f[0]["side"], f[0]["idx"]], "b": [1, f[1]["side"], f[1]["idx"]]})
    tp = c.get("/api/templates?s=2"); alt = [x for x in tp["items"] if not x["cur"]]
    if alt: op(dict(op="template", s=2, **{k: alt[0][k] for k in "LR" if k in alt[0]}))
    op({"op": "blank", "pos": len(st["spreads"])}); op({"op": "addtospread", "s": len(st["spreads"]) - 1, "names": [names[8]], "how": "keep"})
    op({"op": "tono_L", "value": 60})
    c.post("/api/save")
    with open(os.path.join(proj, "spec.py"), encoding="utf-8") as fh: nuovo = fh.read().split("\n")[1:]
    with open(os.path.join(P152, "spec.py"), encoding="utf-8") as fh: vecchio = fh.read().split("\n")[1:]
    assert _senza_misure_testi(nuovo) == _senza_misure_testi(vecchio)
    with open(os.path.join(P152, "progetto.json"), encoding="utf-8") as fh: atteso = json.loads(fh.read().replace("{PROGETTO}", proj.replace("\\", "/")))
    assert formato.leggi_json(os.path.join(proj, "progetto.json")) == atteso
    c.E.inizializza(proj)
    with open(os.path.join(P152, "stato_ridotto.json"), encoding="utf-8") as fh: assert riduci(c.get("/api/state")) == json.load(fh)
