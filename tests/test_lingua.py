"""Lingua dei testi (T-206): una sola tabella per pagine e server, italiano e inglese con le stesse chiavi e gli stessi
parametri; nessun testo visibile fuori dalla tabella (per quanto si può controllare); numeri e date secondo la lingua;
lingua del sistema al primo avvio, scelta dell'utente salvata nelle sue preferenze.

Come si riconosce un testo visibile fuori dalla tabella (prosa()): parole con le lettere maiuscole e minuscole di una
frase, articoli e preposizioni italiani o inglesi, lettere accentate. Restano fuori da questo controllo i nomi propri
del programma e dei formati (ELENCO_LIBERO) e le righe segnate «non tradotto: <motivo>» accanto al testo (il motivo è
obbligatorio, come per i pragma della copertura)."""
import ast
import html.parser
import json
import os
import re
import sys

import pytest

import impaginatore
from impaginatore import lingua, risorse
from impaginatore.piattaforma import lingua as lingua_sistema

SRC = os.path.dirname(os.path.abspath(impaginatore.__file__))
PAGINE = ("home.html", "index.html")
SEGNAPOSTO = re.compile(r"\{(\w+)\}")
ESTENSIONI = ("html", "log", "json", "py", "css", "js", "jsx", "txt", "png", "jpg", "jpeg", "pdf", "psd", "zip", "npz", "woff2", "tmp", "command", "app")

# moduli Python fuori dal controllo, con il motivo; tutti gli altri moduli del pacchetto si controllano
ESCLUSI = {
    "formato_1x.py": "legge e scrive spec.py delle versioni 1.x, che esistevano solo in italiano: nessun utente inglese ha un progetto 1.x",
    "motore/": "script del motore per la skill e la riga di comando (anteprima, abbina, analizza, PSD): non sono l'interfaccia",
    "cli.py": "riga di comando (aiuto di argparse): strumento per sviluppo e assistenza",
}
DENTRO = ("motore/bozza.py", "motore/spazi.py", "motore/album.py", "motore/genera_psd.py")      # del motore, ma i loro testi arrivano all'editor e all'assistente
PAROLE_FUNZIONE = set("""il lo la i gli le un uno una di del dello della dei degli delle da dal dallo dalla dai dalle in nel nello nella
nei negli nelle con su sul sullo sulla sui sulle per tra fra che non è e ed o ma se ci si al allo alla ai agli alle questo questa
questi queste ti tu tuo tua tuoi tue già più può puoi sono hai ha ho the a an to of and or on for with is are not this that your
you be it its from into by at as was were has have""".split())
ELENCO_LIBERO = {"Impaginatore", "Enter", "Escape", "Tab", "Delete", "Backspace", "Shift", "Alt", "Meta", "Control", "Home", "End",
                 "Space", "Ctrl", "Newsreader", "Photoshop", "Claude", "Finder", "Helvetica", "Arial", "Stefano", "Imperato",
                 "Italiano", "English", "Album", "Spread", "Pro", "Studio", "Essenziale", "Essential", "Laboratorio"}


# ---------------------------------------------------------------- strumenti del controllo
def prosa(s, pagina=True):
    """il testo sembra una frase o una parola per l'utente? (vedi il docstring del modulo). pagina: anche una parola sola
    con l'iniziale maiuscola («Testo») e i titoli («Testo (titolo)»); nel Python servono articoli, preposizioni o accenti
    (lì le parole con la maiuscola sono nomi di cartelle di sistema, intestazioni HTTP, programmi)"""
    s = SEGNAPOSTO.sub(" ", s)
    if re.fullmatch(r"[a-z0-9_]+(\.[a-z0-9_]+)+|[A-Za-z0-9]+([_-][A-Za-z0-9]+)+", s.strip()): return False         # chiavi, moduli, costanti, codici («it-IT»)
    if re.search(r"[{}=\[\]*]|(^|;)\s*[a-z-]+\s*:\s*[^;]+;|^\s*[#.\[/@]|^(data|https?|file|blob|javascript|about|mailto):|--[a-z]|=>|\b(var|calc|rgba?|url)\(", s): return False      # CSS, selettori, percorsi, codice
    if s.count("(") >= 3 or re.match(r"\s*(on run|tell application|POSIX path|with timeout|end run|Dim |import )", s): return False                          # script (AppleScript, VBS, Python)
    parole = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’][A-Za-zÀ-ÖØ-öø-ÿ]+)*", s)
    if not parole: return False
    lunghe = [p for p in parole if len(p) >= 2]
    if any(re.search(r"[À-ÖØ-öø-ÿ]", p) for p in parole) and any(len(p) >= 3 for p in parole): return True
    if len(lunghe) >= 2 and any(p.lower() in PAROLE_FUNZIONE or "'" in p or "’" in p for p in parole): return True
    if not pagina: return False
    if len(lunghe) >= 2 and re.match(r"\s*[A-ZÀ-Ý][a-zà-ÿ]+[\s:,·(]", s): return True                               # «Testo (titolo)», «Ritaglio: trascina»
    return len(parole) == 1 and re.fullmatch(r"\W*[A-ZÀ-Ý][a-zà-ÿ]{2,}\W*", s) is not None and parole[0] not in ELENCO_LIBERO


def segnata(righe, da, a):
    return any("non tradotto:" in righe[i - 1] and len(righe[i - 1].split("non tradotto:", 1)[1].strip()) > 3 for i in range(da, a + 1))


def moduli():
    out = []
    for r, _, fs in os.walk(SRC):
        for f in fs:
            rel = os.path.relpath(os.path.join(r, f), SRC).replace(os.sep, "/")
            if f.endswith(".py") and (rel in DENTRO or not rel.startswith(tuple(ESCLUSI))): out.append(os.path.join(r, f))
    return sorted(out)


def stringhe_python(percorso):
    """(riga, testo) dei testi del modulo che possono arrivare all'utente: niente docstring, registri, print, argparse,
    espressioni regolari, chiavi della tabella"""
    sorgente = open(percorso, encoding="utf-8").read(); righe = sorgente.split("\n"); albero = ast.parse(sorgente)
    salta = set()
    for n in ast.walk(albero):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
            salta.add(id(n.body[0].value))
        if isinstance(n, ast.Call):
            f = n.func; nome = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            base = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
            if (base in ("log", "logging", "_log") or nome in ("print", "add_argument", "ArgumentParser", "compile", "search", "match", "fullmatch", "sub", "findall", "split")):
                for x in ast.walk(n): salta.add(id(x))
    out = []
    for n in ast.walk(albero):
        if id(n) in salta: continue
        if isinstance(n, ast.JoinedStr):
            testo = "".join(v.value if isinstance(v, ast.Constant) else "{x}" for v in n.values)
            for v in n.values: salta.add(id(v))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str): testo = n.value
        else: continue
        if prosa(testo, False) and not segnata(righe, n.lineno, n.end_lineno): out.append((n.lineno, testo[:90]))
    return sorted(set(out))


def stringhe_js(js):
    """(riga, testo) delle stringhe e delle parti fisse dei modelli `…${}…` di uno script, senza commenti e regex"""
    out, i, n, riga = [], 0, len(js), 1
    def fine_stringa(i):                              # indice dopo la stringa che comincia in i (modelli annidati compresi)
        q = js[i]; j = i + 1
        while j < n and js[j] != q and (q == "`" or js[j] != "\n"):
            if js[j] == "\\": j += 2; continue
            if q == "`" and js.startswith("${", j): j = fine_espressione(j + 2); continue
            j += 1
        return j + 1
    def fine_espressione(j):                          # indice dopo la «}» che chiude un ${…}
        prof = 1
        while j < n and prof:
            if js[j] in "\"'`": j = fine_stringa(j); continue
            prof += {"{": 1, "}": -1}.get(js[j], 0); j += 1
        return j
    def leggi_modello(i, riga):                       # dopo il backtick: (fine, testo con {x} al posto delle espressioni); le stringhe delle espressioni vanno in out
        parti = []
        while i < n and js[i] != "`":
            if js[i] == "\\": parti.append(js[i:i + 2]); i += 2; continue
            if js.startswith("${", i):
                j = fine_espressione(i + 2)
                out.extend((riga + r - 1, t) for r, t in stringhe_js(js[i + 2:j - 1]))
                riga += js[i:j].count("\n"); parti.append(" {x} "); i = j; continue
            riga += js[i] == "\n"; parti.append(js[i]); i += 1
        return i + 1, riga, "".join(parti)
    prima = ""
    while i < n:
        c = js[i]
        if c == "\n": riga += 1; i += 1; continue
        if js.startswith("//", i): i = js.find("\n", i) if js.find("\n", i) >= 0 else n; continue
        if js.startswith("/*", i): fine = js.find("*/", i); riga += js[i:fine].count("\n"); i = fine + 2; continue
        if c in "\"'`":
            if c == "`":
                inizio = riga; fine, riga, testo = leggi_modello(i + 1, riga); out.append((inizio, testo)); i = fine
            else:
                fine = fine_stringa(i); out.append((riga, js[i + 1:fine - 1])); i = fine
            prima = "x"; continue
        if c == "/" and (not prima or prima in "(,=:[!&|?{};+-*%<>~^" or re.search(r"\b(return|typeof|case)\s*$", js[max(0, i - 8):i])):
            j = i + 1; classe = False
            while j < n and (js[j] != "/" or classe) and js[j] != "\n":
                if js[j] == "\\": j += 2; continue
                classe = (classe or js[j] == "[") and js[j] != "]"; j += 1
            i = j + 1; prima = "x"; continue
        if not c.isspace(): prima = c
        i += 1
    return out


ATTRIBUTI = re.compile(r"""\b(title|aria-label|placeholder|alt)=["']([^"'$]*)["']""")


def visibili_html_js(testo):
    """dal testo di una stringa JS: le parti visibili (senza tag) e i valori degli attributi visibili"""
    attr = [v for _, v in ATTRIBUTI.findall(testo)]
    senza_tag = re.sub(r"<[^>]*>", " ", re.sub(r"&[a-z]+;|&#\d+;", " ", testo))
    return [senza_tag] + attr


def script(pagina):
    s = risorse.leggi(pagina).decode("utf-8"); return s[s.index("<script nonce"):s.index("</script>")]


# ---------------------------------------------------------------- tabella
def test_stesse_chiavi_e_stessi_parametri_in_ogni_lingua():
    it = risorse.testi("it")
    assert len(it) > 600
    for lg in lingua.LINGUE:
        assert risorse.aree(lg) == risorse.aree("it"), lg
        d = risorse.testi(lg)
        assert sorted(set(it) - set(d)) == [], f"mancano in {lg}"
        assert sorted(set(d) - set(it)) == [], f"in più in {lg}"
        assert [k for k in it if sorted(SEGNAPOSTO.findall(it[k])) != sorted(SEGNAPOSTO.findall(d[k]))] == [], f"parametri diversi in {lg}"


def test_ogni_file_ha_le_sue_chiavi_una_volta():
    """«editor.…» in editor.json; nessuna chiave doppia (json la terrebbe zitta), né in un file né fra due"""
    for lg in lingua.LINGUE:
        viste = {}
        for a in risorse.aree(lg):
            coppie = json.loads(risorse.leggi(os.path.join("testi", lg, a + ".json")).decode("utf-8"), object_pairs_hook=lambda p: p)
            for k, v in coppie:
                assert k.startswith(a + ".") and re.fullmatch(r"[a-z0-9_]+(\.[a-z0-9_]+)+", k), (lg, a, k)
                assert k not in viste, (lg, k, viste.get(k)); viste[k] = a
                assert isinstance(v, str) and v.strip() and v == v.strip(), (lg, k)


def test_testi_senza_markup_e_con_parametri_nominati():
    """niente HTML nei testi (le pagine li mettono con textContent o con tH, che li protegge); parametri «{nome}»"""
    for lg in lingua.LINGUE:
        for k, v in risorse.testi(lg).items():
            assert "<" not in v and ">" not in v.replace("->", ""), (lg, k)
            assert all(re.fullmatch(r"[a-z_][a-z0-9_]*", x) for x in SEGNAPOSTO.findall(v)), (lg, k)
            assert "{" not in SEGNAPOSTO.sub("", v) and "}" not in SEGNAPOSTO.sub("", v), (lg, k)


def test_inglese_tradotto_davvero():
    """un testo inglese uguale all'italiano va bene solo se non ha parole italiane (Album, Spread, JPG…); niente «»"""
    it, en = risorse.testi("it"), risorse.testi("en")
    uguali = [k for k in en if en[k] == it[k] and prosa(it[k]) and len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", it[k])) > 1]
    assert uguali == []
    assert [k for k, v in en.items() if "«" in v or "»" in v] == []
    italiane = re.compile(r"\b(il|della|delle|degli|nella|questo|questa|sono|perché|più|già|foto|spread\w* \d+–\d+ e)\b")
    assert [k for k, v in en.items() if italiane.search(v) and not re.fullmatch(r"[^a-z]*", v)] == []


# ---------------------------------------------------------------- chiavi usate dal codice
def corpus():
    testi = []
    for r, _, fs in os.walk(SRC):
        testi += [open(os.path.join(r, f), encoding="utf-8").read() for f in fs if f.endswith((".py", ".html"))]
    return "\n".join(testi)


def chiavi_nel_codice():
    """le stringhe del codice che hanno la forma di una chiave della tabella (area nota, niente estensioni di file)"""
    aree = "|".join(risorse.aree("it"))
    forma = re.compile(rf"(?:{aree})\.[a-z0-9_]+(?:\.[a-z0-9_]+)*")
    trovate = set()
    for r, _, fs in os.walk(SRC):
        for f in fs:
            p = os.path.join(r, f)
            if f.endswith(".py"):
                for n in ast.walk(ast.parse(open(p, encoding="utf-8").read())):
                    if isinstance(n, ast.Constant) and isinstance(n.value, str) and forma.fullmatch(n.value): trovate.add(n.value)
            elif f.endswith(".html"):
                s = open(p, encoding="utf-8").read()
                trovate |= set(re.findall(rf"""["'`]((?:{aree})\.[a-z0-9_.]+)["'`]""", s))
    return {k for k in trovate if not k.endswith((".", "_")) and k.rsplit(".", 1)[1] not in ESTENSIONI}


def test_ogni_chiave_usata_e_nella_tabella():
    """ogni chiave scritta nel codice c'è (o è l'inizio di chiavi composte: "editor.vuoto.foto" + "_tit")"""
    t = risorse.testi("it")
    assert sorted(k for k in chiavi_nel_codice() if k not in t and not any(x.startswith((k + "_", k + ".")) for x in t)) == []


def test_nessuna_chiave_inutile():
    """ogni testo della tabella è usato: per intero, al plurale (tn("x.giorni") per x.giorni_1 e x.giorni_n), oppure con un
    prefisso che il codice compone («editor.ctl.» + …, LIV[x] + "_h"; l'area da sola, «editor.», non conta)"""
    c = corpus(); t = risorse.testi("it")
    def usata(k):
        if re.search(r"""["'`]""" + re.escape(k) + r"""["'`]""", c): return True
        for i in range(len(k) - 1, k.index(".") + 1, -1):
            if k[i] in "._" and re.search(r"""["'`]""" + re.escape(k[:i]) + r"""[._]?(["'`]|\$\{)""", c): return True
        return False
    assert sorted(k for k in t if not usata(k)) == []


def test_parametri_delle_chiamate_python():
    """t("chiave", a=…) passa tutti i parametri che il testo chiede"""
    t = risorse.testi("it"); errori = []
    for p in moduli() + [os.path.join(SRC, "lingua.py")]:
        for n in ast.walk(ast.parse(open(p, encoding="utf-8").read())):
            if not (isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value in t): continue
            f = n.func; nome = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nome not in ("t", "tn") or any(k.arg is None for k in n.keywords): continue
            dati = {k.arg for k in n.keywords} | ({"n"} if nome == "tn" else set())
            mancano = set(SEGNAPOSTO.findall(t[n.args[0].value])) - dati
            if mancano: errori.append((os.path.relpath(p, SRC), n.lineno, n.args[0].value, sorted(mancano)))
    assert errori == []


# ---------------------------------------------------------------- testi fuori dalla tabella
class _Markup(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.dentro, self.trovati = None, []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.dentro = tag
        for k, v in attrs:
            if k in ("title", "aria-label", "placeholder", "alt") and v and prosa(v): self.trovati.append((self.getpos()[0], k, v))
    def handle_endtag(self, tag):
        if tag == self.dentro: self.dentro = None
    def handle_data(self, data):
        if not self.dentro and re.search(r"[A-Za-zÀ-ÿ]{2,}", data) and [w for w in re.findall(r"[A-Za-zÀ-ÿ]{2,}", data) if w not in ELENCO_LIBERO | {"JPG", "PDF", "PSD", "sRGB", "IMP"}]:
            self.trovati.append((self.getpos()[0], "testo", data.strip()[:80]))


@pytest.mark.parametrize("pagina", PAGINE)
def test_pagine_senza_testi_nel_markup(pagina):
    """nel markup delle pagine restano solo i segni (⋯, ✕, ×), le sigle dei formati e il nome del programma"""
    m = _Markup(); m.feed(risorse.leggi(pagina).decode("utf-8"))
    assert m.trovati == []


@pytest.mark.parametrize("pagina", PAGINE)
def test_pagine_senza_testi_nello_script(pagina):
    """nessuna frase o parola per l'utente scritta nello script: tutte passano da t()/tH() (per quanto si riconosce)"""
    righe = script(pagina).split("\n"); trovati = []
    for r, testo in stringhe_js(script(pagina)):
        if segnata(righe, r, r): continue
        if any(prosa(x) for x in visibili_html_js(testo)): trovati.append((r, testo[:90]))
    assert trovati == []


@pytest.mark.parametrize("pagina", PAGINE)
def test_pagine_proteggono_i_parametri(pagina):
    """dentro l'HTML costruito a mano un testo della tabella entra con tH() (o escH/esc), mai con t() nudo"""
    s = script(pagina)
    nudi = [r for r in s.split("\n") if re.search(r"(innerHTML|insertAdjacentHTML|outerHTML)", r) and re.search(r"\$\{\s*(t|TT|tn)\(", r)]
    assert nudi == []


@pytest.mark.parametrize("modulo", [os.path.relpath(p, SRC) for p in moduli()])
def test_moduli_senza_testi_fuori_tabella(modulo):
    """i testi che i server e gli strumenti mandano all'utente passano da lingua.t (o sono segnati «non tradotto: …»)"""
    assert stringhe_python(os.path.join(SRC, modulo)) == []


def test_esclusioni_motivate():
    assert all(len(v) > 20 for v in ESCLUSI.values())
    assert {os.path.relpath(p, SRC).replace(os.sep, "/") for p in moduli()} >= set(DENTRO) | {"editor/server.py", "mcp/strumenti.py", "licenze/__init__.py"}


def test_il_controllo_riconosce_i_testi():
    """prosa() riconosce frasi, parole e attributi visibili; lascia stare codice, classi, CSS e chiavi"""
    for s in ("Ritaglio: trascina la foto", "Testo (titolo)", "Testo", "⇄ scambia la foto", "Più chiara", "Spread {n} di {m}", "Drag to move the photo",
              "Riprova; se succede ancora, chiudi", "errore: la foto non c'è"):
        assert prosa(s), s
    for s in ("slot txt sel", "position:fixed;z-index:40", "#slots > div", "editor.sel.altro", "Enter", "veil sheet", "text/plain",
              "500 16px var(--serif)", "M5 6V4h14v2", "", "12", "Impaginatore", "a b"):
        assert not prosa(s), s
    assert stringhe_js('const a = "uno", b = `<b title="Ciao a tutti">${x ? "Sì" : "no"}</b> e il resto`; // commento\n/re"x/.test(y);')[:1] == [(1, "uno")]
    assert [t for _, t in stringhe_js('x = `a ${f(`b ${"c"}`)} d`; y = /\\/"/; z = \'e\';')] == ["c", "b  {x} ", "a  {x}  d", "e"]
    assert any(prosa(x) for x in visibili_html_js('<b title="Chiudi la finestra">x</b>'))
    assert segnata(["x = 'Ciao' // non tradotto: nome di un font"], 1, 1) and not segnata(["x = 'Ciao' // non tradotto:"], 1, 1)


# ---------------------------------------------------------------- lingua.py
@pytest.fixture
def senza_cache(monkeypatch):
    monkeypatch.setattr(lingua, "_SCELTA", {"firma": None, "lingua": None})
    yield


def test_testo_con_parametri_e_lingua(senza_cache):
    assert lingua.t("comune.annulla", "it") == "Annulla" and lingua.t("comune.annulla", "en") == "Cancel"
    assert lingua.t("comune.elenco", "it", primi="A, B", ultimo="C") == "A, B e C"
    assert lingua.t("comune.elenco", "en", primi="A", ultimo=2.5) == "A and 2.5"
    assert lingua.t("comune.elenco", "it", primi="A", ultimo=2.5) == "A e 2,5"
    assert lingua.t("comune.elenco", "it", primi="A") == "A e {ultimo}", "un parametro che manca resta com'è"
    assert lingua.t("comune.non_c_e") == "comune.non_c_e"
    assert lingua.elenco([], "it") == "" and lingua.elenco(["Pro"], "en") == "Pro" and lingua.elenco(["Pro", "Studio"], "en") == "Pro and Studio"
    assert lingua.elenco(["A", "B", "C"], "it") == "A, B e C"
    assert lingua.t("comune.elenco", "it", primi=True, ultimo=None) == "True e None"


def test_plurale(monkeypatch):
    monkeypatch.setattr(lingua, "_TABELLE", {"it": {"x.g_1": "{n} giorno", "x.g_n": "{n} giorni"}, "en": {"x.g_1": "{n} day", "x.g_n": "{n} days in {m}"}})
    assert lingua.tn("x.g", 1, "it") == "1 giorno" and lingua.tn("x.g", 0, "it") == "0 giorni" and lingua.tn("x.g", 1500, "en", m=2.5) == "1,500 days in 2.5"


def test_numeri_date_e_ore():
    n = lingua.num
    assert (n(22.5, lingua="it"), n(22.5, lingua="en"), n(2.0, lingua="it"), n(0.126, lingua="it")) == ("22,5", "22.5", "2", "0,13")
    assert (n(1234, lingua="it"), n(12345, lingua="it"), n(1234, lingua="en"), n(1234.5, lingua="en")) == ("1234", "12.345", "1,234", "1,234.5")
    assert (n(3.0, 1, True, "it"), n(3, 1, True, "en"), n(-0.001, lingua="it"), n(-2.5, lingua="en")) == ("3,0", "3.0", "0", "-2.5")
    import time
    ts = time.mktime((2026, 11, 16, 10, 42, 0, 0, 0, -1))
    assert lingua.data(ts) == "16/11/2026" and lingua.ora(ts) == "10:42"


def test_lingua_del_sistema_e_scelta(monkeypatch, casa, senza_cache):
    assert lingua.da_codice("it_IT") == "it" and lingua.da_codice("IT-ch") == "it" and lingua.da_codice("de_DE") == "en"
    assert lingua.da_codice("") is None and lingua.da_codice(None) is None and lingua.da_codice("en-GB") == "en"
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en"); assert lingua.di_sistema() == "en"
    monkeypatch.delenv("IMPAGINATORE_LINGUA")
    monkeypatch.setattr(lingua_sistema, "del_sistema", lambda: "fr_FR"); assert lingua.di_sistema() == "en"
    monkeypatch.setattr(lingua_sistema, "del_sistema", lambda: None); assert lingua.di_sistema() == "it"
    monkeypatch.setattr(lingua_sistema, "del_sistema", lambda: "it_IT.UTF-8")
    assert lingua.scelta() is None and lingua.attuale() == "it"
    lingua.prima_volta(); assert json.load(open(lingua.percorso(), encoding="utf-8")) == {"formato": 1, "lingua": "it"}
    monkeypatch.setattr(lingua_sistema, "del_sistema", lambda: "en_US")
    assert lingua.attuale() == "it", "la lingua del primo avvio resta anche se il sistema cambia"
    lingua.prima_volta(); assert lingua.scelta() == "it"
    lingua.imposta("en"); assert lingua.attuale() == "en" and lingua.per_pagina() == ("en", "en-GB")
    assert lingua.t("comune.annulla") == "Cancel"
    with pytest.raises(ValueError, match="language|lingua"): lingua.imposta("de")
    with open(lingua.percorso(), "w", encoding="utf-8") as f: json.dump({"lingua": "de", "altro": 1}, f)
    assert lingua.scelta() is None
    with open(lingua.percorso(), "w", encoding="utf-8") as f: f.write("[1]")
    assert lingua.scelta() is None
    with open(lingua.percorso(), "w", encoding="utf-8") as f: f.write("{rotto")
    assert lingua.scelta() is None and lingua.attuale() == "en"
    os.remove(lingua.percorso()); assert lingua.scelta() is None


def test_prima_volta_senza_cartella_scrivibile(monkeypatch, casa, senza_cache):
    def no(_): raise PermissionError(13, "Permission denied")
    monkeypatch.setattr(lingua, "imposta", no)
    lingua.prima_volta()
    assert lingua.scelta() is None


def test_preferenze_illeggibili(monkeypatch, casa, senza_cache):
    os.makedirs(lingua.percorso())                                    # una cartella al posto del file: OSError
    assert lingua.scelta() is None


# ---------------------------------------------------------------- piattaforma/lingua.py
def test_lingua_del_sistema_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    for k in lingua_sistema.VARIABILI: monkeypatch.delenv(k, raising=False)
    assert lingua_sistema.del_sistema() is None
    monkeypatch.setenv("LANG", "C.UTF-8"); assert lingua_sistema.del_sistema() is None
    monkeypatch.setenv("LC_MESSAGES", "it_IT.UTF-8"); assert lingua_sistema.del_sistema() == "it_IT"
    monkeypatch.setenv("LANGUAGE", "en_GB:it"); assert lingua_sistema.del_sistema() == "en_GB"


def test_lingua_del_sistema_mac(monkeypatch):
    import subprocess
    monkeypatch.setattr(sys, "platform", "darwin")
    for k in lingua_sistema.VARIABILI: monkeypatch.delenv(k, raising=False)
    uscite = {"testo": '(\n    "it-IT",\n    "en-US"\n)\n'}
    monkeypatch.setattr(lingua_sistema.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 0, uscite["testo"], ""))
    assert lingua_sistema.del_sistema() == "it-IT"
    uscite["testo"] = "(\n)\n"; monkeypatch.setenv("LANG", "en_US.UTF-8"); assert lingua_sistema.del_sistema() == "en_US"
    def manca(*a, **k): raise FileNotFoundError("defaults")
    monkeypatch.setattr(lingua_sistema.subprocess, "run", manca); assert lingua_sistema.del_sistema() == "en_US"


def test_lingua_del_sistema_windows(monkeypatch):
    class K:
        @staticmethod
        def GetUserDefaultUILanguage(): return 0x0410
    class W: kernel32 = K
    monkeypatch.setattr(sys, "platform", "win32")
    for k in lingua_sistema.VARIABILI: monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(lingua_sistema.ctypes, "windll", W, raising=False)
    assert lingua_sistema.del_sistema() == "it_IT"
    monkeypatch.delattr(lingua_sistema.ctypes, "windll"); monkeypatch.setenv("LANG", "de_DE")
    assert lingua_sistema.del_sistema() == "de_DE"


# ---------------------------------------------------------------- server: lingua scelta nella schermata, pagine nella lingua
def test_lingua_dalla_schermata_album(home_srv):
    """la schermata dice la lingua in uso e le lingue (ognuna col suo nome); la scelta vale per tutto il programma e solo
    con il gettone"""
    c = home_srv; tutte = [{"id": "it", "nome": "Italiano"}, {"id": "en", "nome": "English"}]
    assert c.get("/api/lingua") == {"lingua": "it", "lingue": tutte}
    assert c.post("/api/lingua", {"lingua": "en"}) == {"lingua": "en", "lingue": tutte} and lingua.attuale() == "en"
    ok, r = c.prova("/api/lingua", {"lingua": "de"}); assert not ok and r["errore"] == "That language isn't available: choose Italian or English."
    assert c.codice("/api/lingua", {"lingua": "it"}, **{"X-Impaginatore-Gettone": None}) == 401 and lingua.attuale() == "en"
    html = c.raw("/").decode("utf-8")
    assert '<html lang="en"' in html and 'LINGUA = "en", LOCALE = "en-GB"' in html and '"comune.annulla":"Cancel"' in html.replace(": ", ":")
    assert c.post("/api/lingua", {"lingua": "it"})["lingua"] == "it" and '"comune.annulla":"Annulla"' in c.raw("/").decode("utf-8").replace(": ", ":")


def test_pagina_non_collegata_nella_lingua(monkeypatch):
    from impaginatore import servizio
    assert '<html lang="it">' in servizio.pagina_non_autorizzata() and "non è collegata" in servizio.pagina_non_autorizzata()
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    p = servizio.pagina_non_autorizzata()
    assert '<html lang="en">' in p and "<p>This tab isn&#x27;t connected to Impaginatore.</p>" in p, "il testo passa da html.escape"


def test_assistente_spiegato_se_la_licenza_non_lo_comprende(home_srv, licenza):
    """l'interruttore delle immagini si mostra solo con una licenza che comprende l'assistente; altrimenti la schermata
    dice perché (Essenziale: solo Pro e Studio)"""
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    r = home_srv.get("/api/assistente")
    assert r["consentito"] is False and r["immagini"] is False and "Essenziale" in r["motivo"] and "Pro" in r["motivo"]


def test_conflitto_con_un_altra_scheda_ha_un_codice(editor):
    """la pagina riconosce «l'album è cambiato altrove» dal codice, non dal testo (che segue la lingua)"""
    editor.post("/api/op", dict(op="evg", value=1.0, cid="a", rev=0))
    ok, r = editor.prova("/api/op", dict(op="evg", value=1.0, cid="b", rev=0))
    assert not ok and r["codice"] == "altra_scheda" and r["errore"]
    assert "codice" not in editor.prova("/api/op", dict(op="sconosciuta"))[1]


def test_esportazione_in_corso_nel_ping(editor, monkeypatch):
    """/api/ping dice se c'è un'esportazione in corso: la finestra del programma chiede conferma prima di chiudersi"""
    import threading as th
    from aiuti import attendi_log
    ferma, dentro = th.Event(), th.Event()
    def lento(*a, **k): dentro.set(); ferma.wait(30); raise OSError("interrotta")
    monkeypatch.setattr(editor.E, "_scrivi_img", lento)
    nomi = [p["n"] for p in editor.get("/api/state")["photos"]]; editor.post("/api/op", dict(op="newspreadsel", names=nomi[:3], pos=0))
    assert editor.get("/api/ping")["esporta"] is False
    editor.post("/api/export", {"fmt": "jpg", "res": "bozza"})
    assert dentro.wait(30) and editor.get("/api/ping")["esporta"] is True
    ferma.set(); attendi_log(editor)
    assert editor.get("/api/ping")["esporta"] is False
