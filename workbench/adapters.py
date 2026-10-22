"""Validate recipes and build argv lists, never shell command strings."""
from pathlib import Path
import math
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
FORMATS = 'codex codexSpread codexPlot 6x9 5.5x8.5 7x10 8.5x11 a5 a4 a3 8x8 spread6x9'.split()
PALETTES = 'codex irongall fieldriso lush barnyard prussian graphite dusk nocturne kraft'.split()
KINDS = 'barn tractor disk_harrow hay_rake wagon farmyard comparison'.split()
CASES = 'recorded_route rehearsed_route late_opening gate_unavailable'.split()


def choice(value, options, name):
    if value not in options:
        raise ValueError(f'{name}: choose one of {", ".join(options)}')
    return value


def number(value, low, high, name, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name}: expected a number')
    if not math.isfinite(value) or not low <= value <= high or (integer and int(value) != value):
        raise ValueError(f'{name}: expected {low} to {high}' + (' (integer)' if integer else ''))
    return int(value) if integer else value


def flag(value):
    if type(value) is not bool:
        raise ValueError('checkbox values must be booleans')
    return value


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('recipe must be a JSON object')
    gen = choice(data.get('generator'), ['driftless', 'farm', 'infernal'], 'generator')
    p = data.get('params', {})
    if not isinstance(p, dict):
        raise ValueError('params must be an object')
    seed = p.get('seed', 'e2' if gen == 'driftless' else 22)
    if gen == 'driftless':
        # CLI seed becomes part of a filename: disallow slashes, option prefixes, etc.
        import re
        if not isinstance(seed, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,64}', seed):
            raise ValueError('seed: use 1–64 letters, digits or underscores')
        q = dict(seed=seed)
        enums = dict(format=(FORMATS, 'a4'), palette=(PALETTES, 'codex'),
                     focal=('auto oak pine grove farmstead watertower prairie rocktop monument rock bluff sun vista'.split(), 'auto'),
                     season=('auto spring summer autumn winter'.split(), 'auto'),
                     frame=('auto none border arch oculus arcade'.split(), 'auto'),
                     time=('auto day dusk night'.split(), 'auto'),
                     rock=('auto sandstone limestone quartzite'.split(), 'auto'),
                     zone=('none codex top middle bottom'.split(), 'none'),
                     zoneMode=(['fade', 'tint'], 'fade'),
                     # '' = the current engine; '1.1' redraws plates kept under engine 1.1 (CLI --compat).
                     compat=(['', '1.1'], ''))
        for k, (opts, default) in enums.items():
            q[k] = choice(p.get(k, default), opts, k)
        # (default, low, high). penWidth is the page's Nib (mm): it changes the lines, not only the stroke.
        ranges = dict(density=(100, 50, 160), imperfection=(50, 0, 100), flora=(60, 0, 100), land=(60, 0, 100),
                      built=(50, 0, 100), sky=(50, 0, 100), strength=(100, 0, 100), penWidth=(.35, .2, .8))
        for k, (default, low, high) in ranges.items():
            q[k] = number(p.get(k, default), low, high, k)
        for k in ['landscape', 'bleed', 'paper', 'riso', 'no-optimize']:
            q[k] = flag(p.get(k, False))
    elif gen == 'farm':
        q = dict(seed=number(seed, 0, 2**32-100, 'seed', True),
                 decay=number(p.get('decay', .72), 0, 1, 'decay'),
                 only=choice(p.get('only', 'barn'), KINDS, 'only'), png=flag(p.get('png', True)))
    else:
        # run.py has fixed scene seeds. Do not advertise a seed it cannot accept.
        q = dict(case=choice(p.get('case', CASES[0]), CASES, 'case'),
                 view=choice(p.get('view', 'main'), ['main', 'low', 'tower', 'barn'], 'view'))
        for k in ['dry_run', 'face_patterns', 'plates', 'no_clay']:
            q[k] = flag(p.get(k, k == 'dry_run'))
        if q['plates'] and q['face_patterns']:
            raise ValueError('plates already includes face patterns')
        if q['view'] in ['tower', 'barn'] and not q['plates']:
            raise ValueError('tower and barn cameras require plates')
    extra = set(p) - set(q)
    if extra:
        raise ValueError('unknown controls: ' + ', '.join(sorted(extra)))
    return dict(generator=gen, params=q)


def settings():
    return dict(node=os.environ.get('WORKBENCH_NODE', 'node'),
                python=os.environ.get('WORKBENCH_PYTHON', sys.executable),
                engraving=os.environ.get('WORKBENCH_ENGRAVING_PYTHON', sys.executable),
                blender=os.environ.get('WORKBENCH_BLENDER_PYTHON', ''),
                vpype=os.environ.get('WORKBENCH_VPYPE', 'vpype'))


def isolated_sources(destination):
    """Copy source only, preserving repo-relative imports and vendor hashes."""
    ignore = shutil.ignore_patterns('output', 'out', '__pycache__', 'tests', '*.pyc', '*.nbc', '*.nbi')
    for relative in ['studies/infernal-landscape', 'lib']:
        shutil.copytree(ROOT / relative, destination / relative, ignore=ignore)


def plan(recipe, job_dir, config):
    gen, p = recipe['generator'], recipe['params']
    output = job_dir / 'artifacts'
    if gen == 'driftless':
        cmd = [config['node'], str(ROOT / 'studies/driftless-plates/cli.js'), '--out', str(output), '--seeds', p['seed']]
        for k, v in p.items():
            if k == 'seed' or (k == 'compat' and not v):
                continue
            if isinstance(v, bool):
                if v:
                    cmd.append('--' + k)
            else:
                cmd += ['--' + k, str(v)]
        return cmd, ROOT, output
    if gen == 'farm':
        cmd = [config['python'], str(ROOT / 'studies/farm-remnants/build.py'), '--out', str(output),
               '--seed', str(p['seed']), '--decay', str(p['decay']), '--only', p['only']]
        if not p['png']:
            cmd.append('--no-png')
        return cmd, ROOT, output
    if not p['dry_run'] and not config['blender']:
        raise ValueError('Set WORKBENCH_BLENDER_PYTHON to a Python with bpy before a Blender render')
    workspace = job_dir / 'workspace'
    study = workspace / 'studies/infernal-landscape'
    cmd = [config['python'], str(study / 'run.py'), '--engraving-python', config['engraving'],
           '--cases', p['case'], '--views', p['view']]
    if config['blender']:
        cmd += ['--blender-python', config['blender']]
    for k in ['dry_run', 'face_patterns', 'plates', 'no_clay']:
        if p[k]:
            cmd.append('--' + k.replace('_', '-'))
    return cmd, study, study / 'output'


def environment(config):
    env = dict(os.environ)
    # Never inherit an unrelated shell's Infernal variant/custom input.
    for k in list(env):
        if k.startswith('INFERNAL_') or k == 'TERRAIN_VIEW':
            del env[k]
    node = shutil.which(config['node'])
    if node:
        # run.py calls `node` by name for its patches stage.
        env['PATH'] = str(Path(node).parent) + os.pathsep + env.get('PATH', '')
    env.update(PYTHONUNBUFFERED='1', NUMBA_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', OMP_NUM_THREADS='4')
    return env
