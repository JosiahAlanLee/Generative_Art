# Generative art and the pen plotter

A short history and a note for anyone who found this repository and is thinking
about buying a plotter. Research date: 22 October 2026. Sources are listed at
the end; dates are taken from them, and where the sources disagree the
disagreement is noted rather than resolved.

## What the words mean

"Generative art" has a standard working definition from Philip Galanter's 2003
paper: any art practice where the artist uses a system, "such as a set of
natural language rules, a computer program, a machine, or other procedural
invention, which is set into motion with some degree of autonomy," and that
system contributes to or produces the finished work. [1] Nothing in that
definition requires a computer, and nothing requires a plotter. The plotter is
only the hand at the end of the process: a machine that holds a pen and moves
it along paths it has been given. Everything interesting happens before the
pen touches the paper, in the rules that decided where the paths go.

The word itself comes from Stuttgart. Georg Nees titled his 1969 doctoral
thesis, supervised by the philosopher Max Bense, *Generative Computergraphik*. [2]

## Drawing machines before computers

The pantograph, described by Christoph Scheiner in 1608, is the plotter's
mechanical ancestor: a linkage that copies a drawing at another scale. [3]
The nineteenth century produced the harmonograph, a pair of swinging pendulums
that move a pen and a drawing board against each other; as the pendulums lose
energy the curve tightens, and the result is a Lissajous figure drawn in ink.
It is usually credited to the Glasgow mathematician Hugh Blackburn, though the
attribution is not secure, and it was at its most popular in the 1890s. [4]
A harmonograph is a generative system in Galanter's sense, built from wood,
weights and gravity.

Three things happened in the 1950s that still shape the field. In 1950 Ben
Laposky, a draughtsman in Cherokee, Iowa, began photographing waveforms on a
cathode-ray oscilloscope; he showed fifty of these "Oscillons" as *Electronic
Abstractions* at the Sanford Museum in 1952 or 1953 (the sources differ), and
he is often credited with the first electronic images made as art, though an
oscilloscope is not a computer. [5] In 1959 Jean Tinguely exhibited his
Métamatics at Galerie Iris Clert in Paris: motorised arms that pressed
visitor-chosen drawing implements against paper; four thousand drawings came
out of that one show, and they looked a good deal like the gestural abstraction
then hanging in the serious galleries. [6] And in 1961 Desmond Paul Henry, a
philosophy lecturer in Manchester, rebuilt a surplus Sperry bombsight computer
into a drawing machine. His machines could not be programmed and had no memory;
their output depended on chance arrangements of their mechanical parts and could
not be repeated. A one-man show, *Ideographs*, opened at the Reid Gallery in
London on 30 August 1962, arranged in part by L. S. Lowry. [7]

The other precondition was conceptual. In Artforum (summer 1967) Sol LeWitt
wrote that in conceptual art "the idea becomes a machine that makes the art"
and that execution is "a perfunctory affair." [8] His wall drawings, executed
from written instructions by other people, are generative art with no
electricity in it at all. If you want to understand what a plotter is for,
LeWitt is a better starting point than any piece of hardware.

## 1959–1965: the digital plotter and the first exhibitions

The digital plotter was an engineering instrument first. CalComp's 565, sold
from 1959, rotated an 11-inch drum in 0.01-inch steps while a pen carriage
moved across it; a solenoid lifted the pen. IBM resold it as the IBM 1627, and
a CalComp plotter attached to an IBM 1401 was the device for which Jack
Bresenham worked out his line algorithm in 1962. [9] In Germany, Konrad Zuse's
last design was the Graphomat Z64, a flatbed drawing machine. Georg Nees helped
buy one in 1963 for the Siemens computing centre in Erlangen. [2] Frieder Nake
has described how the Stuttgart computing centre bought theirs with no
software, so he wrote the control program "blindly on punched tape" without a
machine to test it, took the tape to Zuse's works in Bad Hersfeld, and when
the first run stopped after five minutes he repaired the program by gluing
paper scraps from the floor into selected holes. [10]

The first three exhibitions of computer-drawn pictures all happened in 1965.
Nees showed Graphomat drawings at the Technische Hochschule Stuttgart in
February. [2][10] In New York, A. Michael Noll and Béla Julesz of Bell Labs
showed *Computer-Generated Pictures* at the Howard Wise Gallery in April:
pictures computed on an IBM 7094 and written to film on a General Dynamics
SC-4020 microfilm plotter. The *New York Times* reviewer wrote that "the wave
of the future crashes significantly at the Howard Wise Gallery"; another
reviewer compared the pictures to cut-up punched cards. AT&T, worried that
regulators would see art as a waste of telephone charges, made the two sign
each work with a copyright notice in their own names. [11] In November, Nake
and Nees showed together at Galerie Wendelin Niedlich in Stuttgart. Nake
recalls that Bense did not come. [10]

Nake's *Hommage à Paul Klee, 13/9/65 Nr.2*, drawn by the Graphomat from a
program on an SEL ER56, set up a horizontal and vertical framework derived
from Klee's *High Roads and Byroads* and then let random variables choose
among a fixed set of options inside it. [12] That division of labour, a
structure the artist writes and chances the program takes within it, is still
how most generative drawings are made. Nees's *Schotter* (1968), a grid of
squares that progressively loses its order from top to bottom, is the same
idea reduced to one parameter. [2]

## 1968–1990: artists, the turtle, and the office plotter

*Cybernetic Serendipity*, curated by Jasia Reichardt at the ICA in London from
2 August to 20 October 1968 at Bense's suggestion, drew somewhere between
45,000 and 60,000 visitors and then toured to the Corcoran in Washington and
the Exploratorium in San Francisco. It mixed plotter graphics, computer music
and poetry, painting machines and robots; Henry's Drawing Machine 2 ran in the
gallery. [13][7] It was the moment the subject reached a public.

Three artists who began then defined the next decades. Vera Molnár had been
making combinatorial series by hand since 1959, following rules she called her
*machine imaginaire*; from 1968 she had access to a mainframe, learned Fortran
and BASIC, and made plotter drawings such as *Interruptions* (1969) and
*(Des)Ordres* (1974). Recognition came very late: she was included in the 2022
Venice Biennale at 98 and died in Paris on 7 December 2023, aged 99. [14][15]
Manfred Mohr programmed his first drawings in 1969 at Vincennes with no plotter
at all, plotting printed x–y coordinates by hand; in 1970 the Paris Institute of
Meteorology gave him a CDC 6400 and a Benson 1284 flatbed plotter, and his
1971 show *Une esthétique programmée* at the Musée d'Art Moderne de la Ville
de Paris, where he ran the plotter in public, is described by his gallery as
the first solo museum show of works entirely calculated and drawn by a digital
computer. Since 1973 his work has been built on the cube and the hypercube.
[16] Harold Cohen's AARON, which he worked on from 1973 until his death in
2016, put its drawings on paper through a "turtle," a small robot holding a
marker; at the San Francisco Museum of Modern Art in 1979 it drew on the
gallery floor, and a string of museum shows followed, including the Tate in
1983. Cohen coloured the drawings by hand until 1995. [17]

Meanwhile the plotter became office equipment. Hewlett-Packard introduced
HP-GL in 1977 with the 9872 plotter: an ASCII language of two-letter commands
(PU for pen up, PD for pen down, SP to select a pen) with coordinates in
25-micrometre units. [18] The 7470A of 1982 was cheap enough for a personal
computer because it moved the paper on a grit wheel instead of moving a
flatbed carriage; the 7475A added a six-pen carousel. [19] Drafting offices
and engineering firms bought these machines in large numbers, and when inkjet
printers replaced pen plotters in the 1990s the machines went to surplus
dealers and attics. That is where the hobby found them.

## 2001–2016: software and the revival

Processing came out of John Maeda's Aesthetics and Computation Group at the
MIT Media Lab (founded 1996) and his *Design By Numbers* (1999). Casey Reas and
Ben Fry started it in 2001; the first website went up on 20 October 2001 and
the alpha release followed on 2 February 2004. Its central idea was the
"sketch": write a short program, look, change it, look again. The Processing
Foundation was founded in 2012, and Lauren McCarthy's p5.js later carried the
same model to the browser. [20] Most generative art of the last twenty years
was made this way, and it is a sensible way to start.

The machines came back from two directions. One was the secondhand HP plotter
driven over a serial cable with HP-GL. The other was the maker movement.
Evil Mad Scientist Laboratories, run by Lenore Edman and Windell Oskay since
2007, made the EggBot and the WaterColorBot before the AxiDraw, which launched
in March 2016: a pen carriage on an XY stage with a servo for the pen lift, a
300 × 218 mm drawing area, and Inkscape extensions to drive it. [21][22]
Hanging "polar" plotters, a pen gondola suspended on two cords from two
motors, are the cheap scalable alternative; Jürg Lehni's *Hektor*, which
held a spray can, and Sandy Noble's Polargraph are the designs most of the
others descend from. [23] Edman's own account of
the trade-off is fair: the AxiDraw built "communities of plotter artists,"
while vintage plotters suit people "with a lower budget and more time on
their hands," at the cost of a lot of work on connectivity and software, and
"there's no tech support." [22]

In January 2024 Bantam Tools, Bre Pettis's company, acquired Evil Mad
Scientist. The AxiDraw line is ending, spare parts continue, and its successor
is sold as the Bantam Tools NextDraw. [24] Around the machines grew a software
layer that matters more than any one of them. Antoine Beyeler's *vpype*
(MIT-licensed; 1.15.0 released August 2025) is the standard command-line tool
for preparing plots: `linemerge` joins paths whose ends nearly meet,
`linesort` reorders them to cut pen-up travel, `linesimplify` and `reloop`
clean the geometry, and `write` emits SVG or HP-GL for a vintage machine. [25]

## 2020–2026: the money, and the closures

The last six years need to be told plainly, because a beginner will meet the
wreckage before they meet the history. Art Blocks launched on 27 November
2020 with Erick Calderon's *Chromie Squiggle*: the artist's script is frozen
on the Ethereum chain, and the buyer's minting transaction supplies the hash
that seeds their copy, so the collector, not the artist, determines which
output they get. [26] Hic et Nunc launched on Tezos in March 2021, passed
OpenSea in daily users by May, held more than half a million NFTs, and
disappeared when its founder, Rafael Lima, took the site down in the second
week of November 2021; the tokens survived on the chain and were browsable on
other front ends within minutes. [27] Tyler Hobbs's *Fidenza*, 999 outputs
minted on Art Blocks in June 2021 at 0.17 ETH (about $400) each, sold out in
25 minutes; one output later resold for 1,000 ETH, about $3.3 million at the
time. [28] fxhash, Baptiste Crespy's open generative platform on Tezos, opened
late in 2021; its team was let go in February 2026 and by August 2026 the
website was offline. Its own farewell said that the artwork "lives on," which
is true in the narrow sense that the tokens and the stored code still exist.
[29][30]

Two lessons from that period hold whatever happens to the markets. First, the
institutions arrived in the same window: Molnár at Venice in 2022, Pompidou in
2024, and sixty-year-old plotter drawings entering museum collections. [14]
Second, a platform is not an archive. The platforms that closed did not
destroy the work, but they destroyed the place where it could be seen, run and
found, and anything that lived only in their front ends is gone. This
repository exists partly for that reason: the generators here are kept
runnable from source, with their inputs, seeds and checks, rather than from a
website.

## If you buy a plotter

A plotter is an XY stage with a pen lift. The AxiDraw and NextDraw move the
pen over a fixed sheet; the old HP machines move the sheet under a pen that
only travels on one axis; a polar plotter hangs the pen from two cords and can
be as large as the wall it is on. All of them do one thing: put the pen down,
follow a path, lift the pen. There are no fills, no tone, no colour except by
changing the pen. Everything you want on the page has to be a line, and every
grey has to be hatching. That constraint is the medium. The hatching in this
collection's plates is allocated against a coverage budget, so much ink per
area at a declared pen width, for exactly that reason (see
[RENDERING-NOTES](../studies/infernal-landscape/RENDERING-NOTES.md)).

The file you will send is an SVG, or HP-GL if the machine is old. Keep it
honest: real units (millimetres), stroke-only paths with no fills, no raster
images, no clipping masks, one layer per pen. Merge the paths that share
endpoints and sort them, because pen-up travel is wasted time and a source of
wobble; vpype does both, and the difference is large. The six Driftless
preview plates in this repository fell from 664 metres of pen-up travel in
drawing order to 111 metres after sorting ([VALIDATION](VALIDATION.md)). A
plot of any density takes hours, and the length of pen-down line is the
number to watch before you start.

Pens and paper are an experiment you repeat for every combination. Pigment
fineliners (0.1–0.5 mm) are the default; gel pens are brighter and skip;
fountain and brush pens need slower speeds and smooth, heavy paper. Set the
pen height so the tip just touches, plot a square and measure it, then plot a
strip of hatching at increasing densities and look at where the lines close
up into black. That strip is your tone scale, and it changes with every pen.
Then plot something small before you plot something large.

Two things the hardware will not do. It will not make a dull drawing
interesting; the machine is only as good as the rules it is given, and the
rules are the work, as LeWitt said in 1967. And it will not archive anything.
Keep the program, the seed and the exact SVG for every plot you keep, and keep
them somewhere that is not a platform. The plates in this collection are
written as plot masters, with declared line widths and ink layers; none of
them has yet been physically plotted, and the notes say so. If you do plot
one, that is useful information this repository does not have.

## Where to start here

[Plotter and SVG](../techniques/06-plotter-export/README.md) covers the
two-layer, two-ink stroke export and single-stroke lettering; the
[Driftless Plates](../studies/driftless-plates/README.md) are the batch
landscape generator with pen-travel ordering; the [Infernal Engine](../studies/infernal-landscape/README.md)
plates show a whole pipeline from a 3D model to a 156 mm stroke-only SVG with
measured tone; the [process-art generators](../techniques/12-process-art/README.md)
export editable strokes from erosion, chemistry and growth models.
[Getting started](GETTING_STARTED.md) has the first runnable command.

## Sources

1. [Philip Galanter, "What is Generative Art? Complexity Theory as a Context for Art Theory" (Generative Art conference, 2003), PDF hosted at UC Santa Barbara](https://www.mat.ucsb.edu/~g.legrady/academic/courses/22f255/lect/gen_art.pdf). The definition quoted above.
2. [Georg Nees, Wikipedia](https://en.wikipedia.org/wiki/Georg_Nees). February 1965 exhibition, Graphomat purchase (1963), *Schotter* (1968), *Generative Computergraphik* (1969).
3. [Pablo Garcia, "A brief history of drawing machines"](https://www.pablogarcia.org/a-brief-history-of-drawing-machines). Pantograph (Scheiner, 1608) and other pre-computer devices; CalComp's 1969 "teach your computer to draw" campaign.
4. [Harmonograph, Wikipedia](https://en.wikipedia.org/wiki/Harmonograph). Mechanism, the uncertain Blackburn attribution, 1890s popularity, Lissajous figures.
5. [Ben F. Laposky, Wikipedia](https://en.wikipedia.org/wiki/Ben_F._Laposky). Oscillons from 1950; the Sanford Museum show dated 1952 and 1953 in different passages.
6. [Métamatic, Wikipedia](https://en.wikipedia.org/wiki/M%C3%A9tamatic). Tinguely's drawing machines, the 1959 Iris Clert show and its four thousand drawings.
7. [Desmond Paul Henry, Wikipedia](https://en.wikipedia.org/wiki/Desmond_Paul_Henry). The 1961 bombsight machine, the 30 August 1962 Reid Gallery show, unrepeatable output, *Cybernetic Serendipity*.
8. [Sol LeWitt, "Paragraphs on Conceptual Art", Artforum vol. 5 no. 10, Summer 1967 (PDF)](https://mehtaspring22.commons.gc.cuny.edu/files/2021/06/LeWitt_Paragraphs-on-Conceptual-Art.pdf). The sentences quoted.
9. [Calcomp plotter, Wikipedia](https://en.wikipedia.org/wiki/Calcomp_plotter). The 565 (1959), its 0.01-inch drum steps, the IBM 1627, Bresenham's 1962 algorithm.
10. [Frieder Nake with Wolf Lieser, "Think the Image, Don't Make It!" (DAM, 2025)](https://dam.org/museum/essays_ui/essays/frieder-nake-wolf-lieser-60-years-of-algorithmic-art/). The Graphomat software story, the three 1965 exhibitions, Bense's absence.
11. [A. Michael Noll, "Howard Wise Gallery Show of Digital Art and Patterns (1965): A 50th Anniversary Memoir" (ETHW)](https://ethw.org/First-Hand:Howard_Wise_Gallery_Show_of_Digital_Art_and_Patterns_(1965):_A_50th_Anniversary_Memoir). Dates (the press release and the memoir differ by two days), equipment, reviews, the AT&T copyright instruction.
12. [V&A, *Hommage à Paul Klee, 13/9/65 Nr.2*, Frieder Nake](https://collections.vam.ac.uk/item/O211685/hommage-%C3%A0-paul-klee-13965-print-nake-frieder). SEL ER56, Graphomat Z64, the Klee framework and the random choices within it.
13. [History of Information, "Cybernetic Serendipity"](https://www.historyofinformation.com/detail.php?id=863). Dates, attendance (accounts differ), Bense's suggestion, the tour.
14. [Vera Molnár, Wikipedia](https://en.wikipedia.org/wiki/Vera_Moln%C3%A1r). Combinatorial series from 1959, computers from 1968 (Fortran, BASIC), Venice 2022, Pompidou 2024, death on 7 December 2023.
15. [V&A, "Vera Molnár: Machine Imaginaire"](https://www.vam.ac.uk/blog/museum-life/vera-molnar-machine-imaginaire-the-dance-of-hands-and-machine-thinking). The *machine imaginaire* and the dated plotter drawings in the V&A collection.
16. [Manfred Mohr, biography (bitforms gallery, PDF)](https://bitforms.art/wp-content/uploads/2024/07/mm_bio.pdf). 1969 hand-plotted coordinates, the 1970 Benson 1284 and CDC 6400, the 1971 ARC show, cubes since 1973. The "first solo museum show" claim is the gallery's characterisation.
17. [Computer History Museum, "Harold Cohen and AARON—A 40-Year Collaboration"](https://computerhistory.org/blog/harold-cohen-and-aaron-a-40-year-collaboration/). AARON from 1973, the turtle at SFMOMA (1979), the Tate (1983), colour in 1995, Cohen's death on 27 April 2016.
18. [HP-GL, Wikipedia](https://en.wikipedia.org/wiki/HP-GL). Introduced 1977 with the HP 9872; two-letter commands; 25 µm units.
19. [HP 7470, Wikipedia](https://en.wikipedia.org/wiki/HP_7470). 1982, the grit-wheel mechanism, interfaces; the 7475's six-pen carousel.
20. [Casey Reas and Ben Fry, "A Modern Prometheus" (Processing Foundation)](https://processingfoundation.org/blog/a-modern-prometheus/). ACG (1996), *Design By Numbers* (1999), the 2001 start, the 20 October 2001 site, the 2 February 2004 alpha, the Foundation (2012), p5.js.
21. [Make:, "Create High-Quality Art with This New, Hackable Draw Bot" (11 March 2016)](https://makezine.com/article/digital-fabrication/machining/evil-mad-scientist-launches-axidraw/). The AxiDraw launch, drawing area, Inkscape control, the EggBot and WaterColorBot line.
22. [Raspberry Pi / HackSpace magazine, "Meet the maker: Evil Mad Scientist"](https://magazine.raspberrypi.com/articles/meet-the-maker-evil-mad-scientist). Lenore Edman on the company since 2007 and on vintage plotters versus the AxiDraw.
23. [Polar plotter, Wikipedia](https://en.wikipedia.org/wiki/Polar_plotter). The two-cord mechanism; Lehni's *Hektor*, Noble's Polargraph and other designs.
24. [Bantam Tools, "Bantam Tools Acquires Evil Mad Scientist" (16 January 2024)](https://bantamtools.com/blogs/blog/bantam-tools-acquires-evil-mad-scientist-to-accelerate-development-of-next-generation-art-and-handwriting-machines) and [Hackster.io's report](https://www.hackster.io/news/bantam-tools-acquires-evil-mad-scientist-brings-its-co-founders-in-house-for-new-art-machines-726caf962862). The acquisition, the end of the AxiDraw line with continued spare parts, the NextDraw.
25. [vpype on PyPI](https://pypi.org/project/vpype/). Author, licence, release 1.15.0 (4 August 2025), the commands named above.
26. [Art Blocks, "Chromie Squiggle algorithm guide"](https://www.artblocks.io/articles/chromie-squiggle-algorithm-guide). Launch day 27 November 2020, the mint-hash seeding, 10,000 Squiggles.
27. [The Art Newspaper, "Founder of Hic et Nunc pulls the plug…" (16 November 2021)](https://theartnewspaper.com/2021/11/16/founder-of-hic-et-nunc-pulls-the-plug-on-the-leading-digital-art-marketplacebut-its-half-a-million-nfts-live-on). March 2021 launch, the May 2021 user figures, the shutdown, the tokens' survival on other front ends.
28. [Cointelegraph Magazine, "Fidenza: Tyler Hobbs wrote software that generates art worth millions" (13 September 2021)](https://cointelegraph.com/magazine/fidenza-tyler-hobbs-wrote-a-program-to-make-art-that-is-now-worth-millions/). 999 outputs at 0.17 ETH, the 25-minute sellout, the 1,000 ETH resale.
29. [fxhash on X, closing statement (2026)](https://x.com/fx_hash_/status/2089351038390124661). "The artwork, however, lives on"; the team let go in February.
30. [Right Click Save, "On fxhash and the End of Radical Inclusivity" (24 August 2026)](https://www.rightclicksave.com/article/farewell-to-fxhash-a-heartbreaking-moment-in-the-history-of-digital-art). The platform's launch (dated December 2021 there), its founder, and its closure in the context of Hic et Nunc.
