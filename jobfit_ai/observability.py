"""Structured operational events; never pass user text or exception messages."""
from contextvars import ContextVar
import json
import logging

request_id: ContextVar[str | None] = ContextVar("jobfit_request_id", default=None)
logger = logging.getLogger("jobfit_ai.operations")


def event(name: str, *, level: int = logging.INFO, **fields) -> None:
    logger.log(level, json.dumps({"event": name, "request_id": request_id.get(), **fields}, sort_keys=True))


def configure_api_logging() -> None:
    # Configure only our logger; do not change root or third-party log settings.
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
