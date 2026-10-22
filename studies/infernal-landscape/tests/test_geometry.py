"""The NumPy scene builder: primitives, repetition, naming, export schema, and
all three scene grammars built without Blender.

Run from the repository root:
    python -m unittest discover -s studies/infernal-landscape/tests -v
"""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
import geometry as G                                          # noqa: E402
from compile import compile_case, compile_document            # noqa: E402
from terrain_height import base_height                        # noqa: E402

ARCH = compile_case('recorded_route')


def builder():
    return G.SceneBuilder(ARCH, base_height)


def export(B):
    return B.export(footprints=[], routes=[], terrain_mode='original')


class PrimitiveTests(unittest.TestCase):
    def test_box_and_beam_face_outward(self):
        B = builder()
        B.box('crate', (0, 0, 0), (2, 1, 3))
        B.beam('post', (0, 0, 0), (0, 0, 4), .1)
        B.beam('branch', (1, 2, 3), (3, 1, 5), .08, 2, 5)
        audit = G.outward_audit(export(B))
        self.assertEqual({k: v['inward'] for k, v in audit.items()}, {'crate': 0, 'post': 0, 'branch': 0})
        self.assertTrue(all(v['components'] == 1 for v in audit.values()))

    def test_roof_and_arch_face_outward(self):
        B = builder()
        B.roof('approval roof', 0, 0, 5, 3.95, 3.6, 1.0)
        B.arch('approval portal', 0, -1.72, .14, 1.15, 1.75)
        B.arch('Open approach arch', 0, -.35, .2, 3.8, 4.1, .30)
        d = export(B); audit = G.outward_audit(d)
        self.assertEqual(sum(v['inward'] for v in audit.values()), 0)
        self.assertEqual(sum(v['components'] for v in audit.values()), 1 + 2 * (2 + 10))
        N = np.asarray(d['normals']); names = d['names']
        front = [N[i] for i, n in enumerate(names) if n == 'approval roof'][0]
        self.assertLess(front[1], -.99)                       # the near gable faces the camera side
        slopes = [N[i] for i, n in enumerate(names) if n == 'approval roof'][2:]
        self.assertTrue(all(s[2] > .5 for s in slopes))         # both slopes face up
        crown = [N[i] for i, n in enumerate(names) if n == 'approval portal voussoir.005']
        self.assertLess(crown[0][1], -.99)                      # a ring stone's near face points -y
        self.assertGreater(crown[3][2], .9)                     # its extrados at the crown points up

    def test_audit_detects_an_inside_out_solid(self):
        B = builder()
        verts, faces = G.box_geometry((0, 0, 0), (1, 1, 1))
        B.mesh('inside out', verts, [f[::-1] for f in faces], kind='box')
        self.assertEqual(G.outward_audit(export(B))['inside out']['inward'], 1)

    def test_open_sheets_and_leaves_are_not_audited(self):
        B = builder()
        B.mesh('ledge', [(0, 0, 0), (1, 0, 0), (1, 1, .2), (0, 1, .2)], [(0, 1, 2, 3)], kind='sheet')
        B.terrain_grid(np.linspace(-1, 1, 3), np.linspace(-1, 1, 3))
        self.assertEqual(G.outward_audit(export(B)), {})

    def test_newell_normal_matches_winding(self):
        np.testing.assert_allclose(G.newell_normal([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]), [0, 0, 1])
        np.testing.assert_allclose(G.newell_normal([(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)]), [0, 0, -1])


class RepetitionTests(unittest.TestCase):
    def test_module_realises_count_copies_along_the_offset(self):
        B = builder(); m = B.module('bay')
        m.box((0, 0, 0), (1, 1, 1)); m.box((.2, -.05, .3), (.8, 0, .7), 2)
        rec = B.repeat('tower | duration bays', m, 3, (0, 0, 1.04), (5, 6, .5), group_name='g', modifier_name='m')
        self.assertEqual(len(rec['faces']), 3 * 12)
        self.assertEqual(rec['mat'], [1] * 6 + [2] * 6 + [1] * 6 + [2] * 6 + [1] * 6 + [2] * 6)
        self.assertEqual(rec['face_kinds'], ['box'] * 36)
        v = rec['verts']
        np.testing.assert_allclose(v[16:32] - v[:16], [[0, 0, 1.04]] * 16)
        np.testing.assert_allclose(v[0], [5, 6, .5])
        self.assertEqual(G.outward_audit(export(B))['tower | duration bays'], dict(kind='module', components=6, inward=0))

    def test_story_nodes_height_and_face_count(self):
        B = builder()
        self.assertAlmostEqual(B.story_nodes('read', 0, 0, 1, 3.6, 3.2, 4), 4 * 1.04)
        host = B.objects[-1]
        self.assertEqual(host['name'], 'read | duration bays')
        self.assertEqual(len(host['faces']), 4 * 54)
        self.assertEqual(host['modifier_name'], 'Task duration / repeated bays')
        self.assertEqual(host['props'], dict(task_id='read', duration=4))

    def test_per_face_materials_must_match(self):
        m = G.Module('bad')
        with self.assertRaises(ValueError):
            m.add([(0, 0, 0), (1, 0, 0), (1, 1, 0)], [(0, 1, 2)], [1, 2])


class ExportTests(unittest.TestCase):
    def test_names_deduplicate_like_blender(self):
        B = builder()
        for _ in range(3): B.beam('Service tray 0', (0, 0, 0), (1, 0, 0))
        self.assertEqual([o['name'] for o in B.objects], ['Service tray 0', 'Service tray 0.001', 'Service tray 0.002'])

    def test_record_schema_and_terrain_faces(self):
        B = builder(); B.terrain_grid(np.linspace(-2, 2, 4), np.linspace(-2, 2, 3)); B.box('b', (0, 0, 0), (1, 1, 1))
        B.camera('main', (27, -38, 23), (0, 9.5, 3), 3500.); B.ink('Dependency a to b', [(0, 0, 0), (1, 1, 1)], .32, 2)
        d = export(B)
        for key in ('vertices', 'faces', 'materials', 'normals', 'names', 'hatch', 'terrain_faces', 'strokes', 'colors',
                    'cameras', 'blender', 'host', 'architecture', 'footprints', 'routes', 'terrain_modifier',
                    'geometry_nodes', 'terrain_mode', 'backend', 'objects'):
            self.assertIn(key, d)
        self.assertEqual(d['backend'], 'numpy'); self.assertEqual(d['terrain_faces'], list(range(12)))
        self.assertEqual(d['objects'], [dict(name='Host terrain', kind='terrain', faces=12), dict(name='b', kind='box', faces=6)])
        self.assertEqual(d['strokes'][0]['width'], .32 * 20); self.assertEqual(d['colors'][:7], list(G.COLORS))
        self.assertEqual(d['cameras']['main']['focal_px'], 3500.)
        json.dumps(d)  # serialisable as written to scene.json

    def test_builds_are_deterministic(self):
        A, Bb = builder(), builder()
        for X in (A, Bb): X.oak('Volume oak near', 10.3, 9.5, 6.7, 371)
        self.assertEqual(json.dumps(export(A)), json.dumps(export(Bb)))


class GrammarTests(unittest.TestCase):
    """Every scene grammar assembles through the builder with no bpy present."""

    def assemble(self, A):
        import scene as S
        B = G.SceneBuilder(A, base_height)
        ctx = dict(A=A, state=None, terrain_mode='original')
        extras = S.assemble(B, ctx)
        return B, export(B), extras

    def assert_outward(self, d):
        audit = G.outward_audit(d)
        self.assertGreater(len(audit), 20)
        self.assertEqual(sorted({k.split('.')[0] for k, v in audit.items() if v['inward']}), [])

    def test_estate_specimens(self):
        for case in ('recorded_route', 'late_opening', 'gate_unavailable'):
            B, d, extras = self.assemble(compile_case(case))
            names = set(d['names'])
            self.assertIn('restore | duration bays', names); self.assertIn('Open approach arch voussoir.009', names)
            self.assertEqual(len(extras['routes']), 3); self.assertEqual(len(extras['footprints']), 4)
            self.assertEqual(sorted(d['cameras']), ['low', 'main'])
            if case == 'late_opening': self.assertIn('Release lift landing', names)
            if case == 'gate_unavailable': self.assertIn('Unavailable portcullis.006', names)
            self.assert_outward(d)

    def test_spillway_and_window_from_their_task_files(self):
        for name, expect in (('spillway', 'permit | horizontal duration bays'), ('window', 'Window left jamb')):
            doc = json.loads((STUDY / f'{name}-tasks.json').read_text())
            B, d, extras = self.assemble(compile_document(doc, name))
            self.assertIn(expect, set(d['names'])); self.assertTrue(len(d['faces']) > 1000)
            self.assertTrue(all(h['faces'] > 0 for h in d['geometry_nodes']))
            self.assertIsNotNone(extras['planar_trees'])
            self.assert_outward(d)
        self.assertEqual(d['colors'][7], '#385f6b')  # the window's stream water material


if __name__ == '__main__':
    unittest.main()
