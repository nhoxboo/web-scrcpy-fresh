"""Regression tests for the audio socket handshake.

Background
----------

scrcpy's `DesktopConnection.open()` writes a single dummy `\\x00` byte to
**only** the first socket the server accept()s when `sendDummyByte=true`.
With our setup (video=true, audio=true) the connect order is video → audio
→ control, so that dummy byte goes to the *video* socket. The audio socket
must NOT have a leading byte consumed.

A previous version of `receive_audio_data` called `audio_socket.recv(1)`
before reading the codec id; that mistake ate the leading NUL of the AAC
codec id (`0x00_61_61_63`) and the browser parser then read
`b"\\x61\\x61\\x63\\x80…"` → decoded to `"aac\\uFFFD"` → status bar showed
`Audio codec aac� chưa hỗ trợ trong trình duyệt`. These tests pin both
the source-level fact (no dummy-byte consume on the audio socket) AND the
behavioural property (the codec id reaches the callback bit-exact).
"""

from __future__ import annotations

import importlib
import inspect
import re
import sys
import threading

import pytest


@pytest.fixture
def real_scrcpy():
    """Import the real scrcpy module (conftest replaces it with a stub for
    most tests). Restore the stub on teardown so neighbouring tests still
    use the fake module."""
    saved_stub = sys.modules.get('scrcpy')
    saved_app = sys.modules.pop('app', None)
    sys.modules.pop('scrcpy', None)
    real = importlib.import_module('scrcpy')
    yield real
    sys.modules.pop('scrcpy', None)
    if saved_stub is not None:
        sys.modules['scrcpy'] = saved_stub
    if saved_app is not None:
        sys.modules['app'] = saved_app


def test_receive_audio_data_does_not_consume_dummy_byte(real_scrcpy):
    """Source-level regression: the audio reader must NOT call
    `audio_socket.recv(1)` before the main loop. Pin it textually so a
    future refactor that re-introduces the bug fails CI immediately."""
    src = inspect.getsource(real_scrcpy.Scrcpy.receive_audio_data)
    # Reject any leading single-byte recv on the audio socket — that's the
    # exact pattern that broke `aac` codec id parsing in browsers.
    assert not re.search(r'audio_socket\.recv\(\s*1\s*\)', src), (
        'receive_audio_data must not consume a 1-byte handshake from the '
        'audio socket; the dummy byte goes only to firstSocket (video).'
    )


def test_receive_video_data_still_consumes_dummy_byte(real_scrcpy):
    """The dummy byte goes to the *video* socket (firstSocket in scrcpy's
    DesktopConnection.open). Make sure the video reader keeps consuming it
    so the H.264 stream isn't off-by-one in the other direction."""
    src = inspect.getsource(real_scrcpy.Scrcpy.receive_video_data)
    assert re.search(r'video_socket\.recv\(\s*1\s*\)', src), (
        'receive_video_data must still consume the 1-byte dummy handshake.'
    )


class _FakeAudioSocket:
    """Minimal stand-in for socket.socket: yields pre-loaded byte chunks
    on successive recv() calls, then returns b"" to signal close."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)
        self.recv_calls: list[int] = []

    def recv(self, bufsize: int) -> bytes:
        self.recv_calls.append(bufsize)
        if not self._chunks:
            return b''
        return self._chunks.pop(0)


def test_receive_audio_data_forwards_codec_id_bit_exact(real_scrcpy):
    """Behavioural test: feed `\\x00aac` (AAC codec id) followed by a fake
    PTS+size+payload frame and confirm the callback receives the leading
    NUL untouched. This is what the browser AudioParser needs to look up
    `_SCRCPY_AUDIO_CODEC_IDS[0x00616163] === 'aac'`."""
    cls = real_scrcpy.Scrcpy
    instance = cls.__new__(cls)
    # Bypass __init__ — we just need a few attributes the reader touches.
    instance.audio_codec = 'aac'
    instance.stop = False
    captured: list[bytes] = []
    instance.audio_callback = captured.append
    # codec id (4 BE bytes), then a fake config frame: PTS-with-config-flag
    # (8 bytes, 0x80…), size=2 (4 bytes BE), 2 bytes of ASC.
    codec_id = b'\x00\x61\x61\x63'
    pts_with_cfg = (1 << 63).to_bytes(8, 'big')
    size = (2).to_bytes(4, 'big')
    asc = b'\x12\x10'  # AAC-LC / 44.1kHz / stereo

    fake = _FakeAudioSocket([codec_id, pts_with_cfg + size + asc, b''])
    instance.audio_socket = fake

    # Stop the reader thread quickly: flip self.stop after the third recv
    # by wrapping the callback.
    def _cb_and_stop(data: bytes) -> None:
        captured.append(data)
        if len(captured) >= 2:  # plus the .append already in captured
            instance.stop = True

    instance.audio_callback = _cb_and_stop
    captured.clear()

    t = threading.Thread(target=instance.receive_audio_data, daemon=True)
    t.start()
    t.join(timeout=2.0)
    assert not t.is_alive(), 'receive_audio_data did not terminate'

    # The callback must have seen the codec id bytes byte-for-byte. Either
    # as the first chunk on its own, or concatenated with a later one — but
    # the first 4 bytes seen MUST equal b"\x00aac".
    joined = b''.join(captured)
    assert joined.startswith(codec_id), (
        f'codec id was mangled before reaching callback: {joined[:8]!r}'
    )
    # And recv was NEVER called with bufsize=1 (defensive: that would mean
    # someone re-introduced the dummy-byte read).
    assert 1 not in fake.recv_calls, (
        f'audio reader called recv(1) — that eats the codec id NUL. recv calls: {fake.recv_calls}'
    )
