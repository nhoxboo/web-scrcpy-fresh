"""Pytest configuration.

Mocks the ``scrcpy`` module so ``app`` can be imported without adb/Android. Also
routes auth.json and secret.key to a per-test temp directory.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


def _install_fake_scrcpy():
    module = types.ModuleType('scrcpy')

    class Scrcpy:  # noqa: D401 - test stub
        """No-op replacement for the real Scrcpy class."""

        def __init__(
            self,
            serial=None,
            display_id=None,
            max_size=None,
            new_display=None,
            enable_audio=False,
            audio_codec='aac',
        ):
            self.started = False
            self.stopped = False
            self.serial = serial
            self.display_id = display_id
            self.max_size = max_size
            self.new_display = new_display
            self.enable_audio = bool(enable_audio)
            self.audio_codec = audio_codec
            self.audio_callback = None

        def scrcpy_start(
            self,
            video_callback,
            video_bit_rate,
            max_fps=None,
            audio_callback=None,
        ):  # noqa: ARG002
            self.started = True
            self.audio_callback = audio_callback

        def scrcpy_stop(self):
            self.stopped = True

        def scrcpy_send_control(self, data):  # noqa: ARG002
            pass

    # Tests can monkeypatch list_adb_devices to inject fixtures.
    def list_adb_devices(adb_path=None, timeout=5.0):  # noqa: ARG001
        return []

    def is_valid_serial(serial: str) -> bool:
        if not serial or len(serial) > 64:
            return False
        return all(c.isalnum() or c in '-_.:' for c in serial)

    # Stubs for adb_install / adb_push so the app module imports cleanly.
    # Tests can monkeypatch these with custom behaviour.
    def adb_install(apk_path, serial=None, reinstall=True, timeout=300.0, adb_path=None):  # noqa: ARG001
        return True, 'Success'

    def adb_push(src_path, dest_path, serial=None, timeout=600.0, adb_path=None):  # noqa: ARG001
        return True, '1 file pushed'

    def adb_pair(host, port, code, timeout=30.0, adb_path=None):  # noqa: ARG001
        return True, f'Successfully paired to {host}:{port}'

    def adb_connect(host, port, timeout=15.0, adb_path=None):  # noqa: ARG001
        return True, f'connected to {host}:{port}'

    def adb_disconnect(host=None, port=None, timeout=10.0, adb_path=None):  # noqa: ARG001
        return True, 'disconnected'

    def adb_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        return True, 'ok'

    def adb_simple(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        return True, 'ok'

    def is_valid_host(host: str) -> bool:
        if not host or len(host) > 253:
            return False
        return all(c.isalnum() or c in '.-' for c in host)

    def is_valid_port(port) -> bool:
        try:
            p = int(port)
        except (TypeError, ValueError):
            return False
        return 1 <= p <= 65535

    def is_valid_new_display(spec: str) -> bool:
        if not spec:
            return False
        if spec.startswith('/'):
            return spec[1:].isdigit() and 1 <= int(spec[1:]) <= 1000
        if spec.count('/') > 1:
            return False
        head, _, dpi = spec.partition('/')
        if dpi and (not dpi.isdigit() or not (1 <= int(dpi) <= 1000)):
            return False
        if head.count('x') != 1:
            return False
        w, _, h = head.partition('x')
        if not w.isdigit() or not h.isdigit():
            return False
        return 100 <= int(w) <= 7680 and 100 <= int(h) <= 7680

    module.Scrcpy = Scrcpy
    module.list_adb_devices = list_adb_devices
    module.is_valid_serial = is_valid_serial
    module.adb_install = adb_install
    module.adb_push = adb_push
    module.adb_pair = adb_pair
    module.adb_connect = adb_connect
    module.adb_disconnect = adb_disconnect
    module.adb_shell = adb_shell
    module.adb_simple = adb_simple
    module.is_valid_host = is_valid_host
    module.is_valid_port = is_valid_port
    module.is_valid_new_display = is_valid_new_display
    sys.modules['scrcpy'] = module


_install_fake_scrcpy()


@pytest.fixture
def app(tmp_path: Path, monkeypatch):
    # Redirect auth.json / secret.key to the tmp dir so each test is isolated.
    monkeypatch.setenv('FLASK_SECRET_KEY', 'test-' + 'x' * 40)
    monkeypatch.chdir(tmp_path)

    if 'app' in sys.modules:
        del sys.modules['app']
    import app as app_module  # noqa: WPS433 - intentional late import

    app_module.AUTH_FILE = str(tmp_path / 'auth.json')
    app_module.SECRET_FILE = str(tmp_path / 'secret.key')
    app_module.LOGIN_MAX_ATTEMPTS = 3
    app_module.LOGIN_WINDOW_SECONDS = 60
    app_module._login_attempts.clear()
    app_module.app.config['TESTING'] = True
    app_module.app.config['WTF_CSRF_ENABLED'] = False  # we test our own CSRF
    return app_module


@pytest.fixture
def client(app):
    return app.app.test_client()


def _csrf_token(html: bytes) -> str:
    import re

    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    assert m, 'csrf_token not found in response'
    return m.group(1).decode()


@pytest.fixture
def csrf(client):
    resp = client.get('/login')
    assert resp.status_code == 200
    return _csrf_token(resp.data)


@pytest.fixture
def default_credentials(app):
    # Touch _load_auth() to create the default credentials file.
    app._load_auth()
    return {'username': app.DEFAULT_USERNAME, 'password': app.DEFAULT_PASSWORD}
