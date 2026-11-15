"""Parità àè: 5 spread. Salvato dall'editor il 15/11/2026 18:00."""
from album import *
from album_libere import *     # cornici libere FREE(...) e angoli ROT(...): serve questo file, sta nella cartella del progetto

SPREADS = [
    # 1
    (W(),
     I(P('V10', 0, 0, 6, 8), P('Q09', 6, 0, 6, 4), P('H06', 6, 4, 6, 4))),
    # 2
    (W(P('H02', 1, 1, 10, 6), TEXT('Ciao àè\nseconda riga', 0.1786, 0.061, 0.8571, 0.1921, font='AvenirNext-Regular', size=150.0, col=(200, 30, 30), al='center', tr=40.0, auto=True, lh=1.5, caps=True, stile='Titolo')),
     W(P('H01', 1, 1, 10, 6))),
    # 3
    (I(P('V03', 0, 0, 6, 8), P('V04', 6, 0, 6, 8)),
     W(P('Q05', 5, 1, 6, 6))),
    # 4
    (I(P('V03', 0, 0, 6, 8, bw=True, z=1.4), ROT(STY(FREE('V04', 0.12, 0.1, 0.5, 0.6), bd=(3.0, '#ffffff'), sh=40, oc=80), 7.5)),
     W(P('Q05', 5, 1, 6, 6))),
    # 5
    (W(FREE('H08', 0.2679, 0.1617, 0.55, 0.5009)),
     W()),
]
