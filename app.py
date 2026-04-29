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

from scrcpy import Scrcpy

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
video_bit_rate = os.environ.get('SCRCPY_VIDEO_BIT_RATE', '4000000')
max_fps = os.environ.get('SCRCPY_MAX_FPS', '60')
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
    received = (request.form.get('csrf_token') or '').strip()
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
@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username', DEFAULT_USERNAME))


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
        scpy_ctx = Scrcpy(serial=adb_serial, display_id=chosen_disp)

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
        help='scrcpy video bit rate (default: SCRCPY_VIDEO_BIT_RATE env or 4000000)',
    )
    parser.add_argument(
        '--max_fps',
        default=max_fps,
        help='scrcpy max fps (default: SCRCPY_MAX_FPS env or 60)',
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
    adb_serial = args.serial or None
    display_id = str(args.display_id or '0')
    log.info(
        'Starting web-scrcpy on %s:%d (bit_rate=%s, max_fps=%s, serial=%s, display_id=%s)',
        args.host,
        args.port,
        video_bit_rate,
        max_fps,
        adb_serial or '*',
        display_id,
    )
    socketio.run(app, host=args.host, port=args.port, allow_unsafe_werkzeug=True)
