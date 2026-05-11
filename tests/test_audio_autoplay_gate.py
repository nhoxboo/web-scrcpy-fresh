"""Tests for the audio-autoplay gate on the panel page.

Even with the soft-reconnect refactor (see ``test_audio_soft_reconnect``)
that keeps the user-gesture alive across an audio toggle, Chrome's
autoplay policy can still block ``<audio>`` playback when the document
has a low Media Engagement Index — e.g. fresh sessions on a brand-new
domain. We therefore keep a centred gate banner that:

1. Exists in the DOM (``<div id="audioGate">``), hidden by default, and
   pops up only when ``audioEl.play()`` rejects with ``NotAllowedError``.
2. Wires a capture-phase document-level click/keydown/touchstart
   listener so any user gesture anywhere on the page satisfies the
   autoplay activation requirement and retries playback.
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
