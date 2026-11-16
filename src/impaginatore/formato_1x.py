"""Formato delle versioni 1.x (spec.py): lettura senza eseguire niente, e scrittura per chi usa ancora la 1.x.

spec.py è codice Python («from album import *», SPREADS = [...]): le 1.x lo eseguivano, e così un progetto ricevuto da altri
poteva eseguire qualsiasi istruzione (audit SEC-001). Qui il file si legge con ast, come testo: si accetta solo la piccola
grammatica che scrivono l'editor 1.x e l'assistente con la skill, e niente viene mai eseguito:

    - testi liberi (la riga di descrizione in alto) e commenti
    - from album import *  /  from album_libere import *  (o solo alcuni dei nomi qui sotto)
    - NOME = espressione,  NOME += espressione,  NOME.append(espressione),  NOME.extend(espressione)
    - espressioni: testi, numeri, True/False/None, + e - davanti ai numeri, + - * / tra numeri, + tra elenchi o tra testi,
      elenchi [...] e tuple (...) anche con *elenco, nomi già assegnati, e chiamate ai costruttori del motore:
      P FULL TXT I W DUO VLL V4 G4 CV SV PP COL2 BAND2 STRIP3 (album) e FREE TXTF TEXT ROT STY (album_libere)
      con argomenti che sono a loro volta espressioni di questa grammatica

Ogni altra cosa (import di altri moduli, funzioni, cicli, attributi, dizionari, chiamate a qualsiasi altra funzione...)
produce l'errore «Questo progetto contiene istruzioni non riconosciute» con la riga e il motivo. I costruttori sono
quelli veri del motore (stessi risultati delle 1.x), chiamati solo dopo aver controllato gli argomenti con la loro firma.
Ci sono limiti di misura (file, nodi, profondità, lunghezza degli elenchi e dei testi, numeri) contro i file costruiti
per bloccare il programma.

La scrittura (testo_spec, esporta) serve solo per «Esporta per la versione 1.x»: la 2.0 salva album.json.
"""
import ast
import inspect
import math
import os
import shutil
import time

from .validazione import MAX_ELEMENTI, MAX_SPREAD, ErroreProgetto

SPEC = "spec.py"
MAX_BYTE = 4 * 2**20                       # un album vero di 300 spread scritto dall'editor sta sotto i 300 KB
MAX_NODI = 400_000
MAX_PROFONDITA = 60
MAX_LISTA = 200_000                        # elementi di un elenco costruito con + / append / extend
MAX_TESTO = 1_000_000                      # caratteri di un testo costruito con +
MAX_NUMERO = 1e12
MAX_TESTI_COSTRUITI = 8_000_000            # caratteri di TUTTI i testi costruiti con + (VER-005: i limiti sopra valgono per un testo o un elenco solo)
MAX_ELEMENTI_COSTRUITI = 1_000_000         # elementi di TUTTI gli elenchi costruiti (scritti, +, append, extend): più dei nodi possibili, meno di 10 MB
MAX_ELEMENTI_ALBUM = 100_000               # elementi di tutte le pagine (un album.json di 10 MB non ne contiene di più)
MAX_TESTO_ALBUM = 4_000_000                # caratteri di tutti i livelli di testo dell'album
_SEMPLICI = (str, int, float, bool, type(None))
COSTRUTTORI = {"album": ("P", "FULL", "TXT", "I", "W", "DUO", "VLL", "V4", "G4", "CV", "SV", "PP", "COL2", "BAND2", "STRIP3"),
               "album_libere": ("FREE", "TXTF", "TEXT", "ROT", "STY")}
_PAGINA = ("I", "W")                       # costruttori di pagina: gli altri danno un elemento o un elenco di elementi
_MODULI = ("DUO", "VLL", "V4", "G4", "CV", "SV", "PP", "COL2", "BAND2", "STRIP3")
_ISTRUZIONI = {ast.Import: "import di moduli", ast.FunctionDef: "definizione di funzioni", ast.AsyncFunctionDef: "definizione di funzioni",
               ast.ClassDef: "definizione di classi", ast.For: "cicli", ast.While: "cicli", ast.If: "condizioni", ast.With: "istruzione «with»",
               ast.Try: "istruzione «try»", ast.Delete: "istruzione «del»", ast.Global: "istruzione «global»", ast.Assert: "istruzione «assert»",
               ast.Raise: "istruzione «raise»", ast.Return: "istruzione «return»", ast.AnnAssign: "assegnazione con annotazione"}
_ESPRESSIONI = {ast.Attribute: "accesso ad attributi (nome.qualcosa)", ast.Subscript: "indici (nome[...])", ast.Lambda: "funzioni lambda",
                ast.Dict: "dizionari { … }", ast.Set: "insiemi { … }", ast.ListComp: "elenchi costruiti con for", ast.GeneratorExp: "espressioni con for",
                ast.DictComp: "espressioni con for", ast.SetComp: "espressioni con for", ast.JoinedStr: "testi f\"…\"", ast.IfExp: "espressioni con if",
                ast.BoolOp: "and / or", ast.Compare: "confronti", ast.NamedExpr: "assegnazioni :=", ast.Await: "await", ast.Yield: "yield", ast.YieldFrom: "yield"}


class _NonRiconosciuto(Exception):
    def __init__(self, nodo, motivo):
        super().__init__(motivo); self.riga = getattr(nodo, "lineno", 0); self.motivo = motivo


class _Elemento:
    """segnaposto di un elemento quando si controlla un file senza il progetto caricato (controlla)"""


def errore_istruzioni(nome, riga, motivo):
    return ErroreProgetto(f"Questo progetto contiene istruzioni non riconosciute ({nome}, riga {riga}: {motivo}). "
                          "Per sicurezza l'Impaginatore non esegue il contenuto dei progetti: il progetto non è stato aperto né modificato.")


# firme dei costruttori (argomenti obbligatori, facoltativi): servono al controllo senza motore (la schermata dei progetti
# non carica il motore); un test le confronta con quelle vere di impaginatore.motore.album e album_libere
FIRME = {"P": ("n c r w h", "bw z"), "FULL": ("n", "bw z"), "TXT": ("kind c r w h", ""), "I": None, "W": None,
         "DUO": ("a b", "bw z"), "VLL": ("v a b", "mirror bw"), "V4": ("v a b c d", "mirror z"), "G4": ("a b c d", "bw"),
         "CV": ("v", "bw z"), "SV": ("v", "bw z"), "PP": ("l", "bw"), "COL2": ("a b", "bw"), "BAND2": ("a b", "bw"), "STRIP3": ("a b c", "bw"),
         "FREE": ("n x y w h", "bw z zo"), "TXTF": ("kind fx fy fw fh", "ts zo"),
         "TEXT": ("tx fx fy fw fh", "font size col al tr auto zo stile lh caps"), "ROT": ("it deg", ""), "STY": ("it", "bd sh oc")}


def firma(nome):
    P = inspect.Parameter
    if FIRME[nome] is None: return inspect.Signature([P("items", P.VAR_POSITIONAL)])
    obb, fac = FIRME[nome]
    return inspect.Signature([P(a, P.POSITIONAL_OR_KEYWORD) for a in obb.split()] + [P(a, P.POSITIONAL_OR_KEYWORD, default=None) for a in fac.split()])


def _funzioni(prova):
    """costruttori veri del motore (lettura) o finti con la stessa firma (prova: solo controllo, senza progetto caricato)"""
    if not prova:
        from .motore import album, album_libere
        return {"album": {n: getattr(album, n) for n in COSTRUTTORI["album"]}, "album_libere": {n: getattr(album_libere, n) for n in COSTRUTTORI["album_libere"]}}
    return {mod: {n: _finto(n) for n in nomi} for mod, nomi in COSTRUTTORI.items()}


def _finto(nome):
    def finto(*a, **k):
        if nome in _PAGINA: return (nome, [x for it in a for x in (it if isinstance(it, list) else [it])])       # come album.I / album.W
        return [_Elemento()] if nome in _MODULI else _Elemento()
    finto.__signature__ = firma(nome)
    return finto


class _Lettore:
    def __init__(self, funzioni):
        self.funzioni, self.nomi = funzioni, {}
        self.caratteri = self.elementi = 0     # budget di tutto il file (VER-005)

    # ---- istruzioni
    def istruzione(self, n):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str): return       # descrizione
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute): return self.aggiungi(n.value)
        if isinstance(n, ast.Expr): raise _NonRiconosciuto(n, (f"chiamata a «{n.value.func.id}»" if isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) else "espressione da sola") + " non ammessa")
        if isinstance(n, ast.ImportFrom): return self.importa(n)
        if isinstance(n, ast.Assign):
            if len(n.targets) != 1 or not isinstance(n.targets[0], ast.Name): raise _NonRiconosciuto(n, "si può assegnare solo a un nome (NOME = …)")
            self.nomi[n.targets[0].id] = ("v", self.valore(n.value, 0)); return
        if isinstance(n, ast.AugAssign):
            if not isinstance(n.target, ast.Name) or not isinstance(n.op, ast.Add): raise _NonRiconosciuto(n, "è ammesso solo NOME += …")
            self.nomi[n.target.id] = ("v", self.somma(self.variabile(n.target), self.valore(n.value, 0), n)); return
        raise _NonRiconosciuto(n, f"istruzione non ammessa ({_ISTRUZIONI.get(type(n)) or type(n).__name__})")

    def importa(self, n):
        if n.level or n.module not in COSTRUTTORI: raise _NonRiconosciuto(n, f"import dal modulo «{'.' * n.level}{n.module or ''}» non ammesso (solo album e album_libere)")
        for a in n.names:
            if a.name == "*": self.nomi.update({k: ("f", f) for k, f in self.funzioni[n.module].items()}); continue
            if a.name not in self.funzioni[n.module]: raise _NonRiconosciuto(n, f"«{a.name}» non è un costruttore ammesso del modulo {n.module}")
            self.nomi[a.asname or a.name] = ("f", self.funzioni[n.module][a.name])

    def aggiungi(self, c):
        f = c.func
        if f.attr not in ("append", "extend") or not isinstance(f.value, ast.Name): raise _NonRiconosciuto(c, "chiamata non ammessa (solo NOME.append(…) e NOME.extend(…))")
        lst = self.variabile(f.value)
        if not isinstance(lst, list): raise _NonRiconosciuto(c, f"«{f.value.id}» non è un elenco")
        if c.keywords or len(c.args) != 1 or isinstance(c.args[0], ast.Starred): raise _NonRiconosciuto(c, f"{f.attr} vuole un solo valore")
        v = self.valore(c.args[0], 0)
        if f.attr == "extend":
            if not isinstance(v, (list, tuple)): raise _NonRiconosciuto(c, "extend vuole un elenco")
            self.misura(len(lst) + len(v), c); self.costo(c, elementi=len(v)); lst.extend(v)
        else: self.misura(len(lst) + 1, c); self.costo(c, elementi=1); lst.append(v)

    def variabile(self, n):
        v = self.nomi.get(n.id)
        if v is None: raise _NonRiconosciuto(n, f"nome sconosciuto «{n.id}»")
        if v[0] == "f": raise _NonRiconosciuto(n, f"«{n.id}» si può solo chiamare: {n.id}(…)")
        return v[1]

    # ---- espressioni
    def valore(self, n, prof):
        if prof > MAX_PROFONDITA: raise _NonRiconosciuto(n, "espressione troppo annidata")
        if isinstance(n, ast.Constant): return self.costante(n)
        if isinstance(n, ast.Name): return self.variabile(n)
        if isinstance(n, (ast.List, ast.Tuple)):
            out = self.elenco(n.elts, prof, n); return out if isinstance(n, ast.List) else tuple(out)
        if isinstance(n, ast.UnaryOp):
            v = self.valore(n.operand, prof + 1)
            if not isinstance(n.op, (ast.USub, ast.UAdd)) or not _numero(v): raise _NonRiconosciuto(n, "solo + e - davanti a un numero")
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp): return self.operazione(n, prof)
        if isinstance(n, ast.Call): return self.chiamata(n, prof)
        raise _NonRiconosciuto(n, f"espressione non ammessa ({_ESPRESSIONI.get(type(n)) or type(n).__name__})")

    def costante(self, n):
        v = n.value
        if isinstance(v, str):
            if len(v) > MAX_TESTO: raise _NonRiconosciuto(n, "testo troppo lungo")
            return v
        if v is None or isinstance(v, bool): return v
        if _numero(v): return self.numero(v, n)
        raise _NonRiconosciuto(n, f"valore non ammesso ({type(v).__name__})")

    def numero(self, v, n):
        if (isinstance(v, float) and not math.isfinite(v)) or abs(v) > MAX_NUMERO: raise _NonRiconosciuto(n, "numero troppo grande")
        return v

    def elenco(self, nodi, prof, n):
        out = []
        for e in nodi:
            if isinstance(e, ast.Starred):
                v = self.valore(e.value, prof + 1)
                if not isinstance(v, (list, tuple)): raise _NonRiconosciuto(e, "*… vuole un elenco")
                out.extend(v)
            else: out.append(self.valore(e, prof + 1))
            self.misura(len(out), n)
        self.costo(n, elementi=len(out))
        return out

    def operazione(self, n, prof):
        a, b = self.valore(n.left, prof + 1), self.valore(n.right, prof + 1)
        if isinstance(n.op, ast.Add): return self.somma(a, b, n)
        if isinstance(n.op, (ast.Sub, ast.Mult, ast.Div)) and _numero(a) and _numero(b):
            if isinstance(n.op, ast.Div) and b == 0: raise _NonRiconosciuto(n, "divisione per zero")
            return self.numero(a - b if isinstance(n.op, ast.Sub) else a * b if isinstance(n.op, ast.Mult) else a / b, n)
        raise _NonRiconosciuto(n, "operazione non ammessa (solo + - * / tra numeri e + tra elenchi o testi)")

    def somma(self, a, b, n):
        if _numero(a) and _numero(b): return self.numero(a + b, n)
        if isinstance(a, str) and isinstance(b, str):
            if len(a) + len(b) > MAX_TESTO: raise _NonRiconosciuto(n, "testo troppo lungo")
            self.costo(n, caratteri=len(a) + len(b)); return a + b
        if isinstance(a, (list, tuple)) and type(a) is type(b): self.misura(len(a) + len(b), n); self.costo(n, elementi=len(a) + len(b)); return a + b
        raise _NonRiconosciuto(n, "+ ammesso solo tra numeri, tra testi o tra elenchi")

    def misura(self, k, n):
        if k > MAX_LISTA: raise _NonRiconosciuto(n, "elenco troppo lungo")

    def costo(self, n, caratteri=0, elementi=0):
        """memoria usata da tutto il file: testi ed elenchi costruiti si sommano (un file piccolo non può chiedere gigabyte, VER-005)"""
        self.caratteri += caratteri; self.elementi += elementi
        if self.caratteri > MAX_TESTI_COSTRUITI: raise _NonRiconosciuto(n, "troppo testo costruito con + (il file chiederebbe troppa memoria)")
        if self.elementi > MAX_ELEMENTI_COSTRUITI: raise _NonRiconosciuto(n, "elenchi troppo grandi (il file chiederebbe troppa memoria)")

    def argomenti(self, nome, legati, n):
        """tipi degli argomenti di un costruttore, controllati PRIMA di chiamarlo (VER-005): un elenco dove ci va un numero o
        un testo diventerebbe, con str(), un testo di gigabyte. Ammessi: valori semplici; col, bd (e bw, z di DUO) piccoli
        elenchi di valori semplici; it una foto; nelle pagine I e W al massimo MAX_ELEMENTI elementi"""
        for k, v in legati.arguments.items():
            if nome in _PAGINA:
                if sum(len(x) if isinstance(x, list) else 1 for x in v) > MAX_ELEMENTI: raise _NonRiconosciuto(n, f"troppi elementi in una pagina (al massimo {MAX_ELEMENTI})")
            elif k == "it":
                if not isinstance(v, (dict, _Elemento)): raise _NonRiconosciuto(n, f"valori non validi per {nome}(…): il primo argomento deve essere una foto")
            elif k in ("col", "bd") or (nome == "DUO" and k in ("bw", "z")):
                if v is None and k == "bd": continue
                if not isinstance(v, (list, tuple)) or len(v) > 4 or not all(isinstance(x, _SEMPLICI) for x in v): raise _NonRiconosciuto(n, f"valori non validi per {nome}(…): «{k}» deve essere un piccolo elenco di valori")
                if k == "bd" and (len(v) != 2 or not isinstance(v[1], str)): raise _NonRiconosciuto(n, f'valori non validi per {nome}(…): «bd» deve essere (millimetri, "#rrggbb")')
            elif not isinstance(v, _SEMPLICI) or (k == "tx" and not isinstance(v, str)): raise _NonRiconosciuto(n, f"valori non validi per {nome}(…): «{k}» deve essere " + ("un testo" if k == "tx" else "un numero o un testo"))

    def chiamata(self, n, prof):
        if not isinstance(n.func, ast.Name): raise _NonRiconosciuto(n, "chiamata non ammessa (solo i costruttori del motore, come P(…) o FREE(…))")
        v = self.nomi.get(n.func.id)
        if v is None or v[0] != "f": raise _NonRiconosciuto(n, f"«{n.func.id}» non è un costruttore del motore" + ("" if v else " (o manca «from album import *»)"))
        fn, nome = v[1], n.func.id
        args = self.elenco(n.args, prof, n); kw = {}
        for k in n.keywords:
            if k.arg is None: raise _NonRiconosciuto(k.value, "**argomenti non ammessi")
            kw[k.arg] = self.valore(k.value, prof + 1)
        try: legati = inspect.signature(fn).bind(*args, **kw)
        except TypeError as e: raise _NonRiconosciuto(n, f"argomenti non validi per {nome}(…): {e}") from None
        self.argomenti(nome, legati, n)
        try: return fn(*args, **kw)
        except KeyError as e: raise _NonRiconosciuto(n, f"la foto «{e.args[0]}» non è nel progetto") from None
        except (TypeError, ValueError, AttributeError, IndexError, ZeroDivisionError, OverflowError) as e: raise _NonRiconosciuto(n, f"valori non validi per {nome}(…): {e}") from None


def _numero(v): return isinstance(v, (int, float)) and not isinstance(v, bool)


def _albero(testo, nome):
    if len(testo) > MAX_BYTE: raise ErroreProgetto(f"{nome} è troppo grande per essere un album ({len(testo) // 1024} KB)")
    try: sorgente = testo.decode("utf-8-sig")
    except UnicodeDecodeError as e: raise ErroreProgetto(f"{nome} non è un testo UTF-8 (byte {e.start})") from None
    try: albero = ast.parse(sorgente, nome)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as e:          # ValueError e RecursionError: Python 3.10-3.11 (byte nulli, annidamenti)
        raise errore_istruzioni(nome, getattr(e, "lineno", None) or 0, f"il testo non è scritto correttamente ({getattr(e, 'msg', e)})") from None
    if sum(1 for _ in ast.walk(albero)) > MAX_NODI: raise ErroreProgetto(f"{nome} è troppo complesso per essere un album")
    return albero


def leggi(testo, nome=SPEC, prova=False):
    """SPREADS di uno spec.py (bytes) come li darebbe la 1.x: [[modo, [elementi]], [modo, [elementi]]] per spread.
    Il motore dev'essere caricato con il progetto (i nomi delle foto); con prova=True si controlla solo la grammatica e la
    struttura, senza progetto (gli elementi sono segnaposto). Errori: ErroreProgetto con riga e motivo."""
    albero = _albero(testo, nome); let = _Lettore(_funzioni(prova))
    try:
        for n in albero.body: let.istruzione(n)
    except _NonRiconosciuto as e: raise errore_istruzioni(nome, e.riga, e.motivo) from None
    sp = let.nomi.get("SPREADS")
    if sp is None or sp[0] != "v": raise ErroreProgetto(f"{nome}: manca SPREADS = [ … ] (l'elenco degli spread)")
    return _struttura(sp[1], nome)


def _struttura(sp, nome):
    if not isinstance(sp, (list, tuple)): raise ErroreProgetto(f"{nome}: SPREADS deve essere un elenco di spread [ … ]")
    if len(sp) > MAX_SPREAD: raise ErroreProgetto(f"{nome}: troppi spread (al massimo {MAX_SPREAD})")
    out = []; elementi = caratteri = 0
    for k, s in enumerate(sp, 1):
        if not isinstance(s, (list, tuple)) or len(s) != 2: raise ErroreProgetto(f"{nome}, spread {k}: deve avere due pagine (sinistra, destra)")
        pagine = []
        for lato, pg in zip(("sinistra", "destra"), s):
            if not (isinstance(pg, tuple) and len(pg) == 2 and isinstance(pg[0], str) and pg[0] in _PAGINA and isinstance(pg[1], list)):
                raise ErroreProgetto(f"{nome}, spread {k}, pagina {lato}: deve essere I(…) o W(…)")
            if len(pg[1]) > MAX_ELEMENTI: raise ErroreProgetto(f"{nome}, spread {k}, pagina {lato}: troppi elementi (al massimo {MAX_ELEMENTI})")
            for j, it in enumerate(pg[1], 1):
                if not (isinstance(it, _Elemento) or (isinstance(it, dict) and it.get("k") in ("p", "full", "f", "t"))):
                    raise ErroreProgetto(f"{nome}, spread {k}, pagina {lato}, elemento {j}: non è una foto né un testo")
                caratteri += len(it["tx"]) if isinstance(it, dict) and isinstance(it.get("tx"), str) else 0
            elementi += len(pg[1])                 # lo stesso elenco ripetuto in tanti spread costa ogni volta (VER-005)
            if elementi > MAX_ELEMENTI_ALBUM: raise ErroreProgetto(f"{nome}: troppi elementi nell'album (al massimo {MAX_ELEMENTI_ALBUM})")
            if caratteri > MAX_TESTO_ALBUM: raise ErroreProgetto(f"{nome}: troppo testo nell'album (al massimo {MAX_TESTO_ALBUM} caratteri)")
            pagine.append([pg[0], list(pg[1])])
        out.append(pagine)
    return out


def leggi_file(path, prova=False):
    with open(path, "rb") as f: testo = f.read(MAX_BYTE + 1)
    return leggi(testo, os.path.basename(path), prova)


# ---------------------------------------------------------------- scrittura (Esporta per la versione 1.x)
def is_txt(it): return it["k"] == "t" and it.get("kind") == "txt"                # livelli di testo (strumento Testo)


def ha_liberi(spreads):
    """True se l'impaginazione usa cornici libere, angoli, bordi/ombre/opacità o testi liberi: allora spec.py ha bisogno
    di album_libere.py"""
    return any(it["k"] == "f" or it.get("a") or it.get("bd") or it.get("sh") or it.get("oc", 100) < 100 or "fx" in it for sp in spreads for pg in sp for it in pg[1])


def _lead(it):
    from .motore import testo
    return testo.lead(it)


def fmt0(it, nome_foto):
    """un elemento come chiamata del motore (senza angolo e stile); ogni valore scritto con repr: un dato resta un dato"""
    if is_txt(it):
        return ("TEXT(%r, %r, %r, %r, %r, font=%r, size=%r, col=%r, al=%r, tr=%r, auto=%r" % (it["tx"], it["fx"], it["fy"], it["fw"], it["fh"], it["font"], it["size"], tuple(it["col"]), it["al"], it["tr"], bool(it.get("auto", True)))) + (f', lh={_lead(it)!r}' if _lead(it) != 1.2 else "") + (", caps=True" if it.get("caps") else "") + (f', zo={it["zo"]!r}' if it.get("zo") is not None else "") + (f', stile={it["stile"]!r}' if it.get("stile") else "") + ")"
    if it["k"] == "t":
        if "fx" in it: return f'TXTF({it["kind"]!r}, {it["fx"]!r}, {it["fy"]!r}, {it["fw"]!r}, {it["fh"]!r}, ts={it.get("ts", 1.0)!r}' + (f', zo={it["zo"]!r}' if it.get("zo") is not None else "") + ")"
        return f'TXT({it["kind"]!r}, {it["c"]!r}, {it["r"]!r}, {it["w"]!r}, {it["h"]!r})'
    n = nome_foto(it["i"]); ex = (", bw=True" if it.get("bw") else "") + (f', z={it["z"]!r}' if it.get("z", 1.0) != 1.0 else "") + (f', zo={it["zo"]!r}' if it["k"] == "f" and it.get("zo") is not None else "")
    if it["k"] == "full": return f"FULL({n!r}{ex})"
    if it["k"] == "f": return f'FREE({n!r}, {it["x"]!r}, {it["y"]!r}, {it["w"]!r}, {it["h"]!r}{ex})'
    return f'P({n!r}, {it["c"]!r}, {it["r"]!r}, {it["w"]!r}, {it["h"]!r}{ex})'


def fmt(it, nome_foto):
    """un elemento come chiamata del motore, con angolo (ROT) e stile (STY)"""
    x = fmt0(it, nome_foto)
    if it["k"] != "t" and (it.get("bd") or it.get("sh") or it.get("oc", 100) < 100): x = f'STY({x}, bd={tuple(it["bd"]) if it.get("bd") else None!r}, sh={int(it.get("sh") or 0)!r}, oc={int(it.get("oc", 100))!r})'
    return f'ROT({x}, {it["a"]!r})' if it["k"] != "t" and it.get("a") else x


def descrizione(testo):
    """la riga di descrizione in alto come testo Python sicuro: niente può chiudere le virgolette (audit SEC-003)"""
    out = []
    for c in testo:
        if c in '\\"': out.append("\\" + c)
        elif ord(c) < 32 or ord(c) == 127 or "\ud800" <= c <= "\udfff": out.append(f"\\x{ord(c):02x}" if ord(c) < 256 else f"\\u{ord(c):04x}")
        else: out.append(c)
    return '"""' + "".join(out) + '"""'


def testo_spec(spreads, nome, nome_foto, quando=None):
    """contenuto di spec.py per l'impaginazione `spreads` ([[modo, [elementi]], [modo, [elementi]]] per spread);
    nome_foto(i) dà il nome del file (senza estensione) della foto numero i"""
    quando = time.strftime("%d/%m/%Y %H:%M") if quando is None else quando
    lines = [descrizione(f"{nome}: {len(spreads)} spread. Salvato dall'editor il {quando}."), "from album import *"]
    if ha_liberi(spreads): lines.append("from album_libere import *     # cornici libere FREE(...) e angoli ROT(...): serve questo file, sta nella cartella del progetto")
    lines += ["", "SPREADS = ["]
    for k, sp in enumerate(spreads, 1):
        pages = [f'{pg[0]}(' + ", ".join(fmt(it, nome_foto) for it in pg[1]) + ")" for pg in sp]
        lines.append(f"    # {k}\n    ({pages[0]},\n     {pages[1]}),")
    lines.append("]")
    return "\n".join(lines) + "\n"


def copia_motore(cartella):
    """mette accanto a spec.py le copie di album_libere.py, testo.py e vib_lut.npz (servono agli script delle versioni 1.x)"""
    from . import risorse
    mot = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motore")
    shutil.copy2(os.path.join(mot, "album_libere.py"), os.path.join(cartella, "album_libere.py"))
    shutil.copy2(os.path.join(mot, "testo.py"), os.path.join(cartella, "testo.py"))
    shutil.copy2(risorse.percorso("vib_lut.npz"), os.path.join(cartella, "vib_lut.npz"))


def esporta(cartella, spreads, nome, nome_foto, quando=None):
    """scrive spec.py (formato 1.x) nella cartella e, se servono, le copie del motore: per aprire il progetto con la 1.x"""
    from .formato import scrivi_atomico
    if ha_liberi(spreads): copia_motore(cartella)
    scrivi_atomico(os.path.join(cartella, SPEC), testo_spec(spreads, nome, nome_foto, quando))
