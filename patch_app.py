import os

BASE_DIR = r"C:\Users\Administrator\AppData\Local\hermes\workspace\web-scrcpy-fresh"
APP_PY = os.path.join(BASE_DIR, "app.py")

with open(APP_PY, encoding="utf-8") as f:
    content = f.read()

# 1. Replace globals
content = content.replace(
'''_state_lock = threading.Lock()
scpy_ctx = None
client_sid = None
message_queue = queue.Queue()
# Separate queue + emit task for audio so a slow audio consumer can't stall
# the video pipeline (the browser handles them through different MSE buffers).
audio_message_queue = queue.Queue()''',
'''_state_lock = threading.Lock()
# Multi-device state mapping: sid -> { "scpy_ctx": Scrcpy, "video_q": queue.Queue, "audio_q": queue.Queue, "tasks": [] }
scpy_sessions = {}'''
)

# 2. _shutdown_scrcpy
old_shutdown = '''    global scpy_ctx, client_sid
    with _state_lock:
        ctx = scpy_ctx
        scpy_ctx = None
        client_sid = None
    if ctx is not None:
        try:
            ctx.scrcpy_stop()
        except Exception as e:  # noqa: BLE001
            log.warning('scrcpy_stop during shutdown failed: %s', e)'''
new_shutdown = '''    global scpy_sessions
    with _state_lock:
        ctxs = [s['scpy_ctx'] for s in scpy_sessions.values() if s.get('scpy_ctx')]
        scpy_sessions.clear()
    for ctx in ctxs:
        try:
            ctx.scrcpy_stop()
        except Exception as e:
            log.warning('scrcpy_stop during shutdown failed: %s', e)'''
content = content.replace(old_shutdown, new_shutdown)

# 3. /healthz
content = content.replace(
'''    with _state_lock:
        has_client = client_sid is not None''',
'''    with _state_lock:
        has_client = len(scpy_sessions) > 0'''
)

# 4. /api/session/status
content = content.replace(
'''    with _state_lock:
        active = scpy_ctx is not None''',
'''    with _state_lock:
        # Simplification: active if this session is streaming
        active = any(s.get('scpy_ctx') and s['scpy_ctx'].serial == _selected_serial() for s in scpy_sessions.values())'''
)

# 5. /api/session/kick
content = content.replace(
'''        with _state_lock:
            if client_sid:
                socketio.disconnect(client_sid, namespace='/')''',
'''        with _state_lock:
            # Disconnect all clients watching this device
            for sid, s in list(scpy_sessions.items()):
                if s.get('scpy_ctx') and s['scpy_ctx'].serial == _selected_serial():
                    socketio.disconnect(sid, namespace='/')'''
)

# 6. video_send_task & audio_send_task
content = content.replace(
'''def video_send_task():
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


def audio_send_task():
    global client_sid
    while True:
        with _state_lock:
            active = client_sid
        if active is None:
            break
        try:
            message = audio_message_queue.get(timeout=0.05)
            socketio.emit('audio_data', message, to=active)
        except queue.Empty:
            pass
        except Exception as e:  # noqa: BLE001 - background task shouldn't crash
            log.error('Error sending audio data: %s', e)
        socketio.sleep(0)
    log.info('audio_send_task stopped')''',
'''def video_send_task(sid, q):
    while True:
        with _state_lock:
            if sid not in scpy_sessions: break
        try:
            message = q.get(timeout=0.05)
            socketio.emit('video_data', message, to=sid)
        except queue.Empty:
            pass
        except Exception as e:
            log.error('Error sending video data: %s', e)
        socketio.sleep(0)
    log.info(f'video_send_task stopped for {sid}')


def audio_send_task(sid, q):
    while True:
        with _state_lock:
            if sid not in scpy_sessions: break
        try:
            message = q.get(timeout=0.05)
            socketio.emit('audio_data', message, to=sid)
        except queue.Empty:
            pass
        except Exception as e:
            log.error('Error sending audio data: %s', e)
        socketio.sleep(0)
    log.info(f'audio_send_task stopped for {sid}')'''
)

# 7. send_video_data / send_audio_data
content = content.replace(
'''def send_video_data(data):
    message_queue.put(data)
    webrtc_mgr.broadcast_video(data)


def send_audio_data(data):
    audio_message_queue.put(data)''',
'''# Managed via closures in handle_connect instead
'''
)

# 8. handle_connect lock logic
old_connect = '''    global scpy_ctx, client_sid
    if not _is_authed():
        log.info('Reject socket: unauthenticated sid=%s', request.sid)
        raise SocketConnectionRefusedError('Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.')

    with _state_lock:
        if scpy_ctx is not None:
            log.info('Reject socket: another client already connected (sid=%s)', request.sid)
            raise SocketConnectionRefusedError(
                'Đã có client khác đang điều khiển thiết bị. Vui lòng thử lại sau.'
            )
        client_sid = request.sid'''

new_connect = '''    global scpy_sessions
    if not _is_authed():
        log.info('Reject socket: unauthenticated sid=%s', request.sid)
        raise SocketConnectionRefusedError('Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.')

    with _state_lock:
        sid = request.sid
        # Multi-device enabled!
        vq = queue.Queue()
        aq = queue.Queue()
        scpy_sessions[sid] = {'scpy_ctx': None, 'video_q': vq, 'audio_q': aq, 'tasks': []}'''
content = content.replace(old_connect, new_connect)

# 9. handle_connect Scrcpy assignment
old_assign = '''        chosen_serial = _selected_serial()
        scpy_ctx = Scrcpy('''
new_assign = '''        chosen_serial = _selected_serial()
        ctx = Scrcpy('''
content = content.replace(old_assign, new_assign)

content = content.replace('''        scpy_ctx.device_message_callback = _on_device_message''', '''        ctx.device_message_callback = _on_device_message''')

# 10. Start logic
old_start = '''    try:
        # Drain any leftover bytes from the previous session before the new
        # encoder starts pushing — otherwise the new VideoParser/AudioParser
        # instances on the browser side would consume stale frames first
        # (mid-NALU bytes parsed as the 64-byte device name + 12-byte size
        # header → garbage `Screen <huge>x<negative>` and a permanently
        # out-of-sync stream; stale AAC frames as the first audio).
        for q in (message_queue, audio_message_queue):
            try:
                while True:
                    q.get_nowait()
            except queue.Empty:
                pass
        scpy_ctx.scrcpy_start(
            send_video_data,
            chosen_bit_rate,
            max_fps=chosen_max_fps,
            audio_callback=send_audio_data if chosen_audio else None,
        )
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
        raise SocketConnectionRefusedError('Lỗi không xác định khi khởi động scrcpy.') from e

    # Start background threads to flush queues to this socket. SocketIO
    # starts these in greenlets (if eventlet) or real threads. We spawn them
    # fresh on every connect because they exit when the socket drops.
    socketio.start_background_task(video_send_task)
    if chosen_audio:
        socketio.start_background_task(audio_send_task)'''

new_start = '''    with _state_lock:
        scpy_sessions[sid]['scpy_ctx'] = ctx
        vq = scpy_sessions[sid]['video_q']
        aq = scpy_sessions[sid]['audio_q']

    def _send_video(data):
        vq.put(data)
        webrtc_mgr.broadcast_video(data)

    def _send_audio(data):
        aq.put(data)

    try:
        ctx.scrcpy_start(
            _send_video,
            chosen_bit_rate,
            max_fps=chosen_max_fps,
            audio_callback=_send_audio if chosen_audio else None,
        )
    except Exception as e:
        log.exception('scrcpy_start failed: %s', e)
        with _state_lock:
            if sid in scpy_sessions:
                del scpy_sessions[sid]
        raise SocketConnectionRefusedError(f'Lỗi khởi động scrcpy: {e}') from e

    t1 = socketio.start_background_task(video_send_task, sid, vq)
    with _state_lock:
        if sid in scpy_sessions: scpy_sessions[sid]['tasks'].append(t1)
    if chosen_audio:
        t2 = socketio.start_background_task(audio_send_task, sid, aq)
        with _state_lock:
            if sid in scpy_sessions: scpy_sessions[sid]['tasks'].append(t2)'''
content = content.replace(old_start, new_start)

# 11. handle_disconnect
old_disc = '''def handle_disconnect():
    global scpy_ctx, client_sid
    with _state_lock:
        ctx = scpy_ctx
        scpy_ctx = None
        client_sid = None
    if ctx is not None:
        log.info('Client disconnected, tearing down scrcpy session')
        ctx.scrcpy_stop()'''
new_disc = '''def handle_disconnect():
    sid = request.sid
    with _state_lock:
        s = scpy_sessions.pop(sid, None)
    if s and s.get('scpy_ctx'):
        log.info(f'Client {sid} disconnected, tearing down scrcpy session')
        s['scpy_ctx'].scrcpy_stop()'''
content = content.replace(old_disc, new_disc)

# 12. Input event routes (mouse_event, touch_event, etc.)
old_input = '''    with _state_lock:
        ctx = scpy_ctx
    if ctx is None:'''
new_input = '''    sid = request.sid
    with _state_lock:
        ctx = scpy_sessions.get(sid, {}).get('scpy_ctx')
    if ctx is None:'''
content = content.replace(old_input, new_input)


with open(APP_PY, "w", encoding="utf-8") as f:
    f.write(content)

print("Patched app.py")
