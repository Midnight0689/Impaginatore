// ---- esportazione: un solo pannello per JPG, PDF e PSD
let EF = "jpg", elog = null;
function openExp() {
  $("exp").style.display = "flex"; $("elog").style.display = "none"; $("elog").textContent = ""; $("ereveal").style.display = "none"; $("ego").disabled = false;
  $("eev").value = S.globale || 0; setFmt(EF); updCount();
}
function setFmt(f) {
  EF = f; document.querySelectorAll("#efmt button").forEach(b => b.classList.toggle("on", b.dataset.f === f));
  ["jpg", "pdf", "psd"].forEach(k => $("eo-" + k).style.display = k === f ? "" : "none");
  $("edest").value = ""; $("edest").placeholder = f === "psd" ? "cartella PSD del progetto (come prima)" : "Esportazioni/" + f.toUpperCase() + " dentro il progetto"; $("ego").textContent = "Esporta in " + f.toUpperCase();
}
function rangeNums() {
  if (document.querySelector('input[name=er]:checked').value === "all") return S.spreads.map((_, i) => i + 1);
  const out = []; for (const p of $("erange").value.split(/[,;]/)) { const t = p.trim(); if (!t) continue; const m = t.match(/^(\d+)\s*-\s*(\d+)$/); if (m) { for (let i = Math.min(+m[1], +m[2]); i <= Math.max(+m[1], +m[2]); i++) out.push(i); } else if (/^\d+$/.test(t)) out.push(+t); else return null; }
  return [...new Set(out)];
}
function updCount() { const r = rangeNums(), n = S.spreads.length; $("ecount").textContent = !r ? "Scrivi numeri e intervalli, es. 1, 2, 5-7" : r.some(x => x < 1 || x > n) ? `L'album ha ${n} spread` : `${r.length} spread verranno esportati`; }
document.querySelectorAll("#efmt button").forEach(b => b.onclick = () => setFmt(b.dataset.f));
document.querySelectorAll("input[name=er]").forEach(r => r.onchange = updCount); $("erange").oninput = () => { document.querySelector('input[name=er][value=r]').checked = true; updCount(); };
$("expb").onclick = openExp; $("ecancel").onclick = () => $("exp").style.display = "none";
$("echoose").onclick = async () => { const r = await api("/api/pick", { kind: "folder" }); if (r.paths[0]) $("edest").value = r.paths[0].replace(/\/$/, ""); };
let epoll = null, eres = null;
$("ego").onclick = async () => {
  const body = { fmt: EF, range: document.querySelector('input[name=er]:checked').value === "all" ? "" : $("erange").value, dest: $("edest").value, ev: +$("eev").value || 0,
    res: $("ejq").value, q: EF === "jpg" ? +$("ejqq").value : 80, width: +$("epw").value, numeri: $("epn").checked, force: $("epf").checked };
  if (EF === "psd" && !confirm("Genero i PSD in Photoshop (i PSD modificati a mano non vengono toccati, salvo la spunta). Continuo?")) return;
  try { await api("/api/export", body); } catch (e) { return; }
  $("ego").disabled = true; $("elog").style.display = "block"; $("elog").textContent = "Avvio…"; eres = null;
  clearInterval(epoll);
  epoll = setInterval(async () => {
    const l = await api("/api/log"); $("elog").textContent = l.filter(x => !x.startsWith("RISULTATO:")).join("\n"); $("elog").scrollTop = 1e6;
    const r = l.find(x => x.startsWith("RISULTATO:")); if (r) eres = r.slice(10);
    if (l.length && l[l.length - 1].startsWith("[finito")) {
      clearInterval(epoll); $("ego").disabled = false; const sk = l.filter(x => x.startsWith("SALTATO")), er = l.find(x => /ERRORE|errore/.test(x));
      if (sk.length) toast(sk.length + " spread NON generati: " + sk[0].replace(/ -> .*/, ""), true); else if (er) toast("Qualcosa non è andato: guarda il riquadro", true); else if (eres) toast("Esportazione finita");
      if (eres) $("ereveal").style.display = ""; render();
    }
  }, 800);
};
$("wrap").addEventListener("contextmenu", e => { if (!S || e.target.closest(".slot") || textTool) return; bgMenu(e); });
$("ereveal").onclick = () => api("/api/reveal", { path: eres });

document.addEventListener("keydown", e => {
  if (S && e.key.toLowerCase() === "p" && !e.metaKey && !e.ctrlKey && !e.altKey && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && (view === "foto" || HOV)) { e.preventDefault(); const nn = view === "foto" && SELP.length ? SELP : HOV ? [HOV] : []; if (nn.length) { const v = !nn.every(n => (S.photos.find(x => x.n === n) || {}).star); op({ op: "stella", photos: nn, value: v }); } return; }
  if (S && /^[0-7]$/.test(e.key) && !e.metaKey && !e.ctrlKey && !e.altKey && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && (view === "foto" || HOV)) { e.preventDefault(); assignColor(e.key === "0" ? null : COLS[+e.key - 1][0]); return; }
  if (view === "foto" && S && (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "a" && !(document.activeElement && (/TEXTAREA|SELECT/.test(document.activeElement.tagName) || (document.activeElement.tagName === "INPUT" && /text|number|search/.test(document.activeElement.type))))) {       // ⌘A nella galleria (le caselle da spuntare non lo bloccano): tutte le foto ancora da usare
    e.preventDefault(); SELP = selectable(); lastClick = SELP[SELP.length - 1] || null; renderLib(); return;
  }
  if (view === "album" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && S) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "a") { e.preventDefault(); msel = S.spreads[cur].items.filter(i => i.k !== "t").map(kOf); if (msel.length) { const [a, b] = msel[msel.length - 1].split(":"); sel = { s: cur, side: a, idx: +b }; } render(); return; }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "c" && msel.length) { e.preventDefault(); copySel(); return; }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "v") { e.preventDefault(); pasteSel(); return; }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "d") { e.preventDefault(); dupSpread(); return; }
    if (e.key.toLowerCase() === "t" && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); setTextTool(!textTool); return; }
    if ((e.key === "+" || e.key === "=" || e.key === "-" || e.key === "_") && !e.metaKey && !e.ctrlKey && !e.altKey && msel.length) { e.preventDefault(); op({ op: "zorder", s: cur, ats: mAts(), dir: e.key === "+" || e.key === "=" ? "forward" : "backward" }); return; }
    if ((e.key === "]" || e.key === "[" || e.key === "}" || e.key === "{") && msel.length) { e.preventDefault(); op({ op: "zorder", s: cur, ats: mAts(), dir: e.key === "]" ? "forward" : e.key === "[" ? "backward" : e.key === "}" ? "front" : "back" }); return; }
  }
  if (e.key === "Tab" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); $("tfull").onclick(); return; }
  if (view === "foto") { if (e.key === "Escape") { SELP = []; renderLib(); } return; }
  if (e.key.toLowerCase() === "m" && !e.metaKey && !e.ctrlKey && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) { $("tpl").style.display === "block" ? closeTpl() : openTpl(); }
  else if (e.key.toLowerCase() === "r" && !e.metaKey && !e.ctrlKey && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) setRulers(!showRulers);
  else if (e.key.toLowerCase() === "g" && !e.metaKey && !e.ctrlKey && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) setGuides(!showGuides);
  else if (e.key === "Escape") { if (textTool) { setTextTool(false); return; } closeTpl(); if (cropMode) setCrop(false); else if (msel.length || sel) { msel = []; sel = null; render(); } }
  else if ((e.key === "Delete" || e.key === "Backspace") && msel.length > 1 && !/INPUT/.test(document.activeElement.tagName)) { e.preventDefault(); (async () => { for (const [a, b] of mAts().sort((x, y) => y[1] - x[1])) await op({ op: "delframe", at: [cur, a, b] }); msel = []; sel = null; render(); })(); }
  else if ((e.key === "Delete" || e.key === "Backspace") && sel && selItem() && (selItem().k !== "t" || selItem().kind === "txt") && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) { e.preventDefault(); op({ op: "delframe", at: [sel.s, sel.side, sel.idx] }); }
  else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") { e.preventDefault(); op({ op: e.shiftKey ? "redo" : "undo" }); }
  else if (e.key === "ArrowDown" && !/INPUT/.test(document.activeElement.tagName)) { e.preventDefault(); if (cur < S.spreads.length - 1) { cur++; sel = null; render(); } }
  else if (e.key === "ArrowUp" && !/INPUT/.test(document.activeElement.tagName)) { e.preventDefault(); if (cur > 0) { cur--; sel = null; render(); } }
});



const STG = [["#000000", "Nero"], ["#1b1b1d", "Grigio scuro"], ["#6b6b70", "Grigio chiaro"], ["#ffffff", "Bianco"]];
let STGL = false;
function setStg(c) { STGL = c === "#ffffff"; document.documentElement.classList.toggle("stgl", STGL); document.documentElement.style.setProperty("--stg", c); if (S) drawRulers(); try { localStorage.stgBg = c; } catch (_) {} $("stgsw").innerHTML = STG.map(([k, n]) => `<i style="--c:${k}" data-c="${k}" title="Sfondo ${n.toLowerCase()}" class="${k === c ? "on" : ""}"></i>`).join(""); }
$("stgsw").addEventListener("click", e => { const c = e.target.dataset && e.target.dataset.c; if (c) setStg(c); });
setStg((() => { try { return localStorage.stgBg || "#1b1b1d"; } catch (_) { return "#1b1b1d"; } })());
api("/api/state").then(s => { S = s; aggSeen = s.agg ? s.agg.n : 0; view = S.spreads.length ? "album" : "foto"; render(); });
