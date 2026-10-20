# Attribution and third-party notices

Project and original grimoire: Josiah Alan-Lee. The upstream repository was
developed primarily with Claude. This divergent edition was prepared in
collaboration with ChatGPT/Codex at the author's request.

The original geometry and invented mark vocabulary in `generator/core.py`,
`marks.py`, `hands.py`, and `tx.py` are retained from upstream commit
`cb893d600d78db14d74084f7ebacfa7d112f68a0`. `tx.py` has been made portable.
`plotter/` and its sole source SVG are retained as a separate workshop tool.
New manuscript text, diagram layouts, book generation, and the scheduling
specimen are additions for this divergent edition.

No new blanket copyright license is assigned for the project, manuscript, or
artwork. The author can choose distinct terms for code and creative content.
Do not interpret a typeface license as a license for the surrounding work.

## Bundled fonts

Full upstream license notices are included in `fonts/licenses/`:

| Family | Files in this distribution | Notice |
| --- | --- | --- |
| IM FELL English | `IMFeENrm28P.ttf`, `IMFeENit28P.ttf` | `imfellenglish-OFL.txt` |
| IM FELL English SC | `IMFeENsc28P.ttf` | `imfellenglishsc-OFL.txt` |
| EB Garamond | `static/EBGaramond-Regular400.ttf`, `static/EBGaramond-Italic400.ttf` | `ebgaramond-OFL.txt` |
| IBM Plex Mono | `IBMPlexMono-Regular.ttf` | `ibmplexmono-OFL.txt` |
| Sue Ellen Francisco | `SueEllenFrancisco-Regular.ttf` | `sueellenfrancisco-OFL.txt` |

The two EB Garamond files are the weight-400 static instances inherited from
the original project. They are not represented as newly downloaded official
static releases. Source font notices were retrieved from each family's
`ofl/<family>/OFL.txt` in `google/fonts` on 16 October 2026 UTC.

Python dependencies are installed separately and retain their own licenses.
Hershey lettering in the inherited plotter tool is supplied by Hershey-Fonts;
see that package's upstream notices and its role in `plotter/README.md`.

## Scholarly sources

Only original diagrams and short paraphrases are used. No source-paper figures,
articles, or book scans are redistributed. Source URLs and inspection limits
are in `docs/SOURCES.md` and the PDF's reference register. The supplied five-page
research packet is identified but is not republished in this source package.
