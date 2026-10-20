"""Plate furniture for Book VI, De Potestate et Accusatione.

The series' plate conventions as common/plot/plate.py keeps them for Graduum: an A4 plot sheet,
stroke-only, two layers (Art Paths, Text Outlines), two inks, a drawn reserved blank, the plate's
[F] sentence in the twelve-mark hand at a per-plate shift, and the frame drawn as a scale whose
ticks carry, in the biliteral cipher, the sentence that would count against the plate's claim.
Only the running title and the exported titles differ, so this module subclasses that Plate and
reuses its validator unchanged.

GRADUUM_READING=1 builds the serif reading edition (IM Fell English outlines) for the bound book;
without it the lettering is the EMS Nixish stroke face of the plot masters.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
sys.path.insert(0, os.path.join(REPO, "common", "geometry"))

import plate as base  # noqa: E402
from plate import W, H, FRAME, RESERVED, validate, png_preview  # noqa: E402,F401
from plotkit import INK, RED  # noqa: E402,F401

from plotkit import SVGFont, OutlineFont  # noqa: E402

FACES = (SVGFont(base.PLOT_FONT), OutlineFont(base.READING_FONT, tracking=0.02))
BOOK = "DE POTESTATE ET ACCUSATIONE"
TITLE = "De Potestate et Accusatione"

# The drawable field: inside the frame, below the head rule, above the strap rule.
ART = (12.0, 34.0, 198.0, 235.0)
# The reserved blank and its label, with a margin no drawn stroke may enter.
KEEP_OUT = (RESERVED[0] - 2.0, RESERVED[1] - 2.0, RESERVED[0] + RESERVED[2] + 2.0, RESERVED[1] + RESERVED[3] + 6.5)


def free(x, y, pad=0.0):
    """True where art may be drawn: inside ART and outside the reserved blank."""
    x0, y0, x1, y1 = ART
    if not (x0 + pad <= x <= x1 - pad and y0 + pad <= y <= y1 - pad):
        return False
    k0, l0, k1, l1 = KEEP_OUT
    return not (k0 - pad <= x <= k1 + pad and l0 - pad <= y <= l1 + pad)


def runs(pts, pad=0.0):
    """Split a polyline into the runs that lie in free space."""
    out, cur = [], []
    for p in pts:
        if free(p[0], p[1], pad):
            cur.append(p)
        else:
            if len(cur) > 1:
                out.append(cur)
            cur = []
    if len(cur) > 1:
        out.append(cur)
    return out


class VIPlate(base.Plate):
    """Graduum's Plate with Book VI's running title; everything else inherited."""

    def __init__(self, *a, data=None, **k):
        super().__init__(*a, **k)
        # "data" names the record a plate is drawn from, or None for a plate that carries none.
        self.meta["carries_data"] = bool(data)
        self.meta["data_source"] = data

    def label(self, text, x, y, cap, align="left", color="ink", hand=None):
        """lettering that refuses to leave the sheet's field, measured in both faces"""
        if "'" in text or "\u2019" in text:
            raise ValueError(f"Tabula {self.number}: the plot face has no apostrophe; rephrase {text!r}")
        for font in FACES:
            w = font.width(text, cap)
            x0 = {"left": x, "center": x - w / 2, "right": x - w}[align]
            if x0 < 11.5 or x0 + w > 198.5:
                raise ValueError(f"Tabula {self.number}: lettering runs off the field ({x0:.1f} to {x0 + w:.1f} mm): {text!r}")
        return super().label(text, x, y, cap, align, color, hand)

    def furniture(self, strap_y=245, reserved=True):
        h = self.text
        x0, y0, x1, y1 = base.FRAME
        h.straight([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "hair", "ink", closed=True)
        self.label(BOOK, W / 2, 20.5, 4.1, "center")
        self.label(self.subtitle, W / 2, 27, 2.5, "center")
        h.straight([(x0 + 4, 30.5), (x1 - 4, 30.5)], "hair", "ink")
        if reserved:
            rx, ry, rw, rh = base.RESERVED
            h.straight([(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)], "orn", "ink", closed=True)
            self.label("RESERVED", rx + rw / 2, ry + rh + 4.2, 2.5, "center")
        h.straight([(x0 + 4, 238), (x1 - 4, 238)], "hair", "ink")
        if self.strap:
            self.label(self.strap, W / 2, strap_y, 2.5, "center")
        h.straight([(x0 + 4, 268), (x1 - 4, 268)], "hair", "ink")
        self.label(f"TABULA {self.number}", W / 2, 275.5, 2.5, "center")
        self.label(self.title.upper().replace("'", "").replace("’", ""), W / 2, 281.5, 3.0, "center")

    def export(self, out_dir, extra=None):
        os.makedirs(out_dir, exist_ok=True)
        if extra:
            self.meta.update(extra)
        title = f"{TITLE} - Tabula {self.number} - {self.title}"
        desc = ("Stroke-only pen plot plate, 210 x 297 mm. Two layers (Art Paths, Text Outlines), two inks. "
                "Untested on a physical plotter. " + ("Drawn from " + self.meta["data_source"] + "."
                                                       if self.meta["carries_data"] else "Carries no data."))
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
        self.meta["strokes"] = {"all": len(doc.strokes()), "art": len(doc.strokes("art")), "text": len(doc.strokes("text"))}
        with open(os.path.join(out_dir, "build-meta.json"), "w") as f:
            json.dump(self.meta, f, indent=1)
        png_preview(os.path.join(out_dir, f"{stem}.svg"), os.path.join(out_dir, f"{stem}.png"))
        return self.meta
