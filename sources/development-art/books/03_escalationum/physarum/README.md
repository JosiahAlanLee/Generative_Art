# Physarum figures for the office plates

A study, outside the book's build. Two office plates, Gremory (Customer Success Manager, station 2) and Orobas (Deputy Department Head, station 4), redrawn as plottable line by a slime-mould transport model grown over their figure renders. Made 18–19 October 2026 with Claude.

**Provenance.** The model feeds on `references/raster/batch-01/gremory-raster-reference-v01.png` and `orobas-raster-reference-v01.png`. These figures are therefore derived from a reference render, unlike the book's native plot masters and unlike the general statement in `references/README.md` that nothing there is traced into a plate. Nothing in the book's build uses them. Book III's README still says no reference was embedded or traced; it is left unchanged because the book's build manifest records the README's hash (`tests/test_book.py`), so a note there belongs with the next rebuild. The proofs use the illustrated edition's plate pages (15 and 25) with the render removed. Untested on a physical plotter.

## Contents

| Path | What |
| --- | --- |
| `physarum_plot.py` | The tool: raster in, Physarum network out, as a layered plotter SVG. Works on any image; `--help` lists the options. |
| `study.py` | Rebuilds everything in `out/` from this repository (all 28 runs, about 20 minutes on two cores). |
| `out/plot/<run>/` | Plot masters for each office at its own station: one culture per pen (`network`), competing cultures with home ground and symbiotic cultures (`network`, `hatch`, `marks`). 180 mm wide for a 0.3 mm pen, one Inkscape/AxiDraw layer per pen in light-to-dark order; `run.json` holds the settings, `stats.json` the line lengths and pen-up travel. |
| `out/proofs/` | Six pages per office on its plate page: one culture per pen; competing plate and hatch; symbiotic plate, hatch and marks. |
| `out/sheets/` | Six comparison sheets (below). |
| `out/manifest.json` | Sources and their hashes, the settings and trail shares of all 28 runs, code and library versions, and the hash of every committed output. |
| `out/work/` | Every run in full, including the styles not committed. Git-ignored; `study.py` recreates it. |

## The model

The rule is Jones (2010), the one Book V's notae run [V/S9]: each agent senses the trail at three points ahead, turns toward the strongest, steps and deposits; the trail diffuses (3 × 3) and decays; one agent to a cell. Here it is coupled to the render. Agents also sense a food map (ink darkness plus edges) and their heading is nudged along the drawing's contours.

The station is the dial between two looks, **faithful** (strong pull toward the drawing, fine mesh) and **feral** (weak pull, coarse mesh that mostly follows its own trail). It is used two ways:

- **One culture per pen.** Ochre, steel and slate each get a population fed by its own colour separation. The station moves every population from faithful at station 0 to feral at station 6.
- **Two cultures.** A faithful culture drawn in slate and a feral culture drawn in ochre share the figure. The station sets the feral share of the agents, 15 % at station 0 to 85 % at station 6; neither culture changes how it behaves.
  - *Competing:* they repel each other's trails. Left alone they interleave (`woven`). With territories (`fight`) the figure starts as 24 held regions and the ground is marked: a culture gets a quarter of the drawing's pull on the other's ground and respawns near its own colony, so borders move only by competition. With home ground (`home`) the regions holding Gremory's face, letter and cup and Orobas's eye and spiral always go to the faithful culture.
  - *Symbiotic* (`symb`): they attract each other and draw the same cords.

Rust is an accent in both modes. It draws only on the red marks: Gremory's seal on the letter and the arc of Orobas's spiral.

## Styles

- `topo`, `network`, `fibers`: nested contours of the trail, tapered centrelines, and traced agent paths.
- `hatch`, after the Book V notae (`books/05_notoria/plates/notae.py`, `Field.hatch`): outline, then hatch, then crosshatch as the trail thickens. The notae hatch a coarse field (160 cells) directly. These trails are fine vein networks, which break into confetti when hatched directly, so they are smoothed into tone first. Each layer hatches in its own direction (ochre 135°, slate 45°, rust 90°), so overlapping cultures crosshatch, and on the competing plates territory shows as hatch direction.
- `marks`, after the Nota Clausa plates (`books/07_septimus/clausa/`): one short dash per 1 mm lattice cell, laid along the vein, in the pen of the stronger layer, inside a double contour. In the cipher every dash is an agent on its 0.7 mm lattice, pointing along its last heading. These follow the vein direction instead, so they are more orderly.

## What the runs show

Measured on these runs (all figures from `out/manifest.json` and the runs' `stats.json`):

- **One culture per pen.** Higher stations draw less of the figure. Network line falls from 41.1 m at station 0 to 30.6 m at station 6 for Gremory, and from 33.7 m to 25.0 m for Orobas (`station-dial-one-culture-per-pen.jpg`).
- **Competing cultures.** They do not divide the figure on their own: unmarked territories mixed again within 1,200 steps, and only marked ground holds a border. With home ground, the faithful culture's share of the network line falls from 77 % at station 0 to 26 % at station 6 for Gremory, and from 83 % to 34 % for Orobas, as the feral honeycomb takes the figure region by region (`cultures-competing-station-sweep.jpg`). At a spirit's own station the share moves only a few points between woven, territories and home ground (Gremory 65, 64, 62 %; Orobas 50, 46, 53 %); where the regions happen to fall matters about as much as the home ground does (`cultures-compared.jpg`).
- **Home ground does not keep a face.** It keeps faithful line on Gremory's face, but that line draws the hood's outline and a few loops; eyes and mouth are below what the network resolves at this size.
- **Symbiotic cultures** share every cord, so each culture's share of the trail is about its share of the agents: 85 % faithful at station 0 and 20 % at station 6 for both spirits. In `hatch` the shares are closer (Gremory 70 to 47 %, Orobas 67 to 48 %), since each culture hatches the cords they share (`cultures-symbiotic-station-sweep.jpg`, `competing-vs-symbiotic.jpg`).
- **The hatching** comes from two different mechanisms, compared in `hatching-sources.jpg`: engraving-style crosshatch over the notae's bands, and the cipher's agents, each one a dash.

## Plotting

Pen layers are written light to dark (ochre, steel, slate, rust; or ochre, slate, rust for cultures), so plotting them in order puts dark lines and the accent on top. At 180 mm wide, for the office's own station:

| Run | Style | Strokes | Line | Pen-up travel |
| --- | --- | --- | --- | --- |
| Gremory, one culture per pen | network | 3,148 | 36.8 m | 8.4 m |
| Gremory, competing with home ground | network / hatch / marks | 1,264 / 3,074 / 9,812 | 17.1 / 20.3 / 13.0 m | 4.3 / 5.4 / 9.3 m |
| Gremory, symbiotic | network / hatch / marks | 2,063 / 4,706 / 10,574 | 24.1 / 29.7 / 13.1 m | 5.3 / 7.9 / 10.8 m |
| Orobas, one culture per pen | network | 2,054 | 27.9 m | 6.3 m |
| Orobas, competing with home ground | network / hatch / marks | 894 / 2,621 / 8,338 | 13.8 / 17.4 / 12.1 m | 3.4 / 4.8 / 8.3 m |
| Orobas, symbiotic | network / hatch / marks | 1,680 / 4,171 / 8,811 | 20.9 / 25.7 / 11.7 m | 4.8 / 7.0 / 9.3 m |

`marks` is short in line but nearly every dash is a pen lift, so it is the slowest to plot; the Nota Clausa plates carry 7,920 marks each. Untested on a physical plotter; start with a 0.2–0.3 mm fineliner.

## Rebuild

```sh
python -m pip install -r requirements.txt
python study.py               # every run, then the selection, proofs, sheets and manifest
python study.py --skip-runs   # only the selection, proofs, sheets and manifest, from out/work/
```

Runs are seeded and repeat exactly on the same machine and library versions; another CPU or another numba or numpy version can change the trajectories, though not their character. `requirements.txt` pins the versions the committed outputs were built with (Python 3.13.16).

## Not here

The GPT "primitive growth" page proofs for these two plates, which started the comparison, are not in the repository. Neither are the earlier exploratory runs; everything in `out/` was rebuilt from the files above.
