"""Regression coverage for per-socket stream queues.

The application creates video/audio queues inside ``handle_connect`` and owns
those queues in ``scpy_sessions``. Removing a disconnected session must not
reuse queued bytes in the next browser session.
"""

from __future__ import annotations

import queue


def _session(video_q: queue.Queue, audio_q: queue.Queue) -> dict:
    return {
        'scpy_ctx': None,
        'video_q': video_q,
        'audio_q': audio_q,
        'tasks': [],
    }


def test_new_session_uses_empty_per_session_queues(app):
    stale_video = queue.Queue()
    stale_audio = queue.Queue()
    stale_video.put(b'old-video')
    stale_audio.put(b'old-audio')
    fresh_video = queue.Queue()
    fresh_audio = queue.Queue()

    with app._state_lock:
        app.scpy_sessions['old'] = _session(stale_video, stale_audio)
        app.scpy_sessions.pop('old')
        app.scpy_sessions['new'] = _session(fresh_video, fresh_audio)

    try:
        assert stale_video.qsize() == 1
        assert stale_audio.qsize() == 1
        assert fresh_video.empty()
        assert fresh_audio.empty()
    finally:
        with app._state_lock:
            app.scpy_sessions.clear()
