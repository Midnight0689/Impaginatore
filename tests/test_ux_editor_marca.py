"""Editor ridisegnato con la marca (T-205, passi 3 e 4 di PIANO-UX): zone, barra dello spread e della selezione, provini
delle disposizioni, «Altra disposizione» (D), «Sostituisci», «Controlla» con «Sistema», bozza, menu per compiti, stati
vuoti, tastiera, licenza spiegata prima, esportazione in corso visibile, testi tutti dalla tabella."""
import json
import os
import re
import shutil

import pytest

from impaginatore import risorse

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
PAGINA = os.path.join(os.path.dirname(risorse.__file__), "index.html")
TESTI = os.path.join(os.path.dirname(risorse.__file__), "testi", "it.json")


def html(): return open(PAGINA, encoding="utf-8").read()


def chiavi_usate(s):
    """le chiavi della tabella che la pagina usa: quelle scritte per intero e quelle composte (prefisso + elenco noto)"""
    lit = set(re.findall(r'"((?:editor|comune)\.[a-z0-9_.]+)"', s))
    lit = {k for k in lit if not k.endswith((".", "_")) and k not in ("editor.vuoto.foto", "editor.vuoto.spread")}
    din = {f"editor.ctl.{k}_{x}" for k in ("blocca", "guarda", "info") for x in ("h", "n")}
    din |= {f"editor.vuoto.{k}_{x}" for k in ("foto", "spread") for x in ("tit", "testo")}
    din |= {"editor.allinea." + x for x in ("sx", "ch", "dx", "su", "cv", "giu", "dh", "dv")}
    din |= {"editor.bozza.r_" + x for x in ("alterna", "piene", "bianche")}
    din |= {"editor.sfondo." + x for x in ("tema", "nero", "grigio_scuro", "grigio_chiaro", "bianco")}
    din |= {"editor.side.bordo_" + x for x in ("bianco", "crema", "grigio", "nero")}
    din |= {"editor.side.exif_" + x for x in ("profilo", "tempo", "diaframma", "iso", "focale", "data")}
    m = re.search(r"const KEYS = \[(.*?)\n\];", s, re.S).group(1)
    din |= {"editor.tasti.g_" + g for g in re.findall(r'\["([a-z_]+)", \[\[', m)} | {"editor.tasti." + a for a in re.findall(r'\["([a-z_]+)", "', m)}
    return lit | din


def test_testi_tutti_nella_tabella():
    """ogni testo che la pagina chiede c'è in it.json, e in it.json non restano voci dell'editor che nessuno usa"""
    s, t = html(), json.load(open(TESTI, encoding="utf-8"))
    usate = chiavi_usate(s)
    assert sorted(k for k in usate if k not in t) == []
    assert sorted(k for k in t if k.startswith("editor.") and k not in usate) == []
    for k in usate:
        segnaposto = set(re.findall(r"\{(\w+)\}", t[k])); assert all(re.fullmatch(r"[a-z_]+", x) for x in segnaposto), k


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
            assert stato(c)["annulla"]["nome"] == "Sistema album" and b.js("document.querySelector('#toast').textContent").startswith("Sistemati")
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
        b.js("view = 'album'; render()")
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
