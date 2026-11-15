"""Motore e script della skill (python -m impaginatore.motore.<script>): anteprime, analisi, PSD con un Photoshop finto."""
import json
import os
import re
import struct
import subprocess
import sys

import numpy as np
import pytest
from aiuti import come_script

from impaginatore import formato
from impaginatore.motore import album, genera_psd_angolo

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
    cambiati a mano dopo la generazione (genera_psd non li sovrascrive più); genera_psd salta quelli segnati"""
    import time

    from impaginatore.piattaforma import photoshop
    out = os.path.join(prj, "PSD"); os.makedirs(out); os.makedirs(os.path.join(prj, "_cache"), exist_ok=True)
    reg = os.path.join(prj, "_cache", "psd_generati.json"); t = time.time() - 600
    for n in ("Spread_01.psd", "Spread_02.psd"):
        with open(os.path.join(out, n), "wb") as f: f.write(b"8BPS")
        os.utime(os.path.join(out, n), (t, t))
    os.utime(os.path.join(out, "Spread_02.psd"), (t + 60, t + 60))                       # toccato a mano dopo la generazione
    come_script(monkeypatch, "modifica_psd", "--progetto", prj, "nessun-comando")
    with open(reg, encoding="utf-8") as f: assert json.load(f) == {}, "senza registro: uno vuoto (PSD non generati da qui)"
    with open(reg, "w", encoding="utf-8") as f: json.dump({"Spread_01.psd": t, "Spread_02.psd": t}, f)
    come_script(monkeypatch, "modifica_psd", "--progetto", prj, "nessun-comando")
    with open(reg, encoding="utf-8") as f: assert json.load(f) == {"Spread_01.psd": t, "Spread_02.psd": 0}
    ps = PhotoshopFinto()
    for n in ("trova", "esegui_js", "esegui_jsx"): monkeypatch.setattr(photoshop, n, getattr(ps, n))
    from impaginatore.motore import genera_psd
    assert genera_psd.main(["--progetto", prj, "--spread", "1,2"]) == 0
    assert '"n": 1' in ps.script[-1] and '"n": 2' not in ps.script[-1], "il PSD toccato a mano non si rigenera"


def test_genera_psd_con_photoshop_finto(prj, monkeypatch):
    """il codice che parla con Photoshop gira davvero (salvo Photoshop): angoli, testi, tono e profilo sRGB nello script"""
    from impaginatore.piattaforma import photoshop
    ps = PhotoshopFinto()
    for n in ("trova", "esegui_js", "esegui_jsx"): monkeypatch.setattr(photoshop, n, getattr(ps, n))
    assert genera_psd_angolo.main(["--progetto", prj, "--spread", "1,2,4"]) == 0
    js = "\n".join(ps.script)
    assert "rotAround(L,it.ang" in js and '"ang": 7.5' in js and "sRGB IEC61966-2.1" in js and "addTextX" in js
    assert sorted(f for f in os.listdir(os.path.join(prj, "PSD"))) == ["Spread_01.psd", "Spread_02.psd", "Spread_04.psd"]
    with open(os.path.join(prj, "_cache", "psd_generati.json"), encoding="utf-8") as f: assert set(json.load(f)) == {"Spread_01.psd", "Spread_02.psd", "Spread_04.psd"}
    # seconda volta: i PSD esistono e non sono stati toccati a mano -> rigenerati; uno modificato dopo -> saltato
    p4 = os.path.join(prj, "PSD", "Spread_04.psd"); os.utime(p4, (os.path.getmtime(p4) + 60, os.path.getmtime(p4) + 60))
    assert genera_psd_angolo.main(["--progetto", prj, "--spread", "1,4"]) == 0
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


def test_genera_psd_errore_di_uno_spread(prj, monkeypatch):
    """uno spread che Photoshop non riesce a fare (riga d'errore invece di «ok») non entra nel registro dei PSD generati"""
    from impaginatore.motore import genera_psd
    from impaginatore.piattaforma import photoshop
    ps = PhotoshopFinto(); esegui = ps.esegui_jsx
    monkeypatch.setattr(photoshop, "trova", ps.trova); monkeypatch.setattr(photoshop, "esegui_js", ps.esegui_js)
    monkeypatch.setattr(photoshop, "esegui_jsx", lambda path, timeout=3600: esegui(path, timeout).replace("Spread_02 ok", "Spread_02 ERRORE: cornice non trovata"))
    assert genera_psd.main(["--progetto", prj, "--spread", "1,2"]) == 0
    assert set(formato.leggi_json(os.path.join(prj, "_cache", "psd_generati.json"))) == {"Spread_01.psd"}


def _senza_volti(prj):
    """niente OpenCV: nessun volto in nessuna foto"""
    os.makedirs(os.path.join(prj, "_cache"), exist_ok=True)
    formato.scrivi_json(os.path.join(prj, "_cache", "faces.json"), {f: [] for f in os.listdir(os.path.join(prj, "Foto"))})


def test_cornice_ruotata_in_bianco_e_nero(prj):
    """una cornice libera ruotata e in bianco e nero si disegna in grigi; la stessa a colori resta a colori"""
    from impaginatore.motore import album_libere as L
    _senza_volti(prj); album.carica_progetto(prj)
    for bw in (True, False):
        sp = (album.W(L.ROT(L.FREE("H01", 0.1, 0.1, 0.5, 0.5, bw=bw), 10)), album.W())
        (it,) = album.layout(sp); K = 0.05
        r, g, b = album.render(sp, K).getpixel((round((it["x"] + it["W"] * 0.3) * K), round((it["y"] + it["H"] * 0.5) * K)))
        grigio = abs(r - g) <= 3 and abs(g - b) <= 3
        assert grigio == bw and max(r, g, b) < 250, (bw, (r, g, b))


def test_ritocco_saturazione_contrasto_e_livelli(prj):
    """saturazione -100 = grigi (pesi 601, la stessa matrice va nel Miscelatore canale del PSD); il contrasto da solo non
    sposta il bianco (nessun guadagno) ma passa dalla curva; temperatura da sola: guadagni e nessuna curva; livelli senza curva"""
    from PIL import Image

    from impaginatore.motore import album_libere as L
    cfg = formato.leggi_json(os.path.join(prj, "progetto.json")); cfg["ritocco"] = {"H01": {"sat": -100}, "H02": {"con": 60}}
    formato.scrivi_json(os.path.join(prj, "progetto.json"), cfg)
    _senza_volti(prj); album.carica_progetto(prj)
    h01, h02 = album.IDX["H01"] - 1, album.IDX["H02"] - 1
    assert [[round(v, 6) for v in r] for r in L.sat_matrice(-100)] == [[29.9, 58.7, 11.4]] * 3 and L.sat_matrice(0) == [[100, 0, 0], [0, 100, 0], [0, 0, 100]]
    assert L.rit_job(h01) == dict(c=None, vib=0, sat=-100, satm=L.sat_matrice(-100))
    assert L._apply_rit(Image.new("RGB", (2, 2), (200, 50, 50)), h01).getpixel((0, 0)) == (95, 95, 95)
    scala = Image.new("RGB", (2, 1)); scala.putpixel((0, 0), (64, 64, 64)); scala.putpixel((1, 0), (192, 192, 192))
    L._CUR[0] = h02
    try: out = album.apply_ev(scala, 0.0)
    finally: L._CUR[0] = None
    assert out.getpixel((0, 0))[0] < 64 and out.getpixel((1, 0))[0] > 192, "più contrasto: scuri più scuri, chiari più chiari"
    assert L.rit_curva({"tmp": 20}) is None and L.rit_gains({"tmp": 20})[2] < 1
    lut = L.tono_lut({"b": 20, "w": 235})
    assert (lut[20], lut[128], lut[235]) == (0, 128, 255)


def _modulo_da_file(nome, percorso):
    import importlib.util
    spec = importlib.util.spec_from_file_location(nome, percorso); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_copie_del_motore_accanto_a_spec(tmp_path, monkeypatch):
    """album_libere.py e testo.py, copiati accanto a spec.py per gli script delle 1.x, funzionano fuori dal pacchetto con
    l'album.py di quegli script: album_libere lo estende una volta sola (importato due volte non lo estende di nuovo), le
    cornici libere si posizionano, i testi si disegnano con testo.py accanto; testo.py da solo cerca i font del Mac"""
    mot = os.path.dirname(album.__file__)
    skill = _modulo_da_file("impaginatore.motore._album_della_skill", os.path.join(mot, "album.py"))   # un album tutto suo, non quello del programma
    monkeypatch.setitem(sys.modules, "album", skill)
    tst = _modulo_da_file("testo", os.path.join(mot, "testo.py")); monkeypatch.setitem(sys.modules, "testo", tst)
    assert tst._pfont is None and tst._cartelle is None
    assert tst._dirs() == ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
    assert tst._cache() == os.path.expanduser("~/.album-tools/font_cache.json")
    tst.DIRS, tst.CACHE = [str(tmp_path)], str(tmp_path / "font_cache.json")
    assert tst.font_file("Qualunque-Bold") == ("/System/Library/Fonts/Helvetica.ttc", 0), "nessun font trovato: Helvetica del Mac"
    lib = _modulo_da_file("album_libere", os.path.join(mot, "album_libere.py")); posto = skill._place
    assert lib._a is skill and posto._libere and album._place is not posto
    _modulo_da_file("album_libere", os.path.join(mot, "album_libere.py"))
    assert skill._place is posto, "già esteso: non si avvolge due volte"
    skill.CW, skill.CH, skill.B, skill.G, skill.MG = 1190, 800, 0, 10, 50; skill.FOLD = skill.CW / 2; skill.TW, skill.TH = skill.CW, skill.CH
    (it,) = skill.layout([("W", [lib.FREE(1, 0.2, 0.1, 0.4, 0.5)]), ("W", [])])
    assert {k: it[k] for k in ("k", "side", "x", "y", "W", "H", "libera")} == dict(k="p", side="L", x=149, y=120, W=198, H=350, libera=True)
    im = skill._text(dict(kind="txt", tx="Ciao", font="Qualunque-Bold", size=60, col=[200, 30, 30], W=400, H=100), 1.0)
    a = np.asarray(im)
    assert im.size == (400, 100) and ((a[..., :3] == (200, 30, 30)).all(axis=-1) & (a[..., 3] > 0)).any(), "il testo è disegnato nel suo colore"


# album.py da solo (come lo usano gli script delle 1.x, senza album_libere che ne sostituisce layout e zcrop): griglia 12 x 8,
# pagina immersiva (tutta la mezza pagina meno metà spazio alla piega) e bianca (dentro il margine), ritaglio centrato
ALBUM_DA_SOLO = """from impaginatore.motore import album as a
print(a.PROJ, a.CFG, a.M)
a.CW, a.CH, a.B, a.G, a.MG = 1190, 800, 0, 10, 50; a.FOLD = a.CW / 2; a.TW, a.TH = a.CW, a.CH
a.M, a.F, a.FACE_FIX = [{"n": "x.jpg", "ar": 1.5}], {}, {}
L = a.layout([("I", [a.P(1, 0, 0, 6, 8)]), ("W", [a.P(1, 0, 0, 12, 8)])])
print([(it["side"], it["x"], it["y"], it["W"], it["H"]) for it in L])
print([round(v, 4) for v in a.zcrop(L[0])])
"""


def test_album_senza_progetto_non_legge_niente(tmp_path, monkeypatch):
    r = subprocess.run([sys.executable, "-c", ALBUM_DA_SOLO], capture_output=True, text=True, encoding="utf-8")
    assert r.stdout.splitlines() == ["None None []", "[('L', 0, 0, 290, 800), ('R', 645, 50, 495, 700)]", "[0.3792, 0, 0.6208, 1]"], r.stderr[-2000:]
    assert album.progetto_da_argv(["x", "--progetto", "rel"]) == os.path.abspath("rel")
    monkeypatch.delenv("ALBUM_PROGETTO", raising=False); monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="Progetto non trovato"): album.progetto_da_argv(["x"])
    (tmp_path / "progetto.json").write_text("{}", encoding="utf-8")
    assert album.progetto_da_argv(["x"]) == str(tmp_path), "nella cartella del progetto basta lanciare lo script"


# ---------------------------------------------------------------- testo.py: nomi dei font letti dai file, cache, ripieghi
def _faccia(nomi, base):
    """un font minimo (solo la tabella «name») che comincia a `base` byte dall'inizio del file; nomi = [(piattaforma, id, byte)];
    None = un font senza tabella «name»"""
    if nomi is None: return struct.pack(">IHHHH", 0x00010000, 1, 0, 0, 0) + struct.pack(">4sIII", b"glyf", 0, 0, 0)
    rec, dati = b"", b""
    for pid, nid, raw in nomi:
        rec += struct.pack(">HHHHHH", pid, 1 if pid == 3 else 0, 0x409 if pid == 3 else 0, nid, len(raw), len(dati)); dati += raw
    name = struct.pack(">HHH", 0, len(nomi), 6 + len(rec)) + rec + dati
    return struct.pack(">IHHHH", 0x00010000, 1, 0, 0, 0) + struct.pack(">4sIII", b"name", 0, base + 28, len(name)) + name


def _u(t): return t.encode("utf-16-be")


def _font(p, *facce):
    """file .ttf (una faccia) o .ttc (più facce)"""
    if len(facce) == 1: data = _faccia(facce[0], 0)
    else:
        data = b""; offs = []; base = 12 + 4 * len(facce)
        for f in facce: offs.append(base + len(data)); data += _faccia(f, base + len(data))
        data = b"ttcf" + struct.pack(">II", 0x00010000, len(facce)) + struct.pack(">" + "I" * len(facce), *offs) + data
    p.write_bytes(data)
    return str(p)


PROVA = [(1, 1, b"Vecchio"), (3, 1, _u("Prova")), (3, 2, _u("Grassetto")), (3, 4, _u("Prova Grassetto")), (3, 6, _u("Prova-Grassetto")), (3, 17, b"\x00")]


def test_nomi_dei_font(tmp_path):
    """famiglia, stile e nome PostScript dalla tabella «name» (Windows prima del Mac; nomi tipografici 16/17 se ci sono;
    un nome non decodificabile si salta); raccolte .ttc; facce senza nomi, file rovinati o mancanti: niente"""
    from impaginatore.motore import testo
    assert testo._names(_font(tmp_path / "a.ttf", PROVA)) == [(0, "Prova", "Grassetto", "Prova-Grassetto")]
    ttc = _font(tmp_path / "b.ttc", None, [(3, 16, _u("Tipo")), (3, 1, _u("Tipo Mezzo")), (3, 6, _u("Tipo-Regular"))], [(3, 1, _u("SenzaPS"))])
    assert testo._names(ttc) == [(1, "Tipo", "Regular", "Tipo-Regular")]
    (tmp_path / "rotto.ttf").write_bytes(b"\x00\x01\x00\x00\x00\x09")
    assert testo._names(str(tmp_path / "rotto.ttf")) == [] and testo._names(str(tmp_path / "manca.ttf")) == []


def test_elenco_dei_font_e_cache(tmp_path, monkeypatch):
    """l'elenco dei font si fa una volta e si tiene su disco finché non cambia il numero dei file; doppioni e famiglie
    nascoste (con il punto) fuori; una cache che non si scrive non ferma niente"""
    from impaginatore.motore import testo
    d = tmp_path / "font"; d.mkdir(); (d / "leggimi.txt").write_text("x")
    _font(d / "a.ttf", PROVA); _font(d / "b.otf", PROVA); _font(d / "c.ttf", [(3, 1, _u(".Nascosto")), (3, 6, _u(".Nascosto-Regular"))])
    monkeypatch.setattr(testo, "DIRS", [str(d)]); monkeypatch.setattr(testo, "CACHE", str(tmp_path / "cache" / "font.json")); monkeypatch.setattr(testo, "_FONTS", None)
    attesi = [dict(fam="Prova", sty="Grassetto", ps="Prova-Grassetto", file=str(d / "a.ttf"), idx=0)]
    assert testo.fonts() == attesi and formato.leggi_json(testo.CACHE) == dict(n=3, fonts=attesi)
    formato.scrivi_json(testo.CACHE, dict(n=3, fonts=[dict(fam="DallaCache", sty="R", ps="DallaCache-R", file="x", idx=0)])); testo._FONTS = None
    assert testo.fonts()[0]["fam"] == "DallaCache", "stesso numero di file: si usa la cache"
    _font(d / "d.ttf", [(3, 1, _u("Nuovo")), (3, 6, _u("Nuovo-Regular"))]); testo._FONTS = None
    assert [f["ps"] for f in testo.fonts()] == ["Nuovo-Regular", "Prova-Grassetto"], "un file in più: elenco rifatto"
    (tmp_path / "file").write_text("x"); monkeypatch.setattr(testo, "CACHE", str(tmp_path / "file" / "font.json")); testo._FONTS = None
    assert len(testo.fonts()) == 2 and not os.path.exists(testo.CACHE)
    assert testo.font_file("Prova-Grassetto") == (str(d / "a.ttf"), 0) and testo.font_file("Prova-Corsivo") == (str(d / "a.ttf"), 0), "stesso nome: un altro stile"


def test_font_di_ripiego_e_interlinea(monkeypatch):
    """font che non c'è: quello di ripiego del sistema, se manca anche quello Helvetica (solo Mac), se non si apre quello di
    Pillow; interlinea tra 0,6 e 3, 1,2 se non è un numero"""
    from PIL import ImageFont

    from impaginatore.motore import testo
    monkeypatch.setattr(testo, "fonts", lambda: []); monkeypatch.setattr(testo, "_CACHE_F", {})
    assert testo.font_file("Manca-Regular") == testo._pfont.font_ripiego()
    monkeypatch.setattr(testo._pfont, "font_ripiego", lambda: (None, 0))
    assert testo.font_file("Manca-Regular") == ("/System/Library/Fonts/Helvetica.ttc", 0)
    monkeypatch.setattr(testo, "font_file", lambda ps: ("/non/esiste.ttf", 0))
    assert testo._font("Manca-Regular", 40).getlength("abc") == ImageFont.load_default().getlength("abc")
    assert [testo.lead({"lh": v}) for v in ("x", 10, 0.1, 1.5)] == [1.2, 3.0, 0.6, 1.5] and testo.lead({}) == 1.2


def test_testo_a_capo_centrato_e_righe_vuote():
    """a capo automatico nella larghezza del riquadro, riga vuota tra due paragrafi (nel PSD non sposta il primo inchiostro),
    testo centrato senza spaziatura"""
    from impaginatore.motore import testo
    it = dict(tx="uno due tre quattro cinque\n\nfine", font="DejaVuSans", size=40, col=[0, 0, 0], al="center", tr=0, W=200, H=400)
    righe = testo.wrap(it, 200)
    assert len(righe) >= 4 and righe[-2:] == ["", "fine"] and " ".join(righe[:-2]) == "uno due tre quattro cinque"
    a = np.asarray(testo.render(it, 1.0))[..., 3]
    xs = np.nonzero(a.any(axis=0))[0]
    assert abs((xs.min() + xs.max()) / 2 - 100) < 12, "centrato nel riquadro"
    j = testo.job_x(it)
    assert 0 <= j["gy"] < 40 and 0 < j["gx"] < 100 and j["lh"] == 1.2

