"""Tests for /api/adb/sendevent — raw hardware key injection.

Magisk module install scripts use `getevent` to read raw /dev/input/event*
key presses; soft `input keyevent` is invisible to them. These tests verify
that the sendevent endpoint:
  - Probes `getevent -lp` to discover the right /dev/input/eventX
  - Builds the correct su sendevent argv (down, sync, up, sync)
  - Rejects ops outside the whitelist (vol_up / vol_down / power)
  - Caches the discovered device per-serial so repeated presses skip probe
  - Requires login
"""

from __future__ import annotations

import shlex


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
    assert resp.status_code == 200
    m = re.search(rb'name="csrf-token" content="([^"]+)"', resp.data)
    assert m, 'meta csrf-token not found'
    return m.group(1).decode()


# Sample `getevent -lp` output from a Galaxy Z Fold 3 (representative).
# Two devices: a side-mounted gpio-keys with volume+power, and a hall sensor.
_FAKE_GETEVENT = """\
add device 1: /dev/input/event0
  name:     "hall-sensor"
  events:
    KEY (0001): KEY_F1
add device 2: /dev/input/event2
  name:     "gpio-keys"
  events:
    KEY (0001): KEY_VOLUMEDOWN         KEY_VOLUMEUP           KEY_POWER
add device 3: /dev/input/event5
  name:     "uinput-fpc"
  events:
    KEY (0001): KEY_WAKEUP
"""


def _patch_shell(monkeypatch, app, *, getevent_output=_FAKE_GETEVENT, fail=False):
    """Return a list that captures every adb_shell call argv."""
    calls: list[dict] = []

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        calls.append({'args': list(args), 'serial': serial})
        if args == ['getevent', '-lp']:
            return (not fail), getevent_output
        # sendevent — succeed
        return True, ''

    monkeypatch.setattr(app, 'adb_shell', fake_shell)
    return calls


def test_sendevent_unknown_op_400(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post('/api/adb/sendevent', data={'op': 'rm_rf', 'csrf_token': tok})
    assert r.status_code == 400
    assert r.json['ok'] is False


def test_sendevent_missing_op_400(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)
    r = client.post('/api/adb/sendevent', data={'csrf_token': tok})
    assert r.status_code == 400


def test_sendevent_requires_login(client, csrf):
    # CSRF guard runs before login_required, so we attach a valid token.
    r = client.post('/api/adb/sendevent', data={'op': 'vol_up', 'csrf_token': csrf})
    assert r.status_code in (302, 401)


def test_sendevent_vol_up_builds_correct_argv(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    app._sendevent_dev_cache.clear()
    calls = _patch_shell(monkeypatch, app)
    tok = _post_csrf(client)
    r = client.post('/api/adb/sendevent', data={'op': 'vol_up', 'csrf_token': tok})
    assert r.status_code == 200, r.json
    assert r.json['ok'] is True
    # First call is getevent -lp probe; second is the su sendevent.
    assert calls[0]['args'] == ['getevent', '-lp']
    assert calls[1]['args'][0] == 'su'
    assert calls[1]['args'][1] == '-c'
    # KEY_VOLUMEUP = 115, EV_KEY = 1, EV_SYN = 0.
    expected_inner = (
        'sendevent /dev/input/event2 1 115 1;'
        'sendevent /dev/input/event2 0 0 0;'
        'sendevent /dev/input/event2 1 115 0;'
        'sendevent /dev/input/event2 0 0 0'
    )
    # The arg must be shell-quoted so that when `adb shell` flattens the
    # argv it stays as one token reaching `su -c`. Without quoting, only
    # the first `sendevent` runs as root and the rest fall back to the
    # non-root outer shell (→ Permission denied on /dev/input/*).
    assert calls[1]['args'][2] == shlex.quote(expected_inner)


def test_sendevent_vol_down_uses_keycode_114(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    app._sendevent_dev_cache.clear()
    calls = _patch_shell(monkeypatch, app)
    tok = _post_csrf(client)
    r = client.post('/api/adb/sendevent', data={'op': 'vol_down', 'csrf_token': tok})
    assert r.status_code == 200
    inner_arg = calls[1]['args'][2]
    assert '1 114 1' in inner_arg and '1 114 0' in inner_arg


def test_sendevent_power_uses_keycode_116(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    app._sendevent_dev_cache.clear()
    calls = _patch_shell(monkeypatch, app)
    tok = _post_csrf(client)
    r = client.post('/api/adb/sendevent', data={'op': 'power', 'csrf_token': tok})
    assert r.status_code == 200
    inner_arg = calls[1]['args'][2]
    assert '1 116 1' in inner_arg and '1 116 0' in inner_arg


def test_sendevent_inner_is_quoted_so_adb_join_survives(
    client, csrf, default_credentials, app, monkeypatch
):
    """Regression for the `su -c` permission-denied bug.

    `adb shell A B C` joins A/B/C with single spaces over the wire WITHOUT
    re-quoting. If we hand `['su', '-c', 'cmd1;cmd2']` to adb, the device
    receives `su -c cmd1;cmd2`, which sh tokenises as:
        su -c cmd1     (root) -- runs only cmd1
        cmd2           (uid=shell, 2000) -- denied on /dev/input
    The fix is to pre-quote the `cmd1;cmd2` argument so the join produces
    `su -c 'cmd1;cmd2'`, i.e. the whole payload reaches root.
    This test asserts the dispatched arg starts AND ends with a quote
    character and survives a round-trip through shlex.split as a single
    token.
    """
    _login(client, csrf, default_credentials)
    app._sendevent_dev_cache.clear()
    calls = _patch_shell(monkeypatch, app)
    tok = _post_csrf(client)
    r = client.post('/api/adb/sendevent', data={'op': 'vol_up', 'csrf_token': tok})
    assert r.status_code == 200, r.json
    sendevent_arg = calls[1]['args'][2]
    # Quoted form: starts + ends with the same quote char.
    assert sendevent_arg[0] in {"'", '"'}, sendevent_arg
    assert sendevent_arg[-1] == sendevent_arg[0], sendevent_arg
    # Simulate the device-side join: build the command line adb sends to
    # the device, then re-tokenise it the way `sh` would.
    joined = ' '.join(calls[1]['args'])  # e.g. "su -c 'sendevent ...;sendevent ...'"
    tokens = shlex.split(joined)
    # Must round-trip to exactly 3 tokens: [su, -c, full_inner].
    assert len(tokens) == 3, tokens
    assert tokens[0] == 'su' and tokens[1] == '-c'
    # The full multi-statement payload must survive as one shell token —
    # i.e. all four sendevent calls present, NOT broken into separate
    # statements that would run outside the su shell.
    assert tokens[2].count('sendevent') == 4, tokens[2]
    assert ';' in tokens[2]


def test_sendevent_caches_device_per_serial(client, csrf, default_credentials, app, monkeypatch):
    """Second press should skip the getevent probe."""
    _login(client, csrf, default_credentials)
    app._sendevent_dev_cache.clear()
    calls = _patch_shell(monkeypatch, app)
    tok = _post_csrf(client)
    # First press triggers probe.
    r1 = client.post('/api/adb/sendevent', data={'op': 'vol_up', 'csrf_token': tok})
    assert r1.status_code == 200
    n_after_first = len(calls)
    # Second press should NOT re-probe — cache hit.
    r2 = client.post('/api/adb/sendevent', data={'op': 'vol_up', 'csrf_token': tok})
    assert r2.status_code == 200
    n_after_second = len(calls)
    # Only one additional call (the sendevent), no second getevent.
    assert n_after_second - n_after_first == 1
    assert calls[-1]['args'][0] == 'su'


def test_sendevent_no_matching_device_returns_500(
    client, csrf, default_credentials, app, monkeypatch
):
    """If getevent -lp doesn't list a device with KEY_POWER, return error."""
    _login(client, csrf, default_credentials)
    app._sendevent_dev_cache.clear()
    # Strip the power line.
    bad_output = """\
add device 1: /dev/input/event0
  name:     "useless"
  events:
    KEY (0001): KEY_F1
"""
    _patch_shell(monkeypatch, app, getevent_output=bad_output)
    tok = _post_csrf(client)
    r = client.post('/api/adb/sendevent', data={'op': 'power', 'csrf_token': tok})
    assert r.status_code == 500
    assert r.json['ok'] is False
    assert 'không tìm được' in r.json['error'].lower() or 'not' in r.json['error'].lower()


def test_sendevent_getevent_failure_returns_500(
    client, csrf, default_credentials, app, monkeypatch
):
    _login(client, csrf, default_credentials)
    app._sendevent_dev_cache.clear()
    _patch_shell(monkeypatch, app, fail=True)
    tok = _post_csrf(client)
    r = client.post('/api/adb/sendevent', data={'op': 'vol_up', 'csrf_token': tok})
    assert r.status_code == 500
    assert r.json['ok'] is False


def test_find_event_device_parses_getevent_output(app):
    """Direct unit test for the parser helper."""
    app._sendevent_dev_cache.clear()

    captured = {}

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        captured['args'] = list(args)
        return True, _FAKE_GETEVENT

    app.adb_shell = fake_shell
    try:
        dev_vol = app._find_event_device(115, serial='abc123')
        dev_pwr = app._find_event_device(116, serial='abc123')
        dev_vd = app._find_event_device(114, serial='abc123')
    finally:
        # conftest's fake gets restored next test via monkeypatch fixture;
        # but we modified directly, so restore explicitly.
        import scrcpy

        app.adb_shell = scrcpy.adb_shell

    assert dev_vol == '/dev/input/event2'
    assert dev_pwr == '/dev/input/event2'
    assert dev_vd == '/dev/input/event2'
    # All three should be cached for the serial.
    cache = app._sendevent_dev_cache['abc123']
    assert cache[114] == '/dev/input/event2'
    assert cache[115] == '/dev/input/event2'
    assert cache[116] == '/dev/input/event2'


def test_find_event_device_falls_back_to_su_when_plain_probe_empty(app):
    """Some OEMs (Samsung Knox) hide /sys/class/input from the shell user.

    In that case plain `getevent -lp` returns empty/no `add device` lines,
    and we must retry under `su -c 'getevent -lp'` (also shell-quoted so
    `adb shell` doesn't shred it).
    """
    app._sendevent_dev_cache.clear()
    seen: list[list[str]] = []

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        seen.append(list(args))
        if args == ['getevent', '-lp']:
            # Knox blocks the non-root probe → empty body.
            return True, ''
        # The su fallback must arrive with a single shell-quoted arg,
        # otherwise adb's wire-side join would break it apart.
        if args[:2] == ['su', '-c']:
            assert args[2] == shlex.quote('getevent -lp'), args[2]
            return True, _FAKE_GETEVENT
        return False, ''

    app.adb_shell = fake_shell
    try:
        dev = app._find_event_device(115, serial='abc123')
    finally:
        import scrcpy

        app.adb_shell = scrcpy.adb_shell
    assert dev == '/dev/input/event2'
    # Plain probe attempted first, then su fallback.
    assert seen[0] == ['getevent', '-lp']
    assert seen[1][:2] == ['su', '-c']


def test_find_event_device_returns_none_when_missing(app):
    app._sendevent_dev_cache.clear()
    output = 'add device 1: /dev/input/event0\n  KEY (0001): KEY_F1\n'

    def fake_shell(args, serial=None, timeout=15.0, adb_path=None):  # noqa: ARG001
        return True, output

    app.adb_shell = fake_shell
    try:
        assert app._find_event_device(115) is None
    finally:
        import scrcpy

        app.adb_shell = scrcpy.adb_shell
