#!/usr/bin/env node
// Batch-render Driftless Plates to SVG.
// node cli.js --count 12                                   (Codex 7 x 10 in, Codex inks, into out/)
// node cli.js --seeds c2,a8 --zone codex --zone-mode tint   (lighten the Codex text block)
// node cli.js --count 6 --format codexPlot                  (A4 plot masters inside the plate validator's extent)
'use strict';
const fs = require('fs');
const path = require('path');
const E = require('./engine.js');

// Codex sizes come from the engine's CODEX record, read from the book source (see engine.js)
const CX = E.CODEX;
const FORMATS = {
  codex: CX.trimMM, codexSpread: [CX.trimMM[0] * 2, CX.trimMM[1]], codexPlot: CX.plotMasterMM.sheet,
  '6x9': [152.4, 228.6], '5.5x8.5': [139.7, 215.9], '7x10': [177.8, 254], '8.5x11': [215.9, 279.4],
  a5: [148, 210], a4: [210, 297], a3: [297, 420], '8x8': [203.2, 203.2], spread6x9: [304.8, 228.6],
};
const SPREADS = new Set(['codexSpread', 'spread6x9']);
const num = (v, d) => (v === undefined || v === true ? d : Number(v));

// One plate from a plain spec (the same names as the command-line options). Returns the engine result and SVG.
function renderPlate(spec) {
  const fmt = String(spec.format || 'codex');
  if (!FORMATS[fmt]) throw new Error('Unknown format ' + fmt);
  let [w, h] = FORMATS[fmt];
  const plot = fmt === 'codexPlot';
  if (spec.landscape && !plot && !SPREADS.has(fmt) && w < h) [w, h] = [h, w];
  const bleed = spec.bleed && !plot ? 3.175 : 0;
  const palette = String(spec.palette || 'codex');
  if (!E.PALETTES[palette]) throw new Error('Unknown palette ' + palette);
  const P = {
    seed: String(spec.seed), W: w + 2 * bleed, H: h + 2 * bleed, bleed, spread: SPREADS.has(fmt),
    inset: plot ? CX.plotMasterMM.inset : null,
    density: num(spec.density, 100) / 100, imperfection: num(spec.imperfection, 50) / 100,
    weights: { flora: num(spec.flora, 60) / 100, land: num(spec.land, 60) / 100, built: num(spec.built, 50) / 100, sky: num(spec.sky, 50) / 100 },
    focal: spec.focal || 'auto', rock: spec.rock || 'auto', season: spec.season || 'auto', time: spec.time || 'auto', frame: spec.frame || 'auto',
    textZone: spec.zone || 'none', zoneMode: spec.zoneMode || spec['zone-mode'] || 'fade',
  };
  if (spec.compat) P.compat = String(spec.compat);
  // Nib width in mm, as on the page. It sets hatch spacing and the occlusion halos as well as the
  // stroke width, so a plate drawn for another nib has different lines. Absent = the engine's 0.35.
  const nib = spec.penWidth !== undefined ? spec.penWidth : spec['pen-width'];
  if (nib !== undefined) {
    const pw = Number(nib);
    if (nib === true || !(pw >= 0.1 && pw <= 2)) throw new Error('--penWidth expects a nib width in mm, 0.1 to 2');
    P.penWidth = pw;
  }
  const res = E.generate(P);
  const svg = E.toSVG(res, {
    palette, strength: num(spec.strength, 100) / 100, background: !!spec.paper, optimize: !spec['no-optimize'],
    misregister: spec.riso && !plot ? E.misregistration(P.seed, P.imperfection) : null,
  });
  const name = `driftless-plate-${P.seed}-${fmt}${bleed ? '-bleed' : ''}.svg`;
  return { res, svg, name, format: fmt };
}

module.exports = { renderPlate, FORMATS };

function main() {
  const args = process.argv.slice(2);
  const opt = {};
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (!a.startsWith('--')) continue;
    const k = a.slice(2), next = args[i + 1];
    if (next === undefined || next.startsWith('--')) opt[k] = true; else { opt[k] = next; i++; }
  }
  if (opt.help) {
    console.log(`Options:
  --seeds a,b,c        explicit seeds (default: --count random seeds)
  --count N            number of random seeds (default 6)
  --format NAME        ${Object.keys(FORMATS).join(' | ')} (default codex)
  --landscape          rotate the trim
  --bleed              add 3.175 mm bleed on every edge (not for codexPlot)
  --palette NAME       ${Object.keys(E.PALETTES).join(' | ')} (default codex)
  --strength 0-100     mix inks toward the paper colour (default 100)
  --zone codex|top|middle|bottom   text area (codex = the book's text block); --zone-mode fade|tint
  --focal --season --time --frame   overrides (same names as the web page)
  --rock auto|sandstone|limestone|quartzite
  --compat 1.1         draw a plate as engine 1.1 did
  --flora --land --built --sky 0-100   motif weights
  --density 50-160 --imperfection 0-100
  --penWidth MM        nib width in mm (default 0.35; the page offers 0.2-0.8). It changes
                       hatch spacing and occlusion as well as the stroke, so the lines differ
  --paper              include a paper rectangle layer
  --no-optimize        keep drawing order instead of minimising pen travel
  --riso               offset colour layers like a risograph pass (not for codexPlot)
  --out DIR            output folder (default out/ beside this script)`);
    return;
  }
  const seeds = opt.seeds ? String(opt.seeds).split(',').map((s) => s.trim()).filter(Boolean)
    : Array.from({ length: num(opt.count, 6) }, () => Math.floor(Math.random() * 2 ** 32).toString(16).padStart(8, '0'));
  const outDir = path.resolve(opt.out ? String(opt.out) : path.join(__dirname, 'out'));
  fs.mkdirSync(outDir, { recursive: true });
  const manifest = [];
  for (const seed of seeds) {
    const { res, svg, name } = renderPlate(Object.assign({}, opt, { seed }));
    fs.writeFileSync(path.join(outDir, name), svg);
    const st = E.plotStats(res);
    manifest.push({ seed, file: name, traits: res.traits, strokes: res.count, meters: +st.downMeters.toFixed(1), plotHours: +st.hours.toFixed(2) });
    console.log(`${seed}  ${res.traits.Subject}, ${res.traits.Season}, ${res.traits.Light}  ${res.count} strokes  ${(svg.length / 1e6).toFixed(2)} MB`);
  }
  fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2));
}

if (require.main === module) {
  try { main(); } catch (e) { console.error(e.message || e); process.exit(1); }
}
