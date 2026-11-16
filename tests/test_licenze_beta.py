"""Licenza della beta privata: una chiave IMP1- con il segno «beta» (bit 1 del byte dei segni, che tutti i programmi 2.x
conoscono) e la scadenza (formato 2). Dà le funzioni della sua fascia (Studio per le chiavi di chiavi.py emetti-beta),
mostra «Beta privata · scade il …» nella schermata Album e nell'editor e, dopo la scadenza, va in sola lettura."""
import datetime as dt

import pytest

from impaginatore import licenze, lingua
from impaginatore.licenze import chiave as K

T0 = dt.datetime(2026, 11, 16, 12, 0).timestamp()


@pytest.fixture
def ora(monkeypatch):
    class Ora: t = T0
    o = Ora()
    monkeypatch.setattr(licenze, "orologio", lambda: o.t)
    return o


def beta(licenza, **k):
    campi = dict(fascia="studio", flag=K.FLAG_OMAGGIO | K.FLAG_BETA, scadenza="2027-01-31", seriale=12, intestatario="Anna Neri")
    campi.update(k); testo = licenza.chiavi.chiave(**campi); licenza.usa(testo); return testo


def test_beta_attiva_con_tutte_le_funzioni_fino_alla_scadenza(licenza, ora):
    beta(licenza); s = licenze.stato()
    assert (s["stato"], s["fascia"], s["beta"], s["omaggio"], s["sola_lettura"], s["filigrana"], s["scade"], s["seriale"]) == ("attiva", "studio", True, True, False, False, "2027-01-31", 12)
    assert s["funzioni"] == licenze.funzioni_di("studio")
    assert s["etichetta_beta"] == "Beta privata" and s["riga_beta"] == "Beta privata · scade il 31/01/2027"
    assert s["messaggio"] == ("Beta privata, intestata a «Anna Neri»: hai le funzioni della licenza Studio fino al 31/01/2027 compreso. "
                              "Dopo, gli album restano apribili in sola lettura: il lavoro fatto non si perde.")
    ora.t = dt.datetime(2027, 1, 31, 23, 0).timestamp(); assert licenze.stato()["stato"] == "attiva", "l'ultimo giorno compreso"


def test_beta_finita_in_sola_lettura(licenza, ora):
    beta(licenza); ora.t = dt.datetime(2027, 2, 1, 9, 0).timestamp(); s = licenze.stato()
    assert (s["stato"], s["sola_lettura"], s["beta"]) == ("scaduta", True, True) and s["funzioni"] == licenze.funzioni_sola_lettura()
    assert s["riga_beta"] == "Beta privata · finita il 31/01/2027"
    assert s["messaggio"] == (f"La beta privata intestata a «Anna Neri» è finita il 31/01/2027. {licenze.msg_sola_lettura()} "
                              "Grazie per averla provata: per continuare a lavorare serve una licenza.")
    assert licenze.motivo("export_jpg", s).startswith("Impaginatore è in sola lettura. La beta privata")
    with pytest.raises(K.ChiaveNonValida, match="è finita"): licenze.attiva(licenza.chiavi.chiave(fascia="studio", flag=3, scadenza="2027-01-31"))


def test_beta_senza_intestatario_senza_scadenza_e_altri_casi(licenza, ora, monkeypatch):
    beta(licenza, intestatario="", scadenza=None); s = licenze.stato()
    assert s["messaggio"] == "Beta privata: hai le funzioni della licenza Studio." and s["riga_beta"] == "Beta privata" and s["scade"] is None
    beta(licenza, intestatario=""); ora.t = dt.datetime(2027, 3, 1).timestamp()
    assert licenze.stato()["messaggio"].startswith("La beta privata è finita il 31/01/2027.")
    ora.t = T0; monkeypatch.setattr(licenze, "revocate", lambda: frozenset({12}))
    s = licenze.stato(); assert s["stato"] == "revocata" and s["riga_beta"] == "Beta privata", "revocata: l'etichetta, senza date"
    monkeypatch.setattr(licenze, "revocate", lambda: frozenset())
    beta(licenza, versione=3); s = licenze.stato()
    assert s["stato"] == "non valida" and s["beta"] and s["riga_beta"] is None, "una beta di un'altra versione non si presenta come beta"
    licenza.usa(licenza.chiavi.studio); s = licenze.stato(); assert not s["beta"] and s["etichetta_beta"] is None and s["riga_beta"] is None


def test_beta_in_inglese(licenza, ora, monkeypatch):
    beta(licenza); monkeypatch.setattr(lingua, "attuale", lambda: "en")
    s = licenze.stato()
    assert s["riga_beta"] == "Private beta · expires on 31/01/2027" and s["etichetta_beta"] == "Private beta"
    assert s["messaggio"].startswith("Private beta, registered to “Anna Neri”: you have the features of the Studio licence until 31/01/2027 inclusive.")
    ora.t = dt.datetime(2027, 2, 1).timestamp(); assert licenze.stato()["riga_beta"] == "Private beta · ended on 31/01/2027"


def test_inizio_della_prova(licenza, ora):
    assert licenze.inizio_prova() is None, "non fa partire la prova"
    licenze.stato(); assert licenze.inizio_prova() == T0


def test_schermata_ed_editor_mostrano_la_beta(home_srv, editor, licenza):
    beta(licenza, scadenza="2099-12-31")
    s = home_srv.get("/api/licenza"); assert s["beta"] and s["riga_beta"] == "Beta privata · scade il 31/12/2099"
    L = editor.get("/api/state")["licenza"]; assert L["beta"] is True and L["riga_beta"] == "Beta privata · scade il 31/12/2099"
    licenza.usa(licenza.chiavi.studio); L = editor.get("/api/state")["licenza"]; assert L["beta"] is False and L["riga_beta"] is None
