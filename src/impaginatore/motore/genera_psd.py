"""Genera i PSD degli spread in Photoshop dall'impaginazione del progetto.

python -m impaginatore.motore.genera_psd --progetto <cartella> [--spread 1,2,5 | tutti] [--forza]

Ogni spread = un PSD alla misura esatta di progetto.json, con:
- una cornice di Photoshop (strumento Cornice) per foto, con l'originale incorporato come oggetto avanzato e già ritagliato;
- sopra ogni cornice, agganciati: Esposizione (se diversa da 0), Bilanciamento bianco (se previsto), Bianco e nero (se BN);
- testi veri (titolo, firma finale); cartelle "Pagina sinistra" / "Pagina destra"; guida sulla piega.

PROTEZIONE MODIFICHE A MANO: salva l'ora di ogni PSD generato in _cache/psd_generati.json. Se un PSD è stato salvato
dopo (cioè l'utente lo ha sistemato a mano), NON lo sovrascrive e lo dice. Per quei file usa modifica_psd.py.
--forza sovrascrive comunque: usalo solo se l'utente lo chiede esplicitamente.

Punti di estensione: lo script JavaScript ha delle parti con nome (PARTI) che genera_psd_angolo sostituisce con le sue
(angoli, tono, ritocco, bordi, livelli di testo, profilo sRGB); con estesa=True anche le voci delle foto e dei testi
portano i dati che servono a quelle parti. Niente codice viene modificato come testo o eseguito con exec.
"""
import sys, os, json, argparse, re

from .. import lingua

MOTIVI = dict(aperto="motore.psd_aperto", esiste="motore.psd_esiste", modificato="motore.psd_modificato")      # codice del motivo -> chiave del testo
PROTOCOLLO_SALTATO = re.compile(r"@@SALTATO (\d+) (" + "|".join(MOTIVI) + ")$")                              # riga di protocollo per il server dell'editor: indipendente dalla lingua

TESTO_JS = '''  var L1 = title ? [TX.nome,TX.serif,380,0, it.x+it.w/2, it.y+it.h/2+82] : [TX.nome,TX.serif,170,0, it.x, it.y+it.h-247];
  var L2 = title ? [TX.sotto,TX.sans,62,355, it.x+it.w/2, it.y+it.h/2+307] : [TX.sotto,TX.sans,62,225, it.x+6, it.y+it.h-124];
  var L3 = title ? [TX.data,TX.sans,62,355, it.x+it.w/2, it.y+it.h/2+417] : [TX.data,TX.sans,62,225, it.x+6, it.y+it.h-34];'''
PARTI = dict(TESTO=TESTO_JS, INIZIO='var log=[]; var STEP="start";', NUOVO_DOC='var doc=app.documents.add(G.CW,G.CH,72,nm,NewDocumentMode.RGB,DocumentFill.WHITE);',
             ANGOLO="", STILE="", TONO="", AGGIUNGI_TESTO="addText")
SCRIPT_JS = r"""
function addText(doc,it,ids){   // misure in px a 72 ppi (= pt), allineate alle anteprime
  var title = it.txt=="title";
@@TESTO@@
  var lines=[L1,L2,L3];
  for (var i=0;i<3;i++){ var q=lines[i]; if(!q[0]) continue;
    var L=doc.artLayers.add(); L.kind=LayerKind.TEXT; var ti=L.textItem; ti.contents=q[0]; ti.font=q[1]; ti.size=new UnitValue(q[2],"pt"); ti.tracking=q[3];
    var c=new SolidColor(); c.rgb.red=TX.ink[0]; c.rgb.green=TX.ink[1]; c.rgb.blue=TX.ink[2]; ti.color=c;
    ti.justification = title ? Justification.CENTER : Justification.LEFT; ti.position=[px(q[4]),px(q[5])]; L.name="Testo - "+q[0]; ids.push(L.id); }
}
@@INIZIO@@
for (var j=0;j<JOBS.length;j++){
 try {
  var job=JOBS[j]; var nm="Spread_"+(job.n<10?"0":"")+job.n;
  @@NUOVO_DOC@@   // si costruisce a 72 ppi (px = pt), poi ppi finali senza ricampionare
  doc.guides.add(Direction.VERTICAL,px(G.FOLD));
  var ids={sinistra:[],destra:[]};
  for (var i=job.items.length-1;i>=0;i--){
    var it=job.items[i]; if (it.txt) continue; selectNone();
    STEP="cornice "+it.name; makeFrame(it.x,it.y,it.x+it.w,it.y+it.h); var FR=doc.activeLayer;
    STEP="foto "+it.name; placeIntoFrame(it.file); var L=doc.activeLayer; fitLayer(L,it.left,it.top,it.width); @@ANGOLO@@L.name=it.name;
    FR=(L.parent && L.parent.typename=="LayerSet") ? L.parent : FR; FR.name=it.name; ids[it.side].push(FR.id);
    @@STILE@@var top=FR;
    if (it.ev) { doc.activeLayer=top; top=exposureAdjustment(it.ev); ids[it.side].push(top.id); }
    if (it.wb) { doc.activeLayer=top; top=wbAdjustment(it.wb); ids[it.side].push(top.id); }
    @@TONO@@if (it.bw) { doc.activeLayer=top; top=bwAdjustment(); ids[it.side].push(top.id); }
  }
  for (var i=0;i<job.items.length;i++){ var it=job.items[i]; if (!it.txt) continue; STEP="testo"; selectNone(); @@AGGIUNGI_TESTO@@(doc,it,ids[it.side]); }
  STEP="gruppi"; selectNone(); groupIds(ids.destra,"Pagina destra"); groupIds(ids.sinistra,"Pagina sinistra");
  STEP="risoluzione"; doc.resizeImage(undefined,undefined,G.PPI,ResampleMethod.NONE);
  STEP="salva"; var o=new PhotoshopSaveOptions(); o.layers=true; o.embedColorProfile=true; o.maximizeCompatibility=true;
  doc.saveAs(new File(OUT+"/"+nm+".psd"),o,true); doc.close(SaveOptions.DONOTSAVECHANGES);
  log.push(nm+" ok");
 } catch(e) { log.push("ERRORE "+nm+" "+STEP+": "+e+" (riga "+e.line+")"); try{ app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);}catch(_){} }
}
log.join("\n");
"""


def script_js(parti=None):
    """corpo dello script (dopo i dati): le parti con nome sono quelle di PARTI, o quelle date (stesse chiavi)"""
    parti = dict(PARTI, **(parti or {}))
    js = SCRIPT_JS
    for k, v in parti.items(): js = js.replace(f"@@{k}@@", v)
    return js


def voce_testo(it, side, estesa=False):
    """un testo dello spread per lo script (titolo, firma; con estesa anche i livelli di testo e la scala)"""
    from . import testo
    d = dict(txt=it["kind"])
    if estesa: d.update(ts=float(it.get("ts") or 1), X=(testo.job_x(it) if it["kind"] == "txt" else None))
    d.update(x=it["x"], y=it["y"], w=it["W"], h=it["H"], side=side)
    return d


def voce_foto(it, side, estesa=False):
    """una foto dello spread per lo script: file, cornice, posizione dell'originale, correzioni (con estesa: angolo, tono,
    ritocco, bordo/ombra e bianco totale)"""
    from . import album as A
    from . import album_libere as L
    m = A.M[it["i"]]; l, t, r, b = A.zcrop(it); sc = it["W"] / ((r - l) * m["w"]); g = L.wb_total(it["i"]) if estesa else A.WB.get(A.name(it["i"]))
    d = dict(file=m["src"], name=A.name(it["i"]), side=side, x=it["x"], y=it["y"], w=it["W"], h=it["H"],
             left=it["x"] - l * m["w"] * sc, top=it["y"] - t * m["h"] * sc, width=m["w"] * sc, bw=bool(it.get("bw")))
    if estesa: d["ang"] = float(it.get("a") or 0)
    d["ev"] = A.ev_for(it["i"])
    if estesa: d.update(tono=L.tono_job(it["i"]), rit=L.rit_job(it["i"]), sty=L.sty_job(it))
    d["wb"] = [round(100 * x ** (1 / 2.2), 1) for x in g] if g else None
    return d


def _registro(path):
    """ora di generazione di ogni PSD ({nome file: mtime}); un registro rovinato vale come vuoto (allora nessun PSD
    esistente si sovrascrive senza --forza)"""
    from .. import formato
    try: reg = formato.leggi_json(path) if os.path.exists(path) else {}
    except (OSError, ValueError) as e: print(lingua.t("motore.psd_registro_illeggibile", motivo=e), flush=True); return {}
    if not isinstance(reg, dict): return {}
    return {k: v for k, v in reg.items() if isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)}


def main(argv=None, parti=None, estesa=False):
    """genera i PSD (argomenti come da riga di comando). parti/estesa: vedi genera_psd_angolo"""
    from .. import formato
    from . import album as A
    from . import photoshop as PS
    argv = sys.argv[1:] if argv is None else list(argv)
    A.carica_progetto(A.progetto_da_argv(argv))      # --progetto, ALBUM_PROGETTO o cartella corrente (come nelle 1.x)
    ap = argparse.ArgumentParser(); ap.add_argument("--progetto"); ap.add_argument("--spread", default="tutti"); ap.add_argument("--forza", action="store_true")
    a = ap.parse_args(argv)
    SP = A.load_spec()
    OUT = A.CFG.get("uscita_psd") or os.path.join(A.PROJ, "PSD"); os.makedirs(OUT, exist_ok=True)
    nums = list(range(1, len(SP) + 1)) if a.spread == "tutti" else [int(x) for x in a.spread.split(",")]
    REG = os.path.join(A.CACHE, "psd_generati.json"); reg = _registro(REG)

    open_docs = PS.open_documents()
    skip = []
    for n in nums:
        fn = f"Spread_{n:02d}.psd"; p = os.path.join(OUT, fn)
        if any(d == fn for d, _ in open_docs): skip.append((n, "aperto")); continue
        if os.path.exists(p) and not a.forza:
            if fn not in reg: skip.append((n, "esiste")); continue
            if os.path.getmtime(p) > reg[fn] + 5: skip.append((n, "modificato")); continue
    todo = [n for n in nums if n not in {s for s, _ in skip}]
    for n, codice in skip:
        if os.environ.get("IMPAGINATORE_PROTOCOLLO"): print(f"@@SALTATO {n} {codice}")      # per il server dell'editor (lo lancia con questa variabile): niente testo, solo il codice
        print(lingua.t("motore.psd_saltato", n=n, motivo=lingua.t(MOTIVI[codice])))
    if not todo: return 0

    T = A.CFG.get("testo", {})
    txt = dict(nome=A.TITLE[0], sotto=A.TITLE[1], data=A.TITLE[2], serif=T.get("font_titolo_ps", "Didot-Italic"), sans=T.get("font_testo_ps", "AvenirNext-Regular"), ink=list(A.INK))
    jobs = []
    for n in todo:
        items = []
        for it in A.layout(SP[n - 1]):
            side = "sinistra" if it["side"] == "L" else "destra"
            items.append(voce_testo(it, side, estesa) if it["k"] == "t" else voce_foto(it, side, estesa))
        jobs.append(dict(n=n, items=items))

    js = PS.JS_LIB + "var JOBS=" + json.dumps(jobs) + "; var G=" + json.dumps(dict(CW=A.CW, CH=A.CH, FOLD=A.FOLD, PPI=A.PPI)) + "; var OUT=" + json.dumps(OUT) + "; var TX=" + json.dumps(txt) + ";\n" + script_js(parti)
    jsx = os.path.join(A.CACHE, "genera.jsx"); PS.write_jsx(jsx, js)
    for k in range(0, len(todo), 6):     # a gruppi: Photoshop regge meglio e l'errore di uno non ferma gli altri
        part = [j for j in jobs if j["n"] in todo[k:k + 6]]
        PS.write_jsx(jsx, js.replace("var JOBS=" + json.dumps(jobs), "var JOBS=" + json.dumps(part)))
        out = PS.run_jsx(jsx); print(out)
        for line in out.splitlines():
            if line.endswith(" ok"):
                fn = line.split()[0] + ".psd"; reg[fn] = os.path.getmtime(os.path.join(OUT, fn))
    formato.scrivi_json(REG, reg, indent=1)
    print(lingua.t("motore.psd_verifica", progetto=A.PROJ))
    return 0


if __name__ == "__main__":
    main()
