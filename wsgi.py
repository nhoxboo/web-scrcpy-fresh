"""WSGI entrypoint for production servers (e.g. gunicorn + eventlet).

Usage:
    gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 wsgi:app

Notes:
    * Use exactly one worker. The scrcpy session state is process-local, so
      multiple workers would each try to claim the device.
    * eventlet must be monkey-patched before any other imports that touch
      stdlib networking; that is what this module does in its first lines.
"""

from __future__ import annotations

import eventlet  # noqa: I001 - must be first

eventlet.monkey_patch()

from app import app, socketio  # noqa: E402,F401

# Expose `app` as the WSGI callable; `socketio` is imported so that flask-socketio
# wires its handlers onto `app` at import time.

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000)
