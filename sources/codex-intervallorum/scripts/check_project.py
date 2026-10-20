#!/usr/bin/env python3
"""Check the migration's source inputs, local documentation links, and bound title."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--built', action='store_true')
    parser.add_argument('--edition', choices=['all', 'reading', 'illustrated'], default='all')
    args = parser.parse_args()
    spec = json.loads((ROOT / 'migration-source-manifest.json').read_text())
    problems = []
    assets = 0
    for item in spec['files']:
        path = ROOT / item['path']
        if not path.is_file():
            problems.append('Missing imported input: ' + item['path'])
        elif path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.ttf', '.otf', '.woff', '.woff2', '.svg', '.pdf'}:
            data = path.read_bytes()
            digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if digest != item['sha']:
                problems.append('Imported artwork/font/cipher bytes changed: ' + item['path'])
            assets += 1
    documents = {ROOT / item['path'] for item in spec['files'] if item['path'].endswith('.md')}
    documents.update([ROOT / 'README.md', ROOT / 'docs/BUILD.md', ROOT / 'docs/MIGRATION.md',
                      *ROOT.glob('books/*/README.md'), ROOT / 'docs/reviews/Justin_Sledge_Review.md',
                      *ROOT.glob('docs/research/**/*.md')])
    for p in sorted(documents):
        for target in re.findall(r'\]\(([^)]+)\)', p.read_text()):
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            if not (p.parent / unquote(parsed.path)).exists():
                problems.append(f'{p.relative_to(ROOT)}: missing link {target}')
    if args.built:
        import fitz
        outputs = []
        if args.edition in {'all', 'reading'}:
            outputs.append(ROOT / 'binding/out/Codex_Intervallorum_reading.pdf')
        if args.edition in {'all', 'illustrated'}:
            outputs.append(ROOT / 'binding/out/illustrated/Codex_Intervallorum_illustrated.pdf')
        for pdf in outputs:
            with fitz.open(pdf) as doc:
                first = doc[0].get_text()
                if 'CODEX INTERVALLORUM' not in first or 'Libri Septem' not in first:
                    problems.append('Missing new cover title/subtitle: ' + pdf.name)
                if 'Codex Intervallorum' not in doc.metadata.get('title', ''):
                    problems.append('Missing new PDF metadata title: ' + pdf.name)
    if problems:
        raise SystemExit('\n'.join(problems))
    print(f'Project check passed: {len(spec["files"])} imported paths; {assets} original visual/font inputs verified.')


if __name__ == '__main__':
    main()
