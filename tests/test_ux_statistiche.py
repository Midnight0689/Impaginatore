"""Beta privata e statistiche d'uso (T-204) in un Chrome vero: la riga «Beta privata · scade il …» nella schermata Album e
nell'editor, la domanda del consenso al primo avvio con la licenza beta («No, grazie» / «Sì, condividi», Esc la rimanda),
la finestra «Statistiche d'uso» (interruttore che ripassa dalla domanda, «Cosa condivido», nuovo codice, cancellazione),
nessun errore in console né blocco della CSP."""
import json
import shutil

import pytest

from impaginatore import statistiche as S
from impaginatore.statistiche import invio

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]

VOCE = "[...document.querySelectorAll('#menu button')].find(b => b.textContent.startsWith(%s))"
VISTA = "getComputedStyle(document.getElementById('%s')).display"


@pytest.fixture(autouse=True)
def senza_server(monkeypatch):
    monkeypatch.setattr(invio, "INDIRIZZO", "")


def beta(licenza, scadenza="2099-12-31"):
    licenza.usa(licenza.chiavi.chiave(fascia="studio", flag=3, scadenza=scadenza, seriale=7, intestatario="Anna Neri"))


def test_domanda_al_primo_avvio_e_impostazioni(home_srv, licenza, tmp_path):
    from cdp import Browser
    beta(licenza)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert b.js("document.getElementById('lic').textContent") == "Beta privata · scade il 31/12/2099"
        assert b.js(VISTA % "vstatc") == "flex", "con la licenza beta la domanda compare al primo avvio"
        assert b.js("document.getElementById('vstatc-t').textContent") == "Questa è una beta privata: ci aiuti a migliorarla condividendo come usi il programma?"
        testo = b.js("document.getElementById('vstatc-d').innerText")
        assert "Cosa non annota mai" in testo and "i nomi di file, cartelle, album e clienti" in testo and "numero di serie" in testo and "Esporta le statistiche…" in testo
        assert b.js("document.activeElement.id") == "sc-no" and b.js("document.getElementById('sc-si').className") == "", "due pulsanti di uguale peso"
        b.js("document.getElementById('vstatc').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))"); b.pausa(0.3)
        assert b.js(VISTA % "vstatc") == "none" and S.scelta() is None, "Esc rimanda la domanda: niente salvato"
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5); assert b.js(VISTA % "vstatc") == "flex", "e la domanda torna all'avvio dopo"
        b.js("document.getElementById('sc-si').click()"); b.pausa(0.6)
        assert S.attive() and b.js(VISTA % "vstatc") == "none" and "Grazie" in b.js("document.getElementById('avvtxt').textContent")
        assert [json.loads(r)["ev"] for r in S._righe_grezze()][:2] == ["consenso", "avvio"]
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5); assert b.js(VISTA % "vstatc") == "none", "scelta fatta: non si chiede più"
        assert [json.loads(r)["ev"] for r in S._righe_grezze()][-1] == "finestra", "la misura della finestra, con le statistiche accese"
        b.js("document.getElementById('altro').click()"); b.pausa(0.2)
        b.js((VOCE % "'Statistiche d'") + ".click()"); b.pausa(0.5)
        assert b.js(VISTA % "vstat") == "flex" and b.js("document.getElementById('sint').checked") is True
        info = b.js("document.getElementById('sinfo').textContent")
        assert "eventi nel registro" in info and "Numero di serie della licenza beta: 7" in info and "Invio: nessuno." in info
        b.js("document.getElementById('sregb').click()"); b.pausa(0.5)
        assert b.js(VISTA % "vsreg") == "flex" and '"ev":"consenso"' in b.js("document.getElementById('sregt').value")
        assert "Il registro è nella cartella" in b.js("document.getElementById('sregi').textContent")
        b.js("document.getElementById('sregc').click()")
        vecchio = S.identificativo()
        b.js("document.getElementById('sazz').click()"); b.pausa(0.3); b.js("document.querySelector('#ch-btns [data-esito=ok]').click()"); b.pausa(0.5)
        assert S.identificativo() != vecchio and S.identificativo() in b.js("document.getElementById('sinfo').textContent")
        b.js("document.getElementById('scanc').click()"); b.pausa(0.3); b.js("document.querySelector('#ch-btns [data-esito=ok]').click()"); b.pausa(0.5)
        assert S.stato()["eventi"] == 0 and b.js("document.getElementById('sesp').disabled") is True and "Il registro è vuoto." in b.js("document.getElementById('sinfo').textContent")
        b.js("(() => { const i = document.getElementById('sint'); i.checked = false; i.dispatchEvent(new Event('change')); })()"); b.pausa(0.5)
        assert not S.attive() and "Spente" in b.js("document.getElementById('sinfo').textContent")
        b.js("(() => { const i = document.getElementById('sint'); i.checked = true; i.dispatchEvent(new Event('change')); })()"); b.pausa(0.4)
        assert b.js(VISTA % "vstatc") == "flex", "riaccenderle ripassa dalla domanda"
        b.js("document.getElementById('sc-no').click()"); b.pausa(0.4)
        assert not S.attive() and b.js("document.getElementById('sint').checked") is False
        b.js("document.getElementById('sclose').click()")
        assert not b.problemi(), b.problemi()


def test_senza_licenza_beta_niente_domanda_ne_voce(home_srv, tmp_path):
    from cdp import Browser
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert b.js(VISTA % "vstatc") == "none" and b.js("document.getElementById('lic').textContent") == "Licenza Studio"
        b.js("document.getElementById('altro').click()"); b.pausa(0.2)
        assert b.js(VOCE % "'Statistiche d'") is None
        assert not b.problemi(), b.problemi()
    import os
    assert not os.path.exists(S.cartella())


def test_editor_mostra_la_beta(editor, licenza, tmp_path):
    from cdp import Browser
    beta(licenza)
    with Browser(tmp_path) as b:
        b.apri(editor.srv.indirizzo_avvio(), 2)
        assert b.js("document.getElementById('licb').hidden") is False and b.js("document.getElementById('licb').textContent") == "Beta privata · scade il 31/12/2099"
        assert not b.problemi(), b.problemi()
