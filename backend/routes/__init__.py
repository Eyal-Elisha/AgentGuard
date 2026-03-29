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


from . import auth_routes, event_routes, rule_routes, session_routes  # noqa: E402,F401

from . import proxy as _proxy_routes  # noqa: E402,F401
