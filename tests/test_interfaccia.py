"""Le pagine si aprono davvero in un browser (Chrome/Chromium senza schermo) e mostrano i dati del server."""
import json
import os

import pytest
from cdp import CHROME, EDITOR, HOME
from aiuti import attendi, crea_foto

pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]


def dom(url, tmp_path, atteso):
    """l'HTML della pagina quando contiene «atteso» (un'espressione JavaScript). Con il protocollo di Chrome e non con
    --dump-dom: con il tempo virtuale di --virtual-time-budget alcuni Chrome (i recenti con il meta refresh, quello delle
    macchine macOS Intel con ogni pagina) non escono più"""
    from cdp import Browser
    with Browser(tmp_path / "chrome") as b:
        b.apri(url)
        b.attendi(atteso)
        return b.js("document.documentElement.outerHTML")


def test_home_nel_browser(home_srv, tmp_path):
    """l'indirizzo di avvio collega il browser (cookie) e apre la schermata; l'indirizzo nudo dà la pagina che spiega come
    aprirla (401), che si ricarica da sola ogni 5 secondi (meta refresh)"""
    from cdp import Browser
    from impaginatore import lingua
    home_srv.post("/api/nuovo", {"nome": "Album Verdi", "w": 30, "h": 30})
    assert "Album Verdi" in dom(home_srv.srv.indirizzo_avvio(), tmp_path, "document.body.innerText.includes('Album Verdi')"), "l'indirizzo di avvio collega il browser (cookie) e apre la pagina"
    with Browser(tmp_path / "altro") as b:
        b.apri(home_srv.url("/"))
        testo = b.js("document.body.innerText")
        assert lingua.t("comune.non_collegata_1") in testo and "Album Verdi" not in testo, "senza: la pagina che spiega come aprirla"
        assert b.js("document.querySelector('meta[http-equiv=refresh]').content") == "5" and (401, home_srv.url("/")) in b.risposte()


def test_editor_nel_browser(editor, tmp_path):
    st = editor.get("/api/state"); names = [p["n"] for p in st["photos"]]
    t = editor.post("/api/templates", {"photos": names[:2]})["items"][0]
    editor.post("/api/op", dict(cid="b", rev=st["rev"], op="newspread", pos=0, L=t["L"], R=t["R"]))
    html = dom(editor.srv.indirizzo_avvio(), tmp_path, "!!document.querySelector('img[src*=\"/img/spread/0\"], img[src*=\"/img/thumb/\"]')")
    assert "/img/spread/0" in html or "/img/thumb/" in html, html[:2000]
    assert os.path.exists(os.path.join(editor.progetto, "album.json"))


# ---------------------------------------------------------------- con il protocollo di Chrome (cdp.py): JavaScript nella pagina, errori, CSP
CATTIVO = '<img src=x onerror="document.body.dataset.xss=1">'


def _senza_iniezioni(b):
    """nessun elemento nato da un dato (le immagini «x» ci sarebbero anche con la CSP, che blocca solo onerror), nessuno script eseguito"""
    assert b.js("document.querySelectorAll('img[src=\"x\"]').length") == 0
    assert b.js("document.body.dataset.xss || null") is None


def test_ogni_blocco_della_csp_fa_fallire_il_test(home_srv, tmp_path):
    """controllo generale dei test nel browser (cdp.Browser): una risorsa bloccata dalla CSP fa fallire il test all'uscita,
    anche se il test non guarda problemi()"""
    from cdp import Browser
    with pytest.raises(AssertionError, match="Content-Security-Policy.*img-src"):
        with Browser(tmp_path / "a") as b:
            b.apri(home_srv.srv.indirizzo_avvio(), HOME)
            b.js("document.body.insertAdjacentHTML('beforeend', '<i style=\"display:block;width:9px;height:9px;background:url(data:image/gif;base64,R0lGODlhAQABAAAAACw=)\"></i>')")
            b.attendi_che(b.violazioni_csp)                             # il blocco arriva quando il browser prova a caricare lo sfondo
    with Browser(tmp_path / "b") as b:                                  # senza blocchi: nessun errore all'uscita
        b.apri(home_srv.srv.indirizzo_avvio(), HOME)
        assert b.violazioni_csp() == []


def test_xss_da_nomi_ed_exif(home_srv, apri_editor, tmp_path):
    """SEC-006: nome del progetto, nome del file e data EXIF di una foto del cliente arrivano nella pagina come testo"""
    from cdp import Browser
    h = home_srv; p = h.post("/api/nuovo", {"nome": "Album " + CATTIVO, "w": 30, "h": 30})["path"]
    # Windows non ammette «"», «<» e «>» nel nome di un file: lì il nome prova l'uscita da un attributo tra apici singoli e
    # un'entità che non deve diventare un elemento (data EXIF e nome dell'album restano quelli con «<img …>»)
    nome = ("x' autofocus onfocus='document.body.dataset.xss=2' &lt;img src=x onerror=document.body.dataset.xss=2&gt;" if os.name == "nt"
            else 'x"><img src=x onerror="document.body.dataset.xss=2">')
    crea_foto(os.path.join(p, "Foto"), [("H01", 600, 400, "2026:01:01 10:00:00"), (nome, 500, 500, CATTIVO)])
    c = apri_editor(p)
    with Browser(tmp_path) as b:
        b.apri(h.srv.indirizzo_avvio(), HOME)
        assert "Album " + CATTIVO in b.js("document.body.innerText"), "il nome si vede com'è"
        _senza_iniezioni(b)
        b.apri(c.srv.indirizzo_avvio(), EDITOR)
        assert nome in b.js("S.photos.map(p => p.n)")
        b.js("(async () => { const t = await api('/api/templates', { photos: S.photos.map(p => p.n) }); await op({ op: 'newspread', pos: 0, L: t.items[0].L, R: t.items[0].R }); go(0); })()")
        b.js(f"(() => {{ const it = slotsOf(0).find(i => i.name === {json.dumps(nome)}); sel = {{ s: 0, side: it.side, idx: it.idx }}; msel = [it.side + ':' + it.idx]; render(); }})()")
        b.attendi("document.getElementById('info').innerText", lambda t: CATTIVO in t)   # la data EXIF nel pannello, come testo
        b.js("renderLib()"); b.attendi_rete()                          # immagini caricate (o fallite): un onerror iniettato sarebbe già scattato
        _senza_iniezioni(b)
        # livello di testo con un carattere dal nome cattivo (nomi e stili vengono dai file dei font del sistema): barra e pannello del testo
        font = 'x"></select><img src=x onerror="document.body.dataset.xss=3">'
        b.js(f"(async () => {{ FONTS.push({{ fam: 'Cattiva', sty: {json.dumps(font)}, ps: {json.dumps(font)} }}); await op({{ op: 'addtext', s: 0, fx: 0.1, fy: 0.1, fw: 0.3, fh: 0.1 }}); "
             f"const it = slotsOf(0).find(i => i.k === 't' && i.kind === 'txt'); await op({{ op: 'settext', at: [0, it.side, it.idx], font: {json.dumps(font)} }}); "
             "sel = { s: 0, side: it.side, idx: it.idx }; msel = [it.side + ':' + it.idx]; render(); })()")
        b.attendi_rete()
        assert b.js("document.getElementById('tb-sty').options[0].value") == font and b.js("document.getElementById('tsty').options[0].text") == font
        _senza_iniezioni(b)
        assert not b.problemi(), b.problemi()


def test_interfaccia_completa_senza_errori(home_srv, apri_editor, tmp_path):
    """giro dell'interfaccia vera: schermata, editor, spread, pannelli, selettore di foto con «Altra cartella…», importazione,
    esportazione JPG, ritorno ai progetti. Nessun errore nella console, niente bloccato dalla CSP, nessuna risposta 4xx/5xx"""
    from cdp import Browser

    from impaginatore.piattaforma import dialoghi
    h = home_srv; p = h.post("/api/nuovo", {"nome": "Giro", "w": 30, "h": 30})["path"]
    crea_foto(os.path.join(p, "Foto"))
    nuove = tmp_path / "nuove"; crea_foto(str(nuove), [("N01", 400, 300, None)])
    c = apri_editor(p); c.E.HOME = f"http://127.0.0.1:{h.porta}"
    dialoghi.imposta(type("F", (dialoghi.Dialoghi,), {"_scegli": lambda self, t, m: [str(nuove)]})())
    with Browser(tmp_path) as b:
        b.apri(h.srv.indirizzo_avvio(), HOME)
        assert b.js("LIST.length") == 1 and b.js("document.getElementById('vchk').style.display") == "none", "aggiornamenti spenti: niente «controlla»"
        b.apri(c.srv.indirizzo_avvio(), EDITOR)
        assert b.js("S.photos.length") == 10 and b.js("lblFinder()") in ("Mostra nel Finder", "Mostra in Esplora risorse", "Mostra nel gestore file")
        b.js("(async () => { for (let k = 0; k < 2; k++) { const t = await api('/api/templates', { photos: S.photos.slice(2 * k, 2 * k + 2).map(p => p.n) }); await op({ op: 'newspread', pos: k, L: t.items[0].L, R: t.items[0].R }); } go(1); })()")
        b.attendi_rete()
        b.js("(() => { const it = slotsOf(1).find(i => i.k !== 't'); sel = { s: 1, side: it.side, idx: it.idx }; msel = [it.side + ':' + it.idx]; render(); })()"); b.attendi_rete()
        assert b.js("document.querySelectorAll('#slots .slot').length") >= 2
        assert b.js("[...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).map(i => i.src)") == []
        b.js("fbOpen('files')"); assert b.attendi("FB.data.places.map(x => x.p)")[0] == p
        assert b.js("(async () => { const r = await api('/api/pick', { kind: 'folder' }); await fbLoad(r.paths[0]); return FB.data.files.map(f => f.n); })()") == ["N01.jpg"]
        b.attendi_rete()
        assert b.js("[...document.querySelectorAll('#fbd img')].filter(i => i.complete && i.naturalWidth === 0).length") == 0, "miniature del selettore"
        assert b.js("(async () => await api('/api/import', { paths: [FB.path] }))()") == {"importate": 1, "saltate": 0, "riavvio": True}
        dest = os.path.join(p, "Esportazioni")
        assert b.js(f"(async () => await api('/api/export', {{ fmt: 'jpg', range: '', dest: {json.dumps(dest)}, res: 'bozza', q: 80 }}))()") == {"spread": 2}
        attendi(lambda: "[finito]" in c.get("/api/log"), 120)
        assert len([f for f in os.listdir(dest) if f.endswith(".jpg")]) == 2
        b.segna(); b.js("document.getElementById('home').click()", attendi=False); b.attendi_pagina(HOME)
        assert b.js("location.port") == str(h.porta) and b.js("LIST.length") == 1, "«Progetti» torna alla schermata"
        assert not b.problemi(), b.problemi()
        assert [r for r in b.risposte() if r[0] >= 400] == []


def test_nome_dalla_cartella_delle_foto_anche_su_windows(home_srv, tmp_path):
    """«Scegli…» delle foto di un progetto nuovo: il nome proposto è l'ultima cartella anche con le barre di Windows"""
    from cdp import Browser

    from impaginatore.piattaforma import dialoghi
    dialoghi.imposta(type("F", (dialoghi.Dialoghi,), {"_scegli": lambda self, t, m: ["C:\\Clienti\\Sposi Rossi JPG"]})())
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), HOME)
        b.js("document.getElementById('fpick').click()", attendi=False); b.attendi("document.getElementById('fdir').value")
        assert b.js("document.getElementById('nome').value") == "Sposi Rossi" and b.js("document.getElementById('fdir').value") == "C:\\Clienti\\Sposi Rossi JPG"
        assert not b.problemi(), b.problemi()
