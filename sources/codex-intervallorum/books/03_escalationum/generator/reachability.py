"""A deliberately small, deterministic scheduling model, not an institutional simulator.

All task prerequisites are AND prerequisites. Independent tasks may run in parallel
without capacity contention. A task's valid_until is its own completion deadline;
it does not model an output that later expires. Options are evaluated separately.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True)
class Task:
    duration: float
    needs: tuple[str, ...] = ()
    release_at: float = 0
    valid_until: float = math.inf
    cost: float = 0
    available: bool = True


@dataclass(frozen=True)
class Result:
    feasible: bool
    completion: float | None
    cost: float
    schedule: Mapping[str, tuple[float, float]]
    reason: str


def evaluate(tasks: Mapping[str, Task], target: str, *, now: float = 0,
             deadline: float = math.inf, budget: float = math.inf) -> Result:
    """Find earliest completion for a single target under the declared assumptions.

    The recursion takes max at AND joins, adds task duration, and respects release
    times. It visits shared ancestors once. Infeasibility is exact for this model;
    it is not a prediction about unmodeled people, resources, or future events.
    """
    if not math.isfinite(now):
        raise ValueError("now must be finite")
    if math.isnan(deadline) or math.isnan(budget) or budget < 0:
        raise ValueError("invalid deadline or budget")
    for name, task in tasks.items():
        if (not math.isfinite(task.duration) or task.duration < 0
                or not math.isfinite(task.release_at)
                or not math.isfinite(task.cost) or task.cost < 0
                or math.isnan(task.valid_until)):
            raise ValueError(f"invalid task: {name}")
    schedule: dict[str, tuple[float, float]] = {}
    visiting: set[str] = set()
    failures: list[str] = []

    def visit(name: str) -> float:
        if name in schedule:
            return schedule[name][1]
        if name not in tasks:
            raise ValueError(f"unknown prerequisite: {name}")
        if name in visiting:
            raise ValueError(f"cyclic prerequisites: {name}")
        visiting.add(name)
        task = tasks[name]
        prior = [visit(parent) for parent in task.needs]
        start = max([now, task.release_at] + prior)
        finish = start + task.duration
        schedule[name] = (start, finish)
        if not task.available:
            failures.append(f"unavailable: {name}")
        if finish > task.valid_until:
            failures.append(f"task deadline missed: {name}")
        visiting.remove(name)
        return finish

    completion = visit(target)
    cost = sum(tasks[name].cost for name in schedule)
    if cost > budget:
        failures.append("budget exceeded")
    if completion > deadline:
        failures.append("target deadline missed")
    return Result(not failures, completion, cost, schedule,
                  "; ".join(failures) if failures else "feasible within model")



def escalation_tasks(route="ordinary", *, executive_release=90, absent=False):
    tasks = {"recognize": Task(4)}
    routes = {
        "ordinary": [6, 7, 8, 8, 9, 10],
        "commercial": [6, 8, 9, 10],
        "departmental": [6, 8, 10],
        "direct": [10],
        "emergency": [3],
    }
    prev = "recognize"
    for i, duration in enumerate(routes[route]):
        key = "briefing_" + str(i+1)
        tasks[key] = Task(duration, (prev,))
        prev = key
    tasks["bael_approval"] = Task(5, (prev,), release_at=executive_release, available=not absent)
    tasks["repair"] = Task(8, ("recognize", "bael_approval"))
    return tasks


def executable_record(result):
    from dataclasses import asdict
    record = asdict(result)
    # Deadline misses remain executable late. Absence prevents execution entirely.
    record["completion"] = None if "unavailable:" in result.reason else result.completion
    if "unavailable:" in result.reason:
        record["schedule"] = {}
    return record


def specimen_cases():
    routes = ["ordinary", "commercial", "departmental", "direct", "emergency"]
    cases = {r: executable_record(evaluate(escalation_tasks(r), "repair", deadline=60)) for r in routes}
    cases["continuous_absence"] = executable_record(evaluate(escalation_tasks(absent=True), "repair", deadline=60))
    delegated = {"recognize": Task(4), "local_permission": Task(1, ("recognize",)),
                 "repair": Task(8, ("recognize", "local_permission"))}
    cases["delegated_counterfactual"] = executable_record(evaluate(delegated, "repair", deadline=60))
    return cases


if __name__ == "__main__":
    import json
    print(json.dumps(specimen_cases(), indent=2))
