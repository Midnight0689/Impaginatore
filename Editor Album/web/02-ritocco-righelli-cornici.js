// ---- ritocco stile Lightroom: luce e colore (si applica all'anteprima, ai JPG/PDF e, come livelli di regolazione, ai PSD)
const RITG = [[["con", "Contrasto"], ["alt", "Alteluci"], ["omb", "Ombre"], ["bia", "Bianchi"], ["ner", "Neri"]], [["tmp", "Temperatura"], ["tnt", "Tinta"], ["vib", "Vibranza"], ["sat", "Saturazione"]]];
const RITBG = { tmp: "linear-gradient(90deg,#3b82f6,#ddd,#f59e0b)", tnt: "linear-gradient(90deg,#22c55e,#ddd,#d946ef)", sat: "linear-gradient(90deg,#888,#e11d48)", vib: "linear-gradient(90deg,#888,#0ea5e9)" };
const ritRow = it => ([k, l]) => { const v = Math.round(((it.rit || {})[k]) || 0); return `<div class="sl rit" data-k="${k}"><b>${l}:</b><input type="range" min="-100" max="100" step="1" value="${v}" ${RITBG[k] ? `style="--rb:${RITBG[k]}"` : ""} title="Doppio clic per azzerare"><span class="v">${v}</span></div>`; };
function wireRit(it) {
  document.querySelectorAll("#insp .sl.rit").forEach(row => {
    const k = row.dataset.k, inp = row.querySelector("input"), lab = row.querySelector(".v");
    inp.oninput = () => { lab.textContent = inp.value; }; inp.onchange = () => op({ op: "rit", photo: it.name, key: k, value: +inp.value });
    inp.ondblclick = () => { inp.value = 0; lab.textContent = "0"; op({ op: "rit", photo: it.name, key: k, value: 0 }); };
  });
  $("tnx").onclick = () => op({ op: "rit", photo: it.name, reset: true });
}

// ---- sposta l'immagine dentro la cornice (trascinando la foto o l'anteprima nel pannello)
function setBg(el, it, l, t) {
  const W = it.box[2] - it.box[0], H = it.box[3] - it.box[1];
  el.style.backgroundImage = `url(/img/thumb/${it.name}?w=900)`; el.style.backgroundSize = `${100 / W}% ${100 / H}%`;
  el.style.backgroundPosition = `${W < 1 ? l / (1 - W) * 100 : 0}% ${H < 1 ? t / (1 - H) * 100 : 0}%`; if (it.bw) el.style.filter = "grayscale(1)";
}
function startPan(e, it, slotEl) {
  e.preventDefault(); e.stopPropagation();
  const pvEl = document.querySelector("#side .pv"), at = [cur, it.side, it.idx];
  const W = it.box[2] - it.box[0], H = it.box[3] - it.box[1], x0 = e.clientX, y0 = e.clientY;
  const el = slotEl || e.currentTarget, r = el.getBoundingClientRect(); let l = it.box[0], t = it.box[1], moved = false;
  const onMove = ev => {
    if (!moved && Math.hypot(ev.clientX - x0, ev.clientY - y0) < 3) return; moved = true;
    l = Math.min(Math.max(it.box[0] - (ev.clientX - x0) / r.width * W, 0), 1 - W); t = Math.min(Math.max(it.box[1] - (ev.clientY - y0) / r.height * H, 0), 1 - H);
    if (slotEl) setBg(slotEl, it, l, t); if (pvEl) setBg(pvEl, it, l, t);
  };
  const onUp = () => {
    window.removeEventListener("pointermove", onMove); window.removeEventListener("pointerup", onUp);
    if (!moved) { sel = { s: cur, side: it.side, idx: it.idx }; render(); return; }
    sel = { s: cur, side: it.side, idx: it.idx }; op(Object.assign({ op: "pan", at, l, t }));
  };
  window.addEventListener("pointermove", onMove); window.addEventListener("pointerup", onUp);
}
function setCrop(on) { cropMode = on; $("hint").textContent = on ? "Ritaglio: trascina la foto per spostare l'immagine dentro la cornice (anche dall'anteprima a destra) · Esc o il bottone per uscire" : HINT; render(); }

// ---- righelli (in cm, come in Photoshop) e linee guida
const HINT = $("hint").textContent;
let showRulers = true, showGuides = true, magnet = true;
try { magnet = localStorage.getItem("mag") !== "0"; showRulers = localStorage.getItem("rul") !== "0"; showGuides = localStorage.getItem("gui") !== "0"; } catch (e) {}
function setRulers(on) { showRulers = on; try { localStorage.setItem("rul", on ? "1" : "0"); } catch (e) {} render(); }
function setGuides(on) { showGuides = on; try { localStorage.setItem("gui", on ? "1" : "0"); } catch (e) {} render(); }
const cmOf = px => px / S.ppi * 2.54;
function drawRulers() {
  $("rwrap").classList.toggle("noruler", !showRulers);
  const wr = $("wrap"), w = wr.clientWidth, h = wr.clientHeight; if (!showRulers || !w || !S) return;
  const dpr = window.devicePixelRatio || 1, pxcm = w / cmOf(S.W);
  const step = [1, 2, 5, 10, 20].find(c => c * pxcm >= 42) || 20, minor = pxcm >= 7;
  const draw = (cv, len, thick, horiz, total) => {
    cv.width = (horiz ? len : thick) * dpr; cv.height = (horiz ? thick : len) * dpr; cv.style.width = (horiz ? len : thick) + "px"; cv.style.height = (horiz ? thick : len) + "px";
    const c = cv.getContext("2d"); c.scale(dpr, dpr); c.fillStyle = STGL ? "#e4e4e7" : "#3b3b3b"; c.fillRect(0, 0, cv.width, cv.height); c.strokeStyle = STGL ? "#6e6e73" : "#9a9a9a"; c.fillStyle = STGL ? "#3a3a3c" : "#c8c8c8"; c.font = "10px -apple-system, Arial"; c.lineWidth = 1;
    for (let cm = 0; cm * pxcm <= total + 1; cm += (minor ? 1 : step)) {
      const p = Math.round(cm * pxcm) + .5, major = cm % step === 0;
      c.beginPath();
      if (horiz) { c.moveTo(p, thick); c.lineTo(p, major ? 6 : 16); } else { c.moveTo(thick, p); c.lineTo(major ? 6 : 16, p); }
      c.stroke();
      if (major) { c.save(); if (horiz) c.fillText(cm, p + 3, 11); else { c.translate(11, p + 3); c.rotate(-Math.PI / 2); c.fillText(cm, 0, 0); } c.restore(); }
    }
  };
  draw($("rh"), w, 22, true, w); draw($("rv"), h, 22, false, h);
}
function renderGuides() {
  const G = $("guides"); G.innerHTML = ""; G.className = showGuides ? "" : "nog"; if (!S) return;
  const g = S.spreads[cur].guides;
  g.v.forEach((x, i) => addGuide("v", x, i)); g.h.forEach((y, i) => addGuide("h", y, i));
}
function addGuide(kind, val, i) {
  const d = document.createElement("div"); d.className = "gl " + kind;
  if (kind === "v") d.style.left = val / S.W * 100 + "%"; else d.style.top = val / S.H * 100 + "%";
  d.title = cmOf(val).toFixed(2) + " cm — trascina per spostare, fuori dallo spread per toglierla";
  d.onpointerdown = e => { e.preventDefault(); e.stopPropagation(); dragGuide(e, kind, i, val); };
  $("guides").appendChild(d);
}
function dragGuide(e, kind, idx, start) {                // idx = -1: nuova guida trascinata dal righello
  const wr = $("wrap"), tip = document.createElement("div"); tip.className = "gtip"; document.body.appendChild(tip);
  const g = S.spreads[cur].guides; let val = start, inside = true, el = null;
  if (idx < 0) { el = document.createElement("div"); el.className = "gl " + kind; $("guides").appendChild(el); }
  else el = $("guides").children[kind === "v" ? idx : g.v.length + idx];
  const SP_ = S.spreads[cur], G_ = SP_.grid, T = [];                       // bersagli magnetici: bordi e centri delle foto, margini, piega, centro pagina
  if (kind === "v") { T.push(G_.L.bx[0], G_.R.bx[1], S.fold, ...G_.L.bx, ...G_.R.bx, (G_.L.bx[0] + G_.L.bx[1]) / 2, (G_.R.bx[0] + G_.R.bx[1]) / 2); SP_.items.forEach(i => T.push(i.x, i.x + i.w, i.x + i.w / 2)); }
  else { T.push(G_.L.by[0], G_.L.by[1], (G_.L.by[0] + G_.L.by[1]) / 2); SP_.items.forEach(i => T.push(i.y, i.y + i.h, i.y + i.h / 2)); }
  const upd = ev => {
    const r = wr.getBoundingClientRect(), k = S.W / r.width;
    val = Math.round((kind === "v" ? ev.clientX - r.left : ev.clientY - r.top) * k);
    let snapped = false; if (magnet && !ev.altKey) { let b = null; for (const t of T) if (Math.abs(val - t) < 9 * k && (b === null || Math.abs(val - t) < Math.abs(val - b))) b = t; if (b !== null) { val = Math.round(b); snapped = true; } }
    el.classList.toggle("snap", snapped);
    inside = ev.clientX >= r.left && ev.clientX <= r.right && ev.clientY >= r.top && ev.clientY <= r.bottom;
    if (kind === "v") el.style.left = val / S.W * 100 + "%"; else el.style.top = val / S.H * 100 + "%";
    tip.style.left = ev.clientX + 12 + "px"; tip.style.top = ev.clientY + 12 + "px"; tip.textContent = inside ? cmOf(val).toFixed(2) + " cm" + (snapped ? "  🧲" : "") : "toglie";
    el.style.opacity = inside ? 1 : .35;
  };
  upd(e);
  const up = () => {
    window.removeEventListener("pointermove", upd); window.removeEventListener("pointerup", up); tip.remove();
    const v = g.v.slice(), h = g.h.slice(), L = kind === "v" ? v : h;
    if (idx >= 0) L.splice(idx, 1);
    if (inside) L.push(val);
    if (idx < 0 && !inside) { render(); return; }
    op({ op: "guides", s: cur, v, h });
  };
  window.addEventListener("pointermove", upd); window.addEventListener("pointerup", up);
}
$("rh").onpointerdown = e => { if (e.button === 0) { if (!showGuides) setGuides(true); dragGuide(e, "h", -1); } };
$("rv").onpointerdown = e => { if (e.button === 0) { if (!showGuides) setGuides(true); dragGuide(e, "v", -1); } };
new ResizeObserver(() => { if (S) { drawRulers(); } }).observe($("wrap"));

let pBar = null;
let PH = (() => { try { return +localStorage.getItem("poolH") || 0; } catch (e) { return 0; } })();
function setPoolH() { let st = document.getElementById("prs"); if (!st) { st = document.createElement("style"); st.id = "prs"; document.head.appendChild(st); } st.textContent = `body:not(.nopool) { --pr: ${PH || PF.sz + 78}px; } #poolrow { --ph: ${PF.sz}px; }`; }
function renderPool() {
  const P = $("poolrow"), PM = new Map(S.photos.map(p => [p.n, p])), freeAll = S.unused.map(n => PM.get(n)).filter(Boolean);
  if (!pBar) pBar = mkBar($("poolbar"), PF, { filters: PFILT, zmin: 50, zmax: 220, onChange: renderPool, onZoom: setPoolH });
  if (!$("poolgrip")) { const gr = document.createElement("div"); gr.id = "poolgrip"; gr.title = "Trascina per alzare o abbassare la galleria (doppio clic: altezza automatica)"; $("pool").prepend(gr);
    gr.ondblclick = () => { PH = 0; try { localStorage.removeItem("poolH"); } catch (e) {} setPoolH(); after(); };
    const after = () => setTimeout(() => { drawRulers(); if (S && view === "album") renderStage(); }, 30);
    gr.onpointerdown = e => { e.preventDefault(); const y0 = e.clientY, h0 = $("pool").getBoundingClientRect().height; gr.setPointerCapture(e.pointerId);
      gr.onpointermove = ev => { PH = Math.round(Math.min(Math.max(h0 + (y0 - ev.clientY), 90), innerHeight * 0.7)); setPoolH(); };
      gr.onpointerup = () => { gr.onpointermove = gr.onpointerup = null; try { localStorage.setItem("poolH", PH); } catch (e) {} after(); }; }; }
  setPoolH(); pBar(freeAll);
  const free = filterList(freeAll, PF), keep = P.scrollTop; P.innerHTML = "";
  const info = document.createElement("div"); info.className = "cap"; info.textContent = `Foto libere: ${free.length}${free.length !== freeAll.length ? " di " + freeAll.length : ""} — non sono in nessuno spread${S.tolte.length ? " · in grigio: tolte apposta" : ""} · passa sopra una foto e premi 1-7 per il colore (0 lo toglie)`; P.appendChild(info);
  if (!free.length) P.insertAdjacentHTML("beforeend", `<span class="empty">${freeAll.length ? "Nessuna foto con questi filtri." : "Nessuna: tutte le foto sono usate."}</span>`);
  free.forEach(f => {
    const n = f.n, im = document.createElement("img"); im.src = `/img/thumb/${n}?w=${PF.sz > 110 ? 480 : 240}`; im.title = n + " · trascinala sulla pagina"; im.draggable = false; im.onpointerdown = e => startPhotoDrag(e, n);
    im.onmouseenter = () => HOV = n; im.onmouseleave = () => { if (HOV === n) HOV = null; }; im.oncontextmenu = e => libMenu(e, f, [n], true);
    if (f.star) im.classList.add("star");
    if (f.col) { im.style.borderBottom = `5px solid ${COLC[f.col]}`; im.title += " · " + f.col; }
    if ((S.mancanti || []).some(x => x.replace(/\.[^.]+$/, "") === n)) { im.classList.add("manca"); im.title = n + " · FILE MANCANTE: l'originale non si trova più"; }
    if (S.tolte.includes(n)) { im.className = "tolta" + (f.star ? " star" : ""); im.title = n + " · tolta apposta: clic per ripristinarla"; im.onclick = () => op({ op: "tolta", photo: n, value: false }); }
    P.appendChild(im);
  });
  P.scrollTop = keep;
}

// ---- cornici: si spostano e si ridimensionano liberamente; si agganciano ai bordi della pagina e delle altre foto (anche col giusto spazio)
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
function eqSpace(self, r, snap, doneX, doneY) {            // spaziatura uguale tra le foto (come le guide intelligenti di Photoshop): ritorna spostamento e segni da disegnare
  const O = S.spreads[cur].items.filter(i => !(i.side === self.side && i.idx === self.idx) && i.k !== "t").map(i => ({ x: i.x, y: i.y, w: i.w, h: i.h })), marks = [], tol = 2.5 * S.W / $("wrap").clientWidth, out = { dx: 0, dy: 0, marks };
  const ov = (a0, a1, b0, b1) => Math.min(a1, b1) - Math.max(a0, b0) > 4;
  for (const ax of ["x", "y"]) {
    const [p, q] = ax === "x" ? ["x", "w"] : ["y", "h"], [pp, qq] = ax === "x" ? ["y", "h"] : ["x", "w"];
    const rel = O.filter(o => ov(o[pp], o[pp] + o[qq], r[pp], r[pp] + r[qq]));
    const left = rel.filter(o => o[p] + o[q] <= r[p] + 1).sort((a, b) => b[p] + b[q] - (a[p] + a[q]))[0], right = rel.filter(o => o[p] >= r[p] + r[q] - 1).sort((a, b) => a[p] - b[p])[0];
    const E = []; for (const a of O) for (const b of O) if (a !== b && b[p] >= a[p] + a[q] + 4 && ov(a[pp], a[pp] + a[qq], b[pp], b[pp] + b[qq])) E.push({ g: b[p] - a[p] - a[q], a, b });
    let pos = r[p], done = ax === "x" ? doneX : doneY;
    const gl = left ? pos - (left[p] + left[q]) : null, gr = right ? right[p] - (pos + r[q]) : null;
    if (snap && !done) {
      if (gl !== null && gr !== null && gl > 0 && gr > 0 && Math.abs(gl - gr) < 2 * tol * 3) pos += (gr - gl) / 2;
      else { let best = null; for (const e of E) { for (const [g, base, sgn] of [[gl, left && left[p] + left[q], 1], [gr, right && right[p] - r[q], -1]]) { if (g === null || g <= 0) continue; const d = Math.abs(g - e.g); if (d < 9 * tol / 2.5 && (best === null || d < best.d)) best = { d, np: sgn > 0 ? base + e.g : base - e.g }; } } if (best) pos = best.np; }
      out[ax === "x" ? "dx" : "dy"] = pos - r[p];
    }
    const R2 = { ...r, [p]: pos }, gl2 = left ? pos - (left[p] + left[q]) : null, gr2 = right ? right[p] - (pos + r[q]) : null;
    const seg = (a, b, g) => { const lo = Math.max(Math.min(a[pp], b[pp]), 0), mid = (Math.max(a[pp], R2[pp]) + Math.min(a[pp] + a[qq], R2[pp] + R2[qq])) / 2; marks.push({ ax, from: g[0], to: g[1], at: mid, g: g[1] - g[0] }); };
    const hasEq = (g1, g2) => g1 !== null && g2 !== null && g1 > 1 && Math.abs(g1 - g2) < tol;
    if (hasEq(gl2, gr2)) { seg(left, R2, [left[p] + left[q], pos]); seg(right, R2, [pos + r[q], right[p]]); }
    else for (const [g, a, from, to] of [[gl2, left, left && left[p] + left[q], pos], [gr2, right, pos + r[q], right && right[p]]]) {
      if (g === null || g <= 1) continue; const m = E.find(e => Math.abs(e.g - g) < tol); if (!m) continue;
      marks.push({ ax, from, to, at: (Math.max(a[pp], R2[pp]) + Math.min(a[pp] + a[qq], R2[pp] + R2[qq])) / 2, g }); marks.push({ ax, from: m.a[p] + m.a[q], to: m.b[p], at: (Math.max(m.a[pp], m.b[pp]) + Math.min(m.a[pp] + m.a[qq], m.b[pp] + m.b[qq])) / 2, g: m.g });
    }
  }
  return out;
}
function drawEq(marks) {
  document.querySelectorAll(".eqm").forEach(x => x.remove());
  marks.forEach(m => { const d = document.createElement("div"); d.className = "eqm " + m.ax;
    if (m.ax === "x") { d.style.left = m.from / S.W * 100 + "%"; d.style.width = (m.to - m.from) / S.W * 100 + "%"; d.style.top = m.at / S.H * 100 + "%"; } else { d.style.top = m.from / S.H * 100 + "%"; d.style.height = (m.to - m.from) / S.H * 100 + "%"; d.style.left = m.at / S.W * 100 + "%"; }
    d.innerHTML = `<b>${cmOf(m.g).toFixed(2)}</b>`; $("slots").appendChild(d); });
}
function startFree(e, it, kind) {
  e.preventDefault(); e.stopPropagation();
  const wasOnly = msel.length === 1 && msel[0] === kOf(it) && !cropMode;
  const k = S.W / $("wrap").clientWidth, gap = S.gap, x0 = e.clientX, y0 = e.clientY, sd = 9 * k, free = e.altKey || !magnet;      // Alt = nessun aggancio
  const ctx = side => {                                  // limiti e bordi di aggancio: la foto può occupare tutto lo spread, anche a cavallo della piega
    const G = S.spreads[cur].grid, g = G[side], [pb0, pb1] = g.bx, [by0, by1] = g.by, bx0 = G.L.bx[0], bx1 = G.R.bx[1], fd = S.fold;
    const tx = { lo: [bx0, fd + gap / 2, fd], hi: [bx1, fd - gap / 2, fd] }, ty = { lo: [by0], hi: [by1] };       // lo = bordo sinistro/alto, hi = destro/basso
    S.spreads[cur].items.filter(i => !(i.side === it.side && i.idx === it.idx)).forEach(o => {
      tx.lo.push(o.x, o.x + o.w + gap); tx.hi.push(o.x + o.w, o.x - gap); if (o.side === side) { ty.lo.push(o.y, o.y + o.h + gap); ty.hi.push(o.y + o.h, o.y - gap); } });
    if (showGuides) { const gg = S.spreads[cur].guides; gg.v.forEach(x => { tx.lo.push(x); tx.hi.push(x); }); gg.h.forEach(y => { ty.lo.push(y); ty.hi.push(y); }); }
    return { bx0, bx1, pb0, pb1, by0, by1, tx, ty };
  };
  const best = (v, ts) => { let b = null; for (const t of ts) if (Math.abs(v - t) < sd && (b === null || Math.abs(v - t) < Math.abs(v - b))) b = t; return b; };
  let eqm = [], side = it.side, c = ctx(side), rect = { x: it.x, y: it.y, w: it.w, h: it.h }, moved = false, ghost = null, guides = [];
  const compute = ev => {
    const dx = (ev.clientX - x0) * k, dy = (ev.clientY - y0) * k; let L = it.x, T = it.y, R = it.x + it.w, B = it.y + it.h; guides = [];
    if (kind === "move") {
      let nx = it.x + dx, ny = it.y + dy;
      side = (nx + it.w / 2) < S.fold ? "L" : "R"; c = ctx(side);                // la pagina è quella dove cade il centro della foto
      const gl = free ? null : best(nx, c.tx.lo), gr = free ? null : best(nx + it.w, c.tx.hi), cxm = free ? null : best(nx + it.w / 2, [(c.pb0 + c.pb1) / 2, S.fold]);      // centro pagina e piega
      const dxe = Math.min(gl === null ? 1e9 : Math.abs(nx - gl), gr === null ? 1e9 : Math.abs(nx + it.w - gr));
      if (cxm !== null && Math.abs(nx + it.w / 2 - cxm) <= dxe) { nx = cxm - it.w / 2; guides.push(["v", cxm]); }
      else if (gl !== null && (gr === null || Math.abs(nx - gl) <= Math.abs(nx + it.w - gr))) { nx = gl; guides.push(["v", gl]); } else if (gr !== null) { nx = gr - it.w; guides.push(["v", gr]); }
      const gt = free ? null : best(ny, c.ty.lo), gb = free ? null : best(ny + it.h, c.ty.hi), cym = free ? null : best(ny + it.h / 2, [(c.by0 + c.by1) / 2]);       // centro verticale della pagina
      const dye = Math.min(gt === null ? 1e9 : Math.abs(ny - gt), gb === null ? 1e9 : Math.abs(ny + it.h - gb));
      if (cym !== null && Math.abs(ny + it.h / 2 - cym) <= dye) { ny = cym - it.h / 2; guides.push(["h", cym]); }
      else if (gt !== null && (gb === null || Math.abs(ny - gt) <= Math.abs(ny + it.h - gb))) { ny = gt; guides.push(["h", gt]); } else if (gb !== null) { ny = gb - it.h; guides.push(["h", gb]); }
      L = clamp(nx, c.bx0, c.bx1 - it.w); T = clamp(ny, c.by0, c.by1 - it.h); R = L + it.w; B = T + it.h;
    } else {
      const minw = (c.pb1 - c.pb0) * 0.03, minh = (c.by1 - c.by0) * 0.03;
      const sx = (v, s2) => { if (free) return v; const t = best(v, c.tx[s2]); if (t !== null) { guides.push(["v", t]); return t; } return v; };
      const sy = (v, s2) => { if (free) return v; const t = best(v, c.ty[s2]); if (t !== null) { guides.push(["h", t]); return t; } return v; };
      if (kind.includes("w")) L = clamp(sx(it.x + dx, "lo"), c.bx0, R - minw);
      if (kind.includes("e")) R = clamp(sx(R + dx, "hi"), L + minw, c.bx1);
      if (kind.includes("n")) T = clamp(sy(it.y + dy, "lo"), c.by0, B - minh);
      if (kind.includes("s")) B = clamp(sy(B + dy, "hi"), T + minh, c.by1);
    }
    let out = { x: L, y: T, w: R - L, h: B - T };
    if (magnet && !free) { const es = eqSpace(it, out, kind === "move", guides.some(g => g[0] === "v"), guides.some(g => g[0] === "h")); if (kind === "move") { out.x = clamp(out.x + es.dx, c.bx0, c.bx1 - out.w); out.y = clamp(out.y + es.dy, c.by0, c.by1 - out.h); } eqm = eqSpace(it, out, false, true, true).marks; } else eqm = [];
    return out;
  };
  const draw = () => {
    if (!ghost) { ghost = document.createElement("div"); ghost.className = "ghost"; if (it.name) { ghost.style.backgroundImage = `url(/img/thumb/${it.name}?w=500)`; ghost.style.backgroundSize = "cover"; ghost.style.backgroundPosition = "center"; ghost.style.opacity = ".88"; } $("slots").appendChild(ghost); }
    ghost.style.left = rect.x / S.W * 100 + "%"; ghost.style.top = rect.y / S.H * 100 + "%"; ghost.style.width = rect.w / S.W * 100 + "%"; ghost.style.height = rect.h / S.H * 100 + "%";
    drawEq(eqm);
    document.querySelectorAll(".guide").forEach(x => x.remove());
    guides.forEach(([t, v]) => { const d = document.createElement("div"); d.className = "guide";
      if (t === "v") { d.style.left = v / S.W * 100 + "%"; d.style.top = 0; d.style.bottom = 0; d.style.width = "1px"; } else { d.style.top = v / S.H * 100 + "%"; d.style.left = 0; d.style.right = 0; d.style.height = "1px"; }
      $("slots").appendChild(d); });
  };
  const onMove = ev => { if (!moved && Math.hypot(ev.clientX - x0, ev.clientY - y0) < 4) return; moved = true; rect = compute(ev); draw(); };
  const onUp = async ev => {
    window.removeEventListener("pointermove", onMove); window.removeEventListener("pointerup", onUp);
    document.querySelectorAll(".guide, .eqm").forEach(x => x.remove());
    const grp = msel.length > 1 && inM(it);
    sel = { s: cur, side: it.side, idx: it.idx }; if (!grp) msel = [kOf(it)];
    if (!moved) { if (wasOnly && kind === "move") { msel = []; sel = null; } else if (grp) msel = [kOf(it)]; render(); return; }
    if (ghost) ghost.remove();
    const f = { x: (rect.x - c.pb0) / (c.pb1 - c.pb0), y: (rect.y - c.by0) / (c.by1 - c.by0), w: rect.w / (c.pb1 - c.pb0), h: rect.h / (c.by1 - c.by0) };
    if (it.k === "t" && it.kind !== "txt") f.ts = kind === "move" ? (it.ts || 1) : (it.ts || 1) * rect.w / it.w;
    if (it.kind === "txt" && kind !== "move" && (kind.includes("n") || kind.includes("s"))) f.autoh = false;
    if (side !== it.side) { await op({ op: "crosspage", at: [cur, it.side, it.idx], to: side, ...f }); const n = S.spreads[cur].items.filter(i => i.side === side).length; sel = { s: cur, side, idx: n - 1 }; render(); }
    else if (grp && kind === "move") op({ op: "nudge", s: cur, ats: mAts(), dx: rect.x - it.x, dy: rect.y - it.y });
    else op({ op: "free", at: [cur, it.side, it.idx], ...f });
  };
  window.addEventListener("pointermove", onMove); window.addEventListener("pointerup", onUp);
}

document.addEventListener("click", () => $("nmenu").style.display = "none");
$("nmenu").onclick = async e => {
  const k = e.target.closest("[data-n]"); if (!k) return; $("nmenu").style.display = "none";
  if (k.dataset.n === "blank") { await op({ op: "blank", pos: cur + 1 }); go(cur + 1); }
  else if (k.dataset.n === "photos") { await op({ op: "new", s: cur }); go(cur + 1); }
  else { view = "foto"; $("wherenew").value = "after"; render(); }
};

