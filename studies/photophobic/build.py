#!/usr/bin/env python3
"""Rebuild everything: each scene, then the proof, then the engine check.

  python build.py              # all three scenes (about 8 minutes on two cores)
  python build.py hortus       # one scene, then the proof
"""
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('NUMBA_NUM_THREADS', '4')
SCENES = ('hortus', 'porticus', 'memento')


def run(cwd, *args):
    t = time.time()
    print(f'> {cwd.name}: {" ".join(args)}', flush=True)
    subprocess.run([sys.executable, *args], cwd=cwd, check=True)
    print(f'  {time.time() - t:.0f}s', flush=True)


if __name__ == '__main__':
    chosen = [a for a in sys.argv[1:] if a in SCENES] or SCENES
    for name in chosen:
        run(HERE / name, 'run.py')
    run(HERE, 'proof.py')
    run(HERE / 'common', 'test_engine_unchanged.py', 'physarum_plot_original_9239ac6.py')
