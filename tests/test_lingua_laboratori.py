"""T-206: i testi dei cataloghi dei laboratori e del riepilogo della consegna (T-208) escono nella lingua in uso. L'italiano è
provato da test_laboratori.py; qui l'inglese."""
import json
import os

import pytest
from PIL import Image

from impaginatore import laboratori as L
from impaginatore import lingua
from impaginatore.laboratori import catalogo as CA
from impaginatore.laboratori import consegna as CO
from impaginatore.licenze import chiave as K


@pytest.fixture(autouse=True)
def inglese(monkeypatch):
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")


def prodotto(**campi):
    p = {"id": "album-30", "nome": "Album 30", "pagina_cm": [30, 22.5], "abbondanza_mm": 3, "ppi": 200, "consegna": {"nome": "{album} - Spread {n}"}}
    p.update(campi); return p


def catalogo(**campi):
    d = {"formato_catalogo": 1, "id": "lab-prova", "nome": "Album di prova", "laboratorio": "Lab", "data": "2026-11-01", "prodotti": [prodotto()]}
    d.update(campi); return d


def errore(doc, interno=False):
    with pytest.raises(CA.CatalogoNonValido) as e: CA.valida(doc, "catalogo", interno)
    return str(e.value)


def consegna(nome):
    return catalogo(prodotti=[prodotto(consegna={"nome": nome})])


def test_errori_del_catalogo():
    assert "must be an identifier of lowercase letters, digits and hyphens (at most 40)" in errore(catalogo(id="Lab X"))
    assert "unknown placeholder “{x}”: the valid ones are {album}, {n}, {pagina}, {prodotto}" in errore(consegna("{x} {n}"))
    assert "too many placeholders (at most 4)" in errore(consegna("{n}{n}{n}{n}{n}"))
    assert "unclosed braces: braces are only for placeholders" in errore(consegna("{n} {"))
    assert "contains a character that can't be in a file name (< > : \" / \\ | ? *)" in errore(consegna("{n}:"))
    assert "must contain {n}: every file needs a different name" in errore(consegna("x"))
    assert "can't be less than spread_min" in errore(catalogo(prodotti=[prodotto(spread_min=9, spread_max=3)]))
    assert "the safe zone covers the whole page" in errore(catalogo(prodotti=[prodotto(pagina_cm=[5, 10], sicurezza_mm=25)]))
    assert "must be 1" in errore(catalogo(formato_catalogo=0)) and "must be a date as YYYY-MM-DD" in errore(catalogo(data="ieri"))
    assert "is in a newer format than this version of Impaginatore" in errore(catalogo(formato_catalogo=2))
    assert "must contain an object" in errore([]) and "only the catalogues that come with the program are generic" in errore(catalogo(generico=True))
    assert "must have at least one product" in errore(catalogo(prodotti=[])) and "the same id for more than one product: album-30" in errore(catalogo(prodotti=[prodotto(), prodotto()]))
    assert "catalogo, product 2" in errore(catalogo(prodotti=[prodotto(), prodotto(id="X")]))


def test_firma_in_inglese(chiavi_prova):
    doc = catalogo()
    assert CA.verifica(doc) == (False, "the catalogue isn't signed")
    with pytest.raises(CA.CatalogoNonValido, match="incomplete signature"): CA.verifica(dict(doc, id_firma=1))
    assert CA.verifica(dict(doc, id_firma=9, firma="0" * 128)) == (False, "is signed with a key that this version of Impaginatore doesn't know (no. 9)")
    sviluppo = {1: K.Pubblica(K.SEGNAPOSTO)}
    assert CA.verifica(dict(doc, id_firma=1, firma="0" * 128), sviluppo)[1] == "this copy of Impaginatore doesn't have the key to verify signatures (development build)"
    firmato = CA.firma(doc, chiavi_prova.seme, 1)
    assert CA.verifica(firmato) == (True, "signed by the maker of Impaginatore")
    with pytest.raises(CA.CatalogoNonValido, match="the signature doesn't match the contents"): CA.verifica(dict(firmato, nome="Altro"))
    with pytest.raises(CA.CatalogoNonValido, match="signing key that has been withdrawn"): CA.verifica(firmato, {1: K.Pubblica(chiavi_prova.pubblica.hex(), "2026-01-01")})
    assert lingua.t("laboratori.verifica_interno") == "catalogue that comes with Impaginatore"


def test_ricerca_e_importazione_in_inglese(tmp_path, chiavi_prova):
    with pytest.raises(ValueError, match="Invalid product: the catalogue and the product are needed"): L.scelta("x")
    with pytest.raises(ValueError, match="Catalogue “nonc” not found: import it from the Albums screen"): L.trova("nonc", "x")
    with pytest.raises(ValueError, match="doesn't have the product “x”"): L.trova("generico", "x")
    f = tmp_path / "c.json"
    with pytest.raises(ValueError, match="I can't read the catalogue"): L.importa(str(tmp_path / "manca.json"))
    f.write_bytes(b"x" * (CA.MAX_BYTE + 1))
    with pytest.raises(ValueError, match="The catalogue is too large \\(at most 1 MB\\)"): L.importa(str(f))
    f.write_text(json.dumps(catalogo(id="generico")), encoding="utf-8")
    with pytest.raises(ValueError, match="“generico” is the id of a catalogue that comes with the program"): L.importa(str(f))
    f.write_text(json.dumps(CA.firma(catalogo(), chiavi_prova.seme, 1)), encoding="utf-8"); L.importa(str(f))
    f.write_text(json.dumps(catalogo()), encoding="utf-8")
    with pytest.raises(ValueError, match="you have is verified, this one isn't \\(the catalogue isn't signed\\): I won't replace it"): L.importa(str(f))
    d = L.cartella_utente()
    for nome in ("due.json", "tre.json"):
        with open(os.path.join(d, nome), "w", encoding="utf-8") as g: json.dump(catalogo(id="due"), g)
    assert any(p["errore"] == "there is already a catalogue with the id “due”" for p in L.cataloghi()[1])


def _generico():
    with open(os.path.join(L.INTERNI, "generico.json"), encoding="utf-8") as f: return json.load(f)


def test_catalogo_generico_in_inglese():
    """il Generico, che viene con il programma, si mostra nella lingua in uso; il file resta il dato (in italiano), e il
    progetto ne tiene la copia com'è: stato() la riconosce, e un progetto aperto in un'altra lingua resta «Generico»"""
    g = next(c for c in L.elenco()["cataloghi"] if c["id"] == "generico")
    assert (g["nome"], g["laboratorio"]) == ("Generic", "No lab: common sizes")
    assert g["fonte"].startswith("Common album sizes chosen by Impaginatore") and g["note"].startswith("Careful sizes and rules to start with")
    assert [p["nome"] for p in g["prodotti"]] == ["Square 30 × 30", "Square 25 × 25", "Square 20 × 20", "Landscape 35 × 25", "Landscape 30 × 22.5", "Landscape 25 × 20", "Portrait 20 × 30"]
    cat, prod = L.scelta("generico/orizzontale-30x22"); pr = L.per_progetto(cat, prod)
    assert (pr["nome_catalogo"], pr["laboratorio"], pr["prodotto"]["nome"]) == ("Generico", "Nessun laboratorio: formati comuni", "Orizzontale 30 × 22,5"), "nel progetto il dato com'è"
    assert L.stato(pr)["generico"] is True
    v = L.tradotto_progetto(pr)
    assert (v["nome_catalogo"], v["laboratorio"], v["prodotto"]["nome"]) == ("Generic", "No lab: common sizes", "Landscape 30 × 22.5") and pr["prodotto"]["nome"] == "Orizzontale 30 × 22,5"
    assert L.incompatibile(dict(formato_cm=[50, 20], abbondanza_mm=3), v["prodotto"]).startswith("The album has pages of 25 × 20 cm, the product “Landscape 30 × 22.5” of 30 × 22.5 cm")
    t = CO.riepilogo("W", v, L.stato(pr), [], 3, {}, False)
    assert "Lab: No lab: common sizes" in t and "Catalogue: Generic (generico, " in t and "Product: Landscape 30 × 22.5 (orizzontale-30x22)" in t
    cambiato = dict(pr, prodotto=dict(pr["prodotto"], ppi=200))
    assert L.tradotto_progetto(cambiato) == cambiato, "un «generico» diverso da quello del programma (un progetto ricevuto) si mostra com'è"
    altro = dict(pr, catalogo="lab-prova")
    assert L.tradotto_progetto(altro) == altro
    assert L.tradotto(dict(_generico(), interno=False))["nome"] == "Generico", "solo i cataloghi del programma"


def test_catalogo_generico_in_italiano_come_il_file(monkeypatch):
    """i testi in tabella del Generico in italiano sono quelli del file: per chi usa l'italiano non cambia niente"""
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")
    doc = _generico(); g = next(c for c in L.elenco()["cataloghi"] if c["id"] == "generico")
    assert {k: g[k] for k in ("nome", "laboratorio", "fonte", "note")} == {k: doc[k] for k in ("nome", "laboratorio", "fonte", "note")}
    assert [p["nome"] for p in g["prodotti"]] == [p["nome"] for p in doc["prodotti"]]
    assert [p["id"].replace("-", "_") for p in doc["prodotti"]] == [k.rsplit(".", 1)[1] for k in lingua.tabella("it") if k.startswith("laboratori.cat_generico.") and k.count(".") == 2 and "_" in k.rsplit(".", 1)[1]]


def test_compatibilita_e_riepilogo_in_inglese():
    p = CA.prodotto(prodotto())
    assert L.incompatibile(dict(formato_cm=[50, 20], abbondanza_mm=3), p).startswith("The album has pages of 25 × 20 cm, the product “Album 30” of 30 × 22.5 cm: the size of an existing album can't be changed.")
    assert L.incompatibile(dict(formato_cm=[60, 22.5], abbondanza_mm=1.5), p) == "The album has 1.5 mm of bleed, the product “Album 30” asks for 3: create a new album with this product from the Albums screen"
    pr = L.per_progetto(dict(id="lab-prova", nome="Album di prova", laboratorio="Lab", data="2026-11-01", stato="da_confermare"), dict(p, spread_min=10, spread_max=40, copertina="Rigida"))
    t = CO.riepilogo("Wedding", pr, dict(verificato=False, verifica="the catalogue isn't signed"), ["a.jpg"], 12, dict(blocca=1, guarda=2), True)
    for atteso in ("Delivery of the album “Wedding”", "Prepared on ", "Lab: Lab", "Catalogue signature: NOT verified (the catalogue isn't signed)", "WARNING: the specifications in this catalogue are TO BE CONFIRMED",
                   "Page: 30 × 22.5 cm (open spread 60 × 22.5 cm)", "Bleed: 3 mm per side, included in the files", "Resolution: 200 ppi · sRGB colour profile embedded", "Files: JPG quality 95, one per spread",
                   "Spreads in the album: 12 (the product wants at least 10 and at most 40)", "Album check: 1 problem that blocks, 2 to review", "Free trial: the files carry a watermark", "Cover (to be prepared separately", "Files (1):"):
        assert atteso in t, atteso
    q = dict(pr, stato="confermato", prodotto=CA.prodotto(prodotto(consegna={"nome": "{pagina}", "file": "pagine"}, spread_max=5)))
    t = CO.riepilogo("W", q, dict(verificato=True, verifica="ok"), [], 3, {}, False)
    assert "Catalogue signature: verified (ok)" in t and "one per page" in t and "(the product wants at most 5)" in t
    with pytest.raises(ValueError, match="the album has less bleed than the product asks for"): CO.immagini(Image.new("RGB", (100, 100)), 200, 0, p)
