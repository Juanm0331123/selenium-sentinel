"""Run configuration for a Selenium Sentinel session.

Every value has a safe default and can be overridden by environment variables so
the same workflow code runs locally (headed), in CI (headless), and against a
remote Grid without edits. Nothing here reads secrets: credentials belong in the
project's secret manager and are passed explicitly to the workflow.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path

_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in _TRUE


def _num(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw is not None else default
    except ValueError:
        return default


@dataclass(frozen=True)
class RunConfig:
    """Immutable description of one isolated browser run."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    browser: str = "chrome"  # chrome | firefox | edge
    headless: bool = True
    window_size: tuple[int, int] = (1440, 1200)
    page_load_strategy: str = "normal"  # normal | eager | none
    accept_insecure_certs: bool = False
    locale: str | None = None  # e.g. "es-ES"
    binary_location: str | None = None

    # Synchronization budgets (seconds).
    default_timeout: float = 15.0
    poll_frequency: float = 0.25
    page_load_timeout: float = 45.0
    script_timeout: float = 30.0
    download_timeout: float = 120.0

    # Politeness budgets applied between requests/pages by Throttle.
    min_delay: float = 0.8
    max_delay: float = 2.0

    # Filesystem layout. Every run owns its own subtree: no shared profile,
    # no shared download directory, no shared artifact namespace.
    artifacts_root: Path = Path("artifacts")

    # Remote execution.
    remote_url: str | None = None
    use_local_file_detector: bool = False

    # Diagnostics policy.
    capture_page_source: bool = False  # opt-in: page source can carry private data
    driver_log: bool = True

    @classmethod
    def from_env(cls, **overrides: object) -> "RunConfig":
        """Build a config from SENTINEL_* environment variables plus overrides."""
        width, height = 1440, 1200
        raw_size = os.getenv("SENTINEL_WINDOW_SIZE")
        if raw_size and "x" in raw_size:
            try:
                width, height = (int(part) for part in raw_size.lower().split("x", 1))
            except ValueError:
                pass

        values: dict[str, object] = {
            "browser": os.getenv("SENTINEL_BROWSER", "chrome").strip().lower(),
            "headless": _flag("SENTINEL_HEADLESS", True),
            "window_size": (width, height),
            "page_load_strategy": os.getenv("SENTINEL_PAGE_LOAD_STRATEGY", "normal"),
            "accept_insecure_certs": _flag("SENTINEL_ACCEPT_INSECURE_CERTS", False),
            "locale": os.getenv("SENTINEL_LOCALE") or None,
            "binary_location": os.getenv("SENTINEL_BROWSER_BINARY") or None,
            "default_timeout": _num("SENTINEL_TIMEOUT", 15.0),
            "poll_frequency": _num("SENTINEL_POLL", 0.25),
            "page_load_timeout": _num("SENTINEL_PAGE_LOAD_TIMEOUT", 45.0),
            "script_timeout": _num("SENTINEL_SCRIPT_TIMEOUT", 30.0),
            "download_timeout": _num("SENTINEL_DOWNLOAD_TIMEOUT", 120.0),
            "min_delay": _num("SENTINEL_MIN_DELAY", 0.8),
            "max_delay": _num("SENTINEL_MAX_DELAY", 2.0),
            "artifacts_root": Path(os.getenv("SENTINEL_ARTIFACTS", "artifacts")),
            "remote_url": os.getenv("SENTINEL_REMOTE_URL") or None,
            "use_local_file_detector": _flag("SENTINEL_LOCAL_FILE_DETECTOR", False),
            "capture_page_source": _flag("SENTINEL_CAPTURE_PAGE_SOURCE", False),
            "driver_log": _flag("SENTINEL_DRIVER_LOG", True),
        }
        values.update(overrides)
        return cls(**values)  # type: ignore[arg-type]

    # --- Derived, per-run paths (never shared between concurrent workers) ---

    @property
    def run_dir(self) -> Path:
        return self.artifacts_root / self.run_id

    @property
    def download_dir(self) -> Path:
        return self.run_dir / "downloads"

    @property
    def profile_dir(self) -> Path:
        return self.run_dir / "profile"

    @property
    def log_dir(self) -> Path:
        return self.run_dir / "logs"

    @property
    def evidence_dir(self) -> Path:
        return self.run_dir / "evidence"

    @property
    def data_dir(self) -> Path:
        return self.run_dir / "data"

    def prepare_dirs(self) -> "RunConfig":
        """Create the run's directory tree. Safe to call more than once."""
        for path in (
            self.run_dir,
            self.download_dir,
            self.profile_dir,
            self.log_dir,
            self.evidence_dir,
            self.data_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self
