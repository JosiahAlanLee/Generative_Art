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
import secrets
import shutil
import signal
import subprocess
import threading
from urllib.parse import unquote, urlsplit
import uuid

from . import adapters

STATIC = Path(__file__).parent / 'static'
ACTIVE = {'queued', 'running'}


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
        for file in self.root.glob('*/job.json'):
            job = json.loads(file.read_text())
            if job['status'] in ACTIVE:
                job.update(status='interrupted', error='Server stopped; submit the saved recipe to retry')
                dump(file, job)
            self.jobs[job['id']] = job

    def snapshot(self, job_id=None):
        with self.lock:
            value = self.jobs[job_id] if job_id else sorted(self.jobs.values(), key=lambda j: j['created'], reverse=True)
            return json.loads(json.dumps(value))

    def save(self, job):
        dump(self.root / job['id'] / 'job.json', job)

    def submit(self, data):
        recipe = adapters.validate(data)
        with self.lock:
            if self.stopping:
                raise ValueError('server is stopping')
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
        """Explicit optional vpype pass; original is immutable. Queue must be idle."""
        with self.lock:
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
            # linesort only: no joining/simplification which could change marks.
            cmd = [executable, 'read', str(source), 'linesort', 'write', str(dest)]
            log = source.with_name(source.stem + '.vpype.log')
            try:
                with log.open('wb') as stream:
                    stream.write(('argv: ' + json.dumps(cmd) + '\n').encode()); stream.flush()
                    subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT, timeout=120, check=True)
            except Exception:
                dest.unlink(missing_ok=True)
                job['files'] = self.files(job_id); self.save(job)
                raise
            job['files'] = self.files(job_id)
            self.save(job)
            return self.snapshot(job_id)

    def close(self):
        with self.lock:
            self.stopping = True
            for job_id in self.jobs:
                self.cancel(job_id)
        self.executor.shutdown(wait=True)


def handler(jobs, token, port):
    class Handler(BaseHTTPRequestHandler):
        def send(self, data, status=200, kind='application/json', attachment=None):
            raw = data if isinstance(data, bytes) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
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
                    return self.send(dict(token=token, runtimes={k: shutil.which(v) if v else None for k, v in jobs.config.items()}, output_root=str(jobs.root)))
                if url.path == '/api/jobs':
                    return self.send(jobs.snapshot())
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
                static = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}.get(url.path)
                if static:
                    file = STATIC / static
                    return self.send(file.read_bytes(), kind=mimetypes.guess_type(file.name)[0])
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
    print(f'Workbench: http://127.0.0.1:{args.port}  |  outputs: {jobs.root}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close(); jobs.close()


if __name__ == '__main__':
    main()
