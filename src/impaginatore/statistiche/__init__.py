"""Statistiche d'uso facoltative (T-204): spente di serie, si accendono solo con il consenso esplicito dell'utente.

Documento: docs/architettura/STATISTICHE.md (eventi e campi, registro, invio, cosa deve offrire il server).

Principi:
- consenso: senza la scelta «sì» salvata in consenso.json (con la versione del testo del consenso in uso) non si scrive
  niente e non parte niente. Con una licenza beta la schermata Album chiede la scelta al primo avvio (chiedere());
- mai contenuti: ogni evento passa da schema.pulisci(), che tiene solo nomi e campi dello schema, con numeri, vero/falso
  e parole di elenchi chiusi. Non c'è un campo di testo libero: nomi di file, cartelle, album o clienti, percorsi, testi
  dell'album, EXIF, volti non hanno dove stare. Gli errori portano tipo e punto del codice, mai il messaggio;
- trasparenza: tutto quello che potrebbe partire si scrive prima nel registro eventi.jsonl, che l'utente legge così
  com'è («Cosa condivido»), esporta a mano («Esporta le statistiche…») e cancella quando vuole;
- mai d'intralcio: le funzioni pubbliche non sollevano eccezioni (@sicura) e con le statistiche spente costano un
  os.stat ogni tanto; le operazioni dell'editor si contano in memoria e si scrivono a gruppi (svuota(), ogni OGNI secondi).

File, in <dati dell'utente>/statistiche/ (cartella 0700, file 0600; nessuno esce dal computer se non con l'invio o
l'esportazione):
    consenso.json       {"formato": 1, "scelta": "si"|"no", "testo": TESTO_CONSENSO, "quando": "…"}
    installazione.json  {"formato": 1, "id": "<32 cifre esadecimali casuali>"}: nasce al primo «sì», si azzera a richiesta
    eventi.jsonl        il registro: un evento per riga; oltre MAX_FILE passa a eventi.1.jsonl (ne restano due)
    traguardi.json      quali «prime volte» (primo album, primo spread…) sono già state annotate
    coda.jsonl          eventi da mandare, solo se c'è una destinazione (invio.INDIRIZZO; oggi no)
Importare il modulo non legge né scrive niente.
"""
import atexit
import datetime as dt
import errno as _errno
import functools
import json
import logging
import os
import platform
import re
import secrets
import sys
import threading
import time

from .. import __version__, lingua, licenze
from ..piattaforma import cartelle, sistema
from . import invio, schema

log = logging.getLogger("impaginatore.statistiche")

TESTO_CONSENSO = 1                   # versione del testo del consenso (i dati restano sul computer, li esporta l'utente): se cambia in modo sostanziale si alza e la domanda si rifà
TESTO_CONSENSO_INVIO = 2             # il testo che dice che i dati partono da soli verso il server: con un INDIRIZZO, chi aveva detto sì al testo 1 rivede la domanda
SOLO_BETA = True                     # l'interruttore si offre solo con una licenza beta (o se c'è già qualcosa da vedere): decisione aperta, DA-DECIDERE.md
CONSENSO, INSTALLAZIONE, EVENTI, EVENTI_VECCHI, TRAGUARDI = "consenso.json", "installazione.json", "eventi.jsonl", "eventi.1.jsonl", "traguardi.json"
MAX_FILE = 4 * 2 ** 20               # byte di eventi.jsonl prima della rotazione: al massimo 8 MB in tutto
MAX_CODA = 2 * 2 ** 20               # oltre, gli eventi restano nel registro ma non si mettono in coda
OGNI = 30                            # secondi tra due scritture dei conteggi delle operazioni
GIRO_INVIO = 900                     # secondi tra due giri d'invio (solo con una destinazione)
RIGHE_MOSTRATE = 500                 # righe del registro che «Cosa condivido» mostra (le ultime)
SESSIONE = secrets.token_hex(6)      # questo processo: lega gli eventi di una stessa apertura del programma o di un album

_LOCK = threading.RLock()
_STATO = {"processo": "altro", "inizio": time.monotonic(), "consenso": (None, None), "id": (None, None), "filo": None}
_ALBUM = {"inizio": None, "spread": 0, "vuoto": False, "primo": False}
_OPS = {"cartella": None, "conti": {}}


def sicura(fn):
    """le statistiche non rompono mai niente: un errore qui si annota (solo il tipo) e la funzione restituisce None"""
    @functools.wraps(fn)
    def avvolta(*a, **k):
        try: return fn(*a, **k)
        except Exception as e:
            log.debug("statistiche: %s in %s", type(e).__name__, fn.__name__); return None
    return avvolta


# ---------------------------------------------------------------- file
def cartella():
    """cartella delle statistiche, dentro i dati dell'utente (non la crea)"""
    return os.path.join(cartelle.dati_utente(), "statistiche")


def _percorso(nome): return os.path.join(cartella(), nome)


def _prepara():
    d = cartella(); os.makedirs(d, mode=0o700, exist_ok=True)
    try: os.chmod(d, 0o700)
    except OSError as e: log.warning("permessi della cartella delle statistiche non impostati: %s", e.strerror)
    return d


def _scrivi_json(nome, dati):
    """file JSON riservato (0600), scritto in modo atomico"""
    p = os.path.join(_prepara(), nome); tmp = f"{p}.{secrets.token_hex(6)}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as f: f.write(json.dumps(dati, sort_keys=True).encode("utf-8"))
    os.replace(tmp, p)


def _leggi_json(nome):
    """contenuto di un file JSON delle statistiche, {} se manca o non si legge"""
    try:
        with open(_percorso(nome), encoding="utf-8") as f: d = json.load(f)
    except (OSError, ValueError): return {}
    return d if isinstance(d, dict) else {}


def _firma(nome):
    try: st = os.stat(_percorso(nome)); return (_percorso(nome), st.st_ino, st.st_mtime_ns, st.st_size)
    except OSError: return (_percorso(nome), None)


def _aggiungi(path, dati):
    """aggiunge byte in coda a un file riservato (0600): una sola write, così due processi non mescolano le righe"""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0), 0o600)
    try: os.write(fd, dati)
    finally: os.close(fd)


def _dimensione(path):
    try: return os.path.getsize(path)
    except OSError: return 0


# ---------------------------------------------------------------- consenso e identificativo
def testo_consenso():
    """versione del testo del consenso che vale oggi: senza server i dati restano sul computer (TESTO_CONSENSO), con il
    server partono da soli (TESTO_CONSENSO_INVIO), e la domanda va rifatta"""
    return TESTO_CONSENSO_INVIO if invio.attivo() else TESTO_CONSENSO


def scelta():
    """"si", "no" o None (mai chiesto, o chiesto con un testo del consenso diverso da quello di oggi). Il file si rilegge
    solo quando cambia: la scelta fatta nella schermata vale subito anche negli editor aperti"""
    f = (_firma(CONSENSO), testo_consenso())
    with _LOCK: memo = _STATO["consenso"]
    if memo[0] == f: return memo[1]
    d = _leggi_json(CONSENSO)
    v = d.get("scelta") if d.get("scelta") in ("si", "no") and d.get("testo") == f[1] else None
    with _LOCK: _STATO["consenso"] = (f, v)
    return v


def attive():
    """l'utente ha detto sì?"""
    return scelta() == "si"


def identificativo():
    """identificativo casuale di questa installazione (nato qui, non dice niente del computer), o None se non c'è"""
    f = _firma(INSTALLAZIONE)
    with _LOCK: memo = _STATO["id"]
    if memo[0] == f: return memo[1]
    v = _leggi_json(INSTALLAZIONE).get("id")
    v = v if isinstance(v, str) and schema.RE_ID.fullmatch(v) else None
    with _LOCK: _STATO["id"] = (f, v)
    return v


def azzera_identificativo():
    """un identificativo nuovo: gli eventi da qui in poi non si legano più a quelli di prima (che restano nel registro
    finché l'utente non li cancella)"""
    _scrivi_json(INSTALLAZIONE, {"formato": 1, "id": secrets.token_hex(16)})
    return identificativo()


def imposta(si):
    """salva la scelta dell'utente («Sì, condividi» / «No, grazie», o l'interruttore). Con il sì nasce l'identificativo
    (se non c'è) e si annotano il consenso e l'ambiente; con il no non si raccoglie più niente (il registro resta, finché
    l'utente non lo cancella). ValueError se si non è vero o falso"""
    if not isinstance(si, bool): raise ValueError(lingua.t("statistiche.scelta_vero_falso"))
    _scrivi_json(CONSENSO, {"formato": 1, "scelta": "si" if si else "no", "testo": testo_consenso(), "quando": _istante()})
    log.info("statistiche d'uso: %s", "accese" if si else "spente")
    if si:
        if not identificativo(): azzera_identificativo()
        evento("consenso", scelta="si", testo=testo_consenso()); avvio()
    return stato()


# ---------------------------------------------------------------- scrittura
def _istante(t=None):
    return dt.datetime.fromtimestamp(time.time() if t is None else t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def processo(nome):
    """come si chiama questo processo negli eventi: «home» (schermata Album) o «editor»"""
    _STATO.update(processo=nome if nome in schema.PROCESSI else "altro", inizio=time.monotonic(), chiuso=False)


def _busta(nome):
    """campi di ogni evento: versione dello schema, istante (UTC, al secondo), identificativo dell'installazione, sessione,
    processo, versione del programma e, solo con una licenza beta, il suo numero di serie (il titolare sa così quale tester
    ha mandato i dati: il testo del consenso lo dice)"""
    b = {"v": schema.VERSIONE_SCHEMA, "t": _istante(), "id": identificativo() or azzera_identificativo(), "sessione": SESSIONE, "proc": _STATO["processo"],
         "ver": __version__, "ev": nome}
    st = licenze.stato()
    if st["beta"]: b["serie"] = st["seriale"]
    return b


def _scrivi(righe):
    """righe (dict) nel registro, e nella coda se c'è una destinazione. Il registro passa a eventi.1.jsonl oltre MAX_FILE"""
    dati = "".join(json.dumps(r, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n" for r in righe).encode("ascii")
    with _LOCK:
        d = _prepara(); f = os.path.join(d, EVENTI)
        dim = _dimensione(f)
        if dim and dim + len(dati) > MAX_FILE: os.replace(f, os.path.join(d, EVENTI_VECCHI))
        _aggiungi(f, dati)
        if invio.attivo() and _dimensione(os.path.join(d, invio.CODA)) < MAX_CODA: _aggiungi(os.path.join(d, invio.CODA), dati)


def _riga(nome, campi):
    riga = _busta(nome); riga.update(schema.pulisci(nome, campi))
    return riga


@sicura
def evento(nome, /, **campi):
    """annota un evento dello schema, se l'utente ha detto sì; un evento o un campo fuori schema non si scrive (nome è solo
    posizionale: un evento può avere un campo «nome», come «traguardo»)"""
    if not attive(): return
    try: riga = _riga(nome, campi)
    except schema.FuoriSchema as e: log.warning("evento delle statistiche scartato: %s (%s)", nome if nome in schema.EVENTI else "?", e); return
    _scrivi([riga])


@sicura
def traguardo(nome):
    """la prima volta che succede una cosa (primo album, primo spread, prima esportazione…), una volta sola per
    installazione, con i secondi passati dalla prima apertura del programma"""
    if not attive() or nome not in schema.TRAGUARDI: return
    with _LOCK:
        fatti = _leggi_json(TRAGUARDI); nuovo = nome not in fatti
        if nuovo: fatti[nome] = _istante(); _scrivi_json(TRAGUARDI, fatti)
    if not nuovo: return
    inizio = licenze.inizio_prova()
    evento("traguardo", nome=nome, secondi_dal_primo_avvio=time.time() - inizio if inizio else None)


# ---------------------------------------------------------------- ambiente
def _versione(s):
    """solo i numeri della versione del sistema («6.8.0-149-generic» -> «6.8.0»): niente nomi di chi ha compilato il sistema"""
    m = re.match(r"\d+(?:\.\d+){0,3}", s or "")
    return m.group(0) if m else None


def versione_sistema():
    s = sistema()
    if s == "mac": return _versione(platform.mac_ver()[0])
    if s == "windows": return _versione(platform.version())
    return _versione(platform.release())


def architettura():
    m = platform.machine().lower()
    return "x86_64" if m in ("x86_64", "amd64") else "arm64" if m in ("arm64", "aarch64") else "x86" if m in ("i386", "i686", "x86") else "altra"


def memoria_gb(kernel32=None):
    """memoria del computer in GB (arrotondata), o None se il sistema non lo dice"""
    try: return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30)
    except (AttributeError, ValueError, OSError): pass
    import ctypes
    k = kernel32 or getattr(getattr(ctypes, "windll", None), "kernel32", None)
    if k is None: return None

    class Stato(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = Stato(); m.dwLength = ctypes.sizeof(Stato)
    return round(m.ullTotalPhys / 2 ** 30) if k.GlobalMemoryStatusEx(ctypes.byref(m)) else None


def _licenza():
    st = licenze.stato()
    return dict(licenza=st["stato"].replace(" ", "_"), fascia=st["fascia"] or "nessuna", beta=st["beta"])


@sicura
def avvio(finestra=None):
    """l'ambiente: versione e sistema, lingua, memoria, processori, licenza (all'avvio della schermata e al sì)"""
    if not attive(): return
    inizio = licenze.inizio_prova()
    evento("avvio", sistema=sistema(), sistema_versione=versione_sistema(), architettura=architettura(), python="%d.%d" % sys.version_info[:2],
           lingua=lingua.attuale(), memoria_gb=memoria_gb(), core=os.cpu_count(), finestra_programma=finestra,
           giorni_dal_primo_avvio=(time.time() - inizio) / 86400 if inizio else None, **_licenza())


@sicura
def chiusura():
    """il programma (o l'editor) si chiude: conteggi in sospeso e durata della sessione (una volta sola per processo)"""
    svuota()
    with _LOCK: gia, _STATO["chiuso"] = _STATO.get("chiuso"), True
    if gia: return
    evento("chiusura", durata_s=time.monotonic() - _STATO["inizio"])


@sicura
def finestra(pagina, d):
    """misura della finestra mandata dalla pagina: solo i numeri che servono, il resto della richiesta si ignora"""
    num = lambda k: d.get(k) if isinstance(d.get(k), (int, float)) and not isinstance(d.get(k), bool) else None
    evento("finestra", pagina=pagina, larghezza=num("larghezza"), altezza=num("altezza"), scala=num("scala"),
           schermo_larghezza=num("schermo_larghezza"), schermo_altezza=num("schermo_altezza"))


@sicura
def licenza(azione, st):
    """una chiave attivata o tolta (mai la chiave né l'intestatario)"""
    evento("licenza", azione=azione, stato=st["stato"].replace(" ", "_"), fascia=st["fascia"] or "nessuna", beta=st["beta"], a_scadenza=bool(st["scade"]))


# ---------------------------------------------------------------- album, operazioni, esportazioni
def _cm(cm):
    return (cm[0], cm[1]) if isinstance(cm, (list, tuple)) and len(cm) == 2 else (None, None)


@sicura
def album_nuovo(progetto, cartella_foto):
    """album creato nella schermata: le misure (da progetto.json), se è nato da una cartella di foto e se ha il prodotto di
    un laboratorio. Nient'altro di progetto.json"""
    if not attive(): return
    with open(os.path.join(progetto, "progetto.json"), encoding="utf-8") as f: cfg = json.load(f)
    w, h = _cm(cfg.get("formato_cm"))
    evento("album_nuovo", larghezza_cm=w, altezza_cm=h, cartella_foto=bool(cartella_foto), catalogo=bool(cfg.get("prodotto")))
    traguardo("primo_album")


@sicura
def album_aperto(foto, spread, cm, ppi, secondi):
    """l'editor ha aperto un album: numeri dell'album, quanto ci ha messo e se è in sola lettura. Da qui si contano i
    secondi del primo spread e delle esportazioni"""
    _ALBUM.update(inizio=time.monotonic(), spread=spread, vuoto=spread == 0, primo=False)
    if not attive(): return
    w, h = _cm(cm)
    evento("album_aperto", foto=foto, spread=spread, larghezza_cm=w, altezza_cm=h, ppi=ppi, ms=secondi * 1000, sola_lettura=licenze.stato()["sola_lettura"])
    traguardo("primo_album")
    if foto: traguardo("prime_foto")


def _dall_apertura():
    return time.monotonic() - _ALBUM["inizio"] if _ALBUM["inizio"] is not None else None


@sicura
def operazione(op, secondi, eccezione=None, assistente=False, spread=None, esito=None):
    """un'operazione dell'editor (do_op): si conta in memoria (quante, rifiutate, fermate dalla licenza, errori, fatte
    dall'assistente, durata) e si scrive a gruppi con svuota(). Di un'operazione si tiene solo il nome, se è uno dei
    nomi noti (schema.OPERAZIONI), mai gli argomenti"""
    if not attive(): return
    nome = op if op in schema.OPERAZIONI else "altro"
    ms = secondi * 1000; d = cartella()
    with _LOCK:
        if _OPS["cartella"] != d: _OPS.update(cartella=d, conti={})
        c = _OPS["conti"].setdefault(nome, dict(n=0, rifiutate=0, licenza=0, errori=0, assistente=0, ms_tot=0.0, ms_max=0.0))
        c["n"] += 1; c["assistente"] += bool(assistente); c["ms_tot"] += ms; c["ms_max"] = max(c["ms_max"], ms)
        if isinstance(eccezione, licenze.NonConsentita): c["licenza"] += 1
        elif isinstance(eccezione, ValueError): c["rifiutate"] += 1
        elif eccezione is not None: c["errori"] += 1
    _avvia_filo()
    if eccezione is not None and not isinstance(eccezione, ValueError): errore(eccezione)
    if eccezione is None: _dopo_operazione(nome, assistente, spread, esito or {})


def _dopo_operazione(nome, assistente, spread, esito):
    if nome == "bozza":
        evento("bozza_accettata", spread=esito.get("spread"), foto=esito.get("foto"), assistente=bool(assistente)); traguardo("prima_bozza")
    if spread is None: return
    prima = _ALBUM["spread"]; _ALBUM["spread"] = spread
    if spread <= prima: return
    traguardo("primo_spread")
    if _ALBUM["vuoto"] and not _ALBUM["primo"] and prima == 0:
        _ALBUM["primo"] = True
        evento("primo_spread", secondi=_dall_apertura(), modo="bozza" if nome == "bozza" else "assistente" if assistente else "manuale", foto=esito.get("foto"))


@sicura
def svuota():
    """scrive i conteggi delle operazioni in sospeso (una riga «operazioni» per nome) e li azzera"""
    with _LOCK:
        conti, d = _OPS["conti"], _OPS["cartella"]; _OPS["conti"] = {}
    if not conti or d != cartella() or not attive(): return
    _scrivi([_riga("operazioni", dict(c, op=k)) for k, c in sorted(conti.items())])


def _ciclo_svuota():
    while True:
        time.sleep(OGNI); svuota()


def _avvia_filo():
    with _LOCK:
        nuovo = _STATO["filo"] is None
        if nuovo: _STATO["filo"] = threading.Thread(target=_ciclo_svuota, daemon=True, name="statistiche")
    if nuovo: _STATO["filo"].start(); atexit.register(svuota)


@sicura
def bozza_proposta(p, ritmo, secondi):
    evento("bozza_proposta", foto=p.get("foto"), spread=len(p.get("spreads") or ()), ritmo=ritmo if ritmo in schema.RITMI else "altro", ms=secondi * 1000)


@sicura
def controllo(r, secondi, spread):
    """esito del controllo dell'album su `spread` spread: quanti problemi per livello e per tipo (mai i testi dei problemi,
    che hanno i nomi delle foto)"""
    if not attive(): return
    tipi = {}
    for p in r["problemi"]:
        k = p["tipo"] if p["tipo"] in schema.TIPI_CONTROLLO else "altro"; tipi[k] = tipi.get(k, 0) + 1
    evento("controllo", spread=spread, tipi=tipi, pronto=bool(r["pronto"]), ms=secondi * 1000, **r["conta"])
    traguardo("primo_controllo")


@sicura
def esportazione(e, secondi):
    """un'esportazione finita (esito dell'editor: formato, totale, fatti, saltati, errori; mai la cartella né i nomi)"""
    if not attive(): return
    fmt = e["formato"] if e["formato"] in schema.FORMATI else "altro"
    evento("esportazione", formato=fmt, totale=e["totale"], fatti=e["fatti"], saltati=len(e["saltati"]), errori=len(e["errori"]), ms=secondi * 1000,
           secondi_dall_apertura=_dall_apertura(), filigrana=licenze.stato()["filigrana"] if fmt in ("jpg", "pdf", "consegna") else None)
    if e["fatti"] and fmt != "progetto": traguardo("prima_consegna" if fmt == "consegna" else "prima_esportazione")


@sicura
def importazione(tipo, foto=None, saltate=None, secondi=None):
    evento("importazione", tipo=tipo, foto=foto, saltate=saltate, ms=secondi * 1000 if secondi is not None else None)
    if foto: traguardo("prime_foto")


@sicura
def preparazione(miniature, volti, secondi, interrotta):
    evento("preparazione", miniature=miniature, volti=volti, ms=secondi * 1000, interrotta=interrotta)


# ---------------------------------------------------------------- errori
IGNOTO = "<ignoto>"                  # un nome di codice che non si sa o che non ha la forma giusta


def _codice(s):
    s = str(s)[:100]
    return s if schema.RE_CODICE.fullmatch(s) else IGNOTO


def punto(e):
    """(dove, riga, origine) di un'eccezione: il punto più interno dentro il programma («modulo:funzione» e riga, dai nomi
    del codice, mai dai nomi dei file) e il pacchetto del punto più interno in assoluto (per esempio «PIL»)"""
    dove, riga, origine = IGNOTO, None, IGNOTO; tb = e.__traceback__
    while tb is not None:
        f = tb.tb_frame; mod = str(f.f_globals.get("__name__", IGNOTO))
        origine = mod.split(".")[0]
        if mod.split(".")[0] == "impaginatore": dove, riga = f"{mod}:{f.f_code.co_name}", tb.tb_lineno
        tb = tb.tb_next
    return _codice(dove), riga, _codice(origine)


@sicura
def errore(e, attesi=False):
    """un errore del programma: tipo, punto del codice e, per gli errori del sistema, il codice (ENOSPC…). Mai il
    messaggio, che può contenere percorsi e nomi. attesi=False: i ValueError (richieste rifiutate con un messaggio per
    l'utente) non si contano qui"""
    if not attive() or (isinstance(e, ValueError) and not attesi): return
    dove, riga, origine = punto(e)
    n = getattr(e, "errno", None)
    evento("errore", tipo=_codice(type(e).__name__), dove=dove, riga=riga, origine=origine, errno=_errno.errorcode.get(n) if isinstance(n, int) else None)


# ---------------------------------------------------------------- per la pagina: stato, registro, esportazione, cancellazione
def _file_eventi():
    return [p for p in (_percorso(EVENTI_VECCHI), _percorso(EVENTI)) if os.path.exists(p)]


def _righe_grezze():
    out = []
    for p in _file_eventi():
        with open(p, encoding="ascii", errors="replace") as f: out += [r for r in f.read().split("\n") if r.strip()]
    return out


def chiedere(st=None):
    """la schermata Album deve fare la domanda del consenso? Sì con una licenza beta attiva, se l'utente non ha ancora scelto"""
    st = st or licenze.stato()
    return bool(st["beta"]) and st["stato"] == "attiva" and scelta() is None


def stato():
    """lo stato per la pagina: scelta, se chiedere, identificativo, quanti eventi, dove sono, invio"""
    st = licenze.stato(); s = scelta(); righe = _righe_grezze(); dest = invio.destinazione()
    coda = sum(_dimensione(_percorso(x)) for x in (invio.CODA, invio.IN_INVIO))
    return dict(attive=s == "si", scelta=s, chiedere=chiedere(st), beta=bool(st["beta"]), serie=st["seriale"] if st["beta"] else None,
                disponibili=not SOLO_BETA or bool(st["beta"]) or s is not None or bool(righe), id=identificativo(), eventi=len(righe),
                byte=sum(_dimensione(p) for p in _file_eventi()), cartella=cartella(), testo=testo_consenso(),
                invio=dict(attivo=dest is not None, server=dest.host if dest is not None else None, in_coda=coda))


def righe(n=RIGHE_MOSTRATE):
    """le ultime n righe del registro così come sono scritte, e quante sono in tutto («Cosa condivido»)"""
    r = _righe_grezze()
    return dict(righe=r[-n:], totale=len(r))


def esporta(dest):
    """copia il registro in un file nuovo nella cartella scelta dall'utente, da mandare a mano. Il percorso del file;
    ValueError se non c'è niente da esportare o la cartella non va"""
    r = _righe_grezze()
    if not r: raise ValueError(lingua.t("statistiche.niente_da_esportare"))
    if not os.path.isdir(dest): raise ValueError(lingua.t("statistiche.cartella_non_valida"))
    nome = f"impaginatore-statistiche-{(identificativo() or 'senza-id')[:8]}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    p = os.path.join(dest, nome)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as f: f.write(("\n".join(r) + "\n").encode("ascii"))
    log.info("statistiche esportate: %d righe", len(r))
    return p


def _ids_nel_registro():
    ids = set()
    for r in _righe_grezze():
        try: v = json.loads(r).get("id")
        except (ValueError, AttributeError): continue
        if isinstance(v, str) and schema.RE_ID.fullmatch(v): ids.add(v)
    return ids


def cancella(dest=None):
    """cancella dal computer tutto quello che è stato raccolto (registro, coda, traguardi; restano la scelta e
    l'identificativo). Se c'è una destinazione, le chiede anche di cancellare i dati degli identificativi del registro,
    in sottofondo (se il server non risponde, la richiesta si perde: STATISTICHE.md)"""
    dest = dest if dest is not None else invio.destinazione()
    ids = _ids_nel_registro() | ({identificativo()} if identificativo() else set())
    with _LOCK:
        _OPS["conti"] = {}
        for x in (EVENTI, EVENTI_VECCHI, TRAGUARDI, invio.CODA, invio.IN_INVIO, invio.PROGRESSO):
            try: os.remove(_percorso(x))
            except FileNotFoundError: pass
    log.info("statistiche raccolte cancellate da questo computer")
    if dest is not None and ids:
        filo = threading.Thread(target=sicura(lambda: invio.con_tentativi(lambda: dest.cancella(ids))), daemon=True, name="statistiche-cancella")          # tra un tentativo e l'altro: invio.ATTESE
        filo.start(); return filo
    return None


# ---------------------------------------------------------------- invio (solo con una destinazione: oggi no)
@sicura
def giro_invio(dest=None, fermo=None):
    """un giro d'invio, solo se l'utente ha detto sì e c'è una destinazione: quanti eventi sono partiti"""
    dest = dest if dest is not None else invio.destinazione()
    if dest is None or not attive(): return 0
    svuota()
    return invio.giro(dest, cartella(), fermo)


def ciclo_invio(fermo, ogni=GIRO_INVIO):
    """giri d'invio ogni `ogni` secondi finché `fermo` non viene impostato (thread della schermata, solo con una destinazione)"""
    while not fermo.wait(ogni): giro_invio(fermo=fermo)


def avvia_invio(fermo):
    """fa partire i giri d'invio in sottofondo se c'è una destinazione (oggi no: nessun thread, nessuna rete)"""
    if invio.destinazione() is None: return None
    t = threading.Thread(target=ciclo_invio, args=(fermo,), daemon=True, name="statistiche-invio"); t.start()
    return t
