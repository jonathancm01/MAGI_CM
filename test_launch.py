import io
import json
import os
from pathlib import Path
import socket
import tempfile
from threading import Thread
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.request import urlopen

if os.name == 'nt':
    import msvcrt

from flask import Flask
from werkzeug.serving import make_server

import launch
from harness import DEFAULT_CONFIG
from workspaces import WorkspaceStore

_launcher_directory = tempfile.TemporaryDirectory()
with patch('workspaces.WorkspaceStore', return_value=WorkspaceStore(Path(_launcher_directory.name) / '.magi', DEFAULT_CONFIG)):
    import main


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.lifetime = launch.BrowserLifetime(clock=lambda: self.now)
        self.dash = SimpleNamespace(server=Flask(__name__), index_string='<html><head></head><body></body></html>')
        self.dash.server.before_request(main.local_requests_only)
        launch.install_lifecycle(self.dash, self.lifetime)
        self.client = self.dash.server.test_client()

    def test_last_tab_closes_after_grace_and_background_tabs_stay_alive(self):
        first, second = self.lifetime.connect(), self.lifetime.connect()
        self.lifetime.disconnect(first)
        self.now = 3600
        self.assertFalse(self.lifetime.expired())
        self.lifetime.disconnect(second)
        self.now += 7
        self.assertFalse(self.lifetime.expired())
        self.now += 1
        self.assertTrue(self.lifetime.expired())

    def test_reload_reconnects_without_shutting_down(self):
        first = self.lifetime.connect()
        self.lifetime.disconnect(first)
        self.now = 7
        second = self.lifetime.connect()
        self.now = 100
        self.assertFalse(self.lifetime.expired())
        self.lifetime.disconnect(first)  # a stale disconnect must not affect the new connection
        self.assertEqual(self.lifetime.clients, {second})
        self.lifetime.closed.set()
        with self.assertRaises(RuntimeError):
            self.lifetime.connect()

    def test_failed_browser_start_has_a_bounded_startup_timeout(self):
        self.now = 44
        self.assertFalse(self.lifetime.expired())
        self.now = 45
        self.assertTrue(self.lifetime.expired())

    def test_stream_disconnect_releases_lease_and_requires_current_instance(self):
        for instance in ('', 'stale-instance', 'ñ'):
            self.assertEqual(self.client.get('/_magi/browser', query_string={'instance': instance}).status_code, 403)
        response = self.client.get('/_magi/browser', query_string={'instance': self.lifetime.instance}, buffered=False)
        self.assertEqual(response.mimetype, 'text/event-stream')
        self.assertEqual(self.client.get('/_magi/health').json['clients'], 1)
        response.close()
        self.assertEqual(self.client.get('/_magi/health').json['clients'], 0)
        self.assertIn(f'content="{self.lifetime.instance}"', self.dash.index_string)

    def test_control_routes_keep_loopback_and_origin_boundaries(self):
        self.assertEqual(self.client.get('/_magi/health', base_url='http://evil.example').status_code, 403)
        self.assertEqual(self.client.get('/_magi/browser', query_string={'instance': self.lifetime.instance},
                                         headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.get('/_magi/health').headers['Cache-Control'], 'no-store')
        self.lifetime.closed.set()
        self.assertEqual(self.client.post('/_dash-update-component', json={}).status_code, 503)
        self.assertTrue(self.client.get('/_magi/health').json['closing'])

    def test_second_launch_only_opens_the_matching_running_app(self):
        status = {'application': 'MAGI_CM', 'project': launch.PROJECT, 'mode': 'launcher', 'closing': False}
        with patch('launch.urlopen', return_value=io.BytesIO(json.dumps(status).encode())), patch('launch.webbrowser.open', return_value=True) as browser:
            self.assertTrue(launch.open_existing())
            browser.assert_called_once_with(launch.URL + '/', new=2)
        for changed in ({'project': 'another-project'}, {'closing': True}, {'application': 'unrelated-app'}):
            with patch('launch.urlopen', return_value=io.BytesIO(json.dumps({**status, **changed}).encode())), patch('launch.webbrowser.open') as browser:
                self.assertFalse(launch.open_existing())
                browser.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Windows launcher lock')
    def test_second_process_reuses_lock_owner_without_importing_the_app(self):
        with tempfile.TemporaryDirectory() as folder, patch('launch.ROOT', Path(folder)), patch('launch.open_existing', return_value=True) as existing:
            directory = Path(folder) / '.magi'
            directory.mkdir()
            with (directory / 'launcher.lock').open('w+b') as lock:
                lock.write(b'0')
                lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                with patch('launch.make_server') as server:
                    launch.run()
                server.assert_not_called()
                existing.assert_called_once()

    @unittest.skipUnless(os.name == 'nt', 'Windows launcher')
    def test_an_occupied_port_is_not_killed_or_taken_over(self):
        with tempfile.TemporaryDirectory() as folder, patch('launch.ROOT', Path(folder)), patch('launch.socket.socket') as probe:
            probe.return_value.__enter__.return_value.connect_ex.return_value = 0
            with patch('launch.open_existing', return_value=False), patch('launch.make_server') as server:
                with self.assertRaisesRegex(RuntimeError, 'puerto 8050'):
                    launch.run()
            server.assert_not_called()

    def test_real_sse_connection_closing_stops_server_and_releases_port(self):
        lifetime = launch.BrowserLifetime(grace=0.1, startup_timeout=10)
        dash = SimpleNamespace(server=Flask('magi-sse-integration'), index_string='<head></head>')
        launch.install_lifecycle(dash, lifetime)
        server = make_server('127.0.0.1', 0, dash.server, threaded=True)
        port = server.server_port

        def serve():
            try:
                server.serve_forever(poll_interval=0.05)
            finally:
                server.server_close()

        thread = Thread(target=serve, daemon=True)
        thread.start()
        watcher = Thread(target=launch.stop_when_closed, args=(server, lifetime), daemon=True)
        watcher.start()
        try:
            response = urlopen(f'http://127.0.0.1:{port}/_magi/browser?instance={lifetime.instance}', timeout=3)
            self.assertTrue(response.readline().startswith(b'retry:'))
            response.close()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive(), 'Server did not stop after its last browser connection closed')
            with socket.socket() as probe:
                self.assertNotEqual(probe.connect_ex(('127.0.0.1', port)), 0)
        finally:
            lifetime.closed.set()
            if thread.is_alive():
                server.shutdown()
            thread.join(timeout=3)
            watcher.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
