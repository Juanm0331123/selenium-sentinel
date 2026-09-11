"""Driver construction and lifecycle.

One owner, one session, guaranteed teardown. Options are built from RunConfig so
that browser-specific configuration stays out of workflow code.

Selenium Manager resolves the driver binary automatically; no driver-manager
dependency is used or needed.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from selenium import webdriver
from selenium.webdriver.common.options import ArgOptions

from .config import RunConfig

log = logging.getLogger("sentinel.driver")

_SUPPORTED = {"chrome", "edge", "firefox"}


def _chromium_prefs(cfg: RunConfig) -> dict[str, Any]:
    return {
        "download.default_directory": str(cfg.download_dir.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "profile.default_content_setting_values.automatic_downloads": 1,
        # Keep Safe Browsing enabled; disabling it is a security downgrade, not a fix.
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }


def _apply_common(options: ArgOptions, cfg: RunConfig) -> None:
    options.page_load_strategy = cfg.page_load_strategy
    if cfg.accept_insecure_certs:
        # Only for controlled environments with a documented reason.
        options.accept_insecure_certs = True
    if cfg.binary_location:
        options.binary_location = cfg.binary_location  # type: ignore[attr-defined]


def build_options(cfg: RunConfig) -> ArgOptions:
    """Return browser options for the configured browser.

    Every argument here has an operational reason. Do not add anti-detection,
    sandbox-disabling, or user-agent-spoofing flags by default.
    """
    width, height = cfg.window_size
    browser = cfg.browser

    if browser in {"chrome", "edge"}:
        if browser == "chrome":
            options: ArgOptions = webdriver.ChromeOptions()
        else:
            options = webdriver.EdgeOptions()
        if cfg.headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={width},{height}")
        # Per-run profile: prevents profile locks and cross-run state bleed.
        options.add_argument(f"--user-data-dir={cfg.profile_dir.resolve()}")
        if cfg.locale:
            options.add_argument(f"--lang={cfg.locale}")
        options.add_experimental_option("prefs", _chromium_prefs(cfg))  # type: ignore[attr-defined]
        options.add_experimental_option("excludeSwitches", ["enable-logging"])  # type: ignore[attr-defined]
    elif browser == "firefox":
        options = webdriver.FirefoxOptions()
        if cfg.headless:
            options.add_argument("-headless")
        # geckodriver has no portable window-size flag: set it after launch.
        options.set_preference("browser.download.folderList", 2)  # type: ignore[attr-defined]
        options.set_preference("browser.download.dir", str(cfg.download_dir.resolve()))  # type: ignore[attr-defined]
        options.set_preference("browser.download.useDownloadDir", True)  # type: ignore[attr-defined]
        options.set_preference("pdfjs.disabled", True)  # type: ignore[attr-defined]
        options.set_preference(  # type: ignore[attr-defined]
            "browser.helperApps.neverAsk.saveToDisk",
            "application/pdf,application/octet-stream,text/csv,application/zip,"
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        if cfg.locale:
            options.set_preference("intl.accept_languages", cfg.locale)  # type: ignore[attr-defined]
    else:
        raise ValueError(f"Unsupported browser {cfg.browser!r}; expected one of {sorted(_SUPPORTED)}")

    _apply_common(options, cfg)
    return options


def build_service(cfg: RunConfig):
    """Return a Service with driver logging, or None when logging is disabled."""
    if not cfg.driver_log:
        return None
    log_path = str((cfg.log_dir / f"{cfg.browser}driver.log").resolve())
    if cfg.browser == "chrome":
        from selenium.webdriver.chrome.service import Service

        return Service(log_output=log_path)
    if cfg.browser == "edge":
        from selenium.webdriver.edge.service import Service as EdgeService

        return EdgeService(log_output=log_path)
    from selenium.webdriver.firefox.service import Service as FirefoxService

    return FirefoxService(log_output=log_path)


def build_driver(cfg: RunConfig) -> webdriver.Remote:
    """Create a driver for cfg. The caller owns quit(); prefer driver_session()."""
    cfg.prepare_dirs()
    options = build_options(cfg)

    if cfg.remote_url:
        driver = webdriver.Remote(command_executor=cfg.remote_url, options=options)
        if cfg.use_local_file_detector:
            from selenium.webdriver.remote.file_detector import LocalFileDetector

            driver.file_detector = LocalFileDetector()
    else:
        service = build_service(cfg)
        factory = {
            "chrome": webdriver.Chrome,
            "edge": webdriver.Edge,
            "firefox": webdriver.Firefox,
        }[cfg.browser]
        driver = factory(options=options, service=service) if service else factory(options=options)

    if cfg.browser == "firefox":
        driver.set_window_size(*cfg.window_size)

    driver.set_page_load_timeout(cfg.page_load_timeout)
    driver.set_script_timeout(cfg.script_timeout)
    # Explicit waits only: implicit waits and explicit waits must never be mixed.
    driver.implicitly_wait(0)

    caps = getattr(driver, "capabilities", {}) or {}
    log.info(
        "driver.started",
        extra={
            "run_id": cfg.run_id,
            "browser": caps.get("browserName", cfg.browser),
            "browser_version": caps.get("browserVersion"),
            "remote": bool(cfg.remote_url),
            "session_id": getattr(driver, "session_id", None),
        },
    )
    return driver


@contextmanager
def driver_session(cfg: RunConfig) -> Iterator[webdriver.Remote]:
    """Own a driver for the duration of the block and always quit() it."""
    driver = build_driver(cfg)
    try:
        yield driver
    finally:
        try:
            driver.quit()
        except Exception:  # noqa: BLE001 - teardown must not mask the real failure
            log.warning("driver.quit_failed", extra={"run_id": cfg.run_id}, exc_info=True)
        else:
            log.info("driver.stopped", extra={"run_id": cfg.run_id})
