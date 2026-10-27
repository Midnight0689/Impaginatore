// ---- selettore di foto del programma (⌘A, ⌘-clic e Maiusc-clic funzionano sempre)
let FB = { mode: "files", path: "", data: null, sel: [], last: null };
async function fbLoad(p) {
  try { const d = await (await fetch("/api/ls?p=" + encodeURIComponent(p || ""))).json(); if (d.errore) throw new Error(d.errore); FB.data = d; FB.path = d.path; FB.sel = []; FB.last = null; fbRender(); $("fbmain").scrollTop = 0; } catch (e) { toast(e.message, true); }
}
function fbRender() {
  const d = FB.data; $("fbtitle").textContent = "\u202A" + d.path; $("fbup").disabled = !d.parent; $("fbtitle").style.direction = "rtl";
  $("fbplaces").innerHTML = ""; d.places.forEach(pl => { const e = document.createElement("div"); e.className = "pl" + (d.path === pl.p ? " on" : ""); e.textContent = pl.n; e.onclick = () => fbLoad(pl.p); $("fbplaces").appendChild(e); });
  const M = $("fbmain"); M.innerHTML = ""; const g = document.createElement("div"); g.className = "grid"; M.appendChild(g);
  d.dirs.forEach(n => { const e = document.createElement("div"); e.className = "fbi"; e.innerHTML = '<div class="th">📁</div><div class="nm"></div>'; e.lastChild.textContent = n; e.title = n + " · doppio clic per aprire"; e.ondblclick = () => fbLoad(d.path.replace(/\/$/, "") + "/" + n); e.onclick = () => { if (FB.mode === "folder") fbLoad(d.path.replace(/\/$/, "") + "/" + n); }; g.appendChild(e); });
  d.files.forEach((f, i) => { const e = document.createElement("div"); e.className = "fbi" + (FB.sel.includes(f.n) ? " sel" : ""); e.dataset.n = f.n; e.title = f.n; e.innerHTML = '<div class="th"><img loading="lazy"></div><div class="nm"></div>'; e.querySelector("img").src = "/api/fthumb?w=240&p=" + encodeURIComponent(d.path.replace(/\/$/, "") + "/" + f.n); e.lastChild.textContent = f.n;
    e.onclick = ev => {
      if (FB.mode === "folder") return;
      if (ev.shiftKey && FB.last) { const a = d.files.findIndex(x => x.n === FB.last), b = i; d.files.slice(Math.min(a, b), Math.max(a, b) + 1).forEach(x => { if (!FB.sel.includes(x.n)) FB.sel.push(x.n); }); }
      else if (ev.metaKey || ev.ctrlKey) { const k = FB.sel.indexOf(f.n); if (k >= 0) FB.sel.splice(k, 1); else FB.sel.push(f.n); }
      else FB.sel = (FB.sel.length === 1 && FB.sel[0] === f.n) ? [] : [f.n];
      FB.last = f.n; fbUpdate();
    }; g.appendChild(e); });
  if (!d.dirs.length && !d.files.length) { const e = document.createElement("div"); e.className = "empty"; e.style.padding = "30px"; e.textContent = "Cartella vuota (qui si vedono solo sottocartelle e foto JPEG)."; M.appendChild(e); }
  fbUpdate();
}
function fbUpdate() {
  document.querySelectorAll("#fbmain .fbi[data-n]").forEach(e => e.classList.toggle("sel", FB.sel.includes(e.dataset.n)));
  const nf = FB.data.files.length, folder = FB.mode === "folder";
  $("fbhint").textContent = folder ? "Apri la cartella con le foto, poi premi «Importa questa cartella»" : "⌘A tutte · ⌘-clic aggiunge · Maiusc-clic intervallo";
  $("fbinfo").textContent = folder ? `${nf} foto JPEG in questa cartella (più quelle nelle sottocartelle)` : `${FB.sel.length} selezionate su ${nf}`;
  $("fbgo").textContent = folder ? "Importa questa cartella" : `Importa ${FB.sel.length || ""} foto`.replace("  ", " "); $("fbgo").disabled = folder ? false : !FB.sel.length;
  $("fball").style.display = $("fbnone").style.display = folder ? "none" : "";
}
function fbOpen(mode) { FB.mode = mode; $("fbd").style.display = "flex"; $("fbmain").focus(); fbLoad(FB.path || ""); }
function fbAll() { if (FB.mode === "files") { FB.sel = FB.data.files.map(f => f.n); FB.last = FB.sel[FB.sel.length - 1] || null; fbUpdate(); } }
$("fbup").onclick = () => FB.data.parent && fbLoad(FB.data.parent); $("fball").onclick = fbAll; $("fbnone").onclick = () => { FB.sel = []; fbUpdate(); };
$("fbcancel").onclick = () => $("fbd").style.display = "none";
$("fbgo").onclick = () => { $("fbd").style.display = "none"; const base = FB.data.path.replace(/\/$/, ""); doImport(FB.mode === "folder" ? [base] : FB.sel.map(n => base + "/" + n)); };
document.addEventListener("keydown", e => { if ($("fbd").style.display !== "flex") return; if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "a") { e.preventDefault(); e.stopPropagation(); fbAll(); } else if (e.key === "Escape") { e.stopPropagation(); $("fbd").style.display = "none"; } else if (e.key === "Enter" && !$("fbgo").disabled) { e.stopPropagation(); $("fbgo").onclick(); } }, true);
async function doImport(paths) {
  try {
    const res = await api("/api/import", { paths });
    if (!res.riavvio) { toast(res.saltate ? `Nessuna foto nuova (${res.saltate} già presenti o non JPEG)` : "Nessuna foto trovata", true); return; }
    $("busymsg").innerHTML = `Importo ${res.importate} foto…<br><span style="color:var(--dim);font-size:12px">preparo miniature e riconoscimento volti: ci vuole un po'</span>`; $("busy").style.display = "flex";
    const boot = S.boot; await new Promise(r => setTimeout(r, 1500));
    for (let i = 0; i < 600; i++) { try { const p = await (await fetch("/api/ping")).json(); if (p.boot !== boot) { location.reload(); return; } } catch (e) {} await new Promise(r => setTimeout(r, 1000)); }
  } catch (e) { $("busy").style.display = "none"; }
}
$("impF").onclick = () => fbOpen("folder"); $("impP").onclick = () => fbOpen("files");
$("selclear").onclick = () => { SELP = []; renderLib(); };
$("selall").onclick = () => { SELP = selectable(); lastClick = SELP[SELP.length - 1] || null; renderLib(); };
$("tabF").onclick = () => { view = "foto"; render(); }; $("tabA").onclick = () => { view = "album"; render(); }; $("gofoto").onclick = () => { view = "foto"; render(); };

// ---- galleria modelli (come la scelta dei template di Smart Albums)
let tplFor = -1;
async function openTpl() {
  const T = $("tpl"), mine = tplFor = cur; T.style.display = "block"; T.innerHTML = '<div class="empty">Carico i modelli…</div>';
  const d = await api("/api/templates?s=" + mine); if (tplFor !== mine) return;                       // nel frattempo hai cambiato spread: vale l'ultima richiesta
  const ut = d.utente || [], hasPh = S.spreads[cur].items.some(i => i.k !== "t");
  const apply = t => async () => { closeTpl(); sel = null; await op({ op: "template", s: cur, L: t.L, R: t.R }); };
  const mod = async (body, msg) => { try { await api("/api/modelli", body); toast(msg); openTpl(); } catch (e) {} };
  T.innerHTML = `<div class="bar"><button id="tclose">✕ Chiudi</button><b>Modelli per ${d.n || 0} foto${d.lato ? ` · solo pagina ${d.lato === "L" ? "sinistra" : "destra"}` : ""}</b>${hasPh ? '<button id="tsave" class="primary" title="Salva il layout di questo spread: comparirà per gli spread con lo stesso numero di foto">💾 Salva questo spread come modello…</button>' : ""}<span class="empty">${d.nota || (d.lato ? "L'altra pagina ha il testo e non cambia. " : "") + (d.tot ? d.tot + " possibili · le foto sono già abbinate per orientamento · in verde: quello attuale" : "")}</span></div>
    <div id="tut" style="display:none"><div class="sec" style="margin:10px 4px 4px">I tuoi modelli</div><div class="grid" id="gut"></div></div>
    <div id="tstd" style="display:none"><div class="sec" style="margin:10px 4px 4px">Modelli standard</div><div class="grid" id="gstd"></div></div>
    <div class="empty" id="tnone" style="display:none">${d.nota || "Nessun modello per questo numero di foto."}</div>`;
  $("tclose").onclick = closeTpl;
  if ($("tsave")) $("tsave").onclick = async () => { const n = prompt(`Nome del modello (layout di questo spread, ${d.n} foto):`); if (n && n.trim()) mod({ azione: "salva", s: cur, nome: n.trim() }, "Modello salvato"); };
  ut.forEach(t => {
    const tile = mkTile(t, t.cur ? t.nome + " · attuale" : t.nome, apply(t)), bar = document.createElement("div"); bar.style.cssText = "display:flex;gap:4px;margin:4px 2px 0";
    [["Aggiorna", "Sostituisci questo modello con il layout dello spread attuale", () => { if (confirm(`Aggiornare «${t.nome}» con il layout di questo spread (${d.n} foto)?`)) mod({ azione: "aggiorna", s: cur, id: t.id }, "Modello aggiornato"); }],
     ["Rinomina", "", () => { const n = prompt("Nuovo nome:", t.nome); if (n && n.trim() && n.trim() !== t.nome) mod({ azione: "rinomina", id: t.id, nome: n.trim() }, "Modello rinominato"); }],
     ["Elimina", "Elimina il modello (gli spread già fatti non cambiano)", () => { if (confirm(`Eliminare il modello «${t.nome}»?`)) mod({ azione: "elimina", id: t.id }, "Modello eliminato"); }]].forEach(([l, ti, fn]) => {
      const b = document.createElement("button"); b.textContent = l; b.title = ti; b.style.cssText = "font-size:11px;padding:2px 6px"; if (l === "Elimina") b.className = "danger"; b.onclick = ev => { ev.stopPropagation(); fn(); }; bar.appendChild(b); });
    tile.appendChild(bar); $("gut").appendChild(tile); });
  d.items.forEach((t, n) => $("gstd").appendChild(mkTile(t, t.cur ? "attuale" : "modello " + (n + 1), apply(t))));
  $("tut").style.display = ut.length ? "" : "none"; $("tstd").style.display = d.items.length ? "" : "none"; if (!d.items.length && !ut.length) $("tnone").style.display = "";
  if (!ut.length) T.querySelector("#tstd .sec").style.display = "none";
}
function closeTpl() { $("tpl").style.display = "none"; tplFor = -1; }
$("tplb").onclick = () => openTpl();

$("undo").onclick = () => op({ op: "undo" });
$("redo").onclick = () => op({ op: "redo" });
let pxres = null;
function prjInfo() {
  const m = S.mancanti || [], n = S.photos.length;
  $("prjfoto").innerHTML = m.length ? `<b style="color:var(--danger)">${m.length} foto su ${n} non si trovano</b> (spostate, rinominate o disco scollegato):<br>${m.slice(0, 12).join(", ")}${m.length > 12 ? "…" : ""}<br>Premi «Ricollega foto…» e scegli la cartella dove sono ora.` : `${n} foto · tutte trovate`;
}
function updMiss() { const m = S.mancanti || [], b = $("missb"); b.style.display = m.length ? "" : "none"; b.textContent = `⚠ ${m.length} foto mancanti`; }
const openPrj = () => { prjInfo(); $("prjd").style.display = "flex"; };
$("prjb").onclick = openPrj; $("missb").onclick = openPrj; $("prjclose").onclick = () => $("prjd").style.display = "none";
$("prelink").onclick = async () => {
  try {
    const r = await api("/api/ricollega", {}); if (r.annullato) return;
    S = await api("/api/state"); render(); prjInfo();
    toast(r.mancanti.length ? `Ritrovate ${r.trovate}; ${r.mancanti.length} ancora mancanti` : `Ritrovate ${r.trovate} foto: tutto collegato`, !!r.mancanti.length);
  } catch (e) {}
};
$("pcheck").onclick = async () => {
  try { const r = await api("/api/aggiorna_foto", {}); S = await api("/api/state"); aggSeen = S.agg.n; render(); prjInfo();
    if (!r.aggiornate.length && !r.errori.length) toast("Nessuna foto modificata: è tutto aggiornato"); else avvisoAgg({ nomi: r.aggiornate, ar: r.proporzioni });
    if (r.errori.length) toast(`Non riuscite (file incompleto?): ${r.errori.join(", ")}`, true); } catch (e) {}
};
$("pxgo").onclick = async () => {
  const lg = $("pxlog"); try {
    const r = await api("/api/prj_esporta", { foto: $("pxfoto").checked, zip: $("pxzip").checked }); if (r.annullato) return;
    lg.style.display = "block"; lg.textContent = "…"; $("pxgo").disabled = true; $("pxreveal").style.display = "none"; pxres = null;
    for (let i = 0; i < 3000; i++) { await new Promise(z => setTimeout(z, 800)); const L = await api("/api/log"); lg.textContent = L.filter(x => !x.startsWith("RISULTATO:")).join("\n"); lg.scrollTop = lg.scrollHeight;
      const rs = L.find(x => x.startsWith("RISULTATO:")); if (rs) pxres = rs.slice(10); if (L.includes("[finito]")) break; }
    if (pxres) $("pxreveal").style.display = "";
  } catch (e) {} $("pxgo").disabled = false;
};
$("pxreveal").onclick = () => pxres && api("/api/reveal", { path: pxres });
$("vclose").onclick = () => $("verd").style.display = "none";
$("verb").onclick = async () => {
  $("verd").style.display = "flex"; const l = $("verl"); l.textContent = "…";
  const v = await api("/api/versioni"); l.textContent = v.length ? "" : "Nessuna versione salvata";
  v.forEach(x => { const b = document.createElement("button"); b.style.textAlign = "left"; b.textContent = `${x.label}  ·  ${x.spread} spread`;
    b.onclick = async () => { if (!confirm(`Tornare alla versione del ${x.label} (${x.spread} spread)?\nLo stato attuale viene salvato prima.`)) return;
      const boot = S.boot; await api("/api/ripristina", { ts: x.ts }); $("verd").style.display = "none"; toast("Ripristino…");
      await new Promise(r => setTimeout(r, 1500)); for (let i = 0; i < 120; i++) { try { const p = await (await fetch("/api/ping")).json(); if (p.boot !== boot) { location.reload(); return; } } catch (e) {} await new Promise(r => setTimeout(r, 1000)); } };
    l.appendChild(b); });
};
$("save").onclick = async () => { try { S = await api("/api/save", {}); render(); toast("Salvato spec.py e progetto.json (copie in _backup_editor)"); } catch (e) {} };
