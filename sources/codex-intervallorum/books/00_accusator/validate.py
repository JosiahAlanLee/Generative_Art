#!/usr/bin/env python3
"""Validate the parable's reading edition: text coverage, plates, inscriptions and the end apparatus."""
import argparse
import importlib.util
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('accusator_build', ROOT / 'build.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)


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
                if 50 < line['bbox'][1] and line['bbox'][3] < 670:
                    lines.append(''.join(s['text'] for s in line['spans']))
        text.append('\n'.join(lines))
    require(not bounds, 'text outside safe bounds: ' + str(bounds[:5]))
    require(all(any(x in f for x in ('EBGaramond', 'IM_FELL', 'IMFell', 'IBMPlexMono')) for f in fonts), 'unexpected font: ' + str(fonts))
    start = manifest['bibliography_start']
    body = b.norm('\n'.join(text[:start - 1])); end = b.norm('\n'.join(text[start - 1:]))
    blocks = b.source_blocks()
    for p in blocks:
        require(b.norm(p) in body, 'lost source paragraph: ' + p[:100])
    for head, _ in b.sections():
        require(b.norm(head) in body, 'missing section heading: ' + head)
    require(len(blocks) == manifest['source_paragraphs'], 'paragraph count changed')
    # Verify both the selected illustration and its retained source, when revised.
    # Each plate remains alone on a verso facing its section's opening recto.
    figs = {f['name']: f for f in b.figures()}
    require(len(manifest['plates']) == len(figs), 'plate count differs')
    every = b.norm(' '.join(p.get_text() for p in doc))
    for plate in manifest['plates']:
        fig = figs[plate['name']]; n = plate['page']
        selected_sha = fig.get('prepared_sha256', fig['original_sha256'])
        require(b.sha(ROOT / 'assets' / fig['asset']) == selected_sha, 'plate changed: ' + fig['asset'])
        require(plate['keyed']['source_sha256'] == selected_sha, 'keyed render is not of the selected illustration')
        original_asset = fig.get('original_asset', fig['asset'])
        require(b.sha(ROOT / 'assets' / original_asset) == fig['original_sha256'], 'archived plate changed: ' + original_asset)
        require(n % 2 == 0 and n + 1 < start, fig['name'] + ': plate is not on a verso before the apparatus')
        require(len(doc[n - 1].get_images()) == 1, fig['name'] + ': expected one image on the plate leaf')
        require(b.norm(fig['caption']) in b.norm(doc[n - 1].get_text()), fig['name'] + ': exhibit caption missing')
        require(b.norm(fig['faces_section']) in b.norm(doc[n].get_text()), fig['name'] + ': does not face ' + fig['faces_section'])
        require([r['normalized'] for r in plate['inscription']] == [b.cipher.clean(s) for s in fig['inscription']], fig['name'] + ': inscription differs')
        for line in fig['inscription']:
            # The inscriptions are drawn in the hand; their plaintext is never set as type.
            require(b.norm(line) not in every, fig['name'] + ': inscription plaintext appears as text')
    for p in doc[:start - 1]:
        require(len(p.get_images()) <= 1, 'unexpected images')
    require(sum(len(p.get_images()) for p in doc) == len(figs), 'images outside the plates')
    # The end apparatus: every reference and preparation note, after the reading text.
    for r in b.references():
        for key in r['keys']:
            require(b.norm(key) in end, 'missing bibliography key ' + key)
        require(b.norm(r['citation']) in end, 'missing citation: ' + r['citation'][:60])
    require(sorted(k for r in b.references() for k in r['keys']) == sorted(manifest['reference_keys']), 'reference keys differ')
    for note in b.NOTES:
        require(b.norm(note) in end and b.norm(note) not in body, 'preparation note misplaced: ' + note[:60])
    production = [i + 1 for i, p in enumerate(doc) if 'Production and source notes' in p.get_text().splitlines()]
    continued = [i + 1 for i, p in enumerate(doc) if 'Production and source notes, continued' in p.get_text().splitlines()]
    require(production and not continued and production[-1] == len(doc), 'preparation notes must fill one final leaf for the binder')
    result = dict(pages=len(doc), source_paragraphs=len(blocks), sections=len(b.sections()), plates=len(figs),
                  reference_keys=len(manifest['reference_keys']), all_source_text_retained=True, text_within_bounds=True,
                  plates_face_their_sections=True, inscriptions_drawn_not_typed=True, preparation_at_end=True)
    (out / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / 'out')
    validate(ap.parse_args().out)
