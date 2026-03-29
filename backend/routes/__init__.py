from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

from . import proxy as _proxy_routes  # noqa: E402,F401
