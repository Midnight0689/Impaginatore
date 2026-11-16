"""Lo strumento del negozio (marketing/negozio/chiavi/chiavi.py) e il programma parlano lo stesso formato: le chiavi e
l'elenco delle revoche che firma lo strumento valgono nel programma, con la chiave pubblica stampata da genera-coppia."""
import csv
import importlib.util
import json
import os
import re

import pytest

from impaginatore import licenze
from impaginatore.licenze import chiave as K

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def negozio(tmp_path, monkeypatch, capsys):
    """chiavi.py caricato dal suo file, con la cartella del negozio nel test e la sua chiave pubblica nel programma"""
    spec = importlib.util.spec_from_file_location("chiavi_negozio", os.path.join(RADICE, "marketing", "negozio", "chiavi", "chiavi.py"))
    C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
    d = tmp_path / "negozio"
    C.esegui = lambda *argv: C.main(["--dir", str(d), *argv])
    C.dir = d
    assert C.esegui("genera-coppia") == 0
    pub = re.search(r'CHIAVI_PUBBLICHE = \{1: Pubblica\("([0-9a-f]{64})"\)\}', capsys.readouterr().out).group(1)
    monkeypatch.setattr(K, "CHIAVI_PUBBLICHE", {1: K.Pubblica(pub)})
    return C


def _emetti(C, capsys, *argv):
    assert C.esegui("emetti", "--json", "--riferimento", "FT 1", *argv) == 0
    return json.loads(capsys.readouterr().out)


def test_chiavi_dello_strumento_valgono_nel_programma(negozio, capsys, licenza):
    C = negozio
    assert C.esegui("genera-coppia") == 1, "la coppia c'è già: senza --nuova non si rifà"
    capsys.readouterr()
    pro = _emetti(C, capsys, "--tier", "pro", "--intestatario", "Studio Rossi", "--prezzo", "lancio")
    info = K.decodifica(pro["chiave"])
    assert (info["fascia"], info["seriale"], info["intestatario"], info["computer"], info["scade"], info["formato"]) == ("pro", 1, "Studio Rossi", 2, None, 1)
    assert pro["scadenza"] is None and pro["formato"] == 1
    licenza.usa(None); assert licenze.attiva(pro["chiave"])["fascia"] == "pro"
    lab = _emetti(C, capsys, "--tier", "laboratorio", "--intestatario", "Lab", "--prezzo", "convenzione", "--scadenza", "2099-03-31")
    assert (lab["formato"], lab["scadenza"]) == (2, "2099-03-31") and K.decodifica(lab["chiave"])["scade"] == "2099-03-31"
    assert C.esegui("verifica", lab["chiave"]) == 0 and "VALIDA · registro: attiva" in capsys.readouterr().out
    with open(C.dir / "registro.csv", encoding="utf-8", newline="") as f: righe = list(csv.DictReader(f))
    assert [(r["seriale"], r["scadenza"]) for r in righe] == [("1", ""), ("2", "2099-03-31")]
    with pytest.raises(ValueError, match="scadenza"): C.componi(1, "pro", 2, 2, 3, C.EPOCA.replace(year=2027), "x", 0, C.EPOCA)
    with pytest.raises(C.ChiaveNonValida, match="formato 3"):
        p = bytes([3]) + C.componi(1, "pro", 2, 2, 3, C.EPOCA, "x")[1:]
        C.decodifica(C.in_testo(p + bytes(64)), {1: bytes(32)})


def test_revoca_e_togli_revoca_arrivano_con_il_rilascio(negozio, capsys, licenza, monkeypatch, tmp_path):
    C = negozio
    chiave = _emetti(C, capsys, "--tier", "studio", "--intestatario", "Studio Bianchi", "--prezzo", "listino")["chiave"]
    licenza.usa(chiave)
    assert C.esegui("revoca", "--seriale", "1", "--motivo", "rimborso") == 0
    out = capsys.readouterr().out; assert "src/impaginatore/licenze/revoche.json" in out
    with pytest.raises(SystemExit, match="non «attiva»"): C.esegui("revoca", "--seriale", "1", "--motivo", "rimborso")
    with pytest.raises(SystemExit, match="assente"): C.esegui("revoca", "--seriale", "9", "--motivo", "rimborso")
    rilascio = tmp_path / "rilascio" / "revoche.json"
    assert C.esegui("revoche", "--uscita", str(rilascio)) == 0
    monkeypatch.setattr(licenze, "FILE_REVOCHE", str(rilascio))
    assert licenze.stato()["stato"] == "revocata", "l'elenco firmato dallo strumento vale nel programma"
    assert json.loads((C.dir / "revoche.json").read_text(encoding="utf-8"))["seriali"] == [1]
    assert C.esegui("togli-revoca", "--seriale", "1", "--motivo", "storno-a-favore") == 0
    with pytest.raises(SystemExit, match="non «revocata»"): C.esegui("togli-revoca", "--seriale", "1", "--motivo", "errore")
    assert C.esegui("revoche", "--uscita", str(rilascio)) == 0 and json.loads(rilascio.read_text(encoding="utf-8"))["seriali"] == []
    os.utime(rilascio, ns=(1, 1))                                                       # nuova versione dell'elenco anche se scritta nello stesso istante
    assert licenze.stato()["stato"] == "attiva"
    with open(C.dir / "registro.csv", encoding="utf-8", newline="") as f: r = next(csv.DictReader(f))
    assert r["stato"] == "attiva" and "revocata" in r["nota"] and "revoca tolta" in r["nota"]
    assert C.esegui("revoche") == 0 and (C.dir / "revoche.json").exists()


def test_registro_di_prima_senza_la_colonna_della_scadenza(negozio, capsys):
    C = negozio; C.dir.mkdir(exist_ok=True)
    vecchi = ["seriale", "emessa", "tier", "attivazioni", "versione_maggiore", "prezzo", "riferimento", "intestatario", "impronta", "stato", "nota"]
    with open(C.dir / "registro.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=vecchi); w.writeheader(); w.writerow(dict.fromkeys(vecchi, "") | {"seriale": "7", "stato": "attiva", "prezzo": "lancio"})
    assert _emetti(C, capsys, "--tier", "essenziale", "--intestatario", "X", "--prezzo", "listino")["seriale"] == 8
    with open(C.dir / "registro.csv", encoding="utf-8", newline="") as f: righe = list(csv.DictReader(f))
    assert [(r["seriale"], r["scadenza"]) for r in righe] == [("7", ""), ("8", "")]


def test_autotest_dello_strumento(negozio, capsys):
    assert negozio.esegui("autotest") == 0 and "formati 1 e 2" in capsys.readouterr().out
