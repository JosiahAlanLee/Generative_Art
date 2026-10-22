"""Dependency-free exports, all reading the same ordered motion events."""
from array import array
import csv
import math
from pathlib import Path
import struct
import sys
import wave


def write_svg(score, path):
    w, h = score["page_mm"]
    colors = {"indigo": "#303e72", "oxide": "#ae594e"}
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">',
             '<title>Motor counterpoint — ordered two-ink drawing</title>',
             '<desc>Geometry only. Timings live in score.json; preserve pass and path order. No path sorting, reversal, simplification or scaling after composition.</desc>']
    for ink, color in colors.items():
        lines.append(f'<g id="{ink}" inkscape:groupmode="layer" inkscape:label="{ink}" fill="none" stroke="{color}" stroke-width="0.16" stroke-linejoin="round" stroke-linecap="round">')
        points, first, last = [], None, None

        def flush():
            if len(points) > 1:
                commands = 'M ' + ' L '.join(f'{x:.5f},{y:.5f}' for x, y in points)
                lines.append(f'<path data-first-event="{first}" data-last-event="{last}" d="{commands}"/>')

        for e in score["events"]:
            draw = e["ink"] == ink and e["pen_down"] and any(e["motor_steps"])
            if draw:
                if not points:
                    points = [e["start_mm"]]
                    first = e["index"]
                points.append(e["end_mm"])
                last = e["index"]
            else:
                flush()
                points, first, last = [], None, None
        flush()
        lines.append('</g>')
    lines.append('</svg>')
    Path(path).write_text('\n'.join(lines)+'\n', encoding="utf-8")


def vlq(n):
    if not 0 <= n <= 0x0fffffff:
        raise ValueError("MIDI delta out of range")
    result = [n & 127]
    while n >> 7:
        n >>= 7
        result.insert(0, (n & 127) | 128)
    return bytes(result)


def note_messages(score):
    """(absolute milliseconds, MIDI bytes), shared by SMF and Vastish exports."""
    messages = []
    for motor in (0, 1):
        active, end = None, 0
        for e in score["events"]:
            note = e["target_midi"][motor] if e["kind"] == "phrase" else None
            start, finish = e["t_ms"], e["t_ms"]+e["duration_ms"]
            if note != active or start != end:
                if active is not None:
                    messages.append((end, bytes((0x80+motor, active, 0))))
                if note is not None:
                    messages.append((start, bytes((0x90+motor, note, 80))))
                active = note
            end = finish
        if active is not None:
            messages.append((end, bytes((0x80+motor, active, 0))))
    messages.sort(key=lambda pair: pair[0])
    return messages


def write_midi(score, path):
    """Intended-note channels; travel/links are rests; same-note legs sustain.

    1000 ticks/second = division 500 with tempo 500000 us/quarter,
    independently of composition bpm.
    """
    messages = [(0, b'\xff\x51\x03\x07\xa1\x20'), *note_messages(score)]
    track, previous = bytearray(), 0
    for tick, data in messages:
        track.extend(vlq(tick-previous)+data)
        previous = tick
    track.extend(vlq(score["duration_ms"]-previous)+b'\xff\x2f\x00')
    Path(path).write_bytes(b'MThd'+struct.pack('>IHHH', 6, 0, 1, 500)
                          +b'MTrk'+struct.pack('>I', len(track))+track)


def write_vastish_sequence(score, path, seconds=30., program=5):
    """Excerpt for DSP_Emulation's existing headless Vastish/Pd renderer.

    Its qlist dialect takes relative delays and vast-note/prog/rec messages.
    Uses the intended notes, not the uncalibrated acoustic-rate model.
    """
    if not math.isfinite(seconds) or seconds <= 0 or program not in range(6):
        raise ValueError("invalid Vastish excerpt duration or program")
    limit = min(round(seconds*1000), score['duration_ms'])
    lines = [f'0 vast-prog {program};', '0 vast-rec open vastish-excerpt.wav;',
             '0 vast-rec start;']
    previous, active = 0, {}
    for tick, data in note_messages(score):
        if tick >= limit:
            break
        pair = (data[0] & 15, data[1])
        on = data[0] & 0xf0 == 0x90
        if on:
            active[pair] = data[1]
        else:
            active.pop(pair, None)
        lines.append(f'{tick-previous} vast-note {data[1]} {data[2] if on else 0};')
        previous = tick
    for note in active.values():
        lines.append(f'{limit-previous} vast-note {note} 0;')
        previous = limit
    lines.append(f'{limit-previous+1200} vast-rec stop;')
    Path(path).write_text('\n'.join(lines)+'\n')


def write_wav(score, path, seconds=30., sample_rate=24000):
    """Stereo surrogate: motor 1 left, motor 2 right, including pen-up travel.

    Harmonic oscillators audition the assumed acoustic rates. No physical
    resonances, loads, microstep ripple or acceleration are simulated.
    """
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("audio seconds must be finite and positive")
    if not isinstance(sample_rate, int) or sample_rate < 8000:
        raise ValueError("sample rate must be an integer >=8000")
    limit = min(round(seconds*sample_rate), round(score["duration_ms"]*sample_rate/1000))
    phase, rendered = [0., 0.], 0
    with wave.open(str(path), 'wb') as wav:
        wav.setparams((2, 2, sample_rate, 0, 'NONE', 'not compressed'))
        for e in score["events"]:
            end = min(limit, round((e["t_ms"]+e["duration_ms"])*sample_rate/1000))
            count = end-rendered
            if count <= 0:
                continue
            frequencies = e["estimated_hz"]
            full_count = round(e["duration_ms"]*sample_rate/1000)
            data = array('h')
            for i in range(count):
                # Short audition envelopes avoid clicks; this is not a motor envelope.
                env = min(1., i/(sample_rate*.004), max(0., (full_count-1-i)/(sample_rate*.004)))
                fade_out = min(1., max(0., (limit-1-rendered-i)/(sample_rate*.02)))
                for motor, f in enumerate(frequencies):
                    value = 0.
                    if 0 < f < sample_rate/2:
                        phase[motor] = (phase[motor]+2*math.pi*f/sample_rate) % (2*math.pi)
                        value = math.sin(phase[motor])
                        if 2*f < sample_rate/2:
                            value += .25*math.sin(2*phase[motor])
                        if 3*f < sample_rate/2:
                            value += .10*math.sin(3*phase[motor])
                    data.append(round(value*env*fade_out*18000))
            if sys.byteorder != 'little':
                data.byteswap()
            wav.writeframes(data.tobytes())
            rendered = end
            if rendered == limit:
                break
    return rendered/sample_rate


def write_csv(score, path):
    with Path(path).open('w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(('event', 'time_ms', 'duration_ms', 'kind', 'ink', 'pen_down',
                         'x_mm', 'y_mm', 'motor1_hz_assumed', 'motor2_hz_assumed',
                         'note1_target', 'note2_target', 'vastish_v_oct1', 'vastish_v_oct2'))
        for e in score["events"]:
            notes = e["target_midi"]
            writer.writerow((e["index"], e["t_ms"], e["duration_ms"], e["kind"], e["ink"],
                             int(e["pen_down"]), *e["end_mm"], *e["estimated_hz"],
                             *('' if n is None else n for n in notes),
                             *('' if n is None else (n-60)/12 for n in notes)))
