"""Sparse pen finishing for the illustrated binding; never redraw source content.

The only additions are vector strokes in inspected paper. Selection is stable by
component and local source page, not by physical folio. Cipher/key leaves, Tarot
leaves, the bibliography, plates, alignment blanks and illustrations are excluded
from pen finishing. The four large scene illustrations receive an external mount.

    python binding/scribal.py INPUT.pdf [OUTPUT.pdf]

A binding-log.json beside INPUT is required. A separate output is useful for
comparison; the illustrated binder applies this pass in place. No source PDF or
art asset is changed. scribal-log.json records every actual addition and its box.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re

import fitz
import numpy as np

VERSION = 'scribal-1'
INK = (90 / 255, 67 / 255, 49 / 255)
RED = (139 / 255, 42 / 255, 34 / 255)
GRAPHITE = (40 / 255, 39 / 255, 34 / 255)
STAMP = 'CodexIntervallorum:scribal-1'
LEGACY_STAMP = 'LibrumQuinque:' + VERSION
SCENES = {
    ('Clavis', 2),
    ('Clavicula Matricis et Intervallorum', 2),
    ('De Vinculis', 2),
    ('De Vinculis', 27),
}
EXCLUDED = re.compile(
    r'cipher|inscription|scriptura|scripturae|twelve.mark|three uses of marks|'
    r'clavis.*word|register of propositions|index|seven operations|'
    r'reference|bibliograph|production|scales?', re.I)


def seed_for(title, local):
    return int.from_bytes(hashlib.sha256(f'{VERSION}/{title}/{local}'.encode()).digest()[:8], 'big')


def lines(page):
    return [line for block in page.get_text('dict')['blocks'] for line in block.get('lines', [])]


def text_boxes(page):
    # Protect the whole text box, including whitespace inside a word or glyph.
    return [fitz.Rect(s['bbox']) + (-1.5, -1.5, 1.5, 1.5)
            for line in lines(page) for s in line['spans']]


def clear(page, rect, protected, extra=()):
    """Require paper, clear of every text span, image, and previously added mark.

    The rendered check also sees vector ciphers and geometry, not just PDF text.
    A few light paper specks are permitted; a dark stroke is never permitted.
    """
    rect = fitz.Rect(rect)
    if not (page.rect + (8, 8, -8, -8)).contains(rect):
        return False
    if any(rect.intersects(b) for b in [*protected, *extra]):
        return False
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=rect, alpha=False)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3]
    if not a.size:
        return False
    return bool(a.min() >= 140 and (a.mean(axis=2) < 185).mean() < .003)


def bezier(shape, controls, color, width=.37):
    shape.draw_bezier(*(fitz.Point(*p) for p in controls))
    shape.finish(color=color, width=width, lineCap=1, lineJoin=1, closePath=False)


def pen(page, rect, kind, rng):
    """Open loops and returning quill strokes; deliberately no alphabet or seal."""
    x, y, w, h = rect.x0, rect.y0, rect.width, rect.height
    color = GRAPHITE if rng.random() < .23 else INK
    shape = page.new_shape()
    def b(q, width=.37):
        bezier(shape, [(x + a*w, y + z*h) for a,z in q], color, width)
    if kind == 'capital-flourish':
        # A cadel at the shoulder of an ordinary heading's opening capital.
        # It remains outside the letter's protected box, without replacing it.
        variant=rng.randrange(3)
        if variant==0:
            k = rng.uniform(.05, .14)
            b([(.88,.87),(.05,.98),(.04,.21),(.57,.23)], .42)
            b([(.57,.23),(.98,k),(.94,.63),(.35,.48)], .31)
            b([(.35,.48),(.05,.36),(.12,.03),(.78,.10)], .24)
        elif variant==1:
            b([(.86,.92),(.01,.82),(.91,.36),(.39,.11)], .39)
            b([(.39,.11),(.05,-.01),(.02,.29),(.60,.24)], .26)
            b([(.60,.24),(.88,.15),(.89,.03),(.72,.05)], .20)
            b([(.43,.45),(.11,.65),(.12,.78),(.24,.84)], .19)
        else:
            b([(.84,.85),(.11,1.0),(.19,.30),(.72,.08)], .40)
            b([(.72,.08),(.92,-.01),(.99,.30),(.52,.36)], .24)
            b([(.52,.36),(.12,.42),(.01,.68),(.31,.72)], .26)
            b([(.24,.65),(.05,.53),(.18,.19),(.52,.15)], .19)
    elif kind == 'terminal':
        k = rng.uniform(.35,.62)
        b([(.05,.61),(.23,.18),(.36,.92),(.57,.51)], .34)
        b([(.57,.51),(.92,-.01),(.99,.95),(.70,k)], .26)
        b([(.12,.66),(.45,.60),(.74,.68),(.97,.36)], .19)
    else:
        # A short pen trial in the outer margin, without a pointing hand.
        b([(.77,.10),(.03,.13),(.95,.85),(.28,.89)], .37)
        b([(.28,.89),(.02,.86),(.05,.59),(.58,.62)], .25)
        b([(.33,.20),(.76,.41),(.08,.52),(.71,.75)], .19)
    shape.commit(overlay=True)


def scene_mount(page):
    """Frame the complete scene; no image masking, repainting, or resampling."""
    info = page.get_image_info()
    if len(info) != 1:
        return []
    image = fitz.Rect(info[0]['bbox'])
    if image.width < 400 or image.height < 500:
        return []
    # Four isolated strips keep the protected rectangle away from the picture.
    outer = image + (-3.6, -3.6, 3.6, 3.6)
    strips = [fitz.Rect(outer.x0, outer.y0, outer.x1, image.y0-1.4),
              fitz.Rect(outer.x0, image.y1+1.4, outer.x1, outer.y1),
              fitz.Rect(outer.x0, image.y0-1.4, image.x0-1.4, image.y1+1.4),
              fitz.Rect(image.x1+1.4, image.y0-1.4, outer.x1, image.y1+1.4)]
    protected = text_boxes(page)
    if not all(clear(page, r, protected, [image]) for r in strips):
        return []
    shape = page.new_shape()
    shape.draw_rect(image + (-2.1,-2.1,2.1,2.1))
    shape.finish(color=INK, width=.36, closePath=False)
    # Short paired corner strokes recall the plate mounts without adding symbols.
    for x, y, sx, sy in ((image.x0-3.15,image.y0-3.15,1,1),
                         (image.x1+3.15,image.y0-3.15,-1,1),
                         (image.x0-3.15,image.y1+3.15,1,-1),
                         (image.x1+3.15,image.y1+3.15,-1,-1)):
        shape.draw_polyline([(x,y+sy*10),(x,y),(x+sx*10,y)])
        shape.finish(color=INK, width=.22, closePath=False)
    shape.commit(overlay=True)
    return strips


def finish_page(page, title, local):
    if (title, local) in SCENES:
        return [dict(kind='scene-mount',rect=list(r)) for r in scene_mount(page)]
    if title == 'Tarot of Intervals' or 'nota clausa' in title.casefold() or page.get_images():
        return []
    ll = lines(page)
    if any('NOTA CLAUSA' == ''.join(s['text'] for s in l['spans']).strip().upper()
           for l in ll if l['bbox'][1]<70):
        return []
    headings = [l for l in ll if 68 < l['bbox'][1] < 150 and 40 <= l['bbox'][0] <= 60
                and any(17 <= s['size'] <= 30 for s in l['spans'])]
    body = [l for l in ll if 70 < l['bbox'][1] < 659 and l['bbox'][0] < 65
            and any(9.5 <= s['size'] <= 13 for s in l['spans'])
            and len(''.join(s['text'] for s in l['spans'])) > 35]
    heading = ' '.join(s['text'] for l in headings for s in l['spans'])
    if len(body) < 8 or len(page.get_drawings()) > 160 or EXCLUDED.search(heading):
        return []
    rng = random.Random(seed_for(title, local))
    selection = rng.random()
    if (title,local)==('Clavis',3):selection=.12
    if selection > .48:
        return []
    protected = text_boxes(page); used=[]; result=[]
    def add(r, kind):
        r=fitz.Rect(r)
        if clear(page,r,protected,used):
            pen(page,r,kind,rng); used.append(r)
            result.append(dict(kind=kind,rect=[round(v,3) for v in r]))
            return True
        return False
    if headings and selection < .32:
        r=fitz.Rect(headings[0]['bbox'])
        w=rng.uniform(11,15); h=rng.uniform(23,29)
        add((r.x0-w-3,r.y0-2,r.x0-3,r.y0-2+h),'capital-flourish')
    if not result and selection < .31:
        # Margin side follows the leaf; leave the gutter completely clear.
        b=body[min(len(body)-1,rng.randrange(2, min(9,len(body))))]['bbox']
        x=469 if local%2 else 22
        add((x,b[1]+2,x+11,b[1]+34),'pen-trial')
    if not result:
        # Only genuinely free end-of-text space, above the folio; no long rule.
        low=max(l['bbox'][3] for l in ll if 70<l['bbox'][1]<660)
        if 200<low<615:
            w=rng.uniform(31,43); x=rng.uniform(59,78)
            add((x,low+14,x+w,low+24),'terminal')
    return result


def vector_record(page):
    # seqno reflects stream ordering, not the geometry itself.
    return [{k:v for k,v in d.items() if k != 'seqno'} for d in page.get_drawings()]


def verify(original, finished, records):
    """Exact source text/images/paths, and pixel identity outside declared additions."""
    if len(original)!=len(finished) or original.get_toc()!=finished.get_toc():
        raise ValueError('Page count or outline changed')
    by_page={r['page']:r['marks'] for r in records}
    changed_pixels=0
    for i,(before,after) in enumerate(zip(original,finished),1):
        if before.rect!=after.rect or before.get_text('rawdict')!=after.get_text('rawdict'):
            raise ValueError(f'Text or trim changed on page {i}')
        bi=before.get_image_info(hashes=True); ai=after.get_image_info(hashes=True)
        if bi!=ai:
            raise ValueError(f'Image changed on page {i}')
        bv=vector_record(before); av=vector_record(after)
        if bv!=av[:len(bv)] or (i not in by_page and bv!=av):
            raise ValueError(f'Original vector geometry changed on page {i}')
        def links(p):
            return [{k:v for k,v in l.items() if k not in ('xref','id')} for l in p.get_links()]
        if links(before)!=links(after):
            raise ValueError(f'Link changed on page {i}')
        if i not in by_page:
            continue
        bp=before.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        ap=after.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        a=np.frombuffer(bp.samples,dtype=np.uint8).reshape(bp.height,bp.width,bp.n)
        b=np.frombuffer(ap.samples,dtype=np.uint8).reshape(ap.height,ap.width,ap.n)
        diff=np.any(a!=b,axis=2); allowed=np.zeros(diff.shape,dtype=bool)
        for mark in by_page[i]:
            r=fitz.Rect(mark['rect'])+(-.6,-.6,.6,.6)
            x0,y0,x1,y1=(r*2).irect
            allowed[max(0,y0):y1,max(0,x0):x1]=True
        if np.any(diff & ~allowed):
            raise ValueError(f'Undeclared rendered change on page {i}')
        changed_pixels+=int(diff.sum())
    return dict(pages=len(original),text_exact=True,images_exact=True,
                original_vector_paths_exact=True,links_and_outline_exact=True,
                changes_confined_to_clear_paper=True,changed_pixels=changed_pixels)


def apply(pdf, output=None, log_path=None):
    pdf=Path(pdf); output=Path(output or pdf)
    log=json.loads(Path(log_path or pdf.with_name('binding-log.json')).read_text())
    original=fitz.open(pdf)
    keywords = original.metadata.get('keywords') or ''
    if STAMP in keywords or LEGACY_STAMP in keywords:
        original.close()
        raise ValueError('This PDF already has scribal finishing; rebuild or use the original binding')
    doc=fitz.open(pdf); records=[]
    for title,entry in log.items():
        if not isinstance(entry,dict) or 'source' not in entry:
            continue
        for local,physical in entry['body_page_map'].items():
            marks=finish_page(doc[physical-1],title,int(local))
            if marks:
                records.append(dict(page=physical,book=title,source_page=int(local),marks=marks))
    tmp=output.with_name(output.name+'.scribal-tmp')
    try:
        metadata=doc.metadata
        metadata['keywords']=((metadata.get('keywords') or '')+'; '+STAMP).lstrip('; ')
        doc.set_metadata(metadata)
        doc.save(tmp,garbage=3,deflate=True,no_new_id=True); doc.close()
        with fitz.open(tmp) as finished:
            checks=verify(original,finished,records)
        original.close(); tmp.replace(output)
    except Exception:
        doc.close();original.close();tmp.unlink(missing_ok=True)
        raise
    report=dict(version=VERSION,decorated_pages=len(records),
                marks=dict(Counter(m['kind'] for r in records for m in r['marks'])),
                verification=checks,pages=records)
    output.with_name('scribal-log.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='pages'}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path,nargs='?')
    args=parser.parse_args();apply(args.input,args.output)

