#!/usr/bin/env python3
"""Rebuild every v2 plate, the Trail First variants and the proof."""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent


def run(*args):
    print('>', ' '.join(args), flush=True)
    subprocess.run([sys.executable, *args], check=True, cwd=ROOT)


if __name__ == '__main__':
    run('engrave.py', '--camera', 'front')
    run('engrave.py', '--camera', 'second')
    run('engrave.py', '--camera', 'front', '--plate-mm', '296', '--prefix', 'front-296mm')
    run('trail_v2.py', '--mode', 'original', '--name', 'trail-original-plate-scale')
    run('trail_v2.py', '--mode', 'guided', '--name', 'trail-guided-plate-scale')
    run('trail_v2.py', '--mode', 'guided', '--sampling', 'original', '--count', '20000', '--name', 'trail-network-20000')
    run('proof.py')
    run('manifest.py')
