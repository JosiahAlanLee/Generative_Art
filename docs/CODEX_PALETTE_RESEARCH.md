# Codex palette: data and techniques from the text — 20 October 2026

Prepared with Claude for Josiah Alan-Lee. The pass read the public book at
[`b789e03`](https://github.com/JosiahAlanLee/Codex-Intervallorum/tree/b789e03f30034bc8403f8a40aaf83842885aaad5):
the manuscripts, the plate generators and records, and the 19 October art notes.
It recorded what the text names that no plate draws, then looked for public
data and drawing techniques that this collection does not have. Four leads are
implemented as [Codex palette studies](../techniques/14-codex-palette/README.md),
using only the book's own records. No outside dataset is copied into this
repository.

Licence and terms statements were checked on 20 October 2026 by fetching the
publisher's licence, terms or rights page; "unchecked" marks a statement taken
from a secondary page or not confirmed. The status words describe what a
publisher states. They are not a legal opinion.

| Status | Meaning here |
| --- | --- |
| **open** | Public domain, CC0, CC BY, MIT, BSD or Apache: usable with the stated attribution |
| **share-alike** | CC BY-SA content and GPL software have different scopes. Sharing an adaptation of CC BY-SA content invokes its share-alike terms. GPL obligations concern covered software; an image is not automatically GPL merely because a GPL program generated it. Embedded covered material can change that analysis. |
| **non-commercial** | Keep it out of a sold edition without written permission |
| **no licence** | Link, cite and transcribe facts; do not copy the files |
| **restricted** | Written permission first |

The software/output distinction is explicit in [GPLv3 §2](https://www.gnu.org/licenses/gpl.en.html#section2).
Assess the generator's code, bundled assets, input data and exported image
separately; a code licence alone does not settle the rights in all four.

## 1. What the text names and no plate draws

Book references point to the pinned commit; `RE` is the joined I–II reading
edition.

| Where | In the text, undrawn | Data lead | Technique lead |
| --- | --- | --- | --- |
| I–II | Six public postmortems sit in the register ([RE:847–857](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/01_matricis_intervallorum/manuscript/reading-edition.md#L847-L857)); the combined text dropped "the unsupported causal split of outage time" ([RE:867](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/01_matricis_intervallorum/manuscript/reading-edition.md#L867)) | Status-page incident updates, which record when a provider said each thing, not why the outage lasted (§2.1) | A lifecycle ladder of published status changes; the existing [recurrence loom](../techniques/12-process-art/README.md) fed a real CSV |
| I–II | ASRS's separation of reporting from enforcement ([RE:281](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/01_matricis_intervallorum/manuscript/reading-edition.md#L281)) | ASRS intake and NTSB accident counts (§2.1) | Paired ridgelines in the [Driftless](../techniques/11-landscape-plates/README.md) hidden-line hand, captioned with ASRS's own warning that counts do not measure prevalence |
| I–II, V | Kramar and Alim's tube-diameter hierarchy ([RE:127](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/01_matricis_intervallorum/manuscript/reading-edition.md#L127)); every Physarum figure is Jones's agent model | Nota V's own seven nodes | **Implemented:** Tero's flux-adapted tubes (§3.1) |
| III | Authority, competence and blame appear only as tallies ([generator/art.py:172–176](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/03_escalationum/generator/art.py#L172-L176)); seven reachability cases are computed ([reachability.py:115–122](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/03_escalationum/generator/reachability.py#L115-L122)) and one is drawn; the Goetic source tradition is named but not drawn ([catalogue.json:549](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/03_escalationum/manuscript/catalogue.json#L549)) | The catalogue's numbers; the 1904 Goetia's ranks, legions and seal metals (§2.4) | **Implemented:** guilloché credentials. Also a hive plot (axes: authority, competence, liability; curves: the 21 passages) and a two-disc volvelle indexing the 21 = C(7,2) passages, as Llull's figures index pairs |
| IV | Plate IV's 24 intervals are seeded "with the noise of real data" ([tabula_iv.py:32–38](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/04_graduum/plates/iv-native/tabula_iv.py#L32-L38)); NUMMI's pull and stoppage rates ([G:173](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/04_graduum/manuscript/reading-edition.md#L173)); a dial whose hands measure nothing ([G:131](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/04_graduum/manuscript/reading-edition.md#L131)) | Curated outage durations (CC BY 4.0) or NTSB records (§2.1) | An astrolabe plate for 43° N, whose hour lines do measure (§3.2) |
| V | The 4,096 casts and the 64 × 64 transition array are computed ([N:171–179](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/05_notoria/manuscript/reading-edition.md#L171-L179); `check_math.py`), the King Wen pairs counted ([EDITORIAL.md:15](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/05_notoria/manuscript/EDITORIAL.md#L15)) and the 256 configurations stated ([N:227](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/05_notoria/manuscript/reading-edition.md#L227)); no figure draws them | Unicode's hexagram block in King Wen order; Leibniz's 1703 binary paper (§2.4) | The transition array hatched like the recurrence loom; an arc diagram of the King Wen pairs; Shao Yong's square and circle rebuilt from binary order; geomantic and sikidy figures generated by XOR |
| Before VI | De Matribus Noctis has no plates ([build.py:7](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/00_matres/build.py#L7)): moulds pressed from worn plaques ([MAT:15](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/00_matres/manuscript/de-matribus-noctis.md#L15)), a bowl written in a spiral from the centre ([MAT:51](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/00_matres/manuscript/de-matribus-noctis.md#L51)), a cactus that blooms one night ([MAT:101](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/00_matres/manuscript/de-matribus-noctis.md#L101)) | HYG star data for the night sky (§2.5); museum images of plaques and bowls are unchecked | Spiral lettering in the Matricis hand around an empty centre; serial pressing: one figure redrawn through a shrinking, smoothing map, generation by generation |
| VI | Metz has no plate of its own ([VI §II](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/06_disputationes/manuscript/de-potestate-et-accusatione.md#L97-L117)); Wells Fargo is undrawn ([VI:253](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/06_disputationes/manuscript/de-potestate-et-accusatione.md#L253)); plates II and III are seeded beside Napier and Freeman ([VI:129](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/06_disputationes/manuscript/de-potestate-et-accusatione.md#L129), [VI:155](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/06_disputationes/manuscript/de-potestate-et-accusatione.md#L155)); the case screen is a table ([modern-cases.md:23](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/docs/research/scapegoating/modern-cases.md#L23)) | Wells Fargo's government records; witch-trial datasets; Napier's casebooks (unchecked) (§2.3) | A three-band alluvial for authority, harm and blame; an arc diagram of the Metz sequence from the book's own reconstruction |
| VII | The operations appear only as tokens; the four interventions ([VIN:37](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/07_septimus/manuscript/de-vinculis.md#L37)), the two-state device ([VIN:245–249](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/07_septimus/manuscript/de-vinculis.md#L245-L249)) and the triangle itself ([VIN:31](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/07_septimus/manuscript/de-vinculis.md#L31)) are undrawn | Public-domain Goetic circles and seals in Wellcome MS.3203; Agrippa's tables (§2.4) | A constructed circle and triangle; the Sigillum Dei construction with the Semiphoras names on its outer band |
| Tarot | Every card is a generated raster; the prompts specify dense cellular and lattice ornament ([deck.json:43](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/06_tarot/major-arcana/deck.json#L43)) | Le Breton's 1863 engravings and Mathers's 1904 seals as inputs to the image-fed cultures instead of renders (§2.4) | Data faces after Chernoff from catalogue attributes (§3.3); the [node lattice](../techniques/10-development-generators/README.md) |
| All | The books turn their questions on their own production ([Clavis](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/07_septimus/manuscript/clavis.md)) | The public Git history | **Implemented:** History Flow of the manuscripts |

## 2. Data

### 2.1 Incidents, safety reports and outages

| Source | What it gives | Terms |
| --- | --- | --- |
| [Atlassian Statuspage public API](https://bitbucket.status.atlassian.com/api) (any `…/api/v2/incidents.json`) | The 50 most recent incidents; each has `created_at`, `resolved_at`, impact and a list of updates with status (investigating, identified, monitoring, resolved, postmortem) and display time | None stated on the API page. Only 50 incidents are served, so a history must be polled and archived |
| [Google Cloud Service Health](https://status.cloud.google.com/incidents.json) | Incidents with begin, end, severity, affected products and locations, and timed updates; the [documentation](https://docs.cloud.google.com/support/docs/dashboard) says records are kept for up to five years | Feed terms unstated; the documentation page itself is CC BY 4.0 |
| [AWS Post-Event Summaries](https://aws.amazon.com/premiumsupport/technology/pes/) | Eighteen summaries, 21 April 2011 to 19 October 2025 | All rights reserved: transcribe dates and cite |
| [danluu/post-mortems](https://github.com/danluu/post-mortems) | About 240 linked postmortems in one README | **no licence** |
| [InetIntel/internet_outages](https://github.com/InetIntel/internet_outages) ("Destination Unreachable", SIGCOMM 2023) | About 1,700 curated outages with begin and end, country, network and cause | Repository has no licence; the [Zenodo snapshot](https://doi.org/10.5281/zenodo.10152271) is **open** (CC BY 4.0). Use the Zenodo files |
| [NASA ASRS database](https://asrs.arc.nasa.gov/search/database.html) | De-identified narratives with analyst coding, 1988 to now; CSV exports of up to 10,000 records; 2,321,050 reports received April 1976–December 2025 ([programme briefing](https://asrs.arc.nasa.gov/docs/ASRS_ProgramBriefing.pdf)) | No rights statement found (unchecked). ASRS says its counts cannot be used to infer the prevalence of a problem; the FAA's ASIAS says the data should not generally be used for distributions or trends |
| [NTSB aviation data](https://www-s.ntsb.gov/safety/data) (`avall.zip`, 1982 to now; `PRE1982.zip`) | Accident records since 1962 | **open**: staff-prepared content is public domain ([NTSB policies](https://www.ntsb.gov/about/Policies/Pages/Policies.aspx)); copyrighted images excepted. Full report texts 2016–2023: [Zenodo](https://doi.org/10.5281/zenodo.17096333), CC BY 4.0 |
| [CSB recommendation statistics](https://www.csb.gov/recommendations/statistics/) | 1,061 recommendations with status, including "Closed – Unacceptable Action/No Response Received" | The page invites download and manipulation; its footer reads "All Rights Reserved". Use counts with citation |

Drawing a status ladder answers what a provider published and when. It does
not recover the causal split of outage time that the combined edition removed.

### 2.2 Routing and measurement, for a network-operations hand

| Source | What it gives | Terms |
| --- | --- | --- |
| RouteViews ([doi:10.7264/1y7v-2d90](https://doi.org/10.7264/1y7v-2d90)) | BGP RIB and update archives since 1997 | No licence found; cite the DOI and acknowledge the source |
| [CAIDA AS Relationships](https://data.caida.org/datasets/as-relationships/) | Inferred provider–customer and peer links | Public AUA: copy, modify and use; cite the dataset and date range; notify CAIDA of publications |
| [RIPEstat](https://www.ripe.net/about-us/legal/ripestat-service-terms-and-conditions/) / RIS / [RIPE Atlas](https://atlas.ripe.net/docs/commercial-use) | Prefix visibility; traceroutes from probes | **restricted** for commercial use: written permission, or the default grant with the RIPE NCC logo, link and boilerplate; RIPEstat forbids repackaging or redistribution |
| [IANA IPv4 Address Space Registry](https://www.iana.org/assignments/ipv4-address-space/) | 256 /8 rows with designation, date and status | IANA's [CC0 statement](https://www.iana.org/help/licensing-terms) names protocol registries and does not mention number registries: unchecked |
| [PeeringDB](https://www.peeringdb.com/aup) | Facilities, exchanges and networks | **restricted**: no reproduction except approved operational purposes |

A Hilbert-curve map of the /8 table and an AS graph drawn with hierarchical
edge bundling (provider–customer links read as escalation, peering as lateral
passage) are the two drawings this section suggests.

### 2.3 Accusation, enforcement and courts

| Source | What it gives | Terms |
| --- | --- | --- |
| Wells Fargo: [CFPB 2016-CFPB-0015](https://www.consumerfinance.gov/policy-compliance/enforcement/actions/wells-fargo-bank-2016/); [DOJ 2020 deferred prosecution agreement](https://www.justice.gov/usao-cdca/press-release/file/1251336/dl), Statement of Facts; [OCC, 23 January 2020](https://occ.gov/news-issuances/news-releases/2020/nr-occ-2020-6.html) | Account counts and penalties; more than 23,000 employees referred and more than 5,300 terminated, 2011–2016; eight named executives | US government works are not copyrightable ([17 U.S.C. § 105](https://www.law.cornell.edu/uscode/text/17/105)); DOJ states its information is public domain unless marked. Whether the negotiated agreement counts as a government work is unchecked |
| Wells Fargo board report, 10 April 2017 ([SEC filing](https://www.sec.gov/Archives/edgar/data/0000072971/000119312517118654/d375947ddefa14a.htm)) | Terminations by year (1,327 in 2014; 960 in 2015; 483 January–May 2016) and quarterly allegation counts | A private report: use its numbers, not its charts |
| [Leeson & Russ, `trials.csv`](https://github.com/JakeRuss/witch-trials) (*Economic Journal*, 2018) | 10,940 place-year rows, 43,240 people tried, 1300–1850; Lorraine has 188 rows; Metz has nine rows from 1372–1488 and none for 1519 | **no licence** |
| [Survey of Scottish Witchcraft](https://witches.hca.ed.ac.uk/) ([DataShare, doi:10.7488/ds/100](https://datashare.ed.ac.uk/handle/10283/45)) | 3,837 accused, 1563–1736, with parish, dates and outcomes; sentence known in 305 cases | Conflicting statements (CC BY 4.0 in DataShare metadata; private study only on the [about page](https://witches.hca.ed.ac.uk/about/)): **restricted** until the director answers |
| Survey residences on [Wikidata](https://www.wikidata.org/wiki/Wikidata:Licensing) (Carroll, McAndrew and Lawson, 2019) | Geolocated residences for 3,141 accused | **open** (CC0); credit the Survey. The Wikidata property used is unchecked |
| [Witchcraft trials in the Czech lands](https://zenodo.org/records/7393339) (DISSINET, 2022) | 257 cases, 1491–1785, with residence and interrogation places as coordinates | **open** (CC BY 4.0); names included |
| Salem: [UVA documentary archive](https://salem.lib.virginia.edu/home.html); [`salem` R package](https://cran.r-project.org/web/packages/salem/refman/salem.html) | Case files, 152 accused with town and month | **non-commercial** (archive); **non-commercial** and share-alike (package, CC BY-NC-SA 4.0). The 1692 records themselves are public domain; hand-code edges from them |
| [Old Bailey Proceedings XML](https://orda.shef.ac.uk/articles/view/4775434) | 197,745 trials, 1674–1913 | Unchecked; the derived [Old Bailey Corpus](https://fedora.clarin-d.uni-saarland.de/oldbailey/license.html) is CC BY-NC-SA 4.0 |
| [Enron email corpus](https://www.cs.cmu.edu/~enron/) | About 150 mailboxes, 0.5 million messages | No terms; a privacy request; the page now records reported forged mailboxes, which a scapegoating book would have to caption |

The book's [modern-cases screen](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/docs/research/scapegoating/modern-cases.md)
already lists Wells Fargo's primary URLs. Its counts are of different things —
referrals, terminations, accounts, dollars — and a three-band drawing should
keep them on separate scales rather than one.

### 2.4 Grimoires, divination and public-domain images

| Source | What it gives | Terms |
| --- | --- | --- |
| *The Goetia*, Mathers/Crowley 1904: [Internet Archive](https://archive.org/details/ac_goetia); text, [Gutenberg #72679](https://www.gutenberg.org/ebooks/72679) (de Laurence's 1916 reprint); seals at 1200 dpi, [fromoldbooks](https://www.fromoldbooks.org/Mathers-Goetia/) | The 72 spirits; each entry states its legions; a closing list pairs each rank with a seal metal | **open** (public domain in the US); fromoldbooks asks for credit. No open table of ranks and legions exists — Peterson's edition is all rights reserved — so parse the 1904 text |
| Weyer, *Pseudomonarchia daemonum* (1577), [scan](https://archive.org/details/JohannisWieriDePraestigiisDaemonumE); Scot, *Discoverie* (1584), [Wellcome scan](https://archive.org/details/b30337367) | The book's named source catalogue and its English version | **open** (Public Domain Mark). Whether that scan contains the 1577 appendix is unchecked |
| Collin de Plancy, *Dictionnaire infernal* (1863), [full scan](https://archive.org/details/DictionnaireInfernal1863) | Le Breton's demon engravings | Public domain by date; this scan is from Gallica, whose terms charge for commercial reuse — prefer another copy for a sold edition |
| Wellcome [MS.3203](https://wellcomecollection.org/works/ec44wsyf) and [MS.110](https://wellcomecollection.org/works/p8bhyjys) | "Goetia and Theurgia Goetia" with circles and seals (221 images); an Ars notoria fragment with pen sigils (256 images) | **open** (Public Domain Mark); credit Wellcome Collection |
| British Library Sloane 3648, 3188, 1712 | Lemegeton; Dee; Ars notoria with notae | Images unavailable since the October 2023 cyberattack |
| Agrippa, *Three Books*, 1651 ([scan](https://archive.org/details/b30335231)); Trithemius, *Polygraphia*, 1518 ([scan](https://archive.org/details/b33552137)) | Planetary squares (II.22) and the tables of the 72 names (III.25); the tabula recta and Ave Maria cipher | **open** (Public Domain Mark). Agrippa says the seals are drawn from the squares and leaves the method to "the wise searcher"; the earliest source for tracing names through a square is unchecked |
| Voynich: [transliterations](https://mail.voynich.nu/roadmap.html#cop) and [images](https://collections.library.yale.edu/catalog/2002046) | IVTFF files (Landini–Zandbergen, Takahashi); Beinecke MS 408 | **open**: transliterations CC0; Yale open-access images usable for any purpose |
| Yijing | Unicode U+4DC0–U+4DFF is in King Wen order and ships with Python's `unicodedata`; Leibniz's 1703 *Explication* is in Gerhardt, vol. 7 ([scan](https://archive.org/details/leibnizensmathe12leibgoog)) | Nothing to license; the 64 × 6 line table must be written out |
| Ifá | 256 odù from eight binary marks; the order of the sixteen principal figures | A widely copied table lacks a source. Check it against Abimbola (1976) and Bascom (1969) first — the book already holds this check open ([N:229](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/05_notoria/manuscript/reading-edition.md#L229)) |

Sikidy builds its later columns by XOR, and Marcia Ascher (1997) analysed the
checks that make an array valid. That is firmer ground for a generated figure
than a claim of descent between systems.

### 2.5 Sky and scans

| Source | What it gives | Terms |
| --- | --- | --- |
| [HYG database](https://raw.githubusercontent.com/astronexus/HYG-Database/main/LICENSE) v4 | Star positions, magnitudes and names | **share-alike** (CC BY-SA 4.0) |
| Yale Bright Star Catalogue 5 ([CDS V/50](https://cdsarc.u-strasbg.fr/ftp/cati/V/50)) | 9,110 stars | No rights statement found |
| [Stellarium sky cultures](https://raw.githubusercontent.com/Stellarium/stellarium-skycultures/master/western/description.md) | Constellation lines by culture | Per culture: Western CC BY-SA; Egyptian GPL-2.0 |
| [Smithsonian Open Access](https://raw.githubusercontent.com/awslabs/open-data-registry/main/datasets/smithsonian-open-access.yaml) | 2D and 3D, the source of the Scanned Statue study | **open** (CC0); confirm each model's flag |

## 3. Techniques not in this collection

### 3.1 Implemented here

| Technique | Primary source | In this collection |
| --- | --- | --- |
| History Flow | Viégas, Wattenberg and Dave, "Studying cooperation and conflict between authors with history flow visualizations", CHI 2004 ([PDF](http://politics.media.mit.edu/papers/history_flowviegas.pdf)) | [historyflow.py](../lib/codex_palette/historyflow.py): bands from `git blame` identity instead of a sentence diff |
| Flux-adapted tubes | Tero, Kobayashi and Nakagaki, *J. Theor. Biol.* 244 (2007), [doi:10.1016/j.jtbi.2006.07.015](https://doi.org/10.1016/j.jtbi.2006.07.015); Tero et al., *Science* 327 (2010), [doi:10.1126/science.1177894](https://doi.org/10.1126/science.1177894) | [tubes.py](../lib/codex_palette/tubes.py) |
| Mathematical marbling | Lu, Jaffer, Jin, Zhao and Mao, *IEEE CG&A* 32(6) (2012), [doi:10.1109/MCG.2011.51](https://doi.org/10.1109/MCG.2011.51); [Jaffer's notes](https://people.csail.mit.edu/jaffer/Marbling/) | [marbling.py](../lib/codex_palette/marbling.py), applied to polylines |
| Guilloché | Holtzapffel, *Turning and Mechanical Manipulation*, vol. V (1884); Craig, "The Mechanical Drawing of Cycloids, the Geometric Chuck", [Bridges 2006](https://archive.bridgesmathart.org/2006/bridges2006-203.pdf) | [guilloche.py](../lib/codex_palette/guilloche.py) |

The [guide](../techniques/14-codex-palette/README.md) states each study's
mapping and limits. Two departures matter for the book. History Flow here
colours a line by the last commit to change it; that is neither first
authorship nor a share of authorship, which the Clavis declines to assign.
The tubes use Nota V's nodes and arena but a different model, so the plate is a
comparison of models, not the controls Book V still owes. The
[textile study](../techniques/12-process-art/TEXTILE.md) already adapts
conductance on its scaffold graph with a normalised rule it describes as
inspired by Tero; this study runs the 2007/2010 equations themselves (random
source–sink pairs among the food nodes, the saturating flux response) on a free
mesh. The [Americana packet](../research/occult-americana/README.md)'s Sanborn
correction slips are a paper precedent for History Flow: a sheet that carries
its own revisions.

### 3.2 Instruments and ornament

| Technique | Source and open code | Fit |
| --- | --- | --- |
| Astrolabe by stereographic projection | Morrison, *The Astrolabe* (2007); Ford, [arXiv:1202.2005](https://arxiv.org/abs/1202.2005). Code: [dcf21/astrolabe](https://github.com/dcf21/astrolabe) (GPL; its licence files disagree), [wymarc/astrolabe-generator](https://github.com/wymarc/astrolabe-generator) (GPL-3.0) | Graduum's dial. For a 90 mm Capricorn rim at 43° N: equator 59.07 mm, Cancer 38.77, zenith 25.69 from centre, horizon centre 63.35 and radius 86.62, ecliptic offset 25.61 and radius 64.39. The unequal hours are the planetary hours of the timing rites |
| Volvelles and Llull's wheels | Crupi, "Volvelles of knowledge", *JLIS.it* 10(2) (2019), [doi:10.4403/jlis.it-12534](https://doi.org/10.4403/jlis.it-12534); Bonner, *The Art and Logic of Ramon Llull* (2007). Code: [KakkoiDev/volvelle](https://github.com/KakkoiDev/volvelle) (MIT) | A working index of Book III's passages; cut lines in red |
| Celtic knotwork | Kaplan and Cohen, "Computer Generated Celtic Design", EGSR 2003, [doi:10.2312/EGWR/EGWR03/009-019](https://doi.org/10.2312/EGWR/EGWR03/009-019); Glassner, *IEEE CG&A* 1999–2000. Code: [MrBenGriffin/Knot](https://github.com/MrBenGriffin/Knot) (GPL-3.0) | De Vinculis's chain and binding |
| Islamic star patterns | Kaplan, "Islamic star patterns from polygons in contact", [GI 2005](https://cs.uwaterloo.ca/~csk/publications/Papers/kaplan_2005.pdf). Code: [pierrebai/Alhambra](https://github.com/pierrebai/Alhambra) (GPL-2.0), [tactile-js](https://github.com/isohedral/tactile-js) (BSD-3-Clause) | The Arabic astral-magic sources behind Latin seals |
| Aperiodic hat tiling | Smith, Myers, Kaplan and Goodman-Strauss, *Combinatorial Theory* 4(1) (2024), [doi:10.5070/C64163843](https://doi.org/10.5070/C64163843). Code: [isohedral/hatviz](https://github.com/isohedral/hatviz) (BSD-3-Clause) | A ground that never repeats: each copy's patch as a provenance mark |
| Wave Function Collapse | Gumin's tiled and overlapping models. Code: [mxgmn/WaveFunctionCollapse](https://github.com/mxgmn/WaveFunctionCollapse) (MIT; sample tiles excluded). Truchet tiling (Smith, *Leonardo* 20(4) (1987), [doi:10.2307/1578535](https://doi.org/10.2307/1578535)) is already the [textile grammar](../techniques/12-process-art/TEXTILE.md)'s precedent | Diapered grounds and borders constrained by edge rules |
| Moiré | Amidror, *The Theory of the Moiré Phenomenon*, vol. I, 2nd ed. (2009), [doi:10.1007/978-1-84882-181-1](https://doi.org/10.1007/978-1-84882-181-1) | A figure that appears only when a printed overlay leaf is laid on it |
| Harmonograph | Goold, Benham, Kerr and Wilberforce, *Harmonic Vibrations* (1909), [scan](https://math.ucr.edu/home/baez/harmonograph/Harmonic_Vibrations.pdf). Code: [spirograph-harmonograph](https://github.com/hermes98761234/spirograph-harmonograph) (MIT) | Intervals drawn as figures |

### 3.3 Growth, line and data drawing

| Technique | Source and open code | Fit |
| --- | --- | --- |
| Differential growth | [inconvergent/differential-line](https://github.com/inconvergent/differential-line) (MIT); Pedersen and Singh, NPAR 2006, [doi:10.1145/1124728.1124742](https://doi.org/10.1145/1124728.1124742) | A line that keeps growing inside fixed margins without crossing itself |
| Diffusion-limited aggregation | Witten and Sander, *PRL* 47 (1981), [doi:10.1103/PhysRevLett.47.1400](https://doi.org/10.1103/PhysRevLett.47.1400). Code: [fogleman/dlaf](https://github.com/fogleman/dlaf) (MIT) | Exposed tips catch every arrival and the inner fjords are never reached |
| L-systems | Prusinkiewicz and Lindenmayer, *The Algorithmic Beauty of Plants* ([PDF](https://algorithmicbotany.org/papers/abop/abop.pdf); all rights reserved: link, don't copy). Code: [nylki/lindenmayer](https://github.com/nylki/lindenmayer) (MIT) | Rewriting rules as revision |
| Substrate cracks; craquelure | Tarbell, Substrate (2003): reimplement from the rule, the original's licence is unstated; Paquette, Poulin and Drettakis, GI 2002, [doi:10.20380/GI2002.08](https://doi.org/10.20380/GI2002.08) | Aged grounds; new failures start perpendicular to old ones |
| Weighted Voronoi stippling; TSP art | Secord, NPAR 2002, [doi:10.1145/508530.508537](https://doi.org/10.1145/508530.508537); Kaplan and Bosch, Bridges 2005. Code: [StippleGen](https://github.com/evil-mad/stipplegen) (LGPL-2.1), [python-tsp](https://github.com/fillipe-gsm/python-tsp) (MIT); avoid `elkai` (non-commercial) | A figure as one unbroken pen path, an alternative to tracing a raster |
| Evenly spaced streamlines | Jobard and Lefer, *Visualization in Scientific Computing '97* ([PDF](https://cg.tuwien.ac.at/courses/Visualisierung1/2015W/exercises/Streamlines_Jobard&Lefer.pdf)). Code: [anvaka/streamlines](https://github.com/anvaka/streamlines) (MIT) | Fills whose spacing never falls below the pen width |
| SDF ray-hatching | Piter Pasma's Universal Rayhatcher (fxhash, 2023) has no open licence: write it clean-room. Open 3D line rendering: [fogleman/ln](https://github.com/fogleman/ln) (MIT) | Hatched solids without a mesh |
| Hive plots | Krzywinski, Birol, Jones and Marra, *Brief. Bioinform.* 13(5) (2012), [doi:10.1093/bib/bbr069](https://doi.org/10.1093/bib/bbr069). Code: [ericmjl/hiveplot](https://github.com/ericmjl/hiveplot) (MIT) | Book III's offices and passages |
| Hierarchical edge bundling | Holten, *IEEE TVCG* 12(5) (2006), [doi:10.1109/TVCG.2006.147](https://doi.org/10.1109/TVCG.2006.147). Code: d3-shape `curveBundle` (ISC) | Every link bent through the chain of command |
| Chernoff faces | Chernoff, *JASA* 68 (1973), 361–368. Easy to write natively | Portraits whose features are catalogue attributes |
| Arc diagrams; Sankey and alluvial | Wattenberg, InfoVis 2002, [doi:10.1109/INFVIS.2002.1173155](https://doi.org/10.1109/INFVIS.2002.1173155); Rosvall and Bergstrom, *PLoS ONE* 5 (2010), [doi:10.1371/journal.pone.0008694](https://doi.org/10.1371/journal.pone.0008694). Code: [d3-sankey](https://github.com/d3/d3-sankey) (BSD-3-Clause) | The Metz sequence; blame moving downhill |
| Historical data idioms | Nightingale's 1858 rose diagrams (public domain; transcribe the figures, as the HistData package is GPL); Du Bois's 1900 Paris plates (Library of Congress; item rights unchecked) | Correction made by diagram |

## 4. Not settled in this pass

The shared web-search allowance ran out before these were checked:

- **Napier's casebooks.** Book VI cites Carter's study of them ([VI:129](https://github.com/JosiahAlanLee/Codex-Intervallorum/blob/b789e03f30034bc8403f8a40aaf83842885aaad5/books/06_disputationes/manuscript/de-potestate-et-accusatione.md#L129)). The Cambridge Casebooks Project's data licence is the most useful unchecked lead: it could replace plate II's seeded paths with recorded consultations.
- The Burney Relief's image and 3D-scan terms, and the incantation-bowl images, for De Matribus Noctis.
- Old Bailey's own legal page; whether the IANA number registries fall under its CC0 statement; the Bright Star Catalogue's rights.
- Whether Tero et al. (2010) published the Tokyo city coordinates as data. The supplement read here holds only parameter sweeps.
- The Japanese Supreme Court decision of 8 February 2012 on courts.go.jp, and Article 13 of the Copyright Act, which excludes judgments.
- Wikimedia Commons file tags for Le Breton's engravings, and Wikisource's Goetia.
- Ayodeji Ogunnaike's publications; the exact wording of Eglash's binary claim and its critics.
