"""Validate the Notoria plates: the shared structural checks (two layers, two inks, no fills,
page margin, reserved blank, caption and carrier round trips), and then the field itself:
regenerate it from the plate's run manifest and check that the output hashes identically and
that the identifier the frame carries is the manifest's.

    python validate.py out/            every nota under out/<stem>/
    python validate.py out/nota-i-deposit
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
sys.path.insert(0, os.path.join(HERE, "..", "fields"))
import plate  # noqa: E402
import physarum  # noqa: E402


def validate_dir(d):
    report = plate.validate(d)
    meta = json.load(open(os.path.join(d, "build-meta.json")))
    m = json.load(open(os.path.join(d, "run-manifest.json")))
    ok, _ = physarum.regenerate_and_check(m)
    field = {"manifest_id": m["id"],
             "manifest_id_recomputed": physarum.manifest_id(m) == m["id"],
             "code_sha256_matches_this_file": physarum.code_hash() == m["code_sha256"],
             "field_regenerates_identically": ok,
             "frame_carries_manifest_id": report["hidden_decoded"] == f"NOTA {meta['plate']} RUN {m['id']}"}
    field["all_passed"] = all(v for k, v in field.items() if isinstance(v, bool))
    report["field"] = field
    report["all_passed"] = bool(report["all_passed"] and field["all_passed"])
    with open(os.path.join(d, "validation.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(field, indent=1))
    print("ALL PASSED" if report["all_passed"] else "FAILED", d)
    return report["all_passed"]


def main(path):
    if os.path.exists(os.path.join(path, "build-meta.json")):
        dirs = [path]
    else:
        dirs = sorted(os.path.join(path, n) for n in os.listdir(path) if os.path.exists(os.path.join(path, n, "build-meta.json")))
    results = [validate_dir(d) for d in dirs]
    if not results or not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out"))
