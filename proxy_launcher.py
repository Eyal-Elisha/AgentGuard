from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from backend.settings import get_proxy_port, load_settings_env

_logger = logging.getLogger(__name__)

_mitm_process: subprocess.Popen | None = None
_mitm_log_handle = None


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
    global _mitm_process, _mitm_log_handle
    if proxy_is_running():
        return True, "already_running"
    try:
        cmd = build_mitmweb_command()
    except RuntimeError as exc:
        return False, str(exc)
    repo_root = _repo_root()
    log_dir = repo_root / ".agentguard"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "mitmweb.log"
    try:
        _mitm_log_handle = open(log_path, "a", encoding="utf-8", buffering=1)
        _mitm_log_handle.write(
            f"\n--- mitmweb start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n"
        )
        _mitm_log_handle.write("cmd: " + " ".join(cmd) + "\n")
    except OSError as exc:
        _mitm_log_handle = None
        return False, f"Failed to open mitmweb log file: {exc}"
    popen_kw: dict = {
        "cwd": str(repo_root),
        "env": _mitm_env(),
        "stdout": _mitm_log_handle or subprocess.DEVNULL,
        "stderr": subprocess.STDOUT if _mitm_log_handle else subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        popen_kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        _mitm_process = subprocess.Popen(cmd, **popen_kw)
    except OSError as exc:
        _logger.exception("Failed to start mitmweb")
        if _mitm_log_handle is not None:
            try:
                _mitm_log_handle.write(f"Failed to spawn mitmweb: {exc}\n")
                _mitm_log_handle.close()
            except OSError:
                pass
            _mitm_log_handle = None
        return False, str(exc)

    # Give mitmweb a moment to fail fast (missing executable, port in use, bad addon import, etc.)
    time.sleep(0.35)
    if not proxy_is_running():
        exit_code = _mitm_process.poll() if _mitm_process is not None else None
        _mitm_process = None
        if _mitm_log_handle is not None:
            try:
                _mitm_log_handle.write(f"mitmweb exited early (exit_code={exit_code}).\n")
                _mitm_log_handle.flush()
                _mitm_log_handle.close()
            except OSError:
                pass
            _mitm_log_handle = None
        return False, f"mitmweb exited early (exit_code={exit_code}). See {log_path} for details."

    return True, "started"


def stop_proxy_process() -> tuple[bool, str]:
    """Terminate the mitmweb process started by `start_proxy_process`."""
    global _mitm_process, _mitm_log_handle
    if _mitm_process is None:
        return True, "not_running"
    if _mitm_process.poll() is not None:
        _mitm_process = None
        if _mitm_log_handle is not None:
            try:
                _mitm_log_handle.write("--- mitmweb already stopped ---\n")
                _mitm_log_handle.close()
            except OSError:
                pass
            _mitm_log_handle = None
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
        if _mitm_log_handle is not None:
            try:
                _mitm_log_handle.write(f"Failed to stop mitmweb: {exc}\n")
                _mitm_log_handle.close()
            except OSError:
                pass
            _mitm_log_handle = None
        return False, str(exc)
    _mitm_process = None
    if _mitm_log_handle is not None:
        try:
            _mitm_log_handle.write("--- mitmweb stopped ---\n")
            _mitm_log_handle.close()
        except OSError:
            pass
        _mitm_log_handle = None
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