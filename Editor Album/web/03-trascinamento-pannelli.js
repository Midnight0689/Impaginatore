// ---- trascinare una foto libera: con il puntatore (più affidabile del drag-and-drop del browser)
function startPhotoDrag(e, n) {
  if (e.button !== 0) return; e.preventDefault(); const x0 = e.clientX, y0 = e.clientY; let g = null;
  const hit = ev => { const t = document.elementFromPoint(ev.clientX, ev.clientY); return t; };
  const mv = ev => {
    if (!g && Math.hypot(ev.clientX - x0, ev.clientY - y0) < 5) return;
    if (!g) { g = document.createElement("img"); g.src = `/img/thumb/${n}?w=240`; g.style.cssText = "position:fixed;z-index:50;width:130px;opacity:.85;pointer-events:none;border:2px solid var(--accent);border-radius:4px;box-shadow:0 6px 20px rgba(0,0,0,.5)"; document.body.appendChild(g); }
    g.style.left = ev.clientX - 65 + "px"; g.style.top = ev.clientY - 40 + "px";
    document.querySelectorAll("#slots > div.over").forEach(x => x.classList.remove("over")); const t = hit(ev), sl = t && t.closest("#slots > div"); if (sl) sl.classList.add("over");
  };
  const up = ev => {
    document.removeEventListener("pointermove", mv); document.removeEventListener("pointerup", up); document.querySelectorAll("#slots > div.over").forEach(x => x.classList.remove("over"));
    if (!g) return; g.remove(); const t = hit(ev); if (!t) return; const sl = t.closest("#slots > div");
    if (sl && sl.dataset.at) op({ op: "replace", at: JSON.parse(sl.dataset.at), photo: n });
    else { const r = $("main").getBoundingClientRect(); if (ev.clientX >= r.left && ev.clientX <= r.right && ev.clientY >= r.top && ev.clientY <= r.bottom) op({ op: "putfree", s: cur, photo: n, fx: (ev.clientX - r.left) / r.width, fy: (ev.clientY - r.top) / r.height }); }
  };
  document.addEventListener("pointermove", mv); document.addEventListener("pointerup", up);
}
// se l'editor è stato riavviato, ricarica la pagina da sola
let aggSeen = null;
function avvisoAgg(a) {
  const n = (a.nomi || []).length, ar = (a.ar || []).length;
  toast(`${n} ${n === 1 ? "foto aggiornata" : "foto aggiornate"} (modificate fuori dal programma)${ar ? ` · ${ar} con proporzioni cambiate: controlla il ritaglio` : ""}`, !!ar);
}
setInterval(async () => { try { const p = await (await fetch("/api/ping")).json();
  if (S && S.boot && p.boot !== S.boot && !$("busy").style.display.includes("flex")) { location.reload(); return; }
  if (S && aggSeen !== null && p.agg !== aggSeen) { aggSeen = p.agg; S = await api("/api/state"); render(); if ($("prjd").style.display === "flex") prjInfo(); avvisoAgg(S.agg); }
} catch (e) {} }, 4000);

// ---- una foto trascinata sulla pagina (anche vuota) diventa una cornice libera nel punto dove la lasci
$("wrap").ondragover = e => { if (dragData && dragData.photo && !e.target.closest("#slots > div")) e.preventDefault(); };
$("wrap").ondrop = e => {
  if (!(dragData && dragData.photo) || e.target.closest("#slots > div")) return; e.preventDefault();
  const r = $("main").getBoundingClientRect(), n = dragData.photo; dragData = null;
  op({ op: "putfree", s: cur, photo: n, fx: (e.clientX - r.left) / r.width, fy: (e.clientY - r.top) / r.height });
};

// ---- pannelli comprimibili e tutto schermo
function setPanels(list, side, pool) { document.body.classList.toggle("nolist", !list); document.body.classList.toggle("noside", !side); document.body.classList.toggle("nopool", !pool); try { localStorage.setItem("pan", [list, side, pool].map(x => +x).join("")); } catch (e) {} setTimeout(() => { drawRulers(); if (S && view === "album") renderStage(); }, 30); }
const panels = () => [!document.body.classList.contains("nolist"), !document.body.classList.contains("noside"), !document.body.classList.contains("nopool")];
$("tlist").onclick = () => { const [l, s_, p_] = panels(); setPanels(!l, s_, p_); };
$("tside").onclick = () => { const [l, s_, p_] = panels(); setPanels(l, !s_, p_); };
$("tfull").onclick = () => { const [l, s_, p_] = panels(); const all = l || s_ || p_; setPanels(!all, !all, !all); };
function setTools(on, save = true) { document.body.classList.toggle("tpin", on); $("ttog").classList.toggle("on", on); $("ttog").textContent = (on ? "▾" : "▸") + " Strumenti"; $("ttog").title = on ? "Clicca per nascondere la fascia (si riapre passando qui sopra)" : "Clicca per tenere la fascia sempre visibile"; setTimeout(() => { drawRulers(); if (S && view === "album") renderStage(); }, 30); try { if (save) localStorage.setItem("tbar2", on ? "1" : "0"); } catch (e) {} }
let tHide = null;
function showTools(v) { clearTimeout(tHide); if (v) $("stage").classList.add("tshow"); else tHide = setTimeout(() => $("stage").classList.remove("tshow"), 1800); }
["ttog", "tools", "thot"].forEach(i => { $(i).addEventListener("mouseenter", () => showTools(true)); $(i).addEventListener("mouseleave", () => showTools(false)); });
$("ttog").onclick = () => setTools(!document.body.classList.contains("tpin"));
try { setTools(localStorage.getItem("tbar2") !== "0", false); const pn0 = localStorage.getItem("pan"); if (pn0 === null && innerWidth < 1250) { setPanels(false, true, true); localStorage.removeItem("pan"); } } catch (e) { setTools(false, false); }
try { const pn = localStorage.getItem("pan"); if (pn && pn.length === 3) setPanels(pn[0] === "1", pn[1] === "1", pn[2] === "1"); } catch (e) {}

