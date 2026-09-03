"""End-to-end stream test: login -> socket.io -> receive real H.264 video bytes."""
import base64, sys, time, requests, socketio, re

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
USER = sys.argv[2] if len(sys.argv) > 2 else "admin"
PW   = sys.argv[3] if len(sys.argv) > 3 else "Admin@2026"
DURATION = float(sys.argv[4]) if len(sys.argv) > 4 else 12.0

s = requests.Session()
r = s.get(f"{BASE}/login", timeout=10)
m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
if not m:
    print("FAIL: no csrf_token on /login"); sys.exit(1)
r = s.post(f"{BASE}/login",
           data={"username": USER, "password": PW, "csrf_token": m.group(1)},
           allow_redirects=False, timeout=10)
print(f"login -> {r.status_code} (302 = ok)")
if r.status_code != 302:
    print("FAIL: login rejected"); sys.exit(1)

sio = socketio.Client(http_session=s, reconnection=False,
                      logger=False, engineio_logger=False)

stats = {"video_bytes": 0, "video_msgs": 0, "audio_msgs": 0,
         "screen_size": None, "events": [], "errors": []}

@sio.event
def connect():
    stats["events"].append("connect")
    print("socket connected, sid =", sio.sid)

@sio.event
def connect_error(data):
    stats["errors"].append(f"connect_error: {data}")
    print("connect_error:", data)

@sio.event
def disconnect():
    stats["events"].append("disconnect")

@sio.on("video_data")
def on_video(data):
    stats["video_msgs"] += 1
    if isinstance(data, (bytes, bytearray)):
        stats["video_bytes"] += len(data)
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, (bytes, bytearray)):
                stats["video_bytes"] += len(v)
            elif isinstance(v, str):
                stats["video_bytes"] += len(v)
    elif isinstance(data, str):
        stats["video_bytes"] += len(data)

@sio.on("audio_data")
def on_audio(data):
    stats["audio_msgs"] += 1

@sio.on("screen_size")
def on_size(data):
    stats["screen_size"] = data
    print("screen_size:", data)

@sio.on("error")
def on_err(data):
    stats["errors"].append(f"error event: {data}")
    print("server error event:", data)

@sio.on("*")
def catch_all(event, data=None):
    if event not in ("video_data", "audio_data"):
        preview = str(data)[:120] if data is not None else ""
        stats["events"].append(f"{event}: {preview}")
        print(f"event {event}: {preview}")

try:
    sio.connect(BASE, transports=["polling"], wait=True, wait_timeout=25)
except Exception as e:
    print("FAIL connect:", type(e).__name__, e)
    print("events:", stats["events"]); print("errors:", stats["errors"])
    sys.exit(1)

t0 = time.time()
last = 0
while time.time() - t0 < DURATION:
    time.sleep(1.0)
    got = stats["video_bytes"]
    print(f"  t={time.time()-t0:4.1f}s  video_msgs={stats['video_msgs']:5d}  "
          f"bytes={got:9d}  (+{got-last} last sec)")
    last = got

sio.disconnect()

kb = stats["video_bytes"] / 1024.0
print("\n=== RESULT ===")
print(f"screen_size   : {stats['screen_size']}")
print(f"video msgs    : {stats['video_msgs']}")
print(f"video bytes   : {stats['video_bytes']} ({kb:.1f} KB)")
print(f"audio msgs    : {stats['audio_msgs']}")
print(f"errors        : {stats['errors']}")
print(f"events        : {stats['events'][:12]}")
if stats["video_bytes"] > 50 * 1024:
    print("\nSTREAM WORKS")
    sys.exit(0)
print("\nSTREAM FAILED (expected >50KB)")
sys.exit(2)
