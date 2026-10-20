# Nota Clausa

A closing gathering for the seventh book: seven fields grown by a printed rule, each carrying a reading the growth has scattered. It is the series' one cipher whose key is not printed.

- `TABULA.md` is the leaf in the grimoire register. It says where the key is and prints the SHA-256 digests of the seven readings.
- `REGULA.md` is the rule, printed whole: an integer restatement of the rule of the notae (Book V, after Jones), with its random-number generator, seed derivation, sign table and plate geometry. Anyone can implement it from the page.
- `plates/nota-clausa-1.svg` … `nota-clausa-7.svg` are the plot masters: A4, stroke-only, two inks, Art Paths and Text Outlines layers, and a drawn reserved blank. Each carries 7920 marks, one per cell, red for 1 and black for 0, on contour lines of the field the same growth left.
- `build.py` sets the reading edition, `out/Nota_Clausa_reading.pdf` (title, Tabula, Regula, seven fields; 7 × 10 in). It builds from the files above only.
- `validate.py` checks the plates against the Regula's ground and the Tabula's digests. With `--reading folder/`, it checks a proposed reading against the digests.

```sh
python books/07_septimus/clausa/build.py
python books/07_septimus/clausa/validate.py
python books/07_septimus/clausa/validate.py --reading path/to/readings   # field-1.txt … field-7.txt
```

## What is not here

The plaintext, the key, the seeds and the enciphering script are not in this repository and have never been committed to it. The author holds them. Nothing in this tree can regenerate the plates or read them without the key. This is the one place where the series' rule that every figure regenerates from its manifest is suspended, and the suspension is the point.

## Fairness record

On 17 October 2026, a separate agent was given only the Regula, the seven plot sheets and the key, and was told not to look at any other implementation. It wrote its own decoder from the printed rule and matched all eight digests on its first run, in about 80 seconds on two cores. It found no point where the rule was wrong. The places where it had to choose an interpretation (left and right as names, release of a cell within a step, deposit on a move inside one cell, and how to find the marks in the SVG) are now stated in the Regula. The digests confirm that its choices were the right ones.

## Placement

Bound at the end of De Vinculis in both editions, after the seventy-two seals, since 19 October 2026: its own unnumbered component (`bind.CLAUSA`), last before the collected bibliography. Its leaves keep their folios and page sides. It has no register; its hand line, what is not here and the fairness record above are filed with the production notes. The pen-finishing pass leaves it untouched, and the binding validator checks that it follows De Vinculis with its seven fields intact. CI builds and validates it before binding. The Clavis carries one paragraph declaring it.

When the Tarot of Intervals left the bindings on 19 October, the Tabula's third clue still called it the sixth book. The clue now names the Tarot and says it is a volume of its own. The key, the plates and the digests are unchanged.

Hand: Claude (text, rule, plates, reading edition).

