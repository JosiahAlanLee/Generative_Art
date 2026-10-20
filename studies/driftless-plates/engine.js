/* ==========================================================================
   Driftless Plates — generative line engine
   Pure JS, no dependencies, deterministic per seed. Units are millimetres.
   Scenes are drawn front to back against an occlusion mask, so every line
   that survives is visible: the output is hidden-line plotter work.
   ========================================================================== */
(function (G) {
'use strict';

const PI = Math.PI, TAU = PI * 2, HALF = PI / 2;
const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
// pens
const KEY = 0, FLORA = 1, ACC = 2, TINT = 3;
// stroke kinds: organic, ruled (overshoots), fleck (tiny marks), texture
const ORG = 0, RULED = 1, FLECK = 2, TEX = 3;

/* ---------------------------------------------------------------- random */
// seeding: xmur3 and sfc32 as published in bryc's PRNGs.md (public domain); sfc32 comes from the
// PractRand suite. Used only to seed plates; this is not an entropy-locking algorithm.
function xmur3(str) {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function () {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return (h ^= h >>> 16) >>> 0;
  };
}
function sfc32(a, b, c, d) {
  return function () {
    a |= 0; b |= 0; c |= 0; d |= 0;
    const t = (((a + b) | 0) + d) | 0;
    d = (d + 1) | 0;
    a = b ^ (b >>> 9);
    b = (c + (c << 3)) | 0;
    c = (c << 21) | (c >>> 11);
    c = (c + t) | 0;
    return (t >>> 0) / 4294967296;
  };
}
function Rng(seed, label) {
  const h = xmur3(seed + '::' + label);
  const f = sfc32(h(), h(), h(), h());
  for (let i = 0; i < 15; i++) f();
  let spare = null;
  this.rnd = f;
  this.range = (a, b) => a + (b - a) * f();
  this.int = (a, b) => a + Math.floor((b - a + 1) * f());
  this.pick = (arr) => arr[Math.floor(f() * arr.length)];
  this.chance = (p) => f() < p;
  this.sign = () => (f() < 0.5 ? -1 : 1);
  this.gauss = () => {
    if (spare !== null) { const s = spare; spare = null; return s; }
    let u, v, s;
    do { u = f() * 2 - 1; v = f() * 2 - 1; s = u * u + v * v; } while (s >= 1 || s === 0);
    const m = Math.sqrt(-2 * Math.log(s) / s);
    spare = v * m; return u * m;
  };
  this.weighted = (list) => {
    let t = 0;
    for (let i = 0; i < list.length; i++) t += Math.max(0, list[i][1]);
    let x = f() * t;
    for (let i = 0; i < list.length; i++) { x -= Math.max(0, list[i][1]); if (x <= 0) return list[i][0]; }
    return list[list.length - 1][0];
  };
}

/* ----------------------------------------------------------------- noise */
// 2D simplex noise after Stefan Gustavson's public-domain reference implementation (2005),
// with the permutation shuffled from the plate's seed
function makeNoise(r) {
  const p = new Uint8Array(256), perm = new Uint8Array(512);
  for (let i = 0; i < 256; i++) p[i] = i;
  for (let i = 255; i > 0; i--) { const j = Math.floor(r.rnd() * (i + 1)); const t = p[i]; p[i] = p[j]; p[j] = t; }
  for (let i = 0; i < 512; i++) perm[i] = p[i & 255];
  const GX = [1, -1, 1, -1, 1, -1, 0, 0], GY = [1, 1, -1, -1, 0, 0, 1, -1];
  const F2 = 0.5 * (Math.sqrt(3) - 1), G2 = (3 - Math.sqrt(3)) / 6;
  function n2(xin, yin) {
    const s = (xin + yin) * F2;
    const i = Math.floor(xin + s), j = Math.floor(yin + s);
    const t = (i + j) * G2;
    const x0 = xin - (i - t), y0 = yin - (j - t);
    const i1 = x0 > y0 ? 1 : 0, j1 = x0 > y0 ? 0 : 1;
    const x1 = x0 - i1 + G2, y1 = y0 - j1 + G2, x2 = x0 - 1 + 2 * G2, y2 = y0 - 1 + 2 * G2;
    const ii = i & 255, jj = j & 255;
    let n = 0, tt;
    tt = 0.5 - x0 * x0 - y0 * y0;
    if (tt > 0) { const g = perm[ii + perm[jj]] & 7; tt *= tt; n += tt * tt * (GX[g] * x0 + GY[g] * y0); }
    tt = 0.5 - x1 * x1 - y1 * y1;
    if (tt > 0) { const g = perm[ii + i1 + perm[jj + j1]] & 7; tt *= tt; n += tt * tt * (GX[g] * x1 + GY[g] * y1); }
    tt = 0.5 - x2 * x2 - y2 * y2;
    if (tt > 0) { const g = perm[ii + 1 + perm[jj + 1]] & 7; tt *= tt; n += tt * tt * (GX[g] * x2 + GY[g] * y2); }
    return 70 * n;
  }
  function fbm(x, y, oct) {
    let a = 1, f = 1, s = 0, nrm = 0;
    for (let o = 0; o < (oct || 4); o++) { s += a * n2(x * f, y * f); nrm += a; a *= 0.5; f *= 2.03; }
    return s / nrm;
  }
  return { n2, fbm };
}

/* ------------------------------------------------------------- polylines */
function plen(p) { let L = 0; for (let i = 2; i < p.length; i += 2) L += Math.hypot(p[i] - p[i - 2], p[i + 1] - p[i - 1]); return L; }
function revPts(p) { const o = new Array(p.length); for (let i = 0, n = p.length >> 1; i < n; i++) { o[2 * i] = p[2 * (n - 1 - i)]; o[2 * i + 1] = p[2 * (n - 1 - i) + 1]; } return o; }
function chaikin(p, it) {
  let a = p;
  for (let k = 0; k < it; k++) {
    const n = a.length >> 1; if (n < 3) return a;
    const b = [a[0], a[1]];
    for (let i = 0; i < n - 1; i++) {
      const x0 = a[2 * i], y0 = a[2 * i + 1], x1 = a[2 * i + 2], y1 = a[2 * i + 3];
      b.push(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1, 0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1);
    }
    b.push(a[2 * n - 2], a[2 * n - 1]);
    a = b;
  }
  return a;
}
function subdivide(p, maxSeg) {
  const out = [p[0], p[1]];
  for (let i = 2; i < p.length; i += 2) {
    const x0 = p[i - 2], y0 = p[i - 1], x1 = p[i], y1 = p[i + 1];
    const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / maxSeg));
    for (let s = 1; s <= n; s++) out.push(x0 + (x1 - x0) * s / n, y0 + (y1 - y0) * s / n);
  }
  return out;
}
// math-convention polar point (angle 0 = right, PI/2 = up on the page)
function arcPts(cx, cy, rx, ry, a0, a1, n) {
  const o = [];
  for (let i = 0; i <= n; i++) { const a = lerp(a0, a1, i / n); o.push(cx + rx * Math.cos(a), cy - ry * Math.sin(a)); }
  return o;
}
function circlePts(cx, cy, r, n) { const o = arcPts(cx, cy, r, r, 0, TAU, n || Math.max(24, Math.round(r * 5))); return o; }
function inPoly(poly, x, y) {
  let c = false;
  for (let i = 0, n = poly.length >> 1, j = n - 1; i < n; j = i++) {
    const xi = poly[2 * i], yi = poly[2 * i + 1], xj = poly[2 * j], yj = poly[2 * j + 1];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c;
  }
  return c;
}
// exact parallel hatching of a polygon; returns segments [x0,y0,x1,y1]
function hatchPoly(poly, ang, spacing, phase) {
  const c = Math.cos(ang), s = Math.sin(ang);
  const n = poly.length >> 1, U = new Float64Array(n), V = new Float64Array(n);
  let vmin = Infinity, vmax = -Infinity;
  for (let i = 0; i < n; i++) {
    const x = poly[2 * i], y = poly[2 * i + 1];
    U[i] = x * c + y * s; V[i] = -x * s + y * c;
    if (V[i] < vmin) vmin = V[i]; if (V[i] > vmax) vmax = V[i];
  }
  const out = [], xs = [];
  let v = Math.floor((vmin - (phase || 0)) / spacing) * spacing + (phase || 0);
  if (v < vmin) v += spacing;
  for (; v <= vmax; v += spacing) {
    xs.length = 0;
    for (let i = 0, j = n - 1; i < n; j = i++) {
      const va = V[j], vb = V[i];
      if ((va <= v && vb > v) || (vb <= v && va > v)) xs.push(U[j] + (v - va) / (vb - va) * (U[i] - U[j]));
    }
    xs.sort((a, b) => a - b);
    for (let q = 0; q + 1 < xs.length; q += 2) {
      const u0 = xs[q], u1 = xs[q + 1];
      out.push([u0 * c - v * s, u0 * s + v * c, u1 * c - v * s, u1 * s + v * c]);
    }
  }
  return out;
}
// keep the runs of a polyline where pred(x,y) holds
function clipPred(p, pred, step) {
  step = step || 0.3;
  const out = []; let cur = null;
  let px = p[0], py = p[1], pv = pred(px, py);
  if (pv) cur = [px, py];
  for (let k = 2; k < p.length; k += 2) {
    const x0 = p[k - 2], y0 = p[k - 1], x1 = p[k], y1 = p[k + 1];
    const ns = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / step));
    for (let s = 1; s <= ns; s++) {
      const x = x0 + (x1 - x0) * s / ns, y = y0 + (y1 - y0) * s / ns;
      const v = pred(x, y);
      if (v !== pv) {
        const mx = (px + x) / 2, my = (py + y) / 2;
        if (v) cur = [mx, my]; else { cur.push(mx, my); if (cur.length >= 4) out.push(cur); cur = null; }
        pv = v;
      }
      px = x; py = y;
    }
    if (pv) cur.push(x1, y1);
  }
  if (cur && cur.length >= 4) out.push(cur);
  return out;
}
function boxBlur(a, rad) {
  const n = a.length, out = new Float32Array(n), pre = new Float64Array(n + 1);
  for (let i = 0; i < n; i++) pre[i + 1] = pre[i] + a[i];
  for (let i = 0; i < n; i++) { const lo = Math.max(0, i - rad), hi = Math.min(n - 1, i + rad); out[i] = (pre[hi + 1] - pre[lo]) / (hi - lo + 1); }
  return out;
}
function blur3(a, rad) { return boxBlur(boxBlur(boxBlur(a, rad), rad), rad); }

function Curve(x0, dx, v) { this.x0 = x0; this.dx = dx; this.v = v; this.n = v.length; }
Curve.prototype.at = function (x) {
  const u = (x - this.x0) / this.dx;
  if (u <= 0) return this.v[0];
  if (u >= this.n - 1) return this.v[this.n - 1];
  const i = u | 0, f = u - i;
  return this.v[i] * (1 - f) + this.v[i + 1] * f;
};

/* ------------------------------------------------------------------ mask */
const discCache = new Map();
function discOffsets(r) {
  const key = Math.round(r * 4);
  let o = discCache.get(key); if (o) return o;
  const rr = key / 4, R = Math.ceil(rr); o = [];
  for (let j = -R; j <= R; j++) for (let i = -R; i <= R; i++) if (i * i + j * j <= rr * rr + 0.3) o.push(i, j);
  discCache.set(key, o); return o;
}
function Mask(W, H, cells) {
  this.res = cells / Math.max(W, H);
  this.w = Math.ceil(W * this.res) + 2; this.h = Math.ceil(H * this.res) + 2;
  this.d = new Uint8Array(this.w * this.h);
}
Mask.prototype.free = function (x, y) {
  if (x < 0 || y < 0) return false;
  const i = (x * this.res) | 0, j = (y * this.res) | 0;
  if (i >= this.w || j >= this.h) return false;
  return this.d[j * this.w + i] === 0;
};
Mask.prototype.fillRings = function (rings) {
  const r = this.res, w = this.w, d = this.d;
  let minY = Infinity, maxY = -Infinity;
  for (const p of rings) for (let k = 1; k < p.length; k += 2) { const y = p[k] * r; if (y < minY) minY = y; if (y > maxY) maxY = y; }
  const j0 = Math.max(0, Math.floor(minY)), j1 = Math.min(this.h - 1, Math.ceil(maxY));
  const xs = [];
  for (let j = j0; j <= j1; j++) {
    const sy = j + 0.5; xs.length = 0;
    for (const p of rings) {
      const n = p.length >> 1;
      for (let k = 0, m = n - 1; k < n; m = k++) {
        const ya = p[2 * m + 1] * r, yb = p[2 * k + 1] * r;
        if ((ya <= sy && yb > sy) || (yb <= sy && ya > sy)) {
          const xa = p[2 * m] * r, xb = p[2 * k] * r;
          xs.push(xa + (sy - ya) / (yb - ya) * (xb - xa));
        }
      }
    }
    if (xs.length < 2) continue;
    xs.sort((a, b) => a - b);
    const row = j * w;
    for (let q = 0; q + 1 < xs.length; q += 2) {
      let a = Math.ceil(xs[q] - 0.5), b = Math.floor(xs[q + 1] - 0.5);
      if (a < 0) a = 0; if (b > w - 1) b = w - 1;
      for (let i = a; i <= b; i++) d[row + i] = 1;
    }
  }
};
Mask.prototype.disc = function (cx, cy, rad) {
  const res = this.res, w = this.w, d = this.d;
  const j0 = Math.max(0, Math.floor((cy - rad) * res)), j1 = Math.min(this.h - 1, Math.ceil((cy + rad) * res));
  for (let j = j0; j <= j1; j++) {
    const yy = (j + 0.5) / res - cy, q = rad * rad - yy * yy;
    if (q < 0) continue;
    const hw = Math.sqrt(q);
    let a = Math.ceil((cx - hw) * res - 0.5), b = Math.floor((cx + hw) * res - 0.5);
    if (a < 0) a = 0; if (b > w - 1) b = w - 1;
    for (let i = a; i <= b; i++) d[j * w + i] = 1;
  }
};
Mask.prototype.stamp = function (p, width) {
  const res = this.res, w = this.w, h = this.h, d = this.d;
  const rc = Math.max(0.5, width * 0.5 * res);
  const off = discOffsets(rc), no = off.length;
  const step = Math.max(0.5, rc * 0.7) / res;
  const put = (x, y) => {
    const ci = Math.floor(x * res), cj = Math.floor(y * res);
    for (let q = 0; q < no; q += 2) {
      const i = ci + off[q], j = cj + off[q + 1];
      if (i >= 0 && j >= 0 && i < w && j < h) d[j * w + i] = 1;
    }
  };
  put(p[0], p[1]);
  for (let k = 2; k < p.length; k += 2) {
    const x0 = p[k - 2], y0 = p[k - 1], x1 = p[k], y1 = p[k + 1];
    const ns = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / step));
    for (let s = 1; s <= ns; s++) put(x0 + (x1 - x0) * s / ns, y0 + (y1 - y0) * s / ns);
  }
};
// stamp a polyline with a width that varies per vertex (robust branch silhouettes)
Mask.prototype.stampVar = function (p, ws) {
  const res = this.res, w = this.w, h = this.h, d = this.d;
  const put = (x, y, rc) => {
    const off = discOffsets(rc), ci = Math.floor(x * res), cj = Math.floor(y * res);
    for (let q = 0; q < off.length; q += 2) {
      const i = ci + off[q], j = cj + off[q + 1];
      if (i >= 0 && j >= 0 && i < w && j < h) d[j * w + i] = 1;
    }
  };
  for (let k = 1; k < p.length >> 1; k++) {
    const x0 = p[2 * k - 2], y0 = p[2 * k - 1], x1 = p[2 * k], y1 = p[2 * k + 1];
    const w0 = ws[k - 1], w1 = ws[k];
    const rmin = Math.max(0.5, Math.min(w0, w1) * 0.5 * res);
    const ns = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) * res / Math.max(0.5, rmin * 0.6)));
    for (let s = k === 1 ? 0 : 1; s <= ns; s++) {
      const t = s / ns;
      put(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, Math.max(0.5, lerp(w0, w1, t) * 0.5 * res));
    }
  }
};
Mask.prototype.clip = function (p, minLen) {
  const res = this.res, w = this.w, h = this.h, d = this.d;
  const step = 0.45 / res;
  const out = [];
  let cur = null, px = p[0], py = p[1];
  let pv = this.free(px, py);
  if (pv) cur = [px, py];
  for (let k = 2; k < p.length; k += 2) {
    const x0 = p[k - 2], y0 = p[k - 1], x1 = p[k], y1 = p[k + 1];
    const dx = x1 - x0, dy = y1 - y0;
    const ns = Math.max(1, Math.ceil(Math.sqrt(dx * dx + dy * dy) / step));
    for (let s = 1; s <= ns; s++) {
      const x = x0 + dx * s / ns, y = y0 + dy * s / ns;
      let v = false;
      if (x >= 0 && y >= 0) { const i = (x * res) | 0, j = (y * res) | 0; if (i < w && j < h) v = d[j * w + i] === 0; }
      if (v !== pv) {
        const mx = (px + x) * 0.5, my = (py + y) * 0.5;
        if (v) cur = [mx, my]; else { cur.push(mx, my); out.push(cur); cur = null; }
        pv = v;
      }
      px = x; py = y;
    }
    if (pv) cur.push(x1, y1);
  }
  if (cur && cur.length >= 4) out.push(cur);
  if (!minLen) return out;
  const kept = [];
  for (const q of out) if (q.length >= 4 && plen(q) >= minLen) kept.push(q);
  return kept;
};

/* ----------------------------------------------------------------- scene */
function Scene(P) {
  this.P = P; this.W = P.W; this.H = P.H;
  this.seed = String(P.seed);
  this.mask = new Mask(P.W, P.H, P.cells || 2000);
  this.strokes = [];
  this.penW = P.penWidth || 0.35;
  this.noise = makeNoise(new Rng(this.seed, 'noise'));
  this.minLen = 0.2;
  this.cap = P.strokeCap || 90000;
  this.dens = P.density || 1;
}
Scene.prototype.rng = function (label) { return new Rng(this.seed, label); };
Scene.prototype.free = function (x, y) { return this.mask.free(x, y); };
Scene.prototype.line = function (pts, pen, kind) {
  if (pts.length < 4 || this.strokes.length > this.cap) return;
  const pieces = this.mask.clip(pts, this.minLen);
  for (let i = 0; i < pieces.length; i++) this.strokes.push({ p: pen, k: kind || 0, pts: pieces[i], f: this.tag });
};
Scene.prototype.loop = function (pts, pen, kind) { const q = pts.slice(); q.push(pts[0], pts[1]); this.line(q, pen, kind); };
Scene.prototype.seg = function (x0, y0, x1, y1, pen, kind) { this.line([x0, y0, x1, y1], pen, kind); };
Scene.prototype.fleck = function (x, y, a, len, pen) {
  if (!this.free(x, y)) return;
  const c = Math.cos(a) * len / 2, s = Math.sin(a) * len / 2;
  this.strokes.push({ p: pen, k: FLECK, pts: [x - c, y - s, x + c, y + s] });
};
Scene.prototype.fill = function (poly) { this.mask.fillRings([poly]); };
Scene.prototype.halo = function (pts, w) { this.mask.stamp(pts, w); };

/* ------------------------------------------------------------ composition */
const FOCALS = ['oak', 'pine', 'grove', 'farmstead', 'watertower', 'monument', 'rock', 'sun', 'vista'];

function compose(sc) {
  const P = sc.P, r = sc.rng('compose'), W = sc.W, H = sc.H, wt = P.weights;
  const c = {};
  const season = r.weighted([['summer', 4], ['autumn', 2.6], ['spring', 1.8], ['winter', 1.5]]);
  const time = r.weighted([['day', 5], ['dusk', 2.3], ['night', 1.4]]);
  c.season = P.season && P.season !== 'auto' ? P.season : season;
  c.time = P.time && P.time !== 'auto' ? P.time : time;
  let hz = r.weighted([[r.range(0.28, 0.4), 3], [r.range(0.4, 0.52), 3], [r.range(0.52, 0.64), 1.5], [r.range(0.2, 0.28), 0.8]]);
  hz += (wt.sky - wt.land) * 0.18;
  if (W > H) hz += 0.05;
  const focal = r.weighted([
    ['oak', 2.4 * wt.flora], ['pine', 1.0 * wt.flora], ['grove', 0.9 * wt.flora],
    ['farmstead', 1.8 * wt.built], ['watertower', 0.75 * wt.built], ['monument', 1.0 * wt.built],
    ['rock', 0.6 * wt.built + 0.5 * wt.land], ['sun', 1.0 * wt.sky], ['vista', 0.7 * wt.land + 0.15],
  ]);
  c.focal = P.focal && P.focal !== 'auto' ? P.focal : focal;
  if (c.focal === 'sun') hz += 0.08;
  c.hzFrac = clamp(hz, 0.16, 0.72);
  const fx = P.spread
    ? (r.chance(0.5) ? r.range(0.17, 0.33) : r.range(0.67, 0.83))
    : r.weighted([[r.range(0.26, 0.37), 3], [r.range(0.63, 0.74), 3], [r.range(0.45, 0.55), 1.4], [r.range(0.1, 0.18), 0.6], [r.range(0.82, 0.9), 0.6]]);
  c.focalX = fx;
  c.sunX = fx < 0.5 ? r.range(0.56, 0.88) : r.range(0.12, 0.44);
  if (c.focal === 'sun') c.sunX = P.spread ? fx : lerp(fx, 0.5, 0.5);
  c.lightX = c.sunX < 0.5 ? -1 : 1;
  const frame = r.weighted([['none', 5], ['border', 1.8], ['arch', P.spread ? 0 : 1.5], ['oculus', P.spread ? 0 : 0.6], ['arcade', 1.1]]);
  c.frame = P.frame && P.frame !== 'auto' ? P.frame : frame;
  if (P.spread && (c.frame === 'arch' || c.frame === 'oculus')) c.frame = 'arcade';
  const skyStyle = r.weighted([['lines', 3], ['dashes', 1.6], ['wind', 1.4], ['clear', 1.2], ['rays', 0.8]]);
  const nightSky = r.weighted([['stars', 3], ['lines', 1.6], ['wind', 1]]);
  c.sky = c.time === 'night' ? nightSky : skyStyle;
  c.clouds = r.weighted([['none', 1.4], ['cumulus', 2.6], ['stratus', 1.5], ['mackerel', 1.2]]);
  if (c.time === 'night' && c.clouds === 'cumulus') c.clouds = 'stratus';
  c.sunStyle = r.weighted([['rings', 2.2], ['bands', 2], ['dots', 0.9], ['halo', 1.4]]);
  c.crownStyle = r.weighted([['cloud', 1.1], ['leafy', 2.4], ['stipple', 1], ['hatch', 1]]);
  c.windBias = r.range(-0.35, 0.35);
  c.anomaly = r.chance(0.12 + 0.2 * wt.built);
  c.poles = r.chance(0.18 + 0.35 * wt.built);
  c.fence = r.chance(0.3);
  sc.comp = c;
  sc.frame = computeFrame(sc, c.frame, r);
  const v = sc.view;
  c.bough = c.focal !== 'oak' && c.focal !== 'pine' && c.focal !== 'grove' && c.season !== 'winter' && r.chance(0.1 + 0.18 * wt.flora) ? r.sign() : 0;
  const fb = c.frame === 'arch' || c.frame === 'arcade' ? -0.12 : c.frame === 'oculus' ? -0.04 : 0;
  c.hzFrac = clamp(c.hzFrac + fb, 0.14, 0.7);
  c.horizon = v.y0 + (v.y1 - v.y0) * c.hzFrac;
}

function archPoly(x0, x1, yTop, y1) {
  const rad = (x1 - x0) / 2, cx = (x0 + x1) / 2, cy = yTop + rad;
  const p = [x0, y1, x0, cy];
  for (let i = 1; i < 64; i++) { const a = PI - PI * i / 64; p.push(cx + rad * Math.cos(a), cy - rad * Math.sin(a)); }
  p.push(x1, cy, x1, y1);
  return p;
}
function computeFrame(sc, kind, r) {
  const W = sc.W, H = sc.H, S = Math.min(W, H), bl = sc.P.bleed || 0;
  const fr = { kind, shapes: [], wall: r.chance(0.4), double: r.chance(0.65) };
  const ins = sc.P.inset || null;
  const m = Math.max(S * r.range(0.075, 0.11) + bl, ins ? Math.max(...ins) : 0);
  if (kind === 'none' && ins) {
    // plot masters keep every stroke inside the paper's safe margin; no drawn frame
    fr.shapes.push((e) => [ins[3] - e, ins[0] - e, W - ins[1] + e, ins[0] - e, W - ins[1] + e, H - ins[2] + e, ins[3] - e, H - ins[2] + e]);
    fr.noLine = true; fr.wall = false;
  } else if (kind === 'border') {
    fr.shapes.push((e) => [m - e, m - e, W - m + e, m - e, W - m + e, H - m + e, m - e, H - m + e]);
    fr.wall = false;
  } else if (kind === 'arch') {
    const aw = (W - 2 * m) * r.range(0.8, 1.0), x0 = (W - aw) / 2;
    const yTop = m * r.range(1, 1.5), y1 = H - m * r.range(1, 1.7);
    fr.shapes.push((e) => archPoly(x0 - e, x0 + aw + e, yTop - e, y1 + e));
  } else if (kind === 'oculus') {
    const rad = S / 2 - m * 0.8, cx = W / 2, cy = H > W ? H * r.range(0.46, 0.5) : H / 2;
    fr.shapes.push((e) => circlePts(cx, cy, rad + e, 160));
  } else if (kind === 'arcade') {
    const n = sc.P.spread ? r.pick([2, 4]) : (W > H ? r.int(2, 4) : r.int(2, 3));
    const gap = W * r.range(0.022, 0.045) + (sc.P.spread && n === 2 ? 2 * bl : 0);
    const aw = (W - 2 * m - (n - 1) * gap) / n;
    const yTop = m * r.range(1, 1.5), y1 = H - m * r.range(1, 1.7);
    for (let i = 0; i < n; i++) { const x0 = m + i * (aw + gap); fr.shapes.push((e) => archPoly(x0 - e, x0 + aw + e, yTop - e, y1 + e)); }
  }
  if (!fr.shapes.length) { sc.view = { x0: 0, y0: 0, x1: W, y1: H }; fr.windows = null; return fr; }
  fr.windows = fr.shapes.map((f) => f(0));
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const w of fr.windows) for (let i = 0; i < w.length; i += 2) { x0 = Math.min(x0, w[i]); x1 = Math.max(x1, w[i]); y0 = Math.min(y0, w[i + 1]); y1 = Math.max(y1, w[i + 1]); }
  sc.view = { x0, y0, x1, y1 };
  return fr;
}
function drawFrame(sc) {
  const fr = sc.frame; if (!fr.windows) return;
  const r = sc.rng('frame'), W = sc.W, H = sc.H;
  const gap = sc.penW * r.range(2.4, 3.6);
  sc.tag = 'frame';
  if (!fr.noLine) for (const f of fr.shapes) {
    sc.loop(f(0), KEY, RULED);
    if (fr.double) sc.loop(f(gap), KEY, RULED);
  }
  sc.tag = undefined;
  if (fr.wall) {
    const outside = (x, y) => { for (const w of fr.windows) if (inPoly(w, x, y)) return false; return true; };
    const style = r.pick(['rule', 'stipple', 'courses']);
    if (style === 'rule') {
      const sp = r.range(1.1, 1.8);
      for (let y = sp / 2; y < H; y += sp) for (const piece of clipPred([0, y, W, y], outside, 0.4)) sc.line(piece, TINT, TEX);
    } else if (style === 'courses') {
      const ch = r.range(4, 7), bw = ch * r.range(1.8, 2.6);
      for (let y = 0, row = 0; y < H; y += ch, row++) {
        for (const piece of clipPred([0, y, W, y], outside, 0.4)) sc.line(piece, TINT, TEX);
        for (let x = (row % 2) * bw / 2; x < W; x += bw) if (outside(x, y + ch / 2)) sc.seg(x, y + 0.5, x, y + ch - 0.5, TINT, TEX);
      }
    } else {
      const n = Math.round(W * H * 0.06 * sc.dens);
      for (let i = 0; i < n; i++) { const x = r.rnd() * W, y = r.rnd() * H; if (outside(x, y)) sc.fleck(x, y, r.rnd() * TAU, 0.25, TINT); }
    }
  }
  const page = [-5, -5, W + 5, -5, W + 5, H + 5, -5, H + 5];
  sc.mask.fillRings([page].concat(fr.shapes.map((f) => f(fr.double && !fr.noLine ? gap * 0.5 : 0))));
}

/* ----------------------------------------------------------------- land */
function shapeSamples(sc, type, k, r, x0, dx, nS) {
  const N = sc.noise, W = sc.W, s = new Float32Array(nS);
  const off = k * 17.31 + 3.3, sx = 1 / (W * r.range(0.25, 0.6));
  const X = (i) => x0 + i * dx;
  let blocks = null;
  if (type === 'rolling' || type === 'flat') {
    for (let i = 0; i < nS; i++) s[i] = N.fbm(X(i) * sx, off, 3);
  } else if (type === 'driftless') {
    for (let i = 0; i < nS; i++) s[i] = 0.82 + 0.18 * N.fbm(X(i) * sx * 1.4, off, 3);
    const m = r.int(1, 3);
    for (let q = 0; q < m; q++) {
      const cx = r.range(-0.05, 1.05) * W, hw = r.range(0.07, 0.2) * W, dep = r.range(0.25, 0.65), sh = r.range(0.55, 1);
      for (let i = 0; i < nS; i++) {
        const u = Math.abs(X(i) - cx) / hw;
        if (u < 1) { const v = 1 - u; s[i] -= dep * (sh * v * v * (3 - 2 * v) + (1 - sh) * Math.pow(v, 1.7)); }
      }
    }
    if (r.chance(0.45)) {
      const side = r.sign(), at = r.range(0.0, 0.35) * W, wd = r.range(0.1, 0.3) * W;
      for (let i = 0; i < nS; i++) { const d = side > 0 ? X(i) - (W - at) : at - X(i); s[i] -= 0.7 * smooth(0, wd, d); }
    }
  } else if (type === 'mesa') {
    for (let i = 0; i < nS; i++) s[i] = 0.18 * N.fbm(X(i) * sx, off, 3);
    blocks = [];
    const m = r.int(1, 2);
    for (let q = 0; q < m; q++) {
      const a = r.range(0.02, 0.72) * W, wd = r.range(0.1, 0.32) * W, b = a + wd, e = r.range(0.012, 0.035) * W, top = r.range(0.85, 1);
      blocks.push({ a, b, e, top });
      for (let i = 0; i < nS; i++) {
        const x = X(i), pl = smooth(a - e, a, x) * (1 - smooth(b, b + e, x));
        const tv = top + 0.025 * N.n2(x * 0.25, off + 9 + q);
        s[i] = Math.max(s[i], lerp(s[i], tv, pl));
      }
    }
  } else if (type === 'knoll') {
    const cx = r.range(0.2, 0.8) * W, wd = r.range(0.3, 0.7) * W;
    for (let i = 0; i < nS; i++) { const u = (X(i) - cx) / wd; s[i] = Math.exp(-u * u * 2) + 0.12 * N.fbm(X(i) * sx, off, 2); }
  }
  let lo = Infinity, hi = -Infinity;
  for (let i = 0; i < nS; i++) { const x = X(i); if (x < 0 || x > W) continue; if (s[i] < lo) lo = s[i]; if (s[i] > hi) hi = s[i]; }
  const sp = Math.max(1e-6, hi - lo);
  for (let i = 0; i < nS; i++) s[i] = (s[i] - lo) / sp;
  if (type === 'flat') for (let i = 0; i < nS; i++) s[i] = 0.4 + s[i] * 0.2;
  if (blocks) for (const b of blocks) b.top = (b.top * 1 - lo) / sp;
  return { s, blocks };
}

function buildBands(sc) {
  const P = sc.P, c = sc.comp, r = sc.rng('bands'), W = sc.W, H = sc.H, v = sc.view;
  const pad = 8, dx = 0.5, x0 = -pad, nS = Math.ceil((W + 2 * pad) / dx) + 1;
  const viewH = v.y1 - v.y0;
  const nB = clamp(Math.round(r.range(3.6, 6.4) + (P.weights.land - 0.5) * 2.5), 3, 8);
  const fgH = viewH * (c.focal === 'vista' || c.focal === 'sun' ? r.range(0.07, 0.16) : r.range(0.13, 0.3)) * lerp(1.15, 0.85, P.weights.sky);
  const yFg = v.y1 - fgH;
  const expo = r.range(1.1, 1.6);
  const bands = [];
  for (let k = 0; k < nB; k++) {
    const t = k / (nB - 1), fg = k === nB - 1;
    const mean = c.horizon + (yFg - c.horizon) * Math.pow(t, expo);
    let amp = (v.y1 - c.horizon) * lerp(0.025, 0.12, t) * r.range(0.5, 1.45);
    let type;
    if (fg) type = r.weighted([['rolling', 3], ['flat', 1.4], ['knoll', 1.6]]);
    else if (t < 0.25) type = r.weighted([['rolling', 3], ['driftless', 2.5], ['flat', 0.8], ['mesa', 0.6 * P.weights.land]]);
    else type = r.weighted([['driftless', 3.5], ['rolling', 2], ['mesa', t < 0.5 ? 0.3 * P.weights.land : 0], ['flat', 0.5]]);
    if (!fg && t > 0.45 && (type === 'driftless' || type === 'rolling') && r.chance(0.2)) amp *= r.range(1.25, 1.7);
    if (fg) amp *= r.range(0.6, 1.2);
    const { s, blocks } = shapeSamples(sc, type, k, r, x0, dx, nS);
    const ss = type === 'mesa' ? s : blur3(s, Math.max(1, Math.round(lerp(2, 7, t))));
    const R = new Float32Array(nS);
    for (let i = 0; i < nS; i++) R[i] = mean - amp * (ss[i] - 0.5) * 2;
    const b = { k, t, fg, type, mean, amp, R, x0, dx, nS, curve: new Curve(x0, dx, R) };
    if (blocks) b.blocks = blocks.map((q) => ({ a: q.a, b: q.b, e: q.e, topY: mean - amp * (q.top - 0.5) * 2 }));
    bands.push(b);
  }
  // a river or pond in the middle distance: a band with a dead-flat far shore
  if (nB >= 4 && r.chance(0.16 + 0.14 * P.weights.land)) {
    const b = bands[r.int(Math.max(1, Math.floor(nB * 0.45)), nB - 2)];
    b.water = true; b.type = 'water'; b.blocks = null;
    const lvl = b.mean + b.amp * r.range(0.1, 0.6);
    b.R.fill(lvl); b.mean = lvl; b.amp = 0;
  }
  let env = new Float32Array(nS).fill(H + 40);
  for (let k = nB - 1; k >= 0; k--) {
    const b = bands[k];
    b.E = env.slice(); b.Ec = new Curve(x0, dx, b.E);
    const ne = new Float32Array(nS);
    for (let i = 0; i < nS; i++) ne[i] = Math.min(env[i], b.R[i]);
    env = ne;
  }
  sc.floor = new Curve(x0, dx, env);
  sc.bands = bands;
  for (const b of bands) b.treat = chooseTreatment(sc, b, r);
  // detail hierarchy: one or two rich bands carry the texture, the rest stay quiet
  const mids = bands.filter((b) => !b.fg && b.t >= 0.2);
  for (const b of bands) b.detail = b.fg ? 1 : b.t < 0.2 ? 0.8 : 0.7;
  for (let i = mids.length - 1; i > 0; i--) { const j = Math.floor(r.rnd() * (i + 1)); const t = mids[i]; mids[i] = mids[j]; mids[j] = t; }
  mids.slice(0, Math.min(mids.length, r.int(1, 2))).forEach((b) => { b.detail = 1.35; });
}

function chooseTreatment(sc, b, r) {
  const c = sc.comp, w = sc.P.weights;
  if (b.water) return 'water';
  if (b.fg) {
    if (c.season === 'winter') return r.weighted([['snow', 3], ['meadow', 0.8]]);
    return r.weighted([['meadow', 1.2 + 3 * w.flora], ['farm', 0.5 + 1.3 * w.land], ['prairie', 0.7]]);
  }
  if (b.t < 0.22) return r.weighted([['outline', 1.3], ['stipple', 1.4], ['treeline', 2], ['haze', 1.3]]);
  return r.weighted([['farm', 3 + 2 * w.land], ['forest', 1.3 + 1.2 * w.flora], ['hatch', 0.9], ['stipple', b.t < 0.5 ? 0.4 : 0], ['prairie', 0.5]]);
}

function bandPolygon(b, H) {
  const p = [];
  for (let i = 0; i < b.nS; i++) p.push(b.x0 + i * b.dx, b.R[i]);
  p.push(b.x0 + (b.nS - 1) * b.dx, H + 30, b.x0, H + 30);
  return p;
}
function ridgeLine(sc, b, pen, dotted) {
  const pts = [];
  for (let i = 0; i < b.nS; i++) pts.push(b.x0 + i * b.dx, b.R[i]);
  if (!dotted) { sc.line(pts, pen, ORG); return; }
  const r = sc.rng('dots' + b.k);
  for (let x = -2; x < sc.W + 2; x += r.range(0.7, 1.4)) sc.fleck(x, b.curve.at(x) + 0.05, 0, r.range(0.2, 0.6), pen);
}
function visibleSpan(b, xa, xb, topC) {
  for (let x = Math.max(xa, -2); x <= xb; x += 1.5) if ((topC ? topC.at(x) : b.curve.at(x)) < b.Ec.at(x) - 0.2) return true;
  return false;
}
function farPen(t, r) { return t < 0.3 ? (r.chance(0.75) ? TINT : KEY) : t < 0.55 ? (r.chance(0.35) ? TINT : KEY) : KEY; }

/* --- treatment: contour-strip farmland ----------------------------------- */
function farm(sc, b) {
  const r = sc.rng('farm' + b.k), c = sc.comp, W = sc.W, N = sc.noise;
  const { x0, dx, nS, R, E } = b, t = b.t;
  const radii = [0, 3, 8, 16, 32, 64];
  const lv = radii.map((rd) => (rd === 0 ? R : blur3(R, Math.max(1, Math.round(rd / dx / 1.7)))));
  const smoothR = new Curve(x0, dx, lv[3]);
  let delta = lerp(0.8, 5.2, Math.pow(t, 1.15)) * r.range(0.75, 1.3) / Math.sqrt(sc.dens);
  const grow = r.range(0.05, 0.15), sig = r.range(2, 6) * lerp(0.6, 1.4, t);
  const C = [R];
  let D = 0;
  for (let j = 1; j < 90; j++) {
    D += delta; delta *= 1 + grow;
    const s = Math.min(64, j * sig);
    let L = 0; while (L < radii.length - 2 && radii[L + 1] < s) L++;
    const f = clamp((s - radii[L]) / (radii[L + 1] - radii[L]), 0, 1);
    const cj = new Float32Array(nS); let vis = false;
    for (let i = 0; i < nS; i++) {
      cj[i] = Math.max(lerp(lv[L][i], lv[L + 1][i], f) + D, R[i] + D * 0.35);
      if (cj[i] < E[i]) vis = true;
    }
    C.push(cj);
    if (!vis) break;
  }
  const Cc = C.map((a) => new Curve(x0, dx, a));
  const divs = [];
  let xx = -r.range(0, 40);
  const wMin = lerp(0.05, 0.12, t) * W, wMax = lerp(0.2, 0.42, t) * W;
  while (xx < W + 40) { xx += r.range(wMin, wMax); divs.push({ x: xx, lean: r.range(-0.3, 0.3), p: r.range(0.3, 0.95) }); }
  const season = c.season;
  const texW = {
    summer: [['rows', 4], ['ticks', 2], ['dots', 1.3], ['blank', 1.7], ['waves', 1], ['cross', 0.7], ['diag', 0.8]],
    autumn: [['rows', 3], ['ticks', 2.6], ['dots', 1], ['blank', 1.8], ['cross', 1], ['diag', 1]],
    spring: [['rows', 4.5], ['dots', 1.6], ['blank', 2], ['waves', 0.8], ['diag', 0.8]],
    winter: [['blank', 5], ['rows', 1.4], ['ticks', 1.4], ['dots', 0.6]],
  }[season];
  const penW = {
    summer: [[FLORA, 4], [KEY, 2.4], [TINT, 1.2], [ACC, 0.5]],
    autumn: [[ACC, 2.4], [KEY, 2.4], [FLORA, 1.2], [TINT, 1.3]],
    spring: [[KEY, 2.6], [FLORA, 3], [TINT, 1.6]],
    winter: [[TINT, 3], [KEY, 1.4]],
  }[season];
  const lx = c.lightX;
  const texW2 = texW.map(([k, w]) => [k, k === 'blank' ? w / b.detail : w * b.detail]);
  const woodStyle = t < 0.3 ? 'cloud' : c.crownStyle;
  const woodPen = season === 'autumn' ? [[ACC, 2], [KEY, 1.5], [FLORA, 1]] : season === 'winter' ? [[KEY, 1]] : [[FLORA, 3], [KEY, 1]];
  for (let s = C.length - 2; s >= 0; s--) {
    const top = Cc[s], bot = Cc[s + 1];
    const cuts = [{ x: -40, lean: 0 }];
    for (const d of divs) if (r.chance(d.p)) cuts.push(d);
    cuts.push({ x: W + 40, lean: 0 });
    for (let q = 0; q < cuts.length - 1; q++) {
      const A = cuts[q], B = cuts[q + 1];
      const xa = A.x, xb = B.x;
      if (xb < -2 || xa > W + 2) continue;
      if (!visibleSpan(b, Math.max(xa, -2), Math.min(xb, W + 2), top)) continue;
      const xm = clamp((xa + xb) / 2, 0, W);
      const sl = (smoothR.at(xm + 2) - smoothR.at(xm - 2)) / 4;
      const light = clamp(0.5 + sl * lx * -2.2 + N.n2(xm * 0.02, s * 0.3 + b.k) * 0.25, 0, 1);
      const steep = Math.abs(sl);
      let tex = r.weighted(texW2);
      if (steep > 0.34 && r.chance(0.55 * b.detail)) tex = 'wood';
      else if (r.chance(0.025 * b.detail)) tex = 'wood';
      let pen = r.weighted(penW);
      if (t < 0.3 && r.chance(0.6)) pen = TINT;
      const hgt = bot.at(xm) - top.at(xm);
      const sp = lerp(0.62, 1.9, light) * lerp(0.85, 1.15, t) / Math.sqrt(sc.dens * b.detail);
      const P = { sc, top, bot, xa, xb, la: A.lean, lb: B.lean, pen, r, hgt, sp, t };
      switch (tex) {
        case 'blank':
          if ((season === 'summer' || season === 'autumn') && t > 0.3 && r.chance(0.32)) bales(P);
          break;
        case 'rows': patchRows(P, 0); break;
        case 'waves': patchRows(P, sp * 0.35); break;
        case 'ticks': patchTicks(P); break;
        case 'dots': patchDots(P, light); break;
        case 'cross': patchRows(P, 0); patchDiag(P, r.pick([PI / 4, -PI / 4]), sp * 1.3); break;
        case 'diag': patchDiag(P, r.pick([PI / 4, -PI / 4, PI / 3, -PI / 3]), sp); break;
        case 'wood': {
          const rad = lerp(0.6, 3.6, Math.pow(t, 1.1)) * r.range(0.8, 1.2);
          forestFill(sc, { x0: xa, x1: xb, top, bot, rTop: rad * 0.8, rBot: rad, kind: season === 'winter' ? 'bare' : r.chance(0.2) ? 'mixed' : 'round', pens: woodPen, r, conFrac: 0.35, style: woodStyle });
          break;
        }
      }
    }
    // division lines for this strip
    for (let q = 1; q < cuts.length - 1; q++) {
      const d = cuts[q];
      if (d.x < -1 || d.x > W + 1) continue;
      const y0 = top.at(d.x), y1 = bot.at(d.x);
      sc.seg(d.x, y0, d.x + d.lean * (y1 - y0), y1, t < 0.3 ? TINT : KEY, TEX);
    }
    if (s > 0) {
      if (r.chance(0.08) && season !== 'winter') {
        const rad = lerp(0.5, 2.2, t);
        forestFill(sc, { x0: -2, x1: W + 2, top: { at: (x) => top.at(x) - rad * 0.3 }, bot: top, rTop: rad, rBot: rad, kind: 'round', pens: woodPen, r, rows: 1, style: woodStyle });
      }
      const pts = [];
      for (let x = -2; x <= W + 2; x += 1) pts.push(x, top.at(x));
      sc.line(pts, t < 0.3 ? TINT : KEY, TEX);
    }
  }
  ridgeLine(sc, b, t < 0.25 ? TINT : KEY);
}
function rowRange(P, u) {
  const { top, bot, xa, xb, la, lb } = P;
  const ya = lerp(top.at(xa), bot.at(xa), u), yb = lerp(top.at(xb), bot.at(xb), u);
  return [xa + la * (ya - top.at(xa)) + 0.45, xb + lb * (yb - top.at(xb)) - 0.45];
}
function patchRows(P, wave) {
  const { sc, top, bot, hgt, sp, pen, r } = P;
  const n = Math.floor(hgt / sp);
  if (n < 1) return;
  const ph = r.range(0, TAU), fq = r.range(0.5, 1.4);
  for (let q = 1; q <= n; q++) {
    const u = q / (n + 1);
    let [xs, xe] = rowRange(P, u);
    xs = Math.max(xs, -2); xe = Math.min(xe, sc.W + 2);
    if (xe - xs < 0.5) continue;
    const pts = [];
    for (let x = xs; ; x += 0.8) {
      const xc = Math.min(x, xe);
      let y = lerp(top.at(xc), bot.at(xc), u);
      if (wave) y += wave * Math.sin(xc * fq + ph + q * 0.9);
      pts.push(xc, y);
      if (xc >= xe) break;
    }
    sc.line(pts, pen, TEX);
  }
}
function patchTicks(P) {
  const { sc, top, bot, hgt, sp, pen, r } = P;
  const rs = sp * 1.25, n = Math.floor(hgt / rs);
  if (n < 1) return;
  const lean = r.range(-0.35, 0.35), gap = r.range(0.55, 1.1) * lerp(0.8, 1.3, P.t) / Math.sqrt(sc.dens);
  for (let q = 1; q <= n; q++) {
    const u = q / (n + 1);
    let [xs, xe] = rowRange(P, u);
    xs = Math.max(xs, -1); xe = Math.min(xe, sc.W + 1);
    const th = rs * r.range(0.55, 0.8);
    for (let x = xs + r.range(0, gap); x < xe; x += gap * r.range(0.8, 1.2)) {
      const y = lerp(top.at(x), bot.at(x), u);
      sc.seg(x, y, x + lean * th, y - th, pen, TEX);
    }
  }
}
function patchDots(P, light) {
  const { sc, top, bot, xa, xb, pen, r } = P;
  const x0 = Math.max(xa, -1), x1 = Math.min(xb, sc.W + 1);
  const area = Math.max(0, (x1 - x0) * P.hgt);
  const n = Math.round(area * lerp(0.9, 0.25, light) * sc.dens);
  for (let i = 0; i < n; i++) {
    const x = lerp(x0, x1, r.rnd()), u = r.range(0.06, 0.94);
    sc.fleck(x, lerp(top.at(x), bot.at(x), u), r.rnd() * PI, 0.22, pen);
  }
}
function bales(P) {
  const { sc, top, bot, xa, xb, r, t } = P;
  const x0 = Math.max(xa + 1, 0), x1 = Math.min(xb - 1, sc.W);
  if (x1 - x0 < 3) return;
  const rad = lerp(0.45, 1.7, t) * r.range(0.85, 1.15), lx = sc.comp.lightX;
  const list = [];
  for (let i = r.int(2, 7); i > 0; i--) { const x = r.range(x0, x1), u = r.range(0.25, 0.85); list.push([x, lerp(top.at(x), bot.at(x), u)]); }
  list.sort((a, b) => b[1] - a[1]);
  for (const [x, yb] of list) {
    const cy = yb - rad;
    if (!sc.free(x, cy)) continue;
    const out = circlePts(x, cy, rad, 28);
    sc.line(out, KEY, ORG);
    if (rad > 0.8) {
      const sp = [];
      for (let a = 0; a < TAU * 2.2; a += 0.35) { const rr = rad * 0.85 * (1 - a / (TAU * 2.6)); sp.push(x + Math.cos(a) * rr * 0.55, cy - Math.sin(a) * rr); }
      sc.line(sp, KEY, TEX);
    }
    sc.line([x - lx * rad * 0.2, yb + 0.25, x - lx * rad * 2.2, yb + 0.25], KEY, TEX);
    sc.mask.disc(x, cy, rad + 0.15);
  }
}
function patchDiag(P, ang, sp) {
  const { sc, top, bot, xa, xb, la, lb, pen } = P;
  const x0 = Math.max(xa - 2, -2), x1 = Math.min(xb + 2, sc.W + 2);
  if (x1 <= x0) return;
  let y0 = Infinity, y1 = -Infinity;
  for (let x = x0; x <= x1; x += 2) { y0 = Math.min(y0, top.at(x)); y1 = Math.max(y1, bot.at(x)); }
  const pred = (x, y) => {
    const tt = top.at(x), bb = bot.at(x);
    if (y < tt + 0.3 || y > bb - 0.3) return false;
    return x > xa + la * (y - top.at(xa)) + 0.45 && x < xb + lb * (y - top.at(xb)) - 0.45;
  };
  const box = [x0, y0, x1, y0, x1, y1, x0, y1];
  for (const s of hatchPoly(box, ang, sp, 0)) for (const piece of clipPred(s, pred, 0.35)) sc.line(piece, pen, TEX);
}

/* --- treatment: forest canopy rows --------------------------------------- */
function forestFill(sc, o) {
  const r = o.r;
  const xm0 = Math.max(o.x0, -3), xm1 = Math.min(o.x1, sc.W + 3);
  if (xm1 <= xm0) return;
  let u = 1.0, guard = 0, rows = 0;
  while (u > -0.02 && guard++ < 600) {
    const rad = lerp(o.rTop, o.rBot, clamp(u, 0, 1));
    let x = xm0 + r.range(0, rad);
    while (x < xm1) {
      const yt = o.top.at(x), yb = o.bot.at(x), hgt = yb - yt;
      const rr = rad * r.range(0.75, 1.25);
      if (hgt > 0.15) {
        const y = Math.min(yb, yt + clamp(u, 0, 1) * hgt + r.range(-0.25, 0.25) * rr);
        if (sc.free(x, y - rr * 0.6)) {
          const kind = o.kind === 'mixed' ? (r.chance(o.conFrac || 0.3) ? 'conifer' : 'round') : o.kind;
          crown(sc, x, y, rr, kind, r.weighted(o.pens), r, o.style);
        }
      }
      x += rr * r.range(1.05, 1.6) / Math.sqrt(sc.dens);
    }
    rows++;
    if (o.rows && rows >= o.rows) break;
    const xm = (xm0 + xm1) / 2, hm = Math.max(0.4, o.bot.at(xm) - o.top.at(xm));
    u -= rad * r.range(0.55, 0.8) / hm;
  }
}
function crown(sc, x, yb, rr, kind, pen, r, style) {
  const lx = sc.comp.lightX;
  if (kind === 'conifer') {
    const h = rr * r.range(2.0, 2.9), hw = rr * r.range(0.65, 0.9);
    const n = Math.max(3, Math.round(h / 0.8));
    const L = [], Rt = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n, w = hw * (1 - t) * (i % 2 ? 0.72 : 1) * (1 + r.range(-0.08, 0.08));
      L.push(x - w, yb - t * h); Rt.push(x + w, yb - t * h);
    }
    const out = L.concat(revPts(Rt).slice(2));
    sc.line(out, pen, ORG);
    if (rr > 1) {
      const side = -lx;
      for (let q = 1; q <= (rr > 2.4 ? 3 : 1); q++) {
        const f = 0.25 * q;
        sc.line([x + side * hw * (1 - f) * 0.9, yb - 0.3, x + side * hw * 0.05, yb - h * (0.85 - f * 0.4)], pen, TEX);
      }
    }
    const poly = out.slice(); poly.push(x - hw, yb + 0.15);
    sc.fill(poly);
    return;
  }
  if (kind === 'bare') {
    const h = rr * r.range(1.8, 2.7), lean = r.range(-0.15, 0.15);
    const trunk = [x, yb, x + lean * h * 0.5, yb - h * 0.5, x + lean * h, yb - h];
    sc.line(trunk, pen, ORG); sc.halo(trunk, sc.penW * 1.3);
    const nb = r.int(2, 4);
    for (let q = 0; q < nb; q++) {
      const t = r.range(0.35, 0.85), bx = x + lean * h * t, by = yb - h * t;
      const a = HALF + r.sign() * r.range(0.35, 0.9), L = h * r.range(0.25, 0.45) * (1 - t * 0.4);
      const ex = bx + Math.cos(a) * L, ey = by - Math.sin(a) * L;
      const br = [bx, by, (bx + ex) / 2 + r.range(-0.2, 0.2), (by + ey) / 2, ex, ey];
      sc.line(br, pen, ORG); sc.halo(br, sc.penW * 1.2);
      if (L > 1.5) { const a2 = a + r.sign() * 0.5; const tw = [ex, ey, ex + Math.cos(a2) * L * 0.4, ey - Math.sin(a2) * L * 0.4]; sc.line(tw, pen, ORG); }
    }
    return;
  }
  style = style || 'cloud';
  const cy = yb - rr * 0.82;
  const leafy = style === 'leafy';
  const bumps = leafy ? clamp(Math.round(rr * r.range(2.6, 3.6)), 5, 30) : r.int(4, 7);
  const n = Math.max(12, Math.round(rr * (leafy ? 14 : 8)));
  const a0 = PI + 0.45, a1 = -0.45, ph = r.range(0, TAU), nz = r.range(0, 300);
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const a = lerp(a0, a1, i / n);
    const lump = leafy ? 1 + 0.12 * sc.noise.n2(Math.cos(a) + nz, Math.sin(a)) : 1;
    const rad = rr * lump * (1 - (leafy ? 0.1 : 0.14) * (1 - Math.abs(Math.sin(bumps * a / 2 + ph))) + r.range(-0.02, 0.02));
    pts.push(x + rad * Math.cos(a), cy - rad * Math.sin(a));
  }
  sc.line(pts, pen, ORG);
  const sdx = lx < 0 ? 0.65 : -0.65;
  if (style === 'cloud' && rr > 0.9) {
    const sa = lx < 0 ? -0.35 : PI + 0.35;
    const m = rr > 2.6 ? r.int(2, 4) : 1;
    for (let q = 0; q < m; q++) {
      const rad = rr * lerp(0.72, 0.38, m > 1 ? q / (m - 1) : 0);
      const span = r.range(0.45, 0.95);
      sc.line(arcPts(x, cy, rad, rad, sa - span, sa + span * 0.6, Math.max(4, Math.round(rad * 3))), pen, TEX);
    }
  } else if (style !== 'cloud' && rr > 0.7) {
    const m = Math.round(PI * rr * rr * (style === 'stipple' ? 1.6 : style === 'hatch' ? 0.5 : 0.55) * sc.dens);
    const ha = lx < 0 ? -PI / 3 : PI / 3;
    for (let q = 0; q < m; q++) {
      const a = r.range(0, TAU), d = Math.sqrt(r.rnd()) * 0.85;
      const px = x + Math.cos(a) * d * rr, py = cy - Math.sin(a) * d * rr;
      if (py > yb - 0.25) continue;
      const s = Math.cos(a) * d * sdx - Math.sin(a) * d * 0.75;
      if (r.rnd() > smooth(-0.3, 0.8, s)) continue;
      if (style === 'stipple') sc.fleck(px, py, r.rnd() * PI, 0.2, pen);
      else if (style === 'hatch') { const L = r.range(0.6, 1.2) * Math.min(1, rr / 2); sc.line([px - Math.cos(ha) * L / 2, py + Math.sin(ha) * L / 2, px + Math.cos(ha) * L / 2, py - Math.sin(ha) * L / 2], pen, TEX); }
      else { const w = r.range(0.5, 0.9) * Math.min(1, 0.5 + rr / 4); sc.line(arcPts(px, py, w / 2, w * 0.38, PI + 0.2, TAU - 0.2, 4), pen, TEX); }
    }
  }
  const poly = pts.slice(); poly.push(x + rr * 0.86, yb + 0.15, x - rr * 0.86, yb + 0.15);
  sc.fill(poly);
}
function forestBand(sc, b) {
  const r = sc.rng('forest' + b.k), c = sc.comp, t = b.t;
  const rad = lerp(0.7, 3.8, Math.pow(t, 1.1)) * r.range(0.8, 1.25);
  const kind = c.season === 'winter' ? 'bare' : r.weighted([['round', 3], ['mixed', 2], ['conifer', 0.6]]);
  const pens = c.season === 'autumn' ? [[ACC, 2.2], [KEY, 1.6], [FLORA, 1]] : c.season === 'winter' ? [[KEY, 2], [TINT, 1]] : [[FLORA, 3], [KEY, 1.2]];
  if (t < 0.35) pens.push([TINT, 3]);
  const style = t < 0.3 ? 'cloud' : b.detail < 1 && c.crownStyle === 'leafy' ? 'cloud' : c.crownStyle;
  forestFill(sc, { x0: -3, x1: sc.W + 3, top: b.curve, bot: { at: (x) => Math.min(b.Ec.at(x), sc.H + 2) }, rTop: rad * 0.75, rBot: rad * 1.15, kind, pens, r, conFrac: 0.3, style });
  ridgeLine(sc, b, t < 0.3 ? TINT : KEY);
}
function treelineBand(sc, b) {
  const r = sc.rng('treeline' + b.k);
  const rad = r.range(0.45, 0.95) * lerp(1, 1.6, b.t);
  const pens = sc.comp.season === 'autumn' ? [[ACC, 1], [TINT, 2]] : [[TINT, 3], [KEY, 0.6]];
  const kind = sc.comp.season === 'winter' ? 'bare' : r.weighted([['round', 2], ['mixed', 1.2], ['conifer', 0.5]]);
  forestFill(sc, { x0: -3, x1: sc.W + 3, top: b.curve, bot: { at: (x) => Math.min(b.Ec.at(x), b.curve.at(x) + rad * 3.2) }, rTop: rad, rBot: rad, kind, pens, r });
  if (r.chance(0.6)) stippleBand(sc, b, 0.5);
}
function stippleBand(sc, b, amount) {
  const r = sc.rng('stip' + b.k), W = sc.W;
  const spread = lerp(2, 9, b.t) * r.range(0.7, 1.4);
  const n = Math.round(W * spread * lerp(1.3, 0.6, b.t) * (amount || 1) * sc.dens);
  const pen = b.t < 0.5 ? TINT : KEY;
  for (let i = 0; i < n; i++) {
    const x = r.range(-1, W + 1), y = b.curve.at(x) + Math.abs(r.gauss()) * spread;
    if (y < b.Ec.at(x)) sc.fleck(x, y, r.rnd() * PI, 0.2, pen);
  }
  if (!amount) ridgeLine(sc, b, b.t < 0.3 ? TINT : KEY, b.t < 0.15);
}
function hazeBand(sc, b) {
  const r = sc.rng('haze' + b.k);
  const step = r.range(0.6, 1.0) / Math.sqrt(sc.dens), L = lerp(1.5, 6, b.t) * r.range(0.7, 1.4);
  for (let x = -1; x < sc.W + 1; x += step * r.range(0.8, 1.2)) {
    const y = b.curve.at(x) + 0.35, len = L * Math.pow(r.rnd(), 0.7);
    sc.seg(x, y, x, Math.min(y + len, b.Ec.at(x)), TINT, TEX);
  }
  ridgeLine(sc, b, TINT);
}
function hatchBand(sc, b) {
  const r = sc.rng('hatch' + b.k), c = sc.comp, W = sc.W, H = sc.H, N = sc.noise;
  const smA = blur3(b.R, 8), sm = new Curve(b.x0, b.dx, smA);
  const flat = new Curve(b.x0, b.dx, blur3(b.R, 40));
  const sp = lerp(0.65, 1.2, b.t) * r.range(0.9, 1.2) / Math.sqrt(sc.dens * b.detail);
  const shade = (x, y) => {
    const sl = (sm.at(x + 2) - sm.at(x - 2)) / 4;
    const d = (y - b.curve.at(x)) / Math.max(5, b.amp * 1.4);
    return clamp(0.42 + sl * c.lightX * 1.7 + d * 0.22 + N.n2(x * 0.04, y * 0.07) * 0.16, 0, 1);
  };
  const pen = farPen(b.t, r);
  let maxD = 0;
  for (let x = 0; x <= W; x += 2) maxD = Math.max(maxD, Math.min(b.Ec.at(x), H) - b.curve.at(x));
  const depthK = Math.max(6, b.amp * 2.2);
  for (let D = sp * 0.9, q = 0; D < maxD + 1; D += sp * (1 + 0.02 * q), q++) {
    const f = Math.min(1, D / depthK);
    const pts = [];
    for (let x = -2; x <= W + 2; x += 0.8) pts.push(x, lerp(b.curve.at(x), lerp(sm.at(x), flat.at(x), f), f) + D);
    const thr = [0.16, 0.36, 0.52][q % 3];
    const pred = (x, y) => y < b.Ec.at(x) && y > b.curve.at(x) + 0.3 && shade(x, y) + N.n2(x * 0.3, y * 0.3) * 0.06 > thr;
    for (const pc of clipPred(pts, pred, 0.4)) sc.line(pc, pen, TEX);
  }
  let y0 = Infinity, y1 = -Infinity;
  for (let x = 0; x <= W; x += 2) { y0 = Math.min(y0, b.curve.at(x)); y1 = Math.max(y1, Math.min(b.Ec.at(x), H)); }
  const box = [-2, y0, W + 2, y0, W + 2, y1, -2, y1];
  const ang = c.lightX < 0 ? -PI / 3 : PI / 3;
  const pred2 = (x, y) => y > b.curve.at(x) + 0.35 && y < b.Ec.at(x) && shade(x, y) > 0.76;
  for (const sg of hatchPoly(box, ang, sp * 2, r.rnd() * sp)) for (const pc of clipPred(sg, pred2, 0.4)) sc.line(pc, pen, TEX);
  ridgeLine(sc, b, b.t < 0.3 ? TINT : KEY);
}
function prairieBand(sc, b) {
  const r = sc.rng('prairie' + b.k), W = sc.W;
  const top = b.curve, bot = b.Ec;
  const pen = b.t < 0.4 ? TINT : FLORA;
  let y = Infinity;
  for (let x = 0; x <= W; x += 2) y = Math.min(y, Math.min(bot.at(x), sc.H + 1));
  let ymax = -Infinity;
  for (let x = 0; x <= W; x += 2) ymax = Math.max(ymax, Math.min(bot.at(x), sc.H + 1));
  for (let yy = ymax; yy > -10; yy -= lerp(0.5, 1.1, b.t) / Math.sqrt(sc.dens)) {
    let any = false;
    for (let x = r.range(0, 1); x < W + 1; x += r.range(0.35, 1.0) / Math.sqrt(sc.dens)) {
      const tt = top.at(x);
      if (yy < tt - 0.2 || yy > bot.at(x)) continue;
      any = true;
      const d = clamp((yy - tt) / Math.max(3, bot.at(x) - tt), 0, 1);
      const h = lerp(0.6, 2.2, d) * lerp(0.8, 1.4, b.t) * r.range(0.6, 1.3);
      const lean = r.range(-0.25, 0.25) + sc.noise.n2(x * 0.03, yy * 0.03) * 0.4;
      const pts = [x, yy, x + lean * h * 0.4, yy - h * 0.5, x + lean * h, yy - h];
      if (r.chance(0.025 * sc.P.weights.flora * 2) && sc.comp.season !== 'winter') sc.fleck(x + lean * h, yy - h - 0.2, 0, 0.35, ACC);
      sc.line(pts, pen, ORG); sc.halo(pts, sc.penW * 1.4);
    }
    if (!any && yy < y - 4) break;
  }
}
function waterBand(sc, b) {
  const r = sc.rng('water' + b.k), W = sc.W, c = sc.comp, N = sc.noise, v = sc.view;
  const y0 = b.mean;
  let maxY = -Infinity;
  for (let x = 0; x <= W; x += 1) maxY = Math.max(maxY, Math.min(b.Ec.at(x), sc.H + 1));
  if (maxY <= y0 + 0.5) return;
  const below = (x, y) => y < b.Ec.at(x) - 0.2;
  // far-shore reflections: short vertical strokes under the shoreline
  for (let x = -1; x < W + 1; x += r.range(0.5, 1.1)) {
    if (N.n2(x * 0.08, y0 * 0.1) < -0.1) continue;
    const L = r.range(0.4, 2.2) * (1 + N.n2(x * 0.05, 7));
    for (const pc of clipPred([x, y0 + 0.5, x, y0 + 0.5 + L], below, 0.3)) sc.line(pc, TINT, TEX);
  }
  let y = y0 + r.range(1.2, 2.2), q = 0;
  while (y < maxY) {
    const d = (y - y0) / Math.max(4, maxY - y0);
    const sp = lerp(0.6, 2.6, Math.pow(d, 0.8)) / Math.sqrt(sc.dens);
    const pts = [];
    for (let x = -2; x <= W + 2; x += 1) pts.push(x, y + N.n2(x * 0.02, q) * 0.15);
    const thr = lerp(-0.25, 0.25, d);
    for (const pc of clipPred(pts, (px, py) => below(px, py) && N.n2(px * lerp(0.09, 0.03, d), py * 0.5 + q) > thr, 0.4)) sc.line(pc, q % 4 === 0 ? KEY : TINT, TEX);
    y += sp * r.range(0.85, 1.15); q++;
  }
  if (c.time !== 'night' || r.chance(0.6)) {
    const sx = v.x0 + c.sunX * (v.x1 - v.x0);
    for (let yy = y0 + 0.8; yy < maxY; yy += r.range(0.55, 0.9)) {
      const d = (yy - y0) / Math.max(4, maxY - y0), w = lerp(1.5, 9, d);
      const n = r.int(1, 3);
      for (let k = 0; k < n; k++) {
        const cx = sx + r.gauss() * w * 0.45, L = r.range(0.6, 2.5) * lerp(0.6, 1.6, d);
        if (below(cx, yy)) sc.seg(cx - L / 2, yy, cx + L / 2, yy, ACC, TEX);
      }
    }
  }
  sc.line([-2, y0, W + 2, y0], KEY, ORG);
}
function rockFaces(sc, b) {
  if (!b.blocks) return;
  const r = sc.rng('rock' + b.k), lx = sc.comp.lightX;
  for (const k of b.blocks) {
    const cliffH = Math.max(2, (b.mean + b.amp) - k.topY) * r.range(0.45, 0.75);
    const xa = k.a - k.e, xb = k.b + k.e;
    // strata
    let y = k.topY + r.range(0.3, 0.9);
    const yEnd = k.topY + cliffH;
    while (y < yEnd) {
      const pts = [];
      for (let x = xa; x <= xb; x += 0.6) pts.push(x, y + sc.noise.n2(x * 0.15, y) * 0.25);
      const inside = (x, yy) => yy > b.curve.at(x) + 0.25 && sc.noise.n2(x * 0.3, yy * 2.1) > -0.45;
      for (const pc of clipPred(pts, inside, 0.3)) sc.line(pc, KEY, TEX);
      y += r.range(0.7, 2.6) * lerp(0.6, 1.2, b.t);
    }
    // joints
    const nj = r.int(2, 6);
    for (let q = 0; q < nj; q++) {
      const x = r.range(k.a, k.b), y0 = b.curve.at(x) + 0.3, len = cliffH * r.range(0.3, 0.9);
      const pts = []; let xx = x;
      for (let yy = y0; yy < y0 + len; yy += 0.8) { pts.push(xx, yy); xx += r.range(-0.25, 0.25); }
      sc.line(pts, KEY, ORG);
    }
    // shadow flank hatch
    const side = lx < 0 ? 1 : -1;
    const fx0 = side > 0 ? k.b - (k.b - k.a) * 0.12 : k.a - k.e, fx1 = side > 0 ? k.b + k.e : k.a + (k.b - k.a) * 0.12;
    for (let x = fx0; x < fx1; x += 0.55) {
      const yt = b.curve.at(x) + 0.3;
      sc.seg(x, yt, x, yt + cliffH * r.range(0.6, 1), KEY, TEX);
    }
    // talus
    const nt = Math.round((xb - xa) * 2.5 * sc.dens);
    for (let q = 0; q < nt; q++) {
      const x = r.range(xa - 3, xb + 3), yy = yEnd + Math.abs(r.gauss()) * cliffH * 0.4;
      if (yy > b.curve.at(x)) sc.fleck(x, yy, r.rnd() * PI, 0.3, KEY);
    }
    const tal = cliffH * 0.5, poly = [];
    for (let x = xa - tal; x <= xb + tal; x += 0.5) poly.push(x, Math.max(b.curve.at(x), Math.min(yEnd, k.topY + (Math.max(0, xa - x, x - xb) / tal) * cliffH)));
    poly.push(xb + tal, yEnd + 0.5, xa - tal, yEnd + 0.5);
    sc.fill(poly);
  }
}

/* --- foreground: meadow / snow ------------------------------------------- */
function plantPick(sc, r, dT, drift) {
  const c = sc.comp, w = sc.P.weights.flora;
  const fl = (c.season === 'winter' ? 0.3 : c.season === 'autumn' ? 0.7 : 1) * w * (drift ?? 1);
  const f = dT < 0.12 ? 0 : fl;
  const list = c.season === 'spring'
    ? [['blade', 70], ['seed', 4], ['fork', 2], ['seedball', 2.5 * f], ['daisy', 2 * f], ['umbel', 1.2 * f], ['bud', 2 * f]]
    : c.season === 'autumn'
      ? [['blade', 62], ['seed', 9], ['fork', 6], ['umbel', 2.2 * f], ['seedball', 1.5 * f], ['thistle', 1.4 * f], ['plume', 3 * f], ['daisy', 0.8 * f]]
      : c.season === 'winter'
        ? [['blade', 40], ['seed', 12], ['fork', 8], ['umbel', 4], ['seedball', 1.5], ['thistle', 2]]
        : [['blade', 66], ['seed', 6], ['fork', 4], ['cone', 2.6 * f], ['umbel', 2 * f], ['daisy', 2 * f], ['balm', 1.4 * f], ['seedball', 0.8 * f], ['thistle', 1 * f]];
  return r.weighted(list);
}
function tallGround(sc, b, items) {
  const r = sc.rng('meadow' + b.k), W = sc.W, H = sc.H, c = sc.comp, N = sc.noise;
  const winter = b.treat === 'snow';
  const prairie = b.treat === 'prairie';
  let top = Infinity;
  for (let x = 0; x <= W; x += 1) top = Math.min(top, b.curve.at(x));
  const bottom = Math.min(H + 8, sc.view.y1 + 8);
  const hMax = (bottom - top) * (prairie ? 0.2 : winter ? 0.3 : r.range(0.3, 0.52));
  const dens = sc.dens * (winter ? 0.3 : prairie ? 0.7 : 1);
  const tuftK = winter ? r.range(1, 2) : prairie ? r.range(1.2, 2.4) : r.range(2.5, 5.5);
  const rows = [];
  for (let y = bottom; y > top - 1.5;) {
    const dT = clamp((y - top) / (bottom - top), 0, 1);
    rows.push({ y, dT });
    y -= lerp(0.35, 2.3, dT) / Math.sqrt(dens);
  }
  let oi = 0;
  const fgPens = c.season === 'autumn' ? [[FLORA, 3], [ACC, 1.2], [KEY, 2]] : c.season === 'winter' ? [[KEY, 3], [TINT, 1]] : c.season === 'spring' ? [[FLORA, 5], [KEY, 1.2]] : [[FLORA, 5], [KEY, 1.8]];
  const ps = r.range(0.012, 0.03), fs = r.range(0.02, 0.05);
  for (const row of rows) {
    while (oi < items.length && items[oi].y >= row.y) items[oi++].draw(sc);
    const { y, dT } = row;
    const sx = lerp(0.6, 3.4, dT) * Math.sqrt(tuftK / 3) / Math.sqrt(dens);
    for (let x = -3 + r.rnd() * sx; x < W + 3; x += sx * r.range(0.5, 1.5)) {
      if (y < b.curve.at(x) - 0.25) continue;
      const patch = N.fbm(x * ps, y * ps * 1.8 + 70, 3);
      if (r.rnd() > 0.68 + patch * 0.7) continue;
      const yy = y + r.range(-0.4, 0.4) * sx * 0.5;
      const drift = smooth(-0.15, 0.55, N.fbm(x * fs + 300, y * fs * 1.5, 2));
      const kind = plantPick(sc, r, dT, 0.25 + drift * 2.2);
      const scale = lerp(0.04, 1, Math.pow(dT, 1.5));
      const tall = clamp(0.75 + patch * 0.7, 0.35, 1.35);
      const h = Math.max(0.6, hMax * scale * tall * r.range(0.55, 1.15));
      const wind = N.n2(x * 0.015, yy * 0.02) * 0.45 + c.windBias;
      if (kind === 'blade') tuft(sc, x, yy, h, wind, r, r.weighted(fgPens), tuftK);
      else plant(sc, kind, x, yy, h * r.range(0.9, 1.25), wind, dT, r, r.weighted(fgPens), c.season === 'winter');
    }
  }
  while (oi < items.length) items[oi++].draw(sc);
  if (winter) {
    // drift lines in the snow
    const n = r.int(5, 12);
    for (let q = 0; q < n; q++) {
      const y = lerp(top + 2, bottom - 4, r.rnd()), x0 = r.range(-10, W), L = r.range(15, 60);
      const pts = [];
      for (let x = x0; x < x0 + L; x += 1) pts.push(x, y + Math.sin((x - x0) / L * PI) * -r.range(0.2, 1.5));
      sc.line(pts, TINT, TEX);
    }
  }
}
function tuft(sc, x, y, h, wind, r, pen, k) {
  const n = Math.max(1, Math.round(k * r.range(0.5, 1.5)));
  const spread = r.range(0.15, 0.45), pw = sc.penW;
  const idx = [];
  for (let i = 0; i < n; i++) idx.push(i);
  idx.sort((a, b) => Math.abs(a - (n - 1) / 2) - Math.abs(b - (n - 1) / 2));
  for (const i of idx) {
    const u = n === 1 ? 0 : i / (n - 1) - 0.5;
    const lean = -wind * 0.35 - u * spread * 2 + r.range(-0.07, 0.07);
    const bh = h * r.range(0.5, 1) * (1 - Math.abs(u) * 0.55);
    const bend = -(lean + wind * 0.35) * r.range(0.4, 1.6) + wind * r.range(0.3, 1.1) + r.gauss() * 0.18;
    const bx = x + u * Math.min(1.6, h * 0.07);
    const pts = bladePts(bx, y, bh, lean, bend);
    const wd = bh * r.range(0.022, 0.042);
    if (wd > pw * 1.4 && bh > 6) { const out = widen(pts, wd); sc.line(out, pen, ORG); sc.fill(out); sc.halo(out, pw * 1.1); }
    else { sc.line(pts, pen, ORG); sc.halo(pts, Math.max(pw * 1.7, wd)); }
  }
}
function bladePts(x, y, h, lean, bend) {
  const n = clamp(Math.round(h / 1.0) + 3, 4, 18);
  const pts = [x, y], step = h / n;
  let px = x, py = y;
  for (let i = 1; i <= n; i++) {
    const t = i / n, a = HALF + lean - bend * t * t;
    px += step * Math.cos(a); py -= step * Math.sin(a);
    pts.push(px, py);
  }
  return pts;
}
function widen(pts, w0, taper) {
  const n = pts.length >> 1, L = [], Rr = [];
  for (let i = 0; i < n; i++) {
    const a = Math.max(0, i - 1), b = Math.min(n - 1, i + 1);
    let tx = pts[2 * b] - pts[2 * a], ty = pts[2 * b + 1] - pts[2 * a + 1];
    const l = Math.hypot(tx, ty) || 1; tx /= l; ty /= l;
    const w = w0 * Math.pow(1 - i / (n - 1), taper || 0.85) / 2;
    L.push(pts[2 * i] - ty * w, pts[2 * i + 1] + tx * w);
    Rr.push(pts[2 * i] + ty * w, pts[2 * i + 1] - tx * w);
  }
  return L.concat(revPts(Rr).slice(2));
}
function stem(sc, x, y, h, lean, pen) {
  const pts = bladePts(x, y, h, lean * 0.5, lean * 0.4);
  return pts;
}
function drawStem(sc, pts, pen) { sc.line(pts, pen, ORG); sc.halo(pts, sc.penW * 1.6); }
function plant(sc, kind, x, y, h, wind, dT, r, pen, winter) {
  const pw = sc.penW;
  if (kind === 'blade') {
    const bend = (r.range(-1, 1) * lerp(0.15, 1.5, r.rnd() * r.rnd())) + wind * 0.9;
    const pts = bladePts(x, y, h, wind * 0.5, bend);
    const wd = h * r.range(0.018, 0.04);
    if (wd > pw * 1.4 && h > 6) {
      const out = widen(pts, wd);
      sc.line(out, pen, ORG);
      if (wd > pw * 3 && r.chance(0.5)) sc.line(pts.slice(0, Math.floor(pts.length * 0.6) & ~1), pen, TEX);
      sc.fill(out);
      sc.halo(out, pw * 1.2);
    } else { sc.line(pts, pen, ORG); sc.halo(pts, Math.max(pw * 1.7, wd)); }
    return;
  }
  const st = stem(sc, x, y, h, wind, pen);
  const hx = st[st.length - 2], hy = st[st.length - 1];
  const s = Math.max(0.35, h * 0.09);
  const accent = winter ? KEY : ACC;
  switch (kind) {
    case 'seed': {
      const n = r.int(4, 8), dir = r.sign();
      for (let i = 0; i < n; i++) {
        const k = st.length / 2 - 1 - Math.floor(i * 0.7);
        if (k < 1) break;
        const px = st[2 * k], py = st[2 * k + 1], a = HALF + dir * (i % 2 ? 1 : -1) * r.range(0.4, 0.9) + wind * 0.5;
        const L = s * r.range(0.8, 1.4);
        const leaf = widen([px, py, px + Math.cos(a) * L, py - Math.sin(a) * L], s * 0.45, 0.5);
        sc.loop(leaf, pen, ORG); sc.fill(leaf);
      }
      drawStem(sc, st, pen);
      break;
    }
    case 'fork': {
      for (let q = -1; q <= 1; q++) {
        const a = HALF + wind * 0.4 + q * r.range(0.25, 0.5), L = s * r.range(2, 3.2);
        const pr = bladePts(hx, hy, L, a - HALF, q * 0.4);
        sc.line(pr, pen, ORG); sc.halo(pr, pw * 1.4);
      }
      drawStem(sc, st, pen);
      break;
    }
    case 'cone': {
      const cr = s * 0.9, cx = hx, cy = hy - cr * 0.5;
      const cone = arcPts(cx, cy, cr * 0.55, cr * 0.75, PI + 0.2, -0.2, 14);
      sc.line(cone, KEY, ORG);
      for (let i = 0; i < Math.round(cr * 6); i++) sc.fleck(cx + r.range(-0.35, 0.35) * cr, cy - r.range(0, 0.6) * cr, r.rnd() * PI, 0.2, KEY);
      const cpoly = cone.slice(); sc.fill(cpoly);
      const np = r.int(6, 10);
      for (let i = 0; i < np; i++) {
        const a = -HALF + (i / (np - 1) - 0.5) * r.range(2.2, 2.9);
        const L = cr * r.range(1.5, 2.2);
        const p0x = cx + Math.cos(a + HALF) * cr * 0.4 * Math.sign(Math.cos(a)), p0y = cy + cr * 0.15;
        const pet = widen([p0x, p0y, p0x + Math.cos(a) * L * 0.5, p0y - Math.sin(a) * L * 0.5 - cr * 0.1, p0x + Math.cos(a) * L, p0y - Math.sin(a) * L], cr * 0.38, 0.6);
        sc.loop(pet, accent, ORG); sc.fill(pet);
      }
      drawStem(sc, st, pen);
      break;
    }
    case 'umbel': {
      const rays = r.int(9, 16), R0 = s * r.range(1.6, 2.4);
      const tips = [];
      for (let i = 0; i < rays; i++) {
        const a = lerp(0.25, PI - 0.25, i / (rays - 1)) + r.range(-0.08, 0.08);
        tips.push([hx + Math.cos(a) * R0, hy - Math.sin(a) * R0 * 0.7]);
      }
      for (const [tx, ty] of tips) {
        const fr = s * r.range(0.22, 0.4);
        if (winter) { sc.fleck(tx, ty, r.rnd() * PI, 0.3, KEY); continue; }
        const fl = circlePts(tx, ty, fr, 8);
        sc.loop(fl, ACC, ORG); sc.fill(fl);
      }
      for (const [tx, ty] of tips) { const ray = [hx, hy, tx, ty]; sc.line(ray, pen, ORG); sc.halo(ray, pw * 1.2); }
      drawStem(sc, st, pen);
      break;
    }
    case 'daisy': {
      const cr = s * 0.42, np = r.int(10, 16), L = s * r.range(1.3, 1.9), tilt = r.range(0.45, 0.85);
      const disc = circlePts(hx, hy, cr, 12);
      sc.loop(disc, KEY, ORG);
      sc.fill(disc);
      for (let i = 0; i < np; i++) {
        const a = TAU * i / np + r.range(-0.1, 0.1);
        const ex = hx + Math.cos(a) * (cr + L), ey = hy - Math.sin(a) * (cr + L) * tilt;
        const pet = widen([hx + Math.cos(a) * cr, hy - Math.sin(a) * cr * tilt, ex, ey], s * 0.32, 0.5);
        sc.loop(pet, accent, ORG); sc.fill(pet);
      }
      drawStem(sc, st, pen);
      break;
    }
    case 'balm': {
      const cr = s * r.range(0.8, 1.2);
      const n = r.int(16, 26);
      for (let i = 0; i < n; i++) {
        const a = r.range(-0.3, PI + 0.3), L = cr * r.range(0.9, 1.4);
        const sp = [hx + Math.cos(a) * cr * 0.25, hy - Math.sin(a) * cr * 0.25, hx + Math.cos(a) * L, hy - Math.sin(a) * L];
        sc.line(sp, ACC, ORG); sc.halo(sp, pw * 1.2);
      }
      drawStem(sc, st, pen);
      break;
    }
    case 'seedball': {
      const cr = s * r.range(1.1, 1.7), n = r.int(18, 32);
      for (let i = 0; i < n; i++) {
        const a = TAU * i / n + r.range(-0.1, 0.1);
        if (a > PI * 1.25 && a < PI * 1.75) continue;
        const ex = hx + Math.cos(a) * cr, ey = hy - Math.sin(a) * cr;
        sc.line([hx + Math.cos(a) * cr * 0.15, hy - Math.sin(a) * cr * 0.15, ex, ey], winter ? KEY : TINT, ORG);
        const f = cr * 0.18;
        sc.line([ex + Math.cos(a + 0.6) * f, ey - Math.sin(a + 0.6) * f, ex, ey, ex + Math.cos(a - 0.6) * f, ey - Math.sin(a - 0.6) * f], winter ? KEY : TINT, ORG);
      }
      sc.mask.disc(hx, hy, cr * 0.25);
      drawStem(sc, st, pen);
      break;
    }
    case 'thistle': {
      const bw = s * 0.8, bh = s * 1.0;
      const bulb = arcPts(hx, hy - bh * 0.5, bw * 0.5, bh * 0.55, PI * 1.15, -PI * 0.15, 16);
      sc.line(bulb, pen, ORG);
      for (const sg of hatchPoly(bulb, PI / 4, Math.max(0.5, bw * 0.22), 0)) sc.line(sg, pen, TEX);
      for (const sg of hatchPoly(bulb, -PI / 4, Math.max(0.5, bw * 0.22), 0)) sc.line(sg, pen, TEX);
      sc.fill(bulb);
      const n = r.int(9, 15), ty = hy - bh * 0.95;
      for (let i = 0; i < n; i++) {
        const a = lerp(0.35, PI - 0.35, i / (n - 1)), L = bh * r.range(0.6, 0.95);
        const tuft = [hx + Math.cos(a) * bw * 0.2, ty + 0.2, hx + Math.cos(a) * L, ty - Math.sin(a) * L];
        sc.line(tuft, winter ? KEY : ACC, ORG); sc.halo(tuft, pw * 1.2);
      }
      drawStem(sc, st, pen);
      break;
    }
    case 'plume': {
      const n = r.int(4, 8), dir = r.sign();
      for (let i = 0; i < n; i++) {
        const k = st.length / 2 - 1 - i;
        if (k < 1) break;
        const px = st[2 * k], py = st[2 * k + 1], a = HALF * 0.6 * dir + (dir < 0 ? PI : 0) + r.range(-0.3, 0.3);
        const L = s * r.range(1.2, 2.2) * (1 - i / n * 0.5);
        const br = bladePts(px, py, L, a - HALF, -dir * 0.8);
        sc.line(br, pen, ORG);
        for (let q = 2; q < br.length; q += 2) sc.fleck(br[q], br[q + 1] - 0.3, 0, 0.35, ACC);
      }
      drawStem(sc, st, pen);
      break;
    }
    case 'bud': {
      const cr = s * 0.6;
      const bud = arcPts(hx, hy - cr * 0.8, cr * 0.55, cr, PI * 1.3, -PI * 0.3, 12);
      sc.line(bud, ACC, ORG); sc.fill(bud);
      drawStem(sc, st, pen);
      break;
    }
    default: drawStem(sc, st, pen);
  }
}

/* ----------------------------------------------------------------- trees */
function colonize(r, A, root, o) {
  const seg = o.seg, infl = o.infl, infl2 = infl * infl, kill2 = o.kill * o.kill, dup2 = (seg * 0.4) * (seg * 0.4);
  const X = [], Y = [], Par = [];
  const cs = infl, grid = new Map();
  const gk = (gx, gy) => (gx + 20000) * 40000 + (gy + 20000);
  const add = (x, y, p) => {
    const id = X.length; X.push(x); Y.push(y); Par.push(p);
    const k = gk(Math.floor(x / cs), Math.floor(y / cs));
    let a = grid.get(k); if (!a) grid.set(k, (a = [])); a.push(id);
    return id;
  };
  const na = A.length >> 1, alive = new Uint8Array(na).fill(1);
  let nAlive = na;
  let cur = add(root[0], root[1], -1), tx = root[0], ty = root[1];
  for (let s = 0; s < 500; s++) {
    let near = false;
    for (let i = 0; i < na; i++) { const dx = A[2 * i] - tx, dy = A[2 * i + 1] - ty; if (dx * dx + dy * dy < infl2) { near = true; break; } }
    if (near) break;
    tx += (o.up[0] + r.range(-1, 1) * (o.wob || 0)) * seg; ty += o.up[1] * seg;
    cur = add(tx, ty, cur);
  }
  for (let it = 0; it < (o.maxIter || 300) && nAlive > 0; it++) {
    const acc = new Map();
    for (let i = 0; i < na; i++) {
      if (!alive[i]) continue;
      const ax = A[2 * i], ay = A[2 * i + 1];
      const gx = Math.floor(ax / cs), gy = Math.floor(ay / cs);
      let best = -1, bd = infl2;
      for (let ddx = -1; ddx <= 1; ddx++) for (let ddy = -1; ddy <= 1; ddy++) {
        const arr = grid.get(gk(gx + ddx, gy + ddy)); if (!arr) continue;
        for (let q = 0; q < arr.length; q++) { const id = arr[q], dx = ax - X[id], dy = ay - Y[id], d2 = dx * dx + dy * dy; if (d2 < bd) { bd = d2; best = id; } }
      }
      if (best < 0) continue;
      if (bd < kill2) { alive[i] = 0; nAlive--; continue; }
      const d = Math.sqrt(bd);
      let v = acc.get(best); if (!v) acc.set(best, (v = [0, 0, 0]));
      v[0] += (ax - X[best]) / d; v[1] += (ay - Y[best]) / d; v[2]++;
    }
    if (!acc.size) break;
    let grew = 0;
    for (const [id, v] of acc) {
      let dx = v[0] / v[2] + o.trop[0] + r.range(-0.08, 0.08), dy = v[1] / v[2] + o.trop[1] + r.range(-0.08, 0.08);
      const L = Math.hypot(dx, dy); if (L < 1e-6) continue;
      dx /= L; dy /= L;
      const nx = X[id] + dx * seg, ny = Y[id] + dy * seg;
      const gx = Math.floor(nx / cs), gy = Math.floor(ny / cs);
      let dup = false;
      for (let ddx = -1; ddx <= 1 && !dup; ddx++) for (let ddy = -1; ddy <= 1 && !dup; ddy++) {
        const arr = grid.get(gk(gx + ddx, gy + ddy)); if (!arr) continue;
        for (let q = 0; q < arr.length; q++) { const j = arr[q], ex = nx - X[j], ey = ny - Y[j]; if (ex * ex + ey * ey < dup2) { dup = true; break; } }
      }
      if (dup) continue;
      add(nx, ny, id); grew++;
    }
    if (!grew) break;
  }
  const n = X.length, kids = Array.from({ length: n }, () => []);
  for (let i = 1; i < n; i++) if (Par[i] >= 0) kids[Par[i]].push(i);
  const th = new Float64Array(n), e = o.pipe || 2.3;
  for (let i = n - 1; i >= 0; i--) {
    if (!kids[i].length) th[i] = 1;
    else { let s = 0; for (const k of kids[i]) s += Math.pow(th[k], e); th[i] = Math.pow(s, 1 / e); }
  }
  return { X, Y, Par, kids, th, n };
}
function chainsOf(T) {
  const chains = [], stack = [[0, -1]];
  while (stack.length) {
    const [start, par] = stack.pop();
    const ch = par >= 0 ? [par, start] : [start];
    let cur = start;
    while (T.kids[cur].length) {
      const ks = T.kids[cur].slice().sort((a, b) => T.th[b] - T.th[a]);
      for (let q = 1; q < ks.length; q++) stack.push([ks[q], cur]);
      cur = ks[0]; ch.push(cur);
    }
    chains.push(ch);
  }
  return chains;
}
// draw branch chains thick-to-thin; returns nothing (fills its own silhouette)
function drawBranches(sc, T, scale, o) {
  const chains = chainsOf(T), pw = sc.penW, lx = sc.comp.lightX;
  const items = chains.map((ch) => ({ ch, w: T.th[ch.length > 1 ? ch[1] : ch[0]] * scale }));
  items.sort((a, b) => b.w - a.w);
  const baseY = T.Y[0], topY = Math.min(...T.Y);
  for (const it of items) {
    const ch = it.ch;
    if (ch.length < 2) continue;
    let pts = [], ws = [];
    for (let i = 0; i < ch.length; i++) {
      const id = ch[i];
      let w = T.th[i === 0 && ch.length > 1 ? ch[1] : id] * scale;
      if (ch[0] === 0 && o.flare) { const hf = clamp((baseY - T.Y[id]) / Math.max(1, baseY - topY), 0, 1); w *= 1 + o.flare * Math.pow(Math.max(0, 1 - hf * 6), 2); }
      pts.push(T.X[id], T.Y[id]); ws.push(w);
    }
    // smooth position and width together
    for (let k = 0; k < 2; k++) {
      const n = pts.length >> 1; if (n < 3) break;
      const np = [pts[0], pts[1]], nw = [ws[0]];
      for (let i = 0; i < n - 1; i++) {
        np.push(0.75 * pts[2 * i] + 0.25 * pts[2 * i + 2], 0.75 * pts[2 * i + 1] + 0.25 * pts[2 * i + 3], 0.25 * pts[2 * i] + 0.75 * pts[2 * i + 2], 0.25 * pts[2 * i + 1] + 0.75 * pts[2 * i + 3]);
        nw.push(0.75 * ws[i] + 0.25 * ws[i + 1], 0.25 * ws[i] + 0.75 * ws[i + 1]);
      }
      np.push(pts[2 * n - 2], pts[2 * n - 1]); nw.push(ws[n - 1]);
      pts = np; ws = nw;
    }
    const maxW = Math.max(...ws);
    if (maxW > pw * 2.2) {
      const n = pts.length >> 1, L = [], Rr = [];
      for (let i = 0; i < n; i++) {
        const a = Math.max(0, i - 1), b = Math.min(n - 1, i + 1);
        let tx = pts[2 * b] - pts[2 * a], ty = pts[2 * b + 1] - pts[2 * a + 1];
        const l = Math.hypot(tx, ty) || 1; tx /= l; ty /= l;
        const w = Math.max(ws[i], pw * 0.9) / 2;
        L.push(pts[2 * i] - ty * w, pts[2 * i + 1] + tx * w);
        Rr.push(pts[2 * i] + ty * w, pts[2 * i + 1] - tx * w);
      }
      sc.line(L, o.pen, ORG); sc.line(Rr, o.pen, ORG);
      if (ws[n - 1] > pw * 1.5) sc.line([L[2 * n - 2], L[2 * n - 1], Rr[2 * n - 2], Rr[2 * n - 1]], o.pen, ORG);
      if (maxW > 2.2 && o.bark) bark(sc, pts, ws, o, lx);
      sc.mask.stampVar(pts, ws.map((w) => Math.max(w, pw * 0.9) + pw * 0.6));
    } else {
      sc.line(pts, o.pen, ORG);
      sc.halo(pts, Math.max(pw * 1.5, maxW));
    }
  }
}
function bark(sc, pts, ws, o, lx) {
  const r = o.r, n = pts.length >> 1;
  const lines = r.int(2, 4);
  for (let q = 0; q < lines; q++) {
    const f = (lx < 0 ? 1 : -1) * r.range(0.05, 0.38) * (q % 2 ? -0.6 : 1);
    let cur = [];
    for (let i = 0; i < n; i++) {
      if (ws[i] < 2) { if (cur.length >= 4) sc.line(cur, o.pen, TEX); cur = []; continue; }
      const a = Math.max(0, i - 1), b = Math.min(n - 1, i + 1);
      let tx = pts[2 * b] - pts[2 * a], ty = pts[2 * b + 1] - pts[2 * a + 1];
      const l = Math.hypot(tx, ty) || 1; tx /= l; ty /= l;
      const x = pts[2 * i] + ty * ws[i] * f, y = pts[2 * i + 1] - tx * ws[i] * f;
      if (sc.noise.n2(x * 0.4, y * 0.4 + q * 5) < -0.35) { if (cur.length >= 4) sc.line(cur, o.pen, TEX); cur = []; continue; }
      cur.push(x, y);
    }
    if (cur.length >= 4) sc.line(cur, o.pen, TEX);
  }
}
// one clump of foliage: lumpy scalloped outline plus shading marks on the shadow side
function foliageCluster(sc, cx, cy, rad, pen, penIn, r, opts) {
  const lx = sc.comp.lightX, N = sc.noise;
  const style = opts.style || 'cloud';
  const fine = style !== 'cloud';
  const k = fine ? clamp(Math.round(TAU * rad / r.range(1.1, 1.9)), 6, 90) : r.int(5, 9);
  const n = Math.max(20, k * (fine ? 6 : 4));
  const ph = r.range(0, TAU), sq = opts.sq || r.range(0.72, 0.95), nz = r.range(0, 900);
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const a = TAU * i / n;
    const lump = fine ? 1 + 0.17 * N.n2(Math.cos(a) * 1.2 + nz, Math.sin(a) * 1.2 - nz) : 1;
    const kk = lump * (1 - (fine ? 0.11 : 0.17) * (1 - Math.abs(Math.sin(k * a / 2 + ph)))) + r.range(-0.012, 0.012);
    pts.push(cx + rad * kk * Math.cos(a), cy - rad * kk * sq * Math.sin(a));
  }
  pts[pts.length - 2] = pts[0]; pts[pts.length - 1] = pts[1];
  sc.line(pts, pen, ORG);
  const sdx = lx < 0 ? 0.62 : -0.62, sdy = 0.78;
  if (style === 'cloud') {
    const m = rad > 3 ? r.int(3, 5) : rad > 1.5 ? 2 : 1;
    const ac = sdx > 0 ? -0.55 : PI + 0.55;
    for (let q = 0; q < m; q++) {
      const rr = rad * r.range(0.32, 0.78), span = r.range(0.35, 0.85);
      sc.line(arcPts(cx, cy, rr, rr * sq, ac - span, ac + span, Math.max(6, Math.round(rr * 4))), penIn, TEX);
    }
  } else {
    const area = PI * rad * rad * sq;
    const m = Math.round(area * (style === 'stipple' ? 2.2 : style === 'hatch' ? 0.75 : 0.8) * (opts.marks ?? 1) * sc.dens);
    const ha = sdx > 0 ? -PI / 3 : PI / 3;
    const ms = Math.min(1.25, 0.55 + rad * 0.07);
    for (let q = 0; q < m; q++) {
      const a = r.range(0, TAU), d = Math.sqrt(r.rnd()) * 0.86;
      const px = cx + Math.cos(a) * d * rad, py = cy - Math.sin(a) * d * rad * sq;
      const s = Math.cos(a) * d * sdx - Math.sin(a) * d * sdy;
      if (r.rnd() > smooth(-0.45, 0.7, s) * 0.95 + 0.03) continue;
      if (style === 'stipple') sc.fleck(px, py, r.rnd() * PI, 0.2, penIn);
      else if (style === 'hatch') { const L = ms * r.range(0.9, 1.6); sc.line([px - Math.cos(ha) * L / 2, py + Math.sin(ha) * L / 2, px + Math.cos(ha) * L / 2, py - Math.sin(ha) * L / 2], penIn, TEX); }
      else { const w = ms * r.range(0.75, 1.15), tilt = r.range(-0.35, 0.35); sc.line(arcPts(px, py, w / 2, w * 0.4, PI + 0.25 + tilt, TAU - 0.25 + tilt, 5), penIn, TEX); }
    }
  }
  sc.fill(pts);
}
function oak(sc, x, yb, ht, o) {
  o = o || {};
  const r = o.r || sc.rng('oak' + x.toFixed(3) + ':' + yb.toFixed(3));
  const season = o.season || sc.comp.season;
  const wd = o.wd || ht * r.range(0.95, 1.55);
  const trunkH = ht * r.range(0.2, 0.34);
  const crownTop = yb - ht, crownBot = yb - trunkH * 0.85;
  const ccx = x + r.range(-0.1, 0.1) * wd, ccy = (crownTop + crownBot) / 2;
  const rx = wd / 2, ry = (crownBot - crownTop) / 2;
  const lobes = [{ x: ccx, y: ccy, rx: rx * 0.85, ry: ry * 0.85 }];
  const nl = r.int(3, 6);
  for (let i = 0; i < nl; i++) {
    const a = r.range(0.1, PI - 0.1);
    lobes.push({ x: ccx + Math.cos(a) * rx * r.range(0.3, 0.6), y: ccy - Math.sin(a) * ry * r.range(0.1, 0.45), rx: rx * r.range(0.3, 0.55), ry: ry * r.range(0.3, 0.6) });
  }
  const seg = Math.max(0.45, ht / (o.segs || 75));
  const N = Math.round(clamp((wd * (crownBot - crownTop)) / (seg * seg * 5), 200, 1100) * (o.detail || 1));
  const A = [];
  for (let g = 0; g < N * 40 && A.length < N * 2; g++) {
    const px = ccx + r.range(-1, 1) * rx * 1.2, py = ccy + r.range(-1, 1) * ry * 1.2;
    if (py > crownBot) continue;
    for (const L of lobes) { const u = (px - L.x) / L.rx, v = (py - L.y) / L.ry; if (u * u + v * v < 1) { A.push(px, py); break; } }
  }
  const T = colonize(r, A, [x, yb + seg], { seg, infl: seg * r.range(9, 13), kill: seg * 2.2, trop: o.trop || [0, -0.05], up: [r.range(-0.06, 0.06), -1], wob: 0.25, maxIter: 400 });
  const trunkW = o.trunkW || ht * r.range(0.04, 0.065);
  const scale = trunkW / T.th[0];
  const pen = o.pen ?? KEY;
  // foliage clusters
  const fronts = [], backs = [];
  if (season !== 'winter') {
    const gs = wd / r.range(7, 12) * (o.clusterK || 1);
    const cells = new Map();
    const leafMax = r.range(1.5, 3.5);
    for (let i = 1; i < T.n; i++) {
      if (T.th[i] > leafMax) continue;
      const k = Math.floor(T.X[i] / gs) * 100003 + Math.floor(T.Y[i] / gs);
      let c = cells.get(k); if (!c) cells.set(k, (c = [0, 0, 0])); c[0] += T.X[i]; c[1] += T.Y[i]; c[2]++;
    }
    for (const c of cells.values()) {
      if (season === 'autumn' && r.chance(0.32)) continue;
      if (season === 'spring' && r.chance(0.2)) continue;
      const cl = { x: c[0] / c[2] + r.range(-0.2, 0.2) * gs, y: c[1] / c[2] + r.range(-0.2, 0.2) * gs, rad: gs * r.range(0.45, 0.78) * (season === 'spring' ? 0.75 : 1) * Math.min(1.3, 0.75 + c[2] * 0.04) };
      (r.chance(0.48) ? fronts : backs).push(cl);
    }
  }
  const fpen = () => season === 'autumn' ? r.weighted([[ACC, 2], [FLORA, 1.2], [KEY, 1]]) : season === 'spring' ? r.weighted([[FLORA, 3], [TINT, 1]]) : r.weighted([[FLORA, 3], [KEY, 1]]);
  const style = o.style || sc.comp.crownStyle;
  const drawC = (cl) => { const p = fpen(); foliageCluster(sc, cl.x, cl.y, cl.rad, p, p, r, { style }); };
  fronts.sort((a, b) => b.y - a.y).forEach(drawC);
  drawBranches(sc, T, scale, { pen, bark: true, r, flare: 0.8 });
  backs.sort((a, b) => b.y - a.y).forEach(drawC);
  if (sc.comp.time !== 'night' && o.shadow !== false) {
    const sx = x - sc.comp.lightX * ht * 0.14, rx = wd * r.range(0.32, 0.46), ry = Math.max(0.9, ht * 0.03);
    for (let yy = yb - ry * 0.55; yy < yb + ry; yy += 0.62) {
      const f = 1 - Math.pow((yy - yb) / ry, 2);
      if (f <= 0) continue;
      const hw = rx * Math.sqrt(f) * r.range(0.82, 1.04);
      sc.line([sx - hw, yy, sx + hw, yy], KEY, TEX);
    }
  }
  if (season === 'autumn') {
    const n = Math.round(wd * 0.4 * sc.dens);
    for (let i = 0; i < n; i++) {
      const lxp = x + r.gauss() * wd * 0.35, lyp = yb - r.rnd() * ht * 0.5;
      sc.fleck(lxp, lyp, r.rnd() * PI, 0.5, ACC);
    }
  }
}
function pine(sc, x, yb, ht, o) {
  o = o || {};
  const r = o.r || sc.rng('pine' + x.toFixed(3));
  const pen = KEY, fp = FLORA;
  const lean = r.range(-0.1, 0.1), wind = r.sign() * r.range(0.25, 0.8);
  const NT = 30, trunk = [], wv = r.range(1, 2.2), wph = r.range(0, TAU);
  for (let i = 0; i <= NT; i++) { const t = i / NT; trunk.push(x + lean * ht * t + Math.sin(t * PI * wv + wph) * ht * 0.025, yb - ht * t); }
  const tw = ht * r.range(0.035, 0.05);
  const tiers = r.int(7, 12);
  const pads = [], limbs = [];
  for (let i = 0; i < tiers; i++) {
    const t = clamp(lerp(0.3, 0.97, i / (tiers - 1)) + r.range(-0.025, 0.025), 0.2, 1);
    const k = Math.round(t * NT), tx = trunk[2 * k], ty = trunk[2 * k + 1];
    const nb = t > 0.92 ? 1 : r.weighted([[1, 2], [2, 3], [3, 1]]);
    for (let q = 0; q < nb; q++) {
      const side = nb >= 2 ? (q % 2 ? 1 : -1) : r.sign();
      const windy = side === Math.sign(wind) ? 1 + Math.abs(wind) * 0.8 : 1 - Math.abs(wind) * 0.55;
      const L = ht * r.range(0.13, 0.32) * (1 - t * 0.5) * windy * (q === 2 ? 0.5 : 1);
      const droop = r.range(-0.06, 0.12);
      const limb = chaikin([tx, ty, tx + side * L * 0.4, ty - L * 0.14, tx + side * L * 0.78, ty - L * 0.08, tx + side * L, ty + L * droop], 2);
      limbs.push({ pts: limb, w: tw * (1 - t) * 0.6 + 0.25 });
      const np = r.int(2, 4);
      for (let p = 0; p < np; p++) {
        const f = lerp(0.3, 1.0, np === 1 ? 1 : p / (np - 1)) + r.range(-0.05, 0.05);
        const li = Math.min(limb.length / 2 - 1, Math.round(f * (limb.length / 2 - 1)));
        const pwid = L * r.range(0.38, 0.62) * (0.75 + f * 0.45) + ht * 0.02;
        pads.push({ x: limb[2 * li], y: limb[2 * li + 1] - 0.4, w: pwid, h: pwid * r.range(0.24, 0.4), front: r.chance(0.55) });
      }
    }
  }
  const tx = trunk[2 * NT], ty = trunk[2 * NT + 1];
  for (let q = 0; q < r.int(2, 3); q++) pads.push({ x: tx + r.range(-1, 1) * ht * 0.04, y: ty + q * ht * 0.035 + 0.4, w: ht * r.range(0.1, 0.18), h: ht * r.range(0.04, 0.06), front: true });
  const drawPad = (p) => {
    const n = 18, top = [], bumps = r.int(3, 6), ph = r.range(0, TAU);
    for (let i = 0; i <= n; i++) {
      const t = i / n, a = PI - PI * t;
      top.push(p.x + Math.cos(a) * p.w / 2, p.y - Math.sin(a) * p.h * (1 - 0.25 * (1 - Math.abs(Math.sin(bumps * t * PI + ph)))));
    }
    const bottom = [p.x + p.w / 2, p.y, p.x + p.w * 0.2, p.y + p.h * 0.18, p.x - p.w * 0.25, p.y + p.h * 0.12, p.x - p.w / 2, p.y];
    const out = top.concat(bottom.slice(2));
    sc.line(out, fp, ORG);
    const sp = Math.max(0.45, p.w / 26);
    for (let xx = p.x - p.w / 2 + sp; xx < p.x + p.w / 2; xx += sp) {
      if (r.chance(0.25)) continue;
      const yt = p.y - p.h * 0.35 * (1 - Math.pow((xx - p.x) / (p.w / 2), 2)), yb2 = p.y + p.h * 0.12;
      sc.seg(xx, yt, xx + r.range(-0.15, 0.15), yb2, fp, TEX);
    }
    sc.fill(out);
  };
  pads.filter((p) => p.front).forEach(drawPad);
  // trunk outline
  const L = [], Rr = [];
  for (let i = 0; i <= NT; i++) { const w = Math.max(sc.penW, tw * Math.pow(1 - i / (NT + 2), 1.3) * (1 + 0.5 * Math.pow(Math.max(0, 1 - i / 4), 2))) / 2; L.push(trunk[2 * i] - w, trunk[2 * i + 1]); Rr.push(trunk[2 * i] + w, trunk[2 * i + 1]); }
  sc.line(L, pen, ORG); sc.line(Rr, pen, ORG);
  bark(sc, trunk, trunk.map((_, i) => tw * Math.pow(1 - (i >> 1) / (NT + 2), 1.3)).filter((_, i) => i % 2 === 0), { r, pen }, sc.comp.lightX);
  sc.fill(L.concat(revPts(Rr)));
  for (const l of limbs) { sc.line(l.pts, pen, ORG); sc.halo(l.pts, Math.max(sc.penW * 1.5, l.w)); }
  pads.filter((p) => !p.front).forEach(drawPad);
}
function smallTree(sc, x, yb, h, r, o) {
  o = o || {};
  const season = sc.comp.season;
  const kind = o.kind || (season === 'winter' ? 'bare' : r.weighted([['round', 3], ['conifer', 1.2]]));
  const pen = o.pen ?? (season === 'autumn' ? r.weighted([[ACC, 2], [KEY, 1]]) : season === 'winter' ? KEY : r.weighted([[FLORA, 2], [KEY, 1]]));
  if (kind === 'round') {
    const tr = [x, yb, x + r.range(-0.1, 0.1) * h, yb - h * 0.45];
    const rad = h * r.range(0.26, 0.36);
    if (h > 6) {
      foliageCluster(sc, tr[2], yb - h + rad * 0.95, rad, pen, pen, r, { style: sc.comp.crownStyle });
    } else crown(sc, tr[2], yb - h * 0.35, rad, 'round', pen, r, h > 3 ? sc.comp.crownStyle : 'cloud');
    sc.line(tr, KEY, ORG); sc.halo(tr, Math.max(sc.penW * 1.5, h * 0.03));
  } else crown(sc, x, yb, h * 0.38, kind, pen, r);
}

/* ----------------------------------------------------------- structures */
function silo(sc, x, yb, h, o) {
  const r = o.r, lx = sc.comp.lightX, pen = o.pen ?? KEY;
  const w = o.w || h * r.range(0.2, 0.3), hw = w / 2, top = yb - h, dh = hw * r.range(0.5, 1.0);
  const out = [x - hw, yb, x - hw, top];
  for (let i = 1; i < 24; i++) { const a = PI - PI * i / 24; out.push(x + hw * Math.cos(a), top - dh * Math.sin(a)); }
  out.push(x + hw, top, x + hw, yb);
  sc.line(out, pen, RULED);
  const n = Math.max(6, Math.round(w / 0.7));
  for (let i = 1; i < n; i++) {
    const phi = -HALF + PI * i / n, px = x + hw * Math.sin(phi);
    const shade = 0.5 - 0.5 * lx * Math.sin(phi);
    if (shade > 0.62) sc.seg(px, top, px, yb, pen, RULED);
    else if (shade > 0.42) sc.seg(px, top + h * r.range(0.3, 0.6), px, yb, pen, RULED);
  }
  if (o.hoops !== false) {
    const hs = Math.max(1.2, h / r.int(6, 12));
    for (let yy = yb - hs; yy > top + hs * 0.4; yy -= hs) {
      const hp = [];
      for (let i = 0; i <= 16; i++) { const phi = -HALF + PI * i / 16; hp.push(x + hw * Math.sin(phi), yy + hw * 0.1 * Math.cos(phi)); }
      sc.line(hp, pen, TEX);
    }
  }
  for (let q = 1; q <= 3; q++) {
    const f = q / 4, ac = lx < 0 ? 0.3 : PI - 0.3;
    sc.line(arcPts(x, top, hw * (1 - f * 0.25), dh * (1 - f * 0.6), ac - 0.6, ac + 0.6, 10), pen, TEX);
  }
  if (o.chute) {
    const cxp = x + (lx < 0 ? -1 : 1) * -hw * 0.35, cw = Math.max(0.8, w * 0.1);
    sc.seg(cxp - cw / 2, top - dh * 0.5, cxp - cw / 2, yb, pen, RULED);
    sc.seg(cxp + cw / 2, top - dh * 0.5, cxp + cw / 2, yb, pen, RULED);
    for (let yy = top; yy < yb; yy += 1.1) sc.seg(cxp - cw / 2, yy, cxp + cw / 2, yy, pen, TEX);
  }
  sc.fill(out);
}
function barn(sc, x, yb, s, o) {
  const r = o.r, lx = sc.comp.lightX, pen = o.pen ?? KEY;
  const W = s * r.range(0.95, 1.25), wallH = s * r.range(0.4, 0.48), kneeH = s * r.range(0.7, 0.78), kneeIn = W * r.range(0.11, 0.16);
  const side = o.side || -lx, L = W * r.range(0.6, 1.1), dvx = side * L * 0.8, dvy = -L * 0.32;
  const x0 = x - W / 2, x1 = x + W / 2;
  const front = [x0, yb, x0, yb - wallH, x0 + kneeIn, yb - kneeH, x, yb - s, x1 - kneeIn, yb - kneeH, x1, yb - wallH, x1, yb];
  const ex = side > 0 ? x1 : x0;
  const sideWall = [ex, yb, ex, yb - wallH, ex + dvx, yb - wallH + dvy, ex + dvx, yb + dvy];
  const k1 = side > 0 ? [x1, yb - wallH] : [x0, yb - wallH];
  const k2 = side > 0 ? [x1 - kneeIn, yb - kneeH] : [x0 + kneeIn, yb - kneeH];
  const pk = [x, yb - s];
  const roof1 = [k1[0], k1[1], k2[0], k2[1], k2[0] + dvx, k2[1] + dvy, k1[0] + dvx, k1[1] + dvy];
  const roof2 = [k2[0], k2[1], pk[0], pk[1], pk[0] + dvx, pk[1] + dvy, k2[0] + dvx, k2[1] + dvy];
  // front face boards
  const doorW = W * r.range(0.32, 0.45), doorH = wallH * r.range(0.7, 0.85);
  const door = [x - doorW / 2, yb, x - doorW / 2, yb - doorH, x + doorW / 2, yb - doorH, x + doorW / 2, yb];
  const hay = [x - W * 0.08, yb - kneeH * 0.98, x - W * 0.08, yb - kneeH * 0.8, x + W * 0.08, yb - kneeH * 0.8, x + W * 0.08, yb - kneeH * 0.98];
  sc.loop(front, pen, RULED);
  sc.loop(door, pen, RULED);
  sc.seg(door[0], door[1], door[4], door[5], pen, RULED); sc.seg(door[2], door[3], door[6], door[7], pen, RULED);
  sc.seg(x, yb, x, yb - doorH, pen, RULED);
  sc.loop(hay, pen, RULED);
  const lit = side === -lx;
  const bsp = Math.max(0.55, W / r.range(28, 46));
  for (let xx = x0 + bsp; xx < x1; xx += bsp) {
    const seg = [xx, yb, xx, yb - s];
    const pred = (px, py) => inPoly(front, px, py) && !inPoly(door, px, py) && !inPoly(hay, px, py);
    if (lit && r.chance(0.35)) continue;
    for (const pc of clipPred(seg, pred, 0.35)) sc.line(pc, pen, TEX);
  }
  sc.loop(sideWall, pen, RULED);
  const ssp = lit ? bsp * 1.6 : bsp * 0.75;
  for (const sg of hatchPoly(sideWall, HALF, ssp, 0)) sc.line(sg, pen, TEX);
  if (r.chance(0.6)) {
    const nw = r.int(3, 6);
    for (let i = 1; i <= nw; i++) {
      const t = i / (nw + 1), wx = ex + dvx * t, wy = yb - wallH * 0.55 + dvy * t, ws = Math.max(0.8, wallH * 0.18);
      const win = [wx - ws / 2, wy - ws / 2, wx + ws / 2, wy - ws / 2 + dvy / L * ws * 0.5, wx + ws / 2, wy + ws / 2 + dvy / L * ws * 0.5, wx - ws / 2, wy + ws / 2];
      sc.loop(win, pen, RULED);
    }
  }
  sc.loop(roof1, pen, RULED); sc.loop(roof2, pen, RULED);
  const rsp = Math.max(0.55, s / r.range(14, 22));
  for (const [poly, dense] of [[roof1, 0.8], [roof2, 1.2]]) {
    for (const sg of hatchPoly(poly, Math.atan2(dvy, dvx), rsp * dense, 0)) sc.line(sg, pen, TEX);
  }
  if (r.chance(0.5)) {
    const cx = pk[0] + dvx * 0.5, cy = pk[1] + dvy * 0.5, cw = W * 0.08, chh = s * 0.12;
    const cup = [cx - cw, cy, cx - cw, cy - chh, cx, cy - chh * 1.6, cx + cw, cy - chh, cx + cw, cy];
    sc.line(cup, pen, RULED); sc.fill(cup.concat([cx - cw, cy]));
  }
  sc.fill(front); sc.fill(sideWall); sc.fill(roof1); sc.fill(roof2);
}
function house(sc, x, yb, s, o) {
  const r = o.r, pen = o.pen ?? KEY, lx = sc.comp.lightX;
  const W = s * r.range(0.9, 1.3), wallH = s * 0.55;
  const front = [x - W / 2, yb, x - W / 2, yb - wallH, x, yb - s, x + W / 2, yb - wallH, x + W / 2, yb];
  sc.loop(front, pen, RULED);
  const ws = Math.max(0.8, W * 0.14);
  for (const f of [-0.25, 0.25]) { const wx = x + f * W, wy = yb - wallH * 0.55; const win = [wx - ws / 2, wy - ws * 0.6, wx + ws / 2, wy - ws * 0.6, wx + ws / 2, wy + ws * 0.6, wx - ws / 2, wy + ws * 0.6]; sc.loop(win, pen, RULED); sc.seg(wx, wy - ws * 0.6, wx, wy + ws * 0.6, pen, TEX); }
  const roofSide = [x, yb - s, x + W / 2, yb - wallH];
  for (const sg of hatchPoly(front, -lx * 0.9, Math.max(0.5, W / 22), 0)) {
    const pred = (px, py) => py < yb - wallH - 0.4 + (Math.abs(px - x) / (W / 2)) * (wallH - s) * -1 + 0.01 && py > yb - s;
    for (const pc of clipPred(sg, pred, 0.3)) sc.line(pc, pen, TEX);
  }
  void roofSide;
  const ch = [x + W * 0.22, yb - s * 0.85, x + W * 0.22, yb - s * 1.05, x + W * 0.3, yb - s * 1.05, x + W * 0.3, yb - s * 0.75];
  sc.line(ch, pen, RULED);
  sc.fill(front); sc.fill(ch.concat([x + W * 0.22, yb - s * 0.85]));
}
function waterTower(sc, x, yb, h, o) {
  const r = o.r, pen = o.pen ?? KEY, lx = sc.comp.lightX;
  const tr = h * r.range(0.14, 0.2), ty = yb - h + tr;
  const tank = circlePts(x, ty, tr, 64);
  sc.line(tank, pen, RULED);
  for (let q = 1; q <= 9; q++) {
    const lat = -HALF + PI * q / 10;
    const yy = ty - Math.sin(lat) * tr, rr = Math.cos(lat) * tr;
    const shade = 0.5 + 0.5 * -Math.sin(lat);
    if (shade < 0.38) continue;
    const pts = [];
    for (let i = 0; i <= 20; i++) { const ph = -HALF + PI * i / 20; pts.push(x + rr * Math.sin(ph), yy + rr * 0.18 * Math.cos(ph)); }
    sc.line(pts, pen, TEX);
  }
  const sd = lx < 0 ? 1 : -1;
  for (let q = 1; q <= 4; q++) sc.line(arcPts(x, ty, tr * (1 - q * 0.08), tr * (1 - q * 0.08), sd > 0 ? -0.9 : PI - 0.6, sd > 0 ? 0.6 : PI + 0.9, 10), pen, TEX);
  sc.seg(x, ty - tr, x, ty - tr - tr * 0.35, pen, RULED);
  sc.fill(tank);
  const spread = tr * r.range(0.75, 0.95), foot = spread * 1.35;
  const legs = [[x - spread, ty + tr * 0.4, x - foot, yb], [x + spread, ty + tr * 0.4, x + foot, yb], [x - spread * 0.35, ty + tr * 0.6, x - foot * 0.4, yb], [x + spread * 0.35, ty + tr * 0.6, x + foot * 0.4, yb]];
  const levels = r.int(2, 4);
  for (let q = 1; q <= levels; q++) {
    const t = q / (levels + 1), y = lerp(ty + tr * 0.4, yb, t);
    const xl = lerp(x - spread, x - foot, t), xr = lerp(x + spread, x + foot, t);
    sc.seg(xl, y, xr, y, pen, RULED);
    const t2 = (q + 1) / (levels + 1), y2 = lerp(ty + tr * 0.4, yb, t2);
    const xl2 = lerp(x - spread, x - foot, t2), xr2 = lerp(x + spread, x + foot, t2);
    sc.seg(xl, y, xr2, y2, pen, TEX); sc.seg(xr, y, xl2, y2, pen, TEX);
  }
  for (const l of legs) { sc.line(l, pen, RULED); sc.halo(l, sc.penW * 1.6); }
  const riser = [x, ty + tr, x, yb];
  sc.line(riser, pen, RULED);
}
function rockTower(sc, x, yb, h, o) {
  const r = o.r, N = sc.noise, lx = sc.comp.lightX;
  const shape = o.shape || r.weighted([['chimney', 2], ['mushroom', 1.5], ['butte', 1.4], ['twin', 0.8]]);
  if (shape === 'twin') {
    const g = h * r.range(0.18, 0.3);
    rockTower(sc, x + g, yb - 0.3, h * r.range(0.55, 0.8), { r, shape: 'chimney' });
    rockTower(sc, x - g * 0.6, yb, h, { r, shape: r.pick(['chimney', 'mushroom']) });
    return;
  }
  const wb = h * (shape === 'butte' ? r.range(0.9, 1.5) : shape === 'mushroom' ? r.range(0.35, 0.5) : r.range(0.28, 0.42)), steps = 70;
  const capT = shape === 'mushroom' ? r.range(0.7, 0.82) : r.range(0.82, 0.93);
  const Lx = [], Rx = [], Ys = [];
  const lean = r.range(-0.08, 0.08) * h;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps, y = yb - h * t;
    let w;
    if (shape === 'butte') w = wb * (1 - 0.18 * t) * (t > capT ? 1.03 : 1);
    else if (shape === 'mushroom') w = wb * (t < capT ? 1 - 0.45 * Math.sin(t / capT * PI * 0.75) : 1.25 + 0.25 * Math.sin((t - capT) / (1 - capT) * PI));
    else w = wb * (1 - 0.3 * Math.sin(t * PI * 0.9)) * (t > capT ? 1.12 : 1);
    const ledge = 0.05 * wb * Math.sign(N.n2(Math.floor(t * 16) * 3.1, x)) * (shape === 'butte' ? 0.3 : 1) + N.n2(t * 9, x * 0.1) * 0.04 * wb;
    Lx.push(x + lean * t - w / 2 + ledge); Rx.push(x + lean * t + w / 2 + ledge * 0.6 + N.n2(t * 7 + 50, x) * 0.04 * wb); Ys.push(y);
  }
  const out = [];
  for (let i = 0; i <= steps; i++) out.push(Lx[i], Ys[i]);
  for (let i = steps; i >= 0; i--) out.push(Rx[i], Ys[i] + (i === steps ? r.range(-0.3, 0.3) : 0));
  // vegetation on top
  const nt = shape === 'butte' ? r.int(3, 9) : r.int(1, 3);
  for (let q = 0; q < nt; q++) {
    const tx = lerp(Lx[steps], Rx[steps], r.range(0.1, 0.9));
    smallTree(sc, tx, yb - h + 0.3, h * r.range(0.04, 0.09) * (shape === 'butte' ? 0.7 : 1) + 1, r, { kind: r.chance(0.6) ? 'conifer' : 'round', pen: KEY });
  }
  sc.line(out, KEY, ORG);
  let y = yb - h + r.range(0.6, 1.5);
  while (y < yb - 0.5) {
    const i = Math.round((yb - y) / h * steps);
    const a = Lx[clamp(i, 0, steps)], b = Rx[clamp(i, 0, steps)];
    const pts = [];
    for (let xx = a; xx <= b; xx += 0.5) pts.push(xx, y + N.n2(xx * 0.2, y) * 0.2);
    const pred = (px, py) => N.n2(px * 0.25, py * 1.7) > -0.4;
    for (const pc of clipPred(pts, pred, 0.3)) sc.line(pc, KEY, TEX);
    y += r.range(0.6, 2.4) * Math.max(0.6, h / 40);
  }
  const nj = r.int(2, 5);
  for (let q = 0; q < nj; q++) {
    const t0 = r.range(0.2, 1), y0 = yb - h * t0, len = h * r.range(0.15, 0.5);
    const i0 = Math.round(t0 * steps);
    let xx = lerp(Lx[i0], Rx[i0], r.range(0.2, 0.8));
    const pts = [];
    for (let yy = y0; yy < Math.min(yb, y0 + len); yy += 0.7) { pts.push(xx, yy); xx += r.range(-0.3, 0.3); }
    sc.line(pts, KEY, ORG);
  }
  const sd = lx < 0 ? 1 : -1, sf = r.range(0.18, 0.3);
  const shadowPoly = [];
  for (let i = 0; i <= steps; i++) shadowPoly.push(sd > 0 ? Rx[i] : Lx[i], Ys[i]);
  for (let i = steps; i >= 0; i--) shadowPoly.push(sd > 0 ? lerp(Lx[i], Rx[i], 1 - sf) : lerp(Lx[i], Rx[i], sf), Ys[i]);
  for (const sg of hatchPoly(shadowPoly, HALF + sd * 0.12, r.range(0.75, 1.0), r.rnd())) {
    for (const pc of clipPred(sg, (px, py) => N.n2(px * 0.5, py * 0.15) > -0.3, 0.3)) sc.line(pc, KEY, TEX);
  }
  sc.fill(out);
  const nb = r.int(4, 9);
  for (let q = 0; q < nb; q++) {
    const bx = x + r.gauss() * wb * 0.9, br = h * r.range(0.015, 0.045);
    const bo = arcPts(bx, yb + br * 0.2, br * 1.3, br, PI + 0.1, -0.1, 10);
    sc.line(bo, KEY, ORG); sc.fill(bo);
  }
}
function monument(sc, x, yb, h, o) {
  const r = o.r, lx = sc.comp.lightX, kind = o.kind || r.pick(['stele', 'ring', 'sphere', 'arch']);
  const pen = o.pen ?? KEY;
  if (kind === 'stele') {
    const w = h * r.range(0.25, 0.4), d = w * r.range(0.18, 0.3), side = -lx;
    const front = [x - w / 2, yb, x - w / 2, yb - h, x + w / 2, yb - h, x + w / 2, yb];
    const sx = side > 0 ? x + w / 2 : x - w / 2;
    const sidep = [sx, yb, sx, yb - h, sx + side * d, yb - h - d * 0.35, sx + side * d, yb - d * 0.35];
    const topp = [x - w / 2, yb - h, x + w / 2, yb - h, x + w / 2 + side * d, yb - h - d * 0.35, x - w / 2 + side * d, yb - h - d * 0.35];
    const hole = r.chance(0.5) ? circlePts(x, yb - h * 0.68, w * 0.28, 40) : null;
    sc.loop(front, pen, RULED); sc.loop(sidep, pen, RULED); sc.loop(topp, pen, RULED);
    if (hole) sc.loop(hole, pen, RULED);
    const pat = r.pick(['lines', 'grid', 'rings']);
    const fp = (px, py) => inPoly(front, px, py) && !(hole && inPoly(hole, px, py));
    if (pat === 'lines') for (let yy = yb - h + 1; yy < yb; yy += r.range(0.9, 1.6)) for (const pc of clipPred([x - w / 2, yy, x + w / 2, yy], fp, 0.3)) sc.line(pc, pen, TEX);
    else if (pat === 'grid') { const g = w / r.int(4, 7); for (let xx = x - w / 2 + g; xx < x + w / 2 - 0.1; xx += g) for (const pc of clipPred([xx, yb - h, xx, yb], fp, 0.3)) sc.line(pc, pen, TEX); for (let yy = yb - h + g; yy < yb; yy += g) for (const pc of clipPred([x - w / 2, yy, x + w / 2, yy], fp, 0.3)) sc.line(pc, pen, TEX); }
    else { const cy = yb - h * 0.68; for (let rr = w * 0.33; rr < h; rr += r.range(0.9, 1.4)) for (const pc of clipPred(circlePts(x, cy, rr, 80), fp, 0.3)) sc.line(pc, pen, TEX); }
    for (const sg of hatchPoly(sidep, HALF, 0.55, 0)) sc.line(sg, pen, TEX);
    sc.mask.fillRings(hole ? [front, hole] : [front]); sc.fill(sidep); sc.fill(topp);
  } else if (kind === 'ring') {
    const R = h / 2, ri = R * r.range(0.55, 0.72), cy = yb - R, th = R * r.range(0.12, 0.2), side = -lx;
    const outer = circlePts(x, cy, R, 120), inner = circlePts(x, cy, ri, 100);
    sc.line(outer, pen, RULED); sc.line(inner, pen, RULED);
    const inner2 = circlePts(x + side * th * 0.6, cy - th * 0.25, ri, 100);
    for (const pc of clipPred(inner2, (px, py) => Math.hypot(px - x, py - cy) < ri, 0.3)) sc.line(pc, pen, RULED);
    for (let rr = ri + 0.9; rr < R - 0.4; rr += r.range(0.8, 1.2)) {
      const arc = arcPts(x, cy, rr, rr, side > 0 ? -1.2 : PI - 0.9, side > 0 ? 0.9 : PI + 1.2, 60);
      sc.line(arc, pen, TEX);
    }
    sc.mask.fillRings([outer, inner]);
  } else if (kind === 'sphere') {
    const R = h / 2, cy = yb - R * 0.95;
    const out = circlePts(x, cy, R, 140);
    sc.line(out, pen, RULED);
    const Lx = lx * 0.55, Ly = 0.55, Lz = 0.63;
    const shadeAt = (px, py) => {
      const nx = (px - x) / R, ny = -(py - cy) / R, nz = Math.sqrt(Math.max(0, 1 - nx * nx - ny * ny));
      return 1 - Math.max(0, nx * Lx + ny * Ly + nz * Lz);
    };
    const inside = (px, py) => Math.hypot(px - x, py - cy) < R - 0.35;
    const sp = r.range(0.85, 1.2), a0 = r.pick([0, PI / 6, -PI / 6]);
    const box = [x - R, cy - R, x + R, cy - R, x + R, cy + R, x - R, cy + R];
    [[0.3, a0], [0.55, a0 + PI / 3], [0.78, a0 - PI / 3]].forEach(([th, a]) => {
      for (const sg of hatchPoly(box, a, sp, r.rnd() * sp)) for (const pc of clipPred(sg, (px, py) => inside(px, py) && shadeAt(px, py) > th, 0.3)) sc.line(pc, pen, TEX);
    });
    sc.mask.disc(x, cy, R);
    for (let q = 0; q < 4; q++) { const sw = R * (1.1 - q * 0.18); sc.line([x - lx * R * 0.3 - sw, yb + q * 0.6, x - lx * R * 0.3 + sw, yb + q * 0.6], TINT, TEX); }
  } else {
    const w = h * r.range(0.7, 1.0), pw = w * r.range(0.16, 0.24), R = w / 2, cy = yb - h + R;
    const outer = [x - R, yb]; for (let i = 0; i <= 40; i++) { const a = PI - PI * i / 40; outer.push(x + R * Math.cos(a), cy - R * Math.sin(a)); } outer.push(x + R, yb);
    const ri = R - pw;
    const inner = [x + ri, yb]; for (let i = 0; i <= 40; i++) { const a = PI * i / 40; inner.push(x + ri * Math.cos(a), cy - ri * Math.sin(a)); } inner.push(x - ri, yb);
    const shape = outer.concat(inner);
    sc.loop(shape, pen, RULED);
    for (let i = 1; i < 12; i++) { const a = PI * i / 12; sc.seg(x + ri * Math.cos(a), cy - ri * Math.sin(a), x + R * Math.cos(a), cy - R * Math.sin(a), pen, RULED); }
    for (let yy = yb - 1.6; yy > cy; yy -= r.range(1.6, 2.6)) { sc.seg(x - R, yy, x - ri, yy, pen, TEX); sc.seg(x + ri, yy, x + R, yy, pen, TEX); }
    const sd = -lx;
    for (const sg of hatchPoly(shape, HALF + 0.2, 0.7, 0)) for (const pc of clipPred(sg, (px) => (px - x) * sd > ri * 0.4, 0.3)) sc.line(pc, pen, TEX);
    sc.fill(shape);
  }
}
function poleLine(sc, b, r) {
  const W = sc.W, t = b.t;
  const sz = lerp(0.18, 1, Math.pow(t, 1.2)) * (sc.view.y1 - sc.view.y0) * r.range(0.1, 0.16);
  const gap = sz * r.range(1.6, 2.6), depth = r.range(0.05, 0.5);
  const poles = [];
  for (let x = r.range(-gap, 0); x < W + gap; x += gap * r.range(0.9, 1.1)) {
    const top = b.curve.at(x), bot = Math.min(b.Ec.at(x), sc.H + 2);
    if (bot - top < 0.5) { poles.push(null); continue; }
    poles.push({ x, y: top + (bot - top) * depth * 0.5 + 0.3 });
  }
  return { poles, sz, draw(sc2, i) {
    const p = this.poles[i]; if (!p) return;
    const h = this.sz, x = p.x, y = p.y, arm = h * 0.22;
    const pole = [x, y, x, y - h];
    sc2.line(pole, KEY, RULED); sc2.halo(pole, Math.max(sc2.penW * 1.6, h * 0.02));
    const cross = [x - arm, y - h * 0.92, x + arm, y - h * 0.92];
    sc2.line(cross, KEY, RULED); sc2.halo(cross, sc2.penW * 1.4);
    for (const f of [-0.85, 0.85, 0]) sc2.seg(x + arm * f, y - h * 0.92, x + arm * f, y - h * 0.96, KEY, RULED);
    const q = this.poles[i + 1];
    if (q) {
      for (const f of [-0.85, 0.85]) {
        const ax = x + arm * f, ay = y - h * 0.96, bx = q.x + arm * f, by = q.y - this.sz * 0.96, sag = Math.abs(bx - ax) * 0.06;
        const w = [];
        for (let k = 0; k <= 20; k++) { const u = k / 20; w.push(lerp(ax, bx, u), lerp(ay, by, u) + sag * 4 * u * (1 - u)); }
        sc2.line(w, KEY, ORG);
      }
    }
  } };
}

/* ------------------------------------------------------------- objects */
function placeObjects(sc) {
  const c = sc.comp, r = sc.rng('objects'), bands = sc.bands, nB = bands.length, W = sc.W, H = sc.H, v = sc.view, wt = sc.P.weights;
  const viewH = v.y1 - v.y0, viewW = v.x1 - v.x0;
  const objs = [];
  const fx = v.x0 + c.focalX * viewW;
  const spot = (k, x, f) => {
    const b = bands[k];
    if (!b || b.water) return null;
    const top = b.curve.at(x), bot = Math.min(b.Ec.at(x), H + 5);
    if (bot - top < 0.6) return null;
    return top + (bot - top) * f;
  };
  const scaleK = (k) => lerp(0.16, 1, Math.pow(bands[k].t, 1.25));
  // nearest workable spot to (kPref, x): same band at nearby x first, then neighbouring bands
  const findSpot = (kPref, x, f) => {
    const offs = [0, 0.06, -0.06, 0.12, -0.12, 0.2, -0.2, 0.3, -0.3];
    const ks = [kPref, kPref + 1, kPref - 1, kPref + 2, kPref - 2].filter((k) => k >= 0 && k < nB);
    const edge = c.focal === 'farmstead' ? 0.2 : 0.08;
    for (const k of ks) for (const o of offs) {
      const xx = clamp(x + o * viewW, v.x0 + viewW * edge, v.x1 - viewW * edge);
      const y = spot(k, xx, f);
      if (y != null && (k === kPref || bands[k].Ec.at(xx) - bands[k].curve.at(xx) > 3)) return { k, x: xx, y };
    }
    return null;
  };
  const taken = [];
  const clear = (k, x, w) => !taken.some((q) => Math.abs(q.k - k) <= 1 && Math.abs(q.x - x) < (q.w + w) / 2);
  const add = (k, x, y, w, draw, kind) => { if (y == null) return false; objs.push({ band: k, x, y, draw, kind }); taken.push({ k, x, w }); return true; };
  const ord = r.rnd();
  const nearK = nB >= 3 && ord < 0.4 ? nB - 2 : nB - 1;
  const place = (kPref, f, w, make, kind) => {
    const sp = findSpot(kPref, fx, f);
    if (!sp) return false;
    return add(sp.k, sp.x, sp.y, w(sp.k), (s) => make(s, sp.x, sp.y, sp.k), kind);
  };
  switch (c.focal) {
    case 'oak': {
      const f = r.range(0.02, 0.25), hk = r.range(0.42, 0.66);
      place(nearK, f, () => viewH, (s, x, y, k) => oak(s, x, y, viewH * hk * (k === nB - 1 ? 1 : 0.82), { r: s.rng('focal-oak') }), 'oak');
      break;
    }
    case 'pine': {
      const f = r.range(0.02, 0.2), hk = r.range(0.42, 0.62);
      place(nearK, f, () => viewH * 0.5, (s, x, y, k) => pine(s, x, y, viewH * hk * (k === nB - 1 ? 1 : 0.85), { r: s.rng('focal-pine') }), 'pine');
      break;
    }
    case 'grove': {
      const kp = nearK === nB - 1 && nB > 2 ? nB - 2 : nearK, n = r.int(3, 6);
      const sp = findSpot(kp, fx, 0.05);
      if (!sp) break;
      const base = viewH * r.range(0.22, 0.34) * scaleK(sp.k) / scaleK(nB - 1) * 1.4;
      for (let i = 0; i < n; i++) {
        const xx = sp.x + (i - (n - 1) / 2) * base * r.range(0.45, 0.75) + r.range(-2, 2), y = spot(sp.k, xx, r.range(0.0, 0.18));
        const ht = base * r.range(0.65, 1.15);
        add(sp.k, xx, y, ht * 0.8, (s) => oak(s, xx, y, ht, { r: s.rng('grove' + i), segs: 55, detail: 0.6 }), 'oak');
      }
      break;
    }
    case 'farmstead': {
      const kp = Math.max(1, nB - 2 - (r.chance(0.4) ? 1 : 0)), f = r.range(0.05, 0.4), sk = r.range(0.13, 0.2);
      place(kp, f, (k) => viewH * sk * scaleK(k) * 3, (s, x, y, k) => farmstead(s, x, y, viewH * sk * Math.max(0.55, scaleK(k) / scaleK(Math.max(0, nB - 2))), s.rng('focal-farm')), 'farm');
      break;
    }
    case 'watertower': {
      const f = r.range(0.05, 0.3), hk = r.range(0.35, 0.55);
      place(Math.max(1, nB - 2), f, () => viewH * 0.3, (s, x, y, k) => waterTower(s, x, y, viewH * hk * Math.max(0.6, scaleK(k) / scaleK(Math.max(0, nB - 2))), { r: s.rng('tower') }), 'tower');
      break;
    }
    case 'monument': {
      const f = r.range(0.05, 0.35), hk = r.range(0.3, 0.55), kind = r.pick(['stele', 'ring', 'sphere', 'arch']);
      place(nearK, f, () => viewH * 0.5, (s, x, y, k) => monument(s, x, y, viewH * hk * (k === nB - 1 ? 1 : 0.8), { r: s.rng('mono'), kind }), 'monument');
      break;
    }
    case 'rock': {
      const f = r.range(0.05, 0.25), hk = r.range(0.35, 0.6);
      place(Math.max(0, nB - 2 - (r.chance(0.5) ? 1 : 0)), f, () => viewH * 0.4, (s, x, y, k) => rockTower(s, x, y, viewH * hk * Math.max(0.5, scaleK(k)), { r: s.rng('rock') }), 'rock');
      break;
    }
    default: break;
  }
  // lone trees on ridges
  const nRidgeTrees = Math.round(r.range(0, 5) * wt.flora + 0.3);
  for (let i = 0; i < nRidgeTrees; i++) {
    const k = r.int(0, Math.max(0, nB - 2)), x = r.range(0.04, 0.96) * W;
    const y = spot(k, x, r.range(0, 0.04));
    const h = viewH * r.range(0.05, 0.11) * scaleK(k) * 2.2;
    if (y != null && clear(k, x, h)) add(k, x, y, h, (s) => (r.chance(0.5) && h > 5 ? oak(s, x, y, h, { r: s.rng('rt' + i), segs: 40, detail: 0.35 }) : smallTree(s, x, y, h, s.rng('st' + i))), 'tree');
  }
  // farmsteads
  const nFarms = Math.round(r.range(0, 2.6) * wt.built);
  for (let i = 0; i < nFarms; i++) {
    const k = r.int(Math.min(1, nB - 2), Math.max(0, nB - 2)), x = r.range(0.05, 0.95) * W;
    const s = viewH * r.range(0.1, 0.16) * scaleK(k);
    const y = spot(k, x, r.range(0.05, 0.6));
    if (y != null && s > 1.2 && clear(k, x, s * 3)) add(k, x, y, s * 3, (sc2) => farmstead(sc2, x, y, s, sc2.rng('farm' + i)), 'farm');
  }
  // anomaly
  if (c.anomaly && c.focal !== 'monument') {
    const k = r.int(0, Math.max(0, nB - 2)), x = r.range(0.1, 0.9) * W, y = spot(k, x, r.range(0, 0.3));
    const h = viewH * r.range(0.12, 0.3) * Math.max(0.35, scaleK(k));
    if (y != null && clear(k, x, h)) add(k, x, y, h, (s) => monument(s, x, y, h, { r: s.rng('anom') }), 'monument');
  }
  // poles
  if (c.poles && nB >= 3) {
    const k = r.int(Math.floor(nB / 2), nB - 2);
    if (!bands[k].water) {
      const pl = poleLine(sc, bands[k], r);
      pl.poles.forEach((p, i) => { if (p) objs.push({ band: k, x: p.x, y: p.y, draw: (s) => pl.draw(s, i), kind: 'pole' }); });
    }
  }
  // fence in the foreground
  if (c.fence && (bands[nB - 1].treat === 'meadow' || bands[nB - 1].treat === 'snow')) {
    const b = bands[nB - 1];
    const y0 = lerp(Math.max(b.curve.at(0), b.curve.at(W)), Math.min(H, v.y1), r.range(0.25, 0.7));
    const tilt = r.range(-0.12, 0.12), gap = r.range(10, 22), ph = r.range(0, gap), postH = r.range(5, 10);
    const posts = [];
    for (let x = -ph; x < W + gap; x += gap * r.range(0.9, 1.1)) posts.push({ x, y: y0 + tilt * (x - W / 2) });
    posts.forEach((p, i) => objs.push({ band: nB - 1, x: p.x, y: p.y, kind: 'fence', draw: (s) => {
      const post = [p.x, p.y, p.x + 0.2, p.y - postH];
      const wire = (q, f) => { const pts = []; for (let k2 = 0; k2 <= 12; k2++) { const u = k2 / 12; pts.push(lerp(p.x, q.x, u), lerp(p.y, q.y, u) - postH * f + 0.6 * 4 * u * (1 - u)); } return pts; };
      const q = posts[i + 1];
      if (q) for (const f of [0.35, 0.62, 0.88]) s.line(wire(q, f), KEY, ORG);
      const pp = widen(post, Math.max(0.6, postH * 0.09), 0.1);
      s.line(pp, KEY, ORG); s.fill(pp);
    } }));
  }
  return objs;
}
function farmstead(sc, x, yb, s, r) {
  const side = r.sign();
  const lx = sc.comp.lightX;
  const barnPen = r.chance(0.5) ? ACC : KEY;
  const parts = [];
  const bW = s * 1.1;
  parts.push({ y: yb, draw: () => barn(sc, x, yb, s, { r, pen: barnPen, side: -lx }) });
  const ns = r.int(1, 3);
  for (let i = 0; i < ns; i++) {
    const h = s * r.range(1.4, 2.1), w = s * r.range(0.32, 0.42);
    const sx = x + side * (bW * 0.5 + w * (0.2 + i * 1.08));
    parts.push({ y: yb - 0.4 - i * 0.2, draw: () => silo(sc, sx, yb - 0.4 - i * 0.2, h, { r, w, chute: i === 0 && r.chance(0.6), pen: r.chance(0.2) ? ACC : KEY }) });
  }
  if (r.chance(0.6)) {
    const hx = x - side * bW * r.range(0.9, 1.4);
    parts.push({ y: yb + s * 0.05, draw: () => house(sc, hx, yb + s * 0.05, s * 0.55, { r }) });
  }
  const nt = r.int(0, 3);
  for (let i = 0; i < nt; i++) {
    const tx = x + r.sign() * bW * r.range(0.8, 2.2), th = s * r.range(0.9, 1.6);
    parts.push({ y: yb - 0.8, draw: () => smallTree(sc, tx, yb - 0.8, th, r) });
  }
  parts.sort((a, b) => b.y - a.y).forEach((p) => p.draw());
}

/* ------------------------------------------------------------------ sky */
function drawSky(sc) {
  const c = sc.comp, r = sc.rng('sky'), W = sc.W, v = sc.view, N = sc.noise;
  let floorMax = -Infinity, floorMin = Infinity;
  for (let x = 0; x <= W; x += 1) { const f = sc.floor.at(x); floorMax = Math.max(floorMax, f); floorMin = Math.min(floorMin, f); }
  const skyTop = v.y0, skyH = Math.max(10, c.horizon - skyTop);
  // clouds
  if (c.clouds !== 'none') clouds(sc, r, skyTop, Math.min(floorMin, c.horizon) - 2, c.clouds);
  // celestial body
  const night = c.time === 'night';
  let sx = v.x0 + c.sunX * (v.x1 - v.x0), sy, rad;
  if (c.focal === 'sun') { rad = Math.min(skyH * r.range(0.45, 0.7), (v.x1 - v.x0) * 0.32); sy = c.horizon - rad * r.range(0.1, 0.7); }
  else { rad = skyH * r.range(0.1, 0.24) * (night ? 0.7 : 1); sy = skyTop + skyH * r.range(0.22, 0.62); }
  if (c.time === 'dusk' && c.focal !== 'sun' && r.chance(0.55)) sy = sc.floor.at(sx) - rad * r.range(-0.2, 0.5);
  sc.sun = { x: sx, y: sy, r: rad };
  if (night) moon(sc, r, sx, sy, rad);
  else sun(sc, r, sx, sy, rad, c.sunStyle);
  // sky texture
  const bottom = floorMax + 1;
  const style = c.sky;
  if (style === 'lines' || style === 'dashes') {
    let y = skyTop + r.range(0.2, 1);
    const dashL = r.range(1.5, 6), dashG = r.range(0.6, 2.2);
    let row = 0;
    while (y < bottom) {
      const f = clamp((y - skyTop) / skyH, 0, 1.2);
      const tone = night ? lerp(0.85, 0.35, f) : c.time === 'dusk' ? lerp(0.35, 0.8, f) : lerp(0.55, 0.12, Math.pow(f, 0.8));
      const sp = lerp(4.5, 0.75, tone) / Math.sqrt(sc.dens);
      const pen = c.time === 'dusk' && f > 0.55 ? ACC : TINT;
      if (style === 'lines') {
        const thr = lerp(0.35, -0.45, tone);
        const pts = [];
        for (let x = -1; x <= W + 1; x += 1) pts.push(x, y);
        for (const pc of clipPred(pts, (px, py) => N.n2(px * 0.035 + row * 1.7, py * 0.11) > thr, 0.5)) sc.line(pc, pen, TEX);
      } else {
        const off = (row % 2) * (dashL + dashG) / 2 + r.range(0, 0.5);
        for (let x = -off; x < W + 1; x += dashL + dashG) if (N.n2(x * 0.02, y * 0.05) > lerp(0.4, -0.6, tone)) sc.seg(x, y, x + dashL, y, pen, TEX);
      }
      y += sp * r.range(0.85, 1.15); row++;
    }
  } else if (style === 'wind') {
    windLines(sc, r, skyTop, bottom);
  } else if (style === 'rays') {
    const n = r.int(60, 140);
    for (let i = 0; i < n; i++) {
      const a = TAU * i / n + r.range(-0.01, 0.01);
      if (i % 2 && r.chance(0.5)) continue;
      const L = Math.hypot(W, sc.H);
      const pts = [sx + Math.cos(a) * rad * 1.25, sy - Math.sin(a) * rad * 1.25, sx + Math.cos(a) * L, sy - Math.sin(a) * L];
      sc.line(subdivide(pts, 2), TINT, TEX);
    }
  } else if (style === 'stars') {
    const n = Math.round((W * skyH) * r.range(0.008, 0.02));
    for (let i = 0; i < n; i++) {
      const x = r.range(0, W), y = r.range(skyTop, bottom);
      const big = r.chance(0.08), s = big ? r.range(0.8, 1.6) : r.range(0.25, 0.5);
      if (!sc.free(x, y)) continue;
      if (big) { sc.seg(x - s, y, x + s, y, ACC, FLECK); sc.seg(x, y - s, x, y + s, ACC, FLECK); }
      else sc.fleck(x, y, r.rnd() * PI, s, TINT);
    }
    let y = bottom - r.range(6, 14);
    for (let q = 0; q < 6; q++) { sc.line(subdivide([-1, y, W + 1, y], 3), TINT, TEX); y += r.range(1, 2.5); }
  }
}
function sun(sc, r, x, y, rad, style) {
  const out = circlePts(x, y, rad, 140);
  if (style === 'rings') {
    sc.line(out, ACC, ORG);
    const sp = r.range(0.75, 1.4);
    for (let rr = rad - sp; rr > sp * 0.6; rr -= sp * r.range(0.9, 1.15)) sc.line(circlePts(x, y, rr, Math.max(24, Math.round(rr * 5))), ACC, TEX);
  } else if (style === 'bands') {
    sc.line(out, ACC, ORG);
    let yy = y - rad + 0.7, gap = r.range(0.55, 0.9);
    while (yy < y + rad) {
      const hw = Math.sqrt(Math.max(0, rad * rad - (yy - y) * (yy - y)));
      if (hw > 0.3) sc.seg(x - hw + 0.3, yy, x + hw - 0.3, yy, ACC, TEX);
      yy += gap; if (yy > y - rad * 0.2) gap *= 1.12;
    }
  } else if (style === 'halo') {
    sc.line(out, ACC, ORG);
    sc.line(circlePts(x, y, rad * 0.86, 120), ACC, TEX);
  } else {
    sc.line(out, ACC, ORG);
    const n = Math.round(rad * rad * PI * r.range(1.2, 2.4));
    for (let i = 0; i < n; i++) {
      const a = r.range(0, TAU), d = Math.sqrt(r.rnd()) * (rad - 0.5);
      const px = x + Math.cos(a) * d, py = y + Math.sin(a) * d;
      if (r.rnd() < 0.35 + 0.5 * ((py - y) / rad)) sc.fleck(px, py, r.rnd() * PI, 0.22, ACC);
    }
  }
  sc.mask.disc(x, y, rad + 0.3);
  if (style === 'halo') {
    let rr = rad * 1.25;
    for (let q = 0; q < r.int(5, 12); q++) {
      const pts = circlePts(x, y, rr, Math.round(rr * 4));
      for (const pc of clipPred(pts, (px, py) => sc.noise.n2(px * 0.05, py * 0.05 + q) > -0.2, 0.5)) sc.line(pc, TINT, TEX);
      rr *= r.range(1.12, 1.25);
    }
  }
}
function moon(sc, r, x, y, rad) {
  const out = circlePts(x, y, rad, 120);
  sc.line(out, ACC, ORG);
  const ph = r.range(0.25, 0.9) * (r.chance(0.5) ? 1 : -1);
  const ox = x + ph * rad * 1.1;
  const shadow = (px, py) => Math.hypot(px - x, py - y) < rad - 0.3 && Math.hypot(px - ox, py - y) > rad;
  for (let yy = y - rad; yy < y + rad; yy += 0.6) for (const pc of clipPred([x - rad, yy, x + rad, yy], shadow, 0.25)) sc.line(pc, ACC, TEX);
  const nc = r.int(3, 7);
  for (let q = 0; q < nc; q++) {
    const a = r.range(0, TAU), d = r.range(0, rad * 0.7), cx = x + Math.cos(a) * d, cy = y + Math.sin(a) * d, cr = rad * r.range(0.06, 0.16);
    if (shadow(cx, cy)) continue;
    for (const pc of clipPred(circlePts(cx, cy, cr, 16), (px, py) => !shadow(px, py), 0.25)) sc.line(pc, ACC, TEX);
  }
  sc.mask.disc(x, y, rad + 0.3);
}
function clouds(sc, r, top, bottom, kind) {
  const W = sc.W;
  if (bottom - top < 8) return;
  if (kind === 'cumulus') {
    const n = r.int(1, 3);
    for (let i = 0; i < n; i++) {
      const cw = W * r.range(0.2, 0.5), cx = r.range(-0.05, 1.05) * W, base = lerp(top + (bottom - top) * 0.3, bottom - 2, r.rnd());
      const circles = [];
      const m = r.int(9, 18);
      for (let q = 0; q < m; q++) {
        const u = r.gauss() * 0.32, ox = u * cw;
        const env = Math.max(0.12, 1 - Math.abs(u) * 1.6);
        const rr = cw * r.range(0.06, 0.13) * (0.6 + env * 0.8);
        circles.push({ x: cx + ox, y: base - rr * r.range(0.2, 0.6) - cw * 0.2 * env * r.rnd(), r: rr });
      }
      circles.sort((a, b) => b.y + b.r - (a.y + a.r));
      const inside = (px, py) => py < base && circles.some((cc) => Math.hypot(px - cc.x, py - cc.y) < cc.r - 0.3);
      const hTop = Math.min(...circles.map((cc) => cc.y - cc.r));
      for (let yy = base - 0.8; yy > lerp(base, hTop, 0.22); yy -= r.range(1.1, 1.6)) {
        for (const pc of clipPred([cx - cw, yy, cx + cw, yy], inside, 0.3)) sc.line(pc, TINT, TEX);
      }
      circles.forEach((cc, ci) => {
        const pts = [];
        let a0 = -0.6, a1 = PI + 0.6;
        if (ci < circles.length * 0.6) { const span = r.range(0.35, 0.8) * PI, mid = r.range(0.3, 0.7) * PI; a0 = mid - span / 2; a1 = mid + span / 2; }
        for (let k = 0; k <= 48; k++) { const a = lerp(a0, a1, k / 48); pts.push(cc.x + cc.r * Math.cos(a), cc.y - cc.r * Math.sin(a)); }
        for (const pc of clipPred(pts, (px, py) => py < base - 0.4 && py < cc.y + cc.r * 0.35, 0.3)) sc.line(pc, KEY, ORG);
        const poly = []; for (let k = 0; k <= 40; k++) { const a = TAU * k / 40; poly.push(cc.x + cc.r * Math.cos(a), Math.min(cc.y - cc.r * Math.sin(a), base)); }
        sc.fill(poly);
      });
    }
  } else if (kind === 'stratus') {
    const n = r.int(2, 5);
    for (let i = 0; i < n; i++) {
      const L = W * r.range(0.25, 0.7), x0 = r.range(-0.3, 0.8) * W, y = lerp(top + 4, bottom - 3, r.rnd());
      const lines = r.int(3, 7), sp = r.range(0.7, 1.1), ends = [];
      for (let q = 0; q < lines; q++) {
        const u = (q / (lines - 1)) * 2 - 1, w = L * Math.sqrt(Math.max(0.05, 1 - u * u)) * r.range(0.85, 1.05);
        const cxl = x0 + L / 2 + r.range(-0.08, 0.08) * L, yy = y + q * sp;
        sc.line(subdivide([cxl - w / 2, yy, cxl + w / 2, yy], 2), TINT, TEX);
        ends.push([cxl - w / 2 - 0.3, cxl + w / 2 + 0.3, yy]);
      }
      const poly = [];
      ends.forEach(([a, , yy], q) => poly.push(a, yy + (q === 0 ? -0.45 : 0)));
      for (let q = ends.length - 1; q >= 0; q--) poly.push(ends[q][1], ends[q][2] + (q === ends.length - 1 ? 0.45 : 0));
      sc.fill(poly);
    }
  } else if (kind === 'mackerel') {
    const y0 = lerp(top, bottom, r.range(0, 0.3)), y1 = lerp(top, bottom, r.range(0.55, 0.95));
    const s = r.range(1.2, 2.4), cxm = r.range(0.2, 0.8) * W;
    for (let y = y1, row = 0; y > y0; y -= s * 0.75, row++) {
      for (let x = (row % 2) * s; x < W + s; x += s * 2.1) {
        const d = Math.hypot((x - cxm) / (W * 0.5), (y - (y0 + y1) / 2) / ((y1 - y0) / 2 + 1));
        if (sc.noise.n2(x * 0.03, y * 0.05) * 0.5 + 0.7 - d < 0.2) continue;
        const arc = arcPts(x, y, s, s * 0.6, PI, 0, 10);
        sc.line(arc, TINT, ORG);
        sc.fill(arc.concat([x + s, y + 0.1, x - s, y + 0.1]));
      }
    }
  }
}
function windLines(sc, r, top, bottom) {
  const W = sc.W, N = sc.noise;
  const sep = r.range(1.6, 3.2) / Math.sqrt(sc.dens), cell = sep;
  const gw = Math.ceil(W / cell) + 2, gh = Math.ceil((bottom - top) / cell) + 2;
  const occ = new Uint8Array(gw * gh);
  const gi = (x, y) => { const i = Math.floor(x / cell) + 1, j = Math.floor((y - top) / cell) + 1; return i >= 0 && j >= 0 && i < gw && j < gh ? j * gw + i : -1; };
  const sc2 = r.range(0.012, 0.03), curl = r.range(0.4, 1.2), base = r.range(-0.15, 0.15);
  const ang = (x, y) => base + N.fbm(x * sc2, y * sc2 * 1.6 + 40, 3) * curl;
  const tries = Math.round(W * (bottom - top) / (sep * sep) * 0.8);
  for (let t = 0; t < tries; t++) {
    const x = r.range(0, W), y = r.range(top, bottom);
    const g = gi(x, y); if (g < 0 || occ[g] || !sc.free(x, y)) continue;
    const line = [];
    for (const dir of [1, -1]) {
      let px = x, py = y; const seg = [];
      for (let k = 0; k < 220; k++) {
        const a = ang(px, py);
        px += Math.cos(a) * 0.7 * dir; py += Math.sin(a) * 0.7 * dir;
        const q = gi(px, py);
        if (q < 0 || occ[q] || py > bottom || py < top) break;
        seg.push(px, py);
      }
      if (dir === 1) line.push(...revPts(seg)); else line.push(...seg);
      if (dir === 1) line.push(x, y);
    }
    if (line.length < 12) continue;
    for (let k = 0; k < line.length; k += 2) { const q = gi(line[k], line[k + 1]); if (q >= 0) occ[q] = 1; }
    sc.line(line, TINT, TEX);
  }
}

/* --------------------------------------------------------------- render */
// an overhanging bough entering from a top corner, drawn nearest of all
function bough(sc, side) {
  const r = sc.rng('bough'), v = sc.view, vw = v.x1 - v.x0, vh = v.y1 - v.y0;
  const rootX = side < 0 ? v.x0 - 4 : v.x1 + 4, rootY = v.y0 + vh * r.range(0.04, 0.22);
  const reach = vw * r.range(0.35, 0.6), drop = vh * r.range(0.16, 0.3);
  const cx = rootX - side * reach * 0.55, cy = rootY + drop * 0.25;
  const A = [];
  const N = Math.round(clamp(reach * drop / 6, 160, 650));
  for (let g = 0; g < N * 30 && A.length < N * 2; g++) {
    const px = cx + r.range(-1, 1) * reach * 0.6, py = cy + r.range(-1, 1) * drop * 0.75;
    const u = (px - cx) / (reach * 0.55), w = (py - cy) / (drop * 0.6);
    if (u * u + w * w < 1 && sc.noise.n2(px * 0.08, py * 0.08) > -0.35) A.push(px, py);
  }
  const seg = Math.max(0.5, reach / 60);
  const T = colonize(r, A, [rootX, rootY], { seg, infl: seg * 10, kill: seg * 2.2, trop: [0, 0.06], up: [-side * 0.97, 0.24], wob: 0.15, maxIter: 300 });
  const scale = r.range(2.5, 5) / T.th[0];
  const fronts = [], backs = [];
  const gs = reach / r.range(7, 11), cells = new Map();
  for (let i = 1; i < T.n; i++) {
    if (T.th[i] > 2.5) continue;
    const k = Math.floor(T.X[i] / gs) * 100003 + Math.floor(T.Y[i] / gs);
    let cc = cells.get(k); if (!cc) cells.set(k, (cc = [0, 0, 0])); cc[0] += T.X[i]; cc[1] += T.Y[i]; cc[2]++;
  }
  for (const cc of cells.values()) {
    const cl = { x: cc[0] / cc[2] + r.range(-0.2, 0.2) * gs, y: cc[1] / cc[2] + r.range(-0.1, 0.35) * gs, rad: gs * r.range(0.42, 0.7) };
    (r.chance(0.55) ? fronts : backs).push(cl);
  }
  const style = sc.comp.crownStyle === 'cloud' ? 'leafy' : sc.comp.crownStyle;
  const pen = () => (sc.comp.season === 'autumn' ? r.weighted([[ACC, 2], [FLORA, 1], [KEY, 1]]) : r.weighted([[FLORA, 3], [KEY, 1]]));
  const drawC = (cl) => { const p = pen(); foliageCluster(sc, cl.x, cl.y, cl.rad, p, p, r, { style, sq: r.range(0.6, 0.8) }); };
  fronts.forEach(drawC);
  drawBranches(sc, T, scale, { pen: KEY, bark: true, r, flare: 0 });
  backs.forEach(drawC);
}
function render(sc) {
  drawFrame(sc);
  if (sc.comp.bough) bough(sc, sc.comp.bough);
  const objs = placeObjects(sc);
  const bands = sc.bands;
  for (let k = bands.length - 1; k >= 0; k--) {
    const b = bands[k];
    const items = objs.filter((o) => o.band === k).sort((a, z) => z.y - a.y);
    if (b.treat === 'meadow' || b.treat === 'snow' || (b.fg && b.treat === 'prairie')) {
      tallGround(sc, b, items);
    } else {
      for (const o of items) o.draw(sc);
      rockFaces(sc, b);
      switch (b.treat) {
        case 'farm': farm(sc, b); break;
        case 'forest': forestBand(sc, b); break;
        case 'treeline': treelineBand(sc, b); break;
        case 'stipple': stippleBand(sc, b); break;
        case 'haze': hazeBand(sc, b); break;
        case 'hatch': hatchBand(sc, b); break;
        case 'prairie': prairieBand(sc, b); ridgeLine(sc, b, b.t < 0.3 ? TINT : KEY); break;
        case 'water': waterBand(sc, b); break;
        case 'outline': ridgeLine(sc, b, b.t < 0.3 ? TINT : KEY, b.t < 0.1); break;
        default: ridgeLine(sc, b, KEY);
      }
    }
    sc.fill(bandPolygon(b, sc.H));
  }
  drawSky(sc);
}

/* ---------------------------------------------------------- post-process */
// Codex Intervallorum page geometry, read from JosiahAlanLee/Codex-Intervallorum@b789e03:
//   pagePt       binding/bind.py: PW, PH = 504.0, 720.0 (7 x 10 in)
//   textBlockPt  the frame shared by books/07_septimus/build.py (Clavis, De Vinculis),
//                books/00_accusator/build.py and books/00_matres/build.py: paragraphs drawn at x = 52 and
//                wrapped to 400 pt; the first starts at y = 638 and none goes below y = 55 (origin bottom-left)
//   plotMasterMM common/plot/plate.py: W, H = 210, 297 and within_page_with_8mm_margin
//                (8 <= x <= 202, 10 <= y <= 288)
//   inks         common/plot/plotkit.py INK, RED; common/plot/plate.py PAPER; binding/backmatter.py MUTE
const CODEX = {
  source: 'JosiahAlanLee/Codex-Intervallorum@b789e03f30034bc8403f8a40aaf83842885aaad5',
  pagePt: [504, 720],
  trimMM: [177.8, 254],
  textBlockPt: { left: 52, right: 452, bottom: 55, top: 638 },
  plotMasterMM: { sheet: [210, 297], extent: [8, 10, 202, 288] },
  inks: { paper: '#ede6d4', ink: '#161918', red: '#a32b24', mute: '#5a4331' },
};
// the plot master's safe area as [top, right, bottom, left] insets in mm
CODEX.plotMasterMM.inset = [CODEX.plotMasterMM.extent[1], CODEX.plotMasterMM.sheet[0] - CODEX.plotMasterMM.extent[2],
  CODEX.plotMasterMM.sheet[1] - CODEX.plotMasterMM.extent[3], CODEX.plotMasterMM.extent[0]];
// A zone is one or more rectangles (mm, top-left origin) with a fade width. 'codex' is the book's text
// block, scaled to the trim; on a spread each page gets its own block, unmirrored as in the source frames.
function textZone(kind, W, H, bleed, spread) {
  if (!kind || kind === 'none') return null;
  const b = bleed || 0, tw = W - 2 * b, th = H - 2 * b;
  if (kind === 'codex') {
    const [pw, ph] = CODEX.pagePt, tb = CODEX.textBlockPt;
    const pages = spread ? 2 : 1, cw = tw / pages, rects = [];
    for (let i = 0; i < pages; i++) {
      const ox = b + i * cw;
      rects.push({ x0: ox + cw * tb.left / pw, x1: ox + cw * tb.right / pw, y0: b + th * (ph - tb.top) / ph, y1: b + th * (ph - tb.bottom) / ph });
    }
    return { rects, fade: 4.5 * cw / CODEX.trimMM[0] };
  }
  const z = { x0: b + tw * 0.08, x1: b + tw * 0.92 };
  if (kind === 'top') { z.y0 = b + th * 0.05; z.y1 = b + th * 0.46; }
  else if (kind === 'middle') { z.y0 = b + th * 0.27; z.y1 = b + th * 0.73; }
  else if (kind === 'bottom') { z.y0 = b + th * 0.54; z.y1 = b + th * 0.95; }
  else return null;
  return { rects: [z], fade: Math.min(tw, th) * 0.12 };
}
function zoneAt(z, x, y) {
  if (!z) return 0;
  let v = 0;
  for (const q of z.rects) {
    const d = Math.min(x - q.x0, q.x1 - x, y - q.y0, q.y1 - y);
    if (d > 0) v = Math.max(v, smooth(0, z.fade, d));
  }
  return v;
}
function post(sc) {
  const P = sc.P, imp = clamp(P.imperfection ?? 0.5, 0, 1), N = sc.noise, r = sc.rng('post');
  const N2 = makeNoise(sc.rng('grain'));
  const zone0 = textZone(P.textZone, sc.W, sc.H, P.bleed, P.spread);
  const tintMode = P.zoneMode === 'tint';
  const zoneStrength = P.zoneStrength ?? (tintMode ? 1 : 0.82);
  const amp = imp * 0.3, f = 1 / 13;
  const out = [];
  const grain = imp * 0.16;
  const zval = (x, y) => {
    const zv = zoneAt(zone0, x, y) * zoneStrength;
    return zv > 0 && (N2.n2(x * 0.22, y * 0.22) * 0.5 + 0.5) * 0.85 + N2.n2(x * 1.3, y * 1.3) * 0.15 < zv;
  };
  for (const s of sc.strokes) {
    let p = s.pts;
    const L = plen(p);
    const zone = s.f === 'frame' ? null : zone0;
    if (zone && !tintMode && L < 4) {
      const mx = p[0] + (p[p.length - 2] - p[0]) / 2, my = p[1] + (p[p.length - 1] - p[1]) / 2;
      if (r.rnd() < zoneAt(zone, mx, my) * zoneStrength) continue;
    }
    if (s.k !== FLECK && amp > 0) {
      p = subdivide(p, 1.2);
      const jx = r.range(-1, 1) * amp * 0.25, jy = r.range(-1, 1) * amp * 0.25;
      for (let i = 0; i < p.length; i += 2) {
        const x = p[i], y = p[i + 1];
        p[i] = x + amp * N.n2(x * f, y * f + 31.7) + jx;
        p[i + 1] = y + amp * N.n2(x * f + 57.1, y * f) + jy;
      }
    }
    if (s.k === RULED && imp > 0) {
      const n = p.length;
      if (n >= 4) {
        const e0 = r.range(-0.15, 1) * imp * 0.7, e1 = r.range(-0.15, 1) * imp * 0.7;
        let dx = p[0] - p[2], dy = p[1] - p[3], l = Math.hypot(dx, dy) || 1;
        p[0] += dx / l * e0; p[1] += dy / l * e0;
        dx = p[n - 2] - p[n - 4]; dy = p[n - 1] - p[n - 3]; l = Math.hypot(dx, dy) || 1;
        p[n - 2] += dx / l * e1; p[n - 1] += dy / l * e1;
      }
    }
    let pieces = [p];
    if (s.k !== FLECK && (grain > 0 || (zone && !tintMode))) {
      const pred = (x, y) => {
        if (grain > 0 && N2.n2(x * 0.42, y * 0.42) > 1 - grain * 2.4) return false;
        if (zone && !tintMode && zval(x, y)) return false;
        return true;
      };
      pieces = clipPred(p, pred, 0.25).filter((q) => plen(q) > 0.45);
    }
    if (zone && tintMode && s.p !== TINT) {
      const split = [];
      for (const q of pieces) {
        if (q.length <= 4 && s.k === FLECK) { split.push([q, zval(q[0], q[1])]); continue; }
        for (const a of clipPred(q, (x, y) => !zval(x, y), 0.3)) split.push([a, false]);
        for (const a of clipPred(q, (x, y) => zval(x, y), 0.3)) split.push([a, true]);
      }
      for (const [q, inz] of split) if (plen(q) > 0.15) out.push({ p: inz ? TINT : s.p, k: s.k, pts: q });
      continue;
    }
    for (const q of pieces) {
      out.push({ p: s.p, k: s.k, pts: q });
      if (s.k === RULED && imp > 0 && r.chance(imp * 0.1) && plen(q) > 3) {
        const ox = r.range(-0.35, 0.35) * imp, oy = r.range(-0.35, 0.35) * imp;
        const d = q.map((v, i) => v + (i % 2 ? oy : ox));
        out.push({ p: s.p, k: s.k, pts: d });
      }
    }
  }
  if (!P.inset) return out;
  // plot masters: wobble and overshoot must not carry a stroke past the safe margin
  const [it, ir, ib, il] = P.inset, e = 0.15;
  const inside = (x, y) => x >= il + e && x <= sc.W - ir - e && y >= it + e && y <= sc.H - ib - e;
  const kept = [];
  for (const s of out) {
    let all = true;
    for (let i = 0; i < s.pts.length && all; i += 2) all = inside(s.pts[i], s.pts[i + 1]);
    if (all) { kept.push(s); continue; }
    for (const q of clipPred(s.pts, inside, 0.1)) if (plen(q) > 0.15) kept.push({ p: s.p, k: s.k, pts: q });
  }
  return kept;
}

/* ---------------------------------------------------------------- public */
function generate(P0) {
  const t0 = Date.now();
  const P = Object.assign({ seed: 'driftless', W: 177.8, H: 254, density: 1, imperfection: 0.5, penWidth: 0.35, textZone: 'none', frame: 'auto', season: 'auto', time: 'auto', focal: 'auto', bleed: 0 }, P0);
  P.weights = Object.assign({ flora: 0.6, land: 0.6, built: 0.5, sky: 0.5 }, P0.weights || {});
  const sc = new Scene(P);
  compose(sc);
  buildBands(sc);
  render(sc);
  const strokes = post(sc);
  const pens = [[], [], [], []], len = [0, 0, 0, 0];
  for (const s of strokes) {
    const a = new Float32Array(s.pts.length);
    for (let i = 0; i < a.length; i++) a[i] = Math.round(s.pts[i] * 100) / 100;
    pens[s.p].push(a); len[s.p] += plen(s.pts);
  }
  const c = sc.comp;
  const lands = sc.bands.map((b) => b.treat);
  const traits = {
    Season: cap(c.season), Light: c.time === 'day' ? 'Day' : c.time === 'dusk' ? 'Dusk' : 'Night',
    Subject: FOCAL_NAMES[c.focal] || c.focal, Frame: FRAME_NAMES[c.frame] || c.frame,
    Ground: GROUND_NAMES[sc.bands[sc.bands.length - 1].treat] || sc.bands[sc.bands.length - 1].treat,
    Ridges: String(sc.bands.length), Sky: SKY_NAMES[c.sky] || c.sky, Clouds: CLOUD_NAMES[c.clouds] || c.clouds,
    Fields: lands.filter((t) => t === 'farm').length ? 'Contour strips' : lands.includes('forest') ? 'Woodland' : 'Open',
  };
  if (sc.bands.some((b) => b.water)) traits.Water = 'River';
  if (c.anomaly && c.focal !== 'monument') traits.Anomaly = 'Yes';
  return { W: P.W, H: P.H, seed: P.seed, params: P, pens, lengths: len, count: strokes.length, traits, ms: Date.now() - t0, sun: sc.sun || null };
}
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const FOCAL_NAMES = { oak: 'Bur oak', pine: 'White pine', grove: 'Oak grove', farmstead: 'Farmstead', watertower: 'Water tower', monument: 'Monument', rock: 'Sandstone tower', sun: 'Great sun', vista: 'Open vista' };
const FRAME_NAMES = { none: 'Full bleed', border: 'Ruled border', arch: 'Arched window', oculus: 'Oculus', arcade: 'Arcade' };
const GROUND_NAMES = { meadow: 'Meadow', snow: 'Snowfield', farm: 'Strip field', prairie: 'Short prairie' };
const SKY_NAMES = { lines: 'Ruled', dashes: 'Dashed', wind: 'Wind', clear: 'Clear', rays: 'Rays', stars: 'Stars' };
const CLOUD_NAMES = { none: 'None', cumulus: 'Cumulus', stratus: 'Stratus', mackerel: 'Mackerel' };

const PALETTES = {
  // the book's ground and inks; plot layers 1, 2 and 4 with the black pen and 3 with the red for its two-ink convention
  codex: { name: 'Codex', paper: '#ede6d4', inks: ['#161918', '#161918', '#a32b24', '#5a4331'] }, // CODEX.inks
  irongall: { name: 'Iron Gall', paper: '#f1ece2', inks: ['#231b14', '#4b3c2c', '#8f4a2b', '#9c8e79'] },
  fieldriso: { name: 'Field Riso', paper: '#f4f2ea', inks: ['#2c3a6a', '#127566', '#ee5a3a', '#86a7cf'] },
  lush: { name: 'Lush', paper: '#f3f1ea', inks: ['#2a2948', '#2d8657', '#e2497a', '#7fb1d6'] },
  barnyard: { name: 'Barnyard', paper: '#f6f4ef', inks: ['#1f1f1d', '#4d6b3b', '#b22e26', '#9ea3a6'] },
  prussian: { name: 'Prussian', paper: '#f4f3ee', inks: ['#1b2e49', '#2c4e72', '#3d6ea8', '#8fa6c3'] },
  graphite: { name: 'Graphite', paper: '#ffffff', inks: ['#2c2c2a', '#474744', '#686864', '#a3a39e'] },
  dusk: { name: 'Dusk', paper: '#f2e9e1', inks: ['#3a2440', '#5b6e4c', '#e0653a', '#e3a08a'] },
  nocturne: { name: 'Nocturne', paper: '#15181d', inks: ['#ebe5d5', '#8fb8a1', '#e8b14c', '#5f6c7d'] },
  kraft: { name: 'Kraft', paper: '#c8a67b', inks: ['#21170e', '#3b4a2a', '#f5f1e7', '#7f6142'] },
};
const PEN_NAMES = ['key', 'flora', 'accent', 'tint'];

function hex(c) { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function mixHex(a, b, t) { const A = hex(a), B = hex(b); return '#' + A.map((v, i) => Math.round(lerp(v, B[i], t)).toString(16).padStart(2, '0')).join(''); }
function inkColors(pal, strength) {
  const s = clamp(strength ?? 1, 0.05, 1);
  return pal.inks.map((c) => mixHex(pal.paper, c, s));
}
function fmt(v) { return (Math.round(v * 100) / 100).toString(); }
function orderPaths(paths) {
  // greedy nearest-neighbour ordering with path reversal, bucketed for speed
  const n = paths.length; if (n < 3) return paths;
  const cell = 6, grid = new Map(), used = new Uint8Array(n);
  const key = (x, y) => Math.floor(x / cell) * 100003 + Math.floor(y / cell);
  for (let i = 0; i < n; i++) {
    const p = paths[i];
    for (const e of [0, 1]) {
      const x = e ? p[p.length - 2] : p[0], y = e ? p[p.length - 1] : p[1];
      const k = key(x, y); let a = grid.get(k); if (!a) grid.set(k, (a = [])); a.push(i * 2 + e);
    }
  }
  const out = []; let cx = 0, cy = 0;
  for (let done = 0; done < n; done++) {
    let best = -1, bd = Infinity;
    const gx = Math.floor(cx / cell), gy = Math.floor(cy / cell);
    for (let ring = 0; ring < 400 && best < 0; ring++) {
      for (let dx = -ring; dx <= ring; dx++) for (let dy = -ring; dy <= ring; dy++) {
        if (Math.max(Math.abs(dx), Math.abs(dy)) !== ring) continue;
        const a = grid.get((gx + dx) * 100003 + (gy + dy)); if (!a) continue;
        for (const e of a) {
          const i = e >> 1; if (used[i]) continue;
          const p = paths[i], x = e & 1 ? p[p.length - 2] : p[0], y = e & 1 ? p[p.length - 1] : p[1];
          const d = (x - cx) * (x - cx) + (y - cy) * (y - cy);
          if (d < bd) { bd = d; best = e; }
        }
      }
      if (best >= 0 && ring > 0) break;
    }
    if (best < 0) { for (let i = 0; i < n; i++) if (!used[i]) { best = i * 2; break; } }
    const i = best >> 1; used[i] = 1;
    let p = paths[i];
    if (best & 1) { const q = new Float32Array(p.length); for (let k = 0, m = p.length >> 1; k < m; k++) { q[2 * k] = p[2 * (m - 1 - k)]; q[2 * k + 1] = p[2 * (m - 1 - k) + 1]; } p = q; }
    out.push(p); cx = p[p.length - 2]; cy = p[p.length - 1];
  }
  return out;
}
function travelLength(paths) {
  let L = 0, cx = 0, cy = 0;
  for (const p of paths) { L += Math.hypot(p[0] - cx, p[1] - cy); cx = p[p.length - 2]; cy = p[p.length - 1]; }
  return L;
}
function toSVG(res, o) {
  o = o || {};
  const pal = PALETTES[o.palette] || PALETTES.codex;
  const inks = inkColors(pal, o.strength);
  const W = res.W, H = res.H, pw = o.penWidth || res.params.penWidth || 0.35;
  const mis = o.misregister || [[0, 0], [0, 0], [0, 0], [0, 0]];
  const meta = { generator: 'Driftless Plates', seed: res.seed, size_mm: [W, H], palette: pal.name, strength: o.strength ?? 1, params: res.params, traits: res.traits };
  let s = `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="${fmt(W)}mm" height="${fmt(H)}mm" viewBox="0 0 ${fmt(W)} ${fmt(H)}">\n`;
  s += `<title>Driftless Plates ${escapeXml(String(res.seed))}</title>\n<metadata>${escapeXml(JSON.stringify(meta))}</metadata>\n`;
  if (o.background) s += `<g inkscape:groupmode="layer" inkscape:label="0-paper"><rect width="${fmt(W)}" height="${fmt(H)}" fill="${pal.paper}"/></g>\n`;
  const order = o.order || [3, 1, 2, 0];
  for (const pi of order) {
    let paths = res.pens[pi]; if (!paths || !paths.length) continue;
    if (o.optimize) paths = orderPaths(paths);
    const [dx, dy] = mis[pi] || [0, 0];
    s += `<g inkscape:groupmode="layer" inkscape:label="${pi + 1}-${PEN_NAMES[pi]}" fill="none" stroke="${inks[pi]}" stroke-width="${fmt(pw)}" stroke-linecap="round" stroke-linejoin="round"${dx || dy ? ` transform="translate(${fmt(dx)} ${fmt(dy)})"` : ''}>\n`;
    let d = '', count = 0;
    for (const p of paths) {
      d += 'M' + fmt(p[0]) + ' ' + fmt(p[1]) + 'L';
      for (let i = 2; i < p.length; i += 2) d += fmt(p[i]) + ' ' + fmt(p[i + 1]) + (i + 2 < p.length ? ' ' : '');
      if (++count >= 1200) { s += `<path d="${d}"/>\n`; d = ''; count = 0; }
    }
    if (d) s += `<path d="${d}"/>\n`;
    s += '</g>\n';
  }
  return s + '</svg>\n';
}
function escapeXml(t) { return t.replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c])); }
function misregistration(seed, imp) {
  const r = new Rng(String(seed), 'misreg');
  return [0, 1, 2, 3].map((i) => (i === 0 ? [0, 0] : [r.range(-1, 1) * imp * 0.45, r.range(-1, 1) * imp * 0.45]));
}
function plotStats(res, speed) {
  speed = speed || 25;
  let down = 0, lifts = 0;
  for (let i = 0; i < 4; i++) { down += res.lengths[i]; lifts += res.pens[i].length; }
  const secs = down / speed + lifts * 0.25;
  return { downMeters: down / 1000, lifts, hours: secs / 3600 };
}

const API = { generate, toSVG, textZone, CODEX, orderPaths, travelLength, PALETTES, PEN_NAMES, misregistration, plotStats, inkColors, version: '1.1.0' };
if (typeof module !== 'undefined' && module.exports) module.exports = API;
else G.PlateEngine = API;
})(typeof self !== 'undefined' ? self : this);
