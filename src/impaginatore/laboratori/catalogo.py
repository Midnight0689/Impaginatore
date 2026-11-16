"""Pacchetti catalogo dei laboratori (T-208): formato, controllo rigoroso e firma.

Un catalogo è un file JSON che descrive i prodotti album di un laboratorio (formato della pagina, spread ammessi,
abbondanza, zona di sicurezza, piega, risoluzione, profilo colore, nomi dei file di consegna, copertina). Arriva da altri
(il laboratorio, un collega, un'email): è un dato non fidato. Qui si controlla chiave per chiave, con limiti di misura,
senza percorsi né codice; i testi restano testi (la pagina li mette sempre con esc()). Lo schema completo, con un esempio,
è in docs/architettura/CATALOGHI.md; la guida per chi lo scrive in docs/laboratori/SCRIVERE-UN-CATALOGO.md.

Firma: facoltativa, Ed25519 con le stesse chiavi pubbliche delle licenze (licenze.chiave.CHIAVI_PUBBLICHE) su
DOMINIO_CATALOGO + JSON canonico del catalogo senza «firma». Firmato dal produttore del programma → «verificato»; senza
firma si usa lo stesso ma è «non verificato»; una firma presente che non corrisponde al contenuto rifiuta il catalogo
(qualcuno l'ha cambiato dopo la firma).
"""
import re

from .. import ed25519, lingua
from .. import validazione as V
from ..licenze import chiave as K

FORMATO = 1                                       # versione del formato dei cataloghi che questo programma legge
DOMINIO_CATALOGO = b"IMPAGINATORE-CATALOGO-v1\x00"
MAX_BYTE = 2 ** 20                                # 1 MB: un catalogo vero di 200 prodotti sta sotto i 200 KB
MAX_PRODOTTI = 200
STATI = ("confermato", "da_confermare")
PROFILI = ("sRGB",)                               # profili colore della consegna: quello che Pillow incorpora senza file esterni
FORMATI_FILE = ("jpg",)
FILE_PER = ("spread", "pagine")
SEGNAPOSTI = ("album", "n", "pagina", "prodotto")
MAX_SEGNAPOSTI = 4                                # con 80 caratteri di modello e 40 per segnaposto il nome sta sotto i 255 di ogni sistema
_VIETATI = re.compile(r'[<>:"/\\|?*]')
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
_DATA = re.compile(r"\d{4}-\d{2}-\d{2}")
_SEGNAPOSTO = re.compile(r"\{([^{}]*)\}")
PPI_MINIMI, PPI_CONSIGLIATI = 150, 200            # come editor.server.RIS_BLOCCA e RIS_GUARDA: valgono se il prodotto non dice altro

CHIAVI = ("formato_catalogo", "id", "nome", "laboratorio", "data", "prodotti")
CHIAVI_FACOLTATIVE = ("generico", "stato", "fonte", "note", "id_firma", "firma")
PRODOTTO = ("id", "nome", "pagina_cm", "abbondanza_mm", "ppi", "consegna")
PRODOTTO_FACOLTATIVE = ("descrizione", "spread_min", "spread_max", "sicurezza_mm", "piega_mm", "ppi_minimi", "ppi_consigliati", "profilo_colore", "copertina")
CONSEGNA = ("nome",)
CONSEGNA_FACOLTATIVE = ("formato", "qualita", "file", "cifre")


class CatalogoNonValido(V.ErroreProgetto):
    """il catalogo non si può usare: il messaggio dice dove e perché"""


def _id(v, dove):
    if not isinstance(v, str) or not _ID.fullmatch(v): raise CatalogoNonValido(lingua.t("laboratori.id_non_valido", dove=dove))
    return v


def _controlla(fn, *a, **kw):
    """le funzioni di validazione con CatalogoNonValido al posto di ErroreProgetto"""
    try: return fn(*a, **kw)
    except CatalogoNonValido: raise
    except V.ErroreProgetto as e: raise CatalogoNonValido(str(e)) from None


def modello_nome(v, dove, per_pagine):
    """nome dei file di consegna, senza estensione: testo semplice con i segnaposti {album} {n} {pagina} {prodotto} (al
    massimo MAX_SEGNAPOSTI); deve contenere {n} (o {pagina} se c'è un file per pagina), così due file non hanno mai lo
    stesso nome. Le graffe valgono solo come segnaposti: il modello non passa mai da str.format"""
    V.testo(v, dove, 80)
    trovati = _SEGNAPOSTO.findall(v); resto = _SEGNAPOSTO.sub("", v)
    for s in trovati:
        if s not in SEGNAPOSTI: V.errore(dove, "laboratori.segnaposto_sconosciuto", segnaposto="{" + s + "}", validi=", ".join("{" + x + "}" for x in SEGNAPOSTI))
    if len(trovati) > MAX_SEGNAPOSTI: V.errore(dove, "laboratori.troppi_segnaposti", massimo=MAX_SEGNAPOSTI)
    if "{" in resto or "}" in resto: V.errore(dove, "laboratori.graffe")
    if _VIETATI.search(resto): V.errore(dove, "laboratori.carattere_nome_file", caratteri='< > : " / \\ | ? *')
    serve = "{pagina}" if per_pagine else "{n}"
    if serve not in v: V.errore(dove, "laboratori.serve_segnaposto", segnaposto=serve)
    return v


def _consegna(v, dove):
    V.oggetto(v, dove, CONSEGNA, CONSEGNA_FACOLTATIVE)
    out = dict(formato=V.scelta(v.get("formato", "jpg"), f"{dove}, formato", FORMATI_FILE),
               qualita=V.numero(v.get("qualita", 95), f"{dove}, qualita", 80, 100, intero=True),
               file=V.scelta(v.get("file", "spread"), f"{dove}, file", FILE_PER),
               cifre=V.numero(v.get("cifre", 2), f"{dove}, cifre", 1, 4, intero=True))
    out["nome"] = modello_nome(v["nome"], f"{dove}, nome", out["file"] == "pagine")
    return out


def prodotto(v, dove="prodotto"):
    """un prodotto controllato e completo (i valori che mancano diventano quelli predefiniti): dizionario nuovo"""
    return _controlla(_prodotto, v, dove)


def _prodotto(v, dove):
    V.oggetto(v, dove, PRODOTTO, PRODOTTO_FACOLTATIVE)
    d = lambda k: f"{dove}, {k}"
    out = dict(id=_id(v["id"], d("id")), nome=V.testo(v["nome"], d("nome"), 80))
    if "descrizione" in v: out["descrizione"] = V.testo(v["descrizione"], d("descrizione"), 300)
    w, h = V.lista(v["pagina_cm"], d("pagina_cm"), 2, 2)
    out["pagina_cm"] = [V.numero(w, d("pagina_cm, larghezza"), 5, 150), V.numero(h, d("pagina_cm, altezza"), 5, 200)]
    for k in ("spread_min", "spread_max"):
        if k in v: out[k] = V.numero(v[k], d(k), 1, 500, intero=True)
    if out.get("spread_min", 1) > out.get("spread_max", 500): V.errore(d("spread_max"), "laboratori.spread_max")
    out["abbondanza_mm"] = V.numero(v["abbondanza_mm"], d("abbondanza_mm"), 0, 20)
    out["sicurezza_mm"] = V.numero(v.get("sicurezza_mm", 0), d("sicurezza_mm"), 0, 50)
    out["piega_mm"] = V.numero(v.get("piega_mm", 0), d("piega_mm"), 0, 50)
    if 2 * out["sicurezza_mm"] >= 10 * min(out["pagina_cm"]): V.errore(d("sicurezza_mm"), "laboratori.sicurezza_troppa")
    out["ppi"] = V.numero(v["ppi"], d("ppi"), 150, 600, intero=True)
    out["ppi_minimi"] = V.numero(v.get("ppi_minimi", min(PPI_MINIMI, out["ppi"])), d("ppi_minimi"), 72, out["ppi"], intero=True)
    out["ppi_consigliati"] = V.numero(v.get("ppi_consigliati", max(out["ppi_minimi"], min(PPI_CONSIGLIATI, out["ppi"]))), d("ppi_consigliati"), out["ppi_minimi"], 1200, intero=True)
    out["profilo_colore"] = V.scelta(v.get("profilo_colore", "sRGB"), d("profilo_colore"), PROFILI)
    out["consegna"] = _consegna(v["consegna"], d("consegna"))
    if "copertina" in v: out["copertina"] = V.testo(v["copertina"], d("copertina"), 500)
    return out


def formato(v, dove):
    """il numero del formato: FORMATO e nient'altro"""
    if isinstance(v, bool) or v != FORMATO: V.errore(dove, "laboratori.formato_atteso", atteso=FORMATO)
    return v


def _data(v, dove):
    V.testo(v, dove, 10)
    if not _DATA.fullmatch(v): V.errore(dove, "laboratori.data")
    return v


def valida(doc, dove="catalogo", interno=False):
    """catalogo controllato: {id, nome, laboratorio, data, generico, stato, fonte, note, prodotti: [prodotti completi]}.
    Solo i cataloghi del programma (interno=True) possono dirsi generici. CatalogoNonValido con il motivo"""
    return _controlla(_valida, doc, dove, interno)


def _valida(doc, dove, interno):
    if not isinstance(doc, dict): V.errore(dove, "progetto.contiene_oggetto")
    f = doc.get("formato_catalogo")
    if isinstance(f, int) and not isinstance(f, bool) and f > FORMATO: V.errore(dove, "laboratori.formato_piu_recente")
    V.oggetto(doc, dove, CHIAVI, CHIAVI_FACOLTATIVE)
    d = lambda k: f"{dove}, {k}"
    formato(f, d("formato_catalogo"))
    out = dict(id=_id(doc["id"], d("id")), nome=V.testo(doc["nome"], d("nome"), 80), laboratorio=V.testo(doc["laboratorio"], d("laboratorio"), 80),
               data=_data(doc["data"], d("data")), generico=V.booleano(doc.get("generico", False), d("generico")),
               stato=V.scelta(doc.get("stato", "confermato"), d("stato"), STATI))
    if out["generico"] and not interno: V.errore(d("generico"), "laboratori.generico")
    for k, n in (("fonte", 300), ("note", 1000)):
        if k in doc: out[k] = V.testo(doc[k], d(k), n, libero=k == "note")
    lst = V.lista(doc["prodotti"], d("prodotti"), MAX_PRODOTTI)
    if not lst: V.errore(d("prodotti"), "laboratori.almeno_un_prodotto")
    out["prodotti"] = [_prodotto(p, f"{dove}, {lingua.t('laboratori.dove_prodotto', n=str(k))}") for k, p in enumerate(lst, 1)]
    ids = [p["id"] for p in out["prodotti"]]
    doppi = sorted({i for i in ids if ids.count(i) > 1})
    if doppi: V.errore(d("prodotti"), "laboratori.id_prodotti_doppi", ids=", ".join(doppi))
    return out


def canonico(doc):
    """byte firmati del catalogo: JSON canonico (chiavi ordinate, senza spazi, UTF-8) senza il campo «firma»"""
    return K.canonico(doc)


def firma(doc, seme, id_firma):
    """il catalogo firmato (copia) con la chiave privata `seme`: serve allo strumento del produttore e alle prove"""
    out = {k: v for k, v in doc.items() if k != "firma"}; out["id_firma"] = id_firma
    out["firma"] = ed25519.firma(seme, DOMINIO_CATALOGO + canonico(out)).hex()
    return out


def verifica(doc, pubbliche=None):
    """(verificato, motivo) della firma del catalogo (già controllato da valida). Firma presente e sbagliata, o fatta con una
    chiave ritirata: CatalogoNonValido. Senza firma, o con una chiave che questa copia non può usare: non verificato, e il
    motivo lo dice"""
    pubbliche = K.CHIAVI_PUBBLICHE if pubbliche is None else pubbliche
    idf, fh = doc.get("id_firma"), doc.get("firma")
    if idf is None and fh is None: return False, lingua.t("laboratori.non_firmato")
    if isinstance(idf, bool) or not isinstance(idf, int) or not isinstance(fh, str) or not re.fullmatch(r"[0-9a-f]{128}", fh):
        raise CatalogoNonValido(lingua.t("laboratori.firma_incompleta"))
    p = pubbliche.get(idf)
    if p is None: return False, lingua.t("laboratori.chiave_sconosciuta", numero=str(idf))
    pub = K._bytes_pubblica(p)
    if pub is None: return False, lingua.t("laboratori.senza_chiave")
    if not ed25519.verifica(pub, DOMINIO_CATALOGO + canonico(doc), bytes.fromhex(fh)):
        raise CatalogoNonValido(lingua.t("laboratori.firma_non_corrisponde"))
    if p.emesse_fino and doc["data"] > p.emesse_fino:
        raise CatalogoNonValido(lingua.t("laboratori.firma_ritirata"))
    return True, lingua.t("laboratori.firmato_dal_produttore")
