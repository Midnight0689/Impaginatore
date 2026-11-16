"""VER-005: uno spec.py piccolo non può chiedere gigabyte. Il lettore delle 1.x ha un budget per tutto il file (testi ed
elenchi costruiti), controlla i tipi degli argomenti dei costruttori prima di chiamarli e limita elementi e testo
dell'album intero. Ogni prova resta sotto pochi MB."""
import pytest

from impaginatore import formato_1x
from impaginatore.formato import ErroreProgetto
from impaginatore.motore import album

INIZIO = "from album import *\nfrom album_libere import *\n"
RADDOPPIA = "S = 'xxxxxxx'\n" + "S += S\n" * 16                     # 458 752 caratteri, sotto MAX_TESTO
ELENCO = "A = [0]\n" + "A += A\n" * 17                              # 131 072 elementi, sotto MAX_LISTA


def leggi(corpo, prova=True):
    return formato_1x.leggi((INIZIO + corpo).encode("utf-8"), prova=prova)


def rifiutato(corpo, motivo, prova=True):
    with pytest.raises(ErroreProgetto) as e: leggi(corpo, prova)
    assert motivo in str(e.value), str(e.value)[:300]


def test_budget_dei_testi_costruiti():
    rifiutato(RADDOPPIA + "L = [" + "S+S," * 10 + "]\nSPREADS = []\n", "troppo testo costruito")
    assert leggi(RADDOPPIA + "L = [S+S, S+S]\nSPREADS = []\n") == []


@pytest.mark.parametrize("corpo", [
    ELENCO + "B = A + []\n" * 8,                                    # tanti elenchi, ognuno sotto il limite
    ELENCO + "B = []\n" + "B.extend(A)\n" + "C = []\nC.extend(A)\n" * 7,
    ELENCO + "B = [" + "*A," * 1 + "]\n" + "C = [*A]\n" * 7,
])
def test_budget_degli_elenchi_costruiti(corpo):
    rifiutato(corpo + "SPREADS = []\n", "elenchi troppo grandi")


def test_append_conta():
    lettore = formato_1x._Lettore(formato_1x._funzioni(True)); lettore.elementi = formato_1x.MAX_ELEMENTI_COSTRUITI
    lettore.nomi["L"] = ("v", [])
    import ast
    with pytest.raises(formato_1x._NonRiconosciuto, match="elenchi troppo grandi"): lettore.istruzione(ast.parse("L.append(1)").body[0])


@pytest.mark.parametrize("prova", [True, False])
@pytest.mark.parametrize("corpo,motivo", [
    (RADDOPPIA + "L = [S]\n" + "L += L\n" * 17 + "SPREADS = [[I(TEXT(L, 0, 0, 1, 1)), I()]]\n", "«tx» deve essere un testo"),
    ("SPREADS = [[I(TEXT(5, 0, 0, 1, 1)), I()]]\n", "«tx» deve essere un testo"),
    (RADDOPPIA + "L = [S]\n" + "L += L\n" * 17 + "SPREADS = [[I(STY(P('H01', 0, 0, 6, 8), bd=[1, L])), I()]]\n", "«bd» deve essere"),
    ("SPREADS = [[I(STY(P('H01', 0, 0, 6, 8), bd=[1, 2])), I()]]\n", "«bd» deve essere"),
    ("SPREADS = [[I(STY(P('H01', 0, 0, 6, 8), bd=[1, '#fff', 3])), I()]]\n", "«bd» deve essere"),
    ("SPREADS = [[I(STY(P('H01', 0, 0, 6, 8), bd=5)), I()]]\n", "«bd» deve essere un piccolo elenco"),
    ("SPREADS = [[I(TEXT('a', 0, 0, 1, 1, col=[1, 2, 3, 4, 5])), I()]]\n", "«col» deve essere un piccolo elenco"),
    ("SPREADS = [[I(TEXT('a', 0, 0, 1, 1, col=[[1], 2, 3])), I()]]\n", "«col» deve essere un piccolo elenco"),
    ("SPREADS = [[I(P(['H01'], 0, 0, 6, 8)), I()]]\n", "«n» deve essere un numero o un testo"),
    ("SPREADS = [[I(ROT(5, 10)), I()]]\n", "il primo argomento deve essere una foto"),
    ("SPREADS = [[I(DUO('H01', 'H02', bw=[[1], 2])), I()]]\n", "«bw» deve essere un piccolo elenco"),
    ("L = [P('H01', 0, 0, 6, 8)]\n" + "L += L\n" * 9 + "SPREADS = [[I(L), I()]]\n", "troppi elementi in una pagina"),
])
def test_tipi_degli_argomenti(progetto, prova, corpo, motivo):
    if not prova: album.carica_progetto(progetto)
    rifiutato(corpo, motivo, prova)


def test_argomenti_giusti_passano(progetto):
    album.carica_progetto(progetto)
    sp = leggi("SPREADS = [[I(STY(P('H01', 0, 0, 6, 8), bd=(3.0, '#ffffff'), sh=40), STY(FULL('H02'), bd=None, sh=20), *DUO('H02', 'V03', bw=(True, False))),"
               " W(TEXT('Ciao', 0.1, 0.1, 0.5, 0.2, col=(200, 30, 30), stile=None), ROT(FREE('V04', 0.1, 0.1, 0.5, 0.6, zo=None), 5))]]\n", prova=False)
    assert sp[0][0][1][0]["bd"] == [3.0, "#ffffff"] and "bd" not in sp[0][0][1][1] and sp[0][0][1][2]["bw"] is True and sp[0][1][1][0]["col"] == [200, 30, 30]


def test_elementi_dell_album_intero():
    rifiutato("L = [P('H01', 0, 0, 6, 8)]\n" + "L += L\n" * 8 + "S = [[I(L), I(L)]]\n" + "S += S\n" * 8 + "SPREADS = S\n", "troppi elementi nell'album")


def test_testo_dell_album_intero(progetto):
    album.carica_progetto(progetto)
    rifiutato(RADDOPPIA + "L = [TEXT(S, 0, 0, 1, 1)]\n" + "L += L\n" * 4 + "SPREADS = [[I(L), I()]]\n", "troppo testo nell'album", prova=False)
    assert len(leggi(RADDOPPIA + "L = [TEXT(S, 0, 0, 1, 1)]\n" + "L += L\n" * 2 + "SPREADS = [[I(L), I()]]\n", prova=False)[0][0][1]) == 4


def test_pagina_troppo_lunga_anche_senza_costruttori():
    """il controllo della struttura resta anche se I e W non lo permettono più (difesa doppia)"""
    with pytest.raises(ErroreProgetto, match="troppi elementi"): formato_1x._struttura([[("I", [formato_1x._Elemento()] * 501), ("I", [])]], "spec.py")
