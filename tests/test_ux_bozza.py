"""UX-018: «Prepara la bozza» propone tutto l'album dalle foto da usare (in ordine di scatto, a capitoli, con le
disposizioni che riempiono le pagine) e lo applica con un solo passo d'annulla; gli spread esistenti non si toccano.
Le licenze: la bozza è «impaginazione_automatica_album», «Sistema» su tutto l'album «correzione_spaziature_album»."""
import io
import os

import pytest
from PIL import Image

from impaginatore.motore import album as A
from impaginatore.motore import bozza as BZ


def op(c, **o): return c.post("/api/op", o)


def f(i, dt, ar=1.5, stella=False): return dict(i=i, dt=dt, ar=ar, stella=stella)


def t(L, R, cost=0.1, worst=0.1, mL="I", mR="I"):
    return dict(cost=cost, worst=worst, L=dict(mode=mL, module=L[0], mirror=False, photos=L[1]), R=dict(mode=mR, module=R[0], mirror=False, photos=R[1]))


def test_foto_delle_schermate_a_capitoli(home, apri_editor):
    """le foto finte delle schermate (strumenti/schermate_ux.py) sono di tre momenti della giornata, come quelle di un
    matrimonio: dopo gli spread fatti a mano delle schermate, la bozza della scena «editor-bozza» ha almeno due capitoli"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("schermate_ux", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "strumenti", "schermate_ux.py"))
    S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
    p = home.nuovo({"nome": "Schermate", "w": "60", "h": "22.5"}); S.foto_finte(os.path.join(p, "Foto"))
    c = apri_editor(p); S.prepara_album(c)
    dt = [x["dt"] for x in sorted(A.M, key=lambda m: m["n"])]
    assert dt == sorted(dt) and len(BZ.capitoli([dict(i=i, dt=d) for i, d in enumerate(dt)])) == 3, "nomi in ordine di scatto, tre momenti"
    b = c.post("/api/bozza", {}); assert b["capitoli"] >= 2, b["capitoli"]


# ---------------------------------------------------------------- funzioni pure
def test_capitoli_e_gruppi():
    ore = lambda h, m: f"2026:05:23 {h:02d}:{m:02d}:00"
    foto = [f(0, ore(10, 0)), f(1, ore(10, 5)), f(2, ore(10, 50)), f(3, ore(11, 0)), f(4, ore(12, 0)), f(5, ""), f(6, ore(12, 10)), f(7, ore(15, 0))]
    caps = BZ.capitoli(foto)
    assert [[x["i"] for x in c] for c in caps] == [[0, 1], [2, 3], [4, 5, 6, 7]], "pausa oltre 30 minuti; senza data resta dov'è; l'ultimo da solo va con quello prima"
    assert [[x["i"] for x in c] for c in BZ.capitoli([f(0, ore(9, 0)), f(1, ore(10, 0)), f(2, ore(10, 1))])] == [[0, 1, 2]], "il primo da solo va con quello dopo"
    assert BZ.secondi("non è una data") is None and BZ.secondi("2026:05:23 10:00:00") is not None
    cap = [f(i, "") for i in range(9)]
    assert [len(g) for g in BZ.gruppi(cap, 3, set())] == [3, 2, 4], "3, 3-1, 3+1 (l'ultima foto da sola entra nel gruppo prima)"
    assert [[x["i"] for x in g] for g in BZ.gruppi(cap, 3, {2, 5, 6})] == [[0, 1], [2, 3], [4, 5], [6, 7, 8]], "le foto sole aprono uno spread (o lo chiudono, se prima resterebbe una foto da sola)"
    assert [[x["i"] for x in g] for g in BZ.gruppi(cap, 3, {3, 4})] == [[0, 1, 2], [3, 4], [5, 6, 7, 8]], "due foto sole di fila: una per pagina"
    assert [[x["i"] for x in g] for g in BZ.gruppi(cap[:2], 3, {1})] == [[0, 1]]
    assert [[x["i"] for x in g] for g in BZ.gruppi(cap[:1], 3, {0})] == [[0]], "una foto sola e basta"
    assert [len(g) for g in BZ.gruppi(cap, 20, set())] == [8, 1], "al massimo 8 foto per spread"


def test_punteggio():
    base = t(("DUO", [0, 1]), ("FULL", [2]))
    assert BZ.punteggio(base, 0, "alterna", set(), []) == pytest.approx(0.1)
    assert BZ.punteggio(base, 1, "alterna", set(), []) == pytest.approx(0.5), "spread dispari: ci vuole una pagina bianca"
    assert BZ.punteggio(t(("DUO", [0, 1]), ("CV", [2]), mR="W"), 1, "alterna", set(), []) == pytest.approx(0.1)
    assert BZ.punteggio(base, 0, "bianche", set(), []) == pytest.approx(0.9) and BZ.punteggio(t(("DUO", [0, 1]), ("CV", [2]), mR="W"), 0, "piene", set(), []) == pytest.approx(0.5)
    assert BZ.punteggio(t(("FULL", [0]), ("BLANK", []), mR="W"), 1, "alterna", set(), []) == pytest.approx(1.6), "pagina vuota"
    assert BZ.punteggio(base, 0, "alterna", set(), [("DUO", "FULL"), ("DUO", "FULL")]) == pytest.approx(1.1), "stessi moduli tre volte di fila"
    assert BZ.punteggio(base, 0, "alterna", {0}, []) == pytest.approx(3.1), "la foto sola divide la pagina con un'altra"
    assert BZ.punteggio(t(("DUO", [0, 1]), ("FULL", [2]), worst=0.4), 0, "alterna", set(), []) == pytest.approx(0.1 + 0.5 + 2 * (0.4 - BZ.RITAGLIO))


def test_proposta_con_disposizioni_finte():
    chiesti = []

    def opzioni(ix):
        chiesti.append(list(ix))
        if len(ix) == 3: return dict(items=[], piu=[])                                     # per 3 foto niente: si divide
        if ix == [4]: return dict(items=[dict(cost=0, worst=0, L=dict(mode="I", module="FULL", mirror=False, photos=[4]))], piu=[])  # solo una pagina: non vale
        h = len(ix) // 2 or 1
        return dict(items=[t(("X", ix[:h]), ("Y", ix[h:]))], piu=[t(("Z", ix[:h]), ("W", ix[h:]), cost=0.05)])
    foto = [f(i, f"2026:05:23 10:{i:02d}:00") for i in range(10)]
    p = BZ.proposta(foto, opzioni, per_spread=4)
    assert [s["foto"] for s in p["spreads"]] == [[0, 1, 2, 3], [5, 6], [7], [8, 9]] and p["foto"] == 9, "gruppi di 3 divisi; la 4 senza disposizione resta fuori"
    mods = [(s["L"]["module"], s["R"]["module"]) for s in p["spreads"]]
    assert mods[:2] == [("Z", "W"), ("Z", "W")] and mods[2] == ("X", "Y"), "la meno costosa, ma non tre volte di fila"
    assert p["spreads"][0]["R"] == dict(mode="I", module="W", mirror=False, photos=[2, 3])
    assert p["spreads"][0]["inizio"] is True and p["spreads"][0]["ora"] == "10:00" and p["spreads"][1]["inizio"] is False and p["spreads"][1]["ora"] is None
    assert p["capitoli"] == 1 and p["per_spread"] == round(9 / 4, 1) and p["spreads"][0]["taglia"] == round(__import__("math").exp(0.1), 2)
    assert [4] in chiesti and [7] in chiesti, "i gruppi senza disposizione si dividono"
    assert BZ.proposta([], opzioni) == dict(spreads=[], capitoli=0, foto=0, per_spread=0)
    a, b = BZ.proposta(foto, opzioni, seme=7), BZ.proposta(foto, opzioni, seme=7)
    assert a == b, "stesso seme, stessa bozza"


# ---------------------------------------------------------------- nell'editor
def test_bozza_proposta_e_applicata(editor):
    c = editor; E = c.E
    p = c.post("/api/bozza", {})
    usate = [i for s in p["spreads"] for i in s["L"]["photos"] + s["R"]["photos"]]
    assert sorted(usate) == list(range(10)) and sorted(i for s in p["spreads"] for i in s["foto"]) == list(range(10)), "ogni foto una volta"
    assert all(s["L"]["module"] != "BLANK" and s["R"]["module"] != "BLANK" for s in p["spreads"]), "pagine piene"
    assert p["foto"] == 10 and p["capitoli"] == 2 and p["spreads"][0]["ora"] == "10:00" and all(s["nomi"] for s in p["spreads"])
    ordine = [i for s in p["spreads"] for i in s["foto"]]; dt = [A.M[i]["dt"] for i in ordine]; assert dt == sorted(dt), "in ordine di scatto"
    r = c.raw("/img/bozza/0?k=0.1"); assert Image.open(io.BytesIO(r)).size[0] > 100
    assert c.codice("/img/bozza/99") == 400 and len(E.SP) == 0, "l'anteprima non tocca l'album"
    st = op(c, op="bozza", spreads=p["spreads"])
    assert len(st["spreads"]) == len(p["spreads"]) and st["esito"] == dict(spread=len(p["spreads"]), foto=10, da=0)
    assert st["annulla"] == {"nome": "Bozza dell'album", "s": 0} and len(E.UNDO) == 1
    st = op(c, op="undo"); assert len(st["spreads"]) == 0
    st = op(c, op="bozza"); assert len(E.SP) == len(st["spreads"]) == len(p["spreads"]), "senza spread: la stessa proposta, calcolata lì"
    ok, r = c.prova("/api/bozza", {"seme": 3}); assert not ok and r["errore"].endswith("ce ne sono 0")


def test_bozza_con_una_foto_sola(editor):
    """una foto ancora da usare: «ce n'è 1», non «ce ne sono 1»"""
    c = editor
    op(c, op="newspreadsel", names=["H01", "H02", "V03", "V04"], pos=0); op(c, op="newspreadsel", names=["Q05", "H06", "V07", "H08", "Q09"], pos=1)
    ok, r = c.prova("/api/bozza", {}); assert not ok and r["errore"] == "Per la bozza servono almeno 10 foto ancora da usare: ce n'è 1"


def test_bozza_dopo_gli_spread_esistenti(editor):
    c = editor; E = c.E
    op(c, op="newspreadsel", names=["H01"], pos=0); prima = [list(sp) for sp in E.SP]
    ok, r = c.prova("/api/bozza", {}); assert not ok and r["errore"] == "Per la bozza servono almeno 10 foto ancora da usare: ce ne sono 9"
    monkey = E.BZ.MIN_FOTO; E.BZ.MIN_FOTO = 5
    try:
        op(c, op="stella", photo="V10"); op(c, op="tolta", photo="V07")
        p = c.post("/api/bozza", {"ritmo": "bianche", "per_spread": 2})
        assert sorted(i for s in p["spreads"] for i in s["foto"]) == sorted(i for i in range(10) if A.name(i) not in ("H01", "V07")), "niente foto usate o tolte"
        sola = next(s for s in p["spreads"] if A.IDX["V10"] - 1 in s["foto"])
        assert [A.IDX["V10"] - 1] in (sola["L"]["photos"], sola["R"]["photos"]), "la foto con la stella da sola su una pagina"
        meno = c.post("/api/bozza", {"spread": 2}); assert len(meno["spreads"]) < len(p["spreads"])
        st = op(c, op="bozza", spreads=p["spreads"]); assert E.SP[0] == prima[0] and st["esito"]["da"] == 1 and st["annulla"]["s"] == 1
        ok, r = c.prova("/api/op", dict(op="bozza", spreads=p["spreads"])); assert not ok and "già in uno spread" in r["errore"]
    finally: E.BZ.MIN_FOTO = monkey


@pytest.mark.parametrize("o, msg", [
    ({"ritmo": "a caso"}, "ritmo non valido"), ({"stelle": 1}, "stelle"), ({"seme": -1}, "seme non valido"), ({"seme": 1.5}, "seme non valido"),
    ({"per_spread": 0.5}, "foto per spread"), ({"per_spread": True}, "foto per spread"), ({"spread": 0}, "numero di spread"),
])
def test_bozza_richieste_sbagliate(editor, o, msg):
    ok, r = editor.prova("/api/bozza", o); assert not ok and msg in r["errore"], r
    ok, r = editor.prova("/api/op", dict(o, op="bozza")); assert not ok and msg in r["errore"], r


@pytest.mark.parametrize("spreads, msg", [
    ("tutti", "spread della bozza non validi"), ([], "spread della bozza non validi"),
    ([{"L": {"mode": "I", "module": "NO", "mirror": False, "photos": [0]}, "R": {"mode": "I", "module": "FULL", "mirror": False, "photos": [1]}}], "spread della bozza non valido"),
    ([{"L": {"mode": "I", "module": "FULL", "mirror": False, "photos": [0, 2]}, "R": {"mode": "I", "module": "FULL", "mirror": False, "photos": [1]}}], "spread della bozza non valido"),
    ([{"L": {"mode": "I", "module": "FULL", "mirror": False, "photos": [99]}, "R": {"mode": "I", "module": "FULL", "mirror": False, "photos": [1]}}], "foto inesistente"),
    (["x"], "spread della bozza non valido"),
])
def test_bozza_spread_sbagliati(editor, spreads, msg):
    ok, r = editor.prova("/api/op", dict(op="bozza", spreads=spreads)); assert not ok and msg in r["errore"], r
    ok, r = editor.prova("/api/op", dict(op="bozza", pos=3)); assert not ok and "posizione inesistente" in r["errore"]


def test_licenze_della_bozza_e_di_sistema(editor, licenza):
    c = editor
    op(c, op="newspreadsel", names=["H01", "H02", "V03"], pos=0); op(c, op="newspreadsel", names=["V04", "Q05"], pos=1)
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    ok, r = c.prova("/api/bozza", {}); assert not ok and r["licenza"] is True and r["errore"] == "L'impaginazione automatica dell'album non fa parte della licenza Essenziale: c'è nelle licenze Pro e Studio."
    assert c.codice("/api/op", {"op": "bozza"}) == 403 and c.codice("/img/bozza/0") == 403
    ok, r = c.prova("/api/op", {"op": "sistema"}); assert not ok and r["errore"].startswith("La correzione degli spazi su tutto l'album non fa parte della licenza Essenziale")
    assert c.codice("/api/op", {"op": "sistema", "spread": [0, 1], "tono": False}) == 403
    assert c.codice("/api/op", {"op": "sistema", "spread": [0], "tono": True}) == 403, "il tono è del pannello del tono"
    st = c.post("/api/op", {"op": "sistema", "spread": [0]}); assert st.get("esito", {"spazi": 0, "tono": 0})["tono"] == 0, "uno spread alla volta, senza tono: in Essenziale c'è"
    assert c.codice("/api/op", {"op": "sistema", "spazi": False, "tono": False}) == 200, "senza spazi né tono non c'è niente da cancellare"
    r = c.post("/api/controlla", {}); assert not any(p["tipo"] == "tono" for p in r["problemi"]), "il controllo c'è in tutte le fasce, il tono solo dove c'è il pannello"
    assert c.codice("/api/controlla", {"tono": True}) == 403 and c.codice("/api/controlla", {"tono": "sì"}) == 400
    licenza.usa(licenza.chiavi.studio)
    assert c.codice("/api/bozza", {}) == 400, "con la licenza Studio la bozza c'è (qui mancano le foto da usare)"
