#!/usr/bin/env python3
"""
HTTPS wrapper for web-scrcpy app.py
Redirects HTTP requests to HTTPS and provides SSL support.
"""

import argparse
import os
import sys
from pathlib import Path

import eventlet

eventlet.monkey_patch()

# Add project dir to path
sys.path.insert(0, os.path.dirname(__file__))

# Import app from original app.py
from app import app, socketio  # noqa: E402


def setup_https_redirect():
    """Add HTTP to HTTPS redirect middleware"""

    @app.before_request
    def redirect_http_to_https():
        from flask import redirect, request

        # Don't redirect localhost or internal IPs
        if not request.is_secure:
            remote_addr = request.remote_addr
            if remote_addr not in ['127.0.0.1', 'localhost', '::1']:
                # Redirect HTTP to HTTPS
                url = request.url.replace('http://', 'https://', 1)
                # Replace port 8000 with 443 if present
                url = url.replace(':8000', '', 1)
                return redirect(url, code=301)

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web Scrcpy with HTTPS support')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=8000, help='Port to serve HTTPS directly')
    parser.add_argument(
        '--ssl-cert',
        type=str,
        default='C:/ProgramData/web-scrcpy/runtime-tls/web-scrcpy.crt',
        help='Path to SSL certificate',
    )
    parser.add_argument(
        '--ssl-key',
        type=str,
        default='C:/ProgramData/web-scrcpy/runtime-tls/web-scrcpy.key',
        help='Path to SSL key',
    )
    parser.add_argument('--video-bit-rate', type=int, default=8000000, help='Video bitrate')

    args = parser.parse_args()

    # Validate cert/key paths
    cert_path = Path(args.ssl_cert)
    key_path = Path(args.ssl_key)

    if not cert_path.exists():
        print(f'ERROR: SSL cert not found: {cert_path}', file=sys.stderr)
        sys.exit(1)
    if not key_path.exists():
        print(f'ERROR: SSL key not found: {key_path}', file=sys.stderr)
        sys.exit(1)

    print(f'Starting Web Scrcpy HTTPS directly on {args.host}:{args.port} (cert: {cert_path})')

    # Start with SSL directly on the configured port
    socketio.run(
        app,
        host=args.host,
        port=args.port,
        certfile=str(cert_path),
        keyfile=str(key_path),
        debug=False,
    )
