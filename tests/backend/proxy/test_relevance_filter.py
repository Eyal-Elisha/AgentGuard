"""Concrete noisy request families should not reach backend analysis."""

from __future__ import annotations

from tests.backend.proxy.test_filter_requests import _flow
from backend.proxy.filter_requests import should_forward


def test_google_omnibox_suggestion_is_not_forwarded():
    flow = _flow(host="www.google.com", path="/complete/search?client=chrome-omni&q=wa")
    assert should_forward(flow) is False


def test_google_new_tab_async_is_not_forwarded():
    flow = _flow(host="www.google.com", path="/async/newtab_promos")
    assert should_forward(flow) is False


def test_chatgpt_telemetry_is_not_forwarded():
    flow = _flow(host="chatgpt.com", path="/ces/v1/telemetry/intake")
    assert should_forward(flow) is False


def test_chatgpt_websocket_backend_ping_is_not_forwarded():
    flow = _flow(host="chatgpt.com", path="/backend-api/celsius/ws/user")
    assert should_forward(flow) is False


def test_whatsapp_static_resource_is_not_forwarded():
    flow = _flow(host="static.whatsapp.net", path="/rsrc.php/v4/yK/r/app.js")
    assert should_forward(flow) is False


def test_walla_asset_is_not_forwarded():
    flow = _flow(host="www.walla.co.il", path="/public/assets/icons/homepage3/icon-mail.svg")
    assert should_forward(flow) is False


def test_grammarly_extension_log_is_not_forwarded():
    flow = _flow(host="f-log-extension.grammarly.io", path="/logv2", method="POST")
    assert should_forward(flow) is False


def test_google_play_log_is_not_forwarded():
    flow = _flow(host="play.google.com", path="/log?format=json", method="POST")
    assert should_forward(flow) is False
