"""Collegamento con Photoshop: script ExtendScript (.jsx) eseguiti da Photoshop.

Come si raggiunge Photoshop dipende dal sistema (AppleScript sul Mac, COM su Windows, niente su Linux): sta in
piattaforma/photoshop.py. Qui restano le funzioni usate dagli script del motore e la libreria JS condivisa.

Regole imparate a fatica:
- `do javascript (POSIX file ...)` dà "errore generale 8800": usare `do javascript "$.evalFile(new File('...'))"`.
- Lo script .jsx deve essere ASCII puro (Photoshop lo legge nella codifica di sistema: "·" diventava "¬∑").
- Un "%" dentro il testo JS rompe la formattazione Python con %: evitarlo.
"""
from ..piattaforma import photoshop as _ps


def app_name():
    """nome dell'applicazione Photoshop; se manca ferma lo script con un messaggio (SystemExit, come nelle 1.x)"""
    t = _ps.trova()
    if t is None: raise SystemExit(_ps.motivo_assente())
    return t["nome"]


def write_jsx(path, js):
    with open(path, "w", encoding="ascii") as f: f.write(js.encode("ascii", "backslashreplace").decode("ascii"))


def run_jsx(path, timeout=3600):
    app_name()
    return _ps.esegui_jsx(path, timeout)


def run_js(code):
    app_name()
    return _ps.esegui_js(code)


def open_documents():
    """[(nome, salvato?)] dei documenti aperti in Photoshop: non toccare mai documenti con modifiche non salvate dell'utente"""
    out = run_js('var a=[]; for (var i=0;i<app.documents.length;i++) a.push(app.documents[i].name+"|"+app.documents[i].saved); a.join("\\n");')
    res = []
    for line in out.splitlines():
        if "|" in line: n, s = line.rsplit("|", 1); res.append((n, s == "true"))
    return res

# funzioni ExtendScript condivise (Action Manager): cornici, posizionamento, livelli di regolazione, gruppi
JS_LIB = r"""
app.displayDialogs = DialogModes.NO;
app.preferences.rulerUnits = Units.PIXELS; app.preferences.typeUnits = TypeUnits.POINTS;
function cid(s){return charIDToTypeID(s);} function sid(s){return stringIDToTypeID(s);} function px(v){return new UnitValue(v,"px");}
function makeFrame(l,t,r,b){   // cornice dello strumento Cornice (K)
  var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(sid("framedGroupSection")); d.putReference(cid("null"),ref);
  var rc=new ActionDescriptor(); rc.putDouble(sid("top"),t); rc.putDouble(sid("left"),l); rc.putDouble(sid("bottom"),b); rc.putDouble(sid("right"),r);
  d.putObject(sid("framedGroupRect"),sid("classFloatRect"),rc); executeAction(cid("Mk  "),d,DialogModes.NO); }
function placeIntoFrame(path){  // con la cornice selezionata, la foto entra nella cornice come oggetto avanzato incorporato
  var p=new ActionDescriptor(); p.putPath(cid("null"),new File(path)); p.putBoolean(sid("linked"),false);
  p.putEnumerated(sid("freeTransformCenterState"),sid("quadCenterState"),sid("QCSAverage")); executeAction(sid("placeEvent"),p,DialogModes.NO); }
function fitLayer(L,left,top,width){ var w=L.bounds[2].as("px")-L.bounds[0].as("px"); L.resize(width/w*100,width/w*100,AnchorPosition.TOPLEFT);
  L.translate(px(left-L.bounds[0].as("px")),px(top-L.bounds[1].as("px"))); }
function exposureAdjustment(ev){
  var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var e=new ActionDescriptor(); e.putEnumerated(sid("presetKind"),sid("presetKindType"),sid("presetKindCustom"));
  e.putDouble(cid("Exps"),ev); e.putDouble(cid("Ofst"),0); e.putDouble(sid("gammaCorrection"),1);
  var u=new ActionDescriptor(); u.putObject(cid("Type"),cid("Exps"),e); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Esposizione "+(ev>0?"+":"")+ev; L.grouped=true; return L; }
function setExposure(L,v){ app.activeDocument.activeLayer=L; var d=new ActionDescriptor(),r=new ActionReference(); r.putEnumerated(cid("AdjL"),cid("Ordn"),cid("Trgt")); d.putReference(cid("null"),r);
  var e=new ActionDescriptor(); e.putEnumerated(sid("presetKind"),sid("presetKindType"),sid("presetKindCustom")); e.putDouble(cid("Exps"),v); e.putDouble(cid("Ofst"),0); e.putDouble(sid("gammaCorrection"),1);
  d.putObject(cid("T   "),cid("Exps"),e); executeAction(cid("setd"),d,DialogModes.NO); L.name="Esposizione "+(v>0?"+":"")+v; }
function wbAdjustment(p){   // bilanciamento del bianco = Miscelatore canale non monocromatico, ogni canale x guadagno (percentuale in gamma)
  var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  var mx=new ActionDescriptor(); mx.putEnumerated(sid("presetKind"),sid("presetKindType"),sid("presetKindCustom")); mx.putBoolean(cid("Mnch"),false);
  var keys=["Rd  ","Grn ","Bl  "];
  for (var c=0;c<3;c++){ var ch=new ActionDescriptor(); for (var k=0;k<3;k++) ch.putUnitDouble(cid(keys[k]),cid("#Prc"), k==c ? p[c] : 0); mx.putObject(cid(keys[c]),cid("ChMx"),ch); }
  var u=new ActionDescriptor(); u.putObject(cid("Type"),cid("ChnM"),mx); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Bilanciamento bianco"; L.grouped=true; return L; }
function bwAdjustment(){
  var d=new ActionDescriptor(),ref=new ActionReference(); ref.putClass(cid("AdjL")); d.putReference(cid("null"),ref);
  // pesi = luminanza Rec.601 (30 89 59 70 11 41): il bianco e nero coincide con quello dell'anteprima
  var b=new ActionDescriptor(); b.putInteger(cid("Rd  "),30); b.putInteger(cid("Yllw"),89); b.putInteger(cid("Grn "),59); b.putInteger(cid("Cyn "),70); b.putInteger(cid("Bl  "),11); b.putInteger(cid("Mgnt"),41); b.putBoolean(sid("useTint"),false);
  var u=new ActionDescriptor(); u.putObject(cid("Type"),cid("BanW"),b); d.putObject(cid("Usng"),cid("AdjL"),u);
  executeAction(cid("Mk  "),d,DialogModes.NO); var L=app.activeDocument.activeLayer; L.name="Bianco e nero"; L.grouped=true; return L; }
function selectNone(){ try{ var d=new ActionDescriptor(),r=new ActionReference(); r.putEnumerated(cid("Lyr "),cid("Ordn"),cid("Trgt")); d.putReference(cid("null"),r); executeAction(sid("selectNoLayers"),d,DialogModes.NO);}catch(e){} }
function groupIds(list,name){  // seleziona i livelli per ID e li raggruppa (come Cmd+G): l'unico modo affidabile, spostare dentro gruppi vuoti fallisce
  if(!list.length) return;
  for (var i=0;i<list.length;i++){ var d=new ActionDescriptor(),r=new ActionReference(); r.putIdentifier(cid("Lyr "),list[i]); d.putReference(cid("null"),r);
    if(i>0) d.putEnumerated(sid("selectionModifier"),sid("selectionModifierType"),sid("addToSelection")); d.putBoolean(cid("MkVs"),false); executeAction(cid("slct"),d,DialogModes.NO); }
  var g=new ActionDescriptor(),r1=new ActionReference(); r1.putClass(sid("layerSection")); g.putReference(cid("null"),r1);
  var r2=new ActionReference(); r2.putEnumerated(cid("Lyr "),cid("Ordn"),cid("Trgt")); g.putReference(cid("From"),r2);
  var u=new ActionDescriptor(); u.putString(cid("Nm  "),name); g.putObject(cid("Usng"),sid("layerSection"),u); executeAction(cid("Mk  "),g,DialogModes.NO); }
function findGroup(c,name){ for (var i=0;i<c.layerSets.length;i++){ var s=c.layerSets[i]; if (s.name==name) return s; var r=findGroup(s,name); if (r) return r; } return null; }
// nel DOM di Photoshop i livelli vanno dall'alto in basso: i livelli di regolazione agganciati a una cornice stanno SOPRA di lei (indice minore)
function clippedAbove(g){ var p=g.parent.layers, idx=-1, out=[]; for (var i=0;i<p.length;i++) if (p[i]==g) idx=i;
  for (var i=idx-1;i>=0 && p[i].typename=="ArtLayer" && p[i].grouped; i--) out.push(p[i]); return out; }
"""
