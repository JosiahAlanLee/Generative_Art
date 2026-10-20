"""Text boxes for Tabula VIII (Rev 5 §8, verbatim)."""
from page1 import AX, INK, RED, SEPIA

PAL = {"red": RED, "ink": INK}
SC, PICA, ENG = "IM FELL English SC", "IM FELL DW Pica", "IM FELL English"


def boxes(meta):
    yN, yG, yApex, yD, yF, yGr, eh = (meta[k] for k in ("yN", "yG", "yApex", "yD", "yF", "yGr", "exec_h"))
    B = []

    def add(**k):
        k.setdefault("color", INK)
        k.setdefault("lh", round(k["size"] * 1.3))
        B.append(k)

    # furniture
    add(id="rh_l", x=56, y=28, w=420, size=13, font=SC, ls=0.22, runs=[("Clavicula Matricis", "")])
    add(id="rh_r", x=524, y=28, w=420, size=13, font=SC, ls=0.22, align="right", color=RED,
        runs=[("Tabula VIII · § 8", "")])
    add(id="title", x=60, y=70, w=880, size=42, lh=48, font=ENG, align="center",
        runs=[("Of an Outage Delayed by Authority", "")])
    add(id="lede", x=120, y=139, w=760, size=16.5, lh=23, font=PICA, align="center",
        runs=[("A hypothetical network operations incident, not an account of any employer. A fiber cut causes an "
               "outage. Repair waits because the escalation matrix routes approval through non-technical "
               "executives, two of whom are in conflict.", "i")])

    # plate labels
    add(id="l_noc", x=192, y=yN - 13, w=158, size=21, lh=26, font=SC, align="right", runs=[("NOC", "")])
    add(id="l_gate", x=120, y=yG - 23, w=232, size=15.5, lh=20, font=SC, align="right", ls=0.04,
        runs=[("Mandatory escalation", "")])
    add(id="l_gate2", x=120, y=yG + 0, w=232, size=14, lh=18, font=PICA, align="right",
        runs=[("a required gate", "i")])
    ym = yApex + eh / 2
    add(id="l_exec", x=140, y=ym - 30, w=255, size=18, lh=22, font=SC, align="right", ls=0.04,
        runs=[("Executive", "")])
    add(id="l_exec2", x=140, y=ym - 6, w=255, size=14, lh=18, font=PICA, align="right",
        runs=[("authority; no direct repair capacity", "i")])
    add(id="l_wait", x=AX + 24, y=788, w=200, size=13.5, lh=18, font=SC, ls=0.06, runs=[("Handoff waits", "")])
    add(id="l_ptr", x=118, y=784, w=190, size=14.5, lh=17, font=PICA, align="right", color=RED,
        runs=[("Reported refusal / disputed ownership", "i")])
    add(id="l_ptr2", x=118, y=820, w=190, size=12.5, lh=15, font=PICA, align="right",
        runs=[("a hypothesis about this handoff; verify in records", "i")])
    add(id="l_disp", x=196, y=yD - 12, w=212, size=16.5, lh=22, font=SC, align="right", ls=0.04,
        runs=[("Technical dispatch", "")])
    add(id="l_crew", x=196, y=yF - 12, w=212, size=16.5, lh=22, font=SC, align="right", ls=0.04,
        runs=[("Field crew", "")])
    add(id="l_break", x=AX + 38, y=yGr - 30, w=340, size=14.5, lh=18, font=PICA, sc_font=SC,
        runs=[("Fiber break", "sc"), (" · the physical cause of the outage", "i")])
    add(id="l_r1", x=76 - 230, y=(yN + yD) / 2 - 9, w=460, h=18, size=12.5, lh=18, font=SC, ls=0.14,
        align="center", rot=-90, runs=[("diagnosis-to-dispatch · organizational delay", "")])
    add(id="l_r2", x=630, y=(yD + yGr) / 2 - 22, w=258, size=13.5, lh=18, font=PICA, sc_font=SC, align="right",
        runs=[("Dispatch-to-restoration", "sc"), ("", "br"), ("mostly physical repair", "i")])
    add(id="l_route", x=618, y=256, w=300, size=15, lh=19, font=SC, ls=0.04, color=RED,
        runs=[("Added, pre-authorized technical route", "")])
    add(id="l_route2", x=618, y=296, w=300, size=13.5, lh=17, font=PICA,
        runs=[("add before you remove: the old route is kept", "i")])
    for i, (p, txt) in enumerate(zip(meta["marks"], ("named owner", "alternate on-call", "timed fallback"))):
        add(id=f"l_m{i}", x=p[0] - 214, y=p[1] - 10, w=196, size=14.5, lh=19, font=PICA, align="right",
            color=RED, runs=[(txt, "i")])

    keys = ["standing: an actor with interests", "a required gate", "a centre of decision, contestable",
            "an added route; the old one kept", "unverified attribution", "conditions beneath", "the break",
            "a handoff, waiting"]
    for i, t in enumerate(keys):
        add(id=f"k{i}", x=meta["key_x"][i] + 22, y=meta["key_y"][i] - 10, w=190, size=13.5, lh=18, font=PICA,
            runs=[(t, "i")])

    # body: §8 verbatim
    body = dict(size=17, lh=23.5, font=PICA, sc_font="IM FELL DW Pica SC", para_gap=7, hyph=True)
    add(id="body", x=56, y=1168, w=888, cols=2, gap=40, **body, runs=[
        ("Inference:", "sc red"), (" locate the break, verify alarms, arrange access, estimate repair time.", ""),
        ("", "br"),
        ("Criticism:", "sc red"), (" rebuild the timeline. When was the diagnosis available, which authorization "
                                    "was missing, and what evidence supports the claim of obstruction?", ""),
        ("", "br"),
        ("Constitution:", "sc red"), (" why does rank rather than technical competence control dispatch, and who "
                                       "can change that rule?", ""),
        ("", "br"),
        ("Audits.", "sc red"), (" Map customers, field crews, carrier partners, technicians and executives, "
                                 "keeping responsibility, expertise and control separate. A technician who cannot "
                                 "safely challenge a manager is part of the model, not a personality defect. "
                                 "“Fast escalation” as a measure can reward notifying executives while repairs "
                                 "wait.", ""),
        ("", "br"),
        ("Measure.", "sc red"), (" Split diagnosis-to-dispatch from dispatch-to-restoration. The first is "
                                  "organizational delay; the second is mostly physical repair. This split is the "
                                  "most directly testable idea in the practice, and regulator investigations of "
                                  "outages often carry timelines detailed enough to apply it.", ""),
        ("", "br"),
        ("Proposal.", "sc red"), (" Trial standing technical dispatch authority under specified conditions, keeping "
                                   "executive notification, a shared record and independent review. Compare "
                                   "restoration delays and mistaken dispatches by severity. Name who must act on a "
                                   "substantiated obstruction, and with what appeal; popularity, shame and bonuses "
                                   "do not substitute for authority over people and resources.", "")])

    # footer: the wards in plain text
    add(id="f_l", x=56, y=1550, w=380, size=13, lh=18, font=PICA, color=SEPIA,
        runs=[("left margin: “A sketch prompts a claim and never replaces one.”", "i")])
    add(id="f_r", x=564, y=1550, w=380, size=13, lh=18, font=PICA, color=SEPIA, align="right",
        runs=[("right margin: “Data usefulness is not protocol efficacy.”", "i")])
    add(id="folio", x=440, y=1572, w=120, size=12, lh=16, font=SC, ls=0.2, align="center", color=SEPIA,
        runs=[("viii", "")])
    return B
