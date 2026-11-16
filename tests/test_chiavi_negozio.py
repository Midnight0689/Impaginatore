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


def test_firma_catalogo(negozio, capsys, tmp_path):
    """T-208: il catalogo di un laboratorio firmato dallo strumento è «verificato» nel programma, con la stessa chiave pubblica"""
    from impaginatore.laboratori import catalogo as CAT
    C = negozio
    doc = {"formato_catalogo": 1, "id": "lab-prova", "nome": "Album è prova", "laboratorio": "Lab", "data": "2026-11-01",
           "prodotti": [{"id": "a30", "nome": "A 30", "pagina_cm": [30, 22.5], "abbondanza_mm": 3, "ppi": 300, "consegna": {"nome": "{n}"}}], "firma": "vecchia"}
    src = tmp_path / "lab.json"; src.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert C.esegui("firma-catalogo", str(src)) == 0 and "firmato con la chiave 1" in capsys.readouterr().out
    firmato = json.loads((tmp_path / "lab-firmato.json").read_text(encoding="utf-8"))
    assert CAT.verifica(firmato) == (True, "firmato dal produttore di Impaginatore") and CAT.valida(firmato)["nome"] == "Album è prova"
    assert C.esegui("firma-catalogo", str(src), "--uscita", str(tmp_path / "altro.json")) == 0 and CAT.verifica(json.loads((tmp_path / "altro.json").read_text(encoding="utf-8")))[0]
    (tmp_path / "x.json").write_text('{"formato_catalogo": 2}', encoding="utf-8")
    with pytest.raises(SystemExit, match="non è un catalogo del formato 1"): C.esegui("firma-catalogo", str(tmp_path / "x.json"))
    with pytest.raises(SystemExit, match="catalogo non letto"): C.esegui("firma-catalogo", str(tmp_path / "manca.json"))


def test_emetti_beta_una_chiave_per_tester(negozio, capsys, licenza, tmp_path):
    """beta privata: chiavi Studio con il segno beta e la scadenza, una per tester, nel registro e in un CSV riservato;
    nel programma sono «Beta privata · scade il …»"""
    C = negozio; capsys.readouterr()
    elenco = tmp_path / "tester.txt"
    elenco.write_text("# tester della beta\nAnna Neri\n\n  Studio Bianchi  \nFoto Àlfa\n", encoding="utf-8")
    assert C.esegui("emetti-beta", "--quante", "3", "--scadenza", "2099-01-31", "--intestatari", str(elenco), "--data", "2026-11-16") == 0
    out = capsys.readouterr().out
    assert "3 chiavi della beta privata · studio · 5 computer" in out and "seriali 1–3" in out
    csv_beta = C.dir / "beta-2026-11-16-seriali-1-3.csv"
    assert csv_beta.exists() and (os.name != "posix" or csv_beta.stat().st_mode & 0o777 == 0o600)
    with open(csv_beta, encoding="utf-8", newline="") as f: emesse = list(csv.DictReader(f))
    assert [(r["seriale"], r["intestatario"], r["scadenza"]) for r in emesse] == [("1", "Anna Neri", "2099-01-31"), ("2", "Studio Bianchi", "2099-01-31"), ("3", "Foto Àlfa", "2099-01-31")]
    assert emesse[0]["link"] == "impaginatore://attiva?chiave=" + emesse[0]["chiave"]
    with open(C.dir / "registro.csv", encoding="utf-8", newline="") as f: righe = list(csv.DictReader(f))
    assert {(r["tier"], r["prezzo"], r["nota"], r["scadenza"], r["riferimento"]) for r in righe} == {("studio", "beta", "beta privata", "2099-01-31", "beta privata fino al 2099-01-31")}
    info = K.decodifica(emesse[1]["chiave"])
    assert (info["fascia"], info["beta"], info["omaggio"], info["formato"], info["scade"], info["intestatario"], info["seriale"]) == ("studio", True, True, 2, "2099-01-31", "Studio Bianchi", 2)
    licenza.usa(None); s = licenze.attiva(emesse[1]["chiave"])
    assert s["beta"] and s["riga_beta"] == "Beta privata · scade il 31/01/2099" and s["funzioni"] == licenze.funzioni_di("studio")
    assert C.esegui("emetti-beta", "--scadenza", "2099-01-31", "--intestatari", str(elenco), "--json", "--uscita", str(tmp_path / "b.csv"), "--riferimento", "BETA-2") == 0
    j = json.loads(capsys.readouterr().out); assert [c["seriale"] for c in j["chiavi"]] == ["4", "5", "6"] and j["file"] == str(tmp_path / "b.csv")
    with pytest.raises(FileExistsError): C.esegui("emetti-beta", "--scadenza", "2099-01-31", "--intestatari", str(elenco), "--uscita", str(tmp_path / "b.csv"))
    with open(C.dir / "registro.csv", encoding="utf-8", newline="") as f: assert len(list(csv.DictReader(f))) == 6, "un CSV che c'è già: niente registrato"


def test_emetti_beta_controlla_prima_di_firmare(negozio, capsys, tmp_path):
    C = negozio; elenco = tmp_path / "t.txt"; elenco.write_text("Anna\nBruno\n", encoding="utf-8")
    beta = lambda *a: C.esegui("emetti-beta", "--intestatari", str(elenco), *a)
    with pytest.raises(SystemExit, match="--quante 3 ma l'elenco ha 2"): beta("--quante", "3", "--scadenza", "2099-01-31")
    with pytest.raises(SystemExit, match="prima della data di emissione"): beta("--scadenza", "2026-01-01", "--data", "2026-11-16")
    with pytest.raises(SystemExit, match="dentro il repository"): beta("--scadenza", "2099-01-31", "--uscita", os.path.join(RADICE, "chiavi-beta.csv"))
    elenco.write_text("Anna\nAnna\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="ripetuti"): beta("--scadenza", "2099-01-31")
    elenco.write_text("x" * 49 + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="oltre 48 byte"): beta("--scadenza", "2099-01-31")
    elenco.write_text("# nessuno\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="--quante 0"): beta("--scadenza", "2099-01-31")
    with pytest.raises(SystemExit, match="non letto"): C.esegui("emetti-beta", "--intestatari", str(tmp_path / "manca.txt"), "--scadenza", "2099-01-31")
    assert not (C.dir / "registro.csv").exists() and not os.path.exists(os.path.join(RADICE, "chiavi-beta.csv")), "niente firmato, niente scritto"
