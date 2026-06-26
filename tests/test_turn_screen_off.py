"""Tests for the `--turn-screen-off` (`-S`) option exposed to the web UI.

scrcpy ships a `--turn-screen-off` / `-S` flag that lets the user control
the device while its physical screen stays black — handy when the phone
sits in a drawer and you don't want to drain the OLED. We expose the same
knob to the browser via a toolbar toggle and a `?turn_screen_off=1`
socket.io query parameter. The server then sends a SET_DISPLAY_POWER(off)
control message right after the control socket connects.

Three layers pinned here:

1. **Server** (`handle_connect`) reads the query param, falls back to the
   env-wide default when absent, and forwards a `turn_screen_off=` kwarg
   to the Scrcpy constructor.
2. **Scrcpy core** carries the flag on the instance so the runtime knows
   to send the SET_DISPLAY_POWER message.
3. **Browser** template has the toolbar toggle, persists the choice in
   localStorage, threads it into the socket query, and does a soft
   reconnect (no `location.reload()`) — same pattern as the audio toggle.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / 'templates' / 'index.html'
APP_PY = Path(__file__).resolve().parent.parent / 'app.py'
SCRCPY_PY = Path(__file__).resolve().parent.parent / 'scrcpy.py'


def _connect_with(app, monkeypatch, **socket_args):
    """Drive handle_connect with the given query params and capture kwargs.

    Mirrors the helper in test_stream_quality so the two test modules
    stay in lockstep — same monkeypatch dance, same captured dict shape.
    """
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
    builder = EnvironBuilder(method='GET', query_string=socket_args)
    env = builder.get_environ()
    with app.app.request_context(env):
        flask.session['authenticated'] = True
        monkeypatch.setattr(
            app.socketio, 'start_background_task', lambda *a, **k: None, raising=False
        )
        flask.request.sid = 'sid-test'  # type: ignore[attr-defined]
        app.scpy_ctx = None
        app.client_sid = None
        app.handle_connect()
    return captured


# ---------- server side --------------------------------------------------------


def test_server_forwards_turn_screen_off_when_query_set(app, monkeypatch):
    cap = _connect_with(app, monkeypatch, turn_screen_off='1')
    assert cap['ctor']['turn_screen_off'] is True, (
        f'expected turn_screen_off=True when ?turn_screen_off=1; got {cap["ctor"]!r}'
    )


def test_server_accepts_truthy_aliases(app, monkeypatch):
    for value in ('true', 'yes', 'on', 'TRUE'):
        cap = _connect_with(app, monkeypatch, turn_screen_off=value)
        assert cap['ctor']['turn_screen_off'] is True, (
            f'expected {value!r} to be truthy; got {cap["ctor"]!r}'
        )


def test_server_treats_zero_as_off(app, monkeypatch):
    cap = _connect_with(app, monkeypatch, turn_screen_off='0')
    assert cap['ctor']['turn_screen_off'] is False, (
        f'expected ?turn_screen_off=0 to be False; got {cap["ctor"]!r}'
    )


def test_server_default_off_when_param_missing(app, monkeypatch):
    # SCRCPY_TURN_SCREEN_OFF is not set in the test env, so the
    # env-wide default is False — same as upstream scrcpy.
    cap = _connect_with(app, monkeypatch)
    assert cap['ctor']['turn_screen_off'] is False, (
        f'expected default-off when no query param + no env var; got {cap["ctor"]!r}'
    )


# ---------- scrcpy.py source: control-message wiring exists --------------------


def test_scrcpy_module_defines_set_display_power_message_type():
    src = SCRCPY_PY.read_text(encoding='utf-8')
    assert 'CONTROL_MSG_TYPE_SET_DISPLAY_POWER' in src, (
        'expected the SET_DISPLAY_POWER message-type constant in scrcpy.py'
    )
    # scrcpy v3.3.x assigns message type 10 to SET_DISPLAY_POWER. Pin the
    # constant so an accidental renumber doesn't silently send the wrong
    # control opcode to the device.
    assert re.search(r'CONTROL_MSG_TYPE_SET_DISPLAY_POWER\s*=\s*10', src), (
        'expected CONTROL_MSG_TYPE_SET_DISPLAY_POWER = 10 (scrcpy v3.3.x value)'
    )


def test_scrcpy_init_accepts_turn_screen_off_kwarg():
    src = SCRCPY_PY.read_text(encoding='utf-8')
    assert 'turn_screen_off: bool = False' in src, (
        'expected the Scrcpy.__init__ signature to carry turn_screen_off=False'
    )
    assert 'self.turn_screen_off' in src, (
        'expected the flag to be stored on the instance for scrcpy_start to read'
    )


def test_scrcpy_start_emits_set_display_power_off_when_enabled():
    src = SCRCPY_PY.read_text(encoding='utf-8')
    # The control message is a 2-byte payload: [TYPE, value]. value 0 = off.
    # We check that scrcpy_start (or a helper it calls) sends those bytes
    # gated on self.turn_screen_off — without this branch the toolbar
    # toggle would be cosmetic.
    assert re.search(
        r'if\s+self\.turn_screen_off',
        src,
    ), 'expected an `if self.turn_screen_off:` branch that sends the control message'
    assert 'CONTROL_MSG_TYPE_SET_DISPLAY_POWER' in src
    assert 'scrcpy_send_control' in src


# ---------- browser side -------------------------------------------------------


def test_template_has_turn_screen_off_toolbar_button():
    html = INDEX_HTML.read_text(encoding='utf-8')
    assert 'id="screenOffToggle"' in html, (
        'expected #screenOffToggle button in the toolbar — without it the '
        'feature has no UI affordance'
    )


def test_template_persists_turn_screen_off_in_localstorage():
    html = INDEX_HTML.read_text(encoding='utf-8')
    assert "localStorage.getItem('turnScreenOff')" in html, (
        'expected localStorage key turnScreenOff so the choice survives reloads'
    )
    assert "localStorage.setItem('turnScreenOff'" in html, (
        'expected the toggle handler to write back to localStorage'
    )


def test_template_threads_turn_screen_off_into_socket_query():
    html = INDEX_HTML.read_text(encoding='utf-8')
    assert 'turn_screen_off' in html, (
        'expected the socket.io query assembly to include turn_screen_off'
    )


def test_template_soft_reconnects_on_screen_off_toggle_not_reload():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # Find the screenOffToggle click-handler block. We anchor on the
    # marker comment so we don't accidentally pick up other handlers.
    m = re.search(
        r"if\s*\(\s*screenOffBtn\s*\)\s*\{\s*screenOffBtn\.addEventListener\(\s*'click'\s*,\s*\(\)\s*=>\s*\{",
        html,
    )
    assert m, 'expected screenOffBtn click handler in the template'
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
    body = html[start : i - 1]
    assert 'socket.disconnect()' in body, (
        'screen-off toggle must do a soft reconnect (socket.disconnect)'
    )
    assert 'socket.connect()' in body, 'screen-off toggle must do a soft reconnect (socket.connect)'
    assert 'location.reload' not in body, (
        'screen-off toggle must NOT reload the page — would drop user-activation '
        'and break the audio gate (see PR #37)'
    )


# ---------- app.py source: CLI + env wiring exists -----------------------------


def test_app_exposes_env_default_for_turn_screen_off():
    src = APP_PY.read_text(encoding='utf-8')
    assert 'SCRCPY_TURN_SCREEN_OFF' in src, (
        'expected SCRCPY_TURN_SCREEN_OFF env var as an admin-level default'
    )
    assert 'turn_screen_off_default' in src, (
        'expected a turn_screen_off_default module-level variable'
    )


def test_app_exposes_cli_flag_for_turn_screen_off():
    src = APP_PY.read_text(encoding='utf-8')
    # The CLI flag mirrors the upstream scrcpy short option `-S`.
    assert '--turn_screen_off' in src
    assert "'-S'" in src, "expected the short flag '-S' so the CLI matches scrcpy's upstream UX"
