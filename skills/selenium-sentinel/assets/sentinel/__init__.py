"""Selenium Sentinel toolkit.

A small, dependency-free layer over the official Selenium Python API that makes
the defaults correct: isolated sessions, explicit waits, verified outcomes,
redacted evidence, bounded pagination, and resumable output.

Copy the `sentinel/` package into a project and import what the workflow needs.
It adds no abstraction over WebDriver itself - the driver object is always the
real `selenium.webdriver` driver.

    from sentinel import RunConfig, driver_session, waits

    cfg = RunConfig.from_env(headless=True)
    with driver_session(cfg) as driver:
        driver.get("https://example.test")
        waits.click_when_ready(driver, cfg, (By.CSS_SELECTOR, "[data-testid='search']"))
"""

from __future__ import annotations

from . import extract, pagination, pipeline, waits
from .artifacts import ArtifactStore, redact
from .config import RunConfig
from .downloads import DownloadedFile, snapshot, wait_for_download
from .driver import build_driver, build_options, driver_session
from .logging_setup import configure_logging
from .pipeline import Checkpoint, CsvSink, JsonlSink, Throttle, retry_transient, step

__all__ = [
    "ArtifactStore",
    "Checkpoint",
    "CsvSink",
    "DownloadedFile",
    "JsonlSink",
    "RunConfig",
    "Throttle",
    "build_driver",
    "build_options",
    "configure_logging",
    "driver_session",
    "extract",
    "pagination",
    "pipeline",
    "redact",
    "retry_transient",
    "snapshot",
    "step",
    "wait_for_download",
    "waits",
]

__version__ = "1.1.0"
