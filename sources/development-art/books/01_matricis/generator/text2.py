"""Text for Tabula XIII (Rev 5 §13, verbatim; mark names from Revision 3's sketching marks)."""
from page2 import MEAL, OCHRE, ASH, COLS, ROWS, SR, MARKS

PAL = {"red": OCHRE, "ink": MEAL}
GAR = "EB Garamond"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def boxes(meta):
    B = []

    def add(**k):
        k.setdefault("color", MEAL)
        k.setdefault("lh", round(k["size"] * 1.32))
        B.append(k)

    add(id="rh_l", x=56, y=30, w=420, size=14, font=GAR, ls=0.16, runs=[("Clavicula Matricis", "v")])
    add(id="rh_r", x=524, y=30, w=420, size=14, font=GAR, ls=0.16, align="right", color=OCHRE,
        runs=[("Tabula XIII · § 13", "v")])
    add(id="title", x=60, y=74, w=880, size=44, lh=50, font=GAR, align="center",
        runs=[("Of the Twelve Marks and the Mark", "")])
    add(id="lede", x=130, y=150, w=740, size=17, lh=23, font=GAR, align="center", color=MEAL,
        runs=[("Sketching.", "v red"), (" Any sketch made with the practice follows one rule: a sketch prompts a "
                                        "claim and never replaces one. Revision 3’s twelve sketching marks remain "
                                        "available, provided each mark’s meaning is stated every time it is used.",
                                        "i")])
    for i, (name, meaning) in enumerate(MARKS):
        cx, cy = COLS[i % 4], ROWS[i // 4]
        add(id=f"cap{i}", x=cx - 108, y=cy + SR + 13, w=216, size=14.5, lh=19, font=GAR, align="center",
            runs=[(ROMAN[i] + " · ", "v red"), (name, "v"), ("", "br"), (meaning, "i")])
        B[-1]["color"] = MEAL
    add(id="mark", x=532, y=1084, w=412, size=16.5, lh=22.5, font=GAR, para_gap=8,
        runs=[("The mark.", "v red"), (" A loose curl with no central dot, turning outward with space between "
                                       "turns, its outer end left open, and a short branch curving away into its own "
                                       "open end. It suggests returning to a question from a changed position, with "
                                       "room to diverge or stop. Rotation and proportion carry no doctrine; Le "
                                       "Guin’s Kesh suggested the orientation, and this is not a Kesh glyph.", "")])
    items = ["Keep models contestable.", "Make purposes and exclusions visible.",
             "Protect reporting and the capacity to act on it.",
             "Know who controls what fades, and who else can read the clock.",
             "Count the costs of action and of inaction.", "Keep care independent of earned worth.",
             "Let the practice itself be revised or abandoned. No one needs permission to stop using it, and no "
             "service may depend on adherence."]
    runs = [("Orientation.", "v red")]
    for it in items:
        runs += [("", "br"), ("· ", "red"), (it, "")]
    add(id="orient", x=532, y=1268, w=412, size=15, lh=19.5, font=GAR, para_gap=2.5, runs=runs)
    letters = "abcdefghijklmnopqrstuvwxyz"
    for k, ch in enumerate(letters):
        add(id=f"key{k}", x=56 + meta["cw"] * k, y=1537, w=meta["cw"], size=12.5, lh=15, font=GAR, align="center",
            color=ASH, runs=[(ch, "i")])
    add(id="foot", x=56, y=1566, w=800, size=13, lh=18, font=GAR, color=ASH,
        runs=[("Ring of the great seal, in the cipher hand: “A sketch prompts a claim and never replaces one” · "
               "“Data usefulness is not protocol efficacy.”", "i")])
    add(id="folio", x=844, y=1566, w=100, size=13, lh=18, font=GAR, align="right", color=ASH, ls=0.12,
        runs=[("xiii", "v")])
    return B
