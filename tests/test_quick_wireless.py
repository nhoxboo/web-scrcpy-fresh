"""Tests for /api/quick (whitelisted adb shell) + /api/adb/{pair,connect,disconnect}.

We don't run real adb here — conftest.py mocks the scrcpy module's adb_shell /
adb_simple / adb_pair / adb_connect / adb_disconnect with no-op success stubs,
and these tests monkeypatch them on the imported `app` module to inject specific
responses (and assert on the args).
"""

from __future__ import annotations


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
    """Pull the meta-tag CSRF off the index page so authed POSTs can attach it."""
    import re

    resp = client.get('/')
    assert resp.status_code == 200
    m = re.search(rb'name="csrf-token" content="([^"]+)"', resp.data)
    assert m, 'meta csrf-token not found'
    return m.group(1).decode()


def test_quick_unknown_action_400(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post('/api/quick', data={'action': 'rm_rf', 'csrf_token': tok})
    assert r.status_code == 400
    assert r.json['ok'] is False


def test_quick_home_runs_input_keyevent(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['args'] = args
        captured['serial'] = serial
        return True, 'OK'

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/quick', data={'action': 'home', 'csrf_token': tok})
    assert r.status_code == 200
    assert r.json == {'ok': True, 'output': 'OK'}
    assert captured['args'] == ['input', 'keyevent', 'KEYCODE_HOME']


def test_quick_reboot_uses_adb_simple(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_simple(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['args'] = args
        return True, ''

    monkeypatch.setattr(app, 'adb_simple', fake_simple)
    tok = _post_csrf(client)
    r = client.post('/api/quick', data={'action': 'reboot', 'csrf_token': tok})
    assert r.status_code == 200
    assert captured['args'] == ['reboot']


def test_quick_failure_propagates(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    monkeypatch.setattr(app, 'adb_shell', lambda *a, **k: (False, 'svc: not allowed'))
    tok = _post_csrf(client)
    r = client.post('/api/quick', data={'action': 'wifi_on', 'csrf_token': tok})
    assert r.status_code == 500
    assert r.json == {'ok': False, 'error': 'svc: not allowed'}


def test_pair_validates_inputs(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/pair',
        data={'host': 'bad host!', 'port': '37123', 'code': '123456', 'csrf_token': tok},
    )
    assert r.status_code == 400
    r = client.post(
        '/api/adb/pair',
        data={'host': '1.2.3.4', 'port': '0', 'code': '123456', 'csrf_token': tok},
    )
    assert r.status_code == 400
    r = client.post(
        '/api/adb/pair',
        data={'host': '1.2.3.4', 'port': '37123', 'code': 'abc', 'csrf_token': tok},
    )
    assert r.status_code == 400


def test_pair_success_calls_adb_pair(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_pair(host, port, code, timeout=30.0, adb_path=None):  # noqa: ARG001
        captured.update(host=host, port=port, code=code)
        return True, f'Successfully paired to {host}:{port}'

    monkeypatch.setattr(app, 'adb_pair', fake_pair)
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/pair',
        data={
            'host': '192.168.1.50',
            'port': '37123',
            'code': '654321',
            'csrf_token': tok,
        },
    )
    assert r.status_code == 200
    assert r.json['ok'] is True
    assert captured == {'host': '192.168.1.50', 'port': '37123', 'code': '654321'}


def test_connect_success(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_connect(host, port, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured.update(host=host, port=port)
        return True, f'connected to {host}:{port}'

    monkeypatch.setattr(app, 'adb_connect', fake_connect)
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/connect',
        data={'host': '10.0.0.5', 'port': '5555', 'csrf_token': tok},
    )
    assert r.status_code == 200
    assert captured == {'host': '10.0.0.5', 'port': '5555'}


def test_connect_rejects_bad_host(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/connect',
        data={'host': '$(rm -rf)', 'port': '5555', 'csrf_token': tok},
    )
    assert r.status_code == 400


def test_disconnect_with_no_args_runs(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_disc(host=None, port=None, timeout=10.0, adb_path=None):  # noqa: ARG001
        captured.update(host=host, port=port)
        return True, ''

    monkeypatch.setattr(app, 'adb_disconnect', fake_disc)
    tok = _post_csrf(client)
    r = client.post('/api/adb/disconnect', data={'csrf_token': tok})
    assert r.status_code == 200
    # Empty string is normalised to None to mean "disconnect all".
    assert captured == {'host': None, 'port': None}


def test_endpoints_require_login(client, csrf):
    """All four endpoints must redirect to /login when not authenticated.

    The CSRF guard runs before login_required, so we have to attach a token
    even though the request will redirect — otherwise it 400s on CSRF first.
    """
    for path in ('/api/quick', '/api/adb/pair', '/api/adb/connect', '/api/adb/disconnect'):
        r = client.post(path, data={'csrf_token': csrf})
        assert r.status_code in (302, 401)
