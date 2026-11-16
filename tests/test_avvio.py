"""Schermata di avvio della finestra del programma (T-207): logotipo della marca, versione, stato della licenza; si chiude
quando la schermata Album è pronta (pywebview finto: le finestre vere in tests/test_desktop.py e nella schermata salvata
in docs/prodotto/ux/schermate/2.0/)."""
import base64
import logging
import os
import re
import threading
import time
import types

import pytest

from impaginatore import __version__, licenze, risorse
from impaginatore.desktop import avvio

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("st, atteso", [
    (dict(stato="attiva", fascia="studio", nome_fascia="Studio", beta=False, sola_lettura=False), ("Licenza Studio", "attiva")),
    (dict(stato="attiva", fascia="pro", nome_fascia=None, sola_lettura=False), ("Licenza pro", "attiva")),
    (dict(stato="attiva", fascia="studio", nome_fascia="Studio", beta=True, sola_lettura=False), ("Licenza beta", "beta")),
    (dict(stato="attiva", fascia="beta", nome_fascia="Beta", sola_lettura=False), ("Licenza beta", "beta")),
    (dict(stato="prova", sola_lettura=False, prova=dict(giorni_rimasti=1)), ("Prova gratuita · 1 giorno", "prova")),
    (dict(stato="prova", sola_lettura=False, prova=dict(giorni_rimasti=12)), ("Prova gratuita · 12 giorni", "prova")),
    (dict(stato="non valida", sola_lettura=False, prova=dict(giorni_rimasti=3)), ("Prova gratuita · 3 giorni", "prova")),
    (dict(stato="prova", sola_lettura=False), ("Prova gratuita · 0 giorni", "prova")),
    (dict(stato="scaduta", sola_lettura=True, beta=True), ("Sola lettura", "sola")),
    (dict(stato="revocata", sola_lettura=True), ("Sola lettura", "sola")),
])
def test_riga_della_licenza(st, atteso):
    assert avvio.licenza(st) == atteso


def test_licenza_vera_e_illeggibile(monkeypatch, caplog):
    assert avvio.licenza() == ("Licenza Studio", "attiva"), "la licenza del test (fixture licenza)"
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    assert avvio.licenza() == ("Studio licence", "attiva") and avvio.licenza(dict(stato="prova", prova=dict(giorni_rimasti=1))) == ("Free trial · 1 day left", "prova")
    monkeypatch.setattr(licenze, "stato", lambda: 1 / 0)
    with caplog.at_level(logging.WARNING, logger="impaginatore.desktop"): assert avvio.licenza() == ("", "")
    assert "ZeroDivisionError" in caplog.text, "la schermata di avvio non ferma mai il programma"


def _tracciati(svg):
    return re.findall(r'<path[^>]* d="([^"]+)"', svg)


def test_pagina_della_schermata(monkeypatch):
    p = avvio.pagina(dict(stato="attiva", fascia="studio", nome_fascia="<b>Studio</b> & co", sola_lettura=False))
    font = base64.b64encode(risorse.leggi(avvio.FONT)).decode()
    assert p.startswith("<!DOCTYPE html>") and '<html lang="it">' in p and f"Versione {__version__}" in p and font in p
    assert "Licenza &lt;b&gt;Studio&lt;/b&gt; &amp; co" in p and "<b>Studio" not in p, "i testi entrano neutralizzati"
    resto = p.replace(font, "")
    assert "<script" not in resto.lower() and "default-src 'none'" in resto and "http" not in resto.replace("http-equiv", ""), "niente script, niente indirizzi esterni"
    assert not re.search(r"__[A-Z]+__", p) and 'class="licenza attiva"' in p and "prefers-reduced-motion" in p and "400ms" in p
    monkeypatch.setattr(licenze, "stato", lambda: 1 / 0)
    assert '<span class="licenza "></span>' in avvio.pagina(), "licenza illeggibile: la riga resta vuota (e nascosta)"
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    assert '<html lang="en">' in avvio.pagina() and f"Version {__version__}" in avvio.pagina()


def test_logotipo_della_marca():
    """i tracciati del logotipo sono quelli di brand/logo (in negativo, su Inchiostro): se il logo cambia, cambia anche qui"""
    with open(os.path.join(RADICE, "brand", "logo", "impaginatore-logotipo-negativo.svg"), encoding="utf-8") as f: marca = f.read()
    pagina = risorse.leggi("avvio.html").decode("utf-8")
    pagine, segni, parola = _tracciati(marca)
    su, giu = re.findall(r"M[^M]+", segni)
    assert _tracciati(pagina) == [pagine, su, giu, parola]
    assert re.findall(r'viewBox="([^"]+)"', pagina) == re.findall(r'viewBox="([^"]+)"', marca)
    colori = re.findall(r'fill="(#\w+)"', marca)
    assert re.findall(r'fill="(#\w+)"', pagina) == [colori[0], colori[1], colori[1], colori[2]] == ["#F6F3EC", "#7BCC9C", "#7BCC9C", "#F6F3EC"]
    assert avvio.FONDO == "#181715" and "--inchiostro: #181715" in pagina


class Finestre:
    """pywebview finto per la schermata di avvio"""

    def __init__(self): self.create, self.mostrate, self.chiuse = [], [], []

    def create_window(self, titolo, **kw):
        f = types.SimpleNamespace(titolo=titolo, kw=kw, events=types.SimpleNamespace(shown=Evento()), destroy=lambda: self.chiuse.append(time.monotonic()))
        self.create.append(f); return f


class Evento:
    def __init__(self): self.gestori = []

    def __iadd__(self, g): self.gestori.append(g); return self

    def __call__(self): [g() for g in self.gestori]


def test_finestra_e_tempi(monkeypatch):
    wv = Finestre(); m = types.SimpleNamespace(wv=wv)
    monkeypatch.setattr(avvio, "MINIMO", 0.3); monkeypatch.setattr(avvio, "MASSIMO", 5)
    a = avvio.Avvio(m); f = a.crea("Impaginatore")
    assert f.titolo == "Impaginatore" and f.kw["html"].startswith("<!DOCTYPE html>")
    assert {k: v for k, v in f.kw.items() if k != "html"} == dict(width=480, height=300, resizable=False, frameless=True, easy_drag=False, on_top=True, focus=False,
                                                                 background_color="#181715", text_select=False, zoomable=False)
    principale = types.SimpleNamespace(show=lambda: wv.mostrate.append(time.monotonic()))
    pronta = threading.Event(); pronta.set()
    t = a.segui(principale, pronta)
    time.sleep(0.05); f.events.shown()
    t.join(5)
    assert len(wv.mostrate) == 1 and len(wv.chiuse) == 1 and wv.mostrate[0] - a.visto >= 0.29, "almeno MINIMO secondi di schermata: niente lampi"
    assert wv.mostrate[0] <= wv.chiuse[0], "prima si mostra la finestra, poi si chiude la schermata"


def test_si_apre_anche_se_la_pagina_non_arriva(monkeypatch, caplog):
    wv = Finestre(); m = types.SimpleNamespace(wv=wv)
    monkeypatch.setattr(avvio, "MASSIMO", 0.2)
    a = avvio.Avvio(m); a.crea("Impaginatore")
    def rotta(): raise RuntimeError("finestra già chiusa")
    with caplog.at_level(logging.DEBUG, logger="impaginatore.desktop"):
        inizio = time.monotonic(); a.segui(types.SimpleNamespace(show=rotta), threading.Event()).join(5)
    assert 0.15 <= time.monotonic() - inizio < 3 and len(wv.chiuse) == 1 and "RuntimeError" in caplog.text, "dopo MASSIMO secondi si apre comunque; un errore non ferma niente"
