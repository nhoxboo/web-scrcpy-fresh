# Connection-first Android Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blank/offline remote-phone composition with a readable connection recovery state, while moving remote commands out of the sidebar and preserving all console behavior.

**Architecture:** Keep the existing server and inline Socket.IO/Scrcpy pipeline. Add a small view-state layer to the existing inline script that toggles classes on `#consoleMain`; CSS owns whether recovery or stream controls are visible. Existing remote command IDs remain unchanged when the command dock moves from the sidebar into the main work area.

**Tech Stack:** Flask/Jinja, vanilla browser JavaScript, CSS custom properties, pytest static regression tests, Chrome CDP QA.

## Global Constraints

- Work only on branch `fix/console-offline-composition`; never stage or edit the pre-existing `saved_wifi_devices.json` change.
- Never start, restart, stop, or modify production port `8000` during implementation. QA uses a non-production listener and `DISABLE_ADB_KEEPALIVE=1`.
- Preserve existing Android console DOM IDs, `data-*` names, inline Socket.IO/Scrcpy application bindings, forms, routes, CSRF and ADB behavior.
- Do not change `app.py`, socket transports, authentication or device selection behavior.
- `connection-pending`, `connection-error`, `connection-ready` are the only new console view-state classes.
- Keep media stage dark; all new surrounding UI uses existing semantic tokens; no template inline styles or raw hex colours.
- Every focusable target remains at least 44×44px; visible focus remains available.

---

### Task 1: Connection-first markup and static contract

**Files:**
- Modify: `templates/index.html:30-190`
- Modify: `tests/test_design_system.py`
- Test: `tests/test_template_bindings.py`

**Interfaces:**
- Consumes: existing `#reconnect` click handler and existing route `/devices`.
- Produces: `#consoleMain`, `#connectionRecovery`, `#connectionRetry`, `#statusText`, and a main-area `#quickDock` command dock.
- Preserves: every existing remote-control ID and inline event binding.

- [ ] **Step 1: Write failing source-contract tests**

Add tests that parse `templates/index.html` and assert:

```python
def test_console_main_owns_recovery_surface_and_command_dock():
    text = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="consoleMain"' in text
    assert 'id="connectionRecovery"' in text
    assert 'id="connectionRetry"' in text
    assert 'id="statusText"' in text
    assert 'id="quickDock"' in text
    assert text.index('id="quickDock"') > text.index('id="consoleMain"')
    assert text.index('id="quickDock"') > text.index('</aside>')
```

Add tests confirming the recovery card has `role="status"`, retry is `type="button"`, and `/devices` is its explicit recovery route.

- [ ] **Step 2: Run tests to prove RED**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py::test_console_main_owns_recovery_surface_and_command_dock -q
```

Expected: fail because the IDs and main-area dock do not yet exist.

- [ ] **Step 3: Implement minimal markup move**

Move the entire existing `<div class="control-toolbar quick-dock">…</div>` without changing any contained element ID, title, class, data attribute or content. Place it immediately after `<main id="consoleMain" ...>`.

Add the following recovery composition before the media stage:

```html
<section id="connectionRecovery" class="connection-recovery ui-card" role="status" aria-live="polite">
  <i class="fa-solid fa-plug-circle-xmark" aria-hidden="true"></i>
  <div>
    <p class="connection-kicker">TRẠNG THÁI THIẾT BỊ</p>
    <h1 id="connectionStatus">Đang chuẩn bị kết nối thiết bị…</h1>
    <p id="statusText">Đang kết nối…</p>
  </div>
  <div class="connection-recovery-actions">
    <button id="connectionRetry" class="button-primary" type="button">Kết nối lại</button>
    <a class="button-secondary" href="/devices">Đổi máy</a>
  </div>
</section>
```

Use `<main id="consoleMain" class="console-main main-content connection-pending">`. Keep the existing `#status` element as a compact status line, changing it to contain the nested `#statusText` only if script behavior is updated in Task 2; do not duplicate an ID.

- [ ] **Step 4: Run focused tests and binding test**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py tests/test_template_bindings.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the contract-preserving markup slice**

```bash
git add templates/index.html tests/test_design_system.py tests/test_template_bindings.py
git commit -m "feat: add connection recovery console composition"
```

### Task 2: Connection state transitions and semantic composition CSS

**Files:**
- Modify: `templates/index.html:380-780, 1919-1925, 2630-2645`
- Modify: `static/css/android-console.css`
- Modify: `tests/test_design_system.py`

**Interfaces:**
- Consumes: existing Socket.IO events `connect`, `disconnect`, `connect_error`, `screen_size`; existing `#reconnect` handler.
- Produces: `setConsoleConnectionState(state, message)` and CSS visibility rules for the three approved classes.
- Preserves: the existing `st(message)` call sites and all socket/control behavior.

- [ ] **Step 1: Write failing behavior/source tests**

Add tests requiring:

```python
assert "function setConsoleConnectionState(state, message)" in text
assert "consoleMain.classList.remove('connection-pending', 'connection-error', 'connection-ready')" in text
assert "consoleMain.classList.add(`connection-${state}`)" in text
assert "connectionRetry.addEventListener('click', () => reconnectButton.click())" in text
assert "statusText.textContent = message" in text
assert "connection-pending" in css
assert "connection-error" in css
assert "connection-ready" in css
```

Require CSS rules that hide `.phone-mockup` and `.zoom-bar` for pending/error, hide `.connection-recovery` for ready, and give `.connection-recovery` a bounded readable layout.

- [ ] **Step 2: Run tests to prove RED**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py::test_console_connection_state_contract -q
```

Expected: fail because state helper and CSS selectors do not exist.

- [ ] **Step 3: Implement the smallest state layer**

Introduce references once:

```javascript
const consoleMain = document.getElementById('consoleMain');
const statusText = document.getElementById('statusText');
const reconnectButton = document.getElementById('reconnect');
const connectionRetry = document.getElementById('connectionRetry');
```

Implement `setConsoleConnectionState` so it always sets class, `#connectionStatus.textContent`, and `#statusText.textContent`. Rewrite `st(message)` to update the status text with `textContent` rather than interpolating it through `innerHTML`.

Map events:

```javascript
socket.on('connect', () => setConsoleConnectionState('pending', 'Đã kết nối tới máy chủ; đang khởi động stream…'));
socket.on('disconnect', (reason) => setConsoleConnectionState('error', `Mất kết nối: ${reason}`));
socket.on('connect_error', (err) => setConsoleConnectionState('error', `Không thể khởi động stream: ${message}`));
// in the existing screen_size branch, before attachInput:
setConsoleConnectionState('ready', `Đã kết nối | Màn hình ${deviceW}×${deviceH}`);
```

Bind the new retry button by forwarding to the existing button:

```javascript
connectionRetry.addEventListener('click', () => reconnectButton.click());
```

Add semantic CSS in `android-console.css`:

- make `#quickDock` a full-width, compact main-area command rail;
- `.connection-recovery` uses a three-column desktop grid with icon, copy and actions; mobile stacks into one column;
- pending/error media stage stays dark but hides `.phone-mockup` and `.zoom-bar`;
- ready hides the recovery card; stream stage occupies the available main height;
- `.status` becomes a compact single line rather than a panel;
- preserve 44px controls and focus styles.

- [ ] **Step 4: Run focused static tests**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py tests/test_template_bindings.py -q
"/c/Program Files/Python312/python.exe" -m ruff check tests/test_design_system.py tests/test_template_bindings.py
"/c/Program Files/Python312/python.exe" -m ruff format --check tests/test_design_system.py tests/test_template_bindings.py
```

Expected: all pass.

- [ ] **Step 5: Commit state and CSS slice**

```bash
git add templates/index.html static/css/android-console.css tests/test_design_system.py tests/test_template_bindings.py
git commit -m "feat: prioritize offline recovery in console"
```

### Task 3: Isolated browser QA and release evidence

**Files:**
- Create: `docs/superpowers/verification/2026-09-16-connection-first-console-qa.md`
- Modify: no production source files unless a verified QA regression needs a separate fix cycle.

**Interfaces:**
- QA listener: `DISABLE_ADB_KEEPALIVE=1 "/c/Program Files/Python312/python.exe" app.py --port 8011`.
- Production service: `Hermes_scrcpy` remains untouched until branch review and CI are green.

- [ ] **Step 1: Run full automated verification**

```bash
"/c/Program Files/Python312/python.exe" -m pytest -q
"/c/Program Files/Python312/python.exe" -m ruff check .
"/c/Program Files/Python312/python.exe" -m ruff format --check .
git diff --check
```

Expected: tests, lint, format and whitespace checks pass.

- [ ] **Step 2: Run an isolated no-device QA listener**

```bash
DISABLE_ADB_KEEPALIVE=1 "/c/Program Files/Python312/python.exe" app.py --port 8011
```

Verify port 8011 only; never terminate, restart or modify 8000. Render authenticated console HTML via Flask test client or isolated controlled QA session without submitting device actions.

- [ ] **Step 3: Browser validation at four widths**

At 375, 768, 1024 and 1440 widths, inspect pending/error UI and assert:

- command dock is outside the sidebar;
- no blank phone shell, side keys, nav bar or zoom bar appears before `screen_size`;
- recovery title, detail, Retry and Change-device actions are visible;
- no horizontal overflow; focusable controls are 44px minimum;
- browser has no JavaScript exception.

- [ ] **Step 4: Document evidence and commit**

Write exact commands, viewport outcomes, known device limitation and production non-impact to the QA report. Commit:

```bash
git add docs/superpowers/verification/2026-09-16-connection-first-console-qa.md
git commit -m "docs: record connection-first console QA"
```

## Final review and rollout

Run a whole-branch review after Task 3. Only after the review is clean, push a PR and wait for GitHub CI. Restart production `Hermes_scrcpy` only after merge, green CI and explicit deployment approval; then verify `:8000/healthz`, `/login`, `/devices` and the offline console render.
