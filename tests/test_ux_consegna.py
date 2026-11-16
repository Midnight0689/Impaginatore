"""I controlli dei cataloghi dei laboratori (T-208) nelle due pagine, provati in un Chrome vero: «Nuovo album» da un
prodotto del catalogo Generico (schermata Album), poi nell'editor la scelta del prodotto e la Consegna fino ai file."""
import os
import shutil

import pytest

from impaginatore import formato
from impaginatore import laboratori as L

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]

PRODOTTO = "generico/orizzontale-30x22"
SCEGLI = "(() => {{ const s = document.getElementById('{id}'); s.value = '{v}'; s.dispatchEvent(new Event('change')); }})()"


def album(c, n=2):
    """n spread con le prime foto, come li fa la pagina"""
    nomi = [p["n"] for p in c.get("/api/state")["photos"]]; k = 0
    for s, q in enumerate((3, 2, 3)[:n]):
        t = c.post("/api/templates", {"photos": nomi[k:k + q]})["items"][0]; k += q
        c.post("/api/op", dict(op="newspread", pos=s, L=t["L"], R=t["R"]))


def attendi(b, condizione, secondi=90):
    for _ in range(int(secondi * 2)):
        if b.js(condizione): return True
        b.pausa(0.5)
    return False


def test_nuovo_album_da_un_prodotto_e_consegna(home_srv, apri_editor, foto_campione, tmp_path):
    from cdp import Browser
    with Browser(tmp_path / "album") as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        b.js("window.aperti = []; openProject = p => window.aperti.push(p.path)")
        b.js("openNew()"); b.pausa(0.8)
        assert b.js("document.getElementById('prod').value") == "" and b.js("document.getElementById('w').disabled") is False, "di serie: formato libero"
        assert b.js("[...document.querySelectorAll('#prod optgroup')].map(g => g.label)") == ["Generico · Nessun laboratorio: formati comuni"]
        b.js(SCEGLI.format(id="prod", v=PRODOTTO))
        assert b.js("['w', 'h', 'abb'].map(k => document.getElementById(k).disabled)") == [True, True, True], "il prodotto dà il formato"
        assert b.js("[document.getElementById('w').value, document.getElementById('h').value, document.getElementById('abb').value]") == ["60", "22,5", "3"]
        assert b.js("document.getElementById('prodi').textContent") == "Nessun laboratorio: formati comuni · pagina 30 × 22,5 cm · abbondanza 3 mm · 300 ppi"
        b.js("document.getElementById('nome').value = 'Sposi'; document.getElementById('create').click()"); b.pausa(1.5)
        aperti = b.js("window.aperti"); assert len(aperti) == 1, "creato e aperto"
        cfg = formato.leggi_json(os.path.join(aperti[0], "progetto.json"))
        assert cfg["prodotto"] == L.per_progetto(*L.trova("generico", "orizzontale-30x22")) and (cfg["formato_cm"], cfg["abbondanza_mm"]) == ([60, 22.5], 3)
        assert not b.problemi(), b.problemi()
    p = aperti[0]
    for f in sorted(os.listdir(foto_campione)): shutil.copy2(os.path.join(foto_campione, f), os.path.join(p, "Foto", f))
    c = apri_editor(p); album(c)
    with Browser(tmp_path / "editor") as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        b.js("openExp()"); b.js("document.querySelector('#efmt [data-f=consegna]').click()"); b.pausa(0.8)
        assert b.js("getComputedStyle(document.getElementById('eo-consegna')).display") != "none" and b.js("document.getElementById('ego').textContent") == "Prepara la consegna"
        assert b.js("document.getElementById('eprod').value") == PRODOTTO, "il prodotto scelto alla creazione"
        assert b.js("document.getElementById('eprodi').textContent").startswith("Nessun laboratorio: formati comuni · pagina 30 × 22,5 cm · abbondanza 3 mm · 300 ppi")
        b.js(SCEGLI.format(id="eprod", v="")); b.pausa(0.8)
        assert c.get("/api/state")["prodotto"] is None and b.js("document.getElementById('eprodi').textContent").startswith("Scegli il prodotto del laboratorio")
        b.js(SCEGLI.format(id="eprod", v=PRODOTTO)); b.pausa(0.8)
        st = c.get("/api/state"); assert st["prodotto"]["prodotto"]["id"] == "orizzontale-30x22" and st["annulla"]["nome"] == "Prodotto del laboratorio"
        b.js("document.getElementById('ego').click()")
        cartella = os.path.join(p, "Esportazioni", "Consegna")
        assert attendi(b, "ESPORTO === false && document.getElementById('toast').textContent !== ''"), "la consegna finisce"
        fatte = os.listdir(cartella); assert len(fatte) == 1, "una cartella nuova per ogni consegna"
        assert sorted(os.listdir(os.path.join(cartella, fatte[0]))) == ["Riepilogo consegna.txt", "Sposi - Spread 01.jpg", "Sposi - Spread 02.jpg"]
        assert b.js("document.getElementById('toast').firstChild.textContent") == "Esportazione finita", b.js("document.getElementById('toast').textContent")
        assert not b.problemi(), b.problemi()
