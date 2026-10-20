#!/usr/bin/env python3
"""Validate the reading edition of Book VI: inputs, trim, text coverage in order,
tags, keys against the register, plates facing their sections, internal links and the end
apparatus. Writes out/validation.json."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

import fitz

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('vi_build', ROOT / 'build.py')
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
    book = b.parse()
    start = manifest['bibliography_start']
    texts, bounds, fonts = [], [], set()
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
                        bounds.append((i + 1, span['text'], [round(v, 1) for v in span['bbox']]))
                if 50 < line['bbox'][1] and line['bbox'][3] < 670:
                    lines.append(''.join(s['text'] for s in line['spans']))
        texts.append('\n'.join(lines))
    require(not bounds, 'text outside safe bounds: ' + str(bounds[:5]))
    require(all(any(x in f for x in ('EBGaramond', 'IM_FELL', 'IMFell')) for f in fonts), 'unexpected font: ' + str(fonts))
    body = b.norm('\n'.join(texts[:start - 1])); end = b.norm('\n'.join(texts[start - 1:]))
    # every paragraph of running text, in manuscript order
    blocks = b.source_blocks(book)
    pos = 0
    for p in blocks:
        n = b.norm(p)
        k = body.find(n, pos)
        require(k >= 0, 'lost or misordered paragraph: ' + p[:90])
        pos = k + len(n)
    require(len(blocks) == manifest['source_paragraphs'], 'paragraph count changed')
    for d in book['divisions']:
        require(b.norm(d['head'].split('. ', 1)[-1].split(': ', 1)[-1]) in body, 'missing heading: ' + d['head'])
    for c in book['claims']:
        require(b.norm(c['name']) in body, 'missing claim: ' + c['id'])
    # the tags: every tagged paragraph's tag stands in the margin of the page that opens it
    tagged = [re.match(r'\[([EDHVF])\]', p).group(1) for p in book['proem']]
    for d in book['divisions']:
        if d['kind'] == 'section':
            tagged += [blk[1] for blk in d['blocks'] if blk[0] == 'para']
    margin = []
    for page in doc[:start - 1]:
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    m = re.fullmatch(r'\[([EDHVF])\]', span['text'].strip())
                    if m and span['bbox'][2] <= b.TAGX + 1.5:
                        margin.append(m.group(1))
    require(margin[5:] == tagged, f'margin tags differ from the manuscript: {len(margin) - 5} drawn, {len(tagged)} tagged')
    # keys: every key cited resolves to the register, and every register entry is cited
    refs = {r['id'] for r in b.references()}
    text_all = b.MANUSCRIPT.read_text(encoding='utf-8')
    cited = {k.strip() for m in b.KEYS.finditer(text_all) for k in m.group(1).split(',')}
    require(cited <= refs, 'keys without a register entry: ' + str(sorted(cited - refs)))
    require(refs <= cited, 'register entries never cited: ' + str(sorted(refs - cited)))
    for r in b.references():
        for key in r['keys']:
            require(b.norm(key) in end, 'missing bibliography key ' + key)
        require(b.norm(b.backmatter.citation_form(r['citation'])) in end, 'missing citation: ' + r['citation'][:60])
    require(sorted(k for r in b.references() for k in r['keys']) == sorted(manifest['reference_keys']), 'reference keys differ')
    # internal links resolve
    dests = doc.resolve_names() if hasattr(doc, 'resolve_names') else {}
    links = [l for p in doc for l in p.get_links() if l['kind'] in (fitz.LINK_GOTO, fitz.LINK_NAMED)]
    require(links, 'no internal links')
    require(all(l.get('page', -1) >= start - 1 for l in links if l['kind'] == fitz.LINK_GOTO), 'a key link does not reach the register')
    # plates: alone on a verso, vector only, facing the opening of their section
    meta = b.plates_meta()
    require(len(manifest['plates']) == len(meta) == 9, 'plate count differs')
    sections = [d for d in book['divisions'] if d['kind'] == 'section' and d['plate']]
    for plate, d in zip(manifest['plates'], sections):
        n = plate['page']; m = meta[plate['numeral']]
        require(n % 2 == 0, plate['numeral'] + ': plate is not on a verso')
        require(b.sha(b.REPO / plate['pdf']) == manifest['input_sha256'][plate['pdf']], plate['numeral'] + ': plate file changed')
        require(m['all_passed'] and m['caption_round_trip'] and m['hidden_round_trip'], plate['numeral'] + ': plate did not validate')
        require(len(doc[n - 1].get_images()) == 0 and len(doc[n - 1].get_drawings()) > 300, plate['numeral'] + ': plate leaf is not the vector plate')
        name = d['head'].split('. ', 1)[1]
        require(b.norm(name) in b.norm(doc[n].get_text()), plate['numeral'] + ': does not face ' + d['head'])
        require(b.norm('facing tabula ' + plate['numeral']) in b.norm(doc[n].get_text()), plate['numeral'] + ': opening does not name its plate')
    require(sum(len(p.get_images()) for p in doc) == 0, 'raster images in the edition')
    # the end apparatus: preparation notes on one final leaf
    for note in b.NOTES:
        require(b.norm(note) in end and b.norm(note) not in body, 'preparation note misplaced: ' + note[:60])
    production = [i + 1 for i, p in enumerate(doc) if 'Production and source notes' in p.get_text().splitlines()]
    continued = [i + 1 for i, p in enumerate(doc) if 'Production and source notes, continued' in p.get_text().splitlines()]
    require(production and not continued and production[-1] == len(doc), 'preparation notes must fill one final leaf')
    result = dict(pages=len(doc), source_paragraphs=len(blocks), tagged_paragraphs=len(tagged), claims=len(book['claims']),
                  plates=len(manifest['plates']), reference_keys=len(manifest['reference_keys']), internal_links=len(links),
                  all_source_text_retained_in_order=True, tags_in_margin=True, keys_resolve=True, every_source_cited=True,
                  plates_face_their_sections=True, text_within_bounds=True, preparation_at_end=True)
    (out / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=ROOT / 'out')
    validate(ap.parse_args().out)
