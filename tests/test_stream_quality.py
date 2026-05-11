"""Tests for the per-session Mbps / FPS override in Quick Controls.

The Quick Controls overlay now exposes two new controls — a video bitrate
slider (1..100 Mbps) and a max-FPS slider (15..120) — that the browser
threads into the socket.io connect query as `video_bit_rate` (bits/sec)
and `max_fps`. The server validates the range and clamps; out-of-range
values are silently ignored (the server-side default wins).

These tests pin both halves:

1. **Server** (`handle_connect`) accepts and applies in-range params,
   silently ignores out-of-range ones, and persists the chosen value
   onto the Scrcpy stub instance for later assertions.
2. **Browser** template renders the slider + input + Apply button + at
   least one preset, threads localStorage into the socket query, and
   wires the Apply click handler to a soft reconnect (not a full page
   reload — see PR #37 for why we avoid `location.reload()`).
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / 'templates' / 'index.html'
APP_PY = Path(__file__).resolve().parent.parent / 'app.py'


def _login(client, csrf, default_credentials):
    return client.post(
        '/login',
        data={**default_credentials, 'csrf_token': csrf},
        follow_redirects=False,
    )


def _connect_with(app, monkeypatch, **socket_args):
    # Re-import a fresh app module per call so the global scpy_ctx /
    # client_sid don't leak across cases. The flask_socketio test client
    # is a bit fiddly with auth + query strings, so we exercise the
    # server-side handler directly by faking the request context.
    import flask
    from werkzeug.test import EnvironBuilder

    captured = {}

    class FakeCtx:
        device_message_callback = None

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            captured['ctor'] = kwargs

        def scrcpy_start(self, video_callback, video_bit_rate, max_fps=None, audio_callback=None):
            captured['video_bit_rate'] = video_bit_rate
            captured['max_fps'] = max_fps

        def scrcpy_stop(self):
            pass

    monkeypatch.setattr(app, 'Scrcpy', FakeCtx)
    monkeypatch.setattr(app, '_selected_serial', lambda: None)
    # Drive handle_connect manually inside an authed test context so we
    # can assert on what it forwards to Scrcpy.scrcpy_start.
    builder = EnvironBuilder(method='GET', query_string=socket_args)
    env = builder.get_environ()
    with app.app.request_context(env):
        flask.session['authenticated'] = True
        # request.sid is set by flask_socketio normally; the handle_connect
        # path also calls socketio.start_background_task which we want to
        # no-op so the test stays synchronous.
        monkeypatch.setattr(
            app.socketio, 'start_background_task', lambda *a, **k: None, raising=False
        )
        flask.request.sid = 'sid-test'  # type: ignore[attr-defined]
        # Reset module-level singletons that other tests may have stamped.
        app.scpy_ctx = None
        app.client_sid = None
        app.handle_connect()
    return captured


# ---------- server side --------------------------------------------------------


def test_server_uses_query_video_bit_rate(app, monkeypatch):
    # 12 Mbps = 12_000_000 bps, well inside the 500k..200M server range.
    cap = _connect_with(app, monkeypatch, video_bit_rate='12000000')
    assert cap['video_bit_rate'] == '12000000', (
        f'expected the in-range query bit rate to be forwarded; got {cap["video_bit_rate"]!r}'
    )


def test_server_uses_query_max_fps(app, monkeypatch):
    cap = _connect_with(app, monkeypatch, max_fps='90')
    assert cap['max_fps'] == '90', (
        f'expected the in-range query FPS to be forwarded; got {cap["max_fps"]!r}'
    )


def test_server_falls_back_to_default_for_out_of_range_bit_rate(app, monkeypatch):
    # 1 bps is clearly nonsense; the server should ignore it and use the
    # default (8_000_000 from the env var fallback).
    cap = _connect_with(app, monkeypatch, video_bit_rate='1')
    assert cap['video_bit_rate'] == app.video_bit_rate, (
        f'out-of-range bit rate should fall back to default {app.video_bit_rate!r}; '
        f'got {cap["video_bit_rate"]!r}'
    )


def test_server_falls_back_to_default_for_out_of_range_fps(app, monkeypatch):
    cap = _connect_with(app, monkeypatch, max_fps='99999')
    assert cap['max_fps'] == app.max_fps, (
        f'out-of-range FPS should fall back to default {app.max_fps!r}; got {cap["max_fps"]!r}'
    )


def test_server_falls_back_to_default_for_garbage_input(app, monkeypatch):
    cap = _connect_with(app, monkeypatch, video_bit_rate='nope', max_fps='also-nope')
    assert cap['video_bit_rate'] == app.video_bit_rate
    assert cap['max_fps'] == app.max_fps


def test_server_default_when_nothing_supplied(app, monkeypatch):
    cap = _connect_with(app, monkeypatch)
    assert cap['video_bit_rate'] == app.video_bit_rate
    assert cap['max_fps'] == app.max_fps


# ---------- server-side source: sanity-check that the new code branch exists --


def test_app_handle_connect_handles_bit_rate_query():
    src = APP_PY.read_text(encoding='utf-8')
    assert 'video_bit_rate' in src
    # Range bounds: 500 kbps lower, 200 Mbps upper.
    assert '500_000' in src
    assert '200_000_000' in src


def test_app_handle_connect_handles_max_fps_query():
    src = APP_PY.read_text(encoding='utf-8')
    assert 'max_fps' in src
    # FPS range: 1..240. Above 240 isn't realistic on any phone today.
    assert re.search(r'1\s*<=\s*fps\s*<=\s*240', src), (
        'expected the 1..240 fps clamp in handle_connect'
    )


# ---------- browser side -------------------------------------------------------


def test_template_has_stream_quality_controls():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # Inputs: range slider + number input for both Mbps and FPS, plus the
    # Apply / Reset buttons. The slider IDs are pinned because the JS
    # handlers reference them by getElementById.
    for el_id in ('sqBitrate', 'sqBitrateNum', 'sqFps', 'sqFpsNum', 'sqApply', 'sqReset'):
        assert f'id="{el_id}"' in html, f'missing #{el_id} in Quick Controls'
    # At least one preset chip is wired so the user has a one-click default.
    assert 'class="sq-preset"' in html, 'expected at least one .sq-preset chip'


def test_template_threads_localstorage_into_socket_query():
    html = INDEX_HTML.read_text(encoding='utf-8')
    assert 'streamBitrateMbps' in html, (
        'expected localStorage key for the Mbps slider so values persist'
    )
    assert 'streamMaxFps' in html, 'expected localStorage key for the FPS slider'
    # Both pieces show up in the socket.io query string assembly.
    assert 'video_bit_rate' in html
    assert 'max_fps' in html


def _extract_arrow_body(html: str, name: str) -> str:
    """Extract a `const <name> = () => { ... };` arrow body (brace-balanced)."""
    m = re.search(rf"const\s+{re.escape(name)}\s*=\s*\(\s*\)\s*=>\s*\{{", html)
    assert m, f'expected `const {name} = () => {{ ... }};` arrow in template'
    start = m.end()
    depth = 1
    i = start
    while i < len(html) and depth > 0:
        c = html[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    assert depth == 0, f'unbalanced braces in arrow body {name}'
    return html[start : i - 1]


def test_template_soft_reconnects_on_apply_not_reload():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # The Apply path must call socket.disconnect() and socket.connect() so
    # the browser keeps its UI state (audio gate user-activation, UHID,
    # macro buffer, ...). A `location.reload()` here would undo PR #37.
    body = _extract_arrow_body(html, '_sqApply')
    assert 'socket.disconnect()' in body, 'soft reconnect on Apply must call socket.disconnect()'
    assert 'socket.connect()' in body, 'soft reconnect on Apply must call socket.connect()'
    assert 'location.reload' not in body, (
        'Apply must NOT reload the page — that would drop user-activation '
        'and break the audio gate (see PR #37)'
    )


def test_template_clamps_user_input_within_safe_ranges():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # The slider range is the visible safety net. Even if the user types a
    # huge number into the <input type=number>, the JS _clamp() helper
    # pins it to 1..100 Mbps and 15..120 FPS before the request goes out.
    assert re.search(r'min="1"\s+max="100"', html), '1..100 Mbps slider missing'
    assert re.search(r'min="15"\s+max="120"', html), '15..120 FPS slider missing'
    assert '_clamp' in html, (
        'expected a _clamp() helper so out-of-range numeric input is pinned to the slider range'
    )
