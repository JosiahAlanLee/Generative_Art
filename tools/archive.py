#!/usr/bin/env python3
"""Fetch every folder and metadata file that data/onchain.json points to.

    python tools/archive.py [--gateway URL]... [--only ID]...

Run tools/collect.py first. Needs Node 18 or later and `npm ci` in tools/.
Each CID goes through tools/fetch.mjs, which checks every block against its
CID before anything is written. Folders already listed in data/folders.json
are skipped, so the script can be run again after an interruption.

Writes
    data/metadata/<cid>.json             project metadata and signed token
                                         metadata, byte for byte
    projects/<id>-<slug>/generator/      the generator folder (generativeUri)
    projects/<id>-<slug>/iterations/NNN/ the token's own folder, for the early
                                         iterations whose hash fxhash wrote
                                         into the code instead of the URL
    data/folders.json                    what was fetched, and whether
                                         `ipfs add -r` of the folder gives the
                                         original CID back
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FETCH = os.path.join(ROOT, "tools", "fetch.mjs")
DATA = os.path.join(ROOT, "data")


def cid_of(uri):
    m = re.match(r"ipfs://([^/?#]+)", uri or "")
    return m.group(1) if m else None


def slug(title):
    return re.sub(r"[^a-z0-9_]+", "-", (title or "").lower()).strip("-") or "untitled"


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    os.replace(path + ".part", path)


class Fetcher:
    def __init__(self, gateways):
        self.gateways = gateways
        self.folders = load(os.path.join(DATA, "folders.json"), {})

    def get(self, cid, out, role):
        rel = os.path.relpath(out, ROOT)
        known = self.folders.get(cid)
        if known and known["path"] == rel and os.path.exists(out):
            return known
        tmp = out + ".partial"
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.isfile(tmp):
            os.remove(tmp)
        cmd = ["node", FETCH, cid, tmp, "--readd"]
        for g in self.gateways:
            cmd += ["--gateway", g]
        env = dict(os.environ, NODE_USE_ENV_PROXY=os.environ.get("NODE_USE_ENV_PROXY", "1"),
                   NODE_NO_WARNINGS="1")
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if r.returncode != 0:
            msg = (r.stderr.strip().splitlines() or ["fetch failed"])[-1]
            raise RuntimeError(f"{cid}: {msg}")
        res = json.loads(r.stdout.strip().splitlines()[-1])
        if os.path.isdir(out):
            shutil.rmtree(out)
        elif os.path.exists(out):
            os.remove(out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        os.replace(tmp, out)
        entry = {
            "path": rel, "role": role, "kind": res["kind"], "files": res["files"],
            "size": res["size"], "blocks": res["blocks"],
            "readd_matches": res.get("readd_matches"),
        }
        self.folders[cid] = entry
        save(os.path.join(DATA, "folders.json"), self.folders)
        return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", action="append", default=[])
    ap.add_argument("--only", action="append", type=int, default=[])
    args = ap.parse_args()
    gateways = args.gateway or ["https://trustless-gateway.link"]

    onchain = load(os.path.join(DATA, "onchain.json"), None)
    if onchain is None:
        sys.exit("run tools/collect.py first")
    f = Fetcher(gateways)
    problems = []

    for p in onchain["projects"]:
        if args.only and p["id"] not in args.only:
            continue
        # Project metadata: the name, description and generativeUri.
        mcid = cid_of(p["metadata_uri"])
        try:
            f.get(mcid, os.path.join(DATA, "metadata", f"{mcid}.json"), f"project {p['id']} metadata")
        except RuntimeError as e:
            problems.append(str(e))
            print(f"{p['id']:>6}  metadata not retrieved: {e}", file=sys.stderr)
            continue
        with open(os.path.join(DATA, "metadata", f"{mcid}.json"), "rb") as fh:
            meta = json.loads(fh.read())
        title = meta.get("name") or p.get("title_from_gentk")
        folder = os.path.join(ROOT, "projects", f"{p['id']}-{slug(title)}")
        gen = cid_of(meta.get("generativeUri"))
        status = []
        try:
            e = f.get(gen, os.path.join(folder, "generator"), f"project {p['id']} generator")
            status.append(f"generator {e['files']} files, {e['size']:,} bytes"
                          f"{'' if e['readd_matches'] else ', re-add differs'}")
        except RuntimeError as err:
            problems.append(str(err))
            status.append(f"generator not retrieved: {err}")

        its = load(os.path.join(DATA, "iterations", f"{p['id']}.json"), {"iterations": []})["iterations"]
        width = max(3, len(str(p["mint"]["supply"])))
        baked = [x for x in its if x["artifact_uri"] and "fxhash=" not in x["artifact_uri"]]
        done = 0
        for x in baked:
            acid = cid_of(x["artifact_uri"])
            try:
                f.get(acid, os.path.join(folder, "iterations", str(x["iteration"]).zfill(width)),
                      f"project {p['id']} iteration {x['iteration']}")
                done += 1
            except RuntimeError as err:
                problems.append(str(err))
        if baked:
            status.append(f"{done} of {len(baked)} early iteration folders")

        # Signed token metadata the indexer has not picked up.
        for x in its:
            if x["signed"] and x["name"] is None:
                tcid = cid_of(x["metadata_uri"])
                try:
                    f.get(tcid, os.path.join(DATA, "metadata", f"{tcid}.json"),
                          f"project {p['id']} iteration {x['iteration']} metadata")
                except RuntimeError as err:
                    problems.append(str(err))
        print(f"{p['id']:>6}  {title:<34} {'; '.join(status)}", file=sys.stderr)

    if problems:
        print(f"\n{len(problems)} not retrieved:", file=sys.stderr)
        for line in problems:
            print("  " + line, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
