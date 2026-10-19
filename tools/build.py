#!/usr/bin/env python3
"""Build data/catalog.json (what the viewer reads) and data/cids.txt (what to pin).

    python tools/build.py

Reads data/onchain.json, data/iterations/, data/metadata/ and data/folders.json.
Run it after tools/collect.py and tools/archive.py.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# Who the split addresses are. The labels in quotes are TzKT's public aliases;
# the rest are how the project descriptions name the recipient.
LABELS = {
    "tz1LwHHzSP3oX4Lwpf2oPD52tViuxGCjCZQv": "Echevarian (the artist)",
    "tz1aPHze1U5BEEKrGYt3dvY6aAQEeiWm8jjK": "Processing Foundation (TzKT alias \"ProcessingOrg\")",
    "tz1ZBMhTa7gxSpaeXoqyc6bTCrxEHfZYSpPt": "aebrer (TzKT alias \"aebrer - Andrew B\")",
    "tz1V1WKxhK9g5UFbhRNUnQMmDnnL2vtBzoZJ": "Hydra's inventor, as the descriptions put it (no TzKT alias)",
    "KT1U6EHmNxJTkvaWJ4ThczG4FSDaHC21ssvi": "each iteration's first minter (fxhash records this share against the gentk contract)",
}


SHORT = {
    "tz1LwHHzSP3oX4Lwpf2oPD52tViuxGCjCZQv": "Echevarian",
    "tz1aPHze1U5BEEKrGYt3dvY6aAQEeiWm8jjK": "Processing Foundation",
    "tz1ZBMhTa7gxSpaeXoqyc6bTCrxEHfZYSpPt": "aebrer",
    "tz1V1WKxhK9g5UFbhRNUnQMmDnnL2vtBzoZJ": "Hydra's inventor",
    "KT1U6EHmNxJTkvaWJ4ThczG4FSDaHC21ssvi": "first minter",
}


def cid_of(uri):
    m = re.match(r"ipfs://([^/?#]+)", uri or "")
    return m.group(1) if m else None


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def reads_hash_from_url(folder):
    """True if the generator takes its hash from ?fxhash= rather than from a
    line fxhash rewrote when it minted each token."""
    for dirpath, _, names in os.walk(folder):
        for n in names:
            if n.endswith((".html", ".js")):
                with open(os.path.join(dirpath, n), errors="replace") as f:
                    text = f.read()
                if re.search(r"""\.get\(\s*['"]fxhash['"]\s*\)""", text):
                    return True
    return False


def main():
    onchain = load(os.path.join(DATA, "onchain.json"))
    folders = load(os.path.join(DATA, "folders.json"), {})
    by_role = {v["role"]: (cid, v) for cid, v in folders.items()}
    projects, cids, missing = [], [], []

    for p in onchain["projects"]:
        pid = p["id"]
        mcid = cid_of(p["metadata_uri"])
        meta = load(os.path.join(DATA, "metadata", f"{mcid}.json"), {}) or {}
        its = load(os.path.join(DATA, "iterations", f"{pid}.json"), {"iterations": []})["iterations"]
        title = meta.get("name") or p.get("title_from_gentk") or f"project {pid}"
        gen_cid = cid_of(meta.get("generativeUri")) or (p["generator_cids_in_artifacts"] or [None])[0]
        gen = by_role.get(f"project {pid} generator")
        gen_path = gen[1]["path"] + "/" if gen else None
        if not gen:
            missing.append(f"{pid} generator")
        folder = os.path.dirname(gen_path.rstrip("/")) if gen_path else None

        iteration_folders = {}
        for x in its:
            hit = by_role.get(f"project {pid} iteration {x['iteration']}")
            if hit:
                iteration_folders[str(x["iteration"])] = hit[1]["path"] + "/"
            elif x["artifact_uri"] and "fxhash=" not in x["artifact_uri"]:
                missing.append(f"{pid} iteration {x['iteration']}")

        def split(rows):
            return [{"address": s["address"], "share": s["permille"] / 10,
                     "who": LABELS.get(s["address"], s["alias"] or s["address"])} for s in rows]

        thumb = meta.get("thumbnailUri")
        projects.append({
            "id": pid,
            "title": title,
            "minted": p["mint"]["time"],
            "mint_op": p["mint"]["op"],
            "issuer": p["mint"]["contract"],
            "editions": p["ledger"]["supply"],
            "editions_at_mint": p["mint"]["supply"],
            "iterations_minted": p["iterations_minted"],
            "royalties": p["ledger"]["royalties_permille"] / 10,
            "primary_split": split(p["ledger"]["primary_split"]),
            "royalties_split": split(p["ledger"]["royalties_split"]),
            "description": meta.get("description", p.get("description_from_gentk")),
            "tags": meta.get("tags", p.get("tags_from_gentk")) or [],
            "strobe": "strobe" in title.lower(),
            "folder": folder,
            "generator": gen_path,
            "generator_cid": gen_cid,
            "metadata_cid": mcid,
            "reads_hash_from_url": reads_hash_from_url(os.path.join(ROOT, gen_path)) if gen_path else None,
            "iteration_folders": iteration_folders,
            "thumbnail_cid": cid_of(thumb),
            "display_cid": cid_of(meta.get("displayUri")),
            "preview_hash": meta.get("previewHash"),
        })

        cids.append(("metadata", mcid, f"project {pid} metadata"))
        if gen_cid:
            cids.append(("generator", gen_cid, f"project {pid} generator"))
        for x in its:
            if x["artifact_uri"] and "fxhash=" not in x["artifact_uri"]:
                cids.append(("iteration", cid_of(x["artifact_uri"]), f"project {pid} iteration {x['iteration']}"))
            if x["metadata_uri"]:
                cids.append(("token-metadata", cid_of(x["metadata_uri"]), f"project {pid} iteration {x['iteration']}"))
            for k in ("display_uri", "thumbnail_uri"):
                if x[k]:
                    cids.append(("capture", cid_of(x[k]), f"project {pid} iteration {x['iteration']} {k[:-4]}"))
        for k in ("displayUri", "thumbnailUri"):
            if meta.get(k):
                cids.append(("capture", cid_of(meta[k]), f"project {pid} {k[:-3]}"))

    hen = []
    for h in onchain.get("hen", []):
        art = by_role.get(f"hen {h['token_id']} artifact")
        if not art:
            missing.append(f"OBJKT {h['token_id']}")
        hen.append({
            "token_id": h["token_id"],
            "contract": h["contract"],
            "title": h["title"],
            "minted": h["minted"],
            "mint_op": h["mint_op"],
            "editions": h["editions"],
            "description": h["description"],
            "tags": h["tags"] or [],
            "folder": art[1]["path"] + "/" if art else None,
            "artifact_cid": cid_of(h["artifact_uri"]),
            "metadata_cid": cid_of(h["metadata_uri"]),
        })
        cids.append(("metadata", cid_of(h["metadata_uri"]), f"OBJKT {h['token_id']} metadata"))
        cids.append(("hen", cid_of(h["artifact_uri"]), f"OBJKT {h['token_id']} {h['title']}"))
        for k in ("display_uri", "thumbnail_uri"):
            if h.get(k):
                cids.append(("capture", cid_of(h[k]), f"OBJKT {h['token_id']} {k[:-4]}"))

    catalog = {
        "artist": "Echevarian",
        "address": onchain["author"],
        "note": "Built by tools/build.py from public chain data and IPFS. See README.md.",
        "projects": projects,
        "hen": hen,
    }
    with open(os.path.join(DATA, "catalog.json"), "w") as f:
        json.dump(catalog, f, indent=1, ensure_ascii=False)
        f.write("\n")

    update_readme(projects, hen, onchain)

    seen = set()
    with open(os.path.join(DATA, "cids.txt"), "w") as f:
        f.write("# kind\tcid\twhat\n")
        for kind, cid, what in cids:
            if cid and cid not in seen:
                seen.add(cid)
                f.write(f"{kind}\t{cid}\t{what}\n")

    print(f"{len(projects)} projects, {len(seen)} CIDs to pin", file=sys.stderr)
    if missing:
        print(f"not yet archived: {len(missing)} ({', '.join(missing[:6])}{'...' if len(missing) > 6 else ''})",
              file=sys.stderr)


def replace_between(text, name, body):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    a, b = text.index(start) + len(start), text.index(end)
    return text[:a] + "\n" + body + text[b:]


def update_readme(projects, hen, onchain):
    path = os.path.join(ROOT, "README.md")
    with open(path) as f:
        text = f.read()
    rows = ["| Published | Project | Minted | Code |", "|---|---|---|---|"]
    for p in sorted(projects, key=lambda p: p["minted"]):
        minted = f"{p['iterations_minted']} of {p['editions']}"
        if p["editions_at_mint"] != p["editions"]:
            minted += f" ({p['editions_at_mint']} at launch)"
        code = f"[generator]({p['generator']})" if p["generator"] else "not yet archived"
        if p["iteration_folders"]:
            code += f", {len(p['iteration_folders'])} token folders"
        title = p["title"].replace("|", "\\|")
        rows.append(f"| {p['minted'][:10]} | {title} | {minted} | {code} |")
    text = replace_between(text, "projects", "\n".join(rows) + "\n")

    rows = ["| Published | Piece | Editions | Code |", "|---|---|---|---|"]
    for h in hen:
        code = f"[folder]({h['folder']})" if h["folder"] else "not yet archived"
        rows.append(f"| {h['minted'][:10]} | {h['title']} (OBJKT {h['token_id']}) | {h['editions']} | {code} |")
    text = replace_between(text, "hen", "\n".join(rows) + "\n")

    def fmt(split):
        return ", ".join(f"{SHORT.get(s['address'], s['address'])} {s['share']:g}%" for s in split)

    rows = ["| Project | Sales | Royalties |", "|---|---|---|"]
    others = False
    for p in sorted(projects, key=lambda p: p["minted"]):
        everyone = {s["address"] for s in p["primary_split"] + p["royalties_split"]}
        if everyone == {onchain["author"]}:
            continue
        others = True
        title = p["title"].replace("|", "\\|")
        rows.append(f"| {title} | {fmt(p['primary_split'])} | {p['royalties']:g}% of resales: {fmt(p['royalties_split'])} |")
    note = ("\nIn every other project, sales and royalties went to Echevarian alone. \"Hydra's inventor\" is how the "
            "descriptions name the recipient at tz1V1WKxhK9g5UFbhRNUnQMmDnnL2vtBzoZJ, which has no public alias on TzKT. "
            "\"First minter\" is fxhash's share for whoever minted each iteration, recorded against the gentk contract.\n")
    text = replace_between(text, "splits", ("\n".join(rows) + "\n" + note) if others else "None.\n")
    with open(path, "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
