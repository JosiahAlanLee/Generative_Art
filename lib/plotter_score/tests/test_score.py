import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET

from lib.plotter_score import Profile, compose, velocity, write_midi, write_svg, write_wav, write_vastish_sequence


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile()
        self.score = compose(rows=3, columns=5)

    def test_inverse_and_signed_motor_velocities(self):
        for profile in (self.profile, Profile(matrix=((80, 0), (0, 120)))):
            for xy in ((12.3, -4.2), (0, 0), (-18.75, 51)):
                recovered = profile.to_page(profile.to_motors(xy))
                for a, b in zip(recovered, xy):
                    self.assertAlmostEqual(a, b)
        self.assertEqual(velocity(self.profile, (160, 0), 1), (1, 1))
        self.assertEqual(velocity(self.profile, (0, 160), 1), (1, -1))

    def test_every_segment_reconstructs_geometry_and_clock(self):
        previous, clock = (0, 0), 0
        for e in self.score['events']:
            self.assertEqual(e['t_ms'], clock)
            self.assertEqual(e['start_mm'], previous)
            dx = self.profile.to_page(e['motor_steps'])
            for a, b, delta in zip(e['start_mm'], e['end_mm'], dx):
                self.assertAlmostEqual(b-a, delta)
            for value, bound in zip(e['end_mm'], self.score['page_mm']):
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, bound)
            clock += e['duration_ms']
            previous = e['end_mm']
        self.assertEqual(clock, self.score['duration_ms'])
        json.dumps(self.score, allow_nan=False)

    def test_each_phrase_closes_in_integer_motor_space(self):
        cells = {}
        for e in self.score['events']:
            if e['kind'] == 'phrase':
                key = (e['ink'], *e['cell'])
                group = cells.setdefault(key, [0, 0])
                for motor in (0, 1):
                    group[motor] += e['motor_steps'][motor]
        self.assertEqual(len(cells), 2*3*5)
        self.assertTrue(all(value == [0, 0] for value in cells.values()))

    def test_pitch_error_and_faster_tempo_smaller_marks(self):
        self.assertLess(self.score['metrics']['max_pitch_error_cents'], 10)
        fast = compose(rows=3, columns=5, bpm=240)
        def phrase_length(score):
            return sum(math.dist(e['start_mm'], e['end_mm'])
                       for e in score['events'] if e['kind'] == 'phrase')
        self.assertAlmostEqual(phrase_length(fast)/phrase_length(self.score), .5, delta=.02)

    def test_seed_and_calibration_act_on_both_form_and_pitch(self):
        self.assertEqual(self.score, compose(rows=3, columns=5))
        self.assertNotEqual(self.score['events'], compose(rows=3, columns=5, seed=23)['events'])
        other = compose(rows=3, columns=5, profile=Profile(pulses_per_cycle=(8, 16)))
        e1 = next(e for e in self.score['events'] if e['kind'] == 'phrase')
        e2 = next(e for e in other['events'] if e['kind'] == 'phrase')
        self.assertNotEqual(e1['motor_steps'], e2['motor_steps'])
        self.assertNotEqual(self.profile.to_page(e1['motor_steps']),
                            self.profile.to_page(e2['motor_steps']))
        self.assertAlmostEqual(e1['estimated_hz'][0], e2['estimated_hz'][0], delta=2)

    def test_invalid_and_infeasible_controls(self):
        for options in ({'bpm': float('nan')}, {'bpm': 0}, {'rows': 1.5},
                        {'rows': True}, {'root': 128}, {'page': (100, 0)},
                        {'margin': -1}, {'bpm': 20, 'columns': 100},
                        {'profile': Profile(max_pulses_s=1)}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                compose(**options)
        for fields in ({'matrix': ((1, 1), (1, 1))}, {'pulses_per_cycle': (0, 1)},
                       {'matrix': ((math.inf, 0), (0, 1))}):
            with self.assertRaises(ValueError):
                Profile(**fields)

    def test_svg_contains_exact_pen_down_order_and_no_travel(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'score.svg'
            write_svg(self.score, path)
            root = ET.parse(path).getroot()
            paths = root.findall('.//{http://www.w3.org/2000/svg}path')
            self.assertEqual(len(paths), 6)  # one path per row/pass
            for path in paths:
                first, last = map(int, (path.get('data-first-event'), path.get('data-last-event')))
                events = self.score['events'][first:last+1]
                self.assertTrue(all(e['pen_down'] for e in events))
                self.assertEqual(path.get('d').count(' L '), len(events))
                for e in events:
                    point = f"{e['end_mm'][0]:.5f},{e['end_mm'][1]:.5f}"
                    self.assertIn(point, path.get('d'))

    def test_midi_roundtrip_timing_and_no_hanging_notes(self):
        # Independent minimal SMF reader verifies emitted event timing and gates.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'notes.mid'
            write_midi(self.score, path)
            data = path.read_bytes()
            self.assertEqual(data[:4], b'MThd')
            self.assertEqual(struct.unpack('>HHH', data[8:14]), (0, 1, 500))
            self.assertEqual(struct.unpack('>I', data[18:22])[0], len(data)-22)
            offset, tick, active, notes = 22, 0, set(), 0
            while offset < len(data):
                value = 0
                while True:
                    byte = data[offset]
                    offset += 1
                    value = (value << 7) | (byte & 127)
                    if byte < 128:
                        break
                tick += value
                status = data[offset]
                offset += 1
                if status == 255:
                    kind, length = data[offset:offset+2]
                    offset += 2
                    if kind == 0x51:
                        self.assertEqual(int.from_bytes(data[offset:offset+length], 'big'), 500000)
                    offset += length
                    if kind == 0x2f:
                        break
                else:
                    key, vel = data[offset:offset+2]
                    offset += 2
                    pair = (status & 15, key)
                    if status & 0xf0 == 0x90 and vel:
                        self.assertNotIn(pair, active)
                        active.add(pair)
                        notes += 1
                    else:
                        self.assertIn(pair, active)
                        active.remove(pair)
            self.assertFalse(active)
            self.assertGreater(notes, 0)
            self.assertEqual(tick, self.score['duration_ms'])

    def test_wav_frequency_and_pen_up_travel_is_audible(self):
        # Known rates, independent of the composer: 220 Hz left / 330 Hz right.
        score = {'duration_ms': 1000, 'events': [dict(t_ms=0, duration_ms=1000,
                 kind='travel', pen_down=False, estimated_hz=(220., 330.))]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'test.wav'
            self.assertEqual(write_wav(score, path, seconds=.5, sample_rate=8000), .5)
            with wave.open(str(path)) as wav:
                self.assertEqual(wav.getnchannels(), 2)
                self.assertEqual(wav.getnframes(), 4000)
                samples = struct.unpack('<8000h', wav.readframes(4000))
            for motor, frequency in enumerate((220, 330)):
                channel = samples[400+motor:7600:2]
                crossings = sum(a <= 0 < b for a, b in zip(channel, channel[1:]))
                measured = crossings/(len(channel)/8000)
                self.assertAlmostEqual(measured, frequency, delta=3)
            self.assertLess(max(map(abs, samples)), 32767)

    def test_disconnected_pen_state_and_separate_passes(self):
        score = compose(rows=2, columns=3, connected=False)
        self.assertEqual(sum(e['kind'] == 'pen_lower' for e in score['events']), 12)
        self.assertFalse(any(e['kind'] == 'link' for e in score['events']))
        changes = [e for e in score['events'] if e['kind'] == 'pen_change']
        self.assertEqual(len(changes), 1)
        self.assertFalse(changes[0]['pen_down'])
        self.assertFalse(score['metrics']['hardware_ready'])

    def test_vastish_excerpt_has_relative_delays_and_releases_at_cutoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'sequence.txt'
            write_vastish_sequence(self.score, path, seconds=1.234)
            time, active = 0, {}
            for line in path.read_text().splitlines():
                delay, target, *args = line.rstrip(';').split()
                self.assertGreaterEqual(int(delay), 0)
                time += int(delay)
                if target == 'vast-note':
                    key, vel = map(int, args)
                    active[key] = active.get(key, 0)+(1 if vel else -1)
                    self.assertGreaterEqual(active[key], 0)
            self.assertFalse(any(active.values()))
            self.assertEqual(time, 1234+1200)


if __name__ == '__main__':
    unittest.main()
