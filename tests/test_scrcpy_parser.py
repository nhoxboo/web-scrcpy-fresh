"""Unit tests for scrcpy.list_adb_devices() output parser.

Exercises the parser via subprocess.run mock so no real adb is needed.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def real_scrcpy():
    """Import the real scrcpy.py, then restore the conftest stub afterwards so
    other tests (test_devices.py) keep using the fake module."""
    saved_stub = sys.modules.get('scrcpy')
    saved_app = sys.modules.pop('app', None)
    sys.modules.pop('scrcpy', None)
    real = importlib.import_module('scrcpy')
    yield real
    sys.modules.pop('scrcpy', None)
    if saved_stub is not None:
        sys.modules['scrcpy'] = saved_stub
    if saved_app is not None:
        sys.modules['app'] = saved_app


def test_parses_typical_output(real_scrcpy, monkeypatch):
    sample = (
        'List of devices attached\n'
        'ABCD1234EFGH           device usb:1-2 product:dm3qxx model:SM_S918B '
        'device:dm3q transport_id:1\n'
        '192.168.1.42:5555      device product:r8q model:SM_G991B '
        'device:r8q transport_id:3\n'
    )
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=sample, stderr=''),
    )
    devices = real_scrcpy.list_adb_devices()
    assert len(devices) == 2
    assert devices[0]['serial'] == 'ABCD1234EFGH'
    assert devices[0]['state'] == 'device'
    assert devices[0]['model'] == 'SM_S918B'
    assert devices[0]['transport_id'] == '1'
    assert devices[1]['serial'] == '192.168.1.42:5555'
    assert devices[1]['model'] == 'SM_G991B'


def test_handles_no_devices(real_scrcpy, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda *a, **k: SimpleNamespace(
            returncode=0, stdout='List of devices attached\n', stderr=''
        ),
    )
    assert real_scrcpy.list_adb_devices() == []


def test_handles_unauthorized(real_scrcpy, monkeypatch):
    sample = 'List of devices attached\nXYZ123 unauthorized\n'
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=sample, stderr=''),
    )
    devices = real_scrcpy.list_adb_devices()
    assert devices == [
        {
            'serial': 'XYZ123',
            'state': 'unauthorized',
            'model': '',
            'product': '',
            'transport_id': '',
            'usb': '',
        }
    ]


def test_handles_adb_not_found(real_scrcpy, monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError('adb')

    monkeypatch.setattr(subprocess, 'run', boom)
    assert real_scrcpy.list_adb_devices() == []


def test_handles_nonzero_exit(real_scrcpy, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda *a, **k: SimpleNamespace(returncode=1, stdout='', stderr='daemon not running'),
    )
    assert real_scrcpy.list_adb_devices() == []


def test_is_valid_serial(real_scrcpy):
    assert real_scrcpy.is_valid_serial('ABC123')
    assert real_scrcpy.is_valid_serial('192.168.1.10:5555')
    assert real_scrcpy.is_valid_serial('emulator-5554')
    assert not real_scrcpy.is_valid_serial('')
    assert not real_scrcpy.is_valid_serial('rm -rf /')
    assert not real_scrcpy.is_valid_serial('a;b')
    assert not real_scrcpy.is_valid_serial('x' * 65)
