"""One house style for citations, inspection notes, and preparation records.

Entries are read from the current manuscripts on every build. Identical complete
citations share an entry; distinct editions and inspection accounts stay distinct.
No bibliographic fact is invented to fill a missing field.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

REPO=Path(__file__).resolve().parents[1]
PW,PH=504,720
PAPER='#ede6d4';INK='#161918';RED='#a32b24';MUTE='#5a4331'


def clean(text):
    return re.sub(r'\s+',' ',re.sub(r'\*\*|(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)','',str(text))).strip()


def identity(text):
    return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower())


AUTHOR_FORMS={
    'Julien Véronèse,':'Véronèse, J.', 'Arthur Edward Waite,':'Waite, A. E.',
    'Gottfried Wilhelm Leibniz,':'Leibniz, G. W.', 'Marie-Julie Maitre,':'Maitre, M.-J.',
    'Ayodeji Ogunnaike,':'Ogunnaike, A.', 'Oludamini Ogunnaike,':'Ogunnaike, O.',
    'Thomas Aquinas,':'Aquinas, Thomas.', 'Johann Weyer,':'Weyer, J.',
    'Norton Juster,':'Juster, N.', 'Madeleine Clare Elish,':'Elish, M. C.',
    'Frederick Winslow Taylor,':'Taylor, F. W.', 'Harry Braverman,':'Braverman, H.',
    'James C. Scott,':'Scott, J. C.', 'Mark Fisher,':'Fisher, M.',
    'Jeff Jones,':'Jones, J.',
}


# Book III keeps its debts as running prose. Each debt names its source first,
# sometimes with a gloss after a colon. The prefixes below are matched against the
# catalogue as written; the citation is the same bibliographic matter in register
# form. 'rest' keeps the prose after the prefix as the account; 'full' keeps the
# whole paragraph, where glosses sit between the works it names. A paragraph that
# no longer matches falls back to the earlier sentence split.
ESCALATIONUM_HEADS=[
    ('Johann Weyer, Pseudomonarchia daemonum, appended to De praestigiis daemonum (1577); and the Ars Goetia in the Lemegeton manuscript tradition.',
     'Weyer, J. Pseudomonarchia daemonum, appended to De praestigiis daemonum (1577); and the Ars Goetia in the Lemegeton manuscript tradition.','rest'),
    ('CCRU, Pandemonium and its Matrix, ccru.net/digithype/pandemonium.htm.',
     'CCRU. Pandemonium and its Matrix. ccru.net/digithype/pandemonium.htm.','rest'),
    ('Dante Alighieri, Inferno XXI-XXII, especially XXI.106-117:',
     'Dante Alighieri. Inferno, cantos XXI-XXII, especially XXI.106-117.','full'),
    ('Norton Juster, The Phantom Tollbooth (1961):',
     'Juster, N. The Phantom Tollbooth (1961); Luigi Serafini, Codex Seraphinianus (1981); and the Voynich manuscript.','full'),
    ('Madeleine Clare Elish, Moral Crumple Zones: Cautionary Tales in Human-Robot Interaction, Engaging Science, Technology, and Society 5 (2019), 40-60. DOI: 10.17351/ests2019.260.',
     'Elish, M. C. Moral Crumple Zones: Cautionary Tales in Human-Robot Interaction, Engaging Science, Technology, and Society 5 (2019), 40-60. DOI: 10.17351/ests2019.260.','rest'),
    ('Frederick Winslow Taylor, The Principles of Scientific Management (1911), chapter II; Project Gutenberg ebook 6435.',
     'Taylor, F. W. The Principles of Scientific Management (1911), chapter II; Project Gutenberg ebook 6435.','rest'),
    ('Harry Braverman, Labor and Monopoly Capital: The Degradation of Work in the Twentieth Century (1974; Monthly Review Press anniversary edition, 1998), especially chapter 4.',
     'Braverman, H. Labor and Monopoly Capital: The Degradation of Work in the Twentieth Century (1974; Monthly Review Press anniversary edition, 1998), especially chapter 4.','rest'),
    ('James C. Scott, Seeing Like a State (Yale University Press, 1998), chapter 9; Michael Polanyi, The Tacit Dimension (1966; University of Chicago Press reissue, 2009).',
     'Scott, J. C. Seeing Like a State (Yale University Press, 1998), chapter 9; Michael Polanyi, The Tacit Dimension (1966; University of Chicago Press reissue, 2009).','rest'),
    ('Mark Fisher, Capitalist Realism: Is There No Alternative? (Zero Books, 2009), chapter 6.',
     'Fisher, M. Capitalist Realism: Is There No Alternative? (Zero Books, 2009), chapter 6.','rest'),
    ('Jidoka and andon:',
     'Toyota. Public description of the Toyota Production System: jidoka and andon. global.toyota/en/company/vision-and-philosophy/production-system/.','full'),
]


def escalationum_record(paragraph):
    """Return (citation, account) for one Book III debt."""
    for prefix,citation,mode in ESCALATIONUM_HEADS:
        if paragraph.startswith(prefix):
            account=paragraph if mode=='full' else paragraph[len(prefix):].strip()
            return citation,account
    m=re.search(r'(?<=[.;])\s+(?=(?:The |This |These |Responsibility|Practical|Market|Here ))',paragraph)
    return (paragraph[:m.start()].strip(),paragraph[m.end():].strip()) if m else (paragraph,'')


# Different books sometimes cite one source in different words. These groups
# are merged by citation key; the citation each book used stays with its account.
# A group replaces the merge by identical citation for its members, so it must name
# every key that cites the source; a key left out would become a second entry.
SAME_SOURCE=[
    {'I-II/P1','IV/M1'},   # Revisable Systems Practice, Revision 5
    {'III/D10','IV/T1'},   # Toyota's public description of its production system
    {'I-II/G3','VI/F1'},   # Freeman's Tyranny of Structurelessness, the author's composite version
    {'I-II/Q3','IV/Q3','VI/T2'},   # DORA's capabilities page on streamlining change approval
]

# Working documents, packets and repository files made within the project.
# Acc/R1-R3 are the model reviews the parable answers, filed with it.
PROJECT_KEYS={'I-II/P0','I-II/P1','I-II/P2','I-II/P3','IV/M1','IV/E3','IV/X1','V/R0','Acc/R1','Acc/R2','Acc/R3',
              # Book VI: the project's models, case record, books and research files.
              'VI/M1','VI/M2','VI/M3','VI/I4','VI/B1','VI/B2','VI/B3','VI/B4','VI/B5'}
PROJECT_PREFIXES=('Claude (2026)','ChatGPT (2026)','Systematology','Revisable Systems Practice')


# The unnumbered parables keep their sources in a register beside the manuscript.
PARABLE_REGISTERS={'De Officio Accusatoris':'books/00_accusator/manuscript/references.json',
                   'De Matribus Noctis':'books/00_matres/manuscript/references.json'}
# Book VI keeps its register the same way, but cites it in the text by bracketed key.
# Its validator requires every entry to be cited, so the whole register is collected.
BOOK_VI_REGISTER='books/06_disputationes/manuscript/references.json'


def is_project_record(record):
    return bool(PROJECT_KEYS&set(record['keys'])) or record['citation'].startswith(PROJECT_PREFIXES)


def citation_form(text):
    text=clean(text)
    for original,replacement in AUTHOR_FORMS.items():
        if text.startswith(original):return replacement+' '+text[len(original):].lstrip()
    return text


def opening_records(book):
    records=[]
    for r in book['references']:
        records.append(dict(citation=clean(r['citation']),keys=['I-II/'+r['id']],
                            accounts=[dict(book='I-II',status=clean(r['status']),use=clean(r['use']))],
                            urls=[r['url']] if r.get('url') else []))
    for i,s in enumerate(book.get('further_reading',[]),1):
        records.append(dict(citation=clean(s),keys=[f'I-II/F{i:02d}'],
                            accounts=[],urls=[]))
    return records


def collect(books,repo=REPO):
    repo=Path(repo);records=[];notes=[];inputs={}
    def read(path):
        p=repo/path;raw=p.read_bytes();inputs[path]=hashlib.sha256(raw).hexdigest();return raw.decode()
    for num,title,sub,path,hand in books:
        if not path:continue
        if title in ('Clavis','De Vinculis'):
            # Both parts share a register. Consolidation retains a shared key and
            # account once, while each included manuscript selects its own sources.
            refs=json.loads(read('books/07_septimus/manuscript/references.json'))
            manuscript='clavis.md' if title=='Clavis' else 'de-vinculis.md'
            used=set(re.findall(r'\[(S\d+)\]',read('books/07_septimus/manuscript/'+manuscript)))
            for r in refs:
                if r['id'] in used:
                    records.append(dict(citation=clean(r['citation']),keys=list(r['keys']),
                                        accounts=[dict(book=a['book'],status=clean(a.get('status','')),use=clean(a.get('use',''))) for a in r['accounts']],
                                        urls=list(r.get('urls',[]))))
            continue
        if title in PARABLE_REGISTERS or title=='De Potestate et Accusatione':
            # A parable cites nothing in its text; its register lists every source it
            # draws on. Book VI cites every entry of its register by key. Either way the
            # preparation leaf moves with the production notes (unified.MOVE_HEADINGS).
            for r in json.loads(read(PARABLE_REGISTERS.get(title,BOOK_VI_REGISTER))):
                records.append(dict(citation=clean(r['citation']),keys=list(r['keys']),
                                    accounts=[dict(book=a['book'],status=clean(a.get('status','')),use=clean(a.get('use',''))) for a in r['accounts']],
                                    urls=list(r.get('urls',[]))))
            continue
        if title=='Clavicula Matricis et Intervallorum':
            b=json.loads(read('books/01_matricis_intervallorum/manuscript/book.json'))
            records+=opening_records(b)
            notes.append(dict(title='I-II / preparation',paragraphs=[b['edition']+'.',*b.get('production_notes',[f"{b['author']}. Text and artwork developed with Claude and ChatGPT/Codex."])]))
        elif title=='Clavicula Graduum':
            b=json.loads(read('books/04_graduum/manuscript/book.json'))
            for r in b['references']:
                records.append(dict(citation=clean(r['citation']),keys=['IV/'+r['id']],accounts=[dict(book='IV',status=clean(r['status']),use=clean(r['use']))],urls=[r['url']] if r.get('url') else []))
            notes.append(dict(title='IV / preparation',paragraphs=[f"{b['author']}. {b['edition']}. {hand}.",re.sub(r'^\[V\]\s*','',b['back']['hands'])]))
        elif title=='Pseudomonarchia Escalationum':
            b=json.loads(read('books/03_escalationum/manuscript/catalogue.json'));n=0
            for section in b['back']:
                if not section['title'].startswith('A register of debts'):continue
                for s in section['paragraphs']:
                    n+=1
                    if s.startswith(('The research check','Four parables','Robert Fludd')):
                        notes.append(dict(title='III / source and formal debts',paragraphs=[s]));continue
                    # Book III's prose says what each debt is used for; its
                    # inspection limits are in the research-check note (D13).
                    citation,account=escalationum_record(s)
                    records.append(dict(citation=clean(citation),keys=[f'III/D{n:02d}'],accounts=[dict(book='III',status='',use=clean(account))],urls=[]))
            notes.append(dict(title='III / preparation',paragraphs=[f"{b['author']}. {b['edition']}. {hand}."]))
        elif title=='Ars Notoria Stigmatum':
            text=read('books/05_notoria/manuscript/reading-edition.md')
            for section in re.split(r'^## ',text,flags=re.M)[1:]:
                heading,body=section.split('\n',1)
                if '<!-- leaf: sources -->' not in body:continue
                for p in re.sub(r'<!--.*?-->','',body,flags=re.S).strip().split('\n\n'):
                    match=re.match(r'\*\*\[([^]]+)\]\s*(.*?)\*\*\s*(.*)',p,flags=re.S)
                    if match:
                        key,citation,account=match.groups()
                        markers=['Publisher record','Online transcription','Edition contents','Abstract and publication',
                                 'Official description','Full web essay','Publisher description','Article inspected','Inspected in full',
                                 'Publication metadata checked']
                        positions=[account.index(m) for m in markers if m in account]
                        cut=min(positions) if positions else 0
                        if cut:
                            citation=clean(citation)+' '+clean(account[:cut]);account=account[cut:]
                        urls=re.findall(r'https?://[^\s]+',account)
                        records.append(dict(citation=clean(citation),keys=['V/'+key],accounts=[dict(book='V',status=clean(account),use='')],urls=[u.rstrip('.,;') for u in urls]))
                    elif p.strip():notes.append(dict(title='V / source and workshop notes',paragraphs=[clean(p)]))
            notes.append(dict(title='V / preparation',paragraphs=['Ars Notoria Stigmatum. Developmental reading edition, 17 October 2026. '+hand+'.']))
        elif title=='Nota Clausa':
            # No register: the gathering cites only works already in the books' registers.
            # Its README holds the preparation record: the hand, what is withheld, the fairness test.
            text=read('books/07_septimus/clausa/README.md')
            sections={s.split('\n',1)[0].strip():s.split('\n',1)[1] for s in re.split(r'^## ',text,flags=re.M)[1:]}
            withheld=[clean(p) for p in sections['What is not here'].strip().split('\n\n')]
            fairness=[clean(p) for p in sections['Fairness record'].strip().split('\n\n')]
            hand=re.search(r'^Hand: (.+)$',text,flags=re.M)[1]
            notes.append(dict(title='Nota Clausa / preparation',paragraphs=[
                'Nota Clausa, the closing gathering of Book VII. Hand: '+hand,*withheld,*fairness]))
        else:
            notes.append(dict(title=num+' / preparation',paragraphs=[title+'. Reading mockup, 17 October 2026. '+hand+'.']))
    return consolidate(records),notes,inputs


def consolidate(records):
    merged={}
    for record in records:
        record=dict(record,citation=citation_form(record['citation']))
        key=identity(record['citation'])
        if 'moralcrumplezonescautionarytalesinhumanrobotinteraction' in key and '2019' in key:key='elish2019moralcrumplezones'
        for group in SAME_SOURCE:
            if group&set(record['keys']):key='same-source:'+'|'.join(sorted(group));break
        accounts=[dict(a) for a in record['accounts']]
        if key not in merged:merged[key]=dict(record,keys=list(record['keys']),accounts=accounts,urls=list(record.get('urls',[])))
        else:
            r=merged[key]
            if identity(record['citation'])!=identity(r['citation']):
                # The fuller wording heads the entry; the other wording stays
                # beside the account of the book that used it.
                if len(record['citation'])>len(r['citation']):
                    for a in r['accounts']:a.setdefault('cited_as',r['citation'])
                    r['citation']=record['citation']
                else:
                    for a in accounts:a.setdefault('cited_as',record['citation'])
            record=dict(record,accounts=accounts)
            r['keys']=list(dict.fromkeys(r['keys']+record['keys']))
            for account in record['accounts']:
                if account not in r['accounts']:r['accounts'].append(account)
            r['urls']=list(dict.fromkeys(r['urls']+record.get('urls',[])))
    return sorted(merged.values(),key=lambda r:identity(r['citation']))


def register_fonts(repo=REPO):
    fd=Path(repo)/'common/fonts'
    for name,file in [('RefBody','static/EBGaramond-Regular400.ttf'),('RefItalic','static/EBGaramond-Italic400.ttf'),('RefTitle','IMFeENrm28P.ttf'),('RefSmall','IMFeENsc28P.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(fd/file)))


class Writer:
    def __init__(self,c,start,repo=REPO):
        register_fonts(repo);self.c=c;self.start=start;self.page=start;self.pages=[];self.entries=[];self.sections=[];self.y=0
        # Continuation heading and running head follow the division being set.
        self.continued='Bibliography, continued';self.running='BIBLIOGRAPHY'
        self.styles={
            'body':ParagraphStyle('RefBody',fontName='RefBody',fontSize=11,leading=14.6,textColor=colors.HexColor(INK),spaceAfter=9),
            'small':ParagraphStyle('RefNote',fontName='RefBody',fontSize=10,leading=13.3,textColor=colors.HexColor(MUTE),spaceAfter=8),
            'heading':ParagraphStyle('RefHeading',fontName='RefTitle',fontSize=24,leading=28,textColor=colors.HexColor(INK),spaceAfter=19),
            'subhead':ParagraphStyle('RefSubheading',fontName='RefSmall',fontSize=11,leading=14,textColor=colors.HexColor(RED),spaceAfter=8),
            'label':ParagraphStyle('RefLabel',fontName='RefSmall',fontSize=9,leading=11.5,textColor=colors.HexColor(RED),spaceAfter=4)}

    def new_page(self,heading=None):
        heading=heading or self.continued
        if self.pages:self.c.showPage();self.page+=1
        c=self.c;c.setFillColor(colors.HexColor(PAPER));c.rect(0,0,PW,PH,stroke=0,fill=1)
        c.setStrokeColor(colors.HexColor('#8e7b5f'));c.setLineWidth(.45);c.line(40,679,464,679)
        c.setFillColor(colors.HexColor(INK));c.setFont('RefSmall',8);c.drawString(42,690,'CODEX INTERVALLORUM')
        c.setFillColor(colors.HexColor(RED));c.drawRightString(462,690,self.running)
        c.setFillColor(colors.HexColor(MUTE));c.setFont('RefSmall',9);c.drawCentredString(252,24,str(self.page))
        self.pages.append(dict(page=self.page,title=self.running.capitalize(),key=None));self.y=634
        self.paragraph(heading,'heading',continuation=False)

    def paragraph(self,text,style='body',continuation=True):
        # Source links stay clickable; long URLs are set in the same body face.
        parts=re.split(r'(https?://\S+)',clean(text));formatted=[]
        for part in parts:
            escaped=html.escape(part)
            if part.startswith(('http://','https://')):
                formatted.append('<link href="'+html.escape(part.rstrip('.,;'))+'" color="'+RED+'">'+escaped+'</link>')
            else:formatted.append(escaped)
        markup=''.join(formatted)
        todo=Paragraph(markup,self.styles[style])
        while True:
            _,h=todo.wrap(400,10000)
            if self.y-h>=56:
                todo.drawOn(self.c,52,self.y-h);self.y-=h+self.styles[style].spaceAfter;break
            if not continuation:raise ValueError('Backmatter heading does not fit')
            if self.y<120:self.new_page();continue
            parts=todo.split(400,self.y-56)
            if not parts:self.new_page();continue
            parts[0].wrap(400,10000);parts[0].drawOn(self.c,52,56)
            self.new_page();todo=parts[1]

    def section(self,title):
        if self.y<180:self.new_page()
        self.sections.append(dict(title=title,page=self.page));self.paragraph(title,'subhead')


def write(c,records,notes,start_page=1,repo=REPO,local_book=None):
    w=Writer(c,start_page,repo);w.new_page('Bibliography')
    if local_book=='VII':
        w.paragraph('Sources for this Septimus reading text. Keys retain the VII prefix and match the bracketed S-numbers in the text. Each account distinguishes the material accessed from the use made of it. A source entry does not certify a reproduced experiment or an independent audit. The broader research passes and the check ledger remain in the repository.','small')
    elif local_book=='Acc':
        w.paragraph('Sources the parable draws on. Keys carry the Acc prefix. The parable cites none of them in its text and asks none of them to establish a claim; each account records what was read and where the parable uses it. The model reviews it answers follow as project records.','small')
    elif local_book=='VI':
        w.paragraph('Sources for Book VI. Keys carry the VI prefix and match the bracketed keys in the text. Each account says what was read, by whom and how far; where this draft did not re-read a source, the account says so and names who did. Project records follow the literature as a separate list; they record where material came from and are not independent evidence for it.','small')
    elif local_book=='Mat':
        w.paragraph('Sources the parable draws on. Keys carry the Mat prefix. The parable cites none of them in its text and asks none of them to establish a claim; each account records what was read, how far it was checked, and where the parable uses it. Several are recalled rather than inspected, and say so.','small')
    else:
        w.paragraph('The references of the included books are gathered here in one setting. Keys keep their book prefix: I-II/B1 and IV/B1 refer to different records. Identical citations are combined, as are a few sources that different books cite in different words; each book’s wording, source account, and inspection limits remain attributable. Project working documents follow the literature as a separate list. The I-II/F entries are contextual reading carried forward from Matricis; none implies a fresh inspection.','small')
    def entry(r):
        if w.y<145:w.new_page()
        start=w.page
        for key in r['keys']:
            if local_book and key.startswith(local_book+'/'):c.bookmarkPage('ref-'+key.split('/',1)[1])
        w.paragraph(' / '.join(r['keys']),'label')
        w.paragraph(r['citation'])
        for account in r['accounts']:
            if account.get('cited_as'):w.paragraph('Cited in '+account['book']+' as: '+account['cited_as'],'small')
            if account.get('status'):w.paragraph('Inspection / '+account['book']+'. '+account['status'],'small')
            if account.get('use'):w.paragraph('Use / '+account['book']+'. '+account['use'],'small')
        for url in r.get('urls',[]):
            if url not in r['citation'] and not any(url in a.get('status','') for a in r['accounts']):w.paragraph(url,'small')
        w.entries.append(dict(keys=r['keys'],citation=r['citation'],start_page=start,end_page=w.page));w.y-=8
    consolidated=consolidate(records)
    for r in consolidated:
        if not is_project_record(r):entry(r)
    project=[r for r in consolidated if is_project_record(r)]
    if project:
        w.continued='Project records, continued';w.new_page('Project records')
        w.sections.append(dict(title='Project records',page=w.page))
        w.paragraph('Working documents, research packets and repository files made within the project. They record where material came from; they are not independent evidence for it.','small')
        for r in project:entry(r)
    w.continued='Production and source notes, continued';w.running='PRODUCTION NOTES'
    w.new_page('Production and source notes');w.sections.append(dict(title='Production and source notes',page=w.page))
    grouped={}
    for note in notes:
        group=grouped.setdefault(note['title'],dict(title=note['title'],paragraphs=[]))
        for s in note['paragraphs']:
            if clean(s) and clean(s) not in ' '.join(clean(p) for p in group['paragraphs']):group['paragraphs'].append(s)
    groups=[('The volume',),('Clavis',),('Accusator','De Officio'),('I-II','Clavicula Matricis'),('III','Pseudomonarchia'),('IV','Clavicula Graduum'),('V /','Ars Notoria'),('Matres','De Matribus'),('VI /','Companion','Tarot'),('VII /','De Vinculis'),('Nota Clausa',)]
    def order(note):
        title=note['title']
        for i,prefixes in enumerate(groups):
            if title.startswith(prefixes):return i
        return len(groups)
    seen=set()
    for note in sorted(grouped.values(),key=order):
        paras=[clean(s) for s in note['paragraphs'] if clean(s)]
        signature=' '.join(paras)
        if not signature or signature in seen:continue
        seen.add(signature);w.section(note['title'])
        for s in paras:w.paragraph(s)
        w.y-=5
    c.showPage()
    return dict(pages=w.pages,entries=w.entries,sections=w.sections,start_page=start_page,end_page=w.page,
                keys=sorted(k for r in consolidate(records) for k in r['keys']),record_count=len(consolidate(records)))

