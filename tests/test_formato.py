"""Formato di salvataggio: album.json (formato 2, solo dati) e progetto.json. I progetti salvati dalla 1.5.2 (spec.py) si
convertono senza eseguire niente e danno lo stesso stato e le stesse anteprime; su richiesta un progetto si esporta ancora
per la 1.x (spec.py che gli script 1.5.2 leggono)."""
import ast
import json
import os
import shutil
import subprocess
import sys

import pytest
from aiuti import FOTO_SCENARIO, crea_foto, progetto_152, riduci

from impaginatore import formato, formato_1x, validazione
from impaginatore.motore import album, album_libere

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P152 = os.path.join(RADICE, "tests", "dati", "progetto_152")


def _progetto_152(base):
    """il progetto dello scenario di parità come l'ha salvato la 1.5.2 (spec.py e progetto.json veri), con le stesse foto"""
    p = os.path.join(base, "Parità àè"); crea_foto(os.path.join(p, "Foto"))
    shutil.copy(os.path.join(P152, "spec.py"), os.path.join(p, "spec.py"))
    with open(os.path.join(P152, "progetto.json"), encoding="utf-8") as f: cfg = json.loads(f.read().replace("{PROGETTO}", p.replace("\\", "/")))
    formato.scrivi_json(os.path.join(p, "progetto.json"), cfg, indent=2, ensure_ascii=False)
    return p, cfg


def _esegui_come_la_1x(path):
    """riferimento: SPREADS come li dava la 1.5.2, eseguendo spec.py (solo qui, nel test, su un file nostro e fidato)"""
    nomi = {}
    sys.modules["album"], sys.modules["album_libere"] = album, album_libere          # come faceva la 1.x: i moduli con i nomi brevi
    try:
        with open(path, encoding="utf-8") as f: exec(compile(f.read(), path, "exec"), nomi)
    finally: del sys.modules["album"], sys.modules["album_libere"]
    return [[[m, list(it)] for m, it in sp] for sp in nomi["SPREADS"]]


def _anteprime(spreads):
    return [album.render(sp, 0.05).tobytes() for sp in spreads]


def test_progetto_152_si_converte_e_si_riapre_uguale(tmp_path, apri_editor):
    p, cfg = _progetto_152(str(tmp_path))
    with open(os.path.join(p, "spec.py"), "rb") as f: originale = f.read()
    c = apri_editor(p)
    with open(os.path.join(P152, "stato_ridotto.json"), encoding="utf-8") as f: atteso = json.load(f)
    assert riduci(c.get("/api/state")) == atteso, "stato dell'editor diverso da quello della 1.5.2"
    assert not os.path.exists(os.path.join(p, "spec.py")) and os.path.exists(os.path.join(p, "album.json"))
    with open(os.path.join(p, "spec.py.1x"), "rb") as f: assert f.read() == originale, "spec.py resta, intatto, come copia"
    # la stessa impaginazione riscritta per la 1.x è identica (riga per riga) a quella salvata dalla 1.5.2
    with open(os.path.join(P152, "spec.py"), encoding="utf-8") as f: vecchio = f.read().split("\n")
    assert formato_1x.testo_spec(c.E.SP, "Parità àè", album.name).split("\n")[1:] == vecchio[1:]
    c.E.save(backup=False)
    assert formato.leggi_json(os.path.join(p, "progetto.json")) == cfg, "progetto.json risalvato diverso"
    assert sorted(os.listdir(p)) == ["Foto", "_backup_editor", "_cache", "album.json", "progetto.json", "spec.py.1x"]
    c.E.inizializza(p)
    assert riduci(c.get("/api/state")) == atteso, "riaperto da album.json: stato diverso"


def test_conversione_uguale_alla_152_eseguita(tmp_path):
    """parità vera: la conversione senza esecuzione dà gli stessi elementi e le stesse anteprime (pixel per pixel) di spec.py eseguito"""
    p, _ = _progetto_152(str(tmp_path)); album.carica_progetto(p)
    rif = _esegui_come_la_1x(os.path.join(p, "spec.py"))
    sp = formato.carica(p)
    assert sp == rif
    assert _anteprime(sp) == _anteprime(rif)
    assert formato.carica(p) == rif, "riletto da album.json"


SPEC_SKILL = '''"""Esempio come lo scrive l'assistente con la skill: moduli, tuple, commenti, nomi o numeri delle foto."""
from album import *
from album_libere import FREE, ROT as GIRA

APERTURA = (W(TXT("title", 0, 0, 12, 8)), I(FULL("V10")))
SPREADS = [
    APERTURA,                                                      # apertura
    (I(DUO("V03", "V04", z=(1, 1.1))), I(G4("H01", "H02", "H06", "H08"))),
    (I(DUO("V07", "V10", bw=(True, False), z=(1.25, 1))), W(CV("Q05"))),
    (I(VLL("V03", "H01", "H02", mirror=True)), I(V4("V04", "V07", "V10", "V03", "V04", mirror=True, z=1.2))),
    (W(*SV("Q09"), *PP(1, bw=True)), W(COL2("H01", "H02"), BAND2("H06", "H08"))),
]
SPREADS += [(W(STRIP3("H01", "H02", 3)), W(GIRA(FREE(5, 0.1, 0.2 - 0.1, 1 / 2, 0.5 * 1, zo=+1), -4.5)))]
SPREADS.append((W(P("H08", 0, 0, 6, 8), TXT("end", 7, 0, 5, 8)), I(FULL(-(-2)))))
'''


def test_spec_scritto_con_la_skill_si_converte(tmp_path, foto_campione):
    p = tmp_path / "Album"; (p / "Foto").mkdir(parents=True)
    for f in os.listdir(foto_campione): shutil.copy(os.path.join(foto_campione, f), p / "Foto" / f)
    formato.scrivi_json(str(p / "progetto.json"), dict(nome="Album", foto=str(p / "Foto"), formato_cm=[40, 20]))
    (p / "spec.py").write_text(SPEC_SKILL, encoding="utf-8")
    album.carica_progetto(str(p))
    assert formato.controlla(str(p)) == 7 and formato.conta_spread(str(p)) == 7 and formato.conta_spread(str(p)) == 7
    rif = _esegui_come_la_1x(str(p / "spec.py"))
    sp = formato.carica(str(p))
    doc = formato.leggi_album(str(p / "album.json"))
    assert formato.documento(sp, album.name) == formato.documento(rif, album.name) == doc
    assert _anteprime(sp) == _anteprime(rif)
    assert sp[5][1][1][0]["a"] == -4.5 and sp[5][1][1][0]["zo"] == 1 and sp[6][1][1][0]["i"] == 1
    assert formato.conta_spread(str(p)) == 7 and formato.file_album(str(p)).endswith("album.json") and formato.conta_spread(str(tmp_path)) == 0
    assert "__pycache__" not in os.listdir(p) and str(p) not in sys.path


def test_progetto_si_esporta_per_la_1x(tmp_path, apri_editor):
    """«Esporta per la versione 1.x»: spec.py e copie del motore che gli script della 1.5.2 (ramo main) leggono"""
    p, _ = _progetto_152(str(tmp_path))
    c = apri_editor(p)
    out = tmp_path / "per_1x"; out.mkdir()
    formato_1x.esporta(str(out), c.E.SP, "Nome con \"\"\" e \\ dentro", album.name, quando="01/01/2026 10:00")
    for f in ("album_libere.py", "testo.py", "vib_lut.npz"): assert (out / f).exists(), f
    testo = (out / "spec.py").read_text(encoding="utf-8")
    assert ast.literal_eval(testo.split("\n")[0]) == 'Nome con """ e \\ dentro: 5 spread. Salvato dall\'editor il 01/01/2026 10:00.'
    assert formato_1x.leggi(testo.encode(), prova=True) and len(formato_1x.leggi(testo.encode())) == 5
    vecchio = _album_152()
    if vecchio is None: pytest.skip("storia git della 1.5.2 non disponibile")
    shutil.copy(os.path.join(p, "progetto.json"), out / "progetto.json"); shutil.copytree(os.path.join(p, "_cache"), out / "_cache")
    scr = tmp_path / "scripts_152"; scr.mkdir(); (scr / "album.py").write_bytes(vecchio)
    codice = ("import sys; sys.path.insert(0, sys.argv[1]); sys.argv = ['x', '--progetto', '.']\n"
              "import album\nSP = album.load_spec()\nimport album_libere, testo\n"
              "im = album.render(SP[1], 0.05)\nprint(len(SP), im.size, album_libere.__file__)")
    r = subprocess.run([sys.executable, "-c", codice, str(scr), str(out)], cwd=str(out), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.startswith("5 ") and os.path.join(str(out), "album_libere.py") in r.stdout


def _album_152():
    """album.py della 1.5.2 dalla storia git (o None)"""
    try: r = subprocess.run(["git", "-C", RADICE, "show", "957fdf7:motore/scripts/album.py"], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError): return None
    return r.stdout if r.returncode == 0 else None


def test_copie_nel_progetto_funzionano_da_sole(tmp_path):
    """album_libere.py e testo.py copiati per la 1.x non devono avere bisogno del pacchetto"""
    d = tmp_path / "prj"; d.mkdir()
    formato_1x.copia_motore(str(d))
    (d / "album.py").write_text("def _place(*a): pass\ndef zcrop(it): pass\ndef _photo(*a): pass\ndef render(*a): pass\ndef _text(*a): pass\ndef apply_ev(*a): pass\ndef layout(s): pass\n", encoding="utf-8")
    codice = "import album_libere, testo; print(testo._dirs()[0], testo._cache()); print(album_libere.vib_lut().shape)"
    r = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, '.'); " + codice], cwd=str(d), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    assert ".album-tools" in r.stdout and "17, 17, 17, 3)" in r.stdout


def _tutti_i_tipi():
    i = album.IDX
    return [[["I", [dict(k="p", i=i["H01"] - 1, c=0, r=0, w=6, h=8, bw=True, z=1.3), dict(k="full", i=i["H02"] - 1, bw=False, z=1.0, zo=4, a=2.0, sh=0, oc=100)]],
             ["W", [dict(k="full", i=i["V03"] - 1, bw=False, z=1.0)]]],
            [["W", [dict(k="f", i=i["Q05"] - 1, x=0.1, y=0.2, w=0.5, h=0.4, bw=False, z=1.0, zo=2, a=-4.5, bd=[2.0, "#000000"], sh=30, oc=90)]],
             ["W", [dict(k="t", kind="txt", tx="Ciao «àè»\nriga \"\"\" ' \\", fx=0.1, fy=0.1, fw=0.5, fh=0.2, font="X-Regular", size=90.0, col=[1, 2, 3], al="right", tr=10.0, auto=False, lh=1.4, caps=True, zo=3, stile="T"),
                    dict(k="t", kind="title", c=0, r=0, w=12, h=8, ts=1.5, zo=7), dict(k="t", kind="end", fx=0.5, fy=0.5, fw=0.4, fh=0.3, ts=1.2, c=3, r=3, w=2, h=2)]]]]


def test_album_json_rilegge_quello_che_scrive(tmp_path, foto_campione):
    p = tmp_path / "Album"; (p / "Foto").mkdir(parents=True)
    for f in os.listdir(foto_campione): shutil.copy(os.path.join(foto_campione, f), p / "Foto" / f)
    formato.scrivi_json(str(p / "progetto.json"), dict(nome="Album", foto=str(p / "Foto"), formato_cm=[40, 20]))
    album.carica_progetto(str(p))
    spreads = _tutti_i_tipi()
    doc = formato.salva(str(p), spreads, album.name)
    testo = (p / "album.json").read_text(encoding="utf-8")
    assert json.loads(testo) == doc and doc["formato"] == 2 and doc["programma"].startswith("Impaginatore ")
    assert testo.count("\n") > 8, "un elemento per riga"
    letto = formato.carica(str(p))
    assert formato.documento(letto, album.name) == doc
    # gli elementi riletti sono quelli dei costruttori del motore, come li dava spec.py (più zo e ts che la 1.x perdeva)
    assert letto[1][1][1][1] == dict(k="t", kind="title", c=0, r=0, w=12, h=8, ts=1.5, zo=7)
    assert letto[1][1][1][2] == album_libere.TXTF("end", 0.5, 0.5, 0.4, 0.3, ts=1.2)
    assert letto[0][0][1][1] == dict(album.FULL("H02"), zo=4, a=2.0)
    assert formato.testo_album(formato.leggi_album(str(p / "album.json"))) == testo
    assert json.loads(formato.album_vuoto())["spread"] == [] and formato.testo_album({"formato": 2, "spread": []}).count("[]") == 1
    assert not formato_1x.ha_liberi([[["I", [dict(k="p", i=0)]], ["W", []]]]) and formato_1x.ha_liberi(spreads)


def test_esportato_per_la_1x_e_riaperto_con_la_2(tmp_path, foto_campione):
    """album.json e spec.py insieme (progetto esportato per la 1.x): se spec.py è ancora quello dell'esportazione vale
    album.json (che tiene anche quello che la 1.x non sa scrivere); se la 1.x l'ha cambiato vale spec.py, e l'album.json di
    prima resta tra le versioni. In tutti e due i casi spec.py si legge senza eseguirlo e poi resta solo come copia"""
    p = tmp_path / "Album"; (p / "Foto").mkdir(parents=True)
    for f in os.listdir(foto_campione): shutil.copy(os.path.join(foto_campione, f), p / "Foto" / f)
    formato.scrivi_json(str(p / "progetto.json"), dict(nome="Album", foto=str(p / "Foto"), formato_cm=[40, 20]))
    album.carica_progetto(str(p)); spreads = _tutti_i_tipi()
    doc = formato.salva(str(p), spreads, album.name)
    formato_1x.esporta(str(p), spreads, "Album", album.name)
    assert formato.controlla(str(p)) == 2
    assert formato.documento(formato.carica(str(p)), album.name) == doc, "spec.py non cambiato: vale album.json (con zo e ts)"
    assert not (p / "spec.py").exists() and (p / "spec.py.1x").exists() and not (p / "_backup_editor").exists()
    formato_1x.esporta(str(p), spreads, "Album", album.name)
    testo = (p / "spec.py").read_text(encoding="utf-8"); assert "bw=True, z=1.3" in testo
    (p / "spec.py").write_bytes(testo.replace("bw=True, z=1.3", "z=1.3").replace("\n", "\r\n").encode("utf-8"))       # la 1.x l'ha cambiato
    letto = formato.carica(str(p))
    assert letto[0][0][1][0]["bw"] is False and "zo" not in letto[1][1][1][1], "vale spec.py (la 1.x non scrive zo dei titoli)"
    assert formato.leggi_album(str(p / "album.json"))["spread"][0]["sinistra"]["elementi"][0].get("bw") is None
    copie = os.listdir(p / "_backup_editor"); assert len(copie) == 1 and copie[0].endswith("_album.json")
    assert formato.leggi_album(str(p / "_backup_editor" / copie[0])) == doc and (p / "spec.py.1x.2").exists()
    (p / "spec.py").write_text("import os\nSPREADS = []\n", encoding="utf-8")                     # accanto ad album.json, ma con codice
    prima = (p / "album.json").read_bytes()
    with pytest.raises(validazione.ErroreProgetto, match="istruzioni non riconosciute"): formato.controlla(str(p))
    with pytest.raises(validazione.ErroreProgetto, match="istruzioni non riconosciute"): formato.carica(str(p))
    (p / "spec.py").write_bytes(b"\xff\xfe")
    with pytest.raises(validazione.ErroreProgetto, match="non è un testo UTF-8"): formato.carica(str(p))
    assert (p / "album.json").read_bytes() == prima and len(os.listdir(p / "_backup_editor")) == 1, "un progetto che non si apre non si tocca"


def test_nuovo_progetto_e_solo_dati(home):
    p = home.nuovo({"nome": "  Nuovo  ", "w": 30, "h": 30})
    assert os.path.basename(p) == "Nuovo" and sorted(os.listdir(p)) == ["Foto", "album.json", "progetto.json"]
    assert formato.leggi_album(os.path.join(p, "album.json"))["spread"] == [] and formato.controlla(p) == 0
    assert formato.leggi_progetto(p)["nome"] == "Nuovo"


# ---------------------------------------------------------------- album.json non validi: errori chiari, mai eccezioni qualsiasi
def _doc(*el, modo="I"):
    return {"formato": 2, "spread": [{"sinistra": {"modo": modo, "elementi": list(el)}, "destra": {"modo": "W", "elementi": []}}]}


P0 = {"k": "p", "foto": "H01", "c": 0, "r": 0, "w": 6, "h": 8}
TX0 = {"k": "t", "kind": "txt", "tx": "a", "fx": 0, "fy": 0, "fw": 0.5, "fh": 0.1, "font": "F", "size": 10, "col": [0, 0, 0], "al": "left", "tr": 0}


@pytest.mark.parametrize("doc, messaggio", [
    ([], "deve contenere un oggetto"),
    ({"spread": []}, "manca «formato»"),
    ({"formato": 3, "spread": []}, "aggiorna il programma"),
    ({"formato": "2", "spread": []}, "formato sconosciuto"),
    ({"formato": True, "spread": []}, "formato sconosciuto"),
    ({"formato": 2, "spread": [], "codice": "x"}, "chiave sconosciuta «codice»"),
    ({"formato": 2, "spread": {}}, "deve essere un elenco"),
    ({"formato": 2, "spread": [{"sinistra": {"modo": "I", "elementi": []}}]}, "spread 1: manca «destra»"),
    (_doc(modo="X"), "modo: deve essere uno tra «I», «W»"),
    (_doc(dict(P0, c=11)), "esce dalla griglia"),
    (_doc(dict(P0, c=1.5)), "c: deve essere un numero intero"),
    (_doc(dict(P0, z=float("nan"))), "z: deve essere un numero da -100 a 100"),
    (_doc(dict(P0, z=True)), "z: deve essere un numero"),
    (_doc(dict(P0, zo="__import__('os')")), "zo: deve essere un numero intero"),
    (_doc(dict(P0, bd=[2, "red"])), 'il colore deve essere nella forma "#rrggbb"'),
    (_doc(dict(P0, bd=[2])), "deve essere [millimetri"),
    (_doc(dict(P0, sh=101)), "sh: deve essere un numero da 0 a 100"),
    (_doc(dict(P0, extra=1)), "elemento 1: chiave sconosciuta «extra»"),
    (_doc({"k": "p"}), "manca «foto», «c», «r», «w», «h»"),
    (_doc({"k": "x"}), "tipo di elemento sconosciuto"),
    (_doc("P('H01')"), "elemento 1: deve essere un oggetto"),
    (_doc({"k": "t", "kind": "boh"}), "kind: deve essere"),
    (_doc({"k": "f", "foto": "H01", "x": 0, "y": 0, "w": 0, "h": 1}), "w: deve essere un numero maggiore di 0"),
    (_doc(dict(TX0, al="justify")), "al: deve essere uno tra"),
    (_doc(dict(TX0, col=[0, 0])), "col: deve avere 3 valori"),
    (_doc(dict(TX0, col=[0, 0, 300])), "col: deve essere un numero da 0 a 255"),
    (_doc(dict(TX0, tx="\ud800")), "carattere non ammesso"),
    (_doc(dict(TX0, tx="x" * 100001)), "troppo lungo"),
    (_doc(dict(TX0, tx=5)), "tx: deve essere un testo"),
    (_doc(dict(TX0, size=0)), "size: deve essere un numero maggiore di 0"),
    (_doc(dict(TX0, auto="sì")), "auto: deve essere vero o falso"),
    (_doc(dict(TX0, font="")), None),
    (_doc({"k": "t", "kind": "title", "c": 0, "r": 0, "w": 12, "h": 8, "ts": 99}), "ts: deve essere un numero da 0.05 a 20"),
    (_doc({"k": "t", "kind": "end", "fx": 0, "fy": 0, "fw": 0, "fh": 0}), None),
    ({"formato": 2, "programma": 7, "spread": []}, "programma: deve essere un testo"),
    ({"formato": 2, "spread": [None] * 2001}, "troppi elementi"),
])
def test_album_json_non_valido(doc, messaggio):
    if messaggio is None: validazione.album(doc); return
    with pytest.raises(validazione.ErroreProgetto, match=messaggio.replace("(", r"\(").replace("[", r"\[")): validazione.album(doc)


def test_foto_che_non_ci_sono(tmp_path):
    with pytest.raises(validazione.ErroreProgetto, match="la foto «H01» non è nell'album"): validazione.album(_doc(P0), foto={"H02"})
    validazione.album(_doc(P0), foto={"H01"})


@pytest.mark.parametrize("testo, messaggio", [
    (b'{"formato": 2, "spread": [], "spread": []}', "compare due volte"),
    (b'{"formato": 2, "spread": [NaN]}', "valore non ammesso"),
    (b'{"formato": 2, "spread": [Infinity]}', "valore non ammesso"),
    (b'{"formato": 2, "spread": [', "non è un JSON valido"),
    (b'\xff\xfe', "non è un testo UTF-8"),
    (b"[" * 100000 + b"]" * 100000, "non è valido"),
])
def test_album_json_illeggibile(tmp_path, testo, messaggio):
    p = tmp_path / "album.json"; p.write_bytes(testo)
    with pytest.raises(validazione.ErroreProgetto, match=messaggio): formato.leggi_album(str(p))


def test_annidamento_con_il_limite_del_programma(tmp_path, monkeypatch):
    """i JSON da fuori (file di un progetto, richieste) si rifiutano oltre MAX_ANNIDAMENTO livelli con lo stesso messaggio su
    ogni sistema: il limite di json.loads dipende dalla pila (versione di Python, ulimit) e con Python 3.14 su una pila
    grande centomila livelli si leggono. Le parentesi dentro le stringhe non contano"""
    from impaginatore import servizio
    n = validazione.MAX_ANNIDAMENTO

    def livelli(k, tipo=str): return tipo("[" * k + "]" * k) if tipo is str else b"[" * k + b"]" * k
    for tipo in (str, bytes):
        validazione.controlla_annidamento(livelli(n, tipo))
        with pytest.raises(validazione.JsonAnnidato, match="JSON troppo annidato"): validazione.controlla_annidamento(livelli(n + 1, tipo))
    assert servizio.leggi_json(livelli(n)) == json.loads(livelli(n)), "fino al limite si legge"
    with pytest.raises(ValueError, match="JSON troppo annidato"): servizio.leggi_json(livelli(n + 1))          # json.loads lo leggerebbe ovunque
    with pytest.raises(ValueError, match="JSON troppo annidato"): servizio.leggi_json(b"{" * (n + 1))         # non chiuso: conta lo stesso
    largo = "[" + "[[]]," * 1000 + "[]]"; assert len(servizio.leggi_json(largo)) == 1001, "tante parentesi, pochi livelli"
    for testo in ('["' + "[{" * 1000 + '"]', '"' + "[" * 1000 + '"', '["\\"' + "[" * 1000 + '\\\\", "]]]"]'):
        validazione.controlla_annidamento(testo); validazione.controlla_annidamento(testo.encode()); servizio.leggi_json(testo)
    p = tmp_path / "x.json"; p.write_text(json.dumps({"a": "[" * 100}) + " " * 10, encoding="utf-8")
    assert formato.leggi_json(str(p)) == {"a": "[" * 100}
    p.write_bytes(livelli(n + 1, bytes))
    with pytest.raises(validazione.JsonAnnidato): formato.leggi_json(str(p))
    (tmp_path / "album.json").write_bytes(b'{"formato": 2, "spread": ' + livelli(n, bytes) + b"}")
    with pytest.raises(validazione.ErroreProgetto, match="album.json non è valido: JSON troppo annidato"): formato.leggi_album(str(tmp_path / "album.json"))


def test_album_json_troppo_grande(tmp_path, monkeypatch):
    p = tmp_path / "album.json"; p.write_text(formato.album_vuoto(), encoding="utf-8")
    monkeypatch.setattr(formato, "MAX_ALBUM", 10)
    with pytest.raises(validazione.ErroreProgetto, match="troppo grande"): formato.leggi_album(str(p))
    with pytest.raises(validazione.ErroreProgetto, match="troppo grande"): formato.leggi_json(str(p), massimo=10)


def test_progetto_json_controllato(tmp_path):
    base = dict(nome="X", formato_cm=[30, 20])
    assert validazione.progetto(dict(base, sconosciuta={"resta": 1}))["sconosciuta"] == {"resta": 1}, "le chiavi di altre versioni restano"
    for cfg, msg in [([], "deve contenere un oggetto"), ({}, "manca «formato_cm»"), (dict(base, formato_cm=[30]), "deve avere 2 valori"),
                     (dict(base, ppi=10**6), "ppi: deve essere un numero da 30 a 2400"), (dict(base, formato_cm=[1000, 1000], ppi=2400), "troppo grande da elaborare"),
                     (dict(base, testo={"colore": "rosso"}), "colore: deve essere un elenco"), (dict(base, stili={"T": {"al": "giustificato"}}), "al: deve essere uno tra"),
                     (dict(base, tono={"H01": {"c": [[1, 2, 3]]}}), "tono, c: deve avere 2 valori"), (dict(base, ritocco={"H01": {"vib": 500}}), "vib: deve essere un numero da -100 a 100"),
                     (dict(base, guide=[{"v": ["x"]}]), "guide, v: deve essere un numero"), (dict(base, tolte="H01"), "tolte: deve essere un elenco"),
                     (dict(base, dimensioni_esatte="no"), "vero o falso"), (dict(base, esposizione={"per_foto": {"H01": "+1"}}), "per_foto: deve essere un numero"),
                     (dict(base, centri_volto={"H01": [0.5]}), "centri_volto: deve avere 2 valori"), (dict(base, bilanciamento_bianco={"H01": [1, 1, -1]}), "bilanciamento_bianco: deve essere un numero da 0 a 100"),
                     (dict(base, colori={"H01": 3}), "colori: deve essere un testo")]:
        with pytest.raises(validazione.ErroreProgetto, match=msg): validazione.progetto(cfg)
    (tmp_path / "progetto.json").write_text("{", encoding="utf-8")
    with pytest.raises(validazione.ErroreProgetto, match="non è un JSON valido"): formato.leggi_progetto(str(tmp_path))
    (tmp_path / "progetto.json").write_text("[" * 100000 + "]" * 100000, encoding="utf-8")
    with pytest.raises(validazione.ErroreProgetto, match="non è un JSON valido"): formato.leggi_progetto(str(tmp_path))


def test_cache_delle_foto_controllata():
    buona = [dict(n="a.jpg", dt="", src="/x/a.jpg", w=10, h=10, ar=1.0)]
    assert validazione.meta(buona) == buona and validazione.volti({"a.jpg": [[0, 0, 1, 1]]})
    for m, msg in [([dict(buona[0], n="../../a.jpg")], "non è un nome di file valido"), ([dict(buona[0], n="..")], "non è un nome di file valido"),
                   ([{"n": "a.jpg"}], "manca «dt»"), ([dict(buona[0], w="10")], "w: deve essere un numero intero"), (["a.jpg"], "deve essere un oggetto")]:
        with pytest.raises(validazione.ErroreProgetto, match=msg): validazione.meta(m)
    with pytest.raises(validazione.ErroreProgetto): validazione.volti({"a.jpg": [[0, 0, 1]]})


# ---------------------------------------------------------------- scritture atomiche (BUG-005)
def test_scrivi_atomico(tmp_path):
    d = tmp_path / "w"; d.mkdir(); f = d / "a.txt"; formato.scrivi_atomico(str(f), "àè\n")
    assert f.read_text(encoding="utf-8") == "àè\n" and os.listdir(d) == ["a.txt"]
    formato.scrivi_json(str(tmp_path / "b.json"), {"n": "è"}, ensure_ascii=False)
    assert formato.leggi_json(str(tmp_path / "b.json")) == {"n": "è"}
    os.chmod(f, 0o600); formato.scrivi_atomico(str(f), "x")
    assert (os.stat(f).st_mode & 0o777) == 0o600 or os.name == "nt", "i permessi del file restano quelli di prima"


def test_scrittura_interrotta_non_rovina_il_file(tmp_path, monkeypatch):
    """BUG-005: un errore a metà scrittura (dati non serializzabili, disco pieno, sostituzione fallita) lascia il file di prima"""
    d = tmp_path / "w"; d.mkdir(); f = d / "meta.json"; formato.scrivi_json(str(f), [{"n": "a.jpg"}])
    with pytest.raises(TypeError): formato.scrivi_json(str(f), [{"n": "b.jpg"}, {"x": object()}])
    assert formato.leggi_json(str(f)) == [{"n": "a.jpg"}] and os.listdir(d) == ["meta.json"]
    monkeypatch.setattr(os, "replace", lambda a, b: (_ for _ in ()).throw(OSError(28, "disco pieno")))
    with pytest.raises(OSError): formato.scrivi_json(str(f), [{"n": "c.jpg"}])
    assert formato.leggi_json(str(f)) == [{"n": "a.jpg"}] and os.listdir(d) == ["meta.json"]


def test_scrittura_dove_il_sistema_non_collabora(tmp_path, monkeypatch):
    """la cartella non si apre (Windows) o fsync non riesce: il file si scrive lo stesso; il temporaneo che non si
    riesce a togliere non nasconde l'errore vero"""
    vero_open = os.open
    monkeypatch.setattr(os, "open", lambda p, *a, **k: (_ for _ in ()).throw(PermissionError(13, "cartella")) if os.path.isdir(p) else vero_open(p, *a, **k))
    formato.scrivi_atomico(str(tmp_path / "a.txt"), "uno"); assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "uno"
    monkeypatch.setattr(os, "open", vero_open); vero_fsync = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: vero_fsync(fd) if not os.path.isdir(f"/proc/self/fd/{fd}") or os.name == "nt" else (_ for _ in ()).throw(OSError(22, "fsync")))
    formato.scrivi_atomico(str(tmp_path / "a.txt"), "due"); assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "due"
    monkeypatch.setattr(os, "fsync", vero_fsync)
    monkeypatch.setattr(os, "replace", lambda a, b: (_ for _ in ()).throw(OSError(28, "disco pieno")))
    monkeypatch.setattr(os, "remove", lambda p: (_ for _ in ()).throw(OSError(1, "non si toglie")))
    with pytest.raises(OSError, match="disco pieno"): formato.scrivi_atomico(str(tmp_path / "a.txt"), "tre")


def test_cartella_senza_impaginazione(tmp_path, foto_campione):
    p = tmp_path / "Album"; (p / "Foto").mkdir(parents=True); shutil.copy(os.path.join(foto_campione, "H01.jpg"), p / "Foto" / "H01.jpg")
    formato.scrivi_json(str(p / "progetto.json"), dict(nome="Album", foto=str(p / "Foto"), formato_cm=[40, 20]))
    album.carica_progetto(str(p))
    assert formato.carica(str(p)) == [] and formato.controlla(str(p)) == 0 and formato.file_album(str(p)) is None


def test_copia_atomica(tmp_path):
    a = tmp_path / "a"; a.write_bytes(b"x" * 3000000); os.utime(a, (1000000000, 1000000000))
    formato.copia_atomica(str(a), str(tmp_path / "b"))
    assert (tmp_path / "b").read_bytes() == a.read_bytes() and os.path.getmtime(tmp_path / "b") == 1000000000


def test_cache_rovinata_si_ricostruisce(tmp_path, foto_campione, capsys):
    """BUG-005: meta.json o faces.json troncati (o non validi) non bloccano l'apertura: si rifanno dalle foto"""
    p = tmp_path / "Album"; (p / "Foto").mkdir(parents=True)
    for f in os.listdir(foto_campione): shutil.copy(os.path.join(foto_campione, f), p / "Foto" / f)
    formato.scrivi_json(str(p / "progetto.json"), dict(nome="Album", foto=str(p / "Foto"), formato_cm=[40, 20]))
    album.carica_progetto(str(p)); n = len(album.M)
    (p / "_cache" / "meta.json").write_text('[{"n": "H01.jpg", "dt"', encoding="utf-8")
    (p / "_cache" / "faces.json").write_text('{"H01.jpg": [[0, 0', encoding="utf-8")
    (p / "_cache" / "origine.json").write_text('[1, 2]', encoding="utf-8")
    album.carica_progetto(str(p))
    assert len(album.M) == n and len(album.F) == n and album.ORIGINE == {}
    assert len(formato.leggi_json(str(p / "_cache" / "meta.json"))) == n
    assert "meta.json non valido" in capsys.readouterr().out


def test_meta_json_con_percorsi_fuori_dal_progetto(tmp_path, foto_campione):
    """un meta.json costruito apposta non fa scrivere miniature fuori da _cache/thumbs (nome con ../ o assoluto)"""
    p = tmp_path / "Album"; (p / "Foto").mkdir(parents=True); shutil.copy(os.path.join(foto_campione, "H01.jpg"), p / "Foto" / "H01.jpg")
    formato.scrivi_json(str(p / "progetto.json"), dict(nome="Album", foto=str(p / "Foto"), formato_cm=[40, 20]))
    (p / "_cache").mkdir()
    fuori = tmp_path / "fuori.jpg"
    formato.scrivi_json(str(p / "_cache" / "meta.json"), [dict(n="../../fuori.jpg", dt="", src=str(p / "Foto" / "H01.jpg"), w=900, h=600, ar=1.5),
                                                          dict(n=str(fuori), dt="", src=str(p / "Foto" / "H01.jpg"), w=900, h=600, ar=1.5)])
    album.carica_progetto(str(p))
    assert not fuori.exists() and not (p / "fuori.jpg").exists() and [m["n"] for m in album.M] == ["H01.jpg"]


def test_foto_scenario_nomi():
    assert [n for n, *_ in FOTO_SCENARIO] == ["H01", "H02", "V03", "V04", "Q05", "H06", "V07", "H08", "Q09", "V10"]


def _senza_misure_testi(righe):
    """le misure dei riquadri di testo dipendono dai font installati: si confronta tutto il resto"""
    import re
    return [re.sub(r"TEXT\(('(?:[^'\\]|\\.)*'), [\d.]+, [\d.]+, [\d.]+, [\d.]+,", r"TEXT(\1, #, #, #, #,", r) for r in righe]


def test_stesse_operazioni_stesso_risultato_della_152(home_srv, apri_editor, tmp_path):
    """lo scenario di parità: le operazioni fatte con la 1.5.2 danno, con la 2.0, la stessa impaginazione (album.json
    riscritto per la 1.x è lo spec.py della 1.5.2), lo stesso progetto.json e lo stesso stato dell'editor
    (tests/dati/progetto_152 è l'uscita della 1.5.2)"""
    h = home_srv
    proj = h.post("/api/nuovo", {"nome": "Parità àè", "w": "60", "h": "22,5", "spazio": "2,5"})["path"]
    crea_foto(os.path.join(proj, "Foto"))
    c = apri_editor(proj)
    st = c.get("/api/state"); names = [p["n"] for p in st["photos"]]

    def op(o):
        nonlocal st
        st = c.post("/api/op", dict(cid="scen", rev=st["rev"], **o)); return st
    t = c.post("/api/templates", {"photos": names[:2]}); op({"op": "newspread", "pos": 0, "L": t["items"][0]["L"], "R": t["items"][0]["R"]})
    t3 = c.post("/api/templates", {"photos": names[2:5]}); op({"op": "newspread", "pos": 1, "L": t3["items"][0]["L"], "R": t3["items"][0]["R"]})
    op({"op": "newspreadsel", "names": names[5:8], "pos": 2})
    op({"op": "addtext", "s": 0, "fx": 0.1, "fy": 0.1, "fw": 0.4, "fh": 0, "tx": "Battesimo di Anita"})
    tx = [i for i in st["spreads"][0]["items"] if i.get("kind") == "txt"][0]
    op({"op": "settext", "at": [0, tx["side"], tx["idx"]], "tx": "Ciao àè\nseconda riga", "size": 150, "lh": 1.5, "caps": True, "tr": 40, "al": "center", "col": [200, 30, 30]})
    op({"op": "stile_salva", "at": [0, tx["side"], tx["idx"]], "nome": "Titolo"})
    op({"op": "stella", "photo": names[0], "value": True}); op({"op": "tolta", "photo": names[9], "value": True}); op({"op": "colore", "photo": names[1], "value": "rosso"})
    f1 = [i for i in st["spreads"][1]["items"] if i["k"] != "t"]
    op({"op": "set", "at": [1, f1[0]["side"], f1[0]["idx"]], "z": 1.4, "bw": True})
    op({"op": "free", "at": [1, f1[1]["side"], f1[1]["idx"]], "x": 0.12, "y": 0.1, "w": 0.5, "h": 0.6})
    f1 = [i for i in st["spreads"][1]["items"] if i["k"] != "t"]; fr = [i for i in f1 if i["free"]][0]
    op({"op": "set", "at": [1, fr["side"], fr["idx"]], "a": 7.5, "bd": [3, "#ffffff"], "sh": 40, "oc": 80})
    op({"op": "ev", "photo": names[2], "value": 0.5}); op({"op": "evg", "value": 0.25})
    op({"op": "rit", "photo": names[3], "key": "con", "value": 30}); op({"op": "rit", "photo": names[3], "key": "vib", "value": 20}); op({"op": "rit", "photo": names[4], "key": "tmp", "value": -25})
    op({"op": "tono", "photo": names[4], "value": {"b": 10, "w": 240, "m": 1.2, "c": [[64, 50], [192, 210]]}})
    op({"op": "face", "photo": names[5], "x": 0.3, "y": 0.4})
    op({"op": "guides", "s": 0, "v": [100, 2000.4], "h": [300]})
    op({"op": "dup", "s": 1}); op({"op": "swappages", "s": 3}); op({"op": "move", "s": 3, "to": 0})
    f = [i for i in st["spreads"][1]["items"] if i["k"] != "t"]
    if len(f) >= 2: op({"op": "swap", "a": [1, f[0]["side"], f[0]["idx"]], "b": [1, f[1]["side"], f[1]["idx"]]})
    tp = c.get("/api/templates?s=2"); alt = [x for x in tp["items"] if not x["cur"]]
    if alt: op(dict(op="template", s=2, **{k: alt[0][k] for k in "LR" if k in alt[0]}))
    op({"op": "blank", "pos": len(st["spreads"])}); op({"op": "addtospread", "s": len(st["spreads"]) - 1, "names": [names[8]], "how": "keep"})
    op({"op": "tono_L", "value": 60})
    c.post("/api/save")
    assert not os.path.exists(os.path.join(proj, "spec.py"))
    nuovo = formato_1x.testo_spec(formato.carica(proj), "Parità àè", album.name).split("\n")[1:]
    with open(os.path.join(P152, "spec.py"), encoding="utf-8") as fh: vecchio = fh.read().split("\n")[1:]
    assert _senza_misure_testi(nuovo) == _senza_misure_testi(vecchio)
    assert formato.leggi_json(os.path.join(proj, "progetto.json")) == progetto_152(proj)
    c.E.inizializza(proj)
    with open(os.path.join(P152, "stato_ridotto.json"), encoding="utf-8") as fh: assert riduci(c.get("/api/state")) == json.load(fh)
