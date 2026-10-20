#!/usr/bin/env python3
"""Build Codex Intervallorum from checked-in source inputs."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(path, *args, cwd=ROOT):
    print('+', path, *args, flush=True)
    subprocess.run([sys.executable, str(ROOT / path), *map(str, args)], cwd=cwd, check=True)


def tests(folder):
    print('+ tests:', folder, flush=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                   cwd=ROOT / folder, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', choices=['all', 'reading', 'illustrated'], default='all')
    parser.add_argument('--skip-tests', action='store_true')
    parser.add_argument('--vellum-profile', choices=['light', 'full'], default='light')
    args = parser.parse_args()
    run('books/02_intervallorum/generator/build.py')
    run('books/03_escalationum/generator/build.py')
    if not args.skip_tests:
        tests('books/02_intervallorum')
        tests('books/03_escalationum')
    run('books/01_matricis_intervallorum/build.py')
    if not args.skip_tests:
        tests('books/01_matricis_intervallorum')
        tests('books/01_matricis_intervallorum/models/gate_window')
    for roman in ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii']:
        folder = f'books/04_graduum/plates/{roman}-native'
        out = ROOT / 'build/native' / roman
        run(f'{folder}/tabula_{roman}.py', out)
        if roman in ['v', 'vi', 'vii', 'viii']:
            run(f'{folder}/validate.py', out)
    run('books/04_graduum/reading/build.py')
    run('books/04_graduum/manuscript/make_book.py')
    run('books/04_graduum/build_book.py')
    run('books/05_notoria/plates/notae.py', 'all', ROOT / 'build/notae')
    run('books/05_notoria/plates/validate.py', ROOT / 'build/notae')
    run('books/05_notoria/reading/build.py')
    run('books/05_notoria/manuscript/make_book.py')
    run('books/05_notoria/manuscript/check_math.py')
    run('books/05_notoria/manuscript/make_book.py', '--validate')
    run('books/06_tarot/book/make_book.py')
    run('books/06_disputationes/plates/tabulae.py', 'all', ROOT / 'build/vi-plates')
    run('books/06_disputationes/plates/reading.py')
    run('books/06_disputationes/build.py')
    run('books/06_disputationes/validate.py')
    run('books/07_septimus/build.py')
    run('books/07_septimus/validate.py')
    run('books/07_septimus/clausa/build.py')
    run('books/07_septimus/clausa/validate.py')
    if not args.skip_tests:
        tests('books/07_septimus')
    for book in ['00_accusator', '00_matres']:
        run(f'books/{book}/build.py')
        run(f'books/{book}/validate.py')
    if not args.skip_tests:
        tests('binding')
        print('+ tests: common/illum/tests', flush=True)
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'common/illum/tests', '-v'],
                       cwd=ROOT, check=True)
    if args.edition in ['all', 'reading']:
        run('binding/bind.py')
        run('binding/validate.py', 'binding/out/Codex_Intervallorum_reading.pdf')
    if args.edition in ['all', 'illustrated']:
        run('books/03_escalationum/illustrated/build.py')
        run('books/04_graduum/illustrated/plates.py')
        run('books/04_graduum/illustrated/build.py')
        run('scripts/proof_figure_growth.py')
        run('binding/bind_illustrated.py', '--vellum-profile', args.vellum_profile)
        run('binding/validate.py', 'binding/out/illustrated/Codex_Intervallorum_illustrated.pdf')
    run('scripts/check_project.py', '--built', '--edition', args.edition)


if __name__ == '__main__':
    main()
