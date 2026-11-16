"""VER-001, VER-003, VER-010: un'operazione o si rifiuta (400, stato com'era) o lascia un progetto che si salva, si
riapre e si mostra. Il salvataggio controlla album.json e progetto.json prima di scrivere; «Nuovo progetto» controlla
le misure prima di creare la cartella. Il fuzz è deterministico (seme fisso); la versione lunga è segnata «lento»."""
import json
import os
import random

import pytest

from impaginatore import formato
from impaginatore import validazione as V

OSTILI = [0, 1, -1, 0.5, 2, 1e7, -1e7, 1e300, -1e300, 1e-300, 2**63, 10**30, "x", "1e7", "", None, True, [], {}, [1e7], {"a": 1}, "\ud800", "x" * 5000]
OPERAZIONI = [
    dict(op="set", at="EL", z="N", a="N", bw="N", bd=["N", "#ff0000"], oc="N", sh="N"),
    dict(op="free", at="EL", x="N", y="N", w="N", h="N", ts="N"),
    dict(op="crosspage", at="EL", to="R", x="N", y="N", w="N", h="N"),
    dict(op="ratio", s=0, r="N", ats=[["L", 0]]),
    dict(op="nudge", s=0, ats=[["L", 0]], dx="N", dy="N"),
    dict(op="gscale", s=0, ats=[["L", 0], ["R", 0]], sx="N", sy="N", ax="N", ay="N"),
    dict(op="setrects", s=0, rects=[["L", 0, "N", "N", "N", "N"]]),
    dict(op="equalize", s=0, ref=["L", 0], ats=[["R", 0]]),
    dict(op="orient", s=0, ats=[["L", 0]], dir="v"),
    dict(op="origar", s=0, ats=[["L", 0]]),
    dict(op="fullpage", s=0, ats=[["R", 0]]),
    dict(op="align", s=0, ats=[["L", 0], ["R", 0]], mode="ch"),
    dict(op="zorder", s=0, ats=[["L", 0]], dir="front"),
    dict(op="frame", at="EL", c="N", r="N", w="N", h="N"),
    dict(op="pan", at="EL", l="N", t="N"),
    dict(op="tscale", at="TX", ts="N"),
    dict(op="settext", at="TX", tx="N", size="N", tr="N", lh="N", col=["N", 0, 0], font="N", al="N"),
    dict(op="addtext", s=0, fx="N", fy="N", fw="N", fh="N", tx="Testo"),
    dict(op="stile_salva", at="TX", nome="N"),
    dict(op="evg", value="N"),
    dict(op="ev", photo="FOTO", value="N"),
    dict(op="face", photo="FOTO", x="N", y="N"),
    dict(op="tono", photo="FOTO", value={"b": "N", "w": "N", "m": "N", "c": [["N", "N"]]}),
    dict(op="tono_fix", items=[{"photo": "FOTO", "ev": "N", "rit": {"alt": "N"}}]),
    dict(op="tono_L", value="N", zona="N"),
    dict(op="rit", photo="FOTO", key="vib", value="N"),
    dict(op="testo", nome="N", sottotitolo="N", data="N"),
    dict(op="tolta", photo="N"), dict(op="stella", photo="N"), dict(op="tono_escl", photo="N"), dict(op="colore", photo="FOTO", value="N"),
    dict(op="guides", s=0, v=["N"], h=["N"]),
    dict(op="blank", pos="N"), dict(op="move", s=0, to="N"), dict(op="swappages", s=0), dict(op="dup", s=0),
    dict(op="undo"), dict(op="redo"),
]


def _riempi(v, rnd, foto, testo):
    if v == "N": return rnd.choice(OSTILI)
    if v == "FOTO": return rnd.choice(foto)
    if v == "EL": return [0, rnd.choice("LR"), 0]
    if v == "TX": return testo
    if isinstance(v, list): return [_riempi(x, rnd, foto, testo) for x in v]
    if isinstance(v, dict): return {k: _riempi(x, rnd, foto, testo) for k, x in v.items()}
    return v


def _testo(E):
    """il primo livello di testo dello spread 1 ([0, lato, indice]; se non c'è, il primo elemento)"""
    for lato, pg in zip("LR", E.SP[0]):
        for j, it in enumerate(pg[1]):
            if E.is_txt(it): return [0, lato, j]
    return [0, "L", 0]


def _prepara(c):
    foto = [p["n"] for p in c.get("/api/state")["photos"]]
    c.post("/api/op", dict(op="newspreadsel", names=foto[:4], pos=0))
    c.post("/api/op", dict(op="addtext", s=0, fx=0.1, fy=0.1, fw=0.3, fh=0, tx="Titolo"))
    return foto


def _riapre(c, foto):
    formato.leggi_progetto(c.progetto)
    formato.leggi_album(os.path.join(c.progetto, formato.ALBUM), set(foto))


def _fuzz(c, seme, quante):
    rnd = random.Random(seme); foto = _prepara(c); esiti = {200: 0, 400: 0}
    for k in range(quante):
        o = _riempi(rnd.choice(OPERAZIONI), rnd, foto, _testo(c.E))
        st = c.codice("/api/op", o)
        assert st in (200, 400), (k, o, st)
        esiti[st] += 1
        assert c.codice("/api/state") == 200, (k, o)
        if k % 25 == 24:
            c.post("/api/save", {}); _riapre(c, foto)
    c.post("/api/save", {}); _riapre(c, foto)
    assert esiti[200] and esiti[400], esiti                     # il fuzz ha provato sia operazioni buone sia rifiutate


def test_fuzz_operazioni(editor):
    _fuzz(editor, 2026, 150)


@pytest.mark.lento
@pytest.mark.parametrize("seme", [1, 2])
def test_fuzz_operazioni_lungo(editor, seme):
    _fuzz(editor, seme, 800)


def test_salvataggio_non_scrive_un_progetto_che_non_si_riapre(editor):
    """se lo stato in memoria non si potrebbe riaprire (un difetto dell'editor), il salvataggio non scrive niente"""
    E = editor.E; _prepara(editor); editor.post("/api/save", {})
    prima = {f: open(os.path.join(editor.progetto, f), "rb").read() for f in (formato.ALBUM, formato.PROGETTO)}
    E.CFG["esposizione"]["globale"] = 1e7
    try:
        with pytest.raises(V.ErroreProgetto, match="globale"): E.save(backup=False)
    finally: E.CFG["esposizione"]["globale"] = 0.0
    el = E.SP[0][0][1][0]; w = el["w"]; el["w"] = float("nan")
    try:
        with pytest.raises(V.ErroreProgetto): E.save(backup=False)
    finally: el["w"] = w
    assert {f: open(os.path.join(editor.progetto, f), "rb").read() for f in prima} == prima


def test_tono_annullabile_e_rimesso_se_l_operazione_fallisce(editor, monkeypatch):
    st = editor.post("/api/op", dict(op="tono_L", value=60, zona=10))
    assert st["tono_L"] == 60 and st["tono_Z"] == 10 and st["canundo"] and st["dirty"], "il riferimento del tono è una modifica vera"
    st = editor.post("/api/op", dict(op="undo"))
    assert st["tono_L"] != 60 and st["tono_Z"] != 10 and "tono_L" not in editor.E.CFG and st["canredo"]
    assert editor.post("/api/op", dict(op="redo"))["tono_L"] == 60

    def rotta(): raise ValueError("verifica non riuscita")
    monkeypatch.setattr(editor.E, "verifica", rotta)
    ok, r = editor.prova("/api/op", dict(op="tono_L", value=40, zona=20))
    assert not ok and editor.E.CFG["tono_L"] == 60 and editor.E.CFG["tono_Z"] == 10, "un'operazione fallita rimette anche il tono"


def test_stato_che_non_si_puo_mostrare(editor, monkeypatch):
    prima = editor.get("/api/state")["globale"]
    monkeypatch.setattr(editor.E, "state", lambda: {"x": float("nan")})
    ok, r = editor.prova("/api/op", dict(op="evg", value=0.5))
    monkeypatch.undo()
    assert not ok and "impossibili" in r["errore"] and editor.get("/api/state")["globale"] == prima


def test_esposizione_dell_esportazione_controllata(editor):
    _prepara(editor)
    ok, r = editor.prova("/api/export", dict(fmt="jpg", range="1", ev=1e7, res="anteprima"))
    assert not ok and "globale" in r["errore"] and editor.get("/api/state")["globale"] == 0
    _riapre(editor, [p["n"] for p in editor.get("/api/state")["photos"]])


@pytest.mark.parametrize("campo,valore", [("spazio", "-5"), ("margine", "nan"), ("abb", "1e9"), ("abb", "abc"), ("margine", "1e400")])
def test_nuovo_rifiuta_le_misure_prima_di_creare_la_cartella(home, campo, valore):
    with pytest.raises(ValueError) as e: home.nuovo({"nome": "Misure", "w": "30", "h": "30", campo: valore})
    assert not os.path.exists(os.path.join(home.PROGETTI, "Misure")), "nessuna cartella a metà"
    assert str(e.value).startswith("Misure non valide:") and "progetto.json" not in str(e.value), e.value


def test_testo_progetto_e_album_controllati():
    with pytest.raises(V.ErroreProgetto, match="non si può salvare"): formato.testo_progetto({"formato_cm": [30, 30], "x": float("nan")})
    with pytest.raises(V.ErroreProgetto, match="margine_mm: deve essere un numero"): formato.testo_progetto({"formato_cm": [30, 30], "margine_mm": float("inf")})
    with pytest.raises(V.ErroreProgetto, match="non si può salvare"): formato.testo_progetto({"formato_cm": [30, 30], "x": {1, 2}})
    with pytest.raises(V.ErroreProgetto, match="spazio_mm"): formato.testo_progetto({"formato_cm": [30, 30], "spazio_mm": -5})
    assert json.loads(formato.testo_progetto({"formato_cm": [30, 30], "nome": "Prova"}))["nome"] == "Prova"
    with pytest.raises(V.ErroreProgetto, match="elemento"): formato.testo_album_controllato([[["I", [{"k": "p", "i": 0}]], ["I", []]]], lambda i: "a")
