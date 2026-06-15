from __future__ import annotations

import logging
import os
import shutil
import signal
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


def _mitm_env(*, proxy_agent_name: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    # TODO: Remove this once the project is packaged/installable and mitm can import `backend` without PYTHONPATH.
    env["PYTHONPATH"] = str(_repo_root())
    if proxy_agent_name is not None:
        env["AGENTGUARD_PROXY_AGENT_NAME"] = proxy_agent_name
    return env


def proxy_is_running() -> bool:
    global _mitm_process
    if _mitm_process is None:
        return False
    return _mitm_process.poll() is None


def start_proxy_process(*, proxy_agent_name: str | None = None) -> tuple[bool, str]:
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
        "env": _mitm_env(proxy_agent_name=proxy_agent_name),
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


def _kill_process_on_port(port: int) -> bool:
    """Best-effort: kill whatever process is listening on `port`.

    Used as a fallback when the proxy was started outside Flask's control
    (e.g. via `python proxy_launcher.py` directly) and `_mitm_process` is None.
    """
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["netstat", "-ano"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            killed_any = False
            seen_pids: set[int] = set()
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    try:
                        pid = int(parts[-1])
                    except ValueError:
                        continue
                    if pid <= 4 or pid in seen_pids:  # never kill System/Idle, dedupe
                        continue
                    seen_pids.add(pid)
                    # /T kills the whole tree (mitmweb spawns workers).
                    subprocess.run(
                        ["taskkill", "/T", "/F", "/PID", str(pid)],
                        capture_output=True,
                        timeout=5,
                    )
                    _logger.info("[AgentGuard] Killed external mitmweb PID %s on port %s", pid, port)
                    killed_any = True
            return killed_any
        else:
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
    except Exception as exc:
        _logger.debug("[AgentGuard] _kill_process_on_port(%s) failed: %s", port, exc)
    return False


def stop_proxy_process() -> tuple[bool, str]:
    """Terminate the mitmweb process started by `start_proxy_process`.

    If no process is tracked (proxy was started externally), falls back to
    killing whatever is listening on the configured proxy port.
    """
    global _mitm_process, _mitm_log_handle
    if _mitm_process is None:
        # Proxy may have been started outside Flask — try port-based kill.
        killed = _kill_process_on_port(get_proxy_port())
        return True, "stopped" if killed else "not_running"
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
        if sys.platform == "win32":
            # mitmweb spawns child workers; terminating only the parent leaves
            # them holding the listen port. taskkill /T /F kills the tree.
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=10,
            )
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        else:
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
