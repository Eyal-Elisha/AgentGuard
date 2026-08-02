"""Every setting AgentGuard reads, in one place.

The backend and the proxy addon run as separate processes but share one
`backend/.env`, so both go through here rather than reading os.environ.

  env          loading .env, and the primitives the rest are built on
  network      hosts, ports and the URLs derived from them
  runtime      proxy timeout, failure mode, passive mode, audit log path
  credentials  the JWT secret and the log encryption key
"""

from .credentials import get_log_encryption_key, resolve_jwt_secret
from .env import BACKEND_DIR, REPO_ROOT, env_flag, load_settings_env
from .network import (
    get_api_host,
    get_api_port,
    get_backend_decision_url,
    get_dashboard_url,
    get_frontend_port,
    get_proxy_port,
    server_port,
)
from .runtime import (
    BackendFailureMode,
    get_audit_log_path,
    get_backend_failure_mode,
    get_backend_timeout_seconds,
    get_passive_mode,
    set_passive_mode,
)

__all__ = [
    "BACKEND_DIR",
    "REPO_ROOT",
    "BackendFailureMode",
    "env_flag",
    "get_api_host",
    "get_api_port",
    "get_audit_log_path",
    "get_backend_decision_url",
    "get_backend_failure_mode",
    "get_backend_timeout_seconds",
    "get_dashboard_url",
    "get_frontend_port",
    "get_log_encryption_key",
    "get_passive_mode",
    "get_proxy_port",
    "load_settings_env",
    "resolve_jwt_secret",
    "server_port",
    "set_passive_mode",
]
