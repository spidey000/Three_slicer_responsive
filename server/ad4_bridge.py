"""Local same-origin bridge for FFAD4Manager and the built Three Slicer UI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
BASE = '/Three_slicer_responsive/'
CLI = os.environ.get('AD4_CLI', 'ffadv4manager')
HOST = os.environ.get('AD4_HOST')  # Otherwise use ffadv4manager config set --host.
MAX_GCODE = 100 * 1024 * 1024


def command(*args, timeout=30):
    argv = [CLI]
    if HOST:
        argv += ['--host', HOST]
    argv += list(args)
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[:1000] or f'CLI exit {result.returncode}')
    return result.stdout


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def json(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == '/api/printer/status':
                return self.json(200, json.loads(command('status', '--json')))
            if path == '/api/printer/camera':
                with tempfile.TemporaryDirectory() as directory:
                    frame = Path(directory) / 'frame.jpg'
                    command('camera', 'snapshot', str(frame), timeout=25)
                    data = frame.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                return self.wfile.write(data)
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            return self.json(502, {'error': str(error)})
        if path in ('/', BASE.rstrip('/')):
            self.send_response(302)
            self.send_header('Location', BASE)
            self.end_headers()
            return
        if path.startswith(BASE):
            self.path = '/' + path[len(BASE):]
            return super().do_GET()
        self.send_error(404)

    def do_POST(self):
        path = urlsplit(self.path)
        if path.path != '/api/printer/jobs':
            return self.send_error(404)
        origin = self.headers.get('Origin')
        expected = f'http://{self.headers.get("Host", "")}'
        if origin and origin != expected:
            return self.json(403, {'error': 'Unauthorized origin'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_GCODE:
                return self.json(413, {'error': 'G-code is empty or exceeds 100 MB'})
            if not self.headers.get('Content-Type', '').startswith('text/plain'):
                return self.json(415, {'error': 'G-code must be sent as text/plain'})
            data = self.rfile.read(size)
            if len(data) != size or not data.strip():
                return self.json(400, {'error': 'Incomplete G-code'})
            start = parse_qs(path.query).get('start', ['false'])[0] == 'true'
            with tempfile.TemporaryDirectory() as directory:
                filename = Path(directory) / 'three-slicer-ad4.gcode'
                filename.write_bytes(data)
                output = command('upload', str(filename), *(['--start'] if start else []), timeout=3600)
            return self.json(200, {'remote_name': 'three-slicer-ad4.gx', 'started': start, 'detail': output[-1000:]})
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            return self.json(502, {'error': str(error)})


if __name__ == '__main__':
    if not (DIST / 'index.html').is_file():
        sys.exit('Missing dist/: run npm run build first')
    port = int(os.environ.get('AD4_WEB_PORT', '8765'))
    print(f'AD4 web: http://127.0.0.1:{port}{BASE}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
