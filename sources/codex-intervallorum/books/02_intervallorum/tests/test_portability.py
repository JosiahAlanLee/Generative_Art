from pathlib import Path
import json
import re
import unittest


ROOT=Path(__file__).resolve().parents[1]


class PortableSourceTests(unittest.TestCase):
    def test_no_original_workspace_or_hosted_runtime_dependencies(self):
        forbidden=['/home/'+'claude','/tmp/'+'claude-','/_'+'blob/',
                   'support'+'.js','DC'+'Logic']
        for folder in ['generator','manuscript']:
            for path in (ROOT/folder).rglob('*'):
                if path.suffix in ('.py','.json','.md'):
                    text=path.read_text()
                    for item in forbidden:
                        self.assertNotIn(item,text,str(path))

    def test_each_source_tag_resolves_and_status_is_explicit(self):
        book=json.loads((ROOT/'manuscript/book.json').read_text())
        ids={r['id'] for r in book['references']}
        for ref in book['references']:
            self.assertTrue(ref['status'])
        for ch in book['chapters']:
            self.assertTrue(set(ch['sources']).issubset(ids))
            for page in ch['pages']:
                for para in page['paragraphs']:
                    self.assertRegex(para,r'^\[[EDHVF]\] ')
                    for tag in re.findall(r'\[([A-Z][0-9])\]',para):
                        self.assertIn(tag,ids)

    def test_active_reading_order_has_twelve_new_tables(self):
        book=json.loads((ROOT/'manuscript/book.json').read_text())
        self.assertEqual([c['number'] for c in book['chapters']],list(range(1,13)))
        for c in book['chapters']:
            self.assertEqual(len(c['pages']),2)
        for removed in ['vi.py','fm.py','make_pdf.py','pdfbuild.py']:
            self.assertFalse((ROOT/'generator'/removed).exists())


if __name__=='__main__':unittest.main()
