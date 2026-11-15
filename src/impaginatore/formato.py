"""Formato di salvataggio dei progetti: l'unico modulo che legge e scrive l'impaginazione e i file JSON del progetto.

Un progetto è una cartella con:
    progetto.json    impostazioni, correzioni, testi, guide (JSON, UTF-8)
    album.json       impaginazione (formato 2, JSON puro: solo dati, mai codice). Schema in docs/architettura/FORMATO-PROGETTO.md
    Foto/, _cache/, _backup_editor/, PSD/, Esportazioni/

I progetti delle versioni 1.x hanno spec.py (codice Python) al posto di album.json: alla prima apertura spec.py si legge
SENZA eseguirlo (formato_1x, con ast), si scrive album.json e spec.py diventa spec.py.1x (copia di sicurezza, mai più
letta). Un progetto si può ancora esportare per la 1.x (formato_1x.esporta), su richiesta.

Ogni file si scrive in modo atomico (file temporaneo nella stessa cartella, fsync, os.replace): un'interruzione a metà
lascia il file di prima, mai uno troncato.
"""
import json
import os
import shutil
import stat
import tempfile

from . import formato_1x
from .validazione import FORMATO, PAGINE, ErroreProgetto
from . import validazione as V

ALBUM = "album.json"
SPEC = formato_1x.SPEC
PROGETTO = "progetto.json"
COPIA_1X = "spec.py.1x"                      # spec.py di un progetto 1.x dopo la conversione (con .2, .3... se c'è già)
MAX_ALBUM = 10 * 2**20
MAX_JSON = 256 * 2**20                       # progetto.json, meta.json, faces.json (migliaia di foto stanno sotto i 50 MB)
_CONTEGGI = {}                               # percorso -> (mtime, dimensione, numero di spread): per l'elenco della home


# ---------------------------------------------------------------- file
def leggi_json(path, massimo=MAX_JSON):
    """contenuto di un file JSON (UTF-8) non più grande di `massimo` byte"""
    with open(path, "rb") as f: dati = f.read(massimo + 1)
    if len(dati) > massimo: raise ErroreProgetto(f"{os.path.basename(path)} è troppo grande ({len(dati) // 2**20} MB)")
    return json.loads(dati.decode("utf-8-sig"))


def _coppie(coppie):
    d = {}
    for k, v in coppie:
        if k in d: raise ValueError(f"la chiave «{k}» compare due volte")
        d[k] = v
    return d


def _costante(v): raise ValueError(f"valore non ammesso: {v}")


def leggi_json_rigoroso(path, massimo=MAX_ALBUM):
    """come leggi_json, ma per i file che arrivano da altri e si controllano chiave per chiave: niente chiavi doppie, niente
    NaN o Infinity. Ogni problema è un ErroreProgetto con il nome del file"""
    nome = os.path.basename(path)
    try:
        with open(path, "rb") as f: dati = f.read(massimo + 1)
        if len(dati) > massimo: raise ErroreProgetto(f"{nome} è troppo grande (al massimo {massimo // 2**20} MB)")
        return json.loads(dati.decode("utf-8"), object_pairs_hook=_coppie, parse_constant=_costante)
    except UnicodeDecodeError as e: raise ErroreProgetto(f"{nome} non è un testo UTF-8 (byte {e.start})") from None
    except json.JSONDecodeError as e: raise ErroreProgetto(f"{nome} non è un JSON valido (riga {e.lineno}, colonna {e.colno}: {e.msg})") from None
    except (ValueError, RecursionError) as e: raise ErroreProgetto(f"{nome} non è valido: {e}") from None


def scrivi_atomico(path, testo):
    """scrive il file in modo sicuro: un file temporaneo nella stessa cartella (nome unico, creato in esclusiva), fsync,
    poi os.replace al posto di quello vero e fsync della cartella. Un blocco a metà lascia il file com'era"""
    _sostituisci(path, lambda f: f.write(testo.encode("utf-8")))


def scrivi_json(path, dati, **kw):
    """come json.dump (stessi argomenti), sempre in UTF-8 e in modo atomico"""
    scrivi_atomico(path, json.dumps(dati, **kw))


def copia_atomica(src, dst):
    """copia src in dst in modo atomico (copie di sicurezza), con la data di modifica dell'originale"""
    def scrivi(f):
        with open(src, "rb") as s: shutil.copyfileobj(s, f, 1 << 20)
    _sostituisci(dst, scrivi); st = os.stat(src); os.utime(dst, ns=(st.st_atime_ns, st.st_mtime_ns))


def _sostituisci(path, scrivi):
    cartella = os.path.dirname(os.path.abspath(path))
    try: modo = stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError: modo = 0o644
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=cartella)
    try:
        with os.fdopen(fd, "wb") as f: scrivi(f); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, modo)
        os.replace(tmp, path)
    except BaseException:
        try: os.remove(tmp)
        except OSError: pass
        raise
    _sincronizza(cartella)


def _sincronizza(cartella):
    """fsync della cartella: la sostituzione resta anche se il computer si spegne subito dopo (dove si può: non su Windows)"""
    try: fd = os.open(cartella, os.O_RDONLY)
    except OSError: return
    try: os.fsync(fd)
    except OSError: pass
    finally: os.close(fd)


# ---------------------------------------------------------------- album.json
def _elemento(it, nome_foto):
    """un elemento dell'impaginazione in memoria come oggetto di album.json (le stesse informazioni che le 1.x salvavano
    in spec.py, più zo e ts dove la 1.x li perdeva)"""
    if formato_1x.is_txt(it):
        e = {"k": "t", "kind": "txt", "tx": it["tx"], "fx": it["fx"], "fy": it["fy"], "fw": it["fw"], "fh": it["fh"], "font": it["font"],
             "size": it["size"], "col": list(it["col"]), "al": it["al"], "tr": it["tr"]}
        if not it.get("auto", True): e["auto"] = False
        if formato_1x._lead(it) != 1.2: e["lh"] = formato_1x._lead(it)
        if it.get("caps"): e["caps"] = True
        if it.get("zo") is not None: e["zo"] = it["zo"]
        if it.get("stile"): e["stile"] = it["stile"]
        return e
    if it["k"] == "t":
        e = {"k": "t", "kind": it["kind"]}
        e.update({k: it[k] for k in (("fx", "fy", "fw", "fh") if "fx" in it else ("c", "r", "w", "h"))})
        if it.get("ts") not in (None, 1, 1.0): e["ts"] = it["ts"]
        if it.get("zo") is not None: e["zo"] = it["zo"]
        return e
    e = {"k": it["k"], "foto": nome_foto(it["i"])}
    e.update({k: it[k] for k in {"p": ("c", "r", "w", "h"), "f": ("x", "y", "w", "h"), "full": ()}[it["k"]]})
    if it.get("bw"): e["bw"] = True
    if it.get("z", 1.0) != 1.0: e["z"] = it["z"]
    if it.get("zo") is not None: e["zo"] = it["zo"]
    if it.get("a"): e["a"] = it["a"]
    if it.get("bd"): e["bd"] = [it["bd"][0], it["bd"][1]]
    if int(it.get("sh") or 0): e["sh"] = int(it["sh"])
    if int(it.get("oc", 100)) < 100: e["oc"] = int(it["oc"])
    return e


def documento(spreads, nome_foto):
    """album.json (come dizionario) per l'impaginazione `spreads` ([[modo, [elementi]], [modo, [elementi]]] per spread);
    nome_foto(i) dà il nome del file (senza estensione) della foto numero i"""
    from . import __version__
    return {"formato": FORMATO, "programma": f"Impaginatore {__version__}",
            "spread": [{lato: {"modo": pg[0], "elementi": [_elemento(it, nome_foto) for it in pg[1]]} for lato, pg in zip(PAGINE, sp)} for sp in spreads]}


def testo_album(doc):
    """album.json come testo: un elemento per riga (si legge e si confronta bene anche a occhio)"""
    j = lambda v: json.dumps(v, ensure_ascii=False, allow_nan=False)
    spread = []
    for sp in doc["spread"]:
        pagine = []
        for lato in PAGINE:
            el = sp[lato]["elementi"]
            corpo = "[\n" + ",\n".join("        " + j(e) for e in el) + "\n      ]" if el else "[]"
            pagine.append(f'      {j(lato)}: {{"modo": {j(sp[lato]["modo"])}, "elementi": {corpo}}}')
        spread.append("    {\n" + ",\n".join(pagine) + "\n    }")
    corpo = "[\n" + ",\n".join(spread) + "\n  ]" if spread else "[]"
    return f'{{\n  "formato": {j(doc["formato"])},\n  "programma": {j(doc.get("programma", ""))},\n  "spread": {corpo}\n}}\n'


def leggi_album(path, foto=None):
    """album.json controllato (vedi validazione.album); foto = nomi delle foto del progetto (None: non si controllano)"""
    doc = leggi_json_rigoroso(path, MAX_ALBUM)
    V.formato_album(doc)
    return V.album(doc, foto)


def da_documento(doc):
    """impaginazione in memoria da album.json (già controllato): gli elementi si costruiscono con i costruttori del motore,
    gli stessi che usava spec.py, quindi lo stato è identico a quello delle 1.x. Il motore dev'essere caricato con il progetto"""
    from .motore import album as A
    from .motore import album_libere as L
    out = []
    for sp in doc["spread"]:
        out.append([[sp[lato]["modo"], [_costruisci(e, A, L) for e in sp[lato]["elementi"]]] for lato in PAGINE])
    return out


def _costruisci(e, A, L):
    k = e["k"]
    if k == "t" and e["kind"] == "txt":
        return L.TEXT(e["tx"], e["fx"], e["fy"], e["fw"], e["fh"], font=e["font"], size=e["size"], col=tuple(e["col"]), al=e["al"], tr=e["tr"],
                      auto=e.get("auto", True), zo=e.get("zo"), stile=e.get("stile"), lh=e.get("lh", 1.2), caps=e.get("caps", False))
    if k == "t" and "fx" in e: return L.TXTF(e["kind"], e["fx"], e["fy"], e["fw"], e["fh"], ts=e.get("ts", 1.0), zo=e.get("zo"))
    if k == "t":
        it = A.TXT(e["kind"], e["c"], e["r"], e["w"], e["h"])
        it.update({x: e[x] for x in ("ts", "zo") if x in e})
        return it
    bw, z = e.get("bw", False), e.get("z", 1.0)
    if k == "f": it = L.FREE(e["foto"], e["x"], e["y"], e["w"], e["h"], bw=bw, z=z, zo=e.get("zo"))
    else:
        it = A.P(e["foto"], e["c"], e["r"], e["w"], e["h"], bw=bw, z=z) if k == "p" else A.FULL(e["foto"], bw=bw, z=z)
        if "zo" in e: it["zo"] = e["zo"]
    if "bd" in e or "sh" in e or "oc" in e: it = L.STY(it, bd=e.get("bd"), sh=e.get("sh", 0), oc=e.get("oc", 100))
    return L.ROT(it, e["a"]) if e.get("a") else it


def salva(cartella, spreads, nome_foto):
    """scrive album.json (controllato prima di scriverlo: mai un file che poi non si riapre)"""
    doc = documento(spreads, nome_foto)
    V.album(doc)
    scrivi_atomico(os.path.join(cartella, ALBUM), testo_album(doc))
    return doc


def album_vuoto():
    """album.json di un progetto nuovo"""
    from . import __version__
    return testo_album({"formato": FORMATO, "programma": f"Impaginatore {__version__}", "spread": []})


# ---------------------------------------------------------------- apertura
def file_album(cartella):
    """il file dell'impaginazione: album.json, oppure spec.py di un progetto 1.x non ancora convertito, oppure None"""
    for f in (ALBUM, SPEC):
        p = os.path.join(cartella, f)
        if os.path.isfile(p): return p
    return None


def carica(cartella):
    """impaginazione del progetto ([[modo, [elementi]], [modo, [elementi]]] per spread). Il motore
    (impaginatore.motore.album) dev'essere già caricato con lo stesso progetto: servono i nomi delle foto.
    Un progetto 1.x (solo spec.py) si converte qui, una volta: vedi converti_1x"""
    from .motore import album as A
    from .motore import album_libere  # noqa: F401  (insegna al motore le cornici libere)
    cartella = os.path.abspath(cartella)
    p = os.path.join(cartella, ALBUM)
    if os.path.isfile(p): return da_documento(leggi_album(p, set(A.IDX)))
    if os.path.isfile(os.path.join(cartella, SPEC)): return converti_1x(cartella)
    return []


def documento_1x(path):
    """album.json (dizionario controllato) da uno spec.py delle 1.x, letto senza eseguirlo (formato_1x). Il motore
    dev'essere caricato con il progetto (nomi e numeri delle foto)"""
    from .motore import album as A
    spreads = formato_1x.leggi_file(path)

    def nome_foto(i):
        if not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < len(A.M): raise ErroreProgetto(f"spec.py: la foto numero {i + 1 if isinstance(i, int) else i} non esiste nel progetto")
        return A.name(i)
    try: doc = documento(spreads, nome_foto)
    except ErroreProgetto: raise
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as e: raise ErroreProgetto(f"spec.py: un elemento non è valido ({e!r})") from None
    try: return V.album(doc, set(A.IDX))
    except ErroreProgetto as e: raise ErroreProgetto(f"spec.py non valido: {e}") from None


def converti_1x(cartella):
    """spec.py (1.x) -> album.json, senza eseguire niente; spec.py resta come spec.py.1x (copia, mai più letta).
    Restituisce l'impaginazione"""
    src = os.path.join(cartella, SPEC)
    doc = documento_1x(src)
    scrivi_atomico(os.path.join(cartella, ALBUM), testo_album(doc))
    os.replace(src, _libero(os.path.join(cartella, COPIA_1X)))
    return da_documento(doc)


def _libero(p):
    k = 2; out = p
    while os.path.exists(out): out = f"{p}.{k}"; k += 1
    return out


def controlla(cartella):
    """controlla l'impaginazione di un progetto senza il motore e senza eseguire niente; restituisce il numero di spread.
    Errori: ErroreProgetto con un messaggio per l'utente (la home lo mostra prima di aprire l'editor)"""
    p = file_album(cartella)
    if p is None: return 0
    if os.path.basename(p) == ALBUM: return len(leggi_album(p)["spread"])
    return len(formato_1x.leggi_file(p, prova=True))


def conta_spread(cartella):
    """numero di spread di un progetto (per l'elenco della home), ricordato finché il file non cambia"""
    p = file_album(cartella)
    if p is None: return 0
    st = os.stat(p); k = (st.st_mtime_ns, st.st_size)
    if _CONTEGGI.get(p, (None,))[0] != k: _CONTEGGI[p] = (k, controlla(cartella))
    return _CONTEGGI[p][1]


def leggi_progetto(cartella):
    """progetto.json controllato (validazione.progetto)"""
    p = os.path.join(cartella, PROGETTO)
    try: cfg = leggi_json(p)
    except (UnicodeDecodeError, json.JSONDecodeError) as e: raise ErroreProgetto(f"{PROGETTO} non è un JSON valido ({e})") from None
    return V.progetto(cfg)


def prepara_importato(cartella):
    """progetto arrivato da fuori (ZIP o pacchetto esportato): controlla progetto.json e impaginazione e toglie i percorsi
    del computer di chi l'ha esportato (foto, foto_extra, uscita_psd: li rimette l'editor all'apertura; le foto
    dell'elenco in _cache/meta.json si cercano solo nella cartella Foto del progetto, mai altrove sul tuo computer)"""
    cfg = leggi_progetto(cartella)
    controlla(cartella)
    cfg["foto"] = ""; cfg["foto_extra"] = []; cfg["uscita_psd"] = ""
    scrivi_json(os.path.join(cartella, PROGETTO), cfg, indent=2, ensure_ascii=False)
    mp = os.path.join(cartella, "_cache", "meta.json")
    if os.path.exists(mp):
        try: m = V.meta(leggi_json(mp))
        except (ValueError, RecursionError): os.remove(mp)                # elenco non valido: l'editor lo rifà dalle foto
        else: scrivi_json(mp, [dict(x, src="Foto/" + x["n"]) for x in m])
    return cfg
