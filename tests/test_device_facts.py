from __future__ import annotations


def _login(client, csrf, credentials):
    response = client.post(
        '/login',
        data={
            'username': credentials['username'],
            'password': credentials['password'],
            'csrf_token': csrf,
        },
    )
    assert response.status_code == 302


def test_parse_battery_facts_extracts_level_and_status(app):
    assert app._parse_battery_facts('level: 83\nstatus: 2\n') == {
        'battery_percent': 83,
        'battery_status': 'charging',
    }


def test_device_facts_requires_login(client):
    assert client.get('/api/devices/test-serial/facts').status_code in (302, 401)


def test_device_facts_rejects_unselected_serial(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    response = client.get('/api/devices/not-selected/facts')
    assert response.status_code == 400
    assert response.get_json()['ok'] is False


def test_device_facts_returns_only_safe_parsed_values(
    client, csrf, default_credentials, app, monkeypatch
):
    _login(client, csrf, default_credentials)
    with client.session_transaction() as browser_session:
        browser_session['adb_serial'] = 'test-serial'

    def fake_adb_shell(args, serial=None, timeout=None):
        assert serial == 'test-serial'
        if args == ['getprop', 'ro.product.model']:
            return True, 'SM-F926B\n'
        if args == ['getprop', 'ro.build.version.release']:
            return True, '14\n'
        if args == ['dumpsys', 'battery']:
            return True, 'level: 83\nstatus: 2\nprivate host path: C:/hidden\n'
        raise AssertionError(args)

    monkeypatch.setattr(app, 'adb_shell', fake_adb_shell)
    response = client.get('/api/devices/test-serial/facts')
    assert response.status_code == 200
    assert response.get_json() == {
        'ok': True,
        'available': True,
        'facts': {
            'model': 'SM-F926B',
            'android_version': '14',
            'battery_percent': 83,
            'battery_status': 'charging',
        },
    }


def test_device_facts_hides_adb_failures(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    with client.session_transaction() as browser_session:
        browser_session['adb_serial'] = 'test-serial'
    monkeypatch.setattr(app, 'adb_shell', lambda *args, **kwargs: (False, 'C:/secret/output'))

    response = client.get('/api/devices/test-serial/facts')
    assert response.status_code == 200
    assert response.get_json() == {
        'ok': True,
        'available': False,
        'facts': {
            'model': None,
            'android_version': None,
            'battery_percent': None,
            'battery_status': None,
        },
    }
