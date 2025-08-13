import importlib
import importlib.util
import os
import sys
from fastapi.testclient import TestClient


def _load_app_module():
    tests_dir = os.path.dirname(__file__)
    bridge_dir = os.path.abspath(os.path.join(tests_dir, os.pardir))
    if bridge_dir not in sys.path:
        sys.path.insert(0, bridge_dir)
    app_path = os.path.join(bridge_dir, 'app.py')
    spec = importlib.util.spec_from_file_location('app', app_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Ensure module can import sibling modules like mail_live
    module.__package__ = ''
    sys.modules['app'] = module
    spec.loader.exec_module(module)  # type: ignore
    return module


def test_health_demo_mode(monkeypatch):
    monkeypatch.setenv('MAIL_BRIDGE_MODE', 'demo')
    # Ensure module import uses demo mode
    app_module = _load_app_module()
    client = TestClient(app_module.app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'


def test_messages_demo_mode(monkeypatch):
    monkeypatch.setenv('MAIL_BRIDGE_MODE', 'demo')
    app_module = _load_app_module()
    client = TestClient(app_module.app)
    r = client.get('/v1/mail/messages', params={'mailbox': 'Inbox', 'limit': 3})
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) == 3
    assert all('id' in it and 'subject' in it and 'ts' in it for it in items)


def test_messages_live_mode_falls_back(monkeypatch):
    # Force live mode but stub fetch to raise, ensuring fallback to demo
    monkeypatch.setenv('MAIL_BRIDGE_MODE', 'live')
    app_module = _load_app_module()
    # Stub mail_live.fetch_mail_messages to raise
    import types
    fake = types.SimpleNamespace()
    def _boom(**kwargs):
        raise RuntimeError('boom')
    import builtins
    # Inject a temporary module object
    sys.modules['mail_live'] = types.SimpleNamespace(fetch_mail_messages=_boom)
    try:
        client = TestClient(app_module.app)
        r = client.get('/v1/mail/messages', params={'mailbox': 'Inbox', 'limit': 2})
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) == 2
    finally:
        sys.modules.pop('mail_live', None)


