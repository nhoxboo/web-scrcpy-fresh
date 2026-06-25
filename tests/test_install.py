"""Tests for /api/install and /api/push.

Network calls + adb subprocess are stubbed via conftest.py and per-test
monkeypatches.
"""

from __future__ import annotations

import io


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


def _get_csrf_for_install(client):
    """Hit the index page and pull the meta tag CSRF (different name than form)."""
    import re

    resp = client.get('/')
    assert resp.status_code == 200
    m = re.search(rb'name="csrf-token" content="([^"]+)"', resp.data)
    assert m, 'meta csrf-token not found'
    return m.group(1).decode()


def test_install_requires_auth(client):
    resp = client.post('/api/install', data={})
    # @login_required redirects unauthenticated requests to /login
    assert resp.status_code in (302, 401, 400)


def test_install_with_apk_file(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)
    # Minimal "APK" — ZIP magic bytes
    apk_bytes = b'PK\x03\x04' + b'\x00' * 100
    resp = client.post(
        '/api/install',
        data={
            'file': (io.BytesIO(apk_bytes), 'tiny.apk'),
        },
        headers={'X-CSRF-Token': install_csrf},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 200, resp.data
    body = resp.get_json()
    assert body['ok'] is True


def test_install_rejects_non_apk_extension(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)
    resp = client.post(
        '/api/install',
        data={
            'file': (io.BytesIO(b'PK\x03\x04junk'), 'evil.exe'),
        },
        headers={'X-CSRF-Token': install_csrf},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 400
    assert b'.apk' in resp.data


def test_install_rejects_wrong_magic(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)
    resp = client.post(
        '/api/install',
        data={
            'file': (io.BytesIO(b'NOPE not a zip'), 'fake.apk'),
        },
        headers={'X-CSRF-Token': install_csrf},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert 'APK' in body['error']


def test_install_url_rejects_non_http(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)
    resp = client.post(
        '/api/install',
        data={'url': 'file:///etc/passwd', 'csrf_token': install_csrf},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert 'http' in body['error'].lower()


def test_install_requires_url_or_file(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)
    resp = client.post(
        '/api/install',
        data={'csrf_token': install_csrf},
    )
    assert resp.status_code == 400


def test_install_csrf_required(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    apk_bytes = b'PK\x03\x04' + b'\x00' * 100
    # No header, no form token → must 400
    resp = client.post(
        '/api/install',
        data={
            'file': (io.BytesIO(apk_bytes), 'tiny.apk'),
        },
        content_type='multipart/form-data',
    )
    assert resp.status_code == 400


def test_install_rate_limit(app, client, csrf, default_credentials, monkeypatch):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)
    # Drop the cap to 2 attempts so the test is fast
    app.INSTALL_RATE_MAX = 2
    app._install_attempts.clear()
    apk_bytes = b'PK\x03\x04' + b'\x00' * 100
    for _ in range(2):
        resp = client.post(
            '/api/install',
            data={'file': (io.BytesIO(apk_bytes), 'tiny.apk')},
            headers={'X-CSRF-Token': install_csrf},
            content_type='multipart/form-data',
        )
        assert resp.status_code == 200
    # 3rd attempt → 429
    resp = client.post(
        '/api/install',
        data={'file': (io.BytesIO(apk_bytes), 'tiny.apk')},
        headers={'X-CSRF-Token': install_csrf},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 429


def test_push_uploads_to_default_dest(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)
    resp = client.post(
        '/api/push',
        data={'file': (io.BytesIO(b'hello'), 'hello.txt')},
        headers={'X-CSRF-Token': install_csrf},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['ok'] is True
    assert body['dest'].startswith('/sdcard/Download/')


def test_push_rejects_invalid_dest(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)
    resp = client.post(
        '/api/push',
        data={
            'file': (io.BytesIO(b'x'), 'x.txt'),
            'dest': '../etc/',
        },
        headers={'X-CSRF-Token': install_csrf},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 400


def test_push_propagates_adb_failure(app, client, csrf, default_credentials, monkeypatch):
    _login(client, csrf, default_credentials)
    install_csrf = _get_csrf_for_install(client)

    def fail_push(src_path, dest_path, serial=None, timeout=600.0, adb_path=None):  # noqa: ARG001
        return False, 'adb: error: device offline'

    monkeypatch.setattr(app, 'adb_push', fail_push)
    resp = client.post(
        '/api/push',
        data={'file': (io.BytesIO(b'data'), 'foo.bin')},
        headers={'X-CSRF-Token': install_csrf},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 500
    body = resp.get_json()
    assert body['ok'] is False
    assert 'device offline' in body['error']
