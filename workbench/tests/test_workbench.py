"""Run from repo root: python -m unittest discover -s workbench/tests -v."""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import xml.etree.ElementTree as ET

from workbench import adapters
from workbench.server import Jobs, contained, handler, merged_layers, restore_layer_order, vpype_layers

INK = '{http://www.inkscape.org/namespaces/inkscape}label'
POSIX = os.name != 'nt'


def plate_svg(layers, size='210mm'):
    """A small SVG with Inkscape layers: [(label, stroke or None for a filled rect)] in document order."""
    body = ''.join(
        f'<g inkscape:groupmode="layer" inkscape:label="{label}" fill="none" stroke="{stroke}">'
        f'<path d="M1 1L5 5M6 6L9 2"/></g>' if stroke else
        f'<g inkscape:groupmode="layer" inkscape:label="{label}"><rect width="10" height="10" fill="#fff"/></g>'
        for label, stroke in layers)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            f'width="{size}" height="{size}" viewBox="0 0 10 10">{body}</svg>\n')


def labels_in_order(path):
    root = ET.parse(path).getroot()
    return [g.get(INK) for g in root if g.tag == '{http://www.w3.org/2000/svg}g']


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

    def test_driftless_engine_and_nib_reach_the_cli(self):
        config = dict(node='node')
        cmd, _, _ = adapters.plan(adapters.validate(dict(generator='driftless', params=dict(compat='1.1', penWidth=.5))),
                                  Path('/tmp/job'), config)
        self.assertEqual(cmd[cmd.index('--compat') + 1], '1.1')
        self.assertEqual(cmd[cmd.index('--penWidth') + 1], '0.5')
        default = adapters.validate(dict(generator='driftless'))
        self.assertEqual((default['params']['compat'], default['params']['penWidth']), ('', .35))
        self.assertNotIn('--compat', adapters.plan(default, Path('/tmp/job'), config)[0])
        for params in [{'compat': '1.0'}, {'compat': 1.1}, {'penWidth': .1}, {'penWidth': .9}, {'penWidth': '0.5'}]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                adapters.validate(dict(generator='driftless', params=params))

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


class VpypeLayerTests(unittest.TestCase):
    def test_layer_numbers_follow_vpype_read(self):
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / 'plate.svg'
            src.write_text(plate_svg([('4-tint', '#5a4331'), ('2-flora', '#161918'), ('3-accent', '#a32b24'), ('1-key', '#161918')]))
            layers = vpype_layers(src)
        self.assertEqual([number for _, number, _ in layers], [4, 2, 3, 1])
        self.assertEqual(merged_layers(layers), [])

    def test_same_ink_layers_merge_and_other_merges_are_refused(self):
        notes = merged_layers([('02 architecture', 2, {'#242820'}), ('02 bur oaks', 2, {'#242820'}), ('03 field', 3, {'#242820'})])
        self.assertEqual(len(notes), 1)
        self.assertIn('02 bur oaks', notes[0])
        with self.assertRaisesRegex(ValueError, 'not the same ink'):
            merged_layers([('02 key', 2, {'#161918'}), ('02 accent', 2, {'#a32b24'})])
        with self.assertRaisesRegex(ValueError, 'paper rectangle'):
            merged_layers([('0-paper', 1, set()), ('1-key', 1, {'#161918'})])

    def test_restore_layer_order_moves_only_the_layers(self):
        with tempfile.TemporaryDirectory() as t:
            written, dest = Path(t) / 'plate.vpype.svg.part', Path(t) / 'plate.vpype.svg'
            groups = ''.join(f'<g id="layer{n}" inkscape:groupmode="layer" inkscape:label="{n}-pen" style="display:inline">'
                             f'<polyline points="0,0 {n},{n}"/></g>' for n in (1, 2, 3, 4))
            written.write_text('<?xml version="1.0" encoding="utf-8" ?>\n<svg xmlns="http://www.w3.org/2000/svg" '
                               'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="2cm" height="2cm">'
                               f'<metadata>kept</metadata>{groups}</svg>\n')
            self.assertTrue(restore_layer_order(written, [4, 2, 3, 1], dest))
            self.assertFalse(written.exists())
            self.assertEqual(labels_in_order(dest), ['4-pen', '2-pen', '3-pen', '1-pen'])
            text = dest.read_text()
            self.assertNotIn('ns0:', text)
            self.assertIn('<metadata>kept</metadata>', text)
            self.assertIn('<polyline points="0,0 4,4"', text)
            # Already in document order: vpype's file is kept byte for byte.
            same = dest.read_bytes()
            written.write_bytes(same)
            self.assertFalse(restore_layer_order(written, [4, 2, 3, 1], Path(t) / 'again.svg'))
            self.assertEqual((Path(t) / 'again.svg').read_bytes(), same)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='workbench test ')
        self.jobs = Jobs(Path(self.tmp.name), timeout=120)

    def fake_job(self, svg_text):
        """A finished job holding one SVG, without running a generator."""
        job_id = 'c' * 32
        out = Path(self.tmp.name) / job_id / 'artifacts'
        out.mkdir(parents=True)
        (out / 'plate.svg').write_text(svg_text)
        self.jobs.jobs[job_id] = dict(id=job_id, created='2026-10-22T00:00:00+00:00', status='succeeded',
                                      recipe=dict(generator='driftless', params={}), command=[], cwd='', output=str(out),
                                      directory=str(out.parent), files=[], error=None, returncode=0)
        return job_id

    def fake_vpype(self):
        """Stands in for vpype: checks the arguments, waits, then writes layers in number order as vpype does."""
        script = Path(self.tmp.name) / 'fake_vpype.py'
        script.write_text(textwrap.dedent('''
            import os, pathlib, re, sys, time
            args = sys.argv[1:]
            assert args[:2] == ['read', '--no-crop'] and args[3] == 'linesort', args
            src, out = pathlib.Path(args[2]), pathlib.Path(args[-1])
            time.sleep(float(os.environ.get('FAKE_VPYPE_SLEEP', '0')))
            labels = re.findall(r'inkscape:label="([^"]+)"', src.read_text())
            layers = sorted((int(re.search(r'[0-9]+', label).group()) or 1, label) for label in labels)
            body = ''.join(f'<g id="layer{n}" inkscape:groupmode="layer" inkscape:label="{label}" style="display:inline">'
                           f'<polyline points="0,0 1,1"/></g>' for n, label in layers)
            out.write_text('<?xml version="1.0" encoding="utf-8" ?>\\n<svg xmlns="http://www.w3.org/2000/svg" '
                           'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="1cm" height="1cm">'
                           + body + '</svg>\\n')
        '''))
        launcher = Path(self.tmp.name) / 'fake-vpype'
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n')
        launcher.chmod(0o755)
        return str(launcher)

    @unittest.skipUnless(POSIX, 'the stand-in vpype is a shell script')
    def test_vpype_copy_keeps_layer_order_and_leaves_the_server_responsive(self):
        job_id = self.fake_job(plate_svg([('4-tint', '#5a4331'), ('2-flora', '#161918'), ('3-accent', '#a32b24'), ('1-key', '#161918')]))
        self.jobs.config['vpype'] = self.fake_vpype()
        result = {}
        with patch.dict(os.environ, {'FAKE_VPYPE_SLEEP': '1.5'}):
            worker = threading.Thread(target=lambda: result.update(job=self.jobs.prepare(job_id, 'artifacts/plate.svg')))
            worker.start()
            deadline = time.monotonic() + 5
            while not self.jobs.prepare_process and time.monotonic() < deadline:
                time.sleep(.01)
            started = time.monotonic()
            self.jobs.summaries(); self.jobs.snapshot(job_id)
            self.assertLess(time.monotonic() - started, .5, 'status reads waited for vpype')
            with self.assertRaisesRegex(ValueError, 'vpype copy is being made'):
                self.jobs.submit(dict(generator='driftless'))
            with self.assertRaisesRegex(ValueError, 'already being made'):
                self.jobs.prepare(job_id, 'artifacts/plate.svg')
            worker.join(15)
        copy = Path(self.tmp.name) / job_id / 'artifacts/plate.vpype.svg'
        self.assertEqual(labels_in_order(copy), ['4-tint', '2-flora', '3-accent', '1-key'])
        self.assertIn('artifacts/plate.vpype.svg', [f['path'] for f in result['job']['files']])
        self.assertIsNone(self.jobs.preparing)
        self.assertFalse(copy.with_name('plate.vpype.svg.part').exists())
        log = copy.with_name('plate.vpype.log').read_text()
        self.assertIn('"--no-crop"', log)
        self.assertIn('restored after vpype', log)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.jobs.prepare(job_id, 'artifacts/plate.svg')

    def test_vpype_copy_refuses_a_paper_rectangle_layer(self):
        job_id = self.fake_job(plate_svg([('0-paper', None), ('1-key', '#161918')]))
        self.jobs.config['vpype'] = sys.executable  # refused before anything runs
        with self.assertRaisesRegex(ValueError, 'paper rectangle'):
            self.jobs.prepare(job_id, 'artifacts/plate.svg')
        self.assertIsNone(self.jobs.preparing)
        self.assertEqual(sorted(p.name for p in (Path(self.tmp.name) / job_id / 'artifacts').iterdir()), ['plate.svg'])

    @unittest.skipUnless(POSIX, 'process groups and command lines are POSIX')
    def test_restart_stops_only_its_own_leftover_render(self):
        root = Path(self.tmp.name)
        ours_id, other_id = 'a' * 32, 'b' * 32
        sleeper = 'import time; time.sleep(60)'
        ours = subprocess.Popen([sys.executable, '-c', sleeper, str(root / ours_id / 'artifacts')], start_new_session=True)
        other = subprocess.Popen([sys.executable, '-c', sleeper], start_new_session=True)
        try:
            for job_id, proc in [(ours_id, ours), (other_id, other)]:
                (root / job_id).mkdir()
                (root / job_id / 'job.json').write_text(json.dumps(dict(
                    id=job_id, created='2026-10-22T00:00:00+00:00', status='running', pid=proc.pid,
                    recipe=dict(generator='driftless', params={}), files=[], error=None, returncode=None)))
            restarted = Jobs(root)
            try:
                self.assertIsNotNone(ours.wait(timeout=5))
                self.assertIsNone(other.poll(), 'a process that is not the job was stopped')
                self.assertEqual(restarted.snapshot(ours_id)['status'], 'interrupted')
                self.assertIn('stopped on restart', restarted.snapshot(ours_id)['error'])
                self.assertEqual(restarted.snapshot(other_id)['status'], 'interrupted')
                self.assertNotIn('stopped on restart', restarted.snapshot(other_id)['error'])
            finally:
                restarted.close()
        finally:
            for proc in (ours, other):
                if proc.poll() is None:
                    proc.kill()
                proc.wait()

    @unittest.skipUnless(shutil.which(os.environ.get('WORKBENCH_VPYPE', 'vpype')) and shutil.which('node'), 'vpype and Node required')
    def test_real_vpype_copy_keeps_every_stroke_and_the_layer_order(self):
        job = self.wait(self.jobs.submit(dict(generator='driftless', params=dict(seed='vp1', density=50, format='a5')))['id'])
        self.assertEqual(job['status'], 'succeeded', job['error'])
        svg = next(f['path'] for f in job['files'] if f['path'].endswith('.svg'))
        self.jobs.prepare(job['id'], svg)
        original = self.jobs.artifact(job['id'], svg)
        copy = original.with_name(original.stem + '.vpype.svg')
        self.assertEqual(labels_in_order(copy), labels_in_order(original))
        root = ET.parse(original).getroot()
        strokes = sum(p.get('d').count('M') for p in root.iter('{http://www.w3.org/2000/svg}path'))
        copied = sum(1 for e in ET.parse(copy).getroot().iter()
                     if e.tag.split('}')[1] in ('polyline', 'polygon', 'line'))
        self.assertEqual(copied, strokes)

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

    def test_instance_id_summaries_and_static_types(self):
        with tempfile.TemporaryDirectory() as t:
            jobs = Jobs(Path(t))
            jobs.jobs['d' * 32] = dict(id='d' * 32, created='2026-10-22T00:00:00+00:00', status='succeeded',
                                       recipe=dict(generator='farm', params={}), command=['x'], files=[{'path': 'a'}],
                                       source_sha256={'a': 'b'}, error=None, returncode=0)
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler(jobs, 'test-token', 0))
            port = server.server_address[1]
            server.RequestHandlerClass = handler(jobs, 'test-token', port, instance='run-1')
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                def get(path):
                    conn = http.client.HTTPConnection('127.0.0.1', port)
                    conn.request('GET', path)
                    response = conn.getresponse(); body = response.read(); conn.close()
                    return response, body
                response, body = get('/api/config')
                self.assertEqual(response.getheader('X-Workbench-Instance'), 'run-1')
                self.assertEqual(json.loads(body)['instance'], 'run-1')
                response, body = get('/api/jobs')
                self.assertEqual(set(json.loads(body)[0]), {'id', 'created', 'status', 'error', 'returncode', 'recipe'})
                for path, kind in [('/', 'text/html'), ('/app.js', 'text/javascript'), ('/style.css', 'text/css')]:
                    self.assertTrue(get(path)[0].getheader('Content-Type').startswith(kind), path)
            finally:
                server.shutdown(); server.server_close(); thread.join(); jobs.close()


@unittest.skipUnless(POSIX, 'SIGTERM and SIGHUP delivery is POSIX')
class ShutdownTests(unittest.TestCase):
    """Killing the server (terminal closed, kill) stops the render, as Ctrl-C does."""

    def test_sigterm_and_sighup_stop_the_active_render(self):
        for sig in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig.name), tempfile.TemporaryDirectory(prefix='workbench shutdown ') as t:
                script = Path(t) / 'serve.py'
                script.write_text(textwrap.dedent('''
                    import sys
                    from workbench import adapters, server
                    def plan(recipe, job_dir, config):  # a render that would run for a minute
                        out = job_dir / 'artifacts'
                        return [sys.executable, '-c', 'import time; time.sleep(60)', str(out)], adapters.ROOT, out
                    adapters.plan = plan
                    server.main()
                '''))
                with socket.socket() as probe:
                    probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
                proc = subprocess.Popen([sys.executable, str(script), '--port', str(port), '--output-root', str(Path(t) / 'jobs')],
                                        cwd=adapters.ROOT, env=dict(os.environ, PYTHONPATH=str(adapters.ROOT)),
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                pid = None
                try:
                    self.assertIn('Workbench:', proc.stdout.readline())
                    host = f'127.0.0.1:{port}'

                    def call(method, path, data=None, token=None):
                        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
                        headers = {'Host': host, 'Origin': 'http://' + host}
                        if token:
                            headers['X-Workbench-Token'] = token
                        conn.request(method, path, body=json.dumps(data) if data is not None else None, headers=headers)
                        body = conn.getresponse().read(); conn.close()
                        return json.loads(body)
                    token = call('GET', '/api/config')['token']
                    job_id = call('POST', '/api/jobs', dict(generator='driftless'), token)['id']
                    deadline = time.monotonic() + 10
                    while not pid and time.monotonic() < deadline:
                        pid = call('GET', f'/api/jobs/{job_id}').get('pid')
                        time.sleep(.05)
                    self.assertTrue(pid, 'the render never started')
                    proc.send_signal(sig)
                    self.assertIsNotNone(proc.wait(timeout=15))
                    state = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
                    self.assertTrue(state in ('', 'Z') or state.startswith('Z'), f'render still running ({state})')
                    record = json.loads((Path(t) / 'jobs' / job_id / 'job.json').read_text())
                    self.assertEqual(record['status'], 'cancelled')
                finally:
                    if proc.poll() is None:
                        proc.kill(); proc.wait()
                    if pid:
                        try:
                            os.killpg(pid, signal.SIGKILL)
                        except OSError:
                            pass
                    proc.stdout.close()


if __name__ == '__main__':
    unittest.main()
