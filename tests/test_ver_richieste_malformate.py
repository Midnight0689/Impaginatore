"""VER-012 (e la lettura del JSON di VER-001): intestazioni, percorsi e corpi malformati hanno sempre una risposta ordinata
(400, 411, 413), mai una connessione chiusa senza risposta né un traceback; i numeri non finiti si rifiutano alla lettura."""
import http.client
import socket

import pytest

from impaginatore import servizio

POST_EDITOR = ("/api/op", "/api/templates", "/api/pick", "/api/import", "/api/modelli", "/api/aggiorna_foto", "/api/ricollega", "/api/prj_esporta",
               "/api/ripristina", "/api/save", "/api/export", "/api/reveal", "/api/avvio")
POST_HOME = ("/api/nuovo", "/api/apri", "/api/aggiungi", "/api/scegli-foto", "/api/aggiorna", "/api/ripristina", "/api/controlla", "/api/importa-zip",
             "/api/rimuovi", "/api/cestino", "/api/finder", "/api/esci", "/api/avvio")


def grezzo(c, richiesta):
    """manda byte grezzi al server e restituisce tutta la risposta (b"" se il server chiude senza rispondere)"""
    s = socket.create_connection(("127.0.0.1", c.porta), timeout=20)
    s.sendall(richiesta); out = b""
    try:
        while True:
            x = s.recv(65536)
            if not x: break
            out += x
    except socket.timeout: pass
    s.close(); return out


def post(c, path, corpo, **h):
    k = http.client.HTTPConnection("127.0.0.1", c.porta, timeout=30)
    k.request("POST", path, corpo, {"Host": f"127.0.0.1:{c.porta}", "X-Impaginatore-Gettone": c.gettone, "Content-Type": "application/json", **h})
    r = k.getresponse(); b = r.read(); k.close(); return r.status, b


def codice(risposta): return int(risposta.split(b" ", 2)[1]) if risposta.startswith(b"HTTP/1.") else None


@pytest.mark.parametrize("lunghezza,atteso", [("²", 411), ("٣", 411), ("1" * 19, 413), ("9" * 5000, 413), ("-1", 411), ("0x10", 411)])
def test_content_length_strani(editor, lunghezza, atteso):
    r = grezzo(editor, f"POST /api/op HTTP/1.1\r\nHost: 127.0.0.1:{editor.porta}\r\nX-Impaginatore-Gettone: {editor.gettone}\r\n"
                       f"Content-Type: application/json\r\nContent-Length: {lunghezza}\r\n\r\n{{}}".encode("utf-8"))
    assert codice(r) == atteso, r[:200]


@pytest.mark.parametrize("percorso", ["//[", "http://[x/api/state", "/api/state?p=%ff"])
def test_percorso_malformato(editor, home_srv, percorso):
    for c in (editor, home_srv):
        r = grezzo(c, f"GET {percorso} HTTP/1.1\r\nHost: 127.0.0.1:{c.porta}\r\nX-Impaginatore-Gettone: {c.gettone}\r\n\r\n".encode())
        assert codice(r) in (400, 404) or (percorso.endswith("%ff") and codice(r) == 200), r[:200]


def test_corpo_non_oggetto_su_tutte_le_api(editor, home_srv):
    for c, percorsi in ((editor, POST_EDITOR), (home_srv, POST_HOME)):
        for p in percorsi:
            for corpo in (b"[1, 2]", b"3", b'"testo"', b"null", b"{", b"\xff\xfe", b"[" * 100000 + b"]" * 100000):
                st, b = post(c, p, corpo)
                assert st == 400 and b.startswith(b'{"errore"'), (p, corpo[:10], st, b[:100])
    assert home_srv.uscite == [], "un corpo sbagliato non chiude il programma"


@pytest.mark.parametrize("corpo", [b'{"op": "evg", "value": NaN}', b'{"op": "evg", "value": Infinity}', b'{"op": "evg", "value": -Infinity}',
                                   b'{"op": "evg", "value": 1e400}', b'{"op": "face", "photo": "H01", "x": -1e999, "y": 0}'])
def test_numeri_non_finiti_rifiutati_alla_lettura(editor, corpo):
    prima = editor.get("/api/state")
    st, b = post(editor, "/api/op", corpo)
    assert st == 400 and b"JSON" in b, b
    dopo = editor.get("/api/state")
    assert dopo["globale"] == prima["globale"] and dopo["rev"] == prima["rev"] and not dopo["canundo"]


def test_leggi_json_e_numero():
    assert servizio.leggi_json(b'{"a": 1.5, "b": [1, 2]}') == {"a": 1.5, "b": [1, 2]}
    for t in (b"NaN", b"[Infinity]", b"-Infinity", b"1e309", b"[" * 1000000 + b"]" * 1000000):
        with pytest.raises(ValueError): servizio.leggi_json(t)
    q = {"k": ["0.5"], "w": ["9999"], "n": ["-3"], "x": ["nan"], "y": ["inf"], "z": ["abc"], "i": ["1.5"]}
    assert servizio.numero(q, "k", 0.2, 0.01, 1) == 0.5 and servizio.numero(q, "w", 260, 16, 1200, intero=True) == 1200
    assert servizio.numero(q, "n", 1, 0, 10, intero=True) == 0 and servizio.numero({}, "k", 0.2, 0.01, 1) == 0.2
    for nome in ("x", "y", "z"):
        with pytest.raises(servizio.RichiestaNonValida): servizio.numero(q, nome, 1, 0, 10)
    with pytest.raises(servizio.RichiestaNonValida): servizio.numero(q, "i", 1, 0, 10, intero=True)
