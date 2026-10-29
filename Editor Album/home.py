#!/usr/bin/env python
"""Schermata iniziale dei progetti (come quella di Smart Albums) + avvio dell'editor del progetto scelto.

    python home.py [--porta 8765]

I nuovi progetti stanno in  <cartella del programma>/Progetti/<nome>/  (progetto.json + spec.py + Foto/ + _cache/).
Quella cartella È il file di salvataggio del progetto: l'editor la salva da solo mentre lavori.
Progetti che stanno altrove (es. sul Desktop) si aggiungono con «Apri progetto esistente»: restano dove sono.
Solo libreria standard: l'editor vero (editor.py) parte come processo a parte, uno per progetto aperto.
"""
import argparse, json, os, re, shutil, socket, subprocess, sys, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ap = argparse.ArgumentParser()
ap.add_argument("--porta", type=int, default=8765)
ap.add_argument("--daemon", action="store_true", help="si stacca dal terminale/app che lo ha lanciato (serve a Impaginatore.app)")
ARGS = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
PROGETTI = os.path.abspath(os.path.expanduser(os.environ.get("IMPAGINATORE_PROGETTI") or os.path.join(BASE, "Progetti")))
REG = os.path.join(PROGETTI, "registro.json")
PY = os.path.expanduser("~/.album-tools/venv/bin/python")
if not os.path.exists(PY): PY = sys.executable
os.makedirs(PROGETTI, exist_ok=True)
LOCK = threading.Lock()
EDITORS = {}                                   # percorso progetto -> (Popen, porta)


def registro():
    try: return [p for p in json.load(open(REG)) if os.path.exists(os.path.join(p, "progetto.json"))]
    except Exception: return []


def salva_registro(lst): json.dump(sorted(set(lst)), open(REG, "w"), indent=1)


def progetti():
    out = []
    paths = [os.path.join(PROGETTI, d) for d in sorted(os.listdir(PROGETTI)) if os.path.exists(os.path.join(PROGETTI, d, "progetto.json"))] + registro()
    for p in dict.fromkeys(paths):
        try:
            cfg = json.load(open(os.path.join(p, "progetto.json")))
            spec = os.path.join(p, "spec.py"); nsp = len(re.findall(r"^\s*# \d+\s*$", open(spec).read(), re.M)) if os.path.exists(spec) else 0
            meta = os.path.join(p, "_cache", "meta.json"); nf = len(json.load(open(meta))) if os.path.exists(meta) else 0
            cover = None
            if nf:
                first = json.load(open(meta))[0]["n"]
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
    nome = (d.get("nome") or "").strip()
    if not nome: raise ValueError("Scrivi il nome del progetto")
    w, h = num(d.get("w")), num(d.get("h"))
    if not (5 <= w <= 300 and 5 <= h <= 200): raise ValueError("Misure fuori dal normale: larghezza 5–300 cm, altezza 5–200 cm")
    cartella = re.sub(r'[\\/:*?"<>|]', "-", nome).strip(" .") or "Progetto"
    fotodir = (d.get("foto") or "").strip().rstrip("/")
    if fotodir:                                          # progetto accanto alle foto del cliente: <cartella cliente>/Impaginatore, le foto restano dove sono
        if not os.path.isdir(fotodir): raise ValueError("La cartella delle foto non esiste")
        base, cartella = os.path.dirname(fotodir), "Impaginatore"
    else: base = PROGETTI
    p = os.path.join(base, cartella); k = 2
    while os.path.exists(p): p = os.path.join(base, f"{cartella} {k}"); k += 1
    os.makedirs(p if fotodir else os.path.join(p, "Foto"))
    mm = lambda key, dflt: float(str(d.get(key, dflt)).replace(",", ".") or dflt)
    cfg = dict(nome=nome, foto=fotodir or os.path.join(p, "Foto"), foto_extra=[], tolte=[], formato_cm=[round(w, 2), round(h, 2)], dimensioni_esatte=False, ppi=300,
               abbondanza_mm=mm("abb", 0), spazio_mm=mm("spazio", 2.5), margine_mm=mm("margine", 10), uscita_psd=os.path.join(p, "PSD"),
               testo=dict(nome=nome, sottotitolo="", data=""), esposizione=dict(globale=0.0, per_cartella={}, per_foto={}), bilanciamento_bianco={}, centri_volto={})
    json.dump(cfg, open(os.path.join(p, "progetto.json"), "w"), indent=2, ensure_ascii=False)
    if fotodir: salva_registro(registro() + [p])
    open(os.path.join(p, "spec.py"), "w").write(f'"""{nome}: 0 spread."""\nfrom album import *\n\nSPREADS = [\n]\n')
    return p


def porta_libera(pref=None):
    for pt in ([pref] if pref else []) + list(range(8801, 8900)):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", pt)) != 0: return pt
    raise RuntimeError("nessuna porta libera")


def porta_stabile(path):
    """ogni progetto ha SEMPRE la stessa porta (così l'indirizzo non cambia e ricaricare la pagina funziona dopo un riavvio)"""
    import zlib
    return 8801 + zlib.crc32(path.encode()) % 99


def gia_attivo(path):
    """porta di un editor di questo progetto già in funzione (anche se non lanciato da qui), altrimenti None"""
    for pt in [porta_stabile(path)] + list(range(8801, 8900)):
        try:
            with socket.socket() as s:
                s.settimeout(.2)
                if s.connect_ex(("127.0.0.1", pt)) != 0: continue
            d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{pt}/api/ping", timeout=1))
            if d.get("path") == path: return pt
        except Exception: pass
    return None


def pronto(pt):
    try: return urllib.request.urlopen(f"http://127.0.0.1:{pt}/api/ping", timeout=1).status == 200
    except Exception: return False


def apri(path):
    path = os.path.abspath(path)
    if path not in [p["path"] for p in progetti()]: raise ValueError("progetto non in elenco")
    with LOCK:
        e = EDITORS.get(path)
        if e and e[0].poll() is None: return e[1]
        pt = gia_attivo(path)
        if pt: return pt
        pt = porta_libera(porta_stabile(path))
        log = open(os.path.join(PROGETTI, "editor.log"), "a")
        proc = subprocess.Popen([PY, os.path.join(HERE, "editor.py"), "--progetto", path, "--porta", str(pt), "--home", f"http://127.0.0.1:{ARGS.porta}"],
                                stdout=log, stderr=subprocess.STDOUT, cwd=HERE)
        EDITORS[path] = (proc, pt); return pt


def importa_zip():
    """sceglie un file .zip di progetto esportato, lo apre in <Progetti>/ e lo mette in elenco; restituisce la cartella ('' se annullato)"""
    import zipfile
    r = subprocess.run(["osascript", "-e", 'POSIX path of (choose file of type {"public.zip-archive"} with prompt "Scegli il file ZIP del progetto")'], capture_output=True, text=True)
    zp = r.stdout.strip() if r.returncode == 0 else ""
    if not zp: return ""
    tmp = os.path.join(PROGETTI, ".importazione"); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    try:
        with zipfile.ZipFile(zp) as z: z.extractall(tmp)
        cand = [tmp] + [os.path.join(tmp, d) for d in sorted(os.listdir(tmp)) if os.path.isdir(os.path.join(tmp, d))]
        src = next((c for c in cand if os.path.exists(os.path.join(c, "progetto.json"))), None)
        if not src: raise ValueError("Nel file ZIP non c'è un progetto (manca progetto.json)")
        nome = re.sub(r'[\\/:*?"<>|]', "-", os.path.basename(src) if src != tmp else os.path.splitext(os.path.basename(zp))[0]).strip(" .") or "Progetto"
        p = os.path.join(PROGETTI, nome); k = 2
        while os.path.exists(p): p = os.path.join(PROGETTI, f"{nome} {k}"); k += 1
        shutil.move(src, p); return p
    finally: shutil.rmtree(tmp, ignore_errors=True)


def scegli_cartella(msg="Scegli la cartella del progetto (quella con progetto.json)"):
    r = subprocess.run(["osascript", "-e", f'POSIX path of (choose folder with prompt "{msg}")'], capture_output=True, text=True)
    return r.stdout.strip().rstrip("/") if r.returncode == 0 else ""


AGG = dict(da_aggiornare=False, novita=[], controllato=0, errore="", attuale=None, ultima=None)


def _git(*a, t=30):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(["git", "-C", BASE, *a], capture_output=True, text=True, timeout=t, env=env)


def info_versione(rif):
    """numero progressivo (commit), codice breve, data e titolo di una versione (rif = HEAD oppure @{u})"""
    try:
        n = _git("rev-list", "--count", rif).stdout.strip()
        h, d, t = (_git("log", "-1", "--pretty=%h|%cd|%s", "--date=format:%d/%m/%Y %H:%M", rif).stdout.strip().split("|", 2) + ["", ""])[:3]
        rel = _git("show", f"{rif}:VERSION").stdout.strip()       # numero di rilascio (maggiore.minore.correzione), file VERSION nella radice
        return dict(n=int(n), codice=h, data=d, titolo=t, rel=rel)
    except Exception: return None


def elenco_versioni(k=20):
    out = _git("log", f"-{k}", "--pretty=%h|%cd|%s", "--date=format:%d/%m/%Y %H:%M").stdout.strip().splitlines()
    tot = int(_git("rev-list", "--count", "HEAD").stdout.strip() or 0)
    return [dict(n=tot - i, codice=r.split("|", 2)[0], data=r.split("|", 2)[1], titolo=r.split("|", 2)[2], attuale=i == 0) for i, r in enumerate(out)]


def ripristina_versione(codice):
    """riporta il programma allo stato di una versione precedente CREANDO una nuova versione (la storia non si perde, gli altri Mac la ricevono come un normale aggiornamento)"""
    if not re.fullmatch(r"[0-9a-f]{7,40}", codice or ""): raise ValueError("versione non valida")
    if _git("status", "--porcelain", "--untracked-files=no").stdout.strip(): raise ValueError("Ci sono modifiche del programma non ancora salvate: chiedi a Claude di salvarle prima")
    n = _git("rev-list", "--count", codice).stdout.strip()
    if _git("read-tree", "-u", "--reset", codice).returncode != 0: raise ValueError("Ripristino non riuscito")
    _git("-c", "user.name=Impaginatore", "-c", "user.email=impaginatore@local", "commit", "-q", "--allow-empty", "-m", f"Ripristino alla versione {n} ({codice})")
    p = _git("push", "-q", t=60)
    setup = os.path.join(BASE, "motore", "scripts", "setup.sh")
    if os.path.exists(setup):
        r = subprocess.run(["zsh", setup], capture_output=True, text=True, timeout=900)
        if r.returncode != 0: raise ValueError("Novità scaricate, ma l'ambiente Python non è pronto (" + ((r.stderr or r.stdout).strip().splitlines() or ["errore"])[-1][:200] + "). Il programma resta com'è: lancia Installa.command per sistemarlo.")
    riavvia_programma()
    return dict(n=n, caricato=p.returncode == 0)


def controlla_aggiornamenti():
    """confronta questa versione con quella su GitHub (solo lettura: fetch + confronto); mai pull da solo"""
    try:
        if not os.path.isdir(os.path.join(BASE, ".git")): return
        AGG.update(attuale=info_versione("HEAD"))
        f = _git("fetch", "-q", "origin")
        if f.returncode != 0: AGG.update(errore=(f.stderr or "")[:200], controllato=time.time()); return
        n = _git("log", "--pretty=%s", "HEAD..@{u}").stdout.strip().splitlines()
        AGG.update(da_aggiornare=bool(n), novita=n[:12], ultima=info_versione("@{u}"), controllato=time.time(), errore="")
    except Exception as e: AGG.update(errore=str(e)[:200], controllato=time.time())


def ciclo_aggiornamenti():
    while True:
        controlla_aggiornamenti(); time.sleep(3 * 3600)


def riavvia_programma():
    if os.environ.get("IMPAGINATORE_SENZA_RIAVVIO"): return                       # solo per le prove
    app = os.path.join(BASE, "Impaginatore.app")
    def riavvia():
        time.sleep(.6)
        for pr, _ in EDITORS.values():
            try: pr.terminate()
            except Exception: pass
        subprocess.Popen(["/bin/sh", "-c", f'sleep 1.5; open "{app}"'], start_new_session=True)
        os._exit(0)
    threading.Thread(target=riavvia, daemon=True).start()


def aggiorna_programma():
    """pull + ripristino ambiente + riavvio del programma (i progetti sono già salvati: l'editor salva da solo)"""
    for pr, _ in list(EDITORS.values()):
        try: pr.poll()
        except Exception: pass
    r = _git("pull", "--ff-only", t=120)
    if r.returncode != 0: raise ValueError("Aggiornamento non riuscito: " + (r.stderr or r.stdout)[:300])
    setup = os.path.join(BASE, "motore", "scripts", "setup.sh")
    if os.path.exists(setup): subprocess.run(["zsh", setup], capture_output=True, timeout=900)
    riavvia_programma()
    return True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, body, ctype="application/json", code=200):
        if isinstance(body, (dict, list)): body = json.dumps(body).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store" if ctype != "image/jpeg" else "max-age=600"); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        try:
            if u.path == "/": self.send(open(os.path.join(HERE, "home.html"), "rb").read(), "text/html; charset=utf-8")
            elif u.path == "/api/ping": self.send({"ok": True})
            elif u.path == "/api/progetti": self.send(dict(progetti=progetti(), cartella=PROGETTI))
            elif u.path == "/api/aggiornamento": self.send(AGG)
            elif u.path == "/api/versioni": self.send({"versioni": elenco_versioni()})
            elif u.path == "/api/pronto": self.send({"pronto": pronto(int(q["porta"][0]))})
            elif u.path == "/api/cover":
                p = q["path"][0]; n = q["n"][0]
                if p not in [x["path"] for x in progetti()] or "/" in n: raise ValueError("no")
                self.send(open(os.path.join(p, "_cache", "thumbs", n), "rb").read(), "image/jpeg")
            else: self.send({"errore": "non trovato"}, code=404)
        except Exception as e: self.send({"errore": str(e)}, code=400)

    def do_POST(self):
        u = urlparse(self.path); n = int(self.headers.get("Content-Length", 0)); d = json.loads(self.rfile.read(n) or b"{}")
        try:
            if u.path == "/api/nuovo": self.send({"path": nuovo(d)})
            elif u.path == "/api/apri": self.send({"porta": apri(d["path"])})
            elif u.path == "/api/aggiungi":
                p = scegli_cartella()
                if not p: self.send({"annullato": True}); return
                if not os.path.exists(os.path.join(p, "progetto.json")): raise ValueError("In quella cartella non c'è progetto.json: scegli la cartella del progetto")
                salva_registro(registro() + [p]); self.send({"path": p})
            elif u.path == "/api/scegli-foto":
                self.send({"path": scegli_cartella("Scegli la cartella con le foto del cliente")})
            elif u.path == "/api/aggiorna": self.send({"ok": aggiorna_programma()})
            elif u.path == "/api/ripristina": self.send(ripristina_versione(d.get("codice")))
            elif u.path == "/api/controlla": controlla_aggiornamenti(); self.send(AGG)
            elif u.path == "/api/importa-zip":
                p = importa_zip(); self.send({"path": p} if p else {"annullato": True})
            elif u.path == "/api/rimuovi":
                salva_registro([p for p in registro() if p != d["path"]]); self.send({"ok": True})
            elif u.path == "/api/cestino":
                p = os.path.abspath(d["path"])
                if not p.startswith(PROGETTI + os.sep): raise ValueError("Solo i progetti creati qui si possono mettere nel Cestino")
                subprocess.run(["osascript", "-e", f'tell application "Finder" to delete POSIX file "{p}"'], check=True, capture_output=True); self.send({"ok": True})
            elif u.path == "/api/finder": subprocess.run(["open", "-R", d["path"]]); self.send({"ok": True})
            elif u.path == "/api/esci":
                self.send({"ok": True})
                for pr, _ in EDITORS.values():
                    try: pr.terminate()
                    except Exception: pass
                threading.Thread(target=lambda: (time.sleep(.4), os._exit(0)), daemon=True).start()
            else: self.send({"errore": "non trovato"}, code=404)
        except Exception as e: self.send({"errore": str(e)}, code=400)


if __name__ == "__main__":
    if ARGS.daemon:                                      # doppio fork + nuova sessione: non muore quando l'app che l'ha lanciato si chiude
        if os.fork(): os._exit(0)
        os.setsid()
        if os.fork(): os._exit(0)
        fd = os.open(os.path.join(PROGETTI, "impaginatore.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND); dn = os.open(os.devnull, os.O_RDONLY)
        os.dup2(dn, 0); os.dup2(fd, 1); os.dup2(fd, 2)
    threading.Thread(target=ciclo_aggiornamenti, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.porta), H)
    print(f"Impaginatore: http://127.0.0.1:{ARGS.porta}  | progetti: {PROGETTI}", flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
