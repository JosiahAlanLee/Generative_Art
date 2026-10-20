// Node lattice tests. Run: node --test common/lattice/tests/lattice.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { plate, HOSTS, NodeLattice, LatticeRender } from '../plate.mjs';
import { SAMPLES, MANIFEST, fileOf } from '../samples.mjs';
import { page, PAGE } from '../build.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const LATTICE = resolve(HERE, '..');
const REPO = resolve(LATTICE, '..', '..');
const sha = (buf) => createHash('sha256').update(buf).digest('hex');
const INK = '#161918', RED = '#a32b24';

// every <path> as { stroke, width, fill, d }, with the <g> layer it sits in
function paths(svg) {
  const out = [];
  let layer = null;
  for (const m of svg.matchAll(/<g ([^>]*)>|<\/g>|<path ([^>]*)\/>/g)) {
    if (m[1] !== undefined) layer = /id="([^"]+)"/.exec(m[1])[1];
    else if (m[0] === '</g>') layer = null;
    else {
      const a = m[2], at = (k) => (new RegExp(' ?' + k + '="([^"]*)"').exec(a) || [])[1];
      out.push({ layer, stroke: at('stroke'), width: at('stroke-width'), fill: at('fill'), d: at('d') });
    }
  }
  return out;
}
const layers = (svg) => [...svg.matchAll(/<g id="([^"]+)" inkscape:groupmode="layer" inkscape:label="([^"]+)"/g)].map((m) => [m[1], m[2]]);

test('each traced host has a valid recorded mask and source hash', () => {
  assert.equal(HOSTS.length, 11);
  for (const h of HOSTS) {
    assert.match(h.sha256, /^[a-f0-9]{64}$/);
    if (process.env.GENART_BOOK_SOURCE) {
      const file = resolve(process.env.GENART_BOOK_SOURCE, h.source);
      assert.ok(existsSync(file), h.key + ': ' + h.source + ' is missing');
      assert.equal(sha(readFileSync(file)), h.sha256, h.key + ': source render changed');
    }
    const mask = NodeLattice.decodeRLE(h.rle);
    let on = 0; for (const v of mask) on += v;
    assert.ok(Math.abs(on / mask.length - h.area) < 1e-6, h.key + ': the mask does not decode to its recorded area');
  }
});

test('a seed gives the same plot master every time', () => {
  for (const host of ['robe', 'chair', 'vassago']) {
    const a = plate({ host, seed: 'repeat' }).svg, b = plate({ host, seed: 'repeat' }).svg;
    assert.equal(sha(a), sha(b), host);
  }
  assert.notEqual(sha(plate({ seed: 'one' }).svg), sha(plate({ seed: 'two' }).svg));
});

test('series plot masters keep the books\' plot-master form', () => {
  for (const s of [{ host: 'robe', seed: 'form' }, { host: 'choraz', seed: 'form', params: { dissolve: 0.6 } }, { host: 'chair', seed: 'form', params: { cell: 9, fray: 170 } }]) {
    const { svg } = plate(s);
    assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" xmlns:inkscape="http:\/\/www\.inkscape\.org\/namespaces\/inkscape" width="210mm" height="297mm" viewBox="0 0 210 297" version="1\.1">/);
    assert.deepEqual(layers(svg), [['art-paths', 'Art Paths'], ['text-outlines', 'Text Outlines']]);
    assert.doesNotMatch(svg, /<(polyline|polygon|circle|ellipse|rect|line|text|image|use)\b/);
    const ps = paths(svg);
    assert.ok(ps.length > 1000, 'too few strokes: ' + ps.length);
    for (const p of ps) {
      assert.equal(p.layer, 'art-paths');
      assert.equal(p.fill, 'none');
      assert.ok(p.stroke === INK || p.stroke === RED, 'ink ' + p.stroke);
      assert.ok(['0.12', '0.17', '0.22'].includes(p.width), 'weight ' + p.width);
      assert.match(p.d, /^M[\d.]+,[\d.]+(L[\d.]+,[\d.]+)+Z?$/);
      for (const [, x, y] of p.d.matchAll(/([\d.]+),([\d.]+)/g)) {
        assert.ok(+x >= 15 - 0.01 && +x <= 195 + 0.01 && +y >= 13.5 - 0.01 && +y <= 283.5 + 0.01, 'outside the figure box: ' + x + ',' + y);
      }
    }
    assert.ok(ps.some((p) => p.stroke === RED), 'no red: the ground ring or seal is missing');
  }
});

test('study plot masters carry four pens, light to dark', () => {
  const { svg } = plate({ host: 'robe', seed: 'form', pens: 'study' });
  assert.deepEqual(layers(svg), [['layer1', '1 Ochre'], ['layer2', '2 Slate'], ['layer3', '3 Ink'], ['layer4', '4 Red']]);
  const want = { layer1: LatticeRender.PEN.ochre, layer2: LatticeRender.PEN.slate, layer3: INK, layer4: RED };
  for (const p of paths(svg)) assert.equal(p.stroke, want[p.layer], p.layer);
});

test('dissolution turns membrane into node web', () => {
  const at = (dissolve) => NodeLattice.generate('dissolve', { kind: 'robe', key: 'robe' }, { dissolve }).stats;
  const [a, b, c] = [at(0), at(0.5), at(1)];
  assert.ok(a.membrane > b.membrane && b.membrane > c.membrane, [a.membrane, b.membrane, c.membrane].join(' > '));
  assert.ok(a.links < c.links, 'the web should grow as the membrane goes');
});

test('the committed samples rebuild exactly', () => {
  const manifest = JSON.parse(readFileSync(MANIFEST, 'utf8'));
  assert.equal(manifest.samples.length, SAMPLES.length);
  for (const s of SAMPLES) {
    const rec = manifest.samples.find((r) => r.name === s.name);
    assert.ok(rec, s.name + ' is not in the manifest');
    const { svg, record } = plate(s), committed = readFileSync(resolve(LATTICE, fileOf(s)), 'utf8');
    assert.equal(record.sha256, rec.sha256, s.name + ': a fresh build differs from the manifest');
    assert.equal(sha(committed), rec.sha256, s.name + ': the committed file differs from the manifest');
    assert.equal(svg, committed);
  }
});

test('the page is built from the current sources', () => {
  assert.equal(readFileSync(PAGE, 'utf8'), page(), 'run node common/lattice/build.mjs');
});
