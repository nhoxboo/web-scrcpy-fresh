"""Tests for /api/session/{status,kick}.

The kick endpoint is the recovery path when a tab crashed or a previous
session never released the single-client lock. We test that:
  * status reports `active` correctly based on scpy_ctx
  * kick is a no-op when no client is connected (returns kicked=False)
  * kick calls socketio.disconnect with the recorded sid when there is one
  * kick handles socketio.disconnect raising
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
    import re

    resp = client.get('/')
    m = re.search(rb'name="csrf-token" content="([^"]+)"', resp.data)
    assert m
    return m.group(1).decode()


def test_status_reports_inactive(client, csrf, default_credentials, app):
    _login(client, csrf, default_credentials)
    app.scpy_ctx = None
    app.client_sid = None
    r = client.get('/api/session/status')
    assert r.status_code == 200
    body = r.get_json()
    assert body['ok'] is True
    assert body['active'] is False


def test_status_reports_active(client, csrf, default_credentials, app):
    _login(client, csrf, default_credentials)
    app.scpy_ctx = object()
    app.client_sid = 'sid-of-other-tab'
    try:
        r = client.get('/api/session/status')
        body = r.get_json()
        assert body['ok'] is True
        assert body['active'] is True
    finally:
        app.scpy_ctx = None
        app.client_sid = None


def test_kick_noop_when_nobody_connected(client, csrf, default_credentials, app):
    _login(client, csrf, default_credentials)
    app.scpy_ctx = None
    app.client_sid = None
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


def test_kick_calls_socketio_disconnect(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    app.scpy_ctx = object()
    app.client_sid = 'sid-other'
    fake = _FakeServer()
    monkeypatch.setattr(app.socketio, 'server', fake, raising=False)
    try:
        tok = _post_csrf(client)
        r = client.post('/api/session/kick', data={'csrf_token': tok})
        assert r.status_code == 200
        assert r.get_json() == {'ok': True, 'kicked': True}
        assert fake.calls == ['sid-other']
    finally:
        app.scpy_ctx = None
        app.client_sid = None


def test_kick_handles_disconnect_raise(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    app.scpy_ctx = object()
    app.client_sid = 'sid-other'
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
        app.scpy_ctx = None
        app.client_sid = None


def test_status_requires_login(client):
    r = client.get('/api/session/status')
    assert r.status_code in (302, 401)


def test_kick_requires_login(client):
    r = client.post('/api/session/kick')
    assert r.status_code in (302, 401, 400)
