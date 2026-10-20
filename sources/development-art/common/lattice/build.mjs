#!/usr/bin/env node
// Assemble node-lattice.html, the single-file page, from template.html, hosts.json,
// lattice.js and render.js. The page needs no server: open it from a checkout.
//
//   node common/lattice/build.mjs                  write node-lattice.html
//   node common/lattice/build.mjs --check          exit 1 if node-lattice.html is out of date
//   node common/lattice/build.mjs --fragment FILE  also write the body alone, for a host that
//                                                  supplies its own <head> (a claude.ai artifact)
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (f) => readFileSync(resolve(HERE, f), 'utf8');
export const PAGE = resolve(HERE, 'node-lattice.html');

export function fragment() {
  const parts = { hosts: 'const HOSTS = ' + JSON.stringify(JSON.parse(read('hosts.json')).hosts) + ';', lattice: read('lattice.js'), render: read('render.js') };
  for (const [k, v] of Object.entries(parts)) if (/<\/script/i.test(v)) throw new Error(k + ' contains </script>');
  return read('template.html')
    .replace('/*__HOSTS__*/', () => parts.hosts)
    .replace('/*__LATTICE__*/', () => parts.lattice)
    .replace('/*__RENDER__*/', () => parts.render);
}

export function page() {
  return '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n' +
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n' +
    '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n' +
    '</head>\n<body>\n' + fragment() + '</body>\n</html>\n';
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2), html = page();
  if (args.includes('--check')) {
    let old = '';
    try { old = readFileSync(PAGE, 'utf8'); } catch { /* missing counts as out of date */ }
    if (old !== html) { console.error('node-lattice.html is out of date: run node common/lattice/build.mjs'); process.exit(1); }
    console.log('node-lattice.html is current');
  } else {
    writeFileSync(PAGE, html);
    console.log('wrote node-lattice.html (' + Buffer.byteLength(html) + ' bytes)');
  }
  const f = args.indexOf('--fragment');
  if (f >= 0) { writeFileSync(args[f + 1], fragment()); console.log('wrote ' + args[f + 1]); }
}
