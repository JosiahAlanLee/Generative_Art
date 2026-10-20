"""Exercise binding across odd/even component lengths and an actual facing spread."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("binding_builder", ROOT / "binding/bind.py")
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)
spec = importlib.util.spec_from_file_location("binding_validator", ROOT / "binding/validate.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def component(path, count, size=(504, 720)):
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(path), pagesize=size, invariant=1)
    for n in range(1, count + 1):
        canvas.drawString(30, 100, f"local page {n}")
        if path.name == "tarot.pdf" and n == 5:
            canvas.drawImage(ImageReader(Image.new("RGB", (2, 2), "black")), 40, 140, 20, 20)
        canvas.showPage()
    canvas.save()


class BindingTests(unittest.TestCase):
    def test_known_book_without_register_fails_instead_of_omitting_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "ii.pdf"
            component(source, 2)
            with self.assertRaisesRegex(ValueError, "Cannot locate bibliography"):
                binding.bibliography_pages("Clavicula Intervallorum", source)

    def test_register_moves_once_and_following_workshop_keeps_its_page_side(self):
        binding.fonts()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            c = Canvas(str(root / "ii.pdf"), pagesize=(504, 720), invariant=1)
            for n in range(1, 7):
                c.drawString(30, 680, "REFERENCE REGISTER" if 3 <= n <= 5 else "WORKSHOP RECORD")
                c.drawString(30, 650, f"distinctive source leaf {n}")
                c.showPage()
            c.save()
            books = [("II", "Clavicula Intervallorum", "", "ii.pdf", "one")]
            out = root / "bound.pdf"
            with patch.object(binding, "REPO", str(root)), patch.object(binding, "BOOKS", books), \
                    patch.object(binding, "fonts"), patch("sys.stdout", new=io.StringIO()):
                binding.main(str(out))
                result = validator.validate(out, repo=root)
            log = json.loads((root / "binding-log.json").read_text())
            entry = log["Clavicula Intervallorum"]
            self.assertEqual(entry["body_page_map"], {"1": 5, "2": 6, "6": 8})
            self.assertEqual(entry["body_blank_pages"], [7])
            self.assertEqual(entry["bibliography_source_pages"], [3, 4, 5])
            self.assertEqual(result["bibliography_source_pages"], 3)
            doc = PdfReader(out)
            all_text = "\n".join(p.extract_text() for p in doc.pages)
            for n in range(1, 7):
                self.assertEqual(all_text.count(f"distinctive source leaf {n}"), 1)
            self.assertNotIn("REFERENCE REGISTER", doc.pages[7].extract_text())
            self.assertLess(log["colophon_page"], log["bibliography"]["start_page"])
            self.assertEqual(log["bibliography"]["end_page"], len(doc.pages))

    def test_physical_parity_survives_odd_and_even_length_components(self):
        binding.fonts()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            books = [("I", "First", "", "first.pdf", "one"),
                     ("II", "Second", "", "second.pdf", "two"),
                     ("Companion", "Tarot", "", "tarot.pdf", "three")]
            for name, count in [("first.pdf", 3), ("second.pdf", 2), ("tarot.pdf", 5)]:
                component(root / name, count)
            out = root / "bound.pdf"
            with patch.object(binding, "REPO", str(root)), patch.object(binding, "BOOKS", books), \
                    patch.object(binding, "fonts"), patch("sys.stdout", new=io.StringIO()):
                binding.main(str(out))
            log = json.loads((root / "binding-log.json").read_text())
            doc = PdfReader(out)
            self.assertEqual([log[t]["start_page"] for t in ["First", "Second", "Tarot"]], [5, 9, 11])
            self.assertEqual(doc.pages[7].extract_text().strip(), "")
            # Tarot local verso 4 and recto 5 must be physical 14 and 15.
            self.assertIn("local page 4", doc.pages[13].extract_text())
            self.assertIn("local page 5", doc.pages[14].extract_text())
            self.assertIn("Colophon", doc.pages[-1].extract_text())
            self.assertEqual(log["colophon_page"], len(doc.pages))

    def test_validator_checks_facing_art_and_rejects_changed_input(self):
        binding.fonts()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            component(root / "first.pdf", 3)
            component(root / "tarot.pdf", 5)
            (root / "tarot-log.json").write_text(json.dumps({"pages": 5, "cards": [
                {"title": "local page 4", "verso": 4, "recto": 5}]}))
            books = [("I", "First", "", "first.pdf", "one"),
                     ("Companion", "Tarot of Intervals", "", "tarot.pdf", "two")]
            out = root / "bound.pdf"
            with patch.object(binding, "REPO", str(root)), patch.object(binding, "BOOKS", books), \
                    patch.object(binding, "fonts"), patch("sys.stdout", new=io.StringIO()):
                binding.main(str(out))
                result = validator.validate(out, repo=root)
                self.assertEqual(result["facing_tarot_spreads"], 1)
                component(root / "first.pdf", 4)
                with self.assertRaisesRegex(ValueError, "bound input differs"):
                    validator.validate(out, repo=root)


if __name__ == "__main__":
    unittest.main()
