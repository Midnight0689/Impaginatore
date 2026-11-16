"""Lingua nella schermata Album (T-206), provata in un Chrome vero: si sceglie dal menu ⋯ › Lingua…, la pagina si ricarica
nella lingua nuova (testi, numeri, attributo lang) e la scelta resta per tutto il programma; l'interruttore delle immagini
dell'assistente c'è solo se la licenza comprende l'assistente, altrimenti la finestra dice perché."""
import json
import shutil

import pytest

from impaginatore import __version__, lingua

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]

VOCE = "[...document.querySelectorAll('#menu button')].find(b => b.textContent.startsWith(%s))"


def mostra(b, id_):
    return b.js(f"getComputedStyle(document.getElementById('{id_}')).display")


def test_lingua_si_sceglie_nella_schermata(home_srv, tmp_path):
    from cdp import Browser
    home_srv.post("/api/nuovo", {"nome": "Mezzo", "w": "60", "h": "22,5"})
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert b.js("document.documentElement.lang") == "it" and b.js("document.querySelector('#grid .riga .c-fm').textContent") == "60 × 22,5"
        assert b.js("document.getElementById('credit').textContent") == f"Impaginatore v{__version__}", "nel piede solo nome e versione (T-207)"
        b.js("document.getElementById('altro').click()"); b.pausa(0.2)
        b.js(VOCE % "'Lingua'" + ".click()"); b.pausa(0.4)
        assert mostra(b, "vlingua") == "flex"
        assert b.js("[...document.querySelectorAll('#lingue label')].map(l => l.textContent + ':' + l.querySelector('input').checked + ':' + l.querySelector('span').lang).join('|')") \
            == "Italiano:true:it|English:false:en"
        assert b.js("document.activeElement.value") == "it", "il fuoco sulla lingua in uso"
        b.js("document.querySelector('#lingue input[value=en]').click()"); b.pausa(2)
        assert b.js("document.documentElement.lang") == "en" and lingua.attuale() == "en"
        assert b.js("document.getElementById('titolo-album').textContent") == "Albums"
        assert b.js("document.getElementById('credit').textContent") == f"Impaginatore v{__version__}"
        assert b.js("document.querySelector('#grid .riga .c-fm').textContent") == "60 × 22.5", "numeri con il punto in inglese"
        b.js("document.getElementById('bnuovo').click()"); b.pausa(0.3)
        assert b.js("document.getElementById('h').value") == "22.5" and b.js("document.getElementById('spazio').value") == "2.5"
        assert "editor." not in b.js("document.body.innerText") and "home." not in b.js("document.body.innerText")
        assert not b.problemi(), b.problemi()
    with open(lingua.percorso(), encoding="utf-8") as f: assert json.load(f)["lingua"] == "en"


def test_assistente_senza_licenza_che_lo_comprende(home_srv, licenza, tmp_path):
    """Essenziale: niente interruttore; la finestra dice in quali licenze c'è l'assistente"""
    from cdp import Browser
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        b.js("document.getElementById('altro').click()"); b.pausa(0.2)
        b.js(VOCE % "'Assistente AI'" + ".click()"); b.pausa(0.4)
        assert mostra(b, "vassist") == "flex" and mostra(b, "aimgr") == "none" and mostra(b, "anota") == "none"
        assert "Pro" in b.js("document.getElementById('amotivo').textContent") and mostra(b, "amotivo") != "none"
        assert b.js("document.activeElement.id") == "aclose"
        assert not b.problemi(), b.problemi()
