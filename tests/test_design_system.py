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
