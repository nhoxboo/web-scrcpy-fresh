/**
 * AudioParser — strips the scrcpy v3.x audio socket framing so the rest of
 * the player can hand AAC frames (ADTS-wrapped) to JMuxer.
 *
 * Wire format the server emits for the audio socket (after the 1-byte
 * handshake `\x00`, which scrcpy.py consumes BEFORE forwarding):
 *
 *   - 4 bytes  : codec id (big-endian uint32). scrcpy 3.x:
 *                 OPUS = 0x6f70_7573 ("opus")
 *                 AAC  = 0x0061_6163 ("\0aac" — leading NUL is intentional)
 *                 FLAC = 0x666c_6163 ("flac")
 *                 RAW  = 0x0072_6177 ("\0raw")
 *   - then a sequence of:
 *       8 bytes : PTS (top 2 bits are flags: high = config, next = key);
 *                 the remaining 62 bits are the timestamp.
 *       4 bytes : payload size (u32 BE)
 *       payload bytes
 *
 * The first packet typically has the `config` flag set and carries the
 * codec-specific decoder configuration. For AAC this is the
 * AudioSpecificConfig (ASC) — usually 2 bytes — from which we extract the
 * profile, sampling-frequency index and channel configuration so we can
 * synthesise ADTS headers for every subsequent raw AAC frame. JMuxer
 * audio mode (and most browser AAC decoders) expect ADTS-framed input;
 * scrcpy emits raw AAC access units, so without this wrapping playback
 * fails silently or with `Audio decoder error`.
 *
 * Callbacks:
 *   - onCodec({codec})                          : once, after codec id parsed
 *   - onFrame({data, pts, isConfig, isKey})     : per parsed frame.
 *       For AAC, `data` of a non-config frame is an ADTS-framed buffer
 *       ready to feed to JMuxer/MSE; for other codecs it's the raw
 *       payload as received.
 */
const _SCRCPY_AUDIO_CODEC_IDS = {
    0x6f707573: 'opus',
    0x00616163: 'aac',
    0x666c6163: 'flac',
    0x00726177: 'raw',
};

class AudioParser {
    constructor(handlers = {}) {
        this.buffer = new Uint8Array(0);
        this.codec = null;
        // AAC ADTS state: filled in on the first config frame.
        this._aacProfile = null; // 2-bit ADTS profile (= ASC AOT - 1)
        this._aacFreqIdx = null; // 4-bit sampling-frequency index
        this._aacChannels = null; // 3-bit channel configuration
        this.onCodec = handlers.onCodec || null;
        this.onFrame = handlers.onFrame || null;
    }

    appendData(data) {
        const grown = new Uint8Array(this.buffer.length + data.length);
        grown.set(this.buffer, 0);
        grown.set(data, this.buffer.length);
        this.buffer = grown;
        this._process();
    }

    _decodeCodecId(cidBytes) {
        // scrcpy serialises the codec name as a 4-byte big-endian uint32.
        // ASCII names shorter than 4 chars are NUL-padded — and crucially,
        // for "aac" the NUL goes at the *start* (0x00_61_61_63), not the
        // end. Using a numeric lookup avoids the trap of stripping NULs
        // from one side only.
        const cid =
            (cidBytes[0] << 24) | (cidBytes[1] << 16) | (cidBytes[2] << 8) | cidBytes[3];
        const known = _SCRCPY_AUDIO_CODEC_IDS[cid >>> 0];
        if (known) return known;
        // Fallback for unknown codecs: best-effort ASCII with both-side
        // NUL stripping so callers at least get a recognisable string.
        try {
            return new TextDecoder().decode(cidBytes).replace(/^\0+|\0+$/g, '');
        } catch (_e) {
            return 'unknown';
        }
    }

    _parseAacConfig(asc) {
        // AudioSpecificConfig (ISO 14496-3, §1.6.2.1), big-endian bit-packed:
        //   5 bits: audioObjectType (AOT). AAC-LC = 2.
        //   4 bits: samplingFrequencyIndex (0..0xc valid; 0xf = explicit u24).
        //   4 bits: channelConfiguration.
        if (!asc || asc.length < 2) return false;
        const b0 = asc[0];
        const b1 = asc[1];
        let aot = b0 >> 3;
        let freqIdx = ((b0 & 0x07) << 1) | (b1 >> 7);
        let channels = (b1 >> 3) & 0x0f;
        // ADTS profile field is `audioObjectType - 1`; only LC/SBR/PS fit in
        // the 2-bit ADTS slot, so clamp to 0..3 for safety.
        if (aot < 1) aot = 2; // assume AAC-LC if encoder reports something weird
        this._aacProfile = Math.max(0, Math.min(3, aot - 1));
        this._aacFreqIdx = freqIdx & 0x0f;
        this._aacChannels = channels & 0x07;
        return true;
    }

    _wrapAdts(payload) {
        // ADTS = 7 bytes header (no CRC) + raw AAC frame.
        const len = payload.length + 7;
        const out = new Uint8Array(len);
        const profile = this._aacProfile != null ? this._aacProfile : 1; // AAC-LC
        const freqIdx = this._aacFreqIdx != null ? this._aacFreqIdx : 3; // 48 kHz
        const channels = this._aacChannels != null ? this._aacChannels : 2; // stereo
        out[0] = 0xff;
        out[1] = 0xf1; // sync 0xfff, MPEG-4, layer 0, protection_absent=1
        out[2] = ((profile & 0x03) << 6) | ((freqIdx & 0x0f) << 2) | ((channels & 0x04) >> 2);
        out[3] = ((channels & 0x03) << 6) | ((len >> 11) & 0x03);
        out[4] = (len >> 3) & 0xff;
        out[5] = ((len & 0x07) << 5) | 0x1f;
        out[6] = 0xfc; // buffer_fullness=0x7ff, num_raw_data_blocks_in_frame=0
        out.set(payload, 7);
        return out;
    }

    _process() {
        let idx = 0;
        if (this.codec == null) {
            if (this.buffer.length < 4) return;
            this.codec = this._decodeCodecId(this.buffer.slice(0, 4));
            idx = 4;
            if (this.onCodec) this.onCodec({ codec: this.codec });
        }
        const view = new DataView(this.buffer.buffer);
        while (this.buffer.length - idx >= 12) {
            // PTS layout (scrcpy 3.x): bit 63 = config, bit 62 = key, low 62 = ts.
            const ptsHi = view.getUint32(this.buffer.byteOffset + idx, false);
            const ptsLo = view.getUint32(this.buffer.byteOffset + idx + 4, false);
            const isConfig = !!(ptsHi & 0x80000000);
            const isKey = !!(ptsHi & 0x40000000);
            const pts = ((ptsHi & 0x3fffffff) * 0x100000000) + ptsLo;
            const size = view.getUint32(this.buffer.byteOffset + idx + 8, false);
            // Sanity: payload must fit in remaining buffer; otherwise we just
            // wait for more data on the next appendData() call.
            if (this.buffer.length - idx < 12 + size) break;
            const payload = this.buffer.slice(idx + 12, idx + 12 + size);
            idx += 12 + size;
            // For AAC we need to (a) parse ASC out of the first config frame
            // and (b) wrap each subsequent payload in ADTS so JMuxer/MSE can
            // decode it. For other codecs (opus/flac) we just pass through.
            let outData = payload;
            if (this.codec === 'aac') {
                if (isConfig) {
                    this._parseAacConfig(payload);
                } else {
                    outData = this._wrapAdts(payload);
                }
            }
            if (this.onFrame) this.onFrame({ data: outData, pts, isConfig, isKey });
        }
        // Drop the bytes we consumed; keep the tail for the next chunk.
        this.buffer = this.buffer.slice(idx);
    }
}

if (typeof window !== 'undefined') {
    window.AudioParser = AudioParser;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioParser;
}
