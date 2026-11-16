"""Schermata «Album» a scaffale (UX-022, UX-008, UX-019 in T-205), provata in un Chrome vero: elenco e stati, ricerca oltre i 12 album,
fogli di conferma in pagina (Cestino, Chiudi programma), Invio e doppio clic, stato vuoto, riga della prova, tema, nessun errore in console
né blocco della CSP."""
import json
import os
import shutil
import time

import pytest

from impaginatore import licenze
from impaginatore.piattaforma import azioni

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]

GIORNO = 86400
VOCE = "[...document.querySelectorAll('#menu button')].find(b => b.textContent.startsWith(%s))"
ESC = "document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))"


def crea(h, n, prefisso="Album"):
    return [h.post("/api/nuovo", {"nome": f"{prefisso} {i:02d}", "w": 30, "h": 30})["path"] for i in range(1, n + 1)]


def righe(b):
    return b.js("[...document.querySelectorAll('#grid .riga .nome')].map(e => e.textContent)")


def mostra(b, id_):
    return b.js(f"getComputedStyle(document.getElementById('{id_}')).display")


def test_elenco_con_stati_e_colonne(home_srv, tmp_path):
    from cdp import Browser
    p = crea(home_srv, 2)
    os.makedirs(os.path.join(p[1], "Foto"), exist_ok=True)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert b.js("document.documentElement.dataset.theme") == "dark" and sorted(righe(b)) == ["Album 01", "Album 02"]
        r = b.js("[...document.querySelectorAll('#grid .riga')].map(r => r.innerText.replace(/\\s+/g, ' '))")
        assert all("Senza foto" in x and "30 × 30" in x for x in r), r
        assert b.js("getComputedStyle(document.querySelector('#grid .riga')).height") == "80px" and b.js("getComputedStyle(document.querySelector('.barra')).height") == "52px"
        assert b.js("getComputedStyle(document.querySelector('.riga .nome')).fontFamily").startswith("Newsreader")
        assert b.js("getComputedStyle(document.querySelector('.riga .num')).fontFamily").startswith('"IBM Plex Mono"')
        assert b.js("document.getElementById('cerca').hidden") is True, "la ricerca compare oltre i 12 album"
        assert b.js("document.getElementById('where').textContent").startswith("I nuovi album vengono salvati in: ")
        assert not b.problemi(), b.problemi()


def test_ricerca_oltre_dodici_album(home_srv, tmp_path):
    from cdp import Browser
    crea(home_srv, 12)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert b.js("document.getElementById('cerca').hidden") is True
        crea(home_srv, 1, "Sposi"); b.js("load()"); b.pausa(0.5)
        assert b.js("document.getElementById('cerca').hidden") is False and len(righe(b)) == 13
        b.js("(() => { const c = document.getElementById('cerca'); c.value = 'sposi'; c.dispatchEvent(new Event('input')); })()")
        assert righe(b) == ["Sposi 01"], "filtra per nome, senza badare alle maiuscole"
        b.js("(() => { const c = document.getElementById('cerca'); c.value = 'zzz'; c.dispatchEvent(new Event('input')); })()")
        assert righe(b) == [] and b.js("document.getElementById('nessuno').hidden") is False
        assert not b.problemi(), b.problemi()


def test_invio_e_doppio_clic_aprono(home_srv, tmp_path):
    from cdp import Browser
    crea(home_srv, 2)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        b.js("window.aperti = []; openProject = p => window.aperti.push(p.nome)")
        b.js("(() => { const r = document.querySelector('#grid .riga'); r.focus(); r.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); })()")
        b.js("document.querySelectorAll('#grid .riga')[1].dispatchEvent(new MouseEvent('dblclick', { bubbles: true }))")
        b.js("document.querySelector('#grid .riga [data-a=apri]').click()")
        assert len(b.js("window.aperti")) == 3
        assert b.js("document.querySelector('#grid .riga').getAttribute('tabindex')") == "0", "ogni riga si raggiunge con Tab"
        assert not b.problemi(), b.problemi()


def test_cestino_chiede_in_pagina(home_srv, tmp_path, monkeypatch):
    from cdp import Browser
    cestinati = []
    monkeypatch.setattr(azioni, "cestina", lambda p: (cestinati.append(p), shutil.rmtree(p)))
    p = crea(home_srv, 1)[0]
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        b.js("window.confirm = () => { window.usato = 'confirm'; return true; }; window.alert = () => { window.usato = 'alert'; }")
        b.js("document.querySelector('#grid .riga [data-a=altro]').click()"); b.pausa(0.3)
        assert b.js("getComputedStyle(document.getElementById('menu')).display") == "block"
        b.js(VOCE % "'Metti nel Cestino'" + ".click()"); b.pausa(0.3)
        assert mostra(b, "vchiedi") == "flex" and "Album 01" in b.js("document.getElementById('ch-titolo').textContent")
        assert b.js("document.activeElement.dataset.esito") == "annulla", "il fuoco parte dal pulsante sicuro"
        b.js(ESC); b.pausa(0.3)
        assert mostra(b, "vchiedi") == "none" and cestinati == [] and righe(b) == ["Album 01"], "Esc annulla"
        b.js("document.querySelector('#grid .riga [data-a=altro]').click()"); b.pausa(0.2)
        b.js(VOCE % "'Metti nel Cestino'" + ".click()"); b.pausa(0.3)
        b.js("document.querySelector('#vchiedi [data-esito=ok]').click()"); b.pausa(1)
        assert cestinati == [p] and righe(b) == [] and b.js("window.usato || null") is None, "nessun confirm() né alert()"
        assert mostra(b, "vuoto") == "block", "senza album, lo stato vuoto"
        assert not b.problemi(), b.problemi()


def test_chiudi_programma_chiede_in_pagina(home_srv, tmp_path):
    from cdp import Browser
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        b.js("document.getElementById('altro').click()"); b.pausa(0.3)
        assert [x.strip() for x in b.js("[...document.querySelectorAll('#menu button')].map(x => x.textContent)")] == ["Apri album esistente…", "Importa ZIP…", "Assistente AI…", "Lingua…", "Chiudi programma"]
        b.js(VOCE % "'Chiudi programma'" + ".click()"); b.pausa(0.3)
        assert mostra(b, "vchiedi") == "flex"; b.js(ESC); b.pausa(0.3)
        assert mostra(b, "vchiedi") == "none" and home_srv.uscite == []
        assert b.js("document.activeElement.id") == "altro", "il fuoco torna dove era"
        b.js("document.getElementById('altro').click()"); b.pausa(0.2)
        b.js(VOCE % "'Chiudi programma'" + ".click()"); b.pausa(0.3)
        b.js("document.querySelector('#vchiedi [data-esito=ok]').click()"); b.pausa(1.2)
        assert home_srv.uscite == [1] and "Programma chiuso" in b.js("document.body.innerText")
        assert not b.problemi(), b.problemi()


def test_stato_vuoto_porta_avanti(home_srv, tmp_path):
    from cdp import Browser
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert mostra(b, "vuoto") == "block" and mostra(b, "nuova") == "none" and mostra(b, "scaffale") == "none"
        t = b.js("document.getElementById('vuoto').innerText")
        assert "Il tuo primo album" in t and "restano dove sono, sul tuo computer" in t
        assert b.js("document.querySelectorAll('button.primario:not([hidden])').length && [...document.querySelectorAll('button.primario')].filter(e => e.offsetParent).length") == 1, "un solo pulsante primario"
        b.js("document.getElementById('vuoto-nuovo').focus(); document.getElementById('vuoto-nuovo').click()"); b.pausa(0.3)
        assert mostra(b, "vnew") == "flex" and b.js("document.activeElement.id") == "nome"
        b.js(ESC); b.pausa(0.2)
        assert mostra(b, "vnew") == "none" and b.js("document.activeElement.id") == "vuoto-nuovo"
        assert not b.problemi(), b.problemi()


def test_scegli_cartella_apre_il_nuovo_album(home_srv, tmp_path):
    from cdp import Browser

    from impaginatore.piattaforma import dialoghi

    class Finti(dialoghi.Dialoghi):
        def _scegli(self, tipo, messaggio): return ["/Clienti/Rossi/JPG"]
    dialoghi.imposta(Finti())
    crea(home_srv, 1)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        b.js("document.getElementById('scegli').click()", attendi=False); b.pausa(1)
        assert mostra(b, "vnew") == "flex" and b.js("document.getElementById('nome').value") == "Rossi" and b.js("document.getElementById('fdir').value").endswith("JPG")
        assert not b.problemi(), b.problemi()


def test_riga_della_prova_solo_negli_ultimi_sette_giorni(home_srv, licenza, tmp_path, monkeypatch):
    from cdp import Browser
    licenza.usa(None); licenze.stato()                                                 # parte la prova
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert b.js("document.getElementById('prova').hidden") is True and b.js("document.getElementById('lic').textContent") == "Prova gratuita · 30 giorni"
        monkeypatch.setattr(licenze, "orologio", lambda: time.time() + 26 * GIORNO)
        b.js("loadLic()"); b.pausa(0.5)
        assert b.js("document.getElementById('prova').hidden") is False and b.js("document.getElementById('provatxt').textContent") == "Prova: restano 4 giorni"
        assert b.js("getComputedStyle(document.getElementById('prova')).height") == "40px"
        b.js("document.getElementById('provalic').focus(); document.getElementById('provalic').click()"); b.pausa(0.4)
        assert mostra(b, "vlic") == "flex"
        b.js(ESC); b.pausa(0.2)
        assert mostra(b, "vlic") == "none" and b.js("document.activeElement.id") == "provalic"
        monkeypatch.setattr(licenze, "orologio", lambda: time.time() + 29.5 * GIORNO)
        b.js("loadLic()"); b.pausa(0.5)
        assert b.js("document.getElementById('provatxt').textContent") == "Prova: ultimo giorno"
        licenza.usa(licenza.chiavi.studio); b.js("loadLic()"); b.pausa(0.5)
        assert b.js("document.getElementById('prova').hidden") is True, "con la licenza la riga sparisce"
        assert not b.problemi(), b.problemi()


def test_tema_scuro_predefinito_e_si_ricorda(home_srv, tmp_path):
    from cdp import Browser
    crea(home_srv, 1)
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        tema = lambda: b.js("document.documentElement.dataset.theme")
        assert tema() == "dark" and b.js("document.getElementById('tema').getAttribute('aria-label')") == "Passa al tema chiaro"
        scuro = b.js("getComputedStyle(document.body).backgroundColor")
        b.js("document.getElementById('tema').click()"); b.pausa(0.2)
        assert tema() == "light" and b.js("localStorage.getItem('impaginatore_tema')") == "light" and b.js("getComputedStyle(document.body).backgroundColor") != scuro
        b.js("location.reload()", attendi=False); b.pausa(1.5)
        assert tema() == "light", "la preferenza si ricorda"
        b.js("localStorage.setItem('impaginatore_tema', 'rosso'); location.reload()", attendi=False); b.pausa(1.5)
        assert tema() == "dark", "un valore sconosciuto vale come predefinito"
        assert not b.problemi(), b.problemi()


def test_nessun_testo_italiano_nel_codice_della_pagina():
    """i testi visibili passano da t(): nell'HTML restano solo il marchio e il nome dell'autore"""
    import re
    from impaginatore import risorse
    html = risorse.leggi("home.html").decode("utf-8")
    assert " onclick=" not in html and "javascript:" not in html and html.count("<script") == 1
    assert not re.search(r"\b(alert|confirm|prompt)\(", html), "niente finestre del browser"
    assert "backdrop-filter" not in html and not re.search(r"#[0-9a-fA-F]{3,6}\b|rgba?\(", html.split("</style>")[0]), "solo i token della marca"
    corpo = re.sub(r"<style>.*?</style>|<script.*?</script>", "", html, flags=re.S)
    visibile = re.sub(r"<[^>]+>", " ", corpo)
    assert [w for w in re.findall(r"[A-Za-zÀ-ÿ]{3,}", visibile) if w not in ("Impaginatore", "Stefano", "Imperato")] == []
    assert json.loads(json.dumps(risorse.testi())) and json.loads(json.dumps(risorse.testi("en")))


def test_assistente_immagini_solo_dopo_la_conferma(home_srv, tmp_path):
    """menu ⋯ › Assistente AI…: l'interruttore è spento, accenderlo chiede conferma con il testo che dice dove vanno le
    immagini; «Annulla» lo lascia spento, «Accendi» salva la scelta, spegnerlo non chiede niente"""
    from cdp import Browser
    from impaginatore.mcp import consenso
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        b.js("document.getElementById('altro').click()"); b.pausa(0.2)
        b.js(VOCE % "'Assistente AI'" + ".click()"); b.pausa(0.4)
        assert mostra(b, "vassist") == "flex" and b.js("document.activeElement.id") == "aimg"
        assert b.js("document.getElementById('aimg').checked") is False and b.js("document.getElementById('aimg').getAttribute('role')") == "switch"
        assert "fuori dal tuo computer" in b.js("document.getElementById('anota').textContent")
        b.js("document.getElementById('aimg').click()"); b.pausa(0.3)
        assert mostra(b, "vchiedi") == "flex" and "fuori dal tuo computer" in b.js("document.getElementById('ch-testo').textContent")
        b.js("document.querySelector('#vchiedi [data-esito=annulla]').click()"); b.pausa(0.3)
        assert b.js("document.getElementById('aimg').checked") is False and not consenso.salvato()
        b.js("document.getElementById('aimg').click()"); b.pausa(0.3)
        b.js("document.querySelector('#vchiedi [data-esito=ok]').click()"); b.pausa(0.5)
        assert b.js("document.getElementById('aimg').checked") is True and consenso.salvato()
        b.js("document.getElementById('aimg').click()"); b.pausa(0.5)
        assert mostra(b, "vchiedi") == "none" and b.js("document.getElementById('aimg').checked") is False and not consenso.salvato()
        b.js(ESC); b.pausa(0.2); assert mostra(b, "vassist") == "none"
        assert not b.problemi(), b.problemi()
