"""Standard-library localhost server and one-at-a-time process queue.

Run: python -m workbench.server [--output-root PATH] [--port 8765]
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import threading
from urllib.parse import unquote, urlsplit
import uuid
import xml.etree.ElementTree as ET

from . import adapters

STATIC = Path(__file__).parent / 'static'
# Fixed types rather than mimetypes: a Windows registry that maps .js to text/plain would
# otherwise make the browser refuse app.js under nosniff.
STATIC_FILES = {'/': ('index.html', 'text/html; charset=utf-8'),
                '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                '/style.css': ('style.css', 'text/css; charset=utf-8')}
ACTIVE = {'queued', 'running'}
SVG_NS = 'http://www.w3.org/2000/svg'
INK_NS = 'http://www.inkscape.org/namespaces/inkscape'
DRAWN = {f'{{{SVG_NS}}}{t}' for t in ('path', 'rect', 'line', 'polyline', 'polygon', 'circle', 'ellipse')}
SUMMARY = ('id', 'created', 'status', 'error', 'returncode', 'recipe')


def inks(element):
    """Stroke colours used in an element and its descendants (attribute or inline style)."""
    found = set()
    for el in element.iter():
        style = re.search(r'(?:^|;)\s*stroke\s*:\s*([^;]+)', el.get('style') or '')
        for value in (el.get('stroke'), style.group(1) if style else None):
            if value and value.strip() != 'none':
                found.add(value.strip().lower())
    return found


def vpype_layers(svg_path):
    """Top-level layers in document order: (name, vpype layer number, inks).

    vpype's rule (`vpype read --help`): the first digits of inkscape:label (0 means 1), else of
    the id, else the group's position. Drawn elements outside any group go to layer 1.
    """
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f'could not read {Path(svg_path).name}: {exc}') from None
    layers = []
    groups = [el for el in root if el.tag == f'{{{SVG_NS}}}g']
    for position, group in enumerate(groups, 1):
        label = group.get(f'{{{INK_NS}}}label') or ''
        number = None
        for value in (label, group.get('id') or ''):
            match = re.search(r'\d+', value)
            if match:
                number = int(match.group()) or 1
                break
        layers.append((label or group.get('id') or f'group {position}', number or position, inks(group)))
    loose = [el for el in root if el.tag in DRAWN]
    if loose:
        layers.append(('elements outside any layer', 1, set().union(*(inks(el) for el in loose))))
    return layers


def merged_layers(layers):
    """Layers vpype puts together. Same-ink layers sharing a number (e.g. several "02 …" layers
    drawn with one pen) merge as intended; a merge across inks, or with a layer that has no
    stroke such as a paper rectangle, would plot the wrong thing, so it is refused."""
    by_number = {}
    for name, number, ink in layers:
        by_number.setdefault(number, []).append((name, ink))
    notes = []
    for number, members in sorted(by_number.items()):
        if len(members) < 2:
            continue
        names = ' and '.join(name for name, _ in members)
        if any(not ink for _, ink in members) or len(set().union(*(ink for _, ink in members))) > 1:
            hint = ('; render without "Include paper rectangle" to prepare a plot copy'
                    if any('paper' in name for name, _ in members) else '')
            raise ValueError(f'vpype would merge {names} into one layer ({number}) although they '
                             f'are not the same ink{hint}')
        notes.append(f'layer {number}: {names} share one ink and become one layer')
    return notes


def restore_layer_order(prepared, numbers, dest):
    """vpype writes layers in number order; put them back in the source's document order.

    `numbers` are the source's vpype layer numbers in document order. Returns True if the
    order changed. The geometry inside each layer is untouched.
    """
    try:
        # Keep vpype's prefixes (inkscape:, dc:, …) rather than ElementTree's ns0:. They are all
        # declared before the root element starts, so reading stops there.
        with open(prepared, 'rb') as stream:
            for event, node in ET.iterparse(stream, events=['start-ns', 'start']):
                if event == 'start':
                    break
                try:
                    ET.register_namespace(*node)
                except ValueError:  # an "ns0"-style prefix ElementTree reserves; it writes its own
                    pass
        tree = ET.parse(prepared)
    except ET.ParseError as exc:
        raise ValueError(f'vpype wrote an unreadable SVG: {exc}') from None
    root = tree.getroot()
    groups = [el for el in root if el.tag == f'{{{SVG_NS}}}g']
    by_id = {g.get('id'): g for g in groups}
    ordered = []
    for number in numbers:
        group = by_id.get(f'layer{number}')
        if group is not None and all(group is not g for g in ordered):
            ordered.append(group)
    ordered += [g for g in groups if all(g is not o for o in ordered)]
    if all(a is b for a, b in zip(ordered, groups)):
        os.replace(prepared, dest)
        return False
    first = list(root).index(groups[0])
    for group in groups:
        root.remove(group)
    for offset, group in enumerate(ordered):
        root.insert(first + offset, group)
    tree.write(prepared, encoding='utf-8', xml_declaration=True)
    os.replace(prepared, dest)
    return True


def command_line(pid):
    """A process's command line on POSIX, or '' if it cannot be read."""
    try:
        proc = Path(f'/proc/{pid}/cmdline')
        if proc.exists():
            return proc.read_bytes().replace(b'\0', b' ').decode(errors='replace')
        return subprocess.run(['ps', '-ww', '-o', 'command=', '-p', str(pid)],
                              capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ''


def dump(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    tmp.replace(path)


def contained(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('path escapes job directory')
    return path


class Jobs:
    def __init__(self, root, config=None, timeout=3600):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.config = config or adapters.settings()
        self.timeout = timeout
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.jobs = {}
        self.process = None
        self.current = None
        self.stopping = False
        self.preparing = None
        self.prepare_process = None
        for file in self.root.glob('*/job.json'):
            job = json.loads(file.read_text())
            if job['status'] in ACTIVE:
                error = 'Server stopped; submit the saved recipe to retry'
                if self.stop_leftover(job):
                    error = ('Server stopped while this job ran; its process was still running and was '
                             'stopped on restart. Submit the saved recipe to retry')
                job.update(status='interrupted', error=error)
                dump(file, job)
            self.jobs[job['id']] = job

    @staticmethod
    def stop_leftover(job):
        """Stop a render left running by a server that was killed (POSIX only).

        Only a live process whose command line names this job's folder is stopped, so a
        recycled pid is never touched. On Windows os.kill(pid, 0) would terminate any process,
        so nothing is attempted there.
        """
        pid = job.get('pid')
        if not pid or os.name == 'nt':
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        if job['id'] not in command_line(pid):
            return False
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            return False
        return True

    def snapshot(self, job_id=None):
        with self.lock:
            value = self.jobs[job_id] if job_id else sorted(self.jobs.values(), key=lambda j: j['created'], reverse=True)
            return json.loads(json.dumps(value))

    def summaries(self):
        """The history list: no file lists, commands or source hashes, which only the job view needs."""
        with self.lock:
            rows = sorted(self.jobs.values(), key=lambda j: j['created'], reverse=True)
            return json.loads(json.dumps([{k: j.get(k) for k in SUMMARY} for j in rows]))

    def save(self, job):
        with self.lock:  # every writer shares job.tmp, so writes must not overlap
            dump(self.root / job['id'] / 'job.json', job)

    def submit(self, data):
        recipe = adapters.validate(data)
        with self.lock:
            if self.stopping:
                raise ValueError('server is stopping')
            if self.preparing:
                raise ValueError('a vpype copy is being made; render again when it finishes')
            if sum(j['status'] in ACTIVE for j in self.jobs.values()) >= 8:
                raise ValueError('queue is full (8 jobs); wait for a job to finish')
            job_id = uuid.uuid4().hex
            directory = self.root / job_id
            directory.mkdir()
            try:
                cmd, cwd, output = adapters.plan(recipe, directory, self.config)
            except Exception:
                directory.rmdir()
                raise
            job = dict(id=job_id, created=datetime.now(timezone.utc).isoformat(), status='queued',
                       recipe=recipe, command=cmd, cwd=str(cwd), output=str(output), directory=str(directory),
                       files=[], error=None, returncode=None)
            dump(directory / 'recipe.json', recipe)
            self.jobs[job_id] = job
            self.save(job)
            self.executor.submit(self.run, job_id)
            return self.snapshot(job_id)

    def provenance(self, job):
        gen = job['recipe']['generator']
        paths = ([adapters.ROOT / 'studies/driftless-plates/cli.js', adapters.ROOT / 'studies/driftless-plates/engine.js']
                 if gen == 'driftless' else
                 list((adapters.ROOT / 'lib/farm_objects').glob('*.py')) +
                 [adapters.ROOT / 'studies/farm-remnants/build.py', adapters.ROOT / 'studies/infernal-landscape/geometry.py',
                  adapters.ROOT / 'studies/infernal-landscape/vendor/raycore.py'])
        if gen == 'infernal':
            workspace = self.root / job['id'] / 'workspace'
            return {str(p.relative_to(workspace)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in workspace.rglob('*') if p.is_file() and p.suffix in {'.py', '.js', '.cjs', '.json'}}
        return {str(p.relative_to(adapters.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

    def run(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            if job['status'] != 'queued':
                return
            job['status'] = 'running'
            self.current = job_id
            self.save(job)
        directory = self.root / job_id
        try:
            if job['recipe']['generator'] == 'infernal':
                adapters.isolated_sources(directory / 'workspace')
            job['source_sha256'] = self.provenance(job)
            self.save(job)
            Path(job['output']).mkdir(parents=True, exist_ok=True)
            env = adapters.environment(self.config)
            with (directory / 'job.log').open('wb') as log:
                log.write(('argv: ' + json.dumps(job['command']) + '\n').encode()); log.flush()
                with self.lock:
                    if job['status'] == 'cancelled':
                        return
                    self.process = subprocess.Popen(job['command'], cwd=job['cwd'], env=env,
                                                    stdout=log, stderr=subprocess.STDOUT,
                                                    start_new_session=(os.name != 'nt'))
                    # Recorded so a restart after a hard stop can find and stop this process.
                    job['pid'] = self.process.pid
                    self.save(job)
                try:
                    code = self.process.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    self.kill()
                    self.process.wait()
                    raise RuntimeError(f'Job exceeded {self.timeout}s timeout')
            with self.lock:
                job['returncode'] = code
                if job['status'] != 'cancelled':
                    job['status'] = 'succeeded' if code == 0 else 'failed'
                    if code:
                        job['error'] = f'Process exited {code}; inspect job and stage logs'
        except Exception as exc:
            with self.lock:
                if job['status'] != 'cancelled':
                    job.update(status='failed', error=str(exc))
        finally:
            with self.lock:
                self.process = None
                self.current = None
                job['files'] = self.files(job_id)
                self.save(job)

    def files(self, job_id):
        directory = self.root / job_id
        job = self.jobs[job_id]
        # Expose artifacts and stage logs, never copied source/environment files.
        paths = [directory / 'recipe.json', directory / 'job.log']
        output = Path(job['output'])
        if output.exists():
            paths += sorted(p for p in output.rglob('*') if p.is_file() and p.suffix in
                            {'.svg', '.png', '.jpg', '.json', '.obj', '.blend', '.log'})
        return [dict(path=str(p.relative_to(directory)), size=p.stat().st_size) for p in paths if p.exists()]

    def artifact(self, job_id, relative):
        if not isinstance(relative, str):
            raise ValueError('file must be a relative artifact path')
        with self.lock:
            allowed = {f['path'] for f in self.files(job_id)}
        if relative not in allowed:
            raise ValueError('not a job artifact')
        return contained(self.root / job_id, relative)

    def kill(self):
        if self.process and self.process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(self.process.pid), '/T', '/F'], capture_output=True)
            else:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            if job['status'] in ACTIVE:
                job['status'] = 'cancelled'
                if self.current == job_id:
                    self.kill()
                self.save(job)
            return self.snapshot(job_id)

    def prepare(self, job_id, relative):
        """Explicit optional vpype pass; the original is immutable. Needs an idle queue.

        The lock covers only the checks and the bookkeeping, so status, logs and previews keep
        answering while vpype runs; new renders are refused until it finishes.
        """
        with self.lock:
            if self.stopping:
                raise ValueError('server is stopping')
            if self.preparing:
                raise ValueError('a vpype copy is already being made; wait for it to finish')
            if any(j['status'] in ACTIVE for j in self.jobs.values()):
                raise ValueError('wait for the render queue to finish before preparing an export')
            job = self.jobs[job_id]
            if job['status'] != 'succeeded':
                raise ValueError('prepare requires a successful render')
            source = self.artifact(job_id, relative)
            if source.suffix != '.svg' or source.name.endswith('.vpype.svg'):
                raise ValueError('select an original SVG')
            executable = shutil.which(self.config['vpype'])
            if not executable:
                raise ValueError('vpype is unavailable; install it separately or set WORKBENCH_VPYPE')
            dest = source.with_name(source.stem + '.vpype.svg')
            if dest.exists():
                raise ValueError('prepared copy already exists')
            self.preparing = job_id
        partial = dest.with_name(dest.name + '.part')
        log = source.with_name(source.stem + '.vpype.log')
        try:
            layers = vpype_layers(source)
            merges = merged_layers(layers)
            # Path order only. --no-crop keeps lines past the sheet edge, as the original has them;
            # the layer order vpype writes (by number) is put back to the original's afterwards.
            cmd = [executable, 'read', '--no-crop', str(source), 'linesort',
                   'write', '--format', 'svg', '--dont-set-date', str(partial)]
            with log.open('wb') as stream:
                stream.write(('argv: ' + json.dumps(cmd) + '\n').encode()); stream.flush()
                with self.lock:
                    if self.stopping:
                        raise ValueError('server is stopping')
                    self.prepare_process = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT)
                try:
                    code = self.prepare_process.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    self.prepare_process.kill(); self.prepare_process.wait()
                    raise ValueError('vpype took longer than 10 minutes')
                if code:
                    raise ValueError(f'vpype exited {code}; see {log.name}')
                moved = restore_layer_order(partial, [number for _, number, _ in layers], dest)
                order = ', '.join(name for name, _, _ in layers)
                stream.write(''.join(note + '\n' for note in merges).encode())
                stream.write((f'layer order: {order}' + (' (restored after vpype)' if moved else '') + '\n').encode())
        finally:
            partial.unlink(missing_ok=True)
            with self.lock:
                self.preparing = None
                self.prepare_process = None
                job['files'] = self.files(job_id)
                self.save(job)
        return self.snapshot(job_id)

    def close(self):
        with self.lock:
            self.stopping = True
            for job_id in self.jobs:
                self.cancel(job_id)
            if self.prepare_process and self.prepare_process.poll() is None:
                self.prepare_process.kill()
        self.executor.shutdown(wait=True)


def handler(jobs, token, port, instance=None):
    # Changes with every server start; the page compares it on each poll and fetches the new
    # session token when it changes, instead of failing every action until it is reloaded.
    instance = instance or secrets.token_hex(8)

    class Handler(BaseHTTPRequestHandler):
        def send(self, data, status=200, kind='application/json', attachment=None):
            raw = data if isinstance(data, bytes) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Workbench-Instance', instance)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'")
            if attachment:
                self.send_header('Content-Disposition', f'attachment; filename="{attachment}"')
            self.end_headers()
            self.wfile.write(raw)

        def send_file(self, file, download=False):
            self.send_response(200)
            self.send_header('Content-Type', mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
            self.send_header('Content-Length', str(file.stat().st_size))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; sandbox")
            self.send_header('Cache-Control', 'no-store')
            if download:
                self.send_header('Content-Disposition', f'attachment; filename="{file.name}"')
            self.end_headers()
            with file.open('rb') as stream:
                shutil.copyfileobj(stream, self.wfile)

        def allowed(self, write=False):
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
            host = self.headers.get('Host')
            if host not in hosts:
                self.send({'error': 'invalid Host'}, 403); return False
            if write and (self.headers.get('X-Workbench-Token') != token or
                          self.headers.get('Origin') != 'http://' + host):
                self.send({'error': 'invalid local origin or session token'}, 403); return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            try:
                url = urlsplit(self.path)
                parts = unquote(url.path).strip('/').split('/')
                if url.path == '/api/config':
                    return self.send(dict(token=token, instance=instance, output_root=str(jobs.root),
                                          runtimes={k: shutil.which(v) if v else None for k, v in jobs.config.items()}))
                if url.path == '/api/jobs':
                    return self.send(jobs.summaries())
                if len(parts) >= 3 and parts[:2] == ['api', 'jobs']:
                    job_id = parts[2]
                    if len(parts) == 3:
                        job = jobs.snapshot(job_id)
                        job['files'] = jobs.files(job_id)
                        return self.send(job)
                    if parts[3] == 'log':
                        file = jobs.root / job_id / 'job.log'
                        jobs.snapshot(job_id)
                        data = b''
                        if file.exists():
                            with file.open('rb') as stream:
                                stream.seek(max(0, file.stat().st_size - 65536)); data = stream.read()
                        return self.send(data, kind='text/plain; charset=utf-8')
                    if parts[3] == 'files':
                        file = jobs.artifact(job_id, '/'.join(parts[4:]))
                        return self.send_file(file, download=url.query == 'download')
                if url.path in STATIC_FILES:
                    name, kind = STATIC_FILES[url.path]
                    return self.send((STATIC / name).read_bytes(), kind=kind)
                self.send({'error': 'not found'}, 404)
            except (KeyError, ValueError, FileNotFoundError) as exc:
                self.send({'error': str(exc)}, 404)

        def do_POST(self):
            if not self.allowed(True):
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    raise ValueError('request must be 1–16384 bytes')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('request must be an object')
                parts = urlsplit(self.path).path.strip('/').split('/')
                if parts == ['api', 'jobs']:
                    return self.send(jobs.submit(data), 202)
                if len(parts) == 4 and parts[:2] == ['api', 'jobs']:
                    if parts[3] == 'cancel':
                        return self.send(jobs.cancel(parts[2]))
                    if parts[3] == 'prepare':
                        return self.send(jobs.prepare(parts[2], data.get('file', '')))
                self.send({'error': 'not found'}, 404)
            except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
                self.send({'error': str(exc)}, 400)

        def log_message(self, *_args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--output-root', type=Path, default=adapters.ROOT / '.workbench/jobs')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    jobs = Jobs(args.output_root, timeout=args.timeout)
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(jobs, token, args.port))
    server.daemon_threads = True

    # Renders run in their own process group, so closing the terminal (SIGHUP) or `kill`
    # (SIGTERM) would otherwise end only the server and leave the render running unwatched.
    # Treat both like Ctrl-C: stop the active job and close the queue.
    def stop(*_):
        raise KeyboardInterrupt
    stops = [getattr(signal, name) for name in ('SIGTERM', 'SIGHUP', 'SIGBREAK') if hasattr(signal, name)]
    for sig in stops:
        signal.signal(sig, stop)
    print(f'Workbench: http://127.0.0.1:{args.port}  |  outputs: {jobs.root}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for sig in stops:
            signal.signal(sig, signal.SIG_IGN)
        server.server_close(); jobs.close()


if __name__ == '__main__':
    main()
