"""Esempio di spec (estratto dell'album Battesimo Anita, versione approvata dal cliente).
Ogni voce di SPREADS = (pagina sinistra, pagina destra). Le foto si indicano con il nome file senza estensione.
I(...) pagina immersiva, W(...) pagina bianca. Moduli: FULL, DUO, VLL, V4, G4, CV, SV, PP, COL2, BAND2, STRIP3, P, TXT.
bw=True bianco e nero; z=1.2 stringe sui volti (primo piano).
"""
from album import *

SPREADS = [
    # apertura: titolo sul bianco, la foto più bella della bambina a tutta pagina
    (W(TXT("title", 0, 0, 12, 8)),                     I(FULL("_DSC4287"))),
    # I. Il servizio prima del battesimo
    (W(CV("_DSC3127")),                                I(FULL("_DSC3650"))),            # una sola foto sul bianco -> un volto a tutta pagina
    (I(DUO("_DSC3054", "_DSC3291", z=(1, 1.1))),       I(G4("_DSC3188", "_DSC3407", "_DSC3338", "_DSC3352"))),
    (I(DUO("_DSC3513", "_DSC3529", bw=(True, True), z=(1, 1.8))), W(CV("_DSC3701"))),   # pausa in bianco e nero, poi respiro
    (I(FULL("_DSC3821")),                              I(DUO("_DSC3885", "_DSC3892", bw=(False, True), z=(1.25, 1)))),
    (W(CV("_DSC3957")),                                W(CV("_DSC0347"))),              # due pagine bianche: fine capitolo
    # II. A casa: un tema per spread (lei da sola / con la famiglia / i dettagli)
    (I(FULL("_DSC8814")),                              I(FULL("_DSC8853"))),
    (I(G4("_DSC8906", "_DSC9052", "_DSC9299", "_DSC9333")), I(FULL("_DSC9031"))),
    # III. Il rito: climax su due pagine intere, poi il fonte
    (W(CV("_DSC4289")),                                I(FULL("_DSC0792"))),
    (I(FULL("_DSC0718", bw=True)),                     I(VLL("_DSC0727", "_DSC0672", "_DSC0878", mirror=True))),
    # IV. La festa: allestimento + dettagli, poi gruppi grandi, poi gruppi piccoli
    (I(DUO("_DSC1087", "_DSC1390")),                   I(V4("_DSC1359", "_DSC1418", "_DSC1408", "_DSC1415", "_DSC1417", mirror=True))),
    (I(G4("_DSC1258", "_DSC1267", "_DSC1271", "_DSC1277")), I(G4("_DSC1283", "_DSC1296", "_DSC1302", "_DSC1332"))),
    # Finale: solo la bambina, e la firma
    (I(FULL("_DSC0003")),                              I(DUO("_DSC8801", "_DSC4141", bw=(True, False)))),
    (W(CV("_DSC3993")),                                W(P("_DSC4162", 0, 0, 6, 8), TXT("end", 7, 0, 5, 8))),
]
