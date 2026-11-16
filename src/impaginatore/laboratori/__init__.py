"""Cataloghi dei laboratori (T-208): quali ci sono, quali prodotti offrono, che cosa vuol dire scegliere un prodotto.

Cataloghi: quelli che vengono con il programma (cartella `cataloghi/` di questo pacchetto: solo il «Generico», fatto di
formati comuni e non di un laboratorio vero) e quelli che l'utente importa (copie nella cartella `cataloghi/` dei suoi
dati). Il formato e la firma sono in catalogo.py; la consegna dei file in consegna.py.

Prodotto di un progetto: progetto.json ha la chiave facoltativa «prodotto», una copia del prodotto scelto con il catalogo
da cui viene (per_progetto). Un progetto senza la chiave, o con una chiave che questa versione non capisce, si apre come
sempre: il prodotto si ignora (dal_progetto) e la chiave resta com'era nel file.

Licenza: i cataloghi dei laboratori (non generici) sono la funzione «preset_laboratori» di tier.json; il Generico è di
tutti. Questo modulo non usa la rete e non tocca le foto.
"""
import copy
import logging
import os
import secrets

from .. import formato, licenze, lingua
from .. import validazione as V
from ..piattaforma import cartelle
from . import catalogo as C

INTERNI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cataloghi")
TOLLERANZA_CM = 0.05                     # mezzo millimetro: un album di 30 × 30 cm va bene per un prodotto di 30 × 30
log = logging.getLogger("impaginatore.laboratori")


def cartella_utente():
    """cartella dei cataloghi importati dall'utente (non la crea)"""
    return os.path.join(cartelle.dati_utente(), "cataloghi")


def _leggi(path, interno):
    raw = formato.leggi_json_rigoroso(path, C.MAX_BYTE)
    cat = C.valida(raw, os.path.basename(path), interno)
    ver, perche = (True, lingua.t("laboratori.verifica_interno")) if interno else C.verifica(raw)
    cat.update(verificato=ver, verifica=perche, interno=interno)
    return cat


def cataloghi():
    """(cataloghi validi, problemi): prima quelli del programma, poi quelli dell'utente in ordine di file. Un file che non
    va finisce tra i problemi ({file, errore}) e non ferma gli altri; un id già visto pure (vince il primo)"""
    out, problemi = [], []
    for interno, d in ((True, INTERNI), (False, cartella_utente())):
        try: nomi = sorted(f for f in os.listdir(d) if f.lower().endswith(".json") and not f.startswith("."))
        except OSError: continue                                        # l'utente non ha ancora importato niente
        for f in nomi:
            try: c = _leggi(os.path.join(d, f), interno)
            except (OSError, V.ErroreProgetto) as e: problemi.append(dict(file=f, errore=str(e))); continue
            if any(x["id"] == c["id"] for x in out): problemi.append(dict(file=f, errore=lingua.t("laboratori.id_doppio", id=c["id"]))); continue
            out.append(c)
    return out, problemi


def consentito(cat, st=None):
    """la licenza di questo computer permette di usare il catalogo? (il Generico sempre)"""
    return cat["generico"] or licenze.consentita("preset_laboratori", st)


def controlla_licenza(cat):
    """NonConsentita se il catalogo è di un laboratorio e la licenza non comprende «preset_laboratori»"""
    st = licenze.stato()
    if not consentito(cat, st): raise licenze.NonConsentita(licenze.motivo("preset_laboratori", st))


def elenco():
    """cataloghi e prodotti per le pagine e per l'assistente (solo dati: nessun percorso)"""
    lst, problemi = cataloghi(); st = licenze.stato()
    return dict(cataloghi=[dict({k: c[k] for k in ("id", "nome", "laboratorio", "data", "generico", "stato", "verificato", "verifica", "interno")},
                                consentito=consentito(c, st), prodotti=c["prodotti"], **{k: c[k] for k in ("fonte", "note") if k in c}) for c in lst],
                problemi=problemi)


def trova(id_catalogo, id_prodotto):
    """(catalogo, prodotto) installati, o ValueError con un messaggio per l'utente"""
    for c in cataloghi()[0]:
        if c["id"] == id_catalogo:
            p = next((p for p in c["prodotti"] if p["id"] == id_prodotto), None)
            if p is None: raise ValueError(lingua.t("laboratori.senza_prodotto", nome=c["nome"], prodotto=id_prodotto))
            return c, p
    raise ValueError(lingua.t("laboratori.non_trovato", id=id_catalogo))


def scelta(v):
    """(catalogo, prodotto) dalla scelta di una pagina o dell'assistente: {"catalogo": id, "prodotto": id} oppure "catalogo/prodotto".
    Controlla anche la licenza"""
    if isinstance(v, str) and v.count("/") == 1: v = dict(zip(("catalogo", "prodotto"), v.split("/")))
    if not isinstance(v, dict) or not all(isinstance(v.get(k), str) and C._ID.fullmatch(v[k]) for k in ("catalogo", "prodotto")):
        raise ValueError(lingua.t("laboratori.prodotto_non_valido"))
    c, p = trova(v["catalogo"], v["prodotto"]); controlla_licenza(c)
    return c, p


# ---------------------------------------------------------------- il prodotto in progetto.json
def per_progetto(cat, prod):
    """la chiave «prodotto» di progetto.json: copia del prodotto e del catalogo da cui viene (il progetto resta giusto anche
    se il catalogo cambia o sparisce)"""
    return dict(formato_catalogo=C.FORMATO, catalogo=cat["id"], nome_catalogo=cat["nome"], laboratorio=cat["laboratorio"],
                data=cat["data"], stato=cat["stato"], prodotto=copy.deepcopy(prod))


def dal_progetto(v):
    """il prodotto di progetto.json controllato (come un catalogo: arriva anche con progetti di altri), o None se non c'è o
    se questa versione non lo capisce (il progetto si apre lo stesso)"""
    if v is None: return None
    try:
        V.oggetto(v, "prodotto", ("formato_catalogo", "catalogo", "nome_catalogo", "laboratorio", "data", "stato", "prodotto"))
        C.formato(v["formato_catalogo"], "prodotto, formato_catalogo")
        return dict(formato_catalogo=C.FORMATO, catalogo=C._id(v["catalogo"], "prodotto, catalogo"), nome_catalogo=V.testo(v["nome_catalogo"], "prodotto, nome_catalogo", 80),
                    laboratorio=V.testo(v["laboratorio"], "prodotto, laboratorio", 80), data=C._data(v["data"], "prodotto, data"),
                    stato=V.scelta(v["stato"], "prodotto, stato", C.STATI), prodotto=C.prodotto(v["prodotto"], "prodotto"))
    except V.ErroreProgetto as e:
        log.warning("prodotto del progetto ignorato: %s", e); return None


def stato(pr):
    """come sta il prodotto del progetto rispetto ai cataloghi installati: {generico, verificato, installato, verifica}.
    Generico e verificato solo se il catalogo installato con lo stesso id ha lo stesso identico prodotto: un progetto
    ricevuto non può dichiararsi verificato da solo"""
    for c in cataloghi()[0]:
        if c["id"] == pr["catalogo"]:
            if any(p == pr["prodotto"] for p in c["prodotti"]): return dict(generico=c["generico"], verificato=c["verificato"], installato=True, verifica=c["verifica"])
            return dict(generico=False, verificato=False, installato=True, verifica=lingua.t("laboratori.prodotto_diverso"))
    return dict(generico=False, verificato=False, installato=False, verifica=lingua.t("laboratori.non_installato"))


def geometria(prod):
    """impostazioni di progetto.json che vengono dal prodotto: formato dello spread aperto, abbondanza, risoluzione"""
    w, h = prod["pagina_cm"]
    return dict(formato_cm=[round(2 * w, 2), round(h, 2)], abbondanza_mm=prod["abbondanza_mm"], ppi=prod["ppi"])


def _cm(v): return lingua.num(v)


def incompatibile(cfg, prod):
    """None se l'album (progetto.json) ha il formato del prodotto e almeno la sua abbondanza; altrimenti il motivo, per l'utente.
    Il formato di un album fatto non si cambia qui: si crea un album nuovo con il prodotto"""
    (W, H), (w, h) = cfg["formato_cm"], prod["pagina_cm"]
    if abs(W / 2 - w) > TOLLERANZA_CM or abs(H - h) > TOLLERANZA_CM:
        return lingua.t("laboratori.formato_diverso", larghezza=_cm(round(W / 2, 2)), altezza=_cm(H), nome=prod["nome"], w=_cm(w), h=_cm(h))
    ab = cfg.get("abbondanza_mm", 0)
    if ab + 1e-6 < prod["abbondanza_mm"]:
        return lingua.t("laboratori.abbondanza_poca", abbondanza=_cm(ab), nome=prod["nome"], richiesta=_cm(prod["abbondanza_mm"]))
    return None


# ---------------------------------------------------------------- importare un catalogo
def importa(path):
    """copia nella cartella dei cataloghi dell'utente il catalogo del file `path`, dopo averlo controllato tutto (formato,
    firma, licenza). Restituisce {id, nome, laboratorio, prodotti, verificato, verifica, sostituito}. Un catalogo del
    programma non si sostituisce; uno verificato non si sostituisce con uno che non lo è"""
    try:
        with open(path, "rb") as f: dati = f.read(C.MAX_BYTE + 1)
    except OSError as e: raise ValueError(lingua.t("laboratori.lettura_fallita", motivo=str(e.strerror or e))) from None
    if len(dati) > C.MAX_BYTE: raise ValueError(lingua.t("laboratori.troppo_grande", mb=C.MAX_BYTE // 2**20))
    d = cartella_utente(); os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".importa-{secrets.token_hex(6)}.json")          # i byte letti una volta sola: si controlla quello che si copia
    try:
        with open(tmp, "xb") as f: f.write(dati)
        cat = _leggi(tmp, interno=False)
        controlla_licenza(cat)
        presenti = {c["id"]: c for c in cataloghi()[0]}
        prima = presenti.get(cat["id"])
        if prima and prima["interno"]: raise ValueError(lingua.t("laboratori.id_del_programma", id=cat["id"]))
        if prima and prima["verificato"] and not cat["verificato"]:
            raise ValueError(lingua.t("laboratori.verificato_resta", nome=prima["nome"], motivo=cat["verifica"]))
        dst = os.path.join(d, cat["id"] + ".json")
        for f in os.listdir(d):                                        # lo stesso catalogo salvato prima con un altro nome di file
            if f.lower().endswith(".json") and not f.startswith(".") and os.path.join(d, f) != dst:
                try: altro = _leggi(os.path.join(d, f), False)["id"]
                except (OSError, V.ErroreProgetto): continue
                if altro == cat["id"]: os.remove(os.path.join(d, f))
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    return dict({k: cat[k] for k in ("id", "nome", "laboratorio", "verificato", "verifica", "stato")}, prodotti=len(cat["prodotti"]), sostituito=prima is not None)
