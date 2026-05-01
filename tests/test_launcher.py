"""Tests for the desktop-chrome app launcher.

Covers `is_valid_pkg`, `parse_launcher_apps`, `humanize_pkg`, and the two
HTTP endpoints (`/api/launcher/list` and `/api/launcher/launch`).
"""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture
def real_scrcpy():
    """Import the real scrcpy module (not the conftest stub) for unit tests
    of the pure-python launcher helpers."""
    saved_stub = sys.modules.get('scrcpy')
    saved_app = sys.modules.pop('app', None)
    sys.modules.pop('scrcpy', None)
    real = importlib.import_module('scrcpy')
    yield real
    sys.modules.pop('scrcpy', None)
    if saved_stub is not None:
        sys.modules['scrcpy'] = saved_stub
    if saved_app is not None:
        sys.modules['app'] = saved_app


def _login(client, csrf, default_credentials):
    resp = client.post(
        '/login',
        data={
            'username': default_credentials['username'],
            'password': default_credentials['password'],
            'csrf_token': csrf,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302


def _post_csrf(client):
    import re

    resp = client.get('/')
    m = re.search(rb'name="csrf-token" content="([^"]+)"', resp.data)
    assert m
    return m.group(1).decode()


# --- is_valid_pkg ------------------------------------------------------------


def test_is_valid_pkg_accepts_normal_packages(real_scrcpy):
    assert real_scrcpy.is_valid_pkg('com.android.settings')
    assert real_scrcpy.is_valid_pkg('com.spotify.music')
    assert real_scrcpy.is_valid_pkg('app.example.x_y_z')
    assert real_scrcpy.is_valid_pkg('a.b')


def test_is_valid_pkg_rejects_garbage(real_scrcpy):
    invalid = real_scrcpy.is_valid_pkg
    assert not invalid('')
    assert not invalid('com')  # no dot
    assert not invalid('com.')  # trailing dot
    assert not invalid('.com.app')  # leading dot
    assert not invalid('com..app')  # empty segment
    assert not invalid('com.app;rm -rf')
    assert not invalid('com.app/MainActivity')
    assert not invalid('com.app ')  # trailing space
    assert not invalid('1com.app')  # starts with digit
    assert not invalid('a' * 250)  # too long


# --- humanize_pkg ------------------------------------------------------------


def test_humanize_pkg_picks_last_segment(real_scrcpy):
    assert real_scrcpy.humanize_pkg('com.android.settings') == 'Settings'
    assert real_scrcpy.humanize_pkg('com.spotify.music') == 'Music'


def test_humanize_pkg_splits_camel_case(real_scrcpy):
    assert real_scrcpy.humanize_pkg('com.example.MyApp') == 'My App'


def test_humanize_pkg_splits_underscores(real_scrcpy):
    assert real_scrcpy.humanize_pkg('com.example.my_app') == 'My app'


# --- parse_launcher_apps -----------------------------------------------------


def test_parse_launcher_apps_typical_output(real_scrcpy):
    raw = """3 activities found:
com.android.settings/com.android.settings.Settings
com.android.chrome/com.google.android.apps.chrome.Main
com.spotify.music/.MainActivity
"""
    apps = real_scrcpy.parse_launcher_apps(raw)
    labels = [a['label'] for a in apps]
    assert labels == sorted(labels, key=str.lower)
    assert {a['pkg'] for a in apps} == {
        'com.android.settings',
        'com.android.chrome',
        'com.spotify.music',
    }
    spotify = next(a for a in apps if a['pkg'] == 'com.spotify.music')
    # Relative activity should be expanded against the package.
    assert spotify['activity'] == 'com.spotify.music.MainActivity'


def test_parse_launcher_apps_dedups_by_pkg(real_scrcpy):
    raw = """com.x.y/com.x.y.A
com.x.y/com.x.y.B
"""
    apps = real_scrcpy.parse_launcher_apps(raw)
    assert [a['pkg'] for a in apps] == ['com.x.y']


def test_parse_launcher_apps_drops_garbage_lines(real_scrcpy):
    raw = """N activities found:

malformed line
no/slash
ok com.x.y/com.x.y.A
com.x.y/com.x.y.A
"""
    apps = real_scrcpy.parse_launcher_apps(raw)
    assert [a['pkg'] for a in apps] == ['com.x.y']


def test_parse_launcher_apps_handles_empty_input(real_scrcpy):
    assert real_scrcpy.parse_launcher_apps('') == []
    assert real_scrcpy.parse_launcher_apps(None) == []


# --- /api/launcher/list ------------------------------------------------------


def test_launcher_list_requires_login(client):
    r = client.get('/api/launcher/list')
    # login_required redirects to /login (302) for unauth GETs
    assert r.status_code in (302, 401)


def test_launcher_list_returns_apps(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)

    def fake_list(serial=None, timeout=8.0, adb_path=None):  # noqa: ARG001
        return True, [
            {
                'pkg': 'com.android.settings',
                'activity': 'com.android.settings.Settings',
                'label': 'Settings',
            },
        ]

    monkeypatch.setattr(app, 'list_launcher_apps', fake_list)
    r = client.get('/api/launcher/list')
    assert r.status_code == 200
    body = r.get_json()
    assert body['ok'] is True
    assert body['apps'][0]['pkg'] == 'com.android.settings'


def test_launcher_list_propagates_adb_error(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    monkeypatch.setattr(
        app,
        'list_launcher_apps',
        lambda *a, **k: (False, 'no devices'),
    )
    r = client.get('/api/launcher/list')
    assert r.status_code == 500
    assert r.get_json() == {'ok': False, 'error': 'no devices'}


# --- /api/launcher/launch ----------------------------------------------------


def test_launcher_launch_validates_pkg(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post(
        '/api/launcher/launch',
        data={'pkg': 'not a package', 'csrf_token': tok},
    )
    assert r.status_code == 400
    assert r.get_json()['ok'] is False


def test_launcher_launch_calls_launch_app(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_launch(pkg, serial=None, timeout=10.0, adb_path=None):  # noqa: ARG001
        captured['pkg'] = pkg
        return True, 'Events injected: 1'

    monkeypatch.setattr(app, 'launch_app', fake_launch)
    tok = _post_csrf(client)
    r = client.post(
        '/api/launcher/launch',
        data={'pkg': 'com.spotify.music', 'csrf_token': tok},
    )
    assert r.status_code == 200
    assert r.get_json()['ok'] is True
    assert captured['pkg'] == 'com.spotify.music'


def test_launcher_launch_failure_propagates(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    monkeypatch.setattr(app, 'launch_app', lambda *a, **k: (False, 'monkey: not found'))
    tok = _post_csrf(client)
    r = client.post(
        '/api/launcher/launch',
        data={'pkg': 'com.spotify.music', 'csrf_token': tok},
    )
    assert r.status_code == 500
    assert r.get_json() == {'ok': False, 'error': 'monkey: not found'}
