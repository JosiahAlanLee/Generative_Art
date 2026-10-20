#!/usr/bin/env python3
"""Write manifest.json: sha256 of every committed file, and of the outputs build.py regenerates."""
import fnmatch, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ignored(rel, patterns):
    hit = False
    for p in patterns:
        neg = p.startswith('!'); p = p.lstrip('!')
        if p.endswith('/'):
            match = rel.startswith(p) or f'/{p}' in f'/{rel}'
        else:
            match = fnmatch.fnmatch(rel, p)
        if match:
            hit = not neg
    return hit


if __name__ == '__main__':
    patterns = [l.strip() for l in (HERE / '.gitignore').read_text().splitlines() if l.strip() and not l.startswith('#')]
    files, regen = {}, {}
    for f in sorted(HERE.rglob('*')):
        if not f.is_file():
            continue
        rel = f.relative_to(HERE).as_posix()
        if rel == 'manifest.json' or '__pycache__' in rel or rel.endswith('.log'):
            continue
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        (regen if ignored(rel, patterns) else files)[rel] = digest
    (HERE / 'manifest.json').write_text(json.dumps(dict(files=files, regenerated=regen), indent=1) + '\n')
    print(f'manifest.json: {len(files)} committed files, {len(regen)} regenerated')
