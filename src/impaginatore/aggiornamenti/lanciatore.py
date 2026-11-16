"""Lanciatore: quale copia del programma avviare (T-207). È la prima cosa che fa il comando «impaginatore» (cli.main).

Il programma installato (il pacchetto Python nel suo ambiente, o il checkout) è la «base»: un aggiornamento non la
tocca. La versione nuova si prepara in una cartella dei dati dell'utente e un puntatore dice quale copia avviare:

    <dati dell'utente>/programma/
        attuale.json            il puntatore: si sostituisce in un colpo (os.replace), mai a metà
        versioni/<versione>/    impaginatore/… estratto e verificato; il segno .completa si scrive per ultimo
        scarichi/               pacchetti scaricati (si cancellano dopo l'installazione)

    attuale.json = {"formato": 1, "versione": "2.0.1", "precedente": "2.0.0", "confermata": false, "tentativi": 0,
                    "scartata": null}

Contratto che resta uguale in ogni versione (ognuna, installata, fa da base alle successive):
- si avvia la copia di «versione» se è completa (.completa e __version__ uguale) ed è più nuova della base; altrimenti
  la base. Una base installata più nuova (reinstallazione) vince sempre sulle copie vecchie;
- la copia scelta parte al posto di questo processo (os.execv, stessi argomenti) con
  `python -c CODICE <cartella> <argomenti>`; IMPAGINATORE_VERSIONE_SCELTA dice alla copia che è già stata scelta,
  IMPAGINATORE_BASE dove sta la base (per tornare indietro da una copia aggiornata);
- una versione appena installata ha MAX_TENTATIVI avvii della schermata per confermarsi (conferma(), chiamata quando la
  schermata è in ascolto; editor, server MCP e --versione non contano); se non ci riesce il lanciatore torna da solo alla
  precedente e la segna «scartata».
Da un checkout git (sviluppo) le copie si usano solo con IMPAGINATORE_AGGIORNAMENTI_FINTI: il codice su cui si lavora
non resta nascosto da una copia vecchia. Il programma compilato (sys.frozen) non usa copie: si sostituisce intero.
"""
import json
import logging
import os
import re
import secrets
import sys

FORMATO = 1
PUNTATORE = "attuale.json"
COMPLETA = ".completa"
VAR_SCELTA = "IMPAGINATORE_VERSIONE_SCELTA"
VAR_BASE = "IMPAGINATORE_BASE"
VAR_FINTI = "IMPAGINATORE_AGGIORNAMENTI_FINTI"
MAX_TENTATIVI = 3
CODICE = "import sys; sys.path.insert(0, sys.argv.pop(1)); from impaginatore.cli import main; sys.exit(main())"
_VERSIONE = re.compile(r"(\d{1,4})\.(\d{1,4})\.(\d{1,4})(?:(a|b|rc)(\d{1,4}))?(?:\.dev(\d{1,4}))?")
_INIT = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.M)
log = logging.getLogger("impaginatore.aggiornamenti")


# ---------------------------------------------------------------- numeri di versione (PEP 440, solo le forme che usiamo)
def chiave(v):
    """chiave d'ordine di una versione «2.0.1», «2.1.0rc1», «2.0.0.dev0»: .dev < a < b < rc < finale. ValueError se non è una versione"""
    m = _VERSIONE.fullmatch(v) if isinstance(v, str) else None
    if not m: raise ValueError(f"versione non valida: {v!r}")          # non tradotto: arriva all'utente solo dentro i messaggi della tabella
    a, b, c, pre, n, dev = m.groups()
    prima = (("a", "b", "rc").index(pre), int(n)) if pre else ((-1, 0) if dev is not None else (3, 0))
    return (int(a), int(b), int(c), prima, (0, int(dev)) if dev is not None else (1, 0))


def valida(v):
    try: chiave(v); return True
    except ValueError: return False


def piu_nuova(a, b):
    """la versione a è strettamente più nuova di b?"""
    return chiave(a) > chiave(b)


def maggiore(v):
    return chiave(v)[0]


def di_sviluppo(v):
    """versione di sviluppo o di prova (.dev, a, b, rc)?"""
    k = chiave(v)
    return k[3][0] != 3 or k[4][0] == 0


# ---------------------------------------------------------------- cartelle e puntatore
def cartella():
    """<dati dell'utente>/programma (non la crea)"""
    from ..piattaforma import cartelle
    return os.path.join(cartelle.dati_utente(), "programma")


def qui():
    """cartella che contiene il pacchetto impaginatore di questo processo"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def base():
    """cartella della base: quella che il lanciatore ha lasciato nell'ambiente, altrimenti questa"""
    return os.environ.get(VAR_BASE) or qui()


def versione_in(radice):
    """__version__ della copia del programma che sta in radice (radice/impaginatore/__init__.py), letta senza importarla"""
    try:
        with open(os.path.join(radice, "impaginatore", "__init__.py"), encoding="utf-8") as f: m = _INIT.search(f.read(1 << 16))
    except OSError: return None
    return m.group(1) if m and valida(m.group(1)) else None


def da_checkout(radice):
    """la base è la cartella src di un checkout git (sviluppo)?"""
    su = os.path.dirname(os.path.abspath(radice))
    return os.path.basename(os.path.abspath(radice)) == "src" and os.path.exists(os.path.join(su, ".git")) and os.path.isfile(os.path.join(su, "pyproject.toml"))


def copie_ammesse(radice):
    return bool(os.environ.get(VAR_FINTI, "").strip()) or not da_checkout(radice)


def leggi():
    """il puntatore, o None se manca o non si legge (vale la base)"""
    try:
        with open(os.path.join(cartella(), PUNTATORE), encoding="utf-8") as f: p = json.load(f)
    except FileNotFoundError: return None
    except (OSError, ValueError) as e:
        log.warning("puntatore della versione illeggibile (%s): parte la versione installata", type(e).__name__); return None
    return p if isinstance(p, dict) and p.get("formato") == FORMATO else None


def scrivi(p):
    """sostituisce il puntatore in un colpo: un'interruzione lascia quello di prima o quello nuovo, mai uno a metà"""
    d = cartella(); os.makedirs(d, exist_ok=True)
    dest = os.path.join(d, PUNTATORE); tmp = f"{dest}.{secrets.token_hex(6)}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dict(p, formato=FORMATO), f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, dest)


def copia(versione):
    """cartella della copia di quella versione se è completa, altrimenti None"""
    if not valida(versione): return None
    c = os.path.join(cartella(), "versioni", versione)
    return c if os.path.isfile(os.path.join(c, COMPLETA)) and versione_in(c) == versione else None


def disponibile(versione, radice=None):
    """si può avviare quella versione (è la base, o una copia completa)?"""
    return valida(versione) and (versione == versione_in(radice or base()) or copia(versione) is not None)


# ---------------------------------------------------------------- scelta
def scegli(conta=False):
    """cartella da avviare: la copia del puntatore se è valida e più nuova della base, altrimenti la base.
    conta: è un avvio della schermata (le versioni non ancora confermate hanno MAX_TENTATIVI avvii per confermarsi)"""
    b = base(); vb = versione_in(b)
    if not vb or not copie_ammesse(b): return b
    p = leggi() or {}
    v = p.get("versione")
    c = copia(v) if isinstance(v, str) and valida(v) and piu_nuova(v, vb) else None
    if not c: return b
    if conta and not p.get("confermata"):
        t = p.get("tentativi")
        p["tentativi"] = (t if type(t) is int else 0) + 1
        if p["tentativi"] > MAX_TENTATIVI:
            log.warning("la versione %s non è partita dopo %s tentativi: torno alla %s", v, MAX_TENTATIVI, p.get("precedente"))
            scrivi(dict(p, versione=p.get("precedente"), precedente=None, confermata=True, tentativi=0, scartata=v))
            return scegli()
        scrivi(p)
    return c


def avvia(argv):
    """prima cosa del comando: se la copia da avviare non è questa, la avvia al posto di questo processo (os.execv, stessi
    argomenti) e non ritorna. Ritorna se tocca a questa copia (o se qualcosa non si legge: parte quella che c'è)"""
    scelta = os.environ.pop(VAR_SCELTA, None)
    io = os.path.realpath(qui())
    if scelta:                                                # già scelta da un lanciatore: mai un secondo salto (niente giri senza fine)
        if os.path.realpath(scelta) != io: log.warning("la copia scelta (%s) non è quella partita (%s)", scelta, io)
        return None
    if getattr(sys, "frozen", False): return None
    schermata = list(argv[:1]) not in (["editor"], ["mcp"]) and not set(argv) & {"--versione", "-h", "--help"}
    try: dest = scegli(conta=schermata)
    except (OSError, ValueError) as e:
        log.warning("versione da avviare non scelta (%s): parte questa", type(e).__name__); return None
    if os.path.realpath(dest) == io: return None
    os.environ[VAR_SCELTA] = dest
    os.environ.setdefault(VAR_BASE, base())
    log.info("avvio la versione in %s", dest)
    from ..piattaforma import processi
    processi.riesegui([sys.executable, "-c", CODICE, dest, *argv])
    return dest                                               # solo dove riesegui non sostituisce il processo (le prove)


def conferma(versione=None):
    """la versione in uso è partita (la schermata è in ascolto): non si contano più i suoi avvii"""
    from .. import __version__
    p = leggi()
    if p and p.get("versione") == (versione or __version__) and not p.get("confermata"):
        scrivi(dict(p, confermata=True, tentativi=0)); return True
    return False
