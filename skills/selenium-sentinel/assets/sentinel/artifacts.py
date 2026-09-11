"""Failure evidence capture.

Collects just enough context to diagnose a failure without exporting secrets.
Page source is opt-in (RunConfig.capture_page_source) because it frequently
contains personal data, tokens in markup, and full form values.
"""

from __future__ import annotations

import json
import logging
import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver

from .config import RunConfig

log = logging.getLogger("sentinel.artifacts")

# Patterns redacted from any text written to an artifact or log line.
_REDACTIONS = (
    re.compile(r"(?i)(password|passwd|secret|token|authorization|api[_-]?key|cookie)\s*[=:]\s*\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"\b\d{13,19}\b"),  # long numeric identifiers (cards, accounts)
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
)


def redact(text: str) -> str:
    """Mask credential-shaped and identity-shaped substrings."""
    for pattern in _REDACTIONS:
        text = pattern.sub("[REDACTED]", text)
    return text


@dataclass
class FailureBundle:
    directory: Path
    screenshot: Path | None
    context: Path
    page_source: Path | None


class ArtifactStore:
    """Writes per-run evidence under RunConfig.evidence_dir."""

    def __init__(self, cfg: RunConfig) -> None:
        self.cfg = cfg
        cfg.prepare_dirs()

    def _stamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    def screenshot(self, driver: WebDriver, name: str) -> Path | None:
        target = self.cfg.evidence_dir / f"{self._stamp()}_{name}.png"
        try:
            driver.save_screenshot(str(target))
            return target
        except Exception:  # noqa: BLE001 - evidence capture must never mask the failure
            log.warning("artifact.screenshot_failed", exc_info=True)
            return None

    def context(self, driver: WebDriver, operation: str, error: BaseException | None = None) -> dict[str, Any]:
        """Collect sanitized diagnostic state for one failure boundary."""
        caps = getattr(driver, "capabilities", {}) or {}
        data: dict[str, Any] = {
            "run_id": self.cfg.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "browser": caps.get("browserName"),
            "browser_version": caps.get("browserVersion"),
            "driver_version": (caps.get("chrome") or {}).get("chromedriverVersion")
            if isinstance(caps.get("chrome"), dict)
            else caps.get("moz:geckodriverVersion"),
            "session_id": getattr(driver, "session_id", None),
            "remote": bool(self.cfg.remote_url),
        }
        for field, getter in (
            ("url", lambda: driver.current_url),
            ("title", lambda: driver.title),
            ("window_handle", lambda: driver.current_window_handle),
            ("window_count", lambda: len(driver.window_handles)),
        ):
            try:
                data[field] = getter()
            except Exception as exc:  # noqa: BLE001 - session may already be broken
                data[field] = f"<unavailable: {type(exc).__name__}>"
        if error is not None:
            data["error_type"] = type(error).__name__
            data["error_message"] = redact(str(error))
            data["traceback"] = redact(
                "".join(traceback.format_exception(type(error), error, error.__traceback__))
            )
        return data

    def failure_bundle(
        self, driver: WebDriver, operation: str, error: BaseException | None = None
    ) -> FailureBundle:
        """Screenshot + sanitized context (+ optional page source) for a failure."""
        stamp = self._stamp()
        directory = self.cfg.evidence_dir
        shot = self.screenshot(driver, operation)

        context_path = directory / f"{stamp}_{operation}.json"
        context_path.write_text(
            json.dumps(self.context(driver, operation, error), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        source_path: Path | None = None
        if self.cfg.capture_page_source:
            try:
                source_path = directory / f"{stamp}_{operation}.html"
                source_path.write_text(redact(driver.page_source), encoding="utf-8")
            except Exception:  # noqa: BLE001
                log.warning("artifact.page_source_failed", exc_info=True)
                source_path = None

        log.error(
            "failure.evidence_captured",
            extra={"operation": operation, "evidence_dir": str(directory)},
        )
        return FailureBundle(
            directory=directory, screenshot=shot, context=context_path, page_source=source_path
        )

    def browser_console(self, driver: WebDriver) -> list[dict[str, Any]]:
        """Chromium console logs when the driver exposes them; empty otherwise."""
        try:
            return driver.get_log("browser")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - Firefox and many remotes do not support it
            return []
