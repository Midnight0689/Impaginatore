"""T-208: pacchetti catalogo dei laboratori. Formato e controllo rigoroso (dato non fidato), firma Ed25519 con le chiavi
delle licenze, cataloghi del programma e dell'utente, importazione, prodotto in progetto.json, file della consegna."""
import copy
import json
import os

import pytest
from PIL import Image

from impaginatore import laboratori as L
from impaginatore import licenze, nomi
from impaginatore.laboratori import catalogo as C
from impaginatore.laboratori import consegna as CO
from impaginatore.licenze import chiave as K


def prodotto(**campi):
    p = {"id": "album-30", "nome": "Album 30 × 22,5", "pagina_cm": [30, 22.5], "abbondanza_mm": 0, "ppi": 200, "consegna": {"nome": "{album} - Spread {n}"}}
    p.update(campi); return p


def catalogo(**campi):
    d = {"formato_catalogo": 1, "id": "lab-prova", "nome": "Album di prova", "laboratorio": "Laboratorio di prova", "data": "2026-11-01", "prodotti": [prodotto()]}
    d.update(campi); return d


def scrivi(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8"); return str(path)


def errore(fn, *a, **k):
    with pytest.raises(C.CatalogoNonValido) as e: fn(*a, **k)
    return str(e.value)


@pytest.fixture
def utente():
    """cartella dei cataloghi dell'utente (nella casa finta)"""
    d = L.cartella_utente(); os.makedirs(d, exist_ok=True)
    from pathlib import Path
    return Path(d)


# ---------------------------------------------------------------- formato
def test_prodotto_completo_con_i_valori_di_serie():
    p = C.prodotto(prodotto())
    assert p == dict(id="album-30", nome="Album 30 × 22,5", pagina_cm=[30, 22.5], abbondanza_mm=0, sicurezza_mm=0, piega_mm=0, ppi=200, ppi_minimi=150, ppi_consigliati=200,
                     profilo_colore="sRGB", consegna=dict(formato="jpg", qualita=95, file="spread", cifre=2, nome="{album} - Spread {n}"))
    pieno = prodotto(descrizione="Copertina in lino", spread_min=10, spread_max=40, sicurezza_mm=5, piega_mm=8, ppi=300, ppi_minimi=180, ppi_consigliati=250,
                     profilo_colore="sRGB", copertina="Rigida, 31 × 23 cm, dorso secondo le pagine", consegna={"nome": "{prodotto}_{pagina}", "file": "pagine", "cifre": 3, "qualita": 100, "formato": "jpg"})
    p = C.prodotto(pieno)
    assert (p["descrizione"], p["spread_min"], p["spread_max"], p["ppi_minimi"], p["ppi_consigliati"], p["copertina"]) == ("Copertina in lino", 10, 40, 180, 250, pieno["copertina"])
    assert p["consegna"] == dict(formato="jpg", qualita=100, file="pagine", cifre=3, nome="{prodotto}_{pagina}")
    assert C.prodotto(prodotto(ppi=150))["ppi_consigliati"] == 150, "i ppi consigliati di serie non superano quelli del documento"


@pytest.mark.parametrize("campi,atteso", [
    (dict(id="Album 30"), "id: deve essere un identificativo"),
    (dict(nome=""), "nome: non può essere vuoto"),
    (dict(nome="a‮b"), "carattere non ammesso"),
    (dict(pagina_cm=[30]), "pagina_cm: deve avere 2 valori"),
    (dict(pagina_cm=[200, 30]), "larghezza: deve essere un numero da 5 a 150"),
    (dict(pagina_cm=[30, "30"]), "altezza: deve essere un numero"),
    (dict(spread_min=20, spread_max=10), "spread_max: non può essere minore di spread_min"),
    (dict(spread_max=0), "spread_max: deve essere un numero da 1 a 500"),
    (dict(abbondanza_mm=25), "abbondanza_mm"),
    (dict(sicurezza_mm=40, pagina_cm=[8, 8]), "la zona di sicurezza copre tutta la pagina"),
    (dict(ppi=1000), "ppi: deve essere un numero da 150 a 600"),
    (dict(ppi=300.5), "ppi: deve essere un numero intero"),
    (dict(ppi_minimi=400), "ppi_minimi: deve essere un numero da 72 a 200"),
    (dict(ppi_minimi=180, ppi_consigliati=170), "ppi_consigliati: deve essere un numero da 180"),
    (dict(profilo_colore="FOGRA39"), "profilo_colore: deve essere uno tra «sRGB»"),
    (dict(copertina=7), "copertina: deve essere un testo"),
    (dict(script="alert(1)"), "chiave sconosciuta «script»"),
    (dict(consegna={"nome": "{n}", "percorso": "/tmp"}), "chiave sconosciuta «percorso»"),
    (dict(consegna={"nome": "{n}", "formato": "tif"}), "formato: deve essere uno tra «jpg»"),
    (dict(consegna={"nome": "{n}", "qualita": 50}), "qualita: deve essere un numero da 80 a 100"),
    (dict(consegna={"nome": "{n}", "file": "libro"}), "file: deve essere uno tra «spread», «pagine»"),
    (dict(consegna={"nome": "{n}", "cifre": 9}), "cifre: deve essere un numero da 1 a 4"),
    (dict(consegna={"nome": "{n}{__class__}"}), "segnaposto sconosciuto «{__class__}»"),
    (dict(consegna={"nome": "{0}{n}"}), "segnaposto sconosciuto «{0}»"),
    (dict(consegna={"nome": "{n}{n}{n}{n}{n}"}), "troppi segnaposti (al massimo 4)"),
    (dict(consegna={"nome": "{n} {album"}), "graffe non chiuse"),
    (dict(consegna={"nome": "{n} }"}), "graffe non chiuse"),
    (dict(consegna={"nome": "../{n}"}), "carattere che non può stare nel nome di un file"),
    (dict(consegna={"nome": "C:{n}"}), "carattere che non può stare nel nome di un file"),
    (dict(consegna={"nome": "{album}"}), "deve contenere {n}"),
    (dict(consegna={"nome": "{album} {n}", "file": "pagine"}), "deve contenere {pagina}"),
    (dict(consegna={"nome": "x" * 81}), "troppo lungo (al massimo 80"),
])
def test_prodotto_non_valido(campi, atteso):
    assert atteso in errore(C.prodotto, prodotto(**campi))


def test_catalogo_valido_e_completo():
    c = C.valida(catalogo(stato="da_confermare", fonte="Listino PDF del 2026", note="Riga uno\nRiga due"))
    assert (c["id"], c["generico"], c["stato"], c["fonte"], c["note"], c["data"]) == ("lab-prova", False, "da_confermare", "Listino PDF del 2026", "Riga uno\nRiga due", "2026-11-01")
    assert c["prodotti"] == [C.prodotto(prodotto())]
    assert C.valida(catalogo())["stato"] == "confermato" and "fonte" not in C.valida(catalogo())


@pytest.mark.parametrize("doc,atteso", [
    ([], "deve contenere un oggetto"),
    (catalogo(formato_catalogo=2), "formato più recente di questa versione"),
    (catalogo(formato_catalogo=True), "formato_catalogo: deve essere 1"),
    (catalogo(formato_catalogo="1"), "formato_catalogo: deve essere 1"),
    ({k: v for k, v in catalogo().items() if k != "laboratorio"}, "manca «laboratorio»"),
    (catalogo(codice="import os"), "chiave sconosciuta «codice»"),
    (catalogo(id="../../etc"), "id: deve essere un identificativo"),
    (catalogo(data="1/11/2026"), "data: deve essere una data AAAA-MM-GG"),
    (catalogo(generico=True), "solo i cataloghi che vengono con il programma sono generici"),
    (catalogo(generico="sì"), "generico: deve essere vero o falso"),
    (catalogo(stato="bozza"), "stato: deve essere uno tra «confermato», «da_confermare»"),
    (catalogo(note="x" * 1001), "note: è troppo lungo"),
    (catalogo(prodotti=[]), "deve avere almeno un prodotto"),
    (catalogo(prodotti=[prodotto()] * 201), "troppi elementi (al massimo 200)"),
    (catalogo(prodotti=[prodotto(), prodotto(nome="Altro")]), "lo stesso id per più prodotti: album-30"),
    (catalogo(prodotti=[prodotto(), prodotto(id="b", ppi=10)]), "catalogo, prodotto 2, ppi"),
])
def test_catalogo_non_valido(doc, atteso):
    assert atteso in errore(C.valida, doc)


def test_solo_il_catalogo_del_programma_e_generico():
    assert C.valida(catalogo(generico=True), interno=True)["generico"] is True


# ---------------------------------------------------------------- firma
def test_firma_verificata_con_le_chiavi_delle_licenze(chiavi_prova):
    doc = C.firma(catalogo(), chiavi_prova.seme, 1)
    assert doc["id_firma"] == 1 and len(doc["firma"]) == 128 and C.verifica(doc) == (True, "firmato dal produttore di Impaginatore")
    assert C.firma(dict(doc, firma="0" * 128), chiavi_prova.seme, 1) == doc, "una firma vecchia non entra nei byte firmati"
    assert C.verifica(catalogo()) == (False, "il catalogo non è firmato")
    cambiato = copy.deepcopy(doc); cambiato["prodotti"][0]["ppi"] = 300
    assert "la firma non corrisponde al contenuto" in errore(C.verifica, cambiato)
    assert "la firma non corrisponde" in errore(C.verifica, C.firma(catalogo(), bytes(32), 1)), "firmato da un altro"
    for rotto in (dict(doc, id_firma="1"), dict(doc, id_firma=True), dict(doc, firma="xyz"), {k: v for k, v in doc.items() if k != "firma"}, dict(doc, firma=doc["firma"].upper())):
        assert "firma incompleta" in errore(C.verifica, rotto)
    assert "non conosce (n. 7)" in C.verifica(C.firma(catalogo(), chiavi_prova.seme, 7))[1]
    assert C.verifica(doc, {1: K.Pubblica(K.SEGNAPOSTO)}) == (False, "questa copia di Impaginatore non ha la chiave per verificare le firme (versione di sviluppo)")
    ritirata = {1: K.Pubblica(chiavi_prova.pubblica.hex(), "2026-10-31")}
    assert "chiave di firma ritirata" in errore(C.verifica, doc, ritirata)
    assert C.verifica(C.firma(catalogo(data="2026-10-31"), chiavi_prova.seme, 1), ritirata)[0] is True, "firmato prima del ritiro: vale"
    assert C.canonico(doc) == K.canonico(doc)


# ---------------------------------------------------------------- cataloghi del programma e dell'utente
def test_il_catalogo_del_programma_e_generico_e_valido():
    cat, problemi = L.cataloghi()
    assert problemi == [] and [c["id"] for c in cat] == ["generico"]
    g = cat[0]
    assert g["generico"] and g["interno"] and g["verificato"] and g["stato"] == "confermato" and "non sono le specifiche di un laboratorio" in g["fonte"]
    assert {p["id"] for p in g["prodotti"]} == {"quadrato-30", "quadrato-25", "quadrato-20", "orizzontale-35x25", "orizzontale-30x22", "orizzontale-25x20", "verticale-20x30"}
    assert all(p["abbondanza_mm"] == 3 and p["sicurezza_mm"] == 5 and p["ppi"] == 300 and "spread_max" not in p for p in g["prodotti"])
    assert not os.path.exists(L.cartella_utente()), "leggere i cataloghi non crea niente nei dati dell'utente"


def test_cataloghi_dell_utente(utente, chiavi_prova):
    assert L.cartella_utente().startswith(os.environ["IMPAGINATORE_DATI"])
    scrivi(utente / "b.json", catalogo())
    scrivi(utente / "a.json", C.firma(catalogo(id="lab-firmato", nome="Firmato"), chiavi_prova.seme, 1))
    scrivi(utente / "c.json", catalogo(nome="Doppione"))
    scrivi(utente / "d.json", catalogo(id="rotto", prodotti=[]))
    scrivi(utente / ".nascosto.json", catalogo(id="nascosto"))
    (utente / "leggimi.txt").write_text("non è un catalogo", encoding="utf-8")
    (utente / "e.json").write_text('{"id": 1, "id": 2}', encoding="utf-8")
    cat, problemi = L.cataloghi()
    assert [(c["id"], c["verificato"], c["interno"]) for c in cat] == [("generico", True, True), ("lab-firmato", True, False), ("lab-prova", False, False)]
    assert cat[2]["verifica"] == "il catalogo non è firmato"
    assert [(p["file"], p["errore"].split(":")[0]) for p in problemi] == [("c.json", "c'è già un catalogo con l'id «lab-prova»"), ("d.json", "d.json, prodotti"), ("e.json", "e.json non è valido")]
    e = L.elenco()
    assert [c["id"] for c in e["cataloghi"]] == ["generico", "lab-firmato", "lab-prova"] and len(e["problemi"]) == 3
    assert e["cataloghi"][0]["fonte"] and e["cataloghi"][0]["consentito"] is True and "fonte" not in e["cataloghi"][2]
    assert json.dumps(e).count(str(utente)) == 0, "nessun percorso nell'elenco"


def test_licenza_dei_cataloghi(utente, monkeypatch):
    scrivi(utente / "lab.json", catalogo())
    vero = licenze.stato
    monkeypatch.setattr(licenze, "stato", lambda *a, **k: (lambda s: dict(s, funzioni=dict(s["funzioni"], preset_laboratori=False)))(vero(*a, **k)))
    e = L.elenco()
    assert [c["consentito"] for c in e["cataloghi"]] == [True, False], "il Generico è di tutti"
    with pytest.raises(licenze.NonConsentita, match="L'uso dei cataloghi dei laboratori non fa parte della licenza Studio"): L.scelta("lab-prova/album-30")
    assert L.scelta("generico/quadrato-30")[1]["id"] == "quadrato-30"


def test_trova_e_scelta(utente):
    scrivi(utente / "lab.json", catalogo())
    c, p = L.trova("lab-prova", "album-30"); assert c["id"] == "lab-prova" and p["ppi"] == 200
    assert L.scelta({"catalogo": "lab-prova", "prodotto": "album-30"})[1] == p and L.scelta("lab-prova/album-30")[1] == p
    with pytest.raises(ValueError, match="non ha il prodotto «nessuno»"): L.trova("lab-prova", "nessuno")
    with pytest.raises(ValueError, match="Catalogo «altro» non trovato: importalo"): L.trova("altro", "x")
    for cattivo in (None, "lab-prova", "a/b/c", "../x/y", {"catalogo": "lab-prova"}, {"catalogo": "lab-prova", "prodotto": "Album 30"}, ["lab-prova", "album-30"]):
        with pytest.raises(ValueError, match="Prodotto non valido"): L.scelta(cattivo)


# ---------------------------------------------------------------- il prodotto in progetto.json
def test_prodotto_nel_progetto(utente):
    scrivi(utente / "lab.json", catalogo(stato="da_confermare"))
    c, p = L.trova("lab-prova", "album-30")
    pr = L.per_progetto(c, p)
    assert pr == dict(formato_catalogo=1, catalogo="lab-prova", nome_catalogo="Album di prova", laboratorio="Laboratorio di prova", data="2026-11-01", stato="da_confermare", prodotto=p)
    assert pr["prodotto"] is not p and pr["prodotto"]["consegna"] is not p["consegna"], "una copia: il catalogo può cambiare"
    assert L.dal_progetto(json.loads(json.dumps(pr))) == pr and L.dal_progetto(None) is None
    for rotto in ("x", dict(pr, formato_catalogo=2), dict(pr, prodotto=dict(p, ppi=5)), dict(pr, verificato=True), dict(pr, catalogo="A B")):
        assert L.dal_progetto(rotto) is None, rotto
    assert L.stato(pr) == dict(generico=False, verificato=False, installato=True, verifica="il catalogo non è firmato")
    assert L.stato(dict(pr, prodotto=dict(p, ppi=300)))["verifica"].startswith("il prodotto è diverso")
    assert L.stato(dict(pr, catalogo="altro")) == dict(generico=False, verificato=False, installato=False, verifica="il catalogo di questo prodotto non è installato su questo computer")
    g = L.per_progetto(*L.trova("generico", "quadrato-30"))
    assert L.stato(g)["generico"] is True and L.stato(g)["verificato"] is True
    assert L.stato(dict(g, prodotto=dict(g["prodotto"], ppi=600)))["generico"] is False, "un progetto non si dichiara generico da solo"


def test_geometria_e_formato_dell_album():
    p = C.prodotto(prodotto(pagina_cm=[30, 22.5], abbondanza_mm=3, ppi=250))
    assert L.geometria(p) == dict(formato_cm=[60, 22.5], abbondanza_mm=3, ppi=250)
    assert L.incompatibile(dict(formato_cm=[60, 22.5], abbondanza_mm=3), p) is None
    assert L.incompatibile(dict(formato_cm=[60.08, 22.46], abbondanza_mm=5), p) is None, "mezzo millimetro di tolleranza; più abbondanza va bene"
    m = L.incompatibile(dict(formato_cm=[50, 20]), p)
    assert m.startswith("L'album ha pagine di 25 × 20 cm, il prodotto «Album 30 × 22,5» di 30 × 22,5 cm") and "Crea un album nuovo" in m
    assert L.incompatibile(dict(formato_cm=[60, 22.5], abbondanza_mm=1.5), p).startswith("L'album ha 1,5 mm di abbondanza, il prodotto «Album 30 × 22,5» ne chiede 3")
    assert L.incompatibile(dict(formato_cm=[60, 22.5]), p).startswith("L'album ha 0 mm di abbondanza")


# ---------------------------------------------------------------- importare
def test_importa(utente, tmp_path, chiavi_prova):
    a = scrivi(tmp_path / "da email" / "Catalogo Lab.JSON", catalogo())
    r = L.importa(a)
    assert r == dict(id="lab-prova", nome="Album di prova", laboratorio="Laboratorio di prova", verificato=False, verifica="il catalogo non è firmato", stato="confermato", prodotti=1, sostituito=False)
    assert sorted(os.listdir(utente)) == ["lab-prova.json"] and open(utente / "lab-prova.json", encoding="utf-8").read() == open(a, encoding="utf-8").read(), "i byte controllati, così come sono"
    firmato = scrivi(tmp_path / "firmato.json", C.firma(catalogo(nome="Versione firmata"), chiavi_prova.seme, 1))
    assert L.importa(firmato) == dict(r, nome="Versione firmata", verificato=True, verifica="firmato dal produttore di Impaginatore", sostituito=True)
    with pytest.raises(ValueError, match="Il catalogo «Versione firmata» che hai è verificato, questo no"): L.importa(a)
    assert L.trova("lab-prova", "album-30")[0]["verificato"] is True, "resta quello verificato"
    # lo stesso catalogo salvato a mano con un altro nome: dopo l'importazione ce n'è uno solo
    scrivi(utente / "aaa.json", catalogo(id="lab-due")); (utente / "rotto.json").write_text("{", encoding="utf-8")
    L.importa(scrivi(tmp_path / "due.json", catalogo(id="lab-due", nome="Nuovo")))
    assert sorted(os.listdir(utente)) == ["lab-due.json", "lab-prova.json", "rotto.json"] and L.trova("lab-due", "album-30")[0]["nome"] == "Nuovo"


def test_importa_rifiuta(utente, tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="Non riesco a leggere il catalogo"): L.importa(str(tmp_path / "manca.json"))
    grande = tmp_path / "grande.json"; grande.write_bytes(b" " * (C.MAX_BYTE + 1))
    with pytest.raises(ValueError, match="troppo grande \\(al massimo 1 MB\\)"): L.importa(str(grande))
    with pytest.raises(C.CatalogoNonValido, match="prodotti: deve avere almeno un prodotto"): L.importa(scrivi(tmp_path / "vuoto.json", catalogo(prodotti=[])))
    with pytest.raises(ValueError, match="«generico» è l'id di un catalogo del programma"): L.importa(scrivi(tmp_path / "g.json", catalogo(id="generico")))
    cattivo = catalogo(); cattivo["id_firma"] = 1; cattivo["firma"] = "ab" * 64
    with pytest.raises(C.CatalogoNonValido, match="la firma non corrisponde"): L.importa(scrivi(tmp_path / "f.json", cattivo))
    vero = licenze.stato
    monkeypatch.setattr(licenze, "stato", lambda *a, **k: (lambda s: dict(s, funzioni=dict(s["funzioni"], preset_laboratori=False)))(vero(*a, **k)))
    with pytest.raises(licenze.NonConsentita): L.importa(scrivi(tmp_path / "ok.json", catalogo()))
    assert os.listdir(utente) == [], "niente resta a metà"


# ---------------------------------------------------------------- file della consegna
def test_nomi_dei_file():
    p = C.prodotto(prodotto())
    assert CO.nome_file(p, "Sposi Rossi", 3) == "Sposi Rossi - Spread 03.jpg"
    q = C.prodotto(prodotto(nome="Lino: 30/30", consegna={"nome": "ORD_{prodotto}_{album}_{pagina}", "file": "pagine", "cifre": 3}))
    assert CO.nome_file(q, "a/b\\c:*?", 2, 4) == "ORD_Lino- 30-30_a-b-c---_004.jpg"
    assert CO.nome_file(q, "", 1, 1) == "ORD_Lino- 30-30_Album_001.jpg"
    lungo = CO.nome_file(C.prodotto(prodotto(consegna={"nome": "x" * 55 + "{album}{album}{album}{n}"})), "è" * 100, 7)
    assert lungo.endswith("07.jpg") and len(lungo) < 255 and lungo.count("è") == 120
    assert CO.nome_file(C.prodotto(prodotto(consegna={"nome": "CON{n}", "cifre": 1})), "x", 1) == "CON1.jpg"
    assert CO.nome_file(C.prodotto(prodotto(consegna={"nome": "{n}"})), "x", 1) == "01.jpg"
    assert CO.nome_file(C.prodotto(prodotto(consegna={"nome": "{album}.{n}", "cifre": 1})), "CON", 1) == "_CON.1.jpg", "nomi riservati di Windows: mai"
    assert nomi.nome_cartella("x" * 100) == "x" * 80 and nomi.nome_cartella("x" * 100, lunghezza=90) == "x" * 90


def test_immagini_della_consegna():
    p = C.prodotto(prodotto(pagina_cm=[6, 5], abbondanza_mm=0, ppi=254))             # 254 ppi: 100 pixel per centimetro
    assert CO.misure_px(p) == (1200, 500)
    im = Image.new("RGB", (1200, 500), "white")
    [(pg, out)] = CO.immagini(im, 254, 0, p); assert pg is None and out is im, "già della misura giusta: com'è"
    [(_, out)] = CO.immagini(Image.new("RGB", (600, 250), "white"), 127, 0, p); assert out.size == (1200, 500), "portata alla risoluzione del prodotto"
    p = C.prodotto(prodotto(pagina_cm=[6, 5], abbondanza_mm=1, ppi=254, consegna={"nome": "{pagina}", "file": "pagine"}))
    assert CO.misure_px(p) == (620, 520)
    im = Image.new("RGB", (1220, 520), "white"); im.paste((255, 0, 0), (0, 0, 610, 520)); im.paste((0, 0, 255), (610, 0, 1220, 520))
    (a, sx), (b, dx) = CO.immagini(im, 254, 10, p)
    assert (a, b) == (0, 1) and sx.size == dx.size == (620, 520), "ogni pagina con l'abbondanza anche dal lato della piega"
    assert sx.getpixel((5, 260)) == (255, 0, 0) and sx.getpixel((614, 260)) == (0, 0, 255), "a sinistra, oltre la piega, l'abbondanza viene dalla pagina destra"
    assert dx.getpixel((5, 260)) == (255, 0, 0) and dx.getpixel((614, 260)) == (0, 0, 255)
    (_, sx), _ = CO.immagini(Image.new("RGB", (1260, 560), "white"), 254, 30, p)
    assert sx.size == (620, 520), "l'abbondanza in più si toglie"
    with pytest.raises(ValueError, match="meno abbondanza"): CO.immagini(im, 254, 5, p)


def test_cartella_nuova(tmp_path):
    a = CO.cartella_nuova(str(tmp_path / "Consegna"), "Album 30: lino")
    b = CO.cartella_nuova(str(tmp_path / "Consegna"), "Album 30: lino")
    assert os.path.isdir(a) and os.path.isdir(b) and os.path.basename(a).startswith("Album 30- lino 20") and (b == a + " (2)" or os.path.dirname(b) == os.path.dirname(a))


def test_riepilogo():
    p = C.prodotto(prodotto(spread_min=10, copertina="Rigida in lino"))
    pr = dict(formato_catalogo=1, catalogo="lab-prova", nome_catalogo="Album di prova", laboratorio="Lab", data="2026-11-01", stato="da_confermare", prodotto=p)
    t = CO.riepilogo("Sposi", pr, dict(verificato=False, verifica="il catalogo non è firmato"), ["a.jpg", "b.jpg"], 12, dict(blocca=1, guarda=2), True)
    for riga in ("Consegna dell'album «Sposi»", "Laboratorio: Lab", "Catalogo: Album di prova (lab-prova, 2026-11-01)", "Firma del catalogo: NON verificato (il catalogo non è firmato)",
                 "DA CONFERMARE", "Pagina: 30 × 22,5 cm (spread aperto 60 × 22,5 cm)", "Abbondanza: 0 mm per lato", "Risoluzione: 200 ppi · profilo colore sRGB incorporato",
                 "File: JPG qualità 95, uno per spread · 4724 × 1772 px", "Spread nell'album: 12 (il prodotto ne vuole almeno 10)", "1 problema che blocca, 2 da guardare",
                 "filigrana", "Copertina (da preparare a parte, Impaginatore non la esporta): Rigida in lino", "File (2):\n  a.jpg\n  b.jpg\n"):
        assert riga in t, riga
    q = dict(pr, stato="confermato", prodotto=C.prodotto(prodotto(spread_min=10, spread_max=30, consegna={"nome": "{pagina}", "file": "pagine"})))
    t = CO.riepilogo("Sposi", q, dict(verificato=True, verifica="firmato"), [], 12, {}, False)
    assert "Firma del catalogo: verificato" in t and "almeno 10 e al massimo 30" in t and "uno per pagina" in t and "0 problemi" in t
    assert "DA CONFERMARE" not in t and "filigrana" not in t and "Copertina" not in t
    t = CO.riepilogo("Sposi", dict(q, prodotto=C.prodotto(prodotto())), dict(verificato=True, verifica="firmato"), [], 3, {}, False)
    assert "Spread nell'album: 3\n" in t
