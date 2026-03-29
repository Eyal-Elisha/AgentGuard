from flask import Flask

from backend.settings import load_settings_env


def create_app() -> Flask:
    """
    Application factory for the AgentGuard backend.
    Wires together routing, analysis, and storage layers.
    """
    load_settings_env()

    app = Flask(__name__)

    from .routes import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    return app
