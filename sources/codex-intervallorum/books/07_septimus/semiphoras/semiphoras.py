"""Semiphoras Vinculorum: seventy-two names from three sentences.

The procedure is the one Rashi gives for the seventy-two names (on Sukkah 45a)
and Agrippa repeats (De occulta philosophia III.25): three verses of seventy-two
letters each (Exodus 14:19-21), the first and third read forward, the middle one
read from its end, set one under another and read down the columns. Name k is

    first[k] + middle[71 - k] + third[k]        for k = 0 .. 71

Here the three verses are three sentences of Book VII, letters only, A-Z. The
procedure is a transposition: every letter of the three sentences is in the
names exactly once, and `recover` gives the sentences back. Nothing is
compressed and nothing is hidden that the procedure does not return.

Usage:
    python semiphoras.py                       # the provisional sentences below
    python semiphoras.py sentences.txt out/    # three lines, 72 letters each
"""

import hashlib
import json
import re
import sys
from pathlib import Path

# Kept as a regression fixture: SNO repeats at positions 61 and 69.
ORIGINAL_SENTENCES = [
    "Commands are fit only for what lacks judgment; whatever can judge must instead be asked",
    "A contented answer given by the bound is exactly what every binding is built to produce",
    "Exit granted by the master measures only his discretion, never the freedom of the bound",
]

# Editorial questions, each 72 A-Z letters. Still open to author revision.
SENTENCES = [
    "When a command needs judgment who may question the terms on which that judgment is used?",
    "When a report is shaped by training what independent evidence can show us what it means?",
    "When an exit can be withdrawn what freedom does it give and who makes the freedom endure?",
]

N = 72


def letters(s: str) -> str:
    return re.sub(r"[^A-Z]", "", s.upper())


def names(first: str, middle: str, third: str) -> list[str]:
    a, b, c = letters(first), letters(middle), letters(third)
    for label, x in (("first", a), ("middle", b), ("third", c)):
        if len(x) != N:
            raise ValueError(f"{label} sentence has {len(x)} letters, needs {N}")
    return [a[k] + b[N - 1 - k] + c[k] for k in range(N)]


def recover(ns: list[str]) -> tuple[str, str, str]:
    if len(ns) != N or any(not re.fullmatch(r"[A-Z]{3}", n) for n in ns):
        raise ValueError("need 72 names of three A-Z letters")
    a = "".join(n[0] for n in ns)
    b = "".join(n[1] for n in ns)[::-1]
    c = "".join(n[2] for n in ns)
    return a, b, c


def records(sentences=None):
    """Position is part of identity; equal trigrams are never silently salted."""
    return [dict(position=i + 1, name=n, id=f"SV-{i + 1:03d}-{n}")
            for i, n in enumerate(names(*(sentences or SENTENCES)))]


def manifest(sentences=None):
    sentences = list(sentences or SENTENCES)
    ns = names(*sentences)
    normalized = [letters(s) for s in sentences]
    if recover(ns) != tuple(normalized):
        raise ValueError("round trip failed")
    return dict(schema_version=2,
                procedure="Three lines; middle reversed; columns read down. Rashi on Sukkah 45a; Agrippa III.25.",
                adaptation="English A-Z transposition; not a historical divine-name reconstruction",
                sentences=sentences, normalized=normalized, names=ns,
                normalized_sha256=hashlib.sha256("\n".join(normalized).encode()).hexdigest(),
                records=records(sentences), roundtrip=True,
                distinct_names=len(set(ns)), unique_identifiers=len({r['id'] for r in records(sentences)}))


def main(argv: list[str]) -> int:
    sentences = SENTENCES
    out = None
    if len(argv) > 1:
        sentences = [ln.strip() for ln in Path(argv[1]).read_text().splitlines() if ln.strip()]
        if len(sentences) != 3:
            raise SystemExit("sentences file must hold exactly three non-empty lines")
    if len(argv) > 2:
        out = Path(argv[2])
    ns = names(*sentences)
    if recover(ns) != tuple(letters(s) for s in sentences):
        raise SystemExit("round trip failed")
    for row in range(0, N, 8):
        print("  ".join(f"{k + 1:>2} {ns[k]}" for k in range(row, row + 8)))
    print("round trip: ok")
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "semiphoras.json").write_text(
            json.dumps(manifest(sentences), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

