#!/usr/bin/env python3
"""Caller-side CLI: build and render a girders scene with Blender 5.2."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_BLENDER = Path.home() / "dev/blender-5.2.3-linux-x64/blender"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("scene", type=Path)
    p.add_argument("--look", choices=("overcast", "low_sun", "night"),
                   default="low_sun")
    p.add_argument("--camera", default="auto",
                   help="camera_hints name, index, or auto")
    p.add_argument("--res", default="3840x2160", metavar="WIDTHxHEIGHT")
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--preview", action="store_true",
                   help="quarter-resolution, fast-sample proof")
    p.add_argument("--no-exr", action="store_true")
    p.add_argument("--blender", type=Path,
                   default=Path(os.environ.get("BLENDER", DEFAULT_BLENDER)))
    a = p.parse_args()

    if not a.scene.is_file():
        p.error(f"scene does not exist: {a.scene}")
    if not a.blender.is_file():
        p.error(f"Blender executable does not exist: {a.blender}")
    a.out.mkdir(parents=True, exist_ok=True)
    log_path = a.out / "blender.log"
    command = [
        str(a.blender), "-b", "--python", str(ROOT / "build.py"), "--",
        "--scene", str(a.scene.resolve()), "--out", str((a.out / "scene.blend").resolve()),
        "--stats-out", str((a.out / "build-stats.json").resolve()),
        "--render-look", a.look, "--camera", str(a.camera),
        "--res", a.res, "--samples", str(a.samples),
        "--out-dir", str(a.out.resolve()),
    ]
    if a.preview:
        command.append("--preview")
    if not a.no_exr:
        command.append("--exr")
    print(" ".join(command), flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
            log.write(line)
        code = proc.wait()
    if code:
        print(f"Blender failed with exit code {code}; log: {log_path}", file=sys.stderr)
        raise SystemExit(code)


if __name__ == "__main__":
    main()
