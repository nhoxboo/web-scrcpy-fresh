"""Tests for WebRTC signaling and management."""

from __future__ import annotations

import re
from unittest.mock import MagicMock


def _login(client, csrf, default_credentials):
    resp = client.post(
        '/login',
        data={
            'username': default_credentials['username'],
            'password': default_credentials['password'],
            'csrf_token': csrf,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302


def _post_csrf(client) -> str:
    """Get the fresh CSRF token from the index page after logging in."""
    resp = client.get('/')
    m = re.search(rb'name="csrf-token" content="([^"]+)"', resp.data)
    assert m, 'meta csrf-token not found'
    return m.group(1).decode('utf-8')


def test_webrtc_offer_requires_login(client, csrf):
    # If we have a CSRF token but are not logged in, we should be redirected to login (302)
    r = client.post(
        '/api/webrtc/offer', json={'sdp': 'foo', 'type': 'offer'}, headers={'X-CSRF-Token': csrf}
    )
    assert r.status_code == 302  # redirects to login


def test_webrtc_offer_rejects_missing_csrf(client):
    # Without CSRF token, it should reject with 400 Bad Request
    r = client.post('/api/webrtc/offer', json={'sdp': 'foo', 'type': 'offer'})
    assert r.status_code == 400


def test_webrtc_offer_missing_params(client, csrf, default_credentials):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)

    r = client.post('/api/webrtc/offer', json={}, headers={'X-CSRF-Token': tok})
    assert r.status_code == 400
    assert r.json['ok'] is False
    assert 'Thiếu SDP hoặc type' in r.json['error']


def test_webrtc_offer_success(client, csrf, default_credentials, app, monkeypatch):
    _login(client, csrf, default_credentials)
    tok = _post_csrf(client)

    # Mock app.webrtc_mgr.run_coro to avoid actual RTCPeerConnection negotiation
    fake_answer = {'sdp': 'dummy_sdp_answer', 'type': 'answer'}

    def fake_run_coro(coro):
        coro.close()
        return fake_answer

    monkeypatch.setattr(app.webrtc_mgr, 'run_coro', fake_run_coro)

    r = client.post(
        '/api/webrtc/offer',
        json={'sdp': 'dummy_sdp_offer', 'type': 'offer'},
        headers={'X-CSRF-Token': tok},
    )
    assert r.status_code == 200
    assert r.json['ok'] is True
    assert r.json['sdp'] == 'dummy_sdp_answer'
    assert r.json['type'] == 'answer'


def test_webrtc_manager_channel_management(app):
    # Test WebRTCManager local channels/pcs sets
    mgr = app.WebRTCManager()

    # Setup dummy mock channel
    mock_channel = MagicMock()
    mock_channel.label = "video"
    mock_channel.readyState = "open"

    mgr.add_channel(mock_channel)
    assert mock_channel in mgr.channels

    mgr.remove_channel(mock_channel)
    assert mock_channel not in mgr.channels
