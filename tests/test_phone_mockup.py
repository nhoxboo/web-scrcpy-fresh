"""Tests for the phone-mockup frame around the video.

The mockup wraps the scrcpy <video> in:
  - A bezel (`.phone-shell`, already existed)
  - Side-rail hardware keys: Power / Vol+ / Vol- (`/api/adb/sendevent`)
  - Bottom soft nav bar: Back / Home / Recent (`/api/quick`)

These tests are structural — they don't run JS, they just slice the
inline template to verify:
  - The mockup buttons exist with the right data-* attributes
  - The redundant Quick Controls buttons (Home/Back/Recent + Vol+/Vol-/Mute
    + their hw siblings) have been removed
  - The click dispatcher (`runControlBtn`) routes /api/quick and
    /api/adb/sendevent correctly and is bound to BOTH `.qc-btn` and
    `.side-key, .nav-key` selectors
  - All bindings live OUTSIDE `attachInput(...)` so they work even when
    scrcpy hasn't connected yet (same invariant as PR #20).
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / 'templates' / 'index.html'


def _read() -> str:
    return INDEX_HTML.read_text(encoding='utf-8')


def _inline_script() -> str:
    text = _read()
    blocks = re.findall(r'<script[^>]*>(.*?)</script>', text, flags=re.DOTALL)
    blocks = [b for b in blocks if b.strip()]
    assert blocks
    return max(blocks, key=len)


def _function_body(js: str, name: str) -> str:
    m = re.search(rf'function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{', js)
    assert m, f'function {name} not found'
    start = m.end()
    depth = 1
    i = start
    while i < len(js) and depth > 0:
        c = js[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    assert depth == 0
    return js[start : i - 1]


# ---- HTML structure ---------------------------------------------------------


def test_phone_mockup_wrapper_exists():
    html = _read()
    assert 'class="phone-mockup"' in html
    assert 'id="phoneMockup"' in html


def test_side_keys_exist_with_sendevent_ops():
    html = _read()
    # The three side keys must use /api/adb/sendevent (raw kernel input).
    # data-sendevent matches the server whitelist in app.SENDEVENT_OPS.
    for op in ('power', 'vol_up', 'vol_down'):
        assert f'data-sendevent="{op}"' in html, f'side key for {op} missing'
    assert 'class="side-key side-key-power"' in html
    assert 'class="side-key side-key-volup"' in html
    assert 'class="side-key side-key-voldown"' in html


def test_nav_bar_exists_with_quick_ops():
    html = _read()
    # The three soft nav keys must use /api/quick (input keyevent).
    nav_block = re.search(
        r'<div class="phone-nav-bar"[^>]*>(.*?)</div>',
        html,
        flags=re.DOTALL,
    )
    assert nav_block, '.phone-nav-bar block not found'
    body = nav_block.group(1)
    for act in ('back', 'home', 'recent'):
        assert f'data-act="{act}"' in body, f'nav key for {act} missing'


def test_quick_controls_no_longer_has_moved_buttons():
    """The buttons we moved to the mockup must NOT also appear in the QC panel."""
    html = _read()
    # Slice out the qc-grid block so we don't false-positive on the mockup HTML.
    m = re.search(r'<div class="qc-grid">(.*?)</div>', html, flags=re.DOTALL)
    assert m, 'qc-grid block not found'
    grid = m.group(1)
    # Removed: home, back, recent (nav) + vol_up, vol_down, mute (soft volume).
    for removed in ('home', 'back', 'recent', 'vol_up', 'vol_down', 'mute'):
        assert f'data-act="{removed}"' not in grid, (
            f'{removed!r} still in Quick Controls — should have been moved to mockup'
        )
    # Removed: vol_up, vol_down, power hw variants.
    for removed in ('vol_up', 'vol_down', 'power'):
        assert f'data-sendevent="{removed}"' not in grid, (
            f'hw {removed!r} still in Quick Controls — should have been moved'
        )


def test_remaining_quick_controls_buttons_still_present():
    """Sanity: Lock / Wake / Wi-Fi / BT / etc. were NOT removed."""
    html = _read()
    m = re.search(r'<div class="qc-grid">(.*?)</div>', html, flags=re.DOTALL)
    assert m
    grid = m.group(1)
    for kept in ('lock', 'wake', 'wifi_on', 'bt_on', 'data_on', 'reboot'):
        assert f'data-act="{kept}"' in grid, f'{kept!r} accidentally removed from Quick Controls'


# ---- JS dispatcher ----------------------------------------------------------


def test_run_control_btn_dispatcher_exists():
    js = _inline_script()
    assert re.search(r'(async\s+)?function\s+runControlBtn\s*\(', js), (
        'shared dispatcher `runControlBtn(btn, onOutput)` missing'
    )


def test_dispatcher_routes_sendevent_vs_quick():
    js = _inline_script()
    body = _function_body(js, 'runControlBtn')
    # Sendevent path posts to /api/adb/sendevent with `op`.
    assert "'/api/adb/sendevent'" in body
    assert "fd.append('op', sendevent)" in body
    # data-act path posts to /api/quick with `action`.
    assert "'/api/quick'" in body
    assert "fd.append('action', act)" in body


def test_side_keys_and_nav_keys_are_bound_via_dispatcher():
    js = _inline_script()
    assert ".side-key, .nav-key" in js or '.nav-key, .side-key' in js, (
        'side/nav buttons must be wired up via querySelectorAll'
    )
    # Both selectors must call runControlBtn.
    bind_block = re.search(
        r"querySelectorAll\(['\"]\.side-key,\s*\.nav-key['\"]\)[\s\S]{0,400}runControlBtn",
        js,
    )
    assert bind_block, 'side-key / nav-key click handler does not call runControlBtn'


def test_mockup_button_bindings_live_outside_attach_input():
    """Like the PR #20 regression test: these buttons must work without a
    live scrcpy stream. If their bindings ended up inside attachInput, they
    would be dead until screen_size arrives from the server."""
    js = _inline_script()
    body = _function_body(js, 'attachInput')
    assert '.side-key, .nav-key' not in body
    assert '.nav-key, .side-key' not in body
    assert 'runControlBtn' not in body
