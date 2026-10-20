#!/usr/bin/env python3
"""Check the objections register: entry form, dispositions, and append-only history.

The check covers form. It cannot tell who wrote a line; the rule in AGENTS.md
says who may write which lines.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / 'register.md'

ENTRY = re.compile(r'^## (O-(\d{3,})) · (\d{4}-\d{2}-\d{2}) · (\S.*)$')
FIELD = re.compile(r'^- (Location|Raised by|Objection|Proposed): (.*)$')
EVENT = re.compile(r'^- (\d{4}-\d{2}-\d{2}) · (Author|Objector|Note): (.*)$')
REQUIRED = ('Location', 'Raised by', 'Objection')
AUTHOR_KINDS = ('accepted', 'overruled', 'deferred')
# The register uses an em dash; an en dash or a spaced hyphen is accepted too.
DASH = re.compile(r'\s+(?:—|–|--?)\s+')
REFERENCE = re.compile(r'#\d+|\b[0-9a-f]{7,40}\b')


def _is_date(text):
    try:
        dt.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _split(rest):
    parts = DASH.split(rest, maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else '')


def parse(text):
    """Return (entries, problems) for the register text."""
    entries, problems = [], []
    current = None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        match = ENTRY.match(line)
        if match:
            current = {'id': match.group(1), 'number': int(match.group(2)), 'date': match.group(3),
                       'by': match.group(4), 'fields': {}, 'events': [], 'line': n}
            entries.append(current)
            if not _is_date(match.group(3)):
                problems.append(f'line {n}: {match.group(1)} has an invalid date {match.group(3)}')
            continue
        if line.startswith('## '):
            if line.startswith('## O-'):
                problems.append(f'line {n}: malformed entry heading; expected "## O-NNN · YYYY-MM-DD · who": {line}')
            current = None
            continue
        if current is None or not line.startswith('- '):
            continue
        field = FIELD.match(line)
        if field:
            name, value = field.groups()
            if name in current['fields']:
                problems.append(f'line {n}: {current["id"]} repeats "{name}"; add a dated Note instead')
            current['fields'][name] = value.strip()
            continue
        event = EVENT.match(line)
        if event:
            current['events'].append((n,) + event.groups())
            continue
        problems.append(f'line {n}: {current["id"]} has a line in neither form: {line}')
    return entries, problems


def check(entries):
    """Return problems with numbering, required fields and disposition lines."""
    problems = []
    for expected, entry in enumerate(entries, 1):
        if entry['number'] != expected:
            problems.append(f'line {entry["line"]}: expected O-{expected:03d}, found {entry["id"]}')
        for name in REQUIRED:
            if not entry['fields'].get(name):
                problems.append(f'{entry["id"]}: missing or empty "{name}"')
        for n, date, who, rest in entry['events']:
            if not _is_date(date):
                problems.append(f'line {n}: invalid date {date}')
            kind, detail = _split(rest)
            if who == 'Author':
                if kind not in AUTHOR_KINDS:
                    problems.append(f'line {n}: an Author line begins accepted, overruled or deferred')
                elif not detail:
                    problems.append(f'line {n}: "{kind}" needs detail after the dash')
                elif kind == 'accepted' and not REFERENCE.search(detail):
                    problems.append(f'line {n}: accepted needs the pull request (#N) or commit that answers it')
                elif kind == 'overruled':
                    reason, given, place = detail.partition('Given:')
                    if not given or not place.strip():
                        problems.append(f'line {n}: overruled needs "Given:" and where the reason was given')
                    elif len(reason.split()) < 3:
                        problems.append(f'line {n}: overruled needs the author\'s reason before "Given:"')
            elif who == 'Objector':
                if kind != 'withdrawn' or not detail:
                    problems.append(f'line {n}: an Objector line reads "withdrawn — why"')
            elif who == 'Note' and not rest.strip():
                problems.append(f'line {n}: empty Note')
    return problems


def status(entry):
    """open until the latest author disposition or a withdrawal says otherwise"""
    state = 'open'
    for _, _, who, rest in entry['events']:
        kind = _split(rest)[0]
        if who == 'Author' and kind in AUTHOR_KINDS:
            state = kind
        elif who == 'Objector' and kind == 'withdrawn':
            state = 'withdrawn'
    return state


def _entry_lines(text):
    lines = [line.rstrip() for line in text.splitlines()]
    for i, line in enumerate(lines):
        if ENTRY.match(line):
            return lines[i:]
    return []


def append_only(base, head):
    """Every entry line of the earlier register survives, in order, in the later one.

    The explanatory text above the first entry may change; entries may only grow.
    """
    later = _entry_lines(head)
    j = 0
    for line in _entry_lines(base):
        while j < len(later) and later[j] != line:
            j += 1
        if j == len(later):
            return [f'an earlier entry line was removed or changed: {line!r}']
        j += 1
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('register', nargs='?', default=str(DEFAULT))
    parser.add_argument('--base', help='an earlier copy of the register; its entries must survive unchanged')
    args = parser.parse_args(argv)
    text = Path(args.register).read_text(encoding='utf-8')
    entries, problems = parse(text)
    problems += check(entries)
    if args.base:
        base = Path(args.base)
        if base.is_file() and base.stat().st_size:
            problems += append_only(base.read_text(encoding='utf-8'), text)
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        return 1
    counts = {}
    for entry in entries:
        counts[status(entry)] = counts.get(status(entry), 0) + 1
    summary = ', '.join(f'{count} {state}' for state, count in sorted(counts.items())) or 'no entries'
    noun = 'entry' if len(entries) == 1 else 'entries'
    print(f'Objections register passed: {len(entries)} {noun} ({summary}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
