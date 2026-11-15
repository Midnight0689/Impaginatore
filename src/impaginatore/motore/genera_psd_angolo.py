"""PSD con gli angoli delle foto (ROT): dopo aver messo la foto nella cornice la ruota attorno al centro della cornice.
Imposta anche il profilo colore sRGB sul documento (senza, Photoshop può usare il profilo del monitor e i colori cambiano),
e aggiunge livelli di testo, scala dei titoli, tono, ritocco, bordi, ombre e opacità.

È genera_psd con le sue parti estese (genera_psd.PARTI -> PARTI qui sotto) e le voci estese delle foto e dei testi:
nessuna modifica del codice come testo, niente exec.

    python -m impaginatore.motore.genera_psd_angolo --progetto <cartella> [--spread 1,2,5 | tutti] [--forza]
"""
from . import genera_psd

ROT_JS = r'''function rotAround(L,deg,fx,fy){ var b=L.bounds, cx=(b[0].as("px")+b[2].as("px"))/2, cy=(b[1].as("px")+b[3].as("px"))/2;
  L.rotate(deg,AnchorPosition.MIDDLECENTER); var r=deg*Math.PI/180, nx=fx+(cx-fx)*Math.cos(r)-(cy-fy)*Math.sin(r), ny=fy+(cx-fx)*Math.sin(r)+(cy-fy)*Math.cos(r);
  var b2=L.bounds, c2x=(b2[0].as("px")+b2[2].as("px"))/2, c2y=(b2[1].as("px")+b2[3].as("px"))/2; L.translate(px(nx-c2x),px(ny-c2y)); }
var log=[]; var STEP="start";
function addTextX(doc,it,ids){ var X=it.X; if(!X||!X.tx) return;
  var L=doc.artLayers.add(); L.kind=LayerKind.TEXT; var ti=L.textItem; ti.kind=TextType.PARAGRAPHTEXT; ti.contents=X.tx.replace(/\n/g,"\r"); ti.font=X.font; ti.size=new UnitValue(X.size,"pt"); ti.tracking=X.tr||0; try{ ti.autoKerning=AutoKernType.MANUAL; }catch(e){} if (X.caps) ti.capitalization=TextCase.ALLCAPS;
  ti.useAutoLeading=false; ti.leading=new UnitValue(X.size*(X.lh||1.2),"pt"); var c=new SolidColor(); c.rgb.red=X.col[0]; c.rgb.green=X.col[1]; c.rgb.blue=X.col[2]; ti.color=c;
  ti.width=px(it.w); ti.height=px(it.h); ti.position=[px(it.x),px(it.y)]; L.name="Testo - "+X.tx.split("\n")[0]; if (X.al=="center") ti.justification=Justification.CENTER; else if (X.al=="right") ti.justification=Justification.RIGHT; else ti.justification=Justification.LEFT; var D=L.duplicate(); D.rasterize(RasterizeType.ENTIRELAYER); var bb=D.bounds; D.remove(); doc.activeLayer=L; L.translate(px(it.x+X.gx-bb[0].as("px")),px(it.y+X.gy-bb[1].as("px"))); ids.push(L.id); }
function levelsAdj(b,w,g){ var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var ch=new ActionDescriptor(),cr=new ActionReference(); cr.putEnumerated(cid("Chnl"),cid("Chnl"),cid("Cmps")); ch.putReference(cid("Chnl"),cr);
  var inp=new ActionList(); inp.putInteger(b); inp.putInteger(w); ch.putList(cid("Inpt"),inp); ch.putDouble(cid("Gmm "),g);
  var list=new ActionList(); list.putObject(cid("LvlA"),ch); var l=new ActionDescriptor(); l.putList(cid("Adjs"),list);
  var u=new ActionDescriptor(); u.putObject(cid("Type"),cid("Lvls"),l); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Livelli"; L.grouped=true; return L; }
function mixAdj(M,nm){ var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var mx=new ActionDescriptor(); mx.putEnumerated(sid("presetKind"),sid("presetKindType"),sid("presetKindCustom")); mx.putBoolean(cid("Mnch"),false);
  var keys=["Rd  ","Grn ","Bl  "];
  for (var c=0;c<3;c++){ var ch=new ActionDescriptor(); for (var k=0;k<3;k++) ch.putUnitDouble(cid(keys[k]),cid("#Prc"),M[c][k]); mx.putObject(cid(keys[c]),cid("ChMx"),ch); }
  var u=new ActionDescriptor(); u.putObject(cid("Type"),cid("ChnM"),mx); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name=nm; L.grouped=true; return L; }
function vibAdj(vib,sat){ var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var v=new ActionDescriptor(); v.putInteger(sid("vibrance"),vib); v.putInteger(cid("Strt"),sat);
  var u=new ActionDescriptor(); u.putObject(cid("Type"),sid("vibrance"),v); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Vibranza e saturazione"; L.grouped=true; return L; }
function rectLayer(doc,l,t,r,b,col,name){ var L=doc.artLayers.add(); L.name=name; doc.selection.select([[l,t],[r,t],[r,b],[l,b]]); var c=new SolidColor(); c.rgb.red=col[0]; c.rgb.green=col[1]; c.rgb.blue=col[2]; doc.selection.fill(c); doc.selection.deselect(); return L; }
function layerFx(L,X){ app.activeDocument.activeLayer=L; var d=new ActionDescriptor(),ref=new ActionReference(); ref.putEnumerated(cid("Lyr "),cid("Ordn"),cid("Trgt")); d.putReference(cid("null"),ref);
  var fx=new ActionDescriptor(); fx.putUnitDouble(cid("Scl "),cid("#Prc"),100);
  function colr(c){ var o=new ActionDescriptor(); o.putDouble(cid("Rd  "),c[0]); o.putDouble(cid("Grn "),c[1]); o.putDouble(cid("Bl  "),c[2]); return o; }
  if (X.bd>0){ var f=new ActionDescriptor(); f.putBoolean(cid("enab"),true); f.putBoolean(sid("present"),true); f.putBoolean(sid("showInDialog"),true);
    f.putEnumerated(cid("Styl"),cid("FStl"),cid("InsF")); f.putEnumerated(cid("PntT"),cid("FrFl"),cid("SClr")); f.putEnumerated(cid("Md  "),cid("BlnM"),cid("Nrml"));
    f.putUnitDouble(cid("Opct"),cid("#Prc"),100); f.putUnitDouble(cid("Sz  "),cid("#Pxl"),X.bd); f.putObject(cid("Clr "),cid("RGBC"),colr(X.col)); fx.putObject(cid("FrFX"),cid("FrFX"),f); }
  if (X.sh>0){ var s=new ActionDescriptor(); s.putBoolean(cid("enab"),true); s.putBoolean(sid("present"),true); s.putBoolean(sid("showInDialog"),true);
    s.putEnumerated(cid("Md  "),cid("BlnM"),cid("Mltp")); s.putObject(cid("Clr "),cid("RGBC"),colr([0,0,0])); s.putUnitDouble(cid("Opct"),cid("#Prc"),15+0.5*X.sh);
    s.putBoolean(cid("uglg"),false); s.putUnitDouble(cid("lagl"),cid("#Ang"),90); var mm=X.ppi/25.4; s.putUnitDouble(cid("Dstn"),cid("#Pxl"),(1.5+X.sh/100*4.5)*mm*0.55);
    s.putUnitDouble(cid("Ckmt"),cid("#Pxl"),0); s.putUnitDouble(cid("blur"),cid("#Pxl"),(1.5+X.sh/100*4.5)*mm); s.putUnitDouble(cid("Nose"),cid("#Prc"),0); s.putBoolean(cid("AntA"),false); fx.putObject(cid("DrSh"),cid("DrSh"),s); }
  d.putObject(cid("T   "),cid("Lefx"),fx); executeAction(cid("setd"),d,DialogModes.NO); }
function curvesAdj(pts){ var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var ch=new ActionDescriptor(),cr=new ActionReference(); cr.putEnumerated(cid("Chnl"),cid("Chnl"),cid("Cmps")); ch.putReference(cid("Chnl"),cr);
  var pl=new ActionList(); for (var i=0;i<pts.length;i++){ var p=new ActionDescriptor(); p.putDouble(cid("Hrzn"),pts[i][0]); p.putDouble(cid("Vrtc"),pts[i][1]); pl.putObject(cid("Pnt "),p); }
  ch.putList(cid("Crv "),pl); var list=new ActionList(); list.putObject(cid("CrvA"),ch); var l=new ActionDescriptor(); l.putList(cid("Adjs"),list);
  var u=new ActionDescriptor(); u.putObject(cid("Type"),cid("Crvs"),l); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Curva"; L.grouped=true; return L; }'''
TESTO_JS = '''  var s_=it.ts||1;
  var L1 = title ? [TX.nome,TX.serif,380*s_,0, it.x+it.w/2, it.y+it.h/2+82*s_] : [TX.nome,TX.serif,170*s_,0, it.x, it.y+it.h-247*s_];
  var L2 = title ? [TX.sotto,TX.sans,62*s_,355*s_, it.x+it.w/2, it.y+it.h/2+307*s_] : [TX.sotto,TX.sans,62*s_,225*s_, it.x+6*s_, it.y+it.h-124*s_];
  var L3 = title ? [TX.data,TX.sans,62*s_,355*s_, it.x+it.w/2, it.y+it.h/2+417*s_] : [TX.data,TX.sans,62*s_,225*s_, it.x+6*s_, it.y+it.h-34*s_];'''      # titoli e firma con la scala ts
PARTI = dict(TESTO=TESTO_JS, INIZIO=ROT_JS,
             NUOVO_DOC='var doc=app.documents.add(G.CW,G.CH,72,nm,NewDocumentMode.RGB,DocumentFill.WHITE,1,BitsPerChannelType.EIGHT,"sRGB IEC61966-2.1");',
             ANGOLO='if (it.ang) rotAround(L,it.ang,it.x+it.w/2,it.y+it.h/2); ',
             STILE='if (it.sty && it.sty.oc<100) { try { FR.opacity=it.sty.oc; } catch(e) { log.push("opacità non applicata: "+e); } }\n    if (it.sty && it.sty.sh>0) { try { var SL=rectLayer(doc,it.x,it.y,it.x+it.w,it.y+it.h,[255,255,255],"Ombra "+it.name); layerFx(SL,{bd:0,sh:it.sty.sh,ppi:it.sty.ppi}); SL.move(FR,ElementPlacement.PLACEAFTER); ids[it.side].push(SL.id); } catch(e) { log.push("ombra non applicata: "+e); } doc.activeLayer=FR; }\n    if (it.sty && it.sty.bd>0) { try { var BL=rectLayer(doc,it.x,it.y,it.x+it.w,it.y+it.h,it.sty.col,"Bordo "+it.name); BL.fillOpacity=0; layerFx(BL,{bd:it.sty.bd,col:it.sty.col,sh:0,ppi:it.sty.ppi}); ids[it.side].push(BL.id); } catch(e) { log.push("bordo non applicato: "+e); } doc.activeLayer=FR; }\n    ',
             TONO='if (it.tono) { var T=it.tono; if (T.b>0||T.w<255||Math.abs(T.m-1)>0.001){ doc.activeLayer=top; top=levelsAdj(T.b,T.w,T.m); ids[it.side].push(top.id); } if (T.c && T.c.length){ var pp=[[0,0]].concat(T.c,[[255,255]]); doc.activeLayer=top; top=curvesAdj(pp); ids[it.side].push(top.id); } }\n    if (it.rit) { var RT=it.rit; if (RT.c && RT.c.length){ doc.activeLayer=top; top=curvesAdj(RT.c); top.name="Ritocco: tono"; ids[it.side].push(top.id); } if (RT.satm){ doc.activeLayer=top; top=mixAdj(RT.satm,"Saturazione"); ids[it.side].push(top.id); } if (RT.vib){ doc.activeLayer=top; top=vibAdj(RT.vib,0); top.name="Vibranza"; ids[it.side].push(top.id); } }\n    ',
             AGGIUNGI_TESTO='(it.txt=="txt"?addTextX:addText)')


def main(argv=None):
    return genera_psd.main(argv, parti=PARTI, estesa=True)


if __name__ == "__main__":
    main()
