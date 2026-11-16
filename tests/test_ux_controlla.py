"""UX-014: controllo dell'album come elenco strutturato (blocca / guarda / info) e «Sistema» con un solo passo d'annulla;
il calcolo degli spazi fra le foto è nel motore (motore/spazi.py) e dà lo stesso risultato della pagina."""
import os
import shutil

import pytest
from aiuti import crea_foto

from impaginatore.motore import album as A
from impaginatore.motore import spazi

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
FULL = lambda i: dict(mode="I", module="FULL", mirror=False, photos=[i])
ix = lambda n: A.IDX[n] - 1


def op(c, **o): return c.post("/api/op", o)


def sposta(c, s, d):
    """la foto «davanti» della prima coppia dello spread s si sposta di d px a destra e in basso (e si stringe): uno stacco diverso"""
    R = c.E._rett_spread(s); b = R[spazi.coppie(R, A.G, A.PPI)[0]["b"]]
    op(c, op="setrects", s=s, rects=[[b["side"], b["idx"], b["x"] + d, b["y"] + d, b["w"] - d, b["h"] - d]])


def tipi(r, s=None): return sorted((p["livello"], p["tipo"], p["foto"]) for p in r["problemi"] if s is None or p["s"] == s)


@pytest.fixture
def piccolo(home, apri_editor):
    """album 18 × 6 cm (pagine di 9 × 6, come le foto orizzontali): le foto di prova (900 px) bastano per stampare"""
    p = home.nuovo({"nome": "Controllo", "w": "18", "h": "6"}); crea_foto(os.path.join(p, "Foto")); return apri_editor(p)


# ---------------------------------------------------------------- spazi
def test_spazi_funzioni_pure():
    G, ppi = 30, 300
    a, b = dict(x=0, y=0, w=100, h=100), dict(x=130, y=0, w=100, h=100)
    assert spazi.stato([a, b], G, ppi) == dict(ref=30, n=1, ok=1, diversi=0)
    b2 = dict(b, x=150); assert spazi.stato([a, b2], G, ppi) == dict(ref=30, n=1, ok=0, diversi=1)
    R, ch = spazi.correggi([a, b2], G, ppi); assert ch == 1 and R[1]["x"] == 130 and R[1]["w"] == 120 and spazi.stato(R, G, ppi)["diversi"] == 0
    assert spazi.correggi([a, b], G, ppi) == ([a, b], 0)
    stretta = dict(x=112, y=0, w=10, h=100)
    assert spazi.correggi([a, stretta], G, ppi) == ([a, stretta], 0) and spazi.stato([a, stretta], G, ppi)["diversi"] == 1, "troppo stretta per spostarla: resta da guardare a mano"
    assert spazi.stato([a, b2], G, ppi, "freq")["ref"] == 50 and spazi.stato([a, b2], G, ppi, "custom", 50)["diversi"] == 0
    assert spazi.stato([a, b2], G, ppi, "custom", 0)["ref"] == 30, "valore non valido: lo standard"
    c = dict(x=0, y=140, w=100, h=100); assert spazi.coppie([a, c], G, ppi)[0]["ax"] == "y"
    lontana = dict(x=600, y=0, w=100, h=100); assert spazi.coppie([a, lontana], G, ppi) == [], "oltre il massimo non è una coppia"
    in_mezzo = dict(x=115, y=0, w=5, h=100); assert len(spazi.coppie([a, dict(b, x=135), in_mezzo], G, ppi)) == 2, "con una foto in mezzo, a e b non sono una coppia"
    assert spazi.riferimento([dict(g=40.5)], 30, "freq") == 41, "le metà verso l'alto, come Math.round"
    assert spazi.riferimento([dict(g=40.5), dict(g=40.4), dict(g=20)], 30, "freq") == 40, "a parità, il più vicino allo standard e poi il primo trovato"
    assert spazi.riferimento([dict(g=40), dict(g=20)], 25, "freq") == 20, "a parità di frequenza, il più vicino allo standard"


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_spazi_come_la_pagina(editor, tmp_path):
    """la pagina non rifà i conti degli spazi (T-205): le misure segnate sullo spread sono quelle di /api/spazi e «Correggi
    spazi» manda l'operazione «spazi» del motore, con la misura scelta nel menu; il risultato è quello di correggi_spazi"""
    from cdp import Browser
    c = editor; E = c.E
    for k, names in enumerate((["H01", "H02", "V03"], ["V04", "Q05", "H06", "Q09"], ["H08", "V10", "V07"])):
        op(c, op="newspreadsel", names=names, pos=k)
    for s, d in ((0, 20), (1, 9), (2, 35)): sposta(c, s, d)
    assert all(E.stato_spazi(s)["diversi"] for s in range(3))
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        assert b.js("typeof gapStat") == "undefined" and b.js("typeof gapPairs") == "undefined", "niente conti degli spazi nella pagina"
        for modo, cm in (("std", None), ("freq", None), ("custom", 0.4)):
            gv = f"GAPMODE = {modo!r}; GAPCM = {cm or 0};"
            for s in range(3):
                segni = b.js(f"(async () => {{ {gv} cur = {s}; view = 'album'; GAPCHK = true; render(); for (let i = 0; i < 40 && !gapMarks().length; i++) await new Promise(r => setTimeout(r, 50)); return gapMarks().map(m => [m.ax, m.from, m.to, m.at, m.g, m.c]); }})()")
                py = E.spazi_spread(s, modo, cm)
                assert segni == [[p["ax"], p["da"], p["a"], p["at"], p["g"], "ok" if p["ok"] else "bad"] for p in py["coppie"]], (modo, s)
                preso = b.js(f"(async () => {{ {gv} let preso = null; const vero = op; op = async x => {{ preso = x; return null; }}; try {{ await gapFix({s}, true); }} finally {{ op = vero; }} return preso; }})()")
                assert preso == dict(op="spazi", s=s, modo=modo, **({"cm": cm} if cm else {})), (modo, s)
        prima = E.stato_spazi(0)["diversi"]
        b.js("(async () => { GAPMODE = 'std'; GAPCM = 0; await gapFix(0); })()"); b.pausa(0.5)
        assert prima and E.stato_spazi(0)["diversi"] == 0 and b.js("S.annulla.nome") == "Correggi spazi"
        assert not b.problemi(), b.problemi()


def test_operazione_spazi(editor):
    c = editor; E = c.E
    op(c, op="newspreadsel", names=["H01", "H02", "V03"], pos=0); sposta(c, 0, 20)
    assert E.stato_spazi(0)["diversi"] > 0
    st = op(c, op="spazi", s=0); assert st["esito"]["corretti"] > 0 and st["esito"]["diversi"] == 0 and st["annulla"] == {"nome": "Correggi spazi", "s": 0}
    st = op(c, op="spazi", s=0); assert st["esito"] == {"corretti": 0, "diversi": 0}
    for o, msg in ((dict(op="spazi"), "manca lo spread"), (dict(op="spazi", s=0, modo="x"), "modo degli spazi"), (dict(op="spazi", s=0, modo="custom"), "stacco in cm"),
                   (dict(op="spazi", s=0, modo="custom", cm=11), "stacco in cm"), (dict(op="spazi", s=0, modo="custom", cm=True), "stacco in cm"),
                   (dict(op="sistema", spread=0), "spread non validi"), (dict(op="sistema", spread=[5]), "spread inesistente")):
        ok, r = c.prova("/api/op", o); assert not ok and msg in r["errore"], (o, r)
    st = op(c, op="spazi", s=0, modo="custom", cm=0.5); assert st["esito"]["diversi"] == 0


# ---------------------------------------------------------------- controlla
def test_controlla_trova_i_problemi(piccolo, monkeypatch):
    c = piccolo; E = c.E
    op(c, op="newspread", pos=0, L=FULL(ix("H01")), R=FULL(ix("H02")))          # 0: niente da dire
    op(c, op="newspread", pos=1, L=FULL(ix("V03")), R=FULL(ix("H08")))          # 2: V03 tagliata, H08 senza file
    op(c, op="dup", s=0)                                                         # 1: H01 e H02 ripetute
    op(c, op="blank", pos=3)                                                     # 3: due pagine vuote
    op(c, op="newspread", pos=4, L=FULL(ix("Q05")), R=FULL(ix("Q09")))          # 4: quadrate tagliate, risoluzione, testo fuori
    op(c, op="set", at=[4, "L", 0], z=1.05); op(c, op="set", at=[4, "R", 0], z=1.3)
    op(c, op="addtext", s=4, fx=0.1, fy=0.1, fw=0.1, fh=0.1); op(c, op="addtext", s=4, fx=0.8, fy=0.5, fw=0.1, fh=0.1); op(c, op="free", at=[4, "R", 1], x=0.85, y=0.5, w=0.3, h=0.1)
    op(c, op="stella", photo="V07"); op(c, op="tolta", photo="V10")
    os.remove(os.path.join(c.progetto, "Foto", "H08.jpg"))
    st = c.get("/api/state"); ppi = {(s, e["side"]): e["ppi"] for s in (4,) for e in st["spreads"][s]["items"] if e["k"] != "t"}
    assert 150 <= ppi[(4, "L")] < 200 and ppi[(4, "R")] < 150, ppi
    monkeypatch.setattr(E, "tono_spread", lambda s, over=None, light=False: dict(items=[dict(side="L", idx=0, name="H01", stato="no", d=8)] if s == 0 else []))
    r = c.post("/api/controlla", {})
    assert tipi(r, 0) == [("guarda", "tono", "H01")]
    assert tipi(r, 2) == [("blocca", "mancante", "H08"), ("guarda", "risoluzione", "V03"), ("guarda", "ritaglio", "V03")]
    assert tipi(r, 1) == [("guarda", "ripetuta", "H01"), ("guarda", "ripetuta", "H02")]
    assert tipi(r, 3) == [("guarda", "pagina_vuota", None), ("guarda", "pagina_vuota", None)]
    assert tipi(r, 4) == [("blocca", "fuori_pagina", None), ("blocca", "risoluzione", "Q09"), ("guarda", "risoluzione", "Q05"), ("guarda", "ritaglio", "Q05"), ("guarda", "ritaglio", "Q09")]
    assert [x for x in tipi(r) if x[0] == "info"] == [("info", "non_usata", "H06"), ("info", "non_usata", "V04"), ("info", "stella_non_usata", "V07")]
    assert not any(p["foto"] == "V10" for p in r["problemi"]), "le foto tolte apposta non si segnalano"
    assert [p["livello"] for p in r["problemi"]] == sorted((p["livello"] for p in r["problemi"]), key=("blocca", "guarda", "info").index)
    assert r["conta"]["blocca"] == 3 and r["pronto"] is False and r["sistema"]["tono"] == 1 and r["sistema"]["spazi"] == 0
    tono = next(p for p in r["problemi"] if p["tipo"] == "tono")
    assert tono == dict(livello="guarda", tipo="tono", s=0, side="L", idx=0, foto="H01", testo="Spread 1: H01 è più chiara del resto dell'album", sistema=True)
    r = c.post("/api/controlla", {"spread": [2], "tono": False}); assert tipi(r) == [("blocca", "mancante", "H08"), ("guarda", "risoluzione", "V03"), ("guarda", "ritaglio", "V03")], "solo lo spread chiesto, niente info"
    monkeypatch.setattr(A, "DANNEGGIATE", {"H02.jpg"})
    r = c.post("/api/controlla", {"spread": [0], "tono": False}); assert tipi(r) == [("blocca", "danneggiata", "H02")]
    ok, e = c.prova("/api/controlla", {"modo": "boh"}); assert not ok and "modo degli spazi" in e["errore"]
    op(c, op="free", at=[0, "L", 0], x=-0.9, y=0, w=1, h=1)
    assert ("blocca", "fuori_pagina", "H01") in tipi(c.post("/api/controlla", {"spread": [0], "tono": False})), "oltre l'abbondanza"


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_controlla_al_singolare(piccolo, tmp_path):
    """un problema solo: «1 cosa blocca la stampa» e «1 blocca», non «1 cose bloccano»; la spiegazione di «Sistema» e il suo
    esito nominano solo le correzioni che ci sono («gli spazi di 1 spread», niente «il tono di 0 foto»)"""
    from cdp import Browser
    c = piccolo
    op(c, op="newspread", pos=0, L=FULL(ix("H01")), R=FULL(ix("H08")))
    os.remove(os.path.join(c.progetto, "Foto", "H08.jpg"))
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 1)
        b.js("(async () => { apriControlla(true); for (let i = 0; i < 60 && !(CTL.d && $('ctlsis')); i++) await new Promise(r => setTimeout(r, 50)); })()")
        d = b.js("CTL.d.conta"); assert d["blocca"] == 1 and d["guarda"] == 0, d
        conta = b.js("[...document.querySelectorAll('#insp .conta span')].map(x => x.innerText)")
        assert conta == ["1 blocca", "0 da guardare", f"{d['info']} note"], conta
        assert b.js("$('ctlb').title").startswith("1 cosa blocca la stampa"), b.js("$('ctlb').title")
        assert b.js("ctlSpiega({ spazi: 1, tono: 0, restano: 1 })") == "Sistema corregge da solo gli spazi di 1 spread. Si annulla in un passo. 1 cosa da guardare a mano: clic per andarci."
        assert b.js("ctlSpiega({ spazi: 2, tono: 3, restano: 0 })") == "Sistema corregge da solo gli spazi di 2 spread e il tono di 3 foto. Si annulla in un passo."
        assert b.js("ctlSpiega({ spazi: 0, tono: 0, restano: 2 })") == "2 cose da guardare a mano: clic su una per andarci."
        assert b.js("ctlSpiega({ spazi: 0, tono: 0, restano: 0 })") == "Niente da correggere."
        assert b.js("t('editor.ctl.sistemato', { cosa: ctlCorrezioni(0, 1) })") == "Sistemato: il tono di 1 foto"
        assert b.js("[tn('editor.ctl.info', 1), tn('editor.ctl.pronto_guarda', 1), tn('editor.imp.fatto', 1), tn('editor.prj.mancanti_btn', 1)]") == [
            "1 nota", "Si può stampare; 1 cosa da guardare", "1 foto aggiunta", "⚠ 1 foto mancante"]
        assert not b.problemi(), b.problemi()


def test_controlla_volti(piccolo, monkeypatch):
    c = piccolo; E = c.E
    op(c, op="newspread", pos=0, L=FULL(ix("H01")), R=FULL(ix("V03")))
    v = {e["side"]: e for e in c.get("/api/state")["spreads"][0]["items"]}
    r_ = v["L"]["box"][2]
    F = {"H01.jpg": [[r_ - 0.04, 0.4, r_ - 0.01, 0.5]],                  # vicino al bordo destro della pagina sinistra: la piega
         "V03.jpg": [[0.4, 0.0, 0.6, 1.0], [0.45, 0.0, 0.55, 0.02]]}       # alto: il ritaglio lo taglia (lontano dalla piega); piccolo in cima: tutto fuori
    monkeypatch.setattr(A, "F", F)
    r = E.controlla(tono=False); assert tipi(r, 0) == [("guarda", "risoluzione", "V03"), ("guarda", "ritaglio", "V03"), ("guarda", "volto_piega", "H01"), ("guarda", "volto_tagliato", "V03")]
    monkeypatch.setattr(A, "FACE_FIX", {"H01": (0.5, 0.5)}); r = E.controlla(tono=False)
    assert tipi(r, 0) == [("guarda", "risoluzione", "V03"), ("guarda", "ritaglio", "V03"), ("guarda", "volto_tagliato", "V03")], "volto messo a mano: il fotografo l'ha già guardato"


def test_sistema_un_solo_passo(piccolo, monkeypatch):
    c = piccolo; E = c.E
    op(c, op="newspreadsel", names=["H01", "H02", "V03"], pos=0); op(c, op="newspreadsel", names=["V04", "Q05"], pos=1)
    sposta(c, 0, 12)
    vero = E.tono_spread
    voci = [dict(side="L", idx=0, name="V04", stato="no", d=-9, compl=dict(ev=0.6, rit=dict(omb=10))), dict(side="L", idx=0, name="V04", stato="no", d=-9, compl=dict(ev=0.6, rit={})),
            dict(side="R", idx=0, name="Q05", stato="att", d=3)]
    finto = lambda s, over=None, light=False: dict(items=voci) if s == 1 else vero(s, over, light)
    monkeypatch.setattr(E, "tono_spread", finto)
    assert E.stato_spazi(0)["diversi"]; prima = E.snap(); n = len(E.UNDO)
    r = c.post("/api/controlla", {}); assert r["sistema"]["spazi"] == 1 and r["sistema"]["tono"] >= 1
    st0 = E.stato_spazi(0); spazi_ = [p["testo"] for p in r["problemi"] if p["tipo"] == "spazi"]
    assert st0["diversi"] == 1 and spazi_ == [f"Spread 1: 1 stacco su {st0['n']} diverso da 0,25 cm"], (st0, spazi_)
    st = op(c, op="sistema"); assert st["esito"] == dict(spazi=1, tono=1) and st["annulla"] == {"nome": "Sistema album", "s": None}
    assert len(E.UNDO) == n + 1 and E.stato_spazi(0)["diversi"] == 0
    assert E.CFG["esposizione"]["per_foto"]["V04"] == 0.6 and E.CFG["ritocco"]["V04"] == {"omb": 10} and "Q05" not in E.CFG["esposizione"]["per_foto"]
    op(c, op="undo"); assert E.snap() == prima
    st = op(c, op="sistema", spread=[1], tono=False); assert st["esito"] == dict(spazi=0, tono=0) and len(E.UNDO) == n, "niente da fare: nessun passo"
    st = op(c, op="sistema", spread=[0], spazi=False); assert st["esito"]["spazi"] == 0
