"""Protezione dei server locali (SEC-002, SEC-004, SEC-005, SEC-007, SEC-008, SEC-010): nessuna pagina web aperta nel
browser dell'utente può comandare il programma; i percorsi che arrivano dalla pagina restano nelle cartelle consentite;
i percorsi non diventano mai testo di uno script. Ogni prova qui fallisce senza la correzione che controlla."""
import http.client
import json
import os
import socket
import stat
import sys
import time
import urllib.parse

import pytest

from impaginatore import percorsi, servizio, sicurezza
from impaginatore.piattaforma import processi

SERVER = ["home_srv", "editor"]


@pytest.fixture(params=SERVER)
def srv(request):
    """lo stesso controllo, sui due server"""
    return request.getfixturevalue(request.param)


def _richiesta(c, metodo, path, corpo=None, **h):
    """richiesta HTTP grezza (http.client: nessuna intestazione aggiunta da sola); (codice, intestazioni, corpo)"""
    k = http.client.HTTPConnection("127.0.0.1", c.porta, timeout=30)
    try:
        k.putrequest(metodo, path, skip_host=True, skip_accept_encoding=True)
        h.setdefault("Host", f"127.0.0.1:{c.porta}")
        if corpo is not None: h.setdefault("Content-Length", str(len(corpo)))
        for n, v in h.items():
            if v is not None: k.putheader(n.replace("_", "-"), v)
        k.endheaders(corpo)
        r = k.getresponse(); return r.status, r.headers, r.read()
    finally: k.close()


# ---------------------------------------------------------------- SEC-002: chi può parlare con i server
def test_senza_gettone_nessuna_risposta(srv):
    c = srv
    for path in ("/api/ping", "/api/state", "/api/progetti", "/api/ls?p=/etc", "/api/aggiornamento"):
        assert c.codice(path, **{"X-Impaginatore-Gettone": None}) == 401, path
        assert c.codice(path, **{"X-Impaginatore-Gettone": "sbagliato"}) == 401, path
    for path in ("/api/nuovo", "/api/esci", "/api/aggiorna", "/api/op", "/api/cestino"):
        assert c.codice(path, {}, **{"X-Impaginatore-Gettone": None}) == 401, path
    assert c.codice("/api/ping") == 200


def test_pagina_di_un_altro_sito_non_comanda(home_srv):
    """richieste cross-site come le fa un browser (fetch, form): rifiutate prima di fare qualcosa, anche con il gettone giusto"""
    c = home_srv; prima = len(c.get("/api/progetti")["progetti"])
    corpo = json.dumps({"nome": "Intruso", "w": 30, "h": 30}).encode()
    for h in ({"Origin": "https://sito-cattivo.example"}, {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"},
              {"Origin": f"http://127.0.0.1:{c.porta + 1}"}):
        assert c.codice("/api/nuovo", corpo, **h) == 403, h
    assert c.codice("/api/progetti", **{"Sec-Fetch-Site": "cross-site"}) == 403
    assert c.codice("/api/nuovo", corpo, **{"Origin": f"http://127.0.0.1:{c.porta}", "Sec-Fetch-Site": "same-origin"}) == 200, "la pagina stessa sì"
    assert c.codice("/api/nuovo", corpo, **{"Origin": f"http://localhost:{c.porta}"}) == 200
    assert len(c.get("/api/progetti")["progetti"]) == prima + 2
    # un modulo HTML di un altro sito (text/plain, niente intestazioni personalizzate): 401 prima ancora del tipo
    assert _richiesta(c, "POST", "/api/esci", b'{"x":1}', Content_Type="text/plain")[0] == 401
    assert c.uscite == []


def test_host_arbitrario_dns_rebinding(srv):
    c = srv
    for host in ("sito-cattivo.example", f"sito-cattivo.example:{c.porta}", f"127.0.0.1:{c.porta + 1}", "127.0.0.1", ""):
        assert _richiesta(c, "GET", "/api/ping", Host=host, X_Impaginatore_Gettone=c.gettone)[0] == 403, host
    assert _richiesta(c, "GET", "/api/ping", Host=f"localhost:{c.porta}", X_Impaginatore_Gettone=c.gettone)[0] == 200


def test_post_solo_json_con_lunghezza(srv, monkeypatch):
    c = srv
    assert c.codice("/api/ping", b"{}", **{"Content-Type": "text/plain"}) == 415
    assert c.codice("/api/ping", b"{}", **{"Content-Type": "application/x-www-form-urlencoded"}) == 415
    assert _richiesta(c, "POST", "/api/nonesiste", b"2\r\n{}\r\n0\r\n\r\n", Content_Type="application/json", Transfer_Encoding="chunked", X_Impaginatore_Gettone=c.gettone)[0] == 411
    k = socket.create_connection(("127.0.0.1", c.porta), timeout=30)          # niente Content-Length
    k.sendall(f"POST /api/op HTTP/1.1\r\nHost: 127.0.0.1:{c.porta}\r\nX-Impaginatore-Gettone: {c.gettone}\r\nContent-Type: application/json\r\n\r\n".encode())
    assert b" 411 " in k.recv(200).split(b"\r\n")[0]; k.close()
    # SEC-008: il corpo troppo grande si rifiuta dalla sola intestazione, senza leggerlo
    k = socket.create_connection(("127.0.0.1", c.porta), timeout=30)
    k.sendall(f"POST /api/op HTTP/1.1\r\nHost: 127.0.0.1:{c.porta}\r\nX-Impaginatore-Gettone: {c.gettone}\r\nContent-Type: application/json\r\nContent-Length: {sicurezza.MAX_CORPO + 1}\r\n\r\n".encode())
    assert b" 413 " in k.recv(200).split(b"\r\n")[0]; k.close()
    assert c.codice("/api/op" if hasattr(c, "E") else "/api/rimuovi", b"[1, 2]") == 400, "il corpo deve essere un oggetto JSON"


def test_connessione_lenta_si_chiude(srv, monkeypatch):
    """SEC-008: un client che apre la connessione e non manda niente non tiene un thread per sempre"""
    monkeypatch.setattr(servizio.Gestore, "timeout", 0.5)
    k = socket.create_connection(("127.0.0.1", srv.porta), timeout=10); t = time.time()
    k.sendall(b"GET /api/ping HTTP/1.1\r\n")
    assert k.recv(100) == b"" and time.time() - t < 5, "il server chiude la connessione"
    k.close()


def test_intestazioni_di_sicurezza_e_csp(srv):
    c = srv
    st, h, corpo = _richiesta(c, "GET", "/", X_Impaginatore_Gettone=c.gettone)
    assert st == 200
    nonce = h["Content-Security-Policy"].split("'nonce-")[1].split("'")[0]
    html = corpo.decode("utf-8")
    assert f'<script nonce="{nonce}">' in html and html.count("<script") == 1, "un solo script, con il nonce di questa risposta"
    assert "default-src 'none'" in h["Content-Security-Policy"] and "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert " onclick=" not in html and "javascript:" not in html, "niente gestori in linea: la CSP li bloccherebbe"
    assert h["X-Frame-Options"] == "DENY" and h["X-Content-Type-Options"] == "nosniff" and h["Referrer-Policy"] == "no-referrer"
    assert h["Cross-Origin-Resource-Policy"] == "same-origin" and h["Cache-Control"] == "no-store"
    st2, h2, corpo2 = _richiesta(c, "GET", "/", X_Impaginatore_Gettone=c.gettone)
    assert h2["Content-Security-Policy"] != h["Content-Security-Policy"], "nonce nuovo a ogni pagina"
    st, h, _ = _richiesta(c, "GET", "/api/ping", X_Impaginatore_Gettone=c.gettone)
    assert "script-src 'none'" in h["Content-Security-Policy"] and "Access-Control-Allow-Origin" not in h


def test_avvio_monouso_e_cookie(srv, monkeypatch):
    """l'URL di avvio collega il browser una volta sola: cookie HttpOnly/SameSite=Strict, valido solo per pagina e immagini"""
    c = srv; s = c.srv
    url = s.indirizzo_avvio(); path = url.split(str(c.porta), 1)[1]
    st, h, _ = _richiesta(c, "GET", path)
    assert st == 303 and h["Location"] == "/"
    biscotto = h["Set-Cookie"]; nome = sicurezza.nome_cookie(c.porta)
    assert biscotto.startswith(f"{nome}={c.gettone};") and "HttpOnly" in biscotto and "SameSite=Strict" in biscotto and "Path=/" in biscotto
    assert _richiesta(c, "GET", path)[0] == 401, "il codice vale una volta sola"
    assert _richiesta(c, "GET", "/avvio?c=inventato")[0] == 401 and _richiesta(c, "GET", "/avvio")[0] == 401
    cookie = f"{nome}={c.gettone}"
    st, h, corpo = _richiesta(c, "GET", "/", Cookie=cookie); assert st == 200 and c.gettone.encode() in corpo
    for p in ("/api/ping", "/api/state" if hasattr(c, "E") else "/api/progetti"):
        assert _richiesta(c, "GET", p, Cookie=cookie)[0] == 401, "le API vogliono l'intestazione, il cookie non basta"
    assert _richiesta(c, "POST", "/api/ping", b"{}", Cookie=cookie, Content_Type="application/json")[0] == 401
    assert _richiesta(c, "GET", "/", Cookie=f"{nome}=sbagliato")[0] == 401
    assert _richiesta(c, "GET", "/", Cookie=f"impaginatore_{c.porta + 1}={c.gettone}")[0] == 401, "il cookie di un'altra porta non vale"
    assert _richiesta(c, "GET", "/", Cookie='a="b')[0] == 401
    # navigazione senza cookie: una pagina che spiega come aprire il programma (non un JSON)
    st, h, corpo = _richiesta(c, "GET", "/", Sec_Fetch_Mode="navigate", Accept="text/html")
    assert st == 401 and h["Content-Type"].startswith("text/html") and "non è collegata" in corpo.decode("utf-8")
    assert _richiesta(c, "GET", "/favicon.ico")[0] == 204
    # codice scaduto
    monkeypatch.setattr(sicurezza, "DURATA_CODICE", -1)
    vecchio = s.indirizzo_avvio().split(str(c.porta), 1)[1]
    assert _richiesta(c, "GET", vecchio)[0] == 401
    # un client locale con il gettone chiede un URL di avvio nuovo
    assert c.post("/api/avvio")["indirizzo"].startswith(f"http://127.0.0.1:{c.porta}/avvio?c=")
    assert c.codice("/api/avvio", {}, **{"X-Impaginatore-Gettone": None}) == 401


def test_immagini_con_il_solo_cookie(editor, home_srv):
    """le immagini (img, sfondi CSS) non possono mandare intestazioni: bastano il cookie (le API no)"""
    c = editor; nome = sicurezza.nome_cookie(c.porta); n = c.get("/api/state")["photos"][0]["n"]
    ck = f"{nome}={c.gettone}"
    assert _richiesta(c, "GET", f"/img/thumb/{n}?w=100", Cookie=ck)[0] == 200
    assert _richiesta(c, "GET", f"/img/thumb/{n}?w=100")[0] == 401
    h = home_srv; x = h.get("/api/progetti")["progetti"][0]
    q = f"/api/cover?path={urllib.parse.quote(x['path'])}&n={x['cover']}"
    assert _richiesta(h, "GET", q, Cookie=f"{sicurezza.nome_cookie(h.porta)}={h.gettone}")[0] == 200
    assert _richiesta(h, "GET", q)[0] == 401


def test_esci_e_aggiorna_solo_con_il_gettone(home_srv):
    """SEC-007 / SEC-008: chiudere, aggiornare o tornare a una versione vecchia vuole il gettone"""
    c = home_srv
    for p in ("/api/esci", "/api/aggiorna", "/api/ripristina", "/api/controlla"):
        assert c.codice(p, {"codice": "abc1234"}, **{"X-Impaginatore-Gettone": None}) == 401
    time.sleep(0.6); assert c.uscite == []


# ---------------------------------------------------------------- file di sessione e gettone
def test_file_di_sessione(home_srv, casa):
    c = home_srv; f = os.path.join(sicurezza.cartella_sessioni(), f"home-{c.porta}.json")
    d = sicurezza.leggi_sessione("home", c.porta)
    assert d["gettone"] == c.gettone and d["porta"] == c.porta and d["pid"] == os.getpid() and d["progetti"] == c.modulo.PROGETTI
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(f).st_mode) == 0o600 and stat.S_IMODE(os.stat(os.path.dirname(f)).st_mode) == 0o700
    assert [x["porta"] for x in sicurezza.sessioni("home")] == [c.porta]
    assert sicurezza.gettone_di("editor", c.porta) is None and sicurezza.leggi_sessione("home", 1) is None
    assert sicurezza.leggi_sessione("altro", 1) is None
    with pytest.raises(ValueError): sicurezza.scrivi_sessione("altro", 1, "g")
    # un server nuovo sulla stessa porta ha riscritto il file: chiudendo, il vecchio non lo toglie
    sicurezza.scrivi_sessione("home", c.porta, "nuovo")
    sicurezza.togli_sessione("home", c.porta, c.gettone); assert sicurezza.gettone_di("home", c.porta) == "nuovo"
    sicurezza.togli_sessione("home", c.porta, "nuovo"); assert not os.path.exists(f)
    sicurezza.togli_sessione("home", c.porta, "nuovo")
    with open(os.path.join(sicurezza.cartella_sessioni(), "home-7.json"), "w", encoding="utf-8") as fh: fh.write("[1]")
    with open(os.path.join(sicurezza.cartella_sessioni(), "home-x.json"), "w", encoding="utf-8") as fh: fh.write("{}")
    assert sicurezza.sessioni("home") == [] and sicurezza.sessioni("editor") == []


def test_file_di_sessione_casi_limite(casa, monkeypatch):
    monkeypatch.setattr(sicurezza, "cartella_sessioni", lambda: str(casa / "nessuna"))
    assert sicurezza.sessioni("home") == []
    monkeypatch.setattr(sicurezza.os, "chmod", lambda *a: (_ for _ in ()).throw(PermissionError(1, "no")))
    assert os.path.exists(sicurezza.scrivi_sessione("editor", 5, "g"))
    monkeypatch.setattr(sicurezza.os, "remove", lambda *a: (_ for _ in ()).throw(PermissionError(1, "no")))
    sicurezza.togli_sessione("editor", 5, "g")
    assert sicurezza.indirizzo_avvio("editor", 5, timeout=0.5) is None, "il server non risponde"
    assert sicurezza.indirizzo_avvio("editor", 6) is None, "nessun file di sessione"


def test_gettone_e_codici():
    assert sicurezza.uguali("a", "a") and not sicurezza.uguali("a", "b") and not sicurezza.uguali("", "") and not sicurezza.uguali(None, "a")
    g = sicurezza.gettone_del_processo(); assert len(g) >= 40 and os.environ["IMPAGINATORE_GETTONE"] == g
    assert sicurezza.gettone_del_processo() == g, "dopo un riavvio (execv) resta lo stesso"
    s = sicurezza.Sessione("x"); c1, c2 = s.codice(), s.codice()
    assert c1 != c2 and s.usa(c2) and not s.usa(c2) and s.usa(c1) and not s.usa("") and not s.usa(None)
    assert sicurezza.Sessione().gettone != sicurezza.Sessione().gettone


def test_gettone_non_passa_ai_figli(monkeypatch):
    """i processi figli (editor) non ereditano il gettone della schermata: ognuno ha il suo; il riavvio lo tiene"""
    e = processi.ambiente_figli({"IMPAGINATORE_GETTONE": "segreto", "A": "1"}); assert "IMPAGINATORE_GETTONE" not in e and e["A"] == "1"
    lanci = []
    monkeypatch.setattr(processi.subprocess, "Popen", lambda cmd, **k: lanci.append((cmd, k)))
    processi.rilancia_dopo(["python", "-m", "impaginatore"], 0.1, gettone="segreto")
    assert lanci[0][1]["env"]["IMPAGINATORE_GETTONE"] == "segreto" and "segreto" not in " ".join(lanci[0][0]), "nell'ambiente, mai negli argomenti"


def test_server_su_127_0_0_1(srv):
    assert srv.srv.server_address[0] == "127.0.0.1"


# ---------------------------------------------------------------- SEC-005 / SEC-010: percorsi
def test_percorsi_dentro(tmp_path):
    r = tmp_path / "radice"; (r / "a").mkdir(parents=True); (tmp_path / "fuori").mkdir()
    assert percorsi.dentro(str(r / "a"), str(r)) and percorsi.dentro(str(r), str(r)) and percorsi.dentro(str(r / "non" / "esiste"), str(r))
    assert not percorsi.dentro(str(tmp_path / "fuori"), str(r)) and not percorsi.dentro(str(r / ".." / "fuori"), str(r))
    assert not percorsi.dentro(str(tmp_path / "radice2"), str(r)), "un prefisso del nome non basta"
    os.symlink(str(tmp_path / "fuori"), str(r / "link"))
    assert not percorsi.dentro(str(r / "link"), str(r)) and not percorsi.dentro(str(r / "link" / "x"), str(r))
    assert not percorsi.dentro(str(r), str(tmp_path / "non-esiste")) and not percorsi.dentro("\0", str(r))
    assert percorsi.troppo_ampia("/") and percorsi.troppo_ampia(os.path.expanduser("~")) and not percorsi.troppo_ampia(str(r))


def test_percorsi_maiuscole(tmp_path, monkeypatch):
    """dischi che non distinguono le maiuscole (macOS, Windows): si riconosce la stessa cartella scritta in un altro modo"""
    r = tmp_path / "Radice"; r.mkdir(); (r / "Foto").mkdir()
    reali = os.stat
    monkeypatch.setattr(percorsi.os, "stat", lambda p, *a, **k: reali(str(p).replace("RADICE", "Radice"), *a, **k))
    assert percorsi.dentro(str(tmp_path / "RADICE" / "Foto"), str(r))


def test_radici(tmp_path, casa):
    fisse = [str(tmp_path / "P"), "", str(casa), "/", str(tmp_path / "non-esiste")]
    (tmp_path / "P").mkdir(); (tmp_path / "S").mkdir(); (tmp_path / "S" / "f.jpg").write_bytes(b"x")
    R = percorsi.Radici(lambda: fisse)
    assert R.tutte() == [str(tmp_path / "P")], "vuote, inesistenti e troppo ampie (casa, disco) scartate"
    R.scelta(""); R.scelta(str(tmp_path / "S" / "f.jpg")); R.scelta(str(tmp_path / "S"))
    assert R.tutte() == [str(tmp_path / "P"), str(tmp_path / "S")], "un file scelto vale per la sua cartella"
    assert R.controlla(str(tmp_path / "S" / "f.jpg")) == str(tmp_path / "S" / "f.jpg")
    for p in (str(tmp_path), "/etc/passwd", None, 3, "", str(tmp_path / "S" / ".." / "..")):
        with pytest.raises(percorsi.FuoriDalleRadici): R.controlla(p)
    assert percorsi.Radici().tutte() == []


def test_finder_e_cestino_solo_dentro(home_srv, tmp_path, monkeypatch):
    """SEC-010: «Mostra nel Finder» solo dentro le cartelle consentite (niente «-a» per lanciare app); SEC-005: cestino solo progetti"""
    from impaginatore.piattaforma import azioni
    c = home_srv; fatti = []
    monkeypatch.setattr(azioni, "mostra", lambda p: fatti.append(p)); monkeypatch.setattr(azioni, "cestina", lambda p: fatti.append(("c", p)))
    for p in ("-a/Applications/Calculator.app", "/etc", str(tmp_path), "../../"):
        assert c.codice("/api/finder", {"path": p}) == 403, p
    pr = c.post("/api/nuovo", {"nome": "Mio", "w": 30, "h": 30})["path"]
    for p in (c.modulo.PROGETTI, os.path.join(pr, "Foto"), os.path.join(pr, "..", "..", os.path.basename(str(tmp_path))), "/etc"):
        ok, r = c.prova("/api/cestino", {"path": p}); assert not ok and "Cestino" in r["errore"], p
    os.symlink(pr, os.path.join(str(tmp_path), "scorciatoia"))
    ok, r = c.prova("/api/cestino", {"path": os.path.join(str(tmp_path), "scorciatoia")}); assert ok, "un collegamento si risolve: è il progetto vero"
    assert fatti == [("c", pr)]


@pytest.mark.skipif(sys.platform == "win32", reason="osascript finto: script di shell")
@pytest.mark.parametrize("nome", ['x" & (do shell script "touch /tmp/PWN") & "', "a'b\\c $HOME $(id) `id`", "Sposi àè ñ\nseconda riga"])
def test_cestino_mac_con_osascript_finto(home_srv, tmp_path, monkeypatch, nome):
    """SEC-004 (riproduzione dell'audit): un progetto con virgolette, apici, barre rovesciate, $, accenti o a capo nel nome, nel
    Cestino del Mac. Un osascript finto registra gli argomenti: il percorso arriva come argomento a sé («on run argv»), lo
    script non lo contiene"""
    import impaginatore.piattaforma as pf
    c = home_srv; bin_ = tmp_path / "bin"; bin_.mkdir(); reg = tmp_path / "argomenti.json"
    (bin_ / "osascript").write_text(f"#!{sys.executable}\nimport json, sys\njson.dump(sys.argv[1:], open({str(reg)!r}, 'w', encoding='utf-8'))\n", encoding="utf-8")
    os.chmod(bin_ / "osascript", 0o755)
    monkeypatch.setenv("PATH", str(bin_) + os.pathsep + os.environ["PATH"])
    monkeypatch.setattr(pf.sys, "platform", "darwin")
    p = os.path.join(c.modulo.PROGETTI, nome)
    os.makedirs(p)
    with open(os.path.join(p, "progetto.json"), "w", encoding="utf-8") as f: f.write("{}")
    assert c.post("/api/cestino", {"path": p}) == {"ok": True}
    with open(reg, encoding="utf-8") as f: a = json.load(f)
    assert a[-1] == p, "il percorso è l'ultimo argomento, intero"
    script = "\n".join(a[:-1]); assert "on run argv" in script and "item 1 of argv" in script and nome not in script
