"""Run the imported culture generator on a synthetic ink drawing.

Use the Python environment from requirements-development-art.txt.
"""
import argparse
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=int, default=120)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--out", type=Path, default=ROOT / "examples/out/physarum-sample")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (160, 220), "#eee8d7")
    draw = ImageDraw.Draw(im)
    draw.ellipse((30, 20, 130, 160), outline="#344f56", width=8)
    draw.line([(30, 175), (80, 50), (130, 175)], fill="#344f56", width=9)
    draw.arc((53, 80, 107, 135), 0, 300, fill="#a32b24", width=6)
    draw.line((20, 190, 140, 190), fill="#344f56", width=5)
    source = args.out / "input.png"
    im.save(source)
    tool = ROOT / "sources/development-art/books/03_escalationum/physarum/physarum_plot.py"
    subprocess.run([sys.executable, str(tool), str(source), "-o", str(args.out / "cultures"),
                    "--grid", str(args.grid), "--steps", str(args.steps), "--seed", "17",
                    "--density", ".12", "--cultures", "slate:ochre", "--station", "3",
                    "--territories", "8", "--floor", "rust=.3",
                    "--palette", "paper=#eee8d7,ochre=#a8854a,slate=#344f56,rust=#a32b24",
                    "--styles", "topo,network,fibers,hatch,marks", "--width-mm", "90"], check=True)


if __name__ == "__main__":
    main()
