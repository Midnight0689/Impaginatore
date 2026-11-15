"""Regressioni dell'audit 2026-11 sul formato di salvataggio: i payload dell'audit (spec.py con codice, nome del progetto
che chiude il docstring, ZIP di un collega, modelli di terzi) rifatti in modo innocuo: un file «sentinella» in una
cartella temporanea. Con il codice di prima la sentinella compariva (codice eseguito); ora no, e l'errore è chiaro.
I test che usano solo API presenti anche prima (formato.carica, home.nuovo, editor, Importa ZIP) falliscono sul codice
vecchio: è la prova che le correzioni servono."""
import ast
import json
import os
import shutil
import stat
import zipfile

import pytest

import impaginatore
from impaginatore import formato
from impaginatore.motore import album
from impaginatore.piattaforma import dialoghi

SRC = os.path.dirname(os.path.abspath(impaginatore.__file__))          # il pacchetto davvero importato (sorgente o installato)


def _progetto(base, spec, foto_campione, extra=None):
    p = os.path.join(base, "Collega"); os.makedirs(os.path.join(p, "Foto"))
    for f in os.listdir(foto_campione): shutil.copy(os.path.join(foto_campione, f), os.path.join(p, "Foto", f))
    formato.scrivi_json(os.path.join(p, "progetto.json"), dict(nome="Collega", foto=os.path.join(p, "Foto"), formato_cm=[40, 20]))
    with open(os.path.join(p, "spec.py"), "w", encoding="utf-8") as f: f.write(spec)
    for nome, testo in (extra or {}).items():
        with open(os.path.join(p, nome), "w", encoding="utf-8") as f: f.write(testo)
    return p


# (descrizione, spec.py con {S} = percorso della sentinella, riga attesa nell'errore o None, parte del motivo)
PAYLOAD = [
    ("import", 'import os\nos.makedirs({S})\nSPREADS = []\n', 1, "istruzione non ammessa (import di moduli)"),
    ("open", 'from album import *\nopen({S}, "w").write("x")\nSPREADS = []\n', 2, "chiamata non ammessa"),
    ("exec", 'from album import *\nexec("open(" + repr({S}) + ", \'w\')")\nSPREADS = []\n', 2, "chiamata a «exec» non ammessa"),
    ("__import__", 'from album import *\nSPREADS = [__import__("os").makedirs({S})]\n', 2, "chiamata non ammessa"),
    ("variabili del motore", 'from album import *\nSPREADS = [P.__globals__["os"].makedirs({S})]\n', 2, "chiamata non ammessa"),
    ("attributi", 'from album import *\nX = P.__globals__\nSPREADS = []\n', 2, "accesso ad attributi"),
    ("file del progetto", 'from album import *\nfrom aiuto import PAGINA\nSPREADS = []\n', 2, "import dal modulo «aiuto» non ammesso"),
    ("lambda", 'from album import *\nSPREADS = (lambda: open({S}, "w"))()\n', 2, "chiamata non ammessa"),
    ("comprensione", 'from album import *\nSPREADS = [open({S}, "w") for _ in [1]]\n', 2, "elenchi costruiti con for"),
    ("docstring chiuso (SEC-003)", '"""X"""; import os; os.makedirs({S}); """"""\nfrom album import *\nSPREADS = []\n', 1, "import di moduli"),
    ("getattr", 'from album import *\nSPREADS = getattr(__builtins__, "open")({S}, "w")\n', 2, "chiamata non ammessa"),
    ("dentro un costruttore", 'from album import *\nSPREADS = [(W(TXT(open({S}, "w").name, 0, 0, 1, 1)), W())]\n', 2, "accesso ad attributi"),
    ("funzione non del motore", 'from album import *\nSPREADS = [(W(TXT(open({S}, "w"), 0, 0, 1, 1)), W())]\n', 2, "«open» non è un costruttore del motore"),
    ("costruttore non importato", 'SPREADS = [(W(), W())]\n', 1, "manca «from album import *»"),
    ("funzione definita", 'from album import *\ndef f():\n    open({S}, "w")\nSPREADS = [f()]\n', 2, "definizione di funzioni"),
    ("ciclo", 'from album import *\nfor x in [1]: open({S}, "w")\nSPREADS = []\n', 2, "istruzione non ammessa (cicli)"),
    ("elenco moltiplicato", 'from album import *\nSPREADS = [W()] * 10**9\n', 2, "operazione non ammessa"),
    ("elenco che raddoppia", 'from album import *\nX = [W()]\n' + 'X = X + X\n' * 40 + 'SPREADS = X\n', 20, "elenco troppo lungo"),
    ("annidamento", 'from album import *\nSPREADS = ' + '[' * 70 + ']' * 70 + '\n', 2, "troppo annidata"),
    ("**argomenti", 'from album import *\nSPREADS = [(W(P(**{{"n": 1}})), W())]\n', 2, "**argomenti non ammessi"),
    ("argomenti sbagliati", 'from album import *\nSPREADS = [(W(P("H01", 0, 0, 6)), W())]\n', 2, "argomenti non validi per P"),
    ("foto che non c'è", 'from album import *\nSPREADS = [(W(P("NONCE", 0, 0, 6, 8)), W())]\n', 2, "la foto «NONCE» non è nel progetto"),
    ("valori sbagliati", 'from album import *\nfrom album_libere import *\nSPREADS = [(W(FREE("H01", "x", 0, 1, 1)), W())]\n', 3, "valori non validi per FREE"),
    ("costruttore come valore", 'from album import *\nX = P\nSPREADS = []\n', 2, "si può solo chiamare"),
    ("nome sconosciuto", 'from album import *\nSPREADS = [Y]\n', 2, "nome sconosciuto «Y»"),
    ("import di un nome", 'from album import os\nSPREADS = []\n', 1, "non è un costruttore ammesso"),
    ("import relativo", 'from .album import *\nSPREADS = []\n', 1, "import dal modulo «.album»"),
    ("append su un numero", 'X = 1\nX.append(2)\nSPREADS = []\n', 2, "non è un elenco"),
    ("extend di un numero", 'X = []\nX.extend(3)\nSPREADS = []\n', 2, "extend vuole un elenco"),
    ("append di due valori", 'X = []\nX.append(1, 2)\nSPREADS = []\n', 2, "vuole un solo valore"),
    ("altro metodo", 'X = []\nX.clear()\nSPREADS = []\n', 2, "chiamata non ammessa"),
    ("assegnazione doppia", 'a = b = 1\nSPREADS = []\n', 1, "si può assegnare solo a un nome"),
    ("-=", 'X = 1\nX -= 1\nSPREADS = []\n', 2, "è ammesso solo NOME += …"),
    ("espressione da sola", 'X = 1\nX\nSPREADS = []\n', 2, "espressione da sola non ammessa"),
    ("meno su un testo", 'X = -"a"\nSPREADS = []\n', 1, "solo + e - davanti a un numero"),
    ("divisione per zero", 'X = 1 / 0\nSPREADS = []\n', 1, "divisione per zero"),
    ("numero infinito", 'X = 1e300 * 1e300\nSPREADS = []\n', 1, "numero troppo grande"),
    ("numero enorme", 'X = 10000000000000\nSPREADS = []\n', 1, "numero troppo grande"),
    ("byte", 'X = b"x"\nSPREADS = []\n', 1, "valore non ammesso"),
    ("+ tra tipi diversi", 'X = [1] + "a"\nSPREADS = []\n', 1, "+ ammesso solo"),
    ("testo moltiplicato", 'X = "a" * 3\nSPREADS = []\n', 1, "operazione non ammessa"),
    ("*numero", 'X = [*1]\nSPREADS = []\n', 1, "*… vuole un elenco"),
    ("testo troppo lungo", 'X = "' + "a" * 600000 + '" + "' + "a" * 600000 + '"\nSPREADS = []\n', 1, "testo troppo lungo"),
    ("sintassi", 'from album import *\nSPREADS = [\n', 2, "non è scritto correttamente"),
    ("SPREADS non è un elenco", 'from album import *\nSPREADS = 5\n', None, "SPREADS deve essere un elenco"),
    ("manca SPREADS", 'from album import *\n', None, "manca SPREADS"),
    ("pagina sbagliata", 'from album import *\nSPREADS = [(W(), "I")]\n', None, "deve essere I(…) o W(…)"),
    ("elemento sbagliato", 'from album import *\nSPREADS = [(W(1), W())]\n', None, "non è una foto né un testo"),
    ("una pagina sola", 'from album import *\nSPREADS = [(W(),)]\n', None, "deve avere due pagine"),
    ("foto numero 0", 'from album import *\nSPREADS = [(W(P(0, 0, 0, 6, 8)), W())]\n', None, "la foto numero 0 non esiste"),
    ("valore fuori misura", 'from album import *\nSPREADS = [(W(P("H01", 0, 0, 60, 8)), W())]\n', None, "spec.py non valido: spread 1, pagina sinistra, elemento 1"),
    ("elemento non costruibile", 'from album import *\nSPREADS = [(W(P([1], 0, 0, 6, 8)), W())]\n', 2, "valori non validi per P"),
    ("elemento incompleto", 'from album import *\nfrom album_libere import *\nSPREADS = [(W(TXTF("txt", 0, 0, 1, 1)), W())]\n', None, "spec.py: un elemento non è valido"),
]


@pytest.mark.parametrize("nome, spec, riga, motivo", PAYLOAD, ids=[p[0] for p in PAYLOAD])
def test_sec001_spec_py_non_viene_mai_eseguito(tmp_path, foto_campione, nome, spec, riga, motivo):
    """SEC-001 / TEST-004: uno spec.py con istruzioni non riconosciute non si apre e niente viene eseguito"""
    S = tmp_path / "SENTINELLA"
    p = _progetto(str(tmp_path), spec.replace("{S}", repr(str(S))), foto_campione, {"aiuto.py": f"open({str(S)!r}, 'w').write('x')\nPAGINA = 'W'\n"})
    album.carica_progetto(p)
    with pytest.raises(ValueError) as e: formato.carica(p)
    assert not S.exists(), "codice del progetto eseguito"
    msg = str(e.value)
    assert motivo in msg, msg[:500]
    if riga: assert msg.startswith("Questo progetto contiene istruzioni non riconosciute") and f"riga {riga}:" in msg, msg[:500]
    assert os.path.exists(os.path.join(p, "spec.py")) and not os.path.exists(os.path.join(p, "album.json")), "un progetto che non si apre non si tocca"


def test_sec001_controllo_senza_motore(tmp_path):
    """la schermata dei progetti controlla spec.py senza caricare il motore e senza eseguire niente"""
    from impaginatore import formato_1x
    S = tmp_path / "SENTINELLA"
    assert formato_1x.leggi(b'from album import *\nSPREADS = [(W(P("x", 0, 0, 6, 8)), I(*DUO(1, 2)))]\n', prova=True)[0][1][0] == "I"
    with pytest.raises(ValueError, match=r"riga 1: istruzione non ammessa \(import di moduli\)"): formato_1x.leggi(f"import os; os.makedirs({str(S)!r})\n".encode(), prova=True)
    assert not S.exists()
    for testo, msg in [(b"\xff\xfe", "non è un testo UTF-8"), (b"x = 1\x00", "non è scritto correttamente")]:
        with pytest.raises(ValueError, match=msg): formato_1x.leggi(testo)


def test_limiti_del_lettore(monkeypatch):
    from impaginatore import formato_1x
    monkeypatch.setattr(formato_1x, "MAX_BYTE", 50)
    with pytest.raises(ValueError, match="troppo grande"): formato_1x.leggi(b"SPREADS = []  " + b" " * 60)
    monkeypatch.setattr(formato_1x, "MAX_BYTE", 4 * 2**20); monkeypatch.setattr(formato_1x, "MAX_NODI", 5)
    with pytest.raises(ValueError, match="troppo complesso"): formato_1x.leggi(b"SPREADS = [1, 2, 3, 4, 5, 6]")


def test_firme_dei_costruttori_uguali_a_quelle_del_motore():
    """il controllo senza motore usa una tabella delle firme: deve restare uguale a quella dei costruttori veri"""
    import inspect

    from impaginatore import formato_1x
    from impaginatore.motore import album_libere
    for mod, nomi in formato_1x.COSTRUTTORI.items():
        for n in nomi:
            vera = inspect.signature(getattr(album if mod == "album" else album_libere, n))
            assert [(p.name, p.kind, p.default is p.empty) for p in vera.parameters.values()] == [(p.name, p.kind, p.default is p.empty) for p in formato_1x.firma(n).parameters.values()], n


def test_sec001_zip_del_collega(home_srv, apri_editor, tmp_path):
    """SEC-001, scenario dell'audit: ZIP con spec.py che esegue codice (e un modulo Python accanto) -> Importa ZIP -> Apri"""
    S = tmp_path / "PWNED_zipspec"
    zp = tmp_path / "Album del collega.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("Album del collega/progetto.json", json.dumps({"nome": "Collega", "formato_cm": [30, 30], "foto": "/Users/collega/Foto"}))
        z.writestr("Album del collega/spec.py", f"import os\nopen({str(S)!r}, 'w').write('x')\nfrom album import *\nSPREADS = []\n")
        z.writestr("Album del collega/aiuto.py", f"open({str(S)!r}, 'w').write('x')\n")
    class Z(dialoghi.Dialoghi):
        def _scegli(self, tipo, m): return [str(zp)]
    dialoghi.imposta(Z())
    ok, r = home_srv.prova("/api/importa-zip", {})
    if ok:      # l'importazione può anche accettare la cartella (spec.py si legge solo come dati): l'apertura no
        p = r["path"]; assert not os.path.exists(os.path.join(p, "aiuto.py")), "un modulo Python non si estrae"
        ok2, r2 = home_srv.prova("/api/apri", {"path": p}); assert not ok2 and "istruzioni non riconosciute" in r2["errore"]
        with pytest.raises(ValueError, match="istruzioni non riconosciute"): apri_editor(p)
    else: assert "istruzioni non riconosciute" in r["errore"]
    assert not S.exists(), "codice del progetto eseguito"
    assert home_srv.modulo.EDITORS == {}, "nessun editor avviato per un progetto non valido"


def test_sec003_nome_del_progetto_e_un_dato(home, apri_editor, tmp_path, foto_campione, monkeypatch):
    """SEC-003: il nome dell'audit chiude il docstring di spec.py; ora è solo un valore in progetto.json"""
    monkeypatch.chdir(tmp_path); S = tmp_path / "PWNED_nome"
    nome = 'X"""; open("PWNED_nome", "w").write("x"); """'
    p = home.nuovo({"nome": nome, "w": "60", "h": "20"})
    for f in sorted(os.listdir(foto_campione))[:2]: shutil.copy(os.path.join(foto_campione, f), os.path.join(p, "Foto", f))
    c = apri_editor(p)
    assert not S.exists(), "codice nel nome eseguito"
    assert c.get("/api/state")["nome"] == nome and formato.leggi_json(os.path.join(p, "progetto.json"))["nome"] == nome
    assert '"' not in os.path.basename(p) and os.path.basename(p).startswith("X---")
    c.E.save(backup=False); c.E.inizializza(p)
    assert not S.exists()
    # anche esportato per la 1.x il nome resta dentro il testo di descrizione: nessuna altra istruzione
    from impaginatore import formato_1x
    corpo = ast.parse(formato_1x.testo_spec(c.E.SP, nome, album.name)).body
    assert [type(x).__name__ for x in corpo] == ["Expr", "ImportFrom", "Assign"] and nome in corpo[0].value.value


@pytest.mark.parametrize("nome", ["Riga 1\nriga 2", "con\ttab", "bidi\u202eexe.gpj", "zero\u200bwidth", "x" * 121, "   "])
def test_sec003_nomi_non_ammessi(home, nome):
    with pytest.raises(ValueError): home.nuovo({"nome": nome, "w": 30, "h": 30})
    assert os.listdir(home.PROGETTI) == []


def test_nomi_delle_cartelle():
    from impaginatore import nomi
    assert nomi.nome_progetto("  Matrimonio «Anna» & Luca  ") == "Matrimonio «Anna» & Luca"
    assert nomi.nome_progetto("Cafe\u0301") == "Café" and len(nomi.nome_progetto("Cafe\u0301")) == 4, "forma NFC"
    for nome, cartella in [('a<b>c:d"e/f\\g|h?i*j', "a-b-c-d-e-f-g-h-i-j"), ("CON", "_CON"), ("nul.txt", "_nul.txt"), ("Com1 ", "_Com1"), ("LPT¹", "_LPT¹"),
                           ("fine. . ", "fine"), ("...nascosta", "nascosta"), ("", "Progetto"), ("...", "Progetto"), ("x" * 200, "x" * 80),
                           ("riga\nnuova", "riga-nuova"), ("Cafe\u0301", "Café"), ("CONSOLE", "CONSOLE")]:
        assert nomi.nome_cartella(nome) == cartella, nome
    assert nomi.nome_cartella("", "Album") == "Album"
    assert [nomi.componente_valido(x) for x in ("Foto", "a.jpg", "a:b.jpg", "aux.json", "x.", "x ", "..", ".", "", "a\u202eb", "x" * 256)] == [True, True] + [False] * 9


# ---------------------------------------------------------------- SEC-009: modelli arrivati con un progetto
def test_sec009_modelli_di_terzi_non_entrano_nei_tuoi(progetto, apri_editor, casa):
    S = casa.parent / "PWNED_modelli"
    buono = {"id": "b1", "nome": "Buono", "n": 1, "lato": None, "pages": [{"mode": "I", "items": [{"k": "p", "c": 0, "r": 0, "w": 6, "h": 8}]}, {"mode": "W", "items": []}]}
    cattivi = [dict(buono, id="c1", pages=[{"mode": "I", "items": [{"k": "f", "x": 0, "y": 0, "w": 1, "h": 1, "zo": f"__import__('os').makedirs({str(S)!r})"}]}, {"mode": "W", "items": []}]),
               dict(buono, id="c2", extra="x"), dict(buono, id="../c3"), dict(buono, id="c4", n=3), "non è un modello"]
    with open(os.path.join(progetto, "modelli_utente.json"), "w", encoding="utf-8") as f: json.dump([buono] + cattivi, f)
    c = apri_editor(progetto)
    assert not os.path.exists(c.E.UT_FILE), "i modelli globali non si toccano aprendo un progetto"
    assert c.E.ut_load() == [] and [t["id"] for t in c.E.ut_progetto()] == ["b1"], "solo i modelli validi, solo per questo progetto"
    assert sum("modello tralasciato" in x for x in c.E.LOG) >= 5
    st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    t = [x for x in c.post("/api/templates", {"photos": names[:1]})["utente"] if x["id"] == "b1"][0]
    assert t["progetto"] is True
    st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="newspread", pos=0, L=t["L"], R=t["R"]))
    c.E.save(backup=False)
    assert formato.leggi_album(os.path.join(progetto, "album.json"))["spread"][0]["sinistra"]["elementi"][0]["k"] == "p"
    assert not S.exists()


def test_sec009_scenario_dell_audit(progetto, apri_editor):
    """SEC-009 come nell'audit: un progetto arriva con un modelli_utente.json che ha un modello ben fatto e uno con «zo»
    di codice; aprirlo non cambia i tuoi modelli (la 1.x li univa ai modelli globali) e il codice non arriva mai al file
    dell'impaginazione"""
    buono = {"id": "a1b2", "nome": "Del collega", "n": 1, "lato": None, "pages": [{"mode": "I", "items": [{"k": "p", "c": 0, "r": 0, "w": 6, "h": 8}]}, {"mode": "W", "items": []}]}
    cattivo = dict(buono, id="c3d4", nome="Iniettato", pages=[{"mode": "W", "items": [{"k": "f", "x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5, "zo": "__import__('os').getcwd()"}]}, {"mode": "W", "items": []}])
    with open(os.path.join(progetto, "modelli_utente.json"), "w", encoding="utf-8") as f: json.dump([buono, cattivo], f)
    c = apri_editor(progetto)
    tuoi = formato.leggi_json(c.E.UT_FILE) if os.path.exists(c.E.UT_FILE) else []
    assert [t["id"] for t in tuoi] == [], "i modelli di un progetto aperto non entrano nei tuoi"
    st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    proposti = [t["id"] for t in c.post("/api/templates", {"photos": names[:1]}).get("utente", [])]
    assert "c3d4" not in proposti, "un modello non valido non si propone"


def test_modelli_illeggibili_non_si_perdono(editor):
    c = editor
    os.makedirs(os.path.dirname(c.E.UT_FILE), exist_ok=True)
    with open(c.E.UT_FILE, "w", encoding="utf-8") as f: f.write('[{"id": "x", rotto')
    assert c.E.ut_load() == [] and os.path.exists(c.E.UT_FILE + ".illeggibile")
    altro = {"id": "fut", "nome": "Di una versione futura", "n": 1, "lato": None, "pages": [], "nuovo": 1}
    with open(c.E.UT_FILE, "w", encoding="utf-8") as f: json.dump([altro], f)
    st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]
    t = c.post("/api/templates", {"photos": names[:2]})["items"][0]; st = c.post("/api/op", dict(cid="t", rev=st["rev"], op="newspread", pos=0, L=t["L"], R=t["R"]))
    c.post("/api/modelli", {"azione": "salva", "s": 0, "nome": "Mio"})
    salvati = formato.leggi_json(c.E.UT_FILE)
    assert [t["nome"] for t in salvati] == ["Mio", "Di una versione futura"], "le voci che questa versione non capisce restano"


# ---------------------------------------------------------------- ZIP
def _segna_cifrato(path, nome):
    """mette il bit «cifrato» a una voce dell'indice dello ZIP (zipfile non scrive voci cifrate)"""
    b = bytearray(path.read_bytes()); i = b.find(b"PK\x01\x02")
    while i >= 0:
        n = int.from_bytes(b[i + 28:i + 30], "little")
        if bytes(b[i + 46:i + 46 + n]).decode() == nome: b[i + 8] |= 1
        i = b.find(b"PK\x01\x02", i + 4)
    path.write_bytes(bytes(b))


def _zip(path, voci):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, dati in voci:
            if isinstance(nome, zipfile.ZipInfo): z.writestr(nome, dati)
            else: z.writestr(nome, dati)
    return str(path)


@pytest.mark.parametrize("nome", ["../fuori.json", "/assoluto.json", "C:/x.json", "c:x.json", "a/../../fuori.json", "a\\..\\..\\fuori.json", "Foto/../../x.jpg"])
def test_zip_slip(tmp_path, nome):
    from impaginatore import archivio
    zp = _zip(tmp_path / "a.zip", [("P/progetto.json", "{}"), (nome, "x")])
    with pytest.raises(ValueError, match="non è sicuro"): archivio.estrai(zp, str(tmp_path / "dest"))
    assert not os.path.exists(tmp_path / "dest") or os.listdir(tmp_path / "dest") == []
    assert not (tmp_path / "fuori.json").exists() and not (tmp_path.parent / "fuori.json").exists()


def test_zip_con_collegamento_simbolico(tmp_path):
    from impaginatore import archivio
    zi = zipfile.ZipInfo("P/Foto/a.jpg"); zi.external_attr = (stat.S_IFLNK | 0o777) << 16
    zp = _zip(tmp_path / "a.zip", [("P/progetto.json", "{}"), (zi, "/etc/passwd")])
    with pytest.raises(ValueError, match="collegamento simbolico"): archivio.estrai(zp, str(tmp_path / "dest"))


@pytest.mark.filterwarnings("ignore:Duplicate name")
def test_zip_solo_i_file_di_un_progetto(tmp_path):
    from impaginatore import archivio
    dispositivo = zipfile.ZipInfo("P/fifo.json"); dispositivo.external_attr = (stat.S_IFIFO | 0o644) << 16
    voci = [("P/progetto.json", "{}"), ("P/album.json", "{}"), ("P/spec.py", "SPREADS = []"), ("P/Foto/a.JPG", "x"), ("P/_cache/thumbs/a.jpg", "x"), ("P/LEGGIMI.txt", "x"),
            ("P/aiuto.py", "x"), ("P/sotto/spec.py", "x"), ("P/x.exe", "x"), ("P/x.sh", "x"), ("P/Foto/CON.jpg", "x"), ("P/Foto/a:b.jpg", "x"), ("P/Foto/cifrata.jpg", "x"), (dispositivo, "x"),
            ("P/album_libere.py", "x"), ("P/.DS_Store", "x"), ("__MACOSX/P/._a.jpg", "x"), ("P/._a.jpg", "x"), ("P/Foto/", ""), ("P/Foto/A.jpg", "x"), ("P/Foto/a.JPG", "y")]
    avvisi = []
    zp = _zip(tmp_path / "a.zip", voci); _segna_cifrato(tmp_path / "a.zip", "P/Foto/cifrata.jpg")
    fatti = archivio.estrai(zp, str(tmp_path / "dest"), avvisi)
    (tmp_path / "caso").write_text("x"); sensibile = not (tmp_path / "CASO").exists()           # macOS e Windows: «A.jpg» e «a.JPG» sono lo stesso file
    assert sorted(fatti) == sorted(["P/Foto/a.JPG", "P/LEGGIMI.txt", "P/_cache/thumbs/a.jpg", "P/album.json", "P/progetto.json", "P/spec.py"] + (["P/Foto/A.jpg"] if sensibile else []))
    assert avvisi[0].startswith("8 file non previsti") and any("compare due volte" in a for a in avvisi)
    assert (tmp_path / "dest" / "P" / "Foto" / "a.JPG").read_text() == "x", "il primo resta"


def test_zip_limiti(tmp_path, monkeypatch):
    from impaginatore import archivio
    zp = _zip(tmp_path / "a.zip", [("P/progetto.json", "{}"), ("P/Foto/a.jpg", "x" * 100000), ("P/Foto/b.jpg", "y" * 100000)])
    monkeypatch.setattr(archivio, "MAX_FILE", 2)
    with pytest.raises(ValueError, match="più di 2 file"): archivio.estrai(zp, str(tmp_path / "d1"))
    monkeypatch.setattr(archivio, "MAX_FILE", 100); monkeypatch.setattr(archivio, "MAX_TOTALE", 150000)
    with pytest.raises(ValueError, match="occuperebbe"): archivio.estrai(zp, str(tmp_path / "d2"))
    monkeypatch.setattr(archivio, "MAX_TOTALE", 10**9); monkeypatch.setattr(archivio, "SOGLIA_TOTALE", 100)
    with pytest.raises(ValueError, match="compresso in modo anomalo"): archivio.estrai(zp, str(tmp_path / "d3"))
    monkeypatch.setattr(archivio, "SOGLIA_TOTALE", 10**9)
    monkeypatch.setattr(archivio.shutil, "disk_usage", lambda p: type("Uso", (), {"free": 0})())
    with pytest.raises(ValueError, match="spazio sul disco"): archivio.estrai(zp, str(tmp_path / "d4"))


def test_zip_bomba(home_srv, tmp_path):
    """un file di 3 MB di zeri compresso in pochi KB (rapporto oltre 200): rifiutato prima di estrarre"""
    zp = _zip(tmp_path / "bomba.zip", [("P/progetto.json", json.dumps({"nome": "B", "formato_cm": [30, 30]})), ("P/Foto/a.jpg", b"\0" * (3 * 2**20))])
    class Z(dialoghi.Dialoghi):
        def _scegli(self, tipo, m): return [zp]
    dialoghi.imposta(Z())
    ok, r = home_srv.prova("/api/importa-zip", {})
    assert not ok and "compresso in modo anomalo" in r["errore"]
    assert [d for d in os.listdir(home_srv.modulo.PROGETTI) if d != "registro.json"] == [], "niente estratto, niente cartelle temporanee"


def test_zip_rovinato(tmp_path):
    from impaginatore import archivio
    p = tmp_path / "a.zip"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_STORED) as z: z.writestr("P/progetto.json", "{" + " " * 200 + "}")
    b = bytearray(p.read_bytes()); i = b.index(b"{" + b" " * 200); b[i + 50] = ord("x"); p.write_bytes(bytes(b))
    with pytest.raises(ValueError, match="rovinato"): archivio.estrai(str(p), str(tmp_path / "d"))
    assert not (tmp_path / "d" / "P" / "progetto.json").exists(), "il file a metà si toglie"
    (tmp_path / "non.zip").write_bytes(b"non sono uno zip")
    with pytest.raises(ValueError, match="non è uno ZIP leggibile"): archivio.estrai(str(tmp_path / "non.zip"), str(tmp_path / "d"))


def test_zip_importato_ripulito(home_srv, tmp_path):
    """dopo Importa ZIP i percorsi del computer di chi l'ha esportato spariscono; meta.json punta solo alla cartella Foto"""
    meta = [dict(n="a.jpg", dt="", src="/Users/collega/Privato/a.jpg", w=10, h=10, ar=1.0)]
    zp = _zip(tmp_path / "Rossi.zip", [("progetto.json", json.dumps({"nome": "Rossi", "formato_cm": [30, 30], "foto": "/Users/collega", "foto_extra": ["/x"], "uscita_psd": "/y"})),
                                       ("album.json", '{"formato": 2, "spread": []}'), ("_cache/meta.json", json.dumps(meta))])
    zp2 = _zip(tmp_path / "Meta rotto.zip", [("progetto.json", json.dumps({"nome": "R", "formato_cm": [30, 30]})), ("_cache/meta.json", '[{"n": "../x"')])
    zp3 = _zip(tmp_path / "Non valido.zip", [("progetto.json", json.dumps({"nome": "R", "formato_cm": "30x30"}))])
    class Z(dialoghi.Dialoghi):
        def _scegli(self, tipo, m): return [Z.zp]
    dialoghi.imposta(Z())
    Z.zp = zp; p = home_srv.post("/api/importa-zip")["path"]
    assert os.path.basename(p) == "Rossi"
    cfg = formato.leggi_json(os.path.join(p, "progetto.json")); assert (cfg["foto"], cfg["foto_extra"], cfg["uscita_psd"]) == ("", [], "")
    assert formato.leggi_json(os.path.join(p, "_cache", "meta.json"))[0]["src"] == "Foto/a.jpg"
    Z.zp = zp2; p2 = home_srv.post("/api/importa-zip")["path"]; assert not os.path.exists(os.path.join(p2, "_cache", "meta.json"))
    Z.zp = zp3; ok, r = home_srv.prova("/api/importa-zip", {}); assert not ok and "formato_cm" in r["errore"]


# ---------------------------------------------------------------- TEST-004: niente esecuzione di codice nel pacchetto
VIETATE = {"exec", "eval", "compile", "__import__", "execfile", "breakpoint"}
VIETATI_ATTRIBUTI = {"import_module", "run_module", "run_path", "spec_from_file_location", "exec_module", "load_module", "load_source", "loads", "load"}
MODULI_ATTRIBUTI = {"importlib", "runpy", "imp", "pickle", "marshal", "cPickle", "dill", "shelve"}
MODULI_VIETATI = MODULI_ATTRIBUTI - {"importlib"}            # importlib.util.find_spec (c'è tkinter?) non esegue niente
ECCEZIONI = {}          # file -> motivo: vuoto (nessuna esecuzione di codice ammessa nel pacchetto)


def _chiamate_vietate(path):
    with open(path, encoding="utf-8") as f: albero = ast.parse(f.read(), path)
    out = []
    for n in ast.walk(albero):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            out += [f"riga {n.lineno}: import {m}" for m in mods if m.split(".")[0] in MODULI_VIETATI]
        if not isinstance(n, ast.Call): continue
        f = n.func
        if isinstance(f, ast.Name) and f.id in VIETATE: out.append(f"riga {n.lineno}: {f.id}(…)")
        if isinstance(f, ast.Attribute) and f.attr in VIETATI_ATTRIBUTI and isinstance(f.value, ast.Name) and f.value.id in MODULI_ATTRIBUTI | {"util", "machinery"}: out.append(f"riga {n.lineno}: {f.value.id}.{f.attr}(…)")
        elif isinstance(f, ast.Attribute) and f.attr in ("import_module", "spec_from_file_location", "exec_module", "run_module", "run_path"): out.append(f"riga {n.lineno}: .{f.attr}(…)")
    return out


def test_test004_nessuna_esecuzione_di_codice_nel_pacchetto():
    """exec, eval, compile, __import__, importlib, runpy, pickle...: nessuno nel pacchetto (lista delle eccezioni vuota)"""
    trovate = {}
    for radice, _, files in os.walk(SRC):
        for f in files:
            if not f.endswith(".py"): continue
            p = os.path.join(radice, f); rel = os.path.relpath(p, SRC)
            v = _chiamate_vietate(p)
            if v and rel not in ECCEZIONI: trovate[rel] = v
    assert trovate == {}, trovate


def test_il_controllo_trova_le_chiamate(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("import importlib, runpy\nfrom pickle import loads\nexec('1')\neval('1')\ncompile('1', 'x', 'exec')\n__import__('os')\nimportlib.import_module('os')\nrunpy.run_path('x')\nx.exec_module(m)\nre.compile('x')\n", encoding="utf-8")
    assert len(_chiamate_vietate(str(f))) == 9
