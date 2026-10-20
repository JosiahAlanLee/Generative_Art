#!/usr/bin/env python3
"""Validate the parable's reading edition: text coverage, title page, bounds and the end apparatus."""
import argparse
import importlib.util
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('matres_build', ROOT / 'build.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)


CONTINUED = {'Bibliography, continued', 'Project records, continued', 'Production and source notes, continued'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate(out):
    out = Path(out); manifest = json.loads((out / 'build-manifest.json').read_text())
    for rel, digest in manifest['input_sha256'].items():
        require(b.sha(b.REPO / rel) == digest, 'stale input: ' + rel)
    pdf = out / manifest['pdf']; require(b.sha(pdf) == manifest['sha256'], 'PDF differs from its manifest')
    doc = fitz.open(pdf); require(len(doc) == manifest['pages'], 'page count differs')
    text, bounds, fonts = [], [], set()
    for i, page in enumerate(doc):
        require(abs(page.rect.width - 504) < .01 and abs(page.rect.height - 720) < .01, f'page {i + 1}: wrong trim')
        lines = []
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    if not span['text'].strip():
                        continue
                    x0, y0, x1, y1 = span['bbox']; fonts.add(span['font'])
                    if not (30 <= x0 <= x1 <= 474 and 10 <= y0 <= y1 <= 705):
                        bounds.append((i + 1, span['text'], span['bbox']))
                joined = ''.join(s['text'] for s in line['spans'])
                # Continuation headings interrupt an account split across leaves; skip them.
                if 50 < line['bbox'][1] and line['bbox'][3] < 670 and joined.strip() not in CONTINUED:
                    lines.append(joined)
        text.append('\n'.join(lines))
    require(not bounds, 'text outside safe bounds: ' + str(bounds[:5]))
    require(all(any(x in f for x in ('EBGaramond', 'IM_FELL', 'IMFell', 'IBMPlexMono')) for f in fonts), 'unexpected font: ' + str(fonts))
    # Title page as the first parable sets its own; nothing there for the binder to redact.
    first = doc[0].get_text()
    for words in ('DE MATRIBUS', 'NOCTIS', b.SUBTITLE, '[F]'):
        require(words in first, 'title page lacks ' + words)
    require('josiah' not in first.lower() and '2026' not in first, 'title page carries a byline or date')
    require(not ''.join(text[1].split()), 'the verso after the title page is not an interval leaf')
    start = manifest['bibliography_start']
    require(start > 3, 'apparatus begins before the reading text')
    body = b.norm('\n'.join(text[:start - 1])); end = b.norm('\n'.join(text[start - 1:]))
    blocks = b.source_blocks()
    for p in blocks:
        require(b.norm(p) in body, 'lost source paragraph: ' + p[:100])
        require(b.norm(p) not in end, 'source paragraph repeated in the apparatus: ' + p[:100])
    heads = [h for h, _ in b.sections()]
    require([h.split('. ', 1)[0] for h in heads] == ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'], 'sections are not numbered I-VII in order')
    at = 0
    for head in heads:
        found = body.find(b.norm(head), at)
        require(found >= 0, 'missing or misordered section heading: ' + head)
        at = found
    require(len(blocks) == manifest['source_paragraphs'], 'paragraph count changed')
    for p in doc[:start - 1]:
        require(not p.get_images(), 'unexpected image in the reading text')
    # The end apparatus: every reference and preparation note, after the reading text.
    for r in b.references():
        for key in r['keys']:
            require(key.startswith('Mat/') and b.norm(key) in end, 'missing or misprefixed bibliography key ' + key)
        require(b.norm(r['citation']) in end, 'missing citation: ' + r['citation'][:60])
        for a in r['accounts']:
            for field in ('status', 'use'):
                require(b.norm(a[field]) in end, 'missing source account: ' + a[field][:60])
    require(sorted(k for r in b.references() for k in r['keys']) == sorted(manifest['reference_keys']), 'reference keys differ')
    for note in b.NOTES:
        require(b.norm(note) in end and b.norm(note) not in body, 'preparation note misplaced: ' + note[:60])
    production = [i + 1 for i, p in enumerate(doc) if 'Production and source notes' in p.get_text().splitlines()]
    continued = [i + 1 for i, p in enumerate(doc) if 'Production and source notes, continued' in p.get_text().splitlines()]
    require(production and not continued and production[-1] == len(doc), 'preparation notes must fill one final leaf for the binder')
    result = dict(pages=len(doc), source_paragraphs=len(blocks), sections=len(heads), reference_keys=len(manifest['reference_keys']),
                  all_source_text_retained=True, text_within_bounds=True, title_page_as_first_parable=True, preparation_at_end=True)
    (out / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / 'out')
    validate(ap.parse_args().out)
