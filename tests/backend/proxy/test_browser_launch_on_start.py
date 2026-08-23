"""Opening the browser an agent is protected through."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.proxy.launcher import browser


@pytest.fixture
def popen():
    with patch.object(browser.subprocess, "Popen") as spawn:
        yield spawn


@pytest.fixture
def installed():
    with patch.object(browser, "find_browser", return_value="/usr/bin/chromium"):
        yield


def test_all_traffic_launches_nothing(popen):
    """It is the machine's proxy setting, not an application."""
    launched, detail = browser.launch_browser("AllTraffic")

    assert (launched, detail) == (False, "not_launchable")
    popen.assert_not_called()


@pytest.mark.parametrize("agent", ["BrowserOS", "MicrosoftEdge"])
def test_a_named_agent_opens_at_its_own_port(agent, installed, popen):
    from backend.proxy.ports import ports_for_agent

    launched, _detail = browser.launch_browser(agent)

    assert launched is True
    command = popen.call_args.args[0]
    assert f"--proxy-server=127.0.0.1:{ports_for_agent(agent).listen_port}" in command


def test_the_launch_gets_a_profile_of_its_own(installed, popen):
    """Chromium hands a launch to an instance that is already running, and
    ignores --proxy-server when it does."""
    browser.launch_browser("BrowserOS")

    command = popen.call_args.args[0]
    assert any(arg.startswith("--user-data-dir=") for arg in command)


def test_a_browser_that_is_not_installed_is_reported_not_raised(popen):
    with patch.object(browser, "find_browser", return_value=None):
        launched, detail = browser.launch_browser("MicrosoftEdge")

    assert launched is False
    assert "MicrosoftEdge" in detail
    popen.assert_not_called()


def test_a_browser_that_will_not_spawn_is_reported_not_raised(installed):
    with patch.object(browser.subprocess, "Popen", side_effect=OSError("denied")):
        launched, detail = browser.launch_browser("BrowserOS")

    assert launched is False
    assert "denied" in detail


def test_the_launch_is_not_waited_on(installed, popen):
    """Waiting would hang the Guard screen until the browser was closed."""
    browser.launch_browser("BrowserOS")

    popen.return_value.wait.assert_not_called()
    popen.return_value.communicate.assert_not_called()
