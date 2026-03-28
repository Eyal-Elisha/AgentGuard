"""HTTP API routes."""

from flask import Blueprint, jsonify

app_bp = Blueprint("app", __name__)


@app_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


def register_blueprints(application):
    application.register_blueprint(app_bp, url_prefix="")


from . import auth_routes, event_routes, rule_routes, session_routes  # noqa: E402,F401
