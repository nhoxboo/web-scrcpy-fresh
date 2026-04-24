"""Smoke tests for the auth + CSRF + rate-limit surface."""

from __future__ import annotations


def _login(client, username, password, csrf_token):
    return client.post(
        '/login',
        data={'username': username, 'password': password, 'csrf_token': csrf_token},
        follow_redirects=False,
    )


def test_login_page_renders_and_has_csrf_token(client):
    resp = client.get('/login')
    assert resp.status_code == 200
    assert b'name="csrf_token"' in resp.data


def test_post_login_without_csrf_rejected(client, default_credentials):
    resp = client.post(
        '/login',
        data={
            'username': default_credentials['username'],
            'password': default_credentials['password'],
        },
    )
    assert resp.status_code == 400


def test_correct_login_redirects_and_grants_session(client, csrf, default_credentials):
    resp = _login(client, default_credentials['username'], default_credentials['password'], csrf)
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/')
    home = client.get('/')
    assert home.status_code == 200
    assert b'Web Scrcpy Panel' in home.data


def test_wrong_password_shows_error(client, csrf, default_credentials):
    resp = _login(client, default_credentials['username'], 'not-the-password', csrf)
    assert resp.status_code == 200
    assert 'Sai tài khoản hoặc mật khẩu'.encode() in resp.data


def test_auth_json_is_hashed_on_disk(app, default_credentials):
    import json

    with open(app.AUTH_FILE, encoding='utf-8') as fh:
        data = json.load(fh)
    assert data['password'] != default_credentials['password']
    assert ':' in data['password']  # werkzeug hash format


def test_rate_limit_blocks_after_n_attempts(client, csrf, default_credentials, app):
    for _ in range(app.LOGIN_MAX_ATTEMPTS):
        _login(client, default_credentials['username'], 'nope', csrf)
        csrf = _fresh_csrf(client)
    blocked = _login(client, default_credentials['username'], 'nope', csrf)
    assert blocked.status_code == 429


def _fresh_csrf(client):
    import re

    r = client.get('/login')
    m = re.search(rb'name="csrf_token" value="([^"]+)"', r.data)
    return m.group(1).decode()


def test_security_headers_present(client):
    resp = client.get('/login')
    assert resp.headers.get('X-Frame-Options') == 'DENY'
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('Referrer-Policy') == 'same-origin'
    assert 'Content-Security-Policy' in resp.headers


def test_change_password_flow(client, csrf, default_credentials):
    resp = _login(client, default_credentials['username'], default_credentials['password'], csrf)
    assert resp.status_code == 302

    page = client.get('/change-password')
    assert page.status_code == 200
    token = _fresh_csrf_from(page.data)

    resp = client.post(
        '/change-password',
        data={
            'csrf_token': token,
            'current_password': default_credentials['password'],
            'new_username': default_credentials['username'],
            'new_password': 'a-much-better-password',
            'confirm_password': 'a-much-better-password',
        },
    )
    assert resp.status_code == 302

    # New password works, old one does not.
    client.post('/logout', data={'csrf_token': token})
    new_csrf = _fresh_csrf(client)
    assert (
        _login(
            client, default_credentials['username'], default_credentials['password'], new_csrf
        ).status_code
        == 200
    )
    # The login response for success is 302; reuse a new CSRF token.
    new_csrf = _fresh_csrf(client)
    assert (
        _login(
            client, default_credentials['username'], 'a-much-better-password', new_csrf
        ).status_code
        == 302
    )


def test_change_password_rejects_short_password(client, csrf, default_credentials):
    _login(client, default_credentials['username'], default_credentials['password'], csrf)
    page = client.get('/change-password')
    token = _fresh_csrf_from(page.data)
    resp = client.post(
        '/change-password',
        data={
            'csrf_token': token,
            'current_password': default_credentials['password'],
            'new_username': default_credentials['username'],
            'new_password': 'short',
            'confirm_password': 'short',
        },
    )
    assert resp.status_code == 200
    assert 'tối thiểu'.encode() in resp.data


def _fresh_csrf_from(html: bytes) -> str:
    import re

    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    assert m
    return m.group(1).decode()
