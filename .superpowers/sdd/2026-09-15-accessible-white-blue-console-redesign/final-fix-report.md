# Final accessibility fix report

## Scope

One focused TDD fix wave for the two Important findings in `final-review.md`:

- Restore the Android compact-control 44px target contract in the final CSS cascade.
- Add explicit Vietnamese accessible names for iOS icon-only controls and cover the full icon-only set statically.

No backend, JavaScript, route, form, WebSocket, favicon, service, port, or saved-device data was changed.

## RED

Command:

```text
"/c/Program Files/Python312/python.exe" -m pytest tests/test_design_system.py::test_android_console_final_compact_control_rules_keep_44px_targets tests/test_design_system.py::test_ios_console_icon_only_controls_have_accessible_names -q
```

Output:

```text
FF                                                                       [100%]
================================== FAILURES ===================================
_____ test_android_console_final_compact_control_rules_keep_44px_targets ______

    def test_android_console_final_compact_control_rules_keep_44px_targets():
        css = (ROOT / "static" / "css" / "android-console.css").read_text(encoding="utf-8")

        side_key = _last_css_rule(css, ".side-key")
>       assert "width: 44px" in side_key
E       AssertionError: assert 'width: 44px' in '\n  width: 18px;\n  min-width: 18px;\n  border-radius: var(--radius-sm);\n'

tests\test_design_system.py:257: AssertionError
__________ test_ios_console_icon_only_controls_have_accessible_names __________

    def test_ios_console_icon_only_controls_have_accessible_names():
        ...
>       assert not missing_labels, missing_labels
E       AssertionError: ['rotate', 'fullscreen', 'screenshot', 'recordToggle', 'reconnect', 'hudToggle', ...]

2 failed in 0.13s
```

The Android assertion intentionally reads the last matching CSS rule for each regression-prone selector, so an earlier 44px declaration cannot mask a later compact override. The iOS assertion enumerates parsed icon-only buttons plus the resize handle, requires all review-listed IDs, and fails every empty `aria-label`.

## GREEN

Minimal production changes:

- `.side-key`: `width` and `min-width` changed from `18px` to `44px`.
- `.resize-handle`: final `min-width` and `min-height` changed from `36px` to `44px`.
- `.wm-row/.sq-row` number inputs: final `min-height` changed from `40px` to `44px` while retaining `width: 88px`.
- `.wm-act`, `.wm-preset`, `.sq-preset`: final `min-width` and `min-height` set to `44px`.
- Added Vietnamese `aria-label` values to `rotate`, `fullscreen`, `screenshot`, `recordToggle`, `reconnect`, `hudToggle`, `zoomOut`, `zoomReset`, `zoomIn`, and `resizeHandle`.

Focused verification:

```text
..                                                                       [100%]
2 passed in 0.03s
All checks passed!
```

The initial focused formatting check reported one test-only layout change; it was formatted before the final suite run.

Final verification command:

```text
"/c/Program Files/Python312/python.exe" -m pytest -q && "/c/Program Files/Python312/python.exe" -m ruff check . && "/c/Program Files/Python312/python.exe" -m ruff format --check . && git diff --check
```

Output:

```text
225 passed, 1 warning in 25.68s
All checks passed!
42 files already formatted
```

The sole warning is the pre-existing Eventlet deprecation warning emitted by `engineio.async_drivers.eventlet`; it is not an accessibility failure. `git diff --check` exited 0.
