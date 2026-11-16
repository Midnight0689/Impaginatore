"""Varietà delle disposizioni (docs/architettura/VARIETA.md). Il titolare: «la 1.5.x produceva modelli troppo uguali a
valle della generazione automatica; dovrebbe invece creare modelli molto diversi tra loro». Qui: la misura
(motore/varieta.py), i moduli adattivi e l'ordine delle proposte dell'editor, «Altra disposizione», la scelta degli spread
della bozza. Le foto sono sintetiche: per le proposte e la bozza contano solo proporzioni, date e volti (finti)."""
import math
import random
import time

import pytest

from impaginatore.motore import album as A
from impaginatore.motore import bozza as BZ
from impaginatore.motore import varieta as VA

W, H = 1000, 375                                            # uno spread finto (proporzioni del 60 x 22,5)


def fr(x, y, w, h): return dict(x=x * W, y=y * H, w=w * W, h=h * H)


def dsc(*cc): return VA.descrivi([fr(*c) for c in cc], W, H)


def specchia(cc): return [(1 - x - w, y, w, h) for x, y, w, h in cc]


PIENA = [(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)]                                          # due foto a tutta pagina
GRIGLIA = [(x, y, 0.24, 0.48) for x in (0, 0.25, 0.51, 0.76) for y in (0, 0.52)]     # 2 x 2 per pagina
MOSAICO = [(0, 0, 0.3, 1), (0.31, 0, 0.19, 0.5), (0.31, 0.52, 0.19, 0.48), (0.55, 0.2, 0.4, 0.6)]
PIEGA = [(0.2, 0.1, 0.6, 0.8)]


# ---------------------------------------------------------------- la misura
def test_caselle_e_piega():
    assert VA.caselle([dict(x=-10, y=-5, w=510, h=380), dict(x=10, y=10, w=1, h=100)], W, H) == [(0, 0, 0.5, 1)], "tagliate allo spread, le briciole no"
    assert VA.attraversa_piega([fr(*PIEGA[0])], W) and not VA.attraversa_piega([fr(*c) for c in PIENA], W)


@pytest.mark.parametrize("cas, fam", [
    ([], "vuota"), ([(0, 0, 1, 1)], "intera"), ([(0.2, 0.2, 0.5, 0.5)], "respiro"),
    ([(0.1, 0.1, 0.2, 0.2), (0.4, 0.1, 0.2, 0.2), (0.7, 0.1, 0.2, 0.2)], "respiro"), ([(0, 0, 0.45, 0.45), (0.5, 0.5, 0.45, 0.45)], "respiro"),
    ([(0, 0, 0.6, 1), (0.65, 0, 0.35, 0.5)], "dominante"), ([(0, 0, 0.49, 1), (0.51, 0, 0.49, 1)], "coppia"),
    ([(0, 0.3, 0.32, 0.4), (0.34, 0.3, 0.32, 0.4), (0.68, 0.3, 0.32, 0.4)], "striscia"),
    ([(0, 0, 0.49, 0.49), (0.51, 0, 0.49, 0.49), (0, 0.51, 0.49, 0.49), (0.51, 0.51, 0.49, 0.49)], "griglia"),
    ([(0, 0, 0.5, 1), (0.52, 0, 0.48, 0.6)], "mosaico"),
])
def test_famiglie_di_pagina(cas, fam):
    assert VA.famiglia_pagina(cas) == fam


def test_famiglia_dello_spread_e_schema():
    assert dsc(*PIEGA).fam == "piega" and dsc(*PIEGA).piega
    assert dsc((0, 0, 0.5, 1), (0.55, 0.1, 0.2, 0.3)).fam == "intera+respiro", "le due pagine in ordine alfabetico"
    a, b = dsc(*MOSAICO), dsc(*specchia(MOSAICO))
    assert a.fam == b.fam and a.schema == b.schema and VA.distanza(a, b) == pytest.approx(0, abs=1e-9), "la specchiata è la stessa disposizione"
    assert dsc((0, 0, 0.5, 1), (0.6, 0.2, 0.3, 0.3)).schema != dsc((0, 0, 0.5, 1), (0.6, 0.2, 0.3, 0.4)).schema
    v = VA.descrivi([], W, H); assert v.fam == "vuota+vuota" and v.n == 0 and v.num[3] == 0


def test_pagine_bianche():
    """numero 6 del descrittore: pagine con il margine bianco tutto attorno (vuota vale bianca)"""
    bianche = lambda *cc: dsc(*cc).num[6]
    assert bianche(*PIENA) == 0 and bianche((0.05, 0.1, 0.4, 0.8), (0.55, 0.1, 0.4, 0.8)) == 2
    assert bianche((0.05, 0, 0.4, 0.8)) == 1, "tocca il bordo di sopra; la destra è vuota"
    assert bianche((0.05, 0.2, 0.4, 0.8)) == 1, "tocca il bordo di sotto"
    assert bianche((0, 0.1, 0.4, 0.8), (0.6, 0.1, 0.4, 0.8)) == 0, "toccano i bordi esterni"


def test_distanza():
    p, g, m = dsc(*PIENA), dsc(*GRIGLIA), dsc(*MOSAICO)
    assert VA.distanza(p, g) > 0.5, "due pagine piene contro due griglie: poco in comune"
    assert 0 < VA.distanza(p, m) < 1 and VA.distanza(p, g) == pytest.approx(VA.distanza(g, p))
    vicina = dsc((0, 0, 0.5, 1), (0.5, 0, 0.5, 0.98))
    assert VA.distanza(p, vicina) < 0.1, "spostare una casella di poco non fa una disposizione nuova"


# ---------------------------------------------------------------- ordine delle proposte
def test_ordina_alterna_le_geometrie():
    quasi = [dsc(*PIENA), dsc((0, 0, 0.5, 1), (0.5, 0, 0.5, 0.99)), dsc((0, 0, 0.5, 0.99), (0.5, 0, 0.5, 1))]
    diverse = [dsc(*GRIGLIA), dsc(*MOSAICO), dsc(*PIEGA)]
    descr = quasi + diverse; costi = [0.0, 0.01, 0.02, 0.1, 0.12, 0.14]
    o = VA.ordina(descr, costi)
    assert o[0] == 0 and set(o[1:4]) == {3, 4, 5}, "dopo la migliore, le diverse prima delle quasi uguali (meno costose)"
    assert sorted(o) == list(range(6)) and VA.ordina(descr, costi) == o, "tutte, sempre nello stesso ordine"
    assert VA.ordina(descr, costi, primo=4)[0] == 4
    o2 = VA.ordina(descr, costi, quanti=2); assert o2[:2] == o[:2] and o2[2:] == sorted(o2[2:]), "dopo le prime «quanti», per costo"
    assert VA.ordina([], []) == [] and VA.ordina([descr[0]], [0.3]) == [0]
    m = VA.misura_proposte([descr[k] for k in o[:4]]); prima = VA.misura_proposte(descr[:4])
    assert m["famiglie"] > prima["famiglie"] and m["media"] > prima["media"] and m["doppioni"] < prima["doppioni"]


def test_ripetizioni():
    p, g, m, x = dsc(*PIENA), dsc(*GRIGLIA), dsc(*MOSAICO), dsc(*PIEGA)
    assert len(VA.ripetizioni([], [p])) == 0
    r = VA.ripetizioni([p, g], [p])
    assert r[0] >= VA.SCHEMA_RIPETUTO + VA.PESI_VICINI[0] - 1e-9 and r[1] < r[0], "ripetere lo spread appena prima costa"
    storia = [p, m, g, m, g, m, g]                              # p è il settimo prima: fuori dai vicini, dentro la finestra
    r = VA.ripetizioni([p], storia); assert r[0] >= VA.SCHEMA_RIPETUTO and VA.ripetizioni([p], storia, finestra=6)[0] < VA.SCHEMA_RIPETUTO
    assert VA.ripetizioni([x], [x, g, m])[0] - VA.ripetizioni([x], [g, m])[0] >= VA.PIEGA_VICINA, "due spread a cavallo della piega vicini"
    assert VA.ripetizioni([p], [])[0] == 0


def test_misure():
    p, g, m = dsc(*PIENA), dsc(*GRIGLIA), dsc(*MOSAICO)
    assert VA.misura_proposte([p]) == dict(famiglie=1, media=0.0, minima=0.0, doppioni=0)
    assert VA.misura_proposte([p, p, g])["doppioni"] == 1
    s = VA.misura_sequenza([p, g, p, m, m])
    assert s["spread"] == 5 and s["schemi"] == 3 and s["ripetuti"] == 2 and s["stessa_famiglia"] == 1 and 0 < s["vicini"] < 1
    assert VA.misura_sequenza([p])["vicini"] == 0.0 and VA.misura_sequenza([])["spread"] == 0


# ---------------------------------------------------------------- foto sintetiche nell'editor
T0 = time.mktime((2026, 5, 23, 10, 0, 0, 0, 0, -1))


def insieme(n, tipo, seme=1):
    """n foto finte in ordine di scatto: proporzioni secondo il tipo, un capitolo nuovo ogni 37 foto"""
    rnd = random.Random(seme * 7919 + n); out = []; t = T0
    for k in range(n):
        r = rnd.random()
        if tipo == "orizzontali": ar = rnd.choice([1.5, 1.5, 1.5, 1.333, 1.778])
        elif tipo == "verticali": ar = rnd.choice([0.667, 0.667, 0.667, 0.75, 0.5625])
        elif tipo == "miste": ar = 1.5 if r < .55 else (0.667 if r < .92 else 1.0)
        else: ar = 1.5 if r < .5 else 0.667 if r < .82 else 1.0 if r < .9 else rnd.choice([2.2, 3.0])
        t += rnd.choice([20, 40, 90, 150]) + (3600 if k and k % 37 == 0 else 0)
        out.append(dict(n=f"F{k:04d}.jpg", ar=ar, dt=time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(t)), src=""))
    return out


@pytest.fixture
def finte(editor, monkeypatch):
    """l'editor con le foto finte al posto di quelle del progetto (solo in memoria: niente si salva)"""
    E = editor.E

    def usa(meta, volti=None):
        monkeypatch.setattr(A, "M", meta); monkeypatch.setattr(A, "IDX", {m["n"].rsplit(".", 1)[0]: k + 1 for k, m in enumerate(meta)})
        monkeypatch.setattr(A, "F", volti or {}); monkeypatch.setattr(A, "FACE_FIX", {}); monkeypatch.setitem(E.CFG, "stelle", [])
        return E
    return usa


def descr(E, t): return VA.descrivi(t["frames"], E.VW, E.VH)


def test_moduli_adattivi(editor, apri_editor, home):
    """le cornici dei moduli adattivi stanno nella pagina, non si sovrappongono, hanno fra loro almeno lo spazio G e le
    proporzioni delle foto (3:2 o 2:3) dove la ricetta le fissa, su un formato panoramico e su uno quadrato; lo
    specchio rovescia la pagina"""
    esatte = {"GO6", "GV4", "GV6", "SO3", "SR3", "SV4", "DO3", "DO4", "DV3", "MO4", "RO1", "RV2"}
    q = home.nuovo({"nome": "Quadrato", "w": "30", "h": "30"})
    for c in (editor, apri_editor(q)):
        E = c.E
        for nome, (_, modo, verticale) in E.ADATTIVI.items():
            (x0, x1), (y0, y1) = A._frame("L", modo)
            per = {}
            for m in (False, True):
                lay = [L for L in A.layout(((modo, E.BUILD[nome](list(range(1, E.NPH[nome] + 1)), m)), ("W", []))) if L["k"] != "t"]
                assert len(lay) == E.NPH[nome] and all(L["side"] == "L" for L in lay), nome
                R = [(L["x"], L["y"], L["W"], L["H"]) for L in lay]; per[m] = sorted(R)
                for x, y, w, h in R: assert x0 - 1 <= x and x + w <= x1 + 1 and y0 - 1 <= y and y + h <= y1 + 1 and w > 0 and h > 0, (nome, m)
                for i, a in enumerate(R):
                    for b in R[i + 1:]:
                        dx = max(b[0] - (a[0] + a[2]), a[0] - (b[0] + b[2])); dy = max(b[1] - (a[1] + a[3]), a[1] - (b[1] + b[3]))
                        assert max(dx, dy) >= A.G - 2, (nome, m, a, b)
                if nome in esatte:
                    for _, _, w, h in R: assert min(abs(math.log(w / h / ar)) for ar in (E.OR, E.VE)) < 0.02, (nome, w / h)
            rov = sorted(((x, y0 + y1 - y - h, w, h) if verticale else (x0 + x1 - x - w, y, w, h)) for x, y, w, h in per[False])
            assert all(max(abs(u - v) for u, v in zip(a, b)) <= 2 for a, b in zip(rov, per[True])), nome
    assert len(E.LAYS) == len(set(E.LAYS)) and all(k in E.NPH for k, _, _ in E.LAYS)


def test_proposte_varie(finte):
    """le prime 8 proposte per le stesse foto: almeno 3 famiglie in media e pochi doppioni (la 1.5.x: meno di 2,2 famiglie
    e 5-11 coppie quasi uguali su 28); la prima è la meno costosa fra quelle con i moduli di sempre (quella che la 1.5.x
    metteva prima), se una di loro rispetta le foto"""
    for tipo in ("orizzontali", "verticali", "miste"):
        E = finte(insieme(40, tipo)); fam = media = doppioni = 0; k = 0
        for n in (2, 3, 4, 5, 6):
            for start in (0, 12):
                ix = list(range(start, start + n)); d = E.tpl_options(ix)
                m = VA.misura_proposte([descr(E, t) for t in d["items"][:8]]); fam += m["famiglie"]; media += m["media"]; doppioni += m["doppioni"]; k += 1
                assert all("fam" in t for t in d["items"] + d["piu"]) and d["vista"] == [E.VW, E.VH]
                sc = E.tpl_options(ix, vario=False)["items"]
                assert [t["cost"] for t in sc] == sorted(t["cost"] for t in sc) and "fam" not in sc[0], "senza varietà: per costo"
                cl = [t for t in sc if E._classica(t)]; prima = min(cl or sc, key=lambda t: t["cost"])       # nessun modulo di sempre rispetta le foto: la migliore
                assert d["items"][0]["cost"] == prima["cost"] and E._classica(d["items"][0]) == bool(cl), (tipo, n)
        assert fam / k >= 3 and media / k >= 0.4 and doppioni / k <= 2, (tipo, fam / k, media / k, doppioni / k)


def test_proposte_casi_limite(finte):
    E = finte([dict(n=f"P{k}.jpg", ar=5.0, dt="", src="") for k in range(3)] + [dict(n="Q.jpg", ar=1.5, dt="", src="")])
    d = E.tpl_options([0, 1, 2])
    assert d["items"] and all(t["worst"] > E.TOLL_PROPORZIONI for t in d["items"]), "nessuna rispetta le foto: le meno peggio, cercate fra tutte"
    assert E.tpl_options([])["items"] == [] and E.ordine_vario([], 0) == [] and E.ordine_disposizioni([]) == []
    ad = [dict(L=dict(module="GO6"), R=dict(module="FO3"))]; assert E._primo(ad, [0.1]) is None and not E._classica(ad[0])
    assert E._classica(dict(R=dict(module="FULL"))), "una pagina sola (l'altra è di testo)"


def test_volti_a_rischio(finte, monkeypatch):
    """un volto noto tagliato oltre il 15 % o nella zona della piega conta; quelli centrati a mano no"""
    E = finte([dict(n="A.jpg", ar=1.5, dt="", src=""), dict(n="B.jpg", ar=1.5, dt="", src="")], {"A.jpg": [(0.45, 0.3, 0.55, 0.5)], "B.jpg": [(0.1, 0.1, 0.9, 0.9)]})
    met = E.VW / 2; h = E.VH
    sinistra = dict(x=0, y=0, w=met - 100, h=(met - 100) / 1.5); piega = dict(x=met - 400, y=0, w=800, h=800 / 1.5); stretta = dict(x=0, y=0, w=h * 0.3, h=h)
    assert E._volti_a_rischio([sinistra], [0]) == 0 and E._volti_a_rischio([piega], [0]) == 1, "sulla piega"
    assert E._volti_a_rischio([stretta], [1]) == 1, "il volto non entra nella cornice stretta"
    assert E._volti_a_rischio([dict(x=0, y=0, w=0, h=10)], [1]) == 0 and E._volti_a_rischio([piega], [1]) == 1
    monkeypatch.setattr(A, "FACE_FIX", {"A": (0.5, 0.4)}); assert E._volti_a_rischio([piega], [0]) == 0, "centrato a mano: è una scelta"
    assert E._zona_piega() == pytest.approx(E.PIEGA_CM / 2.54 * A.PPI)
    monkeypatch.setitem(E.CFG, "prodotto", {"prodotto": {"piega_mm": 20}}); assert E._zona_piega() == pytest.approx(2 / 2.54 * A.PPI)
    monkeypatch.setattr(A, "FACE_FIX", {})
    d = E.tpl_options([0, 1]); assert any(t.get("volti") for t in d["items"] + d["piu"]) and not d["items"][0].get("volti"), "la prima proposta non taglia i volti"


def test_altra_disposizione_varia(editor):
    """«Altra disposizione»: dopo quelle che rispettano le foto, alternate per famiglia e geometria, quelle che tagliano di
    più; l'esito dice la famiglia. Pressioni di fila: in media molto diverse dalla precedente (la 1.5.x: 0,21-0,30)"""
    c = editor; E = c.E
    st = c.post("/api/op", dict(op="newspreadsel", names=["H01", "H02", "V03", "V04"], pos=0))
    ordine, k, _ = E.disposizioni(0)
    buone = [t for t in ordine if t["worst"] <= E.TOLL_PROPORZIONI]; altre = ordine[len(buone):]
    assert all(t["worst"] > E.TOLL_PROPORZIONI for t in altre) and [t["worst"] for t in altre] == sorted(t["worst"] for t in altre)
    dd = [VA.distanza(descr(E, a), descr(E, b)) for a, b in zip(buone[:10], buone[1:10])]
    assert sum(dd) / len(dd) >= 0.4, dd
    st = c.post("/api/op", dict(op="disposizione", s=0, passo=1, rev=st["rev"]))
    assert st["esito"]["famiglia"] in {t["fam"] for t in ordine} and st["esito"]["disposizione"] >= 1


# ---------------------------------------------------------------- la bozza
def _sp(fam_frames, L="X", R="Y", cost=0.1, worst=0.1, photos=((0,), (1,)), mL="I", mR="I"):
    return dict(cost=cost, worst=worst, frames=[fr(*c) for c in fam_frames], L=dict(mode=mL, module=L, mirror=False, photos=list(photos[0])),
                R=dict(mode=mR, module=R, mirror=False, photos=list(photos[1])))


def test_scegli_con_la_misura():
    vista = [W, H]; sole = set()
    piena, griglia, piega = _sp(PIENA, "A", "A"), _sp(GRIGLIA[:2], "B", "B", cost=0.15), _sp(PIEGA + [(0.85, 0.1, 0.1, 0.2)], "C", "C", cost=0.05)
    d = dict(items=[piena, griglia, piega], vista=vista)
    t, x = BZ._scegli(d, 0, "piene", sole, [], None, [], piega=False); assert t is piena and x.fam == "intera+intera", "a cavallo della piega solo se si può"
    t, _ = BZ._scegli(d, 0, "piene", sole, [], None, []); assert t is piega, "si può: è la meno costosa"
    t, _ = BZ._scegli(dict(items=[piega], vista=vista), 0, "piene", sole, [], None, [], piega=False); assert t is piega, "se attraversano tutte, si prende comunque"
    t, _ = BZ._scegli(d, 0, "piene", sole, [], None, [VA.descrivi(piena["frames"], W, H)], piega=False); assert t is griglia, "non ripete lo spread appena prima"
    tagliata = _sp(GRIGLIA[2:4], "D", "D", cost=0.0, worst=0.4)
    t, _ = BZ._scegli(dict(items=[piena, tagliata], vista=vista), 0, "piene", sole, [], None, [VA.descrivi(piena["frames"], W, H)]); assert t is piena, "la varietà non taglia oltre ×1,25"
    peggio = _sp(GRIGLIA[2:4], "D", "D", worst=0.5); meno = _sp(PIENA, "A", "A", worst=0.3)
    t, _ = BZ._scegli(dict(items=[meno, peggio], vista=vista), 0, "piene", sole, [], None, [VA.descrivi(meno["frames"], W, H)]); assert t is meno, "se tagliano tutte, non oltre la meno tagliata"
    vuota = _sp(PIENA[:1], "A", "BLANK", cost=0.0, photos=((0,), ()))
    t, _ = BZ._scegli(dict(items=[vuota, griglia], vista=vista), 0, "piene", sole, [], None, []); assert t is griglia, "una pagina vuota è un difetto"
    bianca = _sp(GRIGLIA[:2], "E", "E", mL="W", mR="W", cost=0.0)
    t, _ = BZ._scegli(dict(items=[bianca, griglia], vista=vista), 0, "piene", sole, [], None, []); assert t is griglia, "il ritmo scelto"
    assert BZ._scegli(dict(items=[], vista=vista), 0, "piene", sole, [], None) == (None, None)


def test_duro():
    vista = (W, H); sola = _sp([(0, 0, 0.5, 1), (0.6, 0.4, 0.1, 0.1)], photos=((0,), (1,)))
    assert BZ._duro(sola, {0}, vista) == 0 and BZ._duro(sola, {1}, vista) == 1, "la foto sola in una cornice piccola"
    assert BZ._duro(_sp(PIENA, photos=((0, 1), ())), {0}, vista) == 1 and BZ._duro(dict(sola, volti=2), set(), vista) == 2


def test_proposta_con_la_misura():
    """con la misura (vista) ogni spread ha famiglia e schema e la bozza non ripete lo stesso schema: con tre geometrie
    possibili per ogni gruppo le usa tutte e mai la stessa due volte di fila (la 1.5.x: sempre la meno costosa, salvo
    la terza volta)"""
    geo = [PIENA, GRIGLIA[:2], MOSAICO[:2]]
    opzioni = lambda ix: dict(items=[_sp(g, chr(65 + k), chr(65 + k), cost=0.05 * k, photos=((ix[0],), tuple(ix[1:]))) for k, g in enumerate(geo)], vista=[W, H])
    foto = [dict(i=i, dt=f"2026:05:23 10:{i:02d}:00", ar=1.5) for i in range(24)]
    p = BZ.proposta(foto, opzioni, per_spread=2)
    assert len(p["spreads"]) >= 8 and all(s["fam"] and s["schema"] for s in p["spreads"]) and p["schemi"] == 3
    sch = [s["schema"] for s in p["spreads"]]; assert all(a != b for a, b in zip(sch, sch[1:])), sch
    v = BZ.proposta(foto, lambda ix: dict(items=opzioni(ix)["items"]), per_spread=2)          # senza la misura: come la 1.5.x
    mods = [s["L"]["module"] for s in v["spreads"]]; assert v["schemi"] == 0 and {s["fam"] for s in v["spreads"]} == {None} and any(a == b for a, b in zip(mods, mods[1:]))
    assert BZ.proposta(foto, opzioni, per_spread=2, seme=4) == BZ.proposta(foto, opzioni, per_spread=2, seme=4), "stesso seme, stessa bozza"
    assert BZ.schemi([dict(schema=None), dict(schema="a"), dict(schema="a"), dict()]) == 1


@pytest.mark.parametrize("tipo", ["orizzontali", "verticali", "miste", "panoramiche"])
def test_bozza_varia_e_senza_difetti_nuovi(finte, tipo):
    """120 foto sintetiche: la bozza usa tante geometrie e non ne ripete una entro 8 spread più di rado (la 1.5.x: 8-24
    schemi, 9-30 ripetizioni); niente pagine vuote fuori da quelle che servono, foto sole mai in cornici piccole né
    divise, ritaglio medio non oltre ×1,2"""
    E = finte(insieme(120, tipo)); E.CFG["stelle"] = [A.name(k) for k in range(120) if k % 17 == 5]
    p = E.bozza({}); sp = p["spreads"]
    ds = []
    for s in sp:
        tup = tuple((s[x]["mode"], E.BUILD[s[x]["module"]]([i + 1 for i in s[x]["photos"]], bool(s[x]["mirror"]))) for x in "LR")
        ds.append(VA.descrivi([dict(x=L["x"] - E.BL, y=L["y"] - E.BL, w=L["W"], h=L["H"]) for L in A.layout(tup) if L["k"] != "t"], E.VW, E.VH))
    m = VA.misura_sequenza(ds)
    assert m["schemi"] == p["schemi"] and m["schemi"] >= 18 and m["ripetuti"] <= 5, (tipo, m)
    assert [s["schema"] for s in sp].count(None) == 0 and all(s["fam"] == d.fam for s, d in zip(sp, ds))
    assert sum(1 for s in sp if "BLANK" in (s["L"]["module"], s["R"]["module"])) <= 2
    sole = {k for k in range(120) if k % 17 == 5 or A.M[k]["ar"] >= BZ.PANORAMICA}
    assert all(BZ._duro(dict(s, frames=[dict(x=L["x"] - E.BL, y=L["y"] - E.BL, w=L["W"], h=L["H"]) for L in sorted(A.layout(tuple((s[x]["mode"], E.BUILD[s[x]["module"]]([i + 1 for i in s[x]["photos"]], bool(s[x]["mirror"]))) for x in "LR")), key=lambda L: L.get("_o", 0)) if L["k"] != "t"]), sole, (E.VW, E.VH)) == 0
               for s in sp if "BLANK" not in (s["L"]["module"], s["R"]["module"])), "foto sole grandi e da sole"
    assert sum(s["taglia"] for s in sp) / len(sp) <= 1.2


def test_bozza_senza_piega_se_il_prodotto_ha_la_zona(finte, monkeypatch):
    """con un prodotto che ha una zona della piega, nessuno spread della bozza ha una foto a cavallo della piega"""
    E = finte(insieme(120, "orizzontali")); monkeypatch.setitem(E.CFG, "prodotto", {"prodotto": {"piega_mm": 10}})
    for s in E.bozza({"seme": 3})["spreads"]:
        tup = tuple((s[x]["mode"], E.BUILD[s[x]["module"]]([i + 1 for i in s[x]["photos"]], bool(s[x]["mirror"]))) for x in "LR")
        assert not VA.attraversa_piega([dict(x=L["x"] - E.BL, w=L["W"]) for L in A.layout(tup) if L["k"] != "t"], E.VW), s
