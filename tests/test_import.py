"""Importare il pacchetto non deve fare niente: niente argomenti letti, niente progetti caricati, niente file, porte o thread."""
import os
import subprocess
import sys

CODICE = r'''
import importlib, os, pkgutil, sys, threading
prima = set(os.listdir("."))
sys.argv = ["programma", "--progetto", "/non/esiste", "--porta", "1"]       # le 1.x leggevano questi argomenti all'import
import impaginatore
nomi = sorted(m.name for m in pkgutil.walk_packages(impaginatore.__path__, "impaginatore."))
for n in nomi: importlib.import_module(n)
assert threading.active_count() == 1, threading.enumerate()
assert set(os.listdir(".")) == prima, set(os.listdir(".")) ^ prima
assert not os.listdir(os.environ["HOME"]), os.listdir(os.environ["HOME"])
assert not any(type(f).__name__ == "_Alias" for f in sys.meta_path), "i nomi 1.x si installano solo leggendo uno spec"
from impaginatore.editor import server as E
from impaginatore.home import server as H
assert E.PROJ is None and E.SP == [] and H.PROGETTI is None and H.EDITORS == {}
print(len(nomi))
'''


def test_import_senza_effetti(tmp_path, casa):
    vuota = tmp_path / "vuota"; vuota.mkdir()
    r = subprocess.run([sys.executable, "-c", CODICE], cwd=str(vuota), capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, HOME=str(casa)))
    assert r.returncode == 0, r.stderr[-3000:]
    assert int(r.stdout) >= 30
