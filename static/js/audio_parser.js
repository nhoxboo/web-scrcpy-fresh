/**
 * AudioParser — strips the scrcpy v3.x audio socket framing so the rest of
 * the player can hand raw AAC ADTS frames to JMuxer (or any AAC consumer).
 *
 * Wire format the server emits for the audio socket (after the 1-byte
 * handshake `\x00`, which scrcpy.py consumes BEFORE forwarding):
 *
 *   - 4 bytes  : codec id, big-endian ASCII (e.g. "aac\0", "opus", "flac")
 *   - then a sequence of:
 *       8 bytes : PTS (top 2 bits are flags: high = config, next = key);
 *                 the remaining 62 bits are the timestamp.
 *       4 bytes : payload size (u32 BE)
 *       payload bytes
 *
 * The first packet typically has the `config` flag set and carries the
 * codec-specific decoder configuration (AudioSpecificConfig for AAC). For
 * AAC the actual frames are already ADTS-framed by the encoder, so JMuxer
 * can derive the config off the ADTS header — we simply skip config-flagged
 * packets to avoid feeding raw AudioSpecificConfig bytes to JMuxer.
 *
 * Callbacks:
 *   - onCodec({codec})        : once, after the 4-byte codec id is parsed
 *   - onFrame({data, pts, isConfig, isKey}) : per parsed frame
 */
class AudioParser {
    constructor(handlers = {}) {
        this.buffer = new Uint8Array(0);
        this.codec = null;
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

    _process() {
        let idx = 0;
        if (this.codec == null) {
            if (this.buffer.length < 4) return;
            const cidBytes = this.buffer.slice(0, 4);
            // scrcpy pads short codec ids with NUL (e.g. "aac\0"), strip them.
            this.codec = new TextDecoder().decode(cidBytes).replace(/\0+$/, '');
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
            if (this.onFrame) this.onFrame({ data: payload, pts, isConfig, isKey });
        }
        // Drop the bytes we consumed; keep the tail for the next chunk.
        this.buffer = this.buffer.slice(idx);
    }
}

if (typeof window !== 'undefined') {
    window.AudioParser = AudioParser;
}
