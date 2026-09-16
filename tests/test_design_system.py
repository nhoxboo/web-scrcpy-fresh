import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _token_hex(css: str, token: str) -> str:
    match = re.search(rf"{re.escape(token)}:\s*(#[0-9A-Fa-f]{{6}})", css)
    assert match, f"{token} must define a six-digit hex color"
    return match.group(1)


def _relative_luminance(hex_color: str) -> float:
    channels = tuple(int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5))
    linear_channels = tuple(
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    )
    return sum(
        weight * channel for weight, channel in zip((0.2126, 0.7152, 0.0722), linear_channels)
    )


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


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


def test_placeholder_text_meets_wcag_aa_contrast_on_surface():
    css = (ROOT / "static/css/app-shell.css").read_text(encoding="utf-8")

    assert (
        _contrast_ratio(
            _token_hex(css, "--color-text-placeholder"),
            _token_hex(css, "--color-surface"),
        )
        >= 4.5
    )


def test_control_console_exposes_layout_contract_with_only_media_stage_raw_color():
    css = (ROOT / "static/css/control-console.css").read_text(encoding="utf-8")

    for selector in (
        ".console-shell",
        ".console-sidebar",
        ".console-main",
        ".page-container",
        ".workflow-grid",
        ".media-stage",
    ):
        assert selector in css

    assert re.findall(r"#[0-9A-Fa-f]{3,8}\b", css) == ["#0B1220"]


def test_devices_page_uses_shared_console_styles_not_legacy_glass():
    text = (ROOT / "templates" / "devices.html").read_text(encoding="utf-8")
    assert '/static/css/control-console.css?v={{ static_ver }}' in text
    assert '/static/css/glass.css?v={{ static_ver }}' not in text
    assert 'background:rgba(255,255,255,.04)' not in text
    assert 'color:#e5e7eb' not in text


def test_devices_page_preserves_accessible_wifi_workflow_contract():
    text = (ROOT / "templates" / "devices.html").read_text(encoding="utf-8")

    for marker in (
        'class="ui-card workflow-card"',
        'class="ui-label"',
        'class="ui-input"',
        'id="wireOut" role="status"',
        'aria-live="polite"',
        'class="fact-grid"',
        'id="pairForm"',
        'id="connForm"',
        'id="savedDevicesContainer"',
        'id="savedDevicesList"',
        'id="deviceFacts"',
        'name="csrf_token" value="{{ csrf_token() }}"',
        'name="device_id" value=""',
        'name="host"',
        'name="port"',
        'name="code"',
        'name="save_device"',
        'name="device_name"',
        "new FormData(form)",
        "fd.set('csrf_token', _csrf)",
        "'/api/adb/pair'",
        "'/api/adb/connect'",
        "'/api/saved-wifi-devices'",
        "`/api/saved-wifi-devices/${deviceId}`",
    ):
        assert marker in text

    assert "style=" not in text
    assert not re.search(r"#[0-9A-Fa-f]{3,8}\\b", text)


def test_device_workflow_classes_have_semantic_shared_styles():
    css = (ROOT / "static/css/control-console.css").read_text(encoding="utf-8")

    for selector in (
        ".page-header",
        ".page-header-row",
        ".page-actions",
        ".device-list",
        ".device-row",
        ".device-row.is-selected",
        ".saved-device-row",
        ".workflow-card",
        ".connection-form",
        ".empty-state",
        ".fact-grid",
        ".wire-feedback",
        '.wire-feedback[data-tone="info"]',
        '.wire-feedback[data-tone="success"]',
        '.wire-feedback[data-tone="danger"]',
    ):
        assert selector in css

    assert not re.search(r"#[0-9A-Fa-f]{3,8}\\b", css.replace("#0B1220", ""))


def test_saved_device_deduplication_retains_newest_api_record():
    text = (ROOT / "templates" / "devices.html").read_text(encoding="utf-8")

    assert "const seenTargets = new Set();" in text
    assert "const uniqueDevices = j.devices.filter((device) => {" in text
    assert "if (seenTargets.has(device.target)) return false;" in text
    assert "seenTargets.add(device.target);" in text
    assert "new Map(j.devices.map" not in text
    assert "connectSaved(d.id, d.host, d.port)" in text
    assert "deleteSaved(d.id)" in text


def test_wire_feedback_exposes_all_visible_tones():
    text = (ROOT / "templates" / "devices.html").read_text(encoding="utf-8")

    assert "wireOut.dataset.tone = tone;" in text
    for tone in ("'info'", "'success'", "'danger'"):
        assert tone in text


def test_device_facts_render_as_semantic_four_cell_grid():
    text = (ROOT / "static/js/device-manager.js").read_text(encoding="utf-8")
    assert "grid.className = 'fact-grid'" in text
    assert "fact.className = 'data-fact'" in text


def test_android_console_uses_shared_light_shell_but_keeps_media_stage_dark():
    text = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    assert '/static/css/control-console.css?v={{ static_ver }}' in text
    assert '/static/css/glass.css?v={{ static_ver }}' not in text
    assert 'class="console-shell"' in text
    assert 'class="media-stage"' in text
    assert 'background:#05070e' not in text


class _IconOnlyButtonParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._button: dict[str, str] | None = None
        self._text: list[str] = []
        self.buttons: list[dict[str, str]] = []
        self.icon_only_buttons: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "button":
            self._button = {name: value or "" for name, value in attrs}
            self.buttons.append(self._button)
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._button is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._button is not None:
            if not "".join(self._text).strip():
                self.icon_only_buttons.append(self._button)
            self._button = None
            self._text = []


def test_android_console_icon_only_controls_have_accessible_names():
    parser = _IconOnlyButtonParser()
    parser.feed((ROOT / "templates" / "index.html").read_text(encoding="utf-8"))

    icon_only_buttons = [
        *parser.icon_only_buttons,
        *(
            button
            for button in parser.buttons
            if "resize-handle" in button.get("class", "").split()
        ),
    ]
    icon_only_ids = {button.get("id", "") for button in icon_only_buttons}
    assert {"resizeHandle", "zoomOut", "zoomReset", "zoomIn"} <= icon_only_ids
    missing_labels = [
        button.get("id", "unnamed icon-only button")
        for button in icon_only_buttons
        if not button.get("aria-label", "").strip()
    ]
    assert not missing_labels, missing_labels


def test_android_console_mobile_sidebar_overrides_shared_hide_rule():
    css = (ROOT / "static" / "css" / "android-console.css").read_text(encoding="utf-8")

    tablet_rule = re.search(
        r"@media \(min-width: 769px\) and \(max-width: 1023px\)\s*\{.*?"
        r"\.console-sidebar\s*\{[^}]*display:\s*block",
        css,
        flags=re.DOTALL,
    )
    mobile_rule = re.search(
        r"@media \(max-width: 768px\)\s*\{.*?"
        r"\.console-sidebar\s*\{[^}]*display:\s*block",
        css,
        flags=re.DOTALL,
    )

    assert tablet_rule, "tablet sidebar must remain rendered while the shared rule hides it"
    assert mobile_rule, "mobile drawer sidebar must override the shared display:none rule"


def test_android_console_main_contains_drop_zone_overlay():
    css = (ROOT / "static" / "css" / "android-console.css").read_text(encoding="utf-8")
    console_main_rule = re.search(r"\.console-main\s*\{([^}]*)\}", css, flags=re.DOTALL)

    assert console_main_rule
    assert re.search(r"\bposition:\s*relative", console_main_rule.group(1))


def test_all_production_templates_link_the_tracked_svg_favicon_through_flask_static():
    favicon = ROOT / "static" / "dist" / "favicon.svg"
    assert favicon.is_file()

    favicon_link = (
        '<link rel="icon" type="image/svg+xml" '
        'href="{{ url_for(\'static\', filename=\'dist/favicon.svg\') }}">'
    )
    for filename in (
        "login.html",
        "change_password.html",
        "devices.html",
        "index.html",
        "ios_index.html",
    ):
        text = (ROOT / "templates" / filename).read_text(encoding="utf-8")
        assert text.count(favicon_link) == 1, filename


def test_all_production_templates_stop_loading_legacy_glass_css():
    for filename in (
        "login.html",
        "change_password.html",
        "devices.html",
        "index.html",
        "ios_index.html",
    ):
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


class _TemplateContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, {name: value or "" for name, value in attrs}))

    def matching(self, tag: str, **expected: str) -> list[dict[str, str]]:
        return [
            attrs
            for element, attrs in self.elements
            if element == tag and all(attrs.get(name) == value for name, value in expected.items())
        ]


def _parse_template(filename: str) -> tuple[str, _TemplateContractParser]:
    text = (ROOT / "templates" / filename).read_text(encoding="utf-8")
    parser = _TemplateContractParser()
    parser.feed(text)
    return text, parser


def test_auth_templates_preserve_exact_form_and_field_contracts():
    login_text, login = _parse_template("login.html")
    login_form = login.matching("form", method="post")
    assert len(login_form) == 1
    assert "action" not in login_form[0]
    assert login.matching("input", name="csrf_token", type="hidden")
    assert login.matching(
        "input",
        id="username",
        name="username",
        autocomplete="username",
        required="",
        autofocus="",
    )
    assert login.matching(
        "input",
        id="password",
        type="password",
        name="password",
        autocomplete="current-password",
        required="",
    )
    assert "get_flashed_messages()" in login_text

    password_text, password = _parse_template("change_password.html")
    password_form = password.matching("form", method="post")
    assert len(password_form) == 1
    assert "action" not in password_form[0]
    assert password.matching("input", name="csrf_token", type="hidden")
    assert password.matching(
        "input",
        id="new-username",
        name="new_username",
        autocomplete="username",
        required="",
    )
    for field_id, field_name, autocomplete in (
        ("current-password", "current_password", "current-password"),
        ("new-password", "new_password", "new-password"),
        ("confirm-password", "confirm_password", "new-password"),
    ):
        assert password.matching(
            "input",
            id=field_id,
            type="password",
            name=field_name,
            autocomplete=autocomplete,
            required="",
        )
    assert password.matching("a", href="/")
    assert "get_flashed_messages()" in password_text


def test_task4_templates_load_scoped_styles_without_inline_or_raw_colors():
    for filename in ("login.html", "change_password.html", "ios_index.html"):
        text = (ROOT / "templates" / filename).read_text(encoding="utf-8")
        assert '/static/css/glass.css?v={{ static_ver }}' not in text, filename
        assert '/static/css/app-shell.css?v={{ static_ver }}' in text, filename
        assert '/static/css/ios-console.css?v={{ static_ver }}' in text, filename
        assert "style=" not in text, filename
        assert not re.search(r"#[0-9A-Fa-f]{3,8}\\b", text), filename


def test_ios_template_preserves_control_hooks_and_truthful_availability_contract():
    text, parser = _parse_template("ios_index.html")
    expected_ids = {
        "iosAvailability",
        "rotate",
        "fullscreen",
        "screenshot",
        "recordToggle",
        "displaySelect",
        "transportSelect",
        "decoderSelect",
        "reconnect",
        "hudToggle",
        "videoWrap",
        "phoneMockup",
        "phoneShell",
        "player",
        "playerCanvas",
        "resizeHandle",
        "phoneSideKeys",
        "phoneNavBar",
        "kbCapture",
        "zoomOut",
        "zoomReset",
        "zoomIn",
        "status",
        "forceKick",
        "streamHud",
        "hudFps",
        "hudKbps",
        "hudPing",
        "hudFrames",
        "audioPlayer",
        "audioGate",
        "audioDiag",
        "adEnabled",
        "adStage",
        "adCodec",
        "adAsc",
        "adFrames",
        "adMux",
        "adMs",
        "adAudio",
        "adPlay",
        "adPrimed",
        "adErr",
        "adForcePlay",
        "adReset",
        "qcBackdrop",
        "qcTitle",
        "qcClose",
        "wmW",
        "wmH",
        "wmD",
        "wmApplySize",
        "wmApplyDpi",
        "wmGet",
        "wmResetSize",
        "wmResetDpi",
        "wmResetAll",
        "wmPresets",
        "wmInfo",
        "sqBitrate",
        "sqBitrateNum",
        "sqFps",
        "sqFpsNum",
        "sqApply",
        "sqReset",
        "sqPresets",
        "adbExecCmd",
        "adbExecRun",
        "adbExecClear",
        "adbExecHint",
        "adbExecOut",
        "qcOut",
    }
    actual_ids = {attrs["id"] for _, attrs in parser.elements if "id" in attrs}
    assert actual_ids == expected_ids
    assert parser.matching("meta", name="csrf-token", content="{{ csrf_token() }}")
    assert parser.matching("form", method="post", action="/logout")
    assert '/api/stream/ios_mjpeg' in text
    assert "WDA/AirPlay sẽ hiển thị trạng thái khi thiết bị sẵn sàng." in text
    assert "Đang kết nối" not in text
    for fake_state in ("Đã kết nối", "Connected", "Online"):
        assert fake_state not in text
    assert {
        attrs["src"] for tag, attrs in parser.elements if tag == "script" and "src" in attrs
    } == {
        "/static/js/socket.io.js?v={{ static_ver }}",
        "/static/js/input.js?v={{ static_ver }}",
        "/static/js/exp-golomb.js?v={{ static_ver }}",
        "/static/js/h264-sps-parser.js?v={{ static_ver }}",
        "/static/js/video_parser.js?v={{ static_ver }}",
        "/static/js/audio_parser.js?v={{ static_ver }}",
        "/static/js/jmuxer.min.js?v={{ static_ver }}",
    }


def test_ios_audio_gate_preserves_keyboard_control_and_accessibility_contract():
    _, parser = _parse_template("ios_index.html")
    assert parser.matching("div", id="audioGate", role="button", tabindex="0")

    css = (ROOT / "static/css/ios-console.css").read_text(encoding="utf-8")
    target_rule = re.search(
        r"\.ios-console \.audio-gate\s*\{(?P<rules>[^}]*)\}", css, flags=re.DOTALL
    )
    assert target_rule
    assert "min-width: 44px" in target_rule.group("rules")
    assert "min-height: 44px" in target_rule.group("rules")

    focus_rule = re.search(
        r"\.ios-console \.audio-gate:focus-visible\s*\{(?P<rules>[^}]*)\}",
        css,
        flags=re.DOTALL,
    )
    assert focus_rule
    assert (
        "outline: 3px solid color-mix(in srgb, var(--color-focus) 40%, transparent)"
        in focus_rule.group("rules")
    )


def test_ios_console_css_implements_scoped_auth_availability_and_control_contracts():
    css = (ROOT / "static/css/ios-console.css").read_text(encoding="utf-8")
    for selector in (
        ".auth-page",
        ".auth-card",
        ".form-stack",
        ".ios-availability-card",
        ".top",
        ".toolbar",
        ".tool",
        ".video-wrap",
        ".phone-shell",
        ".btn",
        ".status",
        ".zoom-btn",
        ".tool-select-wrap",
        ".phone-mockup",
        ".resize-handle",
        ".phone-side-keys",
        ".phone-nav-bar",
        ".qc-panel",
    ):
        assert re.search(rf"{re.escape(selector)}(?:[\s,:.#>+~]|\{{)", css), selector
    control_rule = re.search(
        r"(?P<selectors>\.ios-console \.tool,.*?\.ios-console \.ad-actions button)\s*"
        r"\{(?P<rules>[^}]*)\}",
        css,
        flags=re.DOTALL,
    )
    assert control_rule
    for selector in (".zoom-btn", ".nav-key", ".side-key", ".qc-btn", ".wm-act"):
        assert f".ios-console {selector}" in control_rule.group("selectors")
    assert "min-width: 44px" in control_rule.group("rules")
    assert "min-height: 44px" in control_rule.group("rules")
    focus_rule = re.search(
        r"(?P<selectors>\.ios-console \.tool:focus-visible,.*?"
        r"\.ios-console \.ad-actions button:focus-visible)\s*\{(?P<rules>[^}]*)\}",
        css,
        flags=re.DOTALL,
    )
    assert focus_rule
    assert ".ios-console .wm-act:focus-visible" in focus_rule.group("selectors")
    assert "outline:" in focus_rule.group("rules")
    assert ".ios-console" in css
