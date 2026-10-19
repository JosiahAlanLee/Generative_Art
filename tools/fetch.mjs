#!/usr/bin/env node
// Fetch an IPFS folder or file block by block from trustless gateways, check
// every block against its CID, and write the content out unchanged.
//
//   node tools/fetch.mjs <cid> <out> [--gateway URL]... [--cache DIR] [--readd]
//
// <out> is a directory for a folder and a file path for a single file. The
// gateways are asked for one raw block at a time (?format=raw), so nothing
// is trusted: a block whose bytes do not hash to its CID is rejected.
//
// --readd imports the written content again with the 2015 UnixFS profile
// (what `ipfs add` did by default: CIDv0, 256 KiB chunks, no raw leaves) and
// reports whether it reproduces the original CID. If it does, the folder in
// this repository is enough to pin the original CID again with `ipfs add -r`.
//
// Prints one line of JSON describing the result.

import fs from 'node:fs'
import path from 'node:path'
import { CID } from 'multiformats/cid'
import { sha256 } from 'multiformats/hashes/sha2'
import { identity } from 'multiformats/hashes/identity'
import { equals } from 'multiformats/bytes'
import * as dagPb from '@ipld/dag-pb'
import { exporter, recursive } from 'ipfs-unixfs-exporter'
import { importer } from 'ipfs-unixfs-importer'

const RAW = 0x55
const DAG_PB = 0x70

const args = process.argv.slice(2)
const flag = (name) => {
  const out = []
  for (let i = 0; i < args.length; i++) {
    if (args[i] === name) { out.push(args[i + 1]); args.splice(i, 2); i-- }
  }
  return out
}
const gateways = flag('--gateway')
const cacheDir = flag('--cache')[0] ?? path.join(path.dirname(new URL(import.meta.url).pathname), '..', '.cache', 'blocks')
const readd = args.includes('--readd') && args.splice(args.indexOf('--readd'), 1)
const [rootArg, out] = args
if (!rootArg || !out) {
  console.error('usage: fetch.mjs <cid> <out> [--gateway URL]... [--cache DIR] [--readd]')
  process.exit(2)
}
if (gateways.length === 0) gateways.push('https://trustless-gateway.link')

const root = CID.parse(rootArg)
fs.mkdirSync(cacheDir, { recursive: true })

let fetched = 0
let cached = 0

async function verify (cid, bytes) {
  const code = cid.multihash.code
  let digest
  if (code === sha256.code) digest = await sha256.digest(bytes)
  else if (code === identity.code) digest = identity.digest(bytes)
  else throw new Error(`${cid}: unsupported hash 0x${code.toString(16)}`)
  if (!equals(digest.bytes, cid.multihash.bytes)) throw new Error(`${cid}: block does not match its CID`)
  return bytes
}

async function fromGateways (cid) {
  const errors = []
  for (const gw of gateways) {
    for (let attempt = 0; attempt < 4; attempt++) {
      try {
        const res = await fetch(`${gw.replace(/\/$/, '')}/ipfs/${cid}?format=raw`, {
          headers: { Accept: 'application/vnd.ipld.raw' },
          redirect: 'follow',
          signal: AbortSignal.timeout(120_000)
        })
        if (res.status === 429 || res.status >= 500) {
          errors.push(`${gw}: ${res.status}`)
          await new Promise(resolve => setTimeout(resolve, 1500 * (attempt + 1)))
          continue
        }
        if (!res.ok) { errors.push(`${gw}: ${res.status}`); break }
        return await verify(cid, new Uint8Array(await res.arrayBuffer()))
      } catch (err) {
        errors.push(`${gw}: ${err.message}`)
        if (err.message.includes('does not match')) break
      }
    }
  }
  throw new Error(`${cid}: not retrieved (${errors.join('; ')})`)
}

const memo = new Map()
async function block (cid) {
  if (cid.multihash.code === identity.code) return verify(cid, cid.multihash.digest)
  const key = cid.toString()
  if (memo.has(key)) return memo.get(key)
  const promise = (async () => {
    const file = path.join(cacheDir, key)
    if (fs.existsSync(file)) {
      cached++
      return verify(cid, new Uint8Array(fs.readFileSync(file)))
    }
    const bytes = await fromGateways(cid)
    fs.writeFileSync(file + '.part', bytes)
    fs.renameSync(file + '.part', file)
    fetched++
    return bytes
  })()
  memo.set(key, promise)
  return promise
}

// Walk the whole DAG first, a few blocks at a time, so every block is
// verified and cached before anything is written out.
async function walk (start, concurrency = 8) {
  const seen = new Set()
  const queue = [start]
  let blocks = 0
  let bytes = 0
  async function worker () {
    while (queue.length) {
      const cid = queue.shift()
      const key = cid.toString()
      if (seen.has(key)) continue
      seen.add(key)
      const data = await block(cid)
      blocks++
      bytes += data.length
      if (cid.code === DAG_PB) {
        for (const link of dagPb.decode(data).Links) queue.push(link.Hash)
      } else if (cid.code !== RAW) {
        throw new Error(`${cid}: unsupported codec 0x${cid.code.toString(16)}`)
      }
    }
  }
  while (queue.length) await Promise.all(Array.from({ length: concurrency }, worker))
  return { blocks, bytes }
}

const store = { async * get (cid) { yield await block(cid) } }

const dag = await walk(root)

// Write the content out.
const files = []
let kind = 'file'
const relative = (p) => p.split('/').slice(1).join('/')
for await (const item of recursive(root, store)) {
  const rel = relative(item.path)
  const entry = await exporter(item.cid, store)
  if (entry.type === 'directory') {
    kind = 'directory'
    fs.mkdirSync(path.join(out, rel), { recursive: true })
    continue
  }
  if (entry.type !== 'file' && entry.type !== 'raw') throw new Error(`${entry.cid}: unsupported entry type ${entry.type}`)
  const target = rel === '' ? out : path.join(out, rel)
  fs.mkdirSync(path.dirname(target), { recursive: true })
  const fd = fs.openSync(target + '.part', 'w')
  let size = 0
  for await (const chunk of entry.content()) { fs.writeSync(fd, chunk); size += chunk.length }
  fs.closeSync(fd)
  fs.renameSync(target + '.part', target)
  files.push({ path: rel, size, cid: entry.cid.toString() })
}

const result = { cid: root.toString(), kind, out, files: files.length, size: files.reduce((a, f) => a + f.size, 0), blocks: dag.blocks, dag_bytes: dag.bytes, fetched, cached }

if (readd) {
  const nothing = { async put (cid) { return cid } }
  let last
  if (kind === 'directory') {
    const dirs = []
    for await (const item of recursive(root, store)) {
      if ((await exporter(item.cid, store)).type === 'directory') dirs.push(relative(item.path))
    }
    const source = [
      ...dirs.filter(d => d !== '').map(d => ({ path: `root/${d}` })),
      ...files.map(f => ({ path: `root/${f.path}`, content: fs.readFileSync(path.join(out, f.path)) }))
    ]
    for await (const e of importer(source, nothing, { profile: 'unixfs-v0-2015', wrapWithDirectory: false })) {
      if (e.path === 'root') last = e.cid
    }
  } else {
    for await (const e of importer([{ content: fs.readFileSync(out) }], nothing, { profile: 'unixfs-v0-2015' })) last = e.cid
  }
  result.readd_cid = last?.toString()
  result.readd_matches = result.readd_cid === result.cid
}

console.log(JSON.stringify(result))
