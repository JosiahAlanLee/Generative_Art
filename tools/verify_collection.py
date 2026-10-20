"""Check upstream byte identity, complete Python coverage and catalog links."""
import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "catalog/source-manifest.json").read_text())
    included = [f for f in manifest["files"] if f["included"]]
    for entry in included:
        data = (ROOT / entry["local_path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["path"]
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == entry["git_blob_sha"], entry["path"]
        if entry["path"].endswith(".py"):
            ast.parse(data, filename=entry["path"])
    modules = json.loads((ROOT / "catalog/modules.json").read_text())
    python_paths = {f["path"] for f in manifest["files"] if f["path"].endswith(".py")}
    assert python_paths == {m["path"] for m in modules}
    assert all(f["included"] for f in manifest["files"] if f["path"].endswith(".py"))
    development = json.loads((ROOT / "catalog/development-art-manifest.json").read_text())
    for entry in development["files"]:
        data = (ROOT / entry["local_path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["local_path"]
        if not entry["modifications"]:
            assert hashlib.sha256(data).hexdigest() == entry["upstream_sha256"], entry["local_path"]
        if entry["local_path"].endswith(".py"):
            ast.parse(data, filename=entry["local_path"])
    techniques = json.loads((ROOT / "catalog/techniques.json").read_text())
    assert len({t["id"] for t in techniques}) == len(techniques)
    for technique in techniques:
        assert (ROOT / technique["guide"]).is_file(), technique["guide"]
        for path in technique["sources"]:
            assert (ROOT / path).is_file(), path
    # Check our navigation. Upstream Markdown is preserved and can refer to
    # intentionally omitted rasters/PDFs; it is not rewritten to disguise that.
    docs = [ROOT / "README.md", ROOT / "CATALOG.md", ROOT / "NOTICES.md"]
    docs += list((ROOT / "docs").glob("*.md")) + list((ROOT / "techniques").rglob("*.md"))
    for doc in docs:
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            local = unquote(target.split("#")[0])
            assert (doc.parent / local).exists(), f"{doc}: {target}"
    print(f"Verified {len(included)} public snapshot files, {len(development['files'])} selected development-art files, {len(techniques)} techniques and local guide links")


if __name__ == "__main__":
    main()
