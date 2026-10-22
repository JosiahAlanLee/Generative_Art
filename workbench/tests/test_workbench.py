"""Run from repo root: python -m unittest discover -s workbench/tests -v."""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from workbench import adapters
from workbench.server import Jobs, contained, handler


class AdapterTests(unittest.TestCase):
    def test_validation_rejects_path_seeds_invalid_numbers_and_unknown_controls(self):
        for params in [{'seed': '../outside'}, {'seed': '--help'}, {'density': float('nan')},
                       {'density': True}, {'format': 'bogus'}, {'script': 'evil'}, {'bleed': 'false'}]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                adapters.validate(dict(generator='driftless', params=params))
        with self.assertRaises(ValueError):
            adapters.validate(dict(generator='farm', params={'seed': -1}))
        with self.assertRaises(ValueError):
            contained(Path('/tmp/job'), '../secret')

    def test_infernal_uses_separate_runtimes_and_validates_cameras(self):
        config = dict(node='node', python='/runner python', engraving='/engraving python', blender='/bpy python')
        recipe = adapters.validate(dict(generator='infernal', params=dict(dry_run=False, plates=True, view='tower')))
        cmd, cwd, out = adapters.plan(recipe, Path('/tmp/job with spaces'), config)
        self.assertEqual(cmd[0], '/runner python')
        self.assertEqual(cmd[cmd.index('--engraving-python')+1], '/engraving python')
        self.assertEqual(cmd[cmd.index('--blender-python')+1], '/bpy python')
        self.assertEqual(out, cwd / 'output')
        self.assertIn('/tmp/job with spaces/workspace', str(cwd))
        for p in [dict(view='tower'), dict(plates=True, face_patterns=True), dict(seed=42)]:
            with self.assertRaises(ValueError):
                adapters.validate(dict(generator='infernal', params=p))
        config['blender'] = ''
        with self.assertRaises(ValueError):
            adapters.plan(recipe, Path('/tmp/job'), config)

    def test_infernal_does_not_inherit_other_scene_flags(self):
        with patch.dict(os.environ, {'INFERNAL_INPUT': '/private/other.json', 'INFERNAL_PLATES': '1', 'TERRAIN_VIEW': 'barn'}):
            env = adapters.environment(adapters.settings())
        self.assertNotIn('INFERNAL_INPUT', env)
        self.assertNotIn('INFERNAL_PLATES', env)
        self.assertNotIn('TERRAIN_VIEW', env)

    def test_infernal_snapshot_has_sources_but_no_delivered_outputs(self):
        with tempfile.TemporaryDirectory() as t:
            dest = Path(t)
            adapters.isolated_sources(dest)
            self.assertTrue((dest / 'lib/farm_objects/objects.py').exists())
            self.assertTrue((dest / 'studies/infernal-landscape/vendor/raycore.py').exists())
            self.assertFalse((dest / 'studies/infernal-landscape/output').exists())
            original = adapters.ROOT / 'studies/infernal-landscape/run.py'
            self.assertEqual(original.read_bytes(), (dest / 'studies/infernal-landscape/run.py').read_bytes())


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='workbench test ')
        self.jobs = Jobs(Path(self.tmp.name), timeout=120)

    def tearDown(self):
        self.jobs.close()
        self.tmp.cleanup()

    def wait(self, job_id):
        deadline = time.monotonic()+120
        while time.monotonic() < deadline:
            job = self.jobs.snapshot(job_id)
            if job['status'] not in {'running', 'queued'}:
                return job
            time.sleep(.05)
        self.fail('Job did not finish')

    def test_missing_runtime_failure_persists_and_restart_retains_recipe(self):
        self.jobs.config['node'] = '/no/such/node'
        job = self.jobs.submit(dict(generator='driftless'))
        result = self.wait(job['id'])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('/no/such/node', result['error'])
        restored = Jobs(Path(self.tmp.name))
        try:
            self.assertEqual(restored.snapshot(job['id'])['recipe'], job['recipe'])
        finally:
            restored.close()

    def test_cancel_running_job_stops_process_and_next_job_can_run(self):
        with patch('workbench.adapters.plan', return_value=(
                [sys.executable, '-c', 'import time; print("started",flush=True); time.sleep(60)'],
                adapters.ROOT, Path(self.tmp.name) / 'artifacts')):
            job = self.jobs.submit(dict(generator='driftless'))
        deadline = time.monotonic()+5
        while self.jobs.process is None and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertIsNotNone(self.jobs.process)
        self.jobs.cancel(job['id'])
        deadline = time.monotonic()+5
        while self.jobs.current is not None and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertIsNone(self.jobs.current)
        self.assertEqual(self.jobs.snapshot(job['id'])['status'], 'cancelled')
        self.jobs.config['node'] = '/missing-node'
        self.assertEqual(self.wait(self.jobs.submit(dict(generator='driftless'))['id'])['status'], 'failed')

    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_real_driftless_seed_repeatability_and_output_isolation(self):
        recipe = dict(generator='driftless', params=dict(seed='test42', density=50, focal='vista', format='a5'))
        a = self.wait(self.jobs.submit(recipe)['id'])
        b = self.wait(self.jobs.submit(recipe)['id'])
        for job in [a, b]:
            self.assertEqual(job['status'], 'succeeded', job['error'])
            self.assertTrue(any(f['path'].endswith('manifest.json') for f in job['files']))
        svg_a = next(f['path'] for f in a['files'] if f['path'].endswith('.svg'))
        svg_b = next(f['path'] for f in b['files'] if f['path'].endswith('.svg'))
        self.assertNotEqual(a['output'], b['output'])
        self.assertEqual(self.jobs.artifact(a['id'], svg_a).read_bytes(), self.jobs.artifact(b['id'], svg_b).read_bytes())
        with self.assertRaises(ValueError):
            self.jobs.artifact(a['id'], '../job.json')
        with self.assertRaises(ValueError):
            self.jobs.artifact(a['id'], 'job.json')

    @unittest.skipUnless(importlib.util.find_spec('numba') and importlib.util.find_spec('cairosvg'), 'Farm dependencies required')
    def test_real_farm_svg_png_mesh_and_record(self):
        import xml.etree.ElementTree as ET
        from PIL import Image
        job = self.wait(self.jobs.submit(dict(generator='farm', params=dict(seed=41, only='disk_harrow', decay=.6)))['id'])
        self.assertEqual(job['status'], 'succeeded', job['error'])
        paths = [f['path'] for f in job['files']]
        for suffix in ['.svg', '.png', '.obj', '.json']:
            self.assertTrue(any(p.endswith(suffix) for p in paths), suffix)
        svg = self.jobs.artifact(job['id'], next(p for p in paths if p.endswith('.svg')))
        self.assertEqual(ET.parse(svg).getroot().attrib['width'], '190mm')
        png = self.jobs.artifact(job['id'], next(p for p in paths if p.endswith('.png')))
        with Image.open(png) as image:
            image.verify()


class HTTPTests(unittest.TestCase):
    def test_local_origin_token_and_file_confinement(self):
        with tempfile.TemporaryDirectory() as t:
            jobs = Jobs(Path(t))
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler(jobs, 'test-token', 0))
            port = server.server_address[1]
            server.RequestHandlerClass = handler(jobs, 'test-token', port)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                def request(method, path, data=None, headers=None):
                    conn = http.client.HTTPConnection('127.0.0.1', port)
                    conn.request(method, path, body=json.dumps(data) if data is not None else None, headers=headers or {})
                    response = conn.getresponse(); status = response.status; body = response.read(); conn.close()
                    return status, body
                self.assertEqual(request('GET', '/')[0], 200)
                self.assertEqual(request('GET', '/api/config')[0], 200)
                self.assertEqual(request('GET', '/api/config', headers={'Host': 'attacker.test'})[0], 403)
                self.assertEqual(request('POST', '/api/jobs', {})[0], 403)
                headers = {'X-Workbench-Token': 'test-token', 'Origin': f'http://127.0.0.1:{port}'}
                self.assertEqual(request('POST', '/api/jobs', [], headers)[0], 400)
                self.assertEqual(request('POST', '/api/jobs', {'generator': 'bad'}, headers)[0], 400)
                self.assertEqual(request('GET', '/api/jobs/unknown/files/../../secret')[0], 404)
            finally:
                server.shutdown(); server.server_close(); thread.join(); jobs.close()


if __name__ == '__main__':
    unittest.main()
