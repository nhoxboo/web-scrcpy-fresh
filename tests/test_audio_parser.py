"""Tests for static/js/audio_parser.js, the scrcpy v3 audio framing decoder.

The parser lives in JS so it can run in the browser; we exercise it from
Python by shelling out to `node`. Tests are skipped if node isn't on PATH —
ubuntu-latest CI runners ship with node by default, so this works in CI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

_PARSER_JS = os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'audio_parser.js')


def _run_node(snippet: str) -> dict:
    """Run a JS snippet that prints a single JSON line; return the parsed dict.

    The snippet has access to the AudioParser class (loaded via require).
    """
    if not shutil.which('node'):
        pytest.skip('node not available')
    abs_parser = os.path.abspath(_PARSER_JS)
    code = (
        f'const AudioParser = require({json.dumps(abs_parser)});\n(function(){{\n{snippet}\n}})();'
    )
    result = subprocess.run(
        ['node', '-e', code],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise AssertionError(
            f'node exited {result.returncode}\n--- stdout ---\n{result.stdout}'
            f'\n--- stderr ---\n{result.stderr}'
        )
    out = result.stdout.strip().splitlines()
    assert out, f'empty stdout; stderr={result.stderr}'
    return json.loads(out[-1])


def _frame_bytes(payload: bytes, *, is_config: bool = False) -> str:
    """Build a JS Uint8Array literal for a single scrcpy audio frame:
    8-byte PTS (with config flag) + 4-byte size + payload.
    """
    flags = 0x80 if is_config else 0x00
    pts = bytes([flags, 0, 0, 0, 0, 0, 0, 0])
    size = len(payload).to_bytes(4, 'big')
    return ','.join(str(b) for b in (pts + size + payload))


def test_codec_id_aac_decoded_as_string_aac():
    """`0x00_61_61_63` must decode to bare 'aac' (NUL is at the start, not end).

    The original parser stripped only trailing NULs and ended up with
    '\\u0000aac', tripping the "codec not supported" warning even though
    AAC is actually what scrcpy emits.
    """
    snippet = """
    const p = new AudioParser({ onCodec: ({codec}) => {
        process.stdout.write(JSON.stringify({codec}) + '\\n');
    }});
    p.appendData(new Uint8Array([0x00, 0x61, 0x61, 0x63]));
    """
    out = _run_node(snippet)
    assert out['codec'] == 'aac'


def test_codec_id_opus_decoded_as_string_opus():
    snippet = """
    const p = new AudioParser({ onCodec: ({codec}) => {
        process.stdout.write(JSON.stringify({codec}) + '\\n');
    }});
    p.appendData(new Uint8Array([0x6f, 0x70, 0x75, 0x73]));
    """
    out = _run_node(snippet)
    assert out['codec'] == 'opus'


def test_codec_id_flac_decoded_as_string_flac():
    snippet = """
    const p = new AudioParser({ onCodec: ({codec}) => {
        process.stdout.write(JSON.stringify({codec}) + '\\n');
    }});
    p.appendData(new Uint8Array([0x66, 0x6c, 0x61, 0x63]));
    """
    out = _run_node(snippet)
    assert out['codec'] == 'flac'


def test_aac_config_frame_extracts_profile_and_channels():
    """AAC ASC for AAC-LC @ 48kHz stereo is 0x11 0x90 (binary 00010 0011 0010 0).

    audioObjectType = 2 (AAC-LC) -> ADTS profile = 1
    samplingFrequencyIndex = 3 (48000 Hz)
    channelConfiguration = 2 (stereo)
    """
    config = bytes([0x11, 0x90])
    snippet = f"""
    const p = new AudioParser({{}});
    p.appendData(new Uint8Array([0,0x61,0x61,0x63]));
    p.appendData(new Uint8Array([{_frame_bytes(config, is_config=True)}]));
    process.stdout.write(JSON.stringify({{
        profile: p._aacProfile, freqIdx: p._aacFreqIdx, channels: p._aacChannels
    }}) + '\\n');
    """
    out = _run_node(snippet)
    assert out == {'profile': 1, 'freqIdx': 3, 'channels': 2}


def test_aac_payload_wrapped_in_adts_after_config():
    """A non-config AAC frame must be emitted as 7-byte ADTS header + payload.

    The first two ADTS bytes are constant: 0xff 0xf1 (sync + MPEG-4 + LC + no CRC).
    """
    config = bytes([0x11, 0x90])  # AAC-LC, 48 kHz, stereo
    payload = bytes(range(50))  # 50 raw AAC bytes
    snippet = f"""
    const frames = [];
    const p = new AudioParser({{ onFrame: f => frames.push(f) }});
    p.appendData(new Uint8Array([0,0x61,0x61,0x63]));
    p.appendData(new Uint8Array([{_frame_bytes(config, is_config=True)}]));
    p.appendData(new Uint8Array([{_frame_bytes(payload)}]));
    const non_config = frames.find(f => !f.isConfig);
    process.stdout.write(JSON.stringify({{
        len: non_config.data.length,
        head: Array.from(non_config.data.slice(0, 7)),
        tail: Array.from(non_config.data.slice(7)),
    }}) + '\\n');
    """
    out = _run_node(snippet)
    # 7-byte ADTS header + 50-byte raw payload = 57.
    assert out['len'] == 57
    head = out['head']
    assert head[0] == 0xFF
    assert head[1] == 0xF1
    # Frame length field (13 bits across bytes 3,4,5) must equal 57.
    framelen = ((head[3] & 0x03) << 11) | (head[4] << 3) | (head[5] >> 5)
    assert framelen == 57
    # ADTS profile/freq/channels must match what we put in the ASC.
    profile = (head[2] >> 6) & 0x03
    freq_idx = (head[2] >> 2) & 0x0F
    channels = ((head[2] & 0x01) << 2) | (head[3] >> 6)
    assert (profile, freq_idx, channels) == (1, 3, 2)
    # Tail is the original raw AAC payload, untouched.
    assert out['tail'] == list(payload)


def test_aac_config_frame_data_is_raw_asc_not_adts_wrapped():
    """Config frames must NOT be ADTS-wrapped — the consumer skips them.

    Wrapping config bytes in ADTS would produce an 'ADTS frame' that's not
    an actual audio frame and would either be ignored by the decoder or,
    worse, treated as garbage.
    """
    config = bytes([0x11, 0x90])
    snippet = f"""
    const frames = [];
    const p = new AudioParser({{ onFrame: f => frames.push(f) }});
    p.appendData(new Uint8Array([0,0x61,0x61,0x63]));
    p.appendData(new Uint8Array([{_frame_bytes(config, is_config=True)}]));
    process.stdout.write(JSON.stringify({{
        is_config: frames[0].isConfig,
        data: Array.from(frames[0].data),
    }}) + '\\n');
    """
    out = _run_node(snippet)
    assert out['is_config'] is True
    assert out['data'] == [0x11, 0x90]


def test_non_aac_codec_passes_through_unwrapped():
    """OPUS frames must be forwarded as-is — only AAC needs ADTS wrapping."""
    payload = bytes([1, 2, 3, 4, 5])
    snippet = f"""
    const frames = [];
    const p = new AudioParser({{ onFrame: f => frames.push(f) }});
    p.appendData(new Uint8Array([0x6f,0x70,0x75,0x73]));
    p.appendData(new Uint8Array([{_frame_bytes(payload)}]));
    process.stdout.write(JSON.stringify({{
        data: Array.from(frames[0].data),
    }}) + '\\n');
    """
    out = _run_node(snippet)
    assert out['data'] == list(payload)


def test_unknown_codec_id_falls_back_to_stripped_string():
    """Defensive: an unknown 4-byte codec id should still produce a usable
    string for the UI rather than blowing up the parser."""
    snippet = """
    const p = new AudioParser({ onCodec: ({codec}) => {
        process.stdout.write(JSON.stringify({codec}) + '\\n');
    }});
    p.appendData(new Uint8Array([0x00, 0x77, 0x65, 0x69]));  // "\\0wei"
    """
    out = _run_node(snippet)
    assert out['codec'] == 'wei'


def test_streaming_split_across_chunks():
    """Real socket reads chunk arbitrarily; the parser must buffer until a
    full frame is available."""
    config = bytes([0x11, 0x90])
    payload = bytes([0xAA] * 32)
    frame_a = _frame_bytes(config, is_config=True)
    frame_b = _frame_bytes(payload)
    snippet = f"""
    const frames = [];
    const p = new AudioParser({{ onFrame: f => frames.push(f) }});
    // Codec id arrives in two chunks
    p.appendData(new Uint8Array([0x00, 0x61]));
    p.appendData(new Uint8Array([0x61, 0x63]));
    // Config frame split mid-PTS
    const a = [{frame_a}];
    const b = [{frame_b}];
    p.appendData(new Uint8Array(a.slice(0, 5)));
    p.appendData(new Uint8Array(a.slice(5)));
    // Payload frame split inside the payload bytes
    p.appendData(new Uint8Array(b.slice(0, 18)));
    p.appendData(new Uint8Array(b.slice(18)));
    process.stdout.write(JSON.stringify({{
        count: frames.length,
        config_first: frames[0].isConfig,
        // ADTS-wrapped payload should be header (7) + raw (32) = 39 bytes.
        payload_len: frames[1].data.length,
    }}) + '\\n');
    """
    out = _run_node(snippet)
    assert out == {'count': 2, 'config_first': True, 'payload_len': 39}
