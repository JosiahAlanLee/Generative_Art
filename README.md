# Generative Art

The code for the 29 generative projects Echevarian published on fxhash between November 2021 and November 2022, and for the two interactive pieces before them on Hic et Nunc, archived so that each one still runs without either platform.

The viewer, `index.html`, runs every minted iteration from its archived code, and any project with a new random hash. Pieces titled with a strobe warning wait for a click before they run, and so does every piece when the system asks for reduced motion. To publish it, turn on GitHub Pages for this repository (Settings, Pages, deploy from the `main` branch, root folder); it will then be at https://josiahalanlee.github.io/Generative_Art/.

## What is here

- `projects/<id>-<title>/generator/`: each project's generator folder, byte for byte as fxhash stored it on IPFS.
- `projects/<id>-<title>/iterations/NNN/`: for the earliest iterations, the token's own folder (see [Early iterations](#early-iterations)).
- `data/onchain.json`: each project as the Tezos chain records it: the mint operation, editions, price at launch, royalties, and how sales and royalties were split.
- `data/iterations/<id>.json`: every minted iteration: its hash, token, mint operation, and the IPFS addresses of its metadata and capture images.
- `data/metadata/`: the project metadata files, byte for byte.
- `data/folders.json`: every archived folder and file, its original CID, and whether adding it to IPFS again gives that CID back.
- `data/catalog.json` and `data/cids.txt`: built from the above, for the viewer and for pinning.
- `tools/`: the scripts that produced all of this. They can be run again.

## Projects

<!-- projects:start -->
| Published | Project | Minted | Code |
|---|---|---|---|
| 2021-11-17 | polygon chaos | 15 of 15 (400 at launch) | not yet archived |
| 2021-12-08 | banner_day | 50 of 50 | not yet archived |
| 2021-12-11 | banner_day2 | 100 of 100 | not yet archived |
| 2021-12-17 | polygon_chaos2 (strobe warning) | 25 of 25 (50 at launch) | not yet archived |
| 2021-12-18 | polygon_chaos3 | 13 of 13 (100 at launch) | not yet archived |
| 2021-12-22 | difference_engine | 19 of 19 (150 at launch) | not yet archived |
| 2021-12-23 | difference_engine2 (strobe warning) | 11 of 11 (100 at launch) | not yet archived |
| 2021-12-26 | banner_day3 | 100 of 100 | not yet archived |
| 2021-12-27 | difference_engine3 | 50 of 50 | not yet archived |
| 2022-01-05 | quilt_trail | 25 of 25 (150 at launch) | not yet archived |
| 2022-01-07 | lensing | 11 of 11 (128 at launch) | not yet archived |
| 2022-01-09 | singularity_quilt | 13 of 13 (128 at launch) | not yet archived |
| 2022-01-28 | lensing2 | 15 of 15 (50 at launch) | not yet archived |
| 2022-02-04 | rosette | 250 of 250 | not yet archived |
| 2022-02-07 | maelstrom | 30 of 30 | not yet archived |
| 2022-04-16 | maelstrom2 | 75 of 75 | not yet archived |
| 2022-04-29 | cathode_cosmos | 20 of 20 (50 at launch) | not yet archived |
| 2022-05-02 | maelstrom3 | 20 of 20 (100 at launch) | not yet archived |
| 2022-05-21 | warp (maelstrom4) | 15 of 15 (150 at launch) | not yet archived |
| 2022-05-21 | weft (banner_day4) | 55 of 55 (250 at launch) | not yet archived |
| 2022-05-25 | warp&weft2 | 50 of 50 (150 at launch) | not yet archived |
| 2022-05-28 | warp&weft3 | 92 of 92 (150 at launch) | not yet archived |
| 2022-05-29 | generator6 | 150 of 150 (200 at launch) | not yet archived |
| 2022-06-11 | test_pattern | 41 of 41 (64 at launch) | not yet archived |
| 2022-06-12 | generator7 | 25 of 25 (128 at launch) | not yet archived |
| 2022-09-13 | test_pattern2 | 15 of 15 (64 at launch) | not yet archived |
| 2022-09-23 | project 19732 | 0 of 64 | not yet archived |
| 2022-09-23 | test_pattern3 (game of life) | 24 of 24 (128 at launch) | not yet archived |
| 2022-11-15 | polygon_chaos4 | 50 of 50 (365 at launch) | not yet archived |
<!-- projects:end -->

The two interactive p5.js pieces minted before them on Hic et Nunc are kept the same way, in `hen/`:

<!-- hen:start -->
| Published | Piece | Editions | Code |
|---|---|---|---|
| 2021-10-25 | plasma_field (OBJKT 472545) | 25 | not yet archived |
| 2021-10-25 | catherine_wheel (OBJKT 472865) | 25 | not yet archived |
<!-- hen:end -->

## How it was assembled

1. `tools/collect.py` reads the chain through the TzKT indexer: the author's project mints, the fxhash issuer ledger, and every gentk token minted from the projects. An fxhash hash is the hash of the operation that minted the token, so each iteration's hash is checked against its mint operation, and the script stops if any differs. All 1,354 hashes recorded in token metadata match. For the other five, the hash comes from the operation alone: fxhash never signed banner_day2 #95, and four tokens were signed on chain but the indexer still holds the unsigned placeholder.
2. `tools/archive.py` fetches each folder and metadata file from an IPFS trustless gateway one block at a time, and `tools/fetch.mjs` rejects any block whose bytes do not hash to its CID. The folders are rebuilt from the checked blocks, then hashed again the way `ipfs add` did in 2021 to see whether they reproduce the original CID.
3. `tools/build.py` writes the catalog the viewer reads, the list of CIDs to pin, and the tables in this file.

`tools/verify.mjs` re-hashes every archived folder as checked out, without fetching anything. A GitHub workflow runs it on every change.

To run everything again: `pip install requests`, `npm ci` in `tools/`, then `python3 tools/collect.py`, `python3 tools/archive.py` and `python3 tools/build.py`.

## Early iterations

Until late December 2021, fxhash wrote each token's hash into its own copy of the code when the token was minted, and that copy is what the token points to. Later tokens point to the shared generator and pass the hash in the address (`?fxhash=`). The archive keeps both: the token's own folder where one exists, and the generator. For a generator that predates `?fxhash=`, the viewer makes a new random hash by doing in the browser what fxhash did on its server: it writes the hash into the page before running it. The archived files are not changed.

## Pinning on your own computer

Install Kubo (the `ipfs` command) or IPFS Desktop and run `ipfs init` once. Then, from this folder:

    python3 tools/pin.py             # the folders and metadata kept here
    python3 tools/pin.py --network   # also the capture images and token metadata

The first command works offline. It adds each folder with the settings fxhash's uploads used and pins it only if the CID matches the original. The second needs the IPFS node running, and it can only fetch what some other node still serves.

## Credits

The project descriptions name these sources and contributors. Their exact words are in `data/catalog.json` and on each project's page in the viewer.

- banner_day, banner_day2 and banner_day3 started from Jerome Herr's sketch [forma]; banner_day's description records his blessing to mint it. They also use @SableRaph's Hic et Nunc generative template and Sayama's p5.pattern library.
- Most of the projects from polygon_chaos2 on are made with Hydra (https://github.com/ojack/hydra).
- maelstrom and maelstrom2 began from @thingticket's piece "Game Over".
- test_pattern3 combines Hydra with John Conway's Game of Life and aebrer's entropy locking algorithm. Its description also names Nicthib's work during the fxhash beta, such as 56 Modes, and Memo Akten's PixlFlippr.
- Libraries named in the descriptions: p5.js, Hydra, GPU.js, chroma.js and p5.pattern.

Shares written into the projects' sales and royalties on chain:

<!-- splits:start -->
| Project | Sales | Royalties |
|---|---|---|
| cathode_cosmos | Echevarian 100% | 20% of resales: Echevarian 80%, first minter 20% |
| maelstrom3 | Echevarian 70%, Processing Foundation 15%, Hydra's inventor 15% | 20% of resales: Echevarian 90%, first minter 10% |
| warp (maelstrom4) | Echevarian 80%, Hydra's inventor 10%, Processing Foundation 10% | 15% of resales: Echevarian 70%, Hydra's inventor 10%, Processing Foundation 10%, first minter 10% |
| weft (banner_day4) | Echevarian 90%, Processing Foundation 10% | 20% of resales: Echevarian 90%, Processing Foundation 10% |
| warp&weft2 | Echevarian 80%, Hydra's inventor 10%, Processing Foundation 10% | 15% of resales: Echevarian 25%, first minter 25%, Hydra's inventor 25%, Processing Foundation 25% |
| test_pattern | Echevarian 90%, Hydra's inventor 10% | 15% of resales: Echevarian 80%, Hydra's inventor 10%, first minter 10% |
| generator7 | Echevarian 80%, Hydra's inventor 10%, Processing Foundation 10% | 15% of resales: Echevarian 70%, first minter 10%, Processing Foundation 10%, Hydra's inventor 10% |
| test_pattern2 | Echevarian 80%, aebrer 10%, Hydra's inventor 10% | 15% of resales: Echevarian 80%, aebrer 10%, Hydra's inventor 10% |
| test_pattern3 (game of life) | Echevarian 80%, Hydra's inventor 10%, aebrer 10% | 15% of resales: Echevarian 25%, Hydra's inventor 25%, first minter 25%, aebrer 25% |
| polygon_chaos4 | Echevarian 50%, Hydra's inventor 25%, Processing Foundation 25% | 15% of resales: Echevarian 75%, first minter 25% |

In every other project, sales and royalties went to Echevarian alone. "Hydra's inventor" is how the descriptions name the recipient at tz1V1WKxhK9g5UFbhRNUnQMmDnnL2vtBzoZJ, which has no public alias on TzKT. "First minter" is fxhash's share for whoever minted each iteration, recorded against the gentk contract.
<!-- splits:end -->

## Licences

No licence has been chosen yet for the artist's own code here. The libraries bundled inside the generator folders keep their own licences.
