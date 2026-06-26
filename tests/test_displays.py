"""Tests for display listing and parsing logic."""

from __future__ import annotations

from app import parse_displays


def test_parse_displays_dumpsys_window():
    output = """
WINDOW MANAGER DISPLAYS (dumpsys window displays)
  Display #0
    mDisplayId=0
    mDisplayInfo=DisplayInfo{"Built-in Screen", uniqueId "local:0", app 1080 x 2340, real 1080 x 2340, largest app 1080 x 2340, smallest app 1080 x 2340, mode 1, defaultMode 1, modes [{id=1, width=1080, height=2340, fps=60.0}], colorMode 0, hdrCapabilities null, rotation 0, density 420, layerStack 0, appWidth 1080, appHeight 2340, name Built-in Screen}
  Display #2
    mDisplayId=2
    mDisplayInfo=DisplayInfo{"Virtual Display", uniqueId "virtual:2", app 1920 x 1080, real 1920 x 1080, largest app 1920 x 1080, name Virtual Display}
"""
    displays = parse_displays(output)
    assert len(displays) == 2
    assert displays[0]['id'] == 0
    assert "Built-in Screen" in displays[0]['name']
    assert displays[0]['info'] == "1080x2340"

    assert displays[1]['id'] == 2
    assert "Virtual Display" in displays[1]['name']
    assert displays[1]['info'] == "1920x1080"


def test_parse_displays_dumpsys_display():
    output = """
DISPLAY MANAGER (dumpsys display)
  mDisplayId=0
    mDisplayDevices=
      DisplayDeviceInfo{"Built-in Screen": uniqueId="local:0", 1080 x 2400, ...}
  mDisplayId=2
    mDisplayDevices=
      DisplayDeviceInfo{"Virtual Display": uniqueId="virtual:2", 1920 x 1080, ...}
"""
    displays = parse_displays(output)
    assert len(displays) == 2
    assert displays[0]['id'] == 0
    assert "Built-in Screen" in displays[0]['name']
    assert displays[0]['info'] == "1080x2400"

    assert displays[1]['id'] == 2
    assert "Virtual Display" in displays[1]['name']
    assert displays[1]['info'] == "1920x1080"


def test_parse_displays_fallback_empty():
    displays = parse_displays("")
    assert len(displays) == 1
    assert displays[0]['id'] == 0
    assert "Mặc định" in displays[0]['name']


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


def test_api_adb_displays_requires_login(client):
    r = client.get('/api/adb/displays')
    assert r.status_code == 302  # redirects to login


def test_api_adb_displays_success(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)

    # Mock adb_shell
    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        assert args == ['dumpsys', 'window', 'displays'] or args == ['dumpsys', 'display']
        if args == ['dumpsys', 'window', 'displays']:
            return (
                True,
                'Display #0\nmDisplayId=0\nDisplayInfo{"Built-in Screen", real 1080 x 2400}',
            )
        return False, 'error'

    monkeypatch.setattr(app, 'adb_shell', fake_shell)

    r = client.get('/api/adb/displays')
    assert r.status_code == 200
    assert r.json['ok'] is True
    assert len(r.json['displays']) == 1
    assert r.json['displays'][0]['id'] == 0
    assert "Built-in Screen" in r.json['displays'][0]['name']
