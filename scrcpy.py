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
    # Last-resort default so the module still imports on machines that set
    # ADB_PATH at runtime or have adb on PATH later.
    return 'adb'


ADB_PATH = _resolve_adb_path()
SCRCPY_SERVER_PATH = os.path.join(os.path.dirname(__file__), 'scrcpy-server')
DEVICE_SERVER_PATH = '/data/local/tmp/scrcpy-server.jar'


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


LOCAL_PORT = int(os.environ.get('SCRCPY_LOCAL_PORT', '5555'))
DEFAULT_VIDEO_BIT_RATE = os.environ.get('SCRCPY_VIDEO_BIT_RATE', '8000000')
DEFAULT_MAX_FPS = os.environ.get('SCRCPY_MAX_FPS', '60')
# 0 = mirror at the device's native resolution. Setting e.g. 1920 caps the
# longest edge so very-high-DPI phones don't drown the browser decoder, which
# usually looks SHARPER (more bits per pixel) than uncapped 4K at the same
# bitrate. Most modern phones look great at 1920.
DEFAULT_MAX_SIZE = os.environ.get('SCRCPY_MAX_SIZE', '0').strip() or '0'
DEFAULT_ADB_SERIAL = os.environ.get('ADB_SERIAL', '').strip() or None
DEFAULT_DISPLAY_ID = os.environ.get('SCRCPY_DISPLAY_ID', '0').strip() or '0'


class Scrcpy:
    def __init__(
        self,
        serial: str | None = None,
        display_id: int | str | None = None,
        max_size: int | str | None = None,
    ):
        self.video_socket = None
        self.control_socket = None

        self.android_thread = None
        self.video_thread = None
        self.control_thread = None
        self.android_process = None

        self.video_callback = None
        self.video_bit_rate = DEFAULT_VIDEO_BIT_RATE
        self.max_fps = DEFAULT_MAX_FPS
        self.serial = serial or DEFAULT_ADB_SERIAL
        # display_id: 0 = main display (default), 2 = typical Samsung DeX,
        # or any secondary display id reported by `adb shell dumpsys display`.
        self.display_id = str(display_id) if display_id is not None else DEFAULT_DISPLAY_ID
        # max_size: 0 = device native, otherwise caps the longest edge.
        self.max_size = str(max_size) if max_size is not None else DEFAULT_MAX_SIZE
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
        # audio=false: audio was captured but never forwarded to the browser,
        # so disable it at the source to save device CPU + tunnel bandwidth.
        # display_id selects which display to mirror: 0 = main, 2 = typical
        # Samsung DeX, or any id reported by `adb shell dumpsys display`.
        cmd = self._adb(
            'shell',
            (
                f'CLASSPATH={DEVICE_SERVER_PATH} app_process / '
                'com.genymobile.scrcpy.Server 3.1 tunnel_forward=true audio=false '
                f'log_level=VERBOSE video_bit_rate={self.video_bit_rate} '
                f'max_fps={self.max_fps} display_id={self.display_id} '
                f'max_size={self.max_size}'
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
            log.info('scrcpy-server: %s', line.decode(errors='replace').rstrip())
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

    def handle_control_conn(self) -> None:
        log.info('Control connection established (idle)...')
        try:
            self.control_socket.recv(1)
            while not self.stop:
                data = self.control_socket.recv(1024)
                if not data:
                    break
                log.debug('Control msg: %r', data)
        except OSError as e:
            log.info('Control socket closed: %s', e)
        log.info('Control connection stopped')

    # ---- public API ------------------------------------------------------------
    def scrcpy_start(self, video_callback, video_bit_rate, max_fps=None) -> None:
        self.video_bit_rate = video_bit_rate
        if max_fps is not None:
            self.max_fps = str(max_fps)
        self.video_callback = video_callback
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
            online = [
                line.split('\t', 1)[0].strip()
                for line in result.stdout.splitlines()
                if '\tdevice' in line
            ]
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

            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.connect(('localhost', LOCAL_PORT))
            log.info('Control connection established')
        except OSError:
            self.stop = True
            self._close_sockets()
            raise

        self.video_thread = Thread(target=self.receive_video_data, daemon=True)
        self.control_thread = Thread(target=self.handle_control_conn, daemon=True)
        self.video_thread.start()
        self.control_thread.start()
        log.info('Background tasks started')

    def _shutdown_socket(self, sock) -> None:
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def _close_sockets(self) -> None:
        for sock in (self.video_socket, self.control_socket):
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
        self._shutdown_socket(self.control_socket)
        self._close_sockets()

        self._join_thread(self.video_thread)
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
