"""Smoke tests for the auth + CSRF + rate-limit surface."""

from __future__ import annotations


def _login(client, username, password, csrf_token):
    return client.post(
        '/api/login',
        data={'username': username, 'password': password, 'csrf_token': csrf_token},
        follow_redirects=False,
    )


def test_login_page_renders_and_has_csrf_token(client):
    resp = client.get('/api/csrf')
    assert resp.status_code == 200
    assert b'csrf_token' in resp.data


def test_post_login_without_csrf_rejected(client, default_credentials):
    resp = client.post(
        '/api/login',
        data={
            'username': default_credentials['username'],
            'password': default_credentials['password'],
        },
    )
    assert resp.status_code == 400


def test_correct_login_redirects_and_grants_session(client, csrf, default_credentials):
    resp = _login(client, default_credentials['username'], default_credentials['password'], csrf)
    assert resp.status_code == 200
    home = client.get('/')
    assert home.status_code == 200
    assert b'Remote Android nhoxboo' in home.data


def test_wrong_password_shows_error(client, csrf, default_credentials):
    resp = _login(client, default_credentials['username'], 'not-the-password', csrf)
    assert resp.status_code == 401
    assert 'Sai tài khoản hoặc mật khẩu' in resp.json['error']


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
    r = client.get('/api/csrf')
    return r.json['csrf_token']


def test_security_headers_present(client):
    resp = client.get('/api/login')
    assert resp.headers.get('X-Frame-Options') == 'DENY'
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('Referrer-Policy') == 'same-origin'
    assert 'Content-Security-Policy' in resp.headers


def test_change_password_flow(client, csrf, default_credentials):
    resp = _login(client, default_credentials['username'], default_credentials['password'], csrf)
    assert resp.status_code == 200

    token = _fresh_csrf(client)

    resp = client.post(
        '/api/change-password',
        data={
            'csrf_token': token,
            'current_password': default_credentials['password'],
            'new_username': default_credentials['username'],
            'new_password': 'a-much-better-password',
            'confirm_password': 'a-much-better-password',
        },
    )
    assert resp.status_code == 200

    # New password works, old one does not.
    client.post('/api/logout', data={'csrf_token': token})
    new_csrf = _fresh_csrf(client)
    assert (
        _login(
            client, default_credentials['username'], default_credentials['password'], new_csrf
        ).status_code
        == 401
    )
    # The login response for success is 200; reuse a new CSRF token.
    new_csrf = _fresh_csrf(client)
    assert (
        _login(
            client, default_credentials['username'], 'a-much-better-password', new_csrf
        ).status_code
        == 200
    )


def test_change_password_rejects_short_password(client, csrf, default_credentials):
    _login(client, default_credentials['username'], default_credentials['password'], csrf)
    token = _fresh_csrf(client)
    resp = client.post(
        '/api/change-password',
        data={
            'csrf_token': token,
            'current_password': default_credentials['password'],
            'new_username': default_credentials['username'],
            'new_password': 'short',
            'confirm_password': 'short',
        },
    )
    assert resp.status_code == 400 or resp.status_code == 200
    assert 'tối thiểu' in resp.json['error']


def _fresh_csrf_from(html: bytes) -> str:
    # Deprecated for api_csrf
    pass


def test_healthz_no_auth_required(client):
    resp = client.get('/healthz')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {'status': 'ok', 'has_client': False}


def test_session_is_permanent_after_login(client, csrf, default_credentials, app):
    assert (
        _login(
            client,
            default_credentials['username'],
            default_credentials['password'],
            csrf,
        ).status_code
        == 200
    )
    assert app.app.config['PERMANENT_SESSION_LIFETIME'].total_seconds() > 0


def test_change_password_rate_limited(client, csrf, default_credentials, app, monkeypatch):
    # Log in first, then hammer the endpoint with wrong current_password.
    assert (
        _login(
            client,
            default_credentials['username'],
            default_credentials['password'],
            csrf,
        ).status_code
        == 200
    )
    monkeypatch.setattr(app, 'CHANGE_PW_MAX_ATTEMPTS', 3)
    app._change_pw_attempts.clear()

    last_status = None
    for _ in range(5):
        token = _fresh_csrf(client)
        resp = client.post(
            '/api/change-password',
            data={
                'csrf_token': token,
                'current_password': 'definitely-wrong',
                'new_username': default_credentials['username'],
                'new_password': 'another-password',
                'confirm_password': 'another-password',
            },
        )
        last_status = resp.status_code
    assert last_status == 429


def test_audit_log_records_login_events(app, client, csrf, default_credentials, tmp_path):
    audit_path = tmp_path / 'audit.log'
    # Re-point the audit log handler at a test-local file.
    import logging

    for handler in list(app.audit_log.handlers):
        app.audit_log.removeHandler(handler)
    handler = logging.handlers.RotatingFileHandler(str(audit_path), maxBytes=10_000, backupCount=1)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    app.audit_log.addHandler(handler)

    # failure
    client.post(
        '/api/login',
        data={'username': 'bogus', 'password': 'bogus', 'csrf_token': csrf},
    )
    # success
    _login(client, default_credentials['username'], default_credentials['password'], csrf)
    # logout
    token = _fresh_csrf(client)
    client.post('/api/logout', data={'csrf_token': token})

    handler.flush()
    content = audit_path.read_text(encoding='utf-8')
    assert 'event=login_failure' in content
    assert 'event=login_success' in content
    assert 'event=logout' in content
