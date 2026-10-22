"""Turn a bitmap into hairline runs for a pen, after thi.ng's ``geom-trace-bitmap``.

The mask's set pixels are consumed in the order of ``directions``: horizontal
runs first, then vertical, then the two diagonals, then whatever is left as
single points. Each run becomes one straight segment between pixel centres
and the pixels it covers are cleared, so a later direction only sees the
remainder. This is not contour tracing: a solid block becomes parallel runs,
and a dithered image becomes a field of short dashes whose directions follow
the dither's structure. Coordinates are pixel centres ``(column, row)``; use
``to_mm`` to place the result on a plate.
"""
import numpy as np

DIRECTIONS = ("h", "v", "d1", "d2", "p")


def _runs(line):
    """Start and end (exclusive) indices of the True runs in a 1-D boolean array."""
    padded = np.concatenate(([0], line.astype(np.int8), [0]))
    d = np.diff(padded)
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def _split(start, end, min_len, max_len):
    """Split one run into chunks of at most ``max_len`` pixels, dropping short tails."""
    chunks = []
    a = start
    while a < end:
        b = end if max_len is None else min(end, a + max_len)
        if b - a >= min_len:
            chunks.append((a, b))
        a = b
    return chunks


def trace_runs(mask, directions=DIRECTIONS, min_len=2, max_len=None):
    """Consume ``mask`` into segments and leftover points.

    Returns ``{"segments": [((x0, y0), (x1, y1)), ...], "points": (M, 2) array,
    "remaining": bool array}``. ``remaining`` is what no direction consumed
    (only non-empty when ``"p"`` is not requested). Pixels are consumed at most
    once; the union of segments' pixels and points equals the consumed set.
    """
    m = np.array(mask, dtype=bool, copy=True)
    if m.ndim != 2:
        raise ValueError("a 2-D boolean mask is required")
    if min_len < 1:
        raise ValueError("min_len must be at least 1")
    h, w = m.shape
    segments = []
    points = np.zeros((0, 2), dtype=int)
    for direction in directions:
        if direction == "h":
            for y in range(h):
                starts, ends = _runs(m[y])
                for s, e in zip(starts, ends):
                    for a, b in _split(s, e, min_len, max_len):
                        segments.append(((a, y), (b - 1, y)))
                        m[y, a:b] = False
        elif direction == "v":
            for x in range(w):
                starts, ends = _runs(m[:, x])
                for s, e in zip(starts, ends):
                    for a, b in _split(s, e, min_len, max_len):
                        segments.append(((x, a), (x, b - 1)))
                        m[a:b, x] = False
        elif direction in ("d1", "d2"):
            # d2 runs down and to the right (x grows with y); d1 down and to the left.
            view = m if direction == "d2" else m[:, ::-1]
            for k in range(-(h - 1), w):
                diag = np.diagonal(view, offset=k)
                if not diag.any():
                    continue
                starts, ends = _runs(diag)
                for s, e in zip(starts, ends):
                    for a, b in _split(s, e, min_len, max_len):
                        rows = np.arange(a, b) + max(0, -k)
                        cols = rows + k
                        view[rows, cols] = False
                        if direction == "d1":
                            cols = w - 1 - cols
                        segments.append(((int(cols[0]), int(rows[0])), (int(cols[-1]), int(rows[-1]))))
        elif direction == "p":
            ys, xs = np.nonzero(m)
            points = np.column_stack([xs, ys])
            m[:] = False
        else:
            raise ValueError(f"unknown direction {direction!r}")
    return {"segments": segments, "points": points, "remaining": m}


def to_mm(traced, cell, origin=(0, 0), flip_y=False, height_px=None):
    """Scale pixel-centre coordinates to millimetres: ``origin + (p + 0.5) * cell``.

    With ``flip_y`` the image's rows run upward from ``origin``; ``height_px``
    is then required.
    """
    origin = np.asarray(origin, dtype=float)

    def place(p):
        p = np.asarray(p, dtype=float) + .5
        if flip_y:
            p[..., 1] = height_px - p[..., 1]
        return origin + p * cell

    segments = [np.vstack([place(a), place(b)]) for a, b in traced["segments"]]
    points = place(traced["points"]) if len(traced["points"]) else np.zeros((0, 2))
    return segments, points


def pixel_counts(traced):
    """Pixels covered by segments and by points, for coverage checks."""
    covered = 0
    for (x0, y0), (x1, y1) in traced["segments"]:
        covered += max(abs(x1 - x0), abs(y1 - y0)) + 1
    return covered, len(traced["points"])
