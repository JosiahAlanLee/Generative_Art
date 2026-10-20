"""Bind reading pages and rebuild a single, consistently typeset back section."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re

import fitz
from pypdf import PdfReader,PdfWriter
from pypdf.annotations import Link
from pypdf.generic import ArrayObject,NameObject
from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas

import backmatter


MOVE_HEADINGS={
    'Clavicula Matricis et Intervallorum':('The joined setting',),
    'Pseudomonarchia Escalationum':('The workshop record',),
    'Ars Notoria Stigmatum':('Colophon of the unsealed gathering',),
    'Tarot of Intervals':('Of this edition',),
    'Clavis':('Production and source notes',),
    'De Officio Accusatoris':('Production and source notes',),
    'De Matribus Noctis':('Production and source notes',),
    'De Potestate et Accusatione':('Production and source notes',),
    'De Vinculis':('Production and source notes',),
}
# Shared-renderer components file their moved preparation leaf under the group label they set.
NOTE_TITLES={'Clavis':'VII / preparation','De Vinculis':'VII / preparation','De Officio Accusatoris':'Accusator / preparation',
             'De Matribus Noctis':'Matres / preparation','De Potestate et Accusatione':'VI / preparation'}
# Components whose bracketed keys link to their own register: the link text, the
# key prefix in the end bibliography. The binder points each link at the reflowed entry.
# Book VI links the key alone, so its link box can catch part of a bracket or comma.
CITATIONS={'Clavis':(r'\s*\[(S\d+)\]\s*','VII/'),'De Vinculis':(r'\s*\[(S\d+)\]\s*','VII/'),
           'De Potestate et Accusatione':(r'\W*([A-Z]\d+)\W*','VI/')}
SEPTIMUS=('Clavis','De Vinculis');BOOK_VI=('De Potestate et Accusatione',)
DATE=re.compile(r'\b(?:\d{1,2}\s+oct(?:ober)?\s+2026|2026-\d\d-\d\d)\b',re.I)


def normalized(text):return ' '.join(text.split())


def clean_source(title,path,repo):
    """Move dedicated production leaves; remove only identified metadata lines.

    Text removal leaves the original background and all image/vector carriers.
    Exact removed lines and rectangles are recorded for validation and the notes.
    """
    doc=fitz.open(path);moved=[];notes=[];redactions=[]
    for i,page in enumerate(doc):
        lines=page.get_text().splitlines()
        if any(h in lines for h in MOVE_HEADINGS.get(title,())):
            moved.append(i+1)
            blocks=[b[4] for b in page.get_text('blocks') if 48<b[1]<650 and b[6]==0]
            paragraphs=[normalized(s) for s in blocks]
            paragraphs=[p.replace(' This draft has not been inserted into the omnibus; its end bibliography is prepared for later relocation by the binder when Book V is integrated.','') for p in paragraphs]
            # A leaf set by the shared renderer repeats its own heading and group
            # labels (e.g. "VII / preparation"); the back section supplies both.
            paragraphs=[p for p in paragraphs if p.casefold() not in ('production and source notes','production and source notes, continued')
                        and not re.fullmatch(r'[A-Za-z0-9-]+ / [A-Za-z ]+',p)]
            note_title=NOTE_TITLES.get(title,title+' / workshop record')
            notes.append(dict(title=note_title,paragraphs=paragraphs))
            continue
        targets=[]
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                text=''.join(s['text'] for s in line['spans']).strip();rect=fitz.Rect(line['bbox'])
                is_margin=rect.y0<80 or rect.y0>610
                if ((i==0 and ('josiah' in text.lower() or DATE.search(text) or re.search(r'THIRD DIVERGENT|REVISED MANUSCRIPT|COMBINED READING EDITION',text)))
                    or (is_margin and DATE.search(text))
                    or re.search(r'^prepared (?:by|for)\b',text,re.I)):
                    targets.append((rect,text))
        if title=='Clavicula Graduum':
            b=json.loads((repo/'books/04_graduum/manuscript/book.json').read_text())
            hands=re.sub(r'^\[V\]\s*','',b['back']['hands'])
            hand_rects=page.search_for(hands)
            if hand_rects:
                first=hand_rects[0]
                for block in page.get_text('dict')['blocks']:
                    for line in block.get('lines',[]):
                        text=''.join(s['text'] for s in line['spans']).strip();rect=fitz.Rect(line['bbox'])
                        if text=='[V]' and rect.x1<first.x0 and abs(rect.y0-first.y0)<10:targets.append((rect,text))
            for rect in hand_rects:
                text=page.get_textbox(rect);targets.append((rect,text))
        unique=[]
        for rect,text in targets:
            if any(abs(rect.x0-r[0].x0)<.5 and abs(rect.y0-r[0].y0)<.5 for r in unique):continue
            unique.append((rect,text))
            page.add_redact_annot(rect,fill=None,cross_out=False)
            redactions.append(dict(source_page=i+1,rect=list(rect),text=text))
        if unique:page.apply_redactions(images=0,graphics=0,text=0)
    # The dated lines are filed once in their original order, in the back section.
    # Authorship and edition dates are rendered once from the canonical book
    # records. The original label spellings remain in the redaction audit.
    raw=doc.tobytes(garbage=3,deflate=True);doc.close()
    return raw,moved,notes,redactions


def front(c,b,books,present,bibliography):
    # Four front leaves retain the established recto convention. Preparation
    # labels, authorship credits, and edition dates are confined to the back.
    b.paper(c);c.setFillColor(colors.HexColor(b.INK));c.setFont('FellSC',30)
    c.drawCentredString(252,470,'CODEX INTERVALLORUM');c.setFont('FellIt',13)
    c.drawCentredString(252,439,'Libri Septem');c.showPage()
    b.paper(c);c.setFillColor(colors.HexColor(b.INK));c.setFont('FellSC',18);c.drawCentredString(252,640,'The Books')
    y=594
    row_gap=40 if len(books)>8 else 46 if len(books)>6 else 58
    for num,title,sub,path,hand in books:
        c.setFont('FellSC',11);c.drawString(52,y,b.numeral(num))
        c.drawString(103,y,title if num!='Companion' else 'Companion: '+title)
        c.setFont('FellIt',10)
        for line in b.wrapped_lines(sub,'FellIt',10,350):c.drawString(103,y-17,line);y-=14
        c.setFont('Mono',8);p=present.get(num)
        c.drawString(103,y-22,f'pages {p[0]}–{p[1]}' if p else 'not bound in this edition');y-=row_gap
    y=min(y-8,190)
    c.setFont('FellSC',12);c.drawString(103,y,'Bibliography and Production Notes');c.setFont('Mono',8)
    c.drawString(103,y-16,f"pages {bibliography['start_page']}–{bibliography['end_page']}")
    c.showPage()
    b.paper(c);c.setFillColor(colors.HexColor(b.INK));c.setFont('FellSC',15);c.drawCentredString(252,624,'Of the Binding')
    lines=[
        'The Clavis opens the volume: a plain-prose way into the books.',
        'A parable of the accuser follows it; its charges are left open.',
        'The opening pair is joined; its disagreements remain available for reading.',
        'The later books retain their separate questions, figures and intervals.',
        'Book VI holds authority, harm and blame apart. Its plates face their sections.',
        'A parable of the night mothers precedes it; none of them is the first.',
        'De Vinculis follows as Book VII, and the Nota Clausa closes it.',
        'The Tarot of Intervals, once Book VI, is kept as a separate volume.',
        '',
        'Citation keys remain local to their book. The source register and the',
        'workshop records are gathered in one setting at the end of the volume.',
        'Black records an arrangement; red marks an intervention or a question.',
    ]
    c.setFont('Fell',11)
    for i,line in enumerate(lines):c.drawCentredString(252,575-i*18,line)
    c.showPage();b.paper(c);c.showPage();c.save()


def citation_links(original,title):
    """(link, end-bibliography key) for each bracketed citation on a source leaf.

    Book VI links nothing else internally, so an unreadable internal link there is
    an error rather than a link left pointing at a register that has moved. Each
    key read from its link box must also head an entry on the standalone register
    leaf the link pointed to.
    """
    pattern,prefix=CITATIONS[title];found=[]
    for link in original.get_links():
        match=re.fullmatch(pattern,original.get_textbox(link['from']))
        if title in BOOK_VI and link['kind'] in (fitz.LINK_GOTO,fitz.LINK_NAMED):
            number=link.get('page',-1)
            # MuPDF exposes /Fit destinations as named links with one-based
            # numeric strings; ordinary GOTO page numbers are zero-based ints.
            if link['kind']==fitz.LINK_NAMED and isinstance(number,str) and number.isdecimal():
                number=int(number)-1
            target=original.parent[number] if match and isinstance(number,int) and 0<=number<len(original.parent) else None
            labels={k for line in (target.get_text().splitlines() if target else []) for k in line.strip().split(' / ')}
            if not match or prefix+match[1] not in labels:
                raise ValueError(title+': unreadable citation link on source page '+str(original.number+1))
        if match:found.append((link,prefix+match[1]))
    return found


def relink(writer,log,entries,repo,titles):
    """Reconnect bracketed citations to the reflowed end bibliography."""
    destinations={key:entry['start_page'] for entry in entries for key in entry['keys']}
    count=0
    for title in titles:
        if title not in log:continue
        entry=log[title]
        with fitz.open(repo/entry['source']) as source:
            for local,physical in entry['body_page_map'].items():
                original=source[int(local)-1];page=writer.pages[physical-1]
                replacements=[]
                for link,key in citation_links(original,title):
                    if key not in destinations:raise ValueError('Missing citation destination: '+key)
                    r=link['from'];rect=(r.x0,original.rect.height-r.y1,r.x1,original.rect.height-r.y0)
                    replacements.append((rect,destinations[key]))
                if not replacements:continue
                retained=[]
                for ref in page.get('/Annots',[]):
                    annotation=ref.get_object();rect=annotation.get('/Rect',[])
                    replaced=annotation.get('/Subtype')=='/Link' and any(
                        len(rect)==4 and all(abs(float(a)-b)<.1 for a,b in zip(rect,r)) for r,_ in replacements)
                    if not replaced:retained.append(ref)
                page[NameObject('/Annots')]=ArrayObject(retained)
                for rect,target in replacements:
                    annotation=writer.add_annotation(physical-1,Link(rect=rect,target_page_index=target-1))
                    annotation['/Dest'][0]=writer.pages[target-1].indirect_reference
                    count+=1
    return count


def relink_septimus(writer,log,entries,repo):
    """Reconnect bracketed S-citations to the reflowed end bibliography."""
    return relink(writer,log,entries,repo,SEPTIMUS)


def main(b,out):
    repo=Path(b.REPO);out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);b.fonts()
    records,notes,inputs=backmatter.collect(b.BOOKS,repo)
    notes.insert(0,dict(title='The volume / preparation and authorship',paragraphs=[
        'Project, text direction, and artwork: Josiah Alan-Lee, with Claude and ChatGPT/Codex. The consolidated opening and the uniform bibliography setting were prepared with ChatGPT/Codex on 17 October 2026. Individual workshop accounts below retain their original attribution and preparation dates.',
        'The reading editions combine raster illustration, vector geometry, and selectable type. Preparation records identify their makers; they do not authenticate historical claims. The separate plotter masters retain their own physical-testing limits.'
    ]))
    body=PdfWriter();page_no=5;present={};log={};source_records=[]
    for num,title,sub,path,hand in b.BOOKS:
        if not path:continue
        source=repo/path
        bib=b.bibliography_pages(title,str(source))
        raw,production,extra,redactions=clean_source(title,source,repo)
        notes+=extra;reader=PdfReader(io.BytesIO(raw));alignment=[]
        if title=='Tarot of Intervals' and 2 in production:
            with fitz.open(stream=raw,filetype='pdf') as original:
                if len(original)>2 and not original[2].get_text().strip() and not original[2].get_images():alignment=[3]
        skip=set(bib+production+alignment)
        blank_before=page_no%2==0
        if blank_before:body.add_page(b.blank_leaf());page_no+=1
        start=page_no;mapping={};blanks=[]
        for n,p in enumerate(reader.pages,1):
            if n in skip:continue
            if page_no%2!=n%2:body.add_page(b.blank_leaf());blanks.append(page_no);page_no+=1
            b.add_source_page(body,p,num);mapping[str(n)]=page_no;page_no+=1
        present[num]=(start,page_no-1)
        entry=dict(source=path,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_pages=len(reader.pages),
                   pages=page_no-start,start_page=start,end_page=page_no-1,blank_before=blank_before,
                   body_page_map=mapping,body_blank_pages=blanks,bibliography_source_pages=bib,
                   production_source_pages=production,omitted_alignment_source_pages=alignment,metadata_redactions=redactions)
        log[title]=entry
        source_records.append(dict(book=num,title=title,source=path,bibliography_source_pages=bib,production_source_pages=production))
    # The old colophon is now part of the uniform back section, after the books.
    if page_no%2==0:body.add_page(b.blank_leaf());page_no+=1
    bib_start=page_no;buf=io.BytesIO();c=Canvas(buf,pagesize=(504,720),invariant=1,pageCompression=1)
    apparatus=backmatter.write(c,records,notes,bib_start,repo);c.save();buf.seek(0)
    bibliography=dict(mode='typeset',start_page=bib_start,end_page=apparatus['end_page'],
        record_count=apparatus['record_count'],keys=apparatus['keys'],entries=apparatus['entries'],sections=apparatus['sections'],
        source_sections=source_records,source_pages=sum(len(s['bibliography_source_pages']) for s in source_records),input_sha256=inputs)
    frontbuf=io.BytesIO();front(Canvas(frontbuf,pagesize=(504,720),invariant=1),b,b.BOOKS,present,bibliography);frontbuf.seek(0)
    w=PdfWriter()
    for p in PdfReader(frontbuf).pages:w.add_page(p)
    for p in body.pages:w.add_page(p)
    for p in PdfReader(buf).pages:w.add_page(p)
    septimus_links=relink(w,log,apparatus['entries'],repo,SEPTIMUS)
    book_vi_links=relink(w,log,apparatus['entries'],repo,BOOK_VI)
    w.add_outline_item('Title',0);w.add_outline_item('The Books',1)
    for num,title,sub,path,hand in b.BOOKS:
        if num in present:w.add_outline_item(b.label(num,title),present[num][0]-1)
    parent=w.add_outline_item('Bibliography and Production Notes',bib_start-1)
    for section in apparatus['sections']:w.add_outline_item(section['title'],section['page']-1,parent=parent)
    w.add_metadata({'/Title':'Codex Intervallorum — Libri Septem','/Author':'Josiah Alan-Lee'})
    with out.open('wb') as f:w.write(f)
    log.update(total_pages=len(w.pages),front_matter_pages=4,colophon_page=None,bibliography=bibliography,
               septimus_citation_links=septimus_links,book_vi_citation_links=book_vi_links)
    out.with_name('binding-log.json').write_text(json.dumps(log,indent=2)+'\n')
    out.with_name('bibliography-records.json').write_text(json.dumps(dict(references=records,production_notes=notes),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(pdf=str(out),pages=len(w.pages),references=apparatus['record_count'],bibliography_start=bib_start,production_notes=len(notes))))

