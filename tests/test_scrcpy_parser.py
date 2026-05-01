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


def test_is_valid_host(real_scrcpy):
    assert real_scrcpy.is_valid_host('192.168.1.10')
    assert real_scrcpy.is_valid_host('phone-pixel')
    assert real_scrcpy.is_valid_host('a-b.c1')
    assert not real_scrcpy.is_valid_host('')
    assert not real_scrcpy.is_valid_host('1.2.3.4;rm -rf /')
    assert not real_scrcpy.is_valid_host('$(whoami)')
    assert not real_scrcpy.is_valid_host('a' * 254)


def test_is_valid_port(real_scrcpy):
    assert real_scrcpy.is_valid_port(1)
    assert real_scrcpy.is_valid_port('5555')
    assert real_scrcpy.is_valid_port(65535)
    assert not real_scrcpy.is_valid_port(0)
    assert not real_scrcpy.is_valid_port(70000)
    assert not real_scrcpy.is_valid_port('abc')
    assert not real_scrcpy.is_valid_port('')


def test_is_valid_new_display(real_scrcpy):
    assert real_scrcpy.is_valid_new_display('1920x1080/160')
    assert real_scrcpy.is_valid_new_display('2560x1440/240')
    assert real_scrcpy.is_valid_new_display('1280x720')
    assert real_scrcpy.is_valid_new_display('/240')
    assert not real_scrcpy.is_valid_new_display('')
    assert not real_scrcpy.is_valid_new_display('foo')
    assert not real_scrcpy.is_valid_new_display('1920x1080;rm')
    assert not real_scrcpy.is_valid_new_display('1920x1080/abc')
    assert not real_scrcpy.is_valid_new_display('99x99')  # too small
    assert not real_scrcpy.is_valid_new_display('99999x99999')


def test_adb_pair_validates_inputs(real_scrcpy, monkeypatch):
    """adb_pair must reject bad host/port/code without invoking subprocess."""
    called = {'n': 0}

    def fake_run(*args, **kwargs):
        called['n'] += 1
        return SimpleNamespace(returncode=0, stdout='Successfully paired', stderr='')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    ok, _ = real_scrcpy.adb_pair('bad host', 5555, '123456')
    assert not ok
    ok, _ = real_scrcpy.adb_pair('1.2.3.4', 0, '123456')
    assert not ok
    ok, _ = real_scrcpy.adb_pair('1.2.3.4', 5555, 'abc')
    assert not ok
    assert called['n'] == 0  # never invoked subprocess
    ok, out = real_scrcpy.adb_pair('1.2.3.4', 5555, '123456')
    assert ok and 'paired' in out.lower()


def test_adb_connect_detects_failure_text(real_scrcpy, monkeypatch):
    """`adb connect` exits 0 even on failure — must look at stdout text."""
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda *a, **k: SimpleNamespace(
            returncode=0, stdout='cannot connect to 1.2.3.4:5555', stderr=''
        ),
    )
    ok, _ = real_scrcpy.adb_connect('1.2.3.4', 5555)
    assert not ok
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda *a, **k: SimpleNamespace(
            returncode=0, stdout='connected to 1.2.3.4:5555', stderr=''
        ),
    )
    ok, _ = real_scrcpy.adb_connect('1.2.3.4', 5555)
    assert ok
