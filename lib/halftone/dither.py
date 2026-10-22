"""Error-diffusion and ordered dithering on grey arrays in [0, 1].

The kernel table follows the standard published filters (Floyd–Steinberg 1976;
Jarvis, Judice and Ninke 1976; Stucki 1981; Burkes 1988; Sierra 1989; Bill
Atkinson's 6/8 filter) and the row/column/2-D "diffusion" kernels that the
thi.ng ``pixel-dither`` package also ships. Each kernel is a list of
``(dx, dy, weight)`` taps relative to the current pixel plus a divisor.
Atkinson's divisor is deliberately larger than its weights' sum, so a quarter
of the error is dropped and highlights stay open.

Values are tones: 0 is black, 1 is white. ``levels`` quantises to that many
evenly spaced tones; 2 gives a bitmap. An optional ``bleed`` scales the error
carried forward (1 is full diffusion). Serpentine scanning reverses the
direction of every second row and mirrors the kernel horizontally.
"""
import numpy as np

try:  # numba is optional; the pure-Python loop is used when it is absent.
    from numba import njit
except ImportError:  # pragma: no cover
    def njit(*args, **kwargs):
        def wrap(f):
            return f
        return wrap(args[0]) if args and callable(args[0]) else wrap

KERNELS = {
    "floyd-steinberg": ([(1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)], 16),
    "jarvis-judice-ninke": ([(1, 0, 7), (2, 0, 5), (-2, 1, 3), (-1, 1, 5), (0, 1, 7), (1, 1, 5),
                             (2, 1, 3), (-2, 2, 1), (-1, 2, 3), (0, 2, 5), (1, 2, 3), (2, 2, 1)], 48),
    "stucki": ([(1, 0, 8), (2, 0, 4), (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2),
                (-2, 2, 1), (-1, 2, 2), (0, 2, 4), (1, 2, 2), (2, 2, 1)], 42),
    "burkes": ([(1, 0, 8), (2, 0, 4), (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2)], 32),
    "sierra": ([(1, 0, 5), (2, 0, 3), (-2, 1, 2), (-1, 1, 4), (0, 1, 5), (1, 1, 4), (2, 1, 2),
                (-1, 2, 2), (0, 2, 3), (1, 2, 2)], 32),
    "sierra-two-row": ([(1, 0, 4), (2, 0, 3), (-2, 1, 1), (-1, 1, 2), (0, 1, 3), (1, 1, 2), (2, 1, 1)], 16),
    "sierra-lite": ([(1, 0, 2), (-1, 1, 1), (0, 1, 1)], 4),
    "atkinson": ([(1, 0, 1), (2, 0, 1), (-1, 1, 1), (0, 1, 1), (1, 1, 1), (0, 2, 1)], 8),
    "diffusion-row": ([(1, 0, 1)], 1),
    "diffusion-column": ([(0, 1, 1)], 1),
    "diffusion-2d": ([(1, 0, 1), (0, 1, 1)], 2),
}


def _as_tone(image):
    z = np.asarray(image, dtype=float)
    if z.ndim != 2:
        raise ValueError("a 2-D grey array is required")
    if z.size and (z.min() < 0 or z.max() > 1):
        raise ValueError("tones must lie in [0, 1]")
    return z


@njit(cache=True)
def _diffuse(z, dx, dy, weight, steps, bleed, serpentine):
    h, w = z.shape
    out = np.empty_like(z)
    for y in range(h):
        reverse = serpentine and (y % 2 == 1)
        for i in range(w):
            x = w - 1 - i if reverse else i
            old = z[y, x]
            q = np.floor(old * steps + .5) / steps
            if q < 0.:
                q = 0.
            elif q > 1.:
                q = 1.
            out[y, x] = q
            err = (old - q) * bleed
            for k in range(dx.shape[0]):
                ox = -dx[k] if reverse else dx[k]
                xx = x + ox
                yy = y + dy[k]
                if 0 <= xx < w and 0 <= yy < h:
                    z[yy, xx] += err * weight[k]
    return out


def error_diffuse(image, kernel="floyd-steinberg", levels=2, bleed=1.0, serpentine=False):
    """Quantise ``image`` (tones in [0, 1]) to ``levels`` tones with error diffusion."""
    if levels < 2:
        raise ValueError("levels must be at least 2")
    if not 0 <= bleed <= 1:
        raise ValueError("bleed must lie in [0, 1]")
    taps, divisor = KERNELS[kernel] if isinstance(kernel, str) else kernel
    z = _as_tone(image).copy()
    dx = np.array([t[0] for t in taps], dtype=np.int64)
    dy = np.array([t[1] for t in taps], dtype=np.int64)
    weight = np.array([t[2] / divisor for t in taps], dtype=float)
    return _diffuse(z, dx, dy, weight, float(levels - 1), float(bleed), bool(serpentine))


def bayer(size=4):
    """Bayer threshold matrix of ``size`` × ``size`` (a power of two), values 0..size²−1."""
    if size < 1 or size & (size - 1):
        raise ValueError("size must be a power of two")
    m = np.zeros((1, 1), dtype=np.int64)
    while m.shape[0] < size:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return m


def ordered_dither(image, size=4, levels=2):
    """Quantise with a tiled Bayer matrix: the regular screen rather than diffused noise."""
    if levels < 2:
        raise ValueError("levels must be at least 2")
    z = _as_tone(image)
    n = size * size
    t = (bayer(size) + .5) / n           # thresholds strictly inside (0, 1)
    h, w = z.shape
    tile = np.tile(t, (h // size + 1, w // size + 1))[:h, :w]
    steps = levels - 1
    q = np.floor(z * steps + tile) / steps
    return np.clip(q, 0, 1)


def threshold(image, level=.5):
    """Plain cut at ``level``: 1 where the tone is lighter, else 0."""
    z = _as_tone(image)
    return (z > level).astype(float)


def masks(quantised, levels=2):
    """Split a quantised tone array into per-tone boolean masks, darkest first.

    Returns a list of ``levels - 1`` masks: the first covers the darkest tone,
    each following mask the next lighter tone. White is never returned.
    """
    q = np.asarray(quantised, dtype=float)
    steps = levels - 1
    index = np.rint(q * steps).astype(int)
    return [index == k for k in range(steps)]


def resample(image, width, height=None):
    """Box-average a tone array to ``width`` columns (keeping the aspect ratio)."""
    from PIL import Image
    z = _as_tone(image)
    h, w = z.shape
    height = height or max(1, round(h * width / w))
    im = Image.fromarray((z * 255).round().astype(np.uint8), mode="L")
    im = im.resize((int(width), int(height)), Image.Resampling.BOX)
    return np.asarray(im, dtype=float) / 255


def load_gray(path, width=None):
    """Read an image file as tones in [0, 1], optionally box-resampled to ``width`` columns."""
    from PIL import Image
    with Image.open(path) as im:
        g = im.convert("L")
        if width:
            g = g.resize((int(width), max(1, round(g.height * width / g.width))), Image.Resampling.BOX)
        return np.asarray(g, dtype=float) / 255


def specimen(width=240, height=300, seed=0):
    """A synthetic tone specimen: a lit sphere over a ramp, a soft disc and grain.

    It stands in for a scanned figure in the samplers and tests so that no
    third-party raster is bundled.
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width] / max(width, height)
    tone = .3 + .72 * (y / (height / max(width, height)))            # ramp: dark top, light bottom
    cx, cy, r = .5 * width / max(width, height), .36 * height / max(width, height), .22
    d = np.hypot(x - cx, y - cy)
    inside = d < r
    nz = np.sqrt(np.clip(r * r - (x - cx) ** 2 - (y - cy) ** 2, 0, None)) / r
    nx, ny = (x - cx) / r, (y - cy) / r
    light = np.array([-.45, -.6, .66])
    light /= np.linalg.norm(light)
    lambert = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
    sphere = .08 + .8 * lambert ** 1.4 + .25 * np.clip(lambert - .85, 0, None) / .15
    tone = np.where(inside, sphere, tone)
    soft = np.exp(-((x - .22 * width / max(width, height)) ** 2 + (y - .78 * height / max(width, height)) ** 2) / .012)
    tone -= .55 * soft
    grain = rng.normal(0, .035, tone.shape)
    grain = (grain + np.roll(grain, 1, 0) + np.roll(grain, 1, 1)) / 3
    return np.clip(tone + grain, 0, 1)
