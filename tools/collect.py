#!/usr/bin/env python3
"""Rebuild the on-chain record of the fxhash projects from the TzKT indexer.

Everything here is public Tezos data: the project mints, the issuer ledger,
the gentk tokens and the operations that minted them. Nothing is read from
fxhash's servers.

    python tools/collect.py [--author tz1...] [--out data]

Writes
    data/onchain.json            one record per project
    data/iterations/<id>.json    one record per minted iteration

An iteration's hash is the hash of the operation that minted it. The script
checks that against the hash in the token's metadata and stops if they
differ. Where fxhash never signed the token, or the indexer still holds the
unsigned placeholder, the hash comes from the operation alone and is marked.
"""
import argparse
import json
import os
import re
import sys
import time

import requests

API = "https://api.tzkt.io/v1"
AUTHOR = "tz1LwHHzSP3oX4Lwpf2oPD52tViuxGCjCZQv"

ISSUERS = {
    "KT1AEVuykWeuuFX7QkEAMNtffzwhe1Z98hJS": "fxhash issuer, beta (Nov 2021 to Jan 2022)",
    "KT1XCoGnfupWk7Sp8536EfrxcP73LmT68Nyr": "fxhash issuer, v1 (to Apr 2022)",
    "KT1BJC12dG17CVvPKJ1VYaNnaT5mzfnUTwXv": "fxhash issuer, v2 (from Apr 2022; every earlier project was migrated here under the same id)",
}
ISSUER_V2 = "KT1BJC12dG17CVvPKJ1VYaNnaT5mzfnUTwXv"
GENTK = {
    "KT1KEa8z6vWXDJrVqtMrAeDVzsvxat3kHaCE": "fxhash gentk v1",
    "KT1U6EHmNxJTkvaWJ4ThczG4FSDaHC21ssvi": "fxhash gentk v2",
}
PLACEHOLDER = "[WAITING TO BE SIGNED]"

session = requests.Session()


def get(path, **params):
    for attempt in range(6):
        r = session.get(API + path, params=params, timeout=90)
        if r.status_code in (429, 502, 503, 504):
            time.sleep(2 + attempt * 3)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def paged(path, **params):
    out, offset = [], 0
    while True:
        page = get(path, limit=1000, offset=offset, **params)
        out += page
        if len(page) < 1000:
            return out
        offset += 1000


def chunks(seq, n=100):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def decode(v):
    """Bytes stored as hex; the beta issuer wrapped them in a map {"": bytes}."""
    if isinstance(v, dict):
        v = v.get("")
    try:
        return bytes.fromhex(v).decode()
    except (TypeError, ValueError):
        return v


def cid_of(uri):
    m = re.match(r"ipfs://([^/?#]+)", uri or "")
    return m.group(1) if m else None


def bigmap_ptr(contract, path):
    for m in get(f"/contracts/{contract}/bigmaps", select="ptr,path"):
        if m["path"] == path:
            return m["ptr"]
    raise SystemExit(f"no big map {path} on {contract}")


def aliases(addresses):
    out = {}
    for chunk in chunks(sorted(addresses)):
        for a in get("/accounts", **{"address.in": ",".join(chunk), "select": "address,alias"}):
            out[a["address"]] = a["alias"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default=AUTHOR)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    # 1. Every project mint the author sent, on any issuer.
    mints = get("/operations/transactions", sender=args.author, entrypoint="mint_issuer",
                status="applied", limit=1000, select="level,timestamp,target,hash,parameter")
    by_meta = {}
    for m in mints:
        v = m["parameter"]["value"]
        by_meta[decode(v["metadata"])] = {
            "op": m["hash"],
            "time": m["timestamp"],
            "contract": m["target"]["address"],
            "supply": int(v["amount"]),
            "royalties_permille": int(v["royalties"]),
            "enabled": v.get("enabled"),
            "price_mutez": int(v["price"]) if "price" in v else None,
        }

    # 2. The issuer ledger as it stands.
    ledger = paged(f"/contracts/{ISSUER_V2}/bigmaps/ledger/keys",
                   **{"value.author": args.author, "select": "key,value"})
    split_addresses = {s["address"] for row in ledger
                       for s in row["value"].get("primary_split", []) + row["value"].get("royalties_split", [])}
    names = aliases(split_addresses)

    def split(rows):
        return [{"address": s["address"], "alias": names.get(s["address"]),
                 "permille": int(s["pct"])} for s in rows]

    projects = []
    for row in ledger:
        v = row["value"]
        uri = decode(v["metadata"])
        if uri not in by_meta:
            raise SystemExit(f"project {row['key']}: no mint by {args.author} with metadata {uri}")
        projects.append({
            "id": int(row["key"]),
            "metadata_uri": uri,
            "mint": by_meta.pop(uri),
            "ledger": {
                "contract": ISSUER_V2,
                "supply": int(v["supply"]),
                "balance": int(v["balance"]),
                "enabled": v["enabled"],
                "royalties_permille": int(v["royalties"]),
                "primary_split": split(v.get("primary_split", [])),
                "royalties_split": split(v.get("royalties_split", [])),
            },
        })
    if by_meta:
        raise SystemExit(f"mints with no ledger entry: {[m['op'] for m in by_meta.values()]}")
    projects.sort(key=lambda p: p["id"])

    # 3. Iterations: token_data says which project a gentk belongs to.
    os.makedirs(os.path.join(args.out, "iterations"), exist_ok=True)
    ptrs = {c: (bigmap_ptr(c, "token_data"), bigmap_ptr(c, "token_metadata")) for c in GENTK}
    total = 0
    for p in projects:
        its = []
        for contract, (td_ptr, tm_ptr) in ptrs.items():
            rows = paged(f"/bigmaps/{td_ptr}/keys", **{"value.issuer_id": p["id"], "select": "key,value"})
            ids = [r["key"] for r in rows]
            tokens, onchain_meta, mint_op = {}, {}, {}
            for chunk in chunks(ids):
                joined = ",".join(chunk)
                for t in get("/tokens", contract=contract, **{"tokenId.in": joined}, limit=1000,
                             select="tokenId,firstTime,totalSupply,metadata"):
                    tokens[t["tokenId"]] = t
                for k in get(f"/bigmaps/{tm_ptr}/keys", **{"key.in": joined}, limit=1000,
                             select="key,value,updates"):
                    onchain_meta[k["key"]] = (decode(k["value"]["token_info"]), k["updates"])
                transfers = get("/tokens/transfers", **{"token.contract": contract, "token.tokenId.in": joined,
                                                        "from.null": "true"}, limit=1000,
                                select="token.tokenId,transactionId")
                ops = {}
                for tchunk in chunks([str(t["transactionId"]) for t in transfers]):
                    ops.update({o["id"]: o["hash"] for o in get("/operations/transactions",
                                                                 **{"id.in": ",".join(tchunk)}, limit=1000,
                                                                 select="id,hash")})
                for t in transfers:
                    mint_op[t["token.tokenId"]] = ops[t["transactionId"]]
            for r in rows:
                key = r["key"]
                t = tokens.get(key, {})
                md = t.get("metadata") or {}
                meta_uri, updates = onchain_meta[key]
                op = mint_op[key]
                indexed_hash = md.get("iterationHash")
                art = md.get("artifactUri")
                if not indexed_hash and art and "fxhash=" in art:
                    indexed_hash = art.split("fxhash=")[1].split("&")[0]
                placeholder = md.get("name") == PLACEHOLDER
                if indexed_hash and indexed_hash != op:
                    raise SystemExit(f"{contract}:{key}: metadata hash {indexed_hash} != mint operation {op}")
                if not placeholder:
                    source = "metadata, equal to the mint operation"
                elif updates > 1:
                    source = "mint operation; signed on chain, but the indexer still holds the placeholder"
                else:
                    source = "mint operation; fxhash never signed this token"
                its.append({
                    "iteration": int(r["value"]["iteration"]),
                    "hash": op,
                    "hash_source": source,
                    "contract": contract,
                    "token_id": int(key),
                    "minted": t.get("firstTime"),
                    "mint_op": op,
                    "metadata_uri": meta_uri,
                    "signed": updates > 1,
                    "burned": t.get("totalSupply") == "0",
                    "name": None if placeholder else md.get("name"),
                    "artifact_uri": None if placeholder else art,
                    "display_uri": None if placeholder else md.get("displayUri"),
                    "thumbnail_uri": None if placeholder else md.get("thumbnailUri"),
                    "attributes": None if placeholder else md.get("attributes"),
                    "_description": None if placeholder else md.get("description"),
                    "_tags": None if placeholder else md.get("tags"),
                })
        its.sort(key=lambda x: x["iteration"])
        named = [x for x in its if x["name"]]
        if named:
            p["title_from_gentk"] = re.sub(r"\s*#\d+$", "", named[0]["name"])
            p["description_from_gentk"] = named[0]["_description"]
            p["tags_from_gentk"] = named[0]["_tags"]
        p["iterations_minted"] = len(its)
        p["generator_cids_in_artifacts"] = sorted({cid_of(x["artifact_uri"]) for x in its
                                                   if x["artifact_uri"] and "fxhash=" in x["artifact_uri"]})
        for x in its:
            del x["_description"], x["_tags"]
        total += len(its)
        with open(os.path.join(args.out, "iterations", f"{p['id']}.json"), "w") as f:
            json.dump({"project": p["id"], "iterations": its}, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"{p['id']:>6}  {p.get('title_from_gentk', '?'):<34} {len(its):>4} of {p['ledger']['supply']}",
              file=sys.stderr)

    with open(os.path.join(args.out, "onchain.json"), "w") as f:
        json.dump({"author": args.author, "source": API, "issuers": ISSUERS, "gentk": GENTK,
                   "projects": projects}, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"{len(projects)} projects, {total} iterations", file=sys.stderr)


if __name__ == "__main__":
    main()
