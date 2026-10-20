#!/usr/bin/env python3
"""Public checks for the Nota Clausa. Needs no key and reads nothing.

1. Each plot sheet carries 7920 marks, one per cell, every cell inside the arena of the
   Regula, in the two inks only.
2. The Tabula prints eight digests.
3. Optionally, a proposed reading is checked against those digests:
       python validate.py --reading readings/
   where readings/ holds field-1.txt ... field-7.txt, each the 1320 signs of the
   Regula's clause 21 (line feeds as line feeds).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
INK, RED = '#161918', '#a32b24'
G, D, N = 260, 236, 7920
X0, Y0, PITCH = 14.35, 61.35, 0.7     # Regula, clause 17


def inside(x, y):
    return 0 <= x < G and 0 <= y < G and (2 * x + 1 - G) ** 2 + (2 * y + 1 - G) ** 2 <= D * D


def marks(svg_path):
    """The marks of one plot sheet: {(x, y): bit}."""
    s = Path(svg_path).read_text().split('inkscape:label="Text Outlines"')[0]   # marks are in Art Paths
    out = {}
    for colour, d in re.findall(r'<path fill="none" stroke="(#[0-9a-f]{6})" stroke-width="0\.17" d="M([^"L]+L[^"L]+)"/>', s):
        a, b = d.split('L')
        (x1, y1), (x2, y2) = [tuple(map(float, p.split(','))) for p in (a, b)]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        cx, cy = round((mx - X0) / PITCH), round((my - Y0) / PITCH)
        if abs(cx * PITCH + X0 - mx) > 0.05 or abs(cy * PITCH + Y0 - my) > 0.05:
            raise ValueError(f'{svg_path}: mark off the lattice at {mx:.2f},{my:.2f}')
        if (cx, cy) in out:
            raise ValueError(f'{svg_path}: two marks on cell {(cx, cy)}')
        if colour not in (INK, RED):
            raise ValueError(f'{svg_path}: third ink {colour}')
        out[(cx, cy)] = 1 if colour == RED else 0
    return out


def digests():
    rows = re.findall(r'^\| (I|II|III|IV|V|VI|VII|All seven) \| `([0-9a-f]{64})` \|$', (ROOT / 'TABULA.md').read_text(), re.M)
    return dict(rows)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--reading', help='folder holding field-1.txt ... field-7.txt')
    args = ap.parse_args(argv)
    report = {'plates': {}}
    roman = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
    for k in range(1, 8):
        m = marks(ROOT / 'plates' / f'nota-clausa-{k}.svg')
        outside = [c for c in m if not inside(*c)]
        report['plates'][roman[k - 1]] = {'marks': len(m), 'red': sum(m.values()), 'outside_arena': len(outside),
                                          'ok': len(m) == N and not outside}
    dg = digests()
    report['digests_printed'] = len(dg)
    ok = all(p['ok'] for p in report['plates'].values()) and len(dg) == 8
    if args.reading:
        texts = [Path(args.reading, f'field-{k}.txt').read_bytes() for k in range(1, 8)]
        got = {roman[k]: hashlib.sha256(t).hexdigest() for k, t in enumerate(texts)}
        got['All seven'] = hashlib.sha256(b''.join(texts)).hexdigest()
        report['reading'] = {k: got[k] == dg[k] for k in dg}
        ok = ok and all(report['reading'].values())
    report['ok'] = ok
    print(json.dumps(report, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
