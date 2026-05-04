# Web Scrcpy Fresh — production container
#
# Builds a self-contained image with:
#   * Python 3.12 + project deps (incl. gunicorn + eventlet)
#   * android-tools-adb (so `adb devices` works without host adb)
#   * openssh-client (used by some adb wireless / pair flows)
#   * Non-root user; entrypoint runs gunicorn (NOT Werkzeug).
#
# USB device access:
#   The container needs access to host USB to talk to a phone over the cable.
#   docker-compose.yml mounts /dev/bus/usb and runs in privileged mode by
#   default. If you only use wireless ADB, you can drop both — see
#   `docker-compose.yml` comments.
#
# Build:
#   docker build -t web-scrcpy-fresh .
# Run (one-shot, replace with compose for persistence):
#   docker run --rm -it --privileged \
#     -v /dev/bus/usb:/dev/bus/usb \
#     -p 8000:8000 \
#     -e FLASK_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')" \
#     web-scrcpy-fresh

FROM python:3.12-slim AS runtime

# adb is needed by every code path that talks to the device. openjdk is NOT
# needed — scrcpy-server runs on the device, not the host. We DO need
# `procps` so gunicorn's worker management can read /proc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        android-tools-adb \
        openssh-client \
        procps \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root app user. We still mount /dev/bus/usb at runtime; that
# path is owned by root inside the container regardless, so the app needs
# to be in the `plugdev` group on the host or we run privileged.
RUN useradd --create-home --shell /bin/bash --uid 1000 webscrcpy

WORKDIR /app

# Install Python deps separately from app code so layer cache survives
# code changes.
COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-prod.txt

# Copy app source (after deps so cache works).
COPY . .

# Persist auth + audit + custom secret key on a named volume mounted at
# /data — see docker-compose.yml. We symlink the canonical filenames into
# /data so neither code nor users have to know about the volume.
RUN mkdir -p /data \
    && chown -R webscrcpy:webscrcpy /app /data

USER webscrcpy
EXPOSE 8000

# `/healthz` is the canonical endpoint (defined by the app itself, no auth
# needed). `curl -fsS` exits non-zero if the response is not 2xx, which is
# what Docker's healthcheck wants.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

# Use gunicorn + eventlet as the entrypoint. NEVER swap this for `python
# app.py` — that's the Werkzeug single-threaded path which is dev-only.
# -w 1 is REQUIRED: scrcpy session state is process-local; multiple workers
# would each try to claim the device.
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
