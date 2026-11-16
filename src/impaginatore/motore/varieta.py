"""Varietà delle disposizioni: quanto due disposizioni di spread si somigliano, a che famiglia appartengono, e un ordine
delle proposte (e una scelta per la bozza) che non ripete lo stesso schema. Il titolare: «dovrebbe creare modelli molto
diversi tra loro creando una grande differenziazione e varietà». docs/architettura/VARIETA.md spiega misura e scelte.

Una disposizione si guarda come la vede chi sfoglia l'album: le sue caselle normalizzate sullo spread (x, y, w, h fra 0
e 1, la piega a x = 0,5). Da lì:

- `descrivi(cornici, W, H)`: il descrittore, cioè un'immagine ridotta dello spread (per ogni cella la misura e la forma
  della casella che la copre), qualche numero (caselle per pagina, parte coperta, peso della foto più grande, piega
  attraversata, pagine con il margine bianco, simmetria), la famiglia e lo schema;
- `distanza(a, b)`: fra 0 (la stessa disposizione, anche specchiata) e 1 (niente in comune);
- `famiglia`: per pagina «vuota», «intera», «respiro», «coppia», «dominante», «griglia», «striscia», «mosaico»; per lo
  spread le due pagine («griglia+intera») oppure «piega» se una casella attraversa la piega;
- `ordina(...)`: le proposte in un ordine che alterna famiglie e geometrie diverse a parità di rispetto delle foto
  (massima rilevanza marginale: ogni volta la proposta con costo più somiglianza a quelle già messe più bassi);
- `ripetizioni(...)`: quanto ogni candidata ripete gli spread appena prima (per la bozza).

Funzioni pure, deterministiche: niente caso, niente stato. numpy si importa dentro le funzioni (nessun effetto all'import).
"""
import math

RIGHE, COLONNE = 16, 48           # immagine ridotta dello spread: 2 x 2 celle per ogni cella della griglia 12 x 8 di pagina
SCALA_GEOMETRIA = 0.22            # differenza media delle immagini ridotte che vale «del tutto diverse» (tarata su FULL|FULL contro G4|G4)
FAMIGLIE_PAGINA = ("vuota", "intera", "respiro", "coppia", "dominante", "griglia", "striscia", "mosaico")
PIEGA = "piega"
QUANTI = 40                       # le prime proposte messe in ordine di varietà; le altre seguono per costo
PESO_SOMIGLIANZA = 0.9            # ordine delle proposte: quanto costa somigliare alla più vicina fra quelle già messe
PESO_FAMIGLIA = 0.25              # ... e ripetere una famiglia già messa (per ogni volta)
DOPPIONE = 1.0                    # ... e ripetere uno schema già messo (la stessa disposizione specchiata o con le pagine scambiate)
FINESTRA = 8                      # bozza: uno schema non torna prima di tanti spread (salvo che le foto non lascino altro)
PESI_VICINI = (0.7, 0.4, 0.2, 0.1)   # bozza: somiglianza con lo spread prima, due prima, tre prima, quattro prima
PESI_FAMIGLIA = (0.45, 0.2)       # bozza: stessa famiglia dello spread prima, di due prima
SCHEMA_RIPETUTO = 1.2             # bozza: lo stesso schema entro la finestra
PIEGA_VICINA = 0.8                # bozza: due spread a cavallo della piega entro la finestra
_EPS = 0.004


class Descrittore:
    """immagine ridotta (misura, forma), la stessa specchiata sulla piega, numeri, famiglia, schema, piega attraversata"""
    __slots__ = ("img", "spec", "num", "fam", "schema", "piega", "n")

    def __init__(self, img, spec, num, fam, schema, piega, n):
        self.img, self.spec, self.num, self.fam, self.schema, self.piega, self.n = img, spec, num, fam, schema, piega, n


def caselle(cornici, W, H):
    """caselle (x, y, w, h) normalizzate e tagliate allo spread, da cornici {x, y, w, h} in pixel di uno spread W x H"""
    out = []
    for f in cornici:
        x0, y0 = max(f["x"], 0) / W, max(f["y"], 0) / H
        x1, y1 = min(f["x"] + f["w"], W) / W, min(f["y"] + f["h"], H) / H
        if x1 - x0 > _EPS and y1 - y0 > _EPS: out.append((x0, y0, x1 - x0, y1 - y0))
    return out


def _attraversa(c): return c[0] < 0.5 - _EPS and c[0] + c[2] > 0.5 + _EPS


def _pagina(c):
    """«L» o «R» per una casella che non attraversa la piega (dal suo centro)"""
    return "L" if c[0] + c[2] / 2 < 0.5 else "R"


def famiglia_pagina(cas):
    """famiglia di una pagina dalle sue caselle normalizzate sulla pagina (x, y, w, h fra 0 e 1)"""
    if not cas: return "vuota"
    aree = sorted((w * h for _, _, w, h in cas), reverse=True)
    if len(cas) == 1: return "intera" if aree[0] >= 0.8 else "respiro"
    if sum(aree) < 0.25 or len(cas) == 2 and sum(aree) < 0.5: return "respiro"          # poche foto piccole su tanto bianco
    if aree[0] >= 1.8 * aree[1]: return "dominante"
    if aree[0] <= 1.3 * aree[-1]:
        if len(cas) == 2: return "coppia"
        righe = {round(y, 2) for _, y, _, _ in cas}; colonne = {round(x, 2) for x, _, _, _ in cas}
        return "striscia" if len(righe) == 1 or len(colonne) == 1 else "griglia"
    return "mosaico"


def famiglia(cas):
    """famiglia dello spread: «piega» se una casella attraversa la piega, altrimenti le famiglie delle due pagine in ordine
    alfabetico unite da «+» (una disposizione e la sua specchiata hanno la stessa famiglia)"""
    if any(_attraversa(c) for c in cas): return PIEGA
    pag = {"L": [], "R": []}
    for c in cas:
        x, y, w, h = c; s = _pagina(c); x0 = 0 if s == "L" else 0.5
        pag[s].append(((x - x0) * 2, y, w * 2, h))
    return "+".join(sorted(famiglia_pagina(pag[s]) for s in "LR"))


def _schema(cas):
    """chiave della geometria, la stessa per la disposizione specchiata sulla piega: celle dell'immagine ridotta"""
    q = lambda c, sx: (round(sx * COLONNE), round(c[1] * RIGHE), round(c[2] * COLONNE), round(c[3] * RIGHE))
    a = tuple(sorted(q(c, c[0]) for c in cas)); b = tuple(sorted(q(c, 1 - c[0] - c[2]) for c in cas))
    return min(a, b)


def _bianca(cas, s):
    """la pagina s ha il margine bianco tutto attorno (nessuna casella tocca i suoi bordi esterni)? Vuota vale bianca"""
    for c in cas:
        x, y, w, h = c
        if y <= _EPS or y + h >= 1 - _EPS: return False
        if s == "L" and x <= _EPS or s == "R" and x + w >= 1 - _EPS: return False
    return True


def descrivi(cornici, W, H):
    """descrittore di una disposizione: cornici {x, y, w, h} in pixel di uno spread di W x H pixel"""
    import numpy as np
    cas = caselle(cornici, W, H); ar = W / H
    img = np.zeros((2, RIGHE, COLONNE))
    for x, y, w, h in cas:
        c0 = min(round(x * COLONNE), COLONNE - 1); c1 = max(round((x + w) * COLONNE), c0 + 1)
        r0 = min(round(y * RIGHE), RIGHE - 1); r1 = max(round((y + h) * RIGHE), r0 + 1)
        img[0, r0:r1, c0:c1] = math.sqrt(w * h)
        img[1, r0:r1, c0:c1] = min(max(math.log(w / h * ar), -1.2), 1.2) / 2.4
    spec = img[:, :, ::-1].copy()
    piega = [c for c in cas if _attraversa(c)]
    pag = {s: [c for c in cas if not _attraversa(c) and _pagina(c) == s] for s in "LR"}
    aree = sorted((w * h for _, _, w, h in cas), reverse=True); tot = sum(aree)
    simm = 1 - min(float(np.abs(img - spec).mean()) / SCALA_GEOMETRIA, 1.0)
    num = np.array([len(pag["L"]), len(pag["R"]), len(piega), tot, aree[0] / tot if tot else 0.0, 1.0 if piega else 0.0,
                    sum(_bianca(pag[s], s) for s in "LR"), simm], dtype=float)
    return Descrittore(img, spec, num, famiglia(cas), _schema(cas), bool(piega), len(cas))


def attraversa_piega(cornici, W):
    """una delle cornici {x, y, w, h} (pixel di uno spread largo W) attraversa la piega?"""
    return any(_attraversa((f["x"] / W, 0, f["w"] / W, 0)) for f in cornici)


class _Pila:
    """descrittori impilati: le distanze da uno a tutti si calcolano in un colpo"""

    def __init__(self, descr):
        import numpy as np
        self.I = np.stack([x.img for x in descr]); self.S = np.stack([x.spec for x in descr]); self.F = np.stack([x.num for x in descr])
        self.fam = [x.fam for x in descr]


def _distanze(d, pila):
    """distanze fra il descrittore d e ognuno di quelli della pila (array numpy): metà geometria (immagini ridotte, la
    più vicina fra diritta e specchiata), metà struttura (foto per pagina, parte coperta, peso della più grande, piega,
    pagine bianche, simmetria, famiglia)"""
    import numpy as np
    F = pila.F; a = d.num
    g = np.minimum(np.abs(pila.I - d.img).mean(axis=(1, 2, 3)), np.abs(pila.S - d.img).mean(axis=(1, 2, 3))) / SCALA_GEOMETRIA
    nt = np.maximum(np.maximum(F[:, :3].sum(axis=1), a[:3].sum()), 1)
    conta = (np.minimum(np.abs(F[:, 0] - a[0]) + np.abs(F[:, 1] - a[1]), np.abs(F[:, 0] - a[1]) + np.abs(F[:, 1] - a[0])) + np.abs(F[:, 2] - a[2])) / nt
    fam = np.array([0.0 if f == d.fam else 1.0 for f in pila.fam])
    s = (np.minimum(conta, 1) + np.minimum(np.abs(F[:, 3] - a[3]) / 0.5, 1) + np.abs(F[:, 4] - a[4]) + np.abs(F[:, 5] - a[5])
         + np.abs(F[:, 6] - a[6]) / 2 + np.abs(F[:, 7] - a[7]) + fam) / 7
    return np.clip(0.5 * np.minimum(g, 1) + 0.5 * s, 0, 1)


def distanza(a, b):
    """distanza fra due descrittori: 0 la stessa disposizione (o la sua specchiata), 1 niente in comune"""
    return float(_distanze(a, _Pila([b]))[0])


def ordina(descr, costi, quanti=QUANTI, primo=None):
    """indici delle proposte in un ordine vario: prima `primo` (di serie quella di costo minore, a parità la prima), poi
    ogni volta quella che rende più basso costo + PESO_SOMIGLIANZA x somiglianza con la più vicina già messa +
    PESO_FAMIGLIA x volte che la sua famiglia c'è già + DOPPIONE se il suo schema c'è già. costi: per foto (confrontabili
    fra proposte con le stesse foto). Dopo le prime `quanti` le altre seguono per costo. Stessi dati, stesso ordine"""
    import numpy as np
    n = len(descr)
    if n == 0: return []
    per_costo = sorted(range(n), key=lambda i: (costi[i], i)); pila = _Pila(descr)
    scelti = [per_costo[0] if primo is None else primo]; dmin = _distanze(descr[scelti[0]], pila)
    fam = {descr[scelti[0]].fam: 1}; schemi = {descr[scelti[0]].schema}; resto = set(range(n)) - set(scelti)
    while resto and len(scelti) < quanti:
        k = min(resto, key=lambda i: (costi[i] + PESO_SOMIGLIANZA * (1 - float(dmin[i])) + PESO_FAMIGLIA * fam.get(descr[i].fam, 0)
                                      + (DOPPIONE if descr[i].schema in schemi else 0), costi[i], i))
        scelti.append(k); resto.discard(k); dmin = np.minimum(dmin, _distanze(descr[k], pila))
        fam[descr[k].fam] = fam.get(descr[k].fam, 0) + 1; schemi.add(descr[k].schema)
    return scelti + [i for i in per_costo if i in resto]


def ripetizioni(cand, storia, finestra=FINESTRA):
    """penalità di ogni candidata (descrittori) dopo gli spread di storia (descrittori, l'ultimo è quello appena prima):
    somiglianza con gli ultimi quattro (PESI_VICINI), stessa famiglia degli ultimi due (PESI_FAMIGLIA), stesso schema
    entro la finestra (SCHEMA_RIPETUTO), due spread a cavallo della piega entro la finestra (PIEGA_VICINA)"""
    import numpy as np
    p = np.zeros(len(cand))
    if not cand: return p
    vicini = storia[::-1][:finestra]; pila = _Pila(cand)
    for j, d in enumerate(vicini):
        if j < len(PESI_VICINI): p += PESI_VICINI[j] * (1 - _distanze(d, pila))
        if j < len(PESI_FAMIGLIA): p += PESI_FAMIGLIA[j] * np.array([1.0 if c.fam == d.fam else 0.0 for c in cand])
    schemi = {d.schema for d in vicini}; piega = any(d.piega for d in vicini)
    p += np.array([(SCHEMA_RIPETUTO if c.schema in schemi else 0.0) + (PIEGA_VICINA if piega and c.piega else 0.0) for c in cand])
    return p


# ---------------------------------------------------------------- misure (test e documento)
def misura_proposte(descr):
    """{famiglie, media, minima, doppioni}: famiglie diverse, distanza media e minima fra le coppie, coppie quasi uguali
    (distanza < 0,15) fra le disposizioni date (per esempio le prime 8 proposte)"""
    dd = [distanza(a, b) for k, a in enumerate(descr) for b in descr[k + 1:]]
    return dict(famiglie=len({d.fam for d in descr}), media=round(sum(dd) / len(dd), 3) if dd else 0.0, minima=round(min(dd), 3) if dd else 0.0,
                doppioni=sum(1 for x in dd if x < 0.15))


def misura_sequenza(descr, finestra=FINESTRA):
    """{spread, schemi, famiglie, ripetuti, stessa_famiglia, vicini}: per gli spread di una bozza in ordine, quanti schemi e
    famiglie diversi, quanti spread ripetono uno schema entro la finestra, quanti hanno la famiglia di quello prima, la
    distanza media fra spread vicini"""
    rip = sum(1 for k, d in enumerate(descr) if any(d.schema == e.schema for e in descr[max(0, k - finestra):k]))
    vic = [distanza(a, b) for a, b in zip(descr, descr[1:])]
    return dict(spread=len(descr), schemi=len({d.schema for d in descr}), famiglie=len({d.fam for d in descr}), ripetuti=rip,
                stessa_famiglia=sum(1 for a, b in zip(descr, descr[1:]) if a.fam == b.fam), vicini=round(sum(vic) / len(vic), 3) if vic else 0.0)
