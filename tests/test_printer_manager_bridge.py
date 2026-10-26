"""Regression checks for the local printer manager bridge; no physical printer needed."""
import io
import json
from pathlib import Path
import struct
import tempfile
import zipfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

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

    def test_saved_timelapse_gallery_download_and_delete(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work) / 'timelapses'
            folder = root / '20261026T154800-1234abcd'
            folder.mkdir(parents=True)
            (folder / 'frame-20261026T154801-000000.jpg').write_bytes(b'\xff\xd8demo\xff\xd9')
            with patch.object(bridge, 'TIMELAPSE_ROOT', root), patch.object(bridge, 'TIMELAPSE_DIR', None):
                gallery = self.request('/api/printer/timelapses')
                self.assertEqual(len(gallery), 1)
                self.assertEqual(gallery[0]['frames'], 1)
                base = 'http://127.0.0.1:' + str(self.port)
                with urlopen(base + '/api/printer/timelapses/frame?id=' + folder.name + '&index=0') as img:
                    self.assertEqual(img.read(), b'\xff\xd8demo\xff\xd9')
                with urlopen(base + '/api/printer/timelapses/download?id=' + folder.name) as response:
                    with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                        self.assertEqual(len(archive.namelist()), 1)
                with self.assertRaises(HTTPError):
                    self.request('/api/printer/timelapses/frame?id=..%2Fsecret')
                self.assertEqual(self.request('/api/printer/timelapses/delete', {'id': folder.name}),
                                 {'deleted': folder.name})
                self.assertFalse(folder.exists())

    def test_camera_live_rejects_external_urls(self):
        with patch.object(bridge, 'command', return_value='http://8.8.8.8:8080/?action=stream'):
            with self.assertRaises(HTTPError) as error:
                self.request('/api/printer/camera/live')
        self.assertEqual(error.exception.code, 502)

    def test_camera_live_proxies_mjpeg_on_private_network(self):
        class FakeStream:
            status = 200
            def __init__(self):
                self.payload = io.BytesIO(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n\xff\xd8test\xff\xd9\r\n')
            def getheader(self, name, default=''):
                return 'multipart/x-mixed-replace; boundary=frame'
            def read(self, size):
                return self.payload.read(size)
        class FakeConnection:
            def __init__(self, host, port, timeout):
                self.host = host
            def request(self, *args, **kwargs):
                pass
            def getresponse(self):
                return FakeStream()
            def close(self):
                pass
        with patch.object(bridge, 'command', return_value='http://192.168.1.5:8080/?action=stream'), \
                patch.object(bridge.http.client, 'HTTPConnection', FakeConnection):
            with urlopen('http://127.0.0.1:' + str(self.port) + '/api/printer/camera/live') as response:
                self.assertIn('multipart/x-mixed-replace', response.headers['Content-Type'])
                self.assertIn(b'\xff\xd8test\xff\xd9', response.read())

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
