"""Tests for the UHID gamepad bridge.

When the gamepad toolbar toggle is ON, the page polls the browser's
Gamepad API every animation frame, diffs state vs. the last sent report,
and forwards UHID_INPUT messages over the scrcpy control socket so a
real controller plugged into the user's PC shows up as a generic HID
gamepad on the Android device.

These tests pin the bits a refactor is most likely to break:

* The toolbar button + persistent localStorage flag.
* The HID descriptor (Generic Desktop / Game Pad with 17 buttons + 4
  axes + 2 analog triggers).
* The connect / disconnect / poll plumbing on `ScrcpyInput`.
* The 13-byte report layout — bit positions for the buttons and i16
  axes order.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / 'templates' / 'index.html'
INPUT_JS = Path(__file__).resolve().parent.parent / 'static' / 'js' / 'input.js'


# ---------- HTML / template ----------------------------------------------------


def test_template_has_gamepad_toolbar_button():
    html = INDEX_HTML.read_text(encoding='utf-8')
    assert 'id="gamepadInput"' in html, (
        'expected #gamepadInput toolbar button so users can opt into gamepad'
    )
    # Title should be Vietnamese and mention "Gamepad" so users can find it.
    btn = re.search(r'<(?:button|div)[^>]*id=\"gamepadInput\"[^>]*>', html)
    assert btn, 'gamepad button tag not found'
    assert 'Gamepad' in btn.group(0) or 'Tay cầm' in btn.group(0) or 'Tay' in btn.group(0), (
        'gamepad button title must mention Gamepad'
    )


def test_template_persists_gamepad_toggle_in_localstorage():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # We persist with the key `gamepadInput` (matches the element id for
    # discoverability when debugging). The toggle reads + writes it.
    assert "localStorage.getItem('gamepadInput')" in html
    assert "localStorage.setItem('gamepadInput'" in html


def test_template_wires_enable_disable_gamepad_input():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # Soft toggle: the click handler should call enableGamepadInput /
    # disableGamepadInput on the ScrcpyInput instance — no page reload.
    assert 'input.enableGamepadInput()' in html
    assert 'input.disableGamepadInput()' in html
    # And attachInput should also pick up the persisted state on connect.
    assert re.search(r'if\s*\(gamepadOn\)', html), (
        'attachInput should call enableGamepadInput() when localStorage has it ON'
    )


# ---------- JS / HID descriptor ------------------------------------------------


def test_input_js_defines_gamepad_descriptor():
    js = INPUT_JS.read_text(encoding='utf-8')
    assert 'UHID_GAMEPAD_DESCRIPTOR' in js
    # Generic Desktop usage page (0x05, 0x01) + Game Pad usage (0x09, 0x05)
    # is the magic prefix Android InputManager looks for.
    assert re.search(r'0x05,\s*0x01,', js)
    assert re.search(r'0x09,\s*0x05,', js)
    # 17 buttons: Button Usage Page 0x09 with min 1, max 0x11.
    assert re.search(r'0x29,\s*0x11', js), 'gamepad descriptor must declare 17 buttons (0x11)'


def test_input_js_has_enable_and_disable_gamepad_methods():
    js = INPUT_JS.read_text(encoding='utf-8')
    assert re.search(r'enableGamepadInput\s*\(\s*\)\s*\{', js), (
        'expected ScrcpyInput.enableGamepadInput() method'
    )
    assert re.search(r'disableGamepadInput\s*\(\s*\)\s*\{', js), (
        'expected ScrcpyInput.disableGamepadInput() method'
    )


def test_input_js_listens_for_connect_disconnect_events():
    js = INPUT_JS.read_text(encoding='utf-8')
    # The browser Gamepad API only fires these two events; everything else
    # has to be polled via navigator.getGamepads(). Both must be wired.
    assert "'gamepadconnected'" in js
    assert "'gamepaddisconnected'" in js
    # Per-frame poll is the spec-mandated way to read button/axis state.
    assert 'requestAnimationFrame' in js, (
        'gamepad polling must use requestAnimationFrame so it is throttled '
        'with the display refresh rate'
    )


def test_input_js_diffs_state_before_sending():
    js = INPUT_JS.read_text(encoding='utf-8')
    # The HID input report is only sent on change — without diffing we'd
    # flood the device with identical 60 reports/sec.
    assert '_byteArraysEqual' in js, (
        'expected a _byteArraysEqual() helper to diff reports before sending'
    )
    assert '_uhidGamepadLastReport' in js, 'expected per-controller last-report cache for the diff'


def test_input_js_supports_up_to_four_controllers():
    js = INPUT_JS.read_text(encoding='utf-8')
    # The UHID IDs 1 and 2 are reserved for keyboard + mouse; controllers
    # take 3..6 so InputDevice IDs stay stable across reconnects.
    assert re.search(r'_uhidGamepadIds\s*=\s*\[3,\s*4,\s*5,\s*6\]', js), (
        'expected reserved UHID IDs 3..6 for up to four controllers'
    )


def test_input_js_builds_thirteen_byte_report():
    js = INPUT_JS.read_text(encoding='utf-8')
    # Pin the report builder so a layout change here is forced to update
    # the descriptor too: 13 bytes = 3 (buttons) + 8 (axes i16 × 4) + 2
    # (triggers u8 × 2).
    assert re.search(r'new\s+Uint8Array\(\s*13\s*\)', js), (
        'gamepad report must be exactly 13 bytes — descriptor depends on it'
    )
    # i16 little-endian axes at offsets 3, 5, 7, 9.
    for offset in (3, 5, 7, 9):
        assert re.search(rf'setInt16\(\s*{offset}\s*,', js), (
            f'expected setInt16 axis write at offset {offset}'
        )
