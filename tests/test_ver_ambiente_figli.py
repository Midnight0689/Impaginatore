"""VER-011: nessun processo figlio che non sia un nostro riavvio riceve il gettone del server (finestre di sistema, file
manager, Cestino, Photoshop, git, pip, il browser): l'ambiente lo costruisce sempre processi.ambiente_figli."""
import os
import subprocess

import pytest

from impaginatore.aggiornamenti import git
from impaginatore.piattaforma import azioni, dialoghi, photoshop, processi

SEGRETO = "gettone-segreto-di-prova"


class Finto:
    returncode = 0
    stdout = ""
    stderr = ""


@pytest.fixture
def lanci(monkeypatch):
    """subprocess finto in tutti i moduli che lanciano programmi: registra l'ambiente passato (None = quello del processo)"""
    visti = []

    def lancia(cmd, **kw):
        visti.append((cmd[0], kw.get("env")))
        f = Finto(); f.stdout = b"" if not kw.get("text") and not kw.get("encoding") else ""; f.stderr = f.stdout; return f
    for m in (azioni, dialoghi, photoshop, git):
        monkeypatch.setattr(m.subprocess, "run", lancia); monkeypatch.setattr(m.subprocess, "Popen", lancia)
    monkeypatch.setenv("IMPAGINATORE_GETTONE", SEGRETO)
    yield visti
    assert visti and all(e is not None and "IMPAGINATORE_GETTONE" not in e for _, e in visti), visti
    assert all(e.get("PYTHONUTF8") == "1" for _, e in visti), "l'ambiente viene sempre da processi.ambiente_figli"


@pytest.mark.parametrize("s", ["mac", "windows", "linux"])
def test_mostra_e_cestino(lanci, monkeypatch, tmp_path, s):
    monkeypatch.setattr(azioni, "sistema", lambda: s)
    monkeypatch.setattr(azioni.shutil, "which", lambda n: "/usr/bin/" + n)
    azioni.mostra(str(tmp_path)); azioni.cestina(str(tmp_path))
    if s == "windows": assert lanci[-1][1]["IMPAGINATORE_PERCORSO"] == os.path.normpath(str(tmp_path)), "il percorso passa dall'ambiente"


def test_mostra_con_xdg_open(lanci, monkeypatch, tmp_path):
    monkeypatch.setattr(azioni, "sistema", lambda: "linux")
    monkeypatch.setattr(azioni.shutil, "which", lambda n: "/usr/bin/" + n)
    Finto.returncode = 1                          # gdbus non riesce: si apre la cartella con xdg-open
    try: azioni.mostra(str(tmp_path))
    finally: Finto.returncode = 0
    assert [c for c, _ in lanci] == ["gdbus", "xdg-open"]


@pytest.mark.parametrize("finestre", [dialoghi.Mac, dialoghi.Tk, dialoghi.Zenity, dialoghi.Kdialog])
def test_finestre_di_sistema(lanci, finestre):
    for tipo in ("cartella", "zip", "foto"): finestre()._scegli(tipo, "Scegli")


@pytest.mark.parametrize("s", ["mac", "windows"])
def test_photoshop(lanci, monkeypatch, tmp_path, s):
    monkeypatch.setattr(photoshop, "sistema", lambda: s)
    monkeypatch.setattr(photoshop, "trova", lambda: dict(nome="Adobe Photoshop 2026", percorso="/x"))
    photoshop.esegui_jsx(str(tmp_path / "a.jsx")); photoshop.esegui_js("1")


def test_git_e_pip(lanci, monkeypatch, tmp_path):
    g = git.Git(str(tmp_path)); g._git("status")
    monkeypatch.setattr(git.shutil, "which", lambda n: None); g.prepara_ambiente()
    monkeypatch.setattr(git.shutil, "which", lambda n: "/usr/bin/uv"); g.prepara_ambiente()


def test_browser_senza_gettone(monkeypatch):
    visti = []
    monkeypatch.setenv("IMPAGINATORE_GETTONE", SEGRETO)
    monkeypatch.setattr(processi.webbrowser, "open", lambda u: visti.append((u, os.environ.get("IMPAGINATORE_GETTONE"))) or True)
    assert processi.apri_browser("http://127.0.0.1:1/avvio?c=x") is True
    assert visti == [("http://127.0.0.1:1/avvio?c=x", None)], "il browser parte senza il gettone nell'ambiente"
    assert os.environ["IMPAGINATORE_GETTONE"] == SEGRETO, "e il gettone torna per i riavvii del server"
    monkeypatch.delenv("IMPAGINATORE_GETTONE")
    processi.apri_browser("http://127.0.0.1:1/")
    assert "IMPAGINATORE_GETTONE" not in os.environ


def test_browser_della_schermata(home, monkeypatch):
    """la schermata apre il browser con processi.apri_browser (anche dopo il ritardo)"""
    visti = []
    monkeypatch.setattr(processi, "apri_browser", lambda u: visti.append(u))
    home.apri_browser("http://127.0.0.1:1/", 0)
    from aiuti import attendi
    attendi(lambda: visti, 10)


def test_riavvio_tiene_il_gettone(monkeypatch):
    """i nostri riavvii (os.execv, rilancia_dopo) sono gli unici a riceverlo"""
    monkeypatch.setenv("IMPAGINATORE_GETTONE", SEGRETO); chiamate = []
    monkeypatch.setattr(processi.os, "execv", lambda exe, argv: chiamate.append(os.environ.get("IMPAGINATORE_GETTONE")))
    processi.riesegui(["python"])
    monkeypatch.setattr(processi.subprocess, "Popen", lambda cmd, **k: chiamate.append(k["env"].get("IMPAGINATORE_GETTONE")))
    processi.rilancia_dopo(["python"], 0, gettone=SEGRETO)
    assert chiamate == [SEGRETO, SEGRETO] and subprocess is processi.subprocess
