"""The three recurring hands, the later technical hand, and the record's base faces."""

INK = "#1c1813"
RED = "#a3271b"
GRAPHITE = "#4a463f"
SEPIA = "#6d5f4b"

CUST_FONT = "IM FELL English"
M_FONT = "Sue Ellen Francisco"
UN_FONT = "Zeyada"
TECH_FONT = "Cutive Mono"


def _box(**k):
    k.setdefault("lh", round(k["size"] * 1.3, 1))
    k.setdefault("color", INK)
    return k


def cust(id, x, y, w, text, size=20, align=None, color=INK, lh=None, ls=0.01, style=""):
    """The Custodian: formal black text, broad spacing, impersonal imperatives."""
    runs = _runs(text, style)
    b = _box(id=id, x=x, y=y, w=w, size=size, font=CUST_FONT, color=color, ls=ls, runs=runs,
             lh=lh or round(size * 1.38, 1))
    if align:
        b["align"] = align
    b["para_gap"] = round(size * 0.5)
    return b


def mhand(id, x, y, w, text, size=23, align=None, color=RED, lh=None):
    """M., the measurer: narrow script; additions often in red."""
    b = _box(id=id, x=x, y=y, w=w, size=size, font=M_FONT, color=color, runs=_runs(text, ""),
             lh=lh or round(size * 1.12, 1))
    if align:
        b["align"] = align
    b["para_gap"] = 4
    return b


def unh(id, x, y, w, text, size=25, align=None, color=GRAPHITE, lh=None):
    """The Unnumbered Hand: short ordinary sentences, written into unused space."""
    b = _box(id=id, x=x, y=y, w=w, size=size, font=UN_FONT, color=color, runs=_runs(text, ""),
             lh=lh or round(size * 1.1, 1))
    if align:
        b["align"] = align
    b["para_gap"] = 4
    return b


def tech(id, x, y, w, text, size=15, align=None, color=GRAPHITE, lh=None, ls=0.02):
    """The later technical hand (typed labels)."""
    b = _box(id=id, x=x, y=y, w=w, size=size, font=TECH_FONT, color=color, runs=_runs(text, ""),
             lh=lh or round(size * 1.35, 1), ls=ls)
    if align:
        b["align"] = align
    b["para_gap"] = 4
    return b


def _runs(text, style):
    if isinstance(text, list):
        return text
    out = []
    for i, para in enumerate(text.split("\n")):
        if i:
            out.append(("", "br"))
        out.append((para, style))
    return out
