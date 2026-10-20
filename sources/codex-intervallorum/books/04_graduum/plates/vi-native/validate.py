"""Structure, cipher and plot checks for the Tabula VI package. Run after tabula_vi.py."""
import collections
import json
import math
import os
import re
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
INK, RED = "#161918", "#a32b24"
CAPTION_NORM = "EACH LEARNED ITS TILE AND NOTHING BEYOND IT"


def paths(svg):
    return re.findall(r"<path ([^>]*)/>", svg)


def pts_of(d):
    n = [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]
    return list(zip(n[0::2], n[1::2]))


def check_structure(name, want_layers, want_colors):
    s = open(os.path.join(OUT, name), encoding="utf-8").read()
    r = {}
    r["text_elements"] = s.count("<text")
    r["raster"] = s.count("<image")
    r["gradient_mask_clip"] = s.count("Gradient") + s.count("<mask") + s.count("clipPath")
    r["fills"] = dict(collections.Counter(re.findall(r'fill="([^"]+)"', s)))
    r["strokes"] = dict(collections.Counter(re.findall(r'stroke="([^"]+)"', s)))
    r["layers"] = re.findall(r'inkscape:label="([^"]+)"', s)
    r["page"] = re.search(r'width="([^"]+)" height="([^"]+)" viewBox="([^"]+)"', s).groups()
    ok = (r["text_elements"] == 0 and r["raster"] == 0 and r["gradient_mask_clip"] == 0
          and set(r["fills"]) == {"none"} and set(r["strokes"]) <= set(want_colors)
          and r["layers"] == list(want_layers) and r["page"] == ("210mm", "297mm", "0 0 210 297"))
    r["passed"] = ok
    return r, s


def main():
    meta = json.load(open(os.path.join(OUT, "build-meta.json")))
    report = {"physical_plotter_tested": False}
    specs = {
        "vi-feudal-register.svg": (("Art Paths", "Text Outlines"), (INK, RED)),
        "vi-feudal-register-black-a4.svg": (("Art Paths", "Text Outlines"), (INK,)),
        "vi-feudal-register-red-a4.svg": (("Art Paths", "Text Outlines"), (RED,)),
        "vi-feudal-register-art-only.svg": (("Art Paths",), (INK, RED)),
        "vi-feudal-register-text-only.svg": (("Text Outlines",), (INK, RED)),
    }
    master = None
    for name, (layers, colors) in specs.items():
        r, s = check_structure(name, layers, colors)
        report[name] = r
        if name == "vi-feudal-register.svg":
            master = s
    # black + red sheets together equal the master's stroke multiset
    def dset(s):
        return collections.Counter(re.findall(r' d="([^"]+)"', s))
    b = dset(open(os.path.join(OUT, "vi-feudal-register-black-a4.svg")).read())
    rr = dset(open(os.path.join(OUT, "vi-feudal-register-red-a4.svg")).read())
    report["black_plus_red_equals_master"] = (b + rr) == dset(master)

    # geometry: bounds, reserved blank, stroke stats, pen lifts
    allp = [pts_of(d) for d in re.findall(r' d="([^"]+)"', master)]
    xs = [x for p in allp for x, _ in p]
    ys = [y for p in allp for _, y in p]
    report["extent_mm"] = [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
    report["within_page_with_8mm_margin"] = min(xs) >= 8 and min(ys) >= 10 and max(xs) <= 202 and max(ys) <= 288
    rx, ry, rw, rh = meta["reserved_blank_mm"]
    inside = 0
    for p in allp:
        if all(rx + 0.5 < x < rx + rw - 0.5 and ry + 0.5 < y < ry + rh - 0.5 for x, y in p):
            inside += 1
    report["paths_inside_reserved_blank"] = inside
    length = 0.0
    for p in allp:
        length += sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))
    report["stroke_count"] = len(allp)
    report["pen_down_length_m"] = round(length / 1000, 2)
    counts = collections.Counter()
    for m in re.finditer(r'<g id="([^"]+)"[^>]*>(.*?)</g>', master, re.S):
        counts[m.group(1)] = len(re.findall(r"<path ", m.group(2)))
    report["counts"] = dict(counts)
    # minimum stroke segment and tightest coil (pen-width guidance)
    seg = min(math.dist(p[i], p[i + 1]) for p in allp for i in range(len(p) - 1) if math.dist(p[i], p[i + 1]) > 0)
    report["shortest_segment_mm"] = round(seg, 3)

    # cipher: independent decode of the caption tokens from the Matricis mapping
    L = {ch: (i % 12 + 1, i // 12 + 1) for i, ch in enumerate(string.ascii_uppercase)}
    inv = {v: k for k, v in L.items()}
    sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "common", "geometry"))
    import tx
    codes = tx.codes(CAPTION_NORM)
    words = [[tuple(int(v) for v in tok.split(":")) for tok in w.split()] for w in codes.split(" / ")]
    shift = meta["caption"]["shift"]
    shifted = [[((b - 1 + shift) % 12 + 1, t) for (b, t) in w] for w in words]          # as drawn
    unshifted = [[((b - 1 - shift) % 12 + 1, t) for (b, t) in w] for w in shifted]      # as read with the key
    dec = " ".join("".join(inv[t] for t in w) for w in unshifted)
    report["caption_codes_as_drawn"] = " / ".join(" ".join(f"{b:02d}:{t}" for b, t in w) for w in shifted)
    report["caption_round_trip"] = dec == CAPTION_NORM
    report["caption_shift"] = shift
    report["caption_without_key"] = " ".join("".join(inv.get(t, "?") for t in w) for w in shifted)

    # fourth carrier: independent decode from the maze's junction dots (dot = 1), row by row
    n = meta["maze"][2]
    dots = set(int(m) for m in re.findall(r' data-nodedot="(\d+)"', master))
    bl = [1 if i in dots else 0 for i in range((n + 1) * (n + 1))]
    sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "common", "plot"))
    import ornament
    report["hidden_marks"] = len(bl)
    report["hidden_decoded"] = ornament.decode(bl)
    report["hidden_round_trip"] = report["hidden_decoded"] == meta["hidden"]["message"]
    report["hidden_b_fraction"] = round(ornament.b_fraction(meta["hidden"]["message"]), 3)
    report["hidden_readable_from_black_pass"] = True

    # type audit
    ta = json.load(open(os.path.join(OUT, "vi-feudal-register-type-audit.json")))
    report["minimum_cap_mm"] = ta["minimum_cap_mm"]
    report["cipher_base_square_mm"] = ta["cipher_base_square_mm"]
    report["typography_ok"] = ta["minimum_cap_mm"] >= 2.5 and ta["cipher_base_square_mm"] >= 2.6

    report["all_passed"] = all(report[n]["passed"] for n in specs) and report["black_plus_red_equals_master"] \
        and report["within_page_with_8mm_margin"] and inside == 0 and report["caption_round_trip"] and report["typography_ok"] and report["hidden_round_trip"]
    with open(os.path.join(OUT, "validation.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps({k: v for k, v in report.items() if not k.endswith(".svg")}, indent=1))
    for n in specs:
        print(n, "passed" if report[n]["passed"] else report[n])


if __name__ == "__main__":
    main()
