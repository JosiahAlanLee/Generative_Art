"""Graduum IX: shift Matricis base signs modulo twelve; preserve tally and spaces."""
import re
import string

LETTERS = {ch: (i % 12 + 1, i // 12 + 1) for i, ch in enumerate(string.ascii_uppercase)}
INVERSE = {v: k for k, v in LETTERS.items()}
CAPTION = 'The key returns the signs, not the room.'
SHIFT = 3

def normalize(text):
    # Editorial normalization is explicit; never silently throw away a digit or
    # transliterate an unknown character. Punctuation has no encoded form.
    allowed = set(string.ascii_letters + string.whitespace + ",.;:!?'-\"()")
    bad = set(text) - allowed
    if bad:
        raise ValueError('Unsupported characters: ' + repr(sorted(bad)))
    return ' '.join(re.sub(r"[,.;:!?'\"()-]", '', text).upper().split())

def encode(text, shift=SHIFT):
    if type(shift) is not int or not 0 <= shift < 12:
        raise ValueError('Shift must be an integer from 0 through 11')
    return [[((LETTERS[c][0] - 1 + shift) % 12 + 1, LETTERS[c][1])
             for c in word] for word in normalize(text).split()]

def decode(words, shift=SHIFT):
    if type(shift) is not int or not 0 <= shift < 12:
        raise ValueError('Shift must be an integer from 0 through 11')
    output = []
    for word in words:
        if not word:
            raise ValueError('Empty cipher word')
        letters = []
        for b, t in word:
            if type(b) is not int or type(t) is not int or not 1 <= b <= 12 or not 1 <= t <= 3:
                raise ValueError('Malformed base/tally token')
            pair = ((b - 1 - shift) % 12 + 1, t)
            if pair not in INVERSE:
                raise ValueError('Token unshifts into a reserved plaintext combination')
            letters.append(INVERSE[pair])
        output.append(''.join(letters))
    return ' '.join(output)

def codes(words):
    return ' / '.join(' '.join(f'{b:02d}:{t}' for b, t in word) for word in words)

def validate():
    for shift in range(12):
        assert decode(encode(string.ascii_uppercase, shift), shift) == string.ascii_uppercase
        assert decode(encode(CAPTION, shift), shift) == normalize(CAPTION)
    assert encode('KEY')[0][-1] == (4, 3)  # a valid cipher token, reserved in plaintext
    assert decode(encode('KEY')) == 'KEY'
    for bad in ('a1', 'café', 'x/y'):
        try:
            encode(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsupported character was silently accepted')
    try:
        decode([[(3, 3)]], 0)
    except ValueError:
        pass
    else:
        raise AssertionError('Reserved plaintext token was silently accepted')
    return {'all_26_letters_at_all_12_shifts': 'passed', 'caption_at_all_12_shifts': 'passed',
            'reserved_cipher_token': 'passed', 'invalid_input': 'passed'}

if __name__ == '__main__':
    print(codes(encode(CAPTION)))
    print(decode(encode(CAPTION)))
    print(validate())
