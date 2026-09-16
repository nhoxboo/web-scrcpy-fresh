# Accessible White–Blue Control Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mixed dark-glass/light-shell UI with one accessible white–blue control console across Login, Device Management, Android Control, iOS, and Password pages without altering ADB, WebSocket, auth, or stream behavior.

**Architecture:** `static/css/app-shell.css` becomes the semantic color, typography, accessibility, and primitive component layer. A new `static/css/control-console.css` owns shared layouts and page-level console patterns. Templates consume semantic classes only; inline dark glass styling is removed while stable element IDs, form names, routes, and JavaScript hooks remain unchanged.

**Tech Stack:** Flask/Jinja templates, vanilla JavaScript, CSS custom properties, Font Awesome, pytest, Ruff, Flask-SocketIO/Eventlet.

## Global Constraints

- Preserve every existing ADB, WebSocket, authentication, device-facts, and stream API contract.
- Preserve all element IDs referenced by `static/js/*.js` and the inline JavaScript in `templates/index.html`.
- Do not modify or commit `saved_wifi_devices.json`.
- Do not load `static/css/glass.css` from production templates after migration.
- Application styles use semantic CSS variables; do not add raw color hex literals to HTML templates.
- Normal text must have WCAG AA contrast of at least 4.5:1; only the media stage may remain dark.
- Inputs and buttons have a 44px minimum touch/click target; icon-only controls require `aria-label`.
- Test isolated QA using `DISABLE_ADB_KEEPALIVE=1`; do not restart the port-8000 service until all QA steps pass.
- Make every task an atomic commit and run the listed verification before committing.

---

## File map

| File | Responsibility |
|---|---|
| `static/css/app-shell.css` | Semantic tokens, reset, typography, focus, primitive cards/forms/buttons/status components. |
| `static/css/control-console.css` | Shared responsive shell, navigation, device rows, Wi-Fi workflow, device facts, media-stage and console layout. |
| `templates/login.html` | Accessible light login card using shared primitives. |
| `templates/change_password.html` | Accessible light password form using shared primitives. |
| `templates/devices.html` | Device selection, saved Wi-Fi rows, Pair/Connect workflow, feedback and device facts. |
| `templates/index.html` | Android control console layout; preserves all existing IDs and in-page JS event bindings. |
| `templates/ios_index.html` | Truthful iOS availability screen using shared primitives. |
| `static/js/device-manager.js` | Renders device fact cards with semantic classes and accessible text. |
| `tests/test_design_system.py` | Static regression tests for tokens, theme collision removal, semantic class contracts, and template accessibility markers. |
| `tests/test_template_bindings.py` | Existing binding coverage; update expected stylesheet references if necessary. |

---

### Task 1: Establish the semantic theme foundation

**Objective:** Replace the competing light compatibility layer with a complete accessible token/primitives stylesheet and introduce the shared console layout stylesheet.

**Files:**
- Create: `static/css/control-console.css`
- Create: `tests/test_design_system.py`
- Modify: `static/css/app-shell.css`
- Modify: `tests/test_template_bindings.py`

**Interfaces:**
- Produces semantic tokens: `--color-canvas`, `--color-surface`, `--color-text`, `--color-text-secondary`, `--color-text-muted`, `--color-primary`, `--color-danger`, `--color-sidebar`.
- Produces primitives: `.ui-card`, `.ui-label`, `.ui-input`, `.button-primary`, `.button-secondary`, `.button-danger`, `.status-banner`, `.empty-state`, `.data-fact`.
- Produces shared layout classes: `.console-shell`, `.console-sidebar`, `.console-main`, `.page-container`, `.workflow-grid`, `.media-stage`.

- [ ] **Step 1: Write the failing static test for required token and primitive contracts**

Create `tests/test_design_system.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_accessible_theme_exposes_required_semantic_tokens():
    css = (ROOT / "static/css/app-shell.css").read_text(encoding="utf-8")
    for token in (
        "--color-canvas: #F6F9FC",
        "--color-surface: #FFFFFF",
        "--color-text: #102A43",
        "--color-text-secondary: #243B53",
        "--color-text-muted: #486581",
        "--color-primary: #0B74DE",
        "--color-danger: #A61B3C",
        "--color-sidebar: #163A5F",
    ):
        assert token in css


def test_theme_defines_shared_accessible_component_contracts():
    css = (ROOT / "static/css/app-shell.css").read_text(encoding="utf-8")
    for selector in (
        ".ui-card",
        ".ui-label",
        ".ui-input",
        ".button-primary",
        ".button-secondary",
        ".button-danger",
        ".status-banner",
        ".empty-state",
        ".data-fact",
    ):
        assert selector in css
    assert "min-height: 44px" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
```

- [ ] **Step 2: Run the new test to verify failure**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py -q
```

Expected: FAIL because the new semantic token names and primitive selectors are absent.

- [ ] **Step 3: Implement `app-shell.css` semantic tokens and primitives**

Replace legacy aliases with the following foundation (retain aliases only where an unchanged JavaScript/template selector still needs them):

```css
:root {
  --color-canvas: #F6F9FC;
  --color-surface: #FFFFFF;
  --color-surface-subtle: #EEF5FC;
  --color-border: #D7E2EE;
  --color-border-strong: #AFC3D8;
  --color-text: #102A43;
  --color-text-secondary: #243B53;
  --color-text-muted: #486581;
  --color-text-inverse: #FFFFFF;
  --color-text-placeholder: #627D98;
  --color-primary: #0B74DE;
  --color-primary-hover: #075DB4;
  --color-primary-pressed: #054A8F;
  --color-primary-subtle: #E7F1FD;
  --color-focus: #0B74DE;
  --color-success: #0F7B46;
  --color-success-subtle: #E7F7EF;
  --color-warning: #9A5B00;
  --color-warning-subtle: #FFF4DB;
  --color-danger: #A61B3C;
  --color-danger-subtle: #FFF1F3;
  --color-sidebar: #163A5F;
  --color-sidebar-hover: #1E4A75;
  --color-sidebar-active: #DCEEFF;
  --color-sidebar-text: #F7FBFF;
  --color-sidebar-muted: #C5D9EC;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --shadow-card: 0 8px 20px rgba(16, 42, 67, 0.08);
  --transition-fast: 160ms ease-out;
  color-scheme: light;
}

html { background: var(--color-canvas); }
body {
  margin: 0;
  min-height: 100dvh;
  background: var(--color-canvas);
  color: var(--color-text);
  font: 400 16px/1.5 Inter, "Segoe UI", Arial, sans-serif;
}

.ui-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}
.ui-label { color: var(--color-text-secondary); font-size: 14px; font-weight: 600; }
.ui-input {
  min-height: 44px;
  width: 100%;
  padding: 10px 12px;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
}
.ui-input::placeholder { color: var(--color-text-placeholder); opacity: 1; }
.ui-input:focus-visible, button:focus-visible, a:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--color-focus) 35%, transparent);
  outline-offset: 2px;
  border-color: var(--color-focus);
}
.button-primary, .button-secondary, .button-danger {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
  transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}
.button-primary { background: var(--color-primary); color: var(--color-text-inverse); border-color: var(--color-primary); }
.button-primary:hover { background: var(--color-primary-hover); border-color: var(--color-primary-hover); }
.button-secondary { background: var(--color-surface); color: var(--color-text); border-color: var(--color-border-strong); }
.button-secondary:hover { background: var(--color-surface-subtle); border-color: var(--color-primary); }
.button-danger { background: var(--color-danger-subtle); color: var(--color-danger); border-color: color-mix(in srgb, var(--color-danger) 36%, var(--color-surface)); }
.status-banner, .empty-state, .data-fact { color: var(--color-text-secondary); }
```

Add compatibility mappings used by existing code only after the semantic tokens, for example `--surface-page: var(--color-canvas)`, `--text-primary: var(--color-text)`, and `--action-primary: var(--color-primary)`.

- [ ] **Step 4: Implement the shared layout stylesheet**

Create `static/css/control-console.css` with no raw colors except the media-stage dark surface:

```css
.console-shell { min-height: 100dvh; display: grid; grid-template-columns: 264px minmax(0, 1fr); background: var(--color-canvas); }
.console-sidebar { background: var(--color-sidebar); color: var(--color-sidebar-text); padding: 20px 12px; }
.console-main { min-width: 0; background: var(--color-canvas); }
.page-container { width: min(100% - 64px, 1440px); margin: 0 auto; padding: 32px 0 48px; }
.workflow-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.media-stage { background: #0B1220; color: var(--color-text-inverse); }
@media (max-width: 1023px) { .console-shell { grid-template-columns: 1fr; } .console-sidebar { display: none; } .page-container { width: min(100% - 48px, 1440px); padding-top: 24px; } }
@media (max-width: 767px) { .page-container { width: min(100% - 32px, 1440px); padding-top: 16px; } .workflow-grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 5: Run static tests and formatting checks**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py tests/test_template_bindings.py -q
"/c/Program Files/Python312/python.exe" -m ruff check tests/test_design_system.py tests/test_template_bindings.py
"/c/Program Files/Python312/python.exe" -m ruff format --check tests/test_design_system.py tests/test_template_bindings.py
git diff --check
```

Expected: all commands pass.

- [ ] **Step 6: Commit the theme foundation**

```bash
git add static/css/app-shell.css static/css/control-console.css tests/test_design_system.py tests/test_template_bindings.py
git commit -m "feat: establish accessible white-blue design tokens"
```

---

### Task 2: Rebuild Device Management as the readable connection workflow

**Objective:** Convert `devices.html` from mixed inline dark styles into semantic white–blue cards while keeping Pair, Connect, saved-device, selection, and facts behavior unchanged.

**Files:**
- Modify: `templates/devices.html`
- Modify: `static/js/device-manager.js`
- Modify: `tests/test_design_system.py`

**Interfaces:**
- Preserves form IDs: `pairForm`, `connForm`.
- Preserves DOM IDs: `savedDevicesContainer`, `savedDevicesList`, `wireOut`, `deviceFacts`.
- Preserves endpoints: `/api/saved-wifi-devices`, `/api/saved-wifi-devices/<id>`, `/api/adb/pair`, `/api/adb/connect`.
- Produces `.saved-device-row`, `.wire-feedback`, `.workflow-card`, and `.fact-grid` DOM structures.

- [ ] **Step 1: Write failing tests for the migrated device page contract**

Append to `tests/test_design_system.py`:

```python
def test_devices_page_uses_shared_console_styles_not_legacy_glass():
    text = (ROOT / "templates" / "devices.html").read_text(encoding="utf-8")
    assert '/static/css/control-console.css?v={{ static_ver }}' in text
    assert '/static/css/glass.css?v={{ static_ver }}' not in text
    assert 'background:rgba(255,255,255,.04)' not in text
    assert 'color:#e5e7eb' not in text


def test_devices_page_exposes_labeled_accessible_wifi_workflow():
    text = (ROOT / "templates" / "devices.html").read_text(encoding="utf-8")
    for marker in (
        'class="workflow-card"',
        'class="ui-label"',
        'class="ui-input"',
        'id="wireOut" role="status"',
        'aria-live="polite"',
        'class="fact-grid"',
    ):
        assert marker in text
```

- [ ] **Step 2: Run the device design tests to verify failure**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py::test_devices_page_uses_shared_console_styles_not_legacy_glass tests/test_design_system.py::test_devices_page_exposes_labeled_accessible_wifi_workflow -q
```

Expected: FAIL because `devices.html` still loads `glass.css` and contains inline dark styles.

- [ ] **Step 3: Rebuild the device page markup with semantic classes**

1. Replace the `glass.css` stylesheet link with `control-console.css` after `app-shell.css`.
2. Remove the page `<style>` rules that use `var(--line)`, `var(--muted)`, `rgba(...)`, `--easing`, and raw dark foreground values.
3. Wrap the page in `class="page-container"` and use `ui-card` for all major sections.
4. Replace current Pair and Connect columns with:

```html
<div class="workflow-grid" aria-label="Thiết lập kết nối Wi-Fi">
  <section class="ui-card workflow-card" aria-labelledby="pair-title">
    <p class="step-kicker">Bước 1</p>
    <h2 id="pair-title">Pair lần đầu</h2>
    <p class="helper-text">Nhập thông tin từ mục Pair device with pairing code trên Android.</p>
    <form id="pairForm" class="connection-form">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <label class="ui-label">Pair host (IP)<input class="ui-input" name="host" required placeholder="192.168.1.100"></label>
      <label class="ui-label">Pair port<input class="ui-input" name="port" type="number" min="1" max="65535" required placeholder="37123"></label>
      <label class="ui-label">Pair code (6 chữ số)<input class="ui-input" name="code" required pattern="\d{4,8}" inputmode="numeric" placeholder="123456"></label>
      <label class="check-label"><input type="checkbox" name="save_device"> Lưu thiết bị này</label>
      <label class="ui-label">Tên thiết bị <span class="optional">(tùy chọn)</span><input class="ui-input" name="device_name" placeholder="Điện thoại Samsung"></label>
      <button class="button-primary" type="submit"><i class="fa-solid fa-link" aria-hidden="true"></i> Pair thiết bị</button>
    </form>
  </section>
  <section class="ui-card workflow-card" aria-labelledby="connect-title">
    <p class="step-kicker">Bước 2</p>
    <h2 id="connect-title">Kết nối thiết bị đã pair</h2>
    <p class="helper-text">Dùng cổng debug, không dùng cổng Pair ở bước 1.</p>
    <form id="connForm" class="connection-form">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <input type="hidden" name="device_id" value="">
      <label class="ui-label">Connect host<input class="ui-input" name="host" required placeholder="192.168.1.100"></label>
      <label class="ui-label">Connect port<input class="ui-input" name="port" type="number" min="1" max="65535" required value="5555"></label>
      <label class="check-label"><input type="checkbox" name="save_device"> Lưu thiết bị này</label>
      <label class="ui-label">Tên thiết bị <span class="optional">(tùy chọn)</span><input class="ui-input" name="device_name" placeholder="Điện thoại Samsung"></label>
      <button class="button-primary" type="submit"><i class="fa-solid fa-plug" aria-hidden="true"></i> Kết nối</button>
    </form>
  </section>
</div>
<div id="wireOut" class="wire-feedback" role="status" aria-live="polite"></div>
```

5. Leave endpoint calls, form names, hidden CSRF inputs, and `wirePost()` endpoints unchanged.
6. Render device facts as a four-cell `.fact-grid`; empty state must include a direct link to `#wireless`.

- [ ] **Step 4: Make saved-device rendering semantic and deduplicate endpoints**

In the existing `loadSavedDevices()` function, replace `style.cssText` assignments with classes and de-duplicate `target` values before rendering:

```js
const uniqueDevices = Array.from(
  new Map(j.devices.map((device) => [device.target, device])).values(),
);

uniqueDevices.forEach((device) => {
  const row = document.createElement("article");
  row.className = "saved-device-row";
  // keep d.id, d.host, d.port and existing click endpoints unchanged
});
```

Set `deleteBtn.className = "button-danger icon-button"`, add `deleteBtn.setAttribute("aria-label", `Xóa ${device.target}`)`, and set `connectBtn.className = "button-secondary"`. Convert `wireOut` text updates to set `data-tone` (`success`, `danger`, `info`) as well as text, without changing payload handling.

- [ ] **Step 5: Run focused tests and browser-independent validation**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py tests/test_device_facts.py -q
"/c/Program Files/Python312/python.exe" -m ruff check static/js/device-manager.js tests/test_design_system.py
"/c/Program Files/Python312/python.exe" -m ruff format --check static/js/device-manager.js tests/test_design_system.py
git diff --check
```

Expected: all commands pass.

- [ ] **Step 6: Commit the device management slice**

```bash
git add templates/devices.html static/js/device-manager.js tests/test_design_system.py
git commit -m "feat: rebuild Wi-Fi device workflow for readable access"
```

---

### Task 3: Convert the Android control console without breaking controls

**Objective:** Apply the bright console shell and semantic status/control styling to `index.html`, preserving every ID and JavaScript listener.

**Files:**
- Modify: `templates/index.html`
- Modify: `static/css/android-console.css`
- Modify: `tests/test_design_system.py`
- Modify: `tests/test_template_bindings.py`

**Interfaces:**
- Preserves every existing `id=` attribute in `templates/index.html`, especially `sidebar`, `reconnect`, `quickCtl`, `playerCanvas`, `connectionStatus`, and all IDs listed by `SOCKET_INDEPENDENT_BUTTON_IDS`.
- Keeps `attachInput(width, height)` and all existing Socket.IO behavior unchanged.
- Produces `.console-shell`, `.console-sidebar`, `.console-main`, `.control-toolbar`, `.tool-button`, `.media-stage`, `.console-dialog`.

- [ ] **Step 1: Write failing regression tests that protect control bindings and the light shell**

Append to `tests/test_design_system.py`:

```python
def test_android_console_uses_shared_light_shell_but_keeps_media_stage_dark():
    text = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert '/static/css/control-console.css?v={{ static_ver }}' in text
    assert '/static/css/glass.css?v={{ static_ver }}' not in text
    assert 'class="console-shell"' in text
    assert 'class="media-stage"' in text
    assert 'background:#05070e' not in text


def test_android_console_icon_only_controls_have_accessible_names():
    text = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    for control_id in ("reconnect", "quickCtl", "fullscreen", "screenshot"):
        marker = f'id="{control_id}"'
        start = text.index(marker)
        opening_tag = text[text.rfind("<", 0, start) : text.find(">", start) + 1]
        assert "aria-label=" in opening_tag, control_id
```

- [ ] **Step 2: Run the new console tests to verify failure**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py::test_android_console_uses_shared_light_shell_but_keeps_media_stage_dark tests/test_design_system.py::test_android_console_icon_only_controls_have_accessible_names -q
```

Expected: FAIL because the template uses dark inline canvas/sidebar styles and lacks the shared console stylesheet.

- [ ] **Step 3: Replace visual shell and toolbar styles while preserving bindings**

1. Remove `glass.css` link and add `control-console.css` after `app-shell.css`.
2. Replace the inline body/sidebar dark backgrounds with classes:

```html
<body class="console-shell">
  <aside class="console-sidebar" id="sidebar">...</aside>
  <main class="console-main">...</main>
</body>
```

3. Add `class="media-stage"` only to the container around `video`/`canvas#playerCanvas`; retain its black stream background.
4. Convert toolbar controls to `.tool-button` with class variants; do not change their `id`, `onclick`, `data-*`, or child icon values.
5. For icon-only buttons, add explicit `aria-label` based on their existing functionality. Example:

```html
<button id="reconnect" class="tool-button" aria-label="Kết nối lại thiết bị" title="Kết nối lại">
  <i class="fa-solid fa-rotate" aria-hidden="true"></i>
</button>
```

6. Convert dialogs, quick controls, and command output containers to `.ui-card` / `.console-dialog` / semantic status classes. Retain all DOM IDs and visible function text.

- [ ] **Step 4: Implement console and control styles in `android-console.css`**

Replace dark glass rules with semantic rules. The media-specific rule is the only raw dark surface:

```css
.console-main { display: grid; grid-template-rows: auto minmax(0, 1fr); min-height: 100dvh; }
.control-toolbar { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 16px; background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.tool-button { min-width: 44px; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px; color: var(--color-text-secondary); background: var(--color-surface); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); cursor: pointer; }
.tool-button:hover, .tool-button[aria-pressed="true"] { color: var(--color-primary); background: var(--color-primary-subtle); border-color: var(--color-primary); }
.media-stage { display: grid; place-items: center; min-width: 0; min-height: 0; background: #0B1220; }
.console-dialog { background: var(--color-surface); color: var(--color-text); border: 1px solid var(--color-border); border-radius: var(--radius-lg); box-shadow: 0 24px 56px rgba(16, 42, 67, 0.22); }
```

- [ ] **Step 5: Run binding, layout, and syntax tests**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_template_bindings.py tests/test_design_system.py -q
"/c/Program Files/Python312/python.exe" -m ruff check tests/test_template_bindings.py tests/test_design_system.py
"/c/Program Files/Python312/python.exe" -m ruff format --check tests/test_template_bindings.py tests/test_design_system.py
git diff --check
```

Expected: all commands pass; existing socket-independent binding tests remain green.

- [ ] **Step 6: Commit the console styling slice**

```bash
git add templates/index.html static/css/android-console.css tests/test_design_system.py tests/test_template_bindings.py
git commit -m "feat: restyle Android control console with accessible shell"
```

---

### Task 4: Migrate Login, Password, and iOS pages

**Objective:** Make the remaining user-facing routes consistent with the shared white–blue system and explicit accessibility contracts.

**Files:**
- Modify: `templates/login.html`
- Modify: `templates/change_password.html`
- Modify: `templates/ios_index.html`
- Modify: `tests/test_design_system.py`

**Interfaces:**
- Preserves all form `action`, `method`, input `name`, CSRF fields, and submit behavior.
- Produces `.auth-page`, `.auth-card`, `.form-stack`, `.ios-availability-card` markup.

- [ ] **Step 1: Write failing route template tests**

Append to `tests/test_design_system.py`:

```python
def test_all_production_templates_stop_loading_legacy_glass_css():
    for filename in ("login.html", "change_password.html", "devices.html", "index.html", "ios_index.html"):
        text = (ROOT / "templates" / filename).read_text(encoding="utf-8")
        assert '/static/css/glass.css?v={{ static_ver }}' not in text, filename
        assert '/static/css/app-shell.css?v={{ static_ver }}' in text, filename


def test_auth_pages_use_persistent_labels_and_shared_form_primitives():
    for filename in ("login.html", "change_password.html"):
        text = (ROOT / "templates" / filename).read_text(encoding="utf-8")
        assert 'class="auth-card ui-card"' in text
        assert 'class="ui-label"' in text
        assert 'class="ui-input"' in text
        assert 'class="button-primary"' in text


def test_ios_page_describes_real_availability_without_fake_connected_state():
    text = (ROOT / "templates" / "ios_index.html").read_text(encoding="utf-8")
    assert 'class="ios-availability-card ui-card"' in text
    assert 'WDA/AirPlay' in text
    assert 'Đang kết nối' not in text
```

- [ ] **Step 2: Run the route template tests to verify failure**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py::test_all_production_templates_stop_loading_legacy_glass_css tests/test_design_system.py::test_auth_pages_use_persistent_labels_and_shared_form_primitives tests/test_design_system.py::test_ios_page_describes_real_availability_without_fake_connected_state -q
```

Expected: FAIL until every template stops loading the old stylesheet and adopts the new classes.

- [ ] **Step 3: Convert login and password markup**

For each auth page:

1. Remove the `glass.css` link and any page-level dark/glass style block.
2. Use a minimal layout:

```html
<body class="auth-page">
  <main class="auth-card ui-card" aria-labelledby="page-title">
    <p class="eyebrow">REMOTE ANDROID</p>
    <h1 id="page-title">...</h1>
    <p class="helper-text">...</p>
    <form class="form-stack" method="post">...</form>
  </main>
</body>
```

3. Give every `input` the `ui-input` class, retain each existing name/type/value/CSRF token, wrap it in a visible `ui-label`, and use `.button-primary` for the only submit CTA.
4. Add `aria-label` to password reveal controls, if any.

- [ ] **Step 4: Convert iOS page markup**

1. Remove `glass.css` and page-specific dark colors.
2. Use a `page-container` and `ios-availability-card ui-card`.
3. Preserve the truthful WDA/AirPlay unavailable/ready messaging. Include a checklist of requirements and a secondary navigation action, but do not claim a device is connected.

- [ ] **Step 5: Run route tests and full formatting checks**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py tests/test_template_bindings.py -q
"/c/Program Files/Python312/python.exe" -m ruff check tests/test_design_system.py tests/test_template_bindings.py
"/c/Program Files/Python312/python.exe" -m ruff format --check tests/test_design_system.py tests/test_template_bindings.py
git diff --check
```

Expected: all commands pass.

- [ ] **Step 6: Commit the remaining page migration**

```bash
git add templates/login.html templates/change_password.html templates/ios_index.html tests/test_design_system.py
git commit -m "feat: unify auth and iOS pages under accessible theme"
```

---

### Task 5: Isolated browser QA and production rollout

**Objective:** Verify visual, runtime, accessibility, and code quality before restarting production; then verify the scheduled production service.

**Files:**
- Create: `docs/superpowers/verification/2026-09-15-accessible-white-blue-console-qa.md`

**Interfaces:**
- QA listener: `DISABLE_ADB_KEEPALIVE=1 python app.py --port 8010`.
- Production task: `Hermes_scrcpy`.
- Production health endpoint: `http://127.0.0.1:8000/healthz`.

- [ ] **Step 1: Run full automated verification before browser QA**

Run:

```bash
"/c/Program Files/Python312/python.exe" -m pytest -q
"/c/Program Files/Python312/python.exe" -m ruff check .
"/c/Program Files/Python312/python.exe" -m ruff format --check .
git diff --check
```

Expected: pytest passes with no failures; Ruff checks pass; no whitespace errors.

- [ ] **Step 2: Start isolated QA listener without ADB keep-alive**

Run:

```bash
DISABLE_ADB_KEEPALIVE=1 "/c/Program Files/Python312/python.exe" app.py --port 8010
```

Verify listener and routes:

```bash
netstat -ano | grep ':8010 '
curl -sS -o NUL -w 'login=%{http_code}\n' http://127.0.0.1:8010/login
curl -sS -o NUL -w 'devices=%{http_code}\n' http://127.0.0.1:8010/devices
curl -sS -o NUL -w 'ios=%{http_code}\n' http://127.0.0.1:8010/ios
```

Expected: listener exists and all routes return 200 or a documented auth redirect.

- [ ] **Step 3: Browser visual and accessibility QA**

Use isolated browser tooling to inspect `/login`, `/devices`, `/`, and `/ios` at 375px, 768px, 1024px, and 1440px.

For each route/viewport verify:

1. No text blends into its background.
2. No horizontal overflow or clipped labels.
3. Body/label text, buttons, error panel, and device facts are readable.
4. Console contains no JavaScript errors.
5. Tab focus is visible on interactive controls.
6. Device Pair/Connect labels are visible without relying on placeholders.
7. Android media stage is dark, while surrounding controls are light.
8. Icon-only controls expose accessible labels.

Save screenshot paths and observed results in the QA report.

- [ ] **Step 4: Document QA evidence and commit it**

Create `docs/superpowers/verification/2026-09-15-accessible-white-blue-console-qa.md` containing:

- Commands and exact pass/fail outputs.
- Browser routes and viewport checks.
- Console error result.
- ADB keep-alive disabled confirmation.
- Known limitation: physical Android/iOS device behavior is not exercised by a visual-theme migration.
- Go/no-go verdict.

Then commit:

```bash
git add docs/superpowers/verification/2026-09-15-accessible-white-blue-console-qa.md
git commit -m "docs: record accessible console QA"
```

- [ ] **Step 5: Push branch, create PR, and wait for CI**

Run:

```bash
git push --set-upstream origin feature/accessibility-ui-redesign
gh pr create --repo nhoxboo/web-scrcpy-fresh-private --head feature/accessibility-ui-redesign --base main --title "feat: accessible white-blue control console" --body "Replaces mixed dark-glass/light-shell styling with semantic accessible white-blue UI. Preserves ADB/WebSocket behavior and adds regression tests."
gh run list --repo nhoxboo/web-scrcpy-fresh-private --branch feature/accessibility-ui-redesign --limit 5 --json status,conclusion,name,headBranch
```

Expected: PR exists; CI returns success for Python 3.10, 3.11, and 3.12 before merge.

- [ ] **Step 6: Merge only after CI success, then controlled production restart**

After the PR reports all checks successful and merge is completed, run:

```bash
schtasks.exe /End /TN Hermes_scrcpy
sleep 3
schtasks.exe /Run /TN Hermes_scrcpy
sleep 5
netstat -ano | grep ':8000 '
curl -sS -D - http://127.0.0.1:8000/healthz -o NUL
curl -sS -o NUL -w 'login=%{http_code}\n' http://127.0.0.1:8000/login
curl -sS -o NUL -w 'devices=%{http_code}\n' http://127.0.0.1:8000/devices
```

Expected: port 8000 listens; health returns HTTP 200; login/devices return expected status.

- [ ] **Step 7: Verify live production UI and record release result**

Open production `/login` and `/devices` with browser tooling. Check the same readable-label and no-overflow criteria from Step 3. Update the QA report with the production health result, commit the amendment if required, and push.

---

## Final Definition of Done

- [ ] No production template links `glass.css`.
- [ ] No migrated template uses old inline dark background/foreground declarations.
- [ ] Device Pair/Connect labels and error feedback are readable at all target widths.
- [ ] Existing ADB/WebSocket IDs and browser bindings remain intact.
- [ ] `pytest -q`, Ruff check, Ruff format check, and `git diff --check` pass.
- [ ] Isolated browser QA passes at 375px, 768px, 1024px, 1440px with a clean console.
- [ ] PR CI is green for all configured Python versions.
- [ ] Production health endpoint returns 200 after controlled task restart.
- [ ] `saved_wifi_devices.json` remains uncommitted and unmodified by the redesign.
