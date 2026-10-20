#!/usr/bin/env node
// Rebuild index.html from src/app.html, engine.js and src/app.js.
//   node build.js                  -> index.html, a complete page that opens from disk
//   node build.js --fragment FILE  -> the page body only, for hosts that supply their own <head>
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;

function parts() {
  const tpl = fs.readFileSync(path.join(HERE, 'src/app.html'), 'utf8');
  const engine = fs.readFileSync(path.join(HERE, 'engine.js'), 'utf8');
  const app = fs.readFileSync(path.join(HERE, 'src/app.js'), 'utf8');
  if (/<\/script/i.test(engine + app)) throw new Error('a script source contains a closing script tag');
  return tpl.replace('/*ENGINE*/', () => engine).replace('/*APP*/', () => app);
}

// The template starts with its head material (title, metas, font links, style); the body follows it.
function page() {
  const body = parts();
  const cut = body.indexOf('</style>') + '</style>'.length;
  return '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    + '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    + body.slice(0, cut) + '\n</head>\n<body>\n' + body.slice(cut).replace(/^\s+/, '') + '</body>\n</html>\n';
}

module.exports = { page, parts };

if (require.main === module) {
  const i = process.argv.indexOf('--fragment');
  if (i > 0) {
    const out = path.resolve(process.argv[i + 1]);
    fs.writeFileSync(out, parts());
    console.log('wrote', out);
  } else {
    const out = path.join(HERE, 'index.html');
    fs.writeFileSync(out, page());
    console.log('wrote index.html', (fs.statSync(out).size / 1024).toFixed(0) + ' KB');
  }
}
