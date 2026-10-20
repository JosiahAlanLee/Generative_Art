(() => {
'use strict';
const E = window.PlateEngine;
const $ = (s, el) => (el || document).querySelector(s);
const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));

/* ------------------------------------------------------------ catalogues */
// Codex Intervallorum sizes come from the engine's CODEX record, read from the book source
const CX = E.CODEX;
const FORMATS = {
  codex: { w: CX.trimMM[0], h: CX.trimMM[1], label: 'Codex Intervallorum · 7 × 10 in' },
  codexSpread: { w: CX.trimMM[0] * 2, h: CX.trimMM[1], label: 'Codex spread · 14 × 10 in', spread: true },
  codexPlot: { w: CX.plotMasterMM.sheet[0], h: CX.plotMasterMM.sheet[1], label: 'Codex plot master · A4', inset: CX.plotMasterMM.inset, noRotate: true },
  '6x9': { w: 152.4, h: 228.6, label: '6 × 9 in · trade' },
  '5.5x8.5': { w: 139.7, h: 215.9, label: '5.5 × 8.5 in · digest' },
  '7x10': { w: 177.8, h: 254, label: '7 × 10 in' },
  '8.5x11': { w: 215.9, h: 279.4, label: '8.5 × 11 in · letter' },
  a5: { w: 148, h: 210, label: 'A5' },
  a4: { w: 210, h: 297, label: 'A4' },
  a3: { w: 297, h: 420, label: 'A3' },
  '8x8': { w: 203.2, h: 203.2, label: '8 × 8 in · square' },
  spread6x9: { w: 304.8, h: 228.6, label: '6 × 9 in spread', spread: true },
};
const SUBJECTS = [['auto', 'Auto'], ['oak', 'Bur oak'], ['pine', 'White pine'], ['grove', 'Oak grove'], ['farmstead', 'Farmstead'], ['watertower', 'Water tower'], ['monument', 'Monument'], ['rock', 'Sandstone tower'], ['sun', 'Great sun'], ['vista', 'Open vista']];
const SEASONS = [['auto', 'Auto'], ['spring', 'Spring'], ['summer', 'Summer'], ['autumn', 'Autumn'], ['winter', 'Winter']];
const TIMES = [['auto', 'Auto'], ['day', 'Day'], ['dusk', 'Dusk'], ['night', 'Night']];
const FRAMES = [['auto', 'Auto'], ['none', 'Full bleed'], ['border', 'Ruled border'], ['arch', 'Arched window'], ['oculus', 'Oculus'], ['arcade', 'Arcade']];
const PEN_LABELS = ['Key', 'Flora', 'Accent', 'Tint'];
const FIRST_SEED = 'e2';

const DEFAULTS = {
  scene: { focal: 'auto', season: 'auto', time: 'auto', frame: 'auto', flora: 60, land: 60, built: 50, sky: 50, density: 100, imperfection: 50 },
  ink: { palette: 'codex', strength: 100, penWidth: 0.35, riso: true },
  page: { format: 'codex', orient: 'portrait', bleed: false, textZone: 'none', zoneMode: 'tint', guides: true },
  out: { optimize: true, paperSvg: false },
};

/* -------------------------------------------------------------- storage */
const store = {
  // v2: the seeding changed in engine 1.1, so plates kept under v1 would not reproduce
  get(k, d) { try { const v = localStorage.getItem('driftless-plates:v2:' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('driftless-plates:v2:' + k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } },
};
const saved = store.get('settings', {}) || {};
const state = {};
for (const g of Object.keys(DEFAULTS)) state[g] = Object.assign({}, DEFAULTS[g], saved[g] || {});
if (!FORMATS[state.page.format]) state.page.format = 'codex';
if (!E.PALETTES[state.ink.palette]) state.ink.palette = DEFAULTS.ink.palette;
const hashSeed = /^#[A-Za-z0-9._~-]{1,40}$/.test(location.hash) ? location.hash.slice(1) : null;
state.seed = hashSeed || store.get('seed', FIRST_SEED);
state.history = [state.seed];
state.hi = 0;
state.zoom = 1;
state.tab = 'scene';
let kept = store.get('kept', []);
if (!Array.isArray(kept)) kept = [];
const persist = () => store.set('settings', { scene: state.scene, ink: state.ink, page: state.page, out: state.out });

function randomSeed() {
  const a = new Uint32Array(1);
  (self.crypto || window.crypto).getRandomValues(a);
  return a[0].toString(16).padStart(8, '0');
}

/* --------------------------------------------------------------- worker */
function workerMain() {
  let last = null;
  const pack = (res) => {
    const pens = [], transfer = [];
    for (let i = 0; i < 4; i++) {
      const paths = res.pens[i];
      let total = 0;
      for (const p of paths) total += p.length;
      const data = new Float32Array(total), starts = new Uint32Array(paths.length + 1);
      let o = 0;
      for (let k = 0; k < paths.length; k++) { starts[k] = o; data.set(paths[k], o); o += paths[k].length; }
      starts[paths.length] = o;
      pens.push({ data, starts }); transfer.push(data.buffer, starts.buffer);
    }
    return { pens, transfer };
  };
  self.onmessage = (e) => {
    const m = e.data;
    try {
      if (m.type === 'gen') {
        const res = PlateEngine.generate(m.params);
        if (m.keep) last = res;
        const { pens, transfer } = pack(res);
        self.postMessage({ id: m.id, ok: true, plate: { W: res.W, H: res.H, seed: res.seed, traits: res.traits, lengths: res.lengths, counts: res.pens.map((p) => p.length), count: res.count, ms: res.ms, params: res.params, pens } }, transfer);
      } else if (m.type === 'svg') {
        if (!last) throw new Error('No plate has been drawn yet.');
        self.postMessage({ id: m.id, ok: true, svg: PlateEngine.toSVG(last, m.opts) });
      }
    } catch (err) {
      self.postMessage({ id: m.id, ok: false, error: String((err && err.message) || err) });
    }
  };
}
let worker = null, lastLocal = null;
try {
  const src = $('#engine').textContent + '\n;(' + workerMain.toString() + ')();';
  worker = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
} catch (e) { worker = null; }

function unpackLocal(res) {
  const pens = res.pens.map((paths) => {
    let total = 0;
    for (const p of paths) total += p.length;
    const data = new Float32Array(total), starts = new Uint32Array(paths.length + 1);
    let o = 0;
    paths.forEach((p, k) => { starts[k] = o; data.set(p, o); o += p.length; });
    starts[paths.length] = o;
    return { data, starts };
  });
  return { W: res.W, H: res.H, seed: res.seed, traits: res.traits, lengths: res.lengths, counts: res.pens.map((p) => p.length), count: res.count, ms: res.ms, params: res.params, pens };
}
function localExec(msg) {
  if (msg.type === 'gen') {
    const res = E.generate(msg.params);
    if (msg.keep) lastLocal = res;
    return { ok: true, plate: unpackLocal(res) };
  }
  if (!lastLocal) throw new Error('No plate has been drawn yet.');
  return { ok: true, svg: E.toSVG(lastLocal, msg.opts) };
}
let jobSeq = 0, busy = false;
const queue = [], pending = new Map();
function run(job) {
  return new Promise((resolve, reject) => {
    job.resolve = resolve; job.reject = reject; job.id = ++jobSeq; job.msg.id = job.id;
    if (job.priority) {
      for (let i = queue.length - 1; i >= 0; i--) if (queue[i].kind === job.kind) { queue[i].reject({ superseded: true }); queue.splice(i, 1); }
      queue.unshift(job);
    } else queue.push(job);
    pump();
  });
}
function cancelKind(kind) {
  for (let i = queue.length - 1; i >= 0; i--) if (queue[i].kind === kind) { queue[i].reject({ superseded: true }); queue.splice(i, 1); }
}
function pump() {
  if (busy || !queue.length) return;
  const job = queue.shift();
  busy = true;
  if (worker) { pending.set(job.id, job); worker.postMessage(job.msg); return; }
  setTimeout(() => {
    try { job.resolve(localExec(job.msg)); } catch (e) { job.reject(e); }
    busy = false; pump();
  }, 20);
}
if (worker) {
  worker.onmessage = (e) => {
    const m = e.data, job = pending.get(m.id);
    pending.delete(m.id); busy = false;
    if (job) { if (m.ok) job.resolve(m); else job.reject(new Error(m.error)); }
    pump();
  };
  worker.onerror = (ev) => {
    if (ev && ev.preventDefault) ev.preventDefault();
    worker = null;
    const stuck = Array.from(pending.values());
    pending.clear(); busy = false;
    for (const j of stuck.reverse()) queue.unshift(j);
    pump();
  };
}

/* --------------------------------------------------------------- params */
function pageSize() {
  const f = FORMATS[state.page.format];
  let w = f.w, h = f.h;
  if (!f.spread && !f.noRotate && state.page.orient === 'landscape' && w < h) { const t = w; w = h; h = t; }
  const bleed = state.page.bleed && !f.inset ? 3.175 : 0;
  return { w, h, bleed, W: w + 2 * bleed, H: h + 2 * bleed, spread: !!f.spread, inset: f.inset || null };
}
function genParams(seed, extra) {
  const s = state.scene, ps = pageSize();
  return Object.assign({
    seed, W: ps.W, H: ps.H, bleed: ps.bleed, spread: ps.spread, inset: ps.inset,
    density: s.density / 100, imperfection: s.imperfection / 100, penWidth: state.ink.penWidth,
    weights: { flora: s.flora / 100, land: s.land / 100, built: s.built / 100, sky: s.sky / 100 },
    focal: s.focal, season: s.season, time: s.time, frame: s.frame,
    textZone: state.page.textZone, zoneMode: state.page.zoneMode,
  }, extra || {});
}

/* -------------------------------------------------------------- drawing */
function lum(hex) { const n = parseInt(hex.slice(1), 16); return (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255; }
function inkSet(p) {
  const pal = E.PALETTES[state.ink.palette] || E.PALETTES.irongall;
  return { pal, inks: E.inkColors(pal, state.ink.strength / 100), mis: state.ink.riso && !p.params.inset ? E.misregistration(p.seed, p.params.imperfection) : null };
}
function drawPlate(ctx, p, scale) {
  const { pal, inks, mis } = inkSet(p);
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = pal.paper;
  ctx.fillRect(0, 0, p.W * scale, p.H * scale);
  ctx.globalCompositeOperation = lum(pal.paper) > 0.45 ? 'multiply' : 'screen';
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  for (const pi of [3, 1, 2, 0]) {
    const pen = p.pens[pi], n = pen.starts.length - 1;
    if (n <= 0) continue;
    const d = pen.data, st = pen.starts;
    ctx.save();
    if (mis) ctx.translate(mis[pi][0] * scale, mis[pi][1] * scale);
    ctx.strokeStyle = inks[pi];
    ctx.lineWidth = Math.max(0.55, state.ink.penWidth * scale);
    ctx.beginPath();
    let c = 0;
    for (let k = 0; k < n; k++) {
      const a = st[k], b = st[k + 1];
      ctx.moveTo(d[a] * scale, d[a + 1] * scale);
      for (let i = a + 2; i < b; i += 2) ctx.lineTo(d[i] * scale, d[i + 1] * scale);
      if (++c === 1500) { ctx.stroke(); ctx.beginPath(); c = 0; }
    }
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
}

function drawGuides(ctx, p, scale) {
  const col = getComputedStyle(document.documentElement).getPropertyValue('--guide').trim() || '#4fb0dd';
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.strokeStyle = col; ctx.lineWidth = 1.2 * (window.devicePixelRatio || 1); ctx.setLineDash([6 * (window.devicePixelRatio || 1), 4 * (window.devicePixelRatio || 1)]);
  const bl = p.params.bleed || 0;
  if (bl) ctx.strokeRect(bl * scale, bl * scale, (p.W - 2 * bl) * scale, (p.H - 2 * bl) * scale);
  if (p.params.spread) { ctx.beginPath(); ctx.moveTo(p.W / 2 * scale, 0); ctx.lineTo(p.W / 2 * scale, p.H * scale); ctx.stroke(); }
  const z = E.textZone(p.params.textZone, p.W, p.H, bl, p.params.spread);
  if (z) for (const q of z.rects) ctx.strokeRect(q.x0 * scale, q.y0 * scale, (q.x1 - q.x0) * scale, (q.y1 - q.y0) * scale);
  const ins = p.params.inset;
  if (ins) ctx.strokeRect(ins[3] * scale, ins[0] * scale, (p.W - ins[1] - ins[3]) * scale, (p.H - ins[0] - ins[2]) * scale);
  ctx.restore();
}

let plate = null;
const canvas = $('#plate'), sheet = $('#sheet'), mat = $('#mat');
function fitSize() {
  const cs = getComputedStyle(mat);
  const availW = Math.max(120, mat.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight));
  const wide = window.matchMedia('(min-width: 900px)').matches;
  const maxH = wide ? Math.max(320, window.innerHeight * 0.74) : Infinity;
  let w = availW, h = (w * plate.H) / plate.W;
  if (h > maxH) { h = maxH; w = (h * plate.W) / plate.H; }
  return { w: Math.floor(w * state.zoom), h: Math.floor(h * state.zoom) };
}
function render() {
  if (!plate) return;
  const { w, h } = fitSize();
  let dpr = window.devicePixelRatio || 1;
  const maxPx = 14e6;
  if (w * h * dpr * dpr > maxPx) dpr = Math.sqrt(maxPx / (w * h));
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  const ctx = canvas.getContext('2d');
  const scale = canvas.width / plate.W;
  drawPlate(ctx, plate, scale);
  if (state.page.guides) drawGuides(ctx, plate, scale);
  drawMarks(w, h);
  mat.style.setProperty('--grid', Math.max(6, (10 * w) / plate.W) + 'px');
}
function drawMarks(w, h) {
  const svg = $('#marks'), o = 16, s = w / plate.W, bl = (plate.params.bleed || 0) * s;
  const xs = [bl, w - bl], ys = [bl, h - bl];
  let m = '';
  for (const x of xs) {
    m += `<line x1="${o + x}" y1="${0}" x2="${o + x}" y2="${o - 4}"/><line x1="${o + x}" y1="${o + h + 4}" x2="${o + x}" y2="${o + h + o}"/>`;
  }
  for (const y of ys) {
    m += `<line x1="0" y1="${o + y}" x2="${o - 4}" y2="${o + y}"/><line x1="${o + w + 4}" y1="${o + y}" x2="${o + w + o}" y2="${o + y}"/>`;
  }
  if (plate.params.spread) m += `<line x1="${o + w / 2}" y1="0" x2="${o + w / 2}" y2="${o - 4}"/><line x1="${o + w / 2}" y1="${o + h + 4}" x2="${o + w / 2}" y2="${o + h + o}"/>`;
  svg.setAttribute('viewBox', `0 0 ${w + 2 * o} ${h + 2 * o}`);
  svg.innerHTML = m;
}

/* ------------------------------------------------------------- generate */
let genSerial = 0, svgCache = null, svgJob = null;
const busyEl = $('#busy');
function setBusy(on) { busyEl.hidden = !on; sheet.classList.toggle('stale', on && !!plate); }
async function generate() {
  const serial = ++genSerial;
  setBusy(true);
  svgCache = null; svgJob = null;
  updateCopyButton();
  try {
    const m = await run({ kind: 'main', priority: true, msg: { type: 'gen', params: genParams(state.seed), keep: true } });
    if (serial !== genSerial) return;
    plate = m.plate;
    render();
    updateMeta();
    if (state.tab === 'export') prepareSvg().catch(() => {});
  } catch (e) {
    if (!(e && e.superseded)) toast('This plate could not be drawn: ' + ((e && e.message) || e));
  } finally {
    if (serial === genSerial) setBusy(false);
  }
}
let regenTimer = 0;
function regen(delay) { clearTimeout(regenTimer); regenTimer = setTimeout(generate, delay ?? 160); }

/* ----------------------------------------------------------------- meta */
const fmtMM = (v) => (Math.round(v * 10) / 10).toString();
function fmtTime(h) {
  const mins = Math.round(h * 60);
  if (mins < 60) return mins + ' min';
  return Math.floor(mins / 60) + ' h ' + String(mins % 60).padStart(2, '0') + ' min';
}
function updateMeta() {
  const p = plate, t = p.traits, ps = pageSize();
  $('#seed').value = p.seed;
  $('#desc').textContent = [t.Subject, t.Season, t.Light, t.Frame].join(' · ');
  $('#matLabel').textContent = `${fmtMM(p.W)} × ${fmtMM(p.H)} mm${ps.bleed ? ' with bleed' : ''} · ${FORMATS[state.page.format].label}`;
  const isKept = kept.some((k) => k.seed === p.seed);
  $('#keep').setAttribute('aria-pressed', String(isKept));
  $('#keep span').textContent = isKept ? 'Kept' : 'Keep';
  const down = p.lengths.reduce((a, b) => a + b, 0), lifts = p.counts.reduce((a, b) => a + b, 0);
  const hours = (down / 25 + lifts * 0.25) / 3600;
  $('#stats').innerHTML = [
    [p.count.toLocaleString(), 'strokes'],
    [(down / 1000).toFixed(1) + ' m', 'of line'],
    ['≈ ' + fmtTime(hours), 'plot at 25 mm/s'],
    [p.ms + ' ms', 'to draw'],
  ].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join('');
  const { inks } = inkSet(p);
  $('#layers').innerHTML = [0, 1, 2, 3].filter((i) => p.counts[i]).map((i) => `<li><i style="background:${inks[i]}"></i><code>${i + 1}-${E.PEN_NAMES[i]}</code> ${PEN_LABELS[i]}<em>${p.counts[i].toLocaleString()} · ${(p.lengths[i] / 1000).toFixed(1)} m</em></li>`).join('');
  $('#traits').innerHTML = Object.entries(t).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('') +
    `<dt>Seed</dt><dd><code>${escapeHtml(p.seed)}</code></dd><dt>Palette</dt><dd>${E.PALETTES[state.ink.palette].name}</dd>`;
  renderKept();
}
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

/* ------------------------------------------------------- seeds & history */
function goSeed(seed, push) {
  state.seed = String(seed).trim().slice(0, 40) || randomSeed();
  if (push !== false) {
    state.history = state.history.slice(0, state.hi + 1);
    state.history.push(state.seed);
    if (state.history.length > 200) state.history.shift();
    state.hi = state.history.length - 1;
  }
  store.set('seed', state.seed);
  regen(0);
}
$('#new').addEventListener('click', () => goSeed(randomSeed()));
$('#prev').addEventListener('click', () => { if (state.hi > 0) { state.hi--; goSeed(state.history[state.hi], false); } else toast('This is the first plate in this session.'); });
$('#next').addEventListener('click', () => {
  if (state.hi < state.history.length - 1) { state.hi++; goSeed(state.history[state.hi], false); } else goSeed(randomSeed());
});
$('#seed').addEventListener('change', (e) => { const v = e.target.value.trim(); if (v && v !== state.seed) goSeed(v); });
$('#seed').addEventListener('keydown', (e) => { if (e.key === 'Enter') e.target.blur(); });

/* ------------------------------------------------------------------ keep */
function renderKept() {
  const box = $('#kept');
  if (!kept.length) { box.hidden = true; box.innerHTML = ''; return; }
  box.hidden = false;
  box.innerHTML = '<span class="kept-label">Kept</span>' + kept.map((k, i) => `<button class="chip${plate && k.seed === plate.seed ? ' on' : ''}" data-i="${i}"><b>${escapeHtml(k.seed)}</b>${escapeHtml(k.title || '')}</button>`).join('');
}
$('#kept').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-i]'); if (!b) return;
  const k = kept[+b.dataset.i]; if (!k) return;
  if (k.cfg) { for (const g of ['scene', 'ink', 'page']) if (k.cfg[g]) state[g] = Object.assign({}, DEFAULTS[g], k.cfg[g]); syncControls(); persist(); }
  goSeed(k.seed);
});
$('#keep').addEventListener('click', () => {
  if (!plate) return;
  const i = kept.findIndex((k) => k.seed === plate.seed);
  if (i >= 0) { kept.splice(i, 1); toast('Removed from kept plates.'); }
  else {
    kept.unshift({ seed: plate.seed, title: plate.traits.Subject, cfg: { scene: state.scene, ink: state.ink, page: state.page } });
    kept = kept.slice(0, 30);
    toast('Kept. It stays in this browser with its settings.');
  }
  store.set('kept', kept);
  updateMeta();
});

/* --------------------------------------------------------- contact sheet */
let sheetSerial = 0;
async function contactSheet() {
  const serial = ++sheetSerial;
  cancelKind('thumb');
  const box = $('#thumbs');
  const n = window.matchMedia('(min-width: 560px)').matches ? 9 : 6;
  const ps = pageSize();
  box.innerHTML = '';
  const seeds = Array.from({ length: n }, randomSeed);
  const cells = seeds.map((seed) => {
    const b = document.createElement('button');
    b.className = 'thumb'; b.dataset.seed = seed;
    b.innerHTML = `<span class="pic" style="--ar:${ps.W} / ${ps.H}"><canvas></canvas></span><span class="t-name"><b>${seed}</b><span>Drawing…</span></span>`;
    box.appendChild(b);
    return b;
  });
  for (let i = 0; i < seeds.length; i++) {
    if (serial !== sheetSerial) return;
    try {
      const m = await run({ kind: 'thumb', msg: { type: 'gen', params: genParams(seeds[i], { density: Math.min(0.8, state.scene.density / 100), cells: 1100 }), keep: false } });
      if (serial !== sheetSerial) return;
      const p = m.plate, cv = cells[i].querySelector('canvas');
      const cssW = cells[i].querySelector('.pic').clientWidth - 16;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.width = Math.max(60, Math.round(cssW * dpr)); cv.height = Math.round(cv.width * p.H / p.W);
      drawPlate(cv.getContext('2d'), p, cv.width / p.W);
      cells[i].querySelector('.t-name span').textContent = p.traits.Subject + ' · ' + p.traits.Season;
    } catch (e) { if (e && e.superseded) return; cells[i].querySelector('.t-name span').textContent = 'Could not draw'; }
  }
}
$('#sheetBtn').addEventListener('click', () => { $('#contact').hidden = false; contactSheet(); $('#contact').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
$('#moreSheet').addEventListener('click', contactSheet);
$('#closeSheet').addEventListener('click', () => { sheetSerial++; cancelKind('thumb'); $('#contact').hidden = true; });
$('#thumbs').addEventListener('click', (e) => {
  const b = e.target.closest('.thumb'); if (!b) return;
  sheetSerial++; cancelKind('thumb');
  $('#contact').hidden = true;
  goSeed(b.dataset.seed);
  mat.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

/* ------------------------------------------------------------------ zoom */
$$('.zoom button').forEach((b) => b.addEventListener('click', () => {
  state.zoom = +b.dataset.zoom;
  $$('.zoom button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
  render();
  if (state.zoom > 1) { mat.scrollLeft = (mat.scrollWidth - mat.clientWidth) / 2; mat.scrollTop = (mat.scrollHeight - mat.clientHeight) / 2; }
}));

/* -------------------------------------------------------------- controls */
function fillSelect(id, items) { $(id).innerHTML = items.map(([v, l]) => `<option value="${v}">${l}</option>`).join(''); }
fillSelect('#focal', SUBJECTS); fillSelect('#season', SEASONS); fillSelect('#time', TIMES); fillSelect('#frame', FRAMES);
fillSelect('#format', Object.entries(FORMATS).map(([k, f]) => [k, f.label]));
$('#palettes').innerHTML = Object.entries(E.PALETTES).map(([k, p]) =>
  `<button class="pal" data-pal="${k}" aria-pressed="false"><span class="chipset" style="background:${p.paper}">${p.inks.map((c) => `<span style="background:${c}"></span>`).join('')}</span><small>${p.name}</small></button>`).join('');

const sceneSelects = ['focal', 'season', 'time', 'frame'];
const sceneSliders = ['flora', 'land', 'built', 'sky', 'density', 'imperfection'];
function syncControls() {
  for (const k of sceneSelects) $('#' + k).value = state.scene[k];
  for (const k of sceneSliders) { $('#' + k).value = state.scene[k]; outFor(k); }
  $('#strength').value = state.ink.strength; outFor('strength');
  $('#penWidth').value = state.ink.penWidth; outFor('penWidth');
  $('#riso').checked = !!state.ink.riso;
  $$('.pal').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.pal === state.ink.palette)));
  $('#format').value = state.page.format;
  segSync('#orient', state.page.orient); segSync('#textZone', state.page.textZone); segSync('#zoneMode', state.page.zoneMode);
  const fm = FORMATS[state.page.format];
  $('#orient').toggleAttribute('data-disabled', !!fm.spread || !!fm.noRotate || fm.w === fm.h);
  $('#bleed').disabled = !!fm.inset;
  $$('#orient button').forEach((b) => { b.disabled = $('#orient').hasAttribute('data-disabled'); });
  $$('#zoneMode button').forEach((b) => { b.disabled = state.page.textZone === 'none'; });
  $('#bleed').checked = !!state.page.bleed;
  $('#guides').checked = !!state.page.guides;
  $('#optimize').checked = !!state.out.optimize;
  $('#paperSvg').checked = !!state.out.paperSvg;
}
function outFor(k) {
  const el = $('#' + k), out = $(`output[for="${k}"]`);
  if (!out) return;
  const v = +el.value;
  out.textContent = k === 'penWidth' ? v.toFixed(2) + ' mm' : (k === 'density' || k === 'strength') ? v + '%' : String(v);
}
function segSync(sel, v) { $$(sel + ' button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === v))); }
for (const k of sceneSelects) $('#' + k).addEventListener('change', (e) => { state.scene[k] = e.target.value; persist(); regen(); });
for (const k of sceneSliders) {
  $('#' + k).addEventListener('input', () => outFor(k));
  $('#' + k).addEventListener('change', (e) => { state.scene[k] = +e.target.value; persist(); regen(); });
}
$('#palettes').addEventListener('click', (e) => {
  const b = e.target.closest('.pal'); if (!b) return;
  state.ink.palette = b.dataset.pal; persist(); syncControls();
  svgCache = null; updateCopyButton();
  render(); if (plate) updateMeta();
  if (state.tab === 'export') prepareSvg().catch(() => {});
});
$('#strength').addEventListener('input', (e) => { state.ink.strength = +e.target.value; outFor('strength'); render(); });
$('#strength').addEventListener('change', () => { persist(); svgCache = null; updateCopyButton(); if (plate) updateMeta(); if (state.tab === 'export') prepareSvg().catch(() => {}); });
$('#penWidth').addEventListener('input', () => outFor('penWidth'));
$('#penWidth').addEventListener('change', (e) => { state.ink.penWidth = +e.target.value; persist(); regen(); });
$('#riso').addEventListener('change', (e) => { state.ink.riso = e.target.checked; persist(); svgCache = null; updateCopyButton(); render(); if (state.tab === 'export') prepareSvg().catch(() => {}); });
$('#format').addEventListener('change', (e) => { state.page.format = e.target.value; persist(); syncControls(); regen(); });
function segBind(sel, key, after) {
  $(sel).addEventListener('click', (e) => {
    const b = e.target.closest('button[data-v]'); if (!b || b.disabled) return;
    state.page[key] = b.dataset.v; persist(); syncControls(); (after || regen)();
  });
}
segBind('#orient', 'orient'); segBind('#textZone', 'textZone'); segBind('#zoneMode', 'zoneMode');
$('#bleed').addEventListener('change', (e) => { state.page.bleed = e.target.checked; persist(); regen(); });
$('#guides').addEventListener('change', (e) => { state.page.guides = e.target.checked; persist(); render(); });
$('#optimize').addEventListener('change', (e) => { state.out.optimize = e.target.checked; persist(); svgCache = null; updateCopyButton(); prepareSvg().catch(() => {}); });
$('#paperSvg').addEventListener('change', (e) => { state.out.paperSvg = e.target.checked; persist(); svgCache = null; updateCopyButton(); prepareSvg().catch(() => {}); });

/* ------------------------------------------------------------------ tabs */
const tabs = $$('.tabs [role="tab"]');
function selectTab(name, focus) {
  state.tab = name;
  for (const t of tabs) {
    const on = t.id === 'tab-' + name;
    t.setAttribute('aria-selected', String(on)); t.tabIndex = on ? 0 : -1;
    $('#' + t.getAttribute('aria-controls')).hidden = !on;
    if (on && focus) t.focus();
  }
  if (name === 'export') prepareSvg().catch(() => {});
}
tabs.forEach((t, i) => {
  t.addEventListener('click', () => selectTab(t.id.slice(4)));
  t.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    const j = (i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length;
    selectTab(tabs[j].id.slice(4), true);
  });
});

/* ---------------------------------------------------------------- export */
let downloads = null, downloadsReady = null;
const inClaude = !!(window.claude && typeof window.claude.use === 'function');
if (inClaude) downloadsReady = window.claude.use('downloads').then((d) => { downloads = d; refreshExportAvailability(); return d; }).catch(() => null);
function refreshExportAvailability() {
  const canSave = !inClaude || !!downloads;
  $('#saveSvg').hidden = !canSave; $('#savePng').hidden = !canSave;
  if (!canSave) $('#exportNote').textContent = 'File downloads are not available in this view. Copy the SVG instead, or open the page in claude.ai.';
}
if (inClaude) { /* wait for the capability before deciding */ } else refreshExportAvailability();

function svgOptions() {
  return {
    palette: state.ink.palette, strength: state.ink.strength / 100, penWidth: state.ink.penWidth,
    background: state.out.paperSvg, optimize: state.out.optimize,
    misregister: state.ink.riso && plate && !plate.params.inset ? E.misregistration(plate.seed, plate.params.imperfection) : null,
  };
}
function prepareSvg() {
  if (!plate) return Promise.reject(new Error('No plate yet.'));
  const key = genSerial + '|' + JSON.stringify(svgOptions());
  if (svgCache && svgCache.key === key) return Promise.resolve(svgCache.svg);
  if (svgJob && svgJob.key === key) return svgJob.p;
  const p = run({ kind: 'svg', msg: { type: 'svg', opts: svgOptions() } }).then((m) => {
    if (key !== genSerial + '|' + JSON.stringify(svgOptions())) return m.svg;
    svgCache = { key, svg: m.svg };
    updateCopyButton();
    return m.svg;
  });
  svgJob = { key, p };
  updateCopyButton();
  return p;
}
function updateCopyButton() {
  const b = $('#copySvg');
  const ready = !!(svgCache && plate && svgCache.key === genSerial + '|' + JSON.stringify(svgOptions()));
  b.disabled = !ready;
  b.textContent = ready ? `Copy SVG (${(svgCache.svg.length / 1e6).toFixed(1)} MB)` : 'Copy SVG';
}
function fileBase() { return `driftless-plate-${plate.seed}-${state.page.format}${state.page.bleed ? '-bleed' : ''}`; }
async function saveFile(filename, data, mime) {
  if (!inClaude) {
    const blob = data instanceof Blob ? data : new Blob([data], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 8000);
    toast('Saved ' + filename);
    return;
  }
  const d = downloads || (downloadsReady && (await downloadsReady));
  if (!d) { toast('Downloads are not available here. Copy the SVG instead.'); return; }
  try {
    await d.save({ filename, data });
    toast('Saved ' + filename);
  } catch (e) {
    const code = e && e.code;
    if (code === 'declined') toast('Download cancelled.');
    else if (code === 'rate_limited') toast('Another save is still waiting for an answer. Try again in a moment.');
    else if (code === 'too_large') toast('That file is too large to save here. Try a smaller trim size or lower density.');
    else toast('The file could not be saved here' + (e && e.message ? ': ' + e.message : '.'));
  }
}
$('#saveSvg').addEventListener('click', async () => {
  if (!plate) return;
  const b = $('#saveSvg'); b.disabled = true; b.textContent = 'Preparing SVG…';
  try { const svg = await prepareSvg(); await saveFile(fileBase() + '.svg', svg, 'image/svg+xml'); }
  catch (e) { if (!(e && e.superseded)) toast('The SVG could not be built: ' + ((e && e.message) || e)); }
  finally { b.disabled = false; b.textContent = 'Download SVG'; }
});
$('#copySvg').addEventListener('click', () => {
  if (!svgCache) return;
  const text = svgCache.svg;
  const fallback = () => {
    const ta = document.createElement('textarea');
    ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    ta.remove();
    toast(ok ? 'SVG copied.' : 'Copy is blocked in this view.');
  };
  try {
    navigator.clipboard.writeText(text).then(() => toast('SVG copied.'), fallback);
  } catch (e) { fallback(); }
});
function crc32(buf) {
  let c, crc = 0xffffffff;
  for (let n = 0; n < buf.length; n++) {
    c = (crc ^ buf[n]) & 0xff;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    crc = (crc >>> 8) ^ c;
  }
  return (crc ^ 0xffffffff) >>> 0;
}
async function withDpi(blob, dpi) {
  const src = new Uint8Array(await blob.arrayBuffer());
  const ppm = Math.round(dpi / 0.0254);
  const chunk = new Uint8Array(21);
  const dv = new DataView(chunk.buffer);
  dv.setUint32(0, 9);
  chunk.set([0x70, 0x48, 0x59, 0x73], 4);
  dv.setUint32(8, ppm); dv.setUint32(12, ppm); chunk[16] = 1;
  dv.setUint32(17, crc32(chunk.subarray(4, 17)));
  const out = new Uint8Array(src.length + 21);
  out.set(src.subarray(0, 33), 0); out.set(chunk, 33); out.set(src.subarray(33), 54);
  return new Blob([out], { type: 'image/png' });
}
$('#savePng').addEventListener('click', async () => {
  if (!plate) return;
  const b = $('#savePng'); b.disabled = true; b.textContent = 'Rendering PNG…';
  try {
    let dpi = 300;
    const px = (v) => Math.round((v / 25.4) * dpi);
    while (px(plate.W) * px(plate.H) > 26e6 && dpi > 120) dpi -= 25;
    const c = document.createElement('canvas');
    c.width = px(plate.W); c.height = px(plate.H);
    drawPlate(c.getContext('2d'), plate, c.width / plate.W);
    const blob = await new Promise((res, rej) => c.toBlob((x) => (x ? res(x) : rej(new Error('PNG encoding failed.'))), 'image/png'));
    await saveFile(`${fileBase()}-${dpi}dpi.png`, await withDpi(blob, dpi), 'image/png');
  } catch (e) { toast('The PNG could not be rendered: ' + ((e && e.message) || e)); }
  finally { b.disabled = false; b.textContent = 'Download PNG'; }
});

/* ----------------------------------------------------------------- toast */
let toastTimer = 0;
function toast(msg) {
  const t = $('#toast');
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 2800);
}

/* ------------------------------------------------------------------ boot */
let resizeTimer = 0, lastW = window.innerWidth;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (Math.abs(window.innerWidth - lastW) > 2 || state.zoom === 1) { lastW = window.innerWidth; render(); } }, 120);
});
syncControls();
selectTab('scene');
generate();
})();
