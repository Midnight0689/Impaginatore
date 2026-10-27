let lastTxDown = { k: null, t: 0 }, textTool = false, FONTS = [], msel = [], S = null, cur = 0, sel = null, dragData = null, cropMode = false, view = null, SELP = [], lastClick = null;
const $ = id => document.getElementById(id);

function toast(msg, err) { const t = $("toast"); t.textContent = msg; t.className = err ? "err" : ""; t.style.display = "block"; clearTimeout(toast.t); toast.t = setTimeout(() => t.style.display = "none", err ? 4500 : 1800); }

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json();
  if (j.errore) { toast(j.errore, true); throw new Error(j.errore); }
  return j;
}
const CID = Math.random().toString(36).slice(2);
async function op(o) {
  try { S = await api("/api/op", Object.assign({ cid: CID, rev: S ? S.rev : undefined }, o)); render(); }
  catch (e) { if (/un'altra scheda/.test(e.message)) { S = await api("/api/state"); render(); } }
}

function slotsOf(s) { return S.spreads[s].items; }
const kOf = it => it.side + ":" + it.idx, inM = it => msel.includes(kOf(it));
const mAts = () => msel.map(k => { const [a, b] = k.split(":"); return [a, +b]; });
function selItem() { return sel ? slotsOf(sel.s).find(i => i.side === sel.side && i.idx === sel.idx) : null; }
function pageHasText(side) { return slotsOf(cur).some(i => i.side === side && i.k === "t"); }

function render() {
  if (!S) return;
  msel = msel.filter(k => { const [a, b] = k.split(":"); return S.spreads[Math.min(cur, S.spreads.length - 1)].items.some(i => i.side === a && i.idx === +b); });
  if (sel && msel.length === 0) msel = [sel.side + ":" + sel.idx];
  cur = Math.min(cur, S.spreads.length - 1);
  if (sel && !selItem()) sel = null;
  $("title").textContent = S.nome;
  $("undo").disabled = !S.canundo; $("redo").disabled = !S.canredo;
  $("status").textContent = S.saveerr ? "⚠ SALVATAGGIO NON RIUSCITO" : S.dirty ? "salvo…" : "tutto salvato"; $("status").className = S.saveerr ? "err" : S.dirty ? "dirty" : ""; $("status").title = S.saveerr || "";
  clearTimeout(render.t); if (S.dirty) render.t = setTimeout(async () => { try { const d = await api("/api/state"); S.saveerr = d.saveerr; if (!d.dirty) S.dirty = false; $("status").textContent = S.saveerr ? "⚠ SALVATAGGIO NON RIUSCITO" : S.dirty ? "salvo…" : "tutto salvato"; $("status").className = S.saveerr ? "err" : S.dirty ? "dirty" : ""; $("status").title = S.saveerr || ""; if (d.dirty) render.t = setTimeout(() => render(), 100); } catch (e) {} }, 3000);
  if (S.home) { $("home").style.display = ""; $("home").href = S.home; if (!window._upd) { window._upd = 1; const chk = () => fetch(S.home + "/api/aggiornamento").then(r => r.json()).then(r => { $("home").title = r.attuale ? `Torna ai progetti · versione ${r.attuale.n}` : "Torna ai progetti"; $("updn").style.display = r.da_aggiornare ? "" : "none"; $("updn").href = S.home; $("updn").title = "Novità:\n" + (r.novita || []).join("\n") + "\n\nClicca per tornare ai progetti e aggiornare"; }).catch(() => {}); chk(); setInterval(chk, 600000); } }
  document.body.classList.toggle("foto", view === "foto"); $("tabF").classList.toggle("on", view === "foto"); $("tabA").classList.toggle("on", view === "album");
  renderLib();
  const empty = !S.spreads.length; $("nospread").style.display = empty ? "block" : "none"; ["sbarL", "sbarR", "rwrap", "hint"].forEach(i => $(i).style.display = empty ? "none" : "");
  renderList(); renderPool();
  if (empty) { sel = null; $("insp").innerHTML = ""; return; }
  updMiss(); renderSbar(); renderStage(); renderSide(); drawRulers(); renderGuides();
  if ($("tpl").style.display === "block" && tplFor !== cur) openTpl();                    // pannello Modelli aperto e spread cambiato: ricarica i modelli giusti
}

function renderList() {
  const L = $("thumbs"), have = L.children.length;
  while (L.children.length > S.spreads.length) L.lastChild.remove();
  S.spreads.forEach((sp, k) => {
    let d = L.children[k];
    if (!d) { d = document.createElement("div"); d.innerHTML = "<img><span></span>"; L.appendChild(d); }
    d.className = "sth" + (k === cur ? " sel" : ""); const src = `/img/spread/${k}?k=0.05&h=${sp.h}`, im = d.firstChild;
    if (im.getAttribute("src") !== src) im.src = src; d.lastChild.textContent = k + 1; d.onclick = () => go(k); d.oncontextmenu = e => spreadMenu(e, k);
    d.draggable = true; d.ondragstart = e => { dragData = { spread: k }; e.dataTransfer.setData("text/plain", "s" + k); };
    d.ondragover = e => { if (dragData && dragData.spread != null) { e.preventDefault(); d.classList.add("over"); } }; d.ondragleave = () => d.classList.remove("over");
    d.ondrop = e => { d.classList.remove("over"); if (dragData && dragData.spread != null) { e.preventDefault(); const a = dragData.spread; dragData = null; moveSp(a, k); } };
  });
  const el = L.querySelector(".sel"); if (el) el.scrollIntoView({ block: "nearest" });
}
// ---- zoom dello spread: Alt + rotella (o trackpad), centrato sul puntatore; il pulsante «Adatta» torna alla vista intera
let ZM = 1, zmT = null;
function applyZoom(keepPoint) {
  const st = $("stage"), rw = $("rwrap"), w = $("wrap"); st.classList.toggle("zoomed", ZM > 1.001);
  const r0 = w.getBoundingClientRect(), fx = keepPoint ? (keepPoint.x - r0.left) / r0.width : .5, fy = keepPoint ? (keepPoint.y - r0.top) / r0.height : .5;
  if (ZM > 1.001) { rw.style.width = Math.round((st.clientWidth - 32) * ZM) + "px"; rw.style.maxWidth = "none"; } else { rw.style.width = ""; rw.style.maxWidth = ""; }
  if (keepPoint) { const r1 = w.getBoundingClientRect(); st.scrollLeft += (r1.left + fx * r1.width) - keepPoint.x; st.scrollTop += (r1.top + fy * r1.height) - keepPoint.y; }
  let z = $("zpill"); if (!z) { z = document.createElement("button"); z.id = "zpill"; z.title = "Torna alla vista intera dello spread"; z.onclick = () => { ZM = 1; applyZoom(); renderStage(); }; st.appendChild(z); }
  z.style.display = ZM > 1.001 ? "" : "none"; z.textContent = Math.round(ZM * 100) + "% · Adatta";
  clearTimeout(zmT); zmT = setTimeout(() => { if (S && view === "album") renderStage(); drawRulers(); }, 160);
}
$("stage").addEventListener("wheel", e => {
  if (!(e.altKey || e.ctrlKey) || view !== "album" || !S || !S.spreads.length) return; e.preventDefault();       // Alt + rotella, oppure pizzico sul trackpad (arriva come Ctrl + rotella)
  const d = Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX; ZM = Math.min(5, Math.max(1, ZM * Math.exp(-d * (e.ctrlKey ? 0.012 : 0.0025))));
  applyZoom({ x: e.clientX, y: e.clientY });
}, { passive: false });
let gz0 = 1;                                                                                                     // Safari: eventi di gesto
$("stage").addEventListener("gesturestart", e => { if (view !== "album") return; e.preventDefault(); gz0 = ZM; });
$("stage").addEventListener("gesturechange", e => { if (view !== "album" || !S || !S.spreads.length) return; e.preventDefault(); ZM = Math.min(5, Math.max(1, gz0 * e.scale)); applyZoom({ x: e.clientX, y: e.clientY }); });
window.addEventListener("resize", () => { if (ZM > 1.001) applyZoom(); });
function stageK() { const w = $("wrap").clientWidth || 800, k = Math.ceil(Math.min(ZM > 1.001 ? 1 : 0.7, Math.max(0.15, w * (window.devicePixelRatio || 1) / S.W)) * 20) / 20; return +k.toFixed(2); }
function renderStage() {
  const sp = S.spreads[cur]; const m = $("main");
  const src = `/img/spread/${cur}?k=${stageK()}&h=${sp.h}`;
  if (m.getAttribute("src") !== src) { const im = new Image(); im.onload = () => { if (m.dataset.want === src) m.src = src; }; m.dataset.want = src; im.src = src; }   // cambia solo quando la nuova è pronta: niente lampi
  const box = $("slots"); box.innerHTML = "";
  sp.items.forEach(it => {
    const isSel = sel && sel.s === cur && sel.side === it.side && sel.idx === it.idx;
    const d = document.createElement("div");
    d.className = "slot" + (it.k === "t" ? " txt" : "") + (isSel ? " sel" : "") + (inM(it) ? " msel" : "");
    d.style.left = (it.x / S.W * 100) + "%"; d.style.top = (it.y / S.H * 100) + "%"; d.style.width = (it.w / S.W * 100) + "%"; d.style.height = (it.h / S.H * 100) + "%";
    d.style.zIndex = it.free ? 1 + it.zr : 0;      // le cornici libere stanno sopra (come nell'anteprima)
    if (it.k === "t") {
      const lay = it.kind === "txt";
      d.innerHTML = `<span class="tag">${lay ? "Testo" : "Testo (titolo)"}</span>`; d.title = lay ? "Trascina per spostare · doppio clic per scrivere" : "Doppio clic: lo rendo modificabile come livelli di testo"; d.dataset.at = JSON.stringify([cur, it.side, it.idx]);
      d.onpointerdown = e => { if (e.button !== 0) return; if (e.shiftKey || e.metaKey || e.ctrlKey) { e.preventDefault(); e.stopPropagation(); toggleM(it); return; }
        if (lay) { const now = Date.now(), k = kOf(it); if (lastTxDown.k === k && now - lastTxDown.t < 450) { lastTxDown = { k: null, t: 0 }; e.preventDefault(); e.stopPropagation(); setTimeout(() => { sel = { s: cur, side: it.side, idx: it.idx }; msel = [k]; const cur_ = selItem(); if (cur_) enterEdit(cur_); }, 30); return; } lastTxDown = { k, t: now }; }       // doppio clic riconosciuto qui: il primo clic ricostruisce gli elementi e il dblclick del browser andrebbe perso
        startFree(e, it, "move"); };
      d.oncontextmenu = e => frameMenu(e, it);
      d.ondblclick = async () => { if (lay) { sel = { s: cur, side: it.side, idx: it.idx }; msel = [kOf(it)]; render(); enterEdit(it); } else { await op({ op: "t2x", at: [cur, it.side, it.idx] }); sel = null; msel = []; render(); toast("Ora ogni riga è un livello di testo: clic per selezionarla, doppio clic per scrivere"); } };
      if (isSel && msel.length < 2) ["nw", "n", "ne", "e", "se", "s", "sw", "w"].forEach(k => { const hd = document.createElement("div"); hd.className = "hd"; hd.dataset.k = k; hd.onpointerdown = e => { if (e.button === 0) startFree(e, it, k); }; d.appendChild(hd); });
    }
    if (it.k !== "t") {
      const warn = it.crop > 1.25, to = [cur, it.side, it.idx];
      d.innerHTML = `<span class="tag${warn ? " warn" : ""}">${it.name}${it.bw ? " · BN" : ""}${it.z !== 1 ? " · ×" + it.z : ""}${warn ? " · ritaglio ×" + it.crop.toFixed(2) : ""}</span>`;
      d.dataset.at = JSON.stringify(to);
      d.onpointerdown = e => { if (e.button !== 0 || e.target.closest(".chip")) return; if (e.shiftKey || e.metaKey || e.ctrlKey) { e.preventDefault(); e.stopPropagation(); toggleM(it); return; } if (cropMode && isSel) startPan(e, it, d); else startFree(e, it, "move"); };
      d.ondblclick = () => { sel = { s: cur, side: it.side, idx: it.idx }; setCrop(true); };
      d.oncontextmenu = e => frameMenu(e, it);
      if (cropMode && isSel) d.classList.add("cropping");
      d.ondragover = e => { e.preventDefault(); d.classList.add("over"); };
      d.ondragleave = () => d.classList.remove("over");
      d.ondrop = e => {
        e.preventDefault(); d.classList.remove("over");
        if (dragData && dragData.from) { if (JSON.stringify(dragData.from) !== JSON.stringify(to)) op({ op: "swap", a: dragData.from, b: to }); }
        else if (dragData && dragData.photo) op({ op: "replace", at: to, photo: dragData.photo });
        dragData = null;
      };
      if (isSel && !cropMode && msel.length < 2) {
        ["nw", "n", "ne", "e", "se", "s", "sw", "w"].forEach(k => {
          const hd = document.createElement("div"); hd.className = "hd"; hd.dataset.k = k;
          hd.onpointerdown = e => { if (e.button === 0) startFree(e, it, k); }; d.appendChild(hd);
        });
        const ch = document.createElement("div"); ch.className = "chip"; ch.textContent = "⇄ scambia"; ch.title = "Trascinami sopra un'altra foto per scambiarle"; ch.draggable = true;
        ch.ondragstart = e => { dragData = { from: to }; e.dataTransfer.setData("text/plain", it.name); e.dataTransfer.effectAllowed = "move"; };
        d.appendChild(ch);
      }
    }
    box.appendChild(d);
  });
}

function toggleM(it) {
  const k = kOf(it), i = msel.indexOf(k); if (i >= 0) msel.splice(i, 1); else msel.push(k);
  if (msel.length) { const [a, b] = msel[msel.length - 1].split(":"); sel = { s: cur, side: a, idx: +b }; } else sel = null; render();
}
function selOrder() {                                        // ordine delle azioni: la riferimento (ultima toccata) per prima
  const ref = sel ? sel.side + ":" + sel.idx : msel[msel.length - 1]; return { ref: ref.split(":").map((v, i) => i ? +v : v), ats: mAts() };
}
$("stage").addEventListener("pointerdown", e => { if (e.button === 0 && (e.target === $("stage") || e.target === $("rwrap")) && (sel || msel.length)) { msel = []; sel = null; render(); } });
$("wrap").addEventListener("pointerdown", e => {              // rettangolo di selezione sullo sfondo
  if (e.button !== 0 || e.target.closest("#slots > div") || e.target.closest(".guide, .gl")) return; if (!S || cropMode) return;
  const r = $("main").getBoundingClientRect(), x0 = e.clientX, y0 = e.clientY, add = e.shiftKey || e.metaKey || e.ctrlKey, base = add ? msel.slice() : []; let box = null, moved = false;
  const mv = ev => {
    if (!moved && Math.hypot(ev.clientX - x0, ev.clientY - y0) < 4) return; moved = true;
    if (!box) { box = document.createElement("div"); box.style.cssText = "position:fixed;z-index:40;border:1px solid var(--accent);background:rgba(224,178,60,.15);pointer-events:none"; document.body.appendChild(box); }
    const L = Math.min(x0, ev.clientX), T = Math.min(y0, ev.clientY), R = Math.max(x0, ev.clientX), B = Math.max(y0, ev.clientY);
    box.style.left = L + "px"; box.style.top = T + "px"; box.style.width = R - L + "px"; box.style.height = B - T + "px";
    const hit = S.spreads[cur].items.filter(i => (i.k !== "t" || i.kind === "txt") && (() => { const a = r.left + i.x / S.W * r.width, b = r.top + i.y / S.H * r.height, c = a + i.w / S.W * r.width, d = b + i.h / S.H * r.height; return a < R && c > L && b < B && d > T; })()).map(kOf);
    msel = [...new Set(base.concat(hit))]; document.querySelectorAll("#slots > div.slot").forEach(d => { const it = S.spreads[cur].items.find(i => JSON.stringify([cur, i.side, i.idx]) === d.dataset.at); d.classList.toggle("msel", !!it && inM(it)); });
  };
  const up = () => {
    window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); if (box) box.remove();
    if (!moved) { msel = []; sel = null; } else if (msel.length) { const [a, b] = msel[msel.length - 1].split(":"); sel = { s: cur, side: a, idx: +b }; } else sel = null;
    render();
  };
  window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
});
const ICP = {
  prev: '<path d="m15 5-7 7 7 7"/>', next: '<path d="m9 5 7 7-7 7"/>', plus: '<path d="M12 5v14M5 12h14"/>',
  dup: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  mprev: '<path d="M4 4v16M20 12H9m0 0 5-5m-5 5 5 5"/>', mnext: '<path d="M20 4v16M4 12h11m0 0-5-5m5 5-5 5"/>',
  "al-l": '<path d="M4 3v18M8 7h12M8 14h7"/>', "al-ch": '<path d="M12 3v18M5 7h14M8 14h8"/>', "al-r": '<path d="M20 3v18M4 7h12M9 14h7"/>',
  "al-t": '<path d="M3 4h18M7 8v12M14 8v8"/>', "al-cv": '<path d="M3 12h18M7 5v14M14 8v8"/>', "al-b": '<path d="M3 20h18M7 4v12M14 8v8"/>',
  "dist-h": '<path d="M4 4v16M20 4v16"/><rect x="9" y="8" width="6" height="8" rx="1"/>', "dist-v": '<path d="M4 4h16M4 20h16"/><rect x="8" y="9" width="8" height="6" rx="1"/>',
  front: '<rect x="3" y="3" width="12" height="12" rx="2"/><rect x="9" y="9" width="12" height="12" rx="2" fill="currentColor" fill-opacity=".85"/>',
  back: '<rect x="9" y="9" width="12" height="12" rx="2"/><rect x="3" y="3" width="12" height="12" rx="2" fill="currentColor" fill-opacity=".85"/>',
  up: '<path d="M12 19V5M6 11l6-6 6 6"/>', down: '<path d="M12 5v14M6 13l6 6 6-6"/>',
  same: '<rect x="3" y="4" width="8" height="8" rx="1.5"/><rect x="13" y="12" width="8" height="8" rx="1.5"/>',
  photo: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m21 16-5-5-9 8"/>',
  full: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>', vert: '<rect x="8" y="3" width="8" height="18" rx="2"/>', horiz: '<rect x="3" y="8" width="18" height="8" rx="2"/>',
  text: '<path d="M5 6V4h14v2M12 4v16M9 20h6"/>', paste: '<path d="M9 4h6v3H9zM7 5H5v16h14V5h-2"/>',
  magnet: '<path d="M5 20v-9a7 7 0 0 1 14 0v9h-4v-9a3 3 0 0 0-6 0v9z"/>',
  ruler: '<rect x="3" y="8" width="18" height="8" rx="1.5"/><path d="M7 8v3M11 8v4M15 8v3"/>', guide: '<path d="M9 3v18M3 15h18"/>', clear: '<path d="M18 6 6 18M6 6l12 12"/>' };
const IC = k => `<svg class="ic2" viewBox="0 0 24 24">${ICP[k] || ""}</svg>`;
function renderSbar() {
  const sp = S.spreads[cur], n = S.spreads.length;
  const onlyTxt = msel.length > 0 && msel.every(k => { const i = sp.items.find(x => kOf(x) === k); return i && i.kind === "txt"; });
  const page = side => { const mode = side === "L" ? sp.L : sp.R; return `<div class="box"><i>Pagina ${side === "L" ? "sinistra" : "destra"}</i><div><span class="seg2"><button data-mode="${side}:I" class="${mode === "I" ? "on" : ""}" title="La foto arriva fino al bordo">Immersiva</button><button data-mode="${side}:W" class="${mode === "W" ? "on" : ""}" title="Pagina bianca con margine">Bianca</button></span><button data-add="${side}" title="Aggiunge una foto libera nel più grande spazio vuoto della pagina">+ Foto</button></div></div>`; };
  const sel_lbl = `${msel.length} ${onlyTxt ? (msel.length === 1 ? "testo selezionato" : "testi selezionati") : msel.length === 1 ? "foto selezionata" : "foto selezionate"}`;
  const B = (id, ic, lbl, ttl, extra = "") => `<button id="${id}" title="${ttl}" ${extra}>${IC(ic)}${lbl ? `<span>${lbl}</span>` : ""}</button>`;
  const AL = (m, ic, ttl, extra = "") => `<button data-al="${m}" title="${ttl}" class="al" ${extra}>${IC(ic)}</button>`;
    $("sbarL").innerHTML = `<div class="box"><i>Spread</i><div class="g3"><div class="navrow">${B("mvl", "prev", "", "Spread precedente (↑)", cur === 0 ? "disabled" : "")}<div class="cnt"><b>${cur + 1}</b><span>di ${n}</span></div>${B("mvr", "next", "", "Spread successivo (↓)", cur === n - 1 ? "disabled" : "")}</div>
      ${B("newsp", "plus", "Nuovo", "Aggiungi uno spread")}${B("dupsp", "dup", "Duplica", "Duplica questo spread subito dopo (Cmd+D)")}${B("delsp", "trash", "Elimina", "Elimina lo spread (le foto tornano libere)", (n < 2 ? "disabled " : "") + 'class="danger"')}
      ${B("mvup", "mprev", "Sposta prima", "Sposta questo spread prima", cur === 0 ? "disabled" : "")}${B("mvdn", "mnext", "Sposta dopo", "Sposta questo spread dopo", cur === n - 1 ? "disabled" : "")}</div></div>` +
    `<div class="box"><i>Strumenti</i><div class="g3">${B("ttxt", "text", "Testo", "Strumento Testo (T): clicca o trascina sulla pagina e scrivi", textTool ? 'class="on"' : "")}${B("mcopy", "dup", "Copia", "Copia gli elementi scelti (Cmd+C)", msel.length ? "" : "disabled")}${B("mpaste", "paste", "Incolla", "Incolla (Cmd+V): in un altro spread nella stessa posizione")}</div></div>` +
    `<div class="box"><i>Vista</i><div class="g4">${B("tmag", "magnet", "Magnete", "Calamita: guide e foto si agganciano a bordi, centri, piega e spaziature uguali (tieni Alt per disattivarla al volo)", magnet ? 'class="on"' : "")}${B("trul", "ruler", "Righelli", "Righelli (R)", showRulers ? 'class="on"' : "")}${B("tgui", "guide", "Guide", "Guide (G): si creano trascinandole dal righello", showGuides ? 'class="on"' : "")}${B("cgui", "clear", "Cancella", "Cancella le guide di questo spread", sp.guides.v.length + sp.guides.h.length ? "" : "disabled")}</div></div>`;
  $("sbarR").innerHTML = (`<div class="box"><i>${msel.length ? sel_lbl : "Selezione"}</i><div class="g4">
      ${B("zfront", "front", "In cima", "Porta in primo piano (Maiusc + ])")}${B("zfw", "up", "Avanti", "Un livello avanti (] oppure +)")}${B("zbw", "down", "Indietro", "Un livello indietro ([ oppure −)")}${B("zback", "back", "In fondo", "Manda in fondo (Maiusc + [)")}</div>
      ${onlyTxt ? "" : `<div class="g3" style="margin-top:6px">${B("msame", "same", "Stessa misura", "Tutte con la stessa larghezza e altezza della foto che hai toccato per ultima", msel.length < 2 ? "disabled" : "")}${B("mar", "photo", "Proporzioni", "Ridà alla cornice le proporzioni della foto originale")}${B("mfull", "full", "Tutta pagina", "La foto occupa tutta la sua pagina")}${B("mver", "vert", "Verticali", "Tutte le cornici selezionate in verticale")}${B("mhor", "horiz", "Orizzontali", "Tutte le cornici selezionate in orizzontale")}</div>`}</div>`);
  if (!msel.length) document.querySelectorAll("#sbarR button").forEach(b => b.disabled = true);
  $("newsp").onclick = e => { const m = $("nmenu"), r = e.currentTarget.getBoundingClientRect(); m.style.display = "block"; m.style.left = Math.max(8, Math.min(r.left, innerWidth - 270)) + "px"; m.style.top = r.bottom + 4 + "px"; e.stopPropagation(); };
  $("mvup").onclick = () => moveSp(cur, cur - 1); $("mvdn").onclick = () => moveSp(cur, cur + 1);
  $("dupsp").onclick = dupSpread;
  $("mvl").onclick = () => go(cur - 1); $("mvr").onclick = () => go(cur + 1);
  $("delsp").onclick = () => { if (confirm("Eliminare lo spread " + (cur + 1) + "? Le foto tornano libere (puoi annullare).")) op({ op: "delete", s: cur }); };
  document.querySelectorAll(".sb [data-mode]").forEach(b => b.onclick = () => { const [side, mode] = b.dataset.mode.split(":"); op({ op: "mode", s: cur, side, mode }); });
  document.querySelectorAll(".sb [data-add]").forEach(b => b.onclick = () => op({ op: "addframe", s: cur, side: b.dataset.add }));
  {
    const z = d => () => op({ op: "zorder", s: cur, ats: mAts(), dir: d });
    $("zfront").onclick = z("front"); $("zfw").onclick = z("forward"); $("zbw").onclick = z("backward"); $("zback").onclick = z("back");
    if (!onlyTxt) { $("msame").onclick = () => op({ op: "equalize", s: cur, ...selOrder() }); $("mar").onclick = () => op({ op: "origar", s: cur, ats: mAts() });
    $("mfull").onclick = () => op({ op: "fullpage", s: cur, ats: mAts() }); $("mver").onclick = () => op({ op: "orient", s: cur, dir: "v", ats: mAts() }); $("mhor").onclick = () => op({ op: "orient", s: cur, dir: "h", ats: mAts() }); }
  }
  document.querySelectorAll(".sb [data-al]").forEach(b => b.onclick = () => op({ op: "align", s: cur, ats: mAts(), mode: b.dataset.al }));
  $("mcopy").onclick = copySel; $("mpaste").onclick = pasteSel;
  $("ttxt").onclick = () => setTextTool(!textTool);
  $("tmag").onclick = () => { magnet = !magnet; try { localStorage.setItem("mag", magnet ? "1" : "0"); } catch (e) {} render(); toast(magnet ? "Magnetico acceso" : "Magnetico spento"); };
  $("trul").onclick = () => setRulers(!showRulers); $("tgui").onclick = () => setGuides(!showGuides);
  $("cgui").onclick = () => op({ op: "guides", s: cur, v: [], h: [] });
}
async function dupSpread() { await op({ op: "dup", s: cur }); cur = cur + 1; sel = null; msel = []; render(); toast("Spread duplicato"); }
let clipSrc = null;
async function copySel() { if (!msel.length) return; try { await api("/api/op", { cid: CID, rev: S.rev, op: "copia", s: cur, ats: mAts() }); clipSrc = cur; toast(msel.length + (msel.length === 1 ? " elemento copiato" : " elementi copiati")); } catch (e) {} }
async function pasteSel() {
  const before = new Set(S.spreads[cur].items.map(kOf)); await op({ op: "incolla", s: cur, scarto: clipSrc === cur });
  const fresh = S.spreads[cur].items.filter(i => !before.has(kOf(i)));
  if (fresh.length) { msel = fresh.map(kOf); const l = fresh[fresh.length - 1]; sel = { s: cur, side: l.side, idx: l.idx }; render(); toast("Incollato"); }
}
async function moveSp(a, b) { if (b < 0 || b >= S.spreads.length || a === b) return; await op({ op: "move", s: a, to: b }); cur = b; sel = null; render(); }
function go(k) { if (k >= 0 && k < S.spreads.length) { cur = k; sel = null; msel = []; render(); } }
const fmt1 = v => (v >= 0 ? "+" : "") + v.toFixed(2);
function cropStyle(it) {
  const [l, t, r, b] = it.box, W = r - l, H = b - t, ratio = it.w / it.h;
  return `width:min(100%,${Math.round(300 * ratio)}px);aspect-ratio:${it.w}/${it.h};background-image:url(/img/thumb/${it.name}?w=500);background-size:${100 / W}% ${100 / H}%;background-position:${W < 1 ? l / (1 - W) * 100 : 0}% ${H < 1 ? t / (1 - H) * 100 : 0}%`;
}
const fams = () => [...new Set(FONTS.map(f => f.fam))];
const cssFont = ps => { const f = FONTS.find(x => x.ps === ps); if (!f) return `font-family:${ps}`; const st = f.sty.toLowerCase(); return `font-family:"${f.fam}";font-weight:${/black|heavy/.test(st) ? 900 : /extra ?bold|ultra/.test(st) ? 800 : /semi ?bold|demi/.test(st) ? 600 : /bold/.test(st) ? 700 : /medium/.test(st) ? 500 : /light|thin/.test(st) ? 300 : 400};font-style:${/italic|oblique/.test(st) ? "italic" : "normal"}`; };
const hex = c => "#" + c.map(v => Math.round(v).toString(16).padStart(2, "0")).join("");
function renderTextSide(it, P) {
  const f = FONTS.find(x => x.ps === it.font) || { fam: it.font, sty: "", ps: it.font }, at = [cur, it.side, it.idx], pt = it.size * 72 / S.ppi;
  const fo = fams().map(n => `<option${n === f.fam ? " selected" : ""}>${n.replace(/</g, "&lt;")}</option>`).join(""), so = FONTS.filter(x => x.fam === f.fam).map(x => `<option value="${x.ps}"${x.ps === it.font ? " selected" : ""}>${x.sty}</option>`).join("");
  P.innerHTML = `<div class="insp"><div class="nm">Livello di testo</div>
    <textarea id="ttx" rows="4" style="width:100%;box-sizing:border-box;resize:vertical;font:inherit;color:var(--text);background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:6px 8px"></textarea>
    <div class="sec">Stile</div>
    <div class="erow"><select id="tstl" style="width:100%"><option value="">${it.stile ? "(scollega)" : "— nessuno —"}</option>${Object.keys(S.stili || {}).map(n => `<option${n === it.stile ? " selected" : ""}>${n.replace(/</g, "&lt;")}</option>`).join("")}</select></div>
    ${it.stile ? `<div class="empty" style="margin:2px 0 4px">Le modifiche a carattere, corpo, colore e allineamento valgono per tutti i testi con lo stile «${it.stile.replace(/</g, "&lt;")}».</div>` : ""}
    <div class="tools"><button id="tstsave">Salva come stile…</button>${it.stile ? `<button id="tstdel" class="danger" title="Elimina lo stile (i testi restano come sono)">Elimina stile</button>` : ""}</div>
    <div class="sec">Carattere</div>
    <div class="erow"><select id="tfam" style="width:100%">${fo}</select></div>
    <div class="erow"><select id="tsty" style="width:100%">${so}</select></div>
    <div class="sl"><b>Corpo:</b><input id="tsz" type="number" min="3" max="400" step="0.5" value="${pt.toFixed(1)}" style="width:70px"><span class="v">pt</span></div>
    <div class="sl"><b>Spaziatura:</b><input id="ttr" type="range" min="-100" max="800" step="5" value="${it.tr}"><span class="v" id="ttrv">${it.tr}</span></div>
    <div class="sec">Paragrafo e colore</div>
    <div class="tools"><span class="seg2"><button id="tal-left" class="${it.al === "left" ? "on" : ""}" title="A sinistra">⇤</button><button id="tal-center" class="${it.al === "center" ? "on" : ""}" title="Centrato">↔</button><button id="tal-right" class="${it.al === "right" ? "on" : ""}" title="A destra">⇥</button></span>
      <input id="tcol" type="color" value="${hex(it.col)}" style="width:44px;height:28px;padding:0;border:none;background:none" title="Colore"></div>
    <div class="empty" style="margin:10px 0">Trascinalo sulla pagina come un livello. Le maniglie cambiano la larghezza (il testo va a capo) e l'altezza.</div>
    <div class="tools"><button id="tdel" class="danger">Elimina il testo</button></div></div>`;
  $("ttx").value = it.tx; const set = o => op({ op: "settext", at, ...o });
  let tm = null; $("ttx").oninput = () => { clearTimeout(tm); tm = setTimeout(() => set({ tx: $("ttx").value || " " }), 500); }; $("ttx").onchange = () => { clearTimeout(tm); set({ tx: $("ttx").value || " " }); };
  $("ttx").onkeydown = e => e.stopPropagation();
  $("tfam").onchange = () => { const st = FONTS.filter(x => x.fam === $("tfam").value), pick = st.find(x => x.sty === f.sty) || st.find(x => /regular|normal|roman|book/i.test(x.sty)) || st[0]; set({ font: pick.ps }); };
  $("tsty").onchange = () => set({ font: $("tsty").value });
  $("tsz").onchange = () => set({ size: +$("tsz").value * S.ppi / 72 }); $("tsz").onkeydown = e => e.stopPropagation();
  const tr = $("ttr"); tr.oninput = () => $("ttrv").textContent = tr.value; tr.onchange = () => set({ tr: +tr.value });
  ["left", "center", "right"].forEach(a => $("tal-" + a).onclick = () => set({ al: a }));
  $("tcol").onchange = () => { const h = $("tcol").value; set({ col: [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)] }); };
  $("tstl").onchange = () => { const v = $("tstl").value; op(v ? { op: "stile_applica", at, nome: v } : { op: "stile_scollega", at }); };
  $("tstsave").onclick = () => { const n = prompt("Nome dello stile (es. Titolo)", it.stile || ""); if (n && n.trim()) op({ op: "stile_salva", at, nome: n.trim() }); };
  if ($("tstdel")) $("tstdel").onclick = () => { if (confirm(`Eliminare lo stile «${it.stile}»? I testi restano come sono.`)) op({ op: "stile_elimina", nome: it.stile }); };
  $("tdel").onclick = () => op({ op: "delframe", at }).then(() => { sel = null; msel = []; render(); });
}

/* ===== Barra del carattere, stile Photoshop: compare sopra il testo scelto ===== */
let fpop = null;
function closeFpop() { if (fpop) { fpop.remove(); fpop = null; } }
function fontPopup(anchor, curFam, pick) {
  closeFpop(); const r = anchor.getBoundingClientRect(); fpop = document.createElement("div"); fpop.id = "fpop";
  fpop.style.cssText = `left:${Math.max(6, Math.min(r.left, innerWidth - 300))}px;top:${Math.min(r.bottom + 4, innerHeight - 380)}px`;
  fpop.innerHTML = `<input placeholder="Cerca un carattere…" id="fq"><div id="fl"></div>`; document.body.appendChild(fpop);
  const all = fams(), draw = q => { $("fl").innerHTML = all.filter(n => n.toLowerCase().includes(q.toLowerCase())).slice(0, 300).map(n => `<div data-f="${n.replace(/"/g, "&quot;")}" class="${n === curFam ? "on" : ""}"><span style="font-family:'${n.replace(/'/g, "")}'">${n.replace(/</g, "&lt;")}</span></div>`).join("") || `<div class="nof">Nessun carattere</div>`; };
  draw(""); $("fq").oninput = () => draw($("fq").value); $("fq").onkeydown = e => { e.stopPropagation(); if (e.key === "Escape") closeFpop(); if (e.key === "Enter") { const f = $("fl").querySelector("[data-f]"); if (f) { pick(f.dataset.f); closeFpop(); } } };
  $("fl").onclick = e => { const d = e.target.closest("[data-f]"); if (d) { pick(d.dataset.f); closeFpop(); } }; $("fq").focus();
  const cu = $("fl").querySelector(".on"); if (cu) cu.scrollIntoView({ block: "center" });
}
document.addEventListener("pointerdown", e => { if (fpop && !e.target.closest("#fpop,#txbar")) closeFpop(); }, true);
const SIZES = [6, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 42, 48, 60, 72, 96, 120, 160, 200];
function renderTextBar(it) {
  const B = $("txbar"); if (!it || !S) { B.style.display = "none"; B.innerHTML = ""; closeFpop(); return; }
  const f = FONTS.find(x => x.ps === it.font) || { fam: it.font, sty: "", ps: it.font }, at = [cur, it.side, it.idx], pt = it.size * 72 / S.ppi, set = o => op({ op: "settext", at, ...o });
  const sts = FONTS.filter(x => x.fam === f.fam), lh = Math.round((it.lh || 1.2) * 100);
  B.innerHTML = `<button id="tb-fam" class="fam" title="Carattere" style="font-family:'${f.fam.replace(/'/g, "")}'">${f.fam.replace(/</g, "&lt;")}<i>▾</i></button>
    <select id="tb-sty" title="Stile (Regular, Bold, Italic…)">${sts.map(x => `<option value="${x.ps}"${x.ps === it.font ? " selected" : ""}>${x.sty}</option>`).join("")}</select>
    <span class="sep"></span><label title="Corpo (pt)"><b>T</b><input id="tb-sz" type="number" min="3" max="400" step="0.5" value="${+pt.toFixed(1)}"></label><select id="tb-szl" title="Corpi comuni"><option value="">▾</option>${SIZES.map(n => `<option>${n}</option>`).join("")}</select>
    <label title="Interlinea (% del corpo)"><b>↕</b><input id="tb-lh" type="number" min="60" max="300" step="5" value="${lh}"><u>%</u></label>
    <label title="Spaziatura tra le lettere"><b>VA</b><input id="tb-tr" type="number" min="-100" max="800" step="5" value="${it.tr}"></label>
    <span class="sep"></span><span class="seg2"><button data-al="left" class="${it.al === "left" ? "on" : ""}" title="A sinistra">⇤</button><button data-al="center" class="${it.al === "center" ? "on" : ""}" title="Centrato">↔</button><button data-al="right" class="${it.al === "right" ? "on" : ""}" title="A destra">⇥</button></span>
    <button id="tb-caps" class="${it.caps ? "on" : ""}" title="Tutto maiuscolo">TT</button><input id="tb-col" type="color" value="${hex(it.col)}" title="Colore">`;
  const wr = $("wrap"), sc = wr.clientWidth / S.W, bx = it.x * sc, by = it.y * sc; B.style.display = "flex";
  const sr = $("stage").getBoundingClientRect(), wl = wr.getBoundingClientRect().left; B.style.left = (Math.max(sr.left + 8, Math.min(wl + bx, sr.right - B.offsetWidth - 14)) - wl) + "px"; B.style.top = (by - B.offsetHeight - 8 < -40 ? by + it.h * sc + 8 : by - B.offsetHeight - 8) + "px";
  B.onpointerdown = e => e.stopPropagation(); B.ondblclick = e => e.stopPropagation(); B.oncontextmenu = e => e.stopPropagation();
  $("tb-fam").onclick = () => fontPopup($("tb-fam"), f.fam, fam => { const st = FONTS.filter(x => x.fam === fam), pk = st.find(x => x.sty === f.sty) || st.find(x => /regular|normal|roman|book/i.test(x.sty)) || st[0]; set({ font: pk.ps }); });
  $("tb-sty").onchange = () => set({ font: $("tb-sty").value });
  $("tb-sz").onchange = () => set({ size: +$("tb-sz").value * S.ppi / 72 }); $("tb-szl").onchange = () => { if ($("tb-szl").value) set({ size: +$("tb-szl").value * S.ppi / 72 }); };
  $("tb-lh").onchange = () => set({ lh: +$("tb-lh").value / 100 }); $("tb-tr").onchange = () => set({ tr: +$("tb-tr").value });
  B.querySelectorAll("[data-al]").forEach(b => b.onclick = () => set({ al: b.dataset.al })); $("tb-caps").onclick = () => set({ caps: !it.caps });
  $("tb-col").onchange = () => { const h = $("tb-col").value; set({ col: [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)] }); };
  B.querySelectorAll("input").forEach(i => i.onkeydown = e => { e.stopPropagation(); if (e.key === "Enter") i.blur(); });
}
function setTextTool(on) { textTool = on; $("wrap").style.cursor = on ? "text" : ""; if ($("ttxt")) $("ttxt").classList.toggle("on", on); if (on) toast("Strumento Testo: clicca o trascina sulla pagina, poi scrivi"); }
function enterEdit(it, selAll = false) {
  const slot = [...document.querySelectorAll("#slots > div.slot")].find(d => d.dataset.at === JSON.stringify([cur, it.side, it.idx])); if (!slot) return;
  const sc = $("wrap").clientWidth / S.W, ta = document.createElement("textarea"); ta.className = "tedit"; ta.value = it.tx;
  ta.style.cssText = `position:absolute;inset:0;width:100%;height:100%;box-sizing:border-box;padding:0;margin:0;resize:none;overflow:hidden;z-index:40;border:1px dashed var(--accent);background:rgba(255,255,255,.9);outline:none;${cssFont(it.font)};font-size:${it.size * sc}px;line-height:${it.lh || 1.2};${it.caps ? 'text-transform:uppercase;' : ''}color:${hex(it.col)};text-align:${it.al};letter-spacing:${it.tr / 1000}em`;
  slot.appendChild(ta); ta.focus(); if (selAll) ta.select(); else ta.setSelectionRange(ta.value.length, ta.value.length); let done = false;
  const commit = () => { if (done) return; done = true; const v = ta.value; ta.remove(); const at = [cur, it.side, it.idx]; if (!v.trim()) op({ op: "delframe", at }).then(() => { sel = null; msel = []; render(); }); else if (v !== it.tx) op({ op: "settext", at, tx: v }); };
  ta.onblur = commit; ta.onkeydown = e => { e.stopPropagation(); if (e.key === "Escape") { e.preventDefault(); commit(); } }; ta.onpointerdown = e => e.stopPropagation(); ta.ondblclick = e => e.stopPropagation();
}
$("wrap").addEventListener("pointerdown", e => {          // strumento Testo: clic o rettangolo sulla pagina crea un nuovo livello di testo
  if (!textTool || e.button !== 0) return; e.preventDefault(); e.stopPropagation();
  const r = $("main").getBoundingClientRect(), x0 = e.clientX, y0 = e.clientY; let box = null, moved = false;
  const mv = ev => { if (!moved && Math.hypot(ev.clientX - x0, ev.clientY - y0) < 6) return; moved = true; if (!box) { box = document.createElement("div"); box.style.cssText = "position:fixed;z-index:40;border:1px dashed var(--accent);pointer-events:none"; document.body.appendChild(box); }
    box.style.left = Math.min(x0, ev.clientX) + "px"; box.style.top = Math.min(y0, ev.clientY) + "px"; box.style.width = Math.abs(ev.clientX - x0) + "px"; box.style.height = Math.abs(ev.clientY - y0) + "px"; };
  const up = async ev => {
    window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); if (box) box.remove(); setTextTool(false);
    const L = Math.min(x0, ev.clientX), T = Math.min(y0, ev.clientY), before = new Set(S.spreads[cur].items.map(kOf));
    await op({ op: "addtext", s: cur, fx: (L - r.left) / r.width, fy: (T - r.top) / r.height, fw: moved ? Math.abs(ev.clientX - x0) / r.width : 0, fh: moved ? Math.abs(ev.clientY - y0) / r.height : 0 });
    const n = S.spreads[cur].items.find(i => !before.has(kOf(i)) && i.kind === "txt"); if (!n) return; sel = { s: cur, side: n.side, idx: n.idx }; msel = [kOf(n)]; render(); enterEdit(n, true);
  };
  window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
}, true);
fetch("/api/fonts").then(r => r.json()).then(d => { FONTS = d.fonts; renderSide(); });
function renderSide() {
  const it = selItem(), P = $("insp"); renderTextBar(it && it.k === "t" && it.kind === "txt" ? it : null);
  if (!it) { P.innerHTML = `<div class="insp"><div class="nm">Nessuna foto</div><div class="empty">Clicca una foto nello spread per vedere le sue impostazioni.<br><br>Puoi scegliere i modelli con <b>▦ Modelli</b> (M) e trascinare le guide dai righelli.</div></div>`; return; }
  if (it.k === "t" && it.kind === "txt") { renderTextSide(it, P); return; }
  if (it.k === "t") {
    P.innerHTML = `<div class="insp"><div class="nm">Testo (titolo)</div><div class="empty" style="margin:6px 0 10px">Questo è il blocco di testo dell'album. Rendilo modificabile come in Photoshop: ogni riga diventa un livello di testo con il suo carattere, corpo e colore, spostabile.</div><div class="tools"><button id="t2x" class="primary">Rendi modificabile</button></div></div>`;
    $("t2x").onclick = async () => { await op({ op: "t2x", at: [cur, it.side, it.idx] }); sel = null; msel = []; render(); }; return;
  }
  const at = [sel.s, sel.side, sel.idx], lowppi = it.ppi < 200;
  P.innerHTML = `<div class="insp"><div class="nm">${it.name}</div>
    <div class="sec">Design</div>
    <div class="pv" style="${cropStyle(it)}"></div>
    <div style="margin-top:12px">
      <div class="sl"><b>Scala:</b><input id="z" type="range" min="1" max="2" step="0.01" value="${it.z}"><span class="v" id="zv">${Math.round(it.z * 100)}%</span><span class="x" id="zx" title="Ripristina">⊗</span></div>
      <div class="sl"><b>Angolo:</b><input id="ang" type="range" min="-15" max="15" step="0.1" value="${it.a}"><span class="v" id="angv">${it.a.toFixed(1)}°</span><span class="x" id="angx" title="Ripristina">⊗</span></div>
      <div class="sl"><b>Esposiz.:</b><input id="evp" type="range" min="-1" max="1" step="0.05" value="${it.evp}"><span class="v" id="evv">${fmt1(it.evp)}</span><span class="x" id="evx" title="Ripristina">⊗</span></div>
    </div>
    <div class="sec">Luce <span class="x" id="tnx" title="Azzera tutto il ritocco di questa foto" style="float:right">⊗ azzera</span></div>
    <div id="rit">${RITG[0].map(ritRow(it)).join("")}</div>
    <div class="sec">Colore</div>
    <div id="rit2">${RITG[1].map(ritRow(it)).join("")}</div>
    <div class="sec">Cornice</div>
    <div class="sl"><b>Bordo:</b><input id="bdw" type="range" min="0" max="20" step="0.5" value="${it.bd ? it.bd[0] : 0}"><span class="v" id="bdv">${it.bd ? it.bd[0] + " mm" : "no"}</span></div>
    <div class="cdots" id="bdc">${[["#ffffff", "bianco"], ["#f3ead8", "crema"], ["#9a9a9a", "grigio"], ["#000000", "nero"]].map(([c, n]) => `<i data-c="${c}" style="--c:${c}" title="Bordo ${n}" class="${it.bd && it.bd[1] === c ? "on" : ""}"></i>`).join("")}</div>
    <div class="sl"><b>Ombra:</b><input id="shw" type="range" min="0" max="100" step="1" value="${it.sh || 0}"><span class="v" id="shv">${it.sh || "no"}</span></div>
    <div class="sec">Etichetta colore</div>
    <div class="cdots" id="cdots">${COLS.map(([k, c]) => `<i data-k="${k}" style="--c:${c}" title="${k}" class="${((S.photos.find(x => x.n === it.name) || {}).col) === k ? "on" : ""}"></i>`).join("")}<i class="nc" data-k="" title="Nessun colore"></i></div>
    <div class="tools"><button id="crop" class="${cropMode ? "on" : ""}" title="Trascina la foto dentro la cornice (doppio clic sulla foto)">Sposta nella cornice</button><button id="bw" class="${it.bw ? "on" : ""}">Bianco e nero</button><button id="togrid" ${!it.free ? "disabled" : ""} title="Porta la cornice sulle celle più vicine della griglia">Alla griglia</button><button id="delf" class="danger" title="La foto torna libera (Canc)">Rimuovi</button></div>
    <div class="sec">Informazioni immagine</div>
    <div class="kv" id="info"><span>Cornice L×A</span><span>${it.cm[0].toFixed(2)}×${it.cm[1].toFixed(2)} cm</span>
      <span>PPI effettivi</span><span class="${lowppi ? "bad" : ""}">${it.ppi}${lowppi ? " · bassi" : ""}</span>
      <span>Dimensioni</span><span>${it.dim[0]}×${it.dim[1]} px</span></div>
    <div class="sec">Utilizzo</div>
    <div class="kv"><span>Usata</span><span>${it.uses} ${it.uses === 1 ? "volta" : "volte"}</span><span>Esposizione totale</span><span>${fmt1(it.ev)} EV</span>${it.crop > 1.25 ? `<span>Ritaglio</span><span class="bad">×${it.crop.toFixed(2)} (forte)</span>` : ""}</div>
  </div>`;
  fetch("/api/info/" + it.name).then(r => r.json()).then(d => {
    const el = $("info"); if (!el || !selItem() || selItem().name !== it.name) return;
    [["Profilo colore", d.profilo], ["Tempo", d.tempo], ["Diaframma", d.diaframma], ["ISO", d.iso], ["Focale", d.focale], ["Data", d.data]].forEach(([k, v]) => { if (v) el.insertAdjacentHTML("beforeend", `<span>${k}</span><span>${v}</span>`); });
  });
  $("crop").onclick = () => setCrop(!cropMode);
  const pv = P.querySelector(".pv"); pv.classList.add("pan"); pv.onpointerdown = e => { if (e.button === 0) startPan(e, it, null); };
  $("bw").onclick = () => op({ op: "set", at, bw: !it.bw });
  $("delf").onclick = () => op({ op: "delframe", at });
  $("togrid").onclick = () => op({ op: "snap", at });
  const z = $("z"); z.oninput = () => $("zv").textContent = Math.round(z.value * 100) + "%"; z.onchange = () => op({ op: "set", at, z: +z.value });
  $("zx").onclick = () => op({ op: "set", at, z: 1 });
  const an = $("ang"); an.oninput = () => $("angv").textContent = (+an.value).toFixed(1) + "°"; an.onchange = () => op({ op: "set", at, a: +an.value });
  $("angx").onclick = () => op({ op: "set", at, a: 0 });
  const e = $("evp"); e.oninput = () => $("evv").textContent = fmt1(+e.value); e.onchange = () => op({ op: "ev", photo: it.name, value: +e.value });
  $("evx").onclick = () => op({ op: "ev", photo: it.name, value: 0 });
  wireRit(it);
  const bcol = () => (it.bd && it.bd[1]) || "#ffffff", bset = (mm, c) => op({ op: "set", at, bd: mm > 0 ? [mm, c] : null });
  $("bdw").oninput = () => $("bdv").textContent = +$("bdw").value ? $("bdw").value + " mm" : "no"; $("bdw").onchange = () => bset(+$("bdw").value, bcol());
  document.querySelectorAll("#bdc i").forEach(d => d.onclick = () => bset(it.bd ? it.bd[0] : 3, d.dataset.c));
  $("shw").oninput = () => $("shv").textContent = +$("shw").value || "no"; $("shw").onchange = () => op({ op: "set", at, sh: +$("shw").value });
  document.querySelectorAll("#cdots i").forEach(d => d.onclick = () => { const cur0 = (S.photos.find(x => x.n === it.name) || {}).col; op({ op: "colore", photos: [it.name], value: d.dataset.k && d.dataset.k !== cur0 ? d.dataset.k : null }); });
}

