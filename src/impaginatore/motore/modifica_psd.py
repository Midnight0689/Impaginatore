"""Modifiche dirette ai PSD (quelli che l'utente ha già sistemato a mano): tocca solo ciò che serve, il resto resta com'è.
Prima di salvare fa SEMPRE una copia di sicurezza in <PSD>/../PSD_vecchi/backup_<data-ora>/.

python modifica_psd.py --progetto P scambia 4:_DSC3457 5:_DSC3513        scambia due foto tra cornici (anche tra spread diversi);
                                                                          l'esposizione regolata segue la foto, il BN resta alla cornice
python modifica_psd.py --progetto P sostituisci 23:_DSC8801 _DSC9355     mette un'altra foto nella cornice (la foto deve essere in
                                                                          Selezione Alta o in "foto_extra" di progetto.json)
python modifica_psd.py --progetto P colore 15:_DSC0299                    toglie il Bianco e nero
python modifica_psd.py --progetto P bn 15:_DSC0299                        aggiunge il Bianco e nero
python modifica_psd.py --progetto P esposizione 4:_DSC3674 0.95           imposta l'esposizione
python modifica_psd.py --progetto P rifai-pagina 9 sinistra               ricostruisce SOLO quella pagina dalla spec attuale
                                                                          (aggiorna prima spec.py), l'altra pagina non si tocca

Dopo ogni modifica: verifica_psd.py e un'esportazione di controllo da guardare.
"""
import sys, os, json, time, shutil, glob
from album import *
import photoshop as PS
from psd_tools import PSDImage

args = [x for x in sys.argv[1:] if x != "--progetto" and os.path.abspath(x) != PROJ]
if not args: print(__doc__); sys.exit(0)
cmd = args[0]
OUT = CFG.get("uscita_psd") or os.path.join(PROJ, "PSD")
REG = os.path.join(CACHE, "psd_generati.json")
def psd_path(n): return os.path.join(OUT, f"Spread_{int(n):02d}.psd")
def ref(s): n, nm = s.split(":"); return int(n), nm
def frames(n):
    """{nome cornice: (x0,y0,x1,y1)} letto dal PSD, ed esposizione attuale per nome"""
    psd = PSDImage.open(psd_path(n)); Wd, Hd = psd.size; fr, ev = {}, {}
    for g in psd:
        if not g.is_group(): continue
        ls = list(g)
        for k, L in enumerate(ls):
            if L.is_group() and L.has_vector_mask():
                pts = [(q.anchor[1] * Wd, q.anchor[0] * Hd) for p in L.vector_mask.paths for q in p]
                fr[L.name] = tuple(round(v) for v in (min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)))
                for q in ls[k + 1:]:
                    if not q.clipping: break
                    if q.kind == "exposure": ev[L.name] = round(q.exposure, 2)
    return fr, ev
def placement(photo, rect):
    i = IDX[photo] - 1; m = M[i]; x0, y0, x1, y1 = rect; l, t, r, b = crop(i, x1 - x0, y1 - y0); sc = (x1 - x0) / ((r - l) * m["w"])
    return dict(file=m["src"], left=x0 - l * m["w"] * sc, top=y0 - t * m["h"] * sc, width=m["w"] * sc)
def backup(nums):
    d = os.path.join(os.path.dirname(OUT), "PSD_vecchi", "backup_" + time.strftime("%Y%m%d-%H%M%S")); os.makedirs(d, exist_ok=True)
    for n in nums: shutil.copy2(psd_path(n), d)
    print("copia di sicurezza:", d)
def check_open(nums):
    docs = dict(PS.open_documents())
    for n in nums:
        fn = os.path.basename(psd_path(n))
        if fn in docs: raise SystemExit(f"{fn} è aperto in Photoshop" + ("" if docs[fn] else " CON MODIFICHE NON SALVATE") + ": chiedi all'utente di salvarlo e chiuderlo")
def run(ops, nums):
    check_open(nums); backup(nums)
    js = PS.JS_LIB + "var OPS=" + json.dumps(ops) + "; var OUT=" + json.dumps(OUT) + ";\n" + r"""
var log=[], docs={};
function doc(n){ var k="Spread_"+(n<10?"0":"")+n; if(!docs[k]) docs[k]=app.open(new File(OUT+"/"+k+".psd")); app.activeDocument=docs[k]; return docs[k]; }
try {
 // risolvi prima tutte le cornici: i nomi cambiano durante gli scambi
 for (var i=0;i<OPS.length;i++){ var o=OPS[i]; var d=doc(o.n); o.g=findGroup(d,o.frame); if(!o.g) throw "cornice non trovata: "+o.frame+" nello spread "+o.n; }
 for (var i=0;i<OPS.length;i++){ var o=OPS[i]; var d=doc(o.n); var g=o.g;
  if (o.op=="replace"){
    var so=g.artLayers[0]; d.activeLayer=so; var x=new ActionDescriptor(); x.putPath(cid("null"),new File(o.file)); executeAction(sid("placedLayerReplaceContents"),x,DialogModes.NO);
    so=d.activeLayer; fitLayer(so,o.left,o.top,o.width); so.name=o.photo; g.name=o.photo;
    if (o.ev!=null){ var cl=clippedAbove(g); var done=false; for (var k=0;k<cl.length;k++) if (cl[k].kind==LayerKind.EXPOSURE){ setExposure(cl[k],o.ev); done=true; }
      if(!done && o.ev){ d.activeLayer=g; exposureAdjustment(o.ev); } }
    log.push(o.n+": "+o.frame+" -> "+o.photo);
  } else if (o.op=="colore"){ var cl=clippedAbove(g), r="nessun BN"; for (var k=0;k<cl.length;k++) if (cl[k].kind==LayerKind.BLACKANDWHITE){ cl[k].remove(); r="BN tolto"; } log.push(o.n+": "+o.frame+" "+r);
  } else if (o.op=="bn"){ var cl=clippedAbove(g); d.activeLayer = cl.length ? cl[0] : g; bwAdjustment(); log.push(o.n+": "+o.frame+" BN aggiunto");
  } else if (o.op=="esposizione"){ var cl=clippedAbove(g), done=false; for (var k=0;k<cl.length;k++) if (cl[k].kind==LayerKind.EXPOSURE){ setExposure(cl[k],o.ev); done=true; }
    if(!done){ d.activeLayer=g; exposureAdjustment(o.ev); } log.push(o.n+": "+o.frame+" esposizione "+o.ev); }
 }
 for (var k in docs){ app.activeDocument=docs[k]; docs[k].save(); docs[k].close(SaveOptions.DONOTSAVECHANGES); }
} catch(e){ log.push("ERRORE: "+e+" riga "+e.line+" (nessun file salvato)"); for (var k in docs){ try{ docs[k].close(SaveOptions.DONOTSAVECHANGES);}catch(_){} } }
log.join("\n");
"""
    jsx = os.path.join(CACHE, "modifica.jsx"); PS.write_jsx(jsx, js); print(PS.run_jsx(jsx))

if cmd == "scambia":
    (na, pa), (nb, pb) = ref(args[1]), ref(args[2]); fa, ea = frames(na); fb, eb = frames(nb)
    ops = [dict(op="replace", n=na, frame=pa, photo=pb, ev=eb.get(pb), **placement(pb, fa[pa])),
           dict(op="replace", n=nb, frame=pb, photo=pa, ev=ea.get(pa), **placement(pa, fb[pb]))]
    run(ops, sorted({na, nb}))
elif cmd == "sostituisci":
    n, old = ref(args[1]); new = args[2]; fr, ev = frames(n)
    run([dict(op="replace", n=n, frame=old, photo=new, ev=ev_for(IDX[new] - 1), **placement(new, fr[old]))], [n])
elif cmd in ("colore", "bn"):
    n, nm = ref(args[1]); run([dict(op=cmd, n=n, frame=nm)], [n])
elif cmd == "esposizione":
    n, nm = ref(args[1]); run([dict(op="esposizione", n=n, frame=nm, ev=float(args[2]))], [n])
elif cmd == "rifai-pagina":
    n, side = int(args[1]), args[2]; group = "Pagina " + side; SP = load_spec()
    check_open([n]); backup([n])
    # esposizioni già regolate a mano: le cerco in tutti i PSD e le riuso per le stesse foto
    known = {}
    for p in sorted(glob.glob(os.path.join(OUT, "Spread_*.psd"))):
        try: known.update(frames(int(os.path.basename(p)[7:9]))[1])
        except Exception: pass
    items = []
    for it in layout(SP[n - 1]):
        if it["side"] != ("L" if side == "sinistra" else "R") or it["k"] == "t": continue
        nm = name(it["i"]); pl = placement(nm, (it["x"], it["y"], it["x"] + it["W"], it["y"] + it["H"])); g = WB.get(nm)
        items.append(dict(name=nm, rect=[it["x"], it["y"], it["x"] + it["W"], it["y"] + it["H"]], ev=known.get(nm, ev_for(it["i"])), bw=bool(it.get("bw")),
                          wb=[round(100 * x ** (1 / 2.2), 1) for x in g] if g else None, **pl))
    js = PS.JS_LIB + "var ITEMS=" + json.dumps(items) + "; var F=" + json.dumps(psd_path(n)) + "; var GROUP=" + json.dumps(group) + ";\n" + r"""
var log=[]; var d=app.open(new File(F));
try{
  var grp=null; for (var i=0;i<d.layerSets.length;i++) if (d.layerSets[i].name==GROUP) grp=d.layerSets[i];
  if (grp) grp.remove();       // via la pagina vecchia intera (cornici + regolazioni)
  var ids=[];
  for (var i=ITEMS.length-1;i>=0;i--){ var a=ITEMS[i]; selectNone();
    makeFrame(a.rect[0],a.rect[1],a.rect[2],a.rect[3]); placeIntoFrame(a.file); var L=d.activeLayer; fitLayer(L,a.left,a.top,a.width); L.name=a.name;
    var FR=L.parent; FR.name=a.name; ids.push(FR.id); var top=FR;
    if (a.ev){ d.activeLayer=top; top=exposureAdjustment(a.ev); ids.push(top.id); }
    if (a.wb){ d.activeLayer=top; top=wbAdjustment(a.wb); ids.push(top.id); }
    if (a.bw){ d.activeLayer=top; top=bwAdjustment(); ids.push(top.id); }
    log.push(a.name+" ok"); }
  selectNone(); groupIds(ids,GROUP); d.save(); d.close(SaveOptions.DONOTSAVECHANGES);
} catch(e){ log.push("ERRORE: "+e+" riga "+e.line+" (file NON salvato)"); d.close(SaveOptions.DONOTSAVECHANGES); }
log.join("\n");
"""
    jsx = os.path.join(CACHE, "rifai_pagina.jsx"); PS.write_jsx(jsx, js); print(PS.run_jsx(jsx))
else:
    print(__doc__)
# questi file ora contengono modifiche "a mano": genera_psd.py non deve più sovrascriverli
reg = json.load(open(REG)) if os.path.exists(REG) else {}
for p in glob.glob(os.path.join(OUT, "Spread_*.psd")):
    if os.path.basename(p) in reg and os.path.getmtime(p) > reg[os.path.basename(p)] + 5: reg[os.path.basename(p)] = 0
json.dump(reg, open(REG, "w"), indent=1)
