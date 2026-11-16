"""Interfaccia ridisegnata con la marca (T-205), parte del server: file statici delle pagine (token, caratteri con le
licenze), tabella dei testi dentro le pagine, stacchi fra le foto calcolati dal motore per la pagina, licenza nello stato
dell'editor, preparazione delle foto in sottofondo come predefinita."""
import json
import os
import re

import pytest

from impaginatore import licenze, risorse, sicurezza

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIORNO = 86400


def _brand(*p):
    with open(os.path.join(RADICE, "brand", *p), "rb") as f: return f.read()


def test_statici_sono_quelli_della_marca():
    """token e caratteri sono gli stessi di brand/ (i token si rigenerano lì: questa copia non deve restare indietro)"""
    st = risorse.statici()
    assert risorse.leggi("statici/tokens.css") == _brand("tokens.css")
    for nome, orig in (("Newsreader.woff2", "Newsreader[opsz,wght].woff2"), ("InstrumentSans.woff2", "InstrumentSans[wdth,wght].woff2"),
                       ("IBMPlexMono-Regular.woff2", "IBMPlexMono-Regular.woff2"), ("IBMPlexMono-Medium.woff2", "IBMPlexMono-Medium.woff2")):
        assert risorse.leggi(f"statici/{nome}") == _brand("font", orig) and st[nome] == "font/woff2"
        assert f'url("{nome}")' in risorse.leggi("statici/font.css").decode("utf-8")
    for f in ("OFL-Newsreader.txt", "OFL-InstrumentSans.txt", "OFL-IBMPlexMono.txt"):
        assert risorse.leggi(f"statici/{f}") == _brand("font", f), "ogni carattere viaggia con la sua licenza (OFL)"
    assert st["tokens.css"].startswith("text/css") and set(os.path.splitext(n)[1] for n in st) == {".css", ".woff2", ".txt"}


@pytest.mark.parametrize("server", ["home_srv", "editor"])
def test_statici_dai_due_server(server, request):
    c = request.getfixturevalue(server)
    assert c.raw("/risorse/tokens.css") == _brand("tokens.css")
    gettone = {"X-Impaginatore-Gettone": None}
    cookie = {"Cookie": f"{sicurezza.nome_cookie(c.porta)}={sicurezza.valore_cookie(c.gettone, c.porta)}"}
    assert c.codice("/risorse/font.css", **gettone) == 401, "senza gettone né cookie no"
    assert c.codice("/risorse/font.css", **gettone, **cookie) == 200, "il foglio di stile e i caratteri li chiede il browser: basta il cookie"
    import urllib.request
    with urllib.request.urlopen(urllib.request.Request(c.url("/risorse/Newsreader.woff2"), headers={"X-Impaginatore-Gettone": c.gettone})) as r:
        et = r.headers["ETag"]; assert r.headers["Content-Type"] == "font/woff2" and r.headers["Cache-Control"] == "no-cache" and r.headers["Content-Security-Policy"]
    assert c.codice("/risorse/Newsreader.woff2", **{"If-None-Match": et}) == 304, "non cambiato: non si riscarica"
    for p in ("/risorse/__init__.py", "/risorse/../risorse/__init__.py", "/risorse/testi/it.json", "/risorse/", "/risorse/vib_lut.npz", "/risorse/%2e%2e%2f__init__.py"):
        assert c.codice(p) == 404, p


def test_testi_dentro_le_pagine(home_srv, editor):
    t = risorse.testi()
    assert all(isinstance(k, str) and isinstance(v, str) and v for k, v in t.items()) and all(k.split(".")[0] in ("comune", "home", "editor") for k in t)
    for c, pagina, altra in ((home_srv, "home.html", "editor."), (editor, "index.html", "home.")):
        html = c.raw("/").decode("utf-8")
        assert "__TESTI__" not in html and "__NONCE__" not in html
        m = re.search(r"const TESTI = (\{.*?\});", html); assert m, "la tabella dei testi è nello script della pagina"
        d = json.loads(m.group(1)); assert d == {k: v for k, v in t.items() if k.startswith(("comune.", pagina == "home.html" and "home." or "editor."))}
        assert not any(k.startswith(altra) for k in d), "ogni pagina riceve solo i suoi testi"


def test_testi_non_escono_dallo_script(monkeypatch):
    monkeypatch.setattr(risorse, "testi", lambda lingua="it": {"comune.x": "</script><b>  ", "home.y": "a", "editor.z": "b"})
    j = risorse.testi_pagina("home.html")
    assert "<" not in j and " " not in j and " " not in j and json.loads(j) == {"comune.x": "</script><b>  ", "home.y": "a"}
    assert json.loads(risorse.testi_pagina("altra.html")) == {"comune.x": "</script><b>  "}


def _spread(c, n=3):
    nomi = [p["n"] for p in c.get("/api/state")["photos"]]
    return c.post("/api/op", dict(op="newspreadsel", names=nomi[:n], pos=0))


def test_spazi_dal_motore(editor):
    """gli stacchi che la pagina mostra sono quelli del motore (la pagina non li calcola più)"""
    c = editor; _spread(c)
    d = c.get("/api/spazi?s=0")
    assert {k: d[k] for k in ("ref", "n", "ok", "diversi")} == c.E.stato_spazi(0) and d["n"] == len(d["coppie"]) > 0
    assert set(d["coppie"][0]) == {"ax", "da", "a", "at", "g", "ok"} and all(p["ax"] in ("x", "y") and p["a"] > p["da"] for p in d["coppie"])
    e = c.get("/api/spazi?s=0&modo=custom&cm=1.5")
    assert abs(e["ref"] - 1.5 / 2.54 * c.E.A.PPI) < 1e-6 and e["diversi"] == e["n"], "con 1,5 cm di riferimento nessuno stacco è giusto"
    assert c.get("/api/spazi?s=0&modo=freq")["n"] == d["n"]
    for q in ("s=1", "s=-1", "s=x", "s=0&modo=boh", "s=0&modo=custom", "s=0&modo=custom&cm=0"):
        ok, r = c.prova(f"/api/spazi?{q}"); assert not ok and r["errore"], q
        assert c.codice(f"/api/spazi?{q}") == 400, q


def test_licenza_nello_stato_dell_editor(editor, licenza, monkeypatch):
    c = editor
    L = c.get("/api/state")["licenza"]
    assert (L["stato"], L["nome_fascia"], L["sola_lettura"], L["giorni"], L["motivi"]) == ("attiva", "Studio", False, None, {}) and all(L["funzioni"].values())
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    L = c.get("/api/state")["licenza"]
    assert L["funzioni"]["editor_completo"] and not L["funzioni"]["impaginazione_automatica_album"] and not L["funzioni"]["uniformita_tono"]
    assert L["motivi"]["impaginazione_automatica_album"] == "L'impaginazione automatica dell'album non fa parte della licenza Essenziale: c'è nelle licenze Pro e Studio."
    licenza.usa(None)
    L = c.get("/api/state")["licenza"]
    assert (L["stato"], L["giorni"], L["filigrana"]) == ("prova", 30, True) and L["messaggio"].startswith("Prova gratuita")
    licenza.usa("IMP1-AAAAA")
    assert c.get("/api/state")["licenza"]["stato"] == "non valida" and c.get("/api/state")["licenza"]["giorni"] == 30
    licenza.usa(None); licenze.stato(); monkeypatch.setattr(licenze, "orologio", lambda: __import__("time").time() + 31 * GIORNO)
    L = c.get("/api/state")["licenza"]
    assert (L["stato"], L["sola_lettura"], L["giorni"]) == ("scaduta", True, None) and not any(L["funzioni"].values())
    assert L["motivi"]["editor_completo"].startswith("Impaginatore è in sola lettura.")


def test_sottofondo_predefinito_dalla_riga_di_comando(monkeypatch):
    from impaginatore.editor import server as E
    from impaginatore.servizio import ServerLocale
    visti = []
    monkeypatch.setattr(E, "inizializza", lambda p, h, sf: visti.append(sf))
    monkeypatch.setattr(E, "avvia_cicli", lambda: None)
    monkeypatch.setattr(E, "crea_server", lambda porta, g: type("S", (), {"server_address": ("127.0.0.1", 1), "serve_forever": lambda self: None, "server_close": lambda self: None})())
    monkeypatch.setattr(E, "ferma", lambda: None)
    assert ServerLocale
    E.main(["--progetto", "x"]); E.main(["--progetto", "x", "--no-sottofondo"]); E.main(["--progetto", "x", "--sottofondo"])
    assert visti == [True, False, True], "la schermata dei progetti apre l'editor senza opzioni: le foto si preparano mentre si lavora"
