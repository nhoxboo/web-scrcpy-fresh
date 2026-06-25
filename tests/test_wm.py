"""Tests for /api/adb/wm — wm size / wm density override.

Like test_quick_wireless.py, the real adb is mocked in conftest. These tests
patch app.adb_shell so we can observe the argv constructed for each `op` and
assert that user input is range-checked before being spliced into the args.
"""

from __future__ import annotations


def _login(client, csrf, default_credentials):
    resp = client.post(
        '/api/login',
        data={
            'username': default_credentials['username'],
            'password': default_credentials['password'],
            'csrf_token': csrf,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 200


def _post_csrf(client):
    """Pull the meta-tag CSRF off the index page so authed POSTs can attach it."""
    import re

    resp = client.get('/')
    assert resp.status_code == 200
    m = re.search(rb'name="csrf-token" content="([^"]+)"', resp.data)
    assert m, 'meta csrf-token not found'
    return m.group(1).decode()


def test_wm_unknown_op_400(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post('/api/adb/wm', data={'op': 'rm_rf', 'csrf_token': tok})
    assert r.status_code == 400
    assert r.json['ok'] is False


def test_wm_set_size_builds_correct_argv(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['args'] = list(args)
        captured['serial'] = serial
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/wm',
        data={'op': 'set_size', 'width': '1080', 'height': '2400', 'csrf_token': tok},
    )
    assert r.status_code == 200
    assert r.json['ok'] is True
    assert captured['args'] == ['wm', 'size', '1080x2400']


def test_wm_set_density_builds_correct_argv(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['args'] = list(args)
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/wm',
        data={'op': 'set_density', 'density': '420', 'csrf_token': tok},
    )
    assert r.status_code == 200
    assert r.json['ok'] is True
    assert captured['args'] == ['wm', 'density', '420']


def test_wm_reset_size_runs_reset(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['args'] = list(args)
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/adb/wm', data={'op': 'reset_size', 'csrf_token': tok})
    assert r.status_code == 200
    assert captured['args'] == ['wm', 'size', 'reset']


def test_wm_reset_density_runs_reset(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['args'] = list(args)
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/adb/wm', data={'op': 'reset_density', 'csrf_token': tok})
    assert r.status_code == 200
    assert captured['args'] == ['wm', 'density', 'reset']


def test_wm_reset_all_runs_both(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    calls: list[list[str]] = []

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        calls.append(list(args))
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/adb/wm', data={'op': 'reset_all', 'csrf_token': tok})
    assert r.status_code == 200
    assert calls == [['wm', 'size', 'reset'], ['wm', 'density', 'reset']]


def test_wm_get_parses_output(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    outputs = {
        ('wm', 'size'): 'Physical size: 1768x2208\nOverride size: 1080x2400',
        ('wm', 'density'): 'Physical density: 380\nOverride density: 420',
    }

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        return True, outputs[tuple(args)]

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/adb/wm', data={'op': 'get', 'csrf_token': tok})
    assert r.status_code == 200
    body = r.json
    assert body['ok'] is True
    assert body['size'] == {'physical': '1768x2208', 'override': '1080x2400'}
    assert body['density'] == {'physical': '380', 'override': '420'}


def test_wm_get_parses_no_override(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    outputs = {
        ('wm', 'size'): 'Physical size: 1080x2400',
        ('wm', 'density'): 'Physical density: 420',
    }

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        return True, outputs[tuple(args)]

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/adb/wm', data={'op': 'get', 'csrf_token': tok})
    assert r.status_code == 200
    body = r.json
    assert body['size'] == {'physical': '1080x2400'}
    assert body['density'] == {'physical': '420'}
    assert 'override' not in body['size']
    assert 'override' not in body['density']


def test_wm_set_size_rejects_out_of_range(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    called = {'count': 0}

    def fake_shell(*a, **k):  # noqa: ARG001
        called['count'] += 1
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    # too small
    r = client.post(
        '/api/adb/wm',
        data={'op': 'set_size', 'width': '50', 'height': '100', 'csrf_token': tok},
    )
    assert r.status_code == 400
    assert r.json['ok'] is False
    # too big
    r = client.post(
        '/api/adb/wm',
        data={'op': 'set_size', 'width': '99999', 'height': '100', 'csrf_token': tok},
    )
    assert r.status_code == 400
    # negative
    r = client.post(
        '/api/adb/wm',
        data={'op': 'set_size', 'width': '-1080', 'height': '-2400', 'csrf_token': tok},
    )
    assert r.status_code == 400
    # adb_shell never invoked for any of the rejected requests
    assert called['count'] == 0


def test_wm_set_size_rejects_non_numeric(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    called = {'count': 0}

    def fake_shell(*a, **k):  # noqa: ARG001
        called['count'] += 1
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    for w, h in (
        ('1080; rm -rf /', '2400'),
        ('$(echo bad)', '2400'),
        ('1080', ''),
        ('', '2400'),
        ('1080.5', '2400'),
        ('abcd', '2400'),
    ):
        r = client.post(
            '/api/adb/wm',
            data={'op': 'set_size', 'width': w, 'height': h, 'csrf_token': tok},
        )
        assert r.status_code == 400, f'expected 400 for w={w!r} h={h!r}'
    assert called['count'] == 0


def test_wm_set_density_rejects_out_of_range(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    called = {'count': 0}

    def fake_shell(*a, **k):  # noqa: ARG001
        called['count'] += 1
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    for d in ('0', '79', '1001', '99999', '-420', 'abcd', ''):
        r = client.post(
            '/api/adb/wm',
            data={'op': 'set_density', 'density': d, 'csrf_token': tok},
        )
        assert r.status_code == 400, f'expected 400 for d={d!r}'
    assert called['count'] == 0


def test_wm_set_size_propagates_failure(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    monkeypatch.setattr(app, 'adb_shell', lambda *a, **k: (False, 'Permission Denial'))
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/wm',
        data={'op': 'set_size', 'width': '1080', 'height': '2400', 'csrf_token': tok},
    )
    assert r.status_code == 500
    assert r.json == {'ok': False, 'error': 'Permission Denial'}


def test_wm_endpoint_requires_login(client, csrf):
    """Match the convention of other endpoints — must redirect or 401 when
    not authenticated. The CSRF guard runs first so we still attach a token."""
    r = client.post('/api/adb/wm', data={'op': 'get', 'csrf_token': csrf})
    assert r.status_code == 401


def test_wm_set_size_uses_selected_serial(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    captured = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['serial'] = serial
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    # Pin a session-level serial via the existing /devices flow surrogate.
    with client.session_transaction() as s:
        s['adb_serial'] = 'TESTSERIAL123'
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/wm',
        data={'op': 'set_size', 'width': '1080', 'height': '2400', 'csrf_token': tok},
    )
    assert r.status_code == 200
    assert captured['serial'] == 'TESTSERIAL123'
