"""Every setting AgentGuard reads, from the one backend/.env the backend and the
proxy share. Split into env, network, runtime and credentials.
"""

from .credentials import get_log_encryption_key, resolve_jwt_secret
from .env import BACKEND_DIR, REPO_ROOT, env_flag, load_settings_env
from .network import (
    DEFAULT_PROXY_PORT,
    DEFAULT_PROXY_WEB_PORT,
    get_api_host,
    get_api_port,
    get_backend_decision_url,
    get_dashboard_url,
    get_frontend_port,
    get_proxy_port,
    get_proxy_web_port,
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
    "DEFAULT_PROXY_PORT",
    "DEFAULT_PROXY_WEB_PORT",
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
    "get_proxy_web_port",
    "load_settings_env",
    "resolve_jwt_secret",
    "server_port",
    "set_passive_mode",
]
