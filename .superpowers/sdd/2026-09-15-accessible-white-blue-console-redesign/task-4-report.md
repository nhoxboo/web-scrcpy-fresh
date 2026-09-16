# Task 4 — Auth and truthful iOS page migration evidence

## Scope

Modified only the Task 4 templates and test file, plus this required evidence report:

- `templates/login.html`
- `templates/change_password.html`
- `templates/ios_index.html`
- `tests/test_design_system.py`

` saved_wifi_devices.json` was already modified before this task and was not changed or staged.

## Strict TDD evidence

### RED

Added the three specified route-template contract tests before changing production templates, then ran:

```bash
"/c/Program Files/Python312/python.exe" -m pytest \
  tests/test_design_system.py::test_all_production_templates_stop_loading_legacy_glass_css \
  tests/test_design_system.py::test_auth_pages_use_persistent_labels_and_shared_form_primitives \
  tests/test_design_system.py::test_ios_page_describes_real_availability_without_fake_connected_state -q
```

Result: `3 failed`.

Expected failures established that the affected templates still loaded `glass.css`, auth pages lacked the shared semantic classes, and iOS lacked the truthful availability-card contract.

### GREEN

After the smallest scoped template migration, the same targeted tests returned `3 passed in 0.03s`.

Final verification returned:

```text
25 passed in 0.11s
All checks passed!
2 files already formatted
git diff --check: exit 0
```

Commands:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py tests/test_template_bindings.py -q
"/c/Program Files/Python312/python.exe" -m ruff check tests/test_design_system.py tests/test_template_bindings.py
"/c/Program Files/Python312/python.exe" -m ruff format --check tests/test_design_system.py tests/test_template_bindings.py
git diff --check
```

## Functionality preservation

- Login retains `method="post"`, CSRF field, `username` and `password` input names, `autocomplete`, required attributes, autofocus, submit behavior, and flashed messages.
- Change-password retains `method="post"`, CSRF field, `new_username`, `current_password`, `new_password`, and `confirm_password` names, Jinja username value, autocomplete settings, required attributes, submit behavior, return link, and flashed messages.
- iOS retains the existing scripts, CSRF meta token, logout form (`POST /logout`), remote-control DOM IDs, stream endpoint, and client-side control hooks. The legacy glass stylesheet and dark page-specific stylesheet were removed; the shared `control-console.css` and `app-shell.css` are loaded instead.

## Accessibility and visual contracts

- Auth pages now use `auth-page`, `auth-card ui-card`, `form-stack`, visible `ui-label` labels, `ui-input` inputs, and `button-primary` submit controls.
- Shared app-shell primitives provide the 44px minimum interactive control size, focus-visible treatment, white/blue semantic tokens, and contrast-tested text tokens.
- iOS now uses `page-container` and `ios-availability-card ui-card`; legacy glass CSS and raw template hex colors were removed.
- The exact truthful iOS wording is: **“WDA/AirPlay sẽ hiển thị trạng thái khi thiết bị sẵn sàng.”**
- No `Đang kết nối` text remains in the iOS template, so the page does not present a fabricated connected state.

## Concerns

- Task 5 runtime QA/production rollout was intentionally not performed.
- This task did not start, restart, or otherwise touch production port 8000.

## Reviewer-blocker remediation (Task 4 fix round 1)

### Strict TDD evidence

Added the strengthened contract tests before production changes and ran:

```bash
"/c/Program Files/Python312/python.exe" -m pytest \
  tests/test_design_system.py::test_task4_templates_load_scoped_styles_without_inline_or_raw_colors \
  tests/test_design_system.py::test_ios_console_css_implements_scoped_auth_availability_and_control_contracts -q
```

Result: `2 failed in 0.15s` as expected: the new stylesheet link was absent and
`static/css/ios-console.css` did not exist. After implementation, the focused
contract checks returned `4 passed in 0.08s`.

### Remediation delivered

- Added `static/css/ios-console.css`, externally loaded by both auth templates and the iOS console. It supplies scoped white-blue semantic styles for `auth-page`, `auth-card`, `form-stack`, `ios-availability-card`, and the retained iOS console layout/controls (toolbar, stage, phone mockup, side/nav keys, quick controls, status, zoom, resize).
- Scoped operational iOS controls—including `.tool`, `.btn`, `.zoom-btn`, `.nav-key`, `.side-key`, `.qc-btn`, `.wm-act`, presets, panel actions, and resize control—to at least `44px` targets with visible `:focus-visible` outlines.
- Removed all eight static `style=` attributes from `ios_index.html`; replacement named classes preserve logout layout, selector layout, stream/canvas behavior, off-screen keyboard capture, and keyboard-help text styling.
- Strengthened `tests/test_design_system.py` with parsed exact auth field/form contracts; an exact iOS baseline ID set; script URLs; CSRF/logout/stream contracts; neutral availability wording and fake-state exclusions; no-inline/no-hex checks; stylesheet loading; and selector/44px/focus checks.

### Final verification

```text
Focused contracts: 4 passed in 0.08s
Full suite: 221 passed, 1 pre-existing EventletDeprecationWarning in 25.31s
Ruff: All checks passed; 2 files already formatted
Template scan: login.html/change_password.html/ios_index.html each report 0 style attributes and 0 raw hex literals
git diff --check: exit 0
```

Commands:

```bash
"/c/Program Files/Python312/python.exe" -m pytest -q
"/c/Program Files/Python312/python.exe" -m ruff check tests/test_design_system.py tests/test_template_bindings.py
"/c/Program Files/Python312/python.exe" -m ruff format --check tests/test_design_system.py tests/test_template_bindings.py
git diff --check
```

## Reviewer-blocker remediation (Task 4 fix round 2 — audioGate)

### Strict TDD evidence

**RED:** Added `test_ios_audio_gate_preserves_keyboard_control_and_accessibility_contract` before altering CSS, then ran:

```bash
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py::test_ios_audio_gate_preserves_keyboard_control_and_accessibility_contract -q
```

Result: `1 failed in 0.12s`, specifically because `.ios-console .audio-gate` lacked `min-width: 44px`.

**GREEN:** Added only the `audio-gate` 44px target contract and its token-based `:focus-visible` outline. The same focused regression test returned `1 passed in 0.03s`.

### Final focused and full verification

```text
Focused audioGate and iOS CSS contracts: 2 passed in 0.07s
Full suite: 222 passed, 1 pre-existing EventletDeprecationWarning in 26.02s
Ruff: All checks passed; 1 file already formatted
git diff --check: exit 0
```

Commands:

```bash
"/c/Program Files/Python312/python.exe" -m pytest \
  tests/test_design_system.py::test_ios_audio_gate_preserves_keyboard_control_and_accessibility_contract \
  tests/test_design_system.py::test_ios_console_css_implements_scoped_auth_availability_and_control_contracts -q
"/c/Program Files/Python312/python.exe" -m pytest -q
"/c/Program Files/Python312/python.exe" -m ruff check tests/test_design_system.py
"/c/Program Files/Python312/python.exe" -m ruff format --check tests/test_design_system.py
git diff --check
```

### Scope preservation

- `#audioGate` remains the existing `<div role="button" tabindex="0">`; its ID, text, scripts, stream/audio behavior, and handling were unchanged.
- `ios-console.css` now gives the surfaced role-button an explicit 44px minimum width and height plus a visible focus ring using `--color-focus`.
- No template, JavaScript, backend, runtime, `saved_wifi_devices.json`, or port-8000 changes were made.
