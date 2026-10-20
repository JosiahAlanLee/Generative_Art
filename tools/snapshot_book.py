"""Import public book source without changing its bytes or relative paths.

Usage: python tools/snapshot_book.py /path/to/Codex-Intervallorum --commit SHA
The checkout must already contain the selected files. Network access is not used.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "JosiahAlanLee/Codex-Intervallorum"
DEST = "sources/codex-intervallorum"


def reason(path):
    p = Path(path)
    if p.suffix == ".py":
        return None
    if p.suffix == ".svg" or ("fonts" in p.parts and p.suffix in {".ttf", ".txt"}):
        return None
    if p.name in {"NOTICES.md", "requirements.txt", "requirements-lock.txt"}:
        return None
    if path in {"docs/EDGE-GRAIN-2026-10-19.md", "docs/FIGURE-GROWTH-2026-10-19.md"}:
        return None
    if path.startswith("books/07_septimus/clausa/") and p.suffix == ".md":
        return None
    if p.suffix in {".json", ".csv"} and any(part in p.parts for part in ("proofs", "models", "vendor")):
        return None
    return "Outside technique code and technical inputs: book prose, editorial/provenance records, rasters, edition PDFs or repository administration"


def role(path):
    if "/tests/" in path or Path(path).stem.startswith(("test_", "validate", "check_")):
        return "validation"
    if "/models/" in path or Path(path).stem in {"reachability", "refusal"}:
        return "model-support"
    if path.startswith("common/") or "/fields/" in path or "/generator/" in path or "/plates/" in path or "/semiphoras/" in path or "/proofs/" in path or path in {"binding/scribal.py", "binding/vellum.py"}:
        return "visual-technique"
    return "book-integration"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    actual = subprocess.check_output(["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True).strip()
    if actual != args.commit:
        raise SystemExit(f"Checkout is {actual}; expected {args.commit}")
    tree = subprocess.check_output(["git", "-C", str(args.checkout), "ls-tree", "-r", "-z", actual])
    records, modules = [], []
    for item in tree.split(b"\0"):
        if not item:
            continue
        meta, raw_path = item.split(b"\t", 1)
        mode, kind, blob = meta.decode().split()
        path = raw_path.decode()
        omitted = reason(path)
        record = dict(path=path, git_blob_sha=blob, included=omitted is None)
        if omitted:
            record["reason"] = omitted
        else:
            data = (args.checkout / path).read_bytes()
            blob_hash = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if blob_hash != blob:
                raise SystemExit(f"Modified or unavailable upstream file: {path}")
            local = f"{DEST}/{path}"
            target = ROOT / local
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            record.update(local_path=local, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
            if path.endswith(".py"):
                parsed = ast.parse(data, filename=path)
                doc = ast.get_docstring(parsed) or ""
                module = dict(path=path, local_path=local, role=role(path),
                              description=doc.split("\n")[0],
                              symbols=[n.name for n in parsed.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))])
                modules.append(module)
        records.append(record)
    manifest = dict(schema_version=1, repository=REPOSITORY, ref="main", commit=actual,
                    scope="All public Python source, source SVGs, fonts/notices and selected technical inputs; manuscript and upstream provenance records excluded",
                    files=records)
    (ROOT / "catalog").mkdir(exist_ok=True)
    (ROOT / "catalog/source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "catalog/modules.json").write_text(json.dumps(modules, indent=2) + "\n")
    lines = ["# Book source index", "", f"Pinned to `{REPOSITORY}@{actual}`. All {len(modules)} Python files are retained, including validators and build/model dependencies.", "", "Roles distinguish reusable visual code from book assembly, model support and checks. File links go to unchanged local copies. See [the technique catalog](../CATALOG.md) for artistic uses.", ""]
    for m in modules:
        lines += [f"## [{m['path']}](../{m['local_path']})", "", f"**{m['role']}**. {m['description']}", "", "Symbols: " + (", ".join(f"`{s}`" for s in m["symbols"]) or "package marker") + ".", ""]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/SOURCE_INDEX.md").write_text("\n".join(lines))
    print(f"Imported {sum(r['included'] for r in records)} files; {len(modules)} Python modules; {len(records)} upstream paths accounted for")


if __name__ == "__main__":
    main()
