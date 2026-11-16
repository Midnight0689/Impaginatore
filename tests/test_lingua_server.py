"""T-206 (parte C): i testi di MCP, licenze, schermata Album (server), validazione dei progetti e servizi di sistema escono
nella lingua in uso. Qui si provano i punti in inglese e le due lingue insieme; i testi italiani sono provati dai test di
ciascun modulo (che girano in italiano). I controlli sulla tabella (stesse chiavi, nessun testo fuori tabella) sono in
test_lingua.py."""
import http.client
import json
import zipfile

import pytest

from impaginatore import aggiornamenti, archivio, formato, licenze, lingua, nomi, percorsi
from impaginatore import validazione as V
from impaginatore.licenze import chiave as K
from impaginatore.mcp import collegamento as C
from impaginatore.mcp import consenso
from impaginatore.mcp import strumenti as S
from impaginatore.piattaforma import dialoghi


@pytest.fixture
def inglese(monkeypatch):
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")


# ---------------------------------------------------------------- servizio.py
def test_errori_http_in_inglese(home_srv, inglese):
    c = home_srv

    def richiesta(metodo, path, corpo=None, **h):
        k = http.client.HTTPConnection("127.0.0.1", c.porta, timeout=30)
        try:
            k.putrequest(metodo, path, skip_host=True, skip_accept_encoding=True)
            h.setdefault("Host", f"127.0.0.1:{c.porta}")
            if corpo is not None: h.setdefault("Content-Length", str(len(corpo)))
            for n, v in h.items(): k.putheader(n.replace("_", "-"), v)
            k.endheaders(corpo); r = k.getresponse()
            return r.status, json.loads(r.read())["errore"]
        finally: k.close()
    assert richiesta("GET", "/api/progetti", **{"X-Impaginatore-Gettone": "sbagliato"}) == (401, "not authorised")
    assert richiesta("GET", "/api/progetti", Host="altro.example") == (403, "invalid address")
    assert richiesta("POST", "/api/nuovo", b"{}", **{"X-Impaginatore-Gettone": c.gettone, "Content-Type": "text/plain"}) == (415, "the body must be JSON")
    assert richiesta("POST", "/api/boh", b"[1]", **{"X-Impaginatore-Gettone": c.gettone, "Content-Type": "application/json"}) == (400, "the body must be a JSON object")
    ok, r = c.prova("/api/boh"); assert not ok and r["errore"] == "not found"


def test_json_e_parametri_in_inglese(inglese):
    from impaginatore import servizio
    with pytest.raises(ValueError, match="value not allowed in the JSON: NaN"): servizio.leggi_json("[NaN]")
    with pytest.raises(ValueError, match="number too large in the JSON"): servizio.leggi_json("1e999")
    with pytest.raises(ValueError, match="JSON nested too deeply"): servizio.leggi_json("[" * 100000)
    with pytest.raises(servizio.RichiestaNonValida, match="n: not a number$"): servizio.numero({"n": ["x"]}, "n", 1, 0, 10)
    with pytest.raises(servizio.RichiestaNonValida, match="n: not a finite number"): servizio.numero({"n": ["nan"]}, "n", 1, 0, 10)


# ---------------------------------------------------------------- licenze
def test_licenze_in_inglese(licenza, inglese, monkeypatch):
    assert [licenze.nome_fascia(f) for f in ("essenziale", "pro", "studio", "laboratorio")] == ["Essential", "Pro", "Studio", "Lab"]
    assert licenze.fasce_con("export_psd_livelli") == "Pro and Studio" and licenze.fasce_con("export_jpg") == "Essential, Pro and Studio"
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    assert licenze.motivo("export_psd_livelli") == "The layered PSD isn't part of the Essential licence: it comes with Pro and Studio."
    assert licenze.motivo("volo").startswith("The “volo” feature isn't part of")
    assert licenze.stato()["nome_fascia"] == "Essential"
    assert licenze.stato()["messaggio"] == "Essential licence active, registered to “Studio Prova”, for 5 computers. All updates to version 2 are included."
    with pytest.raises(licenze.NonConsentita, match="The Essential licence includes 5 personal templates: to save another, delete one. In Pro and Studio the number is unlimited."):
        licenze.controlla_modelli("salva", 5)
    monkeypatch.setattr(licenze, "limite", lambda f, st=None: 1)
    with pytest.raises(licenze.NonConsentita, match="includes 1 personal template: to save another, delete it. In Pro and Studio"): licenze.controlla_modelli("salva", 1)
    licenza.usa(licenza.chiavi.chiave(fascia="pro", computer=1, seriale=3, scadenza="2027-12-31"))
    assert licenze.stato()["messaggio"] == "Pro licence active, registered to “Studio Prova”, for 1 computer. Valid until 31/12/2027."


def test_prova_e_sola_lettura_in_inglese(licenza, inglese, monkeypatch):
    licenza.usa(None)
    t0 = licenze.orologio(); g = 86400
    s = licenze.stato(t0)
    assert s["messaggio"].startswith("Free trial: 30 days left (until ") and "You have the Pro features except the layered PSD; JPG and PDF exports carry a watermark." in s["messaggio"]
    assert licenze.motivo("export_psd_livelli").startswith("The layered PSD isn't part of the free trial: it comes with Pro and Studio.")
    licenze.stato(t0 + 10 * g)                                       # l'ultima ora vista
    licenza.usa("IMP1-AAAAA")
    s = licenze.stato(t0 + 1 * g)                                    # orologio indietro, chiave salvata che non vale
    assert s["messaggio"].startswith("The saved key isn't valid. The key is incomplete") and "Meanwhile the free trial applies: 20 days left" in s["messaggio"]
    assert s["messaggio"].endswith("The computer's clock is behind its last use: the trial counts from the latest date.")
    licenza.usa(None)
    assert "today is the last day" in licenze.stato(t0 + 29.5 * g)["messaggio"]
    s = licenze.stato(t0 + 40 * g)
    assert s["sola_lettura"] and s["messaggio"].startswith("The free trial ended on ") and "Albums open read-only" in s["messaggio"] and "Enter a licence key" in s["messaggio"]
    licenza.usa("IMP1-AAAAA")
    assert "Albums open read-only" in licenze.stato(t0 + 40 * g)["messaggio"]
    monkeypatch.setattr(licenze, "orologio", lambda: t0 + 40 * g)
    assert licenze.motivo("export_jpg").startswith("Impaginatore is read-only. The saved key isn't valid.")


def test_chiave_non_valida_in_inglese(licenza, inglese, monkeypatch):
    for testo, atteso in (("", "Paste the key you received by email: it starts with IMP1-."), ("ciao", "This isn't an Impaginatore key: the key starts with IMP1-."),
                          ("IMP1-AAAAA", "The key is incomplete: part of it may be missing.")):
        with pytest.raises(K.ChiaveNonValida, match=atteso): licenze.attiva(testo)
    pro = licenza.chiavi.chiave(fascia="pro")
    b = bytearray(K.da_testo(pro)); b[2] = 3
    sbagliata = K.in_testo(bytes(b))
    with pytest.raises(K.ChiaveNonValida, match="This key isn't valid: its contents don't match its signature"): licenze.attiva(sbagliata)
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")
    with pytest.raises(K.ChiaveNonValida, match="Questa chiave non è valida: il contenuto non corrisponde alla firma"): licenze.attiva(sbagliata)    # la verifica in memoria non ricorda la lingua
    monkeypatch.setattr(K, "CHIAVI_PUBBLICHE", {1: K.Pubblica(K.SEGNAPOSTO)})
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    with pytest.raises(K.ChiaveNonValida, match="development build"): K.decodifica(pro)
    assert str(K.errore("licenze.chiave_firma_sconosciuta", numero=7)).endswith("(no. 7): update the program or write to support.")


def test_chiave_di_un_altra_versione_e_scaduta_in_inglese(licenza, inglese):
    with pytest.raises(K.ChiaveNonValida, match="This key is for Impaginatore 1. Impaginatore 2 needs the licence upgrade"): licenze.attiva(licenza.chiavi.chiave(fascia="pro", versione=1))
    with pytest.raises(K.ChiaveNonValida, match="This key is for Impaginatore 3: update the program"): licenze.attiva(licenza.chiavi.chiave(fascia="pro", versione=3))
    licenza.usa(licenza.chiavi.chiave(fascia="laboratorio", scadenza="2026-12-31", intestatario="Lab Bianchi"))
    assert licenze.stato(1.8e9)["messaggio"].startswith("The Lab licence registered to “Lab Bianchi” expired on 31/12/2026. Albums open read-only")
    assert licenze.msg_revocata().startswith("This licence is no longer active")


# ---------------------------------------------------------------- MCP
def test_rifiuti_e_risposte_mcp_in_inglese(editor, home_srv, inglese):
    a = S.Assistente(); p = S.id_progetto(editor.progetto)
    with pytest.raises(S.Rifiuto, match="progetto: use the id that elenca_progetti gives"): a.stato_album("../..")
    with pytest.raises(S.Rifiuto, match="da_spread: a whole number from 1 to 100000 is needed"): a.stato_album(p, 0)
    with pytest.raises(S.Rifiuto, match="filtro: one of tutte, libere"): a.elenca_foto(p, "boh")
    with pytest.raises(S.Rifiuto, match="tono: true or false \\(or nothing\\)"): a.controlla_album(p, tono="x")
    with pytest.raises(S.Rifiuto, match="stelle: true or false$"): a.proponi_bozza(p, stelle=1)
    with pytest.raises(S.Rifiuto, match="gruppo: text of 1 to 100 characters"): S.gruppo("")
    r = a.annulla(p)
    assert r["messaggio"] == "There's nothing to undo." and r["dati_utente"].startswith("Names of photos, projects and folders")
    assert a.ripeti(p)["messaggio"] == "There's nothing to redo."
    assert a.stato_programma()["immagini"]["come_accenderle"] == consenso.spiegazione()
    with pytest.raises(S.Rifiuto, match="Images are off"): a.anteprima_spread(p, 1)
    assert a.salva(p)["salvato"] is True


def test_licenza_che_manca_all_assistente_in_inglese(licenza, inglese, monkeypatch):
    a = S.Assistente()
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    with pytest.raises(S.Rifiuto, match="isn't part of the Essential licence: it comes with Pro and Studio. You'll find the licence in Impaginatore, “Licence” button."): a.stato_programma()
    licenza.usa(None)
    licenze.stato()                                                  # la prova comincia adesso
    monkeypatch.setattr(licenze, "orologio", lambda: 1.9e9)
    with pytest.raises(S.Rifiuto, match="Impaginatore is read-only \\(free trial ended"): a.stato_programma()
    assert S.msg_cambiato().startswith("The album was changed in the editor") and S.msg_non_aperto().startswith("The project isn't open")
    assert S.msg_sola_lettura().endswith("“Licence” button.")


def test_limiti_e_collegamento_in_inglese(inglese, monkeypatch):
    l = S.Limitatore(massimo=1)
    l.passa()
    with pytest.raises(S.Rifiuto, match="Too many requests in a short time"): l.passa()
    grande = {"x": ["a" * 1000] * 100}
    t = S.limita(grande)
    assert "troncato" in grande and grande["troncato"].startswith("Response shortened") and len(t) <= S.MAX_TESTO
    with pytest.raises(S.Rifiuto, match="The response would be too long"): S.limita({"x": "a" * 50000})
    monkeypatch.setattr(C, "programma", lambda: None)
    monkeypatch.setattr(C.subprocess, "Popen", lambda *a, **k: type("P", (), {"poll": lambda self: 1})())
    with pytest.raises(C.Errore, match="Impaginatore didn't start: port 8765 is in use by another program"): C.avvia_programma(attesa=1)
    monkeypatch.setattr(C.subprocess, "Popen", lambda *a, **k: type("P", (), {"poll": lambda self: None})())
    with pytest.raises(C.Errore, match="Impaginatore isn't responding yet"): C.avvia_programma(attesa=0.01)
    e = C.Errore(400, "x", causa="altra_scheda"); assert e.causa == "altra_scheda" and C.Errore(400, "x").causa is None


def test_spiegazione_delle_immagini_nelle_due_lingue(monkeypatch):
    it, en = consenso.spiegazione(), None
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en"); en = consenso.spiegazione()
    for s, interruttore, schermata in ((it, "«L'assistente può vedere le immagini»", "schermata Album"), (en, "“The assistant can see images”", "Albums screen")):
        assert interruttore in s and schermata in s and "--consenti-immagini" in s and "512" in s and "1200" in s
    assert "per spegnerle davvero togli anche l'opzione" in it and "remove the option too" in en
    assert "fuori dal tuo computer" in it and "outside your computer" in en


def test_sdk_mancante_in_inglese(inglese, capsys, monkeypatch):
    import sys
    from impaginatore import mcp
    monkeypatch.setitem(sys.modules, "impaginatore.mcp.server", None)          # l'import fallisce come senza l'SDK
    monkeypatch.delattr(mcp, "server", raising=False)
    assert mcp.main([]) == 2
    assert "needs the official “mcp” SDK" in capsys.readouterr().err


def test_aiuto_in_inglese(inglese, capsys):
    from impaginatore import mcp
    with pytest.raises(SystemExit): mcp.main(["--help"])
    assert "MCP server that connects an AI assistant to Impaginatore" in capsys.readouterr().out


def test_strumenti_dell_assistente_in_inglese(inglese):
    from impaginatore.mcp import server
    assert server.istruzioni().startswith("Impaginatore lays out photo albums")
    srv = server.crea(S.Assistente())
    import asyncio
    tools = {t.name: t for t in asyncio.run(srv.list_tools())}
    assert tools["stato_album"].title == "Album status" and tools["annulla"].description.startswith("Undoes the album's last step")
    assert set(tools) >= {"elenca_progetti", "apri_progetto", "esporta", "miniatura_foto"}, "i nomi non cambiano"


# ---------------------------------------------------------------- validazione, formato, archivio, nomi, percorsi
def test_validazione_in_inglese(inglese):
    def msg(f, *a, **k):
        with pytest.raises(V.ErroreProgetto) as e: f(*a, **k)
        return str(e.value)
    assert msg(V.numero, "x", "z", 0, 1) == "z: must be a number" and msg(V.numero, 1.5, "c", 0, 3, intero=True) == "c: must be a whole number"
    assert msg(V.numero, 5, "z", 0, 1) == "z: must be a number from 0 to 1" and msg(V.numero, 0, "w", 0, 1, escluso=True) == "w: must be a number greater than 0 and no more than 1"
    assert msg(V.booleano, 1, "bw") == "bw: must be true or false" and msg(V.testo, 1, "t") == "t: must be text" and msg(V.testo, "", "t") == "t: can't be empty"
    assert msg(V.testo, "abc", "t", 2) == "t: is too long (at most 2 characters)" and msg(V.testo, "a\x00", "t").startswith("t: contains a character that isn't allowed (U+0000)")
    assert msg(V.scelta, "x", "al", ("left", "center")) == "al: must be one of “left”, “center”"
    assert msg(V.oggetto, [], "o", ("a",)) == "o: must be an object" and msg(V.oggetto, {}, "o", ("a", "b")) == "o: “a”, “b” missing"
    assert msg(V.oggetto, {"a": 1, "x": 1}, "o", ("a",)) == "o: unknown key “x”" and msg(V.oggetto, {"a": 1, "x": 1, "y": 1}, "o", ("a",)) == "o: unknown keys “x”, “y”"
    assert msg(V.lista, {}, "l", 3) == "l: must be a list [ … ]" and msg(V.lista, [1], "l", 3, 2) == "l: must have 2 values" and msg(V.lista, [1] * 4, "l", 3) == "l: too many items (at most 3)"
    assert msg(V.nome_file, "a/b", "n") == "n: “a/b” isn't a valid file name"
    doc = {"formato": 2, "spread": [{"sinistra": {"modo": "I", "elementi": [{"k": "p", "foto": "A", "c": 1, "r": 0, "w": 12, "h": 1}]}, "destra": {"modo": "I", "elementi": []}}]}
    assert msg(V.album, doc) == "spread 1, left page, element 1: the frame goes outside the page grid (12 columns by 8 rows)"
    assert msg(V.album, dict(doc, formato=3)) == "This album was saved by a newer version of Impaginatore (format 3): update the program to open it"
    assert msg(V.album, dict(doc, formato=1)) == "album.json, formato: unknown format (1): this program reads format 2"
    assert msg(V.album, {"spread": []}) == "album.json: “formato” is missing: this isn't an Impaginatore album"
    assert msg(V.progetto, {}) == "progetto.json: “formato_cm” is missing (width and height of the spread in cm)"
    assert msg(V.progetto, {"formato_cm": [1000, 1000], "ppi": 2400}) == "progetto.json, formato_cm: the size and resolution make a spread too large to process"
    assert msg(V.meta, [{"n": "a", "dt": "", "src": ""}]).startswith("_cache/meta.json, photo 1, w: must be a whole number")
    elementi = [{"k": "p", "foto": "Q", "c": 0, "r": 0, "w": 1, "h": 1}]
    assert msg(V.elemento, elementi[0], "e", foto={"A"}) == "e, foto: the photo “Q” isn't in the album"
    mod = {"id": "m1", "nome": "x", "n": 1, "lato": "L", "pages": [{"mode": "I", "items": [{"k": "full"}]}, {"mode": "I", "items": [{"k": "full"}]}]}
    assert msg(V.modello, mod) == "modello, right page: the template applies to the other page only: this one must be empty"
    assert msg(V.modello, dict(mod, id="!")).endswith("must be a code of letters and digits (at most 40)")


def test_formato_in_inglese(inglese, tmp_path):
    f = tmp_path / "album.json"
    f.write_bytes(b'{"formato": 2, "formato": 3}')
    with pytest.raises(V.ErroreProgetto, match='album.json isn\'t valid: the key “formato” appears twice'): formato.leggi_json_rigoroso(str(f))
    f.write_bytes(b"[NaN]")
    with pytest.raises(V.ErroreProgetto, match="value not allowed: NaN"): formato.leggi_json_rigoroso(str(f))
    f.write_bytes(b"\xff")
    with pytest.raises(V.ErroreProgetto, match="album.json isn't UTF-8 text \\(byte 0\\)"): formato.leggi_json_rigoroso(str(f))
    f.write_bytes(b"{")
    with pytest.raises(V.ErroreProgetto, match="album.json isn't valid JSON \\(line 1, column 2"): formato.leggi_json_rigoroso(str(f))
    f.write_bytes(b"x" * 2048)
    with pytest.raises(V.ErroreProgetto, match="album.json is too large \\(at most 0 MB\\)"): formato.leggi_json_rigoroso(str(f), massimo=1024)
    with pytest.raises(V.ErroreProgetto, match="album.json is too large \\(0 MB\\)"): formato.leggi_json(str(f), massimo=1024)
    with pytest.raises(V.ErroreProgetto, match="a value can't be saved"): formato.testo_progetto({"formato_cm": [30, 30], "x": {1, 2}})
    (tmp_path / "progetto.json").write_text("{", encoding="utf-8")
    with pytest.raises(V.ErroreProgetto, match="progetto.json isn't valid JSON"): formato.leggi_progetto(str(tmp_path))
    with pytest.raises(V.ErroreProgetto, match="an element of the layout isn't valid"): formato.testo_album_controllato([[["I", [{"k": "p", "i": 0}]], ["I", []]]], lambda i: "a")


@pytest.mark.filterwarnings("ignore:Duplicate name")
def test_archivio_in_inglese(inglese, tmp_path):
    brutto = tmp_path / "a.zip"; brutto.write_bytes(b"no")
    with pytest.raises(V.ErroreProgetto, match="The file isn't a readable ZIP"): archivio.estrai(str(brutto), str(tmp_path / "d"))
    z = tmp_path / "b.zip"
    with zipfile.ZipFile(z, "w") as f: f.writestr("../x.json", "{}")
    with pytest.raises(V.ErroreProgetto, match="This ZIP file isn't safe to import \\(path that leaves the folder “../x.json”\\): it wasn't imported."): archivio.estrai(str(z), str(tmp_path / "d"))
    with zipfile.ZipFile(z, "w") as f: f.writestr("/x.json", "{}")
    with pytest.raises(V.ErroreProgetto, match="absolute path “/x.json”"): archivio.estrai(str(z), str(tmp_path / "d"))
    with zipfile.ZipFile(z, "w") as f: f.writestr("a/progetto.json", "{}"); f.writestr("a/prog.exe", "x"); f.writestr("a/progetto.json", "[]")
    avvisi = []; archivio.estrai(str(z), str(tmp_path / "e"), avvisi)
    assert avvisi[0] == "1 file that doesn't belong in an album (programs, scripts or other) wasn't extracted" and "“a/progetto.json” appears twice: kept the first" in avvisi[1:]
    with zipfile.ZipFile(z, "w") as f:
        for k in range(archivio.MAX_FILE + 1): f.writestr(f"{k}.json", "")
    with pytest.raises(V.ErroreProgetto, match="it contains more than 20000 files"): archivio.estrai(str(z), str(tmp_path / "f"))


def test_nomi_e_percorsi_in_inglese(inglese, tmp_path):
    for nome, atteso in (("", "Enter the album name"), ("a" * 200, "The name is too long: at most 120 characters"), ("a\nb", "The name contains characters that aren't allowed")):
        with pytest.raises(ValueError, match=atteso): nomi.nome_progetto(nome)
    r = percorsi.Radici(); r.scelta(str(tmp_path))
    for cosa, atteso in (("cartella_foto", "that photos folder"), ("foto_o_cartella", "that photo or folder"), ("questo_percorso", "this path"), ("la mia cartella", "la mia cartella")):
        with pytest.raises(percorsi.FuoriDalleRadici, match=f"I can't use {atteso}: it's outside the album folders and the ones you've chosen. Choose it with “Choose…”"): r.controlla("/etc/passwd", cosa)
    assert r.controlla(str(tmp_path)) == percorsi.reale(str(tmp_path))


# ---------------------------------------------------------------- schermata, finestre di sistema, aggiornamenti
def test_schermata_in_inglese(home, inglese, tmp_path):
    with pytest.raises(ValueError, match="Measurements out of range: width 5–300 cm, height 5–200 cm"): home.nuovo({"nome": "x", "w": "1", "h": "1"})
    with pytest.raises(ValueError, match="invalid measurement"): home.num("0")
    with pytest.raises(ValueError, match="The photos folder doesn't exist"): home.nuovo({"nome": "x", "w": "30", "h": "30", "foto": str(tmp_path / "no")})
    with pytest.raises(ValueError, match="Invalid measurements: “abc” isn't a number"): home.nuovo({"nome": "x", "w": "30", "h": "30", "abb": "abc"})
    with pytest.raises(ValueError, match="Invalid measurements: margine_mm: must be a number from 0 to 500"): home.nuovo({"nome": "x", "w": "30", "h": "30", "margine": "900"})
    with pytest.raises(ValueError, match="album not in the list"): home.apri(str(tmp_path / "boh"))
    assert home.scegli_cartella() == "" and home.importa_zip() == ""


def test_finestre_di_sistema_in_inglese(inglese):
    visti = []

    class Prova(dialoghi.Dialoghi):
        def _scegli(self, tipo, messaggio): visti.append((tipo, messaggio)); return []
    p = Prova(); p.scegli_cartella(); p.scegli_zip(); p.scegli_percorsi(True); p.scegli_percorsi(); p.scegli_cartella("Mio")
    assert visti == [("cartella", "Choose the folder"), ("zip", "Choose the album's ZIP file"), ("cartella", "Choose the folder"), ("foto", "Choose the photos"), ("cartella", "Mio")]


def test_aggiornamenti_in_inglese(inglese, monkeypatch):
    a = aggiornamenti.NonDisponibili()
    assert a.motivo == "Automatic updates aren't available in this installation" and a.stato()["attuale"]["titolo"] == "installed version"
    with pytest.raises(ValueError, match="aren't available"): a.aggiorna()
    monkeypatch.setenv("IMPAGINATORE_AGGIORNAMENTI", "no")
    assert aggiornamenti.predefiniti().motivo == "Automatic updates are switched off (IMPAGINATORE_AGGIORNAMENTI)"
    from impaginatore.aggiornamenti import firmati, installazione, sorgenti
    f = firmati.PacchettiFirmati(sorgenti.SorgenteGitHub(""), installazione.InstallazionePython())
    assert f.stato()["motivo"] == "Updates aren't active yet: the channel for new versions isn't set up in this version"
    assert f.stato()["attuale"]["titolo"] == "installed version"
    with pytest.raises(ValueError, match="isn't set up"): f.aggiorna()
    c = firmati.PacchettiFirmati(sorgenti.SorgenteGitHub("a/b"), installazione.InstallazioneCompilata())
    assert c.stato()["motivo"] == "The installed program will update with its installer: not yet available in this version"


def test_lingua_cambiata_a_meta_si_vede_subito(monkeypatch):
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")
    assert nomi_it() == "Scrivi il nome dell'album"
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    assert nomi_it() == "Enter the album name" and lingua.attuale() == "en"


def test_prodotti_dei_laboratori_in_inglese(editor, home_srv, inglese):
    a = S.Assistente(); p = S.id_progetto(editor.progetto)
    with pytest.raises(S.Rifiuto, match="prodotto: the id that elenca_prodotti gives, for example “generico/quadrato-30”"): a.imposta_prodotto(p, "boh")
    with pytest.raises(S.Rifiuto, match="misure: numbers .*, or the product"): a.crea_progetto("x", "a", 1)
    assert licenze.motivo("preset_laboratori", dict(licenze.stato(), sola_lettura=False, stato="prova")).startswith("Using the labs' catalogues isn't part of the free trial")


def test_finestra_del_catalogo_in_inglese(inglese):
    visti = []

    class Prova(dialoghi.Dialoghi):
        def _scegli(self, tipo, messaggio): visti.append((tipo, messaggio)); return []
    Prova().scegli_catalogo(); Prova().scegli_catalogo("Mio")
    assert visti == [("catalogo", "Choose the lab's catalogue (.json)"), ("catalogo", "Mio")]


def nomi_it():
    try: nomi.nome_progetto("")
    except ValueError as e: return str(e)
