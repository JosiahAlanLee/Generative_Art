/* Renderers for NodeLattice scenes: an illuminated colour render in the palette of the
   raster references, and stroke-only plot strokes that follow the plot-master conventions
   (millimetres, every mark a pen stroke, dots as coils, fills as hatching). */
const LatticeRender = (() => {
  'use strict';
  const NL = typeof NodeLattice !== 'undefined' ? NodeLattice : require('./lattice.js');
  const { COL, PW, PH, TAU, clamp, ellipsePts, rngFor } = NL;
  const MM = 0.18, OX = 15, OY = 13.5; // 1000 x 1500 units -> 180 x 270 mm on A4, 15 / 13.5 mm margins
  const PEN = { ink: COL.ink, slate: COL.slate, ochre: '#a87a36', red: COL.red };

  function ellPath(ctx, h, grow) {
    const a = Math.max(0.1, h.a + grow), b = Math.max(0.1, h.b + grow);
    ctx.moveTo(h.x + a * Math.cos(h.ang), h.y + a * Math.sin(h.ang));
    ctx.ellipse(h.x, h.y, a, b, h.ang, 0, TAU);
  }
  function circPath(ctx, c, grow) { const r = Math.max(0.1, c.r + grow); ctx.moveTo(c.x + r, c.y); ctx.arc(c.x, c.y, r, 0, TAU); }
  function polyPath(ctx, pts) { ctx.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]); ctx.closePath(); }
  function collarOf(h) { return h.style === 'void' ? Math.max(3, h.b * 0.13) : Math.max(2.6, Math.min(h.a, h.b) * 0.13); }
  function catmull(pts, per) {
    if (pts.length < 3) return pts.slice();
    const out = [pts[0]];
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
      for (let k = 1; k <= per; k++) {
        const t = k / per, t2 = t * t, t3 = t2 * t;
        out.push([0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
          0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)]);
      }
    }
    return out;
  }
  function sagPts(L, n) {
    const mx = L.cx, my = L.cy, out = [];
    for (let i = 0; i <= n; i++) { const t = i / n, u = 1 - t; out.push([u * u * L.x1 + 2 * u * t * mx + t * t * L.x2, u * u * L.y1 + 2 * u * t * my + t * t * L.y2]); }
    return out;
  }
  function tendrilPts(t) { return catmull(t.pts, 6); }

  // ------------------------------------------------------------- illuminated
  function illuminate(ctx, sc, k) {
    ctx.save();
    ctx.setTransform(k, 0, 0, k, 0, 0);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    paper(ctx, sc.seed);
    const g = sc.ground;
    if (g) ring(ctx, g, Math.PI, TAU);

    // hanging lines and the node web sit behind the membrane
    ctx.strokeStyle = COL.ink;
    ctx.lineWidth = 0.95;
    ctx.beginPath();
    for (const d of sc.drips) { ctx.moveTo(d.x, d.y1); ctx.lineTo(d.x, d.y2); }
    ctx.stroke();
    ctx.beginPath();
    for (const t of sc.tendrils) { const p = tendrilPts(t); ctx.moveTo(p[0][0], p[0][1]); for (let i = 1; i < p.length; i++) ctx.lineTo(p[i][0], p[i][1]); }
    for (const L of sc.links) { ctx.moveTo(L.x1, L.y1); ctx.quadraticCurveTo(L.cx, L.cy, L.x2, L.y2); }
    ctx.lineWidth = 1.05; ctx.stroke();

    // membrane: ink outline under an ochre fill
    const mem = new Path2D();
    for (const poly of sc.material) polyPath(mem, poly);
    ctx.lineWidth = 2.7; ctx.strokeStyle = COL.ink; ctx.stroke(mem);
    const grad = ctx.createLinearGradient(0, 120, 0, 1400);
    grad.addColorStop(0, '#c4954e'); grad.addColorStop(0.5, '#b78741'); grad.addColorStop(1, '#a67535');
    ctx.fillStyle = grad; ctx.fill(mem);
    ctx.save(); ctx.clip(mem);
    ctx.strokeStyle = 'rgba(92, 58, 18, 0.2)'; ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (let t = -PH; t < PW + PH; t += 2.4) { ctx.moveTo(t, 0); ctx.lineTo(t - PH * 0.58, PH); }
    ctx.stroke();
    // ridge light along the ribs
    ctx.beginPath();
    for (const r of sc.ribs) { ctx.moveTo(r[0][0], r[0][1]); for (let i = 1; i < r.length; i++) ctx.lineTo(r[i][0], r[i][1]); }
    ctx.lineWidth = 1.1; ctx.strokeStyle = 'rgba(244, 214, 150, 0.42)'; ctx.stroke();
    ctx.restore();

    // bevel: darken the material toward every opening
    const opens = new Path2D();
    for (const pn of sc.panes) polyPath(opens, pn.pts);
    for (const h of sc.holes) ellPath(opens, h, 0);
    for (const h of sc.froth) ellPath(opens, h, 0);
    ctx.lineWidth = 3.6; ctx.strokeStyle = 'rgba(86, 50, 12, 0.4)'; ctx.stroke(opens);

    // panes
    for (const pn of sc.panes) drawPane(ctx, pn);
    // net holes
    const cream = new Path2D();
    for (const h of sc.holes) if (h.style === 'cream') ellPath(cream, h, 0);
    for (const h of sc.froth) if (h.style === 'cream') ellPath(cream, h, 0);
    ctx.fillStyle = COL.paper; ctx.fill(cream);
    ctx.save(); ctx.clip(cream);
    const shade = new Path2D();
    for (const h of sc.holes) if (h.style === 'cream' && Math.min(h.a, h.b) > 4) { shade.moveTo(h.x + h.a * Math.cos(h.ang), h.y + 1.6 + h.a * Math.sin(h.ang)); shade.ellipse(h.x, h.y + 1.6, h.a, h.b, h.ang, 0, TAU); }
    ctx.lineWidth = 2.6; ctx.strokeStyle = 'rgba(70, 48, 22, 0.2)'; ctx.stroke(shade);
    ctx.restore();
    for (const h of sc.holes) {
      if (h.style === 'slate') fillGrad(ctx, (c) => ellPath(c, h, 0), h.x, h.y, Math.max(h.a, h.b), SLATE);
      else if (h.style === 'dark') fillGrad(ctx, (c) => ellPath(c, h, 0), h.x, h.y, Math.max(h.a, h.b), DARK);
      else if (h.style === 'void') fillGrad(ctx, (c) => ellPath(c, h, -collarOf(h)), h.x, h.y, Math.max(h.a, h.b), VOID);
      else if (h.style === 'seal') { ctx.beginPath(); ellPath(ctx, h, -collarOf(h)); ctx.fillStyle = COL.paper; ctx.fill(); }
    }
    for (const h of sc.froth) if (h.style === 'dark') fillGrad(ctx, (c) => ellPath(c, h, 0), h.x, h.y, Math.max(h.a, h.b), DARK);
    for (const h of sc.holes) {
      if (!h.fixed) continue;
      const c = collarOf(h);
      ctx.beginPath(); ellPath(ctx, h, 0); ellPath(ctx, h, -c);
      ctx.fillStyle = '#c0914a'; ctx.fill('evenodd');
    }

    // ink outlines
    ctx.strokeStyle = COL.ink;
    const outl = new Path2D();
    for (const pn of sc.panes) polyPath(outl, pn.pts);
    for (const h of sc.holes) ellPath(outl, h, 0);
    ctx.lineWidth = 1.2; ctx.stroke(outl);
    const thin = new Path2D();
    for (const h of sc.froth) ellPath(thin, h, 0);
    for (const h of sc.holes) if (h.fixed) ellPath(thin, h, -collarOf(h));
    ctx.lineWidth = 0.9; ctx.stroke(thin);
    for (const h of sc.holes) if (h.style === 'seal') {
      const r0 = (Math.min(h.a, h.b) - collarOf(h)) * 0.6, R = rngFor(sc.seed, 'seal'), gap = R() * TAU;
      ctx.beginPath(); ctx.arc(h.x, h.y, r0, gap + 0.5, gap + TAU - 0.5);
      ctx.lineWidth = Math.max(2, r0 * 0.16); ctx.strokeStyle = COL.red; ctx.stroke();
    }

    // dots
    const dots = new Path2D(), gloss = new Path2D();
    const dot = (x, y, r) => { dots.moveTo(x + r, y); dots.arc(x, y, r, 0, TAU); if (r >= 2.4) { const s = r * 0.26; gloss.moveTo(x - r * 0.32 + s, y - r * 0.34); gloss.arc(x - r * 0.32, y - r * 0.34, s, 0, TAU); } };
    for (const b of sc.beads) dot(b.x, b.y, b.r);
    for (const b of sc.webBeads) dot(b.x, b.y, b.r);
    for (const t of sc.terminals) dot(t.x, t.y, t.r);
    for (const d of sc.drips) { dot(d.x, d.y2, d.r); for (const b of d.beads) dot(d.x, d.y1 + (d.y2 - d.y1) * b.t, b.r); }
    ctx.fillStyle = COL.ink; ctx.fill(dots);
    ctx.fillStyle = 'rgba(235, 228, 210, 0.5)'; ctx.fill(gloss);
    for (const p of sc.pearls) {
      const gr = ctx.createRadialGradient(p.x - p.r * 0.35, p.y - p.r * 0.4, p.r * 0.1, p.x, p.y, p.r);
      gr.addColorStop(0, '#e6e8e2'); gr.addColorStop(0.45, '#8e9998'); gr.addColorStop(1, '#3a4345');
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, TAU); ctx.fillStyle = gr; ctx.fill();
      ctx.lineWidth = 0.9; ctx.strokeStyle = COL.ink; ctx.stroke();
    }
    if (g) ring(ctx, g, 0, Math.PI);
    ctx.restore();
  }
  const SLATE = ['#89a2a8', '#557782', '#2f454e'], DARK = ['#4b4741', '#1e1f1d', '#0f100f'], VOID = ['#2c2925', '#141514', '#0b0c0b'];
  function fillGrad(ctx, pathFn, x, y, r, cols) {
    const gr = ctx.createRadialGradient(x - r * 0.18, y - r * 0.28, r * 0.05, x, y, r * 1.05);
    gr.addColorStop(0, cols[0]); gr.addColorStop(0.55, cols[1]); gr.addColorStop(1, cols[2]);
    ctx.beginPath(); pathFn(ctx); ctx.fillStyle = gr; ctx.fill();
  }
  function drawPane(ctx, pn) {
    let r = 0; for (const q of pn.pts) r = Math.max(r, Math.hypot(q[0] - pn.x, q[1] - pn.y));
    const path = (c) => polyPath(c, pn.pts);
    if (pn.type === 'slate') fillGrad(ctx, path, pn.x, pn.y, r, SLATE);
    else if (pn.type === 'dark') fillGrad(ctx, path, pn.x, pn.y, r, DARK);
    else if (pn.type === 'pod') fillGrad(ctx, path, pn.x, pn.y, r, ['#e6d5ab', '#d7bf8e', '#c3a46c']);
    else { ctx.beginPath(); path(ctx); ctx.fillStyle = COL.paper; ctx.fill(); }
    ctx.save(); ctx.beginPath(); path(ctx); ctx.clip();
    if (pn.type === 'slate' || pn.type === 'dark') {
      ctx.beginPath();
      for (const v of pn.veins) { ctx.moveTo(v[0][0], v[0][1]); for (let i = 1; i < v.length; i++) ctx.lineTo(v[i][0], v[i][1]); }
      ctx.lineWidth = 0.75; ctx.strokeStyle = pn.type === 'slate' ? 'rgba(214, 222, 214, 0.55)' : 'rgba(150, 140, 120, 0.45)'; ctx.stroke();
      if (pn.type === 'dark') {
        ctx.beginPath();
        for (let x = pn.x - r; x < pn.x + r; x += 2.2) { ctx.moveTo(x, pn.y - r); ctx.lineTo(x + r * 0.15, pn.y + r); }
        ctx.lineWidth = 0.45; ctx.strokeStyle = 'rgba(0, 0, 0, 0.35)'; ctx.stroke();
      }
    } else if (pn.type === 'lace') {
      ctx.beginPath();
      for (const s of pn.lace) { ctx.moveTo(s[0][0], s[0][1]); ctx.lineTo(s[1][0], s[1][1]); }
      ctx.lineWidth = 0.6; ctx.strokeStyle = 'rgba(40, 30, 18, 0.72)'; ctx.stroke();
    } else if (pn.type === 'open') {
      ctx.beginPath(); path(ctx); ctx.translate(0, 2); ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(70, 48, 22, 0.18)'; ctx.stroke();
    } else if (pn.type === 'pod') {
      ctx.beginPath();
      for (let t = -r * 2; t < r * 2; t += 2.4) { ctx.moveTo(pn.x + t - r, pn.y - r); ctx.lineTo(pn.x + t + r * 0.6, pn.y + r); }
      ctx.lineWidth = 0.4; ctx.strokeStyle = 'rgba(120, 84, 34, 0.18)'; ctx.stroke();
    }
    ctx.restore();
    for (const c of pn.circles) {
      const col = Math.max(1.4, c.r * 0.14);
      if (c.r > 3.5) { ctx.beginPath(); circPath(ctx, c, 0); ctx.fillStyle = '#bd8e47'; ctx.fill(); }
      const inner = c.r > 3.5 ? -col : 0;
      if (c.style === 'slate' || c.style === 'rose') fillGrad(ctx, (q) => circPath(q, c, inner), c.x, c.y, c.r, SLATE);
      else if (c.style === 'dark') fillGrad(ctx, (q) => circPath(q, c, inner), c.x, c.y, c.r, DARK);
      else { ctx.beginPath(); circPath(ctx, c, inner); ctx.fillStyle = COL.paper; ctx.fill(); }
      if (c.style === 'rose') tracery(ctx, c, col);
      ctx.beginPath(); circPath(ctx, c, 0); ctx.lineWidth = 1.0; ctx.strokeStyle = COL.ink; ctx.stroke();
      if (inner) { ctx.beginPath(); circPath(ctx, c, inner); ctx.lineWidth = 0.7; ctx.stroke(); }
    }
    for (const d of pn.dots) {
      ctx.beginPath(); circPath(ctx, d, 0);
      ctx.fillStyle = d.style === 'dark' ? COL.ink : COL.paper; ctx.fill();
      if (d.style !== 'dark') { ctx.lineWidth = 0.7; ctx.strokeStyle = COL.ink; ctx.stroke(); }
    }
  }
  function tracery(ctx, c, col) {
    const a = c.r - col, n = c.spokes || 12;
    ctx.save();
    ctx.beginPath(); ctx.arc(c.x, c.y, a, 0, TAU); ctx.clip();
    ctx.lineWidth = Math.max(0.6, a * 0.03); ctx.strokeStyle = 'rgba(222, 204, 160, 0.8)';
    ctx.beginPath();
    for (let i = 0; i < n; i++) { const t = i / n * TAU; ctx.moveTo(c.x + a * 0.15 * Math.cos(t), c.y + a * 0.15 * Math.sin(t)); ctx.lineTo(c.x + a * Math.cos(t), c.y + a * Math.sin(t)); }
    ctx.stroke();
    ctx.beginPath(); ctx.arc(c.x, c.y, a * 0.56, 0, TAU); ctx.stroke();
    ctx.lineWidth = Math.max(0.5, a * 0.02); ctx.strokeStyle = 'rgba(16, 20, 20, 0.55)';
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const t0 = i / n * TAU, t1 = (i + 1) / n * TAU, tm = (t0 + t1) / 2;
      ctx.moveTo(c.x + a * 0.56 * Math.cos(t0), c.y + a * 0.56 * Math.sin(t0));
      ctx.quadraticCurveTo(c.x + a * 0.95 * Math.cos(tm), c.y + a * 0.95 * Math.sin(tm), c.x + a * 0.56 * Math.cos(t1), c.y + a * 0.56 * Math.sin(t1));
    }
    ctx.stroke();
    ctx.restore();
    ctx.beginPath(); ctx.arc(c.x, c.y, a * 0.15, 0, TAU); ctx.fillStyle = '#c69a52'; ctx.fill(); ctx.lineWidth = 0.8; ctx.strokeStyle = COL.ink; ctx.stroke();
  }
  function ring(ctx, g, a0, a1) {
    ctx.save();
    ctx.lineWidth = 1.7; ctx.strokeStyle = COL.red;
    for (const [s, e] of splitGap(a0, a1, g.gap0, g.gap1)) { ctx.beginPath(); ctx.ellipse(g.x, g.y, g.rx, g.ry, 0, s, e); ctx.stroke(); }
    ctx.restore();
  }
  function splitGap(a0, a1, g0, g1) {
    const norm = (a) => ((a % TAU) + TAU) % TAU;
    g0 = norm(g0); g1 = norm(g1);
    if (g1 < g0) g1 += TAU;
    const out = [];
    let s = a0;
    for (const off of [-TAU, 0, TAU]) {
      const lo = g0 + off, hi = g1 + off;
      if (hi <= s || lo >= a1) continue;
      if (lo > s) out.push([s, lo]);
      s = Math.max(s, hi);
    }
    if (s < a1) out.push([s, a1]);
    return out;
  }
  function paper(ctx, seed) {
    ctx.fillStyle = COL.paper; ctx.fillRect(0, 0, PW, PH);
    const R = rngFor(seed, 'paper');
    for (let i = 0; i < 7; i++) {
      const x = R() * PW, y = R() * PH, r = 200 + R() * 500, gr = ctx.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, R() < 0.5 ? 'rgba(255, 252, 240, 0.12)' : 'rgba(170, 140, 90, 0.018)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = gr; ctx.fillRect(0, 0, PW, PH);
    }
    ctx.fillStyle = 'rgba(90, 70, 40, 0.13)';
    ctx.beginPath();
    for (let i = 0; i < 900; i++) { const x = R() * PW, y = R() * PH, r = 0.25 + R() * 0.6; ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, TAU); }
    ctx.fill();
  }

  // ------------------------------------------------------------- plot strokes
  function coil(x, y, rUnits) {
    const r = Math.max(0.28, rUnits * MM), turns = 1 + Math.min(2.5, r * 2.2), n = Math.floor(30 * turns) + 6, pts = [];
    for (let i = 0; i <= n; i++) { const t = i / n, a = TAU * turns * t, rr = r * (1 - 0.82 * t) / MM; pts.push([x + rr * Math.cos(a), y + rr * Math.sin(a)]); }
    return pts;
  }
  function circlePts(x, y, r) { return ellipsePts({ x, y, a: r, b: r, ang: 0 }, 0); }
  function hatchPoly(pts, step, ang) { // parallel lines clipped to a polygon (even-odd)
    const dx = Math.cos(ang), dy = Math.sin(ang), nx = -dy, ny = dx;
    let lo = Infinity, hi = -Infinity;
    for (const q of pts) { const t = q[0] * nx + q[1] * ny; lo = Math.min(lo, t); hi = Math.max(hi, t); }
    const out = [];
    for (let t = lo + step / 2; t < hi; t += step) {
      const ox = nx * t, oy = ny * t, xs = [];
      for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        const ax = pts[j][0], ay = pts[j][1], ex = pts[i][0] - ax, ey = pts[i][1] - ay, den = dx * ey - dy * ex;
        if (Math.abs(den) < 1e-12) continue;
        const wx = ax - ox, wy = ay - oy, s = (wx * ey - wy * ex) / den, u = (wx * dy - wy * dx) / den;
        if (u >= 0 && u < 1) xs.push(s);
      }
      xs.sort((a, b) => a - b);
      for (let k = 0; k + 1 < xs.length; k += 2) if (xs[k + 1] - xs[k] > 0.8) out.push([[ox + dx * xs[k], oy + dy * xs[k]], [ox + dx * xs[k + 1], oy + dy * xs[k + 1]]]);
    }
    return out;
  }
  // Strokes carry a role (the tone they stand for) and a weight. A pen mode maps roles to
  // layers and inks when the strokes are drawn or written:
  //   series: the books' plot-master form, two layers (Art Paths, Text Outlines) and two inks;
  //           slate and ochre roles are drawn in ink at hairline weight, red stays red.
  //   study:  four pens, one layer each, light to dark (1 Ochre, 2 Slate, 3 Ink, 4 Red).
  const WEIGHTS = [0.12, 0.17, 0.22];
  const SERIES = { ink: COL.ink, red: COL.red };
  const STUDY_ORDER = ['ochre', 'slate', 'ink', 'red'];
  function penOf(s, mode) {
    if (mode === 'study') return { layer: s.role, color: PEN[s.role], w: s.w };
    if (s.studyOnly) return null;
    if (s.role === 'red') return { layer: 'art', color: SERIES.red, w: s.w };
    return { layer: 'art', color: SERIES.ink, w: s.role === 'ink' ? s.w : 0.12 };
  }
  function plotStrokes(sc) {
    const S = [];
    const add = (role, w, pts, closed, studyOnly) => { if (pts.length > 1) S.push({ role, w, pts, closed: !!closed, studyOnly: !!studyOnly }); };
    for (const poly of sc.outline) add('ink', 0.22, poly, Math.hypot(poly[0][0] - poly[poly.length - 1][0], poly[0][1] - poly[poly.length - 1][1]) < 1.5);
    for (const r of sc.ribs) add('ochre', 0.17, r);
    for (const pn of sc.panes) {
      add('ink', 0.17, pn.pts, true);
      if (pn.type === 'slate') { for (const l of hatchPoly(pn.pts, 3.4, Math.PI / 4)) add('slate', 0.17, l); for (const v of pn.veins) add('slate', 0.12, v); }
      if (pn.type === 'dark') { for (const l of hatchPoly(pn.pts, 2.4, Math.PI / 4)) add('ink', 0.12, l); for (const l of hatchPoly(pn.pts, 2.4, -Math.PI / 4)) add('ink', 0.12, l); }
      if (pn.type === 'lace') for (const s of pn.lace) add('ink', 0.12, s);
      for (const c of pn.circles) {
        add('ink', 0.17, circlePts(c.x, c.y, c.r), true);
        const col = Math.max(1.4, c.r * 0.14);
        if (c.r > 3.5) add('ink', 0.12, circlePts(c.x, c.y, c.r - col), true);
        if (c.style === 'slate' || c.style === 'rose') for (const l of hatchPoly(circlePts(c.x, c.y, c.r - col - 0.6), 3.4, Math.PI / 4)) add('slate', 0.17, l);
        if (c.style === 'dark') { if (c.r < 3.2) add('ink', 0.17, coil(c.x, c.y, c.r)); else for (const l of hatchPoly(circlePts(c.x, c.y, c.r - col - 0.4), 2.4, Math.PI / 4)) add('ink', 0.12, l); }
        if (c.style === 'rose') { const a = c.r - col, n = c.spokes || 12; for (let i = 0; i < n; i++) { const t = i / n * TAU; add('ochre', 0.12, [[c.x + a * 0.15 * Math.cos(t), c.y + a * 0.15 * Math.sin(t)], [c.x + a * 0.97 * Math.cos(t), c.y + a * 0.97 * Math.sin(t)]]); } add('ink', 0.17, coil(c.x, c.y, a * 0.15)); }
      }
      for (const d of pn.dots) add('ink', 0.17, d.style === 'dark' ? coil(d.x, d.y, d.r) : circlePts(d.x, d.y, d.r), d.style !== 'dark');
    }
    for (const h of sc.holes) {
      add('ink', 0.17, ellipsePts(h, 0), true);
      if (!h.fixed && h.g) add('ochre', 0.17, ellipsePts(h, Math.min(1.6, h.g * 0.7)), true, true);
      if (h.style === 'slate') for (const l of hatchPoly(ellipsePts(h, -0.8), 3.4, Math.PI / 4)) add('slate', 0.17, l);
      if (h.style === 'dark') { if (Math.min(h.a, h.b) < 3.2) add('ink', 0.17, coil(h.x, h.y, Math.min(h.a, h.b) * 0.9)); else for (const l of hatchPoly(ellipsePts(h, -0.6), 2.4, Math.PI / 4)) add('ink', 0.12, l); }
      if (h.fixed) {
        const cw = collarOf(h);
        add('ink', 0.17, ellipsePts(h, -cw), true);
        if (h.style === 'void') { const inner = ellipsePts(h, -cw - 0.6); for (const l of hatchPoly(inner, 2.4, Math.PI / 4)) add('ink', 0.12, l); for (const l of hatchPoly(inner, 2.4, -Math.PI / 4)) add('ink', 0.12, l); }
        if (h.style === 'seal') {
          const r0 = (Math.min(h.a, h.b) - cw) * 0.6, R = rngFor(sc.seed, 'seal'), gap = R() * TAU, pts = [];
          for (let i = 0; i <= 64; i++) { const t = gap + 0.5 + (TAU - 1) * i / 64; pts.push([h.x + r0 * Math.cos(t), h.y + r0 * Math.sin(t)]); }
          add('red', 0.22, pts);
        }
      }
    }
    for (const h of sc.froth) {
      if (h.style === 'dark' && Math.min(h.a, h.b) < 3.4) add('ink', 0.17, coil(h.x, h.y, Math.min(h.a, h.b)));
      else add('ink', 0.12, ellipsePts(h, 0), true);
    }
    for (const t of sc.tendrils) add('ink', 0.12, tendrilPts(t));
    for (const L of sc.links) add('ink', 0.12, sagPts(L, Math.max(2, Math.ceil(Math.hypot(L.x2 - L.x1, L.y2 - L.y1) / 4))));
    for (const d of sc.drips) {
      add('ink', 0.12, [[d.x, d.y1], [d.x, d.y2 - d.r * 0.6]]);
      add('ink', 0.17, coil(d.x, d.y2, d.r));
      for (const b of d.beads) add('ink', 0.17, coil(d.x, d.y1 + (d.y2 - d.y1) * b.t, b.r));
    }
    for (const b of sc.beads) add('ink', 0.17, coil(b.x, b.y, b.r));
    for (const b of sc.webBeads) add('ink', 0.17, coil(b.x, b.y, b.r));
    for (const t of sc.terminals) add('ink', 0.17, coil(t.x, t.y, t.r));
    for (const p of sc.pearls) { add('ink', 0.17, circlePts(p.x, p.y, p.r), true); add('slate', 0.17, circlePts(p.x + p.r * 0.1, p.y + p.r * 0.12, p.r * 0.62), true); }
    const g = sc.ground;
    if (g) for (const [s0, e0] of splitGap(0, TAU, g.gap0, g.gap1)) {
      const n = Math.max(8, Math.ceil((e0 - s0) * 60)), pts = [];
      for (let i = 0; i <= n; i++) { const t = s0 + (e0 - s0) * i / n; pts.push([g.x + g.rx * Math.cos(t), g.y + g.ry * Math.sin(t)]); }
      add('red', 0.22, pts);
    }
    return S;
  }
  // draw on a canvas at k pixels per unit; `show` hides study layers by name
  function drawStrokes(ctx, S, k, mode, show) {
    ctx.save();
    ctx.setTransform(k, 0, 0, k, 0, 0);
    ctx.fillStyle = '#f6f2e8'; ctx.fillRect(0, 0, PW, PH);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    const passes = mode === 'study' ? STUDY_ORDER.map((r) => [r, PEN[r]]) : [['art', SERIES.ink], ['art', SERIES.red]];
    for (const [layer, color] of passes) {
      if (mode === 'study' && show && show[layer] === false) continue;
      ctx.strokeStyle = color;
      for (const w of WEIGHTS) {
        ctx.lineWidth = w / MM;
        ctx.beginPath();
        for (const s of S) {
          const p = penOf(s, mode);
          if (!p || p.layer !== layer || p.color !== color || p.w !== w) continue;
          ctx.moveTo(s.pts[0][0], s.pts[0][1]);
          for (let i = 1; i < s.pts.length; i++) ctx.lineTo(s.pts[i][0], s.pts[i][1]);
          if (s.closed) ctx.closePath();
        }
        ctx.stroke();
      }
    }
    ctx.restore();
  }
  // the plot master: A4 in millimetres, the figure 180 x 270 mm inside 15 / 13.5 mm margins
  function toSVG(S, meta, mode, show) {
    const f = (v) => { const t = v.toFixed(2); return t.endsWith('00') ? t.slice(0, -3) : t.endsWith('0') ? t.slice(0, -1) : t; };
    const X = (x) => f(OX + x * MM), Y = (y) => f(OY + y * MM);
    const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const o = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="210mm" height="297mm" viewBox="0 0 210 297" version="1.1">',
      '<title>' + esc(meta.title) + '</title>', '<desc>' + esc(meta.desc) + '</desc>'];
    const path = (s, p) => {
      let d = 'M' + X(s.pts[0][0]) + ',' + Y(s.pts[0][1]);
      for (let i = 1; i < s.pts.length; i++) d += 'L' + X(s.pts[i][0]) + ',' + Y(s.pts[i][1]);
      if (s.closed) d += 'Z';
      return '<path fill="none" stroke="' + p.color + '" stroke-width="' + p.w + '" d="' + d + '"/>';
    };
    const open = (id, label) => '<g id="' + id + '" inkscape:groupmode="layer" inkscape:label="' + label + '" fill="none" stroke-linecap="round" stroke-linejoin="round">';
    if (mode === 'study') {
      STUDY_ORDER.forEach((role, i) => {
        if (show && show[role] === false) return;
        o.push(open('layer' + (i + 1), (i + 1) + ' ' + role[0].toUpperCase() + role.slice(1)));
        for (const s of S) { const p = penOf(s, mode); if (p && p.layer === role) o.push(path(s, p)); }
        o.push('</g>');
      });
    } else {
      o.push(open('art-paths', 'Art Paths'));
      for (const color of [SERIES.ink, SERIES.red]) for (const s of S) { const p = penOf(s, mode); if (p && p.color === color) o.push(path(s, p)); }
      o.push('</g>');
      o.push(open('text-outlines', 'Text Outlines'));   // a figure master carries no lettering
      o.push('</g>');
    }
    o.push('</svg>');
    return o.join('\n') + '\n';
  }
  // The <title> and <desc> of a plot master. `host` is { kind: 'native' | 'traced', label,
  // source, sha256 }; the page and plate.mjs both call this, so their files agree.
  const PARAM_ORDER = ['cell', 'rib', 'elong', 'drape', 'sweep', 'strut', 'fray', 'drips', 'slate', 'roses', 'dissolve', 'ground', 'seal'];
  function masterMeta(sc, host, mode, show) {
    const P = sc.params, params = PARAM_ORDER.map((k) => k + '=' + P[k]).join(' ');
    const hostText = host.kind === 'traced'
      ? 'Host: ' + host.label + ', outline traced from ' + host.source + ' (sha256 ' + host.sha256 + '), a raster reference; the lattice is regrown.'
      : 'Host: ' + host.label.toLowerCase() + ', native: the silhouette comes from the seed and no raster is used.';
    const pens = mode === 'study'
      ? 'Pens: study, four layers light to dark (1 Ochre ' + PEN.ochre + ', 2 Slate ' + PEN.slate + ', 3 Ink ' + PEN.ink + ', 4 Red ' + PEN.red + ').'
      : 'Pens: series, layers Art Paths and Text Outlines (empty), inks ' + COL.ink + ' and ' + COL.red + '.';
    const left = mode === 'study' && show ? STUDY_ORDER.filter((r) => show[r] === false) : [];
    return {
      title: 'Node lattice: ' + host.label + ', seed ' + sc.seed,
      desc: 'Node lattice, generator ' + sc.version + '. Seed: ' + sc.seed + '. ' + hostText + ' Parameters: ' + params + '. ' + pens +
        (left.length ? ' Layers left out: ' + left.join(', ') + '.' : '') +
        ' Figure master on A4 in millimetres, the figure 180 x 270 mm inside 15 and 13.5 mm margins; every mark a pen stroke, dots as coils, tone as hatching. Untested on a physical plotter.',
    };
  }
  return { illuminate, plotStrokes, drawStrokes, toSVG, masterMeta, penOf, PEN, MM, OX, OY };
})();
if (typeof module !== 'undefined') module.exports = LatticeRender;
