"""Tests for the soft-reconnect-on-audio-toggle refactor.

Previously, flipping the audio toolbar toggle called ``location.reload()``
so the server could restart scrcpy with ``audio=true``. That reload also
killed the browser's user-activation flag — and Chrome's autoplay policy
needs that activation alive to let the ``<audio>`` element play after
JMuxer attaches a MediaSource. The result was silent audio even when the
codec, ADTS framing and socket protocol were all correct.

The refactor:
* removes ``location.reload()`` from the audio toggle path
* soft-reconnects the socket with a new ``?audio=1`` query
* synchronously primes ``audioEl.play()`` / ``AudioContext.resume()``
  *inside* the click handler so the user gesture survives the
  disconnect/connect cycle

These tests pin those invariants so a future cleanup can't silently
re-introduce the reload (which would re-break audio on production).
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / 'templates' / 'index.html'


def _audio_toggle_block() -> str:
    """Slice the inline script down to just the audio toggle click handler.

    Keeps the rest of the test asserts focused — we don't accidentally
    match a ``location.reload()`` from the DeX/Vdesktop fallback paths
    elsewhere in the file. We anchor the end on the gamepad section's
    comment marker which directly follows the audio toggle, so we always
    capture the whole handler regardless of how many ``});`` / ``});``
    closers it contains internally.
    """
    html = INDEX_HTML.read_text(encoding='utf-8')
    match = re.search(
        r"audioBtn\.addEventListener\('click'.*?// ---- Gamepad UHID toggle",
        html,
        flags=re.DOTALL,
    )
    assert match, 'audio toolbar toggle handler not found in index.html'
    return match.group(0)


def test_audio_toggle_does_not_reload_the_page():
    block = _audio_toggle_block()
    assert 'location.reload' not in block, (
        'audio toggle must not call location.reload() — that drops the user '
        'gesture and re-introduces the silent-audio bug on production'
    )


def test_audio_toggle_uses_soft_socket_reconnect():
    block = _audio_toggle_block()
    # Both halves of the soft reconnect must be present, and in this
    # exact handler — not just "anywhere in the file".
    assert 'socket.disconnect' in block, (
        'audio toggle should disconnect the socket before reconnecting with the new ?audio= query'
    )
    assert 'socket.connect' in block, (
        'audio toggle should reconnect the socket so scrcpy restarts with '
        'the new audio capture setting'
    )
    # The new query must actually carry the audio flag.
    assert '_socketQuery.audio' in block, (
        'audio toggle should set _socketQuery.audio so handle_connect sees ?audio=1'
    )


def test_audio_toggle_primes_user_activation_synchronously():
    block = _audio_toggle_block()
    # Primer must be called inside the click handler — synchronously
    # before the setTimeout/disconnect path runs — so the click counts
    # as a user gesture for autoplay purposes.
    assert '_primeAudioUserActivation' in block, (
        'audio toggle must call _primeAudioUserActivation() inside the click '
        'handler so the user-gesture window survives the soft reconnect'
    )


def test_user_activation_primer_resumes_audio_context_and_plays():
    html = INDEX_HTML.read_text(encoding='utf-8')
    match = re.search(
        r'const _primeAudioUserActivation = \(\)=>\{.*?\};',
        html,
        flags=re.DOTALL,
    )
    assert match, '_primeAudioUserActivation helper not found'
    body = match.group(0)
    # AudioContext.resume() unlocks Web Audio output (also satisfies the
    # gesture requirement on some browsers / iOS Safari).
    assert 'AudioContext' in body, 'primer must touch (Web)AudioContext'
    assert 'resume' in body, 'primer must resume the AudioContext'
    # And it must *actually* call play() on the <audio> element while
    # the gesture is still live — empty src is fine, the call consumes
    # the gesture against the element.
    assert 'audioEl.play()' in body, (
        'primer must invoke audioEl.play() synchronously inside the gesture'
    )
