from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from backend.settings import get_proxy_port, load_settings_env

_logger = logging.getLogger(__name__)

_mitm_process: subprocess.Popen | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _resolve_mitmweb_executable() -> str:
    sibling_name = "mitmweb.exe" if sys.platform.startswith("win") else "mitmweb"
    sibling = Path(sys.executable).resolve().with_name(sibling_name)
    if sibling.is_file():
        return str(sibling)
    discovered = shutil.which("mitmweb")
    if discovered:
        return discovered
    raise RuntimeError("Could not find mitmweb in the current environment.")


def build_mitmweb_command() -> list[str]:
    """Same argv as `main()` uses (excluding extra CLI passthrough)."""
    load_settings_env()
    repo_root = _repo_root()
    script_path = repo_root / "backend" / "proxy" / "traffic_interception.py"
    return [
        _resolve_mitmweb_executable(),
        "-s",
        str(script_path),
        "--listen-port",
        str(get_proxy_port()),
    ]


def _mitm_env() -> dict[str, str]:
    env = os.environ.copy()
    # TODO: Remove this once the project is packaged/installable and mitm can import `backend` without PYTHONPATH.
    env["PYTHONPATH"] = str(_repo_root())
    return env


def proxy_is_running() -> bool:
    global _mitm_process
    if _mitm_process is None:
        return False
    return _mitm_process.poll() is None


def start_proxy_process() -> tuple[bool, str]:
    """Start mitmweb with `traffic_interception.py` (decision enforcement). Idempotent if already running."""
    global _mitm_process
    if proxy_is_running():
        return True, "already_running"
    try:
        cmd = build_mitmweb_command()
    except RuntimeError as exc:
        return False, str(exc)
    repo_root = _repo_root()
    popen_kw: dict = {
        "cwd": str(repo_root),
        "env": _mitm_env(),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        popen_kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        _mitm_process = subprocess.Popen(cmd, **popen_kw)
    except OSError as exc:
        _logger.exception("Failed to start mitmweb")
        return False, str(exc)
    return True, "started"


def stop_proxy_process() -> tuple[bool, str]:
    """Terminate the mitmweb process started by `start_proxy_process`."""
    global _mitm_process
    if _mitm_process is None:
        return True, "not_running"
    if _mitm_process.poll() is not None:
        _mitm_process = None
        return True, "not_running"
    proc = _mitm_process
    try:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    except OSError as exc:
        _logger.exception("Failed to stop mitmweb")
        _mitm_process = None
        return False, str(exc)
    _mitm_process = None
    return True, "stopped"


def main() -> int:
    load_settings_env()
    repo_root = _repo_root()
    command = build_mitmweb_command()
    command.extend(sys.argv[1:])
    env = _mitm_env()
    return subprocess.call(command, cwd=repo_root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())