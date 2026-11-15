"""Motore e script della skill (python -m impaginatore.motore.<script>): anteprime, analisi, PSD con un Photoshop finto."""
import json
import os
import re
import runpy
import shutil
import subprocess
import sys

import pytest
from aiuti import crea_foto

from impaginatore import formato
from impaginatore.motore import album, genera_psd_angolo

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P152 = os.path.join(RADICE, "tests", "dati", "progetto_152")


@pytest.fixture
def prj(tmp_path):
    """il progetto dello scenario 1.5.2 (cornici libere, angoli, testi), pronto per gli script"""
    p = tmp_path / "Album àè"; crea_foto(str(p / "Foto"))
    shutil.copy(os.path.join(P152, "spec.py"), p / "spec.py")
    with open(os.path.join(P152, "progetto.json"), encoding="utf-8") as f: cfg = json.loads(f.read().replace("{PROGETTO}", str(p).replace("\\", "/")))
    formato.scrivi_json(str(p / "progetto.json"), cfg, indent=2, ensure_ascii=False)
    return str(p)


def _script(nome, *args, cwd=None, env=None):
    return subprocess.run([sys.executable, "-m", f"impaginatore.motore.{nome}", *args], capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env)


def test_parti_di_genera_psd_angolo():
    """genera_psd_angolo cambia solo le parti con nome dello script di genera_psd (TEST-004: niente codice modificato come testo, niente exec)"""
    from impaginatore.motore import genera_psd
    assert set(genera_psd_angolo.PARTI) == set(genera_psd.PARTI)
    for parti in (None, genera_psd_angolo.PARTI): assert "@@" not in genera_psd.script_js(parti)
    js = genera_psd.script_js(genera_psd_angolo.PARTI)
    assert "rotAround(L,it.ang" in js and "BitsPerChannelType.EIGHT" in js and js.count('var log=[]; var STEP="start";') == 1
    assert "(it.txt==\"txt\"?addTextX:addText)(doc,it,ids[it.side])" in js and "addTextX" not in genera_psd.script_js()


def test_anteprima_e_analizza(prj):
    r = _script("anteprima", "--progetto", prj, "--nome", "v1", "--spread", "1,2", "--prima-dopo", "2", "--tolte", "V07")
    assert r.returncode == 0, r.stderr[-2000:]
    assert "spread 5" in r.stdout
    out = sorted(os.listdir(os.path.join(prj, "Anteprime")))
    assert "Sequenza v1.txt" in out and any(f.startswith("Anteprima v1") for f in out) and any(f.startswith("Prima-dopo") for f in out)
    with open(os.path.join(prj, "Anteprime", "Sequenza v1.txt"), encoding="utf-8") as f: assert "H08" in f.read()
    r = _script("analizza", cwd=prj, env=dict(os.environ, ALBUM_PROGETTO=prj)); assert r.returncode == 0, r.stderr[-2000:]
    r = _script("analizza", "--progetto", prj); assert r.returncode == 0, r.stderr[-2000:]


def test_progetto_mancante(tmp_path):
    r = _script("anteprima", cwd=str(tmp_path), env={k: v for k, v in os.environ.items() if k != "ALBUM_PROGETTO"})
    assert r.returncode == 1 and "Progetto non trovato" in r.stderr


def test_script_psd_senza_photoshop(prj, monkeypatch):
    from impaginatore.piattaforma import photoshop
    if photoshop.disponibile(): pytest.skip("qui Photoshop c'è")
    for s in ("genera_psd_angolo", "genera_psd", "esporta_pdf"):
        r = _script(s, "--progetto", prj, "--spread", "1") if s != "esporta_pdf" else _script(s, "--progetto", prj)
        assert r.returncode == 1 and photoshop.motivo_assente() in r.stderr + r.stdout, (s, r.stderr[-500:])
    r = _script("verifica_psd", "--progetto", prj); assert r.returncode == 0 and "foto nei PSD 0" in r.stdout


def test_modifica_psd_registro(prj):
    """modifica_psd segna come «toccati a mano» i PSD salvati dopo la generazione: il registro si riscrive in modo atomico
    (BUG-005) e uno rovinato vale come vuoto, mai un errore"""
    psd = os.path.join(prj, "PSD"); os.makedirs(psd); os.makedirs(os.path.join(prj, "_cache"), exist_ok=True)
    for n in (1, 2): open(os.path.join(psd, f"Spread_0{n}.psd"), "wb").close()
    reg = os.path.join(prj, "_cache", "psd_generati.json")
    formato.scrivi_json(reg, {"Spread_01.psd": 1000.0, "Spread_02.psd": os.path.getmtime(os.path.join(psd, "Spread_02.psd"))})
    r = _script("modifica_psd", "--progetto", prj, "nessuno"); assert r.returncode == 0, r.stderr[-2000:]
    assert formato.leggi_json(reg)["Spread_01.psd"] == 0 and formato.leggi_json(reg)["Spread_02.psd"] > 0
    assert not [x for x in os.listdir(os.path.join(prj, "_cache")) if x.endswith(".tmp")], "nessun file temporaneo lasciato"
    with open(reg, "w", encoding="utf-8") as f: f.write('{"Spread_01.psd": 10')
    r = _script("modifica_psd", "--progetto", prj, "nessuno"); assert r.returncode == 0, r.stderr[-2000:]
    assert formato.leggi_json(reg) == {} and "non leggibile" in r.stdout


def test_abbina(tmp_path):
    web, orig, dest = tmp_path / "web", tmp_path / "orig", tmp_path / "dest"
    crea_foto(str(web), [("A1", 300, 200, None), ("A2", 300, 200, None)]); crea_foto(str(orig / "cap1"), [("A1", 900, 600, None)])
    r = _script("abbina", "--web", str(web), "--originali", str(orig / "cap1"), "--dest", str(dest), "--lato-minimo", "800")
    assert r.returncode in (0, 1), r.stderr[-2000:]
    assert (dest / "A1.jpg").exists() and "A2" in r.stdout
    with open(dest / "origine.json", encoding="utf-8") as f: assert json.load(f) == {"A1.jpg": str(orig / "cap1")}


class PhotoshopFinto:
    """esegue «a parole» gli script: per ogni spread richiesto crea un PSD finto e risponde «Spread_NN ok»"""

    def __init__(self): self.script = []; self.aperti = ""

    def trova(self): return dict(nome="Adobe Photoshop 2026", percorso="/Applications/x.app")

    def esegui_js(self, codice): return self.aperti               # documenti aperti: «nome|salvato» per riga

    def esegui_jsx(self, path, timeout=3600):
        with open(path, encoding="ascii") as f: js = f.read()
        self.script.append(js)
        jobs = json.loads(re.search(r"var JOBS=(\[.*?\]); var G=", js).group(1))
        out = re.search(r'var OUT=("[^"]*");', js).group(1)
        risposta = []
        for j in jobs:
            nm = "Spread_%02d" % j["n"]
            with open(os.path.join(json.loads(out), nm + ".psd"), "wb") as f: f.write(b"8BPS" + b"\0" * 200000)
            risposta.append(nm + " ok")
        return "\n".join(risposta)


def test_registro_dei_psd_letto_e_scritto(prj, monkeypatch):
    """BUG-007: il registro dei PSD generati (psd_generati.json) si legge e si scrive con file chiusi. modifica_psd segna i PSD
    cambiati a mano dopo la generazione (genera_psd non li sovrascrive più); genera_psd salta quelli segnati.
    Sta prima di test_genera_psd_con_photoshop_finto: quella esegue genera_psd.py con exec e senza __spec__, e da lì in poi
    coverage non segue più quel file in questo processo (la prova passa comunque, cambia solo la misura)"""
    import time

    from impaginatore.piattaforma import photoshop
    out = os.path.join(prj, "PSD"); os.makedirs(out); os.makedirs(os.path.join(prj, "_cache"), exist_ok=True)
    reg = os.path.join(prj, "_cache", "psd_generati.json"); t = time.time() - 600
    for n in ("Spread_01.psd", "Spread_02.psd"):
        with open(os.path.join(out, n), "wb") as f: f.write(b"8BPS")
        os.utime(os.path.join(out, n), (t, t))
    os.utime(os.path.join(out, "Spread_02.psd"), (t + 60, t + 60))                       # toccato a mano dopo la generazione
    monkeypatch.setattr(sys, "argv", ["modifica_psd", "--progetto", prj, "nessun-comando"])
    runpy.run_module("impaginatore.motore.modifica_psd", run_name="__main__")
    with open(reg, encoding="utf-8") as f: assert json.load(f) == {}, "senza registro: uno vuoto (PSD non generati da qui)"
    with open(reg, "w", encoding="utf-8") as f: json.dump({"Spread_01.psd": t, "Spread_02.psd": t}, f)
    runpy.run_module("impaginatore.motore.modifica_psd", run_name="__main__")
    with open(reg, encoding="utf-8") as f: assert json.load(f) == {"Spread_01.psd": t, "Spread_02.psd": 0}
    ps = PhotoshopFinto()
    for n in ("trova", "esegui_js", "esegui_jsx"): monkeypatch.setattr(photoshop, n, getattr(ps, n))
    album.carica_progetto(prj)
    monkeypatch.setattr(sys, "argv", ["genera_psd", "--progetto", prj, "--spread", "1,2"])
    runpy.run_module("impaginatore.motore.genera_psd", run_name="__main__")
    assert '"n": 1' in ps.script[-1] and '"n": 2' not in ps.script[-1], "il PSD toccato a mano non si rigenera"


def test_genera_psd_con_photoshop_finto(prj, monkeypatch):
    """il codice che parla con Photoshop gira davvero (salvo Photoshop): angoli, testi, tono e profilo sRGB nello script"""
    from impaginatore.piattaforma import photoshop
    ps = PhotoshopFinto()
    for n in ("trova", "esegui_js", "esegui_jsx"): monkeypatch.setattr(photoshop, n, getattr(ps, n))
    monkeypatch.setattr(sys, "argv", ["genera_psd_angolo", "--progetto", prj, "--spread", "1,2,4"])
    monkeypatch.delitem(sys.modules, "impaginatore.motore.genera_psd_angolo", raising=False)
    runpy.run_module("impaginatore.motore.genera_psd_angolo", run_name="__main__")
    js = "\n".join(ps.script)
    assert "rotAround(L,it.ang" in js and '"ang": 7.5' in js and "sRGB IEC61966-2.1" in js and "addTextX" in js
    assert sorted(f for f in os.listdir(os.path.join(prj, "PSD"))) == ["Spread_01.psd", "Spread_02.psd", "Spread_04.psd"]
    with open(os.path.join(prj, "_cache", "psd_generati.json"), encoding="utf-8") as f: assert set(json.load(f)) == {"Spread_01.psd", "Spread_02.psd", "Spread_04.psd"}
    # seconda volta: i PSD esistono e non sono stati toccati a mano -> rigenerati; uno modificato dopo -> saltato
    p4 = os.path.join(prj, "PSD", "Spread_04.psd"); os.utime(p4, (os.path.getmtime(p4) + 60, os.path.getmtime(p4) + 60))
    album.carica_progetto(prj)
    monkeypatch.setattr(sys, "argv", ["genera_psd_angolo", "--progetto", prj, "--spread", "1,4"])
    runpy.run_module("impaginatore.motore.genera_psd_angolo", run_name="__main__")
    assert '"n": 4' not in ps.script[-1]


def test_genera_psd_base_e_registro_rovinato(prj, monkeypatch, capsys):
    """genera_psd senza le parti estese; un psd_generati.json rovinato vale come vuoto: i PSD esistenti non si sovrascrivono"""
    from impaginatore.motore import genera_psd
    from impaginatore.piattaforma import photoshop
    ps = PhotoshopFinto()
    for n in ("trova", "esegui_js", "esegui_jsx"): monkeypatch.setattr(photoshop, n, getattr(ps, n))
    assert genera_psd.main(["--progetto", prj, "--spread", "1,2"]) == 0
    assert "rotAround" not in ps.script[-1] and '"ang"' not in ps.script[-1] and '"wb": null' in ps.script[-1]
    reg = os.path.join(prj, "_cache", "psd_generati.json")
    capsys.readouterr(); uscite = []
    for rotto in ("{rotto", "[1, 2]"):
        with open(reg, "w", encoding="utf-8") as f: f.write(rotto)
        n = len(ps.script)
        assert genera_psd.main(["--progetto", prj, "--spread", "1"]) == 0 and len(ps.script) == n
        uscite.append(capsys.readouterr().out)
    assert all("SALTATO spread 1: esiste e non l'ho generato io" in u for u in uscite) and "psd_generati.json non leggibile" in uscite[0]
    ps.aperti = "Spread_02.psd|false\nAltro.psd|true"; n = len(ps.script)
    assert genera_psd.main(["--progetto", prj, "--spread", "2", "--forza"]) == 0 and len(ps.script) == n, "un PSD aperto in Photoshop non si tocca, neanche con --forza"
    assert "SALTATO spread 2: è aperto in Photoshop" in capsys.readouterr().out


def test_album_senza_progetto_non_legge_niente():
    r = subprocess.run([sys.executable, "-c", "from impaginatore.motore import album as a; print(a.PROJ, a.CFG, a.M)"], capture_output=True, text=True, encoding="utf-8")
    assert r.stdout.strip() == "None None []"
    assert album.progetto_da_argv(["x", "--progetto", "rel"]) == os.path.abspath("rel")

