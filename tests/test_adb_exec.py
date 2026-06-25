"""Tests for /api/adb/exec — free-form `adb shell` exec endpoint.

The host-side argv is fixed (no shell=True), so the only thing the user can
do is type a string that the *device's* shell will interpret. These tests
patch ``app.adb_shell`` to verify that:

  - the entire user string is forwarded as a single argv token, untouched,
  - input validation rejects empty / oversized / NUL-bearing strings,
  - the endpoint requires login + CSRF,
  - oversized output is truncated and flagged in the response,
  - failures from the underlying adb_shell propagate as HTTP 500 with the
    error body.
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


def test_exec_requires_login(client, csrf):
    # Without authenticating, /api/adb/exec should redirect to /login.
    r = client.post(
        '/api/adb/exec',
        data={'cmd': 'echo hi', 'csrf_token': csrf},
        follow_redirects=False,
    )
    assert r.status_code in (302, 401)


def test_exec_rejects_missing_csrf(client, default_credentials, csrf):
    _login(client, csrf, default_credentials)
    # No csrf_token field → 400 from the global before_request guard.
    r = client.post('/api/adb/exec', data={'cmd': 'echo hi'})
    assert r.status_code == 400


def test_exec_rejects_empty_cmd(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post('/api/adb/exec', data={'cmd': '', 'csrf_token': tok})
    assert r.status_code == 400
    assert r.json['ok'] is False
    assert 'rỗng' in r.json['error']


def test_exec_rejects_too_long_cmd(client, csrf, default_credentials, app):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    big = 'a' * (app.ADB_EXEC_MAX_CMD_LEN + 1)
    r = client.post('/api/adb/exec', data={'cmd': big, 'csrf_token': tok})
    assert r.status_code == 400
    assert r.json['ok'] is False
    assert 'quá dài' in r.json['error']


def test_exec_rejects_nul_byte(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post(
        '/api/adb/exec',
        data={'cmd': 'echo a\x00b', 'csrf_token': tok},
    )
    assert r.status_code == 400
    assert r.json['ok'] is False
    assert 'NUL' in r.json['error']


def test_exec_forwards_cmd_verbatim_as_single_argv(
    client, csrf, default_credentials, app, monkeypatch
):
    """The user's full string must reach adb_shell as args=[cmd]."""
    _login(client, csrf, default_credentials)
    captured: dict = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['args'] = list(args)
        captured['serial'] = serial
        captured['timeout'] = timeout
        return True, 'pong\n'

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    cmd = 'echo "hello world" && wm size | head -1'
    r = client.post('/api/adb/exec', data={'cmd': cmd, 'csrf_token': tok})
    assert r.status_code == 200
    assert r.json['ok'] is True
    # Must be a SINGLE argv token — adb's host side is given the full string
    # and forwards it to the device shell, which is what expands && and |.
    assert captured['args'] == [cmd]
    # Timeout is the longer ADB_EXEC_TIMEOUT, not the wm-style 15s.
    assert captured['timeout'] == app.ADB_EXEC_TIMEOUT
    # The endpoint passes adb_shell's output through verbatim (no trim);
    # adb_shell.real already strips trailing whitespace, so the production
    # path will see 'pong'.
    assert r.json['output'] == 'pong\n'


def test_exec_passes_through_output_as_is(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        return True, 'line1\nline2\nline3'

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/adb/exec', data={'cmd': 'getprop', 'csrf_token': tok})
    assert r.status_code == 200
    body = r.json
    assert body['ok'] is True
    assert body['output'] == 'line1\nline2\nline3'
    assert body['truncated'] is False


def test_exec_truncates_huge_output(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    huge = 'x' * (app.ADB_EXEC_MAX_OUTPUT_BYTES + 5_000)

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        return True, huge

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/adb/exec', data={'cmd': 'cat /data/local/big', 'csrf_token': tok})
    assert r.status_code == 200
    body = r.json
    assert body['ok'] is True
    assert body['truncated'] is True
    # truncated body keeps exactly MAX bytes of original + sentinel suffix
    assert body['output'].startswith('x' * 100)
    assert body['output'].endswith('(output truncated)')
    assert len(body['output']) <= app.ADB_EXEC_MAX_OUTPUT_BYTES + 100  # sentinel margin


def test_exec_propagates_failure_as_500(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        return False, '/system/bin/sh: not found: nope'

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    tok = _post_csrf(client)
    r = client.post('/api/adb/exec', data={'cmd': 'nope', 'csrf_token': tok})
    assert r.status_code == 500
    body = r.json
    assert body['ok'] is False
    assert 'not found' in body['error']


def test_exec_uses_selected_serial(client, csrf, default_credentials, app, monkeypatch):
    """If the session has a selected serial, it's passed through to adb_shell."""
    _login(client, csrf, default_credentials)
    captured: dict = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['serial'] = serial
        return True, 'ok'

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    monkeypatch.setattr(app, '_selected_serial', lambda: 'ABC123')
    tok = _post_csrf(client)
    r = client.post('/api/adb/exec', data={'cmd': 'echo ok', 'csrf_token': tok})
    assert r.status_code == 200
    assert captured['serial'] == 'ABC123'
