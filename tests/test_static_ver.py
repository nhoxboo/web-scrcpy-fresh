"""Tests for the static-asset cache-bust token (`?v={static_ver}`).

Without this, browsers serve cached JS forever — the audio fix in PR #34
sat in /static/js/audio_parser.js but the user kept seeing the old
"Audio codec aac\u0000 chưa hỗ trợ" warning because the page still
loaded the pre-deploy script. The fix is a stable hash-of-static-tree
token rendered into every <script>/<link> URL; same value across
identical deploys, fresh value the moment any file under static/ changes.
"""

from __future__ import annotations

import re
from pathlib import Path


def _index_html_text():
    p = Path(__file__).resolve().parent.parent / 'templates' / 'index.html'
    return p.read_text(encoding='utf-8')


def _login_html_text():
    p = Path(__file__).resolve().parent.parent / 'templates' / 'login.html'
    return p.read_text(encoding='utf-8')


def test_index_scripts_carry_static_ver_query():
    """Every <script src="/static/..."> in index.html must include
    `?v={{ static_ver }}` so a deploy invalidates the browser cache."""
    text = _index_html_text()
    # Look at <script src="/static/js/..."> tags only — external CDN-style
    # scripts (none today) would be exempt.
    matches = re.findall(r'<script\s+src="(/static/js/[^"]+)"', text)
    assert matches, 'no <script src="/static/js/..."> tags found in index.html'
    for src in matches:
        assert '?v={{ static_ver }}' in src, (
            f'missing cache-bust on {src!r}; without it browsers will serve '
            f'cached JS after every deploy'
        )


def test_index_stylesheets_carry_static_ver_query():
    text = _index_html_text()
    matches = re.findall(r'<link\s+href="(/static/css/[^"]+)"', text)
    assert matches, 'no <link href="/static/css/..."> tags found in index.html'
    for href in matches:
        assert '?v={{ static_ver }}' in href, f'missing cache-bust on {href!r}'


def test_login_stylesheets_carry_static_ver_query():
    text = _login_html_text()
    matches = re.findall(r'<link\s+href="(/static/css/[^"]+)"', text)
    assert matches, 'no <link href="/static/css/..."> tags found in login.html'
    for href in matches:
        assert '?v={{ static_ver }}' in href, f'missing cache-bust on {href!r}'


def test_static_ver_rendered_on_index(client, default_credentials, csrf):
    """End-to-end: served HTML must contain the actual computed static_ver
    token, not the unrendered Jinja placeholder."""
    resp = client.post(
        '/login',
        data={
            'username': default_credentials['username'],
            'password': default_credentials['password'],
            'csrf_token': csrf,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    body = resp.data.decode('utf-8')
    assert '{{ static_ver }}' not in body, 'static_ver template variable was not rendered'
    # Pick out one script src and verify it carries a non-empty hex token.
    m = re.search(r'/static/js/audio_parser\.js\?v=([0-9a-f]+)', body)
    assert m, f'audio_parser.js script tag missing or has no ?v= token; body excerpt: {body[:500]}'
    assert len(m.group(1)) >= 4


def test_static_ver_changes_when_static_file_changes(app, tmp_path, monkeypatch):
    """Recomputing the hash after a static file is mutated should yield a
    different token — otherwise deploy = no cache invalidation."""
    # Build a fake static/ tree under tmp_path and point the helper at it.
    fake_root = tmp_path / 'static'
    (fake_root / 'js').mkdir(parents=True)
    (fake_root / 'js' / 'a.js').write_bytes(b'console.log(1);')
    (fake_root / 'js' / 'b.js').write_bytes(b'console.log(2);')

    # Use the live helper but pointed at the synthetic tree by patching
    # __file__-derived path resolution.
    monkeypatch.setattr(app, '__file__', str(tmp_path / 'app.py'))
    v1 = app._compute_static_ver()
    assert v1 and v1 != '0'
    # Same content → same hash (deterministic).
    assert app._compute_static_ver() == v1
    # Mutate one file → hash must move.
    (fake_root / 'js' / 'a.js').write_bytes(b'console.log(99);')
    v2 = app._compute_static_ver()
    assert v2 != v1
