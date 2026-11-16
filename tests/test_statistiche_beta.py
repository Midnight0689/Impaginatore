"""Lo strumento del titolare per la beta privata (strumenti/statistiche_beta.py): legge i file esportati dai tester,
scarta le righe fuori schema e i doppioni, scrive riepilogo.md e riepilogo.csv. Dati finti, nessuna rete."""
import csv
import importlib.util
import json
import os

import pytest

from impaginatore import statistiche as S
from impaginatore.statistiche import invio

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def B():
    spec = importlib.util.spec_from_file_location("statistiche_beta", os.path.join(RADICE, "strumenti", "statistiche_beta.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def riga(ev, t, serie=None, id_="a" * 32, sessione="0" * 12, **campi):
    r = {"v": 1, "t": f"2026-11-{t}Z", "id": id_, "sessione": sessione, "proc": "editor", "ver": "2.0.0", "ev": ev, **campi}
    if serie is not None: r["serie"] = serie
    return r


def scrivi(p, righe, extra=""):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: f.write("".join(json.dumps(r) + "\n" for r in righe) + extra)


def dati(cartella):
    """due tester con la licenza beta e un'installazione senza: percorsi, operazioni, errori, esportazioni"""
    a = [riga("consenso", "17T09:00:00", 7, scelta="si", testo=1),
         riga("avvio", "17T09:00:00", 7, sistema="mac", sistema_versione="14.6.1", architettura="arm64", python="3.12", lingua="it", memoria_gb=16, core=8,
              finestra_programma=True, licenza="attiva", fascia="studio", beta=True, giorni_dal_primo_avvio=0),
         riga("traguardo", "17T09:01:00", 7, nome="primo_album", secondi_dal_primo_avvio=60),
         riga("album_aperto", "17T09:01:10", 7, foto=80, spread=0, larghezza_cm=60.0, altezza_cm=22.5, ppi=300, ms=900, sola_lettura=False),
         riga("traguardo", "17T09:01:10", 7, nome="prime_foto", secondi_dal_primo_avvio=70),
         riga("bozza_proposta", "17T09:02:00", 7, foto=80, spread=12, ritmo="alterna", ms=1500),
         riga("bozza_accettata", "17T09:02:10", 7, spread=12, foto=80, assistente=False),
         riga("primo_spread", "17T09:02:10", 7, secondi=60, modo="bozza", foto=80),
         riga("traguardo", "17T09:02:10", 7, nome="primo_spread", secondi_dal_primo_avvio=130),
         riga("operazioni", "17T09:03:00", 7, op="swap", n=10, rifiutate=1, licenza=0, errori=0, assistente=2, ms_tot=50, ms_max=9),
         riga("operazioni", "17T09:03:00", 7, op="bozza", n=1, rifiutate=0, licenza=0, errori=0, assistente=0, ms_tot=300, ms_max=300),
         riga("controllo", "17T09:04:00", 7, spread=12, blocca=0, guarda=2, info=1, tipi={"ritaglio": 2, "non_usata": 1}, pronto=True, ms=400),
         riga("esportazione", "17T09:10:00", 7, formato="jpg", totale=12, fatti=12, saltati=0, errori=0, ms=30000, secondi_dall_apertura=530, filigrana=False),
         riga("traguardo", "17T09:10:00", 7, nome="prima_esportazione", secondi_dal_primo_avvio=600),
         riga("errore", "17T09:11:00", 7, tipo="OSError", dove="impaginatore.editor.server:run_export", riga=2100, origine="PIL", errno="ENOSPC"),
         riga("chiusura", "17T10:00:00", 7, durata_s=3600)]
    b = [riga("consenso", "18T15:00:00", 8, id_="b" * 32, sessione="1" * 12, scelta="si", testo=1),
         riga("avvio", "18T15:00:00", 8, id_="b" * 32, sessione="1" * 12, sistema="windows", sistema_versione="10.0.22631", architettura="x86_64", python="3.12",
              lingua="en", memoria_gb=8, core=4, finestra_programma=True, licenza="attiva", fascia="studio", beta=True),
         riga("traguardo", "18T15:10:00", 8, id_="b" * 32, sessione="1" * 12, nome="primo_album", secondi_dal_primo_avvio=600),
         riga("primo_spread", "18T15:20:00", 8, id_="b" * 32, sessione="1" * 12, secondi=600, modo="assistente", foto=3),
         riga("traguardo", "18T15:20:00", 8, id_="b" * 32, sessione="1" * 12, nome="primo_spread", secondi_dal_primo_avvio=1200),
         riga("operazioni", "18T15:20:00", 8, id_="b" * 32, sessione="1" * 12, op="swap", n=4, rifiutate=0, licenza=1, errori=1, assistente=4, ms_tot=40, ms_max=20),
         riga("errore", "18T15:21:00", 8, id_="b" * 32, sessione="1" * 12, tipo="OSError", dove="impaginatore.editor.server:run_export", riga=2100, origine="PIL", errno="ENOSPC"),
         riga("esportazione", "18T15:30:00", 8, id_="b" * 32, sessione="1" * 12, formato="pdf", totale=3, fatti=2, saltati=1, errori=1, ms=8000)]
    c = [riga("chiusura", "19T08:00:00", None, id_="c" * 32, sessione="2" * 12, durata_s=50)]
    scrivi(os.path.join(cartella, "anna", "impaginatore-statistiche-aaaaaaaa.jsonl"), a)
    scrivi(os.path.join(cartella, "anna", "copia.jsonl"), a[:5])                                       # lo stesso file mandato due volte
    scrivi(os.path.join(cartella, "bruno.jsonl"), b, extra='non json\n{"ev": "chiusura"}\n' + json.dumps(riga("chiusura", "18T16:00:00", 8, nome="ZQX")) + "\n\n")
    scrivi(os.path.join(cartella, "anonimo.jsonl"), c)
    with open(os.path.join(cartella, "leggimi.txt"), "w") as f: f.write("non è un registro")


def test_riepilogo_per_tester_e_in_tutto(B, tmp_path, capsys):
    dati(str(tmp_path / "in"))
    reg = tmp_path / "registro.csv"
    with open(reg, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["seriale", "intestatario"]); w.writeheader(); w.writerow({"seriale": "7", "intestatario": "Anna Neri"})
    assert B.main([str(tmp_path / "in"), "--uscita", str(tmp_path / "out"), "--registro", str(reg)]) == 0
    assert "Riepilogo scritto in" in capsys.readouterr().out
    md = (tmp_path / "out" / "riepilogo.md").read_text(encoding="utf-8")
    assert "4 file, 25 eventi validi, 3 righe scartate (fuori schema o rotte), 3 tester, dal 2026-11-17 al 2026-11-19." in md
    assert "| Primo spread entro 5 minuti dal primo avvio (obiettivo dei KPI) | 1 tester su 2 che ci sono arrivati |" in md
    assert "| Tempo mediano dal primo avvio al primo spread | 11 min 05 s |" in md
    assert "| Primo spread di un album: con la bozza / a mano / con l'assistente AI | 1 / 0 / 1 |" in md
    assert "| Bozze accettate su proposte | 1 su 1 |" in md and "| Esportazioni complete (tutti gli spread, nessun errore) | 1 su 2 |" in md
    assert "| Operazioni chieste dall'assistente AI | 6 su 15 |" in md and "| Sessioni con almeno un errore | 2 su 3 |" in md
    assert "| avvio | 2 | — |" in md and "| primo_spread | 2 | 11 min 05 s |" in md and "| prima_esportazione | 1 | 10 min 00 s |" in md and "| prima_consegna | 0 | — |" in md
    assert "| swap | 14 | 6.4 ms | 2 | 1 | 6 |" in md and "| bozza | 1 | 300 ms | 0 | 0 | 0 |" in md
    assert "| OSError | impaginatore.editor.server:run_export | ENOSPC | 2 |" in md
    assert "| Esportazione jpg | 30000 ms | 1 |" in md and "| Sessione del programma | 30 min 25 s | 2 |" in md
    assert "| seriale 7 (Anna Neri) | 1 | 16 |" in md and "mac 14.6.1" in md and "| installazione cccccccc | 1 | 1 |" in md
    assert "ZQX" not in md
    with open(tmp_path / "out" / "riepilogo.csv", encoding="utf-8", newline="") as f: r = list(csv.DictReader(f))
    assert [x["tester"] for x in r] == ["installazione cccccccc", "seriale 7", "seriale 8", "tutti"]
    assert (r[1]["intestatario"], r[1]["eventi"], r[1]["primo_spread_s"], r[1]["prima_esportazione_s"], r[1]["esportazioni_complete"]) == ("Anna Neri", "16", "130", "600", "1")
    assert (r[3]["eventi"], r[3]["operazioni"], r[3]["errori"], r[3]["sessioni"]) == ("25", "15", "2", "3")


def test_cartella_vuota_o_sbagliata(B, tmp_path, capsys):
    assert B.main([str(tmp_path / "manca")]) == 1 and "non è una cartella" in capsys.readouterr().err
    (tmp_path / "vuota").mkdir(); assert B.main([str(tmp_path / "vuota")]) == 0
    md = (tmp_path / "vuota" / "riepilogo.md").read_text(encoding="utf-8")
    assert "0 file, 0 eventi validi" in md and "Nessuna operazione." in md and "Nessun errore." in md and "dal — al —" in md
    assert B.durata(7300) == "2 h 01 min" and B.fmt(2.0) == "2" and B.fmt(None) == "—"


def test_legge_i_file_esportati_dal_programma(B, licenza, tmp_path, monkeypatch):
    """giro completo: il programma annota ed esporta, lo strumento legge senza scartare niente"""
    monkeypatch.setattr(invio, "INDIRIZZO", "")
    licenza.usa(licenza.chiavi.chiave(fascia="studio", flag=3, scadenza="2099-12-31", seriale=9))
    S.processo("editor"); S.imposta(True); S.album_aperto(10, 0, [30, 30], 300, 0.5); S.operazione("swap", 0.01); S.svuota()
    S.errore(KeyError("x")); S.chiusura()
    (tmp_path / "esportati").mkdir(); f = S.esporta(str(tmp_path / "esportati"))
    righe, scartate, file = B.leggi(str(tmp_path / "esportati"))
    assert scartate == 0 and file == 1 and len(righe) == len(open(f).read().splitlines()) and {B.chi(r) for r in righe} == {"seriale 9"}
