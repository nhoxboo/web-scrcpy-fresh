import argparse
import sys
import os

# Add original app code to path
sys.path.insert(0, os.path.dirname(__file__))

# Import original app
from app import app as flask_app, socketio as original_socketio

import ssl
from flask import redirect, request

# Wrap with HTTPS support
def create_https_app():
    @flask_app.before_request
    def redirect_http_to_https():
        """Redirect HTTP requests to HTTPS"""
        if not request.is_secure and request.host.split(':')[0] != '127.0.0.1':
            # Don't redirect localhost requests
            url = request.url.replace('http://', 'https://', 1)
            url = url.replace(':8000', ':443', 1)
            return redirect(url, code=301)
    
    return flask_app

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web Scrcpy with HTTPS')
    parser.add_argument('--port', type=int, default=8000, help='HTTP port (for internal use)')
    parser.add_argument('--https_port', type=int, default=443, help='HTTPS port')
    parser.add_argument('--ssl_cert', type=str, required=True, help='Path to SSL cert')
    parser.add_argument('--ssl_key', type=str, required=True, help='Path to SSL key')
    parser.add_argument('--video_bit_rate', type=int, default=2000000, help='Video bitrate')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind')
    
    args = parser.parse_args()
    
    app = create_https_app()
    
    # Setup SSL context
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(args.ssl_cert, args.ssl_key)
    
    print(f"Starting Web Scrcpy HTTPS on {args.host}:{args.https_port} (cert: {args.ssl_cert})")
    print(f"HTTP redirect on {args.host}:{args.port} -> HTTPS:{args.https_port}")
    
    # Start socketio with SSL
    original_socketio.run(
        app,
        host=args.host,
        port=args.https_port,
        ssl_context=ssl_context,
        debug=False,
        allow_unsafe_werkzeug=True
    )
