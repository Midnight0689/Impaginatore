"""Lingua nella schermata Album (T-206), provata in un Chrome vero: si sceglie dal menu ⋯ › Lingua…, la pagina si ricarica
nella lingua nuova (testi, numeri, attributo lang) e la scelta resta per tutto il programma; l'interruttore delle immagini
dell'assistente c'è solo se la licenza comprende l'assistente, altrimenti la finestra dice perché."""
import json

import pytest
from cdp import CHROME, HOME

from impaginatore import __version__, lingua

pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]

VOCE = "[...document.querySelectorAll('#menu button')].find(b => b.textContent.startsWith(%s))"


def mostra(b, id_):
    return b.js(f"getComputedStyle(document.getElementById('{id_}')).display")


def test_lingua_si_sceglie_nella_schermata(home_srv, tmp_path):
    from cdp import Browser
    home_srv.post("/api/nuovo", {"nome": "Mezzo", "w": "60", "h": "22,5"})
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), HOME)
        assert b.js("document.documentElement.lang") == "it" and b.js("document.querySelector('#grid .riga .c-fm').textContent") == "60 × 22,5"
        assert b.js("document.getElementById('credit').textContent") == f"Impaginatore v{__version__}", "nel piede solo nome e versione (T-207)"
        b.js("document.getElementById('altro').click()")
        b.js(VOCE % "'Lingua'" + ".click()"); b.attendi("getComputedStyle(document.getElementById('vlingua')).display === 'flex'")
        assert b.js("[...document.querySelectorAll('#lingue label')].map(l => l.textContent + ':' + l.querySelector('input').checked + ':' + l.querySelector('span').lang).join('|')") \
            == "Italiano:true:it|English:false:en"
        assert b.js("document.activeElement.value") == "it", "il fuoco sulla lingua in uso"
        b.segna(); b.js("document.querySelector('#lingue input[value=en]').click()"); b.attendi_pagina(HOME)     # la pagina si ricarica in inglese
        assert b.js("document.documentElement.lang") == "en" and lingua.attuale() == "en"
        assert b.js("document.getElementById('titolo-album').textContent") == "Albums"
        assert b.js("document.getElementById('credit').textContent") == f"Impaginatore v{__version__}"
        assert b.js("document.querySelector('#grid .riga .c-fm').textContent") == "60 × 22.5", "numeri con il punto in inglese"
        b.js("document.getElementById('bnuovo').click()")
        b.attendi("[document.getElementById('h').value, document.getElementById('spazio').value]", lambda v: v == ["22.5", "2.5"])
        assert "editor." not in b.js("document.body.innerText") and "home." not in b.js("document.body.innerText")
        assert not b.problemi(), b.problemi()
    with open(lingua.percorso(), encoding="utf-8") as f: assert json.load(f)["lingua"] == "en"


def test_assistente_senza_licenza_che_lo_comprende(home_srv, licenza, tmp_path):
    """Essenziale: niente interruttore; la finestra dice in quali licenze c'è l'assistente"""
    from cdp import Browser
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), HOME)
        b.js("document.getElementById('altro').click()")
        b.js(VOCE % "'Assistente AI'" + ".click()"); b.attendi("getComputedStyle(document.getElementById('vassist')).display === 'flex'")
        assert mostra(b, "aimgr") == "none" and mostra(b, "anota") == "none"
        assert "Pro" in b.js("document.getElementById('amotivo').textContent") and mostra(b, "amotivo") != "none"
        assert b.js("document.activeElement.id") == "aclose"
        assert not b.problemi(), b.problemi()
