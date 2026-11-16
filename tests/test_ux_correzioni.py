"""Correzioni del passo 1 di PIANO-UX senza ridisegno: nome proposto dalla cartella «JPG» (A-01), messaggio di «Salva»
(A-26), menu di «Correggi spazi» che restava aperto (A-30), contatore delle modifiche in /api/ping (per UX-009)."""

import pytest
from cdp import CHROME

from impaginatore import nomi
from impaginatore.piattaforma import dialoghi



class Finti(dialoghi.Dialoghi):
    def __init__(self, risposte): self.risposte = list(risposte)

    def _scegli(self, tipo, messaggio): return [self.risposte.pop(0)] if self.risposte else []


@pytest.mark.parametrize("percorso, nome", [
    ("/Users/anna/Clienti/Sposi Rossi JPG", "Sposi Rossi"),
    ("C:\\Clienti\\Sposi Rossi JPG\\", "Sposi Rossi"),
    ("/Users/anna/Clienti/Rossi/JPG", "Rossi"),
    ("C:\\Clienti\\Rossi\\Export\\JPG", "Rossi"),
    ("/Volumes/Lavori/Bianchi_jpeg", "Bianchi"),
    ("/Volumes/Lavori/Verdi-JPG/Selezione", "Verdi"),
    ("/Users/anna/Matrimonio Jpegger", "Matrimonio Jpegger"),
    ("C:\\JPG", ""), ("/", ""), ("", ""), (None, ""),
    ("/Clienti/Cafe\u0301", "Café"),
])
def test_nome_da_cartella(percorso, nome):
    assert nomi.nome_da_cartella(percorso) == nome


def test_scegli_foto_propone_il_nome(home_srv, tmp_path):
    c = home_srv; d = tmp_path / "Rossi" / "JPG"; d.mkdir(parents=True)
    dialoghi.imposta(Finti([str(d)])); assert c.post("/api/scegli-foto") == {"path": str(d), "nome": "Rossi"}
    dialoghi.imposta(Finti([])); assert c.post("/api/scegli-foto") == {"path": "", "nome": ""}, "finestra chiusa senza scegliere"


def test_ping_dice_il_contatore_delle_modifiche(editor):
    c = editor; r0 = c.get("/api/ping")["rev"]; st = c.get("/api/state"); assert r0 == st["rev"]
    t = c.post("/api/templates", {"photos": [p["n"] for p in st["photos"][:2]]})["items"][0]
    c.post("/api/op", dict(op="newspread", pos=0, L=t["L"], R=t["R"]))
    assert c.get("/api/ping")["rev"] == r0 + 1, "una modifica fatta da un altro (MCP) si vede senza chiedere tutto lo stato"


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_nome_dalla_cartella_jpg_nella_pagina(home_srv, tmp_path):
    from cdp import Browser
    dialoghi.imposta(Finti(["C:\\Clienti\\Rossi\\JPG"]))
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1)
        b.js("document.getElementById('fpick').click()", attendi=False); b.pausa(1)
        assert b.js("document.getElementById('nome').value") == "Rossi" and b.js("document.getElementById('fdir').value") == "C:\\Clienti\\Rossi\\JPG"
        assert not b.problemi(), b.problemi()


@pytest.mark.browser
@pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")
def test_salva_e_menu_degli_spazi_nella_pagina(editor, tmp_path):
    from cdp import Browser
    c = editor
    with Browser(tmp_path) as b:
        b.apri(c.srv.indirizzo_avvio(), 2)
        b.js("(async () => { const t = await api('/api/templates', { photos: S.photos.slice(0, 2).map(p => p.n) }); await op({ op: 'newspread', pos: 0, L: t.items[0].L, R: t.items[0].R }); go(0); })()")
        b.pausa(1)
        b.js("document.getElementById('save').click()", attendi=False); b.pausa(1)
        testo = b.js("document.getElementById('toast').textContent")
        assert testo.startswith("Salvato alle ") and len(testo) == len("Salvato alle 10:30") and "spec.py" not in testo, testo
        assert b.js("S.salvato.slice(9, 11) + ':' + S.salvato.slice(11, 13)") == testo[-5:]
        # il menu si chiude quando si apre la finestra delle foto (A-30) ...
        b.js("gapMenu(document.getElementById('mgapfix'))"); assert b.js("!!document.getElementById('gapmenu')")
        b.js("fbOpen('import')"); assert b.js("!!document.getElementById('gapmenu')") is False
        b.js("document.getElementById('fbcancel').click(); document.getElementById('tabA').click()"); assert b.js("view") == "album"
        # ... e quando si passa alla vista delle foto; nella vista dell'album un render non lo chiude
        b.js("gapMenu(document.getElementById('mgapfix')); render()"); assert b.js("!!document.getElementById('gapmenu')")
        b.js("document.getElementById('tabF').click()"); assert b.js("!!document.getElementById('gapmenu')") is False
        b.js("gapClose()"); assert not b.problemi(), b.problemi()
