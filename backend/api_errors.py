"""Consistent JSON error responses and API error logging."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

_API_LOGGER_NAME = "agentguard.api"
_STREAM_HANDLER_NAME = "agentguard.api.stream"


def configure_api_logger() -> logging.Logger:
    logger = logging.getLogger(_API_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        if handler.get_name() == _STREAM_HANDLER_NAME:
            logger.removeHandler(handler)
            handler.close()

    stream_handler = logging.StreamHandler()
    stream_handler.set_name(_STREAM_HANDLER_NAME)
    stream_handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(stream_handler)
    return logger


def _log_api_error(
    logger: logging.Logger,
    *,
    status_code: int,
    method: str,
    path: str,
    message: str,
    exc: BaseException | None = None,
) -> None:
    detail = f"{method} {path} -> {status_code}: {message}"
    if status_code >= 500:
        logger.error(detail, exc_info=exc)
    elif status_code >= 400:
        logger.warning(detail)


def register_api_error_handlers(app: Flask) -> None:
    logger = configure_api_logger()

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException) -> tuple[Any, int]:
        status_code = exc.code or 500
        message = exc.description or "Request failed"
        _log_api_error(
            logger,
            status_code=status_code,
            method=request.method,
            path=request.path,
            message=message,
        )
        return jsonify({"error": message}), status_code

    @app.errorhandler(sqlite3.OperationalError)
    def handle_database_error(exc: sqlite3.OperationalError) -> tuple[Any, int]:
        _log_api_error(
            logger,
            status_code=503,
            method=request.method,
            path=request.path,
            message="Database temporarily unavailable",
            exc=exc,
        )
        return jsonify({"error": "Database temporarily unavailable"}), 503

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception) -> tuple[Any, int]:
        _log_api_error(
            logger,
            status_code=500,
            method=request.method,
            path=request.path,
            message="Internal server error",
            exc=exc,
        )
        return jsonify({"error": "Internal server error"}), 500
