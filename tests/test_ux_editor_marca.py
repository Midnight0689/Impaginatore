"""Editor ridisegnato con la marca (T-205, passi 3 e 4 di PIANO-UX): zone, barra dello spread e della selezione, provini
delle disposizioni, «Altra disposizione» (D), «Sostituisci», «Controlla» con «Sistema», bozza, menu per compiti, stati
vuoti, tastiera, licenza spiegata prima, esportazione in corso visibile (i testi dalla tabella: test_lingua.py)."""
import json
import os
import re

import pytest
from cdp import CHROME

from impaginatore import risorse

PAGINA = os.path.join(os.path.dirname(risorse.__file__), "index.html")


def html(): return open(PAGINA, encoding="utf-8").read()


def test_niente_finestre_del_browser_ne_codice_rischioso():
    """conferme e nomi in fogli dentro la pagina; niente eval/window.open (la finestra desktop li rifiuta); la memoria
    del browser sempre dentro try (WebView senza localStorage)"""
    s = html(); js = s[s.index('<script nonce="__NONCE__">'):]
    assert not re.search(r"\b(alert|confirm|prompt)\(", js)
    assert not re.search(r"\beval\(|window\.open\(|new Function\(", js)
    for riga in js.split("\n"):
        if "localStorage" in riga or "sessionStorage" in riga: assert "try" in riga, riga
    assert s.count("<script") == 1 and not re.search(r"\son[a-z]+=\"", s.split("<script")[0]), "nessun gestore in linea"


def stato(c): return c.get("/api/state")


def tasto(b, k):
    """un tasto vero (Input.dispatchKeyEvent): Tab sposta davvero il fuoco, le lettere arrivano come keydown"""
    nomi = {"Tab": ("Tab", 9), "Escape": ("Escape", 27)}
    key, vk = nomi[k] if k in nomi else (k, ord(k.upper()))
    b.chiama("Input.dispatchKeyEvent", type="keyDown", key=key, code=key if key in nomi else "Key" + k.upper(), windowsVirtualKeyCode=vk, text=k if len(k) == 1 else "")
    b.chiama("Input.dispatchKeyEvent", type="keyUp", key=key, code=key if key in nomi else "Key" + k.upper(), windowsVirtualKeyCode=vk); b.pausa(0.15)


def album(c, n=3):
    """n spread con le prime foto, come li fa la pagina"""
    st = stato(c); nomi = [p["n"] for p in st["photos"]]; k = 0
    for s, q in enumerate((3, 2, 3, 2)[:n]):
        t = c.post("/api/templates", {"photos": nomi[k:k + q]})["items"][0]; k += q
        c.post("/api/op", dict(op="newspread", pos=s, L=t["L"], R=t["R"]))


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_zone_barre_e_tema(editor, tmp_path):
    from cdp import Browser
    c = editor; album(c)
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        assert b.js("document.documentElement.dataset.theme") == "dark"
        assert b.js("['top','list','stage','side','pool'].every(i => document.getElementById(i).getBoundingClientRect().width > 0)")
        assert b.js("document.getElementById('meta').textContent") == "60 × 22,5 cm · 3 spread"
        assert b.js("[...document.querySelectorAll('#thumbs .sth span')].map(x => x.textContent)") == ["01–02", "03–04", "05–06"]
        assert b.js("document.querySelector('#sbarL .num b').textContent") == "01–02"
        assert b.js("document.getElementById('sbarR').children.length") == 0, "barra della selezione solo con una selezione"
        assert "Altre disposizioni" in b.js("document.getElementById('insp').innerText") and b.js("document.querySelectorAll('#provl .tp').length") > 1
        assert b.js("document.querySelectorAll('#provl .tp.cur').length") == 1, "la disposizione attuale è contornata"
        b.js("(() => { const it = slotsOf(0).find(i => i.k !== 't'); sel = { s: 0, side: it.side, idx: it.idx }; msel = [it.side + ':' + it.idx]; render(); })()")
        assert b.js("[...document.querySelectorAll('#sbarR button span')].map(x => x.textContent)") == ["Sostituisci", "Altra disposizione", "Ritaglia", "B/N"]
        assert re.search(r"\d+ ppi", b.js("document.querySelector('#insp .sub').innerText"))
        # tema: si cambia dal menu ⋯ e resta in questo browser
        b.js("document.getElementById('morb').click()"); assert b.js("document.getElementById('morm').hidden") is False
        b.js("document.getElementById('temab').click()")
        assert b.js("document.documentElement.dataset.theme") == "light" and b.js("localStorage.getItem('impaginatore_tema')") == "light"
        assert b.js("document.getElementById('morm').hidden") is True
        b.apri(c.srv.indirizzo_avvio(), 2); assert b.js("document.documentElement.dataset.theme") == "light"
        assert not b.problemi(), b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_tastiera_tab_libero_e_tasti_per_sistema(editor, tmp_path, monkeypatch):
    from cdp import Browser

    from impaginatore import piattaforma
    c = editor; album(c, 2)
    monkeypatch.setattr(piattaforma, "sistema", lambda: "linux")
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        b.js("document.getElementById('tabA').focus()")
        tasto(b, "Tab"); assert b.js("document.body.classList.contains('nolist')") is False, "Tab non nasconde più i pannelli (A-34)"
        assert b.js("document.activeElement.id") != "tabA", "Tab sposta il fuoco"
        b.js("document.activeElement.blur()"); tasto(b, "f")
        assert b.js("document.body.classList.contains('nolist') && document.body.classList.contains('noside')"), "F: tela piena"
        tasto(b, "f"); assert b.js("document.body.classList.contains('nolist')") is False
        b.js("(async () => { await op({ op: 'blank', pos: 2 }); })()")
        assert "Ctrl+Z" in b.js("document.getElementById('undo').title") and "⌘" not in b.js("document.getElementById('undo').title")
        assert b.js("tasto('⇧ ⌘ Z')") == "Maiusc+Ctrl+Z"
        b.js("keysOpen()"); assert "Ctrl+E" in b.js("document.getElementById('keys').innerText"); tasto(b, "Escape")
        assert b.js("document.getElementById('keys')") is None
        assert not b.problemi(), b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_altra_disposizione_sostituisci_e_annulla_con_il_nome(editor, tmp_path):
    from cdp import Browser
    c = editor; album(c, 2)
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        prima = json.dumps(stato(c)["spreads"][0]["items"])
        b.js("(async () => { await altraDisp(1); await altraDisp(1); })()")
        assert re.match(r"Disposizione 3 di \d+", b.js("document.querySelector('#pill span').textContent"))
        assert b.js("S.annulla.nome") == "Altra disposizione" and json.dumps(stato(c)["spreads"][0]["items"]) != prima
        b.js("(async () => { await dispEsc(); })()"); assert json.dumps(stato(c)["spreads"][0]["items"]) == prima, "Esc torna a com'era, in un passo"
        # Sostituisci: foto libera nella cornice, l'esito si legge nella pillola
        libera = next(p["n"] for p in stato(c)["photos"] if p["sp"] is None)
        b.js(f"(async () => {{ const it = slotsOf(0).find(i => i.k !== 't'); await sostituisci([0, it.side, it.idx], {libera!r}); }})()")
        assert libera in [i.get("name") for i in stato(c)["spreads"][0]["items"]]
        assert b.js("document.querySelector('#pill span').textContent").startswith(("Foto sostituita", "Disposizione adattata", "Pagina adattata"))
        b.js("(async () => { await annulla(); })()")
        assert b.js("document.getElementById('toast').textContent").startswith("Annullato: Sostituisci")
        assert b.js("CAMBIATE.length") >= 1 and b.js("document.querySelectorAll('#slots > .slot.cambiata').length") == b.js("CAMBIATE.length"), "le cornici cambiate si contornano (UX-003)"
        b.pausa(0.6); assert b.js("document.querySelectorAll('#slots > .slot.cambiata').length") == 0, "per 400 ms"
        assert libera not in [i.get("name") for i in stato(c)["spreads"][0]["items"]]
        # elimina spread: niente conferma, un avviso con «Annulla»
        b.js("(async () => { await eliminaSpread(1); })()"); assert len(stato(c)["spreads"]) == 1
        assert b.js("document.querySelector('#toast').textContent").startswith("Spread 03–04 eliminato")
        b.js("document.querySelector('#toast button').click()"); b.pausa(0.5); assert len(stato(c)["spreads"]) == 2
        assert not b.problemi(), b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_menu_per_compiti_sempre_uguale(editor, tmp_path):
    from cdp import Browser
    c = editor; album(c, 1)
    voci = "[...document.querySelectorAll('#cmenu > .mi')].map(x => x.textContent.replace(/[▸⌫SDBPF]$|\\s*$/g, ''))"
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        apri = "(() => { const it = slotsOf(0).find(i => i.k !== 't'); const r = document.querySelector('#slots .slot').getBoundingClientRect(); frameMenu({ preventDefault() {}, stopPropagation() {}, clientX: r.left + 5, clientY: r.top + 5 }, it); })()"
        b.js(apri); prima = b.js(voci)
        assert [v.split("…")[0] for v in prima[:5]] == ["Sostituisci", "Altra disposizione", "Sposta nella cornice", "Bianco e nero", "Primo piano"]
        assert "Disponi" in prima and "Ritocco" in prima and "Suggeriti" not in b.js("document.getElementById('cmenu').innerText")
        tasto(b, "Escape"); assert b.js("document.getElementById('cmenu')") is None
        for _ in range(3):                                          # usare un comando non lo sposta in cima
            b.js(apri); b.js("[...document.querySelectorAll('#cmenu > .mi')].find(x => /referit/.test(x.textContent)).click()")
        b.js(apri); assert b.js(voci)[:5] == prima[:5]
        b.js("document.querySelector('#cmenu .mi.sub').dispatchEvent(new MouseEvent('mouseenter'))")
        assert b.js("[...document.querySelectorAll('.csub .mi')].map(x => x.textContent)")[0].startswith("Porta avanti")
        assert not b.problemi(), b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_controlla_semaforo_e_sistema(editor, tmp_path):
    from cdp import Browser
    c = editor; album(c, 2); E = c.E
    from impaginatore.motore import album as A
    from impaginatore.motore import spazi
    R = E._rett_spread(0); x = R[spazi.coppie(R, A.G, A.PPI)[0]["b"]]
    c.post("/api/op", dict(op="setrects", s=0, rects=[[x["side"], x["idx"], x["x"] + 20, x["y"] + 20, x["w"] - 20, x["h"] - 20]]))
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2); b.pausa(1.6)
        assert b.js("['ok','att','no'].some(k => document.getElementById('ctlb').classList.contains(k))"), "il semaforo si accende da solo"
        tasto(b, "c"); b.pausa(0.6)
        assert b.js("document.body.classList.contains('ctlo')") and "Controlla l'album" in b.js("document.getElementById('insp').innerText")
        d = c.post("/api/controlla", {})
        assert b.js("document.querySelectorAll('#insp .pb').length") == min(len(d["problemi"]), 200 * 3)
        if d["sistema"]["spazi"] + d["sistema"]["tono"]:
            b.js("document.getElementById('ctlsis').click()"); b.pausa(0.8)
            assert stato(c)["annulla"]["nome"] == "Sistema album" and b.js("document.querySelector('#toast').textContent").startswith("Sistemato: ")
            assert c.post("/api/controlla", {})["sistema"]["spazi"] == 0
        b.js("document.querySelector('#insp .pb').click()"); assert b.js("CTL.aperto") is True, "clic su un problema: il pannello resta"
        tasto(b, "Escape"); tasto(b, "Escape"); assert b.js("CTL.aperto") is False
        assert E and not b.problemi(), b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_bozza_dal_foglio_e_stato_vuoto(editor, tmp_path):
    from cdp import Browser
    c = editor
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        assert b.js("view") == "album", "un album senza spread si apre su «Impagina», sullo stato vuoto (UX-008)"
        assert b.js("document.querySelectorAll('#nospread .azioni button.primary').length") == 1, "stato vuoto: una sola azione principale"
        assert b.js("document.querySelector('#nospread .azioni button.primary').textContent") == "Prepara la bozza…"
        b.js("document.querySelector('#nospread .azioni button.primary').click()"); b.pausa(1.5)
        assert b.js("document.querySelectorAll('#bzl figure').length") > 0 and "spread" in b.js("document.getElementById('bzok').textContent")
        b.js("document.querySelector('#bzr [data-r=piene]').click()"); b.pausa(1.2)
        n = b.js("document.querySelectorAll('#bzl figure').length")
        b.js("document.getElementById('bzok').click()"); b.pausa(1)
        st = stato(c); assert len(st["spreads"]) == n and st["annulla"]["nome"] == "Bozza dell'album" and b.js("document.getElementById('bozd')") is None
        assert b.js("view") == "album" and b.js("cur") == 0
        assert not b.problemi(), b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_licenza_detta_prima(editor, tmp_path, licenza):
    """con Essenziale la bozza non c'è: lo dice un foglio (senza chiedere al server); in prova il segno in alto dice i giorni"""
    from cdp import Browser
    c = editor; licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        assert b.js("S.licenza.funzioni.impaginazione_automatica_album") is False and b.js("document.getElementById('licb').hidden") is True
        b.js("apriBozza()"); b.pausa(0.3)
        assert b.js("document.querySelector('.sheet h3').textContent") == "Non compreso nella tua licenza" and b.js("document.getElementById('bozd')") is None
        tasto(b, "Escape")
        b.js("(async () => { try { await api('/api/bozza', {}); } catch (e) {} })()"); b.pausa(0.3)
        assert b.js("document.querySelector('.sheet h3').textContent") == "Non compreso nella tua licenza", "il 403 della licenza diventa un foglio, non un errore"
        tasto(b, "Escape")
        licenza.usa(None); b.apri(c.srv.indirizzo_avvio(), 2)
        assert re.fullmatch(r"Prova · \d+ giorni", b.js("document.getElementById('licb').textContent")) and b.js("document.getElementById('licb').hidden") is False
        assert [x for x in b.problemi() if "403" not in x or "/api/bozza" not in x] == [], b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_esportazione_in_corso_si_vede(editor, tmp_path):
    from cdp import Browser
    c = editor; album(c, 1)
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        b.js("openExp(); document.getElementById('ego').click()"); b.pausa(0.2)
        assert b.js("document.getElementById('expb').classList.contains('busy')") and b.js("document.getElementById('eavv').hidden") is False
        assert "non chiudere" in b.js("document.getElementById('expb').title")
        for _ in range(60):
            if not b.js("ESPORTO"): break
            b.pausa(0.5)
        assert b.js("ESPORTO") is False and b.js("document.querySelector('#expb .lbl').textContent") == "Esporta…"
        assert b.js("document.getElementById('eavv').hidden") is True
        assert not b.problemi(), b.problemi()


def test_passi_dell_assistente_detti_dal_server(editor):
    """le modifiche dell'assistente AI (cid «assistente-…», mcp/strumenti.py) sono passi d'annulla come gli altri, con
    assistente=True; /api/ping dice se l'ultima modifica è sua"""
    c = editor; album(c, 2); r = stato(c)["rev"]
    assert c.get("/api/ping")["assistente"] is False
    st = c.post("/api/op", {"op": "delete", "s": 1, "cid": "assistente-0a1b2c3d", "rev": r})
    assert st["annulla"]["nome"] == "Elimina spread" and st["annulla"]["assistente"] is True
    p = c.get("/api/ping"); assert p["assistente"] is True and p["rev"] == st["rev"] == r + 1
    u = c.post("/api/op", {"op": "undo", "cid": "pagina", "rev": st["rev"]})
    assert u["annullato"]["assistente"] is True and u["ripeti"]["assistente"] is True and "assistente" not in u["annulla"]
    assert c.get("/api/ping")["assistente"] is False, "l'annullamento l'ha fatto la pagina"


def aspetta(b, espressione, secondi=9):
    """la pagina controlla /api/ping ogni 4 secondi: aspetta che l'espressione sia vera"""
    for _ in range(int(secondi / 0.25)):
        if b.js(espressione): return True
        b.pausa(0.25)
    return False


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_modifica_dell_assistente_si_vede_e_si_annulla(editor, tmp_path):
    """l'assistente cambia l'album mentre la pagina è aperta: la pagina rilegge da sola, lo dice («Modificato
    dall'assistente: …» con «Annulla») e Annulla dice di chi era il passo; mentre si scrive in un campo aspetta; una
    modifica da un'altra scheda si dice a parte"""
    from cdp import Browser
    c = editor; album(c, 3)
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        c.post("/api/op", {"op": "delete", "s": 2, "cid": "assistente-0a1b2c3d", "rev": b.js("S.rev")})
        assert aspetta(b, "S.spreads.length === 2"), "la pagina si aggiorna da sola"
        assert b.js("document.getElementById('toast').firstChild.textContent") == "Modificato dall'assistente: Elimina spread"
        assert b.js("document.getElementById('undo').title").startswith("Annulla «Elimina spread (dell'assistente)»")
        b.js("document.querySelector('#toast button').click()"); b.pausa(0.6)
        assert len(stato(c)["spreads"]) == 3 and b.js("S.spreads.length") == 3
        assert b.js("document.getElementById('toast').textContent") == "Annullato: Elimina spread (dell'assistente)"
        # l'assistente annulla e ripete: l'avviso dice il nome del passo, con il pulsante giusto
        c.post("/api/op", {"op": "delete", "s": 2, "cid": "assistente-0a1b2c3d", "rev": stato(c)["rev"]})
        assert aspetta(b, "S.spreads.length === 2")
        c.post("/api/op", {"op": "undo", "cid": "assistente-0a1b2c3d", "rev": stato(c)["rev"]})
        assert aspetta(b, "S.spreads.length === 3")
        assert b.js("document.getElementById('toast').firstChild.textContent") == "L'assistente ha annullato: Elimina spread"
        assert b.js("document.querySelector('#toast button').textContent") == "Ripeti"
        c.post("/api/op", {"op": "redo", "cid": "assistente-0a1b2c3d", "rev": stato(c)["rev"]})
        assert aspetta(b, "S.spreads.length === 2")
        assert b.js("document.getElementById('toast').firstChild.textContent") == "L'assistente ha ripetuto: Elimina spread"
        b.js("document.querySelector('#toast button').click()"); b.pausa(0.6); assert len(stato(c)["spreads"]) == 3
        # mentre si scrive in un campo la pagina non ridisegna: lo fa appena il fuoco esce
        b.js("(() => { const i = document.createElement('input'); i.id = 'campoprova'; document.body.appendChild(i); i.focus(); })()")
        c.post("/api/op", {"op": "delete", "s": 2, "cid": "assistente-0a1b2c3d", "rev": stato(c)["rev"]})
        b.pausa(5); assert b.js("S.spreads.length") == 3
        b.js("document.getElementById('campoprova').blur()")
        assert aspetta(b, "S.spreads.length === 2")
        # un'altra scheda (non l'assistente): avviso diverso, senza «Annulla»
        c.post("/api/op", {"op": "delete", "s": 1, "cid": "altra-scheda", "rev": stato(c)["rev"]})
        assert aspetta(b, "S.spreads.length === 1")
        assert b.js("document.getElementById('toast').textContent") == "Album aggiornato: è stato modificato in un'altra finestra"
        assert b.js("document.querySelector('#toast button')") is None
        assert not b.problemi(), b.problemi()


TELA = "(() => { const r = document.getElementById('main').getBoundingClientRect(); return r.width * r.height / innerWidth / innerHeight * 100; })()"


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_tela_grande_e_foglio_sotto_i_1280(editor, tmp_path):
    """UX-016: lo spread 60 × 22,5 occupa almeno il 24 % della finestra a 1280 × 800 con tutti i pannelli aperti e almeno
    il 30 % a 1024 × 700; sotto i 1280 px il pannello di destra è un foglio che si apre sopra la tela senza rimpicciolirla,
    si chiude con Esc, e la colonna degli spread mostra solo i numeri"""
    from cdp import Browser
    c = editor; album(c, 2)
    with Browser(tmp_path) as b:
        b.chiama("Emulation.setDeviceMetricsOverride", width=1280, height=800, deviceScaleFactor=1, mobile=False)
        b.apri(c.srv.indirizzo_avvio(), 2)
        assert b.js("panels()") == [True, True, True] and b.js(TELA) >= 24, b.js(TELA)
        assert b.js("document.getElementById('sideb').getBoundingClientRect().width") == 0, "a 1280 px il pannello sta al suo posto"
        b.chiama("Emulation.setDeviceMetricsOverride", width=1024, height=700, deviceScaleFactor=1, mobile=False); b.pausa(0.3)
        assert b.js("panels()") == [True, False, True], "la finestra si stringe: il pannello aperto si chiude"
        b.chiama("Emulation.setDeviceMetricsOverride", width=1280, height=800, deviceScaleFactor=1, mobile=False); b.pausa(0.3)
        assert b.js("panels()") == [True, True, True] and b.js("localStorage.getItem('pan')") is None, "torna larga: si riapre, e non è una scelta da ricordare"
        b.chiama("Emulation.setDeviceMetricsOverride", width=1024, height=700, deviceScaleFactor=1, mobile=False)
        b.apri(c.srv.indirizzo_avvio(), 2)
        assert b.js("panels()") == [True, False, True], "finestra stretta: il foglio parte chiuso, la colonna degli spread resta"
        assert b.js("document.querySelector('#thumbs .sth img').getBoundingClientRect().width") == 0
        assert b.js("document.querySelector('#thumbs .sth span').textContent") == "01–02" and b.js("document.getElementById('list').getBoundingClientRect().width") <= 80
        tela = b.js(TELA); assert tela >= 30, tela
        b.js("document.getElementById('sideb').click()"); b.pausa(0.3)
        assert b.js("panels()[1]") is True and b.js(TELA) == tela, "il foglio si apre sopra la tela"
        assert b.js("document.getElementById('sideb').getAttribute('aria-pressed')") == "true"
        lati = b.js("(() => { const a = document.getElementById('side').getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(); return [a.right, s.right, a.width]; })()")
        assert lati == [1024, 1024, 272]
        tasto(b, "Escape"); assert b.js("panels()[1]") is False, "Esc chiude il foglio"
        tasto(b, "c"); b.pausa(0.3); assert b.js("panels()[1]") is True and b.js("CTL.aperto") is True, "Controlla apre il foglio"
        assert not b.problemi(), b.problemi()
