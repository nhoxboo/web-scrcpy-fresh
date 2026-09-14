# Spec: Web Scrcpy Fresh — Unified Control Console

## Status
Approved in principle by Anh Nam on 2026-09-14: implement the complete proposed upgrade, subject to this written specification and its implementation plan.

## Objective

Modernize Web Scrcpy Fresh into a bright white-and-blue remote-device console that makes the active mirrored screen the primary work surface, while retaining every current Android control capability and aligning Android/iOS workflows.

The primary operator is a trusted internal user controlling one or more Android devices over USB or ADB-over-Wi-Fi, with optional iOS AirPlay/WDA support. The system must remain usable on desktop and mobile browsers, preserve the current active device session during development, and provide clear recovery paths when a device or stream fails.

### Success criteria

1. All main application pages use a consistent white content canvas with blue actions and a dark navy sidebar (`#1E293B`) for contrast.
2. The Android control screen presents only high-frequency actions by default; advanced, destructive, and diagnostic functions are separated into named panels.
3. A visible device/stream status strip reports device identity, connection state, transport, decoder, FPS, Mbps, and round-trip latency where available.
4. Android device management supports connected devices, saved Wi-Fi targets, quick connect/disconnect, selected-device state, and a non-sensitive device-information summary (model, Android version, battery when ADB returns it).
5. iOS has the same navigation shell, status language, feedback patterns, and empty/error states as Android. This does not promise unavailable iOS dependencies or capabilities.
6. Existing supported controls remain available: navigation keys, power/volume, screenshot/recording, fullscreen, display selection, transport/decoder selection, stream quality, audio, turn-screen-off, virtual desktop, UHID, gamepad, macro, APK install, file push, ADB quick actions, WM/DPI controls, and diagnostics.
7. Authentication, CSRF, rate limits, upload validation, command validation, and session authorization remain enforced.
8. The test suite passes after test migration to the per-session architecture; Ruff lint and format checks run in the Python 3.12 environment; a browser inspection confirms no console errors on anonymous pages and the logged-in console.
9. The repository no longer tracks private TLS material. The runtime certificate/key are rotated and stored outside Git tracking before a future external push.

## Non-goals

- No rewrite from Flask/Flask-SocketIO to a new frontend framework.
- No database introduction or user/role model redesign.
- No cloud relay, public multi-tenant service, or unbounded remote command execution.
- No claim that iOS control works until `facebook-wda`, `tidevice`, WDA, and a physical iOS device are available and tested.
- No interruption or restart of the current port-8000 process until a new build is verified on an alternate port.

## Assumptions

1. The existing Flask + Socket.IO architecture remains the implementation base.
2. The active branch is `fix/critical-js-and-mobile-ui`; unrelated runtime change `saved_wifi_devices.json` remains untouched.
3. Python 3.12 at `C:/Program Files/Python312/python.exe` is the supported local test runtime.
4. Modern Chromium/Firefox/Safari browsers are supported; Internet Explorer and legacy browsers are out of scope.
5. The remote control endpoint is an internal trusted tool, but all HTTP/browser input remains untrusted and must be validated server-side.
6. Existing CSS Font Awesome assets remain in use. New dependencies are not required for the redesign.

## Tech stack

| Area | Technology |
|---|---|
| Server | Python 3.10–3.12, Flask, Flask-SocketIO, eventlet on Windows |
| Device control | bundled ADB, scrcpy server, `scrcpy.py` integration |
| Web client | Server-rendered Jinja, vanilla ES6, Socket.IO, MSE/WebCodecs, CSS |
| Tests | pytest; Ruff for lint and format |
| CI | GitHub Actions Python 3.10/3.11/3.12 matrix |

## Commands

Use the explicit Python executable on this Windows host:

```bash
# Install development tools into the project runtime
"/c/Program Files/Python312/python.exe" -m pip install -r requirements-dev.txt

# Unit/integration test suite
"/c/Program Files/Python312/python.exe" -m pytest -q

# Targeted test example
"/c/Program Files/Python312/python.exe" -m pytest tests/test_session.py -q

# Formatting and lint gates
"/c/Program Files/Python312/python.exe" -m ruff check .
"/c/Program Files/Python312/python.exe" -m ruff format --check .

# Verify current process before any local launch
netstat -ano | grep ':8000 '

# Launch an isolated verification server; must not reuse production port 8000
SCRCPY_LOCAL_PORT=5555 ADB_SERIAL=<serial> "/c/Program Files/Python312/python.exe" app.py --port 8010
```

## Target information architecture

### Shared shell

- **Sidebar:** dark navy; product identity, active device selector, Android/iOS navigation, account/settings links.
- **Top status bar:** current device name, state badge, stream telemetry, reconnect button, contextual error/recovery message.
- **White content canvas:** `#F8FAFC` background, `#FFFFFF` raised cards, `#0F172A` primary text, `#0369A1` primary CTA, semantic green/amber/red status colors.
- **Accessibility:** focus rings, visible labels/tooltips, 44px touch targets, keyboard operation, `prefers-reduced-motion` behavior, and minimum 4.5:1 text contrast.

### Android Console

1. **Stage:** mirrored device canvas stays central; fullscreen and zoom remain near the stage.
2. **Quick dock:** Back, Home, Recent, Power, volume, screenshot, record, keyboard, reconnect.
3. **Control Center:** tabbed or grouped panel with:
   - Stream: quality preset/custom bitrate/FPS, audio, screen-off, transport, decoder, display, virtual desktop.
   - Device: lock/wake, Wi-Fi/BT/mobile data, settings/camera/notifications, WM/DPI, device facts.
   - Files and apps: install APK, push file, drag/drop.
   - Input and automation: UHID, pointer lock, gamepad, macro, hotkeys.
   - Advanced: explicitly labeled ADB shell and diagnostics, guarded destructive actions (such as reboot).
4. **State feedback:** every action has pending, success, and failure feedback without replacing unrelated connection status.

### Device management

- Connected Android devices appear as cards with serial, device state, model, transport, selected state, and available health facts.
- Saved Wi-Fi devices appear as a compact list with Connect, edit name, delete, last-used state, and clear failure output.
- Pair and direct connect stay distinct, retain existing server validation, and have descriptive help.
- Device facts are best-effort only: unavailable ADB fields display `Không có dữ liệu`, never a fabricated value.

### iOS

- Apply shared shell and visual tokens to `ios_index.html`.
- Present WDA/AirPlay availability explicitly and provide setup/retry guidance.
- Retain existing click, drag, home, lock, text, backspace, enter, and rotation APIs.

## Project structure and ownership

| Path | Responsibility |
|---|---|
| `app.py` | Flask routes, auth, API input validation, per-Socket.IO-session orchestration |
| `scrcpy.py` | ADB/scrcpy lifecycle and protocol implementation |
| `templates/index.html` | Android console semantic markup and minimal page wiring only |
| `templates/devices.html` | Device manager markup and non-sensitive UI state |
| `templates/ios_index.html` | iOS control screen markup |
| `templates/login.html` / `change_password.html` | Authentication/account pages |
| `static/css/app-shell.css` | Shared white-blue layout, semantic tokens, components, responsive rules |
| `static/css/android-console.css` | Android-stage and control-center styling |
| `static/js/console-ui.js` | UI state, panels, status presentation, non-stream controls |
| `static/js/device-manager.js` | Saved Wi-Fi and device manager client behavior |
| `static/js/input.js` | Scrcpy pointer/UHID/gamepad input protocol; no visual layout code |
| `tests/` | Behavioural endpoint/session/template tests grouped by feature |
| `docs/superpowers/specs/` | Approved design specifications |
| `docs/superpowers/plans/` | Execution plan derived from this specification |

The existing inline control code will be migrated progressively rather than rewritten in a single change. Each extraction must leave the console operable and covered by tests.

## Code style

Python: type hints on new public helpers, snake_case, small pure helpers for parsing/selection, no broad state globals for per-client device sessions.

```python
def _session_for_selected_device() -> tuple[str | None, dict | None]:
    selected_serial = _selected_serial()
    for sid, session_state in scpy_sessions.items():
        context = session_state.get('scpy_ctx')
        if context and context.serial == selected_serial:
            return sid, session_state
    return None, None
```

JavaScript: `const` by default, event listeners instead of inline event attributes, text inserted via `textContent` rather than `innerHTML` for data, and one module responsibility per file.

```javascript
export function setStatus(element, { tone, message }) {
  element.dataset.tone = tone;
  element.textContent = message;
}
```

CSS: semantic custom properties in the shared shell; no new raw hex colors inside template inline styles. Motion lasts 150–300ms and respects reduced-motion.

## Testing strategy

| Level | Coverage |
|---|---|
| pytest routes | Auth, CSRF, validation, status, device facts, session-kick and failures |
| pytest regression | Session queue cleanup and per-session state; stale reconnect behavior |
| template assertions | Required control groups, accessibility labels, static asset versioning, absence of deprecated inline controls where migrated |
| Ruff | Lint and formatting under Python 3.12 |
| browser | Login, devices page, and console at desktop/mobile widths; visual hierarchy, console cleanliness, keyboard focus and basic route actions |
| manual device validation | Only against the isolated verification server and a deliberately selected test device; screenshot/reconnect/basic navigation/stream telemetry |

Tests must target `scpy_sessions` and real per-session queues. Obsolete global-state tests will be replaced, not merely deleted.

## Security and operational boundaries

### Always

- Preserve `@login_required`, CSRF validation, current rate limits, ADB argument validation, upload magic-byte checks, and ADB command bounds.
- Keep every new API response free of credentials, secrets, private paths, and raw stack traces.
- Use `textContent` for API-provided device metadata in browser code.
- Run tests, Ruff lint/format, `git diff --check`, and browser verification before a commit.
- Test on a non-production port before restarting or replacing port-8000 runtime.

### Ask first

- New third-party dependencies, new external integrations, changes to authentication/CORS/rate limits, database/schema work, broad destructive cleanup, or public deployment changes.
- Any action that disconnects a device or changes device configuration outside the explicit test target.

### Never

- Commit credentials, TLS private keys, `.env`, authentication records, runtime audit logs, device pairing codes, or device content.
- Execute an ADB shell command received from an untrusted web page or browser output.
- Disable security headers or server-side validation to make a UI flow easier.
- Restart the active port-8000 process without a tested alternate-port build and a rollout decision.

## Security remediation: tracked TLS private key

`certs/key.pem` is tracked by Git and is a credential material finding. Remediation must:

1. Generate a new runtime certificate/key pair outside tracked project files or use an externally managed certificate.
2. Change launch configuration to reference that runtime location.
3. Add `*.pem`, `*.key`, and `certs/` runtime materials to `.gitignore`, while keeping only non-secret documentation/templates if necessary.
4. Remove tracked certificate/key files from the index without deleting the live replacement.
5. Verify no tracked private key remains with `git ls-files` and inspect Git history impact.
6. Do not push until the new key is active and the old key is considered revoked.

## Delivery phases

1. **Foundation:** Make test architecture match `scpy_sessions`; provision Ruff; resolve whitespace/lint drift; document Windows runtime truth.
2. **Shared visual system:** Create white-blue tokens/shell; migrate login, devices, password pages; responsive and accessibility baseline.
3. **Android console:** Extract console UI code/styles from `index.html`; introduce quick dock, grouped Control Center, status telemetry presentation, recovery UX.
4. **Device management:** Add validated best-effort device facts and improve selected/saved Wi-Fi interaction.
5. **iOS alignment:** Apply shell and availability/recovery UX without claiming unsupported hardware behavior.
6. **Hardening and release readiness:** Rotate/remove TLS key, update docs, full automated/browser validation, isolated-port smoke test, then produce rollout decision.

## Open questions resolved for this scope

- Default implementation priority is full scope, delivered in safe sequential phases rather than a risky rewrite.
- The visual direction is white-and-blue content with dark-navy sidebar, not dark Liquid Glass.
- No additional UI framework is introduced.
- The active live session is protected; browser/device validation uses a separate port and selected test device.
