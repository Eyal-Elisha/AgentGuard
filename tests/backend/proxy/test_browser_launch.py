"""Finding each agent's browser.

Browser locations are resolved for every platform here, not only the one the
tests happen to run on, because the paths differ per platform and only one of
them can ever be exercised for real.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.proxy.launcher import browser as launch_agent


def _same_path(a, b):
    """Compare ignoring separator, since Path uses the host OS's."""
    return str(a).replace("\\", "/") == str(b).replace("\\", "/")


@pytest.mark.parametrize(
    "platform, expected",
    [("win32", "win32"), ("darwin", "darwin"), ("linux", "linux"), ("freebsd13", "linux")],
)
def test_platform_key_maps_every_platform(platform, expected):
    assert launch_agent.platform_key(platform) == expected


@pytest.mark.parametrize("agent", ["BrowserOS", "MicrosoftEdge"])
@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_every_agent_has_candidates_on_every_platform(agent, platform):
    assert launch_agent.BROWSER_PATHS[agent][launch_agent.platform_key(platform)]


def test_windows_paths_use_environment_variables_not_a_fixed_user():
    """A literal user directory would only ever work on the machine it was
    written on."""
    for agent in ("BrowserOS", "MicrosoftEdge"):
        for candidate in launch_agent.BROWSER_PATHS[agent]["win32"]:
            assert ":\\" not in candidate, candidate


@pytest.mark.parametrize(
    "platform, present, expected",
    [
        ("darwin", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
         "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        ("win32", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ],
)
def test_an_absolute_candidate_is_used_when_the_file_exists(platform, present, expected):
    with (
        patch.object(launch_agent.os.path, "expandvars", side_effect=lambda p: p.replace(
            "%PROGRAMFILES%", r"C:\Program Files").replace(
            "%PROGRAMFILES(X86)%", r"C:\Program Files (x86)").replace(
            "%LOCALAPPDATA%", r"C:\Users\someone\AppData\Local")),
        patch.object(launch_agent.Path, "is_file", lambda self: _same_path(self, present)),
    ):
        assert _same_path(launch_agent.find_browser("MicrosoftEdge", platform), expected)


def test_a_bare_name_falls_back_to_path_lookup():
    """Linux installs land on PATH rather than at a fixed location."""
    with (
        patch.object(launch_agent.Path, "is_file", lambda self: False),
        patch.object(launch_agent.shutil, "which",
                     side_effect=lambda n: "/usr/bin/microsoft-edge" if n == "microsoft-edge" else None),
    ):
        assert launch_agent.find_browser("MicrosoftEdge", "linux") == "/usr/bin/microsoft-edge"


def test_nothing_installed_returns_none_rather_than_a_wrong_guess():
    with (
        patch.object(launch_agent.Path, "is_file", lambda self: False),
        patch.object(launch_agent.shutil, "which", return_value=None),
    ):
        assert launch_agent.find_browser("BrowserOS", "darwin") is None


def test_browseros_falls_back_to_its_chromium_location():
    """It installs under a plain "Chromium" directory, with nothing in the path
    carrying its own name."""
    chromium = "/Applications/Chromium.app/Contents/MacOS/Chromium"
    with (
        patch.object(launch_agent.Path, "is_file", lambda self: _same_path(self, chromium)),
        patch.object(launch_agent.shutil, "which", return_value=None),
    ):
        assert _same_path(launch_agent.find_browser("BrowserOS", "darwin"), chromium)


def test_the_command_carries_the_agents_own_port_and_a_separate_profile():
    command = launch_agent.build_command("/usr/bin/chromium", 8081, "BrowserOS", own_profile=True)
    assert command[0] == "/usr/bin/chromium"
    assert "--proxy-server=127.0.0.1:8081" in command
    assert any(arg.startswith("--user-data-dir=") for arg in command)


def test_the_main_profile_is_used_without_a_data_dir():
    command = launch_agent.build_command("/usr/bin/chromium", 8081, "BrowserOS", own_profile=False)
    assert not any(arg.startswith("--user-data-dir=") for arg in command)


def test_the_port_comes_from_the_catalogue_allocation():
    """Not written into the script, so it follows the catalogue."""
    from backend.proxy.ports import ports_for_agent

    for agent in ("BrowserOS", "MicrosoftEdge"):
        command = launch_agent.build_command("browser", ports_for_agent(agent).listen_port,
                                             agent, own_profile=False)
        assert f"--proxy-server=127.0.0.1:{ports_for_agent(agent).listen_port}" in command
