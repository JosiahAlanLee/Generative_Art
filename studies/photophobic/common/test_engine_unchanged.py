"""The engine's new options must not change any existing run: compare the edited
physarum_plot.py against the original (Librum_Quinque 9239ac6, vendored by Sol) on
the same inputs and seeds, bit for bit, in every culture mode that existed before.

Both engines are loaded from file paths under made-up module names, which numba's
on-disk cache cannot reload on a later run, so this check compiles into a fresh
cache directory every time."""
import importlib.util
import os
import sys
import tempfile

os.environ['NUMBA_CACHE_DIR'] = tempfile.mkdtemp(prefix='engine-check-')
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(original):
    old = load('engine_old', original)
    new = load('engine_new', HERE / 'physarum_plot.py')
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:120, 0:90]
    img = np.ones((120, 90, 3)) * 0.93
    blob = np.exp(-(((xx - 45) / 22.0) ** 2 + ((yy - 60) / 35.0) ** 2))
    img -= 0.75 * blob[..., None] * np.array([1.0, 0.9, 0.8])
    img = np.clip(img + rng.normal(0, 0.01, img.shape), 0, 1)
    pens = [('ochre', '#a8854a'), ('slate', '#1f2b30')]
    looks = (old.LOOKS['faithful'], old.LOOKS['feral'])
    cases = {'woven': dict(territories=0), 'fight': dict(territories=6),
             'home': dict(territories=6, anchors=[(0.5, 0.4, 0.06, 0.05)]),
             'symbiotic-ish repel 0': dict(territories=0, repel=0.0)}
    ok = True
    for name, kw in cases.items():
        anchors = kw.pop('anchors', None)
        outs = []
        for eng in (old, new):
            f = eng.prepare_cultures(img, 90, pens, '#f1ece0', looks, anchors=anchors)
            outs.append(eng.simulate_cultures(f, looks, 0.4, steps=120, density=0.3, seed=7, verbose=False, **kw))
        same = all(np.array_equal(outs[0][k], outs[1][k]) for k in ('trail', 'final'))
        ok &= same
        print(f'{name:22s} identical: {same}')
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
