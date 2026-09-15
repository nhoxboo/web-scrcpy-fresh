import re
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
