from flask import Flask

from .config import env_flag, resolve_jwt_secret
from .storage.sqlite_store import init_schema


def create_app() -> Flask:
    app = Flask(__name__)
    require_auth = env_flag("REQUIRE_AUTH", default=False)
    app.config["REQUIRE_AUTH"] = require_auth
    app.config["JWT_SECRET"] = resolve_jwt_secret()

    init_schema()

    from .routes import register_blueprints

    register_blueprints(app)

    return app
