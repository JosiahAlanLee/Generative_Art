#!/usr/bin/env python3
"""Pin this archive to an IPFS (Kubo) node on this computer.

    python3 tools/pin.py              pin the folders and metadata kept here
    python3 tools/pin.py --network    also pin what is only on IPFS: the capture
                                      images and token metadata, fetched from
                                      other nodes while they still serve them
    python3 tools/pin.py --dry-run    show what would be pinned

Needs Kubo (the `ipfs` command, also bundled with IPFS Desktop). Run
`ipfs init` once before the first use; for --network the node must be
running (`ipfs daemon`, or IPFS Desktop open).

Each folder is added from this repository with the settings fxhash's uploads
used, and the CID that comes back is compared with the original. A folder
that does not reproduce its CID is reported and left unpinned, so nothing is
pinned under a CID nobody else uses.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADD = ["ipfs", "add", "-Q", "--cid-version=0", "--raw-leaves=false",
       "--chunker=size-262144", "--hidden"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.dry_run and not shutil.which("ipfs"):
        sys.exit("The ipfs command (Kubo) was not found. Install Kubo or IPFS Desktop first.")

    with open(os.path.join(ROOT, "data", "folders.json")) as f:
        folders = json.load(f)
    pinned, differ = set(), []
    for cid, entry in sorted(folders.items(), key=lambda kv: kv[1]["path"]):
        path = os.path.join(ROOT, entry["path"])
        cmd = ADD + (["-r"] if entry["kind"] == "directory" else []) + [path]
        if args.dry_run:
            print(f"add  {entry['path']}  -> {cid}")
            continue
        # Hash first; add and pin only if the CID is the original one.
        got = subprocess.run(cmd + ["--only-hash"], capture_output=True, text=True, check=True).stdout.strip()
        if got == cid:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            pinned.add(cid)
            print(f"pinned   {cid}  {entry['path']}")
        else:
            differ.append((entry["path"], cid, got))
            print(f"differs  {entry['path']}: original {cid}, this copy adds as {got}")

    if args.network:
        with open(os.path.join(ROOT, "data", "cids.txt")) as f:
            rows = [line.rstrip("\n").split("\t") for line in f if not line.startswith("#")]
        todo = [(kind, cid, what) for kind, cid, what in rows if cid not in pinned]
        for i, (kind, cid, what) in enumerate(todo, 1):
            if args.dry_run:
                print(f"pin  {cid}  {what}")
                continue
            r = subprocess.run(["ipfs", "pin", "add", "--progress=false", f"/ipfs/{cid}"],
                               capture_output=True, text=True, timeout=600)
            state = "pinned" if r.returncode == 0 else "failed"
            print(f"[{i}/{len(todo)}] {state}  {cid}  {what}")

    if differ:
        print(f"\n{len(differ)} folders did not reproduce their original CID; see above.")


if __name__ == "__main__":
    main()
