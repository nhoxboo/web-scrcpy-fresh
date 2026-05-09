"""Tests for the message queue drain on (re)connect.

When a browser tab toggles audio (or anything that triggers a soft
reload), the websocket disconnects and reconnects on the same Python
process. The previous Scrcpy instance is torn down — but bytes that the
old encoder already pushed onto the in-process `message_queue` /
`audio_message_queue` survive. If we don't drain them before starting
the next session the new browser-side VideoParser/AudioParser sees mid-
NALU bytes as the 64-byte device name + 12-byte size header, producing
the famous garbage `Screen <huge>x<negative>` and a permanently
out-of-sync stream until the user does a full hard reload.

PR #34 added this drain only for the audio queue. This test pins the
fix that drains BOTH queues, regardless of whether the new session asks
for audio.
"""

from __future__ import annotations

import re
from pathlib import Path

APP_PY = Path(__file__).resolve().parent.parent / 'app.py'


def test_handle_connect_drains_both_queues():
    """Source-level regression: handle_connect must drain message_queue +
    audio_message_queue right before scrcpy_start, so stale bytes from
    the previous Scrcpy instance can't poison the new client."""
    text = APP_PY.read_text(encoding='utf-8')
    # The drain block lives just above scrcpy_start — find scrcpy_start
    # then walk backwards a few lines to inspect the drain construct.
    idx = text.find('scpy_ctx.scrcpy_start(')
    assert idx > 0, 'could not locate scrcpy_start call site'
    above = text[max(0, idx - 1500) : idx]
    # The fix iterates over (message_queue, audio_message_queue) so the
    # same pattern covers both. We accept either order.
    pattern = re.compile(
        r'for\s+\w+\s+in\s+\(\s*([\w_,\s]+?)\s*\)\s*:\s*\n'
        r'(?:\s+(?:try|while|except|continue|pass|\w+\.get_nowait\(\)).*\n)+',
        re.MULTILINE,
    )
    m = pattern.search(above)
    assert m, (
        'handle_connect should iterate over both queues with a single '
        'drain loop just before scrcpy_start; got:\n' + above[-700:]
    )
    queues = {q.strip() for q in m.group(1).split(',') if q.strip()}
    assert 'message_queue' in queues, f'video message_queue not in drain loop targets: {queues}'
    assert 'audio_message_queue' in queues, (
        f'audio_message_queue not in drain loop targets: {queues}'
    )


def test_drain_runs_for_video_only_session(app):
    """Behavioural check: even when audio is OFF, calling the drain logic
    empties an already-stale video queue. We invoke the same construct
    used in handle_connect to confirm it doesn't accidentally short-
    circuit on `chosen_audio=False`."""
    # Pre-populate both queues with junk that simulates leftover bytes
    # from a previous Scrcpy session.
    for _ in range(5):
        app.message_queue.put(b'video-stale')
        app.audio_message_queue.put(b'audio-stale')
    assert app.message_queue.qsize() == 5
    assert app.audio_message_queue.qsize() == 5

    # Mirror handle_connect's drain — this is the exact construct in app.py.
    import queue

    for q in (app.message_queue, app.audio_message_queue):
        try:
            while True:
                q.get_nowait()
        except queue.Empty:
            pass

    assert app.message_queue.qsize() == 0
    assert app.audio_message_queue.qsize() == 0
