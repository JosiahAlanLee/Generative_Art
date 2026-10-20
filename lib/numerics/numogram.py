"""The decimal numogram as plain arithmetic.

The CCRU describe the numogram as built only from additions and subtractions
on the ten digits (https://dataswamp.org/~john/sites/ccru/declab.htm, an
archive of their site). This module encodes those rules and nothing else; it
carries no CCRU prose or demon names.

  zones      0-9
  syzygies   pairs that sum to nine: 0::9, 1::8, 2::7, 3::6, 4::5
  currents   a syzygy's difference, flowing to the zone of that number
  regions    the three central syzygies' currents cycle through each other
             (time-circuit: 1::8, 2::7, 4::5); the upper and lower syzygies
             fold back into one of their own zones (warp 3::6, plex 0::9)
  gates      a zone's digital cumulation (0 + 1 + ... + n); the gate's digital
             reduction is where that zone's channel leads
  cycles     digital reduction of powers of two repeats 1, 2, 4, 8, 7, 5 (the
             time-circuit zones); multiplying by five gives the same cycle
             reversed
  net-spans  the 45 zone pairs a::b with a > b, serially numbered 00-44 in the
             order 1::0, 2::0, 2::1, 3::0 ... 9::8 (the Pandemonium mesh)

Standard library only. `to_dot()` writes a Graphviz graph of the structure.
"""

__all__ = ["ZONES", "SYZYGIES", "TIME_CIRCUIT", "WARP", "PLEX", "reduce", "cumulate",
           "syzygy", "pair", "current", "region", "follow_currents", "gate", "channel",
           "follow_channels", "binodecimal_cycle", "quintuplicative_cycle", "net_spans",
           "mesh", "net_span", "phase", "to_dot"]

ZONES = tuple(range(10))
SYZYGIES = ((0, 9), (1, 8), (2, 7), (3, 6), (4, 5))
TIME_CIRCUIT = (1, 2, 4, 5, 7, 8)
WARP = (3, 6)
PLEX = (0, 9)


def _zone(z):
    if z not in ZONES:
        raise ValueError(f"zones are 0-9, got {z!r}")
    return z


def reduce(n):
    """Digital reduction: sum the decimal digits until one digit remains."""
    n = abs(int(n))
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def cumulate(n):
    """Digital cumulation: 0 + 1 + ... + n."""
    n = int(n)
    if n < 0:
        raise ValueError("cumulation is defined here for n >= 0")
    return n * (n + 1) // 2


def syzygy(z):
    """The nine-sum twin of zone z."""
    return 9 - _zone(z)


def pair(z):
    """z's syzygy written low-high, e.g. pair(5) == (4, 5)."""
    return tuple(sorted((_zone(z), 9 - z)))


def current(z):
    """Value of the current produced by z's syzygy; also the zone it flows to."""
    return abs(2 * _zone(z) - 9)


def region(z):
    """'time-circuit', 'warp' or 'plex'."""
    _zone(z)
    if z in WARP:
        return "warp"
    if z in PLEX:
        return "plex"
    return "time-circuit"


def follow_currents(z, steps=6):
    """Zones visited by repeatedly following currents, starting from z."""
    path = [_zone(z)]
    for _ in range(steps):
        path.append(current(path[-1]))
    return path


def gate(z):
    """A zone's gate value: its digital cumulation."""
    return cumulate(_zone(z))


def channel(z):
    """(gate value, destination zone) for z's channel."""
    g = gate(z)
    return g, reduce(g)


def follow_channels(z, steps=6):
    """Zones visited by repeatedly passing through gates, starting from z."""
    path = [_zone(z)]
    for _ in range(steps):
        path.append(channel(path[-1])[1])
    return path


def binodecimal_cycle(length=6):
    """Digital reduction of 2**k for k = 0 .. length-1: 1, 2, 4, 8, 7, 5, ..."""
    return [reduce(2 ** k) for k in range(length)]


def quintuplicative_cycle(length=6):
    """Digital reduction of 5**k: the binodecimal cycle in reverse order."""
    return [reduce(5 ** k) for k in range(length)]


def net_spans():
    """All 45 net-spans (a, b), a > b, in mesh order."""
    return [(a, b) for a in range(1, 10) for b in range(a)]


def mesh(a, b):
    """Serial number 0-44 of net-span a::b (either argument order)."""
    a, b = max(_zone(a), _zone(b)), min(a, b)
    if a == b:
        raise ValueError("a net-span joins two different zones")
    return a * (a - 1) // 2 + b


def net_span(m):
    """Inverse of mesh(): the (a, b) pair with serial number m."""
    if not 0 <= m <= 44:
        raise ValueError("mesh numbers run 0-44")
    return net_spans()[m]


def phase(m):
    """Phase of mesh number m: the first digit of its net-span."""
    return net_span(m)[0]


def to_dot(gates=True):
    """Graphviz description: zones, syzygy links, currents and (optionally) gates."""
    lines = ["digraph numogram {", '  graph [rankdir=TB, fontname="serif"];',
             '  node [shape=circle, fontname="serif"];']
    for name, members in (("warp", WARP), ("time_circuit", TIME_CIRCUIT), ("plex", PLEX)):
        lines.append(f'  subgraph cluster_{name} {{ label="{name.replace("_", "-")}"; '
                     + " ".join(f'"{z}";' for z in members) + " }")
    for lo, hi in SYZYGIES:
        s = f"{lo}::{hi}"
        lines.append(f'  "{s}" [shape=box, label="{s}"];')
        lines.append(f'  "{lo}" -> "{s}" [dir=none, style=dashed];')
        lines.append(f'  "{hi}" -> "{s}" [dir=none, style=dashed];')
        lines.append(f'  "{s}" -> "{current(lo)}" [label="current {current(lo)}"];')
    if gates:
        for z in ZONES:
            g, dest = channel(z)
            lines.append(f'  "{z}" -> "{dest}" [style=dotted, label="gate {g}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    for lo, hi in SYZYGIES:
        print(f"{lo}::{hi}  current {current(lo)}  region {region(lo)}")
    for z in ZONES:
        g, dest = channel(z)
        print(f"zone {z}: gate {g} -> channel to {dest}")
