#!/usr/bin/env node
// Checks for Driftless Plates. Run from anywhere: node studies/driftless-plates/test.js
//  1. The Codex page geometry in engine.js matches the lines it was read from in the pinned book snapshot.
//  2. The preview plates regenerate with the SVG hashes recorded in manifest.json.
//  3. Plot masters keep every stroke inside the extent the Codex plate validator checks.
//  4. Text blocks land where the book sets type, one per page on a spread.
//  5. index.html is the current build of src/ and engine.js.
//  6. Plates made under engine 1.1 draw the same geometry with compat '1.1'.
//  7. The nib option: 0.35 mm is the default plate byte for byte; other nibs redraw; bad widths are refused.
'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const E = require('./engine.js');
const { renderPlate } = require('./cli.js');
const { page } = require('./build.js');

const HERE = __dirname;
const BOOK = path.resolve(HERE, '../../sources/codex-intervallorum');
let failures = 0, passes = 0;
function check(name, ok, detail) {
  if (ok) { passes++; console.log('ok   ' + name); } else { failures++; console.log('FAIL ' + name + (detail ? ': ' + detail : '')); }
}
const read = (rel) => fs.readFileSync(path.join(BOOK, rel), 'utf8');
const sha256 = (s) => crypto.createHash('sha256').update(s).digest('hex');
function grab(rel, re) {
  const m = read(rel).match(re);
  return m ? m.slice(1).map(Number) : null;
}
const same = (a, b) => Array.isArray(a) && a.length === b.length && a.every((v, i) => Math.abs(v - b[i]) < 1e-9);

// 1. Codex geometry, from the snapshot of the book's main branch
const C = E.CODEX;
check('snapshot pin matches CODEX.source', fs.readFileSync(path.resolve(HERE, '../../docs/PROVENANCE.md'), 'utf8').includes(C.source.split('@')[1]));
check('page 504 x 720 pt (binding/bind.py)', same(grab('binding/bind.py', /^PW,\s*PH\s*=\s*([\d.]+),\s*([\d.]+)/m), C.pagePt));
check('trim in mm equals the page in points', same(C.pagePt.map((v) => +(v / 72 * 25.4).toFixed(4)), C.trimMM));
for (const rel of ['books/07_septimus/build.py', 'books/00_accusator/build.py', 'books/00_matres/build.py']) {
  const src = read(rel);
  const top = (src.match(/self\.y\s*=\s*(\d+)\s*;\s*c\s*=\s*self\.c/) || [])[1];
  const left = (src.match(/todo\.drawOn\(self\.c,\s*(\d+),/) || [])[1];
  const width = (src.match(/todo\.wrap\((\d+),\s*10000\)/) || [])[1];
  const bottom = (src.match(/if self\.y\s*-\s*h\s*>=\s*(\d+):/) || [])[1];
  const got = [left, +left + +width, bottom, top].map(Number);
  const want = [C.textBlockPt.left, C.textBlockPt.right, C.textBlockPt.bottom, C.textBlockPt.top];
  check(`text block ${want.join('/')} pt (${rel})`, same(got, want), 'found ' + got.join('/'));
}
check('plot sheet 210 x 297 mm (common/plot/plate.py)', same(grab('common/plot/plate.py', /^W,\s*H\s*=\s*(\d+),\s*(\d+)/m), C.plotMasterMM.sheet));
check('plot extent 8-202 x 10-288 mm (common/plot/plate.py)', same(grab('common/plot/plate.py',
  /min\(xs\) >= (\d+) and min\(ys\) >= (\d+) and max\(xs\) <= (\d+) and max\(ys\) <= (\d+)/), C.plotMasterMM.extent));
const plotkit = read('common/plot/plotkit.py').match(/^INK,\s*RED\s*=\s*"(#[0-9a-f]{6})",\s*"(#[0-9a-f]{6})"/m) || [];
check('inks (common/plot/plotkit.py)', plotkit[1] === C.inks.ink && plotkit[2] === C.inks.red);
check('paper (common/plot/plate.py)', (read('common/plot/plate.py').match(/^PAPER\s*=\s*"(#[0-9a-f]{6})"/m) || [])[1] === C.inks.paper);
check('mute (binding/backmatter.py)', /MUTE='(#[0-9a-f]{6})'/.exec(read('binding/backmatter.py'))[1] === C.inks.mute);
const pal = E.PALETTES.codex;
check('codex palette uses the book inks', pal.paper === C.inks.paper && pal.inks.join() === [C.inks.ink, C.inks.ink, C.inks.red, C.inks.mute].join());

// 2. Reproducibility of the preview plates
const manifest = JSON.parse(fs.readFileSync(path.join(HERE, 'manifest.json'), 'utf8'));
check(`manifest engine version ${manifest.engine_version} is the engine's`, manifest.engine_version === E.version);
for (const rec of manifest.plates) {
  const { svg } = renderPlate(rec.spec);
  check(`plate ${rec.spec.seed} (${rec.spec.format}) regenerates byte for byte`, sha256(svg) === rec.svg_sha256,
    'hash differs; after an intended change run node make_preview.js');
}

// 3. Plot masters stay inside the validator's extent, including the subjects added in engine 1.2
const [ex0, ey0, ex1, ey1] = C.plotMasterMM.extent;
const plotSpecs = [{ seed: 'f7' }, { seed: 'e2' }, { seed: 'c2' }, { seed: 'g4', focal: 'bluff' }, { seed: 'k3', focal: 'rocktop' }, { seed: 'm4', focal: 'rock', rock: 'quartzite' }];
for (const ps of plotSpecs) {
  const seed = ps.seed + (ps.focal ? ' (' + ps.focal + ')' : '');
  const { res } = renderPlate(Object.assign({ format: 'codexPlot' }, ps));
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const pen of res.pens) for (const p of pen) for (let i = 0; i < p.length; i += 2) {
    if (p[i] < x0) x0 = p[i]; if (p[i] > x1) x1 = p[i]; if (p[i + 1] < y0) y0 = p[i + 1]; if (p[i + 1] > y1) y1 = p[i + 1];
  }
  check(`plot master ${seed} within ${ex0}-${ex1} x ${ey0}-${ey1} mm`, x0 >= ex0 && y0 >= ey0 && x1 <= ex1 && y1 <= ey1,
    [x0, y0, x1, y1].map((v) => v.toFixed(2)).join(', '));
}

// 4. Text block placement
const mm = (pt) => pt / 72 * 25.4;
const z = E.textZone('codex', C.trimMM[0], C.trimMM[1], 0, false);
const want = [mm(C.textBlockPt.left), mm(C.textBlockPt.right), mm(C.pagePt[1] - C.textBlockPt.top), mm(C.pagePt[1] - C.textBlockPt.bottom)];
check('text block at the Codex trim', z.rects.length === 1 && same([z.rects[0].x0, z.rects[0].x1, z.rects[0].y0, z.rects[0].y1].map((v) => +v.toFixed(6)), want.map((v) => +v.toFixed(6))));
const zs = E.textZone('codex', C.trimMM[0] * 2, C.trimMM[1], 0, true);
check('spread gets one unmirrored block per page', zs.rects.length === 2 && Math.abs(zs.rects[1].x0 - zs.rects[0].x0 - C.trimMM[0]) < 1e-9);
const zb = E.textZone('codex', C.trimMM[0] + 6.35, C.trimMM[1] + 6.35, 3.175, false);
check('bleed shifts the block by the bleed', Math.abs(zb.rects[0].x0 - 3.175 - want[0]) < 1e-9 && Math.abs(zb.rects[0].y0 - 3.175 - want[2]) < 1e-9);

// 5. The committed page is the current build
check('index.html is the current build', page() === fs.readFileSync(path.join(HERE, 'index.html'), 'utf8'), 'run node build.js');

// 6. Engine 1.1 plates, by geometry recorded from engine 1.1 itself
function geometry(res) {
  const h = crypto.createHash('sha256');
  for (const pen of res.pens) {
    h.update('|');
    for (const p of pen) { h.update(String(p.length)); h.update(Buffer.from(p.buffer, p.byteOffset, p.byteLength)); }
  }
  return h.digest('hex');
}
const ref11 = manifest.compat_1_1 || [];
check('manifest records engine 1.1 reference plates', ref11.length >= 6);
for (const rec of ref11) {
  const { res } = renderPlate(Object.assign({}, rec.spec, { compat: '1.1' }));
  check(`1.1 plate ${rec.spec.seed} (${rec.spec.format}) draws the same with compat '1.1'`, geometry(res) === rec.geometry_sha256);
}

// 7. Nib width from the command line (the page's Nib setting)
const nibBase = renderPlate({ seed: 'e2', format: 'a4' });
check('--penWidth 0.35 is the default plate byte for byte', renderPlate({ seed: 'e2', format: 'a4', penWidth: '0.35' }).svg === nibBase.svg);
const nibWide = renderPlate({ seed: 'e2', format: 'a4', penWidth: '0.5' });
check('--penWidth 0.5 redraws the lines and sets the stroke', geometry(nibWide.res) !== geometry(nibBase.res) && nibWide.svg.includes('stroke-width="0.5"'));
check('--penWidth refuses a missing or out-of-range width', [true, '0', 'x', '3'].every((v) => {
  try { renderPlate({ seed: 'e2', format: 'a5', penWidth: v }); return false; } catch (e) { return true; }
}));

console.log(`\n${passes} passed, ${failures} failed`);
process.exit(failures ? 1 : 0);
