import argparse
import atexit
import hmac
import json
import logging
import logging.handlers
import os
import queue
import secrets
import signal
import threading
import time
from collections import deque
from datetime import timedelta
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_socketio import ConnectionRefusedError as SocketConnectionRefusedError
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

from scrcpy import (
    Scrcpy,
    adb_connect,
    adb_disconnect,
    adb_install,
    adb_pair,
    adb_push,
    adb_shell,
    adb_simple,
    is_valid_host,
    is_valid_new_display,
    is_valid_port,
    is_valid_serial,
    list_adb_devices,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
log = logging.getLogger('web-scrcpy')

BASE_DIR = os.path.dirname(__file__)
AUTH_FILE = os.path.join(BASE_DIR, 'auth.json')
SECRET_FILE = os.path.join(BASE_DIR, 'secret.key')

DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'admin123'
MIN_PASSWORD_LEN = 8

# Rate limit: max attempts / window (seconds) per client IP on /login
LOGIN_MAX_ATTEMPTS = 8
LOGIN_WINDOW_SECONDS = 300  # 5 minutes

# Rate limit for /change-password (looser since user is already authenticated).
CHANGE_PW_MAX_ATTEMPTS = 10
CHANGE_PW_WINDOW_SECONDS = 300

# Session idle lifetime; override via SESSION_LIFETIME_SECONDS env var.
SESSION_LIFETIME_SECONDS = int(os.environ.get('SESSION_LIFETIME_SECONDS', '86400'))

# APK install / file push limits. Configurable via env so a deploy can lower
# them on a constrained box, or raise them if the user installs huge games.
MAX_INSTALL_SIZE_MB = int(os.environ.get('MAX_INSTALL_SIZE_MB', '500'))
MAX_PUSH_SIZE_MB = int(os.environ.get('MAX_PUSH_SIZE_MB', '500'))
INSTALL_DEFAULT_PUSH_DEST = '/sdcard/Download/'
INSTALL_URL_TIMEOUT_SECONDS = int(os.environ.get('INSTALL_URL_TIMEOUT_SECONDS', '120'))
INSTALL_RATE_MAX = int(os.environ.get('INSTALL_RATE_MAX', '6'))
INSTALL_RATE_WINDOW_SECONDS = int(os.environ.get('INSTALL_RATE_WINDOW_SECONDS', '300'))

# --- audit log setup -----------------------------------------------------------
AUDIT_LOG_FILE = os.environ.get('AUDIT_LOG_FILE', os.path.join(BASE_DIR, 'audit.log'))
audit_log = logging.getLogger('web-scrcpy.audit')
audit_log.setLevel(logging.INFO)
audit_log.propagate = False  # keep auth events out of stdout; file only
if not audit_log.handlers:
    try:
        _audit_handler = logging.handlers.RotatingFileHandler(
            AUDIT_LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding='utf-8'
        )
        _audit_handler.setFormatter(
            logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%dT%H:%M:%S%z')
        )
        audit_log.addHandler(_audit_handler)
    except OSError as _audit_err:  # e.g. read-only fs in tests
        log.warning('audit log disabled: %s', _audit_err)


def _audit(event: str, **fields) -> None:
    """Write a structured line to the audit log (best-effort)."""
    try:
        ip = request.remote_addr if request else '-'
    except RuntimeError:
        ip = '-'
    parts = [f'event={event}', f'ip={ip}']
    for key, value in fields.items():
        parts.append(f'{key}={value}')
    audit_log.info(' '.join(parts))


# --- shared scrcpy session state -------------------------------------------------
_state_lock = threading.Lock()
scpy_ctx = None
client_sid = None
message_queue = queue.Queue()
video_bit_rate = os.environ.get('SCRCPY_VIDEO_BIT_RATE', '10000000')
max_fps = os.environ.get('SCRCPY_MAX_FPS', '60')
max_size = os.environ.get('SCRCPY_MAX_SIZE', '1920').strip() or '1920'
adb_serial = os.environ.get('ADB_SERIAL', '').strip() or None
display_id = os.environ.get('SCRCPY_DISPLAY_ID', '0').strip() or '0'


def _shutdown_scrcpy() -> None:
    """Tear down any running scrcpy session + adb subprocess on process exit.

    Normally handle_disconnect cleans up when the last websocket closes, but if
    the process is killed (SIGTERM from gunicorn, crash) that path doesn't fire
    and the adb shell subprocess + local port forward would leak.
    """
    global scpy_ctx, client_sid
    with _state_lock:
        ctx = scpy_ctx
        scpy_ctx = None
        client_sid = None
    if ctx is not None:
        try:
            ctx.scrcpy_stop()
        except Exception as e:  # noqa: BLE001
            log.warning('scrcpy_stop during shutdown failed: %s', e)


atexit.register(_shutdown_scrcpy)


def _install_signal_handlers() -> None:
    def _handler(signum, _frame):
        log.info('Received signal %s, shutting down scrcpy', signum)
        _shutdown_scrcpy()
        # Re-raise default behavior so gunicorn / systemd can reap us.
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _handler)
        except ValueError:
            # Not main thread (e.g. under gunicorn worker); gunicorn handles signals.
            pass


_install_signal_handlers()


# --- secret / auth helpers -------------------------------------------------------
def _load_secret_key() -> bytes:
    env_secret = os.environ.get('FLASK_SECRET_KEY')
    if env_secret:
        return env_secret.encode('utf-8')
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, 'rb') as f:
            data = f.read().strip()
            if data:
                return data
    data = secrets.token_bytes(32)
    with open(SECRET_FILE, 'wb') as f:
        f.write(data)
    try:
        os.chmod(SECRET_FILE, 0o600)
    except OSError:
        pass
    log.info('Generated new SECRET_KEY at %s', SECRET_FILE)
    return data


def _write_auth(data: dict) -> None:
    tmp_path = AUTH_FILE + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.replace(tmp_path, AUTH_FILE)
    try:
        os.chmod(AUTH_FILE, 0o600)
    except OSError:
        pass


def _is_hashed(password_field: str) -> bool:
    # werkzeug hashes look like "pbkdf2:sha256:..." / "scrypt:..." etc.
    return isinstance(password_field, str) and ':' in password_field and len(password_field) > 20


def _load_auth() -> dict:
    if not os.path.exists(AUTH_FILE):
        data = {
            'username': DEFAULT_USERNAME,
            'password': generate_password_hash(DEFAULT_PASSWORD),
        }
        _write_auth(data)
        log.warning(
            'auth.json not found; created default credentials (%s / %s). '
            'CHANGE THIS PASSWORD IMMEDIATELY via /change-password.',
            DEFAULT_USERNAME,
            DEFAULT_PASSWORD,
        )
        return data

    with open(AUTH_FILE, encoding='utf-8') as f:
        data = json.load(f)

    # Migrate legacy plaintext passwords transparently on load.
    pw = data.get('password', '')
    if not _is_hashed(pw):
        log.warning('Migrating auth.json from plaintext password to hashed storage.')
        data['password'] = generate_password_hash(pw)
        _write_auth(data)
    return data


def _save_auth(username: str, password: str) -> None:
    _write_auth({'username': username, 'password': generate_password_hash(password)})


def _verify_password(stored: str, candidate: str) -> bool:
    if not stored or not candidate:
        return False
    try:
        return check_password_hash(stored, candidate)
    except Exception:  # noqa: BLE001 - defensive
        return False


def _is_authed() -> bool:
    return session.get('authenticated', False) is True


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not _is_authed():
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapper


# --- CSRF ------------------------------------------------------------------------
def _get_csrf_token() -> str:
    token = session.get('_csrf')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf'] = token
    return token


def _validate_csrf() -> bool:
    expected = session.get('_csrf') or ''
    # Accept the token in either the form field (classic POST) or the
    # X-CSRF-Token header (multipart upload from fetch / XMLHttpRequest where
    # adding form fields next to a binary file is awkward).
    received = (request.form.get('csrf_token') or '').strip() or (
        request.headers.get('X-CSRF-Token') or ''
    ).strip()
    if not expected or not received:
        return False
    return hmac.compare_digest(expected, received)


# --- rate limit ------------------------------------------------------------------
_login_attempts: dict[str, deque] = {}
_login_attempts_lock = threading.Lock()
_change_pw_attempts: dict[str, deque] = {}
_change_pw_attempts_lock = threading.Lock()


def _rate_limit_check(ip: str) -> bool:
    now = time.monotonic()
    with _login_attempts_lock:
        dq = _login_attempts.setdefault(ip, deque())
        while dq and now - dq[0] > LOGIN_WINDOW_SECONDS:
            dq.popleft()
        if len(dq) >= LOGIN_MAX_ATTEMPTS:
            return False
        return True


def _rate_limit_record(ip: str) -> None:
    now = time.monotonic()
    with _login_attempts_lock:
        dq = _login_attempts.setdefault(ip, deque())
        dq.append(now)


def _change_pw_check(ip: str) -> bool:
    now = time.monotonic()
    with _change_pw_attempts_lock:
        dq = _change_pw_attempts.setdefault(ip, deque())
        while dq and now - dq[0] > CHANGE_PW_WINDOW_SECONDS:
            dq.popleft()
        if len(dq) >= CHANGE_PW_MAX_ATTEMPTS:
            return False
        return True


def _change_pw_record(ip: str) -> None:
    now = time.monotonic()
    with _change_pw_attempts_lock:
        dq = _change_pw_attempts.setdefault(ip, deque())
        dq.append(now)


def _client_ip() -> str:
    # Respect X-Forwarded-For only if the operator opts in (single reverse proxy).
    if os.environ.get('TRUST_PROXY') == '1':
        fwd = request.headers.get('X-Forwarded-For', '')
        if fwd:
            return fwd.split(',')[0].strip()
    return request.remote_addr or 'unknown'


# --- Flask app setup -------------------------------------------------------------
app = Flask(__name__)
app.config.update(
    SECRET_KEY=_load_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '0') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_LIFETIME_SECONDS),
    # Allow APK uploads. Use the larger of the two limits since the same
    # MAX_CONTENT_LENGTH applies to all routes.
    MAX_CONTENT_LENGTH=max(MAX_INSTALL_SIZE_MB, MAX_PUSH_SIZE_MB) * 1024 * 1024,
)

# When running behind a trusted reverse proxy (nginx, Caddy, Traefik, ...) set
# TRUST_PROXY=1 so request.is_secure / remote_addr honour X-Forwarded-* headers.
if os.environ.get('TRUST_PROXY') == '1':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

socketio = SocketIO(app, async_mode=None)


@app.context_processor
def _inject_csrf():
    return {'csrf_token': _get_csrf_token}


@app.before_request
def _csrf_guard():
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return None
    # Socket.IO handles its own auth via the connect handler.
    if request.path.startswith('/socket.io'):
        return None
    if not _validate_csrf():
        log.warning('CSRF validation failed for %s %s', request.method, request.path)
        abort(400)
    return None


@app.after_request
def _security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'same-origin')
    response.headers.setdefault(
        'Content-Security-Policy',
        "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
        "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; connect-src 'self' ws: wss:; frame-ancestors 'none'",
    )
    return response


# --- routes ----------------------------------------------------------------------
def _selected_serial() -> str | None:
    """Resolve which adb serial to drive: per-session pick > env/CLI default."""
    chosen = (session.get('adb_serial') or '').strip()
    if chosen:
        return chosen
    return adb_serial


def _selected_device_label() -> str:
    """Best-effort 'serial (model)' label for the currently selected device."""
    serial = _selected_serial()
    if not serial:
        return ''
    for d in list_adb_devices():
        if d.get('serial') == serial:
            model = d.get('model') or ''
            return f'{serial} ({model})' if model else serial
    return serial


@app.route('/')
@login_required
def index():
    return render_template(
        'index.html',
        username=session.get('username', DEFAULT_USERNAME),
        device_label=_selected_device_label(),
        device_serial=_selected_serial() or '',
    )


@app.route('/devices', methods=['GET', 'POST'])
@login_required
def devices():
    if request.method == 'POST':
        action = (request.form.get('action') or '').strip()
        if action == 'clear':
            session.pop('adb_serial', None)
            _audit('device_cleared', user=session.get('username', '-'))
            flash('Đã bỏ chọn thiết bị; sẽ dùng mặc định (env/CLI hoặc auto).')
            return redirect(url_for('devices'))

        serial = (request.form.get('serial') or '').strip()
        if not serial:
            flash('Vui lòng chọn một thiết bị.')
        elif not is_valid_serial(serial):
            flash('Serial không hợp lệ.')
        else:
            attached = {d['serial'] for d in list_adb_devices()}
            if attached and serial not in attached:
                flash('Thiết bị không còn kết nối, hãy refresh.')
            else:
                session['adb_serial'] = serial
                _audit('device_selected', user=session.get('username', '-'), serial=serial)
                flash(f'Đã chọn thiết bị {serial}.')
                return redirect(url_for('index'))

    items = list_adb_devices()
    return render_template(
        'devices.html',
        username=session.get('username', DEFAULT_USERNAME),
        devices=items,
        selected=_selected_serial() or '',
        default_serial=adb_serial or '',
    )


@app.route('/api/devices')
@login_required
def api_devices():
    return {
        'devices': list_adb_devices(),
        'selected': _selected_serial() or '',
        'default': adb_serial or '',
    }


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip = _client_ip()
        if not _rate_limit_check(ip):
            log.warning('Login rate-limited for ip=%s', ip)
            _audit('login_rate_limited')
            flash('Quá nhiều lần thử. Vui lòng đợi vài phút rồi thử lại.')
            return render_template('login.html'), 429

        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        auth = _load_auth()
        if username == auth.get('username') and _verify_password(
            auth.get('password', ''), password
        ):
            session.clear()
            session.permanent = True
            session['authenticated'] = True
            session['username'] = username
            _get_csrf_token()  # rotate token for the new session
            _audit('login_success', user=username)
            return redirect(url_for('index'))

        _rate_limit_record(ip)
        log.info('Failed login attempt user=%r ip=%s', username, ip)
        _audit('login_failure', user=username)
        flash('Sai tài khoản hoặc mật khẩu')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    _audit('logout', user=session.get('username', '-'))
    session.clear()
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        ip = _client_ip()
        if not _change_pw_check(ip):
            log.warning('change-password rate-limited for ip=%s', ip)
            flash('Quá nhiều lần thử. Vui lòng đợi vài phút rồi thử lại.')
            return render_template(
                'change_password.html',
                username=session.get('username', DEFAULT_USERNAME),
            ), 429

        current_password = request.form.get('current_password') or ''
        new_username = (request.form.get('new_username') or '').strip() or session.get(
            'username', DEFAULT_USERNAME
        )
        new_password = request.form.get('new_password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        auth = _load_auth()
        if not _verify_password(auth.get('password', ''), current_password):
            _change_pw_record(ip)
            _audit('change_password_failure', user=session.get('username', '-'))
            flash('Mật khẩu hiện tại không đúng')
        elif len(new_password) < MIN_PASSWORD_LEN:
            flash(f'Mật khẩu mới tối thiểu {MIN_PASSWORD_LEN} ký tự')
        elif new_password != confirm_password:
            flash('Xác nhận mật khẩu mới không khớp')
        else:
            old_user = session.get('username', '-')
            _save_auth(new_username, new_password)
            session['username'] = new_username
            _audit('change_password_success', old_user=old_user, new_user=new_username)
            flash('Đổi thông tin đăng nhập thành công')
            return redirect(url_for('index'))

    return render_template(
        'change_password.html', username=session.get('username', DEFAULT_USERNAME)
    )


# --- APK install / file push ----------------------------------------------------
_install_attempts: dict[str, deque] = {}
_install_attempts_lock = threading.Lock()


def _install_rate_check(ip: str) -> bool:
    now = time.monotonic()
    with _install_attempts_lock:
        dq = _install_attempts.setdefault(ip, deque())
        while dq and now - dq[0] > INSTALL_RATE_WINDOW_SECONDS:
            dq.popleft()
        if len(dq) >= INSTALL_RATE_MAX:
            return False
        dq.append(now)
        return True


def _looks_like_apk(path: str) -> bool:
    """APK files are ZIP archives, so check the local-file-header magic.

    Returns False for empty / unreadable files. Doesn't validate the manifest;
    a malformed APK will simply fail at `adb install` with a useful error.
    """
    try:
        with open(path, 'rb') as f:
            sig = f.read(4)
    except OSError:
        return False
    return sig[:2] == b'PK'


def _download_to_tempfile(url: str, max_bytes: int, timeout: float) -> tuple[str, str]:
    """Download `url` into a temp file, enforcing the size cap as we stream.

    Returns (path, error). On success error is empty; on failure path is empty.
    Uses urllib (stdlib) to avoid adding `requests` as a dependency.
    """
    import tempfile
    import urllib.error
    import urllib.parse
    import urllib.request

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return '', f'Only http/https URLs are allowed (got {parsed.scheme!r})'
    if not parsed.netloc:
        return '', 'URL is missing a host'

    req = urllib.request.Request(url, headers={'User-Agent': 'web-scrcpy/1.0'})
    fd, tmp_path = tempfile.mkstemp(prefix='install-', suffix='.apk')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - scheme checked above
            with os.fdopen(fd, 'wb') as out:
                written = 0
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        out.close()
                        os.unlink(tmp_path)
                        return '', f'Download exceeds {max_bytes // (1024 * 1024)} MB cap'
                    out.write(chunk)
    except urllib.error.URLError as e:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return '', f'Download failed: {e}'
    except Exception as e:  # noqa: BLE001
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return '', f'Download failed: {e}'
    return tmp_path, ''


@app.route('/api/install', methods=['POST'])
@login_required
def api_install():
    """Install an APK on the currently selected device.

    Two modes (mutually exclusive):
      * multipart/form-data with `file=<.apk>`
      * form field `url=<https://.../app.apk>` (downloaded server-side first)
    """
    ip = request.remote_addr or '-'
    if not _install_rate_check(ip):
        _audit('install_rate_limited')
        return jsonify(ok=False, error='Quá nhiều lần cài đặt, thử lại sau.'), 429

    serial = _selected_serial()
    if not serial:
        # adb_install() with serial=None lets adb pick the only attached device,
        # which is fine for a single-device setup. Surface a clear hint when
        # multiple devices may be attached.
        log.info('api_install: no serial selected, letting adb auto-pick')

    file = request.files.get('file')
    url = (request.form.get('url') or '').strip()
    if not file and not url:
        return jsonify(ok=False, error='Cần file APK hoặc url.'), 400
    if file and url:
        return jsonify(ok=False, error='Chọn file HOẶC url, không cả hai.'), 400

    import tempfile

    apk_path = ''
    cleanup = False
    try:
        if file:
            if not file.filename or not file.filename.lower().endswith('.apk'):
                return jsonify(ok=False, error='File phải có đuôi .apk'), 400
            fd, apk_path = tempfile.mkstemp(prefix='install-', suffix='.apk')
            os.close(fd)
            file.save(apk_path)
            cleanup = True
        else:
            apk_path, err = _download_to_tempfile(
                url, MAX_INSTALL_SIZE_MB * 1024 * 1024, INSTALL_URL_TIMEOUT_SECONDS
            )
            if err:
                _audit('install_url_download_failed', error=err[:120])
                return jsonify(ok=False, error=err), 400
            cleanup = True

        size = os.path.getsize(apk_path)
        if size > MAX_INSTALL_SIZE_MB * 1024 * 1024:
            return jsonify(ok=False, error=f'File quá lớn (>{MAX_INSTALL_SIZE_MB} MB)'), 413
        if not _looks_like_apk(apk_path):
            return jsonify(ok=False, error='Không phải file APK hợp lệ.'), 400

        ok, output = adb_install(apk_path, serial=serial)
        _audit('install', source='url' if url else 'upload', size=size, ok=ok)
        if ok:
            return jsonify(ok=True, output=output)
        return jsonify(ok=False, error=output or 'adb install failed'), 500
    finally:
        if cleanup and apk_path and os.path.isfile(apk_path):
            try:
                os.unlink(apk_path)
            except OSError:
                pass


@app.route('/api/push', methods=['POST'])
@login_required
def api_push():
    """Push a file to /sdcard/Download/ (or any caller-supplied dest)."""
    ip = request.remote_addr or '-'
    if not _install_rate_check(ip):
        _audit('push_rate_limited')
        return jsonify(ok=False, error='Quá nhiều lần upload, thử lại sau.'), 429

    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify(ok=False, error='Thiếu file.'), 400

    dest_dir = (request.form.get('dest') or INSTALL_DEFAULT_PUSH_DEST).strip()
    if not dest_dir.startswith('/') or '..' in dest_dir.split('/'):
        return jsonify(ok=False, error='Đường dẫn đích không hợp lệ.'), 400
    if not dest_dir.endswith('/'):
        dest_dir += '/'

    from werkzeug.utils import secure_filename

    safe_name = secure_filename(file.filename) or 'upload.bin'
    dest_path = dest_dir + safe_name

    import tempfile

    fd, tmp_path = tempfile.mkstemp(prefix='push-')
    os.close(fd)
    try:
        file.save(tmp_path)
        size = os.path.getsize(tmp_path)
        if size > MAX_PUSH_SIZE_MB * 1024 * 1024:
            return jsonify(ok=False, error=f'File quá lớn (>{MAX_PUSH_SIZE_MB} MB)'), 413
        ok, output = adb_push(tmp_path, dest_path, serial=_selected_serial())
        _audit('push', dest=dest_path, size=size, ok=ok)
        if ok:
            return jsonify(ok=True, output=output, dest=dest_path)
        return jsonify(ok=False, error=output or 'adb push failed'), 500
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---- Quick controls (whitelist of adb shell actions) ------------------------
#
# Every entry is a fully-resolved argv list — no user input is ever spliced
# into the command, so shell injection is impossible. The map keys are the
# only strings the API accepts; anything else is rejected with 400.
#
# 'mode' = 'shell' → run via `adb [-s serial] shell <args...>`
#         'simple' → run via `adb [-s serial] <args...>` (e.g. reboot)
QUICK_ACTIONS: dict[str, dict] = {
    # nav keys (very common, no perms needed)
    'home': {'mode': 'shell', 'args': ['input', 'keyevent', 'KEYCODE_HOME']},
    'back': {'mode': 'shell', 'args': ['input', 'keyevent', 'KEYCODE_BACK']},
    'recent': {'mode': 'shell', 'args': ['input', 'keyevent', 'KEYCODE_APP_SWITCH']},
    'lock': {'mode': 'shell', 'args': ['input', 'keyevent', 'KEYCODE_POWER']},
    'wake': {'mode': 'shell', 'args': ['input', 'keyevent', 'KEYCODE_WAKEUP']},
    # volume
    'vol_up': {'mode': 'shell', 'args': ['input', 'keyevent', 'KEYCODE_VOLUME_UP']},
    'vol_down': {'mode': 'shell', 'args': ['input', 'keyevent', 'KEYCODE_VOLUME_DOWN']},
    'mute': {'mode': 'shell', 'args': ['input', 'keyevent', 'KEYCODE_VOLUME_MUTE']},
    # radios — `svc` works on most devices without root; on some MIUI/HyperOS
    # builds Wi-Fi enable is silently blocked at the system policy layer.
    'wifi_on': {'mode': 'shell', 'args': ['svc', 'wifi', 'enable']},
    'wifi_off': {'mode': 'shell', 'args': ['svc', 'wifi', 'disable']},
    'bt_on': {'mode': 'shell', 'args': ['svc', 'bluetooth', 'enable']},
    'bt_off': {'mode': 'shell', 'args': ['svc', 'bluetooth', 'disable']},
    'data_on': {'mode': 'shell', 'args': ['svc', 'data', 'enable']},
    'data_off': {'mode': 'shell', 'args': ['svc', 'data', 'disable']},
    # intents
    'open_settings': {'mode': 'shell', 'args': ['am', 'start', '-a', 'android.settings.SETTINGS']},
    'open_camera': {
        'mode': 'shell',
        'args': ['am', 'start', '-a', 'android.media.action.IMAGE_CAPTURE'],
    },
    'notifications': {
        'mode': 'shell',
        'args': ['cmd', 'statusbar', 'expand-notifications'],
    },
    # device-level
    'reboot': {'mode': 'simple', 'args': ['reboot']},
}


@app.route('/api/quick', methods=['POST'])
@login_required
def api_quick():
    """Run a pre-approved adb-shell quick action against the selected device.

    Body: form field `action=<key>` where key is in QUICK_ACTIONS.
    """
    action = (request.form.get('action') or '').strip()
    spec = QUICK_ACTIONS.get(action)
    if not spec:
        return jsonify(ok=False, error=f'Hành động không hợp lệ: {action!r}'), 400
    serial = _selected_serial()
    if spec['mode'] == 'shell':
        ok, output = adb_shell(spec['args'], serial=serial)
    else:
        ok, output = adb_simple(spec['args'], serial=serial)
    _audit('quick_action', action=action, ok=ok)
    if ok:
        return jsonify(ok=True, output=output)
    return jsonify(ok=False, error=output or 'adb command failed'), 500


# ---- Wireless ADB pair / connect / disconnect -------------------------------
@app.route('/api/adb/pair', methods=['POST'])
@login_required
def api_adb_pair():
    host = (request.form.get('host') or '').strip()
    port = (request.form.get('port') or '').strip()
    code = (request.form.get('code') or '').strip()
    if not is_valid_host(host) or not is_valid_port(port):
        return jsonify(ok=False, error='Host hoặc port không hợp lệ.'), 400
    if not code.isdigit() or not (4 <= len(code) <= 8):
        return jsonify(ok=False, error='Pair code phải là 4-8 chữ số.'), 400
    ok, output = adb_pair(host, port, code)
    _audit('adb_pair', host=host, port=port, ok=ok)
    if ok:
        return jsonify(ok=True, output=output)
    return jsonify(ok=False, error=output or 'adb pair failed'), 500


@app.route('/api/adb/connect', methods=['POST'])
@login_required
def api_adb_connect():
    host = (request.form.get('host') or '').strip()
    port = (request.form.get('port') or '').strip()
    if not is_valid_host(host) or not is_valid_port(port):
        return jsonify(ok=False, error='Host hoặc port không hợp lệ.'), 400
    ok, output = adb_connect(host, port)
    _audit('adb_connect', host=host, port=port, ok=ok)
    if ok:
        return jsonify(ok=True, output=output)
    return jsonify(ok=False, error=output or 'adb connect failed'), 500


@app.route('/api/adb/disconnect', methods=['POST'])
@login_required
def api_adb_disconnect():
    host = (request.form.get('host') or '').strip()
    port = (request.form.get('port') or '').strip()
    if host and not is_valid_host(host):
        return jsonify(ok=False, error='Host không hợp lệ.'), 400
    if port and not is_valid_port(port):
        return jsonify(ok=False, error='Port không hợp lệ.'), 400
    ok, output = adb_disconnect(host or None, port or None)
    _audit('adb_disconnect', host=host, port=port, ok=ok)
    if ok:
        return jsonify(ok=True, output=output)
    return jsonify(ok=False, error=output or 'adb disconnect failed'), 500


# ---- Session management -----------------------------------------------------
@app.route('/api/session/status', methods=['GET'])
@login_required
def api_session_status():
    """Report whether the device session is currently held by another client.

    The UI uses this to decide whether to show the "Force kick" button — we
    don't expose any identifying info about the other client because both
    are authenticated as the same user (single-account deployment).
    """
    with _state_lock:
        active = scpy_ctx is not None
    return jsonify(ok=True, active=active)


@app.route('/api/session/kick', methods=['POST'])
@login_required
def api_session_kick():
    """Forcibly disconnect whatever client is currently holding the socket.

    Useful when a previous tab crashed or was closed without cleanly
    releasing the lock — without this the only recovery was restarting
    the server. handle_disconnect will run and clear scpy_ctx /
    client_sid; the kicker then reconnects normally.
    """
    with _state_lock:
        sid = client_sid
    _audit('session_kick', target_sid=bool(sid))
    if not sid:
        return jsonify(ok=True, kicked=False)
    # flask_socketio's high-level disconnect() only works inside a socket
    # handler; from an HTTP route we have to drop down to the underlying
    # python-socketio Server. Tests stub this attribute directly.
    try:
        socketio.server.disconnect(sid)
    except Exception as exc:  # noqa: BLE001
        log.warning('socketio.server.disconnect failed: %s', exc)
        return jsonify(ok=False, error=str(exc)), 500
    return jsonify(ok=True, kicked=True)


@app.errorhandler(413)
def _too_large(_e):
    """Friendlier message for over-MAX_CONTENT_LENGTH uploads."""
    if request.path.startswith('/api/'):
        return jsonify(ok=False, error='File vượt quá giới hạn upload.'), 413
    return ('File quá lớn.', 413)


@app.route('/healthz')
def healthz():
    """Lightweight health check for load balancers / uptime monitors.

    Does not require auth and does not touch scrcpy / device state.
    """
    with _state_lock:
        has_client = client_sid is not None
    return jsonify(status='ok', has_client=has_client), 200


# --- socket.io handlers ----------------------------------------------------------
def video_send_task():
    global client_sid
    while True:
        with _state_lock:
            active = client_sid
        if active is None:
            break
        try:
            message = message_queue.get(timeout=0.05)
            socketio.emit('video_data', message, to=active)
        except queue.Empty:
            pass
        except Exception as e:  # noqa: BLE001 - background task shouldn't crash
            log.error('Error sending video data: %s', e)
        socketio.sleep(0)
    log.info('video_send_task stopped')


def send_video_data(data):
    message_queue.put(data)


@socketio.on('connect')
def handle_connect(auth=None):
    global scpy_ctx, client_sid
    if not _is_authed():
        log.info('Reject socket: unauthenticated sid=%s', request.sid)
        raise SocketConnectionRefusedError('Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.')

    with _state_lock:
        if scpy_ctx is not None:
            log.info('Reject socket: another client already connected (sid=%s)', request.sid)
            raise SocketConnectionRefusedError(
                'Đã có client khác đang điều khiển thiết bị. Vui lòng thử lại sau.'
            )
        client_sid = request.sid
        # Per-connection display_id from socket query (?display_id=2 for DeX),
        # falling back to the server-wide default. Validated as an int 0..99.
        req_disp = request.args.get('display_id') if request.args else None
        chosen_disp = display_id
        if req_disp is not None and req_disp != '':
            try:
                d = int(req_disp)
                if 0 <= d < 100:
                    chosen_disp = str(d)
            except (TypeError, ValueError):
                log.warning('Invalid display_id from client: %r', req_disp)
        # Optional virtual display (DeX-style on any Android 11+).
        # ?new_display=1920x1080/160 — validated against a strict regex
        # so it can't shell-inject when spliced into the scrcpy CLI.
        req_newdisp = request.args.get('new_display') if request.args else None
        chosen_new_display = None
        if req_newdisp is not None and req_newdisp != '':
            if is_valid_new_display(req_newdisp):
                chosen_new_display = req_newdisp
            else:
                log.warning('Invalid new_display from client: %r', req_newdisp)
        # Per-session pick (set via /devices) wins over env/CLI default.
        chosen_serial = _selected_serial()
        scpy_ctx = Scrcpy(
            serial=chosen_serial,
            display_id=chosen_disp,
            max_size=max_size,
            new_display=chosen_new_display,
        )
        # Forward device → browser clipboard updates. scrcpy server pushes a
        # CLIPBOARD message whenever the device clipboard changes (including
        # right after start, with the current contents).
        sid_for_clip = request.sid

        def _on_device_message(msg_type: int, payload: dict) -> None:
            if msg_type != 0:  # only clipboard
                return
            text = payload.get('text', '')
            if text is None:
                return
            try:
                socketio.emit('device_clipboard', {'text': text}, to=sid_for_clip)
            except Exception as exc:  # noqa: BLE001
                log.warning('emit device_clipboard failed: %s', exc)

        scpy_ctx.device_message_callback = _on_device_message

    try:
        scpy_ctx.scrcpy_start(send_video_data, video_bit_rate, max_fps=max_fps)
    except RuntimeError as e:
        log.warning('scrcpy_start refused: %s', e)
        with _state_lock:
            client_sid = None
            scpy_ctx = None
        raise SocketConnectionRefusedError(
            'Không thể khởi động scrcpy: ' + str(e) + '. Kiểm tra adb/USB Debugging.'
        ) from e
    except Exception as e:  # noqa: BLE001
        log.exception('scrcpy_start failed: %s', e)
        with _state_lock:
            client_sid = None
            scpy_ctx = None
        raise SocketConnectionRefusedError(
            'Lỗi khởi động scrcpy trên server. Xem log để biết thêm.'
        ) from e

    socketio.start_background_task(video_send_task)
    log.info('Socket connected sid=%s', request.sid)
    return True


@socketio.on('disconnect')
def handle_disconnect():
    global scpy_ctx, client_sid
    with _state_lock:
        ctx = scpy_ctx
        scpy_ctx = None
        client_sid = None
    log.info('Socket disconnected, stopping scrcpy (had_ctx=%s)', ctx is not None)
    if ctx is not None:
        try:
            ctx.scrcpy_stop()
        except Exception as e:  # noqa: BLE001
            log.warning('scrcpy_stop raised: %s', e)


@socketio.on('control_data')
def handle_control_data(data):
    with _state_lock:
        ctx = scpy_ctx
    if ctx is not None:
        try:
            ctx.scrcpy_send_control(data)
        except Exception as e:  # noqa: BLE001
            log.warning('scrcpy_send_control failed: %s', e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web server for scrcpy')
    parser.add_argument(
        '--video_bit_rate',
        default=video_bit_rate,
        help='scrcpy video bit rate (default: SCRCPY_VIDEO_BIT_RATE env or 8000000)',
    )
    parser.add_argument(
        '--max_fps',
        default=max_fps,
        help='scrcpy max fps (default: SCRCPY_MAX_FPS env or 60)',
    )
    parser.add_argument(
        '--max_size',
        default=max_size,
        help='Cap the longest edge in px; 0=device native (default: SCRCPY_MAX_SIZE env or 0)',
    )
    parser.add_argument(
        '--serial',
        default=adb_serial,
        help='ADB serial of the target device (default: ADB_SERIAL env, else auto)',
    )
    parser.add_argument(
        '--display_id',
        default=display_id,
        help='Display id to mirror; 0=main, 2=typical Samsung DeX (default: SCRCPY_DISPLAY_ID env or 0)',
    )
    parser.add_argument('--port', default=8000, type=int, help='listen port')
    parser.add_argument(
        '--host', default=os.environ.get('BIND_HOST', '0.0.0.0'), help='bind host (default 0.0.0.0)'
    )
    args = parser.parse_args()
    video_bit_rate = args.video_bit_rate
    max_fps = args.max_fps
    max_size = str(args.max_size or '0')
    adb_serial = args.serial or None
    display_id = str(args.display_id or '0')
    log.info(
        'Starting web-scrcpy on %s:%d (bit_rate=%s, max_fps=%s, max_size=%s, serial=%s, display_id=%s)',
        args.host,
        args.port,
        video_bit_rate,
        max_fps,
        max_size,
        adb_serial or '*',
        display_id,
    )
    # Loud warning: the Werkzeug dev server is single-threaded and will
    # stutter video noticeably under any real load. The Procfile / wsgi.py
    # ship the production-grade gunicorn+eventlet path; users running
    # `python app.py` for production deserve to know they're leaving
    # performance on the table. Set DISABLE_DEV_BANNER=1 to silence.
    if os.environ.get('DISABLE_DEV_BANNER') != '1':
        bar = '!' * 72
        bind = f'0.0.0.0:{args.port}'
        log.warning(
            '\n%s\n'
            '! Đang chạy Werkzeug development server (single-threaded).\n'
            '! Stream video sẽ KHÔNG mượt cho production. Chạy gunicorn:\n'
            '!\n'
            '!   pip install -r requirements-prod.txt\n'
            '!   gunicorn --worker-class eventlet -w 1 --bind %s wsgi:app\n'
            '!\n'
            '! Hoặc dùng `honcho start` (đọc Procfile có sẵn).\n'
            '! Đặt DISABLE_DEV_BANNER=1 để ẩn cảnh báo này.\n'
            '%s',
            bar,
            bind,
            bar,
        )
    socketio.run(app, host=args.host, port=args.port, allow_unsafe_werkzeug=True)
