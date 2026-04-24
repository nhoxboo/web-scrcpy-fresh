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

        def __init__(self, serial=None):
            self.started = False
            self.stopped = False
            self.serial = serial

        def scrcpy_start(self, video_callback, video_bit_rate, max_fps=None):  # noqa: ARG002
            self.started = True

        def scrcpy_stop(self):
            self.stopped = True

        def scrcpy_send_control(self, data):  # noqa: ARG002
            pass

    module.Scrcpy = Scrcpy
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
