"""Apply the verdict rule to results.csv and write REPORT.md and region.svg.

    python books/01_matricis_intervallorum/models/gate_window/report.py [--dir DIR]

The report is derived entirely from results.csv and verdict.json; running it again
on the same files produces the same text. The figure is a native SVG in the series'
two inks: winners are told apart by hatch direction, not by colour alone.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verdict  # noqa: E402
from verdict import GRID, c_beats_a, in_anchored, in_gate_home  # noqa: E402

INK = "#161918"
RED = "#a32b24"


def fmt(x: float) -> str:
    return f"{x:.3f}"


def lookup(rows: list[dict]) -> dict[tuple, dict]:
    return {tuple(r[k] for k in verdict.GRID_KEYS): r for r in rows}


def key(**kw) -> tuple:
    return tuple(kw[k] for k in verdict.GRID_KEYS)


def frac(rows: list[dict], pred) -> float:
    return sum(1 for r in rows if pred(r)) / len(rows) if rows else float("nan")


def region_svg(rows: list[dict], rule: dict, path: Path) -> None:
    """Small multiples: rows h_wrong in (0.5, 3.0), columns eps in (0.05, 0.3, 0.6).
    Each panel: lam across, delta up. Hatch 45° in ink where C beats A, hatch 135° in
    red where A beats C, blank where the margin leaves it tied. Dashed red: the anchored
    region. Dashed ink: the gate's home."""
    m = rule["margin"]
    L = lookup(rows)
    phi, sigma, d, h_window = 0.0, GRID["sigma"][0], GRID["d"][0], 3.0
    lams, deltas = GRID["lam"], GRID["delta"]
    eps_cols = [0.05, 0.30, 0.60]
    hw_rows = [0.5, 3.0]
    cw, ch = 26, 22                      # cell size
    pw, ph = cw * len(lams), ch * len(deltas)
    gx, gy = 70, 66                      # panel gaps
    x0, y0 = 70, 92
    W = x0 + len(eps_cols) * (pw + gx) + 10
    H = y0 + len(hw_rows) * (ph + gy) + 4
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="serif">')
    o.append('<defs>'
             f'<pattern id="c" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="{INK}" stroke-width="1.2"/></pattern>'
             f'<pattern id="a" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(135)"><line x1="0" y1="0" x2="0" y2="6" stroke="{RED}" stroke-width="1.2"/></pattern>'
             '</defs>')
    o.append(f'<rect width="{W}" height="{H}" fill="#fcfcfb"/>')
    o.append(f'<text x="{x0}" y="26" font-size="14" fill="{INK}">Estimated A-versus-C categories under assumed parameters</text>')
    o.append(f'<text x="{x0}" y="44" font-size="11" fill="{INK}">phi={phi}, sigma={sigma}, d={d}, h_window={h_window}; margin {m}. '
             'Hatch up-right in ink: C beats A. Hatch up-left in red: A beats C.</text>')
    o.append(f'<text x="{x0}" y="60" font-size="11" fill="{INK}">Blank: tied within the margin. '
             'Dashed red: the assumed scenario region. Dashed ink: the gate\'s home.</text>')
    for ri, hw in enumerate(hw_rows):
        for ci, eps in enumerate(eps_cols):
            px = x0 + ci * (pw + gx)
            py = y0 + ri * (ph + gy)
            o.append(f'<text x="{px}" y="{py - 6}" font-size="11" fill="{INK}">eps={eps}, h_wrong={hw}</text>')
            for li, lam in enumerate(lams):
                for di, delta in enumerate(deltas):
                    r = L[key(eps=eps, delta=delta, phi=phi, lam=lam, sigma=sigma, d=d, h_wrong=hw, h_window=h_window)]
                    cx = px + li * cw
                    cy = py + (len(deltas) - 1 - di) * ch
                    if c_beats_a(r, m):
                        fill = "url(#c)"
                    elif r["harm_A"] <= (1.0 - m) * r["harm_C"]:
                        fill = "url(#a)"
                    else:
                        fill = "none"
                    o.append(f'<rect x="{cx + 1}" y="{cy + 1}" width="{cw - 2}" height="{ch - 2}" fill="{fill}" stroke="{INK}" stroke-width="0.4"/>')
            # axes
            for li, lam in enumerate(lams):
                o.append(f'<text x="{px + li * cw + cw / 2}" y="{py + ph + 12}" font-size="9" text-anchor="middle" fill="{INK}">{lam}</text>')
            for di, delta in enumerate(deltas):
                o.append(f'<text x="{px - 4}" y="{py + (len(deltas) - 1 - di) * ch + ch / 2 + 3}" font-size="9" text-anchor="end" fill="{INK}">{delta}</text>')
            o.append(f'<text x="{px + pw / 2}" y="{py + ph + 26}" font-size="10" text-anchor="middle" fill="{INK}">lam (median approval latency, in windows)</text>')
            if ci == 0:
                o.append(f'<text transform="translate({px - 34},{py + ph / 2}) rotate(-90)" font-size="10" text-anchor="middle" fill="{INK}">delta (wrong proposals caught)</text>')
            # anchored region outline: delta <= 0.25 and 0.3 <= lam <= 10
            a = rule["anchored_region"]
            l_idx = [i for i, v in enumerate(lams) if a["lam"][0] - 1e-12 <= v <= a["lam"][1] + 1e-12]
            d_idx = [i for i, v in enumerate(deltas) if a["delta"][0] - 1e-12 <= v <= a["delta"][1] + 1e-12]
            ax, aw = px + min(l_idx) * cw, (max(l_idx) - min(l_idx) + 1) * cw
            ay, ah = py + (len(deltas) - 1 - max(d_idx)) * ch, (max(d_idx) - min(d_idx) + 1) * ch
            o.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="none" stroke="{RED}" stroke-width="1.6" stroke-dasharray="5,3"/>')
            g = rule["gate_home"]
            l_idx = [i for i, v in enumerate(lams) if v <= g["lam_max"] + 1e-12]
            d_idx = [i for i, v in enumerate(deltas) if v >= g["delta_min"] - 1e-12]
            hx, hw_ = px + min(l_idx) * cw, (max(l_idx) - min(l_idx) + 1) * cw
            hy, hh = py + (len(deltas) - 1 - max(d_idx)) * ch, (max(d_idx) - min(d_idx) + 1) * ch
            o.append(f'<rect x="{hx}" y="{hy}" width="{hw_}" height="{hh}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-dasharray="5,3"/>')
    o.append('</svg>')
    path.write_text("\n".join(o) + "\n")


def render_report(rows: list[dict], rule: dict, manifest: dict) -> str:
    """Render all report claims from the stored rows and executable rule data."""
    out = verdict.apply(rows, rule)
    m = rule["margin"]
    home = [r for r in rows if in_gate_home(r, rule)]
    scenario = [r for r in rows if in_anchored(r, rule)]
    a_wins = lambda r: r["harm_A"] <= (1 - m) * r["harm_C"]
    ties = lambda r: not c_beats_a(r, m) and not a_wins(r)
    c_beats_b = lambda r: r["harm_C"] <= (1 - m) * r["harm_B"]
    b_beats_c = lambda r: r["harm_B"] <= (1 - m) * r["harm_C"]
    outside = [r for r in rows if not in_gate_home(r, rule)]
    pos = [r for r in rows if r["delta"] > 0]
    thresholds = rule["thresholds"]
    lines = [
        '# Gate and window: conditional model report', '',
        f'Generated from {out["cells"]} assumed grid cells, {manifest["n_samples_per_cell"]} samples per cell, seed {manifest["seed"]}. This is a supplementary illustration. The parameters are not empirically calibrated; grid-cell percentages are not probabilities for real organisations.', '',
        '## Local rule outcome', '',
        f'**Outcome {out["outcome"]}.** {rule["outcomes"][out["outcome"]]}', '',
        'The numerical criteria are preserved from the initial rule. Their provenance does not establish independently verifiable preregistration. They select an A-versus-C comparison; B is reported separately.', '',
        '| Estimated grid fraction | Value |', '| --- | --- |',
        f'| C beats A, all cells | {fmt(out["frac_all_C_beats_A"])} |',
        f'| C beats A, assumed scenario region ({len(scenario)} cells) | {fmt(out["frac_anchored_C_beats_A"])} |',
        f'| C beats A, scenario without lowest eps | {fmt(out["frac_anchored_C_beats_A_without_lowest_eps"])} |',
        f'| A holds in gate home, including ties ({len(home)} cells) | {fmt(out["frac_gate_home_A_holds"])} |',
        f'| A strictly beats C by the margin, gate home | {fmt(frac(home, a_wins))} |',
        f'| Neither beats the other by the margin, gate home | {fmt(frac(home, ties))} |',
        f'| A strictly beats C by the margin, all cells | {fmt(frac(rows, a_wins))} |',
        f'| Neither beats the other by the margin, all cells | {fmt(frac(rows, ties))} |', '',
        f'The A-holds criterion is {thresholds["region_home_a_holds"]:.3f}; it is a non-superiority criterion for C, not an A-win requirement. Strict A wins {"meet" if frac(home, a_wins) >= thresholds["region_home_a_holds"] else "do not meet"} that fraction. The scenario C-win thresholds are {thresholds["region_anchored_c"]:.6f} and {thresholds["region_without_lowest_eps_c"]:.6f}; the construction-check thresholds are {thresholds["rigged_all_c"]:.3f} overall or {thresholds["rigged_home_c"]:.3f} in gate home.', '',
        '## Include the third comparator', '',
        '| Estimated grid fraction | Value |', '| --- | --- |',
        f'| B beats C, all cells | {fmt(frac(rows, b_beats_c))} |',
        f'| B beats C, assumed scenario region | {fmt(frac(scenario, b_beats_c))} |',
        f'| C beats B, all cells | {fmt(frac(rows, c_beats_b))} |',
        f'| C beats B, gate home | {fmt(frac(home, c_beats_b))} |', '',
        f'C beats B outside the designated gate home in {sum(c_beats_b(r) for r in outside)} cells. Its advantage over B is therefore not confined to that named region. B usually beats C in the selected scenario region. Neither result licenses treating C as the best practical arrangement.', '',
        'B is immediate unreviewed action, not a full HRO implementation. C waits until the deadline and then acts unreviewed, with instantaneous execution. It omits the safeguards and execution time of Table VIII. A comparison among these constructions is not a test of that dispatch proposal.', '',
        '## Booked accounting', '',
        f'With delta > 0, A has lower booked harm than C in {fmt(frac(pos, lambda r: r["booked_A"] < r["booked_C"]))} of cells; C has lower booked harm in {fmt(frac(pos, lambda r: r["booked_C"] < r["booked_A"] - 1e-12))}.', '',
        'Booked harm counts executed wrong actions and omits delay and missed-window losses by assumption. This is not an observation of blame, an explanation of why review gates persist, or evidence of their motives.', '',
        '## Precision and reproducibility', '',
        f'The decision margin is {m:.3f}. These are finite-sample estimates without paired uncertainty intervals. Common random numbers may reduce variance; they do not remove sampling error. The single-seed minimum-latency tables have been withdrawn because a first threshold crossing can change with additional draws. The raw results remain available. No precise boundary is established here.', '',
        '`region.svg` shows estimated A-versus-C categories for selected slices; blank cells have neither estimated advantage at the margin. The dashed scenario region is assumed, not data-calibrated.', '',
        f'Largest truncated fraction: {out["max_truncated_fraction"]:.2e}. The validator checks hashes, regenerates a sample of cells, and verifies this complete generated report. These checks establish computational consistency, not empirical validity.', '',
        'Further modeling is not required for the book. An operational superiority claim would require a specified increment, a credible comparator, appropriate observations and an evaluation capable of distinguishing them.', ''
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=HERE)
    args = ap.parse_args()
    rows = verdict.read_results(args.dir / "results.csv")
    rule = verdict.load_rule(HERE / "verdict.json")
    manifest = json.loads((args.dir / "manifest.json").read_text())
    region_svg(rows, rule, args.dir / "region.svg")
    (args.dir / "REPORT.md").write_text(render_report(rows, rule, manifest))
    print(json.dumps(verdict.apply(rows, rule), indent=2))


if __name__ == "__main__":
    main()
