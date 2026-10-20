"""Regression checks for content-aware paper: preserve functional marks exactly."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

import fitz
import numpy as np
from PIL import Image

SPEC = importlib.util.spec_from_file_location('vellum', Path(__file__).resolve().parents[1] / 'vellum.py')
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


class VellumTests(unittest.TestCase):
    def setUp(self):
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=504, height=720)
        self.page.draw_rect(self.page.rect, color=None, fill=(237/255, 230/255, 212/255))
        self.page.insert_text((52, 110), 'An intact cipher and its reading', fontsize=22, fontname='tiro')
        self.page.draw_polyline([(80, 150), (100, 170), (85, 190)], color=(.25, .2, .15), width=.3)
        # Pale geometry must also count as functional content.
        self.page.draw_line((160, 150), (190, 180), color=(.8, .8, .75), width=.5)

    def tearDown(self):
        self.doc.close()

    def test_text_spans_vectors_and_entire_art_are_protected(self):
        art = io.BytesIO()
        Image.new('RGB', (20, 20), (230, 220, 200)).save(art, format='PNG')
        self.page.insert_image((220, 140, 260, 180), stream=art.getvalue())
        protected, _ = v.protection(self.page)
        whole, _ = v.protection(self.page, whole_spans=True)
        opacity, _ = v.make_texture(self.page, 'Clavis/3')
        self.assertFalse(opacity[protected].any())
        self.assertTrue(whole[round(100*v.SCALE), round(55*v.SCALE)])
        for x, y in [(90, 160), (175, 165), (240, 160)]:
            self.assertTrue(protected[round(y*v.SCALE), round(x*v.SCALE)])
        self.assertTrue(opacity[400:600, 400:600].any())

    def test_repeatability_and_page_identity(self):
        a, _ = v.make_texture(self.page, 'Clavis/3')
        b, _ = v.make_texture(self.page, 'Clavis/3')
        c, _ = v.make_texture(self.page, 'De Vinculis/3')
        self.assertTrue(np.array_equal(a, b))
        self.assertFalse(np.array_equal(a, c))
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'binding-log.json'
            log.write_text(json.dumps({'Clavis': {'source': 'source.pdf', 'body_page_map': {'3': 1}}}))
            self.assertEqual(v.identities(self.doc, log)[0], 'Clavis/3')

    def test_saved_overlay_keeps_source_content_and_protected_pixels_exact(self):
        self.page.insert_link({'kind': fitz.LINK_URI, 'from': fitz.Rect(52, 88, 140, 112),
                               'uri': 'https://example.com'})
        original = self.doc.tobytes()
        opacity, _ = v.make_texture(self.page, 'Clavis/3')
        v.add_texture(self.page, opacity)
        self.assertEqual(v.source_images(self.page), [])
        self.assertEqual(v.source_image_info(self.page), [])
        with fitz.open(stream=original, filetype='pdf') as before, \
                fitz.open(stream=self.doc.tobytes(), filetype='pdf') as after:
            self.assertGreater(v.verify_page(before[0], after[0], True), 1000)

    def test_dark_nonpaper_page_is_skipped(self):
        self.page.draw_rect(self.page.rect, color=None, fill=(.1, .1, .1))
        self.assertIsNone(v.make_texture(self.page, 'dark'))

    def test_light_profile_reduces_pigment_and_compressed_texture_size(self):
        light, light_record = v.make_texture(self.page, 'Clavis/3', profile='light')
        full, full_record = v.make_texture(self.page, 'Clavis/3', profile='full')
        protected, _ = v.protection(self.page)
        self.assertFalse(light[protected].any())
        self.assertLess(light.mean(), full.mean() * .65)
        self.assertLess(len(v.png(light)), len(v.png(full)) * .65)
        self.assertEqual(light_record['ink_spots'], full_record['ink_spots'])

    def test_unknown_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown vellum profile'):
            v.make_texture(self.page, 'Clavis/3', profile='unknown')

    def test_each_page_retains_its_own_protection_mask(self):
        # Equal paper/pigment images must never reuse a different page's alpha.
        other = self.doc.new_page(width=504, height=720)
        other.draw_rect(other.rect, color=None, fill=(237/255, 230/255, 212/255))
        other.insert_text((250, 430), 'A different position', fontsize=28)
        data = self.doc.tobytes()
        for i, page in enumerate(self.doc):
            opacity, _ = v.make_texture(page, f'page/{i}')
            v.add_texture(page, opacity)
        with fitz.open(stream=data, filetype='pdf') as before, \
                fitz.open(stream=self.doc.tobytes(), filetype='pdf') as after:
            for i in range(2):
                self.assertGreater(v.verify_page(before[i], after[i], True), 1000)

    def test_rare_spots_stay_in_clear_margins(self):
        pages_with_spots = 0
        for i in range(18):
            opacity, record = v.make_texture(self.page, 'trial', seed=i)
            for box in record['ink_spots']:
                pages_with_spots += 1
                r = fitz.Rect(box)
                self.assertTrue(r.x1 < 27 or r.x0 > 477 or r.y1 < 27 or r.y0 > 693)
            # The central field remains much lighter than a punctuation mark.
            self.assertLessEqual(int(opacity[36:-36, 36:-36].max()), 11)
        self.assertGreater(pages_with_spots, 0)
        self.assertLess(pages_with_spots, 9)

    def test_verifier_rejects_changed_cipher(self):
        original = self.doc.tobytes()
        self.page.draw_line((80, 150), (100, 170), color=(0, 0, 0), width=1)
        with fitz.open(stream=original, filetype='pdf') as before:
            with self.assertRaisesRegex(ValueError, 'Source paths'):
                v.verify_page(before[0], self.page)

    def test_apply_recognizes_current_and_legacy_finishing(self):
        for stamp in ['CodexIntervallorum:vellum-1', 'LibrumQuinque:vellum-1']:
            with self.subTest(stamp=stamp), tempfile.TemporaryDirectory() as tmp:
                self.doc.set_metadata({'keywords': stamp})
                source = Path(tmp) / 'source.pdf'
                source.write_bytes(self.doc.tobytes())
                original = source.read_bytes()
                with self.assertRaisesRegex(ValueError, 'already has vellum'):
                    v.apply(source)
                self.assertEqual(source.read_bytes(), original)

    def test_apply_rejects_double_application_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp)/'source.pdf', Path(tmp)/'out.pdf'
            source.write_bytes(self.doc.tobytes())
            data = source.read_bytes()
            report = v.apply(source, out)
            self.assertTrue(report['verification']['protected_pixels_exact'])
            self.assertEqual(source.read_bytes(), data)
            final = out.read_bytes()
            with self.assertRaisesRegex(ValueError, 'already has vellum'):
                v.apply(out)
            self.assertEqual(out.read_bytes(), final)


if __name__ == '__main__':
    unittest.main()
