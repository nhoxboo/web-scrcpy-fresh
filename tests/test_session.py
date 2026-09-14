"""Tests for /api/session/{status,kick} using the per-socket session registry."""

from __future__ import annotations

import queue


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


def _active_session(serial: str = 'test-serial') -> tuple[str, dict]:
    class _Context:
        def __init__(self, device_serial: str):
            self.serial = device_serial

    return (
        'sid-other',
        {
            'scpy_ctx': _Context(serial),
            'video_q': queue.Queue(),
            'audio_q': queue.Queue(),
            'tasks': [],
        },
    )


def _set_selected_serial(client, serial: str) -> None:
    with client.session_transaction() as browser_session:
        browser_session['adb_serial'] = serial


def _add_active_session(app, serial: str = 'test-serial') -> str:
    sid, state = _active_session(serial)
    with app._state_lock:
        app.scpy_sessions[sid] = state
    return sid


def _clear_sessions(app) -> None:
    with app._state_lock:
        app.scpy_sessions.clear()


def test_status_reports_inactive(client, csrf, default_credentials, app):
    _login(client, csrf, default_credentials)
    _clear_sessions(app)
    r = client.get('/api/session/status')
    assert r.status_code == 200
    assert r.get_json() == {'ok': True, 'active': False}


def test_status_reports_active_for_selected_device(client, csrf, default_credentials, app):
    _login(client, csrf, default_credentials)
    _set_selected_serial(client, 'test-serial')
    _add_active_session(app, 'test-serial')
    try:
        r = client.get('/api/session/status')
        assert r.status_code == 200
        assert r.get_json() == {'ok': True, 'active': True}
    finally:
        _clear_sessions(app)


def test_status_ignores_session_for_another_device(client, csrf, default_credentials, app):
    _login(client, csrf, default_credentials)
    _set_selected_serial(client, 'selected-serial')
    _add_active_session(app, 'other-serial')
    try:
        r = client.get('/api/session/status')
        assert r.status_code == 200
        assert r.get_json() == {'ok': True, 'active': False}
    finally:
        _clear_sessions(app)


def test_kick_noop_when_nobody_connected(client, csrf, default_credentials, app):
    _login(client, csrf, default_credentials)
    _clear_sessions(app)
    tok = _post_csrf(client)
    r = client.post('/api/session/kick', data={'csrf_token': tok})
    assert r.status_code == 200
    assert r.get_json() == {'ok': True, 'kicked': False}


class _FakeServer:
    def __init__(self, raise_on_disconnect=None):
        self.calls: list[str] = []
        self._raise = raise_on_disconnect

    def disconnect(self, sid):
        if self._raise:
            raise self._raise
        self.calls.append(sid)


def test_kick_calls_socketio_disconnect_for_selected_device(
    client, csrf, default_credentials, app, monkeypatch
):
    _login(client, csrf, default_credentials)
    _set_selected_serial(client, 'test-serial')
    _add_active_session(app, 'test-serial')
    fake = _FakeServer()
    monkeypatch.setattr(app.socketio, 'server', fake, raising=False)
    try:
        tok = _post_csrf(client)
        r = client.post('/api/session/kick', data={'csrf_token': tok})
        assert r.status_code == 200
        assert r.get_json() == {'ok': True, 'kicked': True}
        assert fake.calls == ['sid-other']
    finally:
        _clear_sessions(app)


def test_kick_handles_disconnect_raise(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    _set_selected_serial(client, 'test-serial')
    _add_active_session(app, 'test-serial')
    fake = _FakeServer(raise_on_disconnect=RuntimeError('socket already gone'))
    monkeypatch.setattr(app.socketio, 'server', fake, raising=False)
    try:
        tok = _post_csrf(client)
        r = client.post('/api/session/kick', data={'csrf_token': tok})
        assert r.status_code == 500
        body = r.get_json()
        assert body['ok'] is False
        assert 'socket already gone' in body['error']
    finally:
        _clear_sessions(app)


def test_status_requires_login(client):
    r = client.get('/api/session/status')
    assert r.status_code in (302, 401)


def test_kick_requires_login(client):
    r = client.post('/api/session/kick')
    assert r.status_code in (302, 401, 400)
