"""Il programma vero, come lo lancia l'utente: «python -m impaginatore» (schermata) che apre l'editor in un processo a parte;
riavvio dell'editor (stessi argomenti), chiusura di tutto. E il comando da riga di comando."""
import os
import re
import shutil
import socket
import subprocess
import sys

import pytest
from aiuti import Client, attendi

from impaginatore import __version__, sicurezza


def _avvia(args, env=None):
    p = subprocess.Popen([sys.executable, "-m", "impaginatore", *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=env)
    riga = p.stdout.readline()
    m = re.search(r"http://127\.0\.0\.1:(\d+)/", riga)
    assert m, riga + (p.stdout.read() if p.poll() is not None else "")
    return p, int(m.group(1))


@pytest.mark.lento
def test_programma_completo(tmp_path, foto_campione):
    progetti = tmp_path / "Progetti"
    home, hp = _avvia(["--porta", "0", "--no-browser", "--progetti", str(progetti)])
    try:
        h = Client(hp, sicurezza.gettone_di("home", hp))                 # come un client locale fidato: il gettone dal file di sessione
        p = h.post("/api/nuovo", {"nome": "Vero", "w": 30, "h": 30})["path"]
        for f in sorted(os.listdir(foto_campione))[:4]: shutil.copy(os.path.join(foto_campione, f), os.path.join(p, "Foto", f))
        ep = h.post("/api/apri", {"path": p})["porta"]
        attendi(lambda: h.get(f"/api/pronto?porta={ep}")["pronto"], 120)
        assert h.post("/api/apri", {"path": p})["porta"] == ep, "un solo editor per progetto"
        e = Client(ep, sicurezza.gettone_di("editor", ep)); st = e.get("/api/state"); assert len(st["photos"]) == 4 and st["home"] == f"http://127.0.0.1:{hp}"
        assert e.get("/api/ping")["path"] == p
        # foto aggiunte: l'editor salva e riparte da solo con gli stessi argomenti (os.execv)
        nuova = os.path.join(p, "nuova"); os.mkdir(nuova)                          # dentro il progetto: una cartella che l'editor può usare
        shutil.copy(os.path.join(foto_campione, "V10.jpg"), os.path.join(nuova, "Z99.jpg"))
        r = e.post("/api/import", {"paths": [str(nuova)]}); assert r == {"importate": 1, "saltate": 0, "riavvio": True}
        attendi(lambda: e.get("/api/ping")["boot"] != st["boot"], 120)          # riavviato con lo stesso gettone (variabile d'ambiente, non argomenti)
        assert len(e.get("/api/state")["photos"]) == 5
        el = h.get("/api/progetti")["progetti"]; assert el[0]["aperto"] and el[0]["foto"] == 5
        with open(os.path.join(str(progetti), "editor.log"), encoding="utf-8") as f: assert "Editor album" in f.read()
        assert h.post("/api/esci") == {"ok": True}
        home.wait(20)
        attendi(lambda: _chiusa(ep), 20)
    finally:
        if home.poll() is None: home.terminate(); home.wait(10)


def _chiusa(porta):
    with socket.socket() as s: return s.connect_ex(("127.0.0.1", porta)) != 0


def test_versione():
    r = subprocess.run([sys.executable, "-m", "impaginatore", "--versione"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and r.stdout.strip() == f"Impaginatore {__version__}"
    exe = shutil.which("impaginatore", path=os.path.dirname(sys.executable))
    if exe:
        r = subprocess.run([exe, "--versione"], capture_output=True, text=True, encoding="utf-8"); assert __version__ in r.stdout


def test_aiuto_editor():
    r = subprocess.run([sys.executable, "-m", "impaginatore", "editor", "--help"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "--progetto" in r.stdout
    r = subprocess.run([sys.executable, "-m", "impaginatore.editor"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2 and "--progetto" in r.stderr


def test_porta_occupata_da_altri(capsys):
    from impaginatore import cli
    s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1)
    try:
        assert cli.main(["--porta", str(s.getsockname()[1]), "--no-browser"]) == 1
        assert "occupata" in capsys.readouterr().err
    finally: s.close()


def test_gia_aperto_apre_solo_la_pagina(home_srv, monkeypatch, capsys):
    from impaginatore.home import server
    aperti = []
    monkeypatch.setattr(server.webbrowser, "open", lambda u: aperti.append(u))
    assert server.main(["--porta", str(home_srv.porta)]) == 0
    assert len(aperti) == 1 and aperti[0].startswith(f"http://127.0.0.1:{home_srv.porta}/avvio?c=") and "già aperto" in capsys.readouterr().out
    assert server.main(["--porta", str(home_srv.porta), "--no-browser"]) == 0 and len(aperti) == 1


def test_main_in_processo(monkeypatch, tmp_path):
    """main() della schermata e dell'editor fino a serve_forever (interrotto subito)"""
    from impaginatore import cli
    from impaginatore.editor import server as E
    from impaginatore.home import server as H
    from impaginatore.servizio import ServerLocale
    aperti = []
    monkeypatch.setattr(H, "apri_browser", lambda u: aperti.append(u))
    monkeypatch.setattr(ServerLocale, "serve_forever", lambda self: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert cli.main(["--porta", "0", "--progetti", str(tmp_path / "P")]) == 0
    assert aperti and os.path.isdir(tmp_path / "P")
    p = H.nuovo({"nome": "M", "w": 30, "h": 30})
    assert cli.main(["editor", "--progetto", p, "--porta", "0"]) is None and E.PROJ == p
