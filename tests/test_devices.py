"""Tests for the multi-device picker (/devices, /api/devices)."""

from __future__ import annotations

import re


def _csrf_from(html: bytes) -> str:
    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    assert m, 'csrf_token not found in response'
    return m.group(1).decode()


def _login(client, default_credentials):
    """Authenticate via /login so subsequent calls can hit @login_required."""
    page = client.get('/login')
    token = _csrf_from(page.data)
    resp = client.post(
        '/login',
        data={
            'csrf_token': token,
            'username': default_credentials['username'],
            'password': default_credentials['password'],
        },
    )
    assert resp.status_code == 302


def _set_devices(app, monkeypatch, devices):
    monkeypatch.setattr(app, 'list_adb_devices', lambda *a, **k: devices)


def _post_select(client, serial):
    page = client.get('/devices')
    token = _csrf_from(page.data)
    return client.post('/devices', data={'csrf_token': token, 'serial': serial})


def test_devices_requires_auth(client):
    resp = client.get('/devices')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_api_devices_requires_auth(client):
    resp = client.get('/api/devices')
    assert resp.status_code == 302


def test_devices_page_lists_attached_devices(client, app, default_credentials, monkeypatch):
    _login(client, default_credentials)
    _set_devices(
        app,
        monkeypatch,
        [
            {
                'serial': 'ABC123',
                'state': 'device',
                'model': 'SM_S918B',
                'product': 'dm3qxx',
                'transport_id': '1',
                'usb': '',
            },
            {
                'serial': '192.168.1.10:5555',
                'state': 'unauthorized',
                'model': '',
                'product': '',
                'transport_id': '2',
                'usb': '',
            },
        ],
    )
    resp = client.get('/devices')
    assert resp.status_code == 200
    assert b'ABC123' in resp.data
    assert b'SM_S918B' in resp.data
    assert b'192.168.1.10:5555' in resp.data
    assert b'unauthorized' in resp.data


def test_select_device_persists_in_session(client, app, default_credentials, monkeypatch):
    _login(client, default_credentials)
    _set_devices(
        app,
        monkeypatch,
        [
            {
                'serial': 'ABC123',
                'state': 'device',
                'model': 'X',
                'product': '',
                'transport_id': '',
                'usb': '',
            },
        ],
    )
    resp = _post_select(client, 'ABC123')
    assert resp.status_code == 302
    with client.session_transaction() as s:
        assert s.get('adb_serial') == 'ABC123'

    api = client.get('/api/devices')
    assert api.status_code == 200
    body = api.get_json()
    assert body['selected'] == 'ABC123'
    assert body['devices'][0]['serial'] == 'ABC123'


def test_select_rejects_invalid_serial(client, app, default_credentials, monkeypatch):
    _login(client, default_credentials)
    _set_devices(
        app,
        monkeypatch,
        [
            {
                'serial': 'ABC123',
                'state': 'device',
                'model': '',
                'product': '',
                'transport_id': '',
                'usb': '',
            },
        ],
    )
    resp = _post_select(client, 'rm -rf /')
    assert resp.status_code == 200  # re-renders with flash, no redirect
    with client.session_transaction() as s:
        assert s.get('adb_serial') is None


def test_select_rejects_unattached_serial(client, app, default_credentials, monkeypatch):
    _login(client, default_credentials)
    _set_devices(
        app,
        monkeypatch,
        [
            {
                'serial': 'ABC123',
                'state': 'device',
                'model': '',
                'product': '',
                'transport_id': '',
                'usb': '',
            },
        ],
    )
    resp = _post_select(client, 'NOTPRESENT')
    assert resp.status_code == 200
    with client.session_transaction() as s:
        assert s.get('adb_serial') is None


def test_clear_selection(client, app, default_credentials, monkeypatch):
    _login(client, default_credentials)
    _set_devices(
        app,
        monkeypatch,
        [
            {
                'serial': 'ABC123',
                'state': 'device',
                'model': '',
                'product': '',
                'transport_id': '',
                'usb': '',
            },
        ],
    )
    _post_select(client, 'ABC123')
    with client.session_transaction() as s:
        assert s.get('adb_serial') == 'ABC123'

    page = client.get('/devices')
    token = _csrf_from(page.data)
    resp = client.post('/devices', data={'csrf_token': token, 'action': 'clear'})
    assert resp.status_code == 302
    with client.session_transaction() as s:
        assert s.get('adb_serial') is None


def test_index_shows_device_label(client, app, default_credentials, monkeypatch):
    _login(client, default_credentials)
    _set_devices(
        app,
        monkeypatch,
        [
            {
                'serial': 'ABC123',
                'state': 'device',
                'model': 'Galaxy_S23',
                'product': '',
                'transport_id': '',
                'usb': '',
            },
        ],
    )
    _post_select(client, 'ABC123')
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'ABC123' in resp.data
    assert b'Galaxy_S23' in resp.data
    assert b'/devices' in resp.data  # 'Đổi máy' link
