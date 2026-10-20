#!/usr/bin/env python3
"""Validate coverage and material boundaries in the generated reading editions."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

import fitz
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('septimus_build',ROOT/'build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def validate(out):
    out=Path(out);manifest=json.loads((out/'build-manifest.json').read_text())
    for rel,digest in manifest['input_sha256'].items():
        assert b.sha(b.REPO/rel)==digest, 'stale source: '+rel
    refs=json.loads((ROOT/'manuscript/references.json').read_text())
    ids={r['id'] for r in refs};results={}
    assets=json.loads((ROOT/'assets/figures.json').read_text())
    for a in assets:
        assert b.sha(ROOT/'assets'/a['asset'])==a['prepared_sha256'], 'changed image: '+a['asset']
        assert (ROOT/'assets'/a['prompt']).is_file()
        if 'original_asset' in a:
            assert b.sha(ROOT/'assets'/a['original_asset'])==a['original_asset_sha256'], 'changed archived image: '+a['original_asset']
    for kind,entry in manifest['books'].items():
        pdf=out/entry['pdf'];assert b.sha(pdf)==entry['sha256'], 'changed PDF'
        doc=fitz.open(pdf);assert len(doc)==entry['pages']
        text=[];bounds=[];fonts=set()
        for i,page in enumerate(doc):
            assert abs(page.rect.width-504)<.01 and abs(page.rect.height-720)<.01
            lines=[]
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        if not span['text'].strip():continue
                        x0,y0,x1,y1=span['bbox'];fonts.add(span['font'])
                        if not(30<=x0<=x1<=474 and 10<=y0<=y1<=705):bounds.append((i+1,span['text'],span['bbox']))
                    if 50<line['bbox'][1] and line['bbox'][3]<670:lines.append(''.join(s['text'] for s in line['spans']))
            text.append('\n'.join(lines))
        assert not bounds, 'text outside safe bounds: '+str(bounds[:5])
        assert all(any(x in f for x in ['EBGaramond','IM_FELL','IMFell','IBMPlexMono']) for f in fonts),fonts
        body=b.norm('\n'.join(text[:entry['bibliography_start']-1]));end=b.norm('\n'.join(text[entry['bibliography_start']-1:]))
        blocks=b.all_source_blocks(kind)
        for p in blocks:assert b.norm(p) in body,'lost source paragraph: '+p[:120]
        cited={x for p in blocks for x in re.findall(r'\[(S\d+)\]',p)}
        assert cited<=ids, 'unresolved source keys'
        assert {'VII/'+x for x in cited}==set(entry['reference_keys'])
        for x in cited:assert b.norm('VII/'+x) in end, 'missing bibliography key '+x
        assert 'preparedforjosiahalanlee' not in body
        assert 'preparedforjosiahalanlee' in end
        assert entry['bibliography_start']>max([x['commentarium_page'] for x in entry['tabula_pairs']] or [2])
        for pair in entry['tabula_pairs']:
            assert pair['tabula_page']%2==0 and pair['commentarium_page']==pair['tabula_page']+1
            assert ('TABULA '+pair['operation']) in doc[pair['tabula_page']-1].get_text().upper()
            assert ('COMMENTARIUM '+pair['operation']) in doc[pair['commentarium_page']-1].get_text().upper()
        reader=PdfReader(pdf);page_refs={(p.indirect_reference.idnum,p.indirect_reference.generation) for p in reader.pages};links=0
        for page in reader.pages:
            for ref in page.get('/Annots',[]):
                a=ref.get_object()
                if a.get('/Subtype')!='/Link':continue
                links+=1;dest=a.get('/Dest')
                if isinstance(dest,list) and hasattr(dest[0],'idnum'):assert (dest[0].idnum,dest[0].generation) in page_refs
        assert links>=len(cited),'missing citation links'
        if kind=='vinculis':
            assert len(entry['tabula_pairs'])==7
            seal=json.loads((out/'semiphoras.json').read_text());assert b.sv.recover(seal['names'])==tuple(seal['normalized'])
            assert len({r['id'] for r in seal['records']})==72
            for r in seal['records']:assert b.norm(r['id']) in body, 'lost seal identifier'
        results[kind]=dict(pages=len(doc),source_paragraphs=len(blocks),citation_keys=len(cited),facing_tabula_pairs=len(entry['tabula_pairs']),all_source_text_retained=True,text_within_bounds=True,preparation_at_end=True,links=links)
        doc.close()
    (out/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results))
    return results

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'out');a=ap.parse_args();validate(a.out)
