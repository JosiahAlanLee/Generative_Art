"""Clavicula Graduum - manuscript skeleton (DRAFT). Writes book.json and reading-edition.md.
Every paragraph carries one of the five tags. Nothing here goes beyond the research brief
and the plates already made; the claims are stated so they can fail."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

KEY = {
    "E": "Empirical or textual evidence, with a source and an inspection limit.",
    "D": "Definition, conditional deduction, or worked consequence within stated assumptions.",
    "H": "Hypothesis, proposed instrument, or interpretive extension requiring tests.",
    "V": "Adopted value; no scientific derivation claimed.",
    "F": "Fiction, invented device, or an instruction belonging to the artwork.",
}

FRONT = {
    "proem": [
        "[H] This book asks whether the people permitted to act on a fault can act before its deadline, and who bears the cost when they cannot. Book III invented a building where permission rises while local competence and exposure to blame fall. This book investigates some arrangements that could produce that pattern; it does not derive a law of bureaucracy from the satire.",
        "[D] Rate means a characteristic interval of a named process; rank means an ordering of permission. This book groups processes by rate for a stated task. Stable subassemblies, symbolic constraints, ecological levels and managerial time-spans are different constructions in the sources, not interchangeable definitions of hierarchy.",
        "[D] Rank and rate need not agree. A required approval that arrives after an intervention's deadline cannot authorize that intervention in time. Whether delegation would improve the outcome depends also on competence, risk and resources. The plates draw possible mismatches; the five proposals below state how to examine them.",
        "[D] Deference to relevant expertise, shared vigilance and review have existing HRO antecedents [Q1]. DORA recommends peer review and automated checks in place of heavyweight external change approval [Q3]. These sources do not measure this book's interventions; healthcare evidence on full HRO implementation remains limited [Q2]. The proposals below inherit questions, not a demonstrated comparative advantage.",
        "[F] The book is arranged in three parts, as the Steganographia was: Of Orders, Of Passages, and Of Keys. The working plates use three carriers, described in the Clavis. Plate XII is an announced omission rather than another encrypted result. The twelve-mark hand, the square table and the office litany are instruments of the artwork. The claims do not depend on them.",
    ],
    "claims": [
        {
            "id": "D6",
            "kind": "H",
            "name": "Permission on the critical path",
            "claim": "Where intervention requires serial approvals, their waits can delay correction beyond its deadline. The organisational hypothesis is that bounded delegation can reduce that delay without increasing unacceptable harm.",
            "measure": "Record actual required approvals, parallel work, staffing, risk, resources and decision times. Compare a specified delegation with the existing route on comparable tasks; separate scheduling arithmetic from observed effects.",
            "counts_against": "Delegation gives no time benefit once other bottlenecks are included, or its added harm outweighs the gain. Merely counting ranks does not test this proposal."
        },
        {
            "id": "D7",
            "kind": "H",
            "name": "A bypass needs an effective recipient",
            "claim": "Named coverage, authority and resources may make a bypass more likely to produce timely action. This is a proposal about response arrangements, not a claim that blame exposure is necessary.",
            "measure": "Test receipt and action separately against a declared deadline. Compare arrangements while recording training, staffing and incident severity; distinguish reviewable duties from punitive incentives.",
            "counts_against": "Those arrangements add no predictive or practical value beyond ordinary staffing and workflow measures. Reliable response without punitive exposure counts against the earlier blame-necessity claim."
        },
        {
            "id": "D8",
            "kind": "H",
            "name": "What the record omits",
            "claim": "An escalation record may represent status adequately while omitting responsibility or capacities spent. Whether those consequences can be inferred from that record is a separate evidential question.",
            "measure": "Before reading a retrospective, have independent readers code contemporaneous records. Compare their supported inferences with later corroborated findings; distinguish omission, uncertainty and contradiction.",
            "counts_against": "The status record already supports the relevant consequences, readers cannot reliably identify an omission, or richer records add no useful information. No hidden second text is presumed."
        },
        {
            "id": "D9",
            "kind": "H",
            "name": "The cost of an abstraction",
            "claim": "In the hierarchical learning designs cited here, hiding some signals simplifies interfaces but may withhold feedback useful for adaptation. The tradeoff is architecture- and task-specific; it is not a law of firms.",
            "measure": "Within a specified model, compare hidden, shared and partially shared feedback at matched resources and tasks, including changes of environment. Any organisational extension requires separate evidence.",
            "counts_against": "Hiding has no stated simplification benefit, or shared feedback performs as well at the same cost. Either result limits the proposed tradeoff in that model."
        },
        {
            "id": "D10",
            "kind": "H",
            "name": "Declare the resolution",
            "claim": "A count of levels can depend on the time window and grouping rule. An audit should report how robust its boundaries are rather than decide in advance that levels are wholly invented or observer-independent.",
            "measure": "Vary the window and rule, compare independent observers, and test whether proposed boundaries predict held-out timing or coupling. Agreement under one shared rule is not an ontological test.",
            "counts_against": "Boundaries remain stable across reasonable windows and rules and predict behaviour without the added apparatus. That limits the practical value of the observer-dependence proposal."
        }
    ],
}

CH = []


def chapter(number, title, deck, fiction, caption, pages):
    CH.append({"number": number, "title": title, "deck": deck, "fiction": fiction, "caption": caption, "pages": pages})


# ---------------------------------------------------------------- Book I: Of Orders --

chapter("I", "The Nine and the Seven",
        "The word was coined for angels, and its first rule was that nothing skip a level.",
        "The choirs were counted nine and the offices seven. The clerk who drew them on one sheet found that no ring of the one fell on a ring of the other, and entered the sheet as finished.",
        "Nine rings about an empty centre, in three triads. Three lines descend from the rim and stop at every triad boundary. Seven stations, Book III's offices in order of permission with their seals, sit in the only bands the rings leave them and outside the ninth, threaded by a dotted line; their own centre is marked standing-uncertain, and a red line from the choirs' centre to it is the offset, drawn and not corrected.",
        [{"title": "A sacred order, before it was an org chart", "paragraphs": [
            "[E] Pseudo-Dionysius coined hierarchia around 500 CE for the nine orders of angels, defining it as a sacred order, knowledge and activity in which each rank receives purification, illumination and perfection from the rank directly above it and transmits to the one directly below [H1]. The Ecclesiastical Hierarchy copied the scheme onto bishops, priests and deacons; from there the word migrated to any ranked body. The texts were read in translation and secondary commentary; no Greek was inspected.",
            "[H] The adjacent relay and the qualification by a receiver's capacity suggest a comparison with constrained channels. They do not state Ashby's requisite-variety relation. The plate borrows the descending order as a fictional architecture; it does not establish that theology anticipated cybernetics.",
            "[D] The descending relay drawn on this plate contains no corrective return channel. That is a limit of this diagram, not proof that the theological tradition has no account of ascent or response. Ask separately what a returning signal would have to reach.",
            "[H] Angels, clergy, chancery and firm supply different images of ordered mediation. The juxtaposition proposes a reading, not a demonstrated chain of transmission. The planetary ordering in Trithemius [T2] does not by itself establish that the Church treated his channels as a rival administration.",
            "[F] The plate carries the sentence in the caption strip. The nine and the seven never align because they were never counting the same thing.",
        ]}])

chapter("II", "The Two Watchmakers",
        "Stable subassemblies can limit the cost of interruption.",
        "Hora built in tens and was interrupted a hundred times. Tempus built from loose parts and was interrupted as often. Hora's shop stayed open. The bird returned to the ring each time the bell rang; Tempus's never had a ring to return to.",
        "A diptych with one timeline each side and the same seven bells in red. Hora closes a ten in every interval and sends it through the one door of a walled shelf; eight survive, and the whole on his bench is eight parts of ten. Tempus's panel is loose parts and nothing else, scattered at every bell, with Repetiel at his bench. Above the seam the Returning Trace, the bird that leaves the ring and comes back. Below each bench a completion specimen in the manner of Book II.",
        [{"title": "Near-decomposability", "paragraphs": [
            "[E] Simon's parable of Hora and Tempus argues that complex systems evolve faster when they are nearly decomposable into stable subassemblies, because an interruption costs only the unfinished subassembly rather than the whole [S1]. The 1962 paper was not re-inspected in this pass; the reprint in Pattee's 1973 collection is confirmed by its contents listing.",
            "[D] Within the interrupted-assembly example, preserving completed subassemblies reduces the work lost at an interruption. That conditional result does not show that every hierarchy survives better, or that systems without such subassemblies cannot persist.",
            "[H] Stable intermediate work may help explain why some organisations retain layers. It does not explain who controls permission across those layers, or establish why a particular firm resists removing them. Those require separate evidence.",
            "[F] The bird is the Returning Trace carried over from the fourth book's first mockups. It returns to the ring because the ring is a stable subassembly: an open centre that survives the bell.",
        ]}])

chapter("III", "The Cut",
        "A durable record can constrain a faster process.",
        "The Measurer held the empty frame to the keeper's side and drew one line. Everything on the left of the line moved; everything on the right of it was written down. The keeper did not notice which side it was standing on.",
        "The Measurer of Absences, antlered, in the Keeper's own stroke vocabulary, holds an empty frame out to the seam. Left of it a current of lines runs into the frame and stops at one red line; right of it a ruled table. The figure stands on both sides; Book I's substrate mark lies under the moving side.",
        [{"title": "The epistemic cut", "paragraphs": [
            "[E] Pattee describes a control level as a set of rate-independent constraints, records and symbols, acting on rate-dependent dynamics, with the genotype as the first instance, and calls the boundary between them the epistemic cut [P1]. The 1973 collection was located by catalogue and contents; the epistemic-cut formulation was read in later secondary discussion, not in Pattee's own papers, and that limit stands until they are inspected.",
            "[H] A runbook offers an institutional comparison: a relatively durable record can constrain faster activity when people or machines follow it. Its resemblance to Pattee's symbolic constraints does not make a written instruction, a genotype and an organisation the same mechanism. The record remains a physical object with its own dynamics.",
            "[D] An instruction's effect depends on its continuing use, applicability and availability. Intervallorum asks how such dependencies are maintained. This plate adds the question of who may change an instruction while it governs another person's work.",
            "[F] The Measurer's frame is empty because the cut is drawn, not found. The figure stands on both sides of it.",
        ]}])

chapter("IV", "The Observer's Ladder",
        "Count the levels, and declare the resolution.",
        "Two surveyors measured the same slope. One drew four terraces and one drew six. The farmer asked which was the real number and was told to say what the terraces were for.",
        "Twenty-four processes, each a bar as tall as the log of its interval, one slope, drawn three times. A surveyor has cut it into four terraces in the first panel and another into six in the second, each terrace at the slowest member of its group, the count ringed as an institution. The third panel holds the slope, Severion's balance, and nothing else. The plate carries the tenth claim and does not resolve it.",
        [{"title": "Levels as a way of looking", "paragraphs": [
            "[E] Allen and Starr define levels by characteristic rate, hold that slower levels constrain faster ones, and insist that hierarchy theory is a theory of observation rather than of authority [A1]. The 1982 book was read in reviews and later summaries, not in full.",
            "[D] Any grouping by rate must specify the measured processes, interval, resolution and grouping rule. The resulting count may differ from the permission chart. Reporting both lets a reader distinguish a changed description from a changed organisation.",
            "[H] Compare observers using declared rules, then test whether their boundaries predict held-out behaviour. Agreement alone can reflect shared conventions; disagreement can reflect noisy data. Neither settles whether useful dynamical separations exist.",
            "[F] The blank column is the reserved blank of this plate. It is drawn at full size and nothing is written in it.",
        ]}])

# ---------------------------------------------------------------- Book II: Of Passages --

chapter("V", "The Dial of Seven Keepers",
        "Two scales, no alignment imposed.",
        "The Keeper wore the dial on its chest and the crescent on its head and did not confuse them. Seven hands ran at seven speeds. A thread left the dial's rim and fell to the ground, where it ended in a loop that held nothing.",
        "The Keeper of Intervals with the dial where the chest ring was. Inside, seven equal reign stations after Trithemius; outside, an open logarithmic band from three months to fifty years after Jaques, unlettered, in the order the register gives. Seven bars cross the body where the body is absent. The fourth is read against the thread by a dashed rule and does not reach it.",
        [{"title": "Two accounts of a level's interval", "paragraphs": [
            "[E] De septem secundeis (1508) assigns the government of the world to seven planetary intelligences in turn, each for 354 years and four months [T2]. Jaques's stratified systems theory places managerial strata at discontinuities in the time-span of discretion, with upper boundaries conventionally read as three months, one, two, five, ten, twenty and fifty years [J1]. The Trithemius text was read in Peterson's transcription; Jaques was read in secondary summaries, not in the primary works.",
            "[D] The two series share the number seven and nothing else that has been shown. One is a cycle of equal terms; the other is a logarithmic ladder of unequal ones. The plate places both on one dial and aligns neither to the other. The seven hands run at the Jaques spans from invented phases and measure nothing; they are there so that the dial is seen to be a clock and not a diagram.",
            "[H] Jaques supplies a contested comparison between managerial responsibility and time-span. The summaries inspected here do not establish that his strata cause delay. D6 instead asks whether actual permission dependencies create a wait that a specified delegation would avoid.",
            "[V] The recurrence of seven in this book, in the stations, the intelligences, the strata and the planetary spirits, carries no argument.",
            "[F] The bars are intervals in which the Keeper is not drawn. The thread falls past them. Count III M I Y II Y V Y X Y XX Y L Y.",
        ]}])

chapter("VI", "The Feudal Register",
        "A useful abstraction can also withhold a needed signal.",
        "Each manager was given one tile and told that the reward lay beyond it. Each learned its tile. The reward came down the landings and was caught at each. On the fourth landing a tile leaked, and that manager alone learned where the reward had been.",
        "A maze from above, with its goal cell holding the environment's reward as a red drop. Four landings descend on the right; on each a hooded manager holds up one tile, a true crop of the one maze cell it may see. The environment's thread runs to the first landing and is caught in Culpax's funnel; Redacth's veil, Velaroth's folded sheet and Viridon's pane below each hold a drop of their own, and nothing passes down. The fourth pane is cracked and the drop reaches the last tile. The Twin Register, two heads and one body around an open ring, is the two-way hiding.",
        [{"title": "Reward hiding, information hiding", "paragraphs": [
            "[E] Dayan and Hinton's feudal reinforcement learning builds a hierarchy of managers and sub-managers on two explicit principles: reward hiding, in which a sub-manager is rewarded for obeying its manager whether or not that serves the top goal, and information hiding, in which each level sees state only at its own granularity, hidden in both directions [DH1]. Vezhnevets and colleagues' 2017 FeUdal Networks softened reward hiding because pure hiding did not work well [V1]. Both papers were read in the original.",
            "[H] These learning architectures provide a comparison with Book III, not an implementation or proof of its fictional building. D9 asks what each interface hides and whether that helps or impairs a specified task. A result for a trained agent cannot establish a necessary design rule for human organisations.",
            "[H] Reward feedback and a stop-work channel both change which signals reach an actor, but they are different interventions. The plate places them beside one another; the next chapter asks about the recipient of a bypass.",
            "[F] The serpent's two heads read the same register from opposite ends and agree on nothing but the ring.",
        ]}])

chapter("VII", "The Cord Without a Mount",
        "A cord needs a mount, a receiver and a timely response.",
        "Foras held the cord. It rose past every slab and touched no office. On the roof a bracket had been fitted, and its hook held nothing, and the cord stopped short of it by the length of a hand.",
        "The building of Book III in section. Seven floors, each carrying its office's seal imported from Book III, and the black route offered: a stair from each desk to the next. In the right wall a shaft; in it one red cord from Foras's hand to a knot under an empty hook. The top floor has a chair and no desk. The ground floor has no desk: Foras is the desk. Below, three cases: mounted, received, neither.",
        [{"title": "The algedonic channel and its recipient", "paragraphs": [
            "[E] Beer's viable system model names a channel from operations directly to the policy function, bypassing coordination and control, for signals of pain or pleasure that cannot wait, and calls it algedonic [B1]. Beer insisted the five systems are not a hierarchy. Toyota's andon cord lets a line worker stop the line [T1]. Beer was read in summaries; the andon is general knowledge; neither primary source was inspected in this pass.",
            "[H] D7 asks whether the channel has an available recipient with authority and resources to respond before the relevant deadline. Reviewable duties may help sustain that response; exposure to punishment is neither a demonstrated necessity nor a sufficient condition. Timely unpunished response is evidence to retain, not an exception to explain away.",
            "[E] Labour-process accounts dispute whose stop the andon is. Parker and Slaughter describe a board on which each station shows green, yellow or red, run so that stations hover between green and yellow. A station that stays green loses resources, and a worker who pulls the cord is identified on the board and may be disciplined for not keeping up [PS1]. Slaughter reports a Mazda worker who was filmed after pulling the cord several times and, once injured, was blamed for not pulling it [SL1].",
            "[E] Adler's study of NUMMI reports, from its plant manager, about a hundred pulls a day in final assembly, many cleared before the line stopped, and about thirty minutes of stoppage a shift. It records a worker critic's complaint that pulls were being discouraged, which later interviews suggested was temporary, and grants that the system made people work harder as well as smarter [AD1].",
            "[D] A management-owned quality stop and a worker-owned stop-work power can use the same cord. They differ in who sets the line speed and staffing the cord interrupts, and in whether a pull can be counted against the one who pulls. The first is a signal to a recipient who answers for output; the second is an authority its holder cannot be penalised for using.",
            "[H] D7's question about the recipient has a second part: what a pull costs the one who pulls. A channel can have a prompt recipient and still be too costly to use. Evidence that pulls cost pullers nothing, on a line not timed or staffed to make pulling costly, would make the second part idle; Adler's NUMMI account is where to look.",
            "[H] Brooks's layered control is named in the brief as a contrasting design [BR1], but its primary paper was not inspected. It remains a source to check before using it as evidence against a general theory of escalation. This book does not claim that every hierarchy needs the cord drawn here.",
            "[F] The cord is sound. The mount was never made.",
        ]}])

chapter("VIII", "The Council of the Loudest",
        "The decision demon hears volume, not correctness.",
        "The demons shouted. The one that was right spoke at ordinary volume and was not heard. The decision demon, which had ears and no eyes, chose the loudest, as it was built to.",
        "Three tiers of Book III's handoff demons drawn as apparatus, each with its mouth and, rising from it, as many arcs as its volume. Apart, on its console, the decision apparatus: a head-box with a blank plate where the eyes would be, two ear-trumpets turned down toward the tiers, and a gauge whose needle swings to the loudest, which is Choraz. Foras, the office that knew, stands in the lowest tier at one arc, on a red ring.",
        [{"title": "Pandemonium", "paragraphs": [
            "[E] Selfridge's Pandemonium (1959) models pattern recognition as a hierarchy of demons: image demons, feature demons that shout when they see their feature, cognitive demons that shout in proportion to how many features match, and one decision demon that picks the loudest [SE1]. It is named for Milton's council. The architecture was read in secondary accounts and the 1959 symposium report, not in the paper itself.",
            "[H] In the satire, loudness has become detached from evidential reliability. That is the proposed failure, not an established defect of Selfridge's recognizer: activation strength there is intended to represent a match. An institutional comparison would need evidence that amplification changes independently of the signal's accuracy.",
            "[H] Selfridge offers a technical comparison with the demon hierarchies in the project's debts. This pass does not establish a direct influence on Minsky or the CCRU, or an omission from their citations.",
            "[F] The quiet one is marked red so the reader can find it. The decision demon cannot.",
        ]}])

# ---------------------------------------------------------------- Book III: Of Keys --

chapter("IX", "The Square Table",
        "The key returns the signs, not the room.",
        "The clerk shifted every base by three and held the tally. The letters came back. The room in which they had been written did not.",
        "A twelve-by-twelve table of base marks, each row shifted one place: Trithemius's square table in the twelve-mark hand. Seven rows are ringed in red as stations. The plate's own caption is encrypted in its margins at shift three, and the key is printed on the plate.",
        [{"title": "Trithemius, taken seriously", "paragraphs": [
            "[E] Reeds's 1998 paper reports deciphering the number tables in Book III of the Steganographia; the inspection record here is limited to its abstract and opening pages [R1]. Bibliographic descriptions of the 1518 Polygraphia identify its shifted alphabets and prayer-like encodings [R2]. No early printing or historical cipher table was inspected. This edition does not claim four centuries of uniform interpretation.",
            "[H] A spirit address that carries another text offers a model for an institutional message with consequences its copier may not understand. The analogy does not prove that every report hides a second text. D8 asks whether a particular record supports a particular inference; the artwork supplies a deliberately encoded case.",
            "[D] The square table here shifts only the base mark and holds the tally, so that all twenty-six letters survive the shift and a reader can check the operation without accepting an office. The shift is an arithmetic station, not a claim that organisations have twelve levels or seven.",
            "[F] The key returns the signs, not the room.",
        ]}])

chapter("X", "The Prayer of the Office",
        "The invocation cannot be copied without the indictment.",
        "The office was addressed in forty words, each a title. Read as a prayer, it was a prayer. Read with the table, it said what the office had actually done.",
        "Foras's portrait with six hands. Down registers A and B, a litany of Latin addresses, one word per letter, AMEN at each word boundary, encoding the office's actual-effect line from Book III: located the fault in four minutes; left it running while permission was sought. The sixth hand's request stops outside the drawn permission field.",
        [{"title": "The Ave Maria cipher, adapted", "paragraphs": [
            "[E] Trithemius's Ave Maria cipher replaces each letter with a word so that the ciphertext reads as a prayer; consecutive tables let the result run as continuous Latin [R2]. The litany used here is a new fixed-column table of twenty-six addresses, in the manner of the Ave Maria and not a reproduction of it. No historical table was copied, and no continuous prose is claimed for the Latin.",
            "[D] In this plate's defined encoding, copying the complete litany preserves the effect line, whether or not the copier decodes it. Removing or replacing carrier words can destroy it. This is a property of the constructed cipher, not proof that institutional invocations inevitably carry their own indictment.",
            "[F] The six hands hold what the office is permitted to hold. The thing the office actually did is in the margins.",
        ]}])

chapter("XI", "The Lifted Pen",
        "Only the file keeps the lifts.",
        "The plate was plotted and looked like an ornament. The same plate was plotted again from a tidied file and looked the same, and said nothing.",
        "One continuous pen path per word. The number of straight commands before each curve gives the letter; a new path gives the word boundary and requires a pen lift. The printed plate is silent. Reversing the paths reverses the sentence; simplifying the collinear runs destroys it, with nearly identical images at the proof's recorded render settings.",
        [{"title": "Decay ownership, enacted in the medium", "paragraphs": [
            "[E] The proof for this plate reversed the word paths and obtained the words in reverse order at a mean pixel difference of 0.00001 on a 0-255 scale, and collapsed the collinear runs and obtained a string of As, every count having fallen to one, at 0.002, with the printed plate unchanged to rendering precision in both cases [X1]. These are the plate's own recorded tests; they were read from the proof's validation, not re-run for this edition.",
            "[D] In this constructed carrier, path order and command counts encode a sentence that the printed appearance cannot reliably recover. Reordering or simplifying the file can change that sentence while preserving its visible shape. The example demonstrates dependence on a representation's structure; it does not establish a general law of decay ownership.",
            "[H] The carrier paths should be the contour bands of a figure rather than bare polygons. The cipher does not care what the paths depict, and the plate should.",
            "[F] The file keeps the lifts.",
        ]}])

chapter("XII", "The Withheld Key",
        "The absence is stated; no secret result is promised.",
        "The keeper labelled the empty place: key not supplied. Asked what it would open, the keeper left a second place empty.",
        "A withheld leaf stands where a key might have been. No keyed ciphertext or recoverable secret is supplied on this plate; the omission is stated as part of the artwork.",
        [{"title": "Withholding, stated", "paragraphs": [
            "[E] The source record for the historical Clavis and Book III is given with the discussion of Plate IX [R1]. This leaf adds no further historical finding.",
            "[F] Plate XII supplies no keyed ciphertext. Its announced absence is part of the artwork; this edition makes no claim that an unpublished working key exists. The reader is owed a statement of what is absent, not a promise of a later revelation.",
            "[V] Withholding is declared, never silent. That is the whole of this plate's rule.",
            "[F] The wards are blank. They are drawn, not left.",
        ]}])

BACK = {
    "applications_title": "Practical Applications",
    "applications_deck": "What to do on a Tuesday.",
    "applications": [
        "[V] These are proposed local trials, not a validated package or a requirement to adopt this book's vocabulary. Record the intended benefit, protective functions, review route and harms before changing a live process. Permission, competence and responsibility must be established separately; no general competence gradient or malicious purpose is presumed.",
        "[H] 1. Map the critical permission path. Record when a fault was diagnosable, when action became authorized and when it became feasible. Trial bounded pre-authorization where a required wait misses the task's deadline; retain competence checks, resources and safeguards against an unsafe repair.",
        "[H] 2. Exercise the stop-work route. Name its recipient, coverage, authority and response deadline, then test delivery and response separately. Review failures without assuming that punishment supplies the missing capacity.",
        "[H] 3. Separate reporting from performance penalties. Check whether a fault-count target discourages reporting or displaces incidents elsewhere. Compare reports with independent evidence of faults; a lower count alone cannot establish improvement.",
        "[H] 4. Keep evidence beside status. Carry the last observation time, its uncertainty and the basis of a summary. At review, distinguish what the record showed at the time from what became known later; record responsibility and displaced costs only where evidence supports them.",
        "[H] 5. Test the description as well as the process. Declare the time window and grouping rule behind a level count. When a runbook or dashboard guides action, identify who checks its continuing applicability and when a recheck is due; a review date is not a universal expiry date.",
        "[H] 6. Compare the local target with the wider outcome. Trial additional outcome feedback where useful, measuring its benefit and the burden or confusion it adds. Neither more visibility nor more hiding is assumed to be universally better.",
        "[V] A retrospective should examine the permissions and resources around an operator as well as the operator's action. Rank neither proves fault nor provides immunity. Follow the evidenced dependencies, including dependencies outside the organisation.",
        "[V] None of these trials requires a seal, a litany or a table. The plates are for reading; this page is for use."
    ],
    "clavis": [
        "[F] The carrier descriptions and keys belong here, in one Clavis. Plate IX uses shift three; Plate V uses shift zero. Plate X uses the office litany. Plate XI is read from path structure in the file, not from the page. Plate XII supplies no keyed ciphertext or recoverable secret.",
        "[F] The native plate designs also use a fourth carrier in marks the plate has anyway, five marks to a letter in two forms, after Bacon's biliteral and not in his table. On the figure plates the marks are the drawing's own, a ground read left to right, and the form is a dot head present or absent, so the black pass is complete and the red carries nothing. On the apparatus plates the frame is a graduated rule read clockwise from its top-left corner, and the form is the ink, black a and red b, so the black pass shows the text as gaps and the red completes the instrument. On the key plates the carrier is the lettering, in two forms of the hand, with no mark added. The table weights common letters toward the sparse form so that the carrier stays quiet; space is five a-marks and the stop five b-marks. The existing carriers preserve the earlier draft's counter-clauses. They are historical text within the artwork, not a substitute for the revised hypotheses and tests above.",
            ],
    "hands": "[V] Books I to III were written by three hands, two of them machines, and this book by two. The hands are recorded in the colophon of the binding. No reader is asked to engage with the references; the register of debts is there so that one could.",
}

REFS = [
    {"id": "H1", "citation": "Pseudo-Dionysius, The Celestial Hierarchy and The Ecclesiastical Hierarchy (c. 500 CE); Luibheid trans. (1987); Rorem, Pseudo-Dionysius: A Commentary (1993).", "url": "", "status": "Read in translation and secondary commentary; no Greek inspected.", "use": "The sacred-order vocabulary and descending relay; the plate is not a full account of the theology."},
    {"id": "S1", "citation": "Simon, H. A. (1962). The Architecture of Complexity. Proceedings of the American Philosophical Society 106(6); reprinted in Pattee (ed.), Hierarchy Theory (1973).", "url": "", "status": "Not re-inspected in this pass; reprint confirmed by the 1973 contents listing.", "use": "Near-decomposability; the Hora and Tempus parable."},
    {"id": "P1", "citation": "Pattee, H. H. (ed.) (1973). Hierarchy Theory: The Challenge of Complex Systems. Braziller. Pattee's later papers on the epistemic cut, collected in Laws, Language and Life (2012).", "url": "", "status": "1973 volume located by catalogue and contents; the epistemic cut read in secondary discussion only.", "use": "A level as rate-independent record constraining rate-dependent dynamics."},
    {"id": "A1", "citation": "Allen, T. F. H. and Starr, T. B. (1982; 2nd ed. 2017). Hierarchy: Perspectives for Ecological Complexity. University of Chicago Press.", "url": "https://nature.com/articles/304094a0.pdf", "status": "Read in the 1983 Nature review and later summaries; not in full.", "use": "Levels defined by rate; observer dependence."},
    {"id": "J1", "citation": "Jaques, E. (1976). A General Theory of Bureaucracy. Heinemann. Jaques, E. (1989; 2nd ed. 1996). Requisite Organization. Cason Hall.", "url": "https://globalro.org/node/3543", "status": "Secondary summaries only; the primary texts were not inspected. The strata boundaries used here are the conventional ones and may not match Jaques's own tables.", "use": "Strata as time-spans; used adversarially."},
    {"id": "T2", "citation": "Trithemius, J. (1508). De septem secundeis. Transcribed by J. H. Peterson, esotericarchives.com.", "url": "https://esotericarchives.com/tritheim/tritem.htm", "status": "Transcription inspected for the reign length and the seven names; no early printing inspected.", "use": "354 years and four months; seven keepers of intervals."},
    {"id": "R1", "citation": "Reeds, J. (1998). Solved: The Ciphers in Book III of Trithemius's Steganographia. Cryptologia 22(4), 291-317.", "url": "https://www.gwern.net/doc/cs/cryptography/steganography/1998-reeds.pdf", "status": "Abstract and opening pages inspected; Ernst's independent solution noted from a 1998 press account.", "use": "Book III's ciphers; the rhetorical-strategy hedge; the 1606 Clavis's omission."},
    {"id": "R2", "citation": "Trithemius, J. (1518). Polygraphiae libri sex. Oppenheim. Bibliographic descriptions: History of Information; ABAA listing; Wellcome catalogue.", "url": "https://historyofinformation.com/detail.php?id=348", "status": "Bibliographic descriptions inspected; no table page of any printing was inspected. The litany in Plate X is an adaptation, not a transcription.", "use": "Bibliographic descriptions of prayer-like encodings, shifted alphabets and red/black printing; no priority claim in this edition."},
    {"id": "DH1", "citation": "Dayan, P. and Hinton, G. E. (1993). Feudal Reinforcement Learning. NIPS 5, 271-278.", "url": "https://www.cs.toronto.edu/~hinton/absps/dh93.pdf", "status": "Primary PDF read.", "use": "Reward hiding and information hiding as stated principles."},
    {"id": "V1", "citation": "Vezhnevets, A. S. et al. (2017). FeUdal Networks for Hierarchical Reinforcement Learning. ICML.", "url": "https://arxiv.org/pdf/1703.01161", "status": "Primary PDF read selectively (section 3.2).", "use": "The softening of reward hiding; the leak."},
    {"id": "B1", "citation": "Beer, S. (1972). Brain of the Firm. Allen Lane. Beer, S. (1979). The Heart of Enterprise. Wiley.", "url": "https://thevsmtest.org/VSM-Guide", "status": "Not inspected in this pass; the algedonic channel read in a guide and an overview.", "use": "The bypass channel; the not-a-hierarchy insistence; the Cybersyn recipient problem."},
    {"id": "T1", "citation": "Toyota production system: andon and jidoka.", "url": "", "status": "General knowledge; no primary source inspected.", "use": "The stop-work cord as the mounted case, in one sense only: someone is obliged to answer it. Who owns the stop is disputed in PS1, SL1 and AD1."},
    {"id": "PS1", "citation": "Parker, M. and Slaughter, J. (1988). Choosing Sides: Unions and the Team Concept. South End Press. Excerpt: Management's 'Ideal' Concept. Against the Current 19 (March/April 1989).", "url": "https://againstthecurrent.org/atc019/managements-ideal-concept/", "status": "The 1989 excerpt read through a fetch tool; the book was not inspected.", "use": "Management by stress; the andon board run between green and yellow; pulls identified and disciplined."},
    {"id": "SL1", "citation": "Slaughter, J. (1990). Management by Stress. Multinational Monitor 11(1-2), January/February 1990.", "url": "https://www.multinationalmonitor.org/hyper/issues/1990/01/slaughter.html", "status": "Read through a fetch tool.", "use": "The Mazda worker filmed after pulling the cord and blamed for not pulling it."},
    {"id": "AD1", "citation": "Adler, P. S. (1993). The 'Learning Bureaucracy': New United Motor Manufacturing, Inc. In B. M. Staw and L. L. Cummings (eds.), Research in Organizational Behavior 15. JAI Press.", "url": "https://msbfile03.usc.edu/digitalmeasures/padler/intellcont/NUMMI%28ROB%29-1.pdf", "status": "The author's April 1992 draft (3.1) read through a fetch tool to about its page 51; the published version and the draft's evaluation section were not inspected.", "use": "Pull counts and stoppage at NUMMI; a worker critic's complaint; harder as well as smarter."},
    {"id": "BR1", "citation": "Brooks, R. A. (1986). A Robust Layered Control System for a Mobile Robot. IEEE Journal of Robotics and Automation 2(1).", "url": "", "status": "Not inspected in this pass.", "use": "The counter-model: a hierarchy without escalation."},
    {"id": "SE1", "citation": "Selfridge, O. G. (1959). Pandemonium: A Paradigm for Learning. In Mechanisation of Thought Processes, HMSO. Symposium report, Nature 183, 24 January 1959.", "url": "https://www.nature.com/articles/183225a0.pdf", "status": "Symposium report and secondary accounts inspected; the paper itself not.", "use": "The demon hierarchy; decision by volume."},
    {"id": "BA1", "citation": "Bacon, F. (1623). De dignitate et augmentis scientiarum, Book VI, ch. 1: the biliteral cipher.", "url": "", "status": "Not inspected in this pass; the scheme is general knowledge and the table used here is not Bacon's.", "use": "The two-form, five-mark carrier for the ornament bands."},
    {"id": "EL1", "citation": "Elish, M. C. (2019). Moral Crumple Zones: Cautionary Tales in Human-Robot Interaction. Engaging Science, Technology, and Society 5.", "url": "", "status": "Read in the research brief's summary; the paper was not inspected in this pass.", "use": "The keyboard is not the crumple zone."},
    {"id": "X1", "citation": "Codex Intervallorum, books/04_graduum/proofs/x-xi-v-gpt/validation.json (2026).", "url": "", "status": "The plate's own recorded counterexample tests; read, not re-run.", "use": "The reversed and simplified XI carriers."},
    {"id": "E3", "citation": "Pseudomonarchia Escalationum (2026), manuscript/catalogue.json and output/plates/office-seal-0..6.svg.", "url": "", "status": "Read and imported in full.", "use": "The seven offices, their regions, seals and actual effects; the empty seat."},
    {"id": "M1", "citation": "Clavicula Matricis, Revision 5 (2026): claims D1-D5, the ten constraints, the twelve-mark hand.", "url": "", "status": "The source of the numbering and the house rules.", "use": "D1 decay ownership; P1 boundary declared; P3 representations change what they represent."},
    {'id': 'Q1', 'citation': 'Agency for Healthcare Research and Quality. High Reliability. PSNet primer (2019), reviewed 15 September 2024.', 'url': 'https://psnet.ahrq.gov/primer/high-reliability', 'status': 'Relevant primer passages directly read on 18 October 2026. Its references identify Weick and Sutcliffe, Managing the Unexpected (2015); that book was not newly inspected.', 'use': "Deference to relevant expertise, shared concerns, cross-monitoring and resilience. An antecedent, not proof of this book's intervention."},
    {'id': 'Q2', 'citation': 'Fricke, J., Galligan, M., Douma, C., Souder, J., Hedden-Gross, A., and Mull, N. (2025). Examining the Impact of Implementing High-Reliability Organization Principles on Patient Safety Outcomes: Rapid Review. AHRQ, Making Healthcare Safer IV. doi:10.23970/AHRQEPC_MHS4HRO.', 'url': 'https://pubmed.ncbi.nlm.nih.gov/41248244/', 'status': "The authors' abstract and findings directly read in PubMed on 18 October 2026; the full report was not inspected. Its healthcare scope is retained.", 'use': 'Limited published effectiveness evidence for HRO implementation; no numerical estimate transferred to dispatch or other institutions.'},
    {'id': 'Q3', 'citation': 'DORA. Streamlining change approval. Capabilities page, updated 30 October 2025.', 'url': 'https://dora.dev/capabilities/streamlining-change-approval/', 'status': 'Primary programme page directly read on 18 October 2026. The 2019 report it summarizes was not independently read.', 'use': 'Peer review and automated checks as alternatives to heavyweight external approval. Supplies no gate-detection probability or incident-window calibration.'},
]


def build():
    book = {
        "title": "Clavicula Graduum",
        "subtitle": "A Little Key to the Steps",
        "edition": "Revised manuscript, DRAFT | premise revision, 18 October 2026",
        "author": "Josiah Alan-Lee",
        "strap": "A grimoire of orders, passages and keys: rates, permissions and their possible mismatches",
        "status": "DRAFT. The five numbered proposals are hypotheses, not established laws. Source inspection statements are inherited from the draft; this editorial pass does not claim a fresh primary-source audit. Plate captions and encoded messages may retain earlier wording; the prose here states the revised scope.",
        "parts": [{"name": "Of Orders", "chapters": ["I", "II", "III", "IV"]}, {"name": "Of Passages", "chapters": ["V", "VI", "VII", "VIII"]}, {"name": "Of Keys", "chapters": ["IX", "X", "XI", "XII"]}],
        "front": FRONT, "chapters": CH, "back": BACK, "references": REFS, "evidence_key": KEY,
        "source_commit": "cb893d600d78db14d74084f7ebacfa7d112f68a0",
    }
    json.dump(book, open(os.path.join(HERE, "book.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    md = [f"# {book['title']}", "", book["subtitle"], "", book["strap"], "", book["edition"], "", f"*{book['status']}*", ""]
    md += [f"- [{k}] {v}" for k, v in KEY.items()] + [""]
    md += ["## Proem", ""] + [p + "\n" for p in FRONT["proem"]]
    md += ["## The five claims", "", "The D-numbers are retained identifiers; [H] marks hypothesis, not deduction.", "", "| Claim | Measure | Counts against it |", "| --- | --- | --- |"]
    for c in FRONT["claims"]:
        md.append(f"| **{c['id']} [{c['kind']}] {c['name']}.** {c['claim']} | {c['measure']} | {c['counts_against']} |")
    md.append("")
    for part in book["parts"]:
        md += [f"# {part['name']}", ""]
        for ch in CH:
            if ch["number"] not in part["chapters"]:
                continue
            md += [f"## {ch['number']}. {ch['title']}", "", ch["deck"], "", f"**Reading the plate.** {ch['caption']}", "", f"> {ch['fiction']}", ""]
            for pg in ch["pages"]:
                md += [f"### {pg['title']}", ""] + [p + "\n" for p in pg["paragraphs"]]
    md += [f"# {BACK['applications_title']}", "", BACK["applications_deck"], ""] + [p + "\n" for p in BACK["applications"]]
    md += ["## Clavis", ""] + [p + "\n" for p in BACK["clavis"]] + ["## Of the hands", "", BACK["hands"], ""]
    md += ["## Register of debts", ""]
    for r in REFS:
        md.append(f"- **{r['id']}** {r['citation']} — *{r['status']}* Use: {r['use']}" + (f" [{r['url']}]({r['url']})" if r["url"] else ""))
    open(os.path.join(HERE, "reading-edition.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    n = sum(len(pg["paragraphs"]) for ch in CH for pg in ch["pages"]) + len(FRONT["proem"]) + len(BACK["clavis"]) + len(BACK["applications"]) + 1
    print("chapters", len(CH), "paragraphs", n, "references", len(REFS))


if __name__ == "__main__":
    build()

