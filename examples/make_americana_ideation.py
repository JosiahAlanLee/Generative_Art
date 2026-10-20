#!/usr/bin/env python3
"""Original concept sketches for the Americana research; not historical replicas.

Only the small border carrier is implemented as an encoding. The historical
connections and larger generator proposals are in research/occult-americana.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.process_art.drawing import Plate, INK, RED  # noqa: E402


def encode(text):
    return np.unpackbits(np.frombuffer(text.encode("utf-8"), dtype=np.uint8)).reshape(-1, 8)


def decode(bits):
    return np.packbits(np.asarray(bits, dtype=np.uint8).reshape(-1, 8)).tobytes().decode("utf-8")


def carrier(p, text, x=25, y=166, width=120):
    """One byte per row, eight cells MSB first. Cross = 1; bar = 0.

    Columns/rows are explicit in the manifest; the carrier is not a historical
    cipher. The bit also has a distinct shape when inks are printed monochrome.
    """
    bits = encode(text)
    for row, byte in enumerate(bits):
        for col, bit in enumerate(byte):
            a, b = x+col*width/8, y+row*1.7
            if bit:
                p.add([(a, b), (a+1.4, b+1)], RED, .14)
                p.add([(a, b+1), (a+1.4, b)], RED, .14)
            else:
                p.add([(a, b+.5), (a+1.4, b+.5)], INK, .13)
    assert decode(bits) == text
    return bits.tolist()


def ellipse(p, cx, cy, rx, ry, color=INK, width=.14):
    t = np.linspace(0, 2*np.pi, 200)
    p.add(np.column_stack([cx+rx*np.cos(t), cy+ry*np.sin(t)]), color, width)


def flower(p, cx, cy, radius=9):
    t = np.linspace(0, 2*np.pi, 360)
    r = radius*(.66+.34*np.cos(6*t))
    p.add(np.column_stack([cx+r*np.cos(t), cy+r*np.sin(t)]), RED, .18)
    p.ring(cx, cy, radius*.22, width=.16)


def certificate():
    p = Plate("Punched fraktur — original ideation sketch")
    p.add([(17, 17), (153, 17), (153, 204), (17, 204), (17, 17)], width=.25)
    p.add([(21, 21), (149, 21), (149, 200), (21, 200), (21, 21)], RED, .11)
    for x, direction in ((35, 1), (135, -1)):
        t = np.linspace(0, 1, 150)
        stem = np.column_stack([x+direction*8*np.sin(t*3.7), 145-98*t])
        p.add(stem, width=.24)
        for k in range(1, 8):
            q = stem[k*17]
            side = 1 if k % 2 else -1
            end = q+[side*9, -5]
            v = end-q
            tt = np.linspace(0, 1, 50)
            normal = np.array([-v[1], v[0]])/np.linalg.norm(v)
            leaf = np.vstack([q+tt[:, None]*v+np.sin(tt*np.pi)[:, None]*normal*2.3,
                              (q+tt[:, None]*v-np.sin(tt*np.pi)[:, None]*normal*2.3)[::-1]])
            p.add(np.vstack([leaf, leaf[0]]), width=.12)
        flower(p, *stem[-1], 9)
    for y in (65, 77, 89, 115, 127, 139):
        p.add([(57, y), (113, y)], width=.11)
    # Reserved central name/claim field, surrounded by an original heart contour.
    t = np.linspace(0, 2*np.pi, 260)
    hx = 16*np.sin(t)**3
    hy = -(13*np.cos(t)-5*np.cos(2*t)-2*np.cos(3*t)-np.cos(4*t))
    p.add(np.column_stack([85+hx*.7, 103+hy*.7]), RED, .2)
    bits = carrier(p, "COPY THE QUESTION", y=165)
    return p, {"payload": "COPY THE QUESTION", "bits": bits, "status": "original form/carrier study; certificate fields intentionally blank"}


def county():
    p = Plate("A correction atlas for an unbuilt town — synthetic ideation")
    rng = np.random.default_rng(83)
    parcels = []
    for r in range(4):
        for c in range(3):
            x, y = 22+c*44, 26+r*30
            w, h = 25+rng.uniform(-3, 4), 18+rng.uniform(-2, 3)
            p.add([(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)], width=.23)
            material = int((r+c) % 2)
            for k in np.arange(2, w-1, 2.2):
                p.add([(x+k, y+2), (x+k, y+h-2)], RED if material else INK, .09)
            p.ring(x+w*.5, y+h*.5, 2, RED, .16)
            parcels.append({"id": r*3+c, "material_class": material, "water_access": (r+c)%3 != 0})
    # A correction slip changes the shape and class of one synthetic building.
    p.add([(101, 71), (148, 73), (147, 106), (100, 104), (101, 71)], RED, .22)
    p.add([(108, 80), (140, 80), (140, 98), (108, 98), (108, 80)], width=.2)
    for y in (23, 53, 83, 113, 143):
        p.add([(15, y), (155, y)], width=.1)
    for x in (17, 60, 104, 153):
        p.add([(x, 20), (x, 146)], width=.1)
    for x, y in ((40, 19), (82, 149), (151, 64)):
        p.ring(x, y, 3.5, RED, .18)
        p.add([(x-5, y), (x+5, y)], width=.1)
        p.add([(x, y-5), (x, y+5)], width=.1)
    bits = carrier(p, "LEGEND REVISED", y=165)
    return p, {"payload": "LEGEND REVISED", "bits": bits, "status": "fictional parcels and invented legend, not a Sanborn reproduction", "synthetic_parcels": parcels, "correction": "slip demonstrates a proposed revision layer; no historical town represented"}


def airship():
    p = Plate("Airship correction ledger — original invented machine")
    ellipse(p, 85, 63, 61, 24, width=.27)
    for x in np.linspace(32, 138, 12):
        q = np.sqrt(max(0, 1-((x-85)/61)**2))*24
        p.add([(x, 63-q), (x, 63+q)], width=.1)
    for i, x in enumerate((44, 64, 85, 106, 126)):
        ellipse(p, x, 63, 8, 18, RED if i % 2 else INK, .12)
    for x, target in ((42, 66), (65, 75), (105, 95), (128, 105)):
        anchor_y = 63+24*np.sqrt(1-((x-85)/61)**2)
        p.add([(x, anchor_y), (target, 112)], width=.17)
    p.add([(61, 112), (110, 112), (105, 126), (68, 126), (61, 112)], width=.25)
    p.add([(65, 116), (107, 116)], RED, .13)
    for x in (75, 96):
        p.ring(x, 121, 2.2, width=.15)
    p.add([(24, 63), (13, 48), (25, 51), (24, 63)], width=.18)
    p.add([(145, 64), (155, 55), (155, 72), (145, 64)], width=.18)
    # Index tabs and a revision card are documentary furniture, not deciphered notes.
    for i in range(3):
        x, y = 19+i*49, 136
        p.add([(x, y), (x+35, y), (x+35, y+16), (x, y+16), (x, y)], width=.13)
        p.add([(x+4, y+5), (x+30, y+5)], RED, .1)
        p.add([(x+4, y+10), (x+21, y+10)], width=.1)
    bits = carrier(p, "NO CLAIM OF FLIGHT", y=165)
    return p, {"payload": "NO CLAIM OF FLIGHT", "bits": bits, "status": "original airship form study; no lift or mechanical simulation", "sources_do_not_establish": "the Sonora Aero Club as a historical organization"}


def instrument():
    p = Plate("The witness instrument — original procedural reliquary")
    p.add([(35, 143), (35, 28), (135, 28), (135, 143)], width=.28)
    p.add([(28, 145), (142, 145)], width=.3)
    p.add([(45, 28), (45, 21), (125, 21), (125, 28)], RED, .18)
    for i, x in enumerate(np.linspace(47, 123, 9)):
        last = 45+((i*19)%70)
        p.add([(x, 28), (x, last)], width=.12)
        for y in np.arange(40, last, 6):
            p.ring(x, y, 1.1, RED if i % 3 == 0 else INK, .11)
        p.add([(x, last), (x-4, last+5), (x+4, last+5), (x, last)], RED, .15)
    for cx in (63, 107):
        p.ring(cx, 129, 8, width=.21)
        for a in np.linspace(0, 2*np.pi, 12, endpoint=False):
            p.add([(cx+5*np.cos(a), 129+5*np.sin(a)), (cx+7*np.cos(a), 129+7*np.sin(a))], width=.11)
    p.add([(35, 129), (55, 129)], width=.18)
    p.add([(115, 129), (135, 129)], width=.18)
    p.add([(71, 129), (99, 129)], RED, .2)
    p.add([(35, 143), (29, 151), (45, 151), (39, 143)], width=.21)
    p.add([(131, 143), (125, 151), (141, 151), (135, 143)], width=.21)
    bits = carrier(p, "RECEIPT IS NOT BELIEF", y=165)
    return p, {"payload": "RECEIPT IS NOT BELIEF", "bits": bits, "status": "original form study; no therapeutic or electrical function; not a machine replica"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT/"examples/previews/americana-ideation")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"status": "research sketches, not production generators or historical reconstructions", "carrier_rule": "UTF-8 bytes, rows in order, eight cells per row MSB first; cross=1, bar=0; no cryptographic security claimed", "items": []}
    sheet = Image.new("RGB", (1520, 555), "#e6e1d7")
    d = ImageDraw.Draw(sheet)
    for i, (name, fn) in enumerate((("Punched fraktur", certificate), ("Correction atlas", county), ("Airship ledger", airship), ("Witness instrument", instrument))):
        p, data = fn()
        assert decode(data["bits"]) == data["payload"]
        stem = ["punched-fraktur", "correction-atlas", "airship-ledger", "witness-instrument"][i]
        svg = p.svg()
        (args.out/(stem+".svg")).write_text(svg)
        p.png(args.out/(stem+".png"), 1400)
        manifest["items"].append({"name": name, "stem": stem, "stroke_count": len(p.strokes), "svg_sha256": hashlib.sha256(svg.encode()).hexdigest(), **data})
        im = Image.open(args.out/(stem+".png")).convert("RGB")
        im.thumbnail((365, 476), Image.Resampling.LANCZOS)
        sheet.paste(im, (i*380+(380-im.width)//2, 6))
        d.text((i*380+12, 497), name, font=ImageFont.load_default(size=18), fill="#161918")
        d.text((i*380+12, 527), "Original concept / carrier proof", font=ImageFont.load_default(size=13), fill="#5b554c")
    sheet.save(args.out/"contact-sheet.jpg", quality=87, optimize=True)
    manifest["code_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print("Four original concept sketches; four UTF-8 carrier round trips passed", flush=True)


if __name__ == "__main__":
    main()
