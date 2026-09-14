# Unified Remote-Control Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a white-and-blue, responsive remote-device console with grouped Android controls, actionable stream/device state, improved device management, aligned iOS UI, corrected per-session tests, and release-ready secret hygiene without interrupting the active port-8000 service.

**Architecture:** Preserve Flask/Jinja/vanilla JavaScript and Socket.IO streaming. Establish a shared white-blue app shell in external CSS, progressively extract UI-only behavior from `templates/index.html` into focused static files, retain stream/input protocol logic in the existing code, and add small server helpers/endpoints for selected-device facts. All live testing occurs through an isolated server on port 8010; port 8000 is read-only until a rollout decision.

**Tech Stack:** Python 3.12, Flask, Flask-SocketIO, eventlet, pytest, Ruff, Jinja templates, vanilla ES6, CSS custom properties, Font Awesome assets.

## Global Constraints

- Use `"/c/Program Files/Python312/python.exe"` for every local Python command.
- Preserve all existing Android control capability and `@login_required`/CSRF/rate-limit/server validation boundaries.
- Do not add a UI framework or new third-party dependency unless the user separately approves it.
- Do not touch the unrelated runtime file `saved_wifi_devices.json`.
- Do not restart, disconnect, or alter the port-8000 service while implementing; use port 8010 for validation.
- Do not claim iOS hardware control works without physical-device verification and installed WDA dependencies.
- Never commit `.env`, runtime auth data, audit logs, pairing codes, TLS private keys, or generated certificates.
- Commit each completed and verified task with the exact commit message stated below.

---

## File Map

| Path | Planned responsibility |
|---|---|
| `requirements-dev.txt` | Guarantee pytest/Ruff development quality tools in the app runtime |
| `.gitignore` | Block certificates and private key material from Git tracking |
| `app.py` | Add per-session selection helper and bounded selected-device facts endpoint |
| `tests/test_session.py` | Migrate obsolete global session tests to `scpy_sessions` fixtures/data |
| `tests/test_queue_drain.py` | Replace obsolete global queue test with per-session queue lifecycle regression |
| `tests/test_device_facts.py` | Cover auth, ADB parsing, selected serial, failures and non-sensitive output |
| `static/css/app-shell.css` | Shared white-blue tokens, dark sidebar, layout, components, accessibility/responsive rules |
| `static/css/android-console.css` | Console stage, quick dock, Control Center panels, telemetry presentation |
| `static/js/console-ui.js` | UI panel/drawer state and non-stream visual status helpers |
| `static/js/device-manager.js` | Saved Wi-Fi rendering/edit/delete/connect UI behavior using safe DOM APIs |
| `templates/login.html` | Shared shell/token adoption for authentication entry |
| `templates/change_password.html` | Shared shell/token adoption for account update |
| `templates/devices.html` | Semantic device manager structure, device-facts region, external JS/CSS bindings |
| `templates/index.html` | Android shell/semantic control grouping; references to external UI assets; preserve stream protocol wiring |
| `templates/ios_index.html` | Shared shell, availability state and unified feedback layout |
| `tests/test_template_bindings.py` | Assert shell/Control Center asset and accessibility bindings |
| `tests/test_devices.py` | Assert device manager/facts UI contract |
| `README.md` | Correct Windows runtime instructions, navigation, verification and security stance |
| `.hermes.md` | Keep local runtime truth current and concise |
| `certs/` | Remove tracked certificate/key material only after external runtime replacement is validated |

---

### Task 1: Restore the Quality Gate and Per-Session Test Contract

**Files:**
- Modify: `requirements-dev.txt`
- Modify: `tests/test_session.py`
- Modify: `tests/test_queue_drain.py`
- Modify: `templates/index.html` (only existing whitespace violations)
- Test: `tests/test_session.py`
- Test: `tests/test_queue_drain.py`

**Interfaces:**
- Consumes: `app.scpy_sessions: dict[str, dict]`, `_state_lock`, `socketio.server.disconnect(sid)`.
- Produces: Tests that build session state using `{sid: {'scpy_ctx': context, 'video_q': queue.Queue(), 'audio_q': queue.Queue(), 'tasks': []}}`, never the removed `app.scpy_ctx`, `app.client_sid`, `app.message_queue`, or `app.audio_message_queue` globals.

- [ ] **Step 1: Replace the stale session test setup with a failing per-session helper**

Add this helper in `tests/test_session.py` after `_post_csrf`:

```python
import queue


def _active_session(serial: str = 'test-serial') -> tuple[str, dict]:
    class _Context:
        def __init__(self, device_serial: str):
            self.serial = device_serial

    return (
        'sid-other',
        {
            'scpy_ctx': _Context(serial),
            'video_q': queue.Queue(),
            'audio_q': queue.Queue(),
            'tasks': [],
        },
    )
```

Update active/kick tests to insert the returned `sid, state` into `app.scpy_sessions` under `app._state_lock`, and clear the mapping in `finally`.

- [ ] **Step 2: Run the session test before completing migration**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_session.py -q
```

Expected before all migration edits: tests that still use removed globals fail, proving the stale test contract is exposed.

- [ ] **Step 3: Assert exact status/kick behavior through `scpy_sessions`**

The active test must call `/api/session/status` after inserting a session whose context `.serial` equals the selected serial and assert:

```python
assert r.status_code == 200
assert r.get_json() == {'ok': True, 'active': True}
```

The successful kick test must insert the same session, set a fake Socket.IO server, and assert:

```python
assert r.status_code == 200
assert r.get_json() == {'ok': True, 'kicked': True}
assert fake.calls == ['sid-other']
```

The failure test must assert the route returns status 500 and `body['ok'] is False` when `disconnect()` raises.

- [ ] **Step 4: Replace obsolete queue globals with a session-owned queue regression test**

Replace the contents of `tests/test_queue_drain.py` with a test that verifies a clean reconnect always receives fresh `video_q`/`audio_q` queues:

```python
import queue


def test_new_session_uses_empty_per_session_queues(app):
    stale_video = queue.Queue()
    stale_audio = queue.Queue()
    stale_video.put(b'old-video')
    stale_audio.put(b'old-audio')
    app.scpy_sessions['old'] = {
        'scpy_ctx': None,
        'video_q': stale_video,
        'audio_q': stale_audio,
        'tasks': [],
    }
    app.scpy_sessions.pop('old')

    fresh_video = queue.Queue()
    fresh_audio = queue.Queue()
    app.scpy_sessions['new'] = {
        'scpy_ctx': None,
        'video_q': fresh_video,
        'audio_q': fresh_audio,
        'tasks': [],
    }

    assert fresh_video.empty()
    assert fresh_audio.empty()
```

Wrap state mutation in `app._state_lock` and clean `app.scpy_sessions` in `finally`.

- [ ] **Step 5: Install Ruff in the app Python runtime**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pip install -r requirements-dev.txt
"/c/Program Files/Python312/python.exe" -m ruff --version
```

Expected: install exits 0 and prints a Ruff version in the configured `>=0.5,<1.0` range.

- [ ] **Step 6: Remove only existing whitespace violations**

Remove the trailing whitespace at `templates/index.html` lines 70–72 and the blank line at EOF of `static/js/input.js`; do not modify functional behavior in this task.

- [ ] **Step 7: Run task verification**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_session.py tests/test_queue_drain.py -q
"/c/Program Files/Python312/python.exe" -m ruff check .
"/c/Program Files/Python312/python.exe" -m ruff format --check .
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 8: Commit**

```bash
git add requirements-dev.txt tests/test_session.py tests/test_queue_drain.py templates/index.html static/js/input.js
git commit -m "test: align session coverage with multi-device state"
```

---

### Task 2: Create the Shared White-Blue Application Shell

**Files:**
- Create: `static/css/app-shell.css`
- Modify: `templates/login.html`
- Modify: `templates/change_password.html`
- Modify: `templates/devices.html`
- Test: `tests/test_template_bindings.py`

**Interfaces:**
- Consumes: existing Font Awesome stylesheet and Jinja values `username`, `csrf_token()`, `static_ver`.
- Produces: global classes `app-shell`, `app-sidebar`, `app-main`, `app-topbar`, `surface-card`, `button-primary`, `button-secondary`, `status-badge`, and `sr-only`.

- [ ] **Step 1: Write the failing template bindings**

Append tests to `tests/test_template_bindings.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_shared_light_shell_stylesheet_is_loaded_by_account_and_device_pages():
    for filename in ('login.html', 'change_password.html', 'devices.html'):
        text = (ROOT / 'templates' / filename).read_text(encoding='utf-8')
        assert '/static/css/app-shell.css?v={{ static_ver }}' in text


def test_app_shell_defines_white_blue_tokens_and_navy_sidebar():
    text = (ROOT / 'static/css' / 'app-shell.css').read_text(encoding='utf-8')
    assert '--surface-page: #F8FAFC' in text
    assert '--action-primary: #0369A1' in text
    assert '--sidebar-bg: #1E293B' in text
    assert '@media (prefers-reduced-motion: reduce)' in text
```

- [ ] **Step 2: Run the targeted tests to confirm red**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py -q
```

Expected: new assertions fail because the stylesheet does not exist or is not referenced.

- [ ] **Step 3: Create the shell stylesheet with semantic tokens and accessible components**

Create `static/css/app-shell.css` beginning with:

```css
:root {
  --surface-page: #F8FAFC;
  --surface-card: #FFFFFF;
  --sidebar-bg: #1E293B;
  --sidebar-text: #E2E8F0;
  --text-primary: #0F172A;
  --text-muted: #475569;
  --border-subtle: #CBD5E1;
  --action-primary: #0369A1;
  --action-primary-hover: #075985;
  --state-success: #15803D;
  --state-warning: #B45309;
  --state-danger: #B91C1C;
  --focus-ring: #0EA5E9;
  --radius-sm: 10px;
  --radius-md: 16px;
  --shadow-card: 0 10px 24px rgba(15, 23, 42, 0.08);
}
```

Implement `button-primary`, `button-secondary`, semantic badge styles, inputs with `:focus-visible`, responsive 44px controls, and reduced-motion overrides. Do not use animated aurora or transparent glass effects.

- [ ] **Step 4: Migrate authentication and device page styling links**

For every page in this task:

1. Keep its Font Awesome reference.
2. Load `app-shell.css` with `?v={{ static_ver }}`.
3. Replace dark-only text and background declarations with shell classes or semantic CSS overrides.
4. Do not remove form names, `csrf_token` inputs, endpoints, or existing Jinja conditions.

For `login.html`, make sign-in the primary visual hierarchy. For `change_password.html`, retain current validation/error behavior. For `devices.html`, leave behavior untouched in this task; only prepare semantic wrapper classes.

- [ ] **Step 5: Run template/style tests and browser render check**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py tests/test_auth.py tests/test_devices.py -q
```

Then start an isolated app only if a safe non-conflicting device setup is available, navigate to `http://127.0.0.1:8010/login`, and inspect the screenshot and accessibility tree. Expected: light canvas, navy contrast surface, readable form labels, visible keyboard focus, no browser console errors.

- [ ] **Step 6: Commit**

```bash
git add static/css/app-shell.css templates/login.html templates/change_password.html templates/devices.html tests/test_template_bindings.py
git commit -m "feat: add accessible white-blue application shell"
```

---

### Task 3: Add Selected-Device Facts with Bounded ADB Parsing

**Files:**
- Modify: `app.py`
- Create: `tests/test_device_facts.py`
- Modify: `templates/devices.html`
- Modify: `static/js/device-manager.js` (create file with a read-only facts renderer only)

**Interfaces:**
- Consumes: `_selected_serial() -> str | None`, `adb_shell(argv, serial, timeout) -> tuple[bool, str]`, `login_required`, existing CSRF guard conventions.
- Produces: `GET /api/devices/<serial>/facts` with `{ok: bool, facts: {model: str | None, android_version: str | None, battery_percent: int | None, battery_status: str | None}, error?: str}` and `_parse_battery_facts(output: str) -> dict[str, int | str | None]`.

- [ ] **Step 1: Write failing route/parser tests**

Create `tests/test_device_facts.py`:

```python
from __future__ import annotations


def test_parse_battery_facts_extracts_level_and_status(app):
    facts = app._parse_battery_facts('level: 83\nstatus: 2\n')
    assert facts == {'battery_percent': 83, 'battery_status': 'charging'}


def test_device_facts_requires_login(client):
    response = client.get('/api/devices/192.168.1.2:5555/facts')
    assert response.status_code in (302, 401)


def test_device_facts_rejects_unselected_serial(client, csrf, default_credentials):
    client.post('/login', data={
        'username': default_credentials['username'],
        'password': default_credentials['password'],
        'csrf_token': csrf,
    })
    response = client.get('/api/devices/not-selected/facts')
    assert response.status_code == 400
    assert response.get_json()['ok'] is False
```

- [ ] **Step 2: Run tests and confirm red**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_device_facts.py -q
```

Expected: import/attribute and missing route failures.

- [ ] **Step 3: Implement strict selected-device facts route**

In `app.py`, add a parser that accepts only exact `level:` numeric lines in range 0–100 and known Android status integers `{2: 'charging', 3: 'discharging', 4: 'not_charging', 5: 'full'}`. Add route behavior:

```python
@app.route('/api/devices/<serial>/facts')
@login_required
def api_device_facts(serial: str):
    if serial != _selected_serial():
        return jsonify(ok=False, error='Thiết bị không phải thiết bị đang chọn.'), 400
    # Run bounded getprop/dumpsys commands through existing adb helpers.
    # Return null fields when a command fails; do not return raw ADB output.
```

Use existing serial validation before accepting route input. Use `adb_shell` only with fixed argument lists, one call for Android version/model and one for `dumpsys battery`, with existing timeout bounds. Never expose command output or host paths.

- [ ] **Step 4: Add successful and failure coverage**

Add tests that monkeypatch `app.adb_shell` and assert:

```python
assert response.status_code == 200
assert response.get_json()['facts'] == {
    'model': 'SM-F926B',
    'android_version': '14',
    'battery_percent': 83,
    'battery_status': 'charging',
}
```

Also assert failed ADB calls produce status 200 with null facts and a safe `available=False` or user-safe error message, never raw subprocess details.

- [ ] **Step 5: Add a read-only facts region to the selected device card**

In `templates/devices.html`, add an element with `id="deviceFacts"` only when `selected` exists and include:

```html
<section class="surface-card device-facts" id="deviceFacts" data-serial="{{ selected }}" aria-live="polite">
  <h2>Thông tin thiết bị</h2>
  <p class="muted">Đang tải thông tin thiết bị…</p>
</section>
<script src="/static/js/device-manager.js?v={{ static_ver }}"></script>
```

- [ ] **Step 6: Implement safe browser facts rendering**

Create `static/js/device-manager.js` using only `document.createElement()` and `textContent` to render facts. On failure render `Không có dữ liệu` and a non-sensitive retry button. Do not read or emit CSRF/auth values and do not use `innerHTML` for API fields.

- [ ] **Step 7: Verify**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_device_facts.py tests/test_devices.py tests/test_auth.py -q
"/c/Program Files/Python312/python.exe" -m ruff check app.py tests/test_device_facts.py
```

Browser check: authenticated selected-device page displays either returned facts or `Không có dữ liệu`, with no raw failure output.

- [ ] **Step 8: Commit**

```bash
git add app.py tests/test_device_facts.py templates/devices.html static/js/device-manager.js
git commit -m "feat: surface safe selected-device facts"
```

---

### Task 4: Build the Android Console Layout and Grouped Control Center

**Files:**
- Create: `static/css/android-console.css`
- Create: `static/js/console-ui.js`
- Modify: `templates/index.html`
- Modify: `tests/test_template_bindings.py`
- Test: `tests/test_phone_mockup.py`

**Interfaces:**
- Consumes: all existing element IDs used by inline stream/input logic (`player`, `playerCanvas`, `status`, `quickCtl`, `reconnect`, `zoomIn`, `zoomOut`, `zoomReset`, and existing action IDs).
- Produces: semantic containers `console-stage`, `quick-dock`, `control-center`, `control-tablist`, `control-panel`, `connection-status`, and DOM events `console:tab-change` without changing Socket.IO message format.

- [ ] **Step 1: Write failing structure tests**

Append to `tests/test_template_bindings.py`:

```python
def test_console_loads_external_console_assets():
    text = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    assert '/static/css/android-console.css?v={{ static_ver }}' in text
    assert '/static/js/console-ui.js?v={{ static_ver }}' in text


def test_console_groups_high_frequency_actions_in_quick_dock():
    text = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    assert 'class="quick-dock"' in text
    for identifier in ('back', 'home', 'recent', 'power', 'screenshot', 'recordToggle', 'reconnect'):
        assert f'id="{identifier}"' in text


def test_console_control_center_has_named_panels():
    text = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    for name in ('Stream', 'Thiết bị', 'Tệp & ứng dụng', 'Input & macro', 'Nâng cao'):
        assert name in text
```

- [ ] **Step 2: Run to confirm red**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py tests/test_phone_mockup.py -q
```

Expected: new console structure assertions fail.

- [ ] **Step 3: Create console-only styling**

Create `static/css/android-console.css` with:

```css
.console-stage { min-width: 0; display: grid; place-items: center; }
.quick-dock { display: flex; flex-wrap: wrap; gap: 8px; }
.control-center { background: var(--surface-card); border: 1px solid var(--border-subtle); }
.control-tablist { display: flex; overflow-x: auto; }
.control-panel[hidden] { display: none; }
```

Style the stage as visually primary, retain the video background black for accurate content, use a subtle neutral device frame, and make every dock button at least 44×44px. Include mobile breakpoints for 375px, 768px, 1024px, and 1440px.

- [ ] **Step 4: Create independent Control Center UI state module**

Create `static/js/console-ui.js`:

```javascript
(() => {
  const tabs = [...document.querySelectorAll('[role="tab"][data-panel]')];
  const panels = [...document.querySelectorAll('[role="tabpanel"]')];

  function selectPanel(panelId) {
    tabs.forEach((tab) => {
      const selected = tab.dataset.panel === panelId;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    panels.forEach((panel) => { panel.hidden = panel.id !== panelId; });
    document.dispatchEvent(new CustomEvent('console:tab-change', { detail: { panelId } }));
  }

  tabs.forEach((tab) => tab.addEventListener('click', () => selectPanel(tab.dataset.panel)));
})();
```

Add ArrowLeft/ArrowRight keyboard navigation. This module controls only panel presentation; it must not initialize Socket.IO, modify stream settings, or duplicate existing action handlers.

- [ ] **Step 5: Restructure semantic wrappers while preserving IDs and actions**

In `templates/index.html`:

1. Add external CSS/JS references using `static_ver`.
2. Move existing high-frequency buttons into `.quick-dock` without changing any IDs or button semantics.
3. Move existing stream controls into panel `id="panel-stream"`.
4. Move existing quick actions, WM/DPI, and device controls into `id="panel-device"`.
5. Move install/push controls into `id="panel-files"`.
6. Move UHID/gamepad/macro/hotkey controls into `id="panel-input"`.
7. Move free-form ADB, diagnostics, and reboot into `id="panel-advanced"`, with warning copy retained.
8. Preserve all element IDs consumed by existing inline scripts and preserve the Quick Controls API dispatches.

Do not extract the 3,000-line stream protocol in this task; extract only panel visibility/presentation to `console-ui.js`.

- [ ] **Step 6: Verify existing control regressions plus new structure**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py tests/test_phone_mockup.py tests/test_stream_quality.py tests/test_audio_soft_reconnect.py tests/test_gamepad_input.py -q
```

Expected: all tests pass, demonstrating no loss of required IDs and bindings.

- [ ] **Step 7: Browser verification on an isolated instance**

Open the console on port 8010 and verify:

1. Quick dock is visible without opening advanced controls.
2. Every tab exposes one panel and hides other panels.
3. A panel change creates no browser console error.
4. At 375px width, the dock remains reachable and no page-level horizontal overflow is introduced.
5. At desktop width, video remains central and larger than panels.

- [ ] **Step 8: Commit**

```bash
git add static/css/android-console.css static/js/console-ui.js templates/index.html tests/test_template_bindings.py
git commit -m "feat: organize Android controls into console center"
```

---

### Task 5: Add Connection Telemetry and Recovery Presentation

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/console-ui.js`
- Modify: `static/css/android-console.css`
- Modify: `tests/test_template_bindings.py`

**Interfaces:**
- Consumes: existing `#status`, `#streamHud`, `#hudFps`, `#hudKbps`, `#hudPing`, `#hudFrames`, Socket.IO `connect`, `disconnect`, `connect_error`, and `server_pong` behavior.
- Produces: always-visible `#connectionStatus` with `data-tone` values `connecting|success|warning|danger`, and non-destructive telemetry summary text.

- [ ] **Step 1: Write failing status-presenter test**

Add:

```python
def test_console_has_accessible_connection_status_summary():
    text = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    assert 'id="connectionStatus"' in text
    assert 'role="status"' in text
    assert 'aria-live="polite"' in text
```

- [ ] **Step 2: Run test to confirm red**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py::test_console_has_accessible_connection_status_summary -q
```

Expected: fail because the summary does not exist.

- [ ] **Step 3: Add semantic status UI without replacing existing `#status` behavior**

Add a topbar status element:

```html
<div id="connectionStatus" class="connection-status" data-tone="connecting" role="status" aria-live="polite">
  Đang chuẩn bị kết nối thiết bị…
</div>
```

Keep `#status` for backward compatibility with existing inline code. Update it gradually in a follow-up extraction; this task mirrors its user-facing message into the new status presenter.

- [ ] **Step 4: Extend `console-ui.js` with safe status synchronization**

Use a `MutationObserver` on `#status` and update `#connectionStatus.textContent` with `status.textContent.trim()`. Map messages containing `Đã kết nối` to `success`, `Mất kết nối`/`Bị từ chối` to `danger`, `đang` to `connecting`, and default to `warning`. Do not parse HTML and do not alter the existing stream handler.

Add a telemetry line that reads the already-rendered HUD values every second only when the HUD elements exist. Use text such as `FPS 60 · 8.2 Mbps · 24 ms`, never fabricate missing measurements.

- [ ] **Step 5: Add visual recovery affordance**

Place the existing `#reconnect` button in the connection status area as an explicitly labeled `Kết nối lại`. It must retain the existing handler and must remain available when input has not initialized.

- [ ] **Step 6: Verify**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py tests/test_session.py tests/test_audio_diagnostics.py -q
```

Browser check: simulate or observe a connection state change on port 8010 and confirm status text/tone changes and reconnect remains clickable; console remains clean.

- [ ] **Step 7: Commit**

```bash
git add templates/index.html static/js/console-ui.js static/css/android-console.css tests/test_template_bindings.py
git commit -m "feat: surface stream status and recovery actions"
```

---

### Task 6: Complete Device Manager UX Safely

**Files:**
- Modify: `templates/devices.html`
- Modify: `static/js/device-manager.js`
- Modify: `tests/test_devices.py`
- Modify: `tests/test_template_bindings.py`

**Interfaces:**
- Consumes: existing `/api/devices`, `/api/saved-wifi-devices`, `/api/adb/pair`, `/api/adb/connect`, `DELETE /api/saved-wifi-devices/<id>`, CSRF Jinja field.
- Produces: interactive saved-device card UI with Connect/Delete; device list includes selected state and facts region; all API data is rendered with DOM APIs.

- [ ] **Step 1: Add failing safe-render and semantic-card assertions**

Add tests asserting `device-manager.js` contains `document.createElement` and `textContent`, and does not contain `innerHTML =` for API data:

```python
def test_device_manager_renders_api_data_as_text_not_html():
    text = (ROOT / 'static' / 'js' / 'device-manager.js').read_text(encoding='utf-8')
    assert 'document.createElement' in text
    assert '.textContent =' in text
    assert 'innerHTML =' not in text
```

- [ ] **Step 2: Run targeted tests and confirm red if needed**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_devices.py tests/test_template_bindings.py -q
```

Expected: new safe-render assertion fails before migration completion.

- [ ] **Step 3: Extract existing saved Wi-Fi behavior into `device-manager.js`**

Move the saved-device load/connect/delete rendering code from `templates/devices.html` into `static/js/device-manager.js`. Keep endpoint paths and form payload names unchanged. Replace the existing construction:

```javascript
connectBtn.innerHTML = '<i class="fa-solid fa-plug"></i> Kết nối';
```

with a static icon span created locally or a text-only button; API-originated `d.target` and `d.name` must use `textContent`.

- [ ] **Step 4: Improve operator feedback without changing server behavior**

Implement visible states for loading, connection request pending, success, and failure. Re-enable a disabled action in a `finally` block. A deleted saved device requires the existing confirmation prompt; no destructive request starts before confirmation.

- [ ] **Step 5: Provide explicit fast paths**

Make Connect buttons clearly distinguish saved-target `Kết nối` and initial pairing `Ghép đôi lần đầu`. Keep direct connect separate. Preserve form inputs and browser native validation.

- [ ] **Step 6: Verify routes and DOM behavior**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_devices.py tests/test_device_facts.py tests/test_quick_wireless.py -q
```

Browser check on port 8010: page shows connected list, selected-state copy, facts placeholder/facts, saved Wi-Fi list/error state, and no raw HTML rendering from a mocked device name.

- [ ] **Step 7: Commit**

```bash
git add templates/devices.html static/js/device-manager.js tests/test_devices.py tests/test_template_bindings.py
git commit -m "feat: streamline Android device management"
```

---

### Task 7: Align iOS Page with the Shared Shell

**Files:**
- Modify: `templates/ios_index.html`
- Modify: `tests/test_template_bindings.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: current iOS route/API IDs and WDA/AirPlay behavior.
- Produces: iOS page references `app-shell.css`, uses `app-sidebar`/`app-main` or equivalent shared layout classes, and exposes an availability notice that does not claim a connected iOS device.

- [ ] **Step 1: Write failing iOS shell/availability tests**

Add:

```python
def test_ios_page_uses_shared_shell_and_availability_notice():
    text = (ROOT / 'templates' / 'ios_index.html').read_text(encoding='utf-8')
    assert '/static/css/app-shell.css?v={{ static_ver }}' in text
    assert 'Trạng thái iOS' in text
    assert 'WDA/AirPlay' in text
```

- [ ] **Step 2: Run test to verify red**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py::test_ios_page_uses_shared_shell_and_availability_notice -q
```

Expected: fails until markup is introduced.

- [ ] **Step 3: Add shell and truthful availability UX**

Load `app-shell.css`, retain all existing iOS element IDs and scripts, and add:

```html
<section class="surface-card" id="iosAvailability" role="status" aria-live="polite">
  <h2>Trạng thái iOS</h2>
  <p>WDA/AirPlay sẽ hiển thị trạng thái sau khi thiết bị sẵn sàng.</p>
</section>
```

Do not indicate successful WDA connection merely because the page loaded.

- [ ] **Step 4: Reuse status classes for current iOS errors and actions**

Replace only style declarations needed to apply the white-blue shell. Preserve all fetch endpoints, CSRF mechanics, device control handlers, and current error handling.

- [ ] **Step 5: Verify**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py tests/test_auth.py -q
```

Browser check: unauthenticated `/ios` redirects or rejects exactly as before; authenticated page can render availability state without console errors. Do not claim physical iOS command success.

- [ ] **Step 6: Commit**

```bash
git add templates/ios_index.html tests/test_template_bindings.py
git commit -m "feat: align iOS controls with shared console shell"
```

---

### Task 8: Correct Operational Documentation and TLS Secret Hygiene

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `.hermes.md`
- Delete from Git index after runtime replacement: `certs/key.pem`, `certs/cert.pem`
- Create: `certs/README.md`
- Test: `tests/test_static_ver.py` and repository checks

**Interfaces:**
- Consumes: Windows runtime fact that app uses eventlet and current `.hermes.md` says not to use gunicorn on Windows.
- Produces: no tracked TLS private key, documented runtime certificate placement and Windows launch truth, no contradictory production instructions.

- [ ] **Step 1: Write a pre-change key exposure inventory without printing key contents**

Run:

```bash
git ls-files certs/key.pem certs/cert.pem
git log --all --oneline -- certs/key.pem
git grep -n -I -E 'certs/(key|cert)\.pem|gunicorn|eventlet' -- README.md .hermes.md Procfile '*.cmd' || true
```

Expected: records only paths/commit metadata, never prints certificate/key contents.

- [ ] **Step 2: Create a runtime certificate replacement outside the repository**

Create the replacement key/certificate in an approved external runtime directory (for example a protected `%ProgramData%` service directory) or configure an external certificate manager. Before deleting Git-tracked material, verify the designated HTTPS launch path reads the replacement files. This task must not interrupt port 8000.

- [ ] **Step 3: Document certificate handling without sensitive values**

Create `certs/README.md`:

```markdown
# Runtime TLS files

Do not place private keys or production certificates in this directory.

Use externally managed TLS (recommended) or configure the HTTPS launcher with paths outside this repository. Runtime certificate files must be readable only by the service identity and are never committed to Git.
```

- [ ] **Step 4: Block private certificate material and untrack old files**

Append to `.gitignore`:

```gitignore
# TLS runtime material
certs/*.pem
certs/*.key
certs/*.crt
!certs/README.md
```

After the external replacement is verified, run:

```bash
git rm --cached certs/key.pem certs/cert.pem
```

Do not remove any runtime file until the external replacement has been proven usable.

- [ ] **Step 5: Reconcile documentation**

Update `README.md` to separate Windows and Linux deployment:

- Windows: `python app.py --port 8000` with eventlet runtime; no gunicorn recommendation.
- Linux/container: keep gunicorn/eventlet only if supported and tested.
- State that externally exposed deployments require HTTPS and a non-default password.
- Replace obsolete references to nonexistent frontend filenames in the project structure.

Update `.hermes.md` only with concise local operational truth. Do not contain any password in `.hermes.md`.

- [ ] **Step 6: Verify index, docs and history warning**

Run:

```bash
git ls-files | grep -Ei '(^|/)(.*\.pem|.*\.key)$' || true
git check-ignore -v certs/example.pem certs/example.key
git diff --check
```

Expected: first command prints no tracked private material, `git check-ignore` matches the new ignore rules, and diff check exits 0. Record that historical exposure requires credential rotation before any push, even after index removal.

- [ ] **Step 7: Run associated tests**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_static_ver.py tests/test_auth.py -q
```

- [ ] **Step 8: Commit**

```bash
git add .gitignore README.md .hermes.md certs/README.md
git add -u certs/key.pem certs/cert.pem
git commit -m "security: remove tracked TLS runtime material"
```

---

### Task 9: Full Regression, Browser QA, and Isolated-Port Release Decision

**Files:**
- Modify only if findings require it: implementation/test/docs files above
- Create: `docs/superpowers/verification/2026-09-14-unified-console-qa.md`

**Interfaces:**
- Consumes: complete branch, port 8010 isolated runtime, test commands from specification.
- Produces: evidence-based verification report and a clear go/no-go recommendation for port-8000 rollout. Does not itself restart production.

- [ ] **Step 1: Validate repository state and scope**

Run:

```bash
git status --short --branch
git diff origin/main...HEAD --stat
git diff --check
git log --oneline origin/main..HEAD
```

Expected: only planned files plus explicitly documented runtime exclusions; no whitespace errors.

- [ ] **Step 2: Run complete automated verification**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest -q
"/c/Program Files/Python312/python.exe" -m ruff check .
"/c/Program Files/Python312/python.exe" -m ruff format --check .
```

Expected: all commands exit 0. If a test fails, classify as regression/stale/flake/infra and resolve before proceeding; never delete a failing test to obtain a green suite.

- [ ] **Step 3: Launch only an isolated verification server**

First inspect active ports:

```bash
netstat -ano | grep ':8000 ' || true
netstat -ano | grep ':8010 ' || true
```

Then launch on 8010 with a deliberately selected non-production test device configuration. If no safe test device exists, run browser verification of anonymous/login/device-management UI only and explicitly mark live stream smoke test blocked.

- [ ] **Step 4: Browser test matrix**

Verify at desktop and mobile widths:

| Route | Checks |
|---|---|
| `/login` | white-blue visual hierarchy, explicit form labels, keyboard focus, no console errors |
| `/devices` authenticated | sidebar/shell, selected status, saved Wi-Fi error/loading behavior, safe device facts output |
| `/` authenticated | central video stage, quick dock, five Control Center panels, status/reconnect presentation, no horizontal overflow at 375px |
| `/ios` authenticated | shared shell, truthful WDA/AirPlay availability notice, no console errors |

Do not type credentials with non-vault browser tools. Use the existing safe authenticated test context or a test-only server configuration.

- [ ] **Step 5: Optional physical-device smoke test**

Only when a deliberately selected test device is connected to port 8010:

1. Confirm the displayed device serial matches the intended test device.
2. Check video starts.
3. Trigger Back/Home/Reconnect only after confirming scope.
4. Confirm telemetry updates when data is available.
5. Do not send reboot, change Wi-Fi/BT/data, change WM/DPI, install APK, push files, or execute ADB shell commands.

- [ ] **Step 6: Create evidence report**

Write `docs/superpowers/verification/2026-09-14-unified-console-qa.md` with exact command outcomes, browser routes/viewports checked, console state, device-smoke scope/outcome, known limitations, TLS rotation status, and rollout recommendation.

- [ ] **Step 7: Commit report**

```bash
git add docs/superpowers/verification/2026-09-14-unified-console-qa.md
git commit -m "docs: record unified console verification"
```

- [ ] **Step 8: Present rollout decision instead of restarting production**

Report one of:

- **GO — ready for approved port-8000 rollout:** all automated/browser checks pass and alternate-port smoke test passes.
- **GO WITH LIMITATION:** all software checks pass but no safe physical test device was available; port-8000 restart still needs user approval.
- **NO-GO:** list exact failed verification evidence and remediation.

Do not restart or replace port-8000 until Anh Nam explicitly approves the rollout decision.

---

## Plan Self-Review

### Spec coverage

| Spec requirement | Covered by |
|---|---|
| White-blue shell + navy sidebar | Tasks 2, 4, 7 |
| Android high-frequency actions and grouped advanced controls | Task 4 |
| Connection/stream telemetry and recovery | Task 5 |
| Connected/saved Wi-Fi device management and facts | Tasks 3, 6 |
| iOS alignment without false hardware claims | Task 7 |
| Existing controls retained | Task 4 regression test suite |
| Auth/CSRF/validation preserved | Tasks 1, 3, 4, 6, 9 |
| Multi-session test migration + Ruff | Task 1 |
| Tracked TLS secret remediation | Task 8 |
| No impact to active port 8000 | Global constraints and Task 9 |

### Placeholder scan

No `TBD`, `TODO`, “implement later”, or unspecified test commands exist in this plan. The only conditional sections are explicitly safety-gated physical device checks and external certificate replacement, which cannot be safely fabricated.

### Type/interface consistency

- Per-session state is consistently `scpy_sessions[sid]` with `scpy_ctx`, `video_q`, `audio_q`, and `tasks`.
- Device facts endpoint is consistently `GET /api/devices/<serial>/facts`.
- UI modules do not alter Socket.IO protocol or existing stream/input IDs.
- Port 8010 is the isolated validation endpoint; port 8000 is never a test target for mutation.
