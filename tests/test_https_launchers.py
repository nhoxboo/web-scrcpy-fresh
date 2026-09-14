"""Regression tests for the Eventlet-compatible HTTPS launchers."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_https_launchers_pass_certificate_paths_to_eventlet():
    for filename in ('run_https.py', 'app_https.py'):
        text = (ROOT / filename).read_text(encoding='utf-8')
        assert 'certfile=' in text
        assert 'keyfile=' in text
        assert 'ssl_context=' not in text
