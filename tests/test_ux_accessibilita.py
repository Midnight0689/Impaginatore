"""Controllo automatico minimo dell'accessibilità (UX-019, T-205/T-206), in un Chrome vero, sulle due pagine in stati
diversi: ruoli conosciuti, nome accessibile per ogni comando e per ogni finestra, bersagli di almeno 24 × 24 px
(WCAG 2.5.8), contrasto dei gettoni dei testi sui fondi dell'applicazione nei due temi (4,5:1) e del contorno del
fuoco (3:1). Non sostituisce uno strumento completo né una prova con un lettore di schermo (PIANO-UX: UX-019 resto, 2.1)."""
import shutil

import pytest

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]

CONTROLLO = r"""(() => {
  const P = [];
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && !e.closest("[hidden], [aria-hidden=true], [inert]"); };
  const testo = e => (e.textContent || "").replace(/\s+/g, " ").trim();
  const nome = e => {
    let n = (e.getAttribute("aria-label") || "").trim(); if (n) return n;
    const lb = e.getAttribute("aria-labelledby");
    if (lb) { n = lb.split(/\s+/).map(i => { const x = document.getElementById(i); return x ? testo(x) : ""; }).join(" ").trim(); if (n) return n; }
    if (e.labels && e.labels.length) { n = [...e.labels].map(testo).join(" ").trim(); if (n) return n; }
    if (!/^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName)) { n = testo(e); if (n) return n; }
    return (e.title || e.placeholder || e.getAttribute("alt") || "").trim();
  };
  const RUOLI = new Set("alert alertdialog application article banner button cell checkbox columnheader combobox complementary contentinfo dialog document feed figure form grid gridcell group heading img link list listbox listitem log main menu menubar menuitem menuitemcheckbox menuitemradio navigation none note option presentation progressbar radio radiogroup region row rowgroup rowheader scrollbar search searchbox separator slider spinbutton status switch tab table tablist tabpanel textbox timer toolbar tooltip tree treegrid treeitem".split(" "));
  document.querySelectorAll("[role]").forEach(e => e.getAttribute("role").split(/\s+/).forEach(r => { if (!RUOLI.has(r)) P.push("ruolo sconosciuto «" + r + "»: " + (e.id || e.className)); }));
  document.querySelectorAll("[role=dialog], [role=alertdialog]").forEach(e => { if (vis(e) && !nome(e)) P.push("finestra senza nome: " + (e.id || e.className)); });
  const COMANDI = "button, a[href], input:not([type=hidden]), select, textarea, [role=button], [role=menuitem], [role=switch], [role=tab], [role=option], [role=radio], [tabindex]:not([tabindex='-1'])";
  document.querySelectorAll(COMANDI).forEach(e => {
    if (!vis(e) || e.disabled) return;
    const id = e.id ? "#" + e.id : e.outerHTML.slice(0, 90);
    if (!nome(e)) P.push("senza nome accessibile: " + id);
    let r = e.getBoundingClientRect();
    if (/^(checkbox|radio)$/.test(e.type) && e.closest("label")) r = e.closest("label").getBoundingClientRect();        // si clicca tutta l'etichetta
    if (r.width < 23.5 || r.height < 23.5) P.push(`bersaglio ${Math.round(r.width)}×${Math.round(r.height)} px: ${id}`);
  });
  return P;
})()"""

CONTRASTO = r"""(() => {
  const s = getComputedStyle(document.documentElement), v = n => s.getPropertyValue(n).trim();
  const lum = h => { const m = h.replace("#", ""); return [0, 2, 4].map(i => parseInt(m.slice(i, i + 2), 16) / 255).map(x => x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4).reduce((a, x, i) => a + x * [0.2126, 0.7152, 0.0722][i], 0); };
  const rap = (a, b) => { const [x, y] = [lum(v(a)), lum(v(b))].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const out = [], fondi = ["--imp-app-tela", "--imp-app-pannello", "--imp-app-barra", "--imp-app-sollevato"];
  for (const t of ["--imp-app-testo", "--imp-app-testo-tenue"]) for (const f of fondi) { const r = rap(t, f); if (!(r >= 4.5)) out.push(`${t} su ${f}: ${r.toFixed(2)}`); }
  for (const f of fondi) { const r = rap("--imp-app-accento", f); if (!(r >= 3)) out.push(`--imp-app-accento su ${f}: ${r.toFixed(2)}`); }
  return out;
})()"""


def controlla(b):
    """problemi della pagina com'è adesso, e del contrasto nei due temi"""
    p = b.js(CONTROLLO)
    for tema in ("dark", "light"):
        b.js(f"document.documentElement.dataset.theme = '{tema}'"); p += [f"[{tema}] {x}" for x in b.js(CONTRASTO)]
    b.js("document.documentElement.dataset.theme = 'dark'")
    return p


def test_il_controllo_trova_i_problemi(home_srv, tmp_path):
    """il controllo stesso: un pulsante senza nome, uno piccolo, un ruolo inventato, una finestra senza nome"""
    from cdp import Browser
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        b.js("""document.body.insertAdjacentHTML('beforeend', '<div id="prova"><button id="b1" style="width:40px;height:40px"></button>'
               + '<button id="b2" style="width:16px;height:16px;padding:0">x</button><span role="bottone" id="r1">r</span>'
               + '<div role="dialog" id="d1" style="width:50px;height:50px"></div>'
               + '<label style="display:inline-block;height:30px;width:80px"><input type="checkbox" id="c1">ok</label></div>')""")
        p = b.js(CONTROLLO)
        assert any("senza nome accessibile: #b1" in x for x in p) and any(x.startswith("bersaglio 16×16 px: #b2") for x in p)
        assert any("«bottone»" in x for x in p) and any("finestra senza nome: d1" in x for x in p) and not any("#c1" in x for x in p)
        b.js("document.getElementById('prova').remove(); document.documentElement.style.setProperty('--imp-app-testo-tenue', '#777777')")
        assert any(x.startswith("--imp-app-testo-tenue su") for x in b.js(CONTRASTO))


@pytest.mark.parametrize("lingua", ["it", "en"])
def test_schermata_album_accessibile(home_srv, tmp_path, monkeypatch, lingua):
    from cdp import Browser
    monkeypatch.setenv("IMPAGINATORE_LINGUA", lingua)
    home_srv.post("/api/nuovo", {"nome": "Rossi", "w": 60, "h": 22.5})
    with Browser(tmp_path) as b:
        b.apri(home_srv.srv.indirizzo_avvio(), 1.5)
        assert controlla(b) == []
        for apri in ("document.getElementById('altro').click()", "openNew()", "apriAssistente()", "apriLingua()", "document.getElementById('lic').click()"):
            b.js("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))"); b.pausa(0.2)
            b.js(apri); b.pausa(0.4)
            assert controlla(b) == [], apri
        assert not b.problemi(), b.problemi()
