"""The wiring between the power button and the browser."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from backend import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{Path(tmp_path / 'test.db').as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    monkeypatch.setenv("AGENTGUARD_LOG_ENCRYPTION_KEY", Fernet.generate_key().decode())
    return create_app().test_client()


def _control(client, agent, active=True):
    return client.post(
        "/api/proxy/control",
        json={"active": active, "environment": "test", "agent_name": agent},
    )


def test_starting_a_named_agent_opens_its_browser(client):
    with (
        patch("backend.routes.proxy_control.start_proxy_process", return_value=(True, "started")),
        patch("backend.routes.proxy_control.proxy_is_running", return_value=True),
        patch(
            "backend.routes.proxy_control.launch_browser", return_value=(True, "launched")
        ) as launch,
    ):
        response = _control(client, "MicrosoftEdge")

    launch.assert_called_once_with("MicrosoftEdge")
    assert response.get_json()["browser_launched"] is True


def test_starting_all_traffic_opens_nothing(client):
    """It is the machine's proxy setting; there is no application to open."""
    with (
        patch("backend.routes.proxy_control.start_proxy_process", return_value=(True, "started")),
        patch("backend.routes.proxy_control.proxy_is_running", return_value=True),
        patch("backend.routes.proxy_control.launch_browser") as launch,
    ):
        response = _control(client, "AllTraffic")

    launch.assert_not_called()
    assert "browser_launched" not in response.get_json()


def test_stopping_never_opens_a_browser(client):
    with (
        patch("backend.routes.proxy_control.stop_proxy_process", return_value=(True, "stopped")),
        patch("backend.routes.proxy_control.proxy_is_running", return_value=False),
        patch("backend.routes.proxy_control.launch_browser") as launch,
    ):
        _control(client, "MicrosoftEdge", active=False)

    launch.assert_not_called()


def test_a_browser_that_will_not_open_still_leaves_the_agent_protected(client):
    with (
        patch("backend.routes.proxy_control.start_proxy_process", return_value=(True, "started")),
        patch("backend.routes.proxy_control.proxy_is_running", return_value=True),
        patch(
            "backend.routes.proxy_control.launch_browser",
            return_value=(False, "Could not find MicrosoftEdge on this machine."),
        ),
    ):
        response = _control(client, "MicrosoftEdge")

    body = response.get_json()
    assert response.status_code == 200
    assert body["active"] is True
    assert body["browser_launched"] is False
    assert "Could not find" in body["browser_error"]


def test_a_proxy_that_failed_to_start_opens_nothing(client):
    with (
        patch(
            "backend.routes.proxy_control.start_proxy_process",
            return_value=(False, "port in use"),
        ),
        patch("backend.routes.proxy_control.proxy_is_running", return_value=False),
        patch("backend.routes.proxy_control.launch_browser") as launch,
    ):
        response = _control(client, "BrowserOS")

    launch.assert_not_called()
    assert response.status_code == 500
