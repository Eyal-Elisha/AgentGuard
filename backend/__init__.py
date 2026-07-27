from flask import Flask

from .api_errors import register_api_error_handlers
from .analysis.rules import CONTEXTUAL_RULES, DETERMINISTIC_RULES, SEMANTIC_RULES
from .audit_logging import configure_audit_logger
from .config import env_flag, resolve_jwt_secret
from .storage.sqlite_store import init_schema, rules_seed_defaults

from backend.settings import load_settings_env


def create_app() -> Flask:
    load_settings_env()
    configure_audit_logger()

    app = Flask(__name__)
    require_auth = env_flag("REQUIRE_AUTH", default=False)
    app.config["REQUIRE_AUTH"] = require_auth
    app.config["JWT_SECRET"] = resolve_jwt_secret()

    init_schema()
    rules_seed_defaults([
        *DETERMINISTIC_RULES,
        *CONTEXTUAL_RULES,
        *SEMANTIC_RULES,
    ])

    from .routes import register_blueprints

    register_blueprints(app)
    register_api_error_handlers(app)

    @app.after_request
    def _cors(response):
        """Allow the Vite dev server (or other local UIs) to call the API from the browser."""
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        response.headers.setdefault(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization",
        )
        response.headers.setdefault(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, DELETE, OPTIONS",
        )
        return response

    return app
