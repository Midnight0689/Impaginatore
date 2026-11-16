"""Operazioni del motore per l'interfaccia e per l'MCP (PIANO-UX, passo 2): ogni passo d'annulla ha un nome e uno spread,
le operazioni di un gruppo diventano un passo solo (UX-003); «Altra disposizione» (D) scorre le disposizioni sul posto
(UX-001); «sostituisci» cambia la foto e riadatta lo spread se la nuova foto viene tagliata troppo (UX-002)."""
import pytest

from impaginatore.motore import album as A

FULL = lambda i: dict(mode="I", module="FULL", mirror=False, photos=[i])


def op(c, **o): return c.post("/api/op", o)


def foto(E, s, side=None):
    return [A.name(it["i"]) for k, pg in enumerate(E.SP[s]) if side in (None, "LR"[k]) for it in pg[1] if it["k"] != "t"]


def test_annulla_dice_cosa_e_dove(editor):
    c = editor; ix = lambda n: A.IDX[n] - 1
    st = c.get("/api/state"); assert st["annulla"] is None and st["ripeti"] is None
    st = op(c, op="newspread", pos=0, L=FULL(ix("H01")), R=FULL(ix("H02")))
    assert st["annulla"] == {"nome": "Nuovo spread", "s": 0} and st["ripeti"] is None
    op(c, op="newspread", pos=1, L=FULL(ix("V03")), R=FULL(ix("V04")))
    st = op(c, op="stella", photo="H01"); assert st["annulla"] == {"nome": "Stella", "s": None}, "non tocca uno spread"
    st = op(c, op="dup", s=0); assert st["annulla"] == {"nome": "Duplica spread", "s": 1}, "lo spread nuovo"
    st = op(c, op="delete", s=2); assert st["annulla"] == {"nome": "Elimina spread", "s": 2}
    st = op(c, op="set", at=[0, "L", 0], bw=True); assert st["annulla"] == {"nome": "Modifica cornice", "s": 0}
    st = op(c, op="undo"); assert st["annullato"] == {"nome": "Modifica cornice", "s": 0} and st["ripeti"] == {"nome": "Modifica cornice", "s": 0}
    st = op(c, op="undo"); assert st["annullato"] == {"nome": "Elimina spread", "s": 2} and len(st["spreads"]) == 3
    assert st["annulla"] == {"nome": "Duplica spread", "s": 1} and st["ripeti"] == {"nome": "Elimina spread", "s": 2}
    st = op(c, op="redo"); assert st["ripetuto"] == {"nome": "Elimina spread", "s": 2} and len(st["spreads"]) == 2
    for _ in range(6): op(c, op="undo")
    st = op(c, op="undo"); assert st["annullato"] is None and st["annulla"] is None and len(st["spreads"]) == 0, "niente da annullare"
    st = op(c, op="redo"); assert st["ripetuto"] == {"nome": "Nuovo spread", "s": 0}
    for _ in range(6): op(c, op="redo")
    st = op(c, op="redo"); assert st["ripetuto"] is None


def test_nomi_e_spread_di_ogni_operazione(editor):
    E = editor.E
    assert all(isinstance(v, str) and v for v in E.NOMI_OP.values())
    assert E.spread_op(dict(op="new", s=3)) == 4 and E.spread_op(dict(op="blank", pos=2)) == 2 and E.spread_op(dict(op="free", at=[5, "L", 0])) == 5
    assert E.spread_op(dict(op="tolta", photo="H01")) is None and E.spread_op(dict(op="new", s=True)) is None and E.spread_op(dict(op="x", at=[])) is None
    st = editor.post("/api/op", dict(op="newspreadsel", names=["H01"], pos=0)); assert st["annulla"]["nome"] == "Nuovo spread"
    E.do_op(dict(op="guides", s=0, v=[10], h=[])); assert E.passi()["annulla"] == {"nome": "Linee guida", "s": 0}
    E.UNDO[-1]["chiave"] = E.NOMI_OP.get("sconosciuta", "server.op_modifica"); assert E.passi()["annulla"]["nome"] == "Modifica"


def test_gruppo_di_operazioni_un_solo_passo(editor):
    c = editor; E = c.E; ix = lambda n: A.IDX[n] - 1
    op(c, op="newspread", pos=0, L=FULL(ix("H01")), R=FULL(ix("H02"))); n = len(E.UNDO); prima = E.snap()
    for z in (1.1, 1.2, 1.3): op(c, op="set", at=[0, "L", 0], z=z, gruppo="zoom-1")
    assert len(E.UNDO) == n + 1 and E.SP[0][0][1][0]["z"] == 1.3
    op(c, op="set", at=[0, "L", 0], z=1.3, gruppo="zoom-1"); assert len(E.UNDO) == n + 1, "niente di cambiato: nessun passo"
    st = op(c, op="undo"); assert E.snap() == prima and st["annullato"] == {"nome": "Modifica cornice", "s": 0}
    op(c, op="redo"); op(c, op="set", at=[0, "L", 0], z=1.5, gruppo="zoom-1")
    assert len(E.UNDO) == n + 2, "dopo un annulla o un ripeti il gruppo ricomincia"
    op(c, op="set", at=[0, "R", 0], bw=True); op(c, op="set", at=[0, "L", 0], z=1.6, gruppo="zoom-1")
    assert len(E.UNDO) == n + 4, "un'altra operazione in mezzo separa i passi"
    op(c, op="set", at=[0, "L", 0], z=1.7, gruppo="altro"); assert len(E.UNDO) == n + 5
    for g in ("", "x" * 101, 3):
        ok, r = c.prova("/api/op", dict(op="set", at=[0, "L", 0], z=1.1, gruppo=g)); assert not ok and "gruppo non valido" in r["errore"]


def test_altra_disposizione_scorre_e_torna(editor):
    c = editor; E = c.E
    op(c, op="newspreadsel", names=["H01", "H02", "V03", "Q05"], pos=0); prima = E.snap(); n = len(E.UNDO)
    ordine, k, side = E.disposizioni(0); tot = len(ordine)
    assert tot >= 4 and k is not None and side is None
    viste = set(); st = None
    for j in range(1, tot + 1):
        st = op(c, op="disposizione", s=0); e = st["esito"]
        assert e["di"] == tot and e["disposizione"] == (k + j) % tot + 1 and e["a_mano"] is False and e["taglia"] >= 1
        viste.add(E.snap()); assert sorted(foto(E, 0)) == ["H01", "H02", "Q05", "V03"]
    assert E.snap() == prima and len(viste) == tot, "giro completo: tutte diverse, si torna a quella di partenza"
    assert len(E.UNDO) == n + 1, "un solo passo per tutto il giro"
    st = op(c, op="disposizione", s=0); st = op(c, op="disposizione", s=0, passo=-1); assert E.snap() == prima
    op(c, op="disposizione", s=0); op(c, op="disposizione", s=0)
    st = op(c, op="undo"); assert st["annullato"] == {"nome": "Altra disposizione", "s": 0} and E.snap() == prima, "le pressioni di fila: un solo passo"
    # le prime sono quelle che rispettano le foto, poi quelle che tagliano di più
    pesi = [t["worst"] > E.TOLL_PROPORZIONI for t in ordine]; assert pesi == sorted(pesi)


def test_altra_disposizione_su_una_pagina_e_a_mano(editor):
    c = editor; E = c.E
    op(c, op="newspreadsel", names=["H01", "H02", "V03", "Q05"], pos=0); destra = E.SP[0][1]
    st = op(c, op="disposizione", s=0, side="L"); assert st["esito"]["lato"] == "L" and E.SP[0][1] == destra, "l'altra pagina resta com'è"
    it = next(e for e in st["spreads"][0]["items"] if e["side"] == "L")
    op(c, op="free", at=[0, "L", it["idx"]], x=0.1, y=0.1, w=0.3, h=0.3)
    st = op(c, op="disposizione", s=0, side="L"); assert st["esito"]["a_mano"] is True and st["esito"]["disposizione"] == 1
    st = op(c, op="free", at=[0, "L", 0], x=0.2, y=0.1, w=0.3, h=0.3)
    st = op(c, op="disposizione", s=0, side="L", passo=-1); assert st["esito"]["disposizione"] == st["esito"]["di"]


@pytest.mark.parametrize("o, msg", [
    (dict(op="disposizione"), "manca lo spread"), (dict(op="disposizione", s=0, passo=2), "passo non valido"),
    (dict(op="disposizione", s=0, passo=1.0), "passo non valido"), (dict(op="disposizione", s=0, passo=True), "passo non valido"),
    (dict(op="disposizione", s=1), "Non ci sono foto da disporre"), (dict(op="disposizione", s=2), "solo testo"),
    (dict(op="disposizione", s=3, side="testo"), "Questa pagina è di solo testo"), (dict(op="disposizione", s=4), "Non ci sono altre disposizioni"),
    (dict(op="sostituisci", at=[0, "L", 0]), "servono la cornice"), (dict(op="sostituisci", photo="H01"), "servono la cornice"),
])
def test_altra_disposizione_errori(editor, monkeypatch, o, msg):
    c = editor; E = c.E
    op(c, op="newspreadsel", names=["H01", "H02"], pos=0); op(c, op="blank", pos=1)
    op(c, op="blank", pos=2); op(c, op="addtext", s=2, fx=0.1, fy=0.1, fw=0.3, fh=0.1); op(c, op="addtext", s=2, fx=0.6, fy=0.1, fw=0.3, fh=0.1)
    op(c, op="newspreadsel", names=["V03"], pos=3); op(c, op="newspreadsel", names=["Q09"], pos=4)
    testo = "LR"[next(k for k in (0, 1) if not foto(E, 3, "LR"[k]))]; op(c, op="addtext", s=3, fx=0.1 if testo == "L" else 0.6, fy=0.1, fw=0.3, fh=0.1)
    if o.get("side") == "testo": o = dict(o, side=testo)
    vero = E.tpl_options
    monkeypatch.setattr(E, "tpl_options", lambda photos, cur=None, side=None, s=None: (lambda d: dict(d, items=[t for t in d["items"] if t["cur"]], piu=[]))(vero(photos, cur, side, s)))
    prima = E.snap(); ok, r = c.prova("/api/op", o)
    assert not ok and msg in r["errore"], r; assert E.snap() == prima


def test_sostituisci_riadatta_la_pagina(editor):
    c = editor; E = c.E; ix = lambda n: A.IDX[n] - 1
    op(c, op="newspread", pos=0, L=FULL(ix("H01")), R=FULL(ix("H02"))); n = len(E.UNDO); prima = E.snap(); destra = E.SP[0][1]
    st = op(c, op="sostituisci", at=[0, "L", 0], photo="V03")
    e = st["esito"]; assert e["adattata"] is True and e["lato"] == "L" and e["taglia"] <= 1.25 and e["scambiata_con"] is None, e
    assert foto(E, 0) == ["V03", "H02"] and E.SP[0][1] == destra and E.SP[0][0][1][0]["k"] != "full" or E.SP[0][0] != prima
    assert len(E.UNDO) == n + 1 and st["annulla"] == {"nome": "Sostituisci foto", "s": 0}
    op(c, op="undo"); assert E.snap() == prima, "un solo annulla per sostituzione e nuova disposizione"
    st = op(c, op="sostituisci", at=[0, "L", 0], photo="V03", adatta=False)
    assert st["esito"]["adattata"] is False and st["esito"]["taglia"] > 1.25 and E.SP[0][0][0] == "I" and E.SP[0][0][1][0]["k"] == "full"
    op(c, op="undo"); st = op(c, op="sostituisci", at=[0, "L", 0], photo="H08")
    assert st["esito"] == {"scambiata_con": None, "adattata": False, "taglia": st["esito"]["taglia"]} and st["esito"]["taglia"] <= 1.25, "entra bene: niente da riadattare"


def test_sostituisci_con_una_foto_gia_usata(editor):
    c = editor; E = c.E; ix = lambda n: A.IDX[n] - 1
    op(c, op="newspread", pos=0, L=FULL(ix("H01")), R=FULL(ix("H02"))); op(c, op="newspread", pos=1, L=FULL(ix("V03")), R=FULL(ix("H06")))
    st = op(c, op="sostituisci", at=[0, "L", 0], photo="V03")
    assert st["esito"]["scambiata_con"] == 1 and "H01" in foto(E, 1) and "V03" in foto(E, 0)
    st = op(c, op="sostituisci", at=[0, "R", 0], photo="V03"); assert st["esito"]["scambiata_con"] is None, "scambio nello stesso spread"


def test_sostituisci_tutto_lo_spread_quando_la_pagina_non_basta(editor, monkeypatch):
    c = editor; E = c.E; ix = lambda n: A.IDX[n] - 1
    op(c, op="newspread", pos=0, L=FULL(ix("H01")), R=FULL(ix("H02")))
    vero = E.tpl_options
    monkeypatch.setattr(E, "tpl_options", lambda photos, cur=None, side=None, s=None: dict(vero(photos, cur, side, s), items=[]) if side else vero(photos, cur, side, s))
    st = op(c, op="sostituisci", at=[0, "L", 0], photo="V03"); e = st["esito"]
    assert e["adattata"] is True and e["lato"] is None and e["taglia"] <= 1.25
    op(c, op="undo"); monkeypatch.setattr(E, "tpl_options", lambda *a, **k: dict(items=[], piu=[]))
    st = op(c, op="sostituisci", at=[0, "L", 0], photo="V03"); assert st["esito"]["adattata"] is False and st["esito"]["taglia"] > 1.25, "nessuna disposizione migliore: resta la sostituzione"
    op(c, op="undo"); op(c, op="addtext", s=0, fx=0.6, fy=0.1, fw=0.3, fh=0.1)
    E.SP[0][1][1][:] = [it for it in E.SP[0][1][1] if it["k"] == "t"]; assert E.locked_sides(0) == ["R"]
    st = op(c, op="sostituisci", at=[0, "L", 0], photo="V03"); assert st["esito"]["adattata"] is False, "pagina accanto di solo testo e nessuna disposizione per la pagina: lo spread intero non si tocca"
