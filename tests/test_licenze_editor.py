"""Licenze nell'editor e nella schermata dei progetti (T-202): sola lettura, funzioni della fascia, filigrana della prova,
attivazione dalla schermata. Editor e schermata girano in questo processo (conftest), con la coppia di firma della sessione."""
import json
import os
import time

import pytest
from cdp import CHROME
from aiuti import attendi_log
from impaginatore import licenze
from impaginatore.piattaforma import dialoghi

GIORNO = 86400


class Finti(dialoghi.Dialoghi):
    def __init__(self, *risposte): self.risposte = list(risposte)

    def _scegli(self, tipo, messaggio): return [self.risposte.pop(0)] if self.risposte else []


def _spread(c):
    nomi = [p["n"] for p in c.get("/api/state")["photos"]]
    return c.post("/api/op", dict(op="newspreadsel", names=nomi[:3], pos=0))


def _prova_finita(licenza, monkeypatch):
    """nessuna chiave e prova gratuita finita da un giorno"""
    licenza.usa(None); licenze.stato()
    monkeypatch.setattr(licenze, "orologio", lambda: time.time() + 31 * GIORNO)


def test_sola_lettura_nell_editor(editor, licenza, monkeypatch, tmp_path):
    c = editor; st = _spread(c)
    _prova_finita(licenza, monkeypatch)
    ok, r = c.prova("/api/op", dict(op="newspreadsel", names=[p["n"] for p in st["photos"]][3:5], pos=1))
    assert not ok and r["licenza"] is True and r["errore"].startswith("Impaginatore è in sola lettura. La prova gratuita è finita")
    assert c.codice("/api/op", {"op": "delete", "s": 0}) == 403 and c.codice("/api/op", {"op": "undo"}) == 403
    assert len(c.get("/api/state")["spreads"]) == 1, "lo stato non cambia"
    it = [i for i in st["spreads"][0]["items"] if i["k"] != "t"][0]
    assert c.codice("/api/op", {"op": "copia", "s": 0, "ats": [[it["side"], it["idx"]]]}) == 200, "copiare negli appunti non modifica il progetto"
    assert c.codice("/api/save", {}) == 200, "il lavoro fatto si salva sempre"
    for fmt in ("jpg", "pdf", "psd"):
        ok, r = c.prova("/api/export", {"fmt": fmt, "range": "1", "res": "anteprima"})
        assert not ok and "sola lettura" in r["errore"] and r["licenza"]
    assert c.codice("/api/templates?s=0") == 200 and c.codice("/api/tono?s=0") == 403
    ok, r = c.prova("/api/import", {"paths": [os.path.join(c.progetto, "Foto")]})
    assert not ok and r["licenza"] and c.riavvii == [], "niente foto aggiunte in sola lettura"
    dest = tmp_path / "copia"; dest.mkdir(); dialoghi.imposta(Finti(str(dest)))
    out = c.post("/api/prj_esporta", {"foto": False})["cartella"]; dialoghi.imposta(None)
    assert os.path.dirname(out) == str(dest), "il progetto si esporta anche in sola lettura: non si perde niente"
    attendi_log(c)


def test_prova_esporta_con_la_filigrana(editor, licenza, monkeypatch):
    c = editor; _spread(c)
    chiamate = []; vera = licenze.applica_filigrana
    monkeypatch.setattr(licenze, "applica_filigrana", lambda im: chiamate.append(im.size) or vera(im))
    c.post("/api/export", {"fmt": "jpg", "range": "1", "res": "anteprima"}); L = attendi_log(c)
    assert "ESPORTATI 1 spread su 1" in L and chiamate == [], "con la licenza niente filigrana"
    licenza.usa(None)
    c.post("/api/export", {"fmt": "jpg", "range": "1", "res": "anteprima"}); L = attendi_log(c)
    assert "ESPORTATI 1 spread su 1" in L and len(chiamate) == 1
    c.post("/api/export", {"fmt": "pdf", "range": "1", "width": 600}); L = attendi_log(c)
    assert any(x.startswith("RISULTATO:") for x in L) and len(chiamate) == 2
    ok, r = c.prova("/api/export", {"fmt": "psd", "range": "1"})
    assert not ok and r["errore"] == "Il PSD a livelli non fa parte della prova gratuita: c'è nelle licenze Pro e Studio."


def test_funzioni_dell_essenziale(editor, licenza):
    c = editor; st = _spread(c)
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    assert c.codice("/api/tono?s=0") == 403 and c.codice("/api/tono_all") == 403
    foto = [i for i in st["spreads"][0]["items"] if i["k"] != "t"][0]["name"]
    ok, r = c.prova("/api/op", {"op": "tono_fix", "items": [{"photo": foto, "ev": 0.3}]})
    assert not ok and r["errore"] == "Il controllo del tono dell'album non fa parte della licenza Essenziale: c'è nelle licenze Pro e Studio."
    assert c.codice("/api/op", {"op": "tono_escl", "photo": foto}) == 403
    assert c.codice("/api/op", {"op": "ev", "photo": foto, "value": 0.3}) == 200, "le modifiche dell'editor ci sono tutte"
    ok, r = c.prova("/api/export", {"fmt": "psd", "range": "1"}); assert not ok and "Pro e Studio" in r["errore"]
    for i in range(5): c.post("/api/modelli", {"azione": "salva", "s": 0, "nome": f"M{i}"})
    ok, r = c.prova("/api/modelli", {"azione": "salva", "s": 0, "nome": "M5"})
    assert not ok and r["errore"].startswith("La licenza Essenziale comprende 5 modelli personali")
    primo = c.E.ut_load()[0]["id"]
    assert c.codice("/api/modelli", {"azione": "rinomina", "id": primo, "nome": "Primo"}) == 200
    licenza.usa(licenza.chiavi.studio)
    assert c.codice("/api/modelli", {"azione": "salva", "s": 0, "nome": "M5"}) == 200 and c.codice("/api/tono?s=0") == 200


def test_licenza_dalla_schermata_dei_progetti(home_srv, licenza):
    h = home_srv
    s = h.get("/api/licenza"); assert (s["stato"], s["fascia"]) == ("attiva", "studio")
    ok, r = h.prova("/api/licenza/attiva", {"chiave": "ciao"})
    assert not ok and r["errore"] == "Questa non è una chiave di Impaginatore: la chiave inizia con IMP1-."
    assert h.codice("/api/licenza/attiva", {}) == 400
    pro = licenza.chiavi.chiave(fascia="pro", seriale=4)
    s = h.post("/api/licenza/attiva", {"chiave": pro}); assert (s["stato"], s["fascia"], s["seriale"]) == ("attiva", "pro", 4)
    assert pro not in h.raw("/api/licenza").decode("utf-8"), "la chiave non torna alla pagina"
    s = h.post("/api/licenza/rimuovi", {}); assert s["stato"] == "prova" and not s["chiave_presente"]
    pagina = h.raw("/").decode("utf-8")
    assert 'id="lic"' in pagina and 'id="vlic"' in pagina and '"/api/licenza/attiva"' in pagina and "senza internet" in pagina


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_lucchetto_della_licenza_senza_blocchi_della_csp(editor, licenza, tmp_path):
    """Esporta › PSD nella prova: il pulsante ha il lucchetto, un file statico del programma che la CSP ammette (prima era
    un indirizzo data: che img-src 'self' bloccava)"""
    from cdp import Browser
    _spread(editor); licenza.usa(None)
    with Browser(tmp_path) as b:
        b.apri(editor.srv.indirizzo_avvio(), 2)
        b.js("openExp()"); b.js("document.querySelector('#efmt [data-f=psd]').click()"); b.pausa(1)
        assert b.js("document.getElementById('ego').classList.contains('lock')") and b.js("document.getElementById('ego').disabled")
        assert "/risorse/lucchetto.svg" in b.js("getComputedStyle(document.getElementById('ego'), '::after').maskImage")
        assert any(s == 200 and u.endswith("/risorse/lucchetto.svg") for s, u in b.risposte()), "l'icona si carica"
        assert b.violazioni_csp() == [] and not b.problemi(), b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_finestra_della_licenza_nel_browser(home_srv, licenza, tmp_path):
    from cdp import Browser
    licenza.usa(None)
    pro = licenza.chiavi.chiave(fascia="pro", intestatario="Studio Verdi", computer=2)
    testo = lambda id_: b.js(f"document.getElementById('{id_}').textContent")
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert testo("lic") == "Prova gratuita · 30 giorni"
        b.js("document.getElementById('lic').click()"); b.pausa(0.5)
        assert b.js("getComputedStyle(document.getElementById('vlic')).display") == "flex" and testo("lstato").startswith("Prova gratuita: mancano 30 giorni")
        b.js(f"document.getElementById('lkey').value = {json.dumps(pro.lower())}; document.getElementById('lgo').click()"); b.pausa(0.8)
        assert testo("lic") == "Licenza Pro" and "«Studio Verdi»" in testo("lstato") and b.js("document.getElementById('lkey').value") == ""
        b.js("document.getElementById('lrim').click()"); b.pausa(0.4)
        assert b.js("getComputedStyle(document.getElementById('vchiedi')).display") == "flex", "la conferma è un foglio in pagina, non un confirm()"
        b.js("document.querySelector('#vchiedi [data-esito=ok]').click()"); b.pausa(0.8)
        assert testo("lic").startswith("Prova gratuita") and b.js("document.getElementById('lrim').style.display") == "none"
        licenza.usa("IMP1-AAAAA"); b.js("loadLic()"); b.pausa(0.5)
        assert testo("lic") == "Chiave non valida · prova 30 giorni" and b.js("document.getElementById('lrim').style.display") == ""
        assert not b.problemi(), b.problemi()
