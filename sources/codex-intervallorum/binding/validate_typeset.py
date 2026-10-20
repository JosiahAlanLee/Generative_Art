"""Validate retained body pages and the newly typeset back section."""
import hashlib
import json
from pathlib import Path
import re

import fitz
from pypdf import PdfReader
from unified import CITATIONS, citation_links
from vellum import source_images, source_image_info


def normalized(text):return ' '.join(text.split())


def validate(pdf,repo,log):
    pdf,repo=Path(pdf),Path(repo);doc=fitz.open(pdf);bib=log['bibliography'];used=set();next_page=5;spreads=0;relocated=0
    septimus_spreads=0;septimus_links=0;book_vi_plates=0;book_vi_links=0
    reader=PdfReader(pdf) if any(t in log for t in CITATIONS) else None
    page_ids={(p.indirect_reference.idnum,p.indirect_reference.generation):i+1 for i,p in enumerate(reader.pages)} if reader else {}
    destinations={key:e['start_page'] for e in bib['entries'] for key in e['keys']}
    def require(ok,message):
        if not ok:raise ValueError(message)
    def relinked(title,original,physical):
        """Each bracketed citation has one link, to its consolidated entry."""
        n=0
        for link,key in citation_links(original,title):
            rect=link['from'];expected=(rect.x0,720-rect.y1,rect.x1,720-rect.y0)
            annotations=[a.get_object() for a in reader.pages[physical-1].get('/Annots',[])]
            matching=[a for a in annotations if a.get('/Subtype')=='/Link' and len(a.get('/Rect',[]))==4
                      and all(abs(float(x)-y)<.1 for x,y in zip(a['/Rect'],expected))]
            require(len(matching)==1,title+': missing or duplicated citation link '+key)
            dest=matching[0].get('/Dest');target=dest[0] if isinstance(dest,list) and dest else None
            require(hasattr(target,'idnum') and page_ids.get((target.idnum,target.generation))==destinations.get(key),
                    title+': citation points outside its consolidated entry: '+key)
            n+=1
        return n
    require(len(doc)==log['total_pages'],'Page count differs from binding log')
    for title,e in log.items():
        if not isinstance(e,dict) or 'source' not in e:continue
        path=repo/e['source'];require(hashlib.sha256(path.read_bytes()).hexdigest()==e['source_sha256'],title+': source hash changed')
        source=fitz.open(path);body={int(k):v for k,v in e['body_page_map'].items()}
        bibl=set(e['bibliography_source_pages']);prod=set(e['production_source_pages'])
        alignment=set(e.get('omitted_alignment_source_pages',[]))
        require(not(set(body)&(bibl|prod)),title+': relocated leaf remains in the body')
        require(set(body)|bibl|prod|alignment==set(range(1,len(source)+1)),title+': unexplained missing source leaf')
        for n in alignment:require(not source[n-1].get_text().strip() and not source[n-1].get_images(),'Omitted alignment leaf contains content')
        require(e['start_page']%2==1,title+': component does not begin recto')
        require(e['start_page']==next_page+int(e['blank_before']),title+': unexplained component gap')
        require(set(body.values())|set(e['body_blank_pages'])==set(range(e['start_page'],e['end_page']+1)),title+': unexplained body leaf')
        for r in e['metadata_redactions']:
            p=source[r['source_page']-1];p.add_redact_annot(fitz.Rect(r['rect']),fill=None,cross_out=False)
        for p in source:
            if p.annots():p.apply_redactions(images=0,graphics=0,text=0)
        for local,physical in body.items():
            require(local%2==physical%2,title+': page side changed')
            require(physical not in used,title+': overlapping page');used.add(physical)
            require(normalized(source[local-1].get_text())==normalized(doc[physical-1].get_text()),title+f': body text changed on source page {local}')
        for n in e['body_blank_pages']:
            require(not doc[n-1].get_text().strip() and not source_images(doc[n-1]),'Alignment leaf is not blank')
        if title=='Tarot of Intervals':
            paging=json.loads(path.with_name(path.stem+'-log.json').read_text())
            for card in paging['cards']:
                v,r=body[card['verso']],body[card['recto']]
                require(v%2==0 and r==v+1,'Tarot facing pair changed')
                require(len(source_images(doc[r-1]))==1,'Tarot illustration missing');spreads+=1
        if title in ('Clavis','De Vinculis'):
            manifest=json.loads(path.with_name('build-manifest.json').read_text())
            kind='clavis' if title=='Clavis' else 'vinculis'
            edition=manifest['books'][kind]
            require(edition['sha256']==e['source_sha256'],title+': stale Septimus manifest')
            for pair in edition['tabula_pairs']:
                v,r=body[pair['tabula_page']],body[pair['commentarium_page']]
                require(v%2==0 and r==v+1,'Septimus Tabula and Commentarium do not face')
                septimus_spreads+=1
            for local,physical in body.items():
                original=source[local-1]
                require([i['digest'] for i in original.get_image_info(hashes=True)]==
                        [i['digest'] for i in source_image_info(doc[physical-1])],title+': illumination changed or missing')
                septimus_links+=relinked(title,original,physical)
        if title=='De Potestate et Accusatione':
            manifest=json.loads(path.with_name('build-manifest.json').read_text())
            require(manifest['sha256']==e['source_sha256'],title+': stale Book VI manifest')
            require(set(bibl)|prod==set(range(manifest['bibliography_start'],len(source)+1)),title+': register or preparation leaf left in the body')
            for plate in manifest['plates']:
                # Each plate stands alone on a verso facing the opening of its section.
                v,r=body[plate['page']],body[plate['page']+1]
                require(v%2==0 and r==v+1,title+': Tabula '+plate['numeral']+' does not face its section')
                require(not source_images(doc[v-1]) and len(doc[v-1].get_drawings())>300,title+': Tabula '+plate['numeral']+' is not the vector plate')
                require(re.search(r'\bFACING · TABULA '+plate['numeral']+r'\b',normalized(doc[r-1].get_text())),title+': section does not name Tabula '+plate['numeral'])
                book_vi_plates+=1
            require(book_vi_plates==9,'Book VI plates missing')
            internal=0
            for local,physical in body.items():
                book_vi_links+=relinked(title,source[local-1],physical)
                for a in reader.pages[physical-1].get('/Annots',[]):
                    a=a.get_object();action=a.get('/A',{})
                    if a.get('/Subtype')=='/Link' and ('/Dest' in a or action.get('/S')=='/GoTo'):
                        # A named destination left from the standalone register would dangle here.
                        dest=a.get('/Dest',action.get('/D'));target=dest[0] if isinstance(dest,list) and dest else None
                        require(hasattr(target,'idnum') and bib['start_page']<=page_ids.get((target.idnum,target.generation),0)<=bib['end_page'],
                                title+': an internal link does not reach the end bibliography');internal+=1
            require(internal==book_vi_links,title+': unexplained internal link')
        next_page=e['end_page']+1;relocated+=len(bibl)
    require(bib['start_page']%2==1 and bib['start_page'] in (next_page,next_page+1),'Back section does not follow the books')
    require(bib['end_page']==len(doc),'Bibliography is not at the end')
    if 'De Vinculis' in log:
        vi=log.get('De Potestate et Accusatione')
        require(vi is not None,'Book VII has no preceding Book VI')
        require(log['De Vinculis']['start_page'] in (vi['end_page']+1,vi['end_page']+2),
                'Book VII does not immediately follow Book VI')
        require(septimus_spreads==7,'Septimus facing pairs missing')
    clausa_fields=0
    if 'Nota Clausa' in log:
        # The sealed gathering closes Book VII: straight after De Vinculis, its seven fields intact.
        nc,vii=log['Nota Clausa'],log.get('De Vinculis')
        require(vii is not None and nc['start_page'] in (vii['end_page']+1,vii['end_page']+2),'Nota Clausa does not close De Vinculis')
        meta=json.loads((repo/nc['source']).with_name('build-meta.json').read_text())
        body={int(k):v for k,v in nc['body_page_map'].items()}
        for f in [p['page'] for p in meta['pages'] if p['title'].startswith('Field ')]:
            page=doc[body[f]-1]
            require(len(page.get_drawings())>7000 and not source_images(page),'Nota Clausa field is not its vector plate')
            clausa_fields+=1
        require(clausa_fields==7,'Nota Clausa fields missing')
    require(septimus_links==log.get('septimus_citation_links',0),'Septimus citation-link count differs')
    require(book_vi_links==log.get('book_vi_citation_links',0),'Book VI citation-link count differs')
    if bib['start_page']>next_page:require(not doc[next_page-1].get_text().strip(),'Back section alignment leaf is not blank')
    records=json.loads(pdf.with_name('bibliography-records.json').read_text())
    # Reflow can split an account across leaves; running heads and folios do
    # not interrupt the account's text for comparison.
    running={'CODEX INTERVALLORUM','BIBLIOGRAPHY','Bibliography','Bibliography, continued','Production and source notes',
             'PRODUCTION NOTES','Production and source notes, continued','Project records','Project records, continued'}
    tail=' '.join(normalized('\n'.join(line for line in p.get_text().splitlines() if line.strip() not in running and line.strip()!=str(p.number+1))) for p in doc[bib['start_page']-1:])
    for r in records['references']:
        require(normalized(r['citation']) in tail,'Bibliography citation missing: '+r['citation'][:80])
        for key in r['keys']:require(key in tail,'Bibliography key missing: '+key)
        for account in r['accounts']:
            for key in ['status','use']:
                if account.get(key):require(normalized(account[key]) in tail,'Source account missing')
    for n in records['production_notes']:
        for text in n['paragraphs']:
            require(normalized(text) in tail,'Production note missing: '+text[:70])
    for path,digest in bib['input_sha256'].items():require(hashlib.sha256((repo/path).read_bytes()).hexdigest()==digest,'Bibliographic input changed: '+path)
    for p in doc:
        require(p.rect.width==504 and p.rect.height==720,'Wrong trim')
        for block in p.get_text('dict')['blocks']:
            for line in block.get('lines',[]):require(p.rect.contains(fitz.Rect(line['bbox'])),'Text outside page bounds')
    contents=normalized(doc[1].get_text())
    for title,e in log.items():
        if isinstance(e,dict) and 'source' in e:
            require(f"pages {e['start_page']}–{e['end_page']}" in contents,title+': contents range missing')
    for p in doc[bib['start_page']-1:]:
        for block in p.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for s in line['spans']:require(s['font'].startswith(('EBGaramond','IM_FELL','IMFELL','IM_Fell')),'Unexpected backmatter font: '+s['font'])
    result=dict(pages=len(doc),components=len([e for e in log.values() if isinstance(e,dict) and 'source' in e]),facing_tarot_spreads=spreads,
                facing_septimus_spreads=septimus_spreads,septimus_citation_links=septimus_links,
                facing_book_vi_plates=book_vi_plates,book_vi_citation_links=book_vi_links,nota_clausa_fields=clausa_fields,
                all_components_start_recto=True,source_hashes_match=True,bibliography_at_end=True,bibliography_source_pages=relocated,
                typeset_references=len(records['references']),source_leaves_accounted_for=True,uniform_backmatter_fonts=True)
    pdf.with_name('binding-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


