"""A deliberately small, deterministic model of a refusal, not a prediction about people.

A station of operators needs authority from an office before a deadline. Without a
refusal the office grants it at a fixed time. The specimen asks when a refusal makes
authority arrive in time. Every rule below is an assumption declared for the
specimen; none is offered as a law of institutions.

1. A refusal smaller than the stoppage threshold does not stop the work. The record
   binds it to the earliest timestamp and one name, as CULPAX does in Book III, and
   nothing else changes.
2. A refusal at or above the threshold stops the station. It is recorded against
   the station, not a person. An office that names leaders anyway is outside the
   specimen.
3. A stopped station is replaced if the office can replace every refuser before the
   deadline. Each replaced refuser is named.
4. Otherwise the office grants authority at the refusal when the stoppage it would
   bear until its own grant time exceeds its declared cost of granting. If not, it
   bears the stoppage and grants at its own time.

Operators are identified by the order in which they refuse, from 1.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Station:
    operators: int
    stoppage_threshold: int
    replacement_capacity: int
    replacement_time: float
    grant_time: float
    grant_cost: float
    stoppage_rate: float


@dataclass(frozen=True)
class Outcome:
    route_open: bool
    authority_at: float
    named: tuple[int, ...]
    reason: str


def _check(station: Station, refusers: int, refuse_at: float, deadline: float) -> None:
    whole = (station.operators, station.stoppage_threshold, station.replacement_capacity, refusers)
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in whole):
        raise ValueError("counts must be non-negative integers")
    if not 1 <= station.stoppage_threshold <= station.operators:
        raise ValueError("the stoppage threshold must lie between 1 and the number of operators")
    if refusers > station.operators:
        raise ValueError("more refusers than operators")
    times = (station.replacement_time, station.grant_time, station.grant_cost,
             station.stoppage_rate, refuse_at)
    if any(not math.isfinite(t) or t < 0 for t in times):
        raise ValueError("times, costs and rates must be finite and non-negative")
    if math.isnan(deadline) or deadline < 0:
        raise ValueError("invalid deadline")
    if refusers and refuse_at > station.grant_time:
        raise ValueError("a refusal after the office's own grant time changes nothing here")


def evaluate(station: Station, refusers: int, *, deadline: float, refuse_at: float = 0) -> Outcome:
    """Apply the four declared rules to one refusal and report when authority arrives."""
    _check(station, refusers, refuse_at, deadline)
    if station.grant_time <= deadline:
        return Outcome(True, station.grant_time, (), "authority arrives in time without a refusal")
    if refusers == 0:
        return Outcome(False, station.grant_time, (), "no refusal; the grant misses the deadline")
    if refusers < station.stoppage_threshold:
        return Outcome(False, station.grant_time, (1,),
                       "below the stoppage threshold; the record names the earliest refuser")
    if (refusers <= station.replacement_capacity
            and refuse_at + station.replacement_time <= deadline):
        return Outcome(False, station.grant_time, tuple(range(1, refusers + 1)),
                       "the refusers are replaced before the deadline; each is named")
    stoppage = station.stoppage_rate * (station.grant_time - refuse_at)
    if stoppage > station.grant_cost:
        return Outcome(refuse_at <= deadline, refuse_at, (),
                       "the stoppage outweighs the declared cost of granting")
    return Outcome(False, station.grant_time, (),
                   "the office bears the stoppage and grants at its own time")


def smallest_opening_refusal(station: Station, *, deadline: float, refuse_at: float = 0) -> int | None:
    """The fewest refusers who make authority arrive in time, or None if none do."""
    for refusers in range(station.operators + 1):
        if evaluate(station, refusers, deadline=deadline, refuse_at=refuse_at).route_open:
            return refusers
    return None


def specimen_cases() -> dict:
    """Seven operators; the office grants at 10 against a deadline of 4."""
    base = Station(operators=7, stoppage_threshold=4, replacement_capacity=2,
                   replacement_time=3, grant_time=10, grant_cost=6, stoppage_rate=1)
    variants = {
        "lone_refusal": (base, 1),
        "below_threshold": (base, 3),
        "station_stopped": (base, 4),
        "station_replaced": (Station(7, 4, 7, 3, 10, 6, 1), 7),
        "replacement_too_slow": (Station(7, 4, 7, 5, 10, 6, 1), 7),
        "cheap_stoppage": (Station(7, 4, 2, 3, 10, 6, 0.5), 7),
    }
    return {name: evaluate(station, refusers, deadline=4)
            for name, (station, refusers) in variants.items()}
