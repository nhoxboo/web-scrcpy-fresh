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
