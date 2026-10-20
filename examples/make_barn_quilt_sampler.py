"""Build eight quilt families, a controlled support study, and SVG proof sheets.

Generation uses only the standard library. Pass --png to render proof PNGs
with optional CairoSVG and Pillow. No render dependencies are needed for SVG.
"""

from dataclasses import asdict, replace
from hashlib import sha256
from html import escape
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.barn_quilts import PATTERNS, QuiltSpec, render_fragment, render_svg


def sheet(items, title, subtitle, columns=4, cell=440):
    rows = (len(items)+columns-1)//columns
    margin, header, label = 42, 124, 66
    width, height = 2*margin+columns*cell, header+rows*(cell+label)+32
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#eee5d3"/>',
           '<g fill="#332e28" font-family="Georgia, serif">',
           f'<text x="{margin}" y="48" font-size="30">{escape(title)}</text>',
           f'<text x="{margin}" y="80" font-size="15">{escape(subtitle)}</text></g>']
    for i, (heading, description, spec) in enumerate(items):
        x, y = margin+(i % columns)*cell, header+(i//columns)*(cell+label)
        side = cell-22
        out.append(f'<g transform="translate({x} {y}) scale({side/1000})">'
                   f'{render_fragment(spec, id_prefix=f"sample-{i}")}</g>')
        out.append(f'<g fill="#332e28" font-family="Georgia, serif">'
                   f'<text x="{x}" y="{y+side+26}" font-size="18">{escape(heading)}</text>'
                   f'<text x="{x}" y="{y+side+48}" font-size="13">{escape(description)}</text></g>')
    return "".join(out)+"</svg>\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"examples/previews/barn-quilts")
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    palettes = ("barn-red", "dairy-blue", "prairie", "roadside", "harvest", "barn-red", "dairy-blue", "manuscript")
    materials = ("wood", "mdo", "wood", "aluminum", "wood", "steel", "mdo", "steel")
    records, items = [], []
    for i, name in enumerate(PATTERNS):
        spec = QuiltSpec(pattern=name, palette=palettes[i], material=materials[i], seed=23+i,
                         texture=.78, wear=.30 if i % 2 else .48, detail=4)
        filename = name+".svg"
        svg = render_svg(spec)
        (out/filename).write_text(svg, encoding="utf-8")
        records.append({"file":filename,"spec":asdict(spec),"sha256":sha256(svg.encode()).hexdigest()})
        items.append((name.replace("-", " ").title(), f'{spec.material.upper()}  /  {spec.palette}  /  seed {spec.seed}', spec))
    (out/"block-sampler.svg").write_text(sheet(items, "BARN QUILT / BLOCK STUDIES", 
        "Eight geometric families. Opaque exterior paint, subtle support relief, brushwork, and edge wear."), encoding="utf-8")
    base = QuiltSpec(pattern="ohio-star", palette="barn-red", seed=71, texture=.9, wear=.12, hardware=True)
    surfaces = []
    for wear, label in ((.12, "FRESH"), (.82, "WORN")):
        for material in ("wood", "mdo", "aluminum", "steel"):
            spec = replace(base, material=material, wear=wear)
            filename = f"surface-{material}-{label.lower()}.svg"
            svg = render_svg(spec)
            (out/filename).write_text(svg, encoding="utf-8")
            records.append({"file":filename,"spec":asdict(spec),"sha256":sha256(svg.encode()).hexdigest()})
            surfaces.append((f'{material.upper()} / {label}', f'Same block, colors, seed, scale; wear {wear:.2f}', spec))
    (out/"material-comparison.svg").write_text(sheet(surfaces, "BARN QUILT / PAINT AND SUPPORT", 
        "A controlled comparison: wood relief, smooth MDO, painted aluminum, and painted steel. No rust treatment."), encoding="utf-8")
    outline = replace(base, mode="outline", hardware=False)
    flat = replace(base, mode="flat", hardware=False)
    for filename, spec in (("ohio-star-outline.svg", outline), ("ohio-star-flat.svg", flat)):
        svg = render_svg(spec)
        (out/filename).write_text(svg, encoding="utf-8")
        records.append({"file":filename,"spec":asdict(spec),"sha256":sha256(svg.encode()).hexdigest()})
    (out/"manifest.json").write_text(json.dumps({"generator":"barn-quilts-v1", "samples":records}, indent=2)+"\n")
    if args.png:
        import cairosvg
        from PIL import Image, ImageDraw, ImageFont
        for filename in ("block-sampler", "material-comparison"):
            cairosvg.svg2png(url=str(out/(filename+".svg")), write_to=str(out/(filename+".png")), output_width=1844)
        # One compact deliverable shows every family and a larger material detail.
        top = Image.open(out/"block-sampler.png").convert("RGB")
        canvas = Image.new("RGB", (top.width, top.height+650), "#eee5d3")
        canvas.paste(top, (0, 0))
        draw = ImageDraw.Draw(canvas)
        fontpath = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
        font = ImageFont.truetype(fontpath, 23) if Path(fontpath).exists() else ImageFont.load_default()
        draw.text((42, top.height+24), "PAINT / SUPPORT DETAIL — same Ohio Star, seed 71, wear 0.82", font=font, fill="#332e28")
        for i, material in enumerate(("wood", "mdo", "aluminum", "steel")):
            file = out/f"surface-{material}-worn.svg"
            # Crop a corner at >2x scale so paint chips and support grain are visible.
            png = cairosvg.svg2png(url=str(file), output_width=1000, output_height=1000)
            import io
            panel = Image.open(io.BytesIO(png)).convert("RGB")
            crop = panel.crop((0,0,500,500)).resize((418,418), Image.Resampling.LANCZOS)
            x, y = 42+i*440, top.height+86
            canvas.paste(crop, (x,y))
            draw.text((x, y+436), material.upper(), font=font, fill="#332e28")
        canvas.save(out/"Barn_Quilt_Studies.png")
    print(f"Wrote {len(records)} standalone SVGs, two proof sheets, and a recipe manifest to {out}")


if __name__ == "__main__":
    main()
