# Unified Console QA Report — 2026-09-14

## Scope

Validated the white-blue UI upgrade, per-session test migration, selected-device facts API, Eventlet HTTPS wrapper, runtime TLS handling, and controlled production reload.

## Automated checks

| Check | Command | Result |
|---|---|---|
| Full suite | `"/c/Program Files/Python312/python.exe" -m pytest -q` | 199 passed, 1 Eventlet deprecation warning |
| Lint | `"/c/Program Files/Python312/python.exe" -m ruff check .` | Passed |
| Format | `"/c/Program Files/Python312/python.exe" -m ruff format --check .` | Passed |
| Diff whitespace | `git diff --check` | Passed |
| Tracked TLS material | `git ls-files | grep -Ei '(^|/)(.*\.pem|.*\.key)$'` | No tracked `.pem` or `.key` files |

## Isolated application checks

- Started HTTP QA instance on port `8010` using `DISABLE_ADB_KEEPALIVE=1`.
- Confirmed logs state that ADB keep-alive is disabled; no test instance initiated device reconnect activity.
- Verified login route on `8010` successfully returned `200`.
- Visual inspection confirmed light-blue canvas, white cards, dark-blue login CTA, readable typography, no visible clipping or overlap.
- Browser console backend did not provide console capture; no JavaScript errors were surfaced by the available browser tooling.

## HTTPS QA

- Created a **QA-only self-signed TLS certificate** outside the repository at `C:/ProgramData/web-scrcpy/runtime-tls/`.
- Fixed `run_https.py` and `app_https.py` for Eventlet by passing `certfile`/`keyfile` instead of unsupported `ssl_context`.
- HTTPS QA listener on `127.0.0.1:8443` returned `200` from `/login`.
- OpenSSL observed `TLSv1.3` and `TLS_AES_256_GCM_SHA384`.
- Certificate validation returned code `18` because this QA certificate is self-signed. It is suitable only for local verification, not a public deployment.

## Production reload

- Production is run by scheduled task `Hermes_scrcpy` from `E:/hermes-workspace/.hermes/scripts/hermes_scrcpy.cmd`.
- Controlled task restart completed.
- New listener process bound `0.0.0.0:8000` and `GET http://127.0.0.1:8000/healthz` returned `200` with `{"status":"ok","has_client":false}`.
- The production runtime continues serving HTTP on port 8000. It was not switched to the self-signed QA certificate.

## Security status

- `certs/key.pem` and `certs/cert.pem` were removed from Git tracking.
- `.gitignore` blocks `certs/*.pem`, `certs/*.key`, and `certs/*.crt` while keeping `certs/README.md`.
- Because the old private key existed in Git history, treat it as compromised and rotate/revoke any certificate that used it before an external push or public HTTPS deployment.

## Limitations

- No physical Android stream smoke test was performed on port 8010 because the QA environment intentionally disabled ADB keep-alive to avoid contacting the default device.
- No physical iOS/WDA validation was performed; the UI truthfully reports availability rather than asserting connectivity.

## Rollout decision

**GO WITH LIMITATION.** The code, UI entry path, HTTPS adapter, quality gates, and controlled port-8000 reload are verified. The remaining work for a public HTTPS rollout is to install a CA-signed certificate in the external runtime TLS location and configure the chosen public reverse-proxy/HTTPS launcher to use it.
