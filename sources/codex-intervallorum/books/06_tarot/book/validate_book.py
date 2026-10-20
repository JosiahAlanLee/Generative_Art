"""Validate the initial 52-illustration reading mockup, independently of its build log.

Also render contact sheets and cipher closeups for human layout review.
Usage: python books/06_tarot/book/validate_book.py path/to/mockup.pdf
"""
import argparse
import hashlib
import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

import make_book as book

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalized(text):
    return " ".join(text.split())


def validate(pdf):
    cards = book.load_cards("initial")
    book.validate_initial_sources(cards)
    expected = json.loads((HERE / "initial-pagination.json").read_text())
    log = json.loads(pdf.with_name(pdf.stem + "-log.json").read_text())
    require(log == expected, "Pagination log differs from the initial 107-page edition")
    doc = fitz.open(pdf)
    require(len(doc) == 107, f"Expected 107 PDF pages, got {len(doc)}")
    require("mockup" in doc.metadata["title"].lower(), "PDF metadata must say mockup")
    require("MOCKUP" in doc[0].get_text(), "Title page must say MOCKUP")
    require("52 illustrations" in doc[1].get_text(), "Front matter must identify this selection")
    require(not doc[2].get_text().strip() and not doc[2].get_images(), "Page 3 must be blank")
    for page in doc:
        require(abs(page.rect.width - 504) < .01 and abs(page.rect.height - 720) < .01,
                f"Page {page.number + 1}: expected 7 x 10 inches")
        spans = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    require(page.rect.contains(fitz.Rect(span["bbox"])),
                            f"Page {page.number + 1}: clipped text {span['text']!r}")
                    spans.append(span)
        for i, first in enumerate(spans):
            for second in spans[i + 1:]:
                overlap = fitz.Rect(first["bbox"]) & fitz.Rect(second["bbox"])
                require(overlap.is_empty or overlap.width <= .5 or overlap.height <= 1,
                        f"Page {page.number + 1}: overlapping text {first['text']!r} / {second['text']!r}")
    strips = []
    for i, (card, entry) in enumerate(zip(cards, expected["cards"], strict=True)):
        verso, recto = 4 + 2 * i, 5 + 2 * i
        require(entry == {"verso": verso, "recto": recto, "title": card["title"], "kind": card["kind"]},
                f"Wrong selection/order at illustration {i + 1}")
        left, right = doc[verso - 1], doc[recto - 1]
        text = normalized(left.get_text())
        for key in ("title", "archetype", "keywords", "symbolism", "upright", "reversed", "question", "in_books"):
            value = card.get(key)
            if value:
                # Archetypes and keywords are deliberately typeset in uppercase.
                require(normalized(value).casefold() in text.casefold(), f"Page {verso}: missing {key}")
        require(not left.get_images(), f"Page {verso}: commentary must not contain raster art")
        images = right.get_image_info(xrefs=True)
        require(len(images) == 1, f"Page {recto}: expected exactly one illustration")
        image = images[0]
        require(right.rect.contains(fitz.Rect(image["bbox"])), f"Page {recto}: cropped illustration")
        # Compare the actual embedded JPEG bytes with the existing mockup resampling
        # of this exact archived PNG; no overlay, cipher, or replacement art allowed.
        expected_jpeg = book.light_image(card["image"]).jpeg_fh().getvalue()
        actual_jpeg = doc.extract_image(image["xref"])["image"]
        require(hashlib.sha256(expected_jpeg).digest() == hashlib.sha256(actual_jpeg).digest(),
                f"Page {recto}: illustration differs from its archived source")
        require(len(right.get_drawings()) == 1, f"Page {recto}: unexpected vector overlay on artwork")
        require(normalized(right.get_text()) == f"{recto} {card['running'].upper()}" or
                normalized(right.get_text()) == f"{card['running'].upper()} {recto}",
                f"Page {recto}: unexpected text overlay")
        # Only cipher paths may enter this reserved band (PDF coordinates run down).
        band = fitz.Rect(book.OUTER, 648, book.PW - book.INNER, 666)
        paths = [d for d in left.get_drawings() if d["rect"].intersects(band)
                 and d["rect"].height < 40]  # omit full-page paper background
        if card["kind"] == "major":
            require(paths, f"Page {verso}: missing cipher strip")
            bounds = fitz.Rect(paths[0]["rect"])
            for drawing in paths:
                bounds |= drawing["rect"]
                require(band.contains(drawing["rect"]), f"Page {verso}: cipher outside reserved band")
            require(bounds.height >= 5 and bounds.width >= 100, f"Page {verso}: undersized cipher")
            for block in left.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    require(not fitz.Rect(line["bbox"]).intersects(band), f"Page {verso}: text overlaps cipher band")
            words = book.tx.encode(card["keywords"].replace("/", " "))
            shift = card["number"] % 12
            shifted = [[((base - 1 + shift) % 12 + 1, tally) for base, tally in word] for word in words]
            restored = [[((base - 1 - shift) % 12 + 1, tally) for base, tally in word] for word in shifted]
            require(book.tx.decode(restored) == " ".join(book.tx.normalize(card["keywords"].replace("/", " "))),
                    f"Page {verso}: cipher round trip failed")
            strips.append({"page": verso, "title": card["title"], "bounds_pt": list(bounds), "scale_mm": 2.8})
        else:
            require(not paths, f"Page {verso}: unexpected cipher on a non-Major")
    require(len(strips) == 22, "Expected 22 cipher strips")
    return doc, {"status": "passed", "pages": 107, "illustrations": 52,
                 "selection": {"major": 22, "swords": 14, "cups": 14, "extra": 2},
                 "facing_spreads": 52, "cipher_strips": strips,
                 "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                 "visual_review": "Inspect contact sheets and cipher-closeups.png; automated bounds are not a human legibility judgment."}


def previews(doc, out):
    out.mkdir(parents=True, exist_ok=True)
    for start in (0, 54):
        sheet = Image.new("RGB", (6 * 168, 9 * 258), "white")
        draw = ImageDraw.Draw(sheet)
        for slot, index in enumerate(range(start, min(start + 54, len(doc)))):
            pix = doc[index].get_pixmap(matrix=fitz.Matrix(1/3, 1/3), alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            x, y = (slot % 6) * 168, (slot // 6) * 258
            sheet.paste(im, (x, y))
            draw.text((x + 4, y + 241), str(index + 1), fill="black")
        sheet.save(out / f"pages-{start + 1:03d}-{min(start + 54, len(doc)):03d}.png")
    sheet = Image.new("RGB", (1480, 11 * 70), "white")
    draw = ImageDraw.Draw(sheet)
    for i in range(22):
        page = doc[3 + 2 * i]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=fitz.Rect(65, 647, 435, 666), alpha=False)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        x, y = (i % 2) * 740, (i // 2) * 70
        sheet.paste(im, (x, y + 20))
        draw.text((x + 4, y + 3), f"Major {i} - page {page.number + 1}", fill="black")
    sheet.save(out / "cipher-closeups.png")
    for index in (1, 3, 4, 45, 46, 73, 74, 103, 104, 105, 106):
        doc[index].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(out / f"page-{index + 1:03d}.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    document, report = validate(args.pdf)
    previews(document, args.pdf.parent / "review")
    args.pdf.with_name(args.pdf.stem + "-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: 52 archived illustrations; 107 pages; 52 facing spreads; 22 clear cipher bands")
