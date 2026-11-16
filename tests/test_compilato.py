"""Il programma compilato (T-302): come si riconosce, come lancia se stesso al posto di «python -m», i sottocomandi interni,
PyGObject del sistema su Linux, e i punti del programma che da compilato fanno una cosa diversa (riavvii, finestre di Tk,
copie del motore per la 1.x, sostituzione delle funzioni del motore). La prova sul programma compilato vero è
strumenti/verifica_pacchetto.py (docs/architettura/DISTRIBUZIONE.md)."""
import functools
import os
import subprocess
import sys
import types

import pytest

from impaginatore import cli, compilato, formato_1x, risorse
from impaginatore.piattaforma import dialoghi, processi


@pytest.fixture
def compilato_finto(monkeypatch):
    """come nel programma compilato: sys.frozen (lo mette compilato.prepara) e sys.executable è il programma"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/Applicazioni/Impaginatore/impaginatore")
    return sys.executable


def test_si_riconosce(monkeypatch):
    assert compilato.attivo() is False, "da Python"
    monkeypatch.setattr(sys, "frozen", True, raising=False); assert compilato.attivo() is True
    monkeypatch.delattr(sys, "frozen")
    monkeypatch.setitem(compilato.__dict__, "__compiled__", object()); assert compilato.attivo() is True, "Nuitka mette __compiled__ in ogni modulo"


def test_comando_da_python_e_da_compilato(monkeypatch):
    assert compilato.comando("impaginatore.editor", "--progetto", "/a b") == [sys.executable, "-m", "impaginatore.editor", "--progetto", "/a b"]
    exe = "/Applicazioni/Impaginatore/impaginatore"
    monkeypatch.setattr(sys, "frozen", True, raising=False); monkeypatch.setattr(sys, "executable", exe)
    assert compilato.comando("impaginatore", "--porta", "5") == [exe, "--porta", "5"]
    assert compilato.comando("impaginatore.editor", "--progetto", "/a b") == [exe, "editor", "--progetto", "/a b"]
    assert compilato.comando("impaginatore.mcp") == [exe, "mcp"]
    assert compilato.comando("impaginatore.motore.genera_psd_angolo", "--spread", "1") == [exe, "_psd", "--spread", "1"]
    with pytest.raises(KeyError): compilato.comando("impaginatore.altro")


def test_sottocomandi_interni(monkeypatch):
    from impaginatore.motore import genera_psd_angolo
    visti = []
    monkeypatch.setattr(genera_psd_angolo, "main", lambda argv: visti.append(("psd", argv)) or 0)
    monkeypatch.setattr(dialoghi, "scegli_con_tk", lambda argv: visti.append(("tk", argv)) or 0)
    monkeypatch.setattr(processi, "rilancio", lambda argv: visti.append(("rilancio", argv)) or 0)
    for n in compilato.INTERNI: assert compilato.interno(n, ["x"]) == 0
    assert visti == [("psd", ["x"]), ("tk", ["x"]), ("rilancio", ["x"])]
    with pytest.raises(ValueError, match="sconosciuto"): compilato.interno("_altro", [])


def test_cli_prepara_e_sottocomandi(monkeypatch):
    from impaginatore.aggiornamenti import lanciatore
    visti = []
    monkeypatch.setattr(compilato, "prepara", lambda: visti.append("prepara"))
    monkeypatch.setattr(lanciatore, "avvia", lambda argv: visti.append(("lanciatore", list(argv))))
    monkeypatch.setattr(compilato, "interno", lambda n, argv: visti.append((n, argv)) or 7)
    assert cli.main(["_psd", "--spread", "2"]) == 7 and visti == [("lanciatore", ["_psd", "--spread", "2"]), ("_psd", ["--spread", "2"])], "da Python: niente prepara"
    visti.clear(); monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert cli.main(["_rilancia", "1", "x"]) == 7 and visti == ["prepara", ("lanciatore", ["_rilancia", "1", "x"]), ("_rilancia", ["1", "x"])], "prepara prima del lanciatore"


def _gi_finto(cartella, tag=None):
    d = cartella / "gi"; d.mkdir(parents=True)
    (d / "__init__.py").write_text("NOME = 'gi finto'\n", encoding="utf-8")
    (d / f"_gi.{tag or sys.implementation.cache_tag}-x86_64-linux-gnu.so").write_bytes(b"")
    (cartella / "cairo").mkdir(); (cartella / "cairo" / "__init__.py").write_text("", encoding="utf-8")
    (cartella / "numpy").mkdir(); (cartella / "numpy" / "__init__.py").write_text("", encoding="utf-8")
    return str(cartella)


def test_pygobject_del_sistema(tmp_path):
    v = f"{sys.version_info.major}.{sys.version_info.minor}"
    _gi_finto(tmp_path / f"lib{v}" / "site-packages")
    _gi_finto(tmp_path / "altro", tag="cpython-39")
    sbagliata = tmp_path / "rotta" / "gi"; sbagliata.mkdir(parents=True)                      # gi senza __init__.py
    cartelle = (str(tmp_path / "manca"), str(sbagliata.parent), str(tmp_path / "altro"), str(tmp_path / "lib{v}" / "site-packages"))
    assert compilato.cartella_gi(cartelle) == str(tmp_path / f"lib{v}" / "site-packages")
    assert compilato.cartella_gi(cartelle[:3]) is None, "solo un PyGObject per un altro Python: niente finestra, si apre il browser"
    f = compilato.SoloGi(compilato.cartella_gi(cartelle))
    assert f.find_spec("gi").origin == str(tmp_path / f"lib{v}" / "site-packages" / "gi" / "__init__.py")
    assert f.find_spec("cairo") is not None
    assert f.find_spec("numpy") is None and f.find_spec("gi._gi") is None, "dalla cartella del sistema solo gi e cairo"


def test_prepara(tmp_path, monkeypatch):
    from impaginatore import piattaforma
    _gi_finto(tmp_path / "sys")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "meta_path", list(sys.meta_path))
    monkeypatch.setattr(sys, "stdout", None); monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(piattaforma.sys, "platform", "linux")
    try:
        compilato.prepara((str(tmp_path / "sys"),))
        assert sys.frozen is True and sys.stdout is not None and sys.stderr is not None
        print("non si perde e non si ferma: Windows senza console"); sys.stderr.write("idem\n")
        trovati = [f for f in sys.meta_path if isinstance(f, compilato.SoloGi)]
        assert len(trovati) == 1 and trovati[0].cartella == str(tmp_path / "sys") and sys.meta_path[-1] is trovati[0], "in fondo: prima i moduli compilati"
        compilato.prepara((str(tmp_path / "sys"),))
        assert len([f for f in sys.meta_path if isinstance(f, compilato.SoloGi)]) == 1, "una volta sola"
    finally:
        for f in (sys.stdout, sys.stderr):
            if f is not None: f.close()
    sys.meta_path[:] = [f for f in sys.meta_path if not isinstance(f, compilato.SoloGi)]
    monkeypatch.setattr(piattaforma.sys, "platform", "darwin")
    compilato.prepara((str(tmp_path / "sys"),))
    assert not any(isinstance(f, compilato.SoloGi) for f in sys.meta_path), "solo su Linux"
    monkeypatch.setattr(piattaforma.sys, "platform", "linux")
    compilato.prepara((str(tmp_path / "manca"),))
    assert not any(isinstance(f, compilato.SoloGi) for f in sys.meta_path), "nessun PyGObject adatto: niente"


# ---------------------------------------------------------------- riavvii
def test_riavvii_da_compilato(compilato_finto, monkeypatch):
    chiamate, lanci, attese = [], [], []
    monkeypatch.setattr(processi.os, "execv", lambda exe, argv: chiamate.append((exe, argv)))
    monkeypatch.setattr(sys, "argv", [compilato_finto, "editor", "--progetto", "/a b"])
    monkeypatch.setattr(sys, "orig_argv", ["python", "-X", "utf8", "-m", "impaginatore"])
    processi.riesegui()
    assert chiamate == [(compilato_finto, [compilato_finto, "editor", "--progetto", "/a b"])], "il programma stesso, non l'interprete"

    class Popen:
        def __init__(self, cmd, **k): lanci.append((cmd, k))
    monkeypatch.setattr(processi.subprocess, "Popen", Popen)
    processi.rilancia_dopo([compilato_finto, "--porta", "8765"], 1.5, gettone="g")
    cmd, k = lanci[-1]
    assert cmd == [compilato_finto, "_rilancia", "1.5", compilato_finto, "--porta", "8765"] and k["env"]["IMPAGINATORE_GETTONE"] == "g"
    monkeypatch.setattr(processi.time, "sleep", attese.append)
    assert processi.rilancio(["0.5", compilato_finto, "--porta", "8765"]) == 0
    assert attese == [0.5] and lanci[-1] == ([compilato_finto, "--porta", "8765"], {})


def test_rilancio_vero(tmp_path):
    """«impaginatore _rilancia» è lo stesso aiutante di «python -c RILANCIO»: aspetta e lancia il comando"""
    segno = tmp_path / "rilanciato.txt"
    figlio = [sys.executable, "-c", "import sys; open(sys.argv[1], 'w').write('ok')", str(segno)]
    r = subprocess.run([sys.executable, "-m", "impaginatore", "_rilancia", "0", *figlio], capture_output=True, text=True, timeout=120, cwd=processi.cartella_pacchetto())
    assert r.returncode == 0, r.stderr[-2000:]
    for _ in range(200):
        if segno.exists() and segno.read_text() == "ok": break
        subprocess.run([sys.executable, "-c", "import time; time.sleep(0.05)"])
    assert segno.read_text() == "ok"


# ---------------------------------------------------------------- finestre di Tk
def _tk_finto(cartella, scelta):
    """un modulo tkinter finto (in una cartella da mettere in testa a sys.path): registra le chiamate in tk_finto.log"""
    d = cartella / "tkinter"; d.mkdir(parents=True)
    (d / "__init__.py").write_text(
        "import os\nLOG = os.path.join(os.path.dirname(__file__), 'chiamate.log')\n"
        "class TclError(Exception): pass\n"
        "class Tk:\n"
        "    def withdraw(self): pass\n"
        "    def attributes(self, *a):\n"
        "        if os.environ.get('TK_SENZA_TOPMOST'): raise TclError('no')\n", encoding="utf-8")
    (d / "filedialog.py").write_text(
        "import json, os\nfrom . import LOG\n"
        f"SCELTA = {scelta!r}\n"
        "def _log(nome, k):\n"
        "    with open(LOG, 'a', encoding='utf-8') as f: f.write(json.dumps([nome, k]) + '\\n')\n"
        "def askdirectory(**k): _log('cartella', k); return SCELTA[0]\n"
        "def askopenfilename(**k): _log('file', k); return SCELTA[0]\n"
        "def askopenfilenames(**k): _log('file', k); return tuple(SCELTA)\n", encoding="utf-8")
    return str(cartella)


def test_scegli_con_tk(tmp_path, monkeypatch, capsys):
    monkeypatch.syspath_prepend(_tk_finto(tmp_path, ["/home/s/a.jpg", "", "/home/s/b.jpg"]))
    for m in ("tkinter", "tkinter.filedialog"): monkeypatch.delitem(sys.modules, m, raising=False)
    assert dialoghi.scegli_con_tk(["foto", "Scegli", "*.jpg *.png"]) == 0
    assert capsys.readouterr().out == "/home/s/a.jpg\n/home/s/b.jpg"
    monkeypatch.setenv("TK_SENZA_TOPMOST", "1")
    for tipo in ("cartella", "zip", "catalogo"):
        assert dialoghi.scegli_con_tk([tipo, "Scegli"]) == 0 and capsys.readouterr().out == "/home/s/a.jpg"
    righe = (tmp_path / "tkinter" / "chiamate.log").read_text(encoding="utf-8").splitlines()
    assert [r.split(",")[0] for r in righe] == ['["file"', '["cartella"', '["file"', '["file"'] and "*.zip" in righe[2] and "*.json" in righe[3]
    for m in ("tkinter", "tkinter.filedialog"): sys.modules.pop(m, None)


def test_tk_da_python_e_da_compilato(tmp_path, monkeypatch):
    """il processo figlio di Tk da Python (script fisso _TK, vero, con un tkinter finto) e da compilato («_dialogo»)"""
    monkeypatch.setenv("PYTHONPATH", _tk_finto(tmp_path, ["/home/s/Foto"]))
    assert dialoghi.Tk()._scegli("cartella", "Scegli") == [os.path.normpath("/home/s/Foto")], "lo script _TK vero, nella cartella del pacchetto"
    cmd = []
    monkeypatch.setattr(dialoghi.subprocess, "run", lambda c, **k: cmd.append((c, k["cwd"])) or types.SimpleNamespace(returncode=0, stdout="/home/s/a.jpg\n"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert dialoghi.Tk()._scegli("foto", "Scegli") == [os.path.normpath("/home/s/a.jpg")]
    assert cmd == [([sys.executable, "_dialogo", "foto", "Scegli", " ".join(dialoghi.TIPI_FOTO)], processi.cartella_pacchetto())]


# ---------------------------------------------------------------- copie del motore per la 1.x
def test_copie_del_motore_dalle_risorse(tmp_path, monkeypatch):
    """nel programma compilato i .py del motore non ci sono: le copie per la 1.x vengono dalle risorse (motore_1x/*.txt)"""
    ris = tmp_path / "risorse"; (ris / "motore_1x").mkdir(parents=True)
    for n in formato_1x.MOTORE_1X: (ris / "motore_1x" / (n + ".txt")).write_text(f"# {n} dalle risorse\n", encoding="utf-8")
    (ris / "vib_lut.npz").write_bytes(b"lut")
    monkeypatch.setattr(risorse, "CARTELLA", str(ris))
    monkeypatch.setattr(formato_1x, "__file__", str(tmp_path / "compilato" / "impaginatore" / "formato_1x.py"))
    out = tmp_path / "prj"; out.mkdir()
    formato_1x.copia_motore(str(out))
    assert sorted(os.listdir(out)) == ["album_libere.py", "testo.py", "vib_lut.npz"]
    assert (out / "album_libere.py").read_text(encoding="utf-8") == "# album_libere.py dalle risorse\n"
    monkeypatch.undo()
    assert formato_1x.sorgente_motore("testo.py").endswith(os.path.join("motore", "testo.py")), "da Python: il modulo vero"


# ---------------------------------------------------------------- funzioni del motore sostituite
class _SenzaCodice:
    """come una funzione compilata da Nuitka: il suo __code__ non si può cambiare"""
    def __call__(self, *a): raise AssertionError("questa non si chiama più")

    @property
    def __code__(self): return None

    @__code__.setter
    def __code__(self, v): raise RuntimeError("__code__ is not writable in Nuitka")


def test_motore_sostituito_anche_da_compilato(monkeypatch):
    from impaginatore.motore import album_libere as AL
    finto = types.SimpleNamespace(zcrop=_SenzaCodice(), layout=_SenzaCodice(), crop=lambda i, W, H, z: (0.1, 0.0, 0.9, 1.0), M={0: {"ar": 1.5}},
                                  _place=lambda side, mode, it: dict(it, lato=side, modo=mode))
    monkeypatch.setattr(AL, "_a", finto)
    AL._sostituisci("zcrop", AL._zcrop); AL._sostituisci("layout", AL._layout)
    assert isinstance(finto.zcrop, functools.partial) and isinstance(finto.layout, functools.partial)
    it = dict(i=0, W=10, H=10, z=1.0)
    assert finto.zcrop(it) == (0.1, 0.0, 0.9, 1.0) == AL._zcrop(it, A=finto)
    assert finto.zcrop(dict(it, a=5)) == AL._zcrop(dict(it, a=5), A=finto)
    disposti = finto.layout([("full", [dict(n=1, libera=True)]), ("p", [dict(n=2), dict(n=3, zo=0)])])
    assert [(d["n"], d["lato"], d["modo"]) for d in disposti] == [(3, "R", "p"), (2, "R", "p"), (1, "L", "full")], "le cornici libere sopra le altre"
