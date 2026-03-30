from __future__ import annotations

import logging
from pathlib import Path

from backend.settings import get_audit_log_path

_AUDIT_LOGGER_NAME = "agentguard.audit"
_FILE_HANDLER_NAME = "agentguard.audit.file"
_STREAM_HANDLER_NAME = "agentguard.audit.stream"


def configure_audit_logger() -> logging.Logger:
    logger = logging.getLogger(_AUDIT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        if handler.get_name() in {_FILE_HANDLER_NAME, _STREAM_HANDLER_NAME}:
            logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter("%(message)s")

    log_path = Path(get_audit_log_path())
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.set_name(_FILE_HANDLER_NAME)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.set_name(_STREAM_HANDLER_NAME)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
