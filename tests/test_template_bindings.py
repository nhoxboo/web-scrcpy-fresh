"""Regression tests for the inline JS structure in templates/index.html.

PR #20 introduced a regression where every toolbar button's onclick handler
lived inside a `function initInput(width, height) { ... }` body that only
ran once the server emitted `screen_size`. When the WebSocket was rejected
(single-client lock, scrcpy crash, no device, ...) the function never ran
and the entire toolbar — including the Reconnect button the user needed to
recover — became dead. These tests pin the structural fix so we don't slip
into the same trap again.

We deliberately do not parse the HTML with a full JS engine; we just slice
out the `<script>` block by tag boundaries and inspect ranges. Brittle, but
fast and dependency-free.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / "templates" / "index.html"

# Buttons whose handlers MUST work without an active scrcpy connection — i.e.
# they should be bound at top level, not inside a function that only runs on
# `screen_size`.
SOCKET_INDEPENDENT_BUTTON_IDS = (
    "vdesktopMode",  # localStorage flag + reload
    "uhidInput",  # localStorage flag + reload
    "quickCtl",  # opens overlay; POSTs go via /api/quick (ADB only)
    "reconnect",  # MUST work to retry a rejected/dead socket
    "installApk",  # POSTs /api/install (ADB only)
    "pushFile",  # POSTs /api/push (ADB only)
    "kbToggle",  # focuses textarea (no input dep)
    "hotkeyConfig",  # localStorage hotkey config
    "gameMode",  # localStorage toggle
    "fullscreen",  # browser fullscreen API
    "screenshot",  # canvas.drawImage + toBlob (client-side only)
    "recordToggle",  # MediaRecorder.start/stop (client-side only)
    "zoomOut",
    "zoomIn",
    "zoomReset",
    "macroRec",
    "macroStop",
    "macroPlay",
    "macroClear",
)


def _inline_script() -> str:
    text = INDEX_HTML.read_text(encoding="utf-8")
    # Pick the largest <script>...</script> block (the inline app code, not
    # the CDN-style src=... ones which have no body).
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", text, flags=re.DOTALL)
    blocks = [b for b in blocks if b.strip()]
    assert blocks, "no inline <script> body found in index.html"
    return max(blocks, key=len)


def _function_body(js: str, name: str) -> str:
    """Return the body of `function name(...) { ... }` (brace-balanced)."""
    m = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", js)
    assert m, f"function {name} not found in inline script"
    start = m.end()
    depth = 1
    i = start
    while i < len(js) and depth > 0:
        c = js[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    assert depth == 0, f"unbalanced braces in function {name}"
    return js[start : i - 1]


def test_attach_input_function_exists():
    js = _inline_script()
    # The renamed entry point. Old name was `initInput` and held everything;
    # the new one only creates `input` + flips display-mode-specific UI state.
    assert re.search(r"function\s+attachInput\s*\(", js), (
        "expected attachInput(width, height) function — see PR description for why"
    )


def test_screen_size_handler_calls_attach_input():
    js = _inline_script()
    assert "attachInput(deviceW, deviceH)" in js, (
        "screen_size handler must call attachInput so ScrcpyInput is created"
    )
    # Make sure the old name wasn't left behind by accident.
    assert "initInput(" not in js, "stale initInput(...) reference in screen_size handler"


def test_socket_independent_buttons_are_bound_outside_attach_input():
    js = _inline_script()
    body = _function_body(js, "attachInput")
    for btn_id in SOCKET_INDEPENDENT_BUTTON_IDS:
        # The binding patterns we use in the template.
        patterns = (
            f"document.getElementById('{btn_id}').onclick",
            f"getElementById('{btn_id}').addEventListener",
            f"id('{btn_id}').onclick",
        )
        for p in patterns:
            assert p not in body, (
                f"binding for #{btn_id} must NOT live inside attachInput — "
                "if scrcpy never connects, this button would be dead"
            )


def test_socket_independent_buttons_are_actually_bound_somewhere():
    """Sanity check: we didn't drop the bindings entirely."""
    js = _inline_script()
    for btn_id in SOCKET_INDEPENDENT_BUTTON_IDS:
        from pathlib import Path

        ui_js_path = Path(__file__).parent.parent / 'static' / 'js' / 'ui.js'
        ui_js = ui_js_path.read_text(encoding='utf-8') if ui_js_path.exists() else ''
        assert (
            re.search(rf"getElementById\('{re.escape(btn_id)}'\)", js)
            or re.search(rf"getElementById\('{re.escape(btn_id)}'\)", ui_js)
            or btn_id in js
            or btn_id in ui_js
        ), f"binding for #{btn_id} appears to have been removed"


def test_reconnect_handler_works_without_input():
    """The Reconnect button is the canonical recovery path. Its body must not
    dereference `input` (which might be null), only socket/jmuxer/video which
    are top-level globals."""
    js = _inline_script()
    # Find the reconnect onclick handler body.
    m = re.search(
        r"getElementById\('reconnect'\)\.onclick\s*=\s*\(\s*\)\s*=>\s*\{",
        js,
    )
    assert m, "reconnect onclick handler not found"
    start = m.end()
    depth = 1
    i = start
    while i < len(js) and depth > 0:
        c = js[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    body = js[start : i - 1]
    # The handler may reference `input` only to clean up state; it must not
    # blindly call methods on it without a null check.
    bare_input_call = re.search(r"\binput\.[a-zA-Z]", body)
    assert not bare_input_call, (
        "reconnect handler dereferences input.* without a null check — "
        "would throw if the WS never connected"
    )
