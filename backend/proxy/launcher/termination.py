"""Stopping a proxy instance, and everything platform-specific about it.

mitmweb spawns child workers that hold the listen port, so every path here
targets the whole tree rather than the parent alone. A survivor keeps the port
and the agent, whose port never changes, cannot be started again.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys

_logger = logging.getLogger(__name__)


def terminate(process: subprocess.Popen) -> None:
    """Stop an instance and its workers.

    Raises OSError, or SubprocessError if a kill or a wait times out; the
    caller reports either rather than leaving a half-stopped entry behind.
    """
    if sys.platform == "win32":
        # taskkill /T /F kills the tree; terminating only the parent leaves the
        # workers holding the listen port.
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(process.pid)],
            capture_output=True,
            timeout=10,
        )
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        return

    # Same reason, by process group: the instance was started in its own
    # session, so the group is mitmweb and its workers and nothing else.
    _signal_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        _signal_group(process, signal.SIGKILL)
        process.wait(timeout=5)


def _signal_group(process: subprocess.Popen, sig: int) -> None:
    """Signal an instance's whole process group. POSIX only.

    Falls back to the process alone if the group cannot be resolved, which is
    still better than not signalling.
    """
    try:
        os.killpg(os.getpgid(process.pid), sig)
    except ProcessLookupError:
        pass  # Already gone; nothing to signal.
    except OSError:
        process.send_signal(sig)


def kill_process_on_port(port: int) -> bool:
    """Best-effort: kill whatever process is listening on `port`.

    Used as a fallback when the proxy was started outside Flask's control
    (e.g. via `python proxy_launcher.py` directly) and the agent has no registry
    entry. Always the port allocated to the agent being stopped, so another
    agent's instance is never the one killed.
    """
    try:
        if sys.platform == "win32":
            return _kill_listeners_windows(port)
        return _kill_listeners_posix(port)
    except Exception as exc:
        _logger.debug("[AgentGuard] kill_process_on_port(%s) failed: %s", port, exc)
    return False


def _kill_listeners_windows(port: int) -> bool:
    out = subprocess.check_output(
        ["netstat", "-ano"],
        text=True,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )
    killed_any = False
    seen_pids: set[int] = set()
    for line in out.splitlines():
        if f":{port}" not in line or "LISTENING" not in line:
            continue
        try:
            pid = int(line.split()[-1])
        except ValueError:
            continue
        if pid <= 4 or pid in seen_pids:  # never kill System/Idle, dedupe
            continue
        seen_pids.add(pid)
        # /T kills the whole tree (mitmweb spawns workers).
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
        _logger.info("[AgentGuard] Killed external mitmweb PID %s on port %s", pid, port)
        killed_any = True
    return killed_any


def _kill_listeners_posix(port: int) -> bool:
    out = subprocess.check_output(
        ["lsof", "-ti", f"tcp:{port}"],
        text=True,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )
    for pid_str in out.strip().splitlines():
        pid = int(pid_str.strip())
        if pid > 1:
            os.kill(pid, signal.SIGTERM)
            _logger.info("[AgentGuard] Killed external mitmweb PID %s on port %s", pid, port)
    return True
