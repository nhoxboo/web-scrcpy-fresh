"""Smoke tests for the reset_password CLI helper."""

from __future__ import annotations

import json
import sys


def test_reset_password_cli_updates_auth_json(app, tmp_path, monkeypatch, capsys):
    # Ensure reset_password is freshly imported against the isolated app fixture.
    sys.modules.pop('reset_password', None)
    import reset_password  # noqa: WPS433 - intentional late import

    monkeypatch.setattr(reset_password, '_save_auth', app._save_auth)

    rc = reset_password.main(
        [
            '--non-interactive',
            '--username',
            'someone',
            '--password',
            'brand-new-password',
        ]
    )
    assert rc == 0

    with open(app.AUTH_FILE, encoding='utf-8') as fh:
        data = json.load(fh)
    assert data['username'] == 'someone'
    assert ':' in data['password']  # werkzeug hashed

    out = capsys.readouterr().out
    assert 'someone' in out


def test_reset_password_cli_rejects_short_password(app, tmp_path):
    sys.modules.pop('reset_password', None)
    import reset_password  # noqa: WPS433

    try:
        reset_password.main(['--non-interactive', '--username', 'admin', '--password', 'short'])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError('expected SystemExit for short password')
