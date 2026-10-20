"""Tests for the objections register check."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate  # noqa: E402

HEADER = """# Objections register

Explanatory text.

    ## O-001 · 2026-10-19 · An indented example is not an entry
    - 2026-10-20 · Author: overruled — nor is this

"""

ENTRY_ONE = """## O-001 · 2026-10-19 · Claude Opus 5.5
- Location: books/example.md, line 1, at abc1234
- Raised by: Claude Opus 5.5, in session
- Objection: The sentence claims more than its sources carry.
  A continuation line belongs to the field above it.
- Proposed: Narrow it.
"""

ENTRY_TWO = """
## O-002 · 2026-10-21 · Gemini (Argon)
- Location: books/other.md, section II, at def5678
- Raised by: Gemini (Argon), relayed by the author
- Objection: The attribution is wrong.
"""


def problems(text):
    entries, found = validate.parse(text)
    return entries, found + validate.check(entries)


class FormTests(unittest.TestCase):
    def test_valid_entry_is_open(self):
        entries, found = problems(HEADER + ENTRY_ONE)
        self.assertEqual(found, [])
        self.assertEqual([e['id'] for e in entries], ['O-001'])
        self.assertEqual(validate.status(entries[0]), 'open')

    def test_missing_objection(self):
        text = HEADER + ENTRY_ONE.replace('- Objection: The sentence claims more than its sources carry.\n', '')
        _, found = problems(text)
        self.assertTrue(any('"Objection"' in p for p in found), found)

    def test_numbering_must_run_in_sequence(self):
        _, found = problems(HEADER + ENTRY_ONE + ENTRY_TWO.replace('O-002', 'O-003'))
        self.assertTrue(any('expected O-002' in p for p in found), found)

    def test_malformed_heading(self):
        _, found = problems(HEADER + ENTRY_ONE.replace(' · Claude', ' - Claude'))
        self.assertTrue(any('malformed entry heading' in p for p in found), found)

    def test_unrecognised_line(self):
        _, found = problems(HEADER + ENTRY_ONE + '- Comment: freeform bullet\n')
        self.assertTrue(any('neither form' in p for p in found), found)

    def test_overruled_needs_reason_and_place(self):
        bare = HEADER + ENTRY_ONE + '- 2026-10-20 · Author: overruled — no\n'
        self.assertTrue(problems(bare)[1])
        unplaced = HEADER + ENTRY_ONE + '- 2026-10-20 · Author: overruled — the parable stays as written\n'
        self.assertTrue(problems(unplaced)[1])
        full = (HEADER + ENTRY_ONE + '- 2026-10-20 · Author: overruled — the parable stays as written. '
                'Given: chat with Claude, 20 October 2026\n')
        entries, found = problems(full)
        self.assertEqual(found, [])
        self.assertEqual(validate.status(entries[0]), 'overruled')

    def test_accepted_needs_reference(self):
        self.assertTrue(problems(HEADER + ENTRY_ONE + '- 2026-10-20 · Author: accepted — fixed\n')[1])
        entries, found = problems(HEADER + ENTRY_ONE + '- 2026-10-20 · Author: accepted - PR #12\n')
        self.assertEqual(found, [])
        self.assertEqual(validate.status(entries[0]), 'accepted')

    def test_only_author_kinds(self):
        _, found = problems(HEADER + ENTRY_ONE + '- 2026-10-20 · Author: closed — done\n')
        self.assertTrue(any('begins accepted' in p for p in found), found)

    def test_withdrawal_and_later_status(self):
        text = (HEADER + ENTRY_ONE + '- 2026-10-20 · Author: deferred — until the next binding\n'
                '- 2026-10-21 · Objector: withdrawn — answered by PR #12\n')
        entries, found = problems(text)
        self.assertEqual(found, [])
        self.assertEqual(validate.status(entries[0]), 'withdrawn')

    def test_invalid_date(self):
        _, found = problems(HEADER + ENTRY_ONE.replace('2026-10-19', '2026-13-40'))
        self.assertTrue(any('invalid date' in p for p in found), found)


class HistoryTests(unittest.TestCase):
    def test_additions_pass(self):
        base = HEADER + ENTRY_ONE
        head = base + '- 2026-10-20 · Note: the author has the passage\n' + ENTRY_TWO
        self.assertEqual(validate.append_only(base, head), [])

    def test_edited_entry_fails(self):
        base = HEADER + ENTRY_ONE
        head = base.replace('claims more than its sources carry', 'is fine')
        self.assertTrue(validate.append_only(base, head))

    def test_removed_entry_fails(self):
        base = HEADER + ENTRY_ONE + ENTRY_TWO
        self.assertTrue(validate.append_only(base, HEADER + ENTRY_ONE))

    def test_header_may_change(self):
        base = HEADER + ENTRY_ONE
        head = base.replace('Explanatory text.', 'Revised explanatory text.')
        self.assertEqual(validate.append_only(base, head), [])

    def test_command_line_with_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp, 'base.md')
            head = Path(tmp, 'head.md')
            base.write_text(HEADER + ENTRY_ONE, encoding='utf-8')
            head.write_text(HEADER + ENTRY_ONE.replace('Narrow it.', 'Cut it.'), encoding='utf-8')
            self.assertEqual(validate.main([str(head), '--base', str(base)]), 1)
            head.write_text(HEADER + ENTRY_ONE + ENTRY_TWO, encoding='utf-8')
            self.assertEqual(validate.main([str(head), '--base', str(base)]), 0)
            empty = Path(tmp, 'empty.md')
            empty.write_text('', encoding='utf-8')
            self.assertEqual(validate.main([str(head), '--base', str(empty)]), 0)


class RegisterTests(unittest.TestCase):
    def test_committed_register_passes(self):
        self.assertEqual(validate.main([str(validate.DEFAULT)]), 0)


if __name__ == '__main__':
    unittest.main()
