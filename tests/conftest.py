"""Turning protection on opens the agent's browser, so a test touching the
control route can put a real window on screen. A test checking that wiring
patches `launch_browser` itself."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def never_open_a_real_browser():
    with patch(
        "backend.proxy.launcher.browser.subprocess.Popen",
        side_effect=AssertionError("a test tried to launch a real browser"),
    ):
        yield
