"""Importare il pacchetto non deve fare niente: niente argomenti letti, niente progetti caricati, niente file, porte o thread.

I moduli che vogliono un extra facoltativo (EXTRA) si provano solo dove l'extra è installato: senza, quella prova si
salta con il motivo, come i test del server MCP. Tutti gli altri moduli si provano sempre."""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

EXTRA = {"impaginatore.mcp.server": "mcp"}          # modulo -> pacchetto dell'extra facoltativo che importa (pyproject.toml)
MOTIVO_MCP = "extra «mcp» non installato (uv sync --locked --extra dev --extra mcp)"

CODICE = r'''
import importlib, json, os, pkgutil, sys, threading
salta = set(json.loads(sys.argv[1]))
prima = set(os.listdir("."))
sys.argv = ["programma", "--progetto", "/non/esiste", "--porta", "1"]       # le 1.x leggevano questi argomenti all'import
import impaginatore
nomi = sorted(m.name for m in pkgutil.walk_packages(impaginatore.__path__, "impaginatore.") if m.name not in salta)
for n in nomi: importlib.import_module(n)
assert threading.active_count() == 1, threading.enumerate()
assert set(os.listdir(".")) == prima, set(os.listdir(".")) ^ prima
assert not os.listdir(os.environ["HOME"]), os.listdir(os.environ["HOME"])
assert not [f for f in sys.meta_path if type(f).__module__.startswith("impaginatore")], "nessun cercatore di moduli aggiunto"
from impaginatore.editor import server as E
from impaginatore.home import server as H
assert E.PROJ is None and E.SP == [] and H.PROGETTI is None and H.EDITORS == {}
print(len(nomi))
'''


def _importa(cartella, casa, salta):
    """importa in un processo nuovo tutti i moduli del pacchetto tranne quelli di salta; quanti ne ha importati"""
    vuota = cartella / "vuota"; vuota.mkdir(parents=True)
    r = subprocess.run([sys.executable, "-c", CODICE, json.dumps(sorted(salta))], cwd=str(vuota), capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, HOME=str(casa)))
    assert r.returncode == 0, r.stderr[-3000:]
    return int(r.stdout)


def test_import_senza_effetti(tmp_path, casa):
    """tutti i moduli che non vogliono un extra facoltativo: anche in un ambiente con i soli strumenti di sviluppo"""
    assert _importa(tmp_path, casa, EXTRA) >= 30


def test_import_dei_moduli_degli_extra_senza_effetti(tmp_path, casa):
    """anche i moduli che vogliono un extra (il server MCP con l'SDK ufficiale): tutto il pacchetto"""
    pytest.importorskip("mcp", reason=MOTIVO_MCP)
    assert all(importlib.util.find_spec(m) for m in EXTRA) and set(EXTRA.values()) == {"mcp"}
    assert _importa(tmp_path / "tutti", casa, ()) == _importa(tmp_path / "senza", casa, EXTRA) + len(EXTRA)
