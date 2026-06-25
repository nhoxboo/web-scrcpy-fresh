"""Tests for the multi-device picker (/devices, /api/devices)."""

from __future__ import annotations


def _csrf_from(client) -> str:
    resp = client.get('/api/csrf')
    assert resp.status_code == 200
    return resp.json['csrf_token']


def _login(client, default_credentials):
    """Authenticate via /login so subsequent calls can hit @login_required."""
    token = _csrf_from(client)
    resp = client.post(
        '/api/login',
        data={
            'csrf_token': token,
            'username': default_credentials['username'],
            'password': default_credentials['password'],
        },
    )
    assert resp.status_code == 200


def _set_devices(app, monkeypatch, devices):
    monkeypatch.setattr(app, 'list_adb_devices', lambda *a, **k: devices)


def _post_select(client, serial):
    token = _csrf_from(client)
    return client.post('/api/devices/select', data={'csrf_token': token, 'serial': serial})


def test_devices_requires_auth(client):
    # Route changed to serve SPA. We test api_devices instead.
    pass


def test_api_devices_requires_auth(client):
    resp = client.get('/api/devices')
    assert resp.status_code == 401


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
    resp = client.get('/api/devices')
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
    assert resp.status_code == 200
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
    resp = _post_select(client, '; rm -rf /')
    assert resp.status_code == 200
    assert 'không hợp lệ' in resp.json['error']
    with client.session_transaction() as s:
        assert 'adb_serial' not in s


def test_select_rejects_unattached_serial(client, app, default_credentials, monkeypatch):
    _login(client, default_credentials)
    _set_devices(
        app, monkeypatch, [{'serial': 'OTHER_DEVICE', 'state': 'device'}]
    )  # Device dropped off
    resp = _post_select(client, 'ABC123')
    assert resp.status_code == 200
    assert 'không còn kết nối' in resp.json['error']
    with client.session_transaction() as s:
        assert 'adb_serial' not in s


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

    token = _csrf_from(client)
    resp = client.post('/api/devices/select', data={'csrf_token': token, 'action': 'clear'})
    assert resp.status_code == 200
    with client.session_transaction() as s:
        assert 'adb_serial' not in s


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
    resp = client.get('/api/session')
    assert resp.status_code == 200
    assert 'ABC123' in resp.json['device_label']
    assert 'Galaxy_S23' in resp.json['device_label']
