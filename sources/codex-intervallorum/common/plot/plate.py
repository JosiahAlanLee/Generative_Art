"""Shared furniture for the Graduum plates: frame, title block, reserved blank, caption strip in
the twelve-mark hand at a per-plate shift, the fourth carrier, export, and a generic validator.
Plates V-VIII carry their own copies of this; I-IV and later use this module."""
import collections
import json
import math
import os
import random
import re
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "common", "geometry"))
import ornament  # noqa: E402
import tx  # noqa: E402
from plotkit import PlotDoc, PlotHand, SVGFont, OutlineFont, INK, RED  # noqa: E402

W, H = 210, 297
FRAME = (8, 10, 202, 288)
RESERVED = (17, 42, 40, 24)
READING = os.environ.get("GRADUUM_READING") == "1"     # the serif reading edition for the bound book
PLOT_FONT = os.path.join(REPO, "common", "fonts", "EMSNixish.svg")
READING_FONT = os.path.join(REPO, "common", "fonts", "IMFellEnglish-Regular.ttf")


def lettering():
    """(font, stem suffix): the plot edition letters in the EMS Nixish stroke face; the reading
    edition in IM Fell English outlines. Decided 17 Oct 2026: the bound book is the reading edition."""
    if READING:
        return OutlineFont(READING_FONT, tracking=0.02), "-reading"
    return SVGFont(PLOT_FONT), ""


class Plate:
    def __init__(self, number, title, subtitle, stem, caption, shift, hidden, seed, carrier="scale", strap=None):
        self.number, self.title, self.subtitle, self.stem = number, title, subtitle, stem
        self.caption, self.shift, self.hidden, self.seed, self.carrier = caption, shift, hidden, seed, carrier
        self.strap = strap
        self.rng = random.Random(seed)
        self.doc = PlotDoc(W, H)
        self.font, suffix = lettering()
        self.stem = stem + suffix
        self.reading = READING
        self.art = PlotHand(self.doc, self.rng, "art", amp=0.07)
        self.text = PlotHand(self.doc, random.Random(seed + 1), "text", amp=0.03)
        self.type_audit = []
        self.meta = {"plate": number, "title": title, "seed": seed, "reserved_blank_mm": RESERVED}

    # ---------------------------------------------------------------- text --
    def label(self, text, x, y, cap, align="left", color="ink", hand=None):
        h = hand or self.text
        x0, w = self.font.write(h, text, x, y, cap, align, color)
        self.type_audit.append({"text": text, "cap_height_mm": cap, "x": round(x0, 2), "y": y, "width": round(w, 2), "ink": color})
        return x0, w

    def furniture(self, strap_y=245, reserved=True):
        h = self.text
        x0, y0, x1, y1 = FRAME
        h.straight([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "hair", "ink", closed=True)
        self.label("CLAVICULA GRADUUM", W / 2, 20.5, 4.1, "center")
        self.label(self.subtitle, W / 2, 27, 2.5, "center")
        h.straight([(x0 + 4, 30.5), (x1 - 4, 30.5)], "hair", "ink")
        if reserved:
            rx, ry, rw, rh = RESERVED
            h.straight([(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)], "orn", "ink", closed=True)
            self.label("RESERVED", rx + rw / 2, ry + rh + 4.2, 2.5, "center")
        h.straight([(x0 + 4, 238), (x1 - 4, 238)], "hair", "ink")
        if self.strap:
            self.label(self.strap, W / 2, strap_y, 2.5, "center")
        h.straight([(x0 + 4, 268), (x1 - 4, 268)], "hair", "ink")
        self.label(f"TABULA {self.number}", W / 2, 275.5, 2.5, "center")
        self.label(self.title.upper().replace("'", ""), W / 2, 281.5, 3.0, "center")

    def caption_strip(self, y=252, s=2.7):
        """the caption in the twelve-mark hand, base marks advanced by the plate's shift"""
        h = self.text
        wdt = tx.width(self.caption, s)
        x = (W - wdt) / 2
        cx = x
        for wi, w in enumerate(tx.encode(self.caption)):
            if wi:
                cx += 0.55 * s
            for (b, t) in w:
                tx.mark(h, (b - 1 + self.shift) % 12 + 1, cx, y, s, "orn", "ink")
                tx.tally(h, t, cx, y, s, "ink")
                cx += tx.token_width(t, s)
        self.meta["caption"] = {"base_square_mm": s, "x": round(x, 2), "y": y, "width": round(wdt, 2), "shift": self.shift}
        self.meta["caption_normalized"] = " ".join(tx.normalize(self.caption))

    # ------------------------------------------------------- fourth carrier --
    def scale_carrier(self):
        n, total = ornament.scale_frame(self.text, FRAME, self.hidden, pitch=2.5, short=1.0, long=2.0, long_every=10,
                                        weight="orn" if self.reading else "hair")
        self.meta["hidden"] = {"carrier": "frame scale, clockwise from the top-left corner", "form": "ink: black a, red b",
                               "message": self.hidden, "carrier_marks": n, "ticks": total, "pitch_mm": 2.5, "decode": "ticks"}

    def mark_carrier(self, description, form, count, tag="bmark"):
        """for carriers drawn by the plate itself: the plate tags each b-form mark with data-<tag>="i"
        and reports the total mark count here"""
        self.meta["hidden"] = {"carrier": description, "form": form, "message": self.hidden,
                               "carrier_marks": len(ornament.bits(self.hidden)), "marks": count, "decode": "tags", "tag": tag}

    def bits(self):
        return ornament.bits(self.hidden)

    def tag_last(self, hand, tag, i):
        """tag the last stroke the hand drew as b-mark i"""
        L = hand.pdoc.layers[hand.layer]
        L[-1] = L[-1][:3] + (f' data-{tag}="{i}"',)

    # -------------------------------------------------------------- export --
    def export(self, out_dir, extra=None):
        os.makedirs(out_dir, exist_ok=True)
        if extra:
            self.meta.update(extra)
        title = f"Clavicula Graduum - Tabula {self.number} - {self.title}"
        desc = ("Stroke-only pen plot plate, 210 x 297 mm. Two layers (Art Paths, Text Outlines), two inks. "
                "Untested on a physical plotter.")
        doc, stem = self.doc, self.stem
        files = {
            f"{stem}.svg": doc.svg(("art", "text"), (INK, RED), title, desc),
            f"{stem}-black-a4.svg": doc.svg(("art", "text"), (INK,), title + " - black pass", desc),
            f"{stem}-red-a4.svg": doc.svg(("art", "text"), (RED,), title + " - red pass", desc),
            f"{stem}-art-only.svg": doc.svg(("art",), (INK, RED), title + " - art layer", desc),
            f"{stem}-text-only.svg": doc.svg(("text",), (INK, RED), title + " - text layer", desc),
        }
        for name, s in files.items():
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
                f.write(s)
        with open(os.path.join(out_dir, f"{stem}-type-audit.json"), "w") as f:
            json.dump({"plate": self.type_audit, "minimum_cap_mm": min(t["cap_height_mm"] for t in self.type_audit),
                       "cipher_base_square_mm": self.meta["caption"]["base_square_mm"]}, f, indent=1)
        self.meta["stem"] = stem
        self.meta["reading_edition"] = self.reading
        with open(os.path.join(out_dir, "build-meta.json"), "w") as f:
            json.dump(self.meta, f, indent=1)
        png_preview(os.path.join(out_dir, f"{stem}.svg"), os.path.join(out_dir, f"{stem}.png"))
        print("strokes:", len(doc.strokes()), "art:", len(doc.strokes("art")), "text:", len(doc.strokes("text")))
        return self.meta


PAPER = "#ede6d4"     # the series ground for previews; the plot itself is on whatever paper is loaded


def png_preview(svg_path, png_path, width=1400):
    """an opaque preview; transparent corners made the plates vanish on dark interfaces"""
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=width, background_color=PAPER)
    except ImportError:
        pass


# ------------------------------------------------------------------ validate --

def _paths(svg):
    return re.findall(r"<path ([^>]*)/>", svg)


def _pts(d):
    n = [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]
    return list(zip(n[0::2], n[1::2]))


def _structure(path, want_layers, want_colors):
    s = open(path, encoding="utf-8").read()
    r = {"text_elements": s.count("<text"), "raster": s.count("<image"),
         "gradient_mask_clip": s.count("Gradient") + s.count("<mask") + s.count("clipPath"),
         "fills": dict(collections.Counter(re.findall(r'fill="([^"]+)"', s))),
         "strokes": dict(collections.Counter(re.findall(r'stroke="([^"]+)"', s))),
         "layers": re.findall(r'inkscape:label="([^"]+)"', s),
         "page": re.search(r'width="([^"]+)" height="([^"]+)" viewBox="([^"]+)"', s).groups()}
    r["passed"] = (r["text_elements"] == 0 and r["raster"] == 0 and r["gradient_mask_clip"] == 0
                   and set(r["fills"]) == {"none"} and set(r["strokes"]) <= set(want_colors)
                   and r["layers"] == list(want_layers) and r["page"] == ("210mm", "297mm", "0 0 210 297"))
    return r, s


def validate(out_dir):
    meta = json.load(open(os.path.join(out_dir, "build-meta.json")))
    stem = meta["stem"]
    report = {"physical_plotter_tested": False}
    specs = {f"{stem}.svg": (("Art Paths", "Text Outlines"), (INK, RED)),
             f"{stem}-black-a4.svg": (("Art Paths", "Text Outlines"), (INK,)),
             f"{stem}-red-a4.svg": (("Art Paths", "Text Outlines"), (RED,)),
             f"{stem}-art-only.svg": (("Art Paths",), (INK, RED)),
             f"{stem}-text-only.svg": (("Text Outlines",), (INK, RED))}
    master = None
    for name, (layers, colors) in specs.items():
        r, s = _structure(os.path.join(out_dir, name), layers, colors)
        report[name] = r
        if name == f"{stem}.svg":
            master = s
    dset = lambda s: collections.Counter(re.findall(r' d="([^"]+)"', s))
    b = dset(open(os.path.join(out_dir, f"{stem}-black-a4.svg")).read())
    rr = dset(open(os.path.join(out_dir, f"{stem}-red-a4.svg")).read())
    report["black_plus_red_equals_master"] = (b + rr) == dset(master)
    allp = [_pts(d) for d in re.findall(r' d="([^"]+)"', master)]
    xs = [x for p in allp for x, _ in p]
    ys = [y for p in allp for _, y in p]
    report["extent_mm"] = [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
    report["within_page_with_8mm_margin"] = min(xs) >= 8 and min(ys) >= 10 and max(xs) <= 202 and max(ys) <= 288
    rx, ry, rw, rh = meta["reserved_blank_mm"]
    inside = sum(1 for p in allp if all(rx + 0.5 < x < rx + rw - 0.5 and ry + 0.5 < y < ry + rh - 0.5 for x, y in p))
    report["paths_inside_reserved_blank"] = inside
    report["stroke_count"] = len(allp)
    report["pen_down_length_m"] = round(sum(math.dist(p[i], p[i + 1]) for p in allp for i in range(len(p) - 1)) / 1000, 2)
    report["shortest_segment_mm"] = round(min(math.dist(p[i], p[i + 1]) for p in allp for i in range(len(p) - 1) if math.dist(p[i], p[i + 1]) > 0), 3)
    # caption: round trip through the shift, and what the strip reads without the key
    L = {ch: (i % 12 + 1, i // 12 + 1) for i, ch in enumerate(string.ascii_uppercase)}
    inv = {v: k for k, v in L.items()}
    cap = meta["caption_normalized"]
    words = [[tuple(int(v) for v in tok.split(":")) for tok in w.split()] for w in tx.codes(cap).split(" / ")]
    shift = meta["caption"]["shift"]
    drawn = [[((b_ - 1 + shift) % 12 + 1, t) for (b_, t) in w] for w in words]
    back = [[((b_ - 1 - shift) % 12 + 1, t) for (b_, t) in w] for w in drawn]
    report["caption_round_trip"] = " ".join("".join(inv[t] for t in w) for w in back) == cap
    report["caption_shift"] = shift
    report["caption_without_key"] = " ".join("".join(inv.get(t, "?") for t in w) for w in drawn)
    # fourth carrier
    hd = meta["hidden"]
    if hd["decode"] == "ticks":
        ticks = {int(m.group(2)): (1 if m.group(1) == RED else 0)
                 for m in re.finditer(r'<path fill="none" stroke="([^"]+)" stroke-width="[^"]+" data-tick="(\d+)"', master)}
        bl = [ticks[i] for i in sorted(ticks)]
        report["hidden_readable_from_black_pass"] = "as gaps"
    else:
        tagged = set(int(m) for m in re.findall(r' data-' + hd["tag"] + r'="(\d+)"', master))
        bl = [1 if i in tagged else 0 for i in range(hd["marks"])]
        report["hidden_readable_from_black_pass"] = True
    report["hidden_marks"] = len(bl)
    report["hidden_decoded"] = ornament.decode(bl)
    report["hidden_round_trip"] = report["hidden_decoded"] == hd["message"]
    report["hidden_b_fraction"] = round(ornament.b_fraction(hd["message"]), 3)
    ta = json.load(open(os.path.join(out_dir, f"{stem}-type-audit.json")))
    report["minimum_cap_mm"] = ta["minimum_cap_mm"]
    report["cipher_base_square_mm"] = ta["cipher_base_square_mm"]
    report["typography_ok"] = ta["minimum_cap_mm"] >= 2.5 and ta["cipher_base_square_mm"] >= 2.6
    if meta.get("reading_edition"):
        # filled serif lettering is not plottable; structure checks are for the plot edition
        report["reading_edition"] = True
        report["all_passed"] = (report["within_page_with_8mm_margin"] and inside == 0 and report["caption_round_trip"]
                                and report["hidden_round_trip"])
    else:
        report["all_passed"] = (all(report[n]["passed"] for n in specs) and report["black_plus_red_equals_master"]
                                and report["within_page_with_8mm_margin"] and inside == 0 and report["caption_round_trip"]
                                and report["hidden_round_trip"] and report["typography_ok"])
    with open(os.path.join(out_dir, "validation.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps({k: v for k, v in report.items() if not k.endswith(".svg")}, indent=1))
    for n in specs:
        print(n, "passed" if report[n]["passed"] else report[n])
    return report


if __name__ == "__main__":
    validate(sys.argv[1])
