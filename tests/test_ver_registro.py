"""VER-013: il registro (e le uscite dei processi) li legge solo chi usa il programma; nomi delle foto e percorsi solo a DEBUG."""
import logging
import os
import stat
import sys

import pytest

from impaginatore import giornale
from impaginatore.piattaforma import processi

pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="permessi POSIX")


def modo(p): return stat.S_IMODE(os.stat(p).st_mode)


@pytest.fixture
def registro():
    log = logging.getLogger(giornale.NOME); prima = list(log.handlers)
    yield log
    for h in [h for h in log.handlers if h not in prima]: log.removeHandler(h); h.close()


def test_cartella_e_file_riservati_anche_se_esistevano(registro, casa):
    from impaginatore.piattaforma import cartelle
    d = os.path.join(cartelle.dati_utente(), "registro"); os.makedirs(d, mode=0o755); os.chmod(d, 0o755)
    f = os.path.join(d, "impaginatore.log")
    with open(f, "w", encoding="utf-8") as x: x.write("vecchio\n")
    os.chmod(f, 0o644)                                             # creato da una versione precedente con l'umask
    assert giornale.configura("prova") == f and giornale.configura("prova") == f, "una volta sola per processo"
    logging.getLogger("impaginatore.prova").warning("riga di prova")
    assert modo(d) == 0o700 and modo(f) == 0o600
    with open(f, encoding="utf-8") as x: assert "vecchio" in x.read()


def test_rotazione_tiene_i_permessi(tmp_path):
    f = str(tmp_path / "r.log"); h = giornale._FileRiservato(f, maxBytes=200, backupCount=2, encoding="utf-8")
    try:
        lg = logging.getLogger("prova.rotazione"); lg.propagate = False; lg.addHandler(h); lg.setLevel(logging.INFO)
        for k in range(40): lg.info("riga %d %s", k, "x" * 40)
    finally: lg.removeHandler(h); h.close()
    file = sorted(p for p in os.listdir(tmp_path) if p.startswith("r.log"))
    assert file == ["r.log", "r.log.1", "r.log.2"] and all(modo(tmp_path / p) == 0o600 for p in file), [(p, oct(modo(tmp_path / p))) for p in file]


def test_permessi_che_non_si_cambiano(tmp_path, monkeypatch, casa, registro, caplog):
    f = str(tmp_path / "x.log")

    def no(*a): raise PermissionError(1, "non permesso")
    monkeypatch.setattr(giornale.os, "chmod", no)
    fd = giornale.riservato(f); os.close(fd)
    assert os.path.exists(f), "il file si apre lo stesso"
    with caplog.at_level(logging.WARNING, logger=giornale.NOME):
        giornale.configura("prova")
    assert "permessi della cartella del registro non impostati" in caplog.text


def test_uscita_del_processo_staccato(tmp_path, monkeypatch):
    """stacca (--daemon): il file che raccoglie stdout e stderr nasce 0600 (contiene percorsi)"""
    f = str(tmp_path / "impaginatore.log"); dup = []
    monkeypatch.setattr(processi, "sistema", lambda: "linux")
    monkeypatch.setattr(processi.os, "fork", lambda: 0, raising=False)
    monkeypatch.setattr(processi.os, "setsid", lambda: None, raising=False)
    monkeypatch.setattr(processi.os, "dup2", lambda a, b: dup.append(b))
    assert processi.stacca(f) is True and dup == [0, 1, 2] and modo(f) == 0o600


def test_uscita_degli_editor(home, progetto, monkeypatch):
    lanci = []

    class Finto:
        def poll(self): return None
    monkeypatch.setattr(home.subprocess, "Popen", lambda cmd, **k: lanci.append(cmd) or Finto())
    monkeypatch.setattr(home, "gia_attivo", lambda p: None)
    home.apri(progetto)
    assert lanci and modo(os.path.join(home.PROGETTI, "editor.log")) == 0o600


def test_nomi_e_percorsi_solo_a_debug(editor, caplog, tmp_path):
    from impaginatore.motore import album as A
    lg = logging.getLogger(giornale.NOME)
    with caplog.at_level(logging.DEBUG, logger=giornale.NOME):
        assert editor.codice("/img/thumb/Nome%20segreto?w=10", **{"X-Impaginatore-Gettone": None}) == 401
        (tmp_path / "Foto rovinata segreta.jpg").write_bytes(b"non sono una foto")
        A.SCARTATE.clear(); A._nuove([str(tmp_path / "Foto rovinata segreta.jpg")], [])
    sopra = [r.getMessage() for r in caplog.records if r.levelno > logging.DEBUG and r.name.startswith(lg.name)]
    sotto = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
    assert sopra and not any("segret" in m or str(tmp_path) in m for m in sopra), sopra
    assert any("Nome segreto" in m or "Nome%20segreto" in m for m in sotto) and any("Foto rovinata segreta" in m for m in sotto), sotto
