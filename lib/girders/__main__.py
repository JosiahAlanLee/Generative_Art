"""CLI: python -m lib.girders [generate|preview|validate] ..."""

import argparse
import sys

from .generate import generate, load_scene, save_scene
from .presets import PRESETS
from .preview import render
from .schema import validate


def main(argv=None):
    ap = argparse.ArgumentParser(prog="girders",
                                 description="Seeded block-and-girder megastructure scenes")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="write a girders-scene-1 file")
    g.add_argument("--preset", choices=sorted(PRESETS), default="dense-core")
    g.add_argument("--seed", type=int, default=1)
    g.add_argument("--scale", choices=("small", "medium", "large"), default="medium")
    g.add_argument("--out", required=True)
    g.add_argument("--validate", action="store_true")
    g.add_argument("--preview", help="also render a line drawing PNG here")

    p = sub.add_parser("preview", help="render a PNG line drawing of a scene")
    p.add_argument("scene", nargs="?")
    p.add_argument("--preset", choices=sorted(PRESETS), default="dense-core")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--scale", choices=("small", "medium", "large"), default="medium")
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=2200)

    v = sub.add_parser("validate", help="check a scene file against the schema")
    v.add_argument("scene")

    args = ap.parse_args(argv)
    if args.cmd == "generate":
        scene = generate(args.seed, args.preset, args.scale)
        if args.validate:
            errs = validate(scene)
            if errs:
                for e in errs[:20]:
                    print(f"INVALID: {e}", file=sys.stderr)
                return 2
            print("validator: OK")
        save_scene(scene, args.out)
        st = scene["stats"]
        print(f"wrote {args.out}: {st['blocks']} blocks, {st['beams']} beams, "
              f"{st['details']} details")
        if args.preview:
            render(scene, args.preview)
            print(f"wrote {args.preview}")
        return 0
    if args.cmd == "preview":
        scene = load_scene(args.scene) if args.scene else generate(args.seed, args.preset, args.scale)
        render(scene, args.out, width_px=args.width)
        print(f"wrote {args.out}")
        return 0
    if args.cmd == "validate":
        scene = load_scene(args.scene)
        errs = validate(scene)
        if errs:
            for e in errs[:20]:
                print(f"INVALID: {e}", file=sys.stderr)
            return 2
        st = scene["stats"]
        print(f"OK: {st['blocks']} blocks, {st['beams']} beams, {st['details']} details")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
