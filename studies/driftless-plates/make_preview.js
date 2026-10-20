#!/usr/bin/env node
// Render the six plates in plates.json, record their hashes in manifest.json and draw preview.jpg.
// The preview needs sharp (npm install sharp); without it the manifest is still written.
'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const E = require('./engine.js');
const { renderPlate } = require('./cli.js');
const { page } = require('./build.js');

const HERE = __dirname;
const sha256 = (data) => crypto.createHash('sha256').update(data).digest('hex');

function travel(res) {
  let t = 0;
  for (const paths of res.pens) if (paths.length) t += E.travelLength(E.orderPaths(paths));
  return t;
}

async function main() {
  const specs = JSON.parse(fs.readFileSync(path.join(HERE, 'plates.json'), 'utf8')).plates;
  const built = page();
  if (built !== fs.readFileSync(path.join(HERE, 'index.html'), 'utf8')) {
    throw new Error('index.html is out of date; run node build.js first');
  }
  const plates = [], svgs = [];
  for (const spec of specs) {
    const { res, svg, name, format } = renderPlate(spec);
    const st = E.plotStats(res);
    plates.push({
      spec, file: name, size_mm: [res.W, res.H], traits: res.traits, strokes: res.count,
      pen_down_m: +st.downMeters.toFixed(2), pen_up_travel_m: +(travel(res) / 1000).toFixed(2),
      svg_bytes: Buffer.byteLength(svg), svg_sha256: sha256(svg),
    });
    svgs.push({ svg, res, format });
    console.log(`${spec.seed} ${format}: ${res.traits.Subject}, ${res.traits.Season}, ${res.traits.Light}; ${res.count} strokes`);
  }
  let sharp = null;
  try { sharp = require('sharp'); } catch (e) { sharp = null; }
  const files = {};
  for (const f of ['engine.js', 'cli.js', 'build.js', 'make_preview.js', 'test.js', 'plates.json', 'src/app.html', 'src/app.js', 'index.html']) {
    files[f] = sha256(fs.readFileSync(path.join(HERE, f)));
  }
  if (sharp) {
    const tw = 420, gap = 16, pad = 20, cols = 3;
    const tiles = [];
    for (const { svg, res } of svgs) {
      const density = (tw / res.W) * 25.4;
      const buf = await sharp(Buffer.from(svg), { density, limitInputPixels: false })
        .flatten({ background: E.CODEX.inks.paper }).resize(tw).png().toBuffer();
      tiles.push({ buf, h: Math.round((tw * res.H) / res.W) });
    }
    const rows = Math.ceil(tiles.length / cols);
    const rowH = [];
    for (let r = 0; r < rows; r++) rowH.push(Math.max(...tiles.slice(r * cols, r * cols + cols).map((t) => t.h)));
    const W = pad * 2 + cols * tw + (cols - 1) * gap, H = pad * 2 + rowH.reduce((a, b) => a + b, 0) + (rows - 1) * gap;
    const comps = tiles.map((t, i) => {
      const r = Math.floor(i / cols), c = i % cols;
      return { input: t.buf, left: pad + c * (tw + gap), top: pad + rowH.slice(0, r).reduce((a, b) => a + b, 0) + r * gap };
    });
    await sharp({ create: { width: W, height: H, channels: 3, background: '#cdc7b8' } })
      .composite(comps).jpeg({ quality: 84, mozjpeg: true }).toFile(path.join(HERE, 'preview.jpg'));
    console.log('wrote preview.jpg');
  } else {
    console.log('sharp is not installed; preview.jpg was not redrawn (npm install sharp)');
  }
  if (fs.existsSync(path.join(HERE, 'preview.jpg'))) files['preview.jpg'] = sha256(fs.readFileSync(path.join(HERE, 'preview.jpg')));
  // engine 1.1 reference geometry for the compat check is recorded once and carried forward
  let compat11 = [];
  try { compat11 = JSON.parse(fs.readFileSync(path.join(HERE, 'manifest.json'), 'utf8')).compat_1_1 || []; } catch (e) { compat11 = []; }
  const manifest = {
    study: 'Driftless Plates', engine_version: E.version, codex_source: E.CODEX.source,
    generated_with: `Node ${process.version}`, plates, files, compat_1_1: compat11,
  };
  fs.writeFileSync(path.join(HERE, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  console.log('wrote manifest.json');
}

main().catch((e) => { console.error(e.message || e); process.exit(1); });
