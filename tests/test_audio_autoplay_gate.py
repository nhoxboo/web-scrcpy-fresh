"""Tests for the audio-autoplay gate on the panel page.

When the audio toolbar toggle is flipped on we `location.reload()` so the
server can restart scrcpy with `audio=true`. The reload drops the page's
user-activation state, so the `<audio autoplay>` attribute alone is not
enough to actually start playback in modern browsers (Chrome's autoplay
policy in particular). The fix is twofold and these tests pin both halves:

1. A `<div id="audioGate">` exists in the panel, hidden by default, ready
   to be shown only when `audioEl.play()` rejects with `NotAllowedError`.
2. The inline script attempts `audioEl.play()` after JMuxer attaches and
   wires a fallback document-level gesture listener to retry playback.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / 'templates' / 'index.html'


def test_audio_gate_present_and_hidden_by_default():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # Element exists.
    assert re.search(
        r'<div\s+id="audioGate"[^>]*\bhidden\b',
        html,
    ), 'audioGate element must be in the DOM and start hidden'
    # And bears its CSS class so glass.css styles it.
    assert 'class="audio-gate"' in html or "class='audio-gate'" in html, (
        'audioGate should use the .audio-gate class so glass.css styles it'
    )


def test_inline_script_calls_audio_play_with_autoplay_fallback():
    html = INDEX_HTML.read_text(encoding='utf-8')
    # Pin the call to play() and the NotAllowedError handling path so a
    # future refactor that drops the autoplay-block fallback fails CI.
    assert re.search(r'audioEl\.play\(\s*\)', html), (
        '<audio> playback must be triggered explicitly via audioEl.play()'
    )
    assert 'NotAllowedError' in html, (
        'autoplay block (NotAllowedError) must be handled with a user-'
        'gesture fallback so audio is not silently swallowed'
    )
    # And the fallback listens for ANY of the standard gestures, not just
    # mouse — touchscreen and keyboard users are real, and any of them
    # satisfies the autoplay activation requirement.
    for ev in ('click', 'keydown', 'touchstart'):
        assert ev in html, f'autoplay fallback must listen for {ev}'


def test_audio_gate_styling_loads_from_glass_css():
    css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'glass.css').read_text(
        encoding='utf-8'
    )
    # The gate must render as a centred, clickable surface — pin a few of
    # the styling intents so a future cleanup doesn't accidentally make it
    # invisible / non-interactive.
    assert '.audio-gate' in css
    assert 'cursor: pointer' in css.replace(' ', '').replace(
        ' ', ''
    ) or 'cursor:pointer' in css.replace(' ', '')
    assert 'z-index' in css.lower(), 'audio-gate must stack above the panel'
