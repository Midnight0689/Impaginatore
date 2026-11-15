"""Controllo dei dati letti dai file di un progetto: album.json, modelli dell'utente, progetto.json, cache delle foto.

Un progetto può arrivare da un'altra persona (ZIP, cartella condivisa): ogni file è un dato non fidato. Prima di usarlo si
controllano tipi, intervalli e chiavi; un problema produce sempre ErroreProgetto con un messaggio che dice dove
(«spread 3, pagina sinistra, elemento 2, z: deve essere un numero maggiore di 0 e non oltre 20»), mai un'eccezione
qualsiasi più avanti, mai codice eseguito. Lo schema completo è in docs/architettura/FORMATO-PROGETTO.md.
"""
import math
import os
import re

from .nomi import invisibile

FORMATO = 2                              # versione del formato di album.json scritta e letta da questo programma
NC, NR = 12, 8                           # griglia di ogni pagina (come motore.album)
MAX_SPREAD = 2000
MAX_ELEMENTI = 500                       # per pagina
MAX_TESTO = 100000                       # caratteri di un livello di testo
MAX_MODELLI = 1000
MAX_FOTO = 100000
MAX_PIXEL = 4e9                          # pixel dello spread intero alla risoluzione finale (300 x 200 cm a 300 ppi sono 0,84 miliardi)
PAGINE = ("sinistra", "destra")
_COLORE = re.compile(r"#[0-9a-fA-F]{6}")
_ID = re.compile(r"[A-Za-z0-9_-]{1,40}")
_FOTO_OPZ = ("bw", "z", "a", "bd", "sh", "oc", "zo")
TIPI = {                                 # tipo di elemento: (chiavi obbligatorie, chiavi facoltative); ogni altra chiave è un errore
    "p": (("k", "foto", "c", "r", "w", "h"), _FOTO_OPZ),
    "full": (("k", "foto"), _FOTO_OPZ),
    "f": (("k", "foto", "x", "y", "w", "h"), _FOTO_OPZ),
    "titolo": (("k", "kind", "c", "r", "w", "h"), ("ts", "zo")),
    "titolo_libero": (("k", "kind", "fx", "fy", "fw", "fh"), ("ts", "zo")),
    "txt": (("k", "kind", "tx", "fx", "fy", "fw", "fh", "font", "size", "col", "al", "tr"), ("auto", "lh", "caps", "zo", "stile")),
}
MODELLO_TIPI = {"p": (("k", "c", "r", "w", "h"), ("a", "zo")), "f": (("k", "x", "y", "w", "h"), ("a", "zo")), "full": (("k",), ("a", "zo"))}
STILE_K = ("font", "size", "col", "al", "tr")


class ErroreProgetto(ValueError):
    """dati di un progetto non validi: il messaggio è pensato per l'utente"""


def errore(dove, msg):
    raise ErroreProgetto(f"{dove}: {msg}" if dove else msg)


def _n(v): return f"{v:g}"


# ---------------------------------------------------------------- tipi semplici
def numero(v, dove, minimo, massimo, intero=False, escluso=False):
    """numero finito (non booleano) da `minimo` a `massimo`; con escluso=True deve essere maggiore di `minimo`"""
    if isinstance(v, bool) or not isinstance(v, int if intero else (int, float)): errore(dove, "deve essere un numero intero" if intero else "deve essere un numero")
    if (isinstance(v, float) and not math.isfinite(v)) or v > massimo or v < minimo or (escluso and v == minimo):
        errore(dove, f"deve essere un numero maggiore di {_n(minimo)} e non oltre {_n(massimo)}" if escluso else f"deve essere un numero da {_n(minimo)} a {_n(massimo)}")
    return v


def finito(v, dove, limite=1e6):
    """numero qualsiasi purché finito e non enorme (valori che l'editor scrive senza limiti)"""
    return numero(v, dove, -limite, limite)


def booleano(v, dove):
    if not isinstance(v, bool): errore(dove, "deve essere vero o falso (true / false)")
    return v


def testo(v, dove, massimo=200, vuoto=False, libero=False):
    """testo di al massimo `massimo` caratteri; libero=True ammette a capo e simili (testi delle pagine), mai i surrogati"""
    if not isinstance(v, str): errore(dove, "deve essere un testo")
    if not v and not vuoto: errore(dove, "non può essere vuoto")
    if len(v) > massimo: errore(dove, f"è troppo lungo (al massimo {massimo} caratteri)")
    for c in v:
        if "\ud800" <= c <= "\udfff" or (not libero and invisibile(c)): errore(dove, f"contiene un carattere non ammesso (U+{ord(c):04X})")
    return v


def scelta(v, dove, valori):
    if not isinstance(v, str) or v not in valori: errore(dove, "deve essere uno tra " + ", ".join(f"«{x}»" for x in valori))
    return v


def oggetto(v, dove, obbligatorie, facoltative=()):
    """dizionario con tutte le chiavi obbligatorie e nessuna chiave oltre a quelle previste"""
    if not isinstance(v, dict): errore(dove, "deve essere un oggetto { … }")
    manca = [k for k in obbligatorie if k not in v]
    if manca: errore(dove, "manca " + ", ".join(f"«{k}»" for k in manca))
    altre = sorted(str(k) for k in v if k not in obbligatorie and k not in facoltative)
    if altre: errore(dove, "chiave sconosciuta " + ", ".join(f"«{k}»" for k in altre))
    return v


def lista(v, dove, massimo, lunghezza=None):
    if not isinstance(v, list): errore(dove, "deve essere un elenco [ … ]")
    if lunghezza is not None and len(v) != lunghezza: errore(dove, f"deve avere {lunghezza} valori")
    if len(v) > massimo: errore(dove, f"troppi elementi (al massimo {massimo})")
    return v


def dizionario(v, dove, massimo=MAX_FOTO):
    """dizionario con chiavi di testo (es. nome della foto -> valore)"""
    if not isinstance(v, dict): errore(dove, "deve essere un oggetto { … }")
    if len(v) > massimo: errore(dove, f"troppi elementi (al massimo {massimo})")
    for k in v: testo(k, dove, 4096, vuoto=True, libero=True)
    return v


def nome_file(v, dove):
    """solo un nome di file: niente separatori di cartella (/, e \\ su Windows), niente «.» e «..»"""
    testo(v, dove, 255, libero=True)
    if any(s in v for s in {"/", os.sep, os.altsep or "/"}) or v in (".", ".."): errore(dove, f"«{v}» non è un nome di file valido")
    return v


# ---------------------------------------------------------------- album.json
def _griglia(el, dove):
    c = numero(el["c"], f"{dove}, c", 0, NC - 1, intero=True); r = numero(el["r"], f"{dove}, r", 0, NR - 1, intero=True)
    w = numero(el["w"], f"{dove}, w", 1, NC, intero=True); h = numero(el["h"], f"{dove}, h", 1, NR, intero=True)
    if c + w > NC or r + h > NR: errore(dove, f"la cornice esce dalla griglia della pagina ({NC} colonne per {NR} righe)")


def _riquadro(el, dove, chiavi, escluso):
    """posizione e misura in frazioni della pagina: può uscire dalla pagina (anche sull'altra), non oltre 10 pagine;
    escluso=True: la misura dev'essere maggiore di 0 (cornici di foto)"""
    x, y, w, h = chiavi
    numero(el[x], f"{dove}, {x}", -10, 10); numero(el[y], f"{dove}, {y}", -10, 10)
    numero(el[w], f"{dove}, {w}", 0, 10, escluso=escluso); numero(el[h], f"{dove}, {h}", 0, 10, escluso=escluso)


def _bordo(v, dove):
    if not isinstance(v, list) or len(v) != 2: errore(dove, 'deve essere [millimetri, "#rrggbb"]')
    numero(v[0], dove, 0, 100)
    if not isinstance(v[1], str) or not _COLORE.fullmatch(v[1]): errore(dove, 'il colore deve essere nella forma "#rrggbb"')


def _rgb(v, dove):
    lista(v, dove, 3, 3)
    for x in v: numero(x, dove, 0, 255, intero=True)


def tipo_elemento(el, dove):
    if not isinstance(el, dict): errore(dove, "deve essere un oggetto { … }")
    k = el.get("k")
    if k in ("p", "full", "f"): return k
    if k != "t": errore(f"{dove}, k", "tipo di elemento sconosciuto: deve essere «p», «full», «f» o «t»")
    kind = el.get("kind")
    if kind == "txt": return "txt"
    if kind not in ("title", "end"): errore(f"{dove}, kind", "deve essere «txt», «title» o «end»")
    return "titolo_libero" if "fx" in el else "titolo"


def elemento(el, dove, foto=None):
    """un elemento di una pagina di album.json; `foto` = nomi delle foto del progetto (None: non si controllano)"""
    t = tipo_elemento(el, dove); oggetto(el, dove, *TIPI[t])
    d = lambda k: f"{dove}, {k}"
    if t in ("p", "full", "f"):
        testo(el["foto"], d("foto"), 255, libero=True)
        if foto is not None and el["foto"] not in foto: errore(d("foto"), f"la foto «{el['foto']}» non è nel progetto")
        if "bw" in el: booleano(el["bw"], d("bw"))
        if "z" in el: numero(el["z"], d("z"), -100, 100)             # 1 = nessun ingrandimento; sotto 1 non ha effetto
        if "a" in el: numero(el["a"], d("a"), -360, 360)
        if "bd" in el: _bordo(el["bd"], d("bd"))
        if "sh" in el: numero(el["sh"], d("sh"), 0, 100, intero=True)
        if "oc" in el: numero(el["oc"], d("oc"), 0, 100, intero=True)
    if t in ("p", "titolo"): _griglia(el, dove)
    if t == "f": _riquadro(el, dove, ("x", "y", "w", "h"), True)              # una cornice di foto deve avere una misura
    if t in ("titolo_libero", "txt"): _riquadro(el, dove, ("fx", "fy", "fw", "fh"), False)
    if "zo" in el: numero(el["zo"], d("zo"), -10**6, 10**6, intero=True)
    if "ts" in el: numero(el["ts"], d("ts"), 0.05, 20)
    if t == "txt":
        testo(el["tx"], d("tx"), MAX_TESTO, vuoto=True, libero=True)
        testo(el["font"], d("font"), 200, vuoto=True, libero=True)
        numero(el["size"], d("size"), 0, 5000, escluso=True)
        _rgb(el["col"], d("col"))
        scelta(el["al"], d("al"), ("left", "center", "right"))
        numero(el["tr"], d("tr"), -1000, 5000)
        if "auto" in el: booleano(el["auto"], d("auto"))
        if "lh" in el: numero(el["lh"], d("lh"), 0.1, 10)
        if "caps" in el: booleano(el["caps"], d("caps"))
        if "stile" in el: testo(el["stile"], d("stile"), 200, libero=True)
    return el


def formato_album(doc):
    """numero di formato di un documento album.json (controlla solo quello)"""
    if not isinstance(doc, dict): errore("album.json", "deve contenere un oggetto { … }")
    if "formato" not in doc: errore("album.json", "manca «formato»: non è un album dell'Impaginatore")
    f = doc["formato"]
    if isinstance(f, int) and not isinstance(f, bool) and f > FORMATO:
        errore("", f"Questo album è stato salvato da una versione più recente dell'Impaginatore (formato {f}): aggiorna il programma per aprirlo")
    if f != FORMATO or isinstance(f, bool): errore("album.json, formato", f"formato sconosciuto ({f!r}): questo programma legge il formato {FORMATO}")
    return f


def album(doc, foto=None):
    """documento album.json completo; `foto` = nomi delle foto del progetto (None: non si controllano)"""
    formato_album(doc)
    oggetto(doc, "album.json", ("formato", "spread"), ("programma",))
    if "programma" in doc: testo(doc["programma"], "album.json, programma", 200, vuoto=True)
    lista(doc["spread"], "album.json, spread", MAX_SPREAD)
    for s, sp in enumerate(doc["spread"], 1):
        oggetto(sp, f"spread {s}", PAGINE)
        for lato in PAGINE:
            dove = f"spread {s}, pagina {lato}"
            pg = oggetto(sp[lato], dove, ("modo", "elementi"))
            scelta(pg["modo"], f"{dove}, modo", ("I", "W"))
            lista(pg["elementi"], f"{dove}, elementi", MAX_ELEMENTI)
            for e, el in enumerate(pg["elementi"], 1): elemento(el, f"{dove}, elemento {e}", foto)
    return doc


# ---------------------------------------------------------------- modelli salvati dall'utente
def modello(t, dove="modello"):
    """un modello di spread (solo la geometria delle cornici), come lo scrive l'editor in modelli_utente.json"""
    oggetto(t, dove, ("id", "nome", "n", "lato", "pages"))
    if not isinstance(t["id"], str) or not _ID.fullmatch(t["id"]): errore(f"{dove}, id", "deve essere un codice di lettere e cifre (al massimo 40)")
    testo(t["nome"], f"{dove}, nome", 60, libero=True)
    if t["lato"] is not None: scelta(t["lato"], f"{dove}, lato", ("L", "R"))
    numero(t["n"], f"{dove}, n", 1, 2 * MAX_ELEMENTI, intero=True)
    lista(t["pages"], f"{dove}, pages", 2, 2); n = 0
    for k, pg in enumerate(t["pages"]):
        dp = f"{dove}, pagina {PAGINE[k]}"
        oggetto(pg, dp, ("mode", "items")); scelta(pg["mode"], f"{dp}, mode", ("I", "W")); lista(pg["items"], f"{dp}, items", MAX_ELEMENTI)
        if t["lato"] is not None and "LR"[k] != t["lato"] and pg["items"]: errore(dp, "il modello vale solo per l'altra pagina: questa deve essere vuota")
        for j, it in enumerate(pg["items"], 1):
            di = f"{dp}, cornice {j}"
            if not isinstance(it, dict) or it.get("k") not in MODELLO_TIPI: errore(di, "deve essere una cornice «p», «f» o «full»")
            oggetto(it, di, *MODELLO_TIPI[it["k"]])
            if it["k"] == "p": _griglia(it, di)
            if it["k"] == "f": _riquadro(it, di, ("x", "y", "w", "h"), True)
            if "a" in it: numero(it["a"], f"{di}, a", -360, 360)
            if "zo" in it: numero(it["zo"], f"{di}, zo", -10**6, 10**6, intero=True)
            n += 1
    if n != t["n"]: errore(f"{dove}, n", f"dice {t['n']} foto ma le cornici sono {n}")
    return t


def modelli(lst, dove="modelli_utente.json", avvisi=None):
    """i modelli validi di un elenco; quelli non validi si tralasciano (con una riga in `avvisi`)"""
    lista(lst, dove, 10**6)
    out = []
    for k, t in enumerate(lst[:MAX_MODELLI], 1):
        try: out.append(modello(t, f"{dove}, modello {k}"))
        except ErroreProgetto as e:
            if avvisi is not None: avvisi.append(f"modello tralasciato: {e}")
    return out


# ---------------------------------------------------------------- progetto.json
def _stile(v, dove):
    """stile di testo salvato: le sue chiavi finiscono nei livelli di testo, quindi valgono le stesse regole"""
    dizionario(v, dove, 20)
    if "font" in v: testo(v["font"], f"{dove}, font", 200, vuoto=True, libero=True)
    if "size" in v: numero(v["size"], f"{dove}, size", 0, 5000, escluso=True)
    if "col" in v: _rgb(v["col"], f"{dove}, col")
    if "al" in v: scelta(v["al"], f"{dove}, al", ("left", "center", "right"))
    if "tr" in v: numero(v["tr"], f"{dove}, tr", -1000, 5000)


def progetto(cfg):
    """impostazioni del progetto: si controllano le chiavi che il programma usa (tipi, e intervalli dove un valore sbagliato
    bloccherebbe il programma); le chiavi che non conosce restano com'erano (vengono da altre versioni)"""
    if not isinstance(cfg, dict): errore("progetto.json", "deve contenere un oggetto { … }")
    d = lambda k: f"progetto.json, {k}"
    if "formato_cm" not in cfg: errore("progetto.json", "manca «formato_cm» (larghezza e altezza dello spread in cm)")
    for v in lista(cfg["formato_cm"], d("formato_cm"), 2, 2): numero(v, d("formato_cm"), 1, 1000)
    for k, lo, hi in (("ppi", 30, 2400), ("abbondanza_mm", 0, 100), ("spazio_mm", 0, 100), ("margine_mm", 0, 500)):
        if k in cfg: numero(cfg[k], d(k), lo, hi)
    (w, h), ppi, ab = cfg["formato_cm"], cfg.get("ppi", 300), cfg.get("abbondanza_mm", 0)
    if (w + ab / 5) * (h + ab / 5) * (ppi / 2.54) ** 2 > MAX_PIXEL: errore(d("formato_cm"), "formato e risoluzione danno uno spread troppo grande da elaborare")
    if "dimensioni_esatte" in cfg: booleano(cfg["dimensioni_esatte"], d("dimensioni_esatte"))
    for k in ("tono_L", "tono_Z"):
        if k in cfg: finito(cfg[k], d(k))
    for k in ("nome", "foto", "uscita_psd"):
        if k in cfg: testo(cfg[k], d(k), 4096, vuoto=True, libero=True)
    for k in ("foto_extra", "tolte", "stelle", "tono_escl"):
        if k in cfg:
            for x in lista(cfg[k], d(k), MAX_FOTO): testo(x, d(k), 4096, vuoto=True, libero=True)
    if "testo" in cfg:
        t = dizionario(cfg["testo"], d("testo"), 100)
        if "colore" in t: _rgb(t["colore"], d("testo, colore"))
        if "indice_font_testo" in t: numero(t["indice_font_testo"], d("testo, indice_font_testo"), 0, 10000, intero=True)
        for k in ("nome", "sottotitolo", "data", "file_font_testo", "file_font_titolo", "font_titolo_ps", "font_testo_ps"):
            if k in t: testo(t[k], d(f"testo, {k}"), 4096, vuoto=True, libero=True)
    if "esposizione" in cfg:
        e = dizionario(cfg["esposizione"], d("esposizione"), 10)
        if "globale" in e: numero(e["globale"], d("esposizione, globale"), -1000, 1000)
        for k in ("per_cartella", "per_foto"):
            for v in dizionario(e.get(k, {}), d(f"esposizione, {k}")).values(): numero(v, d(f"esposizione, {k}"), -1000, 1000)
    for v in dizionario(cfg.get("centri_volto", {}), d("centri_volto")).values():
        for x in lista(v, d("centri_volto"), 2, 2): finito(x, d("centri_volto"))
    for v in dizionario(cfg.get("bilanciamento_bianco", {}), d("bilanciamento_bianco")).values():
        for x in lista(v, d("bilanciamento_bianco"), 3, 3): numero(x, d("bilanciamento_bianco"), 0, 100)
    for v in dizionario(cfg.get("tono", {}), d("tono")).values():
        dizionario(v, d("tono"), 10)
        for k in ("b", "w", "m"):
            if k in v: finito(v[k], d(f"tono, {k}"))
        for p in lista(v.get("c", []), d("tono, c"), 64):
            for x in lista(p, d("tono, c"), 2, 2): finito(x, d("tono, c"))
    for v in dizionario(cfg.get("ritocco", {}), d("ritocco")).values():
        for k, x in dizionario(v, d("ritocco"), 20).items():
            numero(x, d(f"ritocco, {k}"), -100, 100) if k in ("vib", "sat") else finito(x, d(f"ritocco, {k}"))
    for v in dizionario(cfg.get("colori", {}), d("colori")).values(): testo(v, d("colori"), 40)
    for k, v in dizionario(cfg.get("stili", {}), d("stili"), 1000).items(): _stile(v, d(f"stili, {k}"))
    for g in lista(cfg.get("guide", []), d("guide"), MAX_SPREAD):
        dizionario(g, d("guide"), 10)
        for k in ("v", "h"):
            for x in lista(g.get(k, []), d(f"guide, {k}"), 1000): finito(x, d(f"guide, {k}"))
    return cfg


# ---------------------------------------------------------------- cache delle foto (_cache/meta.json, faces.json)
def meta(m):
    """elenco delle foto con le misure: la numerazione delle foto viene da qui"""
    for k, x in enumerate(lista(m, "_cache/meta.json", MAX_FOTO), 1):
        dove = f"_cache/meta.json, foto {k}"
        if not isinstance(x, dict): errore(dove, "deve essere un oggetto { … }")
        for c in ("n", "dt", "src"):
            if c not in x: errore(dove, f"manca «{c}»")
        nome_file(x["n"], f"{dove}, n"); testo(x["dt"], f"{dove}, dt", 100, vuoto=True, libero=True); testo(x["src"], f"{dove}, src", 4096, vuoto=True, libero=True)
        for c in ("w", "h"): numero(x.get(c), f"{dove}, {c}", 1, 10**7, intero=True)
        numero(x.get("ar"), f"{dove}, ar", 0, 10**7)
    return m


def volti(f):
    """riquadri dei volti trovati in ogni foto: {nome file: [[sinistra, alto, destra, basso], ...]} in frazioni"""
    for v in dizionario(f, "_cache/faces.json").values():
        for r in lista(v, "_cache/faces.json", 1000):
            for x in lista(r, "_cache/faces.json", 4, 4): finito(x, "_cache/faces.json")
    return f
