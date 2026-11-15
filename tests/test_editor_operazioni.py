"""Operazioni dell'editor (apply, valida e do_op di editor/server.py) nello stesso processo, sul progetto dello scenario 1.5.2
(cornici della griglia e libere, angolo, bordo, ombra, testo con uno stile). Ogni prova guarda quello che l'operazione
cambia (impaginazione, geometria in pixel, impostazioni del progetto); annulla riporta lo stato di prima; i dati che non
vanno si rifiutano con un messaggio e senza toccare lo stato (BUG-001)."""
import json
import os
import shutil

import pytest
from aiuti import crea_foto

from impaginatore import formato
from impaginatore.editor import server as E
from impaginatore.motore import album as A
from impaginatore.motore import testo as TX

P152 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati", "progetto_152")


@pytest.fixture(scope="module")
def _modello(tmp_path_factory):
    """il progetto 1.5.2 com'era salvato (spec.py e progetto.json), preparato una volta per tutto il file"""
    p = os.path.join(str(tmp_path_factory.mktemp("operazioni")), "Parità àè"); crea_foto(os.path.join(p, "Foto"))
    shutil.copy(os.path.join(P152, "spec.py"), p)
    with open(os.path.join(P152, "progetto.json"), encoding="utf-8") as f: cfg = json.loads(f.read().replace("{PROGETTO}", p.replace("\\", "/")))
    formato.scrivi_json(os.path.join(p, "progetto.json"), cfg, indent=2, ensure_ascii=False)
    return p


@pytest.fixture
def ed(_modello, tmp_path):
    """editor (il modulo, senza server) su una copia del progetto 1.5.2: ogni prova parte dallo stesso stato. La prima apre il
    modello (conversione da spec.py, miniature, volti); le copie hanno la cache pronta e lasciano le foto nel modello, dove le
    cercano progetto.json e la cache"""
    if not os.path.exists(os.path.join(_modello, "album.json")): E.inizializza(_modello)
    q = os.path.join(str(tmp_path), "copia"); shutil.copytree(_modello, q, ignore=shutil.ignore_patterns("Foto"))
    E.inizializza(q)
    assert len(A.M) == 10 and not A.SCARTATE and all(os.path.dirname(m["src"]) == os.path.join(_modello, "Foto") for m in A.M)
    assert len(E.SP) == 5 and E.unused() == ["V07"] and not E.UNDO
    return E


def _i(n): return A.IDX[n] - 1


def _el(s, side, idx): return E.SP[s][0 if side == "L" else 1][1][idx]


def _px(s, side, idx):
    """(x, y, larghezza, altezza) in pixel dello spread, come li disegna il motore"""
    L = E._rects(s)[(side, idx)]; return L["x"], L["y"], L["W"], L["H"]


def _centro(r): return r[0] + r[2] / 2, r[1] + r[3] / 2


def _vicini(a, b, tol=1.0): assert all(abs(x - y) <= tol for x, y in zip(a, b)), (a, b)


def _op(**o): E.do_op(o)


def _rifiutata(o, msg, errore=ValueError):
    """l'operazione si ferma con questo messaggio e non lascia niente: stesso stato, niente da annullare"""
    prima, n = E.snap(), len(E.UNDO)
    with pytest.raises(errore, match=msg): E.do_op(dict(o))
    assert E.snap() == prima and len(E.UNDO) == n


def _senza_effetto(o):
    """l'operazione riesce ma non cambia niente: nessun passo da annullare"""
    prima, n = E.snap(), len(E.UNDO)
    E.do_op(dict(o))
    assert E.snap() == prima and len(E.UNDO) == n


def _annulla(prima, passi=1):
    for _ in range(passi): E.do_op(dict(op="undo"))
    assert E.snap() == prima


def _vecchio_testo(s, side, kind="title", c=0, r=0, w=12, h=8, **k):
    """blocco titolo («title») o crediti («end») sulla griglia, come nei progetti delle versioni 1.x: indice nella pagina"""
    pg = E.SP[s][0 if side == "L" else 1][1]; pg.append(dict(k="t", kind=kind, c=c, r=r, w=w, h=h, **k)); return len(pg) - 1


# ---------------------------------------------------------------- do_op, valida
def test_operazione_sconosciuta(ed):
    _rifiutata(dict(op="boh"), "operazione sconosciuta: boh")


def test_modulo_o_modello_che_non_esistono(ed):
    """un modulo di pagina che non c'è: KeyError dal catalogo dei modelli; un modello dell'utente eliminato: messaggio chiaro"""
    v07 = _i("V07")
    _rifiutata(dict(op="newspread", L=dict(mode="W", module="NONESISTE", photos=[v07]), R=dict(mode="W", module="BLANK", photos=[])), "NONESISTE", KeyError)
    _rifiutata(dict(op="newspread", L=dict(mode="W", module="U:abcd:L", photos=[v07]), R=dict(mode="W", module="BLANK", photos=[])), "modello non trovato")


def test_modifica_da_unaltra_scheda(ed):
    """due schede sullo stesso progetto: chi lavora su uno stato vecchio (numero di revisione superato da un'altra scheda) si ferma"""
    _op(op="evg", value=0.5, cid="a", rev=0)
    assert E.REV == 1 and E.LASTC == "a"
    _rifiutata(dict(op="evg", value=1.0, cid="b", rev=0), "modificato da un'altra scheda")
    assert E.CFG["esposizione"]["globale"] == 0.5
    _op(op="evg", value=0.75, cid="a", rev=0)                     # la stessa scheda continua
    _op(op="evg", value=1.0, cid="b", rev=2)                      # l'altra, dopo aver ricaricato lo stato
    assert E.CFG["esposizione"]["globale"] == 1.0 and E.LASTC == "b"


@pytest.mark.parametrize("op", ["dup", "move", "swappages", "delete"])
@pytest.mark.parametrize("s", [5, -1])
def test_spread_che_non_esiste(ed, op, s):
    """lo spread si controlla prima dell'operazione (valida): nessuna operazione lo cerca più per conto suo"""
    _rifiutata(dict(op=op, s=s, to=0), "spread inesistente")


@pytest.mark.parametrize("op", ["newspreadsel", "addtospread"])
def test_foto_sconosciuta_tra_quelle_trascinate(ed, op):
    _rifiutata(dict(op=op, s=0, names=["H01", "NON-ESISTE"]), "foto sconosciuta: 'NON-ESISTE'")


# ---------------------------------------------------------------- foto nelle cornici
def test_sostituisci_foto(ed):
    """«replace»: una foto libera entra nella cornice; una già usata si scambia con quella della cornice; la stessa resta"""
    prima = E.snap()
    _op(op="replace", at=[0, "R", 0], photo="V07")
    assert _el(0, "R", 0)["i"] == _i("V07") and E.unused() == ["V10"]
    _op(op="replace", at=[0, "R", 0], photo="H01")
    assert _el(0, "R", 0)["i"] == _i("H01") and _el(1, "R", 0)["i"] == _i("V07")
    _senza_effetto(dict(op="replace", at=[0, "R", 0], photo="H01"))
    _annulla(prima, 2)
    _rifiutata(dict(op="swap", a=[1, "L", 1], b=[1, "R", 0]), "elemento di testo")


def test_sposta_la_foto_nella_cornice(ed):
    """«pan»: la finestra di ritaglio parte dal punto chiesto (in frazioni della foto, dentro la foto); diventa il centro dei volti
    della foto, che il motore usa per ritagliarla"""
    prima = E.snap(); at = [0, "R", 1]
    l, t, r, b = A.zcrop(E._rects(0)[("R", 1)]); h = b - t
    assert (l, r) == (0, 1) and 0.7 < h < 0.8, "foto quadrata in una cornice orizzontale: si taglia in altezza"
    _op(op="pan", at=at, l=0.3, t=1)
    assert E.CFG["centri_volto"]["Q09"] == [0.5, round(1 - h + 0.42 * h, 4)] and A.FACE_FIX["Q09"] == tuple(E.CFG["centri_volto"]["Q09"])
    _vicini(A.zcrop(E._rects(0)[("R", 1)]), (0, 1 - h, 1, 1), 1e-3)
    _op(op="pan", at=at, l=0, t=-2)
    _vicini(A.zcrop(E._rects(0)[("R", 1)]), (0, 0, 1, h), 1e-3)
    _annulla(prima, 2)
    assert "Q09" not in E.CFG["centri_volto"] and "Q09" not in A.FACE_FIX
    _rifiutata(dict(op="pan", at=[1, "L", 1], l=0, t=0), "elemento di testo")


def test_bordo_ombra_opacita(ed):
    """«set»: bordo (mm, colore #rrggbb; fino a 40 mm), opacità e ombra (0-100); valori nulli o sbagliati li tolgono"""
    at = [3, "L", 1]; prima = E.snap()
    assert {k: _el(*at)[k] for k in ("bd", "sh", "oc")} == dict(bd=[3.0, "#ffffff"], sh=40, oc=80)
    _op(op="set", at=at, bd=[100, "#ABCDEF"], oc=150, sh=None)
    it = _el(*at); assert it["bd"] == [40.0, "#abcdef"] and "oc" not in it and "sh" not in it
    _op(op="set", at=at, bd=[2, "rosso"], oc=-5, sh=250)
    it = _el(*at); assert "bd" not in it and it["oc"] == 0 and it["sh"] == 100
    _op(op="set", at=at, bd=[2.25, "#000000"], oc=99.6, sh=0.4)
    it = _el(*at); assert it["bd"] == [2.2, "#000000"] and "oc" not in it and "sh" not in it
    _op(op="set", at=at, bd=None)
    assert "bd" not in _el(*at)
    _annulla(prima, 4)


def test_proporzione_delle_cornici(ed):
    """«ratio»: stessa area e stesso centro con la proporzione chiesta; se non ci sta, si riduce alla pagina; i testi restano"""
    prima = E.snap(); testo = dict(_el(1, "L", 1)); r0 = _px(1, "L", 0); r1 = _px(1, "R", 0)
    _op(op="ratio", s=1, r=1, ats=[["L", 0], ["L", 1]])
    r = _px(1, "L", 0); it = _el(1, "L", 0)
    assert it["k"] == "f" and it["z"] == 1.0 and abs(r[2] - r[3]) <= 1 and abs(r[2] * r[3] / (r0[2] * r0[3]) - 1) < 0.002
    _vicini(_centro(r), _centro(r0)); assert _el(1, "L", 1) == testo
    _op(op="ratio", s=1, r=10, ats=[["R", 0]])
    (x0, x1), _ = A._frame("R", "W"); r = _px(1, "R", 0)
    assert abs(r[2] - (x1 - x0)) <= 1 and abs(r[2] / r[3] - 10) < 0.05, "larga quanto la pagina, non di più"
    _vicini(_centro(r), _centro(r1))
    _annulla(prima, 2)


def test_esposizione_a_zero(ed):
    """esposizione generale e di una foto: zero (al centesimo) vuol dire nessuna correzione, e non resta nel progetto"""
    prima = E.snap(); esp = E.CFG["esposizione"]
    _op(op="evg", value=0.004)
    assert "globale" not in esp
    _op(op="ev", photo="H01", value=0.333)
    assert esp["per_foto"] == dict(V03=0.5, H01=0.33)
    _op(op="ev", photo="V03", value=-0.004)
    assert esp["per_foto"] == dict(H01=0.33)
    _annulla(prima, 3)


def test_testi_del_titolo(ed):
    """«testo»: nome, sottotitolo e data dell'album (senza spazi ai lati) anche nel motore, che li disegna"""
    prima = E.snap()
    _op(op="testo", nome="  Nuovo nome ", data="2026", altro="x")
    assert E.CFG["testo"] == dict(nome="Nuovo nome", sottotitolo="", data="2026") and A.TITLE == ("Nuovo nome", "", "2026")
    _annulla(prima); assert A.TITLE == ("Parità àè", "", "")


# ---------------------------------------------------------------- tono, ritocco, etichette
def test_correzioni_del_tono_in_un_passo(ed):
    """«tono_fix»: esposizione (±2 EV, zero = tolta) e ritocco di alteluci, ombre e bianchi (±100, zero = tolto) in un solo annulla"""
    prima = E.snap(); pf = E.CFG["esposizione"]["per_foto"]
    _op(op="tono_fix", items=[dict(photo="H01", ev=3, rit=dict(alt=30, omb=0, bia=-150, con=50)), dict(photo="V03", ev=0), dict(photo="Q05", ev=-0.5, rit=dict(omb=12.4))])
    assert pf == dict(H01=2.0, Q05=-0.5) and E.CFG["ritocco"]["H01"] == dict(alt=30, bia=-100), "solo alt, omb e bia; V03 torna a zero"
    assert E.CFG["ritocco"]["Q05"] == dict(tmp=-25, omb=12), "il resto del ritocco resta"
    _op(op="tono_fix", items=[dict(photo="H01", ev=0.001, rit=dict(alt=0, bia=0))])
    assert "H01" not in pf and "H01" not in E.CFG["ritocco"]
    _annulla(prima, 2)


def test_riferimento_e_zona_del_tono(ed):
    """«tono_L»: riferimento (L* 30-75) e zona giusta (4-30); il valore standard non si scrive nel progetto"""
    prima = E.snap()
    assert E.CFG["tono_L"] == 60.0
    _op(op="tono_L", value=E.TONO_L0 + 0.01)
    assert "tono_L" not in E.CFG
    _op(op="tono_L", zona=100)
    assert E.CFG["tono_Z"] == 30.0 and "tono_L" not in E.CFG
    _op(op="tono_L", zona=E.TONO_Z0)
    assert "tono_Z" not in E.CFG
    _annulla(prima, 3)


@pytest.mark.parametrize("op, chiave", [("tono_escl", "tono_escl"), ("stella", "stelle"), ("tolta", "tolte")])
def test_elenchi_di_foto(ed, op, chiave):
    """foto escluse dal tono, preferite e tolte: si aggiungono una volta sola e si tolgono solo se ci sono"""
    E.CFG[chiave][:] = ["H01"]; prima = E.snap()
    _op(op=op, photos=["H01", "H02"], value=True)
    assert E.CFG[chiave] == ["H01", "H02"]
    _op(op=op, photo="V03")
    assert E.CFG[chiave] == ["H01", "H02", "V03"]
    _op(op=op, photos=["H01", "Q05"], value=False)
    assert E.CFG[chiave] == ["H02", "V03"]
    _senza_effetto(dict(op=op, photo="Q05", value=False))
    _annulla(prima, 3)


def test_etichette_colore(ed):
    prima = E.snap()
    _op(op="colore", photos=["H01", "V03"], value="verde")
    assert E.CFG["colori"] == dict(H02="rosso", H01="verde", V03="verde")
    _op(op="colore", photos=["H02", "H01"], value=None)
    assert E.CFG["colori"] == dict(V03="verde")
    _rifiutata(dict(op="colore", photo="V03", value="nero"), "colore sconosciuto")
    _rifiutata(dict(op="colore", photo="V03", value=""), "colore sconosciuto")
    _annulla(prima, 2)


def test_ritocco(ed):
    """«rit»: una regolazione (±100, zero = tolta; senza regolazioni la foto non ha ritocco), copia di un ritocco, azzera (anche il tono)"""
    prima = E.snap(); rit = E.CFG["ritocco"]
    _op(op="rit", photo="V04", key="con", value=0)
    assert rit["V04"] == dict(vib=20)
    _op(op="rit", photo="V04", key="vib", value=0.3)
    assert "V04" not in rit
    _op(op="rit", photos=["H01", "H02"], key="sat", value=-250)
    assert rit["H01"] == rit["H02"] == dict(sat=-100)
    _op(op="rit", photos=["H01", "V10"], copia=dict(con=10, tmp=-5))
    assert rit["H01"] == rit["V10"] == dict(con=10, tmp=-5)
    _op(op="rit", photos=["Q05", "H01"], reset=True)
    assert "Q05" not in rit and "H01" not in rit and "Q05" not in E.CFG["tono"]
    _rifiutata(dict(op="rit", photo="H01", key="boh", value=10), "regolazione sconosciuta")
    _annulla(prima, 5)


def test_livelli_e_curva(ed):
    """«tono»: neri, bianchi (almeno 2 sopra i neri), mezzitoni (0,1-5) e punti della curva, limitati e in ordine; i valori neutri non restano"""
    prima = E.snap()
    _op(op="tono", photo="Q05", value=dict(b=-5, w=1, m=9, c=[[300, -4], [0, 128.4]]))
    assert E.CFG["tono"]["Q05"] == dict(w=2, m=5, c=[[1, 128], [254, 0]])
    _op(op="tono", photo="Q05", value=dict(b=0, w=255, m=1, c=[]))
    assert "Q05" not in E.CFG["tono"]
    _annulla(prima, 2)
    _op(op="tono", photo="Q05", value=None)
    assert "Q05" not in E.CFG["tono"]


# ---------------------------------------------------------------- testi
def test_testo_con_stile(ed):
    """uno stile vale per tutti i testi che lo usano: cambiare il corpo di uno lo cambia a tutti; l'altezza segue il testo
    solo se è automatica"""
    prima = E.snap()
    _op(op="addtext", s=4, fx=0.6, fy=0.1, fw=0.3, tx="Nota")
    assert _el(4, "R", 0)["kind"] == "txt" and _el(4, "R", 0)["size"] == round(A.CH * 0.035)
    _op(op="stile_applica", at=[4, "R", 0], nome="Titolo")
    it = _el(4, "R", 0); assert it["stile"] == "Titolo" and (it["size"], it["col"], it["al"]) == (150.0, [200, 30, 30], "center")
    (x0, x1), (y0, y1) = A._frame("R", "W"); assert it["fh"] == round(TX.fit_height(it, it["fw"] * (x1 - x0)) / (y1 - y0), 4)
    _op(op="settext", at=[4, "R", 0], auto=False)
    fh_fisso, fh_auto = _el(4, "R", 0)["fh"], _el(1, "L", 1)["fh"]
    _op(op="settext", at=[1, "L", 1], size=300)
    assert E.CFG["stili"]["Titolo"]["size"] == 300.0 and _el(4, "R", 0)["size"] == _el(1, "L", 1)["size"] == 300.0
    assert _el(4, "R", 0)["fh"] == fh_fisso and _el(1, "L", 1)["fh"] > fh_auto
    _op(op="settext", at=[4, "R", 0], tx="Nota lunga")                 # non tocca lo stile: l'altezza resta quella scelta
    assert _el(4, "R", 0)["fh"] == fh_fisso and E.CFG["stili"]["Titolo"]["size"] == 300.0
    _rifiutata(dict(op="settext", at=[1, "L", 0], tx="x"), "non è un livello di testo")
    _annulla(prima, 5)


def test_stili_salva_applica_scollega_elimina(ed):
    prima = E.snap()
    _op(op="stile_salva", at=[1, "L", 1], nome="  Grande  ")
    assert E.CFG["stili"]["Grande"] == E.CFG["stili"]["Titolo"] and _el(1, "L", 1)["stile"] == "Grande"
    for o in (dict(at=[1, "L", 0], nome="X"), dict(at=[1, "L", 1], nome="   ")): _rifiutata(dict(op="stile_salva", **o), "serve un testo e un nome")
    _op(op="addtext", s=4, fx=0.1, fy=0.1, fw=0.3, tx="Due")
    _op(op="settext", at=[4, "L", 1], auto=False); fh = _el(4, "L", 1)["fh"]
    _op(op="stile_applica", at=[4, "L", 1], nome="Grande")
    assert _el(4, "L", 1)["stile"] == "Grande" and _el(4, "L", 1)["size"] == 150.0 and _el(4, "L", 1)["fh"] == fh, "altezza scelta a mano: resta"
    for o in (dict(at=[4, "L", 1], nome="Boh"), dict(at=[4, "L", 0], nome="Grande")): _rifiutata(dict(op="stile_applica", **o), "stile inesistente")
    _op(op="stile_scollega", at=[4, "L", 1])
    assert "stile" not in _el(4, "L", 1) and "Grande" in E.CFG["stili"]
    _op(op="stile_applica", at=[4, "L", 1], nome="Grande")
    _op(op="stile_elimina", nome="Grande")
    assert "Grande" not in E.CFG["stili"] and "stile" not in _el(4, "L", 1) and "stile" not in _el(1, "L", 1) and "Titolo" in E.CFG["stili"]
    _annulla(prima, 7)


def test_titolo_e_crediti_delle_1x_diventano_testi(ed):
    """«t2x»: il vecchio blocco del titolo (centrato) o dei crediti (a sinistra, con la sua scala) diventa un livello di testo per
    riga non vuota (nome, sottotitolo, data), nella stessa posizione"""
    _op(op="testo", sottotitolo="Sotto"); ti = _vecchio_testo(4, "R"); cr = _vecchio_testo(0, "L", "end", r=4, w=6, h=4, ts=1.5)
    prima = E.snap(); X, Y, W, H = _px(4, "R", ti)
    _op(op="t2x", at=[4, "R", ti])
    righe = E.SP[4][1][1]; (x0, x1), (y0, y1) = A._frame("R", "W")
    assert [(t["kind"], t["tx"], t["font"], t["size"], t["al"], t["tr"]) for t in righe] == [("txt", "Parità àè", "Didot-Italic", 380.0, "center", 0), ("txt", "Sotto", "AvenirNext-Regular", 62.0, "center", 355)]
    _vicini([y0 + t["fy"] * (y1 - y0) for t in righe], [Y + H / 2 - 260, Y + H / 2 + 260])
    assert all(abs(x0 + t["fx"] * (x1 - x0) - X) < 1 and abs(t["fw"] * (x1 - x0) - W) < 1 for t in righe)
    X, Y, W, H = _px(0, "L", cr)
    _op(op="t2x", at=[0, "L", cr])
    righe = E.SP[0][0][1]; (x0, x1), (y0, y1) = A._frame("L", "W")
    assert [(t["tx"], t["size"], t["al"], t["tr"]) for t in righe] == [("Parità àè", 255.0, "left", 0), ("Sotto", 93.0, "left", 225)]
    _vicini([y0 + t["fy"] * (y1 - y0) for t in righe], [Y + H - 600, Y + H - 255])
    _senza_effetto(dict(op="t2x", at=[1, "L", 1]))
    _annulla(prima, 2)


def test_scala_dei_vecchi_testi(ed):
    """«tscale»: scala dei caratteri di un blocco di testo (0,2-6; 1 = nessuna)"""
    k = _vecchio_testo(4, "R"); prima = E.snap()
    _op(op="tscale", at=[4, "R", k], ts=10)
    assert _el(4, "R", k)["ts"] == 6.0
    _op(op="tscale", at=[4, "R", k], ts=1)
    assert "ts" not in _el(4, "R", k)
    _rifiutata(dict(op="tscale", at=[4, "L", 0], ts=2), "non è un testo")
    _annulla(prima, 2)


def test_testo_spostato_o_ridimensionato(ed):
    """«free» su un testo: l'altezza segue il contenuto, se non la si fissa (autoh False); la scala ts si può cambiare insieme"""
    prima = E.snap(); (x0, x1), (y0, y1) = A._frame("L", "W")
    _op(op="free", at=[1, "L", 1], x=0.1, y=0.2, w=0.5, h=0.6, ts=9)
    it = _el(1, "L", 1)
    assert (it["fx"], it["fy"], it["fw"], it["ts"], it["auto"]) == (0.1, 0.2, 0.5, 6.0, True)
    assert it["fh"] == round(TX.fit_height(it, 0.5 * (x1 - x0)) / (y1 - y0), 4) < 0.6
    _op(op="free", at=[1, "L", 1], x=0.1, y=0.2, w=0.5, h=0.6, autoh=False)
    it = _el(1, "L", 1); assert it["fh"] == 0.6 and it["auto"] is False
    _annulla(prima, 2)


# ---------------------------------------------------------------- moduli e modelli
def test_modulo_di_pagina(ed):
    """«module»: la pagina prende il modulo con le sue foto (e quelle libere se ne servono di più); le altre tornano libere"""
    prima = E.snap()
    _op(op="module", s=0, side="R", module="D2B", mirror=True)
    assert E.SP[0][1] == ["I", [dict(k="p", i=_i("V10"), c=4, r=0, w=8, h=8, bw=False, z=1.0), dict(k="p", i=_i("Q09"), c=0, r=0, w=4, h=8, bw=False, z=1.0)]]
    assert E.unused() == ["H06", "V07"]
    _op(op="module", s=4, side="R", module="FULL")
    assert E.SP[4][1] == ["W", [dict(k="full", i=_i("H06"), bw=False, z=1.0)]]
    _rifiutata(dict(op="module", s=4, side="R", module="S6"), "non ci sono abbastanza foto libere")
    _vecchio_testo(2, "R")
    _rifiutata(dict(op="module", s=2, side="R", module="FULL"), "la pagina ha un testo")
    _annulla(prima, 2)


def test_aggiungi_allo_spread_e_riorganizza(ed):
    """foto lasciate su uno spread: entrano come cornici libere (e lasciano lo spread dove erano); «reorg» poi applica un altro modello"""
    prima = E.snap()
    _op(op="addtospread", s=4, names=["V07", "H08", "H01"])
    foto = sorted(it["i"] for pg in E.SP[4] for it in pg[1]); assert foto == sorted([_i("H08"), _i("V07"), _i("H01")])
    assert E.SP[1][1][1] == [] and not any(t["cur"] for t in E.templates(4)["items"]), "cornici libere: nessun modello corrisponde"
    _annulla(prima)
    _op(op="addtospread", s=4, names=["V07"], how="reorg")
    assert sorted(it["i"] for pg in E.SP[4] for it in pg[1]) == sorted([_i("H08"), _i("V07")])
    assert E.templates(4)["items"][0]["cur"], "ora lo spread è uno dei modelli"
    _annulla(prima)
    _vecchio_testo(4, "L"); _vecchio_testo(4, "R")
    _rifiutata(dict(op="addtospread", s=4, names=["V07"], how="reorg"), "nessun altro modello adatto")


# ---------------------------------------------------------------- cornici: griglia, libere, pagine
def test_cornice_sulla_griglia(ed):
    """«frame»: la cornice va sulle celle chieste (anche una libera, che perde angolo e stile), dentro la pagina e senza sovrapposizioni"""
    prima = E.snap()
    _op(op="frame", at=[3, "L", 1], c=6, r=0, w=6, h=8)
    assert _el(3, "L", 1) == dict(k="p", i=_i("V04"), c=6, r=0, w=6, h=8, bw=False, z=1.0)
    _annulla(prima)
    _rifiutata(dict(op="frame", at=[1, "L", 1], c=0, r=0, w=2, h=2), "il testo non si ridimensiona")
    for c, r, w, h in ((10, 0, 4, 4), (0, 0, 0, 4), (-1, 0, 2, 2), (0, 5, 2, 4)): _rifiutata(dict(op="frame", at=[0, "R", 1], c=c, r=r, w=w, h=h), "la cornice esce dalla pagina")
    _rifiutata(dict(op="frame", at=[0, "R", 1], c=4, r=0, w=4, h=4), "si sovrappone a un'altra cornice")
    k = _vecchio_testo(4, "R", c=0, r=0, w=4, h=2)
    _op(op="addframe", s=4, side="R")
    assert [_el(4, "R", k + 1)[c] for c in "crwh"] == [0, 2, 12, 6], "sotto il vecchio blocco di testo, non sopra"
    _rifiutata(dict(op="frame", at=[4, "R", k + 1], c=2, r=0, w=4, h=4), "si sovrappone a un'altra cornice")


def test_sposta_sullaltra_pagina(ed):
    """«crosspage»: la cornice (o il testo, con la sua scala) passa all'altra pagina come cornice libera, nella posizione chiesta"""
    prima = E.snap()
    _rifiutata(dict(op="crosspage", at=[0, "R", 1], to="R", x=0, y=0, w=0.5, h=0.5), "stessa pagina")
    _op(op="crosspage", at=[0, "R", 1], to="L", x=0.1, y=0.1, w=0.3, h=0.3)
    assert len(E.SP[0][1][1]) == 2 and E.SP[0][0][1] == [dict(k="f", i=_i("Q09"), x=0.1, y=0.1, w=0.3, h=0.3, bw=False, z=1.0)]
    (x0, x1), (y0, y1) = A._frame("L", "W"); _vicini(_px(0, "L", 0), (x0 + 0.1 * (x1 - x0), y0 + 0.1 * (y1 - y0), 0.3 * (x1 - x0), 0.3 * (y1 - y0)))
    _op(op="crosspage", at=[1, "L", 1], to="R", x=5, y=-3, w=0.01, h=0.2, ts=3)
    t = E.SP[1][1][1][-1]
    assert (t["kind"], t["ts"], t["fx"], t["fy"], t["fw"]) == ("txt", 3.0, 1.97, -0.5, 0.03) and len(E.SP[1][0][1]) == 1
    _annulla(prima, 2)


def test_aggancia_alla_griglia(ed):
    """«snap»: la cornice libera va sulle celle più vicine ai suoi bordi; le altre e i testi restano; se si sovrapporrebbe, no"""
    prima = E.snap(); r0 = _px(4, "L", 0); gr = E.page_grid("L", "W"); px, py = gr["xs"][1] - gr["xs"][0], gr["ys"][1] - gr["ys"][0]
    _op(op="snap", at=[4, "L", 0])
    it = _el(4, "L", 0); x, y, w, h = _px(4, "L", 0)
    assert it["k"] == "p" and x == gr["xs"][it["c"]] and x + w == gr["xe"][it["c"] + it["w"] - 1] and y == gr["ys"][it["r"]] and y + h == gr["ye"][it["r"] + it["h"] - 1]
    assert all(abs(a - b) <= p / 2 for a, b, p in ((x, r0[0], px), (y, r0[1], py), (x + w, r0[0] + r0[2], px), (y + h, r0[1] + r0[3], py))), "i bordi più vicini"
    _annulla(prima)
    _senza_effetto(dict(op="snap", at=[0, "R", 0]))
    _senza_effetto(dict(op="snap", at=[1, "L", 1]))
    _rifiutata(dict(op="snap", at=[3, "L", 1]), "si sovrapporrebbe a un'altra cornice")


def test_nuova_cornice_nello_spazio_libero(ed):
    """«addframe»: la cornice nuova occupa il rettangolo libero più grande della pagina (le cornici libere occupano le celle
    il cui centro coprono), con la prima foto libera o quella scelta"""
    prima = E.snap(); v07 = _i("V07")
    _op(op="addframe", s=4, side="L", photo="V07")
    assert _el(4, "L", 1) == dict(k="p", i=v07, c=0, r=5, w=12, h=3, bw=False, z=1.0)
    _annulla(prima)
    _op(op="addframe", s=2, side="R", photo="V07")
    assert _el(2, "R", 1) == dict(k="p", i=v07, c=0, r=0, w=5, h=8, bw=False, z=1.0)
    _annulla(prima)
    _op(op="addframe", s=4, side="R")
    assert E.SP[4][1][1] == [dict(k="p", i=v07, c=0, r=0, w=12, h=8, bw=False, z=1.0)]
    _rifiutata(dict(op="addframe", s=4, side="L"), "non ci sono foto libere")
    _rifiutata(dict(op="addframe", s=0, side="R"), "la pagina è piena")
    _annulla(prima)
    _rifiutata(dict(op="addframe", s=4, side="R", photo="H01"), "non ci sono foto libere")


def test_foto_libera_dove_la_lasci(ed):
    """«putfree»: cornice libera centrata nel punto (frazioni dello spread), larga 55 % della pagina con le proporzioni della foto,
    ma alta al massimo 85 % della pagina; una foto già usata no"""
    prima = E.snap()
    _op(op="putfree", s=4, photo="V07", fx=0.75, fy=0.5)
    (x0, x1), (y0, y1) = A._frame("R", "W"); r = _px(4, "R", 0)
    assert abs(r[3] - 0.85 * (y1 - y0)) <= 1 and abs(r[2] / r[3] - A.M[_i("V07")]["ar"]) < 0.002 and r[2] < 0.55 * (x1 - x0)
    _vicini(_centro(r), (0.75 * A.CW, 0.5 * A.CH))
    _annulla(prima)
    _rifiutata(dict(op="putfree", s=4, photo="H01", fx=0.7, fy=0.5), "la foto è già in uno spread")


def test_livelli_davanti_e_dietro(ed):
    """«zorder»: le foto scelte (e quelle della griglia che toccano) diventano libere nella stessa posizione, poi davanti, dietro,
    un livello avanti o indietro"""
    prima = E.snap(); r = {k: _px(3, "L", k) for k in (0, 1)}
    _op(op="zorder", s=3, ats=[["L", 1]], dir="back")
    v = {e["idx"]: e for e in E.spread_view(3)["items"] if e["side"] == "L"}
    assert v[1]["zr"] < v[0]["zr"] and _el(3, "L", 0)["k"] == "f" and _el(3, "L", 0)["bw"] and _el(3, "L", 0)["z"] == 1.4, "V03 toccata: libera, sopra V04"
    assert _el(3, "R", 0)["k"] == "p", "Q05 non tocca V04: resta sulla griglia"
    for k in (0, 1): _vicini(_px(3, "L", k), r[k])
    _annulla(prima)
    zr = lambda: [{e["idx"]: e["zr"] for e in E.spread_view(0)["items"]}[k] for k in range(3)]
    _op(op="zorder", s=0, ats=[["R", 0], ["R", 1], ["R", 2]], dir="front")
    assert [it["k"] for it in E.SP[0][1][1]] == ["f"] * 3 and zr() == [0, 1, 2]
    _op(op="zorder", s=0, ats=[["R", 0]], dir="forward")
    assert zr() == [1, 0, 2]
    _op(op="zorder", s=0, ats=[["R", 2]], dir="backward")
    assert zr() == [2, 0, 1]
    _op(op="zorder", s=0, ats=[["R", 1], ["R", 2]], dir="forward")
    assert zr() == [0, 1, 2]
    _senza_effetto(dict(op="zorder", s=0, ats=[["R", 0]], dir="backward"))
    _annulla(prima, 4)


def test_stessa_misura(ed):
    """«equalize»: le cornici scelte prendono la misura di quella di riferimento, ciascuna attorno al suo centro (i testi restano)"""
    prima = E.snap(); testo = dict(_el(1, "L", 1)); ref = _px(1, "L", 1); r0 = _px(1, "R", 0)
    _op(op="equalize", s=1, ref=["L", 1], ats=[["L", 1], ["R", 0]])
    r = _px(1, "R", 0); _vicini(r[2:], ref[2:]); _vicini(_centro(r), _centro(r0))
    assert _el(1, "L", 1) == testo and _el(1, "R", 0)["k"] == "f"
    _annulla(prima)


def test_proporzioni_originali(ed):
    """«origar»: la cornice prende le proporzioni della foto (stessa larghezza, o l'altezza della pagina se non ci sta), zoom a 1"""
    prima = E.snap(); r0 = _px(3, "L", 0)
    _op(op="origar", s=3, ats=[["L", 0]])
    r = _px(3, "L", 0)
    assert _el(3, "L", 0)["z"] == 1.0 and abs(r[2] - r0[2]) <= 1 and abs(r[2] / r[3] - A.M[_i("V03")]["ar"]) < 0.002
    _vicini(_centro(r), _centro(r0))
    _op(op="free", at=[0, "R", 0], x=0, y=0.1, w=1, h=0.5)
    testo = dict(_el(1, "L", 1))
    _op(op="origar", s=0, ats=[["R", 0]])
    _op(op="origar", s=1, ats=[["L", 1]])
    r = _px(0, "R", 0); assert abs(r[3] - A.CH) <= 1 and abs(r[2] / r[3] - A.M[_i("V10")]["ar"]) < 0.002, "alta quanto la pagina"
    assert _el(1, "L", 1) == testo
    _annulla(prima, 3)


def test_tutta_la_pagina(ed):
    """«fullpage»: la foto copre tutta la sua pagina fino al bordo, anche su una pagina con margine; i testi restano"""
    prima = E.snap(); testo = dict(_el(1, "L", 1))
    _op(op="fullpage", s=1, ats=[["L", 0], ["L", 1]])
    (x0, x1), (y0, y1) = A._frame("L", "I"); _vicini(_px(1, "L", 0), (x0, y0, x1 - x0, y1 - y0))
    assert _el(1, "L", 1) == testo
    _annulla(prima)


def test_verticali_o_orizzontali(ed):
    """«orient»: scambia larghezza e altezza delle cornici che non hanno l'orientamento chiesto (centro fermo, dentro la pagina)"""
    prima = E.snap(); r0 = _px(4, "L", 0); testo = dict(_el(1, "L", 1))
    _op(op="orient", s=4, ats=[["L", 0]], dir="v")
    r = _px(4, "L", 0); _vicini(r[2:], (r0[3], r0[2])); _vicini(_centro(r), _centro(r0))
    _senza_effetto(dict(op="orient", s=4, ats=[["L", 0]], dir="v"))
    r1 = _px(1, "L", 0)
    _op(op="orient", s=1, ats=[["L", 0], ["L", 1]], dir="v")
    (x0, x1), (y0, y1) = A._frame("L", "W"); r = _px(1, "L", 0)
    assert abs(r[3] - (y1 - y0)) <= 1 and abs(r[2] / r[3] - r1[3] / r1[2]) < 0.002, "ridotta all'altezza della pagina"
    assert _el(1, "L", 1) == testo
    r2 = _px(0, "R", 0)
    _op(op="orient", s=0, ats=[["R", 0]], dir="h")
    _vicini(_px(0, "R", 0)[2:], (r2[3], r2[2]))
    _annulla(prima, 3)


def test_sposta_un_gruppo(ed):
    """«nudge»: le cornici scelte si spostano insieme; quella il cui centro passa la piega va sull'altra pagina; i testi no"""
    prima = E.snap(); r1, r2 = _px(0, "R", 1), _px(0, "R", 2); testo = dict(_el(1, "L", 1))
    _op(op="nudge", s=0, ats=[["R", 1], ["R", 2]], dx=-3000, dy=10)
    assert [it["i"] for it in E.SP[0][1][1]] == [_i("V10")] and sorted(it["i"] for it in E.SP[0][0][1]) == sorted([_i("Q09"), _i("H06")])
    nuove = {_el(0, "L", k)["i"]: _px(0, "L", k) for k in range(2)}
    _vicini(nuove[_i("Q09")], (r1[0] - 3000, r1[1] + 10, r1[2], r1[3])); _vicini(nuove[_i("H06")], (r2[0] - 3000, r2[1] + 10, r2[2], r2[3]))
    _op(op="nudge", s=1, ats=[["L", 0], ["L", 1]], dx=0, dy=-50)
    assert _el(1, "L", 1) == testo; _vicini(_px(1, "L", 0), (396, 424 - 50, 2751, 1809))
    _annulla(prima, 2)


def test_misure_di_piu_cornici(ed):
    """«setrects»: posizione e misura in pixel della vista per più cornici, in un solo annulla; pagine, indici e testi che non vanno si saltano"""
    prima = E.snap(); testo = dict(_el(1, "L", 1))
    _op(op="setrects", s=1, rects=[["L", 0, 500, 600, 1000, 800], ["X", 0, 1, 1, 10, 10], ["R", 9, 1, 1, 10, 10], ["L", 1, 1, 1, 10, 10]])
    _vicini(_px(1, "L", 0), (500, 600, 1000, 800)); assert _el(1, "L", 1) == testo and _el(1, "R", 0)["k"] == "p"
    assert len(E.UNDO) == 1
    _annulla(prima)


def test_ingrandisci_un_gruppo(ed):
    """«gscale»: le cornici scelte si ingrandiscono o rimpiccioliscono attorno a un punto fisso (scala 0,1-10); i testi restano"""
    prima = E.snap(); testo = dict(_el(1, "L", 1))
    _op(op="gscale", s=1, ats=[["L", 0], ["L", 1]], sx=0.5, sy=0.25, ax=396, ay=424)
    _vicini(_px(1, "L", 0), (396, 424, 2751 * 0.5, 1809 * 0.25)); assert _el(1, "L", 1) == testo
    _op(op="gscale", s=0, ats=[["R", 1], ["R", 2]], sx=0.01, sy=1, ax=5338, ay=0)
    _vicini(_px(0, "R", 1), (5338, 0, 1749 * 0.1, 1314)); _vicini(_px(0, "R", 2), (5338, 1344, 1749 * 0.1, 1313))
    _annulla(prima, 2)


def test_copia_e_incolla(ed):
    """appunti dell'editor: si copiano foto e testi (non i vecchi blocchi); incollati nello stesso spread con uno scarto (le foto che
    ci sono già si saltano) o in un altro nella stessa posizione, sopra le altre cornici"""
    _rifiutata(dict(op="incolla", s=4), "gli appunti sono vuoti")
    k = _vecchio_testo(4, "R"); prima = E.snap()
    _senza_effetto(dict(op="copia", s=1, ats=[["L", 0], ["L", 1]]))
    assert [c["item"]["k"] for c in E.CLIP] == ["p", "t"]
    r_foto, r_testo = _px(1, "L", 0), _px(1, "L", 1)
    _op(op="incolla", s=1, scarto=True)
    d = A.CW * 0.02; t = _el(1, "L", 2)
    assert len(E.SP[1][0][1]) == 3 and t["kind"] == "txt" and t["tx"] == _el(1, "L", 1)["tx"], "la foto c'è già: solo il testo"
    _vicini(_px(1, "L", 2), (r_testo[0] + d, r_testo[1] + d, r_testo[2], r_testo[3]))
    assert max(e["zr"] for e in E.spread_view(1)["items"]) == {(e["side"], e["idx"]): e["zr"] for e in E.spread_view(1)["items"]}[("L", 2)], "sopra tutto"
    _op(op="incolla", s=4)
    assert [it["k"] for it in E.SP[4][0][1]] == ["f", "f", "t"] and _el(4, "L", 1)["i"] == _i("H02")
    _vicini(_px(4, "L", 1), r_foto); _vicini(_px(4, "L", 2), r_testo)
    _senza_effetto(dict(op="copia", s=1, ats=[["L", 0]]))
    _rifiutata(dict(op="incolla", s=1), "queste foto sono già in questo spread")
    _annulla(prima, 2)
    _rifiutata(dict(op="copia", s=4, ats=[["R", k]]), "niente da copiare")


def test_allinea_e_distribuisci(ed):
    """«align»: a sinistra, al centro, a destra, in alto, in mezzo, in basso rispetto al gruppo (o alla pagina, per un elemento solo);
    distribuisci con spazi uguali; una cornice allineata oltre la piega passa all'altra pagina"""
    _op(op="setrects", s=0, rects=[["R", 0, 3600, 100, 500, 500], ["R", 1, 4000, 1200, 400, 500], ["R", 2, 6000, 1500, 600, 500]]); prima = E.snap()
    tre = [["R", 0], ["R", 1], ["R", 2]]; pos = lambda: [_px(0, "R", k)[:2] for k in range(3)]

    def prova(mode, attese, ats=tre, s=0):
        _op(op="align", s=s, ats=ats, mode=mode)
        for (x, y), (ax, ay) in zip(pos(), attese): assert (ax is None or abs(x - ax) <= 1) and (ay is None or abs(y - ay) <= 1), (mode, pos())
        _annulla(prima)
    prova("dh", [(3600, 100), (4850, 1200), (6000, 1500)])
    prova("dv", [(3600, 100), (4000, 800), (6000, 1500)])
    prova("l", [(3600, None)] * 3); prova("r", [(6100, None), (6200, None), (6000, None)]); prova("ch", [(4850, None), (4900, None), (4800, None)])
    prova("t", [(None, 100)] * 3); prova("b", [(None, 1500)] * 3); prova("cv", [(None, 800), (None, 800), (None, 800)])
    (x0, x1), (y0, y1) = A._frame("R", "I")
    prova("r", [(round(x1) - 500, 100), (4000, 1200), (6000, 1500)], ats=[["R", 0]])
    for m in ("dh", "dv"): _rifiutata(dict(op="align", s=0, ats=tre[:2], mode=m), "per distribuire servono almeno 3 elementi")
    _rifiutata(dict(op="align", s=0, ats=tre, mode="zz"), "allineamento sconosciuto")
    k = _vecchio_testo(4, "R")
    _senza_effetto(dict(op="align", s=4, ats=[["R", k]], mode="l"))
    _op(op="align", s=1, ats=[["L", 0], ["L", 1], ["R", 0]], mode="l")
    assert [it["k"] for it in E.SP[1][0][1]] == ["f", "t", "f"] and E.SP[1][1][1] == []
    _vicini([_px(1, "L", k)[0] for k in range(3)], [396] * 3)


# ---------------------------------------------------------------- spread e pagine
def test_togli_cornici_e_spread(ed):
    """«delframe» toglie una cornice o un testo (non i vecchi blocchi); «delete» toglie uno spread, ma l'ultimo resta"""
    prima = E.snap()
    _op(op="delframe", at=[3, "L", 1])
    assert [it["i"] for it in E.SP[3][0][1]] == [_i("V03")]
    _op(op="delframe", at=[1, "L", 1])
    assert len(E.SP[1][0][1]) == 1
    _annulla(prima, 2)
    k = _vecchio_testo(4, "R")
    _rifiutata(dict(op="delframe", at=[4, "R", k]), "questo testo non si rimuove da qui")
    E.SP[4][1][1].pop()
    for s in (4, 3, 2, 1): _op(op="delete", s=s)
    assert len(E.SP) == len(E.GD) == 1
    _senza_effetto(dict(op="delete", s=0))
    _annulla(prima, 4)


def test_modo_della_pagina(ed):
    prima = E.snap()
    _op(op="mode", s=4, side="R", mode="I")
    assert E.SP[4][1][0] == "I" and E.SP[4][0][0] == "W"
    _rifiutata(dict(op="mode", s=4, side="R", mode="X"), "pagina non valida")
    _annulla(prima)


def test_spread_nuovi_rifiutati(ed):
    """uno spread nuovo vuole foto libere (e da 1 a 10, se trascinate sulla fila degli spread)"""
    _rifiutata(dict(op="new", s=0), "servono almeno 2 foto libere")
    _rifiutata(dict(op="newspread", L=dict(mode="W", module="FULL", photos=[_i("V07")]), R=dict(mode="I", module="FULL", photos=[_i("H01")])), "una di queste foto è già in uno spread")
    _rifiutata(dict(op="newspreadsel", names=[]), "per uno spread servono da 1 a 10 foto")
