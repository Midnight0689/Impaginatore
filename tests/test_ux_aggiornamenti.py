"""Aggiornamenti nella schermata Album (T-207), provati in un Chrome vero: avviso discreto di una versione nuova con le
novità («Aggiorna e riavvia», «Più tardi» per questa sessione), annuncio dopo il riavvio, interruttore del controllo
automatico nella finestra della versione, piede con nome e versione."""

import pytest
from cdp import CHROME, HOME

from impaginatore import __version__, aggiornamenti

pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]


class Finti(aggiornamenti.Aggiornamenti):
    def __init__(self):
        self.aggiornati = 0
        self.s = dict(da_aggiornare=True, novita=["Esportazione più veloce", "<img src=x onerror=alert(1)>"], controllato=1, errore="", disponibile=True, motivo=None,
                      attuale=dict(n="2.0.0", codice="", data="", titolo="versione installata", rel=""),
                      ultima=dict(n="2.0.1", codice="", data="2026-12-01", titolo="versione firmata", rel=""), precedente=None, scartata=False,
                      annuncio=dict(tipo="aggiornato", versione="2.0.0", id="a1"))

    def stato(self): return dict(self.s)

    def controlla(self): return self.stato()

    def versioni(self, k=20): return []

    def aggiorna(self): self.aggiornati += 1; return True


def test_avviso_annuncio_e_controllo_automatico(home_srv, tmp_path, monkeypatch):
    from cdp import Browser
    a = Finti(); monkeypatch.setattr(home_srv.modulo, "AGGIORNAMENTI", a)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), HOME); b.attendi("!document.getElementById('aggav').hidden")
        assert b.js("document.getElementById('credit').textContent") == f"Impaginatore v{__version__}"
        assert b.js("document.getElementById('aggav').hidden") is False and b.js("document.getElementById('aggav-t').textContent") == "È disponibile Impaginatore 2.0.1"
        assert b.js("[...document.querySelectorAll('#aggav-l li')].map(l => l.textContent).join('|')") == "Esportazione più veloce|<img src=x onerror=alert(1)>", "le novità come testo"
        assert b.js("document.querySelectorAll('#aggav img').length") == 0
        assert b.js("document.getElementById('aggav-ok').textContent") == "Aggiorna e riavvia" and b.js("document.getElementById('aggav-dopo').textContent") == "Più tardi"
        assert b.js("document.getElementById('avvtxt').textContent") == "Impaginatore aggiornato alla versione 2.0.0." and b.js("document.getElementById('avviso').className") == "ok"
        b.js("document.getElementById('aggav-dopo').click()")
        assert b.js("document.getElementById('aggav').hidden") is True
        b.js("document.getElementById('avvchiudi').click()")
        b.apri(home_srv.srv.indirizzo_avvio(), HOME)                     # con la rete ferma: lo stato degli aggiornamenti è arrivato
        assert b.js("document.getElementById('aggav').hidden") is True, "«Più tardi» vale per questa sessione"
        assert b.js("getComputedStyle(document.getElementById('avviso')).display") == "none", "l'annuncio si mostra una volta"
        # finestra della versione: interruttore del controllo automatico
        b.js("document.getElementById('verb').click()"); b.attendi_rete()
        assert b.js("document.getElementById('vautor').hidden") is False and b.js("document.getElementById('vauto').checked") is True
        assert b.js("document.getElementById('vautor').textContent") == "Controlla da solo se ci sono versioni nuove"
        b.js("document.getElementById('vauto').click()"); b.attendi_che(lambda: aggiornamenti.automatico() is False); b.attendi_rete()
        assert b.js("document.getElementById('vauto').checked") is False
        b.js("document.getElementById('vclose').click()")
        # un'altra versione nuova: l'avviso torna; «Aggiorna e riavvia» aggiorna senza altre domande
        a.s.update(ultima=dict(a.s["ultima"], n="2.0.2"), annuncio=None, scartata=False)
        b.apri(home_srv.srv.indirizzo_avvio(), HOME); b.attendi("!document.getElementById('aggav').hidden")
        assert b.js("document.getElementById('aggav').hidden") is False and b.js("document.getElementById('aggav-t').textContent") == "È disponibile Impaginatore 2.0.2"
        assert b.js("document.getElementById('vauto').checked") is False
        b.js("document.getElementById('aggav-ok').click()"); b.attendi_che(lambda: a.aggiornati == 1)
        assert not b.problemi(), b.problemi()
    a.s.update(scartata=True); (tmp_path / "di-nuovo").mkdir()
    with Browser(tmp_path / "di-nuovo") as b:                   # un'altra sessione del browser: «Più tardi» non vale più
        b.apri(home_srv.srv.indirizzo_avvio(), HOME)                     # con la rete ferma: lo stato degli aggiornamenti è arrivato
        assert b.js("document.getElementById('aggav').hidden") is True, "la versione da cui l'utente è tornato indietro non si ripropone nell'avviso"


def test_programma_compilato_scarica_dalla_pagina(home_srv, tmp_path, monkeypatch):
    """T-302: il programma compilato si aggiorna a mano. L'avviso e la finestra della versione dicono «Scarica la versione
    nuova»; il pulsante fa aprire la pagina (al server) e dice cosa fare, senza attese né riavvio"""
    from cdp import Browser

    class Compilato(Finti):
        def aggiorna(self): self.aggiornati += 1; return dict(pagina="https://github.com/x/y/releases/tag/v2.0.1", versione="2.0.1")

    a = Compilato(); a.s.update(manuale=True, annuncio=None); monkeypatch.setattr(home_srv.modulo, "AGGIORNAMENTI", a)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), HOME); b.attendi("!document.getElementById('aggav').hidden")
        assert b.js("document.getElementById('aggav-ok').textContent") == "Scarica la versione nuova"
        assert b.js("document.getElementById('aggav-n').textContent").startswith("Si apre la pagina dei download")
        b.js("document.getElementById('aggav-ok').click()")
        b.attendi("document.getElementById('avvtxt').textContent", lambda t: t.startswith("Nel browser si è aperta la pagina di Impaginatore 2.0.1"))
        assert a.aggiornati == 1
        assert b.js("getComputedStyle(document.getElementById('vwait')).display") == "none" and b.js("document.getElementById('aggav') !== null"), "nessuna attesa né schermata finale: il programma non si riavvia"
        b.js("document.getElementById('verb').click()")
        b.attendi("document.getElementById('vgo').textContent", lambda t: t == "Scarica la versione nuova")
        b.js("document.getElementById('vgo').click()")
        assert b.attendi_che(lambda: a.aggiornati == 2), "dalla finestra della versione senza la domanda sul riavvio"
        assert not b.problemi(), b.problemi()
