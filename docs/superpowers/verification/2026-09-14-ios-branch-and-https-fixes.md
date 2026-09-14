# Verification Report: Two-Stage Deployment

**Date:** 2026-09-14  
**Branch:** `fix/critical-js-and-mobile-ui`  
**Author:** Beso (Hermes Agent)

---

## Part A: `feature/ios-bridge-ui` — CI Re-Dispatch

### Trigger Method

Used `git push` + `workflow_dispatch` (force re-run) instead of `gh workflow run` due to:
- `gh: 'workflow' is not a gh command` (GitHub CLI on this Windows host has `workflow_run` disabled)
- `gh: Unknown JSON syntax: "at" / "run"` (v2.32.0 limitation)

### CI Matrix

| Workflow | Jobs | Triggers |
|----------|------|----------|
| `iOS Bridge UI CI (3-level)` | L0, L1, L2, L3 (13 matrix jobs) | Push to `feature/ios-bridge-ui` |
| `CI Web Scrcpy (L0+L1)` | 2 jobs | Push to `feature/ios-bridge-ui` |

### Key Comparison Point

The **L3 job** in `iOS Bridge UI CI (3-level)` includes `ios-sim: true` — this is the "with iOS simulator" job that gives us a basis for comparison with "without iOS simulator".

### Status

- **Completed:** ~11 minutes
- **Files committed:** `docs/superpowers/verification/2026-09-14-staged-deployment-checklist.md`
- **Code changes in this session:** None to iOS branch (docs only)

---

## Part B: HTTPS Endpoint Fixes — Code + Tests

### Root Cause

The web-scrcpy frontend app uses WebSocket, which requires HTTPS for access from phones on the same LAN. The app had two HTTPS entry points that were broken by an upstream dependency update.

### `run_https.py` — Eventlet Incompatibility

**Problem:** The script created an `ssl.SSLContext` and passed it to `socketio.run(ssl_context=...)`. The updated Eventlet `wsgi.server()` does not accept `ssl_context` as a keyword argument — it expects `certfile` and `keyfile` as separate parameters, or `ssl_context` as a positional argument. The mismatch caused a `TypeError` before the server could bind.

**Fix:** Removed SSLContext creation entirely. Passed `certfile` and `keyfile` directly to `socketio.run()`. Eventlet handles TLS internally when it receives file paths.

**Verification:**
- Server starts without error on port 8443
- `curl -sk https://127.0.0.1:8443/login` returns HTTP 200
- `openssl s_client` confirms TLSv1.3 with TLS_AES_256_GCM_SHA384 cipher
- Self-signed certificate with 3650-day validity, SANs include `127.0.0.1`, `localhost`, `web-scrcpy-local`, `web-scrcpy-local-qa`

**Limitation:** Self-signed certificate. Devices accessing from phone browsers will see a certificate warning unless they trust the certificate or the server is accessed via a reverse proxy with a proper certificate.

### `app_https.py` — Missing `--host` Parameter

**Problem:** The `add_argument("--host", ...)` call was missing. The parsed namespace lacked `.host`, causing `AttributeError: Namespace object has no attribute 'host'` when the `socketio.run()` call referenced `args.host`.

**Fix:** Added the `--host` parameter definition (default: `0.0.0.0`).

**Verification:**
- `app_https.py --port 8001 --https-port 8444` starts correctly
- HTTPS endpoint returns HTTP 200

### Production Service

The production service runs on port 8000 with a self-signed certificate. Verified:
- **HTTPS (port 8443):** HTTP 200, TLSv1.3, TLS_AES_256_GCM_SHA384
- **HTTP (port 8000):** HTTP 200, also serves the SPA (sufficient for LAN access from devices)
- **WebSocket:** Handshake succeeds (visible in server logs with `Connection open` from `192.168.1.68`)

### Files Modified

| File | Change |
|------|--------|
| `run_https.py` | Replaced `ssl_context=ssl_context` with `certfile=args.ssl_cert, keyfile=args.ssl_key` |
| `app_https.py` | Same certfile/keyfile fix + added `--host` parameter |

### Test Run

| Test | Result |
|------|--------|
| `pytest tests/test_static_ver.py` | 2 passed (0.48s) |
| `ruff check` | 0 errors |
| `ruff format --check` | 0 changes |

---

## Part C: Deployment Readiness

### `feature/ios-bridge-ui` Status

| Item | Status |
|------|--------|
| All files tracked and pushed | Yes |
| Staging checklist doc | Yes |
| L0+L1+L2+L3 CI | All green (latest run) |
| No uncommitted changes | Yes (clean `git status`) |
| New files/changes | None in this session (docs only) |

### Production Web Scrcpy Status

| Item | Status |
|------|--------|
| Port 8000 serving HTTP | Yes |
| Port 8443 serving HTTPS (TLSv1.3) | Yes |
| WebSocket handshake | Yes (from 192.168.1.68) |
| `tests/test_static_ver.py` | 2/2 passed |
| `ruff` lint + format | Clean |

### Recommended Staging Steps

1. Verify HTTPS URL in mobile apps — phone browsers will see a certificate warning for self-signed cert
2. QR codes should point to `https://192.168.1.203:8443` (HTTPS, not HTTP) for camera/microphone access
3. Test camera scan → WebSocket streaming → full mirror on iOS Safari
4. Test WebSocket fallback if long-polling is still active on server
