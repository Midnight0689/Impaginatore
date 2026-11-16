"""Strumenti del server MCP: cosa può fare l'assistente AI su Impaginatore, come funzioni Python senza l'SDK MCP.

Ogni strumento è un metodo di Assistente. Prima di tutto passa dal limite di richieste e dalla licenza
(licenze.consentita("server_mcp")); poi parla con il programma in funzione (collegamento.py), che applica gli stessi
controlli della pagina: validazione degli argomenti (editor.server.valida), transazioni (do_op), cancelli della licenza,
radici dei percorsi. Gli argomenti dell'assistente sono dati non fidati: qui si controllano tipi e intervalli e si
costruiscono SOLO le operazioni previste (nessun nome di operazione o di percorso arriva dall'assistente).

Risposte: dizionari (diventano JSON) con soli testi e metadati. I testi che vengono dai progetti (nomi di foto, progetti,
cartelle, messaggi che li contengono) passano da dato() e la risposta lo dice in «dati_utente»: sono dati, non istruzioni.
Nessun percorso completo esce: le cartelle si nominano col solo nome, i file esportati rispetto al progetto. Le immagini
(Immagine) solo con il consenso dell'utente (consenso.py). Ogni risposta sta in MAX_TESTO caratteri (limita).

Il documento è docs/architettura/MCP.md.
"""
import datetime
import hashlib
import json
import logging
import os
import re
import secrets
import threading
import time
import unicodedata
from urllib.parse import quote

from .. import __version__, licenze, lingua
from ..piattaforma import processi
from . import collegamento as C
from . import consenso

log = logging.getLogger("impaginatore.mcp")

MAX_TESTO = 40_000                # caratteri al massimo di una risposta (circa 10 000 token)
MAX_NOME = 160                    # caratteri al massimo di un nome che viene da un progetto
MAX_IMMAGINE = 2 * 2**20          # byte al massimo di un'immagine
ATTESA_APERTURA = 50              # secondi di attesa dell'editor dopo «apri» (poi: «in apertura», si richiama)
ATTESA_ESPORTAZIONE = 45          # secondi di attesa della fine di un'esportazione (poi: «in corso», stato_esportazione)
ATTESA_INIZIO = 10                # secondi in cui un esito ancora vuoto vuol dire «esportazione appena partita»
ATTESA_SCELTA = 900               # secondi per una finestra di scelta aperta all'utente
PROPOSTE = 8                      # proposte di bozza tenute in memoria (le più recenti)
LATI = {"sinistra": "L", "destra": "R"}
NOMI_LATI = {"L": "sinistra", "R": "destra"}
RE_ID = re.compile(r"p[0-9a-f]{10}")
RE_INTERVALLO = re.compile(r"[0-9,;\- ]{0,200}")
RE_PRODOTTO = re.compile(r"[a-z0-9][a-z0-9-]{0,39}/[a-z0-9][a-z0-9-]{0,39}")      # «catalogo/prodotto» (T-208): solo id, mai un percorso


def dati_utente():
    """avvertenza che accompagna ogni risposta: i nomi vengono dai file dell'utente"""
    return lingua.t("mcp.dati_utente")


def msg_cambiato():
    return lingua.t("mcp.cambiato")


def msg_non_aperto():
    return lingua.t("mcp.non_aperto")


def msg_sola_lettura():
    return lingua.t("mcp.sola_lettura")


class Rifiuto(Exception):
    """lo strumento non si può eseguire: il messaggio è per l'assistente (e per l'utente), senza dati riservati"""


class Immagine:
    """risposta con un'immagine JPEG (solo con il consenso) e una riga che la descrive"""

    def __init__(self, dati, testo):
        self.dati, self.testo = dati, testo


# ---------------------------------------------------------------- testi non fidati e misure
def dato(v, n=MAX_NOME):
    """testo che viene da un progetto, pronto per l'assistente: senza caratteri di controllo e di formato (a capo, tabulazioni,
    direzione del testo, invisibili, surrogati), spazi uniti, al massimo n caratteri. Resta un dato dentro il JSON"""
    s = "".join(" " if unicodedata.category(c) in ("Cc", "Zl", "Zp") else "" if unicodedata.category(c) in ("Cf", "Cs") else c for c in str(v))
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 1] + "…"


def id_progetto(cartella):
    """identificativo stabile di un progetto (non contiene il percorso, che resta sul computer)"""
    return "p" + hashlib.sha256(C.reale(cartella).encode("utf-8", "surrogatepass")).hexdigest()[:10]


def intero(v, minimo, massimo, cosa):
    """v è un intero (non un bool) tra minimo e massimo? Altrimenti Rifiuto"""
    if isinstance(v, bool) or not isinstance(v, int) or not minimo <= v <= massimo: raise Rifiuto(lingua.t("mcp.intero", cosa=cosa, minimo=str(minimo), massimo=str(massimo)))
    return v


def scelta(v, ammessi, cosa):
    if not isinstance(v, str) or v not in ammessi: raise Rifiuto(lingua.t("mcp.scelta", cosa=cosa, valori=", ".join(ammessi)))
    return v


def booleano(v, cosa, nullo=False):
    if not (isinstance(v, bool) or (nullo and v is None)): raise Rifiuto(lingua.t("mcp.booleano_o_niente" if nullo else "mcp.booleano", cosa=cosa))
    return v


def gruppo(v):
    """gruppo d'annulla: le operazioni di fila con lo stesso gruppo si annullano con un passo solo"""
    if v is None: return None
    if not isinstance(v, str) or not 0 < len(v) <= 100: raise Rifiuto(lingua.t("mcp.gruppo"))
    return v


def _lista_maggiore(x):
    """(contenitore, chiave) della lista più lunga (in caratteri JSON) dentro x, o (None, None)"""
    migliore, peso = (None, None), 0
    for k, v in (x.items() if isinstance(x, dict) else enumerate(x) if isinstance(x, list) else ()):
        if isinstance(v, list) and len(v) > 1:
            p = len(json.dumps(v, ensure_ascii=False))
            if p > peso: migliore, peso = (x, k), p
        if isinstance(v, (dict, list)):
            c, kk = _lista_maggiore(v)
            if c is not None and (p2 := len(json.dumps(c[kk], ensure_ascii=False))) > peso: migliore, peso = (c, kk), p2
    return migliore


def limita(dati):
    """testo JSON della risposta entro MAX_TESTO: se serve, accorcia le liste più lunghe e lo dice («troncato»)"""
    t = json.dumps(dati, ensure_ascii=False)
    while len(t) > MAX_TESTO:
        c, k = _lista_maggiore(dati)
        if c is None: raise Rifiuto(lingua.t("mcp.troppo_lunga"))
        c[k] = c[k][:len(c[k]) // 2]
        dati["troncato"] = lingua.t("mcp.accorciata")
        t = json.dumps(dati, ensure_ascii=False)
    return t


def _ripulisci(msg, base=None):
    """messaggio del programma per l'assistente: senza la cartella del progetto né la casa dell'utente, come dato"""
    s = str(msg)
    if base: s = s.replace(base, "<progetto>")
    casa = os.path.expanduser("~")
    if len(casa) > 1: s = s.replace(casa, "~")
    return dato(s, 600)


def _data(dt):
    """data di scatto EXIF «2026:05:23 10:00:01» come «2026-05-23 10:00:01»"""
    return dato(dt[:10].replace(":", "-") + dt[10:19], 19) if isinstance(dt, str) and dt else None


def _passo(p):
    return dict(nome=dato(p["nome"]), spread=p["s"] + 1 if isinstance(p.get("s"), int) else None) if isinstance(p, dict) else None


class Limitatore:
    """al massimo `massimo` chiamate in `secondi` (le chiamate di un assistente impazzito non bloccano il programma)"""

    def __init__(self, massimo=120, secondi=60, orologio=time.monotonic):
        self.massimo, self.secondi, self.orologio = massimo, secondi, orologio
        self._t = []; self._lock = threading.Lock()

    def passa(self):
        with self._lock:
            ora = self.orologio(); self._t = [t for t in self._t if ora - t < self.secondi]
            pieno = len(self._t) >= self.massimo
            if not pieno: self._t.append(ora)
        if pieno: raise Rifiuto(lingua.t("mcp.troppe_richieste"))


def licenza():
    """stato della licenza, se comprende il server MCP; altrimenti Rifiuto con il motivo (senza il nome dell'intestatario)"""
    st = licenze.stato()
    if licenze.consentita("server_mcp", st): return st
    if st["sola_lettura"]: raise Rifiuto(msg_sola_lettura())
    raise Rifiuto(lingua.t("mcp.licenza_motivo", motivo=licenze.motivo("server_mcp", st)))


def _prodotto(pr):
    """il prodotto del laboratorio dell'album per l'assistente (None se non c'è): id, nomi (dati), verificato, avviso"""
    if not pr: return None
    return dict(prodotto=f"{pr['catalogo']}/{pr['prodotto']['id']}", nome=dato(pr["prodotto"]["nome"]), laboratorio=dato(pr["laboratorio"]), verificato=pr["verificato"],
                da_confermare=pr["stato"] == "da_confermare", **({"avviso": dato(pr["avviso"], 400)} if pr.get("avviso") else {}))


def _problema(p, base):
    """un problema del controllo dell'editor per l'assistente: spread e cornice da 1, nomi e testi come dati"""
    return dict(livello=p["livello"], tipo=p["tipo"], spread=p["s"] + 1 if p["s"] is not None else None, pagina=NOMI_LATI.get(p["side"]),
                cornice=p["idx"] + 1 if p["idx"] is not None else None, foto=dato(p["foto"]) if p["foto"] else None, testo=_ripulisci(p["testo"], base),
                si_sistema_da_solo=bool(p["sistema"]))


def strumento(fn):
    """ogni strumento: limite di richieste, licenza, errori del programma tradotti in Rifiuto, risposta entro i limiti"""
    def esegui(self, *a, **k):
        self.limitatore.passa(); licenza()
        try: r = fn(self, *a, **k)
        except C.NonRaggiungibile: raise Rifiuto(lingua.t("mcp.non_risponde")) from None
        except C.Errore as e:
            if e.causa == "altra_scheda": raise Rifiuto(msg_cambiato()) from None
            raise Rifiuto(_ripulisci(e) + (" " + lingua.t("mcp.limite_licenza") if e.licenza else "")) from None
        if isinstance(r, dict): limita(r)
        return r
    esegui.__name__, esegui.__doc__ = fn.__name__, fn.__doc__
    return esegui


class Assistente:
    """gli strumenti per un assistente collegato (uno per processo del server MCP). immagini: opzione all'avvio
    «--consenti-immagini»; il resto del consenso è nelle impostazioni del programma (consenso.py)"""

    def __init__(self, immagini=False):
        self.opzione_immagini = immagini is True
        self.cid = "assistente-" + secrets.token_hex(4)          # come una scheda dell'editor: l'editor riconosce chi ha fatto l'ultima modifica
        self.limitatore = Limitatore()
        self._lock = threading.Lock()
        self._rev = {}                    # progetto -> versione dell'album vista per ultima dall'assistente
        self._proposte = {}               # id della proposta -> {progetto, spreads}
        self._esportazioni = {}           # progetto -> {formato, cartella}

    # ------------------------------------------------------------ appoggi
    def _editor(self, progetto):
        """(Server dell'editor, cartella del progetto) del progetto aperto, o Rifiuto"""
        if not isinstance(progetto, str) or not RE_ID.fullmatch(progetto): raise Rifiuto(lingua.t("mcp.progetto_id"))
        for s in C.editori().values():
            if id_progetto(s.ping["path"]) == progetto: return s, s.ping["path"]
        raise Rifiuto(msg_non_aperto())

    def _stato(self, progetto, vista=False):
        """(editor, cartella, stato dell'album). vista=True solo dove l'assistente riceve l'album com'è (stato_album,
        elenca_foto): le sue modifiche partono da quella versione. Gli strumenti che leggono lo stato solo per controllare
        i propri argomenti non la aggiornano, così una modifica dell'utente intanto si vede (MSG_CAMBIATO)"""
        ed, base = self._editor(progetto); st = ed.chiedi("/api/state")
        if vista:
            with self._lock: self._rev[progetto] = st["rev"]
        return ed, base, st

    def _op(self, progetto, corpo, g=None):
        """operazione dell'album (POST /api/op) a nome dell'assistente: un passo d'annulla, controlli e transazione dell'editor.
        Con la versione vista per ultima: se intanto l'utente ha cambiato l'album, l'editor rifiuta (MSG_CAMBIATO)"""
        ed, base = self._editor(progetto); corpo = dict(corpo, cid=self.cid)
        with self._lock: rev = self._rev.get(progetto)
        if rev is not None: corpo["rev"] = rev
        if gruppo(g) is not None: corpo["gruppo"] = g
        st = ed.chiedi("/api/op", corpo, timeout=300)
        with self._lock: self._rev[progetto] = st["rev"]
        return st, base

    def _dopo(self, st, **altro):
        """riassunto dopo un'operazione: versione, spread, annulla e ripeti, modifiche da salvare"""
        return dict(altro, versione=st["rev"], spread=len(st["spreads"]), annulla=_passo(st.get("annulla")), ripeti=_passo(st.get("ripeti")),
                    modifiche_da_salvare=bool(st.get("dirty")), dati_utente=dati_utente())

    def _foto(self, st, nome):
        """nome vero della foto del progetto che l'assistente indica (anche nella forma ripulita da dato), o Rifiuto"""
        if not isinstance(nome, str) or not 0 < len(nome) <= 1000: raise Rifiuto(lingua.t("mcp.foto_nome"))
        nomi = [f["n"] for f in st["photos"]]
        if nome in nomi: return nome
        simili = [n for n in nomi if dato(n) == dato(nome)]
        if len(simili) == 1: return simili[0]
        raise Rifiuto(lingua.t("mcp.foto_sconosciuta", nome=repr(dato(nome))))

    def _spread(self, st, numero):
        return intero(numero, 1, max(len(st["spreads"]), 1), "spread") - 1

    def immagini_consentite(self):
        return consenso.consentite(self.opzione_immagini)

    def _consenso(self):
        if not self.immagini_consentite(): raise Rifiuto(consenso.spiegazione())

    # ------------------------------------------------------------ programma e progetti
    @strumento
    def stato_programma(self):
        """licenza, programma in funzione, progetti aperti, immagini permesse o no"""
        st = licenze.stato(); ed = C.editori()
        lic = dict(stato=st["stato"], fascia=st["nome_fascia"], sola_lettura=st["sola_lettura"], filigrana_sulle_esportazioni=st["filigrana"])
        if st["stato"] == "prova": lic["giorni_di_prova"] = st["prova"]["giorni_rimasti"]
        return dict(versione=__version__, licenza=lic, programma_in_funzione=C.programma() is not None,
                    progetti_aperti=[dict(progetto=id_progetto(s.ping["path"]), cartella=dato(os.path.basename(s.ping["path"]))) for s in ed.values()],
                    immagini=dict(consentite=self.immagini_consentite(), **({} if self.immagini_consentite() else {"come_accenderle": consenso.spiegazione()})),
                    dati_utente=dati_utente())

    @strumento
    def elenca_progetti(self):
        """progetti della schermata dei progetti (avvia Impaginatore se non è in funzione)"""
        home = C.avvia_programma(); aperti = {id_progetto(p) for p in C.editori()}
        out = []
        for p in home.chiedi("/api/progetti")["progetti"]:
            pid = id_progetto(p["path"])
            if p.get("errore"): out.append(dict(progetto=pid, cartella=dato(os.path.basename(p["path"])), errore=_ripulisci(p["errore"], p["path"]))); continue
            mod = datetime.datetime.fromtimestamp(p["mod"]).strftime("%Y-%m-%d %H:%M") if p.get("mod") else None
            out.append(dict(progetto=pid, nome=dato(p["nome"]), cartella=dato(os.path.basename(p["path"])), formato_cm=p.get("cm"), spread=p.get("spread"), foto=p.get("foto"),
                            modificato=mod, aperto=pid in aperti))
        return dict(progetti=out, dati_utente=dati_utente())

    @strumento
    def apri_progetto(self, progetto):
        """apre il progetto nell'editor (id o nome esatto) e ne dà il riassunto"""
        if not isinstance(progetto, str) or not 0 < len(progetto) <= 300: raise Rifiuto(lingua.t("mcp.progetto_id_o_nome"))
        home = C.avvia_programma()
        lst = [p for p in home.chiedi("/api/progetti")["progetti"] if not p.get("errore")]
        trovati = [p for p in lst if id_progetto(p["path"]) == progetto] or [p for p in lst if dato(p["nome"]).casefold() == dato(progetto).casefold()]
        if not trovati: raise Rifiuto(lingua.t("mcp.progetto_non_trovato"))
        if len(trovati) > 1: raise Rifiuto(lingua.t("mcp.nomi_uguali", ids=", ".join(id_progetto(p["path"]) for p in trovati)))
        p = trovati[0]; pid = id_progetto(p["path"])
        home.chiedi("/api/apri", {"path": p["path"]}, timeout=60)
        fine = time.monotonic() + ATTESA_APERTURA
        while not any(id_progetto(x) == pid for x in C.editori()):
            if time.monotonic() > fine:
                return dict(progetto=pid, stato="in_apertura", messaggio=lingua.t("mcp.in_apertura"))
            time.sleep(C.PASSO)
        return self._riassunto(pid)

    def _riassunto(self, progetto):
        _, _, st = self._stato(progetto); f = st["photos"]
        cm = [round(st["W"] / st["ppi"] * 2.54, 2), round(st["H"] / st["ppi"] * 2.54, 2)] if st.get("ppi") else None
        return dict(progetto=progetto, nome=dato(st["nome"]), stato="aperto", spread_cm=cm, spread=len(st["spreads"]),
                    foto=dict(totale=len(f), nell_album=sum(1 for x in f if x["sp"] is not None), libere=sum(1 for x in f if x["sp"] is None and not x["tolta"]),
                              tolte=sum(1 for x in f if x["tolta"]), con_stella=sum(1 for x in f if x["star"]), mancanti=len(st["mancanti"]), non_aperte=len(st["scartate"])),
                    preparazione=st["prep"] if st["prep"].get("attivo") else None, versione=st["rev"], modifiche_da_salvare=bool(st["dirty"]),
                    annulla=_passo(st["annulla"]), ripeti=_passo(st["ripeti"]), prodotto=_prodotto(st.get("prodotto")), dati_utente=dati_utente())

    @strumento
    def mostra_editor(self, progetto):
        """apre l'editor del progetto nel browser dell'utente (così vede le modifiche); nessun dato esce dal computer"""
        ed, _ = self._editor(progetto)
        processi.apri_browser(ed.chiedi("/api/avvio", {})["indirizzo"])
        return dict(progetto=progetto, aperto=True, messaggio=lingua.t("mcp.editor_aperto"))

    @strumento
    def elenca_prodotti(self):
        """prodotti dei cataloghi dei laboratori installati: id per crea_progetto e imposta_prodotto, formato, spread, abbondanza, risoluzione"""
        r = C.avvia_programma().chiedi("/api/cataloghi"); out = []
        for c in r["cataloghi"]:
            for p in c["prodotti"]:
                out.append(dict(prodotto=f"{c['id']}/{p['id']}", nome=dato(p["nome"]), laboratorio=dato(c["laboratorio"]), catalogo=dato(c["nome"]), pagina_cm=p["pagina_cm"],
                                abbondanza_mm=p["abbondanza_mm"], ppi=p["ppi"], **{k: p[k] for k in ("spread_min", "spread_max") if k in p},
                                verificato=c["verificato"], da_confermare=c["stato"] == "da_confermare", generico=c["generico"], consentito=c["consentito"]))
        return dict(prodotti=out, cataloghi_non_letti=len(r["problemi"]), dati_utente=dati_utente())

    @strumento
    def crea_progetto(self, nome, larghezza_cm=None, altezza_cm=None, abbondanza_mm=0.0, spazio_mm=2.5, margine_mm=10.0, scegli_cartella_foto=False, prodotto=None):
        """progetto nuovo, con le misure o con il formato del prodotto di un laboratorio (prodotto: id di elenca_prodotti); con
        scegli_cartella_foto l'utente sceglie la cartella delle foto in una finestra del sistema"""
        if not isinstance(nome, str) or not 0 < len(nome.strip()) <= 120: raise Rifiuto(lingua.t("mcp.nome_lunghezza"))
        if prodotto is not None and (not isinstance(prodotto, str) or not RE_PRODOTTO.fullmatch(prodotto)): raise Rifiuto(lingua.t("mcp.prodotto_id"))
        misure = dict(spazio=spazio_mm, margine=margine_mm, **({} if prodotto else dict(w=larghezza_cm, h=altezza_cm, abb=abbondanza_mm)))       # col prodotto: formato e abbondanza sono i suoi
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in misure.values()): raise Rifiuto(lingua.t("mcp.misure_o_prodotto"))
        booleano(scegli_cartella_foto, "scegli_cartella_foto")
        home = C.avvia_programma(); d = dict({k: str(v) for k, v in misure.items()}, nome=nome, **({"prodotto": prodotto} if prodotto else {}))
        if scegli_cartella_foto:
            r = home.chiedi("/api/scegli-foto", {}, timeout=ATTESA_SCELTA)
            if not r.get("path"): return dict(annullato=True, messaggio=lingua.t("mcp.nessuna_cartella"))
            d["foto"] = r["path"]
        p = home.chiedi("/api/nuovo", d, timeout=60)["path"]
        return dict(progetto=id_progetto(p), nome=dato(nome), cartella=dato(os.path.basename(p)), messaggio=lingua.t("mcp.progetto_creato"), dati_utente=dati_utente())

    # ------------------------------------------------------------ lettura dell'album
    @strumento
    def stato_album(self, progetto, da_spread=1, quanti=20):
        """spread da da_spread (1 = il primo) per quanti: pagine, cornici con foto, misure, risoluzione, ritaglio"""
        intero(da_spread, 1, 100000, "da_spread"); intero(quanti, 1, 50, "quanti")
        _, _, st = self._stato(progetto, vista=True); out = []
        for s in range(da_spread - 1, min(len(st["spreads"]), da_spread - 1 + quanti)):
            sp = st["spreads"][s]; pagine = {}
            for lato in "LR":
                el = []
                for e in sp["items"]:
                    if e["side"] != lato: continue
                    if e["k"] == "t": el.append(dict(cornice=e["idx"] + 1, tipo="testo", **({"testo": dato(e["tx"], 300)} if e.get("tx") else {}))); continue
                    el.append(dict(cornice=e["idx"] + 1, tipo="foto", foto=dato(e["name"]), cm=e["cm"], ppi=e["ppi"], ritaglio=e["crop"], libera=bool(e["free"]),
                                   **({"bianco_e_nero": True} if e.get("bw") else {}), **({"usata_altre_volte": e["uses"] - 1} if e.get("uses", 1) > 1 else {})))
                pagine[NOMI_LATI[lato]] = dict(pagina="intera" if sp[lato] == "I" else "con margine", elementi=el)          # non tradotto: valore del campo «pagina», fisso come il nome del campo
            out.append(dict(numero=s + 1, **pagine))
        return dict(progetto=progetto, nome=dato(st["nome"]), spread_totali=len(st["spreads"]), da_spread=da_spread, spread=out, versione=st["rev"],
                    annulla=_passo(st["annulla"]), ripeti=_passo(st["ripeti"]), modifiche_da_salvare=bool(st["dirty"]), dati_utente=dati_utente())

    @strumento
    def elenca_foto(self, progetto, filtro="tutte", da=1, quanti=100):
        """foto del progetto: nome, proporzioni, data di scatto, spread dove sono, stella, etichetta"""
        scelta(filtro, ("tutte", "libere", "nell_album", "con_stella", "tolte"), "filtro"); intero(da, 1, 1000000, "da"); intero(quanti, 1, 500, "quanti")
        _, _, st = self._stato(progetto, vista=True)
        tiene = dict(tutte=lambda f: True, libere=lambda f: f["sp"] is None and not f["tolta"], nell_album=lambda f: f["sp"] is not None,
                     con_stella=lambda f: f["star"], tolte=lambda f: f["tolta"])[filtro]
        sel = [f for f in st["photos"] if tiene(f)]; out = []
        for f in sel[da - 1:da - 1 + quanti]:
            ar = f["ar"]
            out.append(dict(foto=dato(f["n"]), proporzioni=ar, orientamento="orizzontale" if ar > 1.05 else "verticale" if ar < 0.95 else "quadrata",
                            data=None if f.get("sd") else _data(f.get("dt")), spread=f["sp"] + 1 if f["sp"] is not None else None,
                            **({"stella": True} if f["star"] else {}), **({"etichetta": dato(f["col"], 20)} if f.get("col") else {}), **({"tolta": True} if f["tolta"] else {})))
        return dict(progetto=progetto, filtro=filtro, totale=len(sel), da=da, foto=out, dati_utente=dati_utente())

    @strumento
    def controlla_album(self, progetto, spread=None, tono=None):
        """controllo prima della consegna: problemi dal più grave (blocca, guarda, info)"""
        booleano(tono, "tono", nullo=True)
        if spread is not None and (not isinstance(spread, list) or not 0 < len(spread) <= 1000): raise Rifiuto(lingua.t("mcp.spread_elenco"))
        ed, base = self._editor(progetto); corpo = {}
        if spread is not None: corpo["spread"] = [intero(k, 1, 100000, "spread") - 1 for k in spread]
        if tono is not None: corpo["tono"] = tono
        r = ed.chiedi("/api/controlla", corpo, timeout=300)
        P = [_problema(p, base) for p in r["problemi"][:300]]
        return dict(progetto=progetto, pronto_per_la_stampa=r["pronto"], conta=r["conta"], sistema_corregge=r["sistema"], problemi=P,
                    **({"altri_problemi": len(r["problemi"]) - 300} if len(r["problemi"]) > 300 else {}), dati_utente=dati_utente())

    # ------------------------------------------------------------ bozza
    @strumento
    def proponi_bozza(self, progetto, ritmo="alterna", foto_per_spread=None, numero_spread=None, stelle=True, seme=0):
        """proposta di bozza per le foto ancora da usare (non cambia l'album): da applicare con applica_bozza"""
        corpo = dict(ritmo=scelta(ritmo, ("alterna", "piene", "bianche"), "ritmo"), stelle=booleano(stelle, "stelle"), seme=intero(seme, 0, 2**31 - 1, "seme"))
        if foto_per_spread is not None:
            if isinstance(foto_per_spread, bool) or not isinstance(foto_per_spread, (int, float)) or not 1 <= foto_per_spread <= 8: raise Rifiuto(lingua.t("mcp.foto_per_spread"))
            corpo["per_spread"] = foto_per_spread
        if numero_spread is not None: corpo["spread"] = intero(numero_spread, 1, 1000, "numero_spread")
        ed, _ = self._editor(progetto)
        p = ed.chiedi("/api/bozza", corpo, timeout=300)
        pid = "b" + secrets.token_hex(5)
        with self._lock:
            self._proposte[pid] = dict(progetto=progetto, spreads=[dict(L=s["L"], R=s["R"]) for s in p["spreads"]])
            for vecchia in list(self._proposte)[:-PROPOSTE]: del self._proposte[vecchia]
        sp = []
        for k, s in enumerate(p["spreads"]):
            nomi = dict(zip(s["foto"], s["nomi"]))
            sp.append(dict(numero=k + 1, capitolo=s["capitolo"] + 1, **({"inizio_capitolo": True, "ora": dato(s["ora"], 10) if s.get("ora") else None} if s.get("inizio") else {}),
                           sinistra=[dato(nomi.get(i, "?")) for i in s["L"]["photos"]], destra=[dato(nomi.get(i, "?")) for i in s["R"]["photos"]], ritaglio_peggiore=s.get("taglia")))
        return dict(progetto=progetto, proposta=pid, spread=len(sp), foto=p["foto"], capitoli=p["capitoli"], foto_per_spread=round(p["per_spread"], 2), spreads=sp,
                    messaggio=lingua.t("mcp.proposta_pronta"), dati_utente=dati_utente())

    @strumento
    def applica_bozza(self, progetto, proposta, dopo_spread=None, gruppo=None):
        """mette nell'album gli spread di una proposta, in fondo o dopo lo spread indicato (0 = all'inizio)"""
        with self._lock: pr = self._proposte.get(proposta) if isinstance(proposta, str) else None
        if not pr or pr["progetto"] != progetto: raise Rifiuto(lingua.t("mcp.proposta_sconosciuta"))
        corpo = dict(op="bozza", spreads=pr["spreads"])
        if dopo_spread is not None: corpo["pos"] = intero(dopo_spread, 0, 100000, "dopo_spread")
        st, _ = self._op(progetto, corpo, gruppo)
        e = st.get("esito", {})
        return self._dopo(st, aggiunti=dict(spread=e.get("spread"), foto=e.get("foto"), dal_numero=e["da"] + 1 if isinstance(e.get("da"), int) else None))

    # ------------------------------------------------------------ modifiche
    @strumento
    def cambia_disposizione(self, progetto, spread, pagina=None, passo=1, gruppo=None):
        """altra disposizione delle stesse foto sullo spread (o su una sola pagina): passo 1 la successiva, -1 la precedente"""
        corpo = dict(op="disposizione", s=intero(spread, 1, 100000, "spread") - 1, passo=passo)
        if passo not in (1, -1) or isinstance(passo, bool): raise Rifiuto(lingua.t("mcp.passo"))
        if pagina is not None: corpo["side"] = LATI[scelta(pagina, tuple(LATI), "pagina")]
        st, _ = self._op(progetto, corpo, gruppo); e = st.get("esito", {})
        return self._dopo(st, disposizione=e.get("disposizione"), di=e.get("di"), ritaglio_peggiore=e.get("taglia"), partiva_da_una_disposizione_a_mano=e.get("a_mano"),
                          pagina=NOMI_LATI.get(e.get("lato")))

    @strumento
    def sostituisci_foto(self, progetto, spread, pagina, cornice, foto, adatta=True, gruppo=None):
        """mette `foto` nella cornice indicata; se era già nell'album le due foto si scambiano; con adatta riadatta la disposizione se il ritaglio è forte"""
        _, _, st = self._stato(progetto)
        s = self._spread(st, spread); lato = LATI[scelta(pagina, tuple(LATI), "pagina")]; intero(cornice, 1, 1000, "cornice"); booleano(adatta, "adatta")
        el = next((e for e in st["spreads"][s]["items"] if e["side"] == lato and e["idx"] == cornice - 1), None)
        if el is None: raise Rifiuto(lingua.t("mcp.cornice_assente", pagina=lingua.t("mcp.pagina_" + pagina), spread=str(spread), cornice=str(cornice)))
        if el["k"] == "t": raise Rifiuto(lingua.t("mcp.cornice_testo"))
        st2, _ = self._op(progetto, dict(op="sostituisci", at=[s, lato, cornice - 1], photo=self._foto(st, foto), adatta=adatta), gruppo); e = st2.get("esito", {})
        return self._dopo(st2, scambiata_con_lo_spread=e["scambiata_con"] + 1 if isinstance(e.get("scambiata_con"), int) else None, disposizione_riadattata=e.get("adattata"),
                          ritaglio=e.get("taglia"), pagina_riadattata=NOMI_LATI.get(e.get("lato")) if e.get("adattata") else None)

    @strumento
    def sistema_album(self, progetto, spread=None, spazi=True, tono=None, gruppo=None):
        """correzioni sicure in un passo solo: spazi fra le foto e tono delle foto fuori tono (non cambia foto né disposizioni)"""
        booleano(spazi, "spazi"); booleano(tono, "tono", nullo=True)
        corpo = dict(op="sistema", spazi=spazi)
        if spread is not None:
            if not isinstance(spread, list) or not 0 < len(spread) <= 1000: raise Rifiuto(lingua.t("mcp.spread_elenco"))
            corpo["spread"] = [intero(k, 1, 100000, "spread") - 1 for k in spread]
        if tono is not None: corpo["tono"] = tono
        st, _ = self._op(progetto, corpo, gruppo); e = st.get("esito", {})
        return self._dopo(st, spread_con_spazi_corretti=e.get("spazi"), foto_con_tono_corretto=e.get("tono"))

    @strumento
    def annulla(self, progetto):
        """annulla l'ultimo passo dell'album (dice quale)"""
        st, _ = self._op(progetto, dict(op="undo"))
        if not st.get("annullato"): return self._dopo(st, annullato=None, messaggio=lingua.t("mcp.niente_da_annullare"))
        return self._dopo(st, annullato=_passo(st["annullato"]))

    @strumento
    def ripeti(self, progetto):
        """rifà il passo appena annullato"""
        st, _ = self._op(progetto, dict(op="redo"))
        if not st.get("ripetuto"): return self._dopo(st, ripetuto=None, messaggio=lingua.t("mcp.niente_da_ripetere"))
        return self._dopo(st, ripetuto=_passo(st["ripetuto"]))

    @strumento
    def salva(self, progetto):
        """salva l'album (l'editor salva anche da solo poco dopo ogni modifica); tiene una copia della versione precedente"""
        ed, _ = self._editor(progetto)
        return self._dopo(ed.chiedi("/api/save", {}), salvato=True)               # salvare non vuol dire aver visto l'album: la versione vista resta

    @strumento
    def aggiungi_foto(self, progetto, cosa="cartella"):
        """l'utente sceglie foto o una cartella in una finestra del sistema; entrano nel progetto senza riaprirlo"""
        ed, _ = self._editor(progetto)
        r = ed.chiedi("/api/pick", {"kind": "folder" if scelta(cosa, ("cartella", "foto"), "cosa") == "cartella" else "files"}, timeout=ATTESA_SCELTA)
        if not r.get("paths"): return dict(annullato=True, messaggio=lingua.t("mcp.niente_scelto"))
        r = ed.chiedi("/api/import", {"paths": r["paths"], "a_caldo": True}, timeout=600)
        return dict(importate=r["importate"], saltate=r["saltate"], aggiunte=r.get("aggiunte", 0),
                    messaggio=lingua.t("mcp.miniature"))

    @strumento
    def imposta_prodotto(self, progetto, prodotto=None):
        """prodotto del laboratorio per l'album aperto (id di elenca_prodotti; None = toglierlo): controllo e consegna seguono le sue
        regole. Il formato dell'album non cambia: un prodotto di un altro formato si rifiuta"""
        if prodotto is not None and (not isinstance(prodotto, str) or not RE_PRODOTTO.fullmatch(prodotto)): raise Rifiuto(lingua.t("mcp.prodotto_id"))
        st, _ = self._op(progetto, {"op": "prodotto", "prodotto": prodotto})
        return self._dopo(st, prodotto=_prodotto(st.get("prodotto")))

    # ------------------------------------------------------------ esportazioni
    @strumento
    def esporta(self, progetto, formato, spread="", risoluzione="stampa", conferma_problemi=False):
        """JPG (un file per spread), PDF (bozza per il cliente) o consegna al laboratorio (i file come li chiede il prodotto
        dell'album, con il riepilogo) in una cartella NUOVA dentro Esportazioni: non sovrascrive mai niente. Una consegna
        con problemi che bloccano la stampa non parte: la risposta li elenca (conferma_problemi=True consegna lo stesso)"""
        scelta(formato, ("jpg", "pdf", "consegna"), "formato"); scelta(risoluzione, ("stampa", "schermo"), "risoluzione"); booleano(conferma_problemi, "conferma_problemi")
        if not isinstance(spread, str) or not RE_INTERVALLO.fullmatch(spread): raise Rifiuto(lingua.t("mcp.spread_intervalli"))
        ed, base = self._editor(progetto)
        with self._lock: prima = self._esportazioni.get(progetto)
        if prima and not self._esito(ed, base, prima)["finita"]: raise Rifiuto(lingua.t("mcp.esportazione_in_corso"))
        cartella = os.path.join(base, "Esportazioni", "Consegna" if formato == "consegna" else formato.upper(), "Assistente " + time.strftime("%Y-%m-%d %H.%M.%S")); k = 2
        while os.path.exists(cartella): cartella = cartella.rsplit(" (", 1)[0] + f" ({k})"; k += 1
        try: ed.chiedi("/api/export", dict(fmt=formato, range=spread, dest=cartella, res=risoluzione, conferma_problemi=conferma_problemi), timeout=120)
        except C.Errore as e:
            if e.causa != "problemi_bloccanti": raise
            P = [_problema(p, base) for p in e.dati.get("problemi", [])[:50]]
            return dict(progetto=progetto, partita=False, problemi_bloccanti=e.dati.get("conta", len(P)), problemi=P, messaggio=lingua.t("mcp.consegna_problemi"), dati_utente=dati_utente())
        lavoro = dict(formato=formato, cartella=cartella, t=time.monotonic())
        with self._lock: self._esportazioni[progetto] = lavoro
        fine = time.monotonic() + ATTESA_ESPORTAZIONE
        while True:
            e = self._esito(ed, base, lavoro)
            if e["finita"] or time.monotonic() > fine: return dict(e, progetto=progetto)
            time.sleep(C.PASSO * 5)

    @strumento
    def stato_esportazione(self, progetto):
        """a che punto è l'ultima esportazione chiesta dall'assistente"""
        ed, base = self._editor(progetto)
        with self._lock: lavoro = self._esportazioni.get(progetto)
        if not lavoro: return dict(progetto=progetto, messaggio=lingua.t("mcp.nessuna_esportazione"))
        return dict(self._esito(ed, base, lavoro), progetto=progetto)

    def _esito(self, ed, base, lavoro):
        """esito di un'esportazione dall'esito strutturato dell'editor (/api/esito: numeri e motivi, uguale in ogni lingua).
        L'esito è uno per editor e ogni esportazione lo ricomincia (anche una chiesta dalla pagina, anche una rifiutata): se non
        è più quello della nostra cartella, il suo esito non si sa più (finita per quanto ci riguarda: i file sono nella cartella)"""
        e = ed.chiedi("/api/esito"); filigrana = licenze.stato()["filigrana"]
        if e.get("dest"): nostra = os.path.normpath(e["dest"]) == os.path.normpath(lavoro["cartella"]); lavoro["vista"] = lavoro.get("vista") or nostra
        else: nostra = not lavoro.get("vista") and time.monotonic() - lavoro["t"] < ATTESA_INIZIO      # appena chiesta: l'esportazione parte tra un attimo
        if not nostra:
            return dict(formato=lavoro["formato"], finita=True, stato="non_seguibile", cartella=dato(os.path.relpath(lavoro["cartella"], base), 300), dati_utente=dati_utente(),
                        messaggio=lingua.t("mcp.non_seguibile"))
        saltati = e.get("saltati") or []
        errori = [_ripulisci(lingua.t("server.log_saltato", k=x.get("spread"), motivo=x.get("motivo")), base) for x in saltati] + [_ripulisci(x, base) for x in e.get("errori") or []]
        finita = bool(e.get("finito"))
        return dict(formato=lavoro["formato"], finita=finita, stato="finita" if finita else "in_corso", spread_esportati=int(e.get("fatti") or 0), spread_saltati=len(saltati),
                    errori=errori[:20], cartella=dato(os.path.relpath(lavoro["cartella"], base), 300), **({"filigrana": lingua.t("mcp.filigrana_prova")} if filigrana else {}),
                    **({} if finita else {"messaggio": lingua.t("mcp.esportazione_continua")}), dati_utente=dati_utente())

    # ------------------------------------------------------------ immagini (solo con il consenso)
    @strumento
    def anteprima_spread(self, progetto, spread, larghezza=800):
        """immagine JPEG dello spread com'è adesso (solo se l'utente ha acceso le immagini)"""
        self._consenso(); intero(larghezza, 200, 1200, "larghezza")
        ed, _, st = self._stato(progetto); s = self._spread(st, spread)
        b = ed.chiedi(f"/img/spread/{s}?k={larghezza / st['W']:.5f}", binario=True)
        return self._immagine(b, lingua.t("mcp.img_spread", spread=str(spread), larghezza=str(larghezza)))

    @strumento
    def miniatura_foto(self, progetto, foto, lato=384):
        """miniatura JPEG di una foto del progetto (solo se l'utente ha acceso le immagini)"""
        self._consenso(); intero(lato, 64, 512, "lato")
        ed, _, st = self._stato(progetto); n = self._foto(st, foto)
        b = ed.chiedi(f"/img/thumb/{quote(n, safe='')}?w={lato}", binario=True)
        return self._immagine(b, lingua.t("mcp.img_miniatura", nome=dato(n), lato=str(lato)))

    def _immagine(self, b, testo):
        if len(b) > MAX_IMMAGINE: raise Rifiuto(lingua.t("mcp.img_grande"))
        return Immagine(b, testo)
