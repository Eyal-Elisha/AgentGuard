"""HTTP API routes."""

from flask import Blueprint, jsonify

app_bp = Blueprint("app", __name__)
# Mounted at /api so proxy and settings agree on /api/proxy/decision
api_bp = Blueprint("api", __name__, url_prefix="/api")


@app_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


def register_blueprints(application):
    application.register_blueprint(app_bp, url_prefix="")
    application.register_blueprint(api_bp)


# Imported for their side effect of registering routes on the blueprints above,
# which is why they come after the blueprints are defined.
from . import (  # noqa: E402,F401
    admin_routes,
    auth_routes,
    blacklist_routes,
    event_routes,
    proxy,
    proxy_control,
    rule_routes,
    session_routes,
)
