/* Node lattice: a generative version of the cellular lattice on the Librum Quinque demon
   references. An anisotropic circle packing grown inside a host silhouette becomes a power
   diagram. Deep cells become long panes between curved ribs (pods of round cells, slate
   panes with veins, lace, hollows); a band of small cells at the edge becomes an open net;
   past the silhouette the diagram's edges become beaded tendrils that fray outward and drip.

   Page units: 1000 x 1500 (2:3, the renders' format). Everything is seeded and pure
   arithmetic, with no canvas, so the same seed gives the same scene in Node and in a page.
   Used by plate.mjs (plot masters), node-lattice.html (the interactive page) and the tests. */
const NodeLattice = (() => {
  'use strict';
  const VERSION = '0.1.0';
  const PW = 1000, PH = 1500, TAU = Math.PI * 2;
  const COL = { paper: '#ede6d4', ink: '#161918', red: '#a32b24', slate: '#4f6f7a', ochre: '#b98a45' };
  const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
  const lerp = (a, b, t) => a + (b - a) * t;
  const smooth = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };
  const now = () => (typeof performance !== 'undefined' ? performance : Date).now();

  // ---------------------------------------------------------------- randomness
  function cyrb128(str) {
    let h1 = 1779033703, h2 = 3144134277, h3 = 1013904242, h4 = 2773480762;
    for (let i = 0, k; i < str.length; i++) {
      k = str.charCodeAt(i);
      h1 = h2 ^ Math.imul(h1 ^ k, 597399067);
      h2 = h3 ^ Math.imul(h2 ^ k, 2869860233);
      h3 = h4 ^ Math.imul(h3 ^ k, 951274213);
      h4 = h1 ^ Math.imul(h4 ^ k, 2716044179);
    }
    h1 = Math.imul(h3 ^ (h1 >>> 18), 597399067);
    h2 = Math.imul(h4 ^ (h2 >>> 22), 2869860233);
    h3 = Math.imul(h1 ^ (h3 >>> 17), 951274213);
    h4 = Math.imul(h2 ^ (h4 >>> 19), 2716044179);
    h1 ^= h2 ^ h3 ^ h4; h2 ^= h1; h3 ^= h1; h4 ^= h1;
    return [h1 >>> 0, h2 >>> 0, h3 >>> 0, h4 >>> 0];
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
  // One stream per stage, so a change to one control does not reshuffle the others.
  function rngFor(seed, stage) { const h = cyrb128(String(seed) + '|' + stage); const r = sfc32(h[0], h[1], h[2], h[3]); for (let i = 0; i < 12; i++) r(); return r; }
  const hash01 = (s) => cyrb128(s)[0] / 4294967296;

  function makeNoise(rng) {
    const perm = new Uint8Array(512), base = [];
    for (let i = 0; i < 256; i++) base.push(i);
    for (let i = 255; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const t = base[i]; base[i] = base[j]; base[j] = t; }
    for (let i = 0; i < 512; i++) perm[i] = base[i & 255];
    const gx = new Float32Array(256), gy = new Float32Array(256);
    for (let i = 0; i < 256; i++) { const a = rng() * TAU; gx[i] = Math.cos(a); gy[i] = Math.sin(a); }
    const ox = rng() * 256, oy = rng() * 256;
    function n2(x, y) {
      x += ox; y += oy;
      const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
      const X = xi & 255, Y = yi & 255;
      const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10), v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
      const aa = perm[perm[X] + Y], ab = perm[perm[X] + Y + 1], ba = perm[perm[X + 1] + Y], bb = perm[perm[X + 1] + Y + 1];
      const n00 = gx[aa] * xf + gy[aa] * yf, n10 = gx[ba] * (xf - 1) + gy[ba] * yf;
      const n01 = gx[ab] * xf + gy[ab] * (yf - 1), n11 = gx[bb] * (xf - 1) + gy[bb] * (yf - 1);
      const a = n00 + u * (n10 - n00), b = n01 + u * (n11 - n01);
      return a + v * (b - a);
    }
    return function (x, y, oct) {
      oct = oct || 2; let s = 0, amp = 1, f = 1, t = 0;
      for (let o = 0; o < oct; o++) { s += amp * n2(x * f + o * 31.7, y * f - o * 17.3); t += amp; amp *= 0.5; f *= 2.03; }
      return clamp(0.5 + 0.85 * s / t, 0, 1);
    };
  }

  // ---------------------------------------------------------------- host field
  // A signed-distance grid (positive inside) on a 250 x 375 lattice, 4 units per cell.
  const GW = 250, GH = 375, GC = 4;

  function edt1d(f, d, v, z, n) {
    let k = 0; v[0] = 0; z[0] = -Infinity; z[1] = Infinity;
    for (let q = 1; q < n; q++) {
      let s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
      while (s <= z[k]) { k--; s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]); }
      k++; v[k] = q; z[k] = s; z[k + 1] = Infinity;
    }
    k = 0;
    for (let q = 0; q < n; q++) { while (z[k + 1] < q) k++; d[q] = (q - v[k]) * (q - v[k]) + f[v[k]]; }
  }
  function edt(mask, val) {
    const g = new Float64Array(GW * GH);
    for (let i = 0; i < GW * GH; i++) g[i] = mask[i] === val ? 0 : 1e12;
    const n = Math.max(GW, GH), f = new Float64Array(n), d = new Float64Array(n), v = new Int32Array(n), z = new Float64Array(n + 1);
    for (let x = 0; x < GW; x++) {
      for (let y = 0; y < GH; y++) f[y] = g[y * GW + x];
      edt1d(f, d, v, z, GH);
      for (let y = 0; y < GH; y++) g[y * GW + x] = d[y];
    }
    for (let y = 0; y < GH; y++) {
      for (let x = 0; x < GW; x++) f[x] = g[y * GW + x];
      edt1d(f, d, v, z, GW);
      for (let x = 0; x < GW; x++) g[y * GW + x] = d[x];
    }
    return g;
  }
  function decodeRLE(b64) {
    const bin = typeof atob === 'function' ? atob(b64) : Buffer.from(b64, 'base64').toString('binary');
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const out = new Uint8Array(GW * GH); let k = 0;
    for (let y = 0; y < GH; y++) {
      const n = bytes[k++]; let x = 0, val = 0;
      for (let r = 0; r < n; r++) { const len = bytes[k++]; if (val) out.fill(1, y * GW + x, y * GW + x + len); x += len; val ^= 1; }
    }
    return out;
  }
  function fieldFromMask(mask) {
    const dIn = edt(mask, 0), dOut = edt(mask, 1), sd = new Float32Array(GW * GH);
    for (let i = 0; i < GW * GH; i++) sd[i] = mask[i] ? (Math.sqrt(dIn[i]) - 0.5) * GC : -(Math.sqrt(dOut[i]) - 0.5) * GC;
    return sd;
  }
  function fieldFromSDF(fn) { // fn: negative inside. Evaluated on every other cell, the rest interpolated
    const sd = new Float32Array(GW * GH);
    for (let y = 0; y < GH; y += 2) for (let x = 0; x < GW; x += 2) sd[y * GW + x] = -fn((x + 0.5) * GC, (y + 0.5) * GC);
    for (let y = 0; y < GH; y += 2) for (let x = 1; x < GW; x += 2) sd[y * GW + x] = x + 1 < GW ? (sd[y * GW + x - 1] + sd[y * GW + x + 1]) / 2 : sd[y * GW + x - 1];
    for (let y = 1; y < GH; y += 2) for (let x = 0; x < GW; x++) sd[y * GW + x] = y + 1 < GH ? (sd[(y - 1) * GW + x] + sd[(y + 1) * GW + x]) / 2 : sd[(y - 1) * GW + x];
    return sd;
  }
  function thickness(sd) { // local half-thickness: a max filter of the distance field
    const R = 10, tmp = new Float32Array(GW * GH), out = new Float32Array(GW * GH);
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
      let m = 0; for (let k = Math.max(0, x - R); k <= Math.min(GW - 1, x + R); k++) m = Math.max(m, sd[y * GW + k]);
      tmp[y * GW + x] = m;
    }
    for (let x = 0; x < GW; x++) for (let y = 0; y < GH; y++) {
      let m = 0; for (let k = Math.max(0, y - R); k <= Math.min(GH - 1, y + R); k++) m = Math.max(m, tmp[k * GW + x]);
      out[y * GW + x] = m;
    }
    return out;
  }
  function sampler(sd) {
    const at = (x, y) => {
      let gx = x / GC - 0.5, gy = y / GC - 0.5;
      let extra = 0;
      if (gx < 0) { extra += gx * GC; gx = 0; } else if (gx > GW - 1.001) { extra -= (gx - GW + 1.001) * GC; gx = GW - 1.001; }
      if (gy < 0) { extra += gy * GC; gy = 0; } else if (gy > GH - 1.001) { extra -= (gy - GH + 1.001) * GC; gy = GH - 1.001; }
      const i = Math.floor(gx), j = Math.floor(gy), fx = gx - i, fy = gy - j, k = j * GW + i;
      const a = sd[k] + (sd[k + 1] - sd[k]) * fx, b = sd[k + GW] + (sd[k + GW + 1] - sd[k + GW]) * fx;
      return a + (b - a) * fy + extra;
    };
    const grad = (x, y) => [(at(x + GC, y) - at(x - GC, y)) / (2 * GC), (at(x, y + GC) - at(x, y - GC)) / (2 * GC)];
    return { at, grad };
  }

  // ---------------------------------------------------------------- native hosts
  function sdRoundCone(px, py, ax, ay, r1, bx, by, r2) {
    const dx = bx - ax, dy = by - ay, h = Math.hypot(dx, dy) || 1e-6, ux = dx / h, uy = dy / h;
    const qx = Math.abs(-(px - ax) * uy + (py - ay) * ux), qy = (px - ax) * ux + (py - ay) * uy;
    const b = clamp((r1 - r2) / h, -0.999, 0.999), a = Math.sqrt(1 - b * b), k = -b * qx + a * qy;
    if (k < 0) return Math.hypot(qx, qy) - r1;
    if (k > a * h) return Math.hypot(qx, qy - h) - r2;
    return qx * a + qy * b - r1;
  }
  function sdPolygon(px, py, v) {
    let d = (px - v[0][0]) ** 2 + (py - v[0][1]) ** 2, s = 1;
    for (let i = 0, j = v.length - 1; i < v.length; j = i, i++) {
      const ex = v[j][0] - v[i][0], ey = v[j][1] - v[i][1], wx = px - v[i][0], wy = py - v[i][1];
      const t = clamp((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1), bx = wx - ex * t, by = wy - ey * t;
      d = Math.min(d, bx * bx + by * by);
      const c1 = py >= v[i][1], c2 = py < v[j][1], c3 = ex * wy > ey * wx;
      if ((c1 && c2 && c3) || (!c1 && !c2 && !c3)) s = -s;
    }
    return s * Math.sqrt(d);
  }
  function sdEllipse(px, py, cx, cy, rx, ry, ang) {
    const c = Math.cos(ang), s = Math.sin(ang), x = (px - cx) * c + (py - cy) * s, y = -(px - cx) * s + (py - cy) * c;
    return (Math.hypot(x / rx, y / ry) - 1) * Math.min(rx, ry);
  }
  const smin = (a, b, k) => { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k * 0.25; };
  function quadPts(a, c, b, n) { const out = []; for (let i = 1; i < n; i++) { const t = i / n, u = 1 - t; out.push([u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]]); } return out; }

  function nativeRobe(seed) {
    const R = rngFor(seed, 'host-robe'), rr = (a, b) => a + (b - a) * R();
    const parts = [], fixed = [];
    const x0 = 500 + rr(-20, 20);
    const nHood = 1; // more than one void in a row reads as a face
    const hoodR = rr(80, 96);
    const headY = rr(330, 380);
    const peak = rr(185, 250);
    const shY = headY + rr(85, 115);
    const sw = rr(118, 150);
    const hemY = rr(1215, 1270), hemW = rr(215, 320), hemShift = rr(-40, 40);
    const spread = hoodR * rr(1.55, 1.9);
    for (let k = 0; k < nHood; k++) {
      const off = k - (nHood - 1) / 2;
      const hx = x0 + off * spread + rr(-10, 10), hy = headY + Math.abs(off) * rr(20, 55) + rr(-8, 8);
      const tilt = off * rr(35, 70) + rr(-30, 30), px = hx + tilt, py = hy - peak - Math.abs(off) * rr(-20, 30), pr = rr(5, 8);
      parts.push((x, y) => sdRoundCone(x, y, hx, hy, hoodR, px, py, pr));
      const vang = Math.PI / 2 - Math.atan2(tilt, hy - py) * 0.5;
      fixed.push({ x: hx + tilt * 0.1, y: hy + hoodR * 0.16, a: hoodR * rr(0.56, 0.66), b: hoodR * rr(0.36, 0.44), ang: vang, style: 'void' });
    }
    const span = spread * (nHood - 1) / 2;
    parts.push((x, y) => sdRoundCone(x, y, x0, headY + 10, hoodR * 0.92 + span * 0.6, x0, shY + 70, sw * 0.88));
    // the robe: an A-line with an irregular, tattered hem
    const L0 = [x0 - sw * 0.82, shY + 40], R0 = [x0 + sw * 0.82, shY + 40];
    const Lh = [x0 - hemW + hemShift, hemY], Rh = [x0 + hemW + hemShift, hemY];
    const bulge = rr(-20, 40);
    const left = quadPts(L0, [x0 - sw * 0.82 - bulge, (shY + hemY) * 0.5], Lh, 10);
    const right = quadPts(Rh, [x0 + sw * 0.82 + bulge, (shY + hemY) * 0.5], R0, 10);
    const nt = Math.round(rr(3, 6)), hem = [Lh];
    for (let i = 1; i < 2 * nt; i++) {
      const t = i / (2 * nt);
      hem.push([lerp(Lh[0], Rh[0], t) + rr(-18, 18), hemY + (i % 2 === 1 ? rr(30, 130) : -rr(10, 60))]);
    }
    hem.push(Rh);
    const poly = [L0, ...left, ...hem, ...right, R0];
    // sleeves: empty bell sleeves; no pose ends in a hand
    for (const s of [-1, 1]) {
      const pose = ['down', 'down', 'out', 'out', 'raise', 'front', 'hold', 'hold'][Math.floor(R() * 8)];
      const S = [x0 + s * sw * 0.86, shY + 40];
      let d1, d2;
      if (pose === 'down') { d1 = [s * rr(0.3, 0.55), 1]; d2 = [s * rr(0.05, 0.35), 1]; }
      else if (pose === 'out') { d1 = [s * rr(0.8, 1), rr(0.3, 0.7)]; d2 = [s, rr(-0.3, 0.25)]; }
      else if (pose === 'raise') { d1 = [s * rr(0.8, 1), rr(-0.1, 0.3)]; d2 = [s * rr(0.1, 0.45), -1]; }
      else if (pose === 'front') { d1 = [s * rr(0.25, 0.45), 1]; d2 = [-s * rr(0.7, 1), rr(-0.4, -0.1)]; }
      else { d1 = [s * rr(0.35, 0.6), 1]; d2 = [s * rr(0.6, 1), rr(-0.5, -0.1)]; }
      const n1 = Math.hypot(d1[0], d1[1]), n2 = Math.hypot(d2[0], d2[1]);
      const L1 = rr(150, 185), L2 = rr(120, 160);
      const E = [S[0] + d1[0] / n1 * L1, S[1] + d1[1] / n1 * L1], Wr = [E[0] + d2[0] / n2 * L2, E[1] + d2[1] / n2 * L2];
      const r1 = rr(42, 50), r2 = rr(34, 40), r3 = rr(56, 78);
      parts.push((x, y) => sdRoundCone(x, y, S[0], S[1], r1, E[0], E[1], r2));
      parts.push((x, y) => sdRoundCone(x, y, E[0], E[1], r2, Wr[0], Wr[1], r3));
      const m = [lerp(E[0], Wr[0], 0.7), lerp(E[1], Wr[1], 0.7) + 25], hl = rr(170, 300), hr = rr(48, 66), tr = rr(5, 9), tx = m[0] + s * rr(-15, 35);
      if (d2[1] / n2 < 0.75) parts.push((x, y) => sdRoundCone(x, y, m[0], m[1], hr, tx, Math.min(m[1] + hl, hemY + 60), tr));
    }
    const sdf = (x, y) => {
      let d = sdPolygon(x, y, poly);
      for (let k = 0; k < parts.length; k++) d = smin(d, parts[k](x, y), k < 2 ? 46 : 28);
      return d;
    };
    const seal = { x: x0 + rr(-14, 14), y: shY + rr(120, 175), a: rr(26, 34), b: 0, ang: 0, style: 'seal' };
    seal.b = seal.a;
    return { sdf, fixed, seal, label: 'Native: empty robe' };
  }

  function nativeChair(seed) {
    const R = rngFor(seed, 'host-chair'), rr = (a, b) => a + (b - a) * R();
    const x0 = 500 + rr(-30, 30), seatY = rr(800, 870), floorY = rr(1250, 1300);
    const sw = rr(160, 215), depth = rr(55, 90), backH = rr(430, 560), lean = rr(-0.12, 0.1);
    const legR = rr(13, 18), parts = [];
    const corners = [[x0 - sw, seatY + depth * 0.5], [x0 + sw, seatY + depth * 0.5], [x0 - sw * 0.78, seatY - depth * 0.6], [x0 + sw * 0.78, seatY - depth * 0.6]];
    corners.forEach(([cx, cy], i) => {
      const splay = (cx - x0) * rr(0.08, 0.22), fy = floorY - (i >= 2 ? depth * 0.9 : 0) + rr(-10, 10);
      parts.push((x, y) => sdRoundCone(x, y, cx, cy, legR * 1.6, cx + splay, fy, legR * 0.8));
    });
    const seat = [[x0 - sw - 18, seatY + depth * 0.55 + 18], [x0 + sw + 18, seatY + depth * 0.55 + 18], [x0 + sw * 0.8 + 14, seatY - depth * 0.6 - 10], [x0 - sw * 0.8 - 14, seatY - depth * 0.6 - 10]];
    const bTop = seatY - depth * 0.6 - backH, bx = x0 + lean * backH;
    const back = [[x0 - sw * 0.8, seatY - depth * 0.6], [x0 + sw * 0.8, seatY - depth * 0.6], [bx + sw * 0.62, bTop + 60], [bx, bTop - rr(0, 60)], [bx - sw * 0.62, bTop + 60]];
    const hollow = R() < 0.6;
    const sdf = (x, y) => {
      let d = sdPolygon(x, y, seat);
      let b = sdPolygon(x, y, back);
      if (hollow) b = Math.max(b, -sdEllipse(x, y, (bx + x0) * 0.5, seatY - depth * 0.6 - backH * 0.45, sw * 0.36, backH * 0.25, 0));
      d = smin(d, b, 24);
      for (const p of parts) d = smin(d, p(x, y), 22);
      return d;
    };
    const seal = { x: x0 + lean * backH * 0.25, y: seatY - depth * 0.6 - backH * 0.82, a: rr(26, 32), b: 0, ang: 0, style: 'seal' };
    seal.b = seal.a;
    return { sdf, fixed: [], seal, label: 'Native: empty chair' };
  }

  // ---------------------------------------------------------------- geometry helpers
  function clipPoly(poly, nx, ny, b, tag) { // keep n.x <= b; poly: {x[], y[], t[]}
    const n = poly.x.length, ox = [], oy = [], ot = [];
    for (let k = 0; k < n; k++) {
      const k2 = (k + 1) % n, px = poly.x[k], py = poly.y[k], qx = poly.x[k2], qy = poly.y[k2], tg = poly.t[k];
      const dp = nx * px + ny * py - b, dq = nx * qx + ny * qy - b;
      if (dp <= 0) {
        ox.push(px); oy.push(py); ot.push(tg);
        if (dq > 0) { const s = dp / (dp - dq); ox.push(px + (qx - px) * s); oy.push(py + (qy - py) * s); ot.push(tag); }
      } else if (dq <= 0) {
        const s = dp / (dp - dq); ox.push(px + (qx - px) * s); oy.push(py + (qy - py) * s); ot.push(tg);
      }
    }
    return { x: ox, y: oy, t: ot };
  }
  function area(pts) { let a = 0; for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) a += pts[j][0] * pts[i][1] - pts[i][0] * pts[j][1]; return a / 2; }
  function centroid(pts) {
    let a = 0, cx = 0, cy = 0;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) { const f = pts[j][0] * pts[i][1] - pts[i][0] * pts[j][1]; a += f; cx += (pts[j][0] + pts[i][0]) * f; cy += (pts[j][1] + pts[i][1]) * f; }
    if (Math.abs(a) < 1e-9) { let sx = 0, sy = 0; for (const p of pts) { sx += p[0]; sy += p[1]; } return [sx / pts.length, sy / pts.length]; }
    return [cx / (3 * a), cy / (3 * a)];
  }
  function hull(pts) {
    const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    if (p.length < 3) return p;
    const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const q of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 1e-9) lo.pop(); lo.push(q); }
    for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], q) <= 1e-9) up.pop(); up.push(q); }
    up.pop(); lo.pop();
    return lo.concat(up);
  }
  // offset a closed polygon inward by d (outward if d < 0); miters clamped at sharp tips
  function inset(pts, d) {
    const n = pts.length; if (n < 3) return null;
    const s = area(pts) > 0 ? 1 : -1, nrm = [];
    for (let i = 0; i < n; i++) {
      const a = pts[i], b = pts[(i + 1) % n], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1e-9;
      nrm.push([-dy / L * s, dx / L * s]); // left normal for CCW = inward
    }
    const out = [];
    for (let i = 0; i < n; i++) {
      const n1 = nrm[(i + n - 1) % n], n2 = nrm[i], dot = n1[0] * n2[0] + n1[1] * n2[1];
      let mx = n1[0] + n2[0], my = n1[1] + n2[1];
      if (1 + dot < 0.15) { const ml = Math.hypot(mx, my) || 1; mx = mx / ml * 2.2; my = my / ml * 2.2; }
      else { mx /= (1 + dot); my /= (1 + dot); const ml = Math.hypot(mx, my); if (ml > 2.6) { mx = mx / ml * 2.6; my = my / ml * 2.6; } }
      out.push([pts[i][0] + mx * d, pts[i][1] + my * d]);
    }
    return out;
  }
  function inPoly(x, y, pts) {
    let c = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c;
    }
    return c;
  }
  function edgeDist(x, y, pts) {
    let d = Infinity;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const ax = pts[j][0], ay = pts[j][1], ex = pts[i][0] - ax, ey = pts[i][1] - ay, L2 = ex * ex + ey * ey || 1e-9;
      const t = clamp(((x - ax) * ex + (y - ay) * ey) / L2, 0, 1), dx = x - ax - ex * t, dy = y - ay - ey * t;
      d = Math.min(d, dx * dx + dy * dy);
    }
    return Math.sqrt(d);
  }
  const polyDist = (x, y, pts) => (inPoly(x, y, pts) ? -1 : 1) * edgeDist(x, y, pts); // signed: negative inside
  function ellipsePts(e, grow, n) {
    const a = e.a + grow, b = e.b + grow, c = Math.cos(e.ang), s = Math.sin(e.ang), out = [];
    n = n || clamp(Math.round((a + b) * 1.1), 18, 120);
    for (let i = 0; i < n; i++) { const t = i / n * TAU, x = a * Math.cos(t), y = b * Math.sin(t); out.push([e.x + x * c - y * s, e.y + x * s + y * c]); }
    return out;
  }
  function ellipseDist(px, py, e) { // signed, approximate (radial)
    const c = Math.cos(e.ang), s = Math.sin(e.ang), x = (px - e.x) * c + (py - e.y) * s, y = -(px - e.x) * s + (py - e.y) * c;
    const m = Math.hypot(x / e.a, y / e.b), r = Math.hypot(x, y);
    if (m < 1e-9) return -Math.min(e.a, e.b);
    return (m - 1) * r / m;
  }
  function supportLen(nx, ny, ang, ah) { const c = Math.cos(ang), s = Math.sin(ang); return Math.hypot((nx * c + ny * s) * ah, (-nx * s + ny * c) / ah); }
  function chordOf(pts, ox, oy, dx, dy) { // intersections of the line o + s d with the polygon, as sorted s
    const out = [];
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const ax = pts[j][0], ay = pts[j][1], ex = pts[i][0] - ax, ey = pts[i][1] - ay;
      const den = dx * ey - dy * ex; if (Math.abs(den) < 1e-12) continue;
      const wx = ax - ox, wy = ay - oy, s = (wx * ey - wy * ex) / den, u = (wx * dy - wy * dx) / den;
      if (u >= 0 && u < 1) out.push(s);
    }
    return out.sort((a, b) => a - b);
  }

  // ---------------------------------------------------------------- generation
  const DEFAULTS = { cell: 13, rib: 2.6, elong: 2.3, drape: 0.5, sweep: 0.12, strut: 2.2, fray: 105, drips: 0.55, roses: 4, dissolve: 0, slate: 0.55, ground: true, seal: true };

  // The layout depends only on the host, the seed and the shape controls, so the page can keep it
  // and redress the same packing when an appearance control moves.
  const SAMPLE_FRAY = 170;
  function layout(seed, hostDef, P) {
    const t0 = now(); let tq = t0; const TM = {};
    // ------------------------------------------------ host
    let sd, label, fixed = [], seal = null, provenance;
    if (hostDef.kind === 'traced') {
      sd = fieldFromMask(hostDef.mask || (hostDef.mask = decodeRLE(hostDef.rle)));
      label = hostDef.label;
      provenance = { host: 'traced', source: hostDef.source, sha256: hostDef.sha256 };
    } else {
      const h = hostDef.kind === 'chair' ? nativeChair(seed) : nativeRobe(seed);
      sd = fieldFromSDF(h.sdf); label = h.label; fixed = h.fixed.slice(); seal = h.seal;
      provenance = { host: 'native', source: null, sha256: null };
    }
    const F = sampler(sd), TH = sampler(thickness(sd));
    const fr = rngFor(seed, 'fields');
    const nSize = makeNoise(fr), nFray = makeNoise(fr), nFold = makeNoise(fr), nDiss = makeNoise(fr), nSway = makeNoise(fr), nStrut = makeNoise(fr), nSweep = makeNoise(fr);
    const mat = (x, y) => F.at(x, y) + 10 * (nFray(x / 80, y / 80, 3) - 0.5) * 2;
    const downness = (x, y) => { const g = F.grad(x, y), gl = Math.hypot(g[0], g[1]) || 1; return Math.max(0, -g[1] / gl); };
    const band = P.cell * 2.4;
    // the open net is a thin margin along the sides and a deep one at hems and undersides
    const bandAt = (x, y) => P.cell * (0.6 + 2.8 * Math.pow(downness(x, y), 1.4));
    const deepT = (m, bd) => smooth(bd * 0.55, bd * 1.4, m);
    const orient = (x, y) => {
      const g = F.grad(x, y), gl = Math.hypot(g[0], g[1]);
      let tx = 0, ty = 0;
      if (gl > 1e-6) { const a = Math.atan2(g[1], g[0]) + Math.PI / 2; tx = Math.cos(2 * a); ty = Math.sin(2 * a); }
      const wt = (1 - P.drape) * clamp(gl, 0, 1), wv = P.drape;
      return 0.5 * Math.atan2(wt * ty, wt * tx - wv) + (nSway(x / 260, y / 260) - 0.5) * 0.8;
    };
    const siteShape = (x, y, m) => {
      const n = nSize(x / 200, y / 200, 2), dt = deepT(m, bandAt(x, y));
      const rNet = P.cell * (0.82 + 0.36 * n) * (1 + 0.45 * smooth(0, -SAMPLE_FRAY * 0.65, m));
      const rRib = P.cell * P.rib * (0.58 + 0.84 * n) * (0.6 + 0.4 * smooth(0, P.cell * 4, m));
      const rho = lerp(rNet, rRib, dt), asp = lerp(m > 0 ? 1.12 : 1.04, P.elong, dt);
      let a = rho * asp, b = rho / asp;
      const cap = Math.max(rNet * 0.9, TH.at(x, y) * 0.5);
      if (b > cap) { const s = cap / b; a = Math.max(rNet, a * s); b = cap; }
      return [a, b];
    };

    // seal for traced hosts: the deepest point of the upper body
    if (P.seal && !seal) {
      let best = null;
      for (let y = 100; y < 900; y += 8) for (let x = 60; x < 940; x += 8) {
        const d = F.at(x, y) - Math.abs(x - 500) * 0.05 + (900 - y) * 0.03;
        if (!best || d > best.d) best = { x, y, d };
      }
      if (best && F.at(best.x, best.y) > 40) { const r = Math.min(32, F.at(best.x, best.y) * 0.42); seal = { x: best.x, y: best.y, a: r, b: r, ang: 0, style: 'seal' }; }
    }
    if (P.seal && seal) fixed.push(seal);

    TM.pre = Math.round(now() - tq); tq = now();
    // ------------------------------------------------ anisotropic packing
    const sr = rngFor(seed, 'sites');
    const sites = [];
    const BG = 24, bw = Math.ceil(PW / BG) + 2, bh = Math.ceil(PH / BG) + 2, buckets = new Array(bw * bh);
    let maxExt = 0;
    const radAlong = (s, ux, uy) => { const p = ux * s.cos + uy * s.sin, q = -ux * s.sin + uy * s.cos; return 1 / Math.sqrt((p / s.a) ** 2 + (q / s.b) ** 2); };
    const mk = (x, y, a, b, ang, extra) => {
      const c = Math.cos(ang), s = Math.sin(ang), ia = 1 / (a * a), ib = 1 / (b * b);
      return Object.assign({ x, y, a, b, ang, cos: c, sin: s, ext: Math.max(a, b), w: Math.sqrt(a * b), m11: c * c * ia + s * s * ib, m12: c * s * (ia - ib), m22: s * s * ia + c * c * ib }, extra || {});
    };
    for (const f of fixed) sites.push(mk(f.x, f.y, f.a + 7.4, f.b + 7.4, f.ang, { fixed: f, m: mat(f.x, f.y) }));
    const nFixed = sites.length;
    const K = 0.97;
    const inDomain = (x, y, m) => x > 14 && x < PW - 14 && y > 14 && y < PH - 14 && m > -SAMPLE_FRAY * (0.7 + 0.8 * downness(x, y)) - 6;
    const fits = (c) => {
      for (let i = 0; i < nFixed; i++) {
        const f = sites[i], dx = c.x - f.x, dy = c.y - f.y, d = Math.hypot(dx, dy);
        if (d < 1e-6 || d < K * (radAlong(f, dx / d, dy / d) + radAlong(c, dx / d, dy / d))) return false;
      }
      const R = c.ext + maxExt, i0 = Math.floor((c.x - R) / BG + 1), i1 = Math.floor((c.x + R) / BG + 1), j0 = Math.floor((c.y - R) / BG + 1), j1 = Math.floor((c.y + R) / BG + 1);
      for (let j = Math.max(0, j0); j <= Math.min(bh - 1, j1); j++) for (let i = Math.max(0, i0); i <= Math.min(bw - 1, i1); i++) {
        const b = buckets[j * bw + i]; if (!b) continue;
        for (const k of b) {
          const s = sites[k], dx = c.x - s.x, dy = c.y - s.y;
          if (Math.abs(dx) > c.ext + s.ext || Math.abs(dy) > c.ext + s.ext) continue;
          // distance in the averaged metric of the two ellipses: 2 means just touching
          const d2 = 0.5 * ((c.m11 + s.m11) * dx * dx + 2 * (c.m12 + s.m12) * dx * dy + (c.m22 + s.m22) * dy * dy);
          if (d2 < 4 * K * K) return false;
        }
      }
      return true;
    };
    const siteAt = (x, y) => { const m = mat(x, y), [a, b] = siteShape(x, y, m); return mk(x, y, a, b, orient(x, y), { m }); };
    const active = [];
    const add = (c) => {
      sites.push(c); maxExt = Math.max(maxExt, c.ext);
      const k = Math.floor(c.y / BG + 1) * bw + Math.floor(c.x / BG + 1); (buckets[k] || (buckets[k] = [])).push(sites.length - 1);
      active.push(sites.length - 1);
    };
    const grow = () => {
      while (active.length) {
        const ai = Math.floor(sr() * active.length), s = sites[active[ai]];
        let ok = false;
        for (let t = 0; t < 24; t++) {
          const th = sr() * TAU, ux = Math.cos(th), uy = Math.sin(th);
          const dd = 2 * radAlong(s, ux, uy) * (1 + 0.22 * sr());
          const c = siteAt(s.x + ux * dd, s.y + uy * dd);
          if (!inDomain(c.x, c.y, c.m) || !fits(c)) continue;
          add(c); ok = true; break;
        }
        if (!ok) { active[ai] = active[active.length - 1]; active.pop(); }
      }
    };
    for (let tries = 0; tries < 400; tries++) {
      const c = siteAt(30 + sr() * 940, 30 + sr() * 1440);
      if (c.m > band * 2 && fits(c)) { add(c); break; }
    }
    grow();
    for (let y = 18; y < PH - 14; y += 12) for (let x = 18; x < PW - 14; x += 12) {
      const c = siteAt(x + (sr() - 0.5) * 6, y + (sr() - 0.5) * 6);
      if (inDomain(c.x, c.y, c.m) && fits(c)) { add(c); grow(); }
    }

    TM.packing = Math.round(now() - tq); tq = now();
    // ------------------------------------------------ power diagram
    const N = sites.length, cells = new Array(N);
    for (let i = 0; i < N; i++) {
      const s = sites[i], B = 4 * s.ext + 12;
      let poly = { x: [s.x - B, s.x + B, s.x + B, s.x - B], y: [s.y - B, s.y - B, s.y + B, s.y + B], t: [-1, -1, -1, -1] };
      const R = B * 1.45 + maxExt, cand = [];
      const i0 = Math.floor((s.x - R) / BG + 1), i1 = Math.floor((s.x + R) / BG + 1), j0 = Math.floor((s.y - R) / BG + 1), j1 = Math.floor((s.y + R) / BG + 1);
      for (let j = Math.max(0, j0); j <= Math.min(bh - 1, j1); j++) for (let ii = Math.max(0, i0); ii <= Math.min(bw - 1, i1); ii++) {
        const b = buckets[j * bw + ii]; if (!b) continue;
        for (const k of b) if (k !== i) cand.push(k);
      }
      for (let k = 0; k < nFixed; k++) if (k !== i) cand.push(k);
      const uniq = [...new Set(cand)], dd = uniq.map((k) => (sites[k].x - s.x) ** 2 + (sites[k].y - s.y) ** 2);
      const order = uniq.map((k, q) => q).sort((a, b) => dd[a] - dd[b]);
      for (const q of order) {
        // anisotropic power bisector: the pair's averaged metric, each site weighted by its
        // own radius toward the other, so long cells stay long instead of being cut short
        const k = uniq[q], o = sites[k], dx = o.x - s.x, dy = o.y - s.y, d = Math.hypot(dx, dy) || 1e-9, ux = dx / d, uy = dy / d;
        const m11 = (s.m11 + o.m11) / 2, m12 = (s.m12 + o.m12) / 2, m22 = (s.m22 + o.m22) / 2;
        const nx = m11 * dx + m12 * dy, ny = m12 * dx + m22 * dy;
        const mu = Math.sqrt(m11 * ux * ux + 2 * m12 * ux * uy + m22 * uy * uy);
        const rs = radAlong(s, ux, uy) * mu, ro = radAlong(o, ux, uy) * mu;
        const qf = (x, y) => m11 * x * x + 2 * m12 * x * y + m22 * y * y;
        const b = (qf(o.x, o.y) - qf(s.x, s.y) - ro * ro + rs * rs) / 2;
        let allIn = true;
        for (let v = 0; v < poly.x.length; v++) if (nx * poly.x[v] + ny * poly.y[v] > b) { allIn = false; break; }
        if (allIn) continue;
        poly = clipPoly(poly, nx, ny, b, k);
        if (poly.x.length < 3) break;
      }
      cells[i] = poly;
    }

    // canonical vertices shared between cells
    const vmap = new Map(), verts = [];
    const vid = (x, y) => {
      const qx = Math.round(x * 2), qy = Math.round(y * 2);
      let best = -1, bd = 0.9;
      for (let dx = -2; dx <= 2; dx++) for (let dy = -2; dy <= 2; dy++) {
        const l = vmap.get((qx + dx) + ',' + (qy + dy)); if (!l) continue;
        for (const v of l) { const d = Math.hypot(verts[v].x - x, verts[v].y - y); if (d < bd) { bd = d; best = v; } }
      }
      if (best >= 0) return best;
      verts.push({ x, y, cells: [] });
      const key = qx + ',' + qy, l = vmap.get(key); if (l) l.push(verts.length - 1); else vmap.set(key, [verts.length - 1]);
      return verts.length - 1;
    };
    const cv = new Array(N);
    for (let i = 0; i < N; i++) {
      const p = cells[i];
      if (p.x.length < 3 || p.t.indexOf(-1) >= 0) continue;
      const ids = [], nx = [], ny = [], nt = [];
      for (let k = 0; k < p.x.length; k++) {
        const v = vid(p.x[k], p.y[k]);
        if (ids.length && ids[ids.length - 1] === v) { nt[nt.length - 1] = p.t[k]; continue; } // collapsed edge
        ids.push(v); nx.push(verts[v].x); ny.push(verts[v].y); nt.push(p.t[k]); verts[v].cells.push(i);
      }
      if (ids.length > 1 && ids[0] === ids[ids.length - 1]) { ids.pop(); nx.pop(); ny.pop(); nt.pop(); }
      cells[i] = { x: nx, y: ny, t: nt };   // snapped to the shared vertices, so neighbours meet exactly
      cv[i] = ids;
    }
    TM.power = Math.round(now() - tq);
    return { sd, F, TH, label, provenance, nSize, nFray, nFold, nDiss, nSway, nStrut, nSweep, mat, downness, band, bandAt, deepT, sites, nFixed, cells, cv, verts, TM, ms: Math.round(now() - t0) };
  }

  function generate(seed, hostDef, params, cache) {
    const P = Object.assign({}, DEFAULTS, params);
    const t0 = now(); let tq = t0;
    const key = JSON.stringify([String(seed), hostDef.key || hostDef.kind, P.cell, P.rib, P.elong, P.drape, P.seal]);
    let L = cache && cache.key === key ? cache.layout : null;
    const reused = !!L;
    if (!L) { L = layout(seed, hostDef, P); if (cache) { cache.key = key; cache.layout = L; } }
    const TM = Object.assign({}, L.TM, { reused }); tq = now();
    const { sd, F, label, provenance, nFold, nDiss, nStrut, nSweep, mat, downness, band, bandAt, deepT, sites, nFixed, cv, verts } = L;
    const cells = L.cells, N = sites.length;
    const feff = (x, y) => P.fray * (0.7 + 0.8 * downness(x, y));
    const dissThr = (x, y) => P.dissolve * 190 * (0.2 + 1.0 * nDiss(x / 150, y / 150, 2));
    // ------------------------------------------------ classes
    const cls = new Array(N);
    for (let i = 0; i < N; i++) {
      const s = sites[i], p = cells[i];
      if (s.fixed) { cls[i] = 'fix'; continue; }
      const m = s.m, thr = dissThr(s.x, s.y);
      let c = m > thr ? (deepT(m - thr, bandAt(s.x, s.y)) > 0.45 && s.ext > P.cell * 1.3 ? 'rib' : 'net') : m > 0 ? 'web' : m > -feff(s.x, s.y) ? 'fray' : 'none';
      if (!cv[i]) c = 'none';
      cls[i] = c;
    }
    const isMem = (k) => k >= 0 && (cls[k] === 'rib' || cls[k] === 'net' || cls[k] === 'fix');

    TM.classes = Math.round(now() - tq); tq = now();
    // ------------------------------------------------ ribs and panes in the deep cells
    const strutAt = (x, y, m) => P.strut * (0.75 + 0.5 * nStrut(x / 160, y / 160)) * lerp(0.7, 1.1, smooth(0, band * 2, m));
    const ribCtrl = new Map();
    const ribs = [];
    const curveFor = (va, vb) => { // shared by both cells of an edge, keyed by the vertex pair
      const key = va < vb ? va + ':' + vb : vb + ':' + va;
      let c = ribCtrl.get(key);
      if (c === undefined) {
        const A = verts[Math.min(va, vb)], B = verts[Math.max(va, vb)], L = Math.hypot(B.x - A.x, B.y - A.y);
        if (L < 8) c = null;
        else {
          // bulge from a smooth field, so neighbouring ribs sweep the same way
          const mxr = (A.x + B.x) / 2, myr = (A.y + B.y) / 2, h2 = hash01(seed + '|rib2|' + key);
          const b = L * P.sweep * (0.5 + 0.5 * h2) * (2 * nSweep(mxr / 140, myr / 300) - 1) * 2.2;
          c = [(A.x + B.x) / 2 - (B.y - A.y) / L * b, (A.y + B.y) / 2 + (B.x - A.x) / L * b];
          const pts = [[A.x, A.y], ...quadPts([A.x, A.y], c, [B.x, B.y], Math.max(4, Math.ceil(L / 6))), [B.x, B.y]];
          ribs.push(pts);
        }
        ribCtrl.set(key, c);
      }
      return c;
    };
    const pr = rngFor(seed, 'panes');
    const panes = [], paneOf = new Array(N).fill(null);
    for (let i = 0; i < N; i++) {
      if (cls[i] !== 'rib') continue;
      const p = cells[i], ids = cv[i], pts = [];
      for (let k = 0; k < ids.length; k++) {
        const a = ids[k], b = ids[(k + 1) % ids.length], A = verts[a], B = verts[b], nb = p.t[k];
        pts.push([A.x, A.y]);
        if (nb >= 0 && cls[nb] === 'rib') {
          const c = curveFor(a, b);
          if (c) for (const q of quadPts([A.x, A.y], c, [B.x, B.y], Math.max(4, Math.ceil(Math.hypot(B.x - A.x, B.y - A.y) / 6)))) pts.push(q);
        }
      }
      const [cx, cy] = centroid(pts), m = mat(cx, cy), g = strutAt(cx, cy, m) * 1.25;
      const pane = inset(pts, g);
      if (!pane || Math.abs(area(pane)) < 60 || area(pane) * area(pts) < 0) continue;
      // keep panes inside the silhouette: pull stray vertices back across the edge
      const lim = dissThr(sites[i].x, sites[i].y) + 2;
      for (const q of pane) {
        let mq = mat(q[0], q[1]);
        for (let it = 0; it < 4 && mq < lim; it++) { const gg = F.grad(q[0], q[1]), g2 = gg[0] * gg[0] + gg[1] * gg[1] || 1; q[0] += gg[0] / g2 * (lim - mq); q[1] += gg[1] / g2 * (lim - mq); mq = mat(q[0], q[1]); }
      }
      let per = 0; for (let k = 0; k < pane.length; k++) { const a2 = pane[k], b2 = pane[(k + 1) % pane.length]; per += Math.hypot(b2[0] - a2[0], b2[1] - a2[1]); }
      if (2 * Math.abs(area(pane)) / per < 4.2) continue; // a sliver: leave the cell solid
      const s = sites[i];
      const fold = nFold(cx / 90, cy / 460, 2), r = pr();
      let type;
      if (fold < 0.32) type = r < 0.5 ? 'dark' : r < 0.82 ? 'slate' : 'pod';
      else if (fold < 0.64) type = r < 0.66 ? 'pod' : r < 0.86 ? 'slate' : 'lace';
      else type = r < 0.42 ? 'lace' : r < 0.74 ? 'pod' : 'open';
      if ((type === 'lace' || type === 'open') && pr() < P.slate * 0.5) type = 'slate';
      if (type === 'slate' && pr() > P.slate * 1.4) type = 'pod';
      const ar = Math.abs(area(pane));
      if (ar < 500 && type !== 'pod') type = pr() < 0.6 ? 'pod' : 'open';
      const P1 = { pts: pane, type, x: cx, y: cy, ang: s.ang, cell: i, g, circles: [], veins: [], lace: [], dots: [] };
      paneOf[i] = P1; panes.push(P1);
    }
    TM.panes = Math.round(now() - tq); tq = now();
    // pane contents
    const cr = rngFor(seed, 'contents');
    for (const pn of panes) {
      const u = [Math.cos(pn.ang), Math.sin(pn.ang)], v = [-u[1], u[0]];
      let t0 = Infinity, t1 = -Infinity;
      for (const q of pn.pts) { const t = (q[0] - pn.x) * u[0] + (q[1] - pn.y) * u[1]; t0 = Math.min(t0, t); t1 = Math.max(t1, t); }
      const mid = (t) => { const ox = pn.x + u[0] * t, oy = pn.y + u[1] * t, ch = chordOf(pn.pts, ox, oy, v[0], v[1]); if (ch.length < 2) return null; const s0 = ch[0], s1 = ch[ch.length - 1]; return [ox + v[0] * (s0 + s1) / 2, oy + v[1] * (s0 + s1) / 2, (s1 - s0) / 2]; };
      pn.axis = [];
      for (let k = 0; k <= 12; k++) { const q = mid(lerp(t0, t1, 0.04 + 0.92 * k / 12)); if (q) pn.axis.push([q[0], q[1]]); }
      if (pn.type === 'pod') {
        const gap = 1.6 + P.strut * 0.9, gap2 = 2.2 + P.strut;
        const clearAt = (t) => { const q = mid(t); if (!q) return null; return [q[0], q[1], edgeDist(q[0], q[1], pn.pts) * (inPoly(q[0], q[1], pn.pts) ? 1 : -1) - gap]; };
        let best = null;
        for (let k = 0; k <= 30; k++) { const t = lerp(t0, t1, k / 30), c = clearAt(t); if (c && (!best || c[2] > best.c[2])) best = { t, c }; }
        if (best && best.c[2] > 2) {
          const circ = [{ x: best.c[0], y: best.c[1], r: best.c[2] * (0.94 + 0.06 * cr()), t: best.t }];
          for (const dir of [1, -1]) {
            let prev = circ[0], t = prev.t;
            for (let n = 0; n < 12; n++) {
              let placed = null;
              for (let step = 0; step < 200; step++) {
                t += dir * 0.6;
                if (t < t0 || t > t1) break;
                const c = clearAt(t); if (!c || c[2] < 1.6) continue;
                const d = Math.hypot(c[0] - prev.x, c[1] - prev.y);
                if (d >= prev.r + c[2] + gap2) { placed = { x: c[0], y: c[1], r: c[2] * (0.88 + 0.12 * cr()), t }; break; }
                if (d - prev.r - gap2 > 1.6 && c[2] > d - prev.r - gap2) {
                  const rr2 = d - prev.r - gap2; // the largest circle that fits here
                  if (rr2 >= 1.6) { const nxt = clearAt(t + dir * 0.6); if (!nxt || nxt[2] < rr2 + 0.3) { placed = { x: c[0], y: c[1], r: rr2, t }; break; } }
                }
              }
              if (!placed) break;
              circ.push(placed); prev = placed;
            }
          }
          const depth = smooth(band, band * 4, mat(pn.x, pn.y));
          for (const c of circ) {
            const q = cr(), big = c.r > 9;
            c.style = q < 0.1 + 0.15 * (1 - depth) ? 'cream' : q < 0.32 ? 'dark' : 'slate';
            if (!big && cr() < 0.35) c.style = 'dark';
            pn.circles.push(c);
          }
          // small cells flanking the chain
          const sorted = pn.circles.slice().sort((a, b) => a.t - b.t);
          for (let k = 0; k + 1 < sorted.length; k++) {
            const a = sorted[k], b = sorted[k + 1], mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
            for (const sgn of [-1, 1]) {
              let x = mx + v[0] * sgn * (a.r + b.r) * 0.45, y = my + v[1] * sgn * (a.r + b.r) * 0.45;
              const cl = Math.min(edgeDist(x, y, pn.pts) - gap * 0.8, Math.hypot(x - a.x, y - a.y) - a.r - gap, Math.hypot(x - b.x, y - b.y) - b.r - gap);
              if (inPoly(x, y, pn.pts) && cl > 1.5 && cr() < 0.7) pn.dots.push({ x, y, r: Math.min(cl * 0.75, 4.5), style: cl > 3 && cr() < 0.5 ? 'cream' : 'dark' });
            }
          }
        }
      } else if (pn.type === 'slate' || pn.type === 'dark') {
        // veins: a spine along the long axis, ribs off it toward the edges
        if (pn.axis.length > 2) {
          pn.veins.push(pn.axis.map((q) => [q[0], q[1]]));
          const n = Math.floor((t1 - t0) / 14);
          for (let k = 1; k < n; k++) {
            const t = lerp(t0, t1, k / n) + (cr() - 0.5) * 4, q = mid(t); if (!q) continue;
            for (const sgn of [-1, 1]) {
              const ang = Math.atan2(v[1], v[0]) * 1 + 0, dirx = v[0] * sgn + u[0] * 0.75, diry = v[1] * sgn + u[1] * 0.75, dl = Math.hypot(dirx, diry);
              const ch = chordOf(pn.pts, q[0], q[1], dirx / dl, diry / dl).filter((s) => s > 0);
              if (!ch.length) continue;
              const L = ch[0] * 0.92, bend = (cr() - 0.5) * 0.25;
              const pts = [];
              for (let j = 0; j <= 6; j++) { const f = j / 6, w = L * f; pts.push([q[0] + dirx / dl * w - diry / dl * w * bend * f, q[1] + diry / dl * w + dirx / dl * w * bend * f]); }
              pn.veins.push(pts);
            }
          }
        }
      } else if (pn.type === 'lace') {
        // a fine hairline net: a small Voronoi clipped to the pane
        const pts = [], d0 = 6.5 + P.cell * 0.25;
        let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
        for (const q of pn.pts) { bx0 = Math.min(bx0, q[0]); by0 = Math.min(by0, q[1]); bx1 = Math.max(bx1, q[0]); by1 = Math.max(by1, q[1]); }
        for (let tries = 0; tries < 400 && pts.length < 70; tries++) {
          const x = lerp(bx0, bx1, cr()), y = lerp(by0, by1, cr());
          if (!inPoly(x, y, pn.pts)) continue;
          let ok = true; for (const q of pts) if (Math.hypot(q[0] - x, q[1] - y) < d0) { ok = false; break; }
          if (ok) pts.push([x, y]);
        }
        const segs = new Map();
        for (let a = 0; a < pts.length; a++) {
          let poly = { x: [bx0 - 2, bx1 + 2, bx1 + 2, bx0 - 2], y: [by0 - 2, by0 - 2, by1 + 2, by1 + 2], t: [-1, -1, -1, -1] };
          for (let b = 0; b < pts.length; b++) {
            if (b === a) continue;
            const nx = pts[b][0] - pts[a][0], ny = pts[b][1] - pts[a][1];
            if (nx * nx + ny * ny > (d0 * 4) ** 2) continue;
            poly = clipPoly(poly, nx, ny, (pts[b][0] ** 2 + pts[b][1] ** 2 - pts[a][0] ** 2 - pts[a][1] ** 2) / 2, b);
          }
          for (let k = 0; k < poly.x.length; k++) {
            const b = poly.t[k]; if (b < 0 || b < a) continue;
            const k2 = (k + 1) % poly.x.length;
            segs.set(a + ':' + b, [[poly.x[k], poly.y[k]], [poly.x[k2], poly.y[k2]]]);
          }
        }
        for (const sg of segs.values()) { // keep the parts inside the pane
          const [p0, p1] = sg, dx = p1[0] - p0[0], dy = p1[1] - p0[1], L = Math.hypot(dx, dy);
          if (L < 0.5) continue;
          const cuts = [0, 1, ...chordOf(pn.pts, p0[0], p0[1], dx / L, dy / L).map((s) => s / L).filter((s) => s > 0 && s < 1)].sort((a, b) => a - b);
          for (let k = 0; k + 1 < cuts.length; k++) {
            const fm = (cuts[k] + cuts[k + 1]) / 2;
            if (inPoly(p0[0] + dx * fm, p0[1] + dy * fm, pn.pts)) pn.lace.push([[p0[0] + dx * cuts[k], p0[1] + dy * cuts[k]], [p0[0] + dx * cuts[k + 1], p0[1] + dy * cuts[k + 1]]]);
          }
        }
      }
    }
    TM.contents = Math.round(now() - tq); tq = now();
    // rose windows: the largest pod circles take tracery
    const allCirc = [];
    for (const pn of panes) for (const c of pn.circles) allCirc.push(c);
    allCirc.sort((a, b) => b.r - a.r);
    for (let k = 0; k < Math.min(P.roses, allCirc.length); k++) if (allCirc[k].r > 11) { allCirc[k].style = 'rose'; allCirc[k].spokes = 8 + 2 * Math.floor(cr() * 5); }

    // ------------------------------------------------ open net in the edge band
    const hr = rngFor(seed, 'holes');
    const holes = [], holeOf = new Array(N).fill(null);
    for (let i = 0; i < N; i++) {
      if (cls[i] === 'fix') {
        const f = sites[i].fixed, h = { x: f.x, y: f.y, a: f.a, b: f.b, ang: f.ang, style: f.style, fixed: true };
        holes.push(h); holeOf[i] = h; continue;
      }
      if (cls[i] !== 'net') continue;
      const s = sites[i], p = cells[i];
      const pts = []; for (let k = 0; k < p.x.length; k++) pts.push([p.x[k], p.y[k]]);
      const [cx, cy] = centroid(pts);
      const m = mat(cx, cy), g = strutAt(cx, cy, m) * 0.8;
      const ah = Math.pow(s.a / s.b, 0.5), ang = s.ang + (hr() - 0.5) * 0.25;
      let sc = Infinity;
      for (let k = 0; k < p.x.length; k++) {
        const k2 = (k + 1) % p.x.length, x1 = p.x[k], y1 = p.y[k], ex = p.x[k2] - x1, ey = p.y[k2] - y1, L = Math.hypot(ex, ey);
        if (L < 1e-6) continue;
        let nx = ey / L, ny = -ex / L;
        if (nx * (cx - x1) + ny * (cy - y1) > 0) { nx = -nx; ny = -ny; }
        const nb = p.t[k], gk = nb >= 0 && cls[nb] === 'rib' ? g * 1.6 : nb >= 0 && isMem(nb) ? g : g * 1.1;
        sc = Math.min(sc, (nx * x1 + ny * y1 - gk - (nx * cx + ny * cy)) / supportLen(nx, ny, ang, ah));
      }
      for (let k = 0; k < nFixed; k++) {
        const f = sites[k].fixed, dxf = cx - f.x, dyf = cy - f.y;
        if (Math.hypot(dxf, dyf) > f.a + f.b + s.ext * 4) continue;
        const c = Math.cos(f.ang), si = Math.sin(f.ang);
        let u1 = (dxf * c + dyf * si) / f.a, u2 = (-dxf * si + dyf * c) / f.b; const um = Math.hypot(u1, u2) || 1; u1 /= um; u2 /= um;
        const qx = f.x + (f.a * u1) * c - (f.b * u2) * si, qy = f.y + (f.a * u1) * si + (f.b * u2) * c;
        let nx = (u1 / f.a) * c - (u2 / f.b) * si, ny = (u1 / f.a) * si + (u2 / f.b) * c; const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
        sc = Math.min(sc, (nx * cx + ny * cy - (nx * qx + ny * qy) - g * 2 - 2) / supportLen(nx, ny, ang, ah));
      }
      sc *= 0.92 + 0.08 * hr();
      const a = sc * ah, b = sc / ah;
      if (!(Math.min(a, b) > 1.8)) continue;
      const r = hr();
      const style = r < 0.05 ? 'dark' : r < 0.05 + 0.32 * P.slate * smooth(0, band, m) ? 'slate' : 'cream';
      const h = { x: cx, y: cy, a, b, ang, style, g };
      holes.push(h); holeOf[i] = h;
    }

    TM.net = Math.round(now() - tq); tq = now();
    // ------------------------------------------------ material: the ochre under everything
    const material = [];
    for (let i = 0; i < N; i++) {
      if (!isMem(i)) continue;
      const p = cells[i], h = holeOf[i], pn = paneOf[i];
      let boundary = false;
      for (let k = 0; k < p.t.length; k++) if (!isMem(p.t[k])) { boundary = true; break; }
      const pts = [];
      if (cls[i] === 'fix') {
        for (let k = 0; k < p.x.length; k++) if (isMem(p.t[k]) || isMem(p.t[(k + p.x.length - 1) % p.x.length])) pts.push([p.x[k], p.y[k]]);
        const rim = h.style === 'seal' ? Math.max(4, h.a * 0.14) + P.strut * 1.4 : P.strut * 2.4 + 3;
        for (const q of ellipsePts(h, rim)) pts.push(q);
        if (!boundary) for (let k = 0; k < p.x.length; k++) pts.push([p.x[k], p.y[k]]);
        material.push(hull(pts));
        continue;
      }
      if (!boundary || (!h && !pn)) { for (let k = 0; k < p.x.length; k++) pts.push([p.x[k], p.y[k]]); material.push(pts); continue; }
      // boundary cell: only a rim around its hole or pane. Neighbouring rims overlap along
      // shared sides and part at the outer corners, which leaves a notch between cells
      const ring = h ? ellipsePts(h, h.g * 2 + 1.2) : inset(pn.pts, -(pn.g * 1.7 + 1));
      if (ring && ring.length >= 3) material.push(ring);
    }

    TM.material = Math.round(now() - tq); tq = now();
    // ------------------------------------------------ froth and beads at the junctions
    const xr = rngFor(seed, 'froth');
    const froth = [], beads = [];
    for (let v = 0; v < verts.length; v++) {
      const V = verts[v];
      if (V.cells.length < 3) continue;
      let allMem = true, nRib = 0;
      for (const c of V.cells) { if (!isMem(c)) { allMem = false; break; } if (cls[c] === 'rib') nRib++; }
      if (!allMem) continue;
      const obs = [];
      for (const c of V.cells) { if (holeOf[c]) obs.push(['e', holeOf[c]]); else if (paneOf[c]) obs.push(['p', paneOf[c].pts]); }
      if (obs.length < 2) continue;
      const clear = (x, y) => { let d = Infinity; for (const [k, o] of obs) d = Math.min(d, k === 'e' ? ellipseDist(x, y, o) - (o.fixed ? P.strut * 2 : 0) : polyDist(x, y, o)); return d; };
      let x = V.x, y = V.y, f = clear(x, y);
      for (let it = 0; it < 6; it++) {
        const gx = clear(x + 0.5, y) - clear(x - 0.5, y), gy = clear(x, y + 0.5) - clear(x, y - 0.5), gl = Math.hypot(gx, gy);
        if (gl < 1e-6) break;
        const nx2 = x + gx / gl * f * 0.35, ny2 = y + gy / gl * f * 0.35, f2 = clear(nx2, ny2);
        if (f2 <= f) break;
        x = nx2; y = ny2; f = f2;
      }
      const gF = 1.6 + P.strut * 0.45;
      if (f - gF > 2.4 && xr() < (nRib ? 0.55 : 0.75)) {
        const r = (f - gF) * (0.55 + 0.25 * xr());
        froth.push({ x, y, a: r, b: r * (0.82 + 0.18 * xr()), ang: xr() * TAU, style: xr() < 0.22 ? 'dark' : 'cream' });
      } else if (f > 1.8 && xr() < (nRib ? 0.75 : 0.5)) {
        beads.push({ x, y, r: clamp(f * 0.45, 0.9, 2.3) });
      }
    }
    for (const rb of ribs) { // nodes along the longer ribs
      let L = 0; for (let k = 1; k < rb.length; k++) L += Math.hypot(rb[k][0] - rb[k - 1][0], rb[k][1] - rb[k - 1][1]);
      if (L > 45 && xr() < 0.4) { const q = rb[Math.floor(rb.length * (0.3 + 0.4 * xr()))]; beads.push({ x: q[0], y: q[1], r: 1.1 + xr() * 0.7 }); }
    }

    TM.froth = Math.round(now() - tq); tq = now();
    // ------------------------------------------------ the node web: dissolved interior and fray
    const wr = rngFor(seed, 'web');
    const nodes = new Map();
    const node = (v) => { let n = nodes.get(v); if (!n) { const V = verts[v]; n = { v, x: V.x, y: V.y, out: -mat(V.x, V.y), anchor: false, edges: [] }; nodes.set(v, n); } return n; };
    const edges = [], ekey = new Map();
    for (let i = 0; i < N; i++) {
      if (cls[i] !== 'web' && cls[i] !== 'fray') continue;
      const p = cells[i], ids = cv[i]; if (!ids) continue;
      for (let k = 0; k < ids.length; k++) {
        const j = p.t[k]; if (j < 0) continue;
        const a = ids[k], b = ids[(k + 1) % ids.length]; if (a === b) continue;
        if (isMem(j)) { node(a).anchor = true; node(b).anchor = true; continue; }
        if (cls[j] !== 'web' && cls[j] !== 'fray') continue;
        const key = a < b ? a + ':' + b : b + ':' + a;
        if (ekey.has(key)) continue;
        const e = { a, b, kind: cls[i] === 'web' || cls[j] === 'web' ? 'web' : 'fray', keep: false };
        ekey.set(key, edges.length); edges.push(e);
        node(a).edges.push(edges.length - 1); node(b).edges.push(edges.length - 1);
      }
    }
    for (const e of edges) if (e.kind === 'web' && wr() < 0.92) e.keep = true;
    const anchors = [...nodes.values()].filter((n) => n.anchor);
    for (let i = anchors.length - 1; i > 0; i--) { const j = Math.floor(wr() * (i + 1)); const t = anchors[i]; anchors[i] = anchors[j]; anchors[j] = t; }
    const tendrils = [], stack = [];
    for (const a of anchors) {
      if (wr() > 0.4) continue;
      const g = F.grad(a.x, a.y), below = smooth(-0.6, 0.6, -g[1]);
      stack.push([a, Math.max(12, P.fray * (0.2 + 0.85 * Math.pow(wr(), 0.6)) * (0.7 + 0.6 * below)), 0, null]);
    }
    let guard = 0;
    while (stack.length && guard++ < 50000) {
      let [u, maxOut, depth, dir] = stack.pop();
      const path = [u.v];
      for (let steps = 0; steps < 40; steps++) {
        const cands = [];
        for (const ei of u.edges) {
          const e = edges[ei]; if (e.keep || e.kind !== 'fray') continue;
          const w2 = nodes.get(e.a === u.v ? e.b : e.a);
          if (w2.out < u.out - 3 || w2.out > maxOut + 8) continue;
          const len = Math.hypot(w2.x - u.x, w2.y - u.y) || 1, dx = (w2.x - u.x) / len, dy = (w2.y - u.y) / len;
          const mom = dir ? Math.max(0, dir[0] * dx + dir[1] * dy) : 0.5;
          cands.push([(Math.max(0.5, w2.out - u.out) + 4) * (1 + 1.3 * Math.max(0, dy)) * (0.3 + 1.6 * mom * mom) * (0.4 + wr()), ei, w2, [dx, dy]]);
        }
        if (!cands.length) break;
        let tot = 0; for (const c of cands) tot += c[0];
        let r = wr() * tot, pick = cands[0];
        for (const c of cands) { r -= c[0]; if (r <= 0) { pick = c; break; } }
        edges[pick[1]].keep = true;
        if (depth < 4 && cands.length > 1 && wr() < 0.2) stack.push([u, maxOut * (0.5 + 0.4 * wr()), depth + 1, dir]);
        u = pick[2]; dir = pick[3]; path.push(u.v);
        if (u.out >= maxOut) break;
      }
      if (path.length >= 2) tendrils.push(path);
    }
    // netting close to the body
    const degree = new Map(), bump = (v) => degree.set(v, (degree.get(v) || 0) + 1);
    for (const e of edges) if (e.keep) { bump(e.a); bump(e.b); }
    for (const e of edges) {
      if (e.keep || e.kind !== 'fray' || !degree.get(e.a) || !degree.get(e.b)) continue;
      const near = Math.min(nodes.get(e.a).out, nodes.get(e.b).out);
      if (near < P.fray * 0.28 && wr() < 0.3 * (1 - near / (P.fray * 0.28 + 1))) { e.keep = true; e.net = true; bump(e.a); bump(e.b); }
    }
    // tendrils are relaxed into smooth hanging curves; a branch starts where its parent passed
    const placed = new Map(), onTendril = new Set();
    const tpaths = [];
    for (const path of tendrils) {
      const pts = path.map((v, i) => (i === 0 && placed.has(v) ? placed.get(v).slice() : [nodes.get(v).x, nodes.get(v).y]));
      for (let it = 0; it < 3; it++) for (let i = 1; i < pts.length - 1; i++) {
        pts[i] = [0.5 * pts[i][0] + 0.25 * (pts[i - 1][0] + pts[i + 1][0]), 0.5 * pts[i][1] + 0.25 * (pts[i - 1][1] + pts[i + 1][1]) + 0.8];
      }
      if (pts.length > 2) pts[pts.length - 1][1] += 2;
      path.forEach((v, i) => { if (!placed.has(v)) placed.set(v, pts[i]); onTendril.add(v); });
      tpaths.push({ pts, v: path, a0: nodes.get(path[0]).anchor && !(placed.get(path[0]) !== pts[0]) });
    }
    const pos = (v) => placed.get(v) || [nodes.get(v).x, nodes.get(v).y];
    const links = [];
    for (const e of edges) {
      if (!e.keep || (e.kind === 'fray' && !e.net)) continue;
      const na = nodes.get(e.a), nb = nodes.get(e.b), pa = pos(e.a), pb = pos(e.b), len = Math.hypot(pb[0] - pa[0], pb[1] - pa[1]);
      const sag = 0.11 * len * Math.pow(1 - Math.abs(pb[1] - pa[1]) / (len || 1), 1.4) * (0.6 + 0.8 * wr());
      const mxl = (pa[0] + pb[0]) / 2, myl = (pa[1] + pb[1]) / 2;
      const bend = e.kind === 'web' ? len * P.sweep * (2 * nSweep(mxl / 140, myl / 300) - 1) * 1.6 : 0;
      links.push({ x1: pa[0], y1: pa[1], x2: pb[0], y2: pb[1], a1: na.anchor && !placed.has(e.a), a2: nb.anchor && !placed.has(e.b), kind: e.kind,
        cx: mxl - (pb[1] - pa[1]) / (len || 1) * bend, cy: myl + (pb[0] - pa[0]) / (len || 1) * bend + sag * 2 });
    }
    const webBeads = [], terminals = [];
    for (const [v, d] of degree) {
      const n = nodes.get(v), q = pos(v);
      if (n.anchor && n.out < 6) continue;
      if (d === 1 && n.out > 2) terminals.push({ x: q[0], y: q[1], r: 2.3 + 2.0 * Math.pow(wr(), 0.8) + clamp(n.out / P.fray, 0, 1) * 0.9 });
      else if (wr() < (onTendril.has(v) ? 0.5 : 0.8)) webBeads.push({ x: q[0], y: q[1], r: n.out < 0 ? 1.5 + wr() * 0.5 : 1.2 + wr() * 0.8 });
    }

    TM.web = Math.round(now() - tq); tq = now();
    // ------------------------------------------------ the membrane raster: outline, anchors, drips
    const cov = coverage(material);
    const filled = (x, y) => { x = Math.round(x * RS); y = Math.round(y * RS); if (x < 0 || y < 0 || x >= RW || y >= RH) return false; return cov[y * RW + x] > COV_T; };
    const snap = (x, y, ox, oy) => {
      if (filled(x, y)) return [x, y];
      const dx = x - ox, dy = y - oy, dl = Math.hypot(dx, dy) || 1;
      for (let s = 1; s < 30; s++) { const px = x + dx / dl * s, py = y + dy / dl * s; if (filled(px, py)) return [px + dx / dl * 1.5, py + dy / dl * 1.5]; }
      for (let r = 2; r < 20; r += 2) for (let a = 0; a < 16; a++) { const px = x + Math.cos(a / 16 * TAU) * r, py = y + Math.sin(a / 16 * TAU) * r; if (filled(px, py)) return [px, py]; }
      return [x, y];
    };
    for (const L of links) {
      if (L.a1) [L.x1, L.y1] = snap(L.x1, L.y1, L.x2, L.y2);
      if (L.a2) [L.x2, L.y2] = snap(L.x2, L.y2, L.x1, L.y1);
    }
    for (const t of tpaths) if (t.a0 && t.pts.length > 1) t.pts[0] = snap(t.pts[0][0], t.pts[0][1], t.pts[1][0], t.pts[1][1]);
    const outline = marching(cov, RW, RH).map((l) => l.map((q) => [q[0] / RS, q[1] / RS]));

    TM.raster = Math.round(now() - tq); tq = now();
    const dr = rngFor(seed, 'drips');
    const drips = [], pearls = [], used = new Set();
    const dripLen = 50 + 190 * P.drips;
    const tryDrip = (x, y, p) => {
      const key = Math.round(x / 8) + ',' + Math.round(y / 10);
      if (used.has(key) || dr() > p) return;
      let L = 14 + Math.pow(dr(), 1.5) * dripLen, yy = y + 3;
      while (yy < y + L) { if (filled(x, yy + 3) || yy > PH - 28) { L = yy - y - 3; break; } yy += 2; }
      if (L < 12) return;
      used.add(key);
      const d = { x, y1: y, y2: y + L, beads: [], r: clamp(2.2 + L / 45 + dr() * 1.4, 2.2, 5.4) };
      const nb = L < 40 ? (dr() < 0.6 ? 0 : 1) : dr() < 0.25 ? 0 : dr() < 0.55 ? 1 : dr() < 0.85 ? 2 : 3;
      for (let k = 0; k < nb; k++) d.beads.push({ t: (k + 0.5 + (dr() - 0.5) * 0.6) / (nb + 0.6), r: 1.2 + dr() * 0.9 });
      if (L > 70 && dr() < 0.14) pearls.push({ x, y: y + L * (0.45 + 0.35 * dr()), r: 5 + dr() * 4.5 });
      drips.push(d);
    };
    if (P.drips > 0) {
      for (const poly of outline) for (let k = 0; k < poly.length; k++) {
        const [x, y] = poly[k];
        if (filled(x, y - 2.5) && !filled(x, y + 2.5) && !filled(x, y + 8)) tryDrip(x, y - 1.5, 0.025 + 0.17 * P.drips);
      }
      for (const t of terminals) if (dr() < 0.12 + 0.45 * P.drips) tryDrip(t.x, t.y + t.r * 0.6, 1);
      for (const b of webBeads) if (dr() < 0.05 * P.drips) tryDrip(b.x, b.y + b.r, 1);
    }

    // ------------------------------------------------ ground ring
    TM.drips = Math.round(now() - tq); tq = now();
    let ground = null;
    if (P.ground) {
      // under the host's own silhouette, so it stays put however far the lattice dissolves
      let ymax = -1;
      for (let gy = GH - 1; gy >= 0 && ymax < 0; gy--) for (let gx = 0; gx < GW; gx++) if (sd[gy * GW + gx] > 0) { ymax = (gy + 0.5) * GC; break; }
      const xs = [];
      for (let gy = 0; gy < GH; gy++) { const y = (gy + 0.5) * GC; if (y < ymax - 140 || y > ymax) continue; for (let gx = 0; gx < GW; gx++) if (sd[gy * GW + gx] > 0) xs.push((gx + 0.5) * GC); }
      if (xs.length) {
        xs.sort((a, b) => a - b);
        const lo = xs[Math.floor(xs.length * 0.03)], hi = xs[Math.floor(xs.length * 0.97)];
        const gr = rngFor(seed, 'ground'), rx = clamp((hi - lo) * 0.6 + 50, 140, 440), gap = Math.PI / 2 + (gr() - 0.5) * 1.6;
        ground = { x: (lo + hi) / 2, y: Math.min(PH - 40, ymax - 10), rx, ry: rx * (0.11 + 0.04 * gr()), gap0: gap - 0.08 - gr() * 0.05, gap1: gap + 0.06 + gr() * 0.05 };
      }
    }

    return {
      seed: String(seed), params: P, label, provenance, version: VERSION,
      panes, ribs, holes, froth, beads, material, outline, links, tendrils: tpaths, webBeads, terminals, drips, pearls, ground,
      stats: { tm: TM, sites: N, membrane: cls.filter((c) => c === 'rib' || c === 'net' || c === 'fix').length, panes: panes.length, holes: holes.length, links: links.length + tpaths.length, drips: drips.length, ms: Math.round(now() - t0) },
    };
  }

  // The membrane as a coverage grid: a half-unit cell holds 0-16, how many of its 4 x 4
  // samples fall inside the union of the material polygons (nonzero winding, polygon by
  // polygon). The outline and every inside-the-membrane test read this grid.
  const RS = 0.5, RW = PW * RS, RH = PH * RS, SUB = 4, COV_T = 6.9;
  function coverage(polys) {
    const k = RS * SUB, SW = RW * SUB, SH = RH * SUB;
    const bits = new Uint8Array(SW * SH), xs = [], ds = [];
    for (const poly of polys) {
      const n = poly.length; if (n < 3) continue;
      let y0 = Infinity, y1 = -Infinity;
      for (const q of poly) { const y = q[1] * k; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      const r0 = Math.max(0, Math.ceil(y0 - 0.5)), r1 = Math.min(SH - 1, Math.floor(y1 - 0.5));
      for (let r = r0; r <= r1; r++) {
        const yc = r + 0.5; xs.length = 0; ds.length = 0;
        for (let i = 0, j = n - 1; i < n; j = i++) {
          const ay = poly[j][1] * k, by = poly[i][1] * k;
          if ((ay <= yc) === (by <= yc)) continue;
          const ax = poly[j][0] * k, bx = poly[i][0] * k;
          xs.push(ax + (yc - ay) * (bx - ax) / (by - ay)); ds.push(by > ay ? 1 : -1);
        }
        for (let a = 1; a < xs.length; a++) { // a few crossings: insertion sort
          const x = xs[a], d = ds[a]; let b = a - 1;
          while (b >= 0 && xs[b] > x) { xs[b + 1] = xs[b]; ds[b + 1] = ds[b]; b--; }
          xs[b + 1] = x; ds[b + 1] = d;
        }
        let w = 0;
        for (let a = 0; a + 1 < xs.length; a++) {
          w += ds[a];
          if (w === 0) continue;
          const c0 = Math.max(0, Math.ceil(xs[a] - 0.5)), c1 = Math.min(SW - 1, Math.floor(xs[a + 1] - 0.5));
          if (c1 >= c0) bits.fill(1, r * SW + c0, r * SW + c1 + 1);
        }
      }
    }
    const cov = new Uint8Array(RW * RH);
    for (let y = 0; y < SH; y++) {
      const row = y * SW, out = (y >> 2) * RW;
      for (let x = 0; x < SW; x++) if (bits[row + x]) cov[out + (x >> 2)]++;
    }
    return cov;
  }

  // marching squares on the coverage grid; returns polylines in grid cells
  function marching(cov, w, h) {
    const T = COV_T, v = (x, y) => (x < 0 || y < 0 || x >= w || y >= h ? 0 : cov[y * w + x]);
    const segs = [];
    const lerpPt = (x0, y0, v0, x1, y1, v1) => { const t = (T - v0) / ((v1 - v0) || 1e-9); return [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t]; };
    for (let y = -1; y < h; y++) for (let x = -1; x < w; x++) {
      const a = v(x, y), b = v(x + 1, y), c = v(x + 1, y + 1), d = v(x, y + 1);
      const idx = (a > T ? 8 : 0) | (b > T ? 4 : 0) | (c > T ? 2 : 0) | (d > T ? 1 : 0);
      if (idx === 0 || idx === 15) continue;
      const top = () => lerpPt(x, y, a, x + 1, y, b), right = () => lerpPt(x + 1, y, b, x + 1, y + 1, c);
      const bot = () => lerpPt(x, y + 1, d, x + 1, y + 1, c), left = () => lerpPt(x, y, a, x, y + 1, d);
      switch (idx) {
        case 1: case 14: segs.push([left(), bot()]); break;
        case 2: case 13: segs.push([bot(), right()]); break;
        case 3: case 12: segs.push([left(), right()]); break;
        case 4: case 11: segs.push([top(), right()]); break;
        case 5: segs.push([left(), top()]); segs.push([bot(), right()]); break;
        case 6: case 9: segs.push([top(), bot()]); break;
        case 7: case 8: segs.push([left(), top()]); break;
        case 10: segs.push([top(), right()]); segs.push([left(), bot()]); break;
      }
    }
    const key = (p) => Math.round(p[0] * 64) + ',' + Math.round(p[1] * 64);
    const ends = new Map();
    segs.forEach((s, i) => { for (const e of [0, 1]) { const k = key(s[e]); const l = ends.get(k); if (l) l.push(i); else ends.set(k, [i]); } });
    const used = new Uint8Array(segs.length), lines = [];
    for (let i = 0; i < segs.length; i++) {
      if (used[i]) continue;
      used[i] = 1;
      const line = [segs[i][0], segs[i][1]];
      for (const dir of [1, 0]) {
        for (;;) {
          const tip = dir ? line[line.length - 1] : line[0], l = ends.get(key(tip));
          let nxt = -1; if (l) for (const j of l) if (!used[j]) { nxt = j; break; }
          if (nxt < 0) break;
          used[nxt] = 1;
          const s = segs[nxt], o = key(s[0]) === key(tip) ? s[1] : s[0];
          if (dir) line.push(o); else line.unshift(o);
        }
      }
      if (line.length > 3) lines.push(simplify(line, 0.2));
    }
    return lines;
  }
  function simplify(pts, tol) {
    if (pts.length < 3) return pts;
    const n = pts.length;
    if (Math.hypot(pts[0][0] - pts[n - 1][0], pts[0][1] - pts[n - 1][1]) < 1e-6) { // a closed loop: split at its far point
      let m = 1, md = -1;
      for (let i = 1; i < n - 1; i++) { const d = Math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]); if (d > md) { md = d; m = i; } }
      const a = simplify(pts.slice(0, m + 1), tol), b = simplify(pts.slice(m), tol);
      return a.concat(b.slice(1));
    }
    const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1;
    const st = [[0, pts.length - 1]];
    while (st.length) {
      const [a, b] = st.pop(); let md = 0, mi = -1;
      const ax = pts[a][0], ay = pts[a][1], dx = pts[b][0] - ax, dy = pts[b][1] - ay, L = Math.hypot(dx, dy) || 1e-9;
      for (let i = a + 1; i < b; i++) { const d = Math.abs((pts[i][0] - ax) * dy - (pts[i][1] - ay) * dx) / L; if (d > md) { md = d; mi = i; } }
      if (md > tol) { keep[mi] = 1; st.push([a, mi], [mi, b]); }
    }
    return pts.filter((p, i) => keep[i]);
  }

  function debugHost(seed, kind) { const h = kind === 'chair' ? nativeChair(seed) : nativeRobe(seed); return { sd: fieldFromSDF(h.sdf), fixed: h.fixed, seal: h.seal, label: h.label }; }
  return { VERSION, generate, debugHost, DEFAULTS, COL, PW, PH, TAU, decodeRLE, rngFor, makeNoise, ellipsePts, inset, clamp, lerp };
})();
if (typeof module !== 'undefined') module.exports = NodeLattice;
