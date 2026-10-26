"""Regression checks for the local printer manager bridge; no physical printer needed."""
import json
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from server import ad4_bridge as bridge


class BridgeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), bridge.Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=4)

    def request(self, route, obj=None, origin=None):
        url = 'http://127.0.0.1:' + str(self.port) + route
        headers = {'Origin': origin or 'http://127.0.0.1:' + str(self.port)}
        if obj is None:
            req = Request(url, headers=headers)
        else:
            headers['Content-Type'] = 'application/json'
            req = Request(url, data=json.dumps(obj).encode(), headers=headers)
        with urlopen(req, timeout=4) as response:
            return json.load(response)

    def test_safe_names_and_private_host(self):
        self.assertEqual(bridge.safe_filename('model.gcode'), 'model.gcode')
        with self.assertRaises(ValueError):
            bridge.safe_filename('../evil.gx')
        with self.assertRaises(ValueError):
            bridge.safe_filename('evil.exe')
        self.assertTrue(bridge.private_ip('192.168.1.5'))
        self.assertFalse(bridge.private_ip('8.8.8.8'))
        self.assertFalse(bridge.private_ip('127.0.0.1'))

    def test_session_endpoint_and_reject_cross_origin(self):
        self.assertIn('notifying', self.request('/api/printer/session'))
        with self.assertRaises(HTTPError) as ctx:
            self.request('/api/printer/actions', {'action': 'pause'}, 'https://untrusted.example')
        self.assertEqual(ctx.exception.code, 403)

    def test_status_and_whitelisted_action(self):
        def cmd(*args, **kwargs):
            if args == ('status', '--json'):
                return '{"machine_status":"READY","bed_current":25}'
            if args == ('pause',):
                return 'ok'
            raise AssertionError('unexpected command ' + repr(args))
        with patch.object(bridge, 'command', side_effect=cmd):
            self.assertEqual(self.request('/api/printer/status')['machine_status'], 'READY')
            self.assertEqual(self.request('/api/printer/actions', {'action': 'pause'}), {'detail': 'ok'})
        with self.assertRaises(HTTPError) as ctx:
            self.request('/api/printer/actions', {'action': 'home'})
        self.assertEqual(ctx.exception.code, 502)

    def test_remote_print_requires_listed_filename(self):
        def cmd(*args, **kwargs):
            if args == ('files', '--json'):
                return '["/data/good.gx"]'
            if args == ('print', '/data/good.gx'):
                return 'started'
            raise AssertionError(args)
        with patch.object(bridge, 'command', side_effect=cmd):
            self.assertEqual(self.request('/api/printer/actions',
                              {'action': 'print', 'file': '/data/good.gx'})['detail'], 'started')
            with self.assertRaises(HTTPError):
                self.request('/api/printer/actions',
                             {'action': 'print', 'file': '/data/other.gx'})

    def test_inspect_gcode_and_gx_metadata(self):
        with tempfile.TemporaryDirectory() as work:
            source = Path(work) / 'demo.gcode'
            source.write_text('; estimated printing time (normal mode) = 1h 12m 5s\n'
                              '; nozzle_temperature = 210\n; bed_temperature = 60\nG1 X10\n')
            self.assertEqual(bridge.inspect_upload_metadata(source),
                             {'estimated_seconds': 4325, 'hotend': 210, 'bed': 60})
            gx = Path(work) / 'demo.gx'
            gx.write_bytes(b'xgcode 1.0\n\0' + struct.pack('<4i', 0, 58, 14512, 14512)
                           + struct.pack('<iiih', 3723, 0, 0, 1)
                           + struct.pack('<8h', 200, 0, 2, 60, 55, 215, 0, 1))
            self.assertEqual(bridge.inspect_upload_metadata(gx),
                             {'estimated_seconds': 3723, 'hotend': 215, 'bed': 55})

    def test_file_details_from_local_upload_record_only(self):
        with tempfile.TemporaryDirectory() as work, \
                patch.object(bridge, 'DATA_DIR', Path(work)), \
                patch.object(bridge, 'FILE_METADATA_PATH', Path(work) / 'uploaded-files.json'), \
                patch.object(bridge, 'command', return_value='["/data/demo.gx", "/data/old.gx"]'):
            bridge.save_upload_metadata('demo.gx', {'estimated_seconds': 3600, 'hotend': 205, 'bed': 60})
            detailed = self.request('/api/printer/files?details=1')
            self.assertEqual(len(detailed), 2)
            self.assertEqual(detailed[0]['estimated_seconds'], 3600)
            self.assertIsNotNone(detailed[0]['uploaded_at'])
            self.assertIsNone(detailed[1]['estimated_seconds'])
            self.assertIsNone(detailed[1]['uploaded_at'])
            self.assertEqual(self.request('/api/printer/files'), ['/data/demo.gx', '/data/old.gx'])

    def test_saved_timelapse_mp4_gallery_range_and_delete(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work) / 'timelapses'
            folder = root / '20261026T154800-1234abcd'
            folder.mkdir(parents=True)
            video = b'\0\0\0\x18ftypisom' + b'0' * 100
            (folder / 'timelapse.mp4').write_bytes(video)
            (folder / 'session.json').write_text('{"frames": 400, "status": "complete"}')
            with patch.object(bridge.TIMELAPSES, 'root', root):
                gallery = self.request('/api/printer/timelapses')
                self.assertEqual(len(gallery), 1)
                self.assertTrue(gallery[0]['video_ready'])
                self.assertEqual(gallery[0]['frames'], 400)
                base = 'http://127.0.0.1:' + str(self.port)
                with urlopen(base + '/api/printer/timelapses/video?id=' + folder.name) as response:
                    self.assertEqual(response.headers['Content-Type'], 'video/mp4')
                    self.assertEqual(response.read(), video)
                req = Request(base + '/api/printer/timelapses/video?id=' + folder.name,
                              headers={'Range': 'bytes=1-5'})
                with urlopen(req) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.read(), video[1:6])
                    self.assertEqual(response.headers['Content-Range'], 'bytes 1-5/' + str(len(video)))
                with urlopen(base + '/api/printer/timelapses/download?id=' + folder.name) as response:
                    self.assertIn('.mp4', response.headers['Content-Disposition'])
                    self.assertEqual(response.read(), video)
                with self.assertRaises(HTTPError):
                    self.request('/api/printer/timelapses/video?id=..%2Fsecret')
                self.assertEqual(self.request('/api/printer/timelapses/delete', {'id': folder.name}),
                                 {'deleted': folder.name})
                self.assertFalse(folder.exists())

    def test_auto_timelapse_requires_ffmpeg_before_printing(self):
        with patch.object(bridge.TIMELAPSES, 'require_encoder', side_effect=RuntimeError('install ffmpeg')):
            with self.assertRaises(HTTPError) as error:
                self.request('/api/printer/actions', {
                    'action': 'print', 'file': '/data/good.gx', 'timelapse': True})
            self.assertEqual(error.exception.code, 502)

    def test_camera_live_rejects_external_urls(self):
        with patch.object(bridge, 'command', return_value='http://8.8.8.8:8080/?action=stream'):
            with self.assertRaises(HTTPError) as error:
                self.request('/api/printer/camera/live')
        self.assertEqual(error.exception.code, 502)

    def test_camera_live_proxies_mjpeg_on_private_network(self):
        class LocalCamera(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                self.end_headers()
                self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n\xff\xd8test\xff\xd9\r\n')

            def log_message(self, *args):
                pass

        camera = ThreadingHTTPServer(('127.0.0.1', 0), LocalCamera)
        camera_thread = threading.Thread(target=camera.serve_forever, daemon=True)
        camera_thread.start()
        try:
            url = 'http://127.0.0.1:' + str(camera.server_address[1]) + '/?action=stream'
            with patch.object(bridge, 'command', return_value=url), \
                    patch.object(bridge, 'private_ip', return_value=True):
                with urlopen('http://127.0.0.1:' + str(self.port) + '/api/printer/camera/live') as response:
                    self.assertIn('multipart/x-mixed-replace', response.headers['Content-Type'])
                    self.assertIn(b'\xff\xd8test\xff\xd9', response.read())
        finally:
            camera.shutdown()
            camera.server_close()
            camera_thread.join(timeout=3)

    def test_discovery_and_selection(self):
        with patch.object(bridge, 'command', return_value='[{"name":"AD4","ip":"192.168.1.42","port":8899}]'):
            devices = self.request('/api/printer/discover')
        self.assertEqual(len(devices), 1)
        selection = self.request('/api/printer/selection', {'host': '192.168.1.42'})
        self.assertEqual(selection['host'], '192.168.1.42')
        self.assertIn('--host', bridge.cli_argv('status'))
        with self.assertRaises(HTTPError):
            self.request('/api/printer/selection', {'host': '192.168.1.99'})


if __name__ == '__main__':
    unittest.main()
