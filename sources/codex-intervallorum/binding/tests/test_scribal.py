"""Protect functional marks and retained PDF content during pen finishing."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import fitz

SPEC=importlib.util.spec_from_file_location('scribal',Path(__file__).resolve().parents[1]/'scribal.py')
s=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(s)


class ScribalTests(unittest.TestCase):
    def setUp(self):
        self.doc=fitz.open();self.page=self.doc.new_page(width=504,height=720)
        self.page.draw_rect(self.page.rect,color=None,fill=(237/255,230/255,212/255))

    def tearDown(self):self.doc.close()

    def prose(self,heading='An ordinary opening'):
        self.page.insert_text((52,110),heading,fontsize=25,fontname='tiro')
        for i in range(12):
            self.page.insert_text((52,145+i*16),'The record keeps its own words and the reader keeps a question.',fontsize=12,fontname='tiro')

    def test_vector_cipher_is_not_empty_paper(self):
        self.assertTrue(s.clear(self.page,(80,80,110,110),[]))
        self.page.draw_polyline([(85,90),(105,100),(85,105)],color=(0,0,0),width=.4)
        self.assertFalse(s.clear(self.page,(80,80,110,110),[]))

    def test_entire_text_box_is_protected(self):
        self.page.insert_text((52,110),'O',fontsize=25,fontname='tiro')
        self.assertFalse(s.clear(self.page,(53,90,65,108),s.text_boxes(self.page)))

    def test_key_and_tarot_leaves_are_untouched(self):
        self.prose('The cipher hand')
        for local in range(1,30):
            self.assertEqual(s.finish_page(self.page,'Clavicula Matricis et Intervallorum',local),[])
        self.assertEqual(s.finish_page(self.page,'Tarot of Intervals',3),[])
        self.assertEqual(s.finish_page(self.page,'Nota Clausa',3),[])

    def test_nota_clausa_is_protected_inside_another_component(self):
        self.prose()
        self.page.insert_text((42,30),'NOTA CLAUSA',fontsize=8,fontname='tiro')
        for local in range(1,30):
            self.assertEqual(s.finish_page(self.page,'De Vinculis',local),[])

    def test_exact_text_and_paths_survive_finishing(self):
        self.prose();raw=self.doc.tobytes()
        for local in range(1,30):
            marks=s.finish_page(self.page,'Clavis',local)
            if marks:break
        self.assertTrue(marks)
        with fitz.open(stream=raw,filetype='pdf') as original:
            result=s.verify(original,self.doc,[dict(page=1,marks=marks)])
        self.assertTrue(result['original_vector_paths_exact'])
        self.assertTrue(result['text_exact'])
        self.assertGreater(result['changed_pixels'],0)

    def test_verifier_rejects_undeclared_changes(self):
        raw=self.doc.tobytes();self.page.draw_line((80,80),(110,110),color=(0,0,0))
        with fitz.open(stream=raw,filetype='pdf') as original:
            with self.assertRaisesRegex(ValueError,'vector geometry'):
                s.verify(original,self.doc,[])

    def test_apply_recognizes_current_and_legacy_finishing(self):
        for stamp in ['CodexIntervallorum:scribal-1', 'LibrumQuinque:scribal-1']:
            with self.subTest(stamp=stamp), tempfile.TemporaryDirectory() as tmp:
                self.doc.set_metadata({'keywords': stamp})
                source = Path(tmp) / 'source.pdf'
                source.write_bytes(self.doc.tobytes())
                (Path(tmp) / 'binding-log.json').write_text('{}')
                original = source.read_bytes()
                with self.assertRaisesRegex(ValueError, 'already has scribal'):
                    s.apply(source)
                self.assertEqual(source.read_bytes(), original)

    def test_seed_uses_local_page_identity(self):
        self.assertEqual(s.seed_for('Clavis',3),s.seed_for('Clavis',3))
        self.assertNotEqual(s.seed_for('Clavis',3),s.seed_for('De Vinculis',3))


if __name__=='__main__':unittest.main()
