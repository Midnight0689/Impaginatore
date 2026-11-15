"""Richieste all'editor con dati sbagliati o insoliti (BUG-001, BUG-002): un'operazione con indici che non esistono si
rifiuta prima di toccare lo stato; i nomi delle foto con spazi, accenti e % # ? + funzionano in tutte le richieste."""
import os
import urllib.parse

import pytest
from aiuti import crea_foto

from impaginatore import sicurezza


def _op(c, st, o): return c.prova("/api/op", dict(cid="t", rev=st["rev"], **o))


@pytest.mark.parametrize("o", [
    {"op": "newspread", "pos": 0, "L": {"mode": "W", "module": "M1", "photos": [9999]}, "R": {"mode": "I", "module": "M1", "photos": [0]}},
    {"op": "newspread", "pos": 0, "L": {"mode": "W", "module": "M1", "photos": [-1]}},
    {"op": "newspread", "pos": 0, "L": {"mode": "X", "module": "M1", "photos": [0]}},
    {"op": "newspread", "pos": 0, "L": "nulla"},
    {"op": "template", "s": 0, "L": {"mode": "W", "module": "M1", "photos": ["0"]}},
    {"op": "set", "at": [0, "L", 99], "z": 2},
    {"op": "set", "at": [7, "L", 0], "z": 2},
    {"op": "set", "at": [0, "X", 0], "z": 2},
    {"op": "set", "at": [0, "L"], "z": 2},
    {"op": "set", "at": [True, "L", 0], "z": 2},
    {"op": "swap", "a": [0, "L", 0], "b": [0, "R", 42]},
    {"op": "replace", "at": [0, "L", 0], "photo": "NON-ESISTE"},
    {"op": "stella", "photos": ["H01", "NON-ESISTE"], "value": True},
    {"op": "stella", "photos": "H01", "value": True},
    {"op": "ev", "photo": 3, "value": 1},
    {"op": "delete", "s": 5},
    {"op": "new", "s": 9},
    {"op": "mode", "s": 0, "side": "Z", "mode": "W"},
    {"op": "crosspage", "at": [0, "L", 0], "to": "Q"},
    {"op": "align", "s": 0, "ats": [["L", 50]], "mode": "l"},
    {"op": "align", "s": 0, "ats": [["L"]], "mode": "l"},
    {"op": "rit", "photo": "H01", "copia": {"con": "x"}},
    {"op": "rit", "photo": "H01", "copia": {"boh": 3}},
    {"op": "tono_fix", "items": [{"photo": "NON-ESISTE", "ev": 0}]},
    {"op": None},
])
def test_operazioni_con_indici_sbagliati_rifiutate(editor, o):
    """BUG-001: prima un indice fuori misura entrava nello stato e /api/state rispondeva 500 per sempre (autosalvataggio in errore)"""
    c = editor; st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    t = c.post("/api/templates", {"photos": names[:2]})["items"][0]
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="newspread", pos=0, L=t["L"], R=t["R"]))
    prima = c.get("/api/state")
    ok, r = _op(c, st, o); assert not ok and r["errore"], r
    dopo = c.get("/api/state")
    assert dopo["spreads"] == prima["spreads"] and dopo["rev"] == prima["rev"] and dopo["canundo"] == prima["canundo"]
    c.E.save(backup=False); assert not c.get("/api/state")["saveerr"]


def test_operazione_che_rompe_lo_stato_si_annulla(editor, monkeypatch):
    """se un'operazione lascia lo stato incoerente (anche per un errore nel codice) lo stato torna com'era prima"""
    c = editor; st = c.get("/api/state")
    vera = c.E.apply

    def rompe(o):
        vera(o); c.E.SP.append([["W", [dict(k="p", i=9999)]], ["I", []]]); c.E.GD.append(dict(v=[], h=[]))
    monkeypatch.setattr(c.E, "apply", rompe)
    ok, r = _op(c, st, {"op": "blank", "pos": 0}); assert not ok and "foto inesistente" in r["errore"]
    assert c.get("/api/state")["spreads"] == st["spreads"]
    for guasto in ([["W", []]], [["X", []], ["I", []]], [["W", [dict(k="?")]], ["I", []]]):
        monkeypatch.setattr(c.E, "apply", lambda o, g=guasto: (c.E.SP.append(g), c.E.GD.append(dict(v=[], h=[]))))
        ok, r = _op(c, st, {"op": "blank", "pos": 0}); assert not ok, guasto
    monkeypatch.setattr(c.E, "apply", lambda o: c.E.SP.append([["W", []], ["I", []]]))
    ok, r = _op(c, st, {"op": "blank", "pos": 0}); assert not ok and "guide" in r["errore"]
    assert c.get("/api/state")["spreads"] == st["spreads"]


def test_operazioni_valide_passano(editor):
    """i controlli non fermano le operazioni giuste (angolo «a» di set, «to» numerico di move, «new» in fondo)"""
    c = editor; st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    for k in range(2):
        t = c.post("/api/templates", {"photos": names[2 * k:2 * k + 2]})["items"][0]
        st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="newspread", pos=k, L=t["L"], R=t["R"]))
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="template", s=1, R=t["R"]))           # una pagina sola: l'altra resta com'è
    f = [i for i in st["spreads"][0]["items"] if i["k"] != "t"]
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="free", at=[0, f[0]["side"], f[0]["idx"]], x=.1, y=.1, w=.4, h=.4))
    f = [i for i in st["spreads"][0]["items"] if i["k"] != "t" and i["free"]][0]
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="set", at=[0, f["side"], f["idx"]], a=5))
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="move", s=1, to=0))
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="new", s=len(st["spreads"]) - 1))
    assert len(st["spreads"]) == 3
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="rit", photo=names[0], key="con", value=10))
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="rit", photos=[names[1]], copia={"con": 10, "tmp": -5.5}))
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="undo")); st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="redo"))


NOMI = ["Sposi àè", "100% vero", "n#1", "che?", "a+b", "x&y=z", "spazio  doppio", "çà ñ ü"]


def test_nomi_con_caratteri_speciali(home, apri_editor):
    """BUG-002: i nomi delle foto arrivano nelle richieste codificati (encodeURIComponent) e il server li decodifica"""
    p = home.nuovo({"nome": "Nomi", "w": 30, "h": 30}); fd = os.path.join(p, "Foto")
    crea_foto(fd, [(n, 300, 200, f"2026:01:01 10:00:0{k}") for k, n in enumerate(NOMI)])
    c = apri_editor(p); st = c.get("/api/state"); assert [x["n"] for x in st["photos"]] == NOMI
    q = urllib.parse.quote
    for n in NOMI:
        assert c.raw(f"/img/thumb/{q(n, safe='')}?w=100")[:2] == b"\xff\xd8", n
        assert c.get(f"/api/info/{q(n, safe='')}")["dim"] == [300, 200], n
        assert c.raw(f"/img/corr?n={q(n, safe='')}&w=100")[:2] == b"\xff\xd8", n
    assert c.codice(f"/img/thumb/{q('..%2Fprogetto.json', safe='')}") == 404 and c.codice("/img/thumb/non-esiste") == 404
    assert c.codice(f"/api/info/{q('../../etc/passwd', safe='')}") == 404
    t = c.post("/api/templates", {"photos": NOMI[:2]})["items"][0]
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="newspread", pos=0, L=t["L"], R=t["R"]))
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="stella", photos=NOMI[2:4], value=True))
    assert {x["n"] for x in st["photos"] if x["star"]} == set(NOMI[2:4])


def test_stato_dice_il_sistema_e_le_scartate(editor):
    st = editor.get("/api/state"); assert st["sistema"] in ("mac", "windows", "linux") and st["scartate"] == []


def test_progetti_e_aggiornamenti_dalla_schermata(editor, home_srv):
    """«Progetti» porta alla schermata con un indirizzo di avvio monouso; gli aggiornamenti si chiedono alla schermata con il suo gettone"""
    import http.client
    c = editor; E = c.E; vecchio = E.HOME
    try:
        E.HOME = f"http://127.0.0.1:{home_srv.porta}"
        k = http.client.HTTPConnection("127.0.0.1", c.porta, timeout=30); k.request("GET", "/vai/progetti", headers={"X-Impaginatore-Gettone": c.gettone})
        r = k.getresponse(); assert r.status == 303 and r.headers["Location"].startswith(f"http://127.0.0.1:{home_srv.porta}/avvio?c="); k.close()
        a = c.get("/api/aggiornamento"); assert a["disponibile"] is False and "motivo" in a
        E.HOME = "http://127.0.0.1:9"
        assert c.get("/api/aggiornamento") == {}, "schermata spenta (nessun file di sessione)"
        sicurezza.scrivi_sessione("home", 9, "x"); assert c.get("/api/aggiornamento") == {}, "file di sessione ma nessuno risponde"
        E.HOME = "http://127.0.0.1:boh"; assert c.get("/api/aggiornamento") == {}
        k = http.client.HTTPConnection("127.0.0.1", c.porta, timeout=30); k.request("GET", "/vai/progetti", headers={"X-Impaginatore-Gettone": c.gettone})
        r = k.getresponse(); assert r.status == 303 and r.headers["Location"] == "http://127.0.0.1:boh"; k.close()
        E.HOME = ""; assert c.get("/api/aggiornamento") == {}
    finally: E.HOME = vecchio
