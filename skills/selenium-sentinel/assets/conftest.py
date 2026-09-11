"""pytest fixtures for Selenium Sentinel runs.

Copy into the project's test root (or `tests/`). Gives every test an isolated
browser session, a per-test artifact namespace, and a screenshot + context
bundle written automatically when a test fails.

Requires: pytest, selenium, and the `sentinel/` package importable.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from sentinel import ArtifactStore, RunConfig, build_driver, configure_logging
from sentinel.waits import Locator  # noqa: F401 - re-exported for test modules


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--browser", default=None, help="chrome | firefox | edge")
    parser.addoption("--headed", action="store_true", help="Run with a visible browser")
    parser.addoption("--base-url", default=None, help="Base URL of the environment under test")


@pytest.fixture(scope="session")
def base_url(pytestconfig: pytest.Config) -> str:
    url = pytestconfig.getoption("--base-url")
    if not url:
        pytest.skip("--base-url is required for browser tests")
    return str(url)


@pytest.fixture
def run_config(request: pytest.FixtureRequest) -> RunConfig:
    """One config - and therefore one isolated directory tree - per test."""
    overrides: dict[str, Any] = {}
    browser = request.config.getoption("--browser")
    if browser:
        overrides["browser"] = browser
    if request.config.getoption("--headed"):
        overrides["headless"] = False
    cfg = RunConfig.from_env(**overrides).prepare_dirs()
    configure_logging(cfg)
    return cfg


@pytest.fixture
def driver(run_config: RunConfig, request: pytest.FixtureRequest) -> Iterator[WebDriver]:
    """A fresh browser per test. Teardown always runs, even on failure.

    Function scope is the default for a reason: a browser reused across tests
    carries cookies, storage and history that make failures non-reproducible.
    """
    session = build_driver(run_config)
    request.node.stash_driver = session  # type: ignore[attr-defined]
    try:
        yield session
    finally:
        session.quit()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):  # type: ignore[no-untyped-def]
    """Capture evidence at the moment a browser test fails."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    session = getattr(item, "stash_driver", None)
    cfg = item.funcargs.get("run_config") if hasattr(item, "funcargs") else None
    if session is None or cfg is None:
        return
    try:
        bundle = ArtifactStore(cfg).failure_bundle(
            session, item.name, call.excinfo.value if call.excinfo else None
        )
        report.sections.append(("Selenium evidence", str(bundle.directory)))
    except Exception:  # noqa: BLE001 - never let evidence capture hide the failure
        pass
