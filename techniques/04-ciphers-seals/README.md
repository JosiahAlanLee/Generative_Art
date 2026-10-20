# Ciphers, lettering and seals

Text is a generative input here: some marks are actual recoverable messages.

The collection retains the substitution hand, twelve-sign-plus-tally transcription, shifted variants, biliteral carrier, office litany and ordered-path carrier. Semiphoras reverses the middle of three 72-letter sentences and reads columns into 72 trigrams. Repeated trigrams retain distinct position identifiers.

Use encode/decode and validation functions before and after changing mark geometry. Path order can carry text; optimization or sorting can change the reading. Nota Clausa is documented and supplied as sealed public SVG artifacts: its key and enciphering implementation are absent from the source book, so this collection cannot regenerate it.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Matricis substitution alphabet** (`book`) | Write recoverable text with dot/ring terminals | [cipher.py](../../sources/codex-intervallorum/books/01_matricis/generator/cipher.py) |
| **Twelve-sign plus tally transcription** (`book`) | Generate script strips and circular inscriptions | [tx.py](../../sources/codex-intervallorum/common/geometry/tx.py)<br>[marks.py](../../sources/codex-intervallorum/common/geometry/marks.py) |
| **Biliteral drawing carrier** (`book`) | Carry five-bit letters in scale ticks or head/no-head marks | [ornament.py](../../sources/codex-intervallorum/common/plot/ornament.py) |
| **Shifted signs, office litany and ordered paths** (`book`) | Use position, form or drawing order as a text carrier | [codec.py](../../sources/codex-intervallorum/books/04_graduum/proofs/ix-gpt/codec.py)<br>[ciphers.py](../../sources/codex-intervallorum/books/04_graduum/proofs/x-xi-v-gpt/ciphers.py)<br>[tabula_vii.py](../../sources/codex-intervallorum/books/04_graduum/plates/vii-native/tabula_vii.py) |
| **Semiphoras 72-name transposition** (`book`) | Generate trigrams and indexed seals from three sentences | [semiphoras.py](../../sources/codex-intervallorum/books/07_septimus/semiphoras/semiphoras.py)<br>[build.py](../../sources/codex-intervallorum/books/07_septimus/build.py) |
| **Nota Clausa field carrier** (`sealed-artifact`) | Inspect the public rule and sealed SVGs; validate a proposed reading | [REGULA.md](../../sources/codex-intervallorum/books/07_septimus/clausa/REGULA.md)<br>[TABULA.md](../../sources/codex-intervallorum/books/07_septimus/clausa/TABULA.md)<br>[validate.py](../../sources/codex-intervallorum/books/07_septimus/clausa/validate.py) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
