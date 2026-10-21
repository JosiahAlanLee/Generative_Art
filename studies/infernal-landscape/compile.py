"""Map the book's exact task specimen into an architectural scene grammar.

The evaluator is vendored unchanged. This adapter does not add probabilities,
institutional forecasts or causal interpretations to its results.
"""
from pathlib import Path
import hashlib, json, math, sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
from reachability import Task, evaluate

CASES = ('recorded_route', 'rehearsed_route', 'late_opening', 'gate_unavailable')
POSITIONS = {'read': (-4.8, 3.2), 'staff': (4.3, 3.2),
             'approval': (-4.8, 10.5), 'restore': (3.2, 14.2)}


def compile_case(case):
    if case not in CASES:
        raise ValueError(f'Unknown specimen: {case}')
    tasks = {'read': Task(2), 'staff': Task(3),
             'approval': Task(6, ('read',)),
             'restore': Task(2, ('staff', 'approval'))}
    if case != 'recorded_route':
        tasks['approval'] = Task(1, ('read',), release_at=8 if case == 'late_opening' else 0,
                                 available=case != 'gate_unavailable')
    return compile_tasks(tasks, case, target='restore', deadline=10, positions=POSITIONS)


def compile_tasks(tasks, case, *, target, deadline, positions=None, seed=314159, bay_unit=1):
    """Accept arbitrary finite AND task graphs; absent layout uses graph depth."""
    if not math.isfinite(bay_unit) or bay_unit<=0:
        raise ValueError('bay_unit must be finite and positive')
    result = evaluate(tasks, target, deadline=deadline)
    # The evaluator includes only ancestors of the target. Do the same visually.
    tasks={n:t for n,t in tasks.items() if n in result.schedule}
    levels={}
    def level(n):
        if n not in levels:levels[n]=1+max((level(p) for p in tasks[n].needs),default=-1)
        return levels[n]
    for n in tasks:level(n)
    fallback={}
    for lv in sorted(set(levels.values())):
        members=sorted(n for n in tasks if levels[n]==lv)
        for i,n in enumerate(members):fallback[n]=((i-(len(members)-1)/2)*9,3.2+lv*6)
    positions=positions or {}
    nodes = []
    for name, task in tasks.items():
        bays=max(1,math.ceil(task.duration/bay_unit))
        if bays>24:raise ValueError('More than 24 bays; increase bay_unit for this graph')
        x,y=positions.get(name,fallback[name])
        nodes.append(dict(id=name, x=x, y=y,
                          duration=task.duration, bays=bays,
                          release_at=task.release_at, plinth=.34 * task.release_at,
                          available=task.available, needs=list(task.needs),
                          start=result.schedule[name][0], finish=result.schedule[name][1]))
    return dict(schema='infernal-architecture/0.2', case=case, seed=seed,
                target=target, deadline=deadline, bay_unit=bay_unit,nodes=nodes,
                edges=[dict(source=p, target=n) for n, t in tasks.items() for p in t.needs],
                result=dict(feasible=result.feasible, arithmetic_completion=result.completion,
                            executable_completion=result.completion if all(t.available for t in tasks.values()) else None,
                            reason=result.reason, schedule=dict(result.schedule)),
                interpretation='Artistic mappings from an exact scheduling specimen; no institutional simulation.',
                source=dict(path='sources/codex-intervallorum/books/02_intervallorum/generator/reachability.py',
                            sha256=hashlib.sha256((ROOT/'vendor/reachability.py').read_bytes()).hexdigest()))


def compile_document(doc,case='custom'):
    tasks={n:Task(duration=t['duration'],needs=tuple(t.get('needs',())),release_at=t.get('release_at',0),
                  cost=t.get('cost',0),valid_until=t.get('valid_until',math.inf),available=t.get('available',True))
           for n,t in doc['tasks'].items()}
    positions={n:t['position'] for n,t in doc['tasks'].items() if 'position' in t}
    return compile_tasks(tasks,case,target=doc['target'],deadline=doc['deadline'],positions=positions,
                         seed=doc.get('seed',314159),bay_unit=doc.get('bay_unit',1))


if __name__ == '__main__':
    for case in CASES:
        out = ROOT / 'output' / case
        out.mkdir(parents=True, exist_ok=True)
        (out/'architecture.json').write_text(json.dumps(compile_case(case), indent=2))
        print(case, compile_case(case)['result'])
