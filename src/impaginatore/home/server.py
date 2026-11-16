"""Schermata iniziale dei progetti (come quella di Smart Albums) + avvio dell'editor del progetto scelto.

    impaginatore [--porta 8765] [--browser | --no-browser] [--progetti <cartella>]      (oppure: python -m impaginatore)

Si apre nella finestra del programma (desktop, pywebview) se c'è, altrimenti nel browser; --browser sceglie il browser.

I nuovi progetti stanno in  <cartella dei progetti>/<nome>/  (progetto.json + album.json + Foto/ + _cache/); la cartella dei
progetti è --progetti, IMPAGINATORE_PROGETTI, <checkout>/Progetti (come nelle 1.x) o Documenti/Impaginatore/Progetti.
Quella cartella È il file di salvataggio del progetto: l'editor la salva da solo mentre lavori.
Progetti che stanno altrove (es. sul Desktop) si aggiungono con «Apri progetto esistente»: restano dove sono.
Solo libreria standard: l'editor vero (impaginatore.editor) parte come processo a parte, uno per progetto aperto.

Stato: una schermata per processo, nelle variabili di questo modulo (PROGETTI, PORTA, EDITORS, AGGIORNAMENTI).
Importare il modulo non fa niente: configura() le prepara, crea_server() apre la porta, main() fa tutto.
"""
import argparse, json, logging, os, shutil, subprocess, sys, threading, time  # nosec B404  # processi lanciati solo con argomenti in lista, mai con la shell
import webbrowser  # noqa: F401  (resta come attributo del modulo: lo intercettano i test; il browser si apre con processi.apri_browser)
from urllib.parse import parse_qs, urlparse

from .. import __version__, aggiornamenti, archivio, formato, giornale, nomi, percorsi, piattaforma, sicurezza
from ..piattaforma import azioni, cartelle, dialoghi, processi
from ..servizio import Gestore, ServerLocale, porta_libera as _porta_libera
from .. import licenze                         # T-202: licenza e prova gratuita, controllate su questo computer (docs/architettura/LICENZE.md)
from .. import laboratori                      # T-208: cataloghi dei laboratori (docs/architettura/CATALOGHI.md)
from .. import desktop                         # T-201: finestra del programma (pywebview si carica solo in desktop.motore())
from ..desktop import dialoghi as desktop_dialoghi
from ..mcp import consenso as consenso_mcp      # T-203/T-205: l'interruttore «L'assistente può vedere le immagini» (solo libreria standard)

PORTA_PREDEFINITA = 8765
PROGETTI = None                                # cartella dei progetti nuovi (configura)
REG = None                                     # registro dei progetti che stanno altrove
PORTA = PORTA_PREDEFINITA                      # porta di questa schermata: gli editor la usano per il pulsante «Progetti»
AGGIORNAMENTI = aggiornamenti.NonDisponibili()
LOCK = threading.Lock()
EDITORS = {}                                   # percorso progetto -> (Popen, porta)
SERVER = None                                  # server della schermata (crea_server): il suo gettone resta dopo un riavvio
FINESTRA = False                               # la schermata è nella finestra del programma (desktop.esegui): dialoghi per gli editor, riavvio con la finestra
RADICI = percorsi.Radici(lambda: [PROGETTI] + registro())      # cartelle che la pagina può nominare: progetti e cartelle scelte con le finestre di sistema
log = logging.getLogger("impaginatore.home")


def configura(progetti=None, porta=PORTA_PREDEFINITA, aggiorna=None):
    """prepara la schermata: cartella dei progetti (la crea), porta, aggiornamenti (None = quelli adatti all'installazione)"""
    global PROGETTI, REG, PORTA, AGGIORNAMENTI
    PROGETTI = os.path.abspath(os.path.expanduser(progetti)) if progetti else cartelle.progetti_predefinita()
    REG = os.path.join(PROGETTI, "registro.json")
    PORTA = porta
    AGGIORNAMENTI = aggiorna or aggiornamenti.predefiniti(riavvia_programma)
    os.makedirs(PROGETTI, exist_ok=True)


def registro():
    """progetti aggiunti all'elenco che esistono ancora. Senza registro (prima volta) nessuno; un registro illeggibile si
    annota e si riparte da vuoto (VER-015)"""
    try: return [p for p in formato.leggi_json(REG) if os.path.exists(os.path.join(p, "progetto.json"))]
    except FileNotFoundError: return []
    except (OSError, ValueError, TypeError) as e:
        log.warning("elenco dei progetti aggiunti illeggibile (%s): riparto da vuoto", type(e).__name__); return []


def salva_registro(lst): formato.scrivi_json(REG, sorted(set(lst)), indent=1)


def progetti():
    out = []
    paths = [os.path.join(PROGETTI, d) for d in sorted(os.listdir(PROGETTI)) if os.path.exists(os.path.join(PROGETTI, d, "progetto.json"))] + registro()
    for p in dict.fromkeys(paths):
        try:
            cfg = formato.leggi_json(os.path.join(p, "progetto.json"))
            spec = formato.file_album(p) or ""; nsp = formato.conta_spread(p)          # album.json (o spec.py di un progetto 1.x, letto senza eseguirlo)
            meta = os.path.join(p, "_cache", "meta.json"); nf = len(formato.leggi_json(meta)) if os.path.exists(meta) else 0
            cover = None
            if nf:
                first = formato.leggi_json(meta)[0]["n"]
                if os.path.exists(os.path.join(p, "_cache", "thumbs", first)): cover = first
            mt = max(os.path.getmtime(f) for f in (spec, os.path.join(p, "progetto.json")) if os.path.exists(f))
            out.append(dict(path=p, nome=cfg.get("nome") or os.path.basename(p), cm=cfg.get("formato_cm"), spread=nsp, foto=nf, mod=mt, cover=cover,
                            esterno=not os.path.abspath(p).startswith(PROGETTI + os.sep), aperto=p in EDITORS and EDITORS[p][0].poll() is None))
        except Exception as e:
            out.append(dict(path=p, nome=os.path.basename(p), errore=str(e), spread=0, foto=0, mod=0))
    return sorted(out, key=lambda x: -x["mod"])


def num(v):
    v = float(str(v).replace(",", ".").strip())
    if not v > 0: raise ValueError("misura non valida")
    return v


def nuovo(d):
    nome = nomi.nome_progetto(d.get("nome"))           # il nome è un dato: si salva in progetto.json, mai dentro codice (SEC-003)
    prodotto = laboratori.scelta(d["prodotto"]) if d.get("prodotto") else None       # T-208: formato, abbondanza e risoluzione dal prodotto del laboratorio
    if prodotto:
        g = laboratori.geometria(prodotto[1]); w, h = g["formato_cm"]; d = dict(d, abb=g["abbondanza_mm"])
    else: w, h = num(d.get("w")), num(d.get("h"))
    if not (5 <= w <= 300 and 5 <= h <= 200): raise ValueError("Misure fuori dal normale: larghezza 5–300 cm, altezza 5–200 cm")
    cartella = nomi.nome_cartella(nome)                 # valido su macOS, Windows e Linux
    fotodir = dialoghi.senza_barra((d.get("foto") or "").strip())
    if fotodir:                                          # progetto accanto alle foto del cliente: <cartella cliente>/Impaginatore, le foto restano dove sono
        if not os.path.isdir(fotodir): raise ValueError("La cartella delle foto non esiste")
        base, cartella = os.path.dirname(fotodir), "Impaginatore"
    else: base = PROGETTI
    p = os.path.join(base, cartella); k = 2
    while os.path.exists(p): p = os.path.join(base, f"{cartella} {k}"); k += 1
    def mm(key, dflt):
        try: return float(str(d.get(key, dflt)).replace(",", ".") or dflt)
        except ValueError: raise ValueError(f"Misure non valide: «{d.get(key)}» non è un numero") from None
    cfg = dict(nome=nome, foto=fotodir or os.path.join(p, "Foto"), foto_extra=[], tolte=[], formato_cm=[round(w, 2), round(h, 2)], dimensioni_esatte=False, ppi=300,
               abbondanza_mm=mm("abb", 0), spazio_mm=mm("spazio", 2.5), margine_mm=mm("margine", 10), uscita_psd=os.path.join(p, "PSD"),
               testo=dict(nome=nome, sottotitolo="", data=""), esposizione=dict(globale=0.0, per_cartella={}, per_foto={}), bilanciamento_bianco={}, centri_volto={})
    if prodotto: cfg.update(ppi=g["ppi"], prodotto=laboratori.per_progetto(*prodotto))
    try: testo = formato.testo_progetto(cfg)                # misure controllate come all'apertura, PRIMA di creare la cartella (VER-010)
    except formato.ErroreProgetto as e: raise ValueError(f"Misure non valide: {str(e).removeprefix('progetto.json, ')}") from None
    os.makedirs(p if fotodir else os.path.join(p, "Foto"))
    formato.scrivi_atomico(os.path.join(p, "progetto.json"), testo)
    if fotodir: salva_registro(registro() + [p])
    formato.scrivi_atomico(os.path.join(p, formato.ALBUM), formato.album_vuoto())
    return p


def porta_libera(pref=None):
    for pt in ([pref] if pref else []) + list(range(8801, 8900)):
        if _porta_libera(pt): return pt
    raise RuntimeError("nessuna porta libera")


def porta_stabile(path):
    """ogni progetto ha SEMPRE la stessa porta (così l'indirizzo non cambia e ricaricare la pagina funziona dopo un riavvio)"""
    import zlib
    return 8801 + zlib.crc32(path.encode()) % 99


def gia_attivo(path):
    """porta di un editor di questo progetto già in funzione (anche se non lanciato da qui), altrimenti None"""
    for pt in [porta_stabile(path)] + list(range(8801, 8900)):
        g = sicurezza.gettone_di("editor", pt)              # solo gli editor di questo utente hanno il file di sessione (e rispondono al gettone)
        if not g: continue
        try:
            if sicurezza.chiedi(pt, "/api/ping", g, timeout=1).get("path") == path: return pt
        except (OSError, ValueError) as e: log.debug("editor sulla porta %s non risponde: %s", pt, e)
    return None


def pronto(pt):
    """indirizzo di avvio (monouso) dell'editor sulla porta pt se risponde, altrimenti None"""
    return sicurezza.indirizzo_avvio("editor", pt, timeout=1)


def apri(path):
    path = os.path.abspath(path)
    if path not in [p["path"] for p in progetti()]: raise ValueError("progetto non in elenco")
    formato.leggi_progetto(path); formato.controlla(path)          # un progetto non valido si spiega qui, prima di avviare l'editor
    with LOCK:
        e = EDITORS.get(path)
        if e and e[0].poll() is None: return e[1]  # pragma: no branch  # coverage 7.17 non vede un return dentro «with»; provato da test_apri_riusa_editor_lanciato_da_qui
        pt = gia_attivo(path)
        if pt: return pt  # pragma: no branch  # coverage 7.17 non vede un return dentro «with»; provato da test_apri_riusa_editor_lanciato_da_qui
        pt = porta_libera(porta_stabile(path))
        with os.fdopen(giornale.riservato(os.path.join(PROGETTI, "editor.log")), "ab") as log:          # 0600: percorsi dei progetti (VER-013)
            proc = subprocess.Popen([sys.executable, "-m", "impaginatore.editor", "--progetto", path, "--porta", str(pt), "--home", f"http://127.0.0.1:{PORTA}"],  # nosec B603  # questo stesso Python (sys.executable -m); argomenti in lista, senza shell: nessun dato passa da un interprete di comandi
                                    stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, cwd=processi.cartella_pacchetto(), env=processi.ambiente_figli())
        EDITORS[path] = (proc, pt); return pt


def importa_zip():
    """sceglie un file .zip di progetto esportato, lo apre in <Progetti>/ e lo mette in elenco; restituisce la cartella ('' se annullato).
    Lo ZIP si estrae con archivio.estrai (percorsi, limiti, solo i tipi di file di un progetto) e il progetto si controlla
    prima di metterlo in elenco: niente del suo contenuto viene eseguito"""
    import tempfile
    zp = dialoghi.scegli_zip("Scegli il file ZIP del progetto").strip()
    if not zp: return ""
    tmp = tempfile.mkdtemp(prefix=".importazione-", dir=PROGETTI)
    try:
        avvisi = []; archivio.estrai(zp, tmp, avvisi)
        cand = [tmp] + [os.path.join(tmp, d) for d in sorted(os.listdir(tmp)) if os.path.isdir(os.path.join(tmp, d))]
        src = next((c for c in cand if os.path.exists(os.path.join(c, "progetto.json"))), None)
        if not src: raise ValueError("Nel file ZIP non c'è un progetto (manca progetto.json)")
        formato.prepara_importato(src)
        for a in avvisi: print("importa ZIP:", a, flush=True)
        nome = nomi.nome_cartella(os.path.basename(src) if src != tmp else os.path.splitext(os.path.basename(zp))[0])
        p = os.path.join(PROGETTI, nome); k = 2
        while os.path.exists(p): p = os.path.join(PROGETTI, f"{nome} {k}"); k += 1
        shutil.move(src, p); return p
    finally: shutil.rmtree(tmp, ignore_errors=True)


def scegli_cartella(msg="Scegli la cartella del progetto (quella con progetto.json)"):
    return dialoghi.scegli_cartella(msg).strip()


def riavvia_programma():
    """dopo un aggiornamento: chiude gli editor, rilancia il programma sulla stessa porta (la pagina si ricarica da sola) ed esce.
    Con la finestra del programma il rilancio apre una finestra nuova (questa si chiude con il processo)"""
    if os.environ.get("IMPAGINATORE_SENZA_RIAVVIO"): return                       # solo per le prove
    def riavvia():
        time.sleep(.6)
        for pr, _ in EDITORS.values():
            try: pr.terminate()
            except OSError: pass  # nosec B110  # editor già chiuso: non c'è niente da fermare
        processi.rilancia_dopo([sys.executable, "-m", "impaginatore", "--porta", str(PORTA), "--progetti", PROGETTI] + ([] if FINESTRA else ["--no-browser"]), 1.5,
                               gettone=SERVER.sessione.gettone if SERVER else None)        # stesso gettone: la pagina aperta resta collegata
        esci()
    threading.Thread(target=riavvia, daemon=True).start()


def esci():
    """fine del processo (i test la sostituiscono)"""
    os._exit(0)


class H(Gestore):
    COOKIE = ("/", "/api/cover")                  # pagina e copertine (immagini): anche con il solo cookie

    def send(self, body, ctype="application/json", code=200):
        if isinstance(body, (dict, list)): body = json.dumps(body).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ctype != "image/jpeg" else "max-age=600"); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        try:
            if u.path == "/": self.pagina("home.html")
            elif u.path == "/api/ping": self.send({"ok": True})
            elif u.path == "/api/progetti": self.send(dict(progetti=progetti(), cartella=PROGETTI, sistema=piattaforma.sistema()))
            elif u.path == "/api/aggiornamento": self.send(AGGIORNAMENTI.stato())       # la versione in uso si rilegge sempre (cambia anche se si aggiorna a mano)
            elif u.path == "/api/versioni": self.send({"versioni": AGGIORNAMENTI.versioni()})
            elif u.path == "/api/licenza": self.send(licenze.stato())                     # aprire la schermata la prima volta fa partire la prova
            elif u.path == "/api/assistente": self.send({"immagini": consenso_mcp.salvato()})
            elif u.path == "/api/cataloghi": self.send(dict(laboratori.elenco(), cartella=laboratori.cartella_utente()))
            elif u.path == "/api/pronto":
                a = pronto(int(q["porta"][0])); self.send({"pronto": bool(a), "indirizzo": a})
            elif u.path == "/api/cover":
                p = q["path"][0]; n = q["n"][0]
                if p not in [x["path"] for x in progetti()] or "/" in n or "\\" in n or n in ("", ".", ".."): raise ValueError("no")      # solo un nome di file (anche con le barre di Windows)
                with open(os.path.join(p, "_cache", "thumbs", n), "rb") as f: self.send(f.read(), "image/jpeg")
            else: self.send({"errore": "non trovato"}, code=404)
        except Exception as e: self.send({"errore": str(e)}, code=400)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            d = self.corpo()
            if u.path == "/api/nuovo":
                if str(d.get("foto") or "").strip(): RADICI.controlla(str(d["foto"]).strip(), "quella cartella delle foto")
                self.send({"path": nuovo(d)})
            elif u.path == "/api/apri": self.send({"porta": apri(d["path"])})
            elif u.path == "/api/aggiungi":
                p = scegli_cartella()
                if not p: self.send({"annullato": True}); return
                if not os.path.exists(os.path.join(p, "progetto.json")): raise ValueError("In quella cartella non c'è progetto.json: scegli la cartella del progetto")
                salva_registro(registro() + [p]); self.send({"path": p})
            elif u.path == "/api/scegli-foto":
                p = scegli_cartella("Scegli la cartella con le foto del cliente"); RADICI.scelta(p); self.send({"path": p, "nome": nomi.nome_da_cartella(p)})
            elif u.path == "/api/aggiorna": self.send({"ok": AGGIORNAMENTI.aggiorna()})
            elif u.path == "/api/ripristina": self.send(AGGIORNAMENTI.ripristina(d.get("codice")))
            elif u.path == "/api/controlla": self.send(AGGIORNAMENTI.controlla())
            elif u.path == "/api/licenza/attiva": self.send(licenze.attiva(d.get("chiave")))   # chiave non valida: ValueError con il motivo (400)
            elif u.path == "/api/licenza/rimuovi": self.send(licenze.rimuovi())
            elif u.path == "/api/assistente":                  # solo l'utente, da questa pagina (gettone): nessuno strumento MCP passa di qui
                if not isinstance(d.get("immagini"), bool): raise ValueError("immagini: vero o falso")
                consenso_mcp.imposta(d["immagini"]); self.send({"immagini": consenso_mcp.salvato()})
            elif u.path == "/api/importa-zip":
                p = importa_zip(); self.send({"path": p} if p else {"annullato": True})
            elif u.path == "/api/importa-catalogo":            # T-208: solo l'utente sceglie il file, con la finestra del sistema (nessun percorso dalla pagina)
                p = dialoghi.scegli_catalogo()
                self.send(laboratori.importa(p) if p else {"annullato": True})
            elif u.path == "/api/rimuovi":
                salva_registro([p for p in registro() if p != d["path"]]); self.send({"ok": True})
            elif u.path == "/api/cestino":
                p = percorsi.reale(d["path"])                 # collegamenti e «..» risolti: deve essere davvero un progetto dentro la cartella dei progetti
                if p == percorsi.reale(PROGETTI) or not percorsi.dentro(p, PROGETTI) or not os.path.isfile(os.path.join(p, "progetto.json")):
                    raise ValueError("Solo i progetti creati qui si possono mettere nel Cestino")
                azioni.cestina(p); self.send({"ok": True})
            elif u.path == "/api/finder": azioni.mostra(RADICI.controlla(d["path"], "quel percorso")); self.send({"ok": True})
            elif u.path == "/api/dialogo":                    # finestra di scelta chiesta da un editor, aperta nella finestra del programma (desktop.dialoghi.Ponte)
                if not FINESTRA: raise ValueError("la finestra del programma non è aperta")
                self.send({"percorsi": desktop_dialoghi.scegli(d.get("tipo"), d.get("messaggio"))})
            elif u.path == "/api/esci":
                for pr, _ in EDITORS.values():                                   # prima di rispondere: chi riceve «ok» sa che gli editor sono già stati fermati
                    try: pr.terminate()
                    except OSError: pass  # nosec B110  # editor già chiuso: non c'è niente da fermare
                self.send({"ok": True})
                threading.Thread(target=lambda: (time.sleep(.4), esci()), daemon=True).start()
            else: self.send({"errore": "non trovato"}, code=404)
        except percorsi.FuoriDalleRadici as e: self.send({"errore": str(e)}, code=403)
        except Exception as e: self.send({"errore": str(e)}, code=400)


def crea_server(porta=None, gettone=None):
    """server HTTP della schermata su 127.0.0.1 (porta 0 = una libera; None = quella di configura). Non lo avvia: serve_forever().
    gettone: quello della sessione (None = uno nuovo); il file di sessione per i client locali si scrive qui"""
    global PORTA, SERVER
    if PROGETTI is None: configura()
    srv = ServerLocale(("127.0.0.1", PORTA if porta is None else porta), H, tipo="home", gettone=gettone, progetti=PROGETTI)
    PORTA = srv.server_address[1]; SERVER = srv
    return srv


def gia_aperto(porta):
    """la schermata dei progetti risponde già su questa porta?"""
    g = sicurezza.gettone_di("home", porta)
    if not g: return False
    try: return sicurezza.chiedi(porta, "/api/ping", g, timeout=1).get("ok") is True
    except (OSError, ValueError): return False


def apri_browser(indirizzo, ritardo=0.3):
    threading.Timer(ritardo, processi.apri_browser, args=(indirizzo,)).start()          # senza il gettone nell'ambiente (VER-011)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="impaginatore", description="Impaginatore: schermata dei progetti (nella finestra del programma, o nel browser)")
    ap.add_argument("--porta", type=int, default=PORTA_PREDEFINITA, help="porta della schermata (default %(default)s)")
    ap.add_argument("--progetti", help="cartella dei progetti nuovi")
    ap.add_argument("--browser", action="store_true", help="si apre nel browser anche se la finestra del programma è disponibile")
    ap.add_argument("--no-browser", action="store_true", help="non aprire niente (né finestra né browser)")
    ap.add_argument("--daemon", action="store_true", help="si stacca dal terminale/app che lo ha lanciato (Impaginatore.app sul Mac; non su Windows). Si apre nel browser")
    ap.add_argument("--versione", action="version", version=f"Impaginatore {__version__}")
    args = ap.parse_args(argv)
    finestra = not (args.no_browser or args.browser or args.daemon)          # T-201: la finestra del programma, se c'è (desktop.motore)
    if args.porta and not _porta_libera(args.porta):      # porta 0 = una libera qualsiasi
        indirizzo = f"http://127.0.0.1:{args.porta}/"
        if gia_aperto(args.porta):                         # già in funzione: basta aprire la pagina (con un indirizzo di avvio nuovo)
            print(f"Impaginatore è già aperto: {indirizzo}", flush=True)
            if args.no_browser: return 0
            a = sicurezza.indirizzo_avvio("home", args.porta)
            m = desktop.motore() if finestra and a else None
            if m: return desktop.ospite(m, a, args.porta)          # un'altra finestra sulla schermata in funzione
            processi.apri_browser(a or indirizzo)
            return 0
        print(f"La porta {args.porta} è occupata da un altro programma: scegline un'altra con --porta", file=sys.stderr)
        return 1
    configura(args.progetti, args.porta)
    if args.daemon: processi.stacca(os.path.join(PROGETTI, "impaginatore.log"))       # doppio fork + nuova sessione: non muore quando l'app che l'ha lanciato si chiude
    giornale.configura("home")
    m = desktop.motore() if finestra else None             # None: manca pywebview o il motore del sistema (motivo nel registro): il browser come prima
    fermo = threading.Event()
    threading.Thread(target=AGGIORNAMENTI.ciclo, args=(fermo,), daemon=True).start()
    srv = crea_server(args.porta, desktop.gettone() if m else sicurezza.gettone_del_processo())
    indirizzo = f"http://127.0.0.1:{PORTA}/"
    print(f"Impaginatore: {indirizzo}  | progetti: {PROGETTI}", flush=True)
    if m: return desktop.esegui(m, srv, fermo)            # la finestra apre l'indirizzo di avvio dentro il processo; chiusa la finestra, si chiude tutto
    if not args.no_browser: apri_browser(srv.indirizzo_avvio())                    # anche con --daemon: l'indirizzo semplice che apre Impaginatore.app 1.x non basta più (SICUREZZA.md)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally: fermo.set(); srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
