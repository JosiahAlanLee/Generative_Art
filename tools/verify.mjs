#!/usr/bin/env node
// Check that every folder and file listed in data/folders.json still hashes
// to its original IPFS CID, as checked out from this repository.
//
//   node tools/verify.mjs
//
// The files are hashed the way `ipfs add` did by default when fxhash stored
// them (CIDv0, 256 KiB chunks, no raw leaves). Nothing is fetched. Entries
// whose re-add never matched (see "readd_matches") are reported but do not
// fail the check; any other difference does.

import fs from 'node:fs'
import path from 'node:path'
import { importer } from 'ipfs-unixfs-importer'

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..')
const folders = JSON.parse(fs.readFileSync(path.join(root, 'data', 'folders.json'), 'utf8'))
const nothing = { async put (cid) { return cid } }

function entries (dir, rel = '') {
  const out = []
  for (const d of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name < b.name ? -1 : 1)) {
    const r = rel ? `${rel}/${d.name}` : d.name
    if (d.isDirectory()) out.push({ path: `root/${r}` }, ...entries(path.join(dir, d.name), r))
    else if (d.isFile()) out.push({ path: `root/${r}`, content: fs.readFileSync(path.join(dir, d.name)) })
    else throw new Error(`${path.join(dir, d.name)}: not a regular file or directory`)
  }
  return out
}

async function cidOf (p, kind) {
  let last
  if (kind === 'directory') {
    for await (const e of importer(entries(p), nothing, { profile: 'unixfs-v0-2015' })) if (e.path === 'root') last = e.cid
  } else {
    for await (const e of importer([{ content: fs.readFileSync(p) }], nothing, { profile: 'unixfs-v0-2015' })) last = e.cid
  }
  return last?.toString()
}

let ok = 0
let failed = 0
let unmatched = 0
for (const [cid, f] of Object.entries(folders)) {
  const p = path.join(root, f.path)
  if (!fs.existsSync(p)) { console.log(`missing   ${f.path}  (${cid})`); failed++; continue }
  const got = await cidOf(p, f.kind)
  if (got === cid) ok++
  else if (f.readd_matches === false) { console.log(`never matched  ${f.path}  (${cid}, re-adds as ${got})`); unmatched++ }
  else { console.log(`CHANGED   ${f.path}  (${cid}, now ${got})`); failed++ }
}
console.log(`${ok} match their original CID, ${unmatched} never did, ${failed} changed or missing`)
process.exit(failed ? 1 : 0)
