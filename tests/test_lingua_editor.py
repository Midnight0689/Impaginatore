"""La pagina dell'editor in inglese (T-206): testi inglesi nelle barre e nei menu, numeri col punto, nessuna chiave grezza
visibile, nessun errore in console; e in italiano i numeri restano con la virgola (i controlli sui testi fuori tabella
sono in test_lingua.py)."""
import re

import pytest
from cdp import CHROME, CONTROLLA, EDITOR



def album(c, n=3):
    """n spread con le prime foto, come li fa la pagina"""
    nomi = [p["n"] for p in c.get("/api/state")["photos"]]; k = 0
    for s, q in enumerate((3, 2, 3, 2)[:n]):
        t = c.post("/api/templates", {"photos": nomi[k:k + q]})["items"][0]; k += q
        c.post("/api/op", dict(op="newspread", pos=s, L=t["L"], R=t["R"]))


def senza_chiavi_grezze(b):
    """nessuna chiave della tabella («editor.xxx») resta nel testo che l'utente vede, né nei titoli"""
    visibile = b.js("document.body.innerText") + " " + " ".join(b.js("[...document.querySelectorAll('[title],[aria-label],[placeholder]')].map(e => [e.title, e.getAttribute('aria-label'), e.placeholder].join(' '))"))
    assert not re.search(r"\b(editor|comune)\.[a-z0-9_]+\.", visibile), re.findall(r"\b(?:editor|comune)\.[a-z0-9_.]+", visibile)


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_editor_in_inglese(editor, tmp_path, monkeypatch):
    from cdp import Browser
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")                       # la lingua si legge a ogni pagina servita
    c = editor; album(c)
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), EDITOR)
        assert b.js("document.documentElement.lang") == "en"
        assert b.js("document.getElementById('meta').textContent") == "60 × 22.5 cm · 3 spreads"
        assert b.js("document.getElementById('tabA').textContent.trim()") == "Design" and b.js("document.getElementById('tabF').textContent.trim()") == "Photos"
        assert "More layouts" in b.js("document.getElementById('insp').innerText")
        assert b.js("document.getElementById('undo').title").startswith("Undo “") and b.js("document.getElementById('redo').title") == "Nothing to redo"
        assert b.js("tasto('⇧ ⌫')") in ("⇧ ⌫", "Shift+Delete")
        # la barra della selezione, il menu del tasto destro, la scheda Tono
        b.js("(() => { const it = slotsOf(0).find(i => i.k !== 't'); sel = { s: 0, side: it.side, idx: it.idx }; msel = [it.side + ':' + it.idx]; render(); })()")
        assert b.js("[...document.querySelectorAll('#sbarR button span')].map(x => x.textContent)") == ["Replace", "Next layout", "Crop", "B/W"]
        assert re.search(r"\d+ ppi", b.js("document.querySelector('#insp .sub').innerText"))
        assert re.search(r"\d\.\d\d × \d+\.\d\d cm", b.js("document.querySelector('#insp .sub').innerText")), "misure col punto"
        b.js("(() => { const it = selItem(); frameMenu({ preventDefault() {}, stopPropagation() {}, clientX: 200, clientY: 200 }, it); })()")
        voci = b.js("[...document.querySelectorAll('#cmenu .mi span')].map(x => x.textContent)")
        assert "Replace…" in voci and "Black and white" in voci and "Arrange" in voci and "Retouch" in voci, voci
        b.js("chiudiCtx()")
        b.js("document.querySelector('#ptabs [data-t=tono]').click()")
        b.attendi("document.getElementById('tonopanel').innerText", lambda t: re.search(r"Evenness \d+ / 100|Tone is even|to (fix|review)", t))
        assert "Offset" in b.js("document.getElementById('tonopanel').innerText")
        # «Spacing»: la misura si scrive col punto (in inglese) e si accetta anche la virgola
        b.js("document.getElementById('mgapfix').click()")
        assert b.js("document.querySelector('#gapmenu b').textContent") == "Gaps equal to"
        assert re.fullmatch(r"\d+\.\d\d", b.js("document.getElementById('gmv').value")), b.js("document.getElementById('gmv').value")
        b.js("(() => { const v = document.getElementById('gmv'); document.querySelector('#gapmenu input[value=custom]').checked = true; v.value = '0,75'; document.getElementById('gmb1').click(); })()")
        b.attendi("GAPMODE === 'custom' && !document.getElementById('gapmenu') && OPIN === 0"); b.attendi_rete()     # spazi sistemati con la misura nuova
        assert (b.js("GAPCM"), b.js("GAPMODE"), b.js("!!document.getElementById('gapmenu')"), b.problemi()) == (0.75, "custom", False, [])
        # Controlla, scorciatoie, esportazione
        b.js("apriControlla(true)"); b.attendi(CONTROLLA)
        assert b.js("document.getElementById('insp').innerText").count("Check the album") >= 1
        b.js("apriControlla(false)"); b.js("keysOpen()")
        assert "Keyboard shortcuts" in b.js("document.getElementById('keys').innerText")
        assert re.search(r"Shift|⇧", b.js("document.getElementById('keys').innerText")) and "Enter" in b.js("document.getElementById('keys').innerText")
        b.js("document.querySelector('#keys .kx').click()")
        b.js("openExp()"); assert b.js("document.getElementById('ecount').textContent") == "3 spreads will be exported"
        assert not b.problemi(), b.problemi()
        # conflitto con un'altra scheda: la pagina lo riconosce dal codice, non dal testo (che segue la lingua)
        c.post("/api/op", dict(op="evg", value=1.0, cid="altra", rev=b.js("S.rev")))
        assert b.js("op({ op: 'evg', value: 2.0 }).then(r => r === null)") is True
        assert "changed in another window" in b.js("document.getElementById('toast').textContent")
        assert b.js("S.rev") == c.get("/api/state")["rev"], "la pagina ha riletto lo stato"
        senza_chiavi_grezze(b)


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_editor_in_italiano_numeri_con_la_virgola(editor, tmp_path, monkeypatch):
    from cdp import Browser
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")
    c = editor; album(c)
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), EDITOR)
        assert b.js("document.getElementById('meta').textContent") == "60 × 22,5 cm · 3 spread"
        assert b.js("[fN(22.5), fN(0.3, 2), cmF(1.234), cm2(2), fdv(1.25)]") == ["22,5", "0,30", "1,23", "2,00", "+1,3"]
        assert b.js("document.getElementById('undo').title").startswith("Annulla «") and b.js("document.getElementById('redo').title") == "Niente da ripetere"
        senza_chiavi_grezze(b)
        assert not b.problemi(), b.problemi()
