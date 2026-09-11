"""Structured, redacting logging for a Selenium run.

One JSON line per event, with the run id attached to everything, so a failed
run can be reconstructed from the log alone. A filter masks credential-shaped
text as a second line of defence - the first is never passing secrets to a
logger in the first place.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from .artifacts import redact
from .config import RunConfig

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class RedactingJsonFormatter(logging.Formatter):
    """Render a record as a single redacted JSON object."""

    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.run_id = run_id

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "run_id": self.run_id,
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return redact(json.dumps(payload, ensure_ascii=False, default=str))


def configure_logging(cfg: RunConfig, level: int = logging.INFO) -> logging.Logger:
    """Attach a console handler and a per-run JSONL file handler.

    Idempotent: calling it twice for the same run does not duplicate handlers.
    """
    cfg.prepare_dirs()
    root = logging.getLogger("sentinel")
    root.setLevel(level)
    root.propagate = False

    marker = f"sentinel:{cfg.run_id}"
    if any(getattr(handler, "_sentinel_marker", None) == marker for handler in root.handlers):
        return root
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = RedactingJsonFormatter(cfg.run_id)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console._sentinel_marker = marker  # type: ignore[attr-defined]
    root.addHandler(console)

    file_handler = logging.FileHandler(cfg.log_dir / "run.jsonl", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler._sentinel_marker = marker  # type: ignore[attr-defined]
    root.addHandler(file_handler)

    # Selenium's own HTTP chatter is noisy and can echo URLs with query secrets.
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    root.info("run.configured", extra={"browser": cfg.browser, "headless": cfg.headless})
    return root
