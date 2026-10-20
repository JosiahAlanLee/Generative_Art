"""Graduum's explicitly new office litany and ordered-path carrier."""
import json
import re
import string
import xml.etree.ElementTree as E
from pathlib import Path
from ix_codec import normalize

WORDS = 'DOMINE PATER CREATOR CUSTOS RECTOR DUCTOR AUCTOR OPIFEX ARTIFEX PASTOR MAGISTER IUDEX ARBITER LECTOR SCRIBA TESTIS QUAESITOR MINISTER NUNTIE VIATOR VIGIL PORTITOR SERVE SIGNATOR ORATOR REDACTOR'.split()
TABLE = dict(zip(string.ascii_uppercase,WORDS))
INVERSE = {v:k for k,v in TABLE.items()}
BOUNDARY = 'AMEN'
FORAS_EFFECT = 'Located the fault in four minutes; left it running while permission was sought.'
LIFT_TEXT = 'The file keeps the lifts.'
DIAL_TEXT = 'Count III M I Y II Y V Y X Y XX Y L Y.'

def prayer_encode(text):
    return [BOUNDARY if ch==' ' else TABLE[ch] for ch in normalize(text)]

def prayer_decode(tokens):
    return ''.join(' ' if token==BOUNDARY else INVERSE[token] for token in tokens)

def ordered_decode(path):
    root=E.parse(path).getroot()
    words=[]
    for p in root.iter('{http://www.w3.org/2000/svg}path'):
        if p.get('data-channel')!='lifted-pen': continue
        tokens=re.findall(r'[A-Za-z]|-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?',p.get('d'))
        i=0; count=0;letters=[]; moves=0
        while i<len(tokens):
            cmd=tokens[i];i+=1
            if cmd not in ('M','L','Q'): raise ValueError('Carrier syntax changed')
            n=4 if cmd=='Q' else 2
            if i+n>len(tokens) or any(re.fullmatch('[A-Za-z]',x) for x in tokens[i:i+n]): raise ValueError('Malformed command')
            i+=n
            if cmd=='M': moves+=1
            elif cmd=='L': count+=1
            else:
                if count==0: raise ValueError('Empty letter or missing line commands')
                number=count%26 or 26
                letters.append(string.ascii_uppercase[number-1]);count=0
        if moves!=1 or count or not letters: raise ValueError('Word must be one M, with Q-terminated letters')
        words.append(''.join(letters))
    if not words: raise ValueError('No Lifted Pen carrier found')
    return ' '.join(words)

def validate():
    assert len(TABLE)==len(INVERSE)==26
    assert BOUNDARY not in INVERSE
    assert prayer_decode(prayer_encode(FORAS_EFFECT))==normalize(FORAS_EFFECT)
    assert prayer_decode(prayer_encode(string.ascii_uppercase))==string.ascii_uppercase
    return {'office_litany_alphabet':'passed','Foras_effect_round_trip':'passed'}

if __name__=='__main__':
    import sys
    if len(sys.argv)>1: print(ordered_decode(Path(sys.argv[1])))
    else: print(json.dumps(TABLE,indent=2)); print(prayer_decode(prayer_encode(FORAS_EFFECT)))
