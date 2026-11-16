"""Schema degli eventi delle statistiche d'uso (T-204): l'unico filtro tra il programma e il registro delle statistiche.

Un evento entra nel registro solo se il suo nome e ogni suo campo sono qui, con un valore del tipo giusto:
    intero      numero intero, tra 0 e un miliardo (i valori fuori misura si riportano dentro)
    decimale    numero finito, arrotondato a un decimale, tra 0 e un milione
    vero        True o False
    elenco      una parola di un elenco chiuso (formati, sistemi, nomi delle operazioni…)
    conteggi    {parola di un elenco chiuso: intero}
    codice      nome del codice (tipo e punto di un errore: «KeyError», «impaginatore.editor.server:do_op»): lettere,
                cifre, «_ . : < >», al massimo 100 caratteri. Nessuno spazio né barra: un nome di file, un percorso o una
                frase non ci passano
    versione    «2.0.0», «14.6.1»: cifre, punti e poche lettere, al massimo 32 caratteri
Non c'è un tipo «testo»: un nome di file, di cartella, di album o di cliente, un percorso, un testo scritto nell'album, un
dato EXIF non hanno un posto dove stare. pulisci() rifiuta (FuoriSchema) l'evento intero se un campo non va: meglio
perdere un evento che scriverne uno sbagliato.

Lo schema per chi riceve i dati è in docs/architettura/STATISTICHE.md: le due cose si tengono uguali a mano, e
tests/test_statistiche.py controlla che il documento nomini ogni evento e ogni campo.
"""
import math
import re

VERSIONE_SCHEMA = 1
INTERO, DECIMALE, VERO, CODICE, VERSIONE = "intero", "decimale", "vero", "codice", "versione"
MAX_INTERO, MAX_DECIMALE = 10 ** 9, 10 ** 6
RE_CODICE = re.compile(r"[A-Za-z_<][A-Za-z0-9_.:<>]{0,99}")
RE_VERSIONE = re.compile(r"[0-9][0-9A-Za-z.+-]{0,31}")
RE_ID = re.compile(r"[0-9a-f]{32}")
RE_SESSIONE = re.compile(r"[0-9a-f]{12}")
RE_ISTANTE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


class FuoriSchema(ValueError):
    """evento, campo o valore che lo schema non ammette: l'evento non si scrive"""


def elenco(*valori): return ("elenco", frozenset(valori))
def conteggi(*chiavi): return ("conteggi", frozenset(chiavi))


# nomi delle operazioni dell'editor (editor/server.py, NOMI_OP, più annulla e ripeti); un nome che non è qui diventa «altro».
# tests/test_statistiche.py controlla che ci siano tutte quelle dell'editor
OPERAZIONI = ("swap", "replace", "sostituisci", "set", "ratio", "t2x", "tscale", "gscale", "snap", "origar", "orient", "copia", "incolla",
              "equalize", "align", "nudge", "move", "frame", "free", "addframe", "delframe", "zorder", "crosspage", "putfree", "fullpage",
              "guides", "colore", "stella", "tolta", "face", "pan", "ev", "evg", "rit", "tono", "tono_escl", "tono_fix", "tono_L",
              "stile_applica", "stile_elimina", "stile_salva", "stile_scollega", "testo", "settext", "addtext", "blank", "new", "dup",
              "delete", "swappages", "newspread", "newspreadsel", "addtospread", "template", "setrects", "module", "mode",
              "disposizione", "spazi", "sistema", "bozza", "prodotto", "undo", "redo", "altro")
# tipi dei problemi del controllo (editor/server.py, controlla)
TIPI_CONTROLLO = ("pagina_vuota", "fuori_pagina", "sicurezza", "piega", "mancante", "danneggiata", "risoluzione", "ritaglio", "volto_tagliato",
                  "volto_piega", "ripetuta", "spazi", "tono", "prodotto", "non_usata", "stella_non_usata", "altro")
TRAGUARDI = ("primo_album", "prime_foto", "primo_spread", "prima_bozza", "primo_controllo", "prima_esportazione", "prima_consegna")
STATI_LICENZA = ("prova", "attiva", "scaduta", "revocata", "non_valida")
FASCE = ("essenziale", "pro", "studio", "laboratorio", "nessuna")
FORMATI = ("jpg", "pdf", "psd", "consegna", "progetto", "altro")
RITMI = ("alterna", "piene", "bianche", "altro")                 # motore/bozza.py, RITMI
PROCESSI = ("home", "editor", "altro")

# campi che il modulo mette in ogni evento (la «busta»): chi registra un evento non li passa
BUSTA = {"v": INTERO, "t": "istante", "id": "id", "sessione": "sessione", "proc": elenco(*PROCESSI), "ver": VERSIONE, "serie": INTERO, "ev": "nome"}

EVENTI = {
    "consenso": {"scelta": elenco("si"), "testo": INTERO},
    "avvio": {"sistema": elenco("mac", "windows", "linux"), "sistema_versione": VERSIONE, "architettura": elenco("x86_64", "arm64", "x86", "altra"),
              "python": VERSIONE, "lingua": elenco("it", "en"), "memoria_gb": INTERO, "core": INTERO, "finestra_programma": VERO,
              "licenza": elenco(*STATI_LICENZA), "fascia": elenco(*FASCE), "beta": VERO, "giorni_dal_primo_avvio": INTERO},
    "chiusura": {"durata_s": INTERO},
    "finestra": {"pagina": elenco("album", "editor"), "larghezza": INTERO, "altezza": INTERO, "scala": DECIMALE,
                 "schermo_larghezza": INTERO, "schermo_altezza": INTERO},
    "licenza": {"azione": elenco("attivata", "tolta"), "stato": elenco(*STATI_LICENZA), "fascia": elenco(*FASCE), "beta": VERO, "a_scadenza": VERO},
    "album_nuovo": {"larghezza_cm": DECIMALE, "altezza_cm": DECIMALE, "cartella_foto": VERO, "catalogo": VERO},
    "album_aperto": {"foto": INTERO, "spread": INTERO, "larghezza_cm": DECIMALE, "altezza_cm": DECIMALE, "ppi": INTERO, "ms": INTERO, "sola_lettura": VERO},
    "operazioni": {"op": elenco(*OPERAZIONI), "n": INTERO, "rifiutate": INTERO, "licenza": INTERO, "errori": INTERO, "assistente": INTERO,
                   "ms_tot": INTERO, "ms_max": INTERO},
    "primo_spread": {"secondi": INTERO, "modo": elenco("bozza", "manuale", "assistente"), "foto": INTERO},
    "bozza_proposta": {"foto": INTERO, "spread": INTERO, "ritmo": elenco(*RITMI), "ms": INTERO},
    "bozza_accettata": {"spread": INTERO, "foto": INTERO, "assistente": VERO},
    "controllo": {"spread": INTERO, "blocca": INTERO, "guarda": INTERO, "info": INTERO, "tipi": conteggi(*TIPI_CONTROLLO), "pronto": VERO, "ms": INTERO},
    "esportazione": {"formato": elenco(*FORMATI), "totale": INTERO, "fatti": INTERO, "saltati": INTERO, "errori": INTERO, "ms": INTERO,
                     "secondi_dall_apertura": INTERO, "filigrana": VERO},
    "importazione": {"tipo": elenco("foto", "progetto_zip", "catalogo"), "foto": INTERO, "saltate": INTERO, "ms": INTERO},
    "preparazione": {"miniature": INTERO, "volti": INTERO, "ms": INTERO, "interrotta": VERO},
    "traguardo": {"nome": elenco(*TRAGUARDI), "secondi_dal_primo_avvio": INTERO},
    "errore": {"tipo": CODICE, "dove": CODICE, "riga": INTERO, "origine": CODICE, "errno": CODICE},
}


def _intero(v, campo):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise FuoriSchema(campo)
    return min(max(int(round(v)), 0), MAX_INTERO)


def valore(tipo, v, campo):
    """il valore v del campo, pulito secondo il tipo; FuoriSchema se non va"""
    if tipo == INTERO: return _intero(v, campo)
    if tipo == DECIMALE:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise FuoriSchema(campo)
        return round(min(max(float(v), 0.0), MAX_DECIMALE), 1)
    if tipo == VERO:
        if not isinstance(v, bool): raise FuoriSchema(campo)
        return v
    if tipo == CODICE or tipo == VERSIONE:
        if not isinstance(v, str) or not (RE_CODICE if tipo == CODICE else RE_VERSIONE).fullmatch(v): raise FuoriSchema(campo)
        return v
    genere, ammessi = tipo
    if genere == "elenco":
        if not isinstance(v, str) or v not in ammessi: raise FuoriSchema(campo)
        return v
    if not isinstance(v, dict) or not all(isinstance(k, str) and k in ammessi for k in v): raise FuoriSchema(campo)
    return {k: _intero(n, campo) for k, n in sorted(v.items())}


def pulisci(nome, campi):
    """i campi dell'evento `nome` pronti da scrivere: solo quelli dello schema, puliti; i None si tolgono. FuoriSchema se
    l'evento non c'è, se un campo non è dello schema o se un valore non va"""
    schema = EVENTI.get(nome)
    if schema is None: raise FuoriSchema(nome)
    out = {}
    for k, v in campi.items():
        if k not in schema: raise FuoriSchema(k)
        if v is not None: out[k] = valore(schema[k], v, k)
    return out


def controlla_riga(riga):
    """una riga del registro (busta e campi) rispetta lo schema? FuoriSchema altrimenti. La usano le prove e lo strumento
    di lettura del titolare (strumenti/statistiche_beta.py) sui file che arrivano dai tester"""
    if not isinstance(riga, dict): raise FuoriSchema("riga")
    nome = riga.get("ev")
    if nome not in EVENTI: raise FuoriSchema("ev")
    for k in ("v", "t", "id", "sessione", "proc", "ver"):
        if k not in riga: raise FuoriSchema(k)
    controlli = {"istante": RE_ISTANTE, "id": RE_ID, "sessione": RE_SESSIONE}
    for k, tipo in BUSTA.items():
        if k == "ev" or k not in riga: continue
        v = riga[k]
        if tipo in controlli:
            if not isinstance(v, str) or not controlli[tipo].fullmatch(v): raise FuoriSchema(k)
        elif valore(tipo, v, k) != v: raise FuoriSchema(k)
    campi = {k: v for k, v in riga.items() if k not in BUSTA}
    if pulisci(nome, campi) != campi: raise FuoriSchema(nome)
