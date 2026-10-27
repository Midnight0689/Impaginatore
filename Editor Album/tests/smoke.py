"""Prova automatica dell'editor: crea un progetto temporaneo, fa le operazioni principali, salva, riapre e confronta.

Uso:  ~/.album-tools/venv/bin/python tests/smoke.py --foto "/cartella/con/jpg"
Non tocca nessun progetto vero: tutto avviene in una cartella temporanea che alla fine viene tolta.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ED = os.path.dirname(HERE)
ap = argparse.ArgumentParser(); ap.add_argument("--foto", required=True); ap.add_argument("--n", type=int, default=6); ap.add_argument("--psd", action="store_true", help="prova anche i PSD (apre Photoshop: lento)"); a = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="smoke_"); procs = []; ok = []; ko = []

def call(port, path, body=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))

def prova(port, path, body):
    """come call(), ma restituisce (ok, risposta) anche quando il server risponde con un errore"""
    try: return True, call(port, path, body)
    except urllib.error.HTTPError as e:
        try: return False, json.load(e)
        except Exception: return False, {"errore": str(e)}

def esporta(P, **o):
    ok_, r = prova(P, "/api/export", o)
    if not ok_: return False, [r.get("errore", "")]
    for _ in range(600):
        L = call(P, "/api/log")
        if "[finito]" in L: return True, L
        time.sleep(0.5)
    return False, ["tempo scaduto"]

def check(nome, cond, extra=""):
    (ok if cond else ko).append(nome); print(("  ok   " if cond else "  ERRORE ") + nome + (f"  {extra}" if extra and not cond else ""), flush=True)

def start(args, port):
    p = subprocess.Popen([sys.executable] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(os.environ, IMPAGINATORE_PROGETTI=TMP)); procs.append(p)
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1); return p
        except Exception: time.sleep(0.5)
    raise SystemExit("server non partito")

try:
    start([os.path.join(ED, "home.py"), "--porta", "8791"], 8791)
    r = call(8791, "/api/nuovo", {"nome": "Smoke", "w": 30, "h": 30}); proj = r["path"]
    for f in sorted(x for x in os.listdir(a.foto) if x.lower().endswith(".jpg"))[: a.n]: shutil.copy(os.path.join(a.foto, f), os.path.join(proj, "Foto", f))
    ed = start([os.path.join(ED, "editor.py"), "--progetto", proj, "--porta", "8892"], 8892); P = 8892
    st = call(P, "/api/state"); names = [p["n"] for p in st["photos"]]
    import re, shutil, tempfile    # il codice della pagina deve almeno essere sintatticamente corretto (se manca node il controllo si salta)
    if shutil.which("node"):
        js = "\n".join(re.findall(r"<script>(.*?)</script>", open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html")).read(), re.S))
        tf = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False); tf.write(js); tf.close()
        r = subprocess.run(["node", "--check", tf.name], capture_output=True, text=True); os.unlink(tf.name)
        check("codice della pagina senza errori di sintassi", r.returncode == 0, r.stderr[:300])
    check("foto lette", len(names) == a.n, str(len(names)))
    def op(o):
        global st
        st = call(P, "/api/op", dict(cid="smoke", rev=st["rev"], **o)); return st
    t = call(P, "/api/templates", {"photos": names[:2]})["items"][0]
    op({"op": "newspread", "pos": 0, "L": t["L"], "R": t["R"]}); check("spread creato", len(st["spreads"]) == 1)
    t3 = call(P, "/api/templates", {"photos": names[2:5]})["items"][0]
    op({"op": "newspread", "pos": 1, "L": t3["L"], "R": t3["R"]}); check("secondo spread", len(st["spreads"]) == 2)
    op({"op": "addtext", "s": 0, "fx": 0.1, "fy": 0.1, "fw": 0.4, "fh": 0, "tx": "Prova"}); tx = [i for i in st["spreads"][0]["items"] if i.get("kind") == "txt"]
    check("testo aggiunto", len(tx) == 1)
    at = [0, tx[0]["side"], tx[0]["idx"]]
    op({"op": "settext", "at": at, "tx": "Ciao", "size": 150, "lh": 1.5, "caps": True, "tr": 40, "al": "center"}); tx = [i for i in st["spreads"][0]["items"] if i.get("kind") == "txt"][0]
    check("testo modificato", tx["tx"] == "Ciao" and tx["caps"] and tx["lh"] == 1.5 and tx["al"] == "center", str(tx))
    op({"op": "stella", "photo": names[0], "value": True}); check("preferita", any(p["n"] == names[0] and p["star"] for p in st["photos"]))
    img = urllib.request.urlopen(f"http://127.0.0.1:{P}/img/spread/0?k=0.05&h={st['spreads'][0]['h']}", timeout=60).read(); check("anteprima spread", len(img) > 2000, str(len(img)))
    check("annulla disponibile", st["canundo"])
    call(P, "/api/save", {}); time.sleep(0.5); st = call(P, "/api/state"); check("salvato", not st["dirty"] and not st.get("saveerr"))
    spec = open(os.path.join(proj, "spec.py")).read(); compile(spec, "spec.py", "exec"); check("spec.py valido", "TEXT(" in spec and "caps=True" in spec)
    check("nessun .tmp rimasto", not [f for f in os.listdir(proj) if f.endswith(".tmp")])
    json.load(open(os.path.join(proj, "progetto.json"))); check("progetto.json valido", True)
    before = json.dumps([[(i.get("kind"), i.get("tx"), i.get("name")) for i in sp["items"]] for sp in st["spreads"]])
    ed.terminate(); ed.wait(); time.sleep(1)
    start([os.path.join(ED, "editor.py"), "--progetto", proj, "--porta", "8893"], 8893); P = 8893; st = call(P, "/api/state")
    after = json.dumps([[(i.get("kind"), i.get("tx"), i.get("name")) for i in sp["items"]] for sp in st["spreads"]])
    check("riapertura identica", before == after); check("stella ricordata", any(p["star"] for p in st["photos"]))

    # ---- esportazione
    dj = os.path.join(TMP, "out_jpg"); okx, L = esporta(P, fmt="jpg", range="", dest=dj, res="bozza", q=80)
    jp = sorted(f for f in os.listdir(dj)) if os.path.isdir(dj) else []
    check("export JPG riuscito", okx and len(jp) == len(st["spreads"]) and any(x.startswith("RISULTATO:") for x in L), str(L[-3:]))
    try:
        from PIL import Image
        check("JPG si aprono", all(Image.open(os.path.join(dj, f)).size[0] > 100 for f in jp))
    except Exception as e: check("JPG si aprono", False, str(e))
    check("nessun .tmp nell'export", not [f for f in jp if f.endswith(".tmp")])
    dp = os.path.join(TMP, "out_pdf"); okx, L = esporta(P, fmt="pdf", range="", dest=dp, width=800, q=70, numeri=True)
    pdfs = [f for f in os.listdir(dp)] if os.path.isdir(dp) else []
    check("export PDF riuscito", okx and len(pdfs) == 1 and open(os.path.join(dp, pdfs[0]), "rb").read(5) == b"%PDF-", str(L[-3:]))
    okx, L = esporta(P, fmt="jpg", range="99", dest=dj, res="bozza"); check("spread inesistente rifiutato con messaggio", not okx and "inesistenti" in " ".join(L), str(L))
    okx, L = esporta(P, fmt="jpg", range="", dest="/System/Library/vietato", res="bozza"); check("cartella non scrivibile rifiutata", not okx and L and L[0], str(L))
    okx, L = esporta(P, fmt="gif", range="", dest=dj); check("formato sconosciuto rifiutato", not okx, str(L))
    # foto mancante: il messaggio deve dire quali
    f0 = os.path.join(proj, "Foto", [x for x in os.listdir(os.path.join(proj, "Foto")) if x.startswith(names[0])][0]); os.rename(f0, f0 + ".spostata")
    okx, L = esporta(P, fmt="jpg", range="1", dest=dj, res="bozza"); check("foto mancante segnalata prima di esportare", not okx and "non si trovano" in " ".join(L) and names[0] in " ".join(L), str(L))
    os.rename(f0 + ".spostata", f0)
    if a.psd:
        dpsd = os.path.join(TMP, "out_psd"); okx, L = esporta(P, fmt="psd", range="1", dest=dpsd, force=True)
        check("export PSD riuscito", okx and os.path.exists(os.path.join(dpsd, "Spread_01.psd")) and os.path.getsize(os.path.join(dpsd, "Spread_01.psd")) > 1e5, str(L[-6:]))
finally:
    for p in procs:
        try: p.terminate()
        except Exception: pass
    shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{len(ok)} ok, {len(ko)} errori"); sys.exit(1 if ko else 0)
