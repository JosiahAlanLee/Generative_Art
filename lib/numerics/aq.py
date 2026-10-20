"""Anglossic Qabbala (AQ): base-36 values for text, plus digital reduction.

Each character is read as a base-36 digit: 0-9 keep their face value and
A-Z count 10-35. Everything else is ignored, so spacing and punctuation never
change a value. A text's AQ value is the sum of its characters. Accents are
stripped first ("café" counts as CAFE); letters with no A-Z decomposition are
ignored.

Digital reduction (repeated digit sums) and cumulation (0 + 1 + ... + n) are
the two operations the CCRU used to numerize names; both are here so a value
can be carried into the numogram or used as a seed.

The aqcalc library's own checks give a fixed point to test against:
aq("Hello, World!") == 214 and aq("###") == 0
(https://github.com/VitorGoatman/aqcalc).

Standard library only. Usable as a script:
    python lib/numerics/aq.py "HIC ET NUNC"
"""
import re
import unicodedata

__all__ = ["char_value", "aq", "words", "reduce", "reduction_chain", "cumulate",
           "rule", "matches"]


def char_value(ch):
    """Base-36 value of one character after accent stripping, or None."""
    base = unicodedata.normalize("NFKD", ch)
    base = "".join(c for c in base if not unicodedata.combining(c)).upper()
    if len(base) != 1:
        return None
    if "0" <= base <= "9":
        return ord(base) - ord("0")
    if "A" <= base <= "Z":
        return ord(base) - ord("A") + 10
    return None


def aq(text):
    """Sum of the base-36 values of every alphanumeric character in `text`."""
    return sum(v for v in map(char_value, text) if v is not None)


def words(text):
    """[(word, value), ...] for each run of characters that carries a value."""
    out = []
    for token in re.split(r"\s+", text.strip()):
        value = aq(token)
        if value or any(char_value(c) is not None for c in token):
            out.append((token, value))
    return out


def reduce(n):
    """Digital reduction: sum the decimal digits until one digit remains."""
    n = abs(int(n))
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def reduction_chain(n):
    """Every step of the reduction, e.g. 99 -> [99, 18, 9]."""
    n = abs(int(n))
    chain = [n]
    while n > 9:
        n = sum(int(d) for d in str(n))
        chain.append(n)
    return chain


def cumulate(n):
    """Digital cumulation: 0 + 1 + ... + n (the n-th triangular number)."""
    n = int(n)
    if n < 0:
        raise ValueError("cumulation is defined here for n >= 0")
    return n * (n + 1) // 2


def rule(text):
    """AQ value mod 256, usable as a Wolfram elementary cellular-automaton rule."""
    return aq(text) % 256


def matches(text, candidates):
    """Candidates sharing `text`'s AQ value: the equivalences AQ is used for.

    Equal values are the point of the system, so using aq() directly as a seed
    deliberately gives every equivalent phrase the same plate.
    """
    target = aq(text)
    return [c for c in candidates if aq(c) == target]


if __name__ == "__main__":
    import sys
    phrase = " ".join(sys.argv[1:]) or "Hello, World!"
    value = aq(phrase)
    print(f"{phrase!r}: AQ {value}, reduction {' -> '.join(map(str, reduction_chain(value)))}, rule {rule(phrase)}")
    for word, v in words(phrase):
        print(f"  {word}: {v}")
