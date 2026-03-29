from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from backend.settings import get_proxy_port, load_settings_env


def _resolve_mitmweb_executable() -> str:
    sibling_name = "mitmweb.exe" if sys.platform.startswith("win") else "mitmweb"
    sibling = Path(sys.executable).resolve().with_name(sibling_name)
    if sibling.is_file():
        return str(sibling)
    discovered = shutil.which("mitmweb")
    if discovered:
        return discovered
    raise RuntimeError("Could not find mitmweb in the current environment.")


def main() -> int:
    load_settings_env()
    repo_root = Path(__file__).resolve().parent
    script_path = repo_root / "backend" / "proxy" / "traffic_interception.py"
    command = [
        _resolve_mitmweb_executable(),
        "-s",
        str(script_path),
        "--listen-port",
        str(get_proxy_port()),
        *sys.argv[1:],
    ]
    env = os.environ.copy()
    # TODO: Remove this once the project is packaged/installable and mitm can import `backend` without PYTHONPATH.
    env["PYTHONPATH"] = str(repo_root)
    return subprocess.call(command, cwd=repo_root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())