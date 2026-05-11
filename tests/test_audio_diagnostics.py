"""Tests for the audio diagnostics panel (Ctrl+Shift+A).

When audio fails to play in production, screenshots of the DevTools
Console are slow to obtain and easy to crop wrong. The panel renders
the live ``_audioState`` directly in the page so the user can take a
single screenshot showing which step in the pipeline broke
(codec parsed? ASC extracted? frames fed to JMuxer? play() rejected?).

These tests pin the panel's structure so a refactor doesn't silently
drop fields, breaking our ability to debug user reports.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / 'templates' / 'index.html'
GLASS_CSS = Path(__file__).resolve().parent.parent / 'static' / 'css' / 'glass.css'


def test_audio_diag_panel_present_and_hidden_by_default():
    html = INDEX_HTML.read_text(encoding='utf-8')
    assert re.search(
        r'<div\s+id="audioDiag"[^>]*\bhidden\b',
        html,
    ), 'audioDiag panel must exist in the DOM and start hidden'


def test_audio_diag_panel_exposes_required_fields():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # Every observable point in the pipeline must be reflected in the
    # panel — that's what makes "share a screenshot" a useful debug ask.
    required_ids = [
        'adEnabled',
        'adStage',
        'adCodec',
        'adAsc',
        'adFrames',
        'adMux',
        'adMs',
        'adAudio',
        'adPlay',
        'adPrimed',
        'adErr',
    ]
    for slot_id in required_ids:
        assert f'id="{slot_id}"' in html, (
            f'audioDiag panel must expose <span id="{slot_id}"> so the '
            'refresh helper can render this field'
        )


def test_audio_diag_panel_has_action_buttons():
    html = INDEX_HTML.read_text(encoding='utf-8')
    assert 'id="adForcePlay"' in html, (
        'panel must have a Force play() button so the user can retry '
        'audioEl.play() without reloading'
    )
    assert 'id="adReset"' in html, (
        'panel must have a Reset audio button so a stuck JMuxer/MediaSource '
        'can be torn down + recreated without reloading'
    )


def test_inline_script_wires_ctrl_shift_a_toggle():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # The keyboard handler MUST check both ctrl+shift and meta+shift so
    # Linux/Windows users (Ctrl) and macOS users (Cmd) both work.
    # We pin both conditions and the letter A.
    assert re.search(
        r'\(e\.ctrlKey \|\| e\.metaKey\) && e\.shiftKey',
        html,
    ), 'panel toggle must accept Ctrl+Shift OR Cmd+Shift'
    assert re.search(
        r"e\.key === 'A' \|\| e\.key === 'a'",
        html,
    ), 'panel toggle must bind to the A key (uppercase + lowercase)'


def test_audio_state_object_has_diagnostic_fields():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # `_audioState` is the single source of truth for the panel + the
    # `window.__scrcpyAudio` debug handle. Pin its shape so a refactor
    # doesn't drop a field the panel renders.
    for field in (
        'enabled',
        'primed',
        'codec',
        'asc',
        'framesConfig',
        'framesData',
        'framesFedToMux',
        'bytesReceived',
        'msState',
        'playState',
        'lastError',
        'lastStage',
    ):
        assert re.search(
            r'\b' + re.escape(field) + r'\s*:',
            html,
        ), f'_audioState must contain {field!r} so the diag panel can render it'


def test_window_handle_for_devtools_inspection():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # Exposing `window.__scrcpyAudio` lets us walk a user through reading
    # state from DevTools even if the on-page panel is hidden / styled
    # off-screen by an extension.
    assert 'window.__scrcpyAudio' in html, (
        'inline script should expose window.__scrcpyAudio for DevTools'
    )


def test_diag_panel_css_loads():
    css = GLASS_CSS.read_text(encoding='utf-8')
    assert '.audio-diag' in css, 'panel must have CSS rules in glass.css'
    # The panel uses a monospace font so values stay tabular & readable.
    assert 'monospace' in css.lower(), 'panel should use monospace font'
