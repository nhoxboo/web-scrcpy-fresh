from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import time
from threading import Thread

log = logging.getLogger('web-scrcpy.scrcpy')


def _resolve_adb_path() -> str:
    """Find an adb binary without hardcoding a machine-specific path."""
    env_path = os.environ.get('ADB_PATH')
    if env_path and os.path.exists(env_path):
        return env_path

    candidate = shutil.which('adb') or shutil.which('adb.exe')
    if candidate:
        return candidate

    # Workspace fallback: ../platform-tools/adb(.exe)
    base_dir = os.path.dirname(__file__)
    fallback_candidates = [
        os.path.join(base_dir, '..', 'platform-tools', 'adb.exe'),
        os.path.join(base_dir, '..', 'platform-tools', 'adb'),
        os.path.expanduser('~/Downloads/platform-tools-latest-windows/platform-tools/adb.exe'),
        os.path.expanduser('~/Downloads/scrcpy-win64-v3.3.1/scrcpy-win64-v3.3.1/adb.exe'),
        os.path.expanduser('~/AppData/Local/Android/Sdk/platform-tools/adb.exe'),
    ]
    for fb in fallback_candidates:
        fb_norm = os.path.normpath(fb)
        if os.path.exists(fb_norm):
            return fb_norm

    # Last-resort default so the module still imports on machines that set
    # ADB_PATH at runtime or have adb on PATH later.
    return 'adb'


ADB_PATH = _resolve_adb_path()
SCRCPY_SERVER_PATH = os.path.join(os.path.dirname(__file__), 'scrcpy-server', 'scrcpy-server.jar')
DEVICE_SERVER_PATH = '/data/local/tmp/scrcpy-server.jar'
# Must match the BuildConfig.VERSION_NAME baked into the jar at SCRCPY_SERVER_PATH;
# Server.main() rejects the connection on a string mismatch (see Options.parse).
SCRCPY_SERVER_VERSION = '3.3.4'


def list_adb_devices(adb_path: str | None = None, timeout: float = 5.0) -> list[dict]:
    """Run `adb devices -l` and return a list of dicts with serial/state/model.

    Each entry: {'serial': str, 'state': str, 'model': str, 'product': str,
    'transport_id': str, 'usb': str}. Empty list if adb is not available or
    no devices are attached. Never raises (returns [] on failure).
    """
    cmd = [adb_path or ADB_PATH, 'devices', '-l']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        log.warning('list_adb_devices failed: %s', e)
        return []
    if result.returncode != 0:
        log.warning('adb devices returned %d: %s', result.returncode, result.stderr.strip())
        return []
    devices: list[dict] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith('list of devices'):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        entry = {
            'serial': parts[0],
            'state': parts[1],
            'model': '',
            'product': '',
            'transport_id': '',
            'usb': '',
        }
        for token in parts[2:]:
            if ':' in token:
                key, _, value = token.partition(':')
                if key in entry:
                    entry[key] = value
        devices.append(entry)
    return devices


def is_valid_serial(serial: str) -> bool:
    """Cheap structural check for an ADB serial (alnum, dash, dot, colon)."""
    if not serial or len(serial) > 64:
        return False
    return all(c.isalnum() or c in '-_.:' for c in serial)


def adb_install(
    apk_path: str,
    serial: str | None = None,
    reinstall: bool = True,
    timeout: float = 300.0,
    adb_path: str | None = None,
) -> tuple[bool, str]:
    """Run `adb install` and return (ok, combined_output).

    timeout is generous (5 min) because large APKs over slow USB can take a while.
    Always non-raising — on subprocess error we return (False, error string).
    """
    if not os.path.isfile(apk_path):
        return False, f'APK not found: {apk_path}'
    cmd = [adb_path or ADB_PATH]
    if serial:
        cmd += ['-s', serial]
    cmd += ['install']
    if reinstall:
        cmd += ['-r']
    cmd += [apk_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        log.warning('adb install failed: %s', e)
        return False, f'{type(e).__name__}: {e}'
    out = (result.stdout or '') + (result.stderr or '')
    # adb install reports success via "Success" in stdout even when returncode=0,
    # and various failures in stderr. Treat returncode + presence of "Success".
    ok = result.returncode == 0 and 'Success' in out
    return ok, out.strip()


def adb_push(
    src_path: str,
    dest_path: str,
    serial: str | None = None,
    timeout: float = 600.0,
    adb_path: str | None = None,
) -> tuple[bool, str]:
    """Run `adb push <src> <dest>`. Returns (ok, combined_output)."""
    if not os.path.isfile(src_path):
        return False, f'Source not found: {src_path}'
    if not dest_path or not dest_path.startswith('/'):
        return False, f'Invalid destination: {dest_path!r}'
    cmd = [adb_path or ADB_PATH]
    if serial:
        cmd += ['-s', serial]
    cmd += ['push', src_path, dest_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        log.warning('adb push failed: %s', e)
        return False, f'{type(e).__name__}: {e}'
    out = (result.stdout or '') + (result.stderr or '')
    return result.returncode == 0, out.strip()


# ----- wireless adb + simple adb-shell helpers -------------------------------


def is_valid_host(host: str) -> bool:
    """Allow hostname / IPv4 only (no IPv6, no shell metacharacters).

    Wireless ADB only ever connects to LAN IPs in practice, so a strict
    allow-list of `[a-zA-Z0-9.\\-]` is enough — and it makes shell injection
    via `adb connect` impossible regardless of how we shell out.
    """
    if not host or len(host) > 253:
        return False
    return all(c.isalnum() or c in '.-' for c in host)


def is_valid_port(port: int | str) -> bool:
    try:
        p = int(port)
    except (TypeError, ValueError):
        return False
    return 1 <= p <= 65535


def adb_pair(
    host: str,
    port: int | str,
    code: str,
    timeout: float = 30.0,
    adb_path: str | None = None,
) -> tuple[bool, str]:
    """Pair with an Android device over Wi-Fi using `adb pair host:port code`.

    Modern adb (>=1.0.41) accepts the 6-digit pairing code as the second
    positional arg, removing the interactive prompt. We always pass it
    explicitly so the call is non-interactive even on older builds (which
    will read it from stdin).
    """
    if not is_valid_host(host):
        return False, f'Invalid host: {host!r}'
    if not is_valid_port(port):
        return False, f'Invalid port: {port!r}'
    if not code.isdigit() or not (4 <= len(code) <= 8):
        return False, 'Pair code phải là 4-8 chữ số.'
    target = f'{host}:{int(port)}'
    cmd = [adb_path or ADB_PATH, 'pair', target, code]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=f'{code}\n',  # legacy adb that prompts will read this
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        log.warning('adb pair failed: %s', e)
        return False, f'{type(e).__name__}: {e}'
    out = ((result.stdout or '') + (result.stderr or '')).strip()
    # adb pair prints "Successfully paired" on success.
    ok = result.returncode == 0 and 'success' in out.lower()
    return ok, out


def adb_connect(
    host: str,
    port: int | str,
    timeout: float = 15.0,
    adb_path: str | None = None,
) -> tuple[bool, str]:
    """Run `adb connect host:port`. Idempotent."""
    if not is_valid_host(host):
        return False, f'Invalid host: {host!r}'
    if not is_valid_port(port):
        return False, f'Invalid port: {port!r}'
    target = f'{host}:{int(port)}'
    cmd = [adb_path or ADB_PATH, 'connect', target]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        log.warning('adb connect failed: %s', e)
        return False, f'{type(e).__name__}: {e}'
    out = ((result.stdout or '') + (result.stderr or '')).strip()
    # adb connect always exits 0 — success is signalled by "connected to ..."
    # vs "failed to connect" / "cannot connect" in stdout. Be permissive but
    # check for the failure markers.
    low = out.lower()
    ok = result.returncode == 0 and 'cannot' not in low and 'failed' not in low
    return ok, out


def adb_disconnect(
    host: str | None = None,
    port: int | str | None = None,
    timeout: float = 10.0,
    adb_path: str | None = None,
) -> tuple[bool, str]:
    """Run `adb disconnect [host:port]`; with no args disconnects all."""
    cmd = [adb_path or ADB_PATH, 'disconnect']
    if host is not None:
        if not is_valid_host(host):
            return False, f'Invalid host: {host!r}'
        if port is None:
            cmd.append(host)
        else:
            if not is_valid_port(port):
                return False, f'Invalid port: {port!r}'
            cmd.append(f'{host}:{int(port)}')
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        log.warning('adb disconnect failed: %s', e)
        return False, f'{type(e).__name__}: {e}'
    out = ((result.stdout or '') + (result.stderr or '')).strip()
    return result.returncode == 0, out


def adb_shell(
    args: list[str],
    serial: str | None = None,
    timeout: float = 15.0,
    adb_path: str | None = None,
) -> tuple[bool, str]:
    """Run `adb [-s serial] shell <args...>`.

    args is a list of already-validated argv tokens. Caller MUST NOT pass
    user-controlled strings directly — only members of a fixed allow-list,
    so command injection is impossible regardless of shell quoting.
    """
    if not args or not all(isinstance(a, str) for a in args):
        return False, 'No shell args.'
    cmd = [adb_path or ADB_PATH]
    if serial:
        cmd += ['-s', serial]
    cmd += ['shell'] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        log.warning('adb shell failed: %s', e)
        return False, f'{type(e).__name__}: {e}'
    out = ((result.stdout or '') + (result.stderr or '')).strip()
    return result.returncode == 0, out


def adb_simple(
    args: list[str],
    serial: str | None = None,
    timeout: float = 15.0,
    adb_path: str | None = None,
) -> tuple[bool, str]:
    """Run `adb [-s serial] <args...>` (no `shell` prefix). For e.g. `reboot`."""
    if not args:
        return False, 'No args.'
    cmd = [adb_path or ADB_PATH]
    if serial:
        cmd += ['-s', serial]
    cmd += list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        log.warning('adb_simple failed: %s', e)
        return False, f'{type(e).__name__}: {e}'
    out = ((result.stdout or '') + (result.stderr or '')).strip()
    return result.returncode == 0, out


def is_valid_new_display(spec: str) -> bool:
    """Validate `WxH`, `WxH/dpi`, `/dpi`, or empty (=any).

    scrcpy 3.x accepts these forms; we restrict to digits + a single 'x'
    + a single '/' so shell-quoting concerns can't bite us when we splice
    the value into the scrcpy CLI.
    """
    if not spec:
        return False
    # /dpi only
    if spec.startswith('/'):
        return spec[1:].isdigit() and 1 <= int(spec[1:]) <= 1000
    # split optional /dpi tail
    if spec.count('/') > 1:
        return False
    head, _, dpi = spec.partition('/')
    if dpi and (not dpi.isdigit() or not (1 <= int(dpi) <= 1000)):
        return False
    if 'x' not in head:
        return False
    if head.count('x') != 1:
        return False
    w, _, h = head.partition('x')
    if not w.isdigit() or not h.isdigit():
        return False
    iw, ih = int(w), int(h)
    return 100 <= iw <= 7680 and 100 <= ih <= 7680


LOCAL_PORT = int(os.environ.get('SCRCPY_LOCAL_PORT', '5555'))
# Defaults tuned for fast LAN / Wi-Fi 5+ on a modern phone:
#   * 10 Mbps gives clean 1080p without saturating typical home Wi-Fi.
#   * 60 fps matches the panel refresh rate of all current Samsung flagships.
#   * max_size=1920 caps the longest edge so 4K-class phones (e.g. Galaxy
#     Fold/Ultra) don't drown the browser MSE decoder; the result is
#     sharper-looking than uncapped native because more bits hit each pixel
#     at the same bitrate. Set SCRCPY_MAX_SIZE=0 to opt back into native res.
DEFAULT_VIDEO_BIT_RATE = os.environ.get('SCRCPY_VIDEO_BIT_RATE', '10000000')
DEFAULT_MAX_FPS = os.environ.get('SCRCPY_MAX_FPS', '60')
DEFAULT_MAX_SIZE = os.environ.get('SCRCPY_MAX_SIZE', '1080').strip() or '1080'
DEFAULT_ADB_SERIAL = os.environ.get('ADB_SERIAL', '').strip() or None
DEFAULT_DISPLAY_ID = os.environ.get('SCRCPY_DISPLAY_ID', '0').strip() or '0'
# Mirror of scrcpy v3.3.x ControlMessage.TYPE_SET_DISPLAY_POWER. Sent over the
# control socket to ask the device to turn its physical screen on/off without
# affecting the mirrored stream — same trick the upstream CLI uses for
# `--turn-screen-off` / `-S`. Payload is a single byte: 0 = off, 1 = on.
CONTROL_MSG_TYPE_SET_DISPLAY_POWER = 10


class Scrcpy:
    def __init__(
        self,
        serial: str | None = None,
        display_id: int | str | None = None,
        max_size: int | str | None = None,
        new_display: str | None = None,
        enable_audio: bool = False,
        audio_codec: str = 'aac',
        turn_screen_off: bool = False,
    ):
        self.video_socket = None
        self.audio_socket = None
        self.control_socket = None

        self.android_thread = None
        self.video_thread = None
        self.audio_thread = None
        self.control_thread = None
        self.android_process = None

        self.video_callback = None
        # audio_callback(data: bytes) — invoked from the audio reader thread
        # whenever the device pushes audio bytes. The data is the raw scrcpy
        # audio socket stream (codec id + per-packet 12-byte header + payload),
        # which the browser parses with AudioParser into AAC ADTS frames.
        self.audio_callback = None
        # device_message_callback(msg_type: int, payload: dict) — invoked from
        # the control reader thread when scrcpy-server pushes a message back
        # to the client. Today we only forward TYPE_CLIPBOARD (= 0); the
        # payload dict is {'text': str} for that type. UHID_OUTPUT (LED state
        # etc.) is parsed but not forwarded since the browser has no use
        # for it.
        self.device_message_callback = None
        self.video_bit_rate = DEFAULT_VIDEO_BIT_RATE
        self.max_fps = DEFAULT_MAX_FPS
        # Last few stderr lines from scrcpy-server, used to surface a useful
        # reason when socket connect fails (e.g. "Display 2 not found").
        self._server_stderr_tail: list[str] = []
        self.serial = serial or DEFAULT_ADB_SERIAL
        # display_id: 0 = main display (default), 2 = typical Samsung DeX,
        # or any secondary display id reported by `adb shell dumpsys display`.
        self.display_id = str(display_id) if display_id is not None else DEFAULT_DISPLAY_ID
        # max_size: 0 = device native, otherwise caps the longest edge.
        self.max_size = str(max_size) if max_size is not None else DEFAULT_MAX_SIZE
        # new_display: when set (e.g. '1920x1080/160'), scrcpy creates a virtual
        # display on the device and mirrors that one — same trick Samsung DeX
        # uses, but available on any Android 11+. Mutually exclusive with a
        # non-default display_id; we'll skip the display_id arg when this is on.
        self.new_display = (
            str(new_display).strip()
            if new_display is not None and str(new_display).strip()
            else None
        )
        # enable_audio: when True, scrcpy server captures device audio and
        # opens an *additional* socket to stream it. We default it off because
        # the browser playback path (jmuxer audio mode → MSE) still needs
        # device-side QA on each OEM. Codec choice is locked to 'aac' so the
        # browser MSE pipeline can decode it — Opus would need a separate
        # decoder we don't ship today.
        self.enable_audio = bool(enable_audio)
        self.audio_codec = (audio_codec or 'aac').strip().lower()
        if self.audio_codec not in ('aac',):
            # Be explicit so a typo'd codec doesn't silently fall through
            # the scrcpy CLI and produce a stream the browser can't play.
            log.warning('Unsupported audio_codec=%r; falling back to aac.', self.audio_codec)
            self.audio_codec = 'aac'
        # turn_screen_off: mirrors scrcpy's `--turn-screen-off` / `-S` flag.
        # When True we send a SET_DISPLAY_POWER(off) control message right
        # after the control socket connects, so the device's physical screen
        # turns black while the browser keeps receiving the mirrored video
        # over the existing stream. Useful for headless control where the
        # phone is in a drawer and you don't want to drain the OLED.
        self.turn_screen_off = bool(turn_screen_off)
        self.stop = True  # True until scrcpy_start flips it; avoids AttributeError

    # ---- device setup ----------------------------------------------------------
    def _adb(self, *args: str) -> list[str]:
        """Build an adb command, optionally targeting a specific serial."""
        cmd = [ADB_PATH]
        if self.serial:
            cmd += ['-s', self.serial]
        cmd += list(args)
        return cmd

    def push_server_to_device(self) -> bool:
        log.info('Pushing scrcpy-server.jar to device (serial=%s)...', self.serial or '*')
        result = subprocess.run(
            self._adb('push', SCRCPY_SERVER_PATH, DEVICE_SERVER_PATH),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.error('Error pushing server: %s', result.stderr.strip())
            return False
        return True

    def setup_adb_forward(self) -> None:
        log.info('Setting up ADB forward: tcp:%d -> localabstract:scrcpy', LOCAL_PORT)
        subprocess.run(
            self._adb('forward', f'tcp:{LOCAL_PORT}', 'localabstract:scrcpy'),
            check=True,
        )

    # ---- server lifecycle ------------------------------------------------------
    def start_server(self) -> None:
        log.info('Starting scrcpy server in background...')
        # audio: when False (default) the server skips capture entirely, saving
        # device CPU + tunnel bandwidth. When True we additionally pin the
        # codec to AAC so the browser MSE pipeline can decode it (Opus needs
        # a separate decoder we don't ship). The audio socket is opened in
        # *between* the video and control sockets, so scrcpy_start adds a
        # third connect() in the right order when self.enable_audio is set.
        # display_id selects which display to mirror: 0 = main, 2 = typical
        # Samsung DeX, or any id reported by `adb shell dumpsys display`.
        # new_display takes precedence: scrcpy server rejects display_id when
        # new_display is set (it creates a fresh virtual display whose id it
        # picks). Validate the spec defensively before splicing into the CLI.
        display_arg = ''
        if self.new_display and is_valid_new_display(self.new_display):
            display_arg = f'new_display={self.new_display} '
        else:
            display_arg = f'display_id={self.display_id} '
        audio_arg = (
            f'audio=true audio_codec={self.audio_codec} ' if self.enable_audio else 'audio=false '
        )
        cmd = self._adb(
            'shell',
            (
                f'CLASSPATH={DEVICE_SERVER_PATH} app_process / '
                f'com.genymobile.scrcpy.Server {SCRCPY_SERVER_VERSION} tunnel_forward=true {audio_arg}'
                f'log_level=VERBOSE video_bit_rate={self.video_bit_rate} '
                f'max_fps={self.max_fps} {display_arg}'
                f'max_size={self.max_size} stay_awake=true'
            ),
        )
        self.android_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Drain stderr while process runs. readline blocks so the `stop` flag is
        # best-effort here; scrcpy_stop terminates the process which unblocks it.
        while not self.stop:
            line = self.android_process.stderr.readline()
            if not line:
                break
            decoded = line.decode(errors='replace').rstrip()
            log.info('scrcpy-server: %s', decoded)
            # Keep a bounded tail so connect failures can quote the real cause.
            self._server_stderr_tail.append(decoded)
            if len(self._server_stderr_tail) > 50:
                self._server_stderr_tail.pop(0)
        self.android_process.wait()
        log.info('Server stopped')

    # ---- socket readers --------------------------------------------------------
    def receive_video_data(self) -> None:
        log.info('Receiving video data (H.264)...')
        try:
            self.video_socket.recv(1)
            while not self.stop:
                data = self.video_socket.recv(20480)
                if not data:
                    break
                if self.video_callback is not None:
                    self.video_callback(data)
        except OSError as e:
            log.info('Video socket closed: %s', e)
        log.info('Video data reception stopped')

    def receive_audio_data(self) -> None:
        # Audio reader: server streams the codec id (4 bytes, big-endian
        # uint32 — AAC = 0x00_61_61_63, "\0aac") followed by repeated
        # [8-byte PTS+flags, 4-byte size, payload]. The browser-side
        # AudioParser strips those headers and feeds ADTS-framed AAC to
        # JMuxer.
        #
        # NB: scrcpy's `sendDummyByte` only writes the 1-byte handshake to
        # the *first* socket the server accept()s (see upstream
        # DesktopConnection.open). With our setup (video=true, audio=true)
        # that socket is the video one — see receive_video_data — so we
        # MUST NOT consume a leading byte from the audio socket. Doing so
        # eats the leading NUL of the AAC codec id and the parser then
        # decodes "aac\0x80…" → "aac\uFFFD" → status bar shows
        # "Audio codec aac� chưa hỗ trợ trong trình duyệt".
        log.info('Receiving audio data (codec=%s)...', self.audio_codec)
        if self.audio_socket is None:
            log.info('Audio socket not connected; skipping audio reader')
            return
        try:
            while not self.stop:
                data = self.audio_socket.recv(8192)
                if not data:
                    break
                if self.audio_callback is not None:
                    self.audio_callback(data)
        except OSError as e:
            log.info('Audio socket closed: %s', e)
        log.info('Audio data reception stopped')

    def handle_control_conn(self) -> None:
        # The control socket is bidirectional: we send INJECT_KEYCODE,
        # UHID_INPUT, SET_CLIPBOARD, etc. *to* the device and the device
        # pushes DeviceMessage frames *back* (clipboard updates, ack,
        # UHID output). Parse them frame-by-frame and dispatch via
        # device_message_callback so app.py can forward to the browser.
        #
        # Wire format (scrcpy v3.3.4 DeviceMessageWriter.java; identical to 3.1):
        #   TYPE_CLIPBOARD     = 0  : u8=0  | u32 length | utf8 bytes
        #   TYPE_ACK_CLIPBOARD = 1  : u8=1  | u64 sequence
        #   TYPE_UHID_OUTPUT   = 2  : u8=2  | u16 id | u16 size | data
        log.info('Control connection established (reading device messages)')
        buf = b''

        def _need(n: int) -> bool:
            # Pull bytes until we have at least n in buf, returning False
            # iff the socket closed mid-message.
            nonlocal buf
            while len(buf) < n and not self.stop:
                try:
                    chunk = self.control_socket.recv(4096)
                except OSError:
                    return False
                if not chunk:
                    return False
                buf += chunk
            return len(buf) >= n

        try:
            while not self.stop:
                if not _need(1):
                    break
                msg_type = buf[0]
                if msg_type == 0:  # TYPE_CLIPBOARD
                    if not _need(1 + 4):
                        break
                    length = int.from_bytes(buf[1:5], 'big')
                    if not _need(1 + 4 + length):
                        break
                    text_bytes = buf[5 : 5 + length]
                    buf = buf[5 + length :]
                    try:
                        text = text_bytes.decode('utf-8', errors='replace')
                    except Exception:
                        text = ''
                    log.debug('Device clipboard update (%d bytes)', length)
                    if self.device_message_callback is not None:
                        try:
                            self.device_message_callback(0, {'text': text})
                        except Exception as exc:  # noqa: BLE001
                            log.warning('device_message_callback raised: %s', exc)
                elif msg_type == 1:  # TYPE_ACK_CLIPBOARD
                    if not _need(1 + 8):
                        break
                    buf = buf[9:]  # sequence ack — we don't use it client-side
                elif msg_type == 2:  # TYPE_UHID_OUTPUT
                    if not _need(1 + 2 + 2):
                        break
                    size = int.from_bytes(buf[3:5], 'big')
                    if not _need(1 + 2 + 2 + size):
                        break
                    buf = buf[5 + size :]
                else:
                    log.warning('Unknown device message type %d, dropping connection', msg_type)
                    break
        except OSError as e:
            log.info('Control socket closed: %s', e)
        log.info('Control connection stopped')

    # ---- public API ------------------------------------------------------------
    def scrcpy_start(
        self,
        video_callback,
        video_bit_rate,
        max_fps=None,
        audio_callback=None,
    ) -> None:
        self.video_bit_rate = video_bit_rate
        if max_fps is not None:
            self.max_fps = str(max_fps)
        self.video_callback = video_callback
        # Audio: only request the extra socket if the caller supplied a
        # callback AND the instance was constructed with enable_audio=True.
        # Either condition alone wouldn't make sense — no callback means
        # nowhere for the bytes to go; no enable_audio means the server
        # won't open the socket and connect() would dangle.
        if audio_callback is not None and self.enable_audio:
            self.audio_callback = audio_callback
        else:
            self.audio_callback = None
        self.stop = False

        result = subprocess.run(
            [ADB_PATH, 'devices'],
            capture_output=True,
            text=True,
        )
        if 'device' not in result.stdout:
            log.error('No device found. Please connect your Android device via USB.')
            self.stop = True
            raise RuntimeError('No ADB device found')
        log.info('adb devices output: %s', result.stdout.strip())
        if self.serial:
            # Require the requested serial to be present and online.
            # Capture both 'device' and 'unauthorized' so we can give a clear
            # hint when the phone is reachable but hasn't accepted the RSA key.
            online = []
            unauthorized = []
            for line in result.stdout.splitlines():
                if '\tdevice' in line:
                    online.append(line.split('\t', 1)[0].strip())
                elif '\tunauthorized' in line:
                    unauthorized.append(line.split('\t', 1)[0].strip())
            if self.serial in unauthorized:
                self.stop = True
                raise RuntimeError(
                    f'ADB serial {self.serial!r} is UNAUTHORIZED. '
                    'On the Android device, accept the "Allow USB debugging" prompt, '
                    'or in Developer options > Wireless debugging tap "Pair device with pairing code".'
                )
            if self.serial not in online:
                self.stop = True
                raise RuntimeError(f'ADB serial {self.serial!r} not online (found: {online})')

        if not self.push_server_to_device():
            self.stop = True
            raise RuntimeError('Failed to push scrcpy-server to device')

        self.setup_adb_forward()
        self.android_thread = Thread(target=self.start_server, daemon=True)
        self.android_thread.start()
        time.sleep(1)

        try:
            self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.video_socket.connect(('localhost', LOCAL_PORT))
            log.info('Video connection established')

            # Audio socket is opened in between video and control to match
            # scrcpy's connect-back order when audio=true is set on the server.
            # If we leave it out the server's audio thread would hang on
            # accept() and (in some versions) tear down the whole streamer.
            if self.audio_callback is not None and self.enable_audio:
                self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.audio_socket.connect(('localhost', LOCAL_PORT))
                log.info('Audio connection established')

            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.connect(('localhost', LOCAL_PORT))
            log.info('Control connection established')
        except OSError as exc:
            self.stop = True
            self._close_sockets()
            # Common case: user toggled DeX on a non-Samsung phone (or DeX not
            # active). The server prints "Display [id] not found" to stderr
            # and exits before we can connect. Surface that reason so the UI
            # can offer to disable DeX automatically.
            tail = '\n'.join(self._server_stderr_tail[-10:])
            tail_low = tail.lower()
            # Friendly errors so the UI can offer auto-fallback / clear hints.
            if self.new_display and (
                'createvirtualdisplay' in tail_low
                or 'permission' in tail_low
                or 'requires android 11' in tail_low
                or 'invalid display' in tail_low
            ):
                raise RuntimeError(
                    'Virtual Desktop không khả dụng trên máy này '
                    '(yêu cầu Android 11+; tắt Virtual Desktop để dùng màn hình chính).'
                ) from exc
            display_missing = self.display_id != '0' and (
                'not found' in tail_low or 'invalid display' in tail_low or 'no display' in tail_low
            )
            if display_missing:
                raise RuntimeError(
                    f'Display id={self.display_id} không khả dụng trên máy này '
                    f'(DeX chưa bật hoặc máy không hỗ trợ DeX).'
                ) from exc
            raise

        self.video_thread = Thread(target=self.receive_video_data, daemon=True)
        self.control_thread = Thread(target=self.handle_control_conn, daemon=True)
        self.video_thread.start()
        self.control_thread.start()
        if self.audio_socket is not None and self.audio_callback is not None:
            self.audio_thread = Thread(target=self.receive_audio_data, daemon=True)
            self.audio_thread.start()
        # scrcpy CLI's `--turn-screen-off` is implemented entirely on the client
        # side: the server has no startup flag for it, so we send a
        # SET_DISPLAY_POWER(off) control message ourselves right after the
        # control socket is up. Best-effort — scrcpy_send_control already
        # swallows OSError, so a torn-down socket during shutdown can't crash
        # us.
        if self.turn_screen_off:
            log.info('Sending SET_DISPLAY_POWER(off) — --turn-screen-off')
            self.scrcpy_send_control(
                bytes([CONTROL_MSG_TYPE_SET_DISPLAY_POWER, 0]),
            )
        log.info('Background tasks started')

    def _shutdown_socket(self, sock) -> None:
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def _close_sockets(self) -> None:
        for sock in (self.video_socket, self.audio_socket, self.control_socket):
            if sock is None:
                continue
            try:
                sock.close()
            except OSError:
                pass

    def _join_thread(self, thread, timeout: float = 2.0) -> None:
        if thread is None:
            return
        try:
            thread.join(timeout=timeout)
        except RuntimeError:
            pass

    def scrcpy_stop(self) -> None:
        log.info('Stopping Scrcpy')
        self.stop = True

        self._shutdown_socket(self.video_socket)
        self._shutdown_socket(self.audio_socket)
        self._shutdown_socket(self.control_socket)
        self._close_sockets()

        self._join_thread(self.video_thread)
        self._join_thread(self.audio_thread)
        self._join_thread(self.control_thread)

        if self.android_process is not None:
            try:
                self.android_process.terminate()
            except OSError:
                pass
            try:
                self.android_process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.android_process.kill()
        self._join_thread(self.android_thread)
        log.info('Scrcpy stopped')

    def scrcpy_send_control(self, data) -> None:
        sock = self.control_socket
        if sock is None:
            return
        try:
            sock.send(data)
        except OSError as e:
            log.warning('control_socket.send failed: %s', e)
