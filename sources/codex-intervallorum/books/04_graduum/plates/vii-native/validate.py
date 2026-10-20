"""Structure, cipher and plot checks for the Tabula VII package. Run after tabula_vii.py."""
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
CAPTION_NORM = "THE CORD IS SOUND THE MOUNT WAS NEVER MADE"


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
        "vii-cord-without-a-mount.svg": (("Art Paths", "Text Outlines"), (INK, RED)),
        "vii-cord-without-a-mount-black-a4.svg": (("Art Paths", "Text Outlines"), (INK,)),
        "vii-cord-without-a-mount-red-a4.svg": (("Art Paths", "Text Outlines"), (RED,)),
        "vii-cord-without-a-mount-art-only.svg": (("Art Paths",), (INK, RED)),
        "vii-cord-without-a-mount-text-only.svg": (("Text Outlines",), (INK, RED)),
    }
    master = None
    for name, (layers, colors) in specs.items():
        r, s = check_structure(name, layers, colors)
        report[name] = r
        if name == "vii-cord-without-a-mount.svg":
            master = s
    # black + red sheets together equal the master's stroke multiset
    def dset(s):
        return collections.Counter(re.findall(r' d="([^"]+)"', s))
    b = dset(open(os.path.join(OUT, "vii-cord-without-a-mount-black-a4.svg")).read())
    rr = dset(open(os.path.join(OUT, "vii-cord-without-a-mount-red-a4.svg")).read())
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

    # cipher: decode the litany words recorded for the registers with the office-litany table
    import csv
    table = {}
    for r in csv.DictReader(open(os.path.join(HERE, "..", "..", "proofs", "x-xi-v-gpt", "office-litany.csv"), encoding="utf-8")):
        table[r["carrier_word"]] = " " if r["plaintext"] == "SPACE" else r["plaintext"]
    words = meta["litany_words"]
    dec = "".join(table[w] for w in words)
    report["litany_word_count"] = len(words)
    report["caption_round_trip"] = dec == CAPTION_NORM
    # and the words really are lettered on the text layer: every litany word appears in the type audit
    ta0 = json.load(open(os.path.join(OUT, "vii-cord-without-a-mount-type-audit.json")))
    lettered = [t["text"] for t in ta0["plate"]]
    report["litany_words_lettered"] = all(lettered.count(w) >= words.count(w) for w in set(words))

    # fourth carrier: independent decode from the frame ticks (red = 1)
    ticks = {}
    for m in re.finditer(r'<path fill="none" stroke="([^"]+)" stroke-width="[^"]+" data-tick="(\d+)"', master):
        ticks[int(m.group(2))] = 1 if m.group(1) == RED else 0
    bl = [ticks[i] for i in sorted(ticks)]
    sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "common", "plot"))
    import ornament
    report["hidden_marks"] = len(bl)
    report["hidden_decoded"] = ornament.decode(bl)
    report["hidden_round_trip"] = report["hidden_decoded"] == meta["hidden"]["message"]
    report["hidden_b_fraction"] = round(ornament.b_fraction(meta["hidden"]["message"]), 3)
    report["hidden_readable_from_black_pass"] = "as gaps"

    # type audit
    ta = json.load(open(os.path.join(OUT, "vii-cord-without-a-mount-type-audit.json")))
    report["minimum_cap_mm"] = ta["minimum_cap_mm"]
    report["typography_ok"] = ta["minimum_cap_mm"] >= 2.5

    report["all_passed"] = all(report[n]["passed"] for n in specs) and report["black_plus_red_equals_master"] \
        and report["within_page_with_8mm_margin"] and inside == 0 and report["caption_round_trip"] and report["litany_words_lettered"] and report["typography_ok"] and report["hidden_round_trip"]
    with open(os.path.join(OUT, "validation.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps({k: v for k, v in report.items() if not k.endswith(".svg")}, indent=1))
    for n in specs:
        print(n, "passed" if report[n]["passed"] else report[n])


if __name__ == "__main__":
    main()
