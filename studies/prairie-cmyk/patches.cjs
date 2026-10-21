// Stroke patches for the depth-ordered meadow. Like driftless_bridge.cjs, this loads the unchanged
// Driftless engine and only extends its in-memory export object. Each patch also records what the
// engine filled into its own occlusion mask (blade and petal fills, stroke halos, branch widths), so
// meadow.py can stamp the same silhouette into one shared screen-space mask.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const text = fs.readFileSync(path.join(__dirname, 'vendor/driftless-engine.js'), 'utf8');
const marker = 'const API = { generate,';
if (!text.includes(marker)) throw new Error('Pinned Driftless API changed');
const sandbox = { module: { exports: {} }, console };
vm.runInNewContext(text.replace(marker, 'const API = { Scene, Rng, oak, pine, tuft, plant, farm, post, generate,'), sandbox);
const E = sandbox.module.exports;

const round = (v) => Math.round(v * 1000) / 1000;
function scene(seed, W = 200, H = 220) {
  const sc = new E.Scene({ seed, W, H, density: 0.9, imperfection: 0.28, penWidth: 0.18, textZone: 'none' });
  sc.comp = { season: 'summer', time: 'day', lightX: -1, crownStyle: 'leafy' };
  const ops = [], m = sc.mask;
  const fillRings = m.fillRings.bind(m), stamp = m.stamp.bind(m), stampVar = m.stampVar.bind(m), disc = m.disc.bind(m);
  m.fillRings = (rings) => { ops.push({ t: 'rings', rings: rings.map((q) => Array.from(q, round)) }); fillRings(rings); };
  m.stamp = (p, w) => { ops.push({ t: 'stamp', pts: Array.from(p, round), w: round(w) }); stamp(p, w); };
  m.stampVar = (p, ws) => { ops.push({ t: 'var', pts: Array.from(p, round), ws: Array.from(ws, round) }); stampVar(p, ws); };
  m.disc = (cx, cy, r) => { ops.push({ t: 'disc', cx: round(cx), cy: round(cy), r: round(r) }); disc(cx, cy, r); };
  sc.ops = ops;
  return sc;
}
function patch(sc, extra) {
  return Object.assign({ strokes: E.post(sc).map((s) => ({ pen: s.p, kind: s.k, pts: Array.from(s.pts, round) })), occluders: sc.ops }, extra || {});
}

const oaks=[];
for(let i=0;i<6;i++){
 const sc=scene('prairie-bur-oak-'+i);
 E.oak(sc,100,202,166,{shadow:false,detail:.8,wd:140+i*7});
 oaks.push(patch(sc,{origin:[100,202],height:166,kind:'oak-'+i}));
}
// a library of meadow plants: tufts with different blade counts, heights and wind, and summer flowers
// each with a tuft beside it. Every patch is rooted at (20, 40) in a 40 x 45 frame.
const plants = [];
const winds = [-0.45, -0.2, 0.05, 0.3, 0.55];
for (let i = 0; i < 60; i++) {
  const sc = scene('meadow-tuft-' + i, 40, 45), r = sc.rng('tuft');
  const wind = winds[i % winds.length] + r.range(-0.08, 0.08);
  const h = r.range(9, 22), k = r.range(2.5, 5.5);
  E.tuft(sc, 20, 40, h, wind, r, r.chance(0.7) ? 1 : 0, k);
  plants.push(patch(sc, { kind: 'tuft', wind: round(wind), h: round(h) }));
}
const flowers = ['cone', 'umbel', 'daisy', 'balm', 'thistle', 'seedball', 'seed', 'fork'];
for (let i = 0; i < 32; i++) {
  const kind = flowers[i % flowers.length];
  const sc = scene('meadow-flower-' + i, 40, 45), r = sc.rng('flower');
  const wind = winds[i % winds.length] + r.range(-0.08, 0.08);
  const h = r.range(14, 26);
  E.tuft(sc, 20 + r.range(-3, 3), 40, h * r.range(0.45, 0.7), wind, r, r.chance(0.7) ? 1 : 0, r.range(2, 3.5));
  E.plant(sc, kind, 20, 40, h, wind, 0.8, r, r.chance(0.7) ? 1 : 0, false);
  plants.push(patch(sc, { kind, wind: round(wind), h: round(h) }));
}

const out={generator:'Driftless Plates '+E.version,oaks,plants,plantOrigin:[20,40]};
fs.writeFileSync(path.join(__dirname,'output/driftless-meadow-patches.json'),JSON.stringify(out));
console.log({oakVariants:oaks.length,plantVariants:plants.length});
