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
    return classify_routes(dict(schema='infernal-architecture/0.2', case=case, seed=seed,
                target=target, deadline=deadline, bay_unit=bay_unit,nodes=nodes,
                edges=[dict(source=p, target=n) for n, t in tasks.items() for p in t.needs],
                result=dict(feasible=result.feasible, arithmetic_completion=result.completion,
                            executable_completion=result.completion if all(t.available for t in tasks.values()) else None,
                            reason=result.reason, schedule=dict(result.schedule)),
                interpretation='Artistic mappings from an exact scheduling specimen; no institutional simulation.',
                source=dict(path='sources/codex-intervallorum/books/02_intervallorum/generator/reachability.py',
                            sha256=hashlib.sha256((ROOT/'vendor/reachability.py').read_bytes()).hexdigest())))


def classify_routes(arch):
    """Decide which recorded dependencies are drawn in red.

    Black records an arrangement; red marks what happened. Every prerequisite is
    a black tray. The red centerline is reserved for edges on the critical path
    to the target: an edge p -> n is critical when n is critical and p's finish
    is what set n's start. A node whose start was set by its release time rather
    than by a prerequisite gets a red release mark instead, and the edges into
    it carry slack and stay black. When no executable completion exists, red
    follows the critical path only as far as the first unavailable ancestor:
    the route reached a closed gate and nothing downstream is reached.

    The classification is pure arithmetic on the evaluator's schedule; it adds
    no model of priority, blame or intent. The engraving stage recomputes it
    from the embedded record, so earlier scene records need no rebuild.
    """
    nodes={n['id']:n for n in arch['nodes']}
    ins={}
    for e in arch['edges']:ins.setdefault(e['target'],[]).append(e['source'])
    binding={}
    for name,n in nodes.items():
        latest=max((nodes[p]['finish'] for p in ins.get(name,[]) if p in nodes),default=0)
        if n['release_at']>0 and n['release_at']>=latest and n['start']==n['release_at']:binding[name]='release'
        elif ins.get(name) and n['start']==latest:binding[name]='prerequisite'
        else:binding[name]='start'
    critical_nodes=set();critical_edges=set();stack=[arch['target']]
    while stack:
        name=stack.pop()
        if name in critical_nodes:continue
        critical_nodes.add(name)
        if binding[name]!='prerequisite':continue
        for p in ins.get(name,[]):
            if nodes[p]['finish']==nodes[name]['start']:
                critical_edges.add((p,name));stack.append(p)
    executable=all(n['available'] for n in nodes.values())
    red_edges=set(critical_edges)
    if not executable:
        # Red reaches the closed gate and stops: only the critical edges that
        # lead into an unavailable node, or into its own critical ancestors.
        upstream=set();frontier=[n for n in critical_nodes if not nodes[n]['available']]
        while frontier:
            name=frontier.pop()
            if name in upstream:continue
            upstream.add(name)
            frontier.extend(p for (p,q) in critical_edges if q==name)
        red_edges={(p,q) for (p,q) in critical_edges if q in upstream}
    for e in arch['edges']:
        key=(e['source'],e['target'])
        e['critical']=key in critical_edges;e['red']=key in red_edges
    for n in arch['nodes']:
        n['binding']=binding[n['id']]
        n['release_mark']=binding[n['id']]=='release' and n['id'] in critical_nodes and (executable or n['available'])
    arch['red_rule']=('the critical path to the target; a release that set a start is marked on its lift; '
                      'with no executable completion, red stops at the first closed gate')
    if arch.get('scene_profile')=='spillway':arch['red_rule']=arch['red_rule'].replace('on its lift','on its access passage')
    return arch


def compile_document(doc,case='custom'):
    tasks={n:Task(duration=t['duration'],needs=tuple(t.get('needs',())),release_at=t.get('release_at',0),
                  cost=t.get('cost',0),valid_until=t.get('valid_until',math.inf),available=t.get('available',True))
           for n,t in doc['tasks'].items()}
    positions={n:t['position'] for n,t in doc['tasks'].items() if 'position' in t}
    arch=compile_tasks(tasks,case,target=doc['target'],deadline=doc['deadline'],positions=positions,
                       seed=doc.get('seed',314159),bay_unit=doc.get('bay_unit',1))
    profile=doc.get('scene_profile','estate')
    if profile not in ('estate','spillway','window'):raise ValueError('Unknown scene_profile: '+profile)
    arch['scene_profile']=profile
    if profile=='spillway':
        nodes={n['id']:n for n in arch['nodes']}
        for n in arch['nodes']:
            latest=max((nodes[p]['finish'] for p in n['needs']),default=0)
            n['plinth']=0
            n['wait_duration']=max(0,n['release_at']-latest)
            n['wait_length']=.75*n['wait_duration']
        arch['duration_encoding']='horizontal 1.6-unit factory bays; ceil(duration / bay_unit)'
        arch['release_encoding']='horizontal access passage: 0.75 units per unit of effective release wait'
        arch['red_rule']=arch['red_rule'].replace('on its lift','on its access passage')
    return arch


if __name__ == '__main__':
    for case in CASES:
        out = ROOT / 'output' / case
        out.mkdir(parents=True, exist_ok=True)
        (out/'architecture.json').write_text(json.dumps(compile_case(case), indent=2))
        print(case, compile_case(case)['result'])
