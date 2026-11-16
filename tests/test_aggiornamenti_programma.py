"""Il giro vero degli aggiornamenti (T-207): il programma, in un processo a parte, trova una versione nuova in una release
finta firmata, la scarica, la verifica, la installa, si riavvia sulla stessa porta nella versione nuova (con lo stesso
gettone: la pagina aperta resta collegata), poi torna alla precedente. Nessuna rete: la release è una cartella."""
import json
import logging
import os
import socket
import subprocess
import sys

import pytest
from aiuti import Client, attendi, stato_processo
from aiuti_aggiornamenti import SEME, SRC, ambiente_senza_coverage

from impaginatore import __version__, sicurezza
from impaginatore.aggiornamenti import lanciatore, rilascio


def _porta_libera():
    with socket.socket() as s: s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def _chiusa(porta):
    with socket.socket() as s: return s.connect_ex(("127.0.0.1", porta)) != 0


@pytest.mark.lento
def test_aggiorna_e_torna_indietro_davvero(tmp_path):
    rel = tmp_path / "release"
    pk = rilascio.pacchetto_da_sorgente(SRC, "2.0.1", str(tmp_path / "pacchetto"))
    rilascio.release_finta(str(rel), pk, SEME, novita={"it": ["Prova del giro completo"], "en": ["Full round trip"]})
    porta = _porta_libera()
    env = ambiente_senza_coverage()                              # le copie installate stanno fuori da src: coverage non le segue
    for k in ("IMPAGINATORE_AGGIORNAMENTI", "IMPAGINATORE_SENZA_RIAVVIO", lanciatore.VAR_BASE, lanciatore.VAR_SCELTA): env.pop(k, None)
    env[lanciatore.VAR_FINTI] = str(rel)
    p = subprocess.Popen([sys.executable, "-m", "impaginatore", "--porta", str(porta), "--no-browser", "--progetti", str(tmp_path / "Progetti")],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=env, cwd=os.path.dirname(SRC))
    c = None
    try:
        assert f"127.0.0.1:{porta}" in p.stdout.readline()
        c = Client(porta, sicurezza.gettone_di("home", porta))
        s = c.post("/api/controlla")
        assert s["da_aggiornare"] and s["ultima"]["n"] == "2.0.1" and s["novita"] == ["Prova del giro completo"] and s["errore"] == "", s
        assert c.post("/api/aggiorna") == {"ok": True}
        assert p.wait(60) == 0, "il programma di prima si chiude"
        attendi(lambda: c.get("/api/aggiornamento", timeout=5)["attuale"]["n"] == "2.0.1", 180, 0.5, spiega=lambda: stato_processo("home", porta))
        s = c.get("/api/aggiornamento")
        assert s["annuncio"]["tipo"] == "aggiornato" and s["annuncio"]["versione"] == "2.0.1" and s["precedente"] == __version__
        with open(os.path.join(os.environ["IMPAGINATORE_DATI"], "programma", "attuale.json"), encoding="utf-8") as f: punt = json.load(f)
        assert punt["versione"] == "2.0.1" and punt["confermata"] is True, "la versione nuova è partita e si è confermata"
        assert c.get("/api/versioni")["versioni"][1]["n"] == __version__
        assert c.post("/api/ripristina", {"codice": __version__}) == {"n": __version__, "caricato": True}
        attendi(lambda: c.get("/api/aggiornamento", timeout=5)["attuale"]["n"] == __version__, 180, 0.5, spiega=lambda: stato_processo("home", porta))
        s = c.get("/api/aggiornamento")
        assert s["annuncio"]["tipo"] == "tornato" and s["da_aggiornare"] is False and s["precedente"] is None
        s = c.post("/api/controlla")
        assert s["da_aggiornare"] and s["scartata"] is True, "la versione lasciata si propone ancora, ma senza avviso in pagina"
    finally:
        if c is not None:
            try: c.post("/api/esci", timeout=5)
            except OSError: pass
            attendi(lambda: _chiusa(porta), 30)
        if p.poll() is None: p.kill(); p.wait(10)


def test_la_schermata_conferma_la_versione(monkeypatch, tmp_path, caplog):
    """main() della schermata conferma la versione appena installata quando è in ascolto; se il file non si scrive va avanti"""
    from impaginatore.home import server as H
    from impaginatore.servizio import ServerLocale
    monkeypatch.setattr(ServerLocale, "serve_forever", lambda self: (_ for _ in ()).throw(KeyboardInterrupt()))
    conferme = []
    monkeypatch.setattr(lanciatore, "conferma", lambda: conferme.append(1))
    assert H.main(["--porta", "0", "--no-browser", "--progetti", str(tmp_path / "P")]) == 0 and conferme == [1]
    monkeypatch.setattr(lanciatore, "conferma", lambda: (_ for _ in ()).throw(PermissionError("sola lettura")))
    with caplog.at_level(logging.WARNING, logger="impaginatore.home"):
        assert H.main(["--porta", "0", "--no-browser", "--progetti", str(tmp_path / "P")]) == 0
    assert "conferma della versione non scritta" in caplog.text
