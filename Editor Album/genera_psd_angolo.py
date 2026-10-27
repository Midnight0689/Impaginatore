"""Esegue genera_psd.py della skill aggiungendo l'angolo delle foto (ROT): dopo aver messo la foto nella cornice la ruota attorno al centro della cornice.
Imposta anche il profilo colore sRGB sul documento (senza, Photoshop può usare il profilo del monitor e i colori cambiano). Non modifica la skill: legge il suo codice e ci applica tre sostituzioni; se la skill è cambiata e non combaciano, genera i PSD senza angoli e lo dice."""
import os, sys
SCR = os.environ.get("ALBUM_SCRIPTS") or next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--scripts"), None) or os.getcwd()
path = os.path.join(SCR, "genera_psd.py"); src = open(path).read()
sys.path.insert(0, SCR); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROT_JS = r'''function rotAround(L,deg,fx,fy){ var b=L.bounds, cx=(b[0].as("px")+b[2].as("px"))/2, cy=(b[1].as("px")+b[3].as("px"))/2;
  L.rotate(deg,AnchorPosition.MIDDLECENTER); var r=deg*Math.PI/180, nx=fx+(cx-fx)*Math.cos(r)-(cy-fy)*Math.sin(r), ny=fy+(cx-fx)*Math.sin(r)+(cy-fy)*Math.cos(r);
  var b2=L.bounds, c2x=(b2[0].as("px")+b2[2].as("px"))/2, c2y=(b2[1].as("px")+b2[3].as("px"))/2; L.translate(px(nx-c2x),px(ny-c2y)); }
var log=[]; var STEP="start";
function addTextX(doc,it,ids){ var X=it.X; if(!X||!X.tx) return;
  var L=doc.artLayers.add(); L.kind=LayerKind.TEXT; var ti=L.textItem; ti.kind=TextType.PARAGRAPHTEXT; ti.contents=X.tx.replace(/\n/g,"\r"); ti.font=X.font; ti.size=new UnitValue(X.size,"pt"); ti.tracking=X.tr||0;
  ti.useAutoLeading=false; ti.leading=new UnitValue(X.size*1.2,"pt"); var c=new SolidColor(); c.rgb.red=X.col[0]; c.rgb.green=X.col[1]; c.rgb.blue=X.col[2]; ti.color=c;
  ti.width=px(it.w); ti.height=px(it.h); ti.position=[px(it.x),px(it.y)]; L.name="Testo - "+X.tx.split("\n")[0]; if (X.al=="center") ti.justification=Justification.CENTER; else if (X.al=="right") ti.justification=Justification.RIGHT; else ti.justification=Justification.LEFT; var bb=L.bounds; L.translate(px(it.x+X.gx-bb[0].as("px")),px(it.y+X.gy-bb[1].as("px"))); ids.push(L.id); }
function levelsAdj(b,w,g){ var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var ch=new ActionDescriptor(),cr=new ActionReference(); cr.putEnumerated(cid("Chnl"),cid("Chnl"),cid("Cmps")); ch.putReference(cid("Chnl"),cr);
  var inp=new ActionList(); inp.putInteger(b); inp.putInteger(w); ch.putList(cid("Inpt"),inp); ch.putDouble(cid("Gmm "),g);
  var list=new ActionList(); list.putObject(cid("LvlA"),ch); var l=new ActionDescriptor(); l.putList(cid("Adjs"),list);
  var u=new ActionDescriptor(); u.putObject(cid("Type"),cid("Lvls"),l); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Livelli"; L.grouped=true; return L; }
function vibAdj(vib,sat){ var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var v=new ActionDescriptor(); v.putInteger(sid("vibrance"),vib); v.putInteger(cid("Strt"),sat);
  var u=new ActionDescriptor(); u.putObject(cid("Type"),sid("vibrance"),v); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Vibranza e saturazione"; L.grouped=true; return L; }
function curvesAdj(pts){ var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var ch=new ActionDescriptor(),cr=new ActionReference(); cr.putEnumerated(cid("Chnl"),cid("Chnl"),cid("Cmps")); ch.putReference(cid("Chnl"),cr);
  var pl=new ActionList(); for (var i=0;i<pts.length;i++){ var p=new ActionDescriptor(); p.putDouble(cid("Hrzn"),pts[i][0]); p.putDouble(cid("Vrtc"),pts[i][1]); pl.putObject(cid("Pnt "),p); }
  ch.putList(cid("Crv "),pl); var list=new ActionList(); list.putObject(cid("CrvA"),ch); var l=new ActionDescriptor(); l.putList(cid("Adjs"),list);
  var u=new ActionDescriptor(); u.putObject(cid("Type"),cid("Crvs"),l); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Curva"; L.grouped=true; return L; }'''
NEWDOC = 'var doc=app.documents.add(G.CW,G.CH,72,nm,NewDocumentMode.RGB,DocumentFill.WHITE);'
TXT_OLD = '''  var L1 = title ? [TX.nome,TX.serif,380,0, it.x+it.w/2, it.y+it.h/2+82] : [TX.nome,TX.serif,170,0, it.x, it.y+it.h-247];
  var L2 = title ? [TX.sotto,TX.sans,62,355, it.x+it.w/2, it.y+it.h/2+307] : [TX.sotto,TX.sans,62,225, it.x+6, it.y+it.h-124];
  var L3 = title ? [TX.data,TX.sans,62,355, it.x+it.w/2, it.y+it.h/2+417] : [TX.data,TX.sans,62,225, it.x+6, it.y+it.h-34];'''
TXT_NEW = '''  var s_=it.ts||1;
  var L1 = title ? [TX.nome,TX.serif,380*s_,0, it.x+it.w/2, it.y+it.h/2+82*s_] : [TX.nome,TX.serif,170*s_,0, it.x, it.y+it.h-247*s_];
  var L2 = title ? [TX.sotto,TX.sans,62*s_,355*s_, it.x+it.w/2, it.y+it.h/2+307*s_] : [TX.sotto,TX.sans,62*s_,225*s_, it.x+6*s_, it.y+it.h-124*s_];
  var L3 = title ? [TX.data,TX.sans,62*s_,355*s_, it.x+it.w/2, it.y+it.h/2+417*s_] : [TX.data,TX.sans,62*s_,225*s_, it.x+6*s_, it.y+it.h-34*s_];'''
reps = [(TXT_OLD, TXT_NEW), ('items.append(dict(txt=it["kind"], x=it["x"],', 'items.append(dict(txt=it["kind"], ts=float(it.get("ts") or 1), X=(__import__("testo").job_x(it) if it["kind"] == "txt" else None), x=it["x"],'), (NEWDOC, 'var doc=app.documents.add(G.CW,G.CH,72,nm,NewDocumentMode.RGB,DocumentFill.WHITE,1,BitsPerChannelType.EIGHT,"sRGB IEC61966-2.1");'),
        ('bw=bool(it.get("bw")), ev=ev_for(it["i"])', 'bw=bool(it.get("bw")), ang=float(it.get("a") or 0), ev=ev_for(it["i"]), tono=__import__("album_libere").tono_job(it["i"]), rit=__import__("album_libere").rit_job(it["i"])'),
        ('addText(doc,it,ids[it.side]); }', '(it.txt=="txt"?addTextX:addText)(doc,it,ids[it.side]); }'),
        ('if (it.bw) { doc.activeLayer=top; top=bwAdjustment();', 'if (it.tono) { var T=it.tono; if (T.b>0||T.w<255||Math.abs(T.m-1)>0.001){ doc.activeLayer=top; top=levelsAdj(T.b,T.w,T.m); ids[it.side].push(top.id); } if (T.c && T.c.length){ var pp=[[0,0]].concat(T.c,[[255,255]]); doc.activeLayer=top; top=curvesAdj(pp); ids[it.side].push(top.id); } }\n    if (it.rit) { var RT=it.rit; if (RT.c && RT.c.length){ var pq=[[0,0]].concat(RT.c,[[255,255]]); doc.activeLayer=top; top=curvesAdj(pq); top.name="Ritocco: tono"; ids[it.side].push(top.id); } if (RT.vib||RT.sat){ doc.activeLayer=top; top=vibAdj(RT.vib,RT.sat); ids[it.side].push(top.id); } }\n    if (it.bw) { doc.activeLayer=top; top=bwAdjustment();'),
        ('g = WB.get(name(it["i"]))', 'g = __import__("album_libere").wb_total(it["i"])'),
        ('fitLayer(L,it.left,it.top,it.width); L.name=it.name;', 'fitLayer(L,it.left,it.top,it.width); if (it.ang) rotAround(L,it.ang,it.x+it.w/2,it.y+it.h/2); L.name=it.name;'),
        ('var log=[]; var STEP="start";', ROT_JS)]
if all(a in src for a, _ in reps):
    for a, b in reps: src = src.replace(a, b, 1)
else: print("ATTENZIONE: genera_psd.py della skill è cambiato: i PSD vengono generati senza gli angoli delle foto.", flush=True)
sys.argv[0] = path
exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
