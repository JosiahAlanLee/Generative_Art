"""Checks of the consolidation's source routing, identity, and cipher carriers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
BOOK=json.loads((ROOT/'manuscript/book.json').read_text())


class CombinedTests(unittest.TestCase):
    def test_every_inherited_table_is_accounted_for_once(self):
        inherited=[ch['plate'] for ch in BOOK['chapters'] if isinstance(ch['plate'],int)]
        # Intervallorum 12 (the Open Inventory) gave way to the mounted Matricis XIII.
        self.assertEqual(sorted(inherited),list(range(1,12)))
        mounted=[ch['plate'] for ch in BOOK['chapters'] if str(ch['plate']).startswith('matricis-')]
        mounted+=[il['plate'] for il in BOOK.get('interleaves',[])]
        self.assertEqual(sorted(mounted),sorted(['matricis-i','matricis-vii','matricis-viii','matricis-x','matricis-xiii']))
        for il in BOOK.get('interleaves',[]):
            self.assertIn(il['after'],range(1,18))
            for p in il['paragraphs']:
                for key in re.findall(r'\[([A-Z]\d+)\]',p):self.assertIn(key,[r['id'] for r in BOOK['references']])
        self.assertEqual([ch['number'] for ch in BOOK['chapters']],list(range(1,18)))
        for ch in BOOK['chapters']:
            self.assertEqual(len(ch['pages']),2)
        prose=' '.join(p for ch in BOOK['chapters'] for pg in ch['pages'] for p in pg['paragraphs'])
        self.assertNotIn('mostly physical repair',prose)
        self.assertIn('comparison records are not included',prose)
        self.assertIn('6. Investigate material dependence',prose)
        self.assertIn('10. Critical decisions require',prose)

    def test_all_citation_keys_resolve(self):
        keys=[r['id'] for r in BOOK['references']]
        self.assertEqual(len(keys),len(set(keys)))
        used=set()
        for ch in BOOK['chapters']:
            used.update(ch['sources'])
            for pg in ch['pages']:
                for p in pg['paragraphs']:used.update(re.findall(r'\b([A-Z]\d+)\b',p))
        self.assertLessEqual(used,set(keys))

    def test_prepared_images_have_the_recorded_identity(self):
        entries=json.loads((ROOT/'assets/figures.json').read_text())
        self.assertEqual(len(entries),5)
        for e in entries:
            self.assertTrue(e['original'].endswith('.png'))
            self.assertEqual(hashlib.sha256((ROOT/'assets'/e['asset']).read_bytes()).hexdigest(),e['prepared_sha256'])

    def test_active_binding_includes_only_one_opening_component(self):
        spec=importlib.util.spec_from_file_location('combined_binding',REPO/'binding/bind.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        opening=[b for b in module.BOOKS if b[0] in ('I','II','I-II')]
        self.assertEqual(len(opening),1)
        self.assertIn('01_matricis_intervallorum',opening[0][3])
        pdf=ROOT/'out/Clavicula_Matricis_et_Intervallorum.pdf'
        if pdf.exists():
            import fitz
            pages=module.bibliography_pages(opening[0][1],str(pdf))
            d=fitz.open(pdf)
            self.assertEqual(pages,list(range(pages[0],len(d)+1)))


if __name__=='__main__':unittest.main()
