"""Beta privata e statistiche d'uso (T-204) in un Chrome vero: la riga «Beta privata · scade il …» nella schermata Album e
nell'editor, la domanda del consenso al primo avvio con la licenza beta («No, grazie» / «Sì, condividi», Esc la rimanda),
la finestra «Statistiche d'uso» (interruttore che ripassa dalla domanda, «Cosa condivido», nuovo codice, cancellazione),
nessun errore in console né blocco della CSP."""
import json
import shutil
import time

import pytest

from impaginatore import statistiche as S
from impaginatore.statistiche import invio

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]

VOCE = "[...document.querySelectorAll('#menu button')].find(b => b.textContent.startsWith(%s))"
VISTA = "getComputedStyle(document.getElementById('%s')).display"
DOMANDA = "getComputedStyle(document.getElementById('vstatc')).display === 'flex'"
CONFERMA = "getComputedStyle(document.getElementById('vchiedi')).display === 'flex' && !!document.querySelector('#ch-btns [data-esito=ok]')"


def aspetta(b, cond, secondi=10):
    """il valore della condizione (espressione JavaScript o funzione) appena è vera, o l'ultimo dopo `secondi`: la domanda
    arriva dopo licenza e stato delle statistiche, che la pagina chiede a parte; nessuna attesa fissa che dipende dalla macchina"""
    fine = time.time() + secondi
    while True:
        v = b.js(cond) if isinstance(cond, str) else cond()
        if v or time.time() > fine: return v
        b.pausa(0.1)


@pytest.fixture(autouse=True)
def senza_server(monkeypatch):
    monkeypatch.setattr(invio, "INDIRIZZO", "")


def beta(licenza, scadenza="2099-12-31"):
    licenza.usa(licenza.chiavi.chiave(fascia="studio", flag=3, scadenza=scadenza, seriale=7, intestatario="Anna Neri"))


def test_domanda_al_primo_avvio_e_impostazioni(home_srv, licenza, tmp_path, monkeypatch):
    from cdp import Browser
    beta(licenza)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1)
        assert aspetta(b, DOMANDA), "con la licenza beta la domanda compare al primo avvio"
        assert b.js("document.getElementById('lic').textContent") == "Beta privata · scade il 31/12/2099"
        assert b.js("document.getElementById('vstatc-t').textContent") == "Questa è una beta privata: ci aiuti a migliorarla condividendo come usi il programma?"
        testo = b.js("document.getElementById('vstatc-d').innerText")
        assert "Cosa non annota mai" in testo and "i nomi di file, cartelle, album e clienti" in testo and "numero di serie" in testo and "Esporta le statistiche…" in testo
        assert b.js("document.activeElement.id") == "sc-no" and b.js("document.getElementById('sc-si').className") == "", "due pulsanti di uguale peso"
        b.js("document.getElementById('vstatc').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))"); b.pausa(0.3)
        assert b.js(VISTA % "vstatc") == "none" and S.scelta() is None, "Esc rimanda la domanda: niente salvato"
        b.apri(home_srv.srv.indirizzo_avvio(), 1); assert aspetta(b, DOMANDA), "e la domanda torna all'avvio dopo"
        b.js("document.getElementById('sc-si').click()")
        assert aspetta(b, S.attive) and aspetta(b, "document.getElementById('avvtxt').textContent.includes('Grazie')") and b.js(VISTA % "vstatc") == "none"
        assert [json.loads(r)["ev"] for r in S._righe_grezze()][:2] == ["consenso", "avvio"]
        b.apri(home_srv.srv.indirizzo_avvio(), 1); assert aspetta(b, "typeof STAT !== 'undefined' && !!STAT && STAT.scelta === 'si'")
        assert b.js(VISTA % "vstatc") == "none", "scelta fatta: non si chiede più"
        assert aspetta(b, lambda: [json.loads(r)["ev"] for r in S._righe_grezze()][-1] == "finestra"), "la misura della finestra, con le statistiche accese"
        b.js("document.getElementById('altro').click()"); assert aspetta(b, (VOCE % "'Statistiche d'") + " != null")
        b.js((VOCE % "'Statistiche d'") + ".click()")
        assert aspetta(b, "document.getElementById('sinfo').textContent.includes('eventi nel registro')") and b.js(VISTA % "vstat") == "flex"
        info = b.js("document.getElementById('sinfo').textContent")
        assert b.js("document.getElementById('sint').checked") is True and "Numero di serie della licenza beta: 7" in info and "Invio: nessuno." in info
        b.js("document.getElementById('sregb').click()")
        assert aspetta(b, "document.getElementById('sregt').value.includes('\"ev\":\"consenso\"')") and b.js(VISTA % "vsreg") == "flex"
        assert aspetta(b, "document.getElementById('sregi').textContent.startsWith('Il registro è nella cartella')")
        b.js("document.getElementById('sregc').click()")
        tutte = S.righe; monkeypatch.setattr(S, "righe", lambda: tutte(1))                   # un registro più lungo di quello che la finestra mostra
        b.js("document.getElementById('sregb').click()")
        assert aspetta(b, "document.getElementById('sregi').textContent.startsWith(%s)" % json.dumps(f"L'ultima riga di {S.stato()['eventi']}.")), "il registro è più lungo: lo dice, al singolare"
        b.js("document.getElementById('sregc').click()"); monkeypatch.setattr(S, "righe", tutte)
        vecchio = S.identificativo()
        b.js("document.getElementById('sazz').click()"); assert aspetta(b, CONFERMA); b.js("document.querySelector('#ch-btns [data-esito=ok]').click()")
        assert aspetta(b, lambda: S.identificativo() != vecchio) and aspetta(b, "document.getElementById('sinfo').textContent.includes(%s)" % json.dumps(S.identificativo()))
        b.js("document.getElementById('scanc').click()"); assert aspetta(b, CONFERMA); b.js("document.querySelector('#ch-btns [data-esito=ok]').click()")
        assert aspetta(b, "document.getElementById('sinfo').textContent.includes('Il registro è vuoto.')") and S.stato()["eventi"] == 0 and b.js("document.getElementById('sesp').disabled") is True
        b.js("(() => { const i = document.getElementById('sint'); i.checked = false; i.dispatchEvent(new Event('change')); })()")
        assert aspetta(b, "document.getElementById('sinfo').textContent.includes('Spente')") and not S.attive()
        b.js("(() => { const i = document.getElementById('sint'); i.checked = true; i.dispatchEvent(new Event('change')); })()")
        assert aspetta(b, DOMANDA), "riaccenderle ripassa dalla domanda"
        b.js("document.getElementById('sc-no').click()")
        assert aspetta(b, lambda: S.scelta() == "no") and not S.attive() and aspetta(b, "document.getElementById('sint').checked === false")
        b.js("document.getElementById('sclose').click()")
        assert not b.problemi(), b.problemi()


def test_senza_licenza_beta_niente_domanda_ne_voce(home_srv, tmp_path):
    from cdp import Browser
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1)
        assert aspetta(b, "document.getElementById('lic').textContent === 'Licenza Studio'") and b.js(VISTA % "vstatc") == "none"
        b.js("document.getElementById('altro').click()"); b.pausa(0.2)
        assert b.js(VOCE % "'Statistiche d'") is None
        assert not b.problemi(), b.problemi()
    import os
    assert not os.path.exists(S.cartella())


def test_editor_mostra_la_beta(editor, licenza, tmp_path):
    from cdp import Browser
    beta(licenza)
    with Browser(tmp_path) as b:
        b.apri(editor.srv.indirizzo_avvio(), 1)
        assert aspetta(b, "document.getElementById('licb').textContent === 'Beta privata · scade il 31/12/2099'") and b.js("document.getElementById('licb').hidden") is False
        assert not b.problemi(), b.problemi()
