#!/usr/bin/env node
// Rebuild the sample plot masters in out/plot/ and their record, out/manifest.json.
//
//   node common/lattice/samples.mjs           write them
//   node common/lattice/samples.mjs --check   exit 1 if a committed sample differs from a fresh build
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { plate, NodeLattice } from './plate.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
export const MANIFEST = resolve(HERE, 'out/manifest.json');
export const SAMPLES = [
  { name: 'robe-handoff', host: 'robe', seed: 'handoff', params: {}, pens: 'series' },
  { name: 'robe-handoff-dissolve-50', host: 'robe', seed: 'handoff', params: { dissolve: 0.5 }, pens: 'series' },
  { name: 'choronzon-handoff', host: 'choronzon', seed: 'handoff', params: {}, pens: 'series' },
];
export const fileOf = (s) => 'out/plot/' + s.name + '.svg';

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const check = process.argv.includes('--check');
  let bad = 0;
  const records = [];
  for (const s of SAMPLES) {
    const { svg, record } = plate(s), file = fileOf(s), path = resolve(HERE, file);
    if (check) {
      let old = '';
      try { old = readFileSync(path, 'utf8'); } catch { /* missing */ }
      const ok = old === svg;
      if (!ok) bad++;
      console.log((ok ? 'same     ' : 'DIFFERS  ') + file + '  ' + record.sha256.slice(0, 16));
    } else {
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, svg);
      console.log('wrote ' + file + '  ' + record.paths + ' paths  ' + record.sha256.slice(0, 16));
    }
    records.push(Object.assign({ name: s.name, file }, record));
  }
  if (check) process.exit(bad ? 1 : 0);
  writeFileSync(MANIFEST, JSON.stringify({
    generator: NodeLattice.VERSION, node: process.version,
    note: 'Built by samples.mjs. tests/lattice.test.mjs regenerates every sample and checks it against its file and sha256 here.',
    samples: records,
  }, null, 1) + '\n');
  console.log('wrote out/manifest.json');
}
