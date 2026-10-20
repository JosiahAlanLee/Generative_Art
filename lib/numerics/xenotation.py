"""Tic Xenotation: integers written as nested prime tallies, drawn as glyphs.

Rules, as summarized at https://word.site/2019/11/11/nullary/ after Nick
Land's essays "The Tic Xenotation" and "TX2":

    ':'    is 2
    'xy'   is x times y            (writing terms side by side multiplies)
    '(x)'  is the x-th prime       (2 is the 1st prime, 3 the 2nd, 5 the 3rd)

So 3 = (:), 4 = ::, 5 = ((:)), 6 = :(:), 7 = (::), 11 = (((:))). Strict TX
has no mark for 1. The "nullary" variant described on the same page takes the
empty string as 1, which makes () = 2 and removes the special tic. Term order
does not change a value; encode() writes smallest factors first unless asked
for order="descending" (the canonical nullary form puts the largest first).

Unrelated to the book's common/geometry/tx.py, which is the twelve-sign
transcription hand.

The glyph functions turn a string into stroke-only polylines: each tic is a
vertical stroke and each bracket pair an enclosure, either a closed capsule or
a pair of open arcs. draw() sends them through any object with the book's
Hand.stroke(points, weight, color, closed=...) signature (marks.Hand,
plotkit.PlotHand); to_svg() writes a standalone stroke-only SVG in millimetres.

Standard library only. Usable as a script:
    python lib/numerics/xenotation.py 360
    python lib/numerics/xenotation.py 360 --svg out.svg
"""
from bisect import bisect_right
import math

__all__ = ["PRIME_LIMIT", "nth_prime", "prime_index", "factorize", "encode", "decode",
           "stats", "layout", "draw", "to_svg"]

PRIME_LIMIT = 20_000_000   # largest prime this module will sieve to
_primes = [2, 3, 5, 7, 11, 13]
_sieved_to = 13


def _sieve(limit):
    global _primes, _sieved_to
    if limit <= _sieved_to:
        return
    if limit > PRIME_LIMIT:
        raise ValueError(f"needs primes beyond {PRIME_LIMIT:,}; raise xenotation.PRIME_LIMIT deliberately")
    flags = bytearray([1]) * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for i in range(2, math.isqrt(limit) + 1):
        if flags[i]:
            flags[i * i::i] = bytes(len(range(i * i, limit + 1, i)))
    _primes = [i for i, f in enumerate(flags) if f]
    _sieved_to = limit


def nth_prime(k):
    """The k-th prime, counting 2 as the 1st."""
    k = int(k)
    if k < 1:
        raise ValueError("prime positions start at 1")
    if len(_primes) < k:
        # Rosser: the k-th prime is below k(ln k + ln ln k) for k >= 6.
        bound = int(k * (math.log(k) + math.log(math.log(k)))) + 1
        if bound > PRIME_LIMIT:
            raise ValueError(f"the {k:,}-th prime may exceed {PRIME_LIMIT:,}; raise xenotation.PRIME_LIMIT deliberately")
        _sieve(bound)
    return _primes[k - 1]


def prime_index(p):
    """Position of the prime p in the sequence 2, 3, 5, ... (2 -> 1)."""
    p = int(p)
    _sieve(max(p, 16))
    i = bisect_right(_primes, p)
    if i == 0 or _primes[i - 1] != p:
        raise ValueError(f"{p} is not prime")
    return i


def factorize(n):
    """Prime factors of n >= 1 with multiplicity, ascending."""
    n = int(n)
    if n < 1:
        raise ValueError("factorize needs n >= 1")
    out, d = [], 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        out.append(n)
    return out


def encode(n, mode="tx", order="ascending"):
    """Xenotate n. mode: 'tx' (from 2) or 'nullary' (from 1); order of factors."""
    n = int(n)
    if mode not in ("tx", "nullary"):
        raise ValueError("mode is 'tx' or 'nullary'")
    if order not in ("ascending", "descending"):
        raise ValueError("order is 'ascending' or 'descending'")
    if n == 1 and mode == "nullary":
        return ""
    if n < 2:
        raise ValueError("strict TX writes integers from 2 upward; mode='nullary' also writes 1")
    factors = factorize(n)
    if order == "descending":
        factors.reverse()
    return "".join(":" if p == 2 and mode == "tx" else "(" + encode(prime_index(p), mode, order) + ")"
                   for p in factors)


def _parse(s, i, mode):
    value, terms = 1, 0
    while i < len(s) and s[i] != ")":
        if s[i] == ":":
            value *= 2
            i += 1
        elif s[i] == "(":
            inner, i = _parse(s, i + 1, mode)
            if i >= len(s) or s[i] != ")":
                raise ValueError("unclosed '('")
            value *= nth_prime(inner)
            i += 1
        else:
            raise ValueError(f"unexpected {s[i]!r}; TX uses only ':', '(' and ')'")
        terms += 1
    if terms == 0 and mode == "tx":
        raise ValueError("an empty expression has no value in strict TX; use mode='nullary'")
    return value, i


def decode(s, mode="tx"):
    """Value of a xenotation string. Whitespace is ignored; ':' is 2 in either mode."""
    if mode not in ("tx", "nullary"):
        raise ValueError("mode is 'tx' or 'nullary'")
    s = "".join(s.split())
    value, i = _parse(s, 0, mode)
    if i != len(s):
        raise ValueError("unmatched ')'")
    return value


def stats(s):
    """Counts that are handy as visual parameters: tics, enclosures, nesting depth."""
    depth = deepest = 0
    for c in s:
        if c == "(":
            depth += 1
            deepest = max(deepest, depth)
        elif c == ")":
            depth -= 1
    return {"tics": s.count(":"), "enclosures": s.count("("), "depth": deepest}


def _arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _measure(s, i, tic, gap, pad, r_min):
    """Return (items, width, height, next index); items are (kind, width, height, children)."""
    items = []
    while i < len(s) and s[i] != ")":
        if s[i] == ":":
            items.append(("tic", 0.0, tic, None))
            i += 1
        elif s[i] == "(":
            child, w, h, i = _measure(s, i + 1, tic, gap, pad, r_min)
            if i >= len(s):
                raise ValueError("unclosed '('")
            r = max(h / 2 + pad, r_min)
            items.append(("enclosure", w + 2 * r, 2 * r, (child, w)))
            i += 1
        else:
            raise ValueError(f"unexpected {s[i]!r}; TX uses only ':', '(' and ')'")
    width = sum(it[1] for it in items) + gap * max(0, len(items) - 1)
    height = max((it[2] for it in items), default=0.0)
    return items, width, height, i


def _emit(items, x0, strokes, tic, gap, style, segments):
    x = x0
    for kind, w, h, payload in items:
        if kind == "tic":
            strokes.append(([(x, -tic / 2), (x, tic / 2)], False))
        else:
            child, inner_w = payload
            r = h / 2
            left, right = x + r, x + r + inner_w
            n = max(segments, int(segments * r))
            left_arc = _arc(left, 0, r, 90, 270, n)
            right_arc = _arc(right, 0, r, -90, 90, n)
            if style == "parens":
                strokes.append((left_arc, False))
                strokes.append((right_arc, False))
            else:
                strokes.append((left_arc + right_arc, True))
            _emit(child, left, strokes, tic, gap, style, segments)
        x += w + gap


def layout(s, tic=1.0, gap=0.32, pad=0.3, r_min=0.3, style="capsule", segments=12):
    """Glyph geometry in units: {'width', 'height', 'strokes': [(points, closed), ...]}.

    Points run left to right from x = 0 with y = 0 on the glyph's centre line
    (y down, as in SVG). style is 'capsule' (closed enclosures) or 'parens'.
    """
    if style not in ("capsule", "parens"):
        raise ValueError("style is 'capsule' or 'parens'")
    s = "".join(s.split())
    items, width, height, i = _measure(s, 0, tic, gap, pad, r_min)
    if i != len(s):
        raise ValueError("unmatched ')'")
    strokes = []
    _emit(items, 0.0, strokes, tic, gap, style, segments)
    return {"width": width, "height": height, "strokes": strokes}


def _as_string(value, mode, order):
    return value if isinstance(value, str) else encode(value, mode, order)


def draw(h, value, x, y, size, weight="orn", color="ink", mode="tx", order="ascending", **layout_args):
    """Draw an integer or TX string with a book-style hand; (x, y) is the top-left.

    Returns (width, height) in drawing units. Ticks and enclosures both go
    through h.stroke, so marks.Hand wobbles them and PlotHand exports them.
    """
    g = layout(_as_string(value, mode, order), **layout_args)
    oy = y + g["height"] * size / 2
    for points, closed in g["strokes"]:
        h.stroke([(x + u * size, oy + v * size) for u, v in points], weight, color, closed=closed)
    return g["width"] * size, g["height"] * size


def to_svg(value, mode="tx", order="ascending", unit=6.0, stroke=0.35, margin=4.0, ink="#000",
           **layout_args):
    """Standalone stroke-only SVG sized in millimetres (unit = mm per glyph unit)."""
    g = layout(_as_string(value, mode, order), **layout_args)
    w = g["width"] * unit + 2 * margin
    hgt = max(g["height"], 1e-9) * unit + 2 * margin
    oy = margin + g["height"] * unit / 2
    paths = []
    for points, closed in g["strokes"]:
        d = " ".join(f"{'M' if j == 0 else 'L'}{margin + u * unit:.3f},{oy + v * unit:.3f}"
                     for j, (u, v) in enumerate(points))
        paths.append(f'<path d="{d}{" Z" if closed else ""}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{hgt:.3f}mm" '
            f'viewBox="0 0 {w:.3f} {hgt:.3f}">\n'
            f'<g fill="none" stroke="{ink}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round">\n' + "\n".join(paths) + "\n</g>\n</svg>\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Xenotate an integer, or decode a TX string.")
    parser.add_argument("value", help="integer to encode, or a string of ':', '(' and ')' to decode")
    parser.add_argument("--nullary", action="store_true", help="use the nullary variant (empty string = 1)")
    parser.add_argument("--svg", help="also write a stroke-only SVG glyph to this path")
    parser.add_argument("--parens", action="store_true", help="draw enclosures as open arcs")
    args = parser.parse_args()
    mode = "nullary" if args.nullary else "tx"
    if args.value.isdigit():
        text, number = encode(int(args.value), mode), int(args.value)
    else:
        text, number = args.value, decode(args.value, mode)
    print(f"{number} = {text if text else '(empty)'}   {stats(text)}")
    if args.svg:
        from pathlib import Path
        target = Path(args.svg)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(to_svg(text, mode, style="parens" if args.parens else "capsule"))
        print(f"wrote {target}")
