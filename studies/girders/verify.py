#!/usr/bin/env python3
"""Generate fixtures, run native Blender checks, and render all look proofs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_BLENDER = Path.home() / "dev/blender-5.2.3-linux-x64/blender"


def run(command, log):
    print(" ".join(str(x) for x in command), flush=True)
    with log.open("a", encoding="utf-8") as stream:
        proc = subprocess.Popen(
            [str(x) for x in command], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
            stream.write(line)
        code = proc.wait()
    if code:
        raise SystemExit(f"command failed ({code}); see {log}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--scene", type=Path,
                   help="verify this scene instead of generating the fixture")
    p.add_argument("--blender", type=Path,
                   default=Path(os.environ.get("BLENDER", DEFAULT_BLENDER)))
    p.add_argument("--skip-renders", action="store_true")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    log = a.out / "verify.log"
    log.write_text("", encoding="utf-8")
    scene = a.scene or (a.out / "fixture.json.gz")
    if a.scene is None:
        run([sys.executable, ROOT / "testscene.py", "--kind", "fixture",
             "--out", scene], log)
    run([a.blender, "-b", "--python", ROOT / "verify_blender.py", "--",
         "--scene", scene, "--out", a.out], log)
    if not a.skip_renders:
        for look in ("overcast", "low_sun", "night", "mineral", "ink"):
            run([sys.executable, ROOT / "render.py", scene,
                 "--look", look, "--camera", "worm", "--preview",
                 "--res", "3840x2160", "--samples", "32",
                 "--out", a.out / look], log)
    report = json.loads((a.out / "verify.json").read_text())
    report["renders"] = {} if a.skip_renders else {
        look: sorted(str(x) for x in (a.out / look).glob("*.png"))
        for look in ("overcast", "low_sun", "night", "mineral", "ink")
    }
    (a.out / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "renders": report["renders"]}, indent=2))


if __name__ == "__main__":
    main()
