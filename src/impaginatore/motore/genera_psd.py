"""Genera i PSD degli spread in Photoshop dalla spec.

python genera_psd.py --progetto <cartella> [--spread 1,2,5 | tutti] [--forza]

Ogni spread = un PSD alla misura esatta di progetto.json, con:
- una cornice di Photoshop (strumento Cornice) per foto, con l'originale incorporato come oggetto avanzato e già ritagliato;
- sopra ogni cornice, agganciati: Esposizione (se diversa da 0), Bilanciamento bianco (se previsto), Bianco e nero (se BN);
- testi veri (titolo, firma finale); cartelle "Pagina sinistra" / "Pagina destra"; guida sulla piega.

PROTEZIONE MODIFICHE A MANO: salva l'ora di ogni PSD generato in _cache/psd_generati.json. Se un PSD è stato salvato
dopo (cioè l'utente lo ha sistemato a mano), NON lo sovrascrive e lo dice. Per quei file usa modifica_psd.py.
--forza sovrascrive comunque: usalo solo se l'utente lo chiede esplicitamente.
"""
import sys, os, json, argparse, time
from album import *
import photoshop as PS

ap = argparse.ArgumentParser(); ap.add_argument("--progetto"); ap.add_argument("--spread", default="tutti"); ap.add_argument("--forza", action="store_true")
a = ap.parse_args()
SP = load_spec()
OUT = CFG.get("uscita_psd") or os.path.join(PROJ, "PSD"); os.makedirs(OUT, exist_ok=True)
nums = list(range(1, len(SP) + 1)) if a.spread == "tutti" else [int(x) for x in a.spread.split(",")]
REG = os.path.join(CACHE, "psd_generati.json"); reg = json.load(open(REG)) if os.path.exists(REG) else {}

open_docs = PS.open_documents()
skip = []
for n in nums:
    fn = f"Spread_{n:02d}.psd"; p = os.path.join(OUT, fn)
    if any(d == fn for d, _ in open_docs): skip.append((n, "è aperto in Photoshop")); continue
    if os.path.exists(p) and not a.forza:
        if fn not in reg: skip.append((n, "esiste e non l'ho generato io")); continue
        if os.path.getmtime(p) > reg[fn] + 5: skip.append((n, "modificato a mano dopo la generazione")); continue
todo = [n for n in nums if n not in {s for s, _ in skip}]
for n, why in skip: print(f"SALTATO spread {n}: {why} -> usa modifica_psd.py o --forza se l'utente vuole davvero rigenerarlo")
if not todo: sys.exit(0)

T = CFG.get("testo", {})
txt = dict(nome=TITLE[0], sotto=TITLE[1], data=TITLE[2], serif=T.get("font_titolo_ps", "Didot-Italic"), sans=T.get("font_testo_ps", "AvenirNext-Regular"), ink=list(INK))
jobs = []
for n in todo:
    items = []
    for it in layout(SP[n - 1]):
        side = "sinistra" if it["side"] == "L" else "destra"
        if it["k"] == "t": items.append(dict(txt=it["kind"], x=it["x"], y=it["y"], w=it["W"], h=it["H"], side=side)); continue
        m = M[it["i"]]; l, t, r, b = zcrop(it); sc = it["W"] / ((r - l) * m["w"]); g = WB.get(name(it["i"]))
        items.append(dict(file=m["src"], name=name(it["i"]), side=side, x=it["x"], y=it["y"], w=it["W"], h=it["H"],
                          left=it["x"] - l * m["w"] * sc, top=it["y"] - t * m["h"] * sc, width=m["w"] * sc,
                          bw=bool(it.get("bw")), ev=ev_for(it["i"]), wb=[round(100 * x ** (1 / 2.2), 1) for x in g] if g else None))
    jobs.append(dict(n=n, items=items))

js = PS.JS_LIB + "var JOBS=" + json.dumps(jobs) + "; var G=" + json.dumps(dict(CW=CW, CH=CH, FOLD=FOLD, PPI=PPI)) + "; var OUT=" + json.dumps(OUT) + "; var TX=" + json.dumps(txt) + ";\n" + r"""
function addText(doc,it,ids){   // misure in px a 72 ppi (= pt), allineate alle anteprime
  var title = it.txt=="title";
  var L1 = title ? [TX.nome,TX.serif,380,0, it.x+it.w/2, it.y+it.h/2+82] : [TX.nome,TX.serif,170,0, it.x, it.y+it.h-247];
  var L2 = title ? [TX.sotto,TX.sans,62,355, it.x+it.w/2, it.y+it.h/2+307] : [TX.sotto,TX.sans,62,225, it.x+6, it.y+it.h-124];
  var L3 = title ? [TX.data,TX.sans,62,355, it.x+it.w/2, it.y+it.h/2+417] : [TX.data,TX.sans,62,225, it.x+6, it.y+it.h-34];
  var lines=[L1,L2,L3];
  for (var i=0;i<3;i++){ var q=lines[i]; if(!q[0]) continue;
    var L=doc.artLayers.add(); L.kind=LayerKind.TEXT; var ti=L.textItem; ti.contents=q[0]; ti.font=q[1]; ti.size=new UnitValue(q[2],"pt"); ti.tracking=q[3];
    var c=new SolidColor(); c.rgb.red=TX.ink[0]; c.rgb.green=TX.ink[1]; c.rgb.blue=TX.ink[2]; ti.color=c;
    ti.justification = title ? Justification.CENTER : Justification.LEFT; ti.position=[px(q[4]),px(q[5])]; L.name="Testo - "+q[0]; ids.push(L.id); }
}
var log=[]; var STEP="start";
for (var j=0;j<JOBS.length;j++){
 try {
  var job=JOBS[j]; var nm="Spread_"+(job.n<10?"0":"")+job.n;
  var doc=app.documents.add(G.CW,G.CH,72,nm,NewDocumentMode.RGB,DocumentFill.WHITE);   // si costruisce a 72 ppi (px = pt), poi ppi finali senza ricampionare
  doc.guides.add(Direction.VERTICAL,px(G.FOLD));
  var ids={sinistra:[],destra:[]};
  for (var i=job.items.length-1;i>=0;i--){
    var it=job.items[i]; if (it.txt) continue; selectNone();
    STEP="cornice "+it.name; makeFrame(it.x,it.y,it.x+it.w,it.y+it.h); var FR=doc.activeLayer;
    STEP="foto "+it.name; placeIntoFrame(it.file); var L=doc.activeLayer; fitLayer(L,it.left,it.top,it.width); L.name=it.name;
    FR=(L.parent && L.parent.typename=="LayerSet") ? L.parent : FR; FR.name=it.name; ids[it.side].push(FR.id);
    var top=FR;
    if (it.ev) { doc.activeLayer=top; top=exposureAdjustment(it.ev); ids[it.side].push(top.id); }
    if (it.wb) { doc.activeLayer=top; top=wbAdjustment(it.wb); ids[it.side].push(top.id); }
    if (it.bw) { doc.activeLayer=top; top=bwAdjustment(); ids[it.side].push(top.id); }
  }
  for (var i=0;i<job.items.length;i++){ var it=job.items[i]; if (!it.txt) continue; STEP="testo"; selectNone(); addText(doc,it,ids[it.side]); }
  STEP="gruppi"; selectNone(); groupIds(ids.destra,"Pagina destra"); groupIds(ids.sinistra,"Pagina sinistra");
  STEP="risoluzione"; doc.resizeImage(undefined,undefined,G.PPI,ResampleMethod.NONE);
  STEP="salva"; var o=new PhotoshopSaveOptions(); o.layers=true; o.embedColorProfile=true; o.maximizeCompatibility=true;
  doc.saveAs(new File(OUT+"/"+nm+".psd"),o,true); doc.close(SaveOptions.DONOTSAVECHANGES);
  log.push(nm+" ok");
 } catch(e) { log.push("ERRORE "+nm+" "+STEP+": "+e+" (riga "+e.line+")"); try{ app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);}catch(_){} }
}
log.join("\n");
"""
jsx = os.path.join(CACHE, "genera.jsx"); PS.write_jsx(jsx, js)
for k in range(0, len(todo), 6):     # a gruppi: Photoshop regge meglio e l'errore di uno non ferma gli altri
    part = [j for j in jobs if j["n"] in todo[k:k + 6]]
    PS.write_jsx(jsx, js.replace("var JOBS=" + json.dumps(jobs), "var JOBS=" + json.dumps(part)))
    out = PS.run_jsx(jsx); print(out)
    for line in out.splitlines():
        if line.endswith(" ok"):
            fn = line.split()[0] + ".psd"; reg[fn] = os.path.getmtime(os.path.join(OUT, fn))
json.dump(reg, open(REG, "w"), indent=1)
print("Ora: python verifica_psd.py --progetto", PROJ)
