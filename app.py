from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
from scrcpy import Scrcpy
import argparse
import queue
import os
import json

scpy_ctx = None
client_sid = None
message_queue = queue.Queue()
video_bit_rate = "1024000"

BASE_DIR = os.path.dirname(__file__)
AUTH_FILE = os.path.join(BASE_DIR, 'auth.json')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=None)


def _load_auth():
    if not os.path.exists(AUTH_FILE):
        data = {"username": "admin", "password": "admin123"}
        with open(AUTH_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return data
    with open(AUTH_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_auth(username: str, password: str):
    with open(AUTH_FILE, 'w', encoding='utf-8') as f:
        json.dump({"username": username, "password": password}, f)


def _is_authed() -> bool:
    return session.get('authenticated', False) is True


@app.route('/')
def index():
    if not _is_authed():
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username', 'admin'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        auth = _load_auth()
        if username == auth.get('username') and password == auth.get('password'):
            session['authenticated'] = True
            session['username'] = username
            return redirect(url_for('index'))
        flash('Sai tài khoản hoặc mật khẩu')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if not _is_authed():
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form.get('current_password') or ''
        new_username = (request.form.get('new_username') or '').strip() or session.get('username', 'admin')
        new_password = request.form.get('new_password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        auth = _load_auth()
        if current_password != auth.get('password'):
            flash('Mật khẩu hiện tại không đúng')
        elif len(new_password) < 6:
            flash('Mật khẩu mới tối thiểu 6 ký tự')
        elif new_password != confirm_password:
            flash('Xác nhận mật khẩu mới không khớp')
        else:
            _save_auth(new_username, new_password)
            session['username'] = new_username
            flash('Đổi thông tin đăng nhập thành công')
            return redirect(url_for('index'))

    return render_template('change_password.html', username=session.get('username', 'admin'))

def video_send_task():
    global client_sid
    while client_sid != None:
        try:
            message = message_queue.get(timeout=0.01)
            socketio.emit('video_data', message, to=client_sid)
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error sending data: {e}")
        finally:
            socketio.sleep(0.001)
    print(f"video_send_task stopped")

def send_video_data(data):
    message_queue.put(data)

@socketio.on('connect')
def handle_connect(auth=None):
    global scpy_ctx, client_sid
    if not _is_authed():
        print('reject socket: unauthenticated')
        return False

    print('Client connected')

    if scpy_ctx is not None:
        print(f'reject connection, client {scpy_ctx} is already connected')
        return False
    else:
        client_sid = request.sid
        scpy_ctx = Scrcpy()
        scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
        socketio.start_background_task(video_send_task)
        print(f'connectioned, client  {scpy_ctx}')

@socketio.on('disconnect')
def handle_disconnect():
    global scpy_ctx, client_sid
    client_sid = None
    print('Client disconnected', {scpy_ctx})
    if scpy_ctx is not None:
        scpy_ctx.scrcpy_stop()
        scpy_ctx = None
    print('scrcpy stopped, client {scpy_ctx}')

@socketio.on('control_data')
def handle_control_data(data):
    global scpy_ctx
    if scpy_ctx is not None:
        scpy_ctx.scrcpy_send_control(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web server for scrcpy')
    parser.add_argument('--video_bit_rate', default="2000000", help='scrcpy video bit rate')
    parser.add_argument('--port', default=8000, type=int, help='listen port')
    args = parser.parse_args()
    video_bit_rate = args.video_bit_rate
    socketio.run(app, host='0.0.0.0', port=args.port, allow_unsafe_werkzeug=True)