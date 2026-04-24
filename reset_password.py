#!/usr/bin/env python3
"""Reset the local admin credentials for web-scrcpy.

Run this on the server (same directory as ``app.py``) when you have forgotten
the password or want to rotate credentials without going through the web UI::

    python reset_password.py                    # interactive prompts
    python reset_password.py --username admin   # override username
    python reset_password.py --non-interactive --username admin --password 'S3cret!'

The new password is hashed with ``werkzeug.security.generate_password_hash``
before being written to ``auth.json``. The existing in-memory Flask process
is **not** restarted automatically; stop/restart it yourself if needed.
"""

from __future__ import annotations

import argparse
import getpass
import sys

# Import constants + helpers from app without starting the Flask server.
from app import MIN_PASSWORD_LEN, _save_auth  # noqa: E402


def _prompt_password() -> str:
    while True:
        pw = getpass.getpass('New password: ')
        if len(pw) < MIN_PASSWORD_LEN:
            print(f'Password must be at least {MIN_PASSWORD_LEN} characters.', file=sys.stderr)
            continue
        confirm = getpass.getpass('Confirm new password: ')
        if pw != confirm:
            print('Passwords do not match, try again.', file=sys.stderr)
            continue
        return pw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Reset web-scrcpy admin credentials.')
    parser.add_argument('--username', default='admin', help='Username to set (default: admin)')
    parser.add_argument(
        '--password',
        default=None,
        help='Password to set (only use with --non-interactive; avoid on shared shells).',
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Do not prompt; requires --password.',
    )
    args = parser.parse_args(argv)

    if args.non_interactive:
        if not args.password:
            parser.error('--non-interactive requires --password')
        if len(args.password) < MIN_PASSWORD_LEN:
            parser.error(f'password must be at least {MIN_PASSWORD_LEN} characters')
        password = args.password
    else:
        password = args.password or _prompt_password()
        if len(password) < MIN_PASSWORD_LEN:
            print(
                f'Password must be at least {MIN_PASSWORD_LEN} characters.',
                file=sys.stderr,
            )
            return 2

    _save_auth(args.username, password)
    print(f'Updated credentials for {args.username!r}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
