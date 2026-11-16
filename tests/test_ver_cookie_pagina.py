"""VER-006: il browser manda i cookie di 127.0.0.1 a ogni porta, anche al server di un altro programma. Il cookie della
pagina quindi non è il gettone (è un HMAC del gettone, diverso per porta) e apre solo la pagina, che non contiene il
gettone, e le immagini: mai le API né un URL di avvio. Il gettone arriva alla scheda una volta sola, dalla pagina
dell'URL di avvio, che lo lascia in sessionStorage (nessun server la riceve)."""
import http.client
import json

import pytest
from cdp import CHROME

from impaginatore import sicurezza



def _get(c, path, **h):
    k = http.client.HTTPConnection("127.0.0.1", c.porta, timeout=30)
    try:
        k.request("GET", path, headers=dict({"Host": f"127.0.0.1:{c.porta}"}, **h))
        r = k.getresponse(); return r.status, r.headers, r.read()
    finally: k.close()


def _cookie_dall_avvio(c):
    st, h, corpo = _get(c, c.srv.indirizzo_avvio().split(str(c.porta), 1)[1])
    assert st == 200
    return h["Set-Cookie"].split(";", 1)[0], corpo.decode("utf-8")


def test_il_cookie_rubato_non_apre_le_api(editor, home_srv):
    """quello che riceve il server «spia» su un'altra porta: con il valore del cookie, né come intestazione né come cookie, le API non rispondono"""
    for c, api in ((editor, ("/api/state", "/api/ls?p=" + editor.progetto, "/api/vai_progetti", "/api/log")), (home_srv, ("/api/progetti", "/api/aggiornamento"))):
        cookie, _ = _cookie_dall_avvio(c); valore = cookie.split("=", 1)[1]
        assert valore != c.gettone and len(valore) == 64
        for p in api:
            assert _get(c, p, **{sicurezza.INTESTAZIONE: valore})[0] == 401, p
            assert _get(c, p, Cookie=cookie)[0] == 401, p
        st, _, pagina = _get(c, "/", Cookie=cookie)
        assert st == 200 and c.gettone.encode() not in pagina, "la pagina che il cookie apre non contiene il gettone"


def test_vai_progetti_non_si_apre_con_il_cookie(editor):
    """prima «/vai/progetti» si apriva con il cookie e rimandava a un URL di avvio della schermata (cioè al suo gettone)"""
    cookie, _ = _cookie_dall_avvio(editor)
    assert _get(editor, "/vai/progetti", Cookie=cookie)[0] == 401
    assert _get(editor, "/api/vai_progetti", Cookie=cookie)[0] == 401


def test_valore_del_cookie():
    a = sicurezza.valore_cookie("gettone", 8765)
    assert a == sicurezza.valore_cookie("gettone", 8765) and a != sicurezza.valore_cookie("gettone", 8766) and a != sicurezza.valore_cookie("altro", 8765)
    assert "gettone" not in a and len(a) == 64


def test_pagina_di_avvio_tiene_il_gettone_come_stringa():
    """anche un gettone strano (ereditato dall'ambiente) resta una stringa JS: niente «</script>» che chiude lo script"""
    html = sicurezza.pagina_avvio('a"</script><script>x()</script>', "N")
    assert html.count("</script>") == 1 and '<script nonce="N">' in html
    js = html.split('<script nonce="N">', 1)[1].split("</script>", 1)[0]
    g = js.split('sessionStorage.setItem("impaginatore_gettone", ', 1)[1].split("); }", 1)[0]
    assert json.loads(g) == 'a"</script><script>x()</script>'


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_nel_browser(home_srv, tmp_path):
    """l'URL di avvio lascia il gettone nella scheda; una scheda senza (aperta a mano con il solo cookie) dice che non è collegata"""
    from cdp import Browser
    h = home_srv; h.post("/api/nuovo", {"nome": "Album Bianchi", "w": 30, "h": 30})
    with Browser(tmp_path) as b:
        b.apri(h.srv.indirizzo_avvio(), 1.5)
        assert b.js("location.pathname") == "/" and b.js("sessionStorage.getItem('impaginatore_gettone')") == h.gettone
        assert "Album Bianchi" in b.js("document.body.innerText") and h.gettone not in b.js("document.documentElement.outerHTML")
        b.js("sessionStorage.clear(); location.reload()", attendi=False); b.pausa(1.5)
        testo = b.js("document.body.innerText")
        assert "non è collegata" in testo and "Album Bianchi" not in testo
