"""Licenze, fasce e prova gratuita (T-202): tutto si decide sul computer dell'utente, senza rete e senza server.

Documento: docs/architettura/LICENZE.md (come funziona, modello di minaccia, cosa non si fa).

stato() dice in che condizione è il programma:
    prova       nessuna chiave, prova gratuita in corso: funzioni di «prova» in tier.json, esportazioni con la filigrana
    attiva      chiave valida: funzioni della sua fascia
    scaduta     prova finita, oppure chiave a scadenza (laboratori) oltre l'ultimo giorno: sola lettura
    revocata    chiave nell'elenco firmato delle revoche, che arriva con gli aggiornamenti del programma: sola lettura
    non valida  chiave salvata che non si verifica o è di un'altra versione maggiore: come senza chiave (prova o sola lettura)
Sola lettura (LICENZA-USO.md 5.3, sito, email di fine prova): i progetti si aprono e si guardano, si esportano come
progetto (cartella o ZIP) e si ripristinano le versioni; non si modificano e non si esportano JPG, PDF e PSD.

consentita(funzione) è l'unica domanda che il resto del programma fa sulle fasce. Le funzioni sono le chiavi di «funzioni»
in tier.json (copia in questa cartella, uguale a docs/mercato/tier.json: lo controlla un test). I cancelli dell'editor
(controlla_operazione, controlla_esportazione, controlla_modelli, controlla_lettura) rifiutano con NonConsentita, che ha
un messaggio per l'utente.

File, nella cartella dei dati dell'utente (cartella(); 0700, file 0600): chiave.txt (il testo della chiave) e prova.json
(inizio della prova e ultima ora vista, contro l'orologio spostato indietro). Importare il modulo non legge né scrive niente.
"""
import datetime as dt
import json
import logging
import math
import os
import secrets
import threading
import time

from .. import __version__, lingua
from ..piattaforma import cartelle
from . import chiave as K
from .chiave import ChiaveNonValida  # noqa: F401  (si usa come licenze.ChiaveNonValida)

log = logging.getLogger("impaginatore.licenze")

NON_VALIDA = "non valida"          # non tradotto: nome dello stato (identificativo che leggono il codice e le pagine, non un testo)
STATI = ("prova", "attiva", "scaduta", "revocata", NON_VALIDA)
QUI = os.path.dirname(os.path.abspath(__file__))
FILE_TIER = os.path.join(QUI, "tier.json")
FILE_REVOCHE = os.path.join(QUI, "revoche.json")      # elenco firmato delle revoche: lo aggiunge il rilascio (LICENZE.md); manca = nessuna revoca
FILE_CHIAVE, FILE_PROVA = "chiave.txt", "prova.json"
VERSIONE_MAGGIORE = int(__version__.split(".")[0])
SEMPRE = ("import_export_progetto", "versioni_backup")  # anche in sola lettura: il lavoro fatto non si perde mai
GIORNO = 86400
TOLLERANZA_OROLOGIO = 6 * 3600                          # orologio indietro di meno (fuso, ora legale, sincronizzazione): non si segnala
AGGIORNA_VISTO = 600                                    # l'ultima ora vista si riscrive al massimo ogni 10 minuti

_LOCK = threading.Lock()
_VERIFICHE = {}                                         # (testo, chiavi pubbliche) -> contenuto della chiave o messaggio d'errore
_TIER = {}
_REVOCHE = {}


class NonConsentita(ValueError):
    """funzione che la licenza non comprende, o programma in sola lettura: il messaggio è per l'utente"""


def cartella():
    """cartella dei file della licenza, dentro i dati dell'utente (non la crea)"""
    return os.path.join(cartelle.dati_utente(), "licenza")


def orologio():
    """ora attuale (secondi): le prove la sostituiscono"""
    return time.time()


# ---------------------------------------------------------------- tier.json
def tier():
    """tier.json (fasce, prova, laboratorio), letto una volta"""
    if not _TIER:
        with open(FILE_TIER, encoding="utf-8") as f: _TIER.update(json.load(f))
    return _TIER


def funzioni_di(fascia):
    """funzioni di una fascia («essenziale», «pro», «studio», «laboratorio») o della prova («prova»)"""
    t = tier()
    if fascia in ("prova", "laboratorio"): return dict(t[fascia]["funzioni"])
    return dict(next(x for x in t["tiers"] if x["id"] == fascia)["funzioni"])


def funzioni_sola_lettura():
    return {k: k in SEMPRE for k in funzioni_di("prova")}


def nome_fascia(fascia):
    """nome della fascia («essenziale», «pro», «studio», «laboratorio») nella lingua in uso"""
    return lingua.t("licenze.fascia_" + fascia)


def fasce_con(funzione, senza_limite=False):
    """nomi delle fasce in vendita che comprendono la funzione (senza_limite: solo quelle dove non ha un tetto), es. «Pro e Studio»"""
    return lingua.elenco([nome_fascia(x["id"]) for x in tier()["tiers"] if (x["funzioni"].get(funzione) is True if senza_limite else x["funzioni"].get(funzione) not in (False, 0, None))])


# ---------------------------------------------------------------- file
def _scrivi_riservato(path, testo):
    """scrive un file che legge solo l'utente (0600, cartella 0700), in modo atomico"""
    d = os.path.dirname(path)
    os.makedirs(d, mode=0o700, exist_ok=True)
    try: os.chmod(d, 0o700)
    except OSError as e: log.warning("permessi della cartella della licenza non impostati: %s", e.strerror)
    tmp = f"{path}.{secrets.token_hex(6)}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(testo); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def chiave_salvata():
    """testo della chiave salvata su questo computer, o None"""
    try:
        with open(os.path.join(cartella(), FILE_CHIAVE), encoding="utf-8", errors="replace") as f: t = f.read(K.MAX_TESTO + 1)
    except FileNotFoundError: return None
    except OSError as e: log.warning("chiave di licenza non letta: %s", e.strerror); return None
    return t.strip() or None


def _verifica(testo):
    """contenuto della chiave (firma verificata una volta per testo e per chiavi pubbliche); ChiaveNonValida altrimenti"""
    k = (testo, tuple(sorted(K.CHIAVI_PUBBLICHE.items())))
    with _LOCK:
        if k not in _VERIFICHE:
            if len(_VERIFICHE) > 64: _VERIFICHE.clear()
            try: _VERIFICHE[k] = K.decodifica(testo)
            except K.ChiaveNonValida as e: _VERIFICHE[k] = (e.chiave, e.param)          # il testo si compone ogni volta: la lingua può cambiare
        r = _VERIFICHE[k]
    if isinstance(r, tuple): raise K.errore(r[0], **r[1])
    return dict(r)


def revocate():
    """seriali dell'elenco firmato delle revoche che arriva con il programma; vuoto se manca, non si legge o la firma non
    è valida (in quei casi non succede niente: FORMATO-CHIAVE.md, § 4)"""
    try: st = os.stat(FILE_REVOCHE)
    except OSError: return frozenset()
    k = (FILE_REVOCHE, st.st_mtime_ns, st.st_size, tuple(sorted(K.CHIAVI_PUBBLICHE.items())))
    with _LOCK:
        if _REVOCHE.get("k") != k:
            try:
                with open(FILE_REVOCHE, "rb") as f: corpo = json.loads(f.read(4 * 2**20).decode("utf-8"))
                seriali = frozenset(K.revoche(corpo)[0])
            except (OSError, ValueError) as e:
                log.warning("elenco delle revoche ignorato: %s", e); seriali = frozenset()
            _REVOCHE.update(k=k, seriali=seriali)
        return _REVOCHE["seriali"]


# ---------------------------------------------------------------- prova gratuita
def _leggi_prova(path):
    try:
        with open(path, encoding="utf-8") as f: d = json.load(f)
    except FileNotFoundError: return None
    except (OSError, ValueError) as e: log.warning("dati della prova illeggibili (%s): la prova riparte", type(e).__name__); return None
    v = [d.get(k) for k in ("inizio", "visto")] if isinstance(d, dict) else []
    if len(v) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v) and v[0] <= v[1]: return dict(inizio=float(v[0]), visto=float(v[1]))
    log.warning("dati della prova non validi: la prova riparte"); return None


def inizio_prova():
    """istante (secondi) della prima apertura del programma, dal file della prova; None se non c'è. Lo usano le statistiche
    d'uso (T-204) per i tempi «dal primo avvio»; non fa partire la prova"""
    d = _leggi_prova(os.path.join(cartella(), FILE_PROVA))
    return d["inizio"] if d else None


def _data(t):
    return dt.datetime.fromtimestamp(t).date()


def _it(giorno):
    """data per l'utente: 16/12/2026"""
    return dt.date.fromisoformat(giorno).strftime("%d/%m/%Y") if isinstance(giorno, str) else giorno.strftime("%d/%m/%Y")


def prova(adesso=None):
    """stato della prova gratuita; alla prima apertura del programma la fa partire. L'ora che conta non torna mai indietro:
    è la più recente tra l'orologio e l'ultima vista (prova.json), così spostare indietro la data non allunga la prova"""
    adesso = orologio() if adesso is None else adesso
    path = os.path.join(cartella(), FILE_PROVA)
    d = _leggi_prova(path); nuova = d is None
    if nuova: d = dict(inizio=adesso, visto=adesso)
    efficace = max(adesso, d["visto"])
    if nuova or adesso > d["visto"] + AGGIORNA_VISTO:
        d["visto"] = efficace
        try: _scrivi_riservato(path, json.dumps(dict(formato=1, inizio=d["inizio"], visto=d["visto"])))
        except OSError as e: log.warning("dati della prova non salvati: %s", e.strerror)
    giorni = tier()["prova"]["giorni"]; fine = d["inizio"] + giorni * GIORNO
    return dict(inizio=_data(d["inizio"]).isoformat(), fine=_data(fine).isoformat(), giorni=giorni, giorni_rimasti=max(0, math.ceil((fine - efficace) / GIORNO)),
                in_corso=efficace < fine, orologio_indietro=adesso < d["visto"] - TOLLERANZA_OROLOGIO)


# ---------------------------------------------------------------- stato
def msg_sola_lettura():
    return lingua.t("licenze.sola_lettura")


def msg_revocata():
    return lingua.t("licenze.revocata")


def _problema(info, adesso):
    """(stato, motivo) se la chiave, pur firmata, non vale su questo programma oggi; None se vale"""
    v = info["versione_maggiore"]
    if v > VERSIONE_MAGGIORE: return NON_VALIDA, lingua.t("licenze.chiave_piu_nuova", versione=v)
    if v < VERSIONE_MAGGIORE: return NON_VALIDA, lingua.t("licenze.chiave_vecchia", versione=v, attuale=VERSIONE_MAGGIORE)
    if info["seriale"] in revocate(): return "revocata", msg_revocata()
    if info["scade"] and _data(adesso).isoformat() > info["scade"]:
        chi = " " + lingua.t("licenze.intestata_a", nome=info["intestatario"]) if info["intestatario"] else ""
        if info["beta"]: return "scaduta", lingua.t("licenze.beta_finita", chi=chi, data=_it(info["scade"]), sola_lettura=msg_sola_lettura())       # fine della beta privata: sola lettura, come alla fine della prova
        return "scaduta", lingua.t("licenze.scaduta", fascia=nome_fascia(info["fascia"]), chi=chi, data=_it(info["scade"]), sola_lettura=msg_sola_lettura())
    return None


def _beta(info, stato):
    """etichetta della licenza beta privata e riga che la schermata Album e l'editor mostrano («Beta privata · scade il
    31/01/2027»; dopo la scadenza «… · finita il …»); niente se la chiave non è una beta"""
    if not info["beta"]: return {}
    et = lingua.t("licenze.beta_etichetta"); riga = et
    if info["scade"] and stato == "attiva": riga = lingua.t("licenze.beta_scade", data=_it(info["scade"]))
    elif info["scade"] and stato == "scaduta": riga = lingua.t("licenze.beta_finita_riga", data=_it(info["scade"]))
    return dict(etichetta_beta=et, riga_beta=riga)


def _msg_attiva(info):
    if info["beta"]:
        chi = f", {lingua.t('licenze.intestata_a', nome=info['intestatario'])}" if info["intestatario"] else ""
        f = nome_fascia(info["fascia"])
        return lingua.t("licenze.beta_attiva", chi=chi, fascia=f, data=_it(info["scade"])) if info["scade"] else lingua.t("licenze.beta_attiva_senza_scadenza", chi=chi, fascia=f)
    chi = f", {lingua.t('licenze.intestata_a', nome=info['intestatario'])}," if info["intestatario"] else ""
    coda = lingua.t("licenze.attiva_fino_al", data=_it(info["scade"])) if info["scade"] else lingua.t("licenze.attiva_aggiornamenti", versione=info["versione_maggiore"])
    return lingua.t("licenze.attiva", fascia=nome_fascia(info["fascia"]), chi=chi, computer=lingua.tn("licenze.computer", info["computer"]), coda=coda)


def _coda_orologio(pr):
    """frase sull'orologio spostato indietro, con lo spazio davanti, o niente"""
    return " " + lingua.t("licenze.orologio_indietro") if pr["orologio_indietro"] else ""


def _dettaglio_prova(pr):
    """«mancano 12 giorni (fino al 16/12/2026). Hai le funzioni del Pro…»: la frase della prova dopo i due punti"""
    f = funzioni_di("prova"); t = tier()["prova"]
    quando = lingua.t("licenze.prova_ultimo_giorno") if pr["giorni_rimasti"] <= 1 else lingua.t("licenze.prova_mancano", n=pr["giorni_rimasti"])
    cosa = lingua.t("licenze.prova_cosa_" + ("psd" if f["export_psd_livelli"] else "senza_psd") + "_" + ("filigrana" if t["filigrana_export"] else "pulita"))
    return lingua.t("licenze.prova_dettaglio", quando=quando, fine=_it(pr["fine"]), cosa=cosa)


def _msg_prova(pr):
    return lingua.t("licenze.prova", dettaglio=_dettaglio_prova(pr))


def _senza_chiave(base, pr):
    """stato del programma senza una chiave che valga: prova in corso o sola lettura"""
    if pr["in_corso"]:
        return dict(base, stato="prova", sola_lettura=False, filigrana=bool(tier()["prova"]["filigrana_export"]), funzioni=funzioni_di("prova"), messaggio=_msg_prova(pr))
    return dict(base, stato="scaduta", sola_lettura=True, filigrana=False, funzioni=funzioni_sola_lettura(),
                messaggio=lingua.t("licenze.prova_finita", fine=_it(pr["fine"]), sola_lettura=msg_sola_lettura()))


def stato(adesso=None):
    """condizione del programma: {stato, messaggio, sola_lettura, filigrana, funzioni, fascia, nome_fascia, intestatario,
    computer, seriale, emessa, scade, impronta, omaggio, beta, etichetta_beta, riga_beta, motivo, prova, versione_maggiore,
    chiave_presente}. Mai il testo della chiave. Licenza beta privata: beta True, etichetta_beta «Beta privata» e riga_beta
    «Beta privata · scade il 31/01/2027» (dopo la scadenza «… · finita il …»), da mostrare così come sono"""
    adesso = orologio() if adesso is None else adesso
    pr = prova(adesso); testo = chiave_salvata()
    base = dict(versione_maggiore=VERSIONE_MAGGIORE, prova=pr, fascia=None, nome_fascia=None, intestatario=None, computer=None, seriale=None,
                emessa=None, scade=None, impronta=None, omaggio=False, beta=False, etichetta_beta=None, riga_beta=None, motivo=None, chiave_presente=bool(testo))
    if not testo: return _orologio(_senza_chiave(base, pr))
    try:
        info = _verifica(testo)
        base.update({k: info[k] for k in ("fascia", "intestatario", "computer", "seriale", "emessa", "scade", "impronta", "omaggio", "beta")}, nome_fascia=nome_fascia(info["fascia"]))
        problema = _problema(info, adesso)
    except K.ChiaveNonValida as e: problema = (NON_VALIDA, str(e))
    if problema is None: return dict(base, stato="attiva", sola_lettura=False, filigrana=False, funzioni=funzioni_di(info["fascia"]), messaggio=_msg_attiva(info), **_beta(info, "attiva"))
    tipo, motivo = problema
    if tipo != NON_VALIDA: return dict(base, stato=tipo, sola_lettura=True, filigrana=False, funzioni=funzioni_sola_lettura(), messaggio=motivo, motivo=motivo, **_beta(info, tipo))
    s = _orologio(_senza_chiave(base, pr))
    seguito = lingua.t("licenze.intanto_la_prova", dettaglio=_dettaglio_prova(pr) + _coda_orologio(pr)) if s["stato"] == "prova" else msg_sola_lettura()
    return dict(s, stato=NON_VALIDA, motivo=motivo, messaggio=lingua.t("licenze.chiave_non_vale", motivo=motivo, seguito=seguito))


def _orologio(s):
    if s["prova"]["orologio_indietro"] and s["stato"] in ("prova", "scaduta"):
        s["messaggio"] += _coda_orologio(s["prova"])
    return s


def attiva(testo, adesso=None):
    """verifica la chiave incollata e, se vale su questo programma oggi, la salva (0600) al posto di quella che c'era.
    Restituisce il nuovo stato; ChiaveNonValida con il motivo altrimenti (la chiave che c'era resta)"""
    adesso = orologio() if adesso is None else adesso
    info = _verifica(K.in_testo(K.da_testo(testo)))
    problema = _problema(info, adesso)
    if problema: raise K.ChiaveNonValida(problema[1])
    _scrivi_riservato(os.path.join(cartella(), FILE_CHIAVE), info["testo"] + "\n")
    log.info("licenza %s attivata (seriale %s)", info["fascia"], info["seriale"])          # mai il testo della chiave né l'intestatario
    return stato(adesso)


def rimuovi(adesso=None):
    """toglie la chiave da questo computer (per usarla su un altro): torna la prova, se c'è ancora, o la sola lettura"""
    try:
        os.remove(os.path.join(cartella(), FILE_CHIAVE)); log.info("licenza tolta da questo computer")
    except FileNotFoundError: pass
    return stato(adesso)


# ---------------------------------------------------------------- domande e cancelli
def consentita(funzione, st=None):
    """la licenza di questo computer comprende la funzione (chiave di «funzioni» in tier.json)? Un limite numerico maggiore
    di zero conta come sì (limite() dice quanto). KeyError per una funzione che tier.json non conosce"""
    v = (st or stato())["funzioni"][funzione]
    return v is True or (type(v) is int and v > 0)


def limite(funzione, st=None):
    """None = senza limite, 0 = esclusa, n = al massimo n"""
    v = (st or stato())["funzioni"][funzione]
    return None if v is True else 0 if v is False else int(v)


FUNZIONI_CON_NOME = frozenset(("editor_completo", "export_jpg", "export_pdf", "export_psd_livelli", "impaginazione_automatica_album",
                               "correzione_spaziature_album", "uniformita_tono", "modelli_personali", "server_mcp", "preset_laboratori"))     # nomi in licenze.funzione_<id>


def nome_funzione(funzione):
    """nome della funzione per l'utente, con l'articolo («Il PSD a livelli»)"""
    return lingua.t("licenze.funzione_" + funzione) if funzione in FUNZIONI_CON_NOME else lingua.t("licenze.funzione_ignota", funzione=funzione)


def motivo(funzione, st=None):
    """frase per l'utente: perché la funzione non c'è e dove si trova"""
    st = st or stato()
    if st["sola_lettura"]: return lingua.t("licenze.motivo_sola_lettura", messaggio=st["messaggio"])
    dove = lingua.t("licenze.dove_prova") if st["stato"] in ("prova", NON_VALIDA) else lingua.t("licenze.dove_licenza", fascia=st["nome_fascia"])
    return lingua.t("licenze.motivo", funzione=nome_funzione(funzione), dove=dove, fasce=fasce_con(funzione))


OP_SENZA_MODIFICHE = frozenset({"copia"})                 # appunti dell'editor: non cambiano il progetto
OP_FUNZIONI = dict.fromkeys(("tono_fix", "tono_L", "tono_escl"), "uniformita_tono")   # operazioni del pannello del tono; tutte le altre: editor_completo
ESPORTAZIONI = {"jpg": "export_jpg", "pdf": "export_pdf", "psd": "export_psd_livelli", "consegna": "export_jpg"}     # la consegna al laboratorio (T-208) sono JPG
LETTURE = {"/api/tono": "uniformita_tono", "/api/tono_all": "uniformita_tono"}      # GET dell'editor che sono funzioni di fascia


def controlla_operazione(o):
    """cancello delle operazioni dell'editor (do_op): NonConsentita in sola lettura o se l'operazione è una funzione di
    un'altra fascia"""
    t = o.get("op") if isinstance(o, dict) else None
    if t in OP_SENZA_MODIFICHE: return
    f = OP_FUNZIONI.get(t, "editor_completo"); st = stato()
    if not consentita(f, st): raise NonConsentita(motivo(f, st))


def controlla_modifica():
    """cancello delle modifiche al progetto fuori da do_op (foto aggiunte): NonConsentita in sola lettura"""
    st = stato()
    if not consentita("editor_completo", st): raise NonConsentita(motivo("editor_completo", st))


def controlla_esportazione(fmt):
    """cancello delle esportazioni (run_export, formato già controllato): NonConsentita se il formato non è compreso o il
    programma è in sola lettura. Restituisce True se l'esportazione va con la filigrana (prova)"""
    f = ESPORTAZIONI[fmt]; st = stato()
    if not consentita(f, st): raise NonConsentita(motivo(f, st))
    return st["filigrana"]


def applica_filigrana(im):
    """copia dell'immagine con la filigrana della prova (filigrana.py). PIL si carica qui e non all'import: la schermata dei
    progetti usa licenze senza caricare le librerie delle immagini"""
    from . import filigrana
    return filigrana.applica(im)


def controlla_modelli(azione, quanti):
    """cancello dei modelli personali: salvarne o importarne uno nuovo quando ce ne sono già `quanti`"""
    if azione not in ("salva", "importa"): return
    st = stato(); n = limite("modelli_personali", st)
    if n == 0: raise NonConsentita(motivo("modelli_personali", st))
    if n is not None and quanti >= n:
        raise NonConsentita(lingua.tn("licenze.modelli_al_limite", n, fascia=st["nome_fascia"], fasce=fasce_con("modelli_personali", senza_limite=True)))


def controlla_lettura(percorso):
    """cancello delle GET dell'editor: NonConsentita se il percorso è una funzione che la licenza non comprende"""
    f = LETTURE.get(percorso)
    if f is None: return
    st = stato()
    if not consentita(f, st): raise NonConsentita(motivo(f, st))
