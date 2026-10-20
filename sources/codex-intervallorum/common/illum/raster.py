"""Raster figures for the illustrated edition.

The GPT figure renders (references/raster/, books/06_tarot/*/art/) are painted on a cream ground close to
the series paper. To sit them in the page rather than on it, each render is divided by its own
measured ground so the ground becomes white, eased to white near its border, and then laid on
the page in Multiply: the page's ground, washes and furniture show through wherever the figure
is light, and the figure's ink darkens what lies beneath it, as ink on paper does.

The red thread in the renders runs deeper and more saturated than the series ink #a32b24 by a
similar amount on every image (references/raster/batch-04/red-check.md). Pixels read as red are
pulled toward the ink by per-channel gain, weighted by how red they are. That is the
composition-time remap the red check proposed; the native renders are not modified.

Outputs are cached under build/illum-cache/ (gitignored) as JPEG at full native size, quality 86,
4:4:4 so the red thread keeps its edge.
"""
import hashlib
import json
import os

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(REPO, "build", "illum-cache")
VERSION = "illum-raster-6"

INK_RED = np.array([163.0, 43.0, 36.0])
RENDER_RED = np.array([151.0, 38.0, 26.0])      # median of the red-check medians across batches 04-07


def _ground(a):
    """the render's ground: the median of a 2 % border, all four sides"""
    h, w, _ = a.shape
    m = max(8, int(0.02 * min(h, w)))
    border = np.concatenate([a[:m].reshape(-1, 3), a[-m:].reshape(-1, 3), a[:, :m].reshape(-1, 3), a[:, -m:].reshape(-1, 3)])
    return np.median(border, axis=0)


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def key(src, white_point=0.972, feather=0.035, red=True, darken=1.0):
    """returns (path to keyed JPEG, metadata). darken < 1 deepens the figure's darks a little
    (a gamma on the keyed values) where a figure has to hold its own beside dense line work."""
    raw = open(src, "rb").read()
    h = hashlib.sha256(raw + json.dumps([VERSION, white_point, feather, red, darken]).encode()).hexdigest()[:16]
    os.makedirs(CACHE, exist_ok=True)
    stem = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(CACHE, f"{stem}-{h}.jpg")
    meta_path = out[:-4] + ".json"
    if os.path.exists(out) and os.path.exists(meta_path):
        return out, json.load(open(meta_path))

    remap_red = red
    img = Image.open(src).convert("RGB")
    a = np.asarray(img).astype(np.float64)
    g = _ground(a)
    k = a / g[None, None, :]
    # ease the ground to white: values above the white point go to 1, below it keep their tone
    lum = k.mean(axis=2, keepdims=True)
    lift = _smooth((lum - white_point) / (1.0 - white_point + 1e-6))
    k = k * (1 - lift) + 1.0 * lift
    k = np.clip(k, 0, 1)
    if darken != 1.0:
        k = k ** (1.0 / darken)

    if red:
        r, gg, b = a[..., 0], a[..., 1], a[..., 2]
        w = np.clip((r - np.maximum(gg, b) - 45.0) / 45.0, 0, 1)[..., None]
        gain = INK_RED / RENDER_RED
        k = k * (1 - w) + np.clip(k * gain[None, None, :], 0, 1) * w

    # feather the outer border to white so no render can show a rectangle
    hh, ww, _ = k.shape
    fy = _smooth(np.minimum(np.arange(hh), np.arange(hh)[::-1]) / (feather * hh))[:, None]
    fx = _smooth(np.minimum(np.arange(ww), np.arange(ww)[::-1]) / (feather * ww))[None, :]
    f = (fy * fx)[..., None]
    k = k * f + (1 - f)

    outimg = Image.fromarray((k * 255 + 0.5).astype(np.uint8))
    outimg.save(out, "JPEG", quality=86, subsampling=0, optimize=True)

    dark = (k.mean(axis=2) < 0.9)
    ys, xs = np.nonzero(dark)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else [0, 0, ww - 1, hh - 1]
    # where the render's red sits (the seal, the thread): the largest red cluster's centre
    r, gg, b = a[..., 0], a[..., 1], a[..., 2]
    redm = (r - np.maximum(gg, b) > 70) & (r > 110)
    red = None
    if redm.sum() > 30:
        small = Image.fromarray((redm * 255).astype(np.uint8)).resize((ww // 8, hh // 8), Image.BOX)
        sa = np.asarray(small).astype(float)
        sa = np.asarray(Image.fromarray(sa.astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(float)
        cy, cx = np.unravel_index(np.argmax(sa), sa.shape)
        ry, rx = np.nonzero(redm)
        red = {"peak_px": [int(cx * 8 + 4), int(cy * 8 + 4)], "count": int(redm.sum()),
               "bbox_px": [int(rx.min()), int(ry.min()), int(rx.max()), int(ry.max())]}
    meta = {"source": os.path.relpath(src, REPO), "source_sha256": hashlib.sha256(raw).hexdigest(),
            "ground_rgb": [round(float(x), 1) for x in g], "size": [ww, hh], "figure_bbox_px": bbox, "red": red,
            "white_point": white_point, "feather": feather, "red_remap": remap_red, "darken": darken, "version": VERSION}
    json.dump(meta, open(meta_path, "w"), indent=1)
    return out, meta


def silhouette(src, grow=0.012, soft=0.01, rgb=(237, 230, 212)):
    """a paper-coloured PNG with alpha = the figure's dilated shape. Drawn (normal blend) just
    before a figure, it clears line work the figure should stand in front of."""
    path, meta = key(src)
    h = hashlib.sha256((path + json.dumps([grow, soft, rgb])).encode()).hexdigest()[:12]
    out = path[:-4] + f"-sil-{h}.png"
    if os.path.exists(out):
        return out
    k = np.asarray(Image.open(path).convert("L")).astype(np.float64) / 255.0
    m = Image.fromarray(((k < 0.93) * 255).astype(np.uint8))
    n = max(3, int(grow * max(m.size)) | 1)
    m = m.filter(ImageFilter.MaxFilter(min(n, 61)))
    if n > 61:
        for _ in range(n // 61):
            m = m.filter(ImageFilter.MaxFilter(61))
    m = m.filter(ImageFilter.GaussianBlur(max(1, soft * max(m.size))))
    rgba = Image.new("RGBA", m.size, tuple(rgb) + (0,))
    rgba.putalpha(m)
    rgba.save(out)
    return out


def figure_box(meta, x, y, w, h):
    """where the figure's dark extent lands when the whole render is drawn at (x, y, w, h), PDF
    points, origin bottom-left. Returns (x0, y0, x1, y1)."""
    W, H = meta["size"]
    bx0, by0, bx1, by1 = meta["figure_bbox_px"]
    s = min(w / W, h / H)
    ox, oy = x + (w - W * s) / 2, y + (h - H * s) / 2
    return ox + bx0 * s, oy + (H - by1) * s, ox + bx1 * s, oy + (H - by0) * s


def place(c, src, x, y, w, h, anchor="center", knockout=False, **kw):
    """draw the keyed render inside (x, y, w, h) on a ReportLab canvas, preserving aspect,
    in Multiply. anchor: center | bottom | top. Returns the drawn rectangle."""
    path, meta = key(src, **kw)
    W, H = meta["size"]
    s = min(w / W, h / H)
    dw, dh = W * s, H * s
    dx = x + (w - dw) / 2
    dy = y + (h - dh) / 2 if anchor == "center" else (y if anchor == "bottom" else y + h - dh)
    if knockout:
        c.drawImage(silhouette(src), dx, dy, dw, dh, mask="auto")
    import figure_growth
    path, growth = figure_growth.appearance(c, path, meta, (dw, dh))
    meta = dict(meta, figure_growth=growth)
    c.saveState()
    c.setBlendMode("Screen" if getattr(c, "_figure_ground", "light") == "dark" else "Multiply")
    c.drawImage(path, dx, dy, dw, dh)
    c.restoreState()
    return dx, dy, dw, dh, meta


def place_fit_figure(c, src, x, y, w, h, anchor="bottom", knockout=False, **kw):
    """like place(), but scales so the figure's dark extent (not the whole render) fills the box.
    The render is clipped to the box's margins only by its own white ground, never cropped."""
    path, meta = key(src, **kw)
    W, H = meta["size"]
    bx0, by0, bx1, by1 = meta["figure_bbox_px"]
    fw, fh = bx1 - bx0 + 1, by1 - by0 + 1
    s = min(w / fw, h / fh)
    fx = x + (w - fw * s) / 2
    fy = y if anchor == "bottom" else (y + (h - fh * s) / 2 if anchor == "center" else y + h - fh * s)
    dx = fx - bx0 * s
    dy = fy - (H - 1 - by1) * s
    if knockout:
        c.drawImage(silhouette(src), dx, dy, W * s, H * s, mask="auto")
    import figure_growth
    path, growth = figure_growth.appearance(c, path, meta, (W*s, H*s))
    meta = dict(meta, figure_growth=growth)
    c.saveState()
    c.setBlendMode("Screen" if getattr(c, "_figure_ground", "light") == "dark" else "Multiply")
    c.drawImage(path, dx, dy, W * s, H * s)
    c.restoreState()
    return dx, dy, W * s, H * s, meta


def to_page(drawn, px):
    """map a pixel (x, y) of the render to page points, given place()'s return value"""
    dx, dy, dw, dh, meta = drawn
    W, H = meta["size"]
    return dx + px[0] / W * dw, dy + (H - px[1]) / H * dh


def figure_extent(drawn):
    """the drawn figure's dark extent on the page: (x0, y0, x1, y1)"""
    dx, dy, dw, dh, meta = drawn
    W, H = meta["size"]
    bx0, by0, bx1, by1 = meta["figure_bbox_px"]
    return dx + bx0 / W * dw, dy + (H - by1) / H * dh, dx + bx1 / W * dw, dy + (H - by0) / H * dh


def red_point(drawn):
    m = drawn[4]
    return to_page(drawn, m["red"]["peak_px"]) if m.get("red") else None


def mask_cells(src, cell=12, thresh=0.9, frac=0.04, **kw):
    """occupied cells of the keyed render: a list of (x0, y0, x1, y1) in render pixels, for
    building an avoidance shape in whatever coordinates the caller maps them into"""
    path, meta = key(src, **kw)
    k = np.asarray(Image.open(path).convert("L")).astype(np.float64) / 255.0
    dark = k < thresh
    H, W = dark.shape
    out = []
    for y in range(0, H, cell):
        for x in range(0, W, cell):
            if dark[y:y + cell, x:x + cell].mean() > frac:
                out.append((x, y, min(W, x + cell), min(H, y + cell)))
    return out, meta


class Slot:
    """a render placed in native plate millimetres (y down): its feet (or centre) at a point,
    scaled so a chosen extent has a chosen size. px -> mm through .mm(); the page placement is
    derived from a platekit Map at draw time."""

    def __init__(self, src, s=None, anchor_px=None, anchor_mm=None, height_mm=None, fit="figure", crop_px=None,
                 mirror=False, anchor="feet", **kw):
        """crop_px (x0, y0, x1, y1): use only that part of the render. mirror: flip left-right.
        anchor: 'feet' (bottom centre of the figure's extent) or 'centre'; or give anchor_px."""
        self.src, self.kw = src, kw
        self.path, self.meta = key(src, **kw)
        W, H = self.meta["size"]
        self.crop = crop_px
        self.mirror = mirror
        if crop_px:
            k = np.asarray(Image.open(self.path).convert("L")).astype(np.float64) / 255.0
            x0, y0, x1, y1 = crop_px
            sub = k[y0:y1, x0:x1] < 0.9
            ys, xs = np.nonzero(sub)
            self.bbox = [int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + x0, int(ys.max()) + y0]
        else:
            self.bbox = list(self.meta["figure_bbox_px"])
        bx0, by0, bx1, by1 = self.bbox
        if s is None:
            s = height_mm / (by1 - by0 + 1) if fit == "figure" else height_mm / H
        self.s = s
        if anchor_px is None:
            anchor_px = ((bx0 + bx1) / 2, by1) if anchor == "feet" else ((bx0 + bx1) / 2, (by0 + by1) / 2)
        self.ax, self.ay = anchor_px
        self.mx, self.my = anchor_mm

    def mm(self, px, py):
        dx = (px - self.ax) * self.s
        return self.mx + (-dx if self.mirror else dx), self.my + (py - self.ay) * self.s

    def extent_mm(self):
        bx0, by0, bx1, by1 = self.bbox
        (x0, y0), (x1, y1) = self.mm(bx0, by0), self.mm(bx1, by1)
        return min(x0, x1), y0, max(x0, x1), y1

    def red_mm(self):
        r = self.meta.get("red")
        return self.mm(*r["peak_px"]) if r else None

    def avoid(self, buffer=0.8):
        from shapely.geometry import box as sbox
        from shapely.ops import unary_union
        cells, _ = mask_cells(self.src, **self.kw)
        polys = []
        for (x0, y0, x1, y1) in cells:
            if self.crop and not (self.crop[0] <= x0 and x1 <= self.crop[2] and self.crop[1] <= y0 and y1 <= self.crop[3]):
                continue
            (a, b), (c, d) = self.mm(x0, y0), self.mm(x1, y1)
            polys.append(sbox(min(a, c), b, max(a, c), d))
        return unary_union(polys).buffer(buffer)

    def draw(self, c, M, knockout=False):
        """draw in Multiply through a platekit Map (y-down mm onto y-up points)"""
        W, H = self.meta["size"]
        X0, Y1 = M.P(*self.mm(0, 0))
        X1, Y0 = M.P(*self.mm(W, H))
        c.saveState()
        if self.crop:
            cx0, cy1 = M.P(*self.mm(self.crop[0], self.crop[1]))
            cx1, cy0 = M.P(*self.mm(self.crop[2], self.crop[3]))
            p = c.beginPath()
            p.rect(min(cx0, cx1), cy0, abs(cx1 - cx0), cy1 - cy0)
            c.clipPath(p, stroke=0, fill=0)
        if self.mirror:
            # X0 is the mapped left edge of the render's px 0, which lies to the right when mirrored
            c.translate(X0, 0)
            c.scale(-1, 1)
            X0, X1 = 0, X0 - X1
        w = X1 - X0
        if knockout:
            c.drawImage(silhouette(self.src), X0, Y0, w, Y1 - Y0, mask="auto")
        import figure_growth
        appearance, growth = figure_growth.appearance(c, self.path, self.meta, (w, Y1-Y0))
        self.meta = dict(self.meta, figure_growth=growth)
        c.setBlendMode("Screen" if getattr(c, "_figure_ground", "light") == "dark" else "Multiply")
        c.drawImage(appearance, X0, Y0, w, Y1 - Y0)
        c.restoreState()
        return self
