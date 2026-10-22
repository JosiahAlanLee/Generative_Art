"""Ideal, piecewise-constant motion; no device transport or acceleration planner.

The matrix maps page displacement in mm to signed motor pulses. Acoustic pitch
is an explicitly assumed/calibrated pulses-per-audible-cycle relationship, NOT
an assertion that a microstep pulse is the acoustic fundamental.
"""
from dataclasses import asdict, dataclass
import math
import random


def positive(value, name):
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


@dataclass(frozen=True)
class Profile:
    name: str = "illustrative-corexy-NOT-CALIBRATED"
    matrix: tuple = ((80., 80.), (80., -80.))
    pulses_per_cycle: tuple = (16., 16.)
    max_pulses_s: float = 8000.
    max_speed_mm_s: float = 80.

    def __post_init__(self):
        if (len(self.matrix) != 2 or any(len(row) != 2 for row in self.matrix)
                or any(not math.isfinite(v) for row in self.matrix for v in row)):
            raise ValueError("matrix must be finite 2 x 2")
        if abs(self.determinant) < 1e-9:
            raise ValueError("matrix must be invertible")
        if len(self.pulses_per_cycle) != 2:
            raise ValueError("pulses_per_cycle needs two values")
        for v in self.pulses_per_cycle:
            positive(v, "pulses_per_cycle")
        positive(self.max_pulses_s, "max_pulses_s")
        positive(self.max_speed_mm_s, "max_speed_mm_s")

    @property
    def determinant(self):
        (a, b), (c, d) = self.matrix
        return a*d-b*c

    def to_motors(self, xy):
        x, y = xy
        return tuple(a*x+b*y for a, b in self.matrix)

    def to_page(self, ab):
        (a, b), (c, d) = self.matrix
        u, v = ab
        return ((d*u-b*v)/self.determinant, (-c*u+a*v)/self.determinant)


def hz(note):
    return 440. * 2.**((note-69)/12)


def velocity(profile, steps, seconds):
    positive(seconds, "seconds")
    return tuple(v/seconds for v in profile.to_page(steps))


def compose(*, seed=22, rows=22, columns=18, bpm=120., profile=None,
            page=(210., 297.), margin=14., root=48, connected=True):
    """Compose two consecutive ink passes from balanced signed motor phrases.

    Four/eight balanced legs close each figure exactly in integer motor space.
    Pitch pairs choose the aspect; beat duration chooses its physical size.
    We reject overflow rather than rescale coordinates and break that relation.
    """
    profile = profile or Profile()
    if (isinstance(rows, bool) or isinstance(columns, bool)
            or not isinstance(rows, int) or not isinstance(columns, int)
            or not 1 <= rows <= 100 or not 1 <= columns <= 100):
        raise ValueError("rows and columns must be integers in 1..100")
    positive(bpm, "bpm")
    if not 20 <= bpm <= 600:
        raise ValueError("bpm must be in 20..600")
    if isinstance(root, bool) or not isinstance(root, int) or not 12 <= root <= 100:
        raise ValueError("root must be an integer MIDI note in 12..100")
    if len(page) != 2 or any(not math.isfinite(v) or v <= 0 for v in page):
        raise ValueError("page needs two positive finite dimensions")
    if not math.isfinite(margin) or margin < 0 or 2*margin >= min(page):
        raise ValueError("invalid margin")
    rng = random.Random(seed)
    width, height = page
    cell_w, cell_h = (width-2*margin)/columns, (height-2*margin)/rows
    # Repeated themes, with row transpositions and occasional seeded substitutions.
    scale = (0, 2, 5, 7, 9, 12)
    theme = [rng.randrange(len(scale)) for _ in range(8)]
    events, position, clock = [], (0, 0), 0
    pen, active_ink = False, None

    def add(steps, ms, kind, ink, targets=(None, None), cell=None):
        nonlocal position, clock
        start = profile.to_page(position)
        end_steps = tuple(a+b for a, b in zip(position, steps))
        end = profile.to_page(end_steps)
        speed = velocity(profile, steps, ms/1000.)
        rates = [s*1000/ms for s in steps]
        if max(map(abs, rates)) > profile.max_pulses_s+1e-8:
            raise ValueError("motor rate exceeds profile; change pitch, tempo or calibration")
        if math.hypot(*speed) > profile.max_speed_mm_s+1e-8:
            raise ValueError("page speed exceeds profile")
        if any(not -1e-8 <= v <= lim+1e-8 for v, lim in zip(end, page)):
            raise ValueError("motion exceeds page bounds")
        estimated = [abs(rate)/k for rate, k in zip(rates, profile.pulses_per_cycle)]
        events.append(dict(index=len(events), t_ms=clock, duration_ms=ms,
                           kind=kind, ink=ink, pen_down=pen,
                           start_mm=start, end_mm=end, motor_steps=steps,
                           motor_pulses_s=rates, estimated_hz=estimated,
                           target_midi=targets, cell=cell))
        clock += ms
        position = end_steps

    def set_pen(down, ink):
        nonlocal pen
        pen = down
        add((0, 0), 120, "pen_lower" if down else "pen_raise", ink)

    def move_to(xy, ink, kind="travel"):
        target = tuple(round(s) for s in profile.to_motors(xy))
        steps = tuple(b-a for a, b in zip(position, target))
        length = math.hypot(*profile.to_page(steps))
        # Round upward so pulse and page speed limits remain bounds.
        ms = max(1, math.ceil(max(length/min(25., profile.max_speed_mm_s),
                                 max(map(abs, steps))/profile.max_pulses_s)*1000))
        add(steps, ms, kind, ink)

    for layer, ink in enumerate(("indigo", "oxide")):
        if active_ink is not None:
            # Untimed manual operation; following timestamps exclude this pause.
            events.append(dict(index=len(events), t_ms=clock, duration_ms=0,
                               kind="pen_change", ink=ink, pen_down=False,
                               start_mm=profile.to_page(position), end_mm=profile.to_page(position),
                               motor_steps=(0, 0), motor_pulses_s=(0., 0.),
                               estimated_hz=(0., 0.), target_midi=(None, None), cell=None))
        active_ink = ink
        for row in range(rows):
            for col in range(columns):
                degree = theme[(col+row//4) % len(theme)]
                if rng.random() < .12:
                    degree = rng.randrange(len(scale))
                n1 = root + scale[degree]
                n2 = root + scale[(degree + 2 + row % 3) % len(scale)]
                # Layer two shares the harmonic alphabet but uses a different rhythm/form.
                signs = ((1, 1), (1, -1), (-1, -1), (-1, 1))
                if layer:
                    signs = ((1, 0), (1, 1), (0, 1), (-1, 1),
                             (-1, 0), (-1, -1), (0, -1), (1, -1))
                leg_ms = max(1, round((60000/bpm)*.5/len(signs)))
                counts = tuple(max(1, round(hz(n)*k*leg_ms/1000))
                               for n, k in zip((n1, n2), profile.pulses_per_cycle))
                local = [(0., 0.)]
                for a, b in signs:
                    dx, dy = profile.to_page((a*counts[0], b*counts[1]))
                    x, y = local[-1]
                    local.append((x+dx, y+dy))
                lo = [min(p[i] for p in local) for i in (0, 1)]
                hi = [max(p[i] for p in local) for i in (0, 1)]
                # Leave a .8 mm guard for rounding and the second ink's offset.
                if hi[0]-lo[0] > cell_w-1.6 or hi[1]-lo[1] > cell_h-1.6:
                    raise ValueError("phrase does not fit its cell; raise bpm, reduce grid or pitch")
                center = (margin+(col+.5)*cell_w+.25*layer,
                          margin+(row+.5)*cell_h+.35*layer)
                origin = tuple(center[i]-(lo[i]+hi[i])/2 for i in (0, 1))
                if col == 0 or not connected:
                    move_to(origin, ink)
                    set_pen(True, ink)
                else:
                    move_to(origin, ink, "link")
                for a, b in signs:
                    add((a*counts[0], b*counts[1]), leg_ms, "phrase", ink,
                        (n1 if a else None, n2 if b else None), (row, col))
                if col == columns-1 or not connected:
                    set_pen(False, ink)
    score = dict(schema="plotter-score/0.1", seed=seed, bpm=bpm,
                 page_mm=page, margin_mm=margin, rows=rows, columns=columns,
                 root_midi=root, connected=connected, profile=asdict(profile),
                 duration_ms=clock, events=events,
                 timing_model="ideal constant velocity; no acceleration or controller transport",
                 exclusions=["homing", "startup", "manual pen-change pause", "return home"],
                 calibration="illustrative; acoustic transfer must be measured on the actual machine")
    moving = [e for e in events if any(e["motor_steps"])]
    errors = [abs(1200*math.log2(f/hz(n))) for e in moving
              for f, n in zip(e["estimated_hz"], e["target_midi"]) if n is not None]
    # This is a diagnostic, not a claimed acceleration estimate or feasibility check.
    jumps, previous = [], (0., 0.)
    for e in events:
        current = tuple(e["motor_pulses_s"])
        jumps.append(max(abs(a-b) for a, b in zip(current, previous)))
        previous = current
    score["metrics"] = dict(segments=len(moving),
        pen_down_mm=sum(math.dist(e["start_mm"], e["end_mm"]) for e in moving if e["pen_down"]),
        max_pitch_error_cents=max(errors, default=0.),
        max_velocity_jump_pulses_s=max(jumps, default=0.),
        hardware_ready=False)
    return score
