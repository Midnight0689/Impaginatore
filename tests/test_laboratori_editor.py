"""T-208 nel programma: album nuovo da un prodotto (schermata dei progetti), importazione di un catalogo con la finestra del
sistema, prodotto di un album aperto (operazione dell'editor, con annulla), controllo e bozza con le regole del prodotto,
consegna al laboratorio (file, nomi, misure, profilo, riepilogo, cartella nuova), assistente AI (MCP)."""
import json
import os
import types

import pytest
from PIL import Image

from aiuti import attendi_log
from impaginatore import formato, licenze
from impaginatore import laboratori as L
from impaginatore.desktop import dialoghi as D
from impaginatore.laboratori import catalogo as C
from impaginatore.piattaforma import dialoghi


def prodotto(**campi):
    """prodotto con il formato dell'album della fixture «progetto» (spread 60 × 22,5 cm, abbondanza 0)"""
    p = {"id": "album-30", "nome": "Album 30 × 22,5", "pagina_cm": [30, 22.5], "abbondanza_mm": 0, "ppi": 150, "consegna": {"nome": "LAB_{album}_{n}"}}
    p.update(campi); return p


def catalogo(**campi):
    d = {"formato_catalogo": 1, "id": "lab-prova", "nome": "Album di prova", "laboratorio": "Laboratorio di prova", "data": "2026-11-01", "prodotti": [prodotto()]}
    d.update(campi); return d


def installa(doc, nome="lab.json"):
    d = L.cartella_utente(); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, nome), "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False)


def album(c, n=3):
    """n spread con le prime foto, come li fa la pagina"""
    nomi = [p["n"] for p in c.get("/api/state")["photos"]]; k = 0
    for s, q in enumerate((3, 2, 3, 2)[:n]):
        t = c.post("/api/templates", {"photos": nomi[k:k + q]})["items"][0]; k += q
        c.post("/api/op", dict(op="newspread", pos=s, L=t["L"], R=t["R"]))


def senza_licenza_laboratori(monkeypatch):
    vero = licenze.stato
    monkeypatch.setattr(licenze, "stato", lambda *a, **k: (lambda s: dict(s, funzioni=dict(s["funzioni"], preset_laboratori=False)))(vero(*a, **k)))


def progetto_json(c): return formato.leggi_json(os.path.join(c.progetto, "progetto.json"))


# ---------------------------------------------------------------- schermata dei progetti
def test_album_nuovo_dal_prodotto(home_srv):
    c = home_srv
    e = c.get("/api/cataloghi")
    assert [x["id"] for x in e["cataloghi"]] == ["generico"] and e["cartella"] == L.cartella_utente() and e["problemi"] == []
    p = c.post("/api/nuovo", {"nome": "Quadrato", "w": "10", "h": "10", "abb": "0", "prodotto": "generico/quadrato-30"})["path"]
    cfg = formato.leggi_json(os.path.join(p, "progetto.json"))
    assert (cfg["formato_cm"], cfg["abbondanza_mm"], cfg["ppi"]) == ([60, 30], 3, 300), "il formato è quello del prodotto, non quello scritto"
    assert cfg["prodotto"] == L.per_progetto(*L.trova("generico", "quadrato-30"))
    installa(catalogo(prodotti=[prodotto(abbondanza_mm=5, ppi=250)]))
    p = c.post("/api/nuovo", {"nome": "Lab", "prodotto": {"catalogo": "lab-prova", "prodotto": "album-30"}})["path"]
    cfg = formato.leggi_json(os.path.join(p, "progetto.json"))
    assert (cfg["formato_cm"], cfg["abbondanza_mm"], cfg["ppi"], cfg["prodotto"]["catalogo"]) == ([60, 22.5], 5, 250, "lab-prova")
    ok, r = c.prova("/api/nuovo", {"nome": "X", "prodotto": "altro/x"})
    assert not ok and "Catalogo «altro» non trovato" in r["errore"]
    p = c.post("/api/nuovo", {"nome": "Libero", "w": "50", "h": "20"})["path"]
    assert "prodotto" not in formato.leggi_json(os.path.join(p, "progetto.json")), "senza prodotto: come prima"


def test_album_nuovo_senza_licenza_dei_laboratori(home_srv, monkeypatch):
    installa(catalogo()); senza_licenza_laboratori(monkeypatch)
    ok, r = home_srv.prova("/api/nuovo", {"nome": "Lab", "prodotto": "lab-prova/album-30"})
    assert not ok and "L'uso dei cataloghi dei laboratori non fa parte" in r["errore"]
    assert [x["consentito"] for x in home_srv.get("/api/cataloghi")["cataloghi"]] == [True, False]
    assert home_srv.post("/api/nuovo", {"nome": "Generico", "prodotto": "generico/quadrato-20"})["path"]


class Scelte(dialoghi.Dialoghi):
    def __init__(self, r): self.r, self.chieste = r, []

    def _scegli(self, tipo, messaggio):
        self.chieste.append((tipo, messaggio)); return list(self.r)


def test_importa_catalogo_dalla_schermata(home_srv, tmp_path, chiavi_prova):
    c = home_srv; s = Scelte([]); dialoghi.imposta(s)
    assert c.post("/api/importa-catalogo") == {"annullato": True} and s.chieste == [("catalogo", "Scegli il catalogo del laboratorio (.json)")]
    f = tmp_path / "rossi.json"; f.write_text(json.dumps(C.firma(catalogo(), chiavi_prova.seme, 1)), encoding="utf-8")
    s.r = [str(f)]
    r = c.post("/api/importa-catalogo", {"path": "/etc/passwd"})
    assert r["id"] == "lab-prova" and r["verificato"] is True and r["prodotti"] == 1, "il file è quello scelto nella finestra, mai uno della richiesta"
    assert [x["id"] for x in c.get("/api/cataloghi")["cataloghi"]] == ["generico", "lab-prova"]
    f.write_text("{", encoding="utf-8")
    ok, r = c.prova("/api/importa-catalogo", {})
    assert not ok and "rossi.json" not in r["errore"] and "non è un JSON valido" in r["errore"]


def test_finestre_di_scelta_del_catalogo(monkeypatch):
    import subprocess
    cmd = []
    monkeypatch.setattr(subprocess, "run", lambda c, *a, **k: (cmd.append(c), types.SimpleNamespace(returncode=0, stdout="/home/s/lab.json\n"))[1])
    for cls in (dialoghi.Mac, dialoghi.Zenity, dialoghi.Kdialog, dialoghi.Tk):
        assert cls().scegli_catalogo("Scegli") == (os.path.normpath("/home/s/lab.json") if cls is dialoghi.Tk else "/home/s/lab.json")
    assert '"public.json"' in cmd[0][2] and cmd[0][-1] == "Scegli"
    assert cmd[1][-2:] == ["--file-filter", "Catalogo | *.json"] and cmd[2][-1] == "*.json" and cmd[3][3] == "catalogo"
    dialoghi.imposta(Scelte(["/x/lab.json"])); assert dialoghi.scegli_catalogo() == "/x/lab.json"
    dialoghi.imposta(None); assert dialoghi.scegli_catalogo() == "", "nessuna finestra (test): annullato"

    class Finestra:
        localization, scelte = {}, []

        def create_file_dialog(self, tipo, **kw): self.scelte.append((tipo, kw, dict(self.localization))); return ("/x/lab.json",)
    f = Finestra()
    assert D.DialoghiFinestra(f, types.SimpleNamespace(OPEN=10, FOLDER=20)).scegli_catalogo("Catalogo") == os.path.normpath("/x/lab.json")
    assert f.scelte == [(10, dict(file_types=(D.filtro_catalogo(),)), {"linux.openFile": "Catalogo"})]


# ---------------------------------------------------------------- il prodotto dell'album aperto
def test_prodotto_dell_album_si_annulla_e_si_salva(editor):
    c = editor; installa(catalogo(stato="da_confermare"))
    assert c.get("/api/state")["prodotto"] is None
    e = c.get("/api/prodotti")
    assert [x["id"] for x in e["cataloghi"]] == ["generico", "lab-prova"]
    assert all(p["incompatibile"] for p in e["cataloghi"][0]["prodotti"]), "i formati generici hanno 3 mm di abbondanza: l'album ne ha 0"
    assert e["cataloghi"][1]["prodotti"][0]["incompatibile"] is None
    st = c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    pr = st["prodotto"]
    assert pr["prodotto"]["id"] == "album-30" and (pr["verificato"], pr["generico"], pr["installato"], pr["avviso"], pr["stato"]) == (False, False, True, None, "da_confermare")
    assert st["esito"] == {"prodotto": "Album 30 × 22,5", "laboratorio": "Laboratorio di prova"} and st["annulla"]["nome"] == "Prodotto del laboratorio" and st["dirty"]
    c.post("/api/save")
    assert progetto_json(c)["prodotto"] == L.per_progetto(*L.trova("lab-prova", "album-30"))
    st = c.post("/api/op", {"op": "undo"}); assert st["prodotto"] is None
    c.post("/api/save"); assert "prodotto" not in progetto_json(c), "annullato: tolto anche dal file"
    st = c.post("/api/op", {"op": "redo"}); assert st["prodotto"]["catalogo"] == "lab-prova"
    st = c.post("/api/op", {"op": "prodotto", "prodotto": None}); assert st["prodotto"] is None and st["annulla"]["nome"] == "Prodotto del laboratorio"
    n = len(c.E.UNDO); c.post("/api/op", {"op": "prodotto"}); assert len(c.E.UNDO) == n, "togliere un prodotto che non c'è non è un passo"
    ok, r = c.prova("/api/op", {"op": "prodotto", "prodotto": "generico/quadrato-30"})
    assert not ok and "il formato di un album fatto non si cambia" in r["errore"] and c.get("/api/state")["prodotto"] is None
    ok, r = c.prova("/api/op", {"op": "prodotto", "prodotto": "generico/orizzontale-30x22"})
    assert not ok and "L'album ha 0 mm di abbondanza, il prodotto «Orizzontale 30 × 22,5» ne chiede 3" in r["errore"]
    ok, r = c.prova("/api/op", {"op": "prodotto", "prodotto": "lab-prova/../x"})
    assert not ok and "Prodotto non valido" in r["errore"]


def test_prodotto_e_licenza_nell_editor(editor, monkeypatch):
    installa(catalogo()); senza_licenza_laboratori(monkeypatch)
    ok, r = editor.prova("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    assert not ok and r["licenza"] is True and "cataloghi dei laboratori" in r["errore"]
    assert editor.get("/api/state")["licenza"]["funzioni"]["preset_laboratori"] is False


def test_progetti_di_prima_e_prodotti_sconosciuti(progetto, apri_editor):
    """un progetto senza prodotto si apre e si salva come prima; uno con un prodotto che questa versione non capisce (una
    versione più recente) si apre lo stesso e il file lo tiene com'era"""
    pj = os.path.join(progetto, "progetto.json"); prima = formato.leggi_json(pj)
    c = apri_editor(progetto); c.post("/api/save")
    assert formato.leggi_json(pj).get("prodotto", "assente") == "assente" and c.get("/api/state")["prodotto"] is None
    c.srv.shutdown(); c.srv.server_close()
    futuro = {"formato_catalogo": 2, "catalogo": "lab-futuro", "qualcosa": [1, 2]}
    formato.scrivi_progetto(progetto, dict(prima, prodotto=futuro))
    c = apri_editor(progetto)
    assert c.get("/api/state")["prodotto"] is None
    c.post("/api/op", {"op": "prodotto"}); c.post("/api/save")
    assert formato.leggi_json(pj)["prodotto"] == futuro
    installa(catalogo())
    c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"}); c.post("/api/save")
    assert formato.leggi_json(pj)["prodotto"]["catalogo"] == "lab-prova"
    c.post("/api/op", {"op": "undo"}); c.post("/api/save")
    assert formato.leggi_json(pj)["prodotto"] == futuro, "annullato: torna quello di prima"


def test_prodotto_ricevuto_con_un_altro_formato(progetto, apri_editor):
    """un progetto ricevuto con il prodotto di un altro formato: il controllo lo blocca e la consegna non parte"""
    installa(catalogo(prodotti=[prodotto(pagina_cm=[25, 25])]))
    cfg = formato.leggi_json(os.path.join(progetto, "progetto.json"))
    formato.scrivi_progetto(progetto, dict(cfg, prodotto=L.per_progetto(*L.trova("lab-prova", "album-30"))))
    c = apri_editor(progetto)
    st = c.get("/api/state")["prodotto"]
    assert st["avviso"].startswith("L'album ha pagine di 30 × 22,5 cm, il prodotto «Album 30 × 22,5» di 25 × 25 cm")
    p = c.post("/api/controlla", {})["problemi"]
    assert [x["testo"] for x in p if x["tipo"] == "prodotto"] == [st["avviso"]]
    ok, r = c.prova("/api/export", {"fmt": "consegna"})
    assert not ok and "il formato di un album fatto non si cambia" in r["errore"]


# ---------------------------------------------------------------- controllo e bozza con le regole del prodotto
def test_controllo_con_le_regole_del_prodotto(editor):
    c = editor
    album(c, 3)
    c.post("/api/op", {"op": "addtext", "s": 0, "fx": 0.0, "fy": 0.4, "fw": 0.1})               # testo sul bordo sinistro
    c.post("/api/op", {"op": "addtext", "s": 0, "fx": 0.45, "fy": 0.4, "fw": 0.1})              # testo sulla piega
    base = c.post("/api/controlla", {"tono": False})["problemi"]
    assert not any(p["tipo"] in ("prodotto", "sicurezza", "piega") for p in base)
    cornici = sum(1 for s in c.get("/api/state")["spreads"] for it in s["items"] if it["k"] != "t")
    installa(catalogo(prodotti=[prodotto(spread_min=5, sicurezza_mm=8, piega_mm=10, ppi=600, ppi_minimi=600)]))
    c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    p = c.post("/api/controlla", {"tono": False})["problemi"]
    assert [x["testo"] for x in p if x["tipo"] == "prodotto"] == ["L'album ha 3 spread, il prodotto «Album 30 × 22,5» ne vuole almeno 5"]
    ris = [x for x in p if x["tipo"] == "risoluzione"]
    assert len(ris) == cornici and all(x["livello"] == "blocca" and "ne servono almeno 600" in x["testo"] for x in ris), "le soglie di risoluzione del prodotto"
    assert [(x["tipo"], x["livello"], x["s"]) for x in p if x["tipo"] in ("sicurezza", "piega")] == [("sicurezza", "guarda", 0), ("piega", "guarda", 0)]
    assert next(x for x in p if x["tipo"] == "sicurezza")["testo"] == "Spread 1: un testo è a meno di 8 mm dal bordo: il laboratorio lo può tagliare"
    assert not any(x["tipo"] == "prodotto" for x in c.post("/api/controlla", {"spread": [0], "tono": False})["problemi"]), "i problemi dell'album intero solo nel controllo di tutto l'album"
    installa(catalogo(prodotti=[prodotto(spread_max=2, ppi=600, ppi_minimi=72, ppi_consigliati=1200)]))
    c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    p = c.post("/api/controlla", {"tono": False})["problemi"]
    assert [x["testo"] for x in p if x["tipo"] == "prodotto"] == ["L'album ha 3 spread, il prodotto «Album 30 × 22,5» ne ammette al massimo 2"]
    assert not any(x["tipo"] in ("sicurezza", "piega") for x in p), "senza zona di sicurezza e senza piega nel prodotto: niente"
    ris = [x for x in p if x["tipo"] == "risoluzione"]
    assert len(ris) == cornici and all(x["livello"] == "guarda" or "almeno 72" in x["testo"] for x in ris) and any(x["livello"] == "guarda" for x in ris)


def test_bozza_entro_gli_spread_del_prodotto(editor):
    c = editor
    installa(catalogo(prodotti=[prodotto(spread_max=2)]))
    c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    b = c.post("/api/bozza", {})
    assert len(b["spreads"]) <= 2 and b["foto"] == sum(len(s["foto"]) for s in b["spreads"])
    b = c.post("/api/bozza", {"per_spread": 1, "stelle": True})
    assert len(b["spreads"]) == 2 and b["limite_prodotto"]["spread_max"] == 2 and b["limite_prodotto"]["foto_escluse"] > 0 and b["capitoli"] >= 1
    tre = c.post("/api/bozza", {})["spreads"] * 2
    ok, r = c.prova("/api/op", {"op": "bozza", "spreads": tre[:3]})
    assert not ok and "ammette al massimo 2 spread e l'album ne ha 0: se ne possono aggiungere ancora 2, non 3" in r["errore"]
    st = c.post("/api/op", {"op": "bozza", "spreads": tre[:2]}); assert len(st["spreads"]) == 2
    ok, r = c.prova("/api/bozza", {})
    assert not ok and "non se ne possono aggiungere altri" in r["errore"]
    ok, r = c.prova("/api/op", {"op": "bozza", "spreads": tre[:1]})
    assert not ok and "non se ne possono aggiungere altri" in r["errore"]


# ---------------------------------------------------------------- consegna
def test_consegna_al_laboratorio(editor, chiavi_prova):
    c = editor
    ok, r = c.prova("/api/export", {"fmt": "consegna"})
    assert not ok and "non ha ancora il prodotto del laboratorio" in r["errore"]
    installa(catalogo()); c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    ok, r = c.prova("/api/export", {"fmt": "consegna"})
    assert not ok and "Non c'è nessuno spread da esportare" in r["errore"]
    assert os.listdir(os.path.join(c.progetto, "Esportazioni", "Consegna")) == [], "un controllo che non passa non lascia cartelle"
    album(c, 2)
    p = prodotto(spread_min=3, copertina="Rigida, in lino grigio", consegna={"nome": "LAB_{album}_{pagina}", "file": "pagine", "cifre": 3, "qualita": 90})
    installa(C.firma(catalogo(prodotti=[p]), chiavi_prova.seme, 1))
    c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    assert c.post("/api/export", {"fmt": "consegna"}) == {"spread": 2}
    L_ = attendi_log(c)
    dest = next(x[len("RISULTATO:"):] for x in L_ if x.startswith("RISULTATO:"))
    assert os.path.dirname(dest) == os.path.join(c.progetto, "Esportazioni", "Consegna") and os.path.basename(dest).startswith("Album 30 × 22,5 20")
    assert L_[0] == f"Esporto 2 spread in CONSEGNA → {dest}" and "  spread 1: LAB_Prova_001.jpg, LAB_Prova_002.jpg" in L_ and "ESPORTATI 2 spread su 2" in L_
    assert sorted(os.listdir(dest)) == ["LAB_Prova_001.jpg", "LAB_Prova_002.jpg", "LAB_Prova_003.jpg", "LAB_Prova_004.jpg", "Riepilogo consegna.txt"]
    with Image.open(os.path.join(dest, "LAB_Prova_003.jpg")) as im:
        assert im.size == (1772, 1329) and round(im.info["dpi"][0]) == 150 and im.info.get("icc_profile") and im.mode == "RGB", "pagina 30 × 22,5 cm a 150 ppi, sRGB incorporato"
    t = open(os.path.join(dest, "Riepilogo consegna.txt"), encoding="utf-8").read()
    assert "Firma del catalogo: verificato" in t and "uno per pagina · 1772 × 1329 px" in t and "Spread nell'album: 2 (il prodotto ne vuole almeno 3)" in t
    assert "Copertina (da preparare a parte, Impaginatore non la esporta): Rigida, in lino grigio" in t and "File (4):" in t and "filigrana" not in t
    # di nuovo: un'altra cartella, mai sopra quella di prima
    c.post("/api/export", {"fmt": "consegna", "range": "2"}); L2 = attendi_log(c)
    dest2 = next(x[len("RISULTATO:"):] for x in L2 if x.startswith("RISULTATO:"))
    assert dest2 != dest and sorted(os.listdir(dest)) == sorted(os.listdir(dest)) and len(os.listdir(dest2)) == 3


def test_consegna_cartella_scelta_e_prova(editor, licenza):
    c = editor; album(c, 1); installa(catalogo())
    c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    vuota = os.path.join(c.progetto, "Per il lab"); os.makedirs(vuota)
    c.post("/api/export", {"fmt": "consegna", "dest": vuota}); L_ = attendi_log(c)
    assert f"RISULTATO:{vuota}" in L_ and sorted(os.listdir(vuota)) == ["LAB_Prova_01.jpg", "Riepilogo consegna.txt"], "cartella scelta vuota: si usa quella"
    c.post("/api/export", {"fmt": "consegna", "dest": vuota}); L_ = attendi_log(c)
    dentro = next(x[len("RISULTATO:"):] for x in L_ if x.startswith("RISULTATO:"))
    assert os.path.dirname(dentro) == vuota and os.listdir(dentro), "cartella scelta piena: una nuova dentro"
    with Image.open(os.path.join(dentro, "LAB_Prova_01.jpg")) as im: assert im.size == (3543, 1329) and im.info.get("icc_profile")
    licenza.usa(None)                                                          # prova gratuita: la filigrana
    prova = os.path.join(c.progetto, "Prova")
    c.post("/api/export", {"fmt": "consegna", "dest": prova}); attendi_log(c)
    assert "filigrana e non vanno stampati" in open(os.path.join(prova, "Riepilogo consegna.txt"), encoding="utf-8").read()


def test_consegna_licenza_e_spread_saltati(editor, monkeypatch):
    c = editor; E = c.E; album(c, 2); installa(catalogo())
    c.post("/api/op", {"op": "prodotto", "prodotto": "lab-prova/album-30"})
    d = lambda n: os.path.join(c.progetto, "Consegne", n)
    rotto = E.A.render
    monkeypatch.setattr(E.A, "render", lambda tup, *a, **k: (_ for _ in ()).throw(MemoryError()) if tup == E.spread_tuple(1) else rotto(tup, *a, **k))
    c.post("/api/export", {"fmt": "consegna", "dest": d("a")}); L_ = attendi_log(c)
    assert "SALTATO spread 2 -> memoria insufficiente: prova a esportare meno spread alla volta" in L_ and "ERRORE: 1 spread non esportato (vedi sopra)" in L_
    assert "ESPORTATI 1 spread su 2" in L_ and sorted(os.listdir(d("a"))) == ["LAB_Prova_01.jpg", "Riepilogo consegna.txt"]
    scrivi = E._scrivi_img; monkeypatch.setattr(E, "_scrivi_img", lambda im, f, **kw: open(f, "wb").write(b"x"))
    c.post("/api/export", {"fmt": "consegna", "range": "1", "dest": d("b")}); L_ = attendi_log(c)
    assert "SALTATO spread 1 -> file vuoto" in L_ and not any(x.startswith("RISULTATO:") for x in L_) and "File (0):" in open(os.path.join(d("b"), "Riepilogo consegna.txt"), encoding="utf-8").read()
    monkeypatch.setattr(E, "_scrivi_img", scrivi); monkeypatch.setattr(E.A, "render", rotto)
    senza_licenza_laboratori(monkeypatch)
    ok, r = c.prova("/api/export", {"fmt": "consegna", "dest": d("c")})
    assert not ok and r["licenza"] is True and not os.path.exists(d("c"))
    g = L.per_progetto(*L.trova("generico", "orizzontale-30x22")); E.CFG["prodotto"] = dict(g, prodotto=dict(g["prodotto"], abbondanza_mm=0))
    assert c.prova("/api/export", {"fmt": "consegna", "range": "1", "dest": d("d")})[0] is False, "un prodotto generico cambiato non è più generico"
    E.CFG["prodotto"] = g; E.CFG["abbondanza_mm"] = 3
    assert c.prova("/api/export", {"fmt": "consegna", "range": "1", "dest": d("e")})[0] is True, "il Generico è di tutti"
    attendi_log(c)


# ---------------------------------------------------------------- assistente AI (MCP)
def test_assistente_prodotti_e_consegna(editor, home_srv, monkeypatch):
    from impaginatore.mcp import collegamento as MC
    from impaginatore.mcp import strumenti as S
    monkeypatch.setattr(MC, "avvia_programma", lambda attesa=None: MC.programma())          # la schermata di questo test, mai il programma vero
    a = S.Assistente(); p = S.id_progetto(editor.progetto)
    installa(catalogo(stato="da_confermare", laboratorio="Lab <b>Rossi</b>", prodotti=[prodotto(spread_max=40)]))
    installa({"rotto": True}, "rotto.json")
    el = a.elenca_prodotti()
    assert el["cataloghi_non_letti"] == 1 and "generico/quadrato-30" in [x["prodotto"] for x in el["prodotti"]]
    assert el["prodotti"][-1] == dict(prodotto="lab-prova/album-30", nome="Album 30 × 22,5", laboratorio="Lab <b>Rossi</b>", catalogo="Album di prova", pagina_cm=[30, 22.5],
                                      abbondanza_mm=0, ppi=150, spread_max=40, verificato=False, da_confermare=True, generico=False, consentito=True)
    for cattivo in ("../x", "lab-prova/album-30/x", 7, "/etc/passwd"):
        with pytest.raises(S.Rifiuto, match="prodotto: l'id che dà elenca_prodotti"): a.imposta_prodotto(p, cattivo)
        with pytest.raises(S.Rifiuto, match="prodotto: l'id che dà elenca_prodotti"): a.crea_progetto("X", prodotto=cattivo)
    with pytest.raises(S.Rifiuto, match="misure: numeri .*oppure il prodotto"): a.crea_progetto("X")
    assert a._riassunto(p)["prodotto"] is None
    r = a.imposta_prodotto(p, "lab-prova/album-30")
    assert r["prodotto"] == dict(prodotto="lab-prova/album-30", nome="Album 30 × 22,5", laboratorio="Lab <b>Rossi</b>", verificato=False, da_confermare=True)
    assert r["annulla"]["nome"] == "Prodotto del laboratorio" and editor.E.UNDO[-1]["assistente"] is True
    assert a._riassunto(p)["prodotto"]["prodotto"] == "lab-prova/album-30"
    with pytest.raises(S.Rifiuto, match="il formato di un album fatto non si cambia"): a.imposta_prodotto(p, "generico/quadrato-30")
    album(editor, 1)
    e = a.esporta(p, "consegna")
    assert e["finita"] is True and e["spread_esportati"] == 1 and e["errori"] == [] and e["cartella"].startswith(os.path.join("Esportazioni", "Consegna", "Assistente "))
    assert sorted(os.listdir(os.path.join(editor.progetto, e["cartella"]))) == ["LAB_Prova_01.jpg", "Riepilogo consegna.txt"]
    assert a.imposta_prodotto(p, None)["prodotto"] is None
    with pytest.raises(S.Rifiuto, match="non ha ancora il prodotto del laboratorio"): a.esporta(p, "consegna")
    altro = L.per_progetto(*L.trova("lab-prova", "album-30")); altro["prodotto"]["pagina_cm"] = [20, 20]; editor.E.CFG["prodotto"] = altro
    assert a._riassunto(p)["prodotto"]["avviso"].startswith("L'album ha pagine di 30 × 22,5 cm")
    r = a.crea_progetto("Dal laboratorio", prodotto="lab-prova/album-30")
    cfg = formato.leggi_json(os.path.join(home_srv.modulo.PROGETTI, r["cartella"], "progetto.json"))
    assert (cfg["formato_cm"], cfg["prodotto"]["prodotto"]["id"]) == ([60, 22.5], "album-30")
