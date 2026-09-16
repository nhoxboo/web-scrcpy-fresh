# Task 5 favicon QA remediation report

## Original observation

Isolated-browser QA on port 8010 previously observed no JavaScript exceptions, but Chrome CDP `Log.enable` recorded `GET /favicon.ico` returning HTTP 404 while loading `/login`. The tracked replacement asset already existed at `static/dist/favicon.svg`; production Jinja templates did not link it.

## TDD evidence

### RED

Command:

```bash
"/c/Program Files/Python312/python.exe" -m pytest -q tests/test_design_system.py::test_all_production_templates_link_the_tracked_svg_favicon_through_flask_static
```

Result: expected failure (`1 failed in 0.12s`). The new regression test confirmed `static/dist/favicon.svg` exists and failed because `login.html` had zero favicon links.

### GREEN

Each production template received exactly one identical Flask static URL:

```jinja2
<link rel="icon" type="image/svg+xml" href="{{ url_for('static', filename='dist/favicon.svg') }}">
```

Command:

```bash
"/c/Program Files/Python312/python.exe" -m pytest -q tests/test_design_system.py::test_all_production_templates_link_the_tracked_svg_favicon_through_flask_static
```

Result: `1 passed in 0.03s`.

The regression test covers `login.html`, `change_password.html`, `devices.html`, `index.html`, and `ios_index.html`, requires exactly one canonical link in each, and asserts the SVG target is a file.

## Isolated listener check

A pre-existing listener was already bound to port 8010. An attempted local start with `DISABLE_ADB_KEEPALIVE=1` exited with `WinError 10048` and did not replace or alter that listener. Against the existing isolated listener:

```text
login=200
favicon=200
```

The browser opened `http://127.0.0.1:8010/login` successfully. This browser backend does not expose console/network capture, so the direct isolated static request is the runtime network evidence; the original CDP 404 observation is recorded above.

## Full verification

```text
"/c/Program Files/Python312/python.exe" -m pytest -q
223 passed, 1 warning in 26.16s

"/c/Program Files/Python312/python.exe" -m ruff check .
All checks passed!

"/c/Program Files/Python312/python.exe" -m ruff format --check .
42 files already formatted

git diff --check
exit 0
```

The sole pytest warning is the pre-existing `EventletDeprecationWarning` from `engineio.async_drivers.eventlet`.

## Scope and contract confirmation

- Changed only the regression test and the five named production templates.
- CSS load order is unchanged in every template.
- No backend, authentication, ADB, Socket.IO, route, binary asset, production-8000, or runtime-service change was made.
- `saved_wifi_devices.json` was already modified before this task and is intentionally excluded from the scoped commit.
