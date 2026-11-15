"""Le pagine si aprono davvero in un browser (Chrome/Chromium senza schermo) e mostrano i dati del server."""
import json
import os
import shutil
import subprocess

import pytest
from aiuti import attendi, crea_foto

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]


def dom(url, tmp_path):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", f"--user-data-dir={tmp_path / 'chrome'}",
                        "--virtual-time-budget=8000", "--dump-dom", url], capture_output=True, text=True, encoding="utf-8", timeout=120)
    return r.stdout


def test_home_nel_browser(home_srv, tmp_path):
    home_srv.post("/api/nuovo", {"nome": "Album Verdi", "w": 30, "h": 30})
    assert "Album Verdi" in dom(home_srv.srv.indirizzo_avvio(), tmp_path), "l'indirizzo di avvio collega il browser (cookie) e apre la pagina"
    assert "Album Verdi" not in dom(home_srv.url("/"), tmp_path / "altro"), "senza: la pagina che spiega come aprirla"


def test_editor_nel_browser(editor, tmp_path):
    st = editor.get("/api/state"); names = [p["n"] for p in st["photos"]]
    t = editor.post("/api/templates", {"photos": names[:2]})["items"][0]
    editor.post("/api/op", dict(cid="b", rev=st["rev"], op="newspread", pos=0, L=t["L"], R=t["R"]))
    html = dom(editor.srv.indirizzo_avvio(), tmp_path)
    assert "/img/spread/0" in html or "/img/thumb/" in html, html[:2000]
    assert os.path.exists(os.path.join(editor.progetto, "spec.py"))


# ---------------------------------------------------------------- con il protocollo di Chrome (cdp.py): JavaScript nella pagina, errori, CSP
CATTIVO = '<img src=x onerror="document.body.dataset.xss=1">'


def _senza_iniezioni(b):
    """nessun elemento nato da un dato (le immagini «x» ci sarebbero anche con la CSP, che blocca solo onerror), nessuno script eseguito"""
    assert b.js("document.querySelectorAll('img[src=\"x\"]').length") == 0
    assert b.js("document.body.dataset.xss || null") is None


def test_xss_da_nomi_ed_exif(home_srv, apri_editor, tmp_path):
    """SEC-006: nome del progetto, nome del file e data EXIF di una foto del cliente arrivano nella pagina come testo"""
    from cdp import Browser
    h = home_srv; p = h.post("/api/nuovo", {"nome": "Album " + CATTIVO, "w": 30, "h": 30})["path"]
    nome = 'x"><img src=x onerror="document.body.dataset.xss=2">'
    crea_foto(os.path.join(p, "Foto"), [("H01", 600, 400, "2026:01:01 10:00:00"), (nome, 500, 500, CATTIVO)])
    c = apri_editor(p)
    with Browser(tmp_path) as b:
        b.apri(h.srv.indirizzo_avvio(), 1.5)
        assert "Album " + CATTIVO in b.js("document.body.innerText"), "il nome si vede com'è"
        _senza_iniezioni(b)
        b.apri(c.srv.indirizzo_avvio(), 2)
        assert nome in b.js("S.photos.map(p => p.n)")
        b.js("(async () => { const t = await api('/api/templates', { photos: S.photos.map(p => p.n) }); await op({ op: 'newspread', pos: 0, L: t.items[0].L, R: t.items[0].R }); })()")
        b.js(f"(() => {{ const it = slotsOf(0).find(i => i.name === {json.dumps(nome)}); sel = {{ s: 0, side: it.side, idx: it.idx }}; msel = [it.side + ':' + it.idx]; render(); }})()")
        b.pausa(1.5)
        assert CATTIVO in b.js("document.getElementById('info').innerText"), "la data EXIF nel pannello, come testo"
        b.js("renderLib()"); b.pausa(0.5)
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
        b.apri(h.srv.indirizzo_avvio(), 1.5)
        assert b.js("LIST.length") == 1 and b.js("document.getElementById('vchk').style.display") == "none", "aggiornamenti spenti: niente «controlla»"
        b.apri(c.srv.indirizzo_avvio(), 2)
        assert b.js("S.photos.length") == 10 and b.js("lblFinder()") in ("Mostra nel Finder", "Mostra in Esplora risorse", "Mostra nel gestore file")
        b.js("(async () => { for (let k = 0; k < 2; k++) { const t = await api('/api/templates', { photos: S.photos.slice(2 * k, 2 * k + 2).map(p => p.n) }); await op({ op: 'newspread', pos: k, L: t.items[0].L, R: t.items[0].R }); } go(1); })()")
        b.pausa(1.5)
        b.js("(() => { const it = slotsOf(1).find(i => i.k !== 't'); sel = { s: 1, side: it.side, idx: it.idx }; msel = [it.side + ':' + it.idx]; render(); })()"); b.pausa(1)
        assert b.js("document.querySelectorAll('#slots .slot').length") >= 2
        assert b.js("[...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).map(i => i.src)") == []
        assert b.js("(async () => { fbOpen('files'); await new Promise(r => setTimeout(r, 600)); return FB.data.places.map(x => x.p); })()")[0] == p
        assert b.js("(async () => { const r = await api('/api/pick', { kind: 'folder' }); await fbLoad(r.paths[0]); await new Promise(r => setTimeout(r, 600)); return FB.data.files.map(f => f.n); })()") == ["N01.jpg"]
        b.pausa(1)
        assert b.js("[...document.querySelectorAll('#fbd img')].filter(i => i.complete && i.naturalWidth === 0).length") == 0, "miniature del selettore"
        assert b.js("(async () => await api('/api/import', { paths: [FB.path] }))()") == {"importate": 1, "saltate": 0, "riavvio": True}
        dest = os.path.join(p, "Esportazioni")
        assert b.js(f"(async () => await api('/api/export', {{ fmt: 'jpg', range: '', dest: {json.dumps(dest)}, res: 'bozza', q: 80 }}))()") == {"spread": 2}
        attendi(lambda: "[finito]" in c.get("/api/log"), 120)
        assert len([f for f in os.listdir(dest) if f.endswith(".jpg")]) == 2
        b.js("document.getElementById('home').click()", attendi=False); b.pausa(2)
        assert b.js("location.port") == str(h.porta) and b.js("LIST.length") == 1, "«Progetti» torna alla schermata"
        assert not b.problemi(), b.problemi()
        assert [r for r in b.risposte() if r[0] >= 400] == []
