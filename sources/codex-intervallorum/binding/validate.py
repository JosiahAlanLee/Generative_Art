"""Check the final binding, including physical spread parity and input provenance."""
import argparse
import hashlib
import json
from pathlib import Path

import fitz

REPO = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(pdf, repo=REPO):
    pdf, repo = Path(pdf), Path(repo)
    log = json.loads(pdf.with_name("binding-log.json").read_text())
    if (log.get("bibliography") or {}).get("mode")=="typeset":
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        import validate_typeset
        return validate_typeset.validate(pdf,repo,log)
    doc = fitz.open(pdf)
    require(len(doc) == log["total_pages"], "Binding page count differs from log")
    next_page = log["front_matter_pages"] + 1
    components = 0
    tarot_spreads = 0
    bibliography = log.get("bibliography")
    registers = {s["title"]: s for s in bibliography["sections"]} if bibliography else {}
    relocated = 0
    used_pages = set()
    for title, entry in log.items():
        if not isinstance(entry, dict) or "source" not in entry:
            continue
        start, end = entry["start_page"], entry["end_page"]
        require(start % 2 == 1, f"{title}: local rectos became physical versos")
        require(start == next_page + int(entry["blank_before"]), f"{title}: unexpected gap")
        if entry["blank_before"]:
            blank = doc[next_page - 1]
            require(not blank.get_text().strip() and not blank.get_images(), f"{title}: alignment leaf is not blank")
        require(end - start + 1 == entry["pages"], f"{title}: inconsistent range")
        source = repo / entry["source"]
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        require(digest == entry["source_sha256"], f"{title}: bound input differs from current source PDF")
        with fitz.open(source) as original:
            require(len(original) == entry["source_pages"], f"{title}: source page count changed")
            body_map = {int(n): p for n, p in entry["body_page_map"].items()}
            moved_map = {p["source_page"]: p["bound_page"] for p in registers.get(title, {}).get("page_map", [])}
            require(set(moved_map) == set(entry["bibliography_source_pages"]), f"{title}: register map differs")
            require(not set(body_map) & set(moved_map), f"{title}: duplicated bibliography in body")
            require(set(body_map) | set(moved_map) == set(range(1, len(original) + 1)),
                    f"{title}: source leaves omitted or duplicated")
            for number, physical in body_map.items():
                require(start <= physical <= end, f"{title}: body leaf outside component")
            require(set(body_map.values()) | set(entry["body_blank_pages"]) == set(range(start, end + 1)),
                    f"{title}: unexplained body leaf")
            for physical in entry["body_blank_pages"]:
                require(not doc[physical - 1].get_text().strip() and not doc[physical - 1].get_images(),
                        f"{title}: interior alignment leaf is not blank")
            for number, physical in {**body_map, **moved_map}.items():
                require(number % 2 == physical % 2, f"{title}: source leaf {number} lost parity")
                require(physical not in used_pages, f"{title}: overlapping physical leaf")
                used_pages.add(physical)
                actual = " ".join(doc[physical - 1].get_text().split())
                expected = " ".join(original[number - 1].get_text().split())
                require(actual == expected, f"{title}: source leaf {number} text changed or went missing")
            relocated += len(moved_map)
        if title == "Tarot of Intervals":
            pagination = json.loads(source.with_name(source.stem + "-log.json").read_text())
            require(pagination["pages"] == entry["source_pages"], "Tarot pagination differs from binding")
            for card in pagination["cards"]:
                verso = body_map[card["verso"]]
                recto = body_map[card["recto"]]
                require(verso % 2 == 0 and recto == verso + 1 and recto <= end,
                        f"{card['title']}: commentary and illustration do not face")
                require(" ".join(card["title"].split()).casefold() in " ".join(doc[verso - 1].get_text().split()).casefold(),
                        f"{card['title']}: commentary page missing")
                require(len(doc[recto - 1].get_images()) == 1, f"{card['title']}: missing illustration")
                tarot_spreads += 1
        next_page = end + 1
        components += 1
    require(log["colophon_page"] == next_page, "Missing or misplaced colophon")
    require("Colophon" in doc[next_page - 1].get_text(), "Colophon missing")
    if bibliography:
        first, last = bibliography["start_page"], bibliography["end_page"]
        require(first % 2 == 1 and first in (next_page + 1, next_page + 2), "Bibliography opening misplaced")
        if first == next_page + 2:
            require(not doc[first - 2].get_text().strip(), "Bibliography alignment leaf is not blank")
        require(last == len(doc), "Bibliography is not the final section")
        require("Bibliography" in doc[first - 1].get_text(), "Bibliography heading missing")
        mapped = {p["bound_page"] for s in registers.values() for p in s["page_map"]}
        require(mapped | set(bibliography["blank_pages"]) == set(range(first + 1, last + 1)),
                "Unexplained bibliography leaf")
        require(relocated == bibliography["source_pages"], "Moved source-page count differs")
        for physical in bibliography["blank_pages"]:
            require(not doc[physical - 1].get_text().strip() and not doc[physical - 1].get_images(),
                    "Bibliography alignment leaf is not blank")
    else:
        require(next_page == len(doc), "Unexpected leaves after colophon")
    for page in doc:
        require(abs(page.rect.width - 504) < .01 and abs(page.rect.height - 720) < .01,
                f"Page {page.number + 1}: wrong trim")
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                require(page.rect.contains(fitz.Rect(line["bbox"])),
                        f"Page {page.number + 1}: text outside page bounds")
    # Each source retains its own pagination; the contents uses physical page ranges.
    contents = " ".join(doc[1].get_text().split())
    for title, entry in log.items():
        if isinstance(entry, dict) and "start_page" in entry:
            require(f"pages {entry['start_page']}–{entry['end_page']}" in contents,
                    f"{title}: contents page range missing or clipped")
    result = {"pages": len(doc), "components": components, "facing_tarot_spreads": tarot_spreads,
              "all_components_start_recto": True, "source_hashes_match": True,
              "bibliography_source_pages": relocated, "source_leaves_preserved_once": True,
              "bibliography_at_end": bool(bibliography)}
    pdf.with_name("binding-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    validate(parser.parse_args().pdf)
