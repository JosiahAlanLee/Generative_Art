#!/usr/bin/env node
// Write one node-lattice plot master (SVG) and print its record as JSON.
//
//   node common/lattice/plate.mjs --host robe --seed handoff --out robe.svg
//   node common/lattice/plate.mjs --host choronzon --set dissolve=0.4 --pens study --out c.svg
//   node common/lattice/plate.mjs --list
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
export const NodeLattice = require('./lattice.js');
export const LatticeRender = require('./render.js');
export const HOSTS = JSON.parse(readFileSync(resolve(HERE, 'hosts.json'), 'utf8')).hosts;
export const NATIVE = { robe: 'Empty robe', chair: 'Empty chair' };

// what generate() takes, and what masterMeta() records
export function host(key) {
  if (NATIVE[key]) return { def: { kind: key, key }, info: { kind: 'native', key, label: NATIVE[key], source: null, sha256: null } };
  const h = HOSTS.find((x) => x.key === key);
  if (!h) throw new Error('unknown host "' + key + '"; try --list');
  return { def: Object.assign({ kind: 'traced' }, h), info: { kind: 'traced', key, label: h.label, source: h.source, sha256: h.sha256 } };
}

export function plate({ host: key = 'robe', seed = 'handoff', params = {}, pens = 'series' } = {}) {
  if (pens !== 'series' && pens !== 'study') throw new Error('--pens is series or study');
  for (const k of Object.keys(params)) if (!(k in NodeLattice.DEFAULTS)) throw new Error('unknown parameter "' + k + '"');
  const h = host(key);
  const sc = NodeLattice.generate(String(seed), h.def, params);
  const svg = LatticeRender.toSVG(LatticeRender.plotStrokes(sc), LatticeRender.masterMeta(sc, h.info, pens), pens);
  const { tm, ms, ...stats } = sc.stats;   // timings are not part of the record
  return {
    svg,
    record: {
      generator: NodeLattice.VERSION, host: h.info, seed: String(seed), pens, params: sc.params, stats,
      paths: (svg.match(/<path /g) || []).length, bytes: Buffer.byteLength(svg),
      sha256: createHash('sha256').update(svg).digest('hex'),
    },
  };
}

function parseArgs(argv) {
  const o = { params: {} };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i], v = () => { if (i + 1 >= argv.length) throw new Error(a + ' needs a value'); return argv[++i]; };
    if (a === '--host') o.host = v();
    else if (a === '--seed') o.seed = v();
    else if (a === '--pens') o.pens = v();
    else if (a === '--out') o.out = v();
    else if (a === '--record') o.record = v();
    else if (a === '--list') o.list = true;
    else if (a === '--set') {
      const [k, raw] = v().split('=');
      o.params[k] = raw === 'true' ? true : raw === 'false' ? false : Number(raw);
      if (typeof o.params[k] === 'number' && !Number.isFinite(o.params[k])) throw new Error('--set ' + k + ' needs a number, true or false');
    } else if (a === '--help' || a === '-h') o.help = true;
    else throw new Error('unknown option ' + a);
  }
  return o;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const o = parseArgs(process.argv.slice(2));
    if (o.help || (!o.out && !o.list)) {
      console.log('usage: node plate.mjs [--host KEY] [--seed TEXT] [--set NAME=VALUE ...] [--pens series|study] --out FILE.svg [--record FILE.json]\n       node plate.mjs --list\nparameters and defaults: ' +
        Object.entries(NodeLattice.DEFAULTS).map(([k, v]) => k + '=' + v).join(' '));
      process.exit(o.help ? 0 : 2);
    }
    if (o.list) {
      for (const [k, v] of Object.entries(NATIVE)) console.log(k.padEnd(11) + v + ' (native)');
      for (const h of HOSTS) console.log(h.key.padEnd(11) + h.label + ', ' + h.office + ' (traced from ' + h.source + ')');
      process.exit(0);
    }
    const { svg, record } = plate(o);
    mkdirSync(dirname(resolve(o.out)), { recursive: true });
    writeFileSync(o.out, svg);
    if (o.record) writeFileSync(o.record, JSON.stringify(record, null, 1) + '\n');
    console.log(JSON.stringify(record, null, 1));
  } catch (err) {
    console.error('plate.mjs: ' + err.message);
    process.exit(2);
  }
}
