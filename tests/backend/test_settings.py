from __future__ import annotations

import os
from unittest.mock import patch

from backend.settings import get_api_host, get_api_port, get_backend_decision_url, get_proxy_port


def test_get_backend_decision_url_uses_api_port():
    with patch.dict(os.environ, {"API_PORT": "3000"}, clear=False):
        assert get_backend_decision_url() == "http://127.0.0.1:3000/api/proxy/decision"


def test_get_backend_decision_url_uses_api_host_when_configured():
    with patch.dict(os.environ, {"API_HOST": "localhost", "API_PORT": "3000"}, clear=False):
        assert get_backend_decision_url() == "http://localhost:3000/api/proxy/decision"


def test_get_proxy_port_reads_proxy_port_env():
    with patch.dict(os.environ, {"PROXY_PORT": "8080"}, clear=False):
        assert get_proxy_port() == 8080


def test_get_proxy_port_falls_back_when_invalid():
    with patch.dict(os.environ, {"PROXY_PORT": "bad"}, clear=False):
        assert get_proxy_port() == 8080


def test_get_api_port_reads_api_port_env():
    with patch.dict(os.environ, {"API_PORT": "3000"}, clear=False):
        assert get_api_port() == 3000


def test_get_api_port_falls_back_to_port_env():
    with patch.dict(os.environ, {"PORT": "3000"}, clear=False):
        if "API_PORT" in os.environ:
            del os.environ["API_PORT"]
        assert get_api_port() == 3000


def test_get_api_host_defaults_to_loopback():
    with patch.dict(os.environ, {}, clear=False):
        assert get_api_host() == "127.0.0.1"
