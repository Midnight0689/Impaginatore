"""Motore di impaginazione album (stile Stefano).

Uso: ogni album ha una cartella di progetto con `progetto.json` e `album.json` (le 1.x avevano `spec.py`).
Il progetto si carica in modo esplicito con carica_progetto(cartella); gli script da riga di comando trovano la cartella con
--progetto <cartella>, con la variabile ALBUM_PROGETTO o nella cartella corrente (progetto_da_argv).
L'impaginazione (SPREADS: lista di coppie pagina sinistra / destra, fatte con i costruttori qui sotto) la legge
formato.carica: dati JSON, mai codice eseguito.

Griglia: ogni pagina 12 colonne x 8 righe, un solo spazio tra le foto (default 2,5 mm) ovunque, anche sulla piega.
Pagine "I" immersive (la griglia arriva al bordo, look flush) e "W" bianche (margine uguale sui 4 lati, default 10 mm).
Nessuna foto attraversa la piega: ogni pagina si compone da sola.

Stato: un progetto per processo. carica_progetto riempie le variabili del modulo (CFG, M, CW, IDX...) che il resto del motore,
gli script e l'editor leggono; importare il modulo non legge niente dal disco.
"""
import contextlib, io, logging, math, os, struct, sys, time
from fractions import Fraction
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .. import formato as _formato
from .. import lingua
from .. import percorsi as _percorsi
from .. import validazione as _V
from ..piattaforma import font as _pfont

# ---------------- progetto ----------------
PROJ = CFG = SRC = CACHE = THUMBS = None             # riempiti da carica_progetto()
CW = CH = PPI = B = G = MG = FOLD = TW = TH = None
M, F, IDX, ORIGINE, FACE_FIX, WB, _ESP, TXTCFG = [], {}, {}, {}, {}, {}, {}, {}
SCARTATE = []                                        # foto non aperte all'ultimo caricamento: [{n, motivo}] (le mostra l'editor)
DANNEGGIATE = {}                                     # foto del progetto che non si decodificano: nome file -> data di modifica del file rovinato (VER-002)
def danneggiata():
    """perché una foto non si legge, nella lingua in uso (si traduce quando serve, non quando il programma parte)"""
    return lingua.t("motore.danneggiata")


GRIGIO_SEGNAPOSTO = (128, 128, 128)                  # miniatura al posto di una foto che non si legge
log = logging.getLogger("impaginatore.motore")
TITLE, INK = ("", "", ""), (58, 54, 51)
SERIF_FILE = SANS_FILE = None


def progetto_da_argv(argv=None):
    """cartella del progetto per gli script: --progetto <cartella> negli argomenti, poi ALBUM_PROGETTO, poi la cartella corrente"""
    argv = sys.argv if argv is None else argv
    for k, a in enumerate(argv):
        if a == "--progetto" and k + 1 < len(argv): return os.path.abspath(argv[k + 1])
    if os.environ.get("ALBUM_PROGETTO"): return os.path.abspath(os.environ["ALBUM_PROGETTO"])
    if os.path.exists("progetto.json"): return os.getcwd()
    raise SystemExit("Progetto non trovato: passa --progetto <cartella con progetto.json> o imposta ALBUM_PROGETTO")


def carica_progetto(cartella, sottofondo=False):
    """legge progetto.json, aggiorna l'elenco delle foto (metadati, miniature, volti) e prepara geometria, correzioni e testi.
    Restituisce il modulo stesso. Si può richiamare per passare a un altro progetto (un progetto alla volta per processo).
    sottofondo=True (UX-012): solo i metadati, che si leggono dall'intestazione dei file in millisecondi; miniature e volti
    che mancano li prepara chi apre il progetto (da_preparare, prepara_miniatura, _build_faces), mentre si lavora. Una foto
    nuova che si apre ma non si decodifica non resta fuori: diventa danneggiata quando si prova a farne la miniatura"""
    global PROJ, CFG, SRC, CACHE, THUMBS, CW, CH, PPI, B, G, MG, FOLD, TW, TH, M, F, IDX, ORIGINE, FACE_FIX, _ESP, WB, TXTCFG, TITLE, INK, SERIF_FILE, SANS_FILE
    Image.MAX_IMAGE_PIXELS = limite_pixel(); SCARTATE.clear(); DANNEGGIATE.clear()
    PROJ = os.path.abspath(cartella)
    CFG = _V.progetto(_leggi_json(os.path.join(PROJ, "progetto.json")))
    _togli_riservate(CFG)
    SRC = CFG["foto"]                                   # cartella con le foto scelte in alta risoluzione
    CACHE = os.path.join(PROJ, "_cache"); THUMBS = os.path.join(CACHE, "thumbs")
    os.makedirs(THUMBS, exist_ok=True)
    CW, CH, PPI, B, G, MG = _geometry()
    FOLD = CW / 2; TW, TH = CW - 2 * B, CH - 2 * B
    # ---- foto: metadati, miniature, volti
    mp, fp = os.path.join(CACHE, "meta.json"), os.path.join(CACHE, "faces.json")
    M = _cache_valida(mp, _V.meta, [])                  # cache rovinata o non valida: si ricostruisce dalle foto
    _src_fidate(M)
    _date_mancanti(M)
    new = _nuove(_cerca_foto(SRC), M)
    # foto aggiunte dopo, prese dalle cartelle complete (non nella selezione del cliente): vanno in coda, la numerazione non cambia
    new += _nuove(CFG.get("foto_extra", []), M + new)
    rotte = set() if sottofondo else set(_build_thumbs(new, segnaposto=False))  # una foto nuova che non si decodifica resta fuori e si riprova la volta dopo (VER-002)
    SCARTATE.extend(dict(n=m["n"], motivo=danneggiata()) for m in new if m["n"] in rotte)
    new = [m for m in new if m["n"] not in rotte]
    if new:
        first = not M
        M += sorted(new, key=lambda x: x["dt"]) if first else new
        _scrivi_json(mp, M)
    if not sottofondo: _build_thumbs(M)
    F = _cache_valida(fp, _V.volti, {})
    missing = [m for m in M if m["n"] not in F]
    if missing and not sottofondo: F.update(_build_faces(missing)); _scrivi_json(fp, F)
    IDX = {m["n"].rsplit(".", 1)[0]: k + 1 for k, m in enumerate(M)}      # nome file senza estensione -> numero foto
    # origine di ogni foto (cartella completa da cui viene): scritta da abbina.py, serve per le correzioni per capitolo
    ORIGINE = {}
    for op in (os.path.join(SRC, "origine.json"), os.path.join(CACHE, "origine.json")):
        o = _cache_valida(op, lambda d: _V.dizionario(d, "origine.json"), {})
        ORIGINE.update({k: v for k, v in o.items() if isinstance(v, str)})
    FACE_FIX = {k: tuple(v) for k, v in CFG.get("centri_volto", {}).items()}   # {"_DSC3885": [x, y]} centro a mano (0-1)
    _ESP = CFG.get("esposizione", {})
    WB = CFG.get("bilanciamento_bianco", {})     # {"_DSC1406": [r, g, b]} guadagni lineari
    TXTCFG = CFG.get("testo", {})
    TITLE = (TXTCFG.get("nome", ""), TXTCFG.get("sottotitolo", ""), TXTCFG.get("data", ""))
    INK = tuple(TXTCFG.get("colore", [58, 54, 51]))
    SERIF_FILE, SANS_FILE = _pfont.serif_predefinito(), _pfont.sans_predefinito()      # Didot e Avenir Next sul Mac
    return sys.modules[__name__]


def _togli_riservate(cfg):
    """percorsi di progetto.json in cartelle riservate (percorsi.riservata: nascoste della casa, dati dei programmi, sistema):
    non si usano mai (VER-004). Al loro posto quelli del progetto: Foto, nessuna foto aggiunta da lì, PSD"""
    if _percorsi.riservata(cfg.get("foto")): cfg["foto"] = os.path.join(PROJ, "Foto"); log.warning("cartella delle foto in una cartella riservata: uso Foto del progetto")
    if "foto_extra" in cfg: cfg["foto_extra"] = [p for p in cfg["foto_extra"] if not _percorsi.riservata(p)]
    if _percorsi.riservata(cfg.get("uscita_psd")): cfg["uscita_psd"] = os.path.join(PROJ, "PSD")


def luoghi_foto():
    """cartelle da cui il progetto legge le foto: la sua cartella, quella delle foto e quella che la contiene (le altre
    cartelle del cliente), quelle delle foto aggiunte (foto_extra). Vengono solo da progetto.json, mai dall'elenco delle
    foto in _cache/meta.json: un progetto ricevuto non allarga così le cartelle che si leggono (VER-004). Le troppo ampie
    (la casa, la radice del disco) restano fuori"""
    foto = str(CFG.get("foto") or "").rstrip("/\\")
    out = [PROJ, foto, os.path.dirname(foto) if foto else ""] + [os.path.dirname(str(p)) for p in CFG.get("foto_extra", [])]
    return [p for p in dict.fromkeys(out) if p and not _percorsi.troppo_ampia(p)]


def fidata(s, luoghi):
    """il file s si legge come foto del progetto? Deve avere l'estensione di una foto, stare dentro uno dei luoghi
    (luoghi_foto) e non in una cartella riservata, nemmeno passando da un collegamento (VER-004)"""
    n = os.path.normcase(os.path.normpath(s or "."))
    return (os.path.isabs(n) and n.lower().endswith(ESTENSIONI + (".heic", ".heif"))
            and any(n == r or n.startswith(r.rstrip(os.sep) + os.sep) for r in (os.path.normcase(os.path.abspath(p)) for p in luoghi))
            and (_percorsi.dentro(s, PROJ) or not _percorsi.riservata(s)))


def _src_fidate(meta):
    """una foto dell'elenco che non è fidata (fidata) ha src "": risulta mancante e si ricollega con «Ricollega foto», che
    ricorda la cartella scelta. Così nessuna miniatura né esportazione legge file fuori dal progetto (VER-004)"""
    luoghi = luoghi_foto()
    for m in meta:
        if not m.get("src") or fidata(m["src"], luoghi): continue
        log.warning("una foto dell'elenco sta fuori dalle cartelle del progetto: la considero mancante"); log.debug("src non usato: %s", m["src"])
        m["src"] = ""


def _leggi_json(p):
    return _formato.leggi_json(p)


def _scrivi_json(p, dati):
    _formato.scrivi_json(p, dati)                       # atomico: un'interruzione non lascia un JSON troncato


def _cache_valida(p, controlla, vuota):
    """contenuto di un file di cache controllato; se manca, è rovinato o non è valido si riparte da `vuota` (la cache si
    ricostruisce dalle foto: niente blocca l'apertura del progetto)"""
    if not os.path.exists(p): return vuota
    try: return controlla(_leggi_json(p))
    except (OSError, ValueError, RecursionError) as e:
        print(f"{os.path.basename(p)} non valido, lo ricostruisco: {e}", flush=True)
        return vuota


# ---------------- geometria ----------------
def _geometry():
    wcm, hcm = CFG["formato_cm"]; ppi_target = CFG.get("ppi", 300); bleed_mm = CFG.get("abbondanza_mm", 0)
    wcm_t, hcm_t = wcm + 2 * bleed_mm / 10, hcm + 2 * bleed_mm / 10
    if CFG.get("dimensioni_esatte", True):
        # pixel con lo stesso rapporto esatto del formato, ppi aggiustati di poco: Photoshop mostra la misura esatta in cm
        r = Fraction(wcm_t).limit_denominator(1000) / Fraction(hcm_t).limit_denominator(1000)
        a, b = r.numerator, r.denominator
        n = max(1, round(wcm_t / 2.54 * ppi_target / a))
        W, H = a * n, b * n
        ppi = W / (wcm_t / 2.54)
    else:
        W, H = round(wcm_t / 2.54 * ppi_target), round(hcm_t / 2.54 * ppi_target); ppi = ppi_target
    mm = lambda v: round(v / 25.4 * ppi)
    return W, H, ppi, mm(bleed_mm), mm(CFG.get("spazio_mm", 2.5)), mm(CFG.get("margine_mm", 10))
NC, NR = 12, 8

# ---------------- foto: metadati, miniature, volti ----------------
MAX_MPIXEL = 160                 # milioni di pixel al massimo per foto (IMPAGINATORE_MAX_MPIXEL): oltre, la foto si scarta con un avviso
ESTENSIONI = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")
NON_SUPPORTATE = (".heic", ".heif", ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".psd", ".gif", ".bmp")      # si riconoscono ma non si aprono: si avvisa
_HEIF = []


def limite_pixel():
    """pixel massimi per foto (vale anche come Image.MAX_IMAGE_PIXELS): IMPAGINATORE_MAX_MPIXEL milioni, predefinito MAX_MPIXEL"""
    try: mp = float(os.environ.get("IMPAGINATORE_MAX_MPIXEL") or MAX_MPIXEL)
    except ValueError: mp = MAX_MPIXEL
    return int(max(mp, 0.01) * 1_000_000)


def estensioni():
    """estensioni delle foto che il programma apre (HEIC/HEIF solo con il pacchetto facoltativo pillow-heif)"""
    if not _HEIF:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener(); _HEIF.append((".heic", ".heif"))
        except ImportError: _HEIF.append(())
    return ESTENSIONI + _HEIF[0]


def apri_foto(f):
    """apre la foto (senza decodificarla) controllando il limite di pixel: ValueError con un messaggio chiaro se è troppo grande"""
    lim = Image.MAX_IMAGE_PIXELS = limite_pixel(); estensioni()
    try: im = Image.open(f)
    except Image.DecompressionBombError: im = None
    if im is None or im.width * im.height > lim:
        if im is not None: im.close()
        raise ValueError(lingua.t("motore.troppo_grande", nome=os.path.basename(f), milioni=lingua.num(lim / 1e6)))
    return im


def in_srgb(im):
    """la foto in RGB a 8 bit nello spazio sRGB: profilo colore incorporato convertito (CMYK, Adobe RGB...), trasparenza su bianco, 16 bit ridotti"""
    icc = im.info.get("icc_profile")
    if im.mode.startswith("I"): im = im.point(lambda v: v * (1 / 256)).convert("L") if im.mode == "I" else im.convert("I").point(lambda v: v * (1 / 256)).convert("L")
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA"); fondo = Image.new("RGBA", im.size, (255, 255, 255, 255)); fondo.alpha_composite(im); im = fondo.convert("RGB")
    if icc and im.mode in ("RGB", "CMYK", "L"):
        from PIL import ImageCms
        try: return ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"), outputMode="RGB")
        except (ImageCms.PyCMSError, OSError) as e: log.warning("profilo colore non convertito (%s): colori come sono", e)
    return im.convert("RGB")


def _data_file(f):
    """data di modifica del file, nella forma delle date EXIF: per le foto senza data di scatto"""
    return time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(os.path.getmtime(f))) + ".00"


def _date_mancanti(meta):
    """foto senza data di scatto lette con le versioni fino alla 2.0 ("None.00"): la data del file (l'ordine resta quello salvato)"""
    for m in meta:
        if str(m.get("dt", "")).startswith("None") and os.path.exists(m.get("src", "")): m["dt"], m["senza_data"] = _data_file(m["src"]), True


def _cerca_foto(cartella):
    """foto della cartella (formati supportati), in ordine di nome; quelle in formati che non si aprono vanno in SCARTATE"""
    try: nomi = sorted(os.listdir(cartella))
    except OSError: return []
    out = []
    for n in nomi:
        e = os.path.splitext(n)[1].lower()
        if n.startswith(".") or not os.path.isfile(os.path.join(cartella, n)): continue
        if e in estensioni(): out.append(os.path.join(cartella, n))
        elif e in NON_SUPPORTATE: SCARTATE.append(dict(n=n, motivo=lingua.t("motore.formato_non_supportato", formato=e[1:].upper())))
    return out


def _nuove(files, meta):
    """metadati delle foto non ancora in meta, una sola per nome senza estensione (è la chiave delle foto in spec.py).
    Quelle che non si aprono (file rovinato, troppo grande, doppione) vanno in SCARTATE con il motivo"""
    noti = {m["n"] for m in meta}; radici = {m["n"].rsplit(".", 1)[0] for m in meta}; out = []
    for f in files:
        n = os.path.basename(f); r = n.rsplit(".", 1)[0]
        if n in noti: continue
        if r in radici: SCARTATE.append(dict(n=n, motivo=lingua.t("motore.nome_doppio", nome=r))); continue
        try: out.append(_meta_one(f))
        except ERRORI_FOTO as e:
            SCARTATE.append(dict(n=n, motivo=str(e) if isinstance(e, ValueError) else lingua.t("motore.non_si_apre")))
            log.warning("una foto non si apre (%s)", type(e).__name__); log.debug("foto scartata %s: %s", n, e); continue          # nomi solo a DEBUG (VER-013)
        noti.add(n); radici.add(r)
    return out


def _meta_one(f):
    with apri_foto(f) as im:
        ex = im.getexif(); sub = ex.get_ifd(0x8769); w, h = im.size
        if ex.get(274) in (5, 6, 7, 8): w, h = h, w                       # ruotata dall'EXIF: misure come la si vede (come la miniatura)
    dt = sub.get(36867) or ex.get(306)
    m = dict(n=os.path.basename(f), dt=f"{dt}.{sub.get(37521, '00')}" if dt else _data_file(f), w=w, h=h, ar=round(w / h, 3), src=os.path.abspath(f))
    if not dt: m["senza_data"] = True                                  # data presa dal file: l'editor lo dice
    return m
# errori che Pillow solleva per un file rovinato, troncato o che non è quello che dice di essere
ERRORI_FOTO = (OSError, SyntaxError, ValueError, EOFError, struct.error, IndexError, TypeError, KeyError, ZeroDivisionError, Image.DecompressionBombError)


def _build_thumbs(meta, segnaposto=True):
    """miniature che mancano (1200 px, JPEG). Restituisce i nomi delle foto che non si leggono (VER-002): mai un'eccezione
    che blocca l'apertura del progetto. Con segnaposto=True (foto già del progetto) al loro posto va un riquadro grigio
    con data 0, così la foto resta dov'è e, appena il file torna buono (o si ricollega), l'editor la vede cambiata e la rifà;
    quelle che esistono ma non si decodificano vanno in DANNEGGIATE e SCARTATE"""
    rotte = []
    for m in meta:
        e = prepara_miniatura(m)
        if e is None: continue
        rotte.append(m["n"])
        if segnaposto: segna_danneggiata(m)
    return rotte


def prepara_miniatura(m, cartella=None):
    """fa la miniatura della foto m se manca (1200 px, JPEG). None se c'è, altrimenti l'errore della foto che non si legge.
    Il file si scrive accanto e poi si rinomina: chi legge le miniature mentre si preparano (UX-012) non ne trova mai una a metà.
    cartella: quella delle miniature (di serie THUMBS; in sottofondo quella del progetto di quando è partita la preparazione)"""
    cartella = cartella or THUMBS; p = os.path.join(cartella, m["n"])
    if os.path.exists(p): return None
    try:
        with apri_foto(m["src"]) as im0:
            im0.draft("RGB", (1200, 1200)); im = in_srgb(ImageOps.exif_transpose(im0))
        im.thumbnail((1200, 1200)); t = os.path.join(cartella, f".{m['n']}.{os.urandom(4).hex()}.tmp")
        try: im.save(t, "JPEG", quality=85); os.replace(t, p)          # sempre JPEG (anche da PNG o TIFF): si servono come image/jpeg
        finally:
            with contextlib.suppress(FileNotFoundError): os.remove(t)
    except ERRORI_FOTO as e:
        log.warning("una foto non si legge (%s)", type(e).__name__); log.debug("foto non letta %s: %s", m["n"], e)
        return e
    return None


def segna_danneggiata(m):
    """la foto m (già del progetto) non si legge: riquadro grigio con data 0 al posto della miniatura, così resta dov'è e,
    appena il file torna buono (o si ricollega), l'editor la vede cambiata e la rifà; se il file c'è va tra le danneggiate"""
    p = os.path.join(THUMBS, m["n"])
    riquadro_grigio(m).save(p, "JPEG", quality=85); os.utime(p, (0, 0))
    if os.path.exists(m.get("src") or ""):                                 # c'è ma non si legge (se manca, l'editor la mostra tra le mancanti)
        DANNEGGIATE[m["n"]] = os.path.getmtime(m["src"]); SCARTATE.append(dict(n=m["n"], motivo=danneggiata()))


def da_preparare():
    """(foto senza miniatura in ordine di scatto, foto senza volti): il lavoro che resta dopo un'apertura in sottofondo"""
    mini = sorted((m for m in M if not os.path.exists(os.path.join(THUMBS, m["n"]))), key=lambda m: m["dt"])
    return mini, [m for m in M if m["n"] not in F]
def _build_faces(meta):
    import cv2
    d = cv2.data.haarcascades
    fr = cv2.CascadeClassifier(d + "haarcascade_frontalface_default.xml"); pr = cv2.CascadeClassifier(d + "haarcascade_profileface.xml")
    out = {}
    for m in meta:
        im = cv2.imread(os.path.join(THUMBS, m["n"]))
        if im is None: out[m["n"]] = []; continue                         # miniatura che non si legge: nessun volto (VER-002)
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); H, W = g.shape; mn = int(min(W, H) * 0.04)
        bx = list(fr.detectMultiScale(g, 1.1, 6, minSize=(mn, mn))) + list(pr.detectMultiScale(g, 1.1, 6, minSize=(mn, mn))) + \
             [(W - x - w, y, w, h) for x, y, w, h in pr.detectMultiScale(cv2.flip(g, 1), 1.1, 6, minSize=(mn, mn))]
        out[m["n"]] = [[float(x / W), float(y / H), float((x + w) / W), float((y + h) / H)] for x, y, w, h in bx]
    return out

def name(i): return M[i]["n"].rsplit(".", 1)[0]

# ---------------- ritaglio ----------------
def _faces_center(i):
    if name(i) in FACE_FIX: return FACE_FIX[name(i)]
    fs = F.get(M[i]["n"], [])
    if not fs: return None
    A = [(f[2] - f[0]) * (f[3] - f[1]) for f in fs]; big = max(A); fs = [f for f, a in zip(fs, A) if a > big * 0.15]
    return (min(f[0] for f in fs) + max(f[2] for f in fs)) / 2, (min(f[1] for f in fs) + max(f[3] for f in fs)) / 2
def crop(i, cw, ch, z=1.0):
    """finestra di ritaglio normalizzata (l,t,r,b) perché la foto i riempia cw x ch; tiene i volti; z>1 stringe sui volti"""
    ar = M[i]["ar"]; ca = cw / ch; fc = _faces_center(i); fx, fy = fc if fc else (0.5, 0.42)
    if ar > ca: fw = ca / ar; l = min(max(fx - fw / 2, 0), 1 - fw); l, t, r, b = l, 0, l + fw, 1
    else: fh = ar / ca; t = min(max(fy - fh * 0.42, 0), 1 - fh); l, t, r, b = 0, t, 1, t + fh
    if z > 1:
        cx, cy = fc if fc else ((l + r) / 2, (t + b) / 2); w, h = (r - l) / z, (b - t) / z
        nl = min(max(cx - w / 2, l), r - w); nt = min(max(cy - h * 0.42, t), b - h); l, t, r, b = nl, nt, nl + w, nt + h
    return l, t, r, b

# ---------------- griglia e moduli ----------------
def _p(n): return IDX[n] if isinstance(n, str) else n
def P(n, c, r, w, h, bw=False, z=1.0): return dict(k="p", i=_p(n) - 1, c=c, r=r, w=w, h=h, bw=bw, z=z)
def FULL(n, bw=False, z=1.0): return dict(k="full", i=_p(n) - 1, bw=bw, z=z)
def TXT(kind, c, r, w, h): return dict(k="t", kind=kind, c=c, r=r, w=w, h=h)
def _frame(side, mode):
    if mode == "I": return ((0, FOLD - G / 2) if side == "L" else (FOLD + G / 2, CW)), (0, CH)
    return ((B + MG, FOLD - MG) if side == "L" else (FOLD + MG, B + TW - MG)), (B + MG, B + TH - MG)
def _place(side, mode, it):
    if it["k"] == "full":
        x0, x1 = (0, FOLD - G / 2) if side == "L" else (FOLD + G / 2, CW); return dict(it, x=round(x0), y=0, W=round(x1) - round(x0), H=CH, side=side)
    (x0, x1), (y0, y1) = _frame(side, mode); cw = (x1 - x0 - (NC - 1) * G) / NC; rh = (y1 - y0 - (NR - 1) * G) / NR
    # linee della griglia su pixel interi prima di tutto: così ogni spazio è esattamente G
    colx = lambda c: round(x0 + c * (cw + G)); rowy = lambda r: round(y0 + r * (rh + G))
    xa, ya = colx(it["c"]), rowy(it["r"])
    xb = round(x1) if it["c"] + it["w"] == NC else colx(it["c"] + it["w"]) - G
    yb = round(y1) if it["r"] + it["h"] == NR else rowy(it["r"] + it["h"]) - G
    return dict(it, x=xa, y=ya, W=xb - xa, H=yb - ya, side=side)
def layout(spread):
    out = []
    for side, (mode, items) in zip("LR", spread): out += [_place(side, mode, i) for i in items]
    return out
def zcrop(it): return crop(it["i"], it["W"], it["H"], it.get("z", 1.0))
def _flat(items): return [x for it in items for x in (it if isinstance(it, list) else [it])]
def I(*items): return ("I", _flat(items))      # pagina immersiva
def W(*items): return ("W", _flat(items))      # pagina bianca con margine
# moduli di pagina (n = nome file "_DSC1234" o numero foto)
def DUO(a, b, bw=(False, False), z=(1, 1)): return [P(a, 0, 0, 6, 8, bw[0], z[0]), P(b, 6, 0, 6, 8, bw[1], z[1])]          # 2 verticali
def VLL(v, a, b, mirror=False, bw=False):                                                                                   # 1 verticale + 2 orizzontali
    return [P(v, 6, 0, 6, 8, bw), P(a, 0, 0, 6, 4, bw), P(b, 0, 4, 6, 4, bw)] if mirror else [P(v, 0, 0, 6, 8, bw), P(a, 6, 0, 6, 4, bw), P(b, 6, 4, 6, 4, bw)]
def V4(v, a, b, c, d, mirror=False, z=1.0):                                                                                 # 1 verticale grande + 4 piccole verticali
    o, vx = (0, 6) if mirror else (6, 0)
    return [P(v, vx, 0, 6, 8, z=z), P(a, o, 0, 3, 4), P(b, o + 3, 0, 3, 4), P(c, o, 4, 3, 4), P(d, o + 3, 4, 3, 4)]
def G4(a, b, c, d, bw=False): return [P(a, 0, 0, 6, 4, bw), P(b, 6, 0, 6, 4, bw), P(c, 0, 4, 6, 4, bw), P(d, 6, 4, 6, 4, bw)]  # 4 orizzontali
def CV(v, bw=False, z=1.0): return [P(v, 3, 0, 6, 8, bw, z)]          # 1 verticale centrata (su pagina bianca)
def SV(v, bw=False, z=1.0): return [P(v, 4, 1, 4, 6, bw, z)]          # 1 verticale piccola centrata: un sussurro
def PP(l, bw=False): return [P(l, 1, 1, 10, 6, bw)]                   # 1 orizzontale con passe-partout bianco
def COL2(a, b, bw=False): return [P(a, 3, 0, 6, 4, bw), P(b, 3, 4, 6, 4, bw)]
def BAND2(a, b, bw=False): return [P(a, 0, 2, 6, 4, bw), P(b, 6, 2, 6, 4, bw)]
def STRIP3(a, b, c, bw=False): return [P(a, 0, 1, 4, 6, bw), P(b, 4, 1, 4, 6, bw), P(c, 8, 1, 4, 6, bw)]

# ---------------- correzioni di luminosità e colore ----------------
def ev_for(i):
    """EV totale della foto i: globale + base del capitolo (cartella di origine) + correzione della singola foto"""
    n = name(i); ev = _ESP.get("globale", 0.0)
    orig = ORIGINE.get(M[i]["n"]) or os.path.dirname(M[i]["src"])
    for folder, v in _ESP.get("per_cartella", {}).items():
        if os.path.normpath(orig) == os.path.normpath(folder): ev += v
    return round(ev + _ESP.get("per_foto", {}).get(n, 0.0), 2)
def apply_ev(im, ev, gains=None):
    """esposizione come il livello Esposizione di Photoshop (gamma 2.2, nessuna spalla: identica nel PSD); poi i guadagni del bilanciamento bianco in luce lineare"""
    import numpy as np
    if abs(ev) < 1e-3 and not gains: return im
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    if abs(ev) >= 1e-3: a = np.clip(a ** 2.2 * (2 ** ev), 0, 1) ** (1 / 2.2)
    if gains:
        lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4) * np.array(gains, dtype=np.float32)
        lin = np.clip(lin, 0, 1)
        a = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8))

# ---------------- testi ----------------
def _font(path_key, default, size, index=0):
    p = TXTCFG.get(path_key) or default
    try: return ImageFont.truetype(p, size, index=index)
    except Exception: return _pfont.pil_ripiego(size)          # Helvetica sul Mac, Arial su Windows, DejaVu su Linux
def _spaced(d, xy, text, font, track, center=None):
    w = sum(font.getlength(ch) for ch in text) + track * (len(text) - 1); x, y = xy
    if center is not None: x = center - w / 2
    for ch in text: d.text((x, y), ch, font=font, fill=INK); x += font.getlength(ch) + track
def _text(it, K):
    Wd, Hd = max(1, round(it["W"] * K)), max(1, round(it["H"] * K)); im = Image.new("RGBA", (Wd, Hd), (255, 255, 255, 0)); d = ImageDraw.Draw(im)
    small = _font("file_font_testo", SANS_FILE, round(62 * K), TXTCFG.get("indice_font_testo", 7))
    if it["kind"] == "title":
        big = _font("file_font_titolo", SERIF_FILE, round(380 * K)); cx = Wd / 2; y = Hd / 2 - round(260 * K)
        d.text((cx - big.getlength(TITLE[0]) / 2, y), TITLE[0], font=big, fill=INK); y += round(520 * K)
        _spaced(d, (0, y), TITLE[1], small, round(22 * K), cx); y += round(110 * K); _spaced(d, (0, y), TITLE[2], small, round(22 * K), cx)
    else:
        mid = _font("file_font_titolo", SERIF_FILE, round(170 * K)); y = Hd - round(400 * K)
        d.text((0, y), TITLE[0], font=mid, fill=INK); y += round(230 * K)
        _spaced(d, (round(6 * K), y), TITLE[1], small, round(14 * K)); y += round(90 * K); _spaced(d, (round(6 * K), y), TITLE[2], small, round(14 * K))
    return im

# ---------------- rendering anteprime ----------------
def leggi_rgb(p):
    """immagine p in RGB, con il file già chiuso (VER-015)"""
    with Image.open(p) as im0: im = im0.convert("RGB")
    return im


def riquadro_grigio(m):
    """riquadro grigio con le proporzioni della foto: al posto della miniatura che non c'è ancora (preparazione in sottofondo)"""
    w, h = m.get("w") or 3, m.get("h") or 2; f = 300 / max(w, h)
    return Image.new("RGB", (max(1, round(w * f)), max(1, round(h * f))), GRIGIO_SEGNAPOSTO)


def foto_rgb(i, originale=False, serve=None):
    """la foto i in RGB. Di serie la miniatura (anteprime a schermo; un riquadro grigio se non è ancora pronta). Con
    originale=True il file originale (stampa, UX-011): letto con il limite di pixel (apri_foto), decodificato alla misura
    più piccola che basta a `serve` (larghezza, altezza in pixel della foto intera; i JPEG si riducono già in decodifica),
    raddrizzato dall'EXIF e portato in sRGB come la miniatura. Un originale che manca o è danneggiato (VER-002): ValueError"""
    m = M[i]
    if not originale:
        p = os.path.join(THUMBS, m["n"])
        return leggi_rgb(p) if os.path.exists(p) else riquadro_grigio(m)
    src = m.get("src") or ""
    if m["n"] in DANNEGGIATE: raise ValueError(f"{m['n']}: {danneggiata()}")
    if not os.path.isfile(src): raise ValueError(lingua.t("motore.originale_non_trovato", nome=m["n"]))
    with apri_foto(src) as im0:
        if serve:
            w, h = (serve[1], serve[0]) if im0.getexif().get(274) in (5, 6, 7, 8) else serve      # la decodifica lavora sul file com'è, prima della rotazione
            im0.draft("RGB", (max(1, math.ceil(w)), max(1, math.ceil(h))))
        im = in_srgb(ImageOps.exif_transpose(im0))
    return im


def margine_filtro(scala):
    """pixel attorno al riquadro che il ricampionamento (LANCZOS, BICUBIC) legge ancora: ritagliando con questo margine il
    risultato è lo stesso di quello fatto sulla foto intera"""
    return math.ceil(3 * max(1.0, scala)) + 2


def _photo(it, K, corrected=False, originale=False):
    l, t, r, b = zcrop(it); size = (max(1, round(it["W"] * K)), max(1, round(it["H"] * K)))
    if originale:          # stampa (UX-011): dall'originale, ricampionato una volta sola; le correzioni (pixel per pixel) solo sulla parte che serve
        im = foto_rgb(it["i"], True, (size[0] / max(r - l, 1e-6), size[1] / max(b - t, 1e-6)))
        box = (l * im.width, t * im.height, r * im.width, b * im.height); mg = margine_filtro((box[2] - box[0]) / size[0])
        x0, y0 = max(0, math.floor(box[0]) - mg), max(0, math.floor(box[1]) - mg)
        im = im.crop((x0, y0, min(im.width, math.ceil(box[2]) + mg), min(im.height, math.ceil(box[3]) + mg)))
        if corrected: im = apply_ev(im, ev_for(it["i"]), WB.get(name(it["i"])))
        out = im.resize(size, Image.LANCZOS, box=(box[0] - x0, box[1] - y0, box[2] - x0, box[3] - y0))
    else:
        im = foto_rgb(it["i"])
        if corrected: im = apply_ev(im, ev_for(it["i"]), WB.get(name(it["i"])))
        out = im.resize(size, Image.LANCZOS, box=(l * im.width, t * im.height, r * im.width, b * im.height))
    return ImageOps.grayscale(out).convert("RGB") if it.get("bw") else out
def render(spread, K, corrected=True, originale=False):
    """lo spread disegnato alla scala K (1 = pixel del documento, con l'abbondanza). originale=True legge le foto dagli
    originali (stampa); altrimenti dalle miniature (anteprime)"""
    S = Image.new("RGB", (round(CW * K), round(CH * K)), "white")
    for it in layout(spread):
        pos = (round(it["x"] * K), round(it["y"] * K))
        if it["k"] == "t": t = _text(it, K); S.paste(t, pos, t)
        else: S.paste(_photo(it, K, corrected, originale=originale), pos)
    return S

def load_spec(modname="spec"):
    """SPREADS del progetto caricato, da album.json (un progetto 1.x con spec.py si converte, senza eseguirlo); modname
    resta per compatibilità con gli script 1.x e non si usa"""
    return _formato.carica(PROJ)
