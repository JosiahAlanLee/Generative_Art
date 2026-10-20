"""Gate and window: a harm-accounting model in which the book's arrangement can lose.

Not an institutional simulator. One incident, one operator, one gate, one window.
Time is measured in windows: the window H is 1, and every latency and harm is a
multiple of it. Nothing here models people, incentives, learning or culture; those
exist only in the human layer, which this model does not reach.

The incident begins at time 0. In each round the operator spends `d` diagnosing and
proposes an action, which is wrong with probability `eps`. What happens next depends
on the arrangement:

  A  universal gate      every proposal waits for approval; the wait is lognormal with
                         median `lam` and log-sd `sigma`, and it is waited in full
                         whatever the window. The gate catches a wrong proposal with
                         probability `delta` and sends it back, and rejects a correct
                         one with probability `phi` (an override). Either way the
                         operator diagnoses again.
  B  deference           the operator acts at once on their own authority. No review.
  C  window-bounded gate the operator waits for approval only as long as the window
                         allows: until the approval arrives or the window closes,
                         whichever is first. An approval that arrives in time reviews
                         the proposal as in A; when the window closes first the
                         operator acts as in B.

A wrong action, once executed, costs `h_wrong` and the incident continues. The
incident ends when a correct action is executed, at time T. Total harm is

    T  +  h_window * [T > 1]  +  h_wrong * (wrong actions executed)

where `h_window` is the irreversible loss when the correct action lands after the
window. Booked harm is `h_wrong * (wrong actions executed)` alone: the part the
organisation attributes to the person who acted. That split is an assumption about
accounting, not a finding; it is reported separately so it can be rejected on its own.

All three arrangements use shared random draws (common random numbers). Pairing can
reduce the sampling variance of a difference; it does not eliminate Monte Carlo
error or make a threshold crossing certain. The round loop ends
when every sample has resolved under every arrangement or at `max_rounds`, and the
fraction truncated is recorded.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math

import numpy as np

ARRANGEMENTS = ("A", "B", "C")


@dataclass(frozen=True)
class Params:
    eps: float       # P(the operator's proposed action is wrong)
    delta: float     # P(the gate catches a wrong proposal)
    phi: float       # P(the gate rejects a correct proposal)
    lam: float       # median approval latency, in windows
    sigma: float     # log-sd of the approval latency
    d: float         # diagnosis time per attempt, in windows
    h_wrong: float   # harm of one executed wrong action, in windows
    h_window: float  # irreversible loss when the correct action lands after the window

    def check(self) -> None:
        for name in ("eps", "delta", "phi"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be a probability, got {v}")
        if self.eps >= 1.0:
            raise ValueError("eps must be below 1 or no incident ever resolves")
        for name in ("lam", "sigma", "d", "h_wrong", "h_window"):
            v = getattr(self, name)
            if v < 0:
                raise ValueError(f"{name} must be non-negative, got {v}")

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Stats:
    harm: float          # expected total harm, in windows
    booked: float        # expected booked harm (wrong actions only)
    T: float             # expected time to the correct action
    p_late: float        # P(T > 1): the correct action landed after the window
    n_wrong: float       # expected wrong actions executed
    truncated: float     # fraction of samples unresolved at max_rounds

    def as_dict(self) -> dict:
        return asdict(self)


def _stats(t: np.ndarray, n_wrong: np.ndarray, done: np.ndarray, p: Params) -> Stats:
    harm = t + p.h_window * (t > 1.0) + p.h_wrong * n_wrong
    return Stats(
        harm=float(harm.mean()),
        booked=float((p.h_wrong * n_wrong).mean()),
        T=float(t.mean()),
        p_late=float((t > 1.0).mean()),
        n_wrong=float(n_wrong.mean()),
        truncated=float((~done).mean()),
    )


def simulate_cell(p: Params, n: int, rng: np.random.Generator, max_rounds: int = 80) -> dict[str, Stats]:
    """Run the three arrangements on `n` samples with shared draws. Returns stats by arrangement."""
    p.check()
    mu = math.log(p.lam) if p.lam > 0 else -math.inf

    tA = np.zeros(n); tB = np.zeros(n); tC = np.zeros(n)
    wA = np.zeros(n, dtype=np.int64); wB = np.zeros(n, dtype=np.int64); wC = np.zeros(n, dtype=np.int64)
    dA = np.zeros(n, dtype=bool); dB = np.zeros(n, dtype=bool); dC = np.zeros(n, dtype=bool)

    for _ in range(max_rounds):
        if dA.all() and dB.all() and dC.all():
            break
        # Shared draws for this round.
        wrong = rng.random(n) < p.eps
        u_gate = rng.random(n)
        lat = rng.lognormal(mu, p.sigma, n) if p.lam > 0 else np.zeros(n)
        caught = wrong & (u_gate < p.delta)           # a wrong proposal the gate returns
        overridden = (~wrong) & (u_gate < p.phi)      # a correct proposal the gate rejects

        # A: universal gate. Diagnose, wait the whole latency, then the gate decides.
        a = ~dA
        tA[a] += p.d + lat[a]
        execA = a & ~caught & ~overridden
        wA[execA & wrong] += 1
        dA[execA & ~wrong] = True

        # B: deference. Diagnose and act.
        b = ~dB
        tB[b] += p.d
        wB[b & wrong] += 1
        dB[b & ~wrong] = True

        # C: window-bounded gate. Wait only as long as the window allows.
        c = ~dC
        tC[c] += p.d
        remaining = np.clip(1.0 - tC, 0.0, None)
        in_time = lat <= remaining
        tC[c] += np.minimum(lat, remaining)[c]
        reviewed = c & in_time
        unreviewed = c & ~in_time
        execC = (reviewed & ~caught & ~overridden) | unreviewed
        wC[execC & wrong] += 1
        dC[execC & ~wrong] = True

    return {
        "A": _stats(tA, wA, dA, p),
        "B": _stats(tB, wB, dB, p),
        "C": _stats(tC, wC, dC, p),
    }


def expected_harm_deference(p: Params) -> float:
    """Closed form for arrangement B, used to check the simulation.

    Attempts K are geometric with success 1 - eps; T = K d; wrong actions K - 1;
    T > 1 iff K > 1/d, i.e. K >= floor(1/d) + 1, with probability eps ** floor(1/d).
    """
    q = p.eps
    k_late = math.floor(1.0 / p.d) if p.d > 0 else math.inf
    p_late = q ** k_late if k_late != math.inf else 0.0
    return p.d / (1 - q) + p.h_wrong * q / (1 - q) + p.h_window * p_late


def cell_rng(seed: int, index: int) -> np.random.Generator:
    """One independent generator per cell, so any cell can be regenerated alone."""
    return np.random.default_rng([int(seed), int(index)])
