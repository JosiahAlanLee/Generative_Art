#!/usr/bin/env python3
"""Build reading-size, before/after figure and Graduum material proofs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import fitz
from reportlab.pdfgen.canvas import Canvas

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'common/illum'))
import figure_growth as fg
import furniture as fu
import raster

PLATES=ROOT/'books/04_graduum/illustrated'
SELECT=['II','IV','V','VI','VII','VIII','X']


def main():
    out=ROOT/'binding/out/illustrated';out.mkdir(parents=True,exist_ok=True)
    temp=ROOT/'build/figure-growth-proof';temp.mkdir(parents=True,exist_ok=True)
    path=temp/'progression.pdf'
    fu.fonts();c=Canvas(str(path),pagesize=(1008,720),invariant=1,pageCompression=1)
    fu.ground(c,1008,720)
    c.setFillColorRGB(*fu.rgb(fu.INK));c.setFont('FellTitle',27)
    c.drawString(42,666,'One figure, four stages')
    c.setFont('Fell',12)
    c.drawString(42,642,'The same source and field; increasing replacement, with cornmeal sampled along the flow.')
    source=sorted((ROOT/'references/raster').glob('batch-*/gremory-raster-reference-v*.png'))[-1]
    keyed,meta=raster.key(str(source))
    samples=[]
    for i,amount in enumerate([0,.30,.60,.82]):
        c._figure_growth=dict(section='proof',index=i,total=4,amount=amount)
        c._figure_growth_records=[]
        appearance,details=fg.appearance(c,keyed,meta,(232,448));samples.append(details)
        c.setFont('FellSC',11);c.drawCentredString(126+i*252,610,['Source appearance','Early transition','Developing field','Later transition'][i])
        c.saveState();c.setBlendMode('Multiply');c.drawImage(appearance,10+i*252,146,232,448,preserveAspectRatio=True,anchor='c');c.restoreState()
        c.setFont('Mono',9);c.drawCentredString(126+i*252,123,f'MASK CONTROL {amount:.2f}')
    c.setFont('Fell',12)
    c.drawString(42,78,'Book III begins untouched and rises to 0.38. Graduum continues from 0.43 to 0.86.')
    c.drawString(42,59,'Heads, held objects and red interventions retain protected cores with feathered shoulders.')
    c.save()

    # Generate genuine untreated leaves from the same adapter and live sources.
    # The environment switch also suppresses the new dark grounds and grain.
    spec=importlib.util.spec_from_file_location('graduum_art_comparison',PLATES/'plates.py')
    plates=importlib.util.module_from_spec(spec);spec.loader.exec_module(plates)
    plates.OUT=str(temp/'before')
    old=os.environ.get('GRIMOIRE_FIGURE_GROWTH')
    os.environ['GRIMOIRE_FIGURE_GROWTH']='0'
    try:plates.main(SELECT)
    finally:
        if old is None:os.environ.pop('GRIMOIRE_FIGURE_GROWTH',None)
        else:os.environ['GRIMOIRE_FIGURE_GROWTH']=old
    before_manifest=json.loads((temp/'before/plates.json').read_text())
    after_manifest=json.loads((PLATES/'out/plates/plates.json').read_text())
    result=fitz.open(path);checks=[]
    for num in SELECT:
        stem='tabula-'+num.lower()+'-illustrated.pdf'
        before=fitz.open(temp/'before'/stem)
        after=fitz.open(PLATES/'out/plates'/stem)
        before_text=before[0].get_text();after_text=after[0].get_text()
        provenance_note=after_manifest[num].get('figure_source_note')
        if provenance_note:
            assert after_text.count(provenance_note+'\n')==1,(num,'missing or repeated source note')
            after_text=after_text.replace(provenance_note+'\n','',1)
        assert before_text==after_text,f'Typeset body text changed in {num}'
        # Compare the actual retained/decode records, not merely mark counts.
        for key in ['carrier_check','frame_rule','carrier_message','second_text','table_cells']:
            assert before_manifest[num].get(key)==after_manifest[num].get(key),(num,key)
        page=result.new_page(width=1008,height=746)
        page.draw_rect(page.rect,fill=(237/255,230/255,212/255),color=None)
        page.insert_text((18,17),'BEFORE / TABULA '+num,fontsize=10,color=(.22,.18,.12))
        page.insert_text((522,17),'PROGRESSIVE FIGURE / SHARED MATERIAL',fontsize=10,color=(.22,.18,.12))
        page.show_pdf_page(fitz.Rect(0,26,504,746),before,0)
        page.show_pdf_page(fitz.Rect(504,26,1008,746),after,0)
        checks.append(dict(plate=num,typeset_body_text_equal=True,added_provenance_note=provenance_note,
            carrier_records_equal=True,
            ground=after_manifest[num]['material_ground'],
            structural_grains=after_manifest[num]['cornmeal_structural_grains']))
        before.close();after.close()
    target=out/'Codex_Intervallorum_Figure_Growth_Proof.pdf'
    result.set_metadata({'title':'Codex Intervallorum — progressive figure and cornmeal proof',
                         'author':'ChatGPT/Codex'})
    result.save(target,garbage=4,deflate=True);result.close()
    record=dict(proof=str(target.relative_to(ROOT)),pages=1+len(SELECT),checks=checks,
        samples=samples,pdf_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    (out/'figure-growth-proof.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(pages=record['pages'],output=str(target),checks=checks),indent=2))


if __name__=='__main__':main()
