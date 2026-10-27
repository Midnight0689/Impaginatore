// ---- libreria foto: seleziona le foto e compaiono i modelli per quel numero di foto
function mkTile(t, label, onclick) {
  const c = document.createElement("div"); c.className = "tp" + (t.cur ? " cur" : "");
  const pv = document.createElement("div"); pv.className = "pv"; pv.style.paddingTop = (S.H / S.W * 100) + "%";
  t.frames.forEach(f => { const i = document.createElement("i"); i.style.cssText = `left:${f.x / S.W * 100}%;top:${f.y / S.H * 100}%;width:${f.w / S.W * 100}%;height:${f.h / S.H * 100}%;background-image:url(/img/thumb/${f.n}?w=520)`; pv.appendChild(i); });
  pv.appendChild(document.createElement("b")); c.appendChild(pv); c.insertAdjacentHTML("beforeend", `<span>${label}</span>`); c.onclick = onclick; return c;
}
// ---- filtri, colori, ordinamento e zoom: uguali per la galleria Foto e per la striscia «foto libere» dell'album
const COLS = [["rosso", "#ff453a"], ["arancio", "#ff9f0a"], ["giallo", "#ffd60a"], ["verde", "#30d158"], ["azzurro", "#0a84ff"], ["viola", "#bf5af2"], ["rosa", "#ff6bb5"]], COLC = Object.fromEntries(COLS);
const SORTS = [["ord", "Ordine di import"], ["nome", "Nome A→Z"], ["nomeD", "Nome Z→A"], ["data", "Data scatto ↑"], ["dataD", "Data scatto ↓"], ["col", "Per colore"]];
function mkF(key, sz) { let o = {}; try { o = JSON.parse(localStorage.getItem(key) || "{}"); } catch (e) {} return { key, f: o.f || "tutte", o: o.o || "tutte", c: Array.isArray(o.c) ? o.c : [], star: !!o.star, s: o.s || "ord", sz: +o.sz || sz, q: "" }; }
const saveF = st => { try { localStorage.setItem(st.key, JSON.stringify({ f: st.f, o: st.o, c: st.c, star: st.star, s: st.s, sz: st.sz })); } catch (e) {} };
const GF = mkF("galleriaFoto2", 140), PF = mkF("stricciaFoto", 100);
const GFILT = [["tutte", "Tutte"], ["free", "Da usare"], ["used", "Già usate"], ["tolta", "Tolte"], ["manca", "Mancanti"]], PFILT = [["tutte", "Tutte"], ["free", "Da usare"], ["tolta", "Tolte"], ["manca", "Mancanti"]], GORI = [["tutte", "Tutte"], ["v", "Vert."], ["h", "Orizz."]];
const missSet = () => new Set((S.mancanti || []).map(x => x.replace(/\.[^.]+$/, "")));
const gPass = (p, f, M) => f === "tutte" ? true : f === "free" ? p.sp == null && !p.tolta : f === "used" ? p.sp != null : f === "tolta" ? !!p.tolta : M.has(p.n);
function filterList(list, st) {          // list: foto del programma; applica filtro, orientamento, colori, ricerca, ordinamento
  const M = missSet(), q = st.q.trim().toLowerCase(), ix = new Map(S.photos.map((p, i) => [p.n, i]));
  const a = list.filter(p => gPass(p, st.f, M) && (st.o === "tutte" || (st.o === "v" ? p.ar < 1 : p.ar >= 1)) && (!st.c.length || st.c.includes(p.col || "-")) && (!st.star || p.star) && (!q || p.n.toLowerCase().includes(q)));
  const nm = (x, y) => x.n.localeCompare(y.n, undefined, { numeric: true }), cx = p => p.col ? COLS.findIndex(c => c[0] === p.col) : 99;
  const cmp = { ord: (x, y) => ix.get(x.n) - ix.get(y.n), nome: nm, nomeD: (x, y) => nm(y, x), data: (x, y) => (x.dt < y.dt ? -1 : x.dt > y.dt ? 1 : nm(x, y)), dataD: (x, y) => (x.dt < y.dt ? 1 : x.dt > y.dt ? -1 : nm(y, x)), col: (x, y) => cx(x) - cx(y) || ix.get(x.n) - ix.get(y.n) }[st.s] || (() => 0);
  return a.sort(cmp);
}
// barra: filtri, orientamento, colori, ordinamento, ricerca, zoom. cfg = { filters, zmin, zmax, onChange(), onZoom(live), assign() }
function mkBar(el, st, cfg) {
  el.innerHTML = '<div class="seg gF"></div><div class="seg gO"></div><span class="dots gC"></span><select class="gS" title="Ordina per"></select><button class="gst" title="Mostra solo le preferite (★)">★</button><input class="gQ" type="search" placeholder="Cerca nome…"><span class="zoom"><button class="zm" title="Miniature più piccole">−</button><input class="zr" type="range" title="Dimensione miniature"><button class="zp" title="Miniature più grandi">+</button></span>' + (cfg.assign ? '<span class="dots as"><span class="lb">Colora:</span></span>' : "");
  const $q = c => el.querySelector(c), rg = $q(".zr"); rg.min = cfg.zmin; rg.max = cfg.zmax; rg.step = 10;
  $q(".gS").innerHTML = SORTS.map(([k, l]) => `<option value="${k}">${l}</option>`).join(""); $q(".gS").onchange = e => { st.s = e.target.value; saveF(st); cfg.onChange(); };
  $q(".gst").onclick = () => { st.star = !st.star; saveF(st); cfg.onChange(); };
  $q(".gQ").oninput = e => { st.q = e.target.value; cfg.onChange(); }; $q(".gQ").onkeydown = e => e.stopPropagation();
  const zoom = v => { st.sz = Math.max(cfg.zmin, Math.min(cfg.zmax, Math.round(v / 10) * 10)); rg.value = st.sz; saveF(st); cfg.onZoom(); };
  $q(".zm").onclick = () => { zoom(st.sz - 20); cfg.onChange(); }; $q(".zp").onclick = () => { zoom(st.sz + 20); cfg.onChange(); };
  rg.oninput = () => zoom(+rg.value); rg.onchange = () => cfg.onChange();
  if (cfg.assign) { const A = $q(".as"); COLS.forEach(([k, c]) => { const i = document.createElement("i"); i.style.setProperty("--c", c); i.title = "Colora: " + k; i.onclick = () => cfg.assign(k); A.appendChild(i); }); const x = document.createElement("i"); x.className = "nc"; x.title = "Togli il colore"; x.onclick = () => cfg.assign(null); A.appendChild(x); }
  return function refresh(list) {
    const M = missSet(), cnt = f => list.filter(p => gPass(p, f, M)).length;
    const F = $q(".gF"); F.innerHTML = ""; cfg.filters.forEach(([k, l]) => { if (k === "manca" && !cnt(k) && st.f !== k) return; const b = document.createElement("button"); b.className = st.f === k ? "on" : ""; b.innerHTML = `${l}<span class="c">${cnt(k)}</span>`; b.onclick = () => { st.f = k; saveF(st); cfg.onChange(); }; F.appendChild(b); });
    const O = $q(".gO"); O.innerHTML = ""; GORI.forEach(([k, l]) => { const b = document.createElement("button"); b.className = st.o === k ? "on" : ""; b.textContent = l; b.onclick = () => { st.o = k; saveF(st); cfg.onChange(); }; O.appendChild(b); });
    const C = $q(".gC"); C.innerHTML = ""; [...COLS, ["-", ""]].forEach(([k, c]) => { const i = document.createElement("i"); if (k === "-") i.className = "nc"; else i.style.setProperty("--c", c); if (st.c.includes(k)) i.classList.add("on"); i.title = k === "-" ? "Senza colore" : "Mostra solo: " + k; i.onclick = () => { const n = st.c.indexOf(k); if (n >= 0) st.c.splice(n, 1); else st.c.push(k); saveF(st); cfg.onChange(); }; C.appendChild(i); });
    $q(".gst").classList.toggle("on", st.star); $q(".gS").value = st.s; rg.value = st.sz;
  };
}
let HOV = null;                                   // foto sotto il mouse: i tasti 1-7 le danno il colore, 0 lo toglie
function assignColor(v, names) { names = names || (view === "foto" && SELP.length ? SELP : HOV ? [HOV] : []); if (!names.length) { toast("Seleziona prima una o più foto (o passaci sopra col mouse)", true); return; } op({ op: "colore", photos: names.slice(), value: v }); }
// ---- scelta di una foto libera (sostituisci / aggiungi qui)
function pickPhoto(titolo, onPick, withUsed) {
  let d = $("pickd"); if (d) d.remove(); d = document.createElement("div"); d.id = "pickd"; d.className = "veil"; d.style.display = "flex";
  d.innerHTML = `<div class="dlg" style="width:760px"><h3 style="margin:0 0 4px">${titolo}</h3><div style="display:flex;gap:10px;align-items:center"><input id="pkq" type="search" placeholder="Cerca nome…" style="flex:1">${withUsed ? '<label style="cursor:pointer;color:var(--dim)"><input type="checkbox" id="pku"> anche quelle già usate</label>' : ""}</div><div class="grid" id="pkg"></div><div style="text-align:right"><button id="pkc">Annulla</button></div></div>`;
  document.body.appendChild(d);
  const draw = () => { const q = $("pkq").value.trim().toLowerCase(), used = $("pku") && $("pku").checked, g = $("pkg"); g.innerHTML = "";
    S.photos.filter(p => (p.sp == null || used) && !p.tolta && (!q || p.n.toLowerCase().includes(q))).slice(0, 400).forEach(p => { const im = document.createElement("img"); im.loading = "lazy"; im.src = `/img/thumb/${p.n}?w=240`; im.title = p.n + (p.sp != null ? " · in spread " + (p.sp + 1) : ""); im.onclick = () => { d.remove(); onPick(p.n); }; g.appendChild(im); }); };
  $("pkq").oninput = draw; $("pkq").onkeydown = e => { e.stopPropagation(); if (e.key === "Escape") d.remove(); }; if ($("pku")) $("pku").onchange = draw; $("pkc").onclick = () => d.remove(); d.onclick = e => { if (e.target === d) d.remove(); }; draw(); $("pkq").focus();
}
// ---- menu del tasto destro (foto della galleria, della striscia e dello spread)
let RITCLIP = null;
const CTXTOP = 5;                                 // quante voci stanno nel primo livello del menu
function ctxUso() { try { return JSON.parse(localStorage.getItem("ctxUso") || "{}"); } catch (e) { return {}; } }
const ctxId = it => it.id || (it.t || it.label || "").replace(/«.*?»|\(\d+\)|\d+/g, "#").trim();
function ctxMenu(e, items, kind = "x") {
  e.preventDefault(); e.stopPropagation(); const old = $("cmenu"); if (old) old.remove(); document.querySelectorAll(".csub").forEach(x => x.remove());
  items = items.filter(Boolean); const uso = ctxUso(), cnt = uso[kind] || {};
  const isCmd = it => it !== "-" && !it.colors && (it.t || it.chips);
  const bump = it => { const id = ctxId(it); cnt[id] = (cnt[id] || 0) + 1; uso[kind] = cnt; try { localStorage.setItem("ctxUso", JSON.stringify(uso)); } catch (x) {} };
  const close = () => { m.remove(); document.querySelectorAll(".csub").forEach(x => x.remove()); };
  const row = (it, host) => {
    if (it === "-") { host.insertAdjacentHTML("beforeend", "<hr>"); return; }
    if (it.chips) { const r = document.createElement("div"); r.className = "chips"; r.innerHTML = `<span>${it.label}</span>`; it.chips.forEach(([l, f]) => { const b = document.createElement("b"); b.textContent = l; b.onclick = () => { bump(it); close(); f(); }; r.appendChild(b); }); host.appendChild(r); return; }
    if (it.colors) { const r = document.createElement("div"); r.className = "crow"; r.innerHTML = COLS.map(([k, c]) => `<i data-k="${k}" style="--c:${c}" title="${k}"></i>`).join("") + '<i class="nc" data-k="" title="Nessun colore"></i>'; r.onclick = ev => { const d = ev.target.closest("i"); if (d) { assignColor(d.dataset.k || null, it.colors); close(); } }; host.appendChild(r); return; }
    const d = document.createElement("div"); d.className = "mi" + (it.off ? " off" : ""); d.innerHTML = `<span>${it.t}</span>${it.k ? `<kbd>${it.k}</kbd>` : ""}`;
    if (!it.off) d.onclick = () => { bump(it); close(); it.f(); }; host.appendChild(d);
  };
  const m = document.createElement("div"); m.id = "cmenu";
  const cmds = items.filter(isCmd), fixed = items.filter(it => it.colors);
  const ranked = cmds.map((it, k) => ({ it, k, n: cnt[ctxId(it)] || 0 })).filter(x => !x.it.off).sort((a, b) => b.n - a.n || a.k - b.k).slice(0, CTXTOP), top = new Set(ranked.map(x => x.it));
  fixed.forEach(it => row(it, m)); if (fixed.length) m.insertAdjacentHTML("beforeend", "<hr>");
  if (ranked.some(x => x.n > 0)) m.insertAdjacentHTML("beforeend", '<div class="mh">I tuoi comandi più usati</div>'); else m.insertAdjacentHTML("beforeend", '<div class="mh">Suggeriti</div>');
  ranked.forEach(x => row(x.it, m));
  const rest = items.filter(it => !top.has(it) && !(it.colors)); while (rest.length && rest[0] === "-") rest.shift(); while (rest.length && rest[rest.length - 1] === "-") rest.pop();
  const clean = rest.filter((it, k) => !(it === "-" && rest[k - 1] === "-"));
  if (clean.some(isCmd)) {
    m.insertAdjacentHTML("beforeend", "<hr>");
    const all = document.createElement("div"); all.className = "mi sub"; all.innerHTML = "<span>Tutti i comandi</span><kbd>▸</kbd>"; m.appendChild(all);
    let sub = null;
    const open = () => { if (sub) return; sub = document.createElement("div"); sub.className = "csub"; sub.id = "cmenu2"; clean.forEach(it => row(it, sub)); document.body.appendChild(sub);
      const r = all.getBoundingClientRect(); const left = r.right + 4 + sub.offsetWidth < innerWidth ? r.right + 4 : Math.max(6, r.left - sub.offsetWidth - 4);
      sub.style.left = left + "px"; sub.style.top = Math.max(6, Math.min(r.top - 6, innerHeight - sub.offsetHeight - 8)) + "px"; };
    all.onmouseenter = open; all.onclick = open;
    m.onmouseover = ev => { if (sub && !sub.contains(ev.target) && !all.contains(ev.target) && ev.target.closest(".mi,.chips,.crow")) { sub.remove(); sub = null; } };
  }
  document.body.appendChild(m); m.style.left = Math.max(6, Math.min(e.clientX, innerWidth - m.offsetWidth - 8)) + "px"; m.style.top = Math.max(6, Math.min(e.clientY, innerHeight - m.offsetHeight - 8)) + "px";
  setTimeout(() => { const off = ev => { if (!m.contains(ev.target) && !ev.target.closest(".csub")) close(); document.removeEventListener("pointerdown", off, true); }; document.addEventListener("pointerdown", off, true); }, 0);
}
function photoItems(names, where) {          // voci comuni a ogni foto, ovunque sia
  const one = names.length === 1, n0 = names[0], P = S.photos.find(x => x.n === n0) || {};
  const allStar = names.every(n => (S.photos.find(x => x.n === n) || {}).star), sameCol = P.col ? S.photos.filter(x => x.col === P.col && x.n !== n0).map(x => x.n) : [];
  return [{ colors: names }, { id: "stella", t: allStar ? "Togli dalle preferite" : "Segna come preferita", k: "P", f: () => op({ op: "stella", photos: names, value: !allStar }) }, "-",
    { t: "Copia il ritocco", off: !one || !RITCLIPOK(n0), f: () => { RITCLIP = Object.assign({}, RITCLIPSRC(n0)); toast("Ritocco copiato: incollalo su altre foto"); } },
    { t: "Incolla il ritocco" + (names.length > 1 ? " su " + names.length + " foto" : ""), off: !RITCLIP, f: () => op({ op: "rit", photos: names, copia: RITCLIP }).then(() => toast("Ritocco incollato")) },
    { t: "Azzera il ritocco", f: () => op({ op: "rit", photos: names, reset: true }) },
    one && P.col && P.rit && sameCol.length ? { t: `Applica questo ritocco a tutte le «${P.col}» (${sameCol.length})`, f: () => op({ op: "rit", photos: sameCol, copia: P.rit }).then(() => toast("Ritocco applicato a " + sameCol.length + " foto")) } : null, "-",
    { t: "Mostra nel Finder", off: !one, f: () => api("/api/reveal", { foto: n0 }) },
    { t: "Copia il nome", off: !one, f: () => { try { navigator.clipboard.writeText(n0); toast("Nome copiato: " + n0); } catch (x) {} } }];
}
const RITCLIPSRC = n => (S.photos.find(x => x.n === n) || {}).rit || {}; const RITCLIPOK = n => Object.keys(RITCLIPSRC(n)).length > 0;
function libMenu(e, p, names, inPool) {       // galleria o striscia
  const free = p.sp == null, one = names.length === 1;
  ctxMenu(e, [{ colors: names }, "-",
    free && !p.tolta ? { t: "Usa in un nuovo spread…", f: () => { SELP = names.filter(n => { const q = S.photos.find(x => x.n === n); return q && q.sp == null && !q.tolta; }); lastClick = SELP[SELP.length - 1]; view = "foto"; render(); toast("Scegli un modello a destra per creare lo spread"); } } : null,
    !free ? { t: "Vai allo spread " + (p.sp + 1), f: () => { cur = p.sp; view = "album"; render(); } } : null,
    free ? { id: "tolta", t: p.tolta ? "Ripristina (torna tra quelle da usare)" : "Togli dalle foto da usare", f: () => op({ op: "tolta", photo: p.n, value: !p.tolta }) } : null,
    p.col && !inPool ? { t: "Seleziona tutte le " + p.col + "", f: () => { SELP = S.photos.filter(x => x.col === p.col && x.sp == null && !x.tolta).map(x => x.n); lastClick = SELP[SELP.length - 1] || null; view = "foto"; render(); } } : null,
    ...photoItems(names).slice(1)], "lib");
}
function bgMenu(e) {                          // tasto destro su un punto vuoto dello spread
  const r = $("main").getBoundingClientRect(), fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
  ctxMenu(e, [{ t: "Aggiungi una foto qui…", f: () => pickPhoto("Aggiungi una foto libera", n => op({ op: "putfree", s: cur, photo: n, fx, fy })) },
    { t: "Aggiungi testo qui", f: async () => { await op({ op: "addtext", s: cur, fx, fy, fw: 0, tx: "Testo" }); const last = S.spreads[cur].items.filter(i => i.k === "t" && i.kind === "txt").pop(); if (last) { sel = { s: cur, side: last.side, idx: last.idx }; msel = [kOf(last)]; render(); enterEdit(last, true); } } },
    { t: "Incolla", k: "⌘V", off: clipSrc === null, f: pasteSel }, "-",
    { id: "righelli", t: showRulers ? "Nascondi i righelli" : "Mostra i righelli", k: "R", f: () => setRulers(!showRulers) },
    { id: "guide", t: showGuides ? "Nascondi le guide" : "Mostra le guide", k: "G", f: () => setGuides(!showGuides) }, "-",
    { t: "Duplica questo spread", k: "⌘D", f: dupSpread }, { t: "Esporta questo spread come JPG…", f: () => exportOne(cur) }], "bg");
}
function exportOne(k) { openExp(); setFmt("jpg"); document.querySelector("input[name=er][value=r]").checked = true; $("erange").value = String(k + 1); updCount(); }
function spreadMenu(e, k) {                   // tasto destro su una miniatura dello spread
  const n = S.spreads.length;
  ctxMenu(e, [{ t: "Vai allo spread " + (k + 1), f: () => go(k) }, "-",
    { t: "Nuovo spread vuoto dopo", f: async () => { await op({ op: "blank", pos: k + 1 }); cur = k + 1; sel = null; msel = []; render(); } },
    { t: "Duplica", f: async () => { cur = k; await dupSpread(); } },
    { t: "Sposta prima", off: k === 0, f: async () => { cur = k; await moveSp(k, k - 1); } }, { t: "Sposta dopo", off: k === n - 1, f: async () => { cur = k; await moveSp(k, k + 1); } }, "-",
    { t: "Esporta come JPG…", f: () => exportOne(k) }, "-",
    { t: "Elimina lo spread", off: n < 2, f: () => { if (confirm("Eliminare lo spread " + (k + 1) + "? Le foto tornano libere (puoi annullare).")) op({ op: "delete", s: k }); } }], "sp");
}
function frameMenu(e, it) {                   // tasto destro su una foto/testo dello spread
  const k = kOf(it); if (!msel.includes(k)) { sel = { s: cur, side: it.side, idx: it.idx }; msel = [k]; render(); }
  const items = msel.map(x => S.spreads[cur].items.find(i => kOf(i) === x)).filter(Boolean), photos = items.filter(i => i.k !== "t"), names = photos.map(i => i.name), at = mAts(), many = msel.length > 1;
  const z = d => () => op({ op: "zorder", s: cur, ats: at, dir: d });
  const list = [];
  if (photos.length) list.push({ colors: names }, "-");
  list.push({ t: "Porta avanti", k: "+", f: z("forward") }, { t: "Porta indietro", k: "−", f: z("backward") }, { t: "In cima", k: "⇧ ]", f: z("front") }, { t: "In fondo", k: "⇧ [", f: z("back") }, "-");
  list.push({ t: "Centra in orizzontale", f: () => op({ op: "align", s: cur, ats: at, mode: "ch" }) }, { t: "Centra in verticale", f: () => op({ op: "align", s: cur, ats: at, mode: "cv" }) });
  if (photos.length) {
    list.push("-", { t: "Tutta pagina", f: () => op({ op: "fullpage", s: cur, ats: at }) }, { t: "Proporzioni originali", f: () => op({ op: "origar", s: cur, ats: at }) }, { t: "Stessa misura (come l'ultima toccata)", off: !many, f: () => op({ op: "equalize", s: cur, ...selOrder() }) },
      { id: "bn", t: photos.every(i => i.bw) ? "Togli il bianco e nero" : "Bianco e nero", f: async () => { const v = !photos.every(i => i.bw); for (const i of photos) await op({ op: "set", at: [cur, i.side, i.idx], bw: v }); } },
      { t: "Sposta l'immagine nella cornice", off: many, f: () => { sel = { s: cur, side: it.side, idx: it.idx }; setCrop(true); } },
      { label: "Proporzioni", chips: [["1:1", 1], ["3:2", 1.5], ["2:3", 2 / 3], ["4:5", 0.8], ["5:4", 1.25], ["16:9", 16 / 9]].map(([l, r]) => [l, () => op({ op: "ratio", s: cur, ats: at, r })]) },
      { id: "bordo", t: photos.every(i => i.bd) ? "Togli il bordo" : "Aggiungi un bordo bianco", f: async () => { const v = photos.every(i => i.bd) ? null : [3, "#ffffff"]; for (const i of photos) await op({ op: "set", at: [cur, i.side, i.idx], bd: v }); } },
      { id: "ombra", t: photos.every(i => i.sh) ? "Togli l'ombra" : "Aggiungi un'ombra", f: async () => { const v = photos.every(i => i.sh) ? 0 : 40; for (const i of photos) await op({ op: "set", at: [cur, i.side, i.idx], sh: v }); } },
      { t: "Sostituisci con un'altra foto…", off: many, f: () => pickPhoto("Sostituisci " + names[0], n => op({ op: "replace", at: [cur, it.side, it.idx], photo: n }), true) });
    list.push(...photoItems(names).slice(1));
  }
  list.push("-", { t: "Copia", k: "⌘C", f: copySel }, { t: "Incolla", k: "⌘V", f: pasteSel });
  list.push({ id: "togli", t: photos.length ? "Togli dallo spread (la foto torna libera)" : "Elimina", k: "⌫", f: async () => { for (const [a, b] of at.sort((x, y) => y[1] - x[1])) await op({ op: "delframe", at: [cur, a, b] }); msel = []; sel = null; render(); } });
  if (photos.length === 1) list.push({ t: "Mostra nella galleria Foto", f: () => { SELP = [names[0]]; view = "foto"; render(); } });
  ctxMenu(e, list, "frame");
}
const visPhotos = () => filterList(S.photos, GF);
const selectable = () => visPhotos().filter(x => x.sp == null && !x.tolta).map(x => x.n);
let gBar = null;
function renderLib() {
  if (view !== "foto") return;
  const G = $("libgrid"), keep = G.scrollTop; G.innerHTML = "";
  if (!gBar) gBar = mkBar($("libfbar"), GF, { filters: GFILT, zmin: 80, zmax: 360, onChange: renderLib, onZoom: () => G.style.setProperty("--th", GF.sz + "px"), assign: assignColor.bind(null) });
  G.style.setProperty("--th", GF.sz + "px"); gBar(S.photos);
  const VIS = visPhotos(), tw = GF.sz > 200 ? 560 : 300;
  const free = S.photos.filter(p => p.sp == null && !p.tolta).length;
  $("libinfo").textContent = `${S.photos.length} foto · ${free} da usare · ${S.photos.filter(p => p.sp != null).length} già in uno spread`;
  if (!S.photos.length) { G.innerHTML = '<div class="empty" style="grid-column:1/-1;text-align:center;padding:60px 0;line-height:2">Nessuna foto nel progetto.<br>Premi <b>+ Importa cartella…</b> o <b>+ Importa foto…</b> per cominciare.</div>'; }
  else if (!VIS.length) G.innerHTML = '<div class="empty" style="grid-column:1/-1;text-align:center;padding:60px 0">Nessuna foto con questi filtri.</div>';
  const MISS = missSet();
  VIS.forEach(p => {
    const d = document.createElement("div"), k = SELP.indexOf(p.n); d.className = "ph" + (k >= 0 ? " sel" : "") + (p.sp != null ? " used" : "") + (p.tolta ? " tolta" : "") + (MISS.has(p.n) ? " manca" : "");
    d.innerHTML = `${MISS.has(p.n) ? '<span class="mc">⚠ MANCANTE</span>' : ""}<img src="/img/thumb/${p.n}?w=${tw}" title="${p.n} · ${p.dt}">${p.star ? '<span class="st">★</span>' : ""}${p.col ? `<span class="cl" style="background:${COLC[p.col]}" title="${p.col}"></span>` : ""}${k >= 0 ? `<span class="n">${k + 1}</span>` : ""}${p.sp != null ? `<span class="u">spread ${p.sp + 1}</span>` : p.tolta ? '<span class="u">tolta · clic per ripristinare</span>' : `<span class="rm" title="Togli questa foto: non verrà più proposta">✕</span>`}`;
    const rm = d.querySelector(".rm"); if (rm) rm.onclick = ev => { ev.stopPropagation(); SELP = SELP.filter(x => x !== p.n); op({ op: "tolta", photo: p.n, value: true }); };
    d.onmouseenter = () => HOV = p.n; d.onmouseleave = () => { if (HOV === p.n) HOV = null; }; d.oncontextmenu = e => libMenu(e, p, SELP.includes(p.n) ? SELP : [p.n], false);
    d.onclick = e => {
      if (p.sp != null) { cur = p.sp; view = "album"; render(); return; }
      if (p.tolta) { op({ op: "tolta", photo: p.n, value: false }).then(() => toast("Foto ripristinata: torna tra quelle da usare")); return; }
      if (e.shiftKey && lastClick) {                                  // intervallo dalla foto cliccata prima
        const vis = selectable(), a = vis.indexOf(lastClick), b = vis.indexOf(p.n);
        if (a >= 0 && b >= 0) vis.slice(Math.min(a, b), Math.max(a, b) + 1).forEach(n => { if (!SELP.includes(n)) SELP.push(n); });
      } else if (e.metaKey || e.ctrlKey) { if (k >= 0) SELP.splice(k, 1); else SELP.push(p.n); }          // ⌘-clic: aggiunge/toglie questa foto
      else if (k >= 0 && SELP.length === 1) SELP = []; else SELP = [p.n];                                   // clic semplice: solo questa foto
      lastClick = p.n; renderLib();
    };
    G.appendChild(d);
  });
  G.scrollTop = keep;
  clearTimeout(renderLib.t); renderLib.t = setTimeout(loadProposals, 120);
}
let propSeq = 0;
async function loadProposals() {
  const names = SELP.slice(), seq = ++propSeq, L = $("tplist"), cap = $("tplcap");
  $("tplwhere").style.display = names.length ? "" : "none";
  if (!names.length) { cap.innerHTML = "Seleziona le foto per uno spread: qui compaiono i modelli adatti.<br><span style='font-size:12px'>Clic = seleziona · Maiusc+clic = intervallo · l'ordine dei numeri è l'ordine di lettura</span>"; L.innerHTML = ""; return; }
  const d = await api("/api/templates", { photos: names }); if (seq !== propSeq) return;
  cap.innerHTML = d.items.length || (d.utente || []).length ? `<b>${names.length} foto selezionate</b> · ${d.tot + (d.utente || []).length} modelli possibili. Clicca per creare lo spread.` : `<b>${names.length} foto</b>: nessun modello (da 1 a 10 foto per spread).`;
  L.innerHTML = "";
  const mk = (t, lab) => mkTile(t, lab, async () => {
    const pos = $("wherenew").value === "after" && S.spreads.length ? cur + 1 : S.spreads.length;
    await op({ op: "newspread", pos, L: t.L, R: t.R }); SELP = []; lastClick = null; cur = pos; toast("Spread " + (pos + 1) + " aggiunto"); render();
  });
  (d.utente || []).forEach(t => L.appendChild(mk(t, "★ " + t.nome)));
  d.items.slice(0, 40).forEach((t, n) => L.appendChild(mkTile(t, "modello " + (n + 1), async () => {
    const pos = $("wherenew").value === "after" && S.spreads.length ? cur + 1 : S.spreads.length;
    await op({ op: "newspread", pos, L: t.L, R: t.R }); SELP = []; lastClick = null; cur = pos; toast("Spread " + (pos + 1) + " aggiunto"); render();
  })));
}
// ---- titoli dei pulsanti subito (senza attendere quelli lenti del sistema)
(function () {
  const tip = document.createElement("div"); tip.id = "tip"; document.body.appendChild(tip); let t = null, cur1 = null;
  const hide = () => { clearTimeout(t); tip.style.display = "none"; cur1 = null; };
  document.addEventListener("pointerover", e => {
    const el = e.target.closest && e.target.closest("[title],[data-tip]"); if (!el || el === cur1) { if (!el) hide(); return; }
    if (!/^(BUTTON|I|SPAN|LABEL|DIV|CANVAS|INPUT|SELECT)$/.test(el.tagName) || el.closest("#libgrid,#poolrow,#thumbs")) return;
    if (el.title) { el.dataset.tip = el.title; el.removeAttribute("title"); }
    const txt = el.dataset.tip; if (!txt) return;
    cur1 = el; clearTimeout(t); t = setTimeout(() => { tip.textContent = txt; tip.style.display = "block"; const r = el.getBoundingClientRect(); tip.style.left = Math.max(6, Math.min(innerWidth - tip.offsetWidth - 6, r.left + r.width / 2 - tip.offsetWidth / 2)) + "px"; tip.style.top = (r.bottom + 8 + tip.offsetHeight > innerHeight ? r.top - tip.offsetHeight - 8 : r.bottom + 8) + "px"; }, 120);
  });
  document.addEventListener("pointerdown", hide, true); document.addEventListener("pointerleave", hide); document.addEventListener("scroll", hide, true);
})();
