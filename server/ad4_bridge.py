"""Same-origin, loopback-only FFAD4Manager bridge for ThreeSlicer.

The GitHub Pages demo has no printer API. Protected remote access must use
Cloudflare Access JWT verification at this loopback-only origin.
"""
import atexit
from datetime import datetime, timezone
import http.client
import secrets
import struct
import zipfile
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

if __package__:
    from .cloudflare_access import load_access_config, verify_access_jwt, _jwks_client
else:
    from cloudflare_access import load_access_config, verify_access_jwt, _jwks_client

ACCESS_CONFIG = load_access_config(os.environ)

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
BASE = '/Three_slicer_responsive/'
CLI = os.environ.get('AD4_CLI', 'ffadv4manager')
HOST = os.environ.get('AD4_HOST')
MAX_GCODE = 100 * 1024 * 1024
FILE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,119}\Z')
PROFILE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,63}\Z')
STATE_LOCK = threading.RLock()
SELECTED = {'host': None, 'profile': None}
DISCOVERED = {}
WORKERS = {'timelapse': None, 'notifications': None}
TIMELAPSE_DIR = None
DATA_DIR = Path(os.environ.get('AD4_DATA_DIR', Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'three-slicer-ad4'))
TIMELAPSE_ROOT = DATA_DIR / 'timelapses'
FILE_METADATA_PATH = DATA_DIR / 'uploaded-files.json'
TIMELAPSE_ID = re.compile(r'\d{8}T\d{6}-[0-9a-f]{8}\Z')



def private_ip(value):
    try:
        ip = ipaddress.ip_address(value)
        return (ip.version == 4 and ip.is_private and not ip.is_loopback
                and not ip.is_link_local and not ip.is_multicast)
    except ValueError:
        return False


def cli_argv(*args, selected=True):
    argv = [CLI]
    if selected:
        with STATE_LOCK:
            profile, host = SELECTED['profile'], SELECTED['host']
        if profile:
            argv += ['--profile', profile]
        elif host or HOST:
            argv += ['--host', host or HOST]
    argv.extend(args)
    return argv


def command(*args, timeout=30, selected=True):
    result = subprocess.run(cli_argv(*args, selected=selected), capture_output=True,
                            text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[:1000]
                           or 'CLI exit ' + str(result.returncode))
    return result.stdout


def safe_filename(name):
    if not isinstance(name, str) or not FILE_NAME.fullmatch(name) or name in ('.', '..'):
        raise ValueError('Nombre de archivo no válido')
    if Path(name).suffix.lower() not in ('.gx', '.gcode', '.gco', '.g'):
        raise ValueError('Solo se admiten archivos .gx, .gcode, .gco y .g')
    return name


def worker_running(name):
    with STATE_LOCK:
        worker = WORKERS[name]
    return bool(worker and worker.poll() is None)


def timelapse_state():
    with STATE_LOCK:
        folder = TIMELAPSE_DIR
    return {'running': worker_running('timelapse'),
            'frames': len(list(folder.glob('frame-*.jpg'))) if folder and folder.is_dir() else 0}


def _metadata_scope():
    with STATE_LOCK:
        profile, host = SELECTED['profile'], SELECTED['host']
    return ('profile:' + profile) if profile else ('host:' + (host or HOST or 'default'))


def _read_file_metadata():
    try:
        content = json.loads(FILE_METADATA_PATH.read_text(encoding='utf-8'))
        return content if isinstance(content, dict) else {}
    except (OSError, ValueError):
        return {}


def _print_seconds(value):
    value = value.strip().lower()
    if value.isdecimal():
        return int(value)
    parts = re.findall(r'(\d+)\s*([hms])\b', value)
    if not parts:
        return None
    units = {'h': 3600, 'm': 60, 's': 1}
    return sum(int(amount) * units[unit] for amount, unit in parts)


def inspect_upload_metadata(file):
    """Read recognized source-file metadata, never claim the printer reported it."""
    with file.open('rb') as handle:
        prefix = handle.read(1024 * 1024)
    metadata = {'estimated_seconds': None, 'hotend': None, 'bed': None}
    if prefix.startswith(b'xgcode 1.0\n\0') and len(prefix) >= 58:
        seconds = struct.unpack_from('<i', prefix, 28)[0]
        gx_values = struct.unpack_from('<8h', prefix, 42)
        if 1 < seconds < 30 * 86400:
            metadata['estimated_seconds'] = seconds
        if 0 < gx_values[5] <= 350:
            metadata['hotend'] = gx_values[5]
        if 0 < gx_values[4] <= 150:
            metadata['bed'] = gx_values[4]
        return metadata
    if b'\0' in prefix:
        return metadata
    body = prefix.decode('utf-8', errors='replace')
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(';'):
            comment = stripped[1:].strip()
            for pattern in (r'estimated printing time \(normal mode\)\s*=\s*(.+)',
                            r'(?:print time|estimated_print_time)\s*=\s*(.+)',
                            r'TIME\s*:\s*(\d+)'):
                match = re.fullmatch(pattern, comment, flags=re.I)
                if match:
                    seconds = _print_seconds(match.group(1))
                    if seconds and 1 < seconds < 30 * 86400:
                        metadata['estimated_seconds'] = seconds
            for key, pattern in (('hotend', r'(?:nozzle_temperature|first_layer_temperature)\s*=\s*(\d+)'),
                                 ('bed', r'(?:bed_temperature|first_layer_bed_temperature)\s*=\s*(\d+)')):
                match = re.fullmatch(pattern, comment, flags=re.I)
                if match and metadata[key] is None:
                    value = int(match.group(1))
                    if 0 < value <= (350 if key == 'hotend' else 150):
                        metadata[key] = value
        else:
            match = re.match(r'^M(?:104|109|140|190)\b.*?\bS(\d+(?:\.\d+)?)', stripped, flags=re.I)
            if match:
                key = 'hotend' if stripped.upper().startswith(('M104', 'M109')) else 'bed'
                if metadata[key] is None:
                    value = round(float(match.group(1)))
                    if 0 < value <= (350 if key == 'hotend' else 150):
                        metadata[key] = value
        if all(metadata.values()):
            break
    return metadata


def save_upload_metadata(filename, metadata):
    scope = _metadata_scope()
    with STATE_LOCK:
        values = _read_file_metadata()
        values.setdefault(scope, {})[filename] = {
            **metadata, 'uploaded_at': datetime.now(timezone.utc).isoformat()
        }
        DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = FILE_METADATA_PATH.with_suffix('.tmp')
        temporary.write_text(json.dumps(values, ensure_ascii=False), encoding='utf-8')
        os.replace(temporary, FILE_METADATA_PATH)


def printer_file_details():
    names = json.loads(command('files', '--json'))
    if not isinstance(names, list):
        raise ValueError('Invalid printer file listing')
    metadata = _read_file_metadata().get(_metadata_scope(), {})
    result = []
    for name in names:
        if not isinstance(name, str):
            continue
        fields = metadata.get(name.rsplit('/', 1)[-1], {})
        result.append({'path': name, 'name': name.rsplit('/', 1)[-1],
                       'estimated_seconds': fields.get('estimated_seconds'),
                       'hotend': fields.get('hotend'), 'bed': fields.get('bed'),
                       'uploaded_at': fields.get('uploaded_at')})
    return result


def timelapse_folder(value):
    if not isinstance(value, str) or not TIMELAPSE_ID.fullmatch(value):
        raise ValueError('Invalid timelapse identifier')
    folder = TIMELAPSE_ROOT / value
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError('Timelapse not found')
    return folder


def timelapse_frames(folder):
    return sorted(f for f in folder.glob('frame-*.jpg') if f.is_file() and not f.is_symlink())


def list_timelapses():
    if not TIMELAPSE_ROOT.is_dir():
        return []
    with STATE_LOCK:
        active = TIMELAPSE_DIR
    records = []
    for folder in TIMELAPSE_ROOT.iterdir():
        if not folder.is_dir() or folder.is_symlink() or not TIMELAPSE_ID.fullmatch(folder.name):
            continue
        frames = timelapse_frames(folder)
        records.append({'id': folder.name, 'created_at': datetime.fromtimestamp(
            folder.stat().st_mtime, timezone.utc).isoformat(),
            'frames': len(frames), 'running': folder == active and worker_running('timelapse')})
    return sorted(records, key=lambda item: item['id'], reverse=True)


def cleanup():
    with STATE_LOCK:
        workers = list(WORKERS.values())
        folder = TIMELAPSE_DIR
    for worker in workers:
        if worker and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=3)
            except subprocess.TimeoutExpired:
                worker.kill()
    # Captures stay available until explicitly deleted from the gallery.


atexit.register(cleanup)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def picture(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def download_timelapse(self, folder):
        with tempfile.TemporaryFile() as output:
            with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
                for frame in timelapse_frames(folder):
                    archive.write(frame, arcname=frame.name)
                manifest = folder / 'timelapse.jsonl'
                if manifest.is_file() and not manifest.is_symlink():
                    archive.write(manifest, arcname=manifest.name)
            size = output.tell()
            output.seek(0)
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', 'attachment; filename="timelapse-' + folder.name + '.zip"')
            self.send_header('Content-Length', str(size))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            shutil.copyfileobj(output, self.wfile, length=64 * 1024)

    def camera_live(self):
        # Resolve camera on the protected bridge; never expose its private URL to the browser.
        camera_url = command('camera', 'url', timeout=10).strip()
        target = urlsplit(camera_url)
        if (target.scheme != 'http' or not private_ip(target.hostname)
                or target.username or target.password or not target.port
                or target.fragment or len(camera_url) > 2048):
            raise ValueError('Camera URL must point to a private IPv4 HTTP camera')
        connection = http.client.HTTPConnection(target.hostname, target.port, timeout=15)
        try:
            connection.request('GET', target.path + ('?' + target.query if target.query else ''),
                               headers={'Accept': 'multipart/x-mixed-replace'})
            stream = connection.getresponse()
            mime = stream.getheader('Content-Type', '')
            if stream.status != 200 or not re.fullmatch(
                    r'multipart/x-mixed-replace\s*;\s*boundary="?[-\w]+"?', mime, re.I):
                raise ValueError('The printer camera did not return an MJPEG stream')
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store, no-transform')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.close_connection = True
            while chunk := stream.read(16 * 1024):
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass  # Browser closed the feed.
        finally:
            connection.close()

    def request_authorized(self, write=False):
        host = self.headers.get('Host', '').lower()
        origin = self.headers.get('Origin')
        if ACCESS_CONFIG:
            # Access enabled: no loopback authentication bypass. Public requests
            # need the exact Host and a valid signed Access JWT for this user.
            if host != ACCESS_CONFIG['public_host']:
                return False
            if origin and origin != ACCESS_CONFIG['public_origin']:
                return False
            if write and origin != ACCESS_CONFIG['public_origin']:
                return False
            return verify_access_jwt(
                self.headers.get('Cf-Access-Jwt-Assertion'), ACCESS_CONFIG)
        # Development / local-only mode, never accessible from another host.
        if not re.fullmatch(r'(?:localhost|127\.0\.0\.1):\d{1,5}', host):
            return False
        if not write or not origin:
            return True
        return origin in ('http://' + host, 'http://localhost:5173',
                          'http://127.0.0.1:5173')

    def data(self, limit=4096):
        size = int(self.headers.get('Content-Length', '0'))
        if not 0 < size <= limit:
            raise ValueError('Tamaño de petición no válido')
        if 'application/json' not in self.headers.get('Content-Type', ''):
            raise ValueError('Se requiere JSON')
        return json.loads(self.rfile.read(size))

    def do_HEAD(self):
        # Do not leak static file metadata through an unauthenticated inherited handler.
        self.send_error(405, 'HEAD not supported')

    def do_GET(self):
        if not self.request_authorized():
            return self.json(401 if ACCESS_CONFIG else 403, {'error': 'Unauthorized request'})
        url = urlsplit(self.path)
        path = url.path
        try:
            if path == '/api/printer/session':
                with STATE_LOCK:
                    selection = dict(SELECTED)
                return self.json(200, {**selection, 'notifying': worker_running('notifications')})
            if path == '/api/printer/status':
                return self.json(200, json.loads(command('status', '--json')))
            if path == '/api/printer/discover':
                devices = json.loads(command('discover', '--json', timeout=12, selected=False))
                if not isinstance(devices, list):
                    raise ValueError('Respuesta de descubrimiento inválida')
                with STATE_LOCK:
                    DISCOVERED.clear()
                    DISCOVERED.update({d['ip']: d.get('port', 8899) for d in devices
                                       if isinstance(d, dict) and private_ip(d.get('ip'))})
                return self.json(200, devices)
            if path == '/api/printer/files':
                if parse_qs(url.query).get('details') == ['1']:
                    return self.json(200, printer_file_details())
                return self.json(200, json.loads(command('files', '--json')))
            if path == '/api/printer/profiles':
                return self.json(200, json.loads(command('profiles', 'list', selected=False)))
            if path == '/api/printer/diagnostics':
                kind = parse_qs(url.query).get('kind', ['doctor'])[0]
                if kind not in ('doctor', 'info', 'position'):
                    raise ValueError('Diagnóstico no compatible')
                output = command(kind, *(['--json'] if kind in ('info', 'position') else []), timeout=45)
                return self.json(200, {'output': json.loads(output) if kind != 'doctor' else output})
            if path == '/api/printer/timelapse':
                return self.json(200, timelapse_state())
            if path == '/api/printer/timelapses':
                return self.json(200, list_timelapses())
            if path == '/api/printer/timelapses/frame':
                query = parse_qs(url.query)
                folder = timelapse_folder(query.get('id', [''])[0])
                index = int(query.get('index', ['0'])[0])
                frames = timelapse_frames(folder)
                if not 0 <= index < len(frames):
                    raise ValueError('Invalid frame index')
                return self.picture(frames[index].read_bytes())
            if path == '/api/printer/timelapses/download':
                query = parse_qs(url.query)
                return self.download_timelapse(timelapse_folder(query.get('id', [''])[0]))
            if path == '/api/printer/camera/live':
                return self.camera_live()
            if path == '/api/printer/camera':
                with tempfile.TemporaryDirectory() as directory:
                    frame = Path(directory) / 'frame.jpg'
                    command('camera', 'snapshot', str(frame), timeout=25)
                    data = frame.read_bytes()
                return self.picture(data)
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.TimeoutExpired,
                json.JSONDecodeError) as error:
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
        global TIMELAPSE_DIR
        url = urlsplit(self.path)
        path = url.path
        if path not in ('/api/printer/jobs', '/api/printer/upload', '/api/printer/actions',
                        '/api/printer/selection', '/api/printer/profiles',
                        '/api/printer/profiles/delete', '/api/printer/timelapse',
                        '/api/printer/timelapses/delete', '/api/printer/notifications'):
            return self.send_error(404)
        if not self.request_authorized(write=True):
            return self.json(401 if ACCESS_CONFIG else 403, {'error': 'Unauthorized request'})
        try:
            if path in ('/api/printer/jobs', '/api/printer/upload'):
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= MAX_GCODE:
                    return self.json(413, {'error': 'Archivo vacío o superior a 100 MB'})
                legacy = path.endswith('/jobs')
                expected_type = 'text/plain' if legacy else 'application/octet-stream'
                if not self.headers.get('Content-Type', '').startswith(expected_type):
                    return self.json(415, {'error': 'Tipo de archivo no admitido'})
                data = self.rfile.read(size)
                if len(data) != size or not data.strip(b'\x00\r\n\t '):
                    raise ValueError('Archivo vacío o incompleto')
                name = 'three-slicer-ad4.gcode' if legacy else safe_filename(
                    unquote(parse_qs(url.query).get('name', [''])[0]))
                start = parse_qs(url.query).get('start', ['false'])[0] == 'true'
                with tempfile.TemporaryDirectory() as directory:
                    filename = Path(directory) / name
                    filename.write_bytes(data)
                    output = command('upload', str(filename), *(['--start'] if start else []), timeout=3600)
                    metadata = inspect_upload_metadata(filename)
                remote_name = name if name.lower().endswith('.gx') else str(Path(name).with_suffix('.gx'))
                save_upload_metadata(remote_name, metadata)
                return self.json(200, {'remote_name': remote_name, 'started': start, 'detail': output[-1000:]})
            body = self.data()
            if not isinstance(body, dict):
                raise ValueError('Formato JSON no válido')
            if path == '/api/printer/actions':
                action = body.get('action')
                simple = {'pause': ('pause',), 'resume': ('resume',), 'cancel': ('cancel',),
                          'fan_on': ('fan', 'on'), 'fan_off': ('fan', 'off')}
                if action == 'print':
                    filename = body.get('file')
                    listed = json.loads(command('files', '--json'))
                    if not isinstance(filename, str) or filename not in listed:
                        raise ValueError('El archivo no está en el listado actual')
                    output = command('print', filename, timeout=50)
                elif action in simple:
                    output = command(*simple[action], timeout=50)
                else:
                    raise ValueError('Acción no admitida')
                return self.json(200, {'detail': output[-1000:]})
            if path == '/api/printer/selection':
                profile = body.get('profile')
                host = body.get('host')
                if bool(profile) == bool(host):
                    raise ValueError('Selecciona un host o un perfil')
                if profile:
                    profiles = json.loads(command('profiles', 'list', selected=False))
                    if profile not in profiles:
                        raise ValueError('Perfil inexistente')
                    with STATE_LOCK:
                        SELECTED.update(profile=profile, host=None)
                else:
                    with STATE_LOCK:
                        eligible = DISCOVERED.get(host) == 8899
                    if not private_ip(host) or not eligible:
                        raise ValueError('Selecciona una impresora descubierta con puerto 8899')
                    with STATE_LOCK:
                        SELECTED.update(host=host, profile=None)
                return self.json(200, dict(SELECTED))
            if path == '/api/printer/profiles':
                name, host = body.get('name'), body.get('host')
                if not isinstance(name, str) or not PROFILE_NAME.fullmatch(name):
                    raise ValueError('Nombre de perfil inválido')
                if not isinstance(host, str) or not private_ip(host):
                    raise ValueError('Se requiere una IPv4 privada válida')
                command('profiles', 'add', name, '--host', host, selected=False)
                return self.json(200, {'added': name})
            if path == '/api/printer/profiles/delete':
                name = body.get('name')
                if not isinstance(name, str) or not PROFILE_NAME.fullmatch(name):
                    raise ValueError('Perfil inválido')
                command('profiles', 'delete', name, selected=False)
                with STATE_LOCK:
                    if SELECTED['profile'] == name:
                        SELECTED.update(host=None, profile=None)
                return self.json(200, {'deleted': name})
            if path == '/api/printer/timelapses/delete':
                folder = timelapse_folder(body.get('id'))
                with STATE_LOCK:
                    if folder == TIMELAPSE_DIR and worker_running('timelapse'):
                        raise ValueError('Stop the timelapse before deleting it')
                    shutil.rmtree(folder)
                    if folder == TIMELAPSE_DIR:
                        TIMELAPSE_DIR = None
                return self.json(200, {'deleted': folder.name})
            if path == '/api/printer/timelapse':
                action = body.get('action')
                with STATE_LOCK:
                    worker = WORKERS['timelapse']
                    if action == 'stop':
                        if worker and worker.poll() is None:
                            worker.terminate()
                        return self.json(200, timelapse_state())
                    if action != 'start':
                        raise ValueError('Acción de timelapse inválida')
                    if worker and worker.poll() is None:
                        raise ValueError('Timelapse ya activo')
                    TIMELAPSE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
                    TIMELAPSE_DIR = TIMELAPSE_ROOT / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + secrets.token_hex(4))
                    TIMELAPSE_DIR.mkdir(mode=0o700)
                    WORKERS['timelapse'] = subprocess.Popen(
                        cli_argv('camera', 'timelapse', str(TIMELAPSE_DIR),
                                 '--interval', '10', '--count', '20'),
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
                return self.json(200, timelapse_state())
            if path == '/api/printer/notifications':
                action = body.get('action')
                with STATE_LOCK:
                    worker = WORKERS['notifications']
                    if action == 'stop':
                        if worker and worker.poll() is None:
                            worker.terminate()
                    elif action == 'start':
                        if not shutil.which('notify-send'):
                            raise ValueError('notify-send no está instalado en el equipo Linux')
                        if not worker or worker.poll() is not None:
                            WORKERS['notifications'] = subprocess.Popen(
                                cli_argv('notify', '--events', 'paused,offline,printing,ready'),
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
                    else:
                        raise ValueError('Acción de notificaciones inválida')
                return self.json(200, {'running': worker_running('notifications')})
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.TimeoutExpired,
                json.JSONDecodeError) as error:
            return self.json(502, {'error': str(error)})


if __name__ == '__main__':
    if not (DIST / 'index.html').is_file():
        sys.exit('Missing dist/: run npm run build first')
    if ACCESS_CONFIG:
        _jwks_client(ACCESS_CONFIG['jwks_url'])  # Fail fast if PyJWT is missing.
        print('Cloudflare Access validation enabled: ' + ACCESS_CONFIG['public_origin'], flush=True)
    else:
        print('Local-only mode: Cloudflare authentication disabled', flush=True)
    port = int(os.environ.get('AD4_WEB_PORT', '8765'))
    print('AD4 web: http://127.0.0.1:' + str(port) + BASE, flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
