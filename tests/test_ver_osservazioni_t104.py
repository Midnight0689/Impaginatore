"""Osservazioni lasciate da T-104 e corrette insieme alla verifica T-106:
- «newspreadsel» con un numero di foto sbagliato si ferma in valida con un messaggio chiaro (prima dipendeva da un next()
  senza ripiego: con 0 foto o più di 10 sarebbe stato uno StopIteration senza messaggio);
- _spiega non mette il nome del tipo di errore davanti ai messaggi per l'utente;
- «copia» non riuscita lascia gli appunti com'erano;
- «frame» e «snap» (cornice libera -> cornice della griglia) tengono angolo, bordo, ombra, opacità e livello."""
import itertools

import pytest


def _nomi(c): return [p["n"] for p in c.get("/api/state")["photos"]]


@pytest.mark.parametrize("names,errore", [([], "per uno spread servono da 1 a 10 foto"), (None, "per uno spread servono da 1 a 10 foto"),
                                          ("H01", "elenco di foto non valido: names"), (["H01", "nuova"], "foto sconosciuta: 'nuova'")])
def test_newspreadsel_numero_di_foto(editor, names, errore):
    o = dict(op="newspreadsel", pos=0)
    if names is not None: o["names"] = names
    ok, r = editor.prova("/api/op", o)
    assert not ok and r["errore"] == errore and editor.get("/api/state")["spreads"] == []


def test_newspreadsel_doppioni_e_tutti_i_numeri(editor):
    """da 1 a 10 foto (anche ripetute) c'è sempre un modello: valida basta perché next() non resti mai senza risultato"""
    st = editor.post("/api/op", dict(op="newspreadsel", names=["H01", "H01", "H01"], pos=0))
    assert len(st["spreads"]) == 1
    nomi = _nomi(editor)
    for k in range(1, 11):
        for scelta in itertools.islice(itertools.combinations(nomi, k), 0, None, 37):
            ok, r = editor.prova("/api/op", dict(op="newspreadsel", names=list(scelta), pos=0))
            assert ok, (scelta, r)


def test_spiega_senza_nome_del_tipo(editor):
    E = editor.E
    assert E._spiega(ValueError("il PDF risulta vuoto")) == "il PDF risulta vuoto"
    assert E._spiega(RuntimeError("Photoshop non risponde")) == "Photoshop non risponde"
    assert E._spiega(KeyError("x")) == "errore imprevisto (KeyError: 'x')" and E._spiega(ValueError()) == "errore imprevisto (ValueError: )"


def test_copia_non_riuscita_lascia_gli_appunti(editor):
    nomi = _nomi(editor)
    editor.post("/api/op", dict(op="newspreadsel", names=nomi[:3], pos=0))
    editor.post("/api/op", dict(op="addtext", s=0, fx=0.1, fy=0.1, fw=0.3, fh=0, tx="Titolo"))
    editor.post("/api/op", dict(op="copia", s=0, ats=[["L", 0]]))
    prima = [dict(c) for c in editor.E.CLIP]
    E = editor.E; E.SP[0][0][1].append(dict(k="t", kind="title", c=0, r=0, w=2, h=2))          # vecchio blocco titolo: non si copia
    idx = len(E.SP[0][0][1]) - 1
    ok, r = editor.prova("/api/op", dict(op="copia", s=0, ats=[["L", idx]]))
    assert not ok and "niente da copiare" in r["errore"] and E.CLIP == prima


@pytest.mark.parametrize("op", ["frame", "snap"])
def test_cornice_libera_nella_griglia_tiene_lo_stile(editor, op):
    nomi = _nomi(editor); E = editor.E
    editor.post("/api/op", dict(op="newspreadsel", names=nomi[:1], pos=0))
    lato = "L" if E.SP[0][0][1] else "R"
    editor.post("/api/op", dict(op="free", at=[0, lato, 0], x=0.1, y=0.1, w=0.4, h=0.4))
    editor.post("/api/op", dict(op="set", at=[0, lato, 0], a=7.5, bd=[3, "#ff0000"], sh=40, oc=80))
    E.SP[0][0 if lato == "L" else 1][1][0]["zo"] = 3
    if op == "frame": editor.post("/api/op", dict(op="frame", at=[0, lato, 0], c=0, r=0, w=6, h=8))
    else: editor.post("/api/op", dict(op="snap", at=[0, lato, 0]))
    it = E.SP[0][0 if lato == "L" else 1][1][0]
    assert it["k"] == "p" and (it["a"], it["bd"], it["sh"], it["oc"], it["zo"]) == (7.5, [3.0, "#ff0000"], 40, 80, 3), it
