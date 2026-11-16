"""Dove vive il codice aggiornabile e come si sostituisce (T-207).

    Installazione            interfaccia: disponibile/motivo, pacchetto (quale pacchetto del manifesto serve),
                             precedente(), installa(manifesto, pacchetto), torna(versione)
    InstallazionePython      programma da sorgente o da pacchetto Python (oggi): la versione nuova si estrae e si verifica
                             in <dati>/programma/versioni/<versione>, si prova ad avviarla (importazioni in un processo a
                             parte, con questo Python e le sue dipendenze), poi il puntatore cambia in un colpo
                             (lanciatore.py). La base installata non si tocca: la precedente resta per tornare indietro
    InstallazioneCompilata   programma compilato (T-302): la versione nuova si installa a mano, intera, con il pacchetto
                             del suo sistema, come la prima volta. Il programma controlla il manifesto firmato e avvisa;
                             «Scarica la versione nuova» apre nel browser la pagina della release (manuale = True). Perché
                             non si sostituisce da solo: docs/architettura/AGGIORNAMENTI.md, «Programma compilato»

Estrazione sicura (estrai): solo i file elencati nel manifesto firmato, sotto impaginatore/, ognuno una volta, con lo
sha256 del manifesto; niente collegamenti simbolici, file cifrati, percorsi fuori dalla cartella; limiti di numero e
misura. Il resto del pacchetto (i metadati .dist-info di una wheel) non si estrae. Un errore in qualunque punto lascia il
puntatore com'era e toglie la cartella a metà.
"""
import hashlib
import json
import logging
import os
import secrets
import shutil
import stat
import subprocess  # nosec B404  # un solo processo: la prova di avvio della versione nuova, con argomenti in lista
import sys
import zipfile

from .. import __version__
from . import Rifiutato, lanciatore
from .firmati import percorso_valido

MAX_VOCI = 10000                       # voci nello ZIP (una wheel del programma ne ha qualche centinaio)
MAX_FILE = 64 << 20                    # byte di un file estratto
MAX_ESTRATTO = 512 << 20               # byte estratti in tutto
TEMPO_PROVA = 300                      # secondi per la prova di avvio (importa editor e motore: numpy, OpenCV, Pillow)
REVOCHE = "impaginatore/licenze/revoche.json"
PAGINA_SCARICAMENTO = ""               # pagina dei download del programma compilato, con {versione}; vuota: la release su GitHub (sorgenti.REPOSITORY)
PROVA = ("import sys; r = sys.argv[1]; sys.path.insert(0, r); import impaginatore, impaginatore.cli, impaginatore.home.server, impaginatore.editor.server; "
         "print('IMPAGINATORE ' + impaginatore.__version__ + ' ' + str(impaginatore.__file__.startswith(r)))")
log = logging.getLogger("impaginatore.aggiornamenti")


class Installazione:
    """interfaccia"""
    disponibile = True
    motivo = None                      # chiave della tabella: perché non si aggiorna (se non disponibile)
    pacchetto = None                   # chiave del pacchetto in manifesto["pacchetti"]
    manuale = False                    # True: la versione nuova si installa a mano (a_mano apre la pagina), niente scaricamento né riavvio

    def a_mano(self, manifesto, sorgente):
        """installazione a mano: apre la pagina della versione del manifesto; {pagina, versione}"""
        raise NotImplementedError

    def precedente(self):
        """versione a cui si può tornare, o None"""
        return None

    def installa(self, manifesto, pacchetto):
        """installa il pacchetto verificato (percorso) della versione del manifesto: la prossima partenza la avvia"""
        raise NotImplementedError

    def torna(self, versione):
        """la prossima partenza avvia la versione precedente"""
        raise NotImplementedError


class InstallazioneCompilata(Installazione):
    """programma compilato: niente si scarica né si sostituisce da solo. a_mano() apre la pagina della release nel browser:
    lo scaricamento passa dal browser, quindi il sistema fa sui file gli stessi controlli della prima installazione
    (Gatekeeper, SmartScreen) e la guida di installazione vale uguale. Non c'è una versione precedente da qui: per tornare
    indietro si reinstalla la precedente (stessa pagina)"""
    manuale = True
    motivo = "sistema.agg_compilato_a_mano"

    def __init__(self, apri=None, pagina=None):
        from ..piattaforma import processi
        self.apri = apri or processi.apri_browser
        self.pagina = PAGINA_SCARICAMENTO if pagina is None else pagina

    @property
    def pacchetto(self):
        return chiave_pacchetto()

    def indirizzo(self, manifesto, sorgente):
        """pagina dove si scarica la versione del manifesto: quella scelta per il prodotto (PAGINA_SCARICAMENTO, con
        {versione}), altrimenti la release su GitHub con l'etichetta v<versione>. La versione viene dal manifesto firmato e il
        repository è quello che il programma ha già controllato"""
        v = manifesto["versione"]
        if self.pagina: return self.pagina.format(versione=v)
        return f"https://github.com/{sorgente.repository}/releases/tag/v{v}"

    def a_mano(self, manifesto, sorgente):
        u = self.indirizzo(manifesto, sorgente)
        if not self.apri(u): raise Rifiutato("sistema.agg_pagina_non_aperta", indirizzo=u)
        log.info("pagina della versione %s aperta nel browser", manifesto["versione"])
        return dict(pagina=u, versione=manifesto["versione"])

    def installa(self, manifesto, pacchetto): raise Rifiutato(self.motivo)

    def torna(self, versione): raise Rifiutato(self.motivo)


def chiave_pacchetto(sistema=None, macchina=None):
    """chiave del pacchetto di questo computer in manifesto["pacchetti"] (e nel nome dei file della release, compila.py):
    mac-arm64 (Apple Silicon), mac-x86_64 (Intel), windows (x64: anche sui PC Windows con processore ARM, che lo eseguono
    in emulazione; un pacchetto nativo arm64 non c'è, DISTRIBUZIONE.md), linux (x86_64), linux-arm64"""
    import platform

    from .. import piattaforma
    s = sistema or piattaforma.sistema()
    if s == "windows": return s
    arm = (macchina or platform.machine()).lower() in ("arm64", "aarch64")
    if s == "linux": return "linux-arm64" if arm else "linux"
    return "mac-arm64" if arm else "mac-x86_64"


# ---------------------------------------------------------------- estrazione e prova
def estrai(pacchetto, manifesto, dest):
    """estrae in dest (che non esiste) i file del manifesto dallo ZIP, controllando ognuno; Rifiutato se qualcosa non torna"""
    attesi = manifesto["file"]; visti = set(); totale = 0
    try: z = zipfile.ZipFile(pacchetto)
    except (OSError, zipfile.BadZipFile): raise Rifiutato("sistema.agg_pacchetto_non_valido") from None
    try:                                     # non «with z:»: coverage con Python 3.12 non vede l'uscita dei raise dentro un «with»
        voci = z.infolist()
        if len(voci) > MAX_VOCI: raise Rifiutato("sistema.agg_pacchetto_non_valido")
        os.makedirs(dest)
        for zi in voci:
            n = zi.filename
            if not n.startswith("impaginatore/"): continue                  # metadati della wheel (.dist-info): non si estraggono
            if zi.is_dir(): continue
            if n not in attesi or n in visti or not percorso_valido(n): raise Rifiutato("sistema.agg_file_non_ammesso", nome=n[:120])
            if stat.S_ISLNK(zi.external_attr >> 16) or zi.flag_bits & 1 or zi.file_size > MAX_FILE: raise Rifiutato("sistema.agg_file_non_ammesso", nome=n[:120])
            uscita = os.path.join(dest, *n.split("/"))
            os.makedirs(os.path.dirname(uscita), exist_ok=True)
            with z.open(zi) as src, open(uscita, "xb") as out: h, totale = _copia(src, out, totale)    # zipfile non legge oltre la misura dichiarata (file_size, già controllata)
            if h.hexdigest() != attesi[n]: raise Rifiutato("sistema.agg_pacchetto_diverso")
            visti.add(n)
    finally: z.close()
    mancano = len(set(attesi) - visti)
    if mancano: raise Rifiutato("sistema.agg_file_mancanti_1" if mancano == 1 else "sistema.agg_file_mancanti_n", n=mancano)


def _copia(src, out, totale):
    """copia src in out (fino al disco: fsync) contando i byte estratti finora; (sha256, totale). Rifiutato oltre MAX_ESTRATTO"""
    h = hashlib.sha256()
    while True:
        b = src.read(1 << 16)
        if not b: break
        totale += len(b)
        if totale > MAX_ESTRATTO: raise Rifiutato("sistema.agg_troppo_grande")
        h.update(b); out.write(b)
    out.flush(); os.fsync(out.fileno())
    return h, totale


def controlla_revoche(dest):
    """l'elenco firmato delle revoche delle licenze viaggia con l'aggiornamento (licenze/revoche.json, LICENZE.md): lo copre
    già la firma del manifesto; qui si controlla anche la sua firma di licenza, perché un elenco che il programma poi
    scarterebbe (licenze.revocate) non arrivi agli utenti per sbaglio. Se questa copia non ha le chiavi vere delle licenze
    (versione di sviluppo) o l'elenco è firmato con una chiave nuova che questa non conosce, vale la firma del manifesto"""
    p = os.path.join(dest, *REVOCHE.split("/"))
    if not os.path.isfile(p): return False
    from ..licenze import chiave as K
    try:
        with open(p, "rb") as f: corpo = json.loads(f.read(4 << 20).decode("utf-8"))
        idf = corpo.get("id_firma") if isinstance(corpo, dict) else None
        if type(idf) is not int: raise ValueError("elenco delle revoche senza id_firma")          # non tradotto: diventa il messaggio della tabella qui sotto
        if K.problemi_per_il_rilascio() or idf not in K.CHIAVI_PUBBLICHE:
            log.info("elenco delle revoche coperto dalla sola firma del manifesto (chiave %r)", idf); return True
        K.revoche(corpo)
    except (ValueError, UnicodeDecodeError): raise Rifiutato("sistema.agg_revoche_non_valide") from None
    return True


def prova_avvio(radice, versione):
    """la versione in radice si importa con questo Python e le sue dipendenze (schermata, editor, motore)? Rifiutato altrimenti.
    È il caso di una versione che vuole una libreria nuova: si ferma qui, prima di cambiare il puntatore"""
    from ..piattaforma import processi
    try:
        r = subprocess.run([sys.executable, "-c", PROVA, radice], cwd=radice, capture_output=True, text=True, encoding="utf-8", errors="replace",  # nosec B603  # questo stesso Python con il codice fisso PROVA; argomenti in lista, senza shell
                           timeout=TEMPO_PROVA, env=processi.ambiente_figli(), stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e: raise Rifiutato("sistema.agg_non_si_avvia", dettaglio=type(e).__name__) from None
    righe = (r.stdout or "").strip().splitlines()
    if r.returncode != 0 or not righe or righe[-1] != f"IMPAGINATORE {versione} True":
        dettaglio = ((r.stderr or r.stdout or "").strip().splitlines() or ["?"])[-1][:200]
        raise Rifiutato("sistema.agg_non_si_avvia", dettaglio=dettaglio)


def _togli(percorso):
    """toglie una cartella: prima la rinomina (un colpo solo), poi la cancella; un errore resta nel registro"""
    if not os.path.isdir(percorso): return
    via = os.path.join(os.path.dirname(percorso), f".via-{secrets.token_hex(4)}")
    try: os.rename(percorso, via)
    except OSError: via = percorso
    shutil.rmtree(via, ignore_errors=True)


class InstallazionePython(Installazione):
    """copie del codice in <dati>/programma/versioni e puntatore (lanciatore.py)"""
    pacchetto = "python"

    def __init__(self, prova=prova_avvio):
        self.prova = prova

    @property
    def versioni(self): return os.path.join(lanciatore.cartella(), "versioni")

    def precedente(self):
        p = lanciatore.leggi() or {}
        v = p.get("precedente")
        return v if isinstance(v, str) and p.get("versione") == __version__ and lanciatore.disponibile(v) else None

    def installa(self, manifesto, pacchetto):
        v = manifesto["versione"]
        os.makedirs(self.versioni, exist_ok=True)
        tmp = os.path.join(self.versioni, f".prepara-{v}-{secrets.token_hex(4)}")
        try:
            estrai(pacchetto, manifesto, tmp)
            controlla_revoche(tmp)
            self.prova(tmp, v)
            with open(os.path.join(tmp, lanciatore.COMPLETA), "w", encoding="utf-8") as f:
                json.dump({"versione": v, "file": len(manifesto["file"])}, f); f.flush(); os.fsync(f.fileno())
            dest = os.path.join(self.versioni, v)
            _togli(dest)                                       # una copia della stessa versione di prima (dopo un ritorno indietro): si rifà
            os.rename(tmp, dest)
        except BaseException:
            _togli(tmp); raise
        p = lanciatore.leggi() or {}
        lanciatore.scrivi(dict(versione=v, precedente=__version__, confermata=False, tentativi=0, scartata=p.get("scartata") if p.get("scartata") != v else None))
        log.info("versione %s installata (precedente %s)", v, __version__)
        self.pulisci()

    def torna(self, versione):
        if versione != self.precedente(): raise Rifiutato("sistema.agg_nessuna_precedente")
        lanciatore.scrivi(dict(versione=versione, precedente=None, confermata=True, tentativi=0, scartata=__version__))
        log.info("ritorno alla versione %s (da %s)", versione, __version__)

    def pulisci(self):
        """toglie le copie che non servono più: restano quella del puntatore e la precedente"""
        p = lanciatore.leggi() or {}
        tenere = {p.get("versione"), p.get("precedente")}
        for n in sorted(os.listdir(self.versioni)):
            if n not in tenere: _togli(os.path.join(self.versioni, n))
