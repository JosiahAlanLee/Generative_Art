# Node lattice

A generator for the cellular lattice on the demon renders: ochre struts around slate and cream cells, chains of round cells, rose windows, beads at the junctions, hems that fray into beaded chains, and drips ending in dots. It grows the lattice from a seed inside a host silhouette, then writes either an illustrated render or a stroke-only plot master. Made 19 October 2026 with Claude at the author's request. It sits outside every build, and no book uses it yet.

![The three samples illustrated, then the first as plotted](out/sheet.jpg)

*Left to right: an empty robe, the same robe half dissolved, a lattice grown in Choronzon's outline, and the first robe as its plot master draws it. The preview was rendered in the page, and the tests do not check it.*

**Provenance.** The idiom is taken from the GPT raster references: the batches in `references/raster/` (prompts in each batch's `figures.json`) and the Tarot's Choronzon and Foras in `books/06_tarot/`. No pixel of a render enters a plate. **Native hosts** (an empty robe, an empty chair) are built from the seed and use no raster at all. **Traced hosts** use one render's outline, as a mask on a 250 × 375 grid. `hosts.json` records each source's path and sha256, and every plot master repeats them in its description. Like the Physarum study (`books/03_escalationum/physarum/`), a plate on a traced host is derived from a reference render. That is unlike the statement in `references/README.md` that nothing there is traced into a plate; that file is left as it stands.

## Contents

| Path | What |
| --- | --- |
| `lattice.js` | The generator: host field, packing, power diagram, panes, open net, node web, drips. Seeded, with no canvas, so it runs in Node and in a page. |
| `render.js` | The illustrated render (canvas, in the page), the plot strokes, and the SVG writer. |
| `hosts.json` | Eleven traced host masks, each with its source path, sha256, crop and opening radius, plus the tracing method and library versions. |
| `trace_hosts.py` | Rebuilds `hosts.json` from the renders (`requirements.txt`). |
| `plate.mjs` | Writes one plot master from the command line. |
| `samples.mjs` | Rebuilds `out/plot/` and `out/manifest.json`. |
| `template.html`, `build.mjs` | The page source and its assembler. |
| `node-lattice.html` | The page, built. Open it in a browser from a checkout; it needs no server. |
| `out/plot/` | Three sample plot masters (below). |
| `out/manifest.json` | Each sample's host, seed, parameters, counts and sha256. |
| `out/sheet.jpg` | The preview above. |
| `tests/` | `lattice.test.mjs` (Node) and `test_svgimport.py` (Python, standard library only). |

## How a plate grows

1. **Host.** A signed distance field from the host: a traced mask, or a robe or chair built from the seed out of rounded cones and polygons.
2. **Packing.** Ellipses are packed inside the host and out past its edge as far as the fray reaches. Deep in the body they are long and lie along the drape; in a band at the edge they are small and round. The band is thin along the sides and deep at hems and undersides.
3. **Power diagram.** An anisotropic power diagram of the packing gives one cell per ellipse. Neighbours share exact vertices.
4. **Panes.** Deep cells become panes between curved ribs. The ribs bow together from a smooth field, so neighbouring ribs sweep the same way. A pane is a chain of round cells (the largest become rose windows), slate with veins, fine lace, a dark hollow, or open.
5. **Open net.** Edge cells become ochre rings around an elliptical hole: cream, a few slate, a few dark. Junctions between openings get small cells and beads.
6. **Node web.** Cells outside the body, and cells the dissolution takes, give up their membrane. Their edges become the node web: tendrils that leave the membrane and drift outward and down to terminal dots, with a little netting near the body. Dissolution works patch by patch, by a noise field over the body.
7. **Drips.** Drips fall from the undersides of the membrane and from tendril ends, with beads, an occasional slate pearl and a dot at the foot. The red ground ring sits under the host's own silhouette, so it stays put however far the lattice dissolves. The robe carries a dark void in its hood, and a seal with a red broken ring sits deep in the upper body of any host.

The membrane's outline and every inside-the-membrane test come from a coverage grid (4 × 4 samples per half-unit cell), computed in plain arithmetic for the reason given under Reproducibility.

## Parameters

| Name | Default | What it does |
| --- | --- | --- |
| `cell` | 13 | Cell size in page units (the page is 1000 × 1500) |
| `rib` | 2.6 | Pane size, as a multiple of `cell` |
| `elong` | 2.3 | How much longer a pane is than wide |
| `drape` | 0.5 | 0: panes follow the outline; 1: panes hang straight down |
| `sweep` | 0.12 | How far the ribs bow |
| `strut` | 2.2 | Strut width between openings |
| `slate` | 0.55 | Share of slate in panes and the net |
| `roses` | 4 | Rose windows, taken from the largest round cells |
| `fray` | 105 | How far the web reaches past the silhouette |
| `drips` | 0.55 | Drip frequency and length |
| `dissolve` | 0 | Share of the membrane turned into node web |
| `ground` | true | The red ground ring |
| `seal` | true | The seal with its red broken ring |

`cell`, `rib`, `elong`, `drape` and `seal` change the packing. The page keeps the packing while the other controls move, and regrows it when one of these does.

## Plot masters

A4 in millimetres, with the figure at 180 × 270 mm inside 15 and 13.5 mm margins. Every mark is a pen stroke: dots are coils, tone is hatching, and nothing is filled. There are two pen modes:

- **Series** (the default): the books' form, two layers (`Art Paths`, and `Text Outlines`, left empty) and two inks, `#161918` and `#a32b24`, at 0.22, 0.17 and 0.12 mm. Slate is hatched 0.61 mm apart. Dark panes and the hood's void are crosshatched 0.43 mm apart, and dark cells are hatched at that spacing. The ochre ribs become ink hairlines.
- **Study**: four layers, one per pen, light to dark (`1 Ochre`, `2 Slate`, `3 Ink`, `4 Red`), as in the Physarum study. Strut highlight rings appear only here.

These are figure masters, not plates, so there is no frame, title block or reserved blank. A plate generator can place one with `common/plot/svgimport.py`, which reads every stroke of these files (`tests/test_svgimport.py`). Strokes are in drawing order, not optimised for pen-up travel. Untested on a physical plotter.

| Sample | Host | Strokes | Line | Red |
| --- | --- | --- | --- | --- |
| `robe-handoff` | empty robe, seed `handoff` | 4,313 | 28.4 m | 0.26 m |
| `robe-handoff-dissolve-50` | the same, `dissolve=0.5` | 3,064 | 16.7 m | 0.26 m |
| `choronzon-handoff` | Choronzon's outline, seed `handoff` | 4,967 | 32.0 m | 0.19 m |

## Commands

```sh
node common/lattice/plate.mjs --list
node common/lattice/plate.mjs --host robe --seed handoff --out robe.svg
node common/lattice/plate.mjs --host choronzon --set dissolve=0.4 --pens study --out choronzon.svg --record choronzon.json
node common/lattice/samples.mjs            # rebuild out/plot/ and out/manifest.json
node common/lattice/build.mjs              # rebuild node-lattice.html after changing a source
node --test common/lattice/tests/lattice.test.mjs
python -m unittest discover -s common/lattice/tests -v
python -m pip install -r common/lattice/requirements.txt && python common/lattice/trace_hosts.py   # re-trace the hosts
```

Node 22 needs no packages. `trace_hosts.py` needs NumPy, SciPy and Pillow, pinned in `requirements.txt` at the versions that made `hosts.json`.

## Reproducibility

A seed reproduces exactly in Node 22, which the tests pin. On 19 October 2026 the page in Chromium 141, which uses the same JavaScript engine as Node, wrote all three samples byte for byte. Browsers built on other engines may differ in small details, because JavaScript does not fix the last bit of `sin`, `cos` and similar functions across engines. The illustrated render is drawn on a canvas and differs slightly between browsers; the plot master does not depend on the canvas.

The tests check that:

- every traced host's source exists with its recorded sha256, and its mask decodes to its recorded area;
- a seed gives the same file twice, and two seeds give different files;
- series masters keep the two-layer, two-ink form, with stroke-only paths, the three weights, and every point inside the figure box;
- study masters carry the four pens in order;
- the membrane shrinks and the web grows as dissolution rises;
- the committed samples rebuild byte for byte and match the manifest;
- `node-lattice.html` is built from the current sources.

## Limits

- No faces, hands or held objects. In the renders those carry much of each figure's identity.
- Thin parts break up, because the lattice cannot go much narrower than one cell. Bael's chair legs fall into separate fragments and Choraz's horns become a tangle. Robe-shaped hosts hold together best.
- A traced mask keeps anything dense enough to read as body, held objects included, such as Vassago's book and Paimon's megaphone.
- There are two native hosts, the robe (one hood, empty sleeves) and the chair.
