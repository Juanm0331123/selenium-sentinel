"""Explicit synchronization helpers.

Every helper waits for the precondition of the *next* action and returns the
object that action needs. No time.sleep() is used as synchronization anywhere.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from typing import Any, TypeVar

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import RunConfig

log = logging.getLogger("sentinel.waits")

Locator = tuple[str, str]
T = TypeVar("T")


def waiter(driver: WebDriver, cfg: RunConfig, timeout: float | None = None) -> WebDriverWait:
    """Build a WebDriverWait using the run's synchronization budget."""
    return WebDriverWait(
        driver,
        timeout if timeout is not None else cfg.default_timeout,
        poll_frequency=cfg.poll_frequency,
        ignored_exceptions=(StaleElementReferenceException,),
    )


def wait_until(
    driver: WebDriver,
    cfg: RunConfig,
    condition: Callable[[WebDriver], T],
    *,
    what: str,
    timeout: float | None = None,
) -> T:
    """Wait for a condition, raising a TimeoutException that says what failed."""
    try:
        return waiter(driver, cfg, timeout).until(condition)
    except TimeoutException as exc:
        budget = timeout if timeout is not None else cfg.default_timeout
        raise TimeoutException(
            f"timeout after {budget}s waiting for {what} "
            f"(url={driver.current_url!r}, title={driver.title!r})"
        ) from exc


def present(
    driver: WebDriver, cfg: RunConfig, locator: Locator, *, timeout: float | None = None
) -> WebElement:
    """Element exists in the DOM (not necessarily visible)."""
    return wait_until(
        driver,
        cfg,
        EC.presence_of_element_located(locator),
        what=f"presence of {locator}",
        timeout=timeout,
    )


def visible(
    driver: WebDriver, cfg: RunConfig, locator: Locator, *, timeout: float | None = None
) -> WebElement:
    """Element is rendered and has a non-zero size."""
    return wait_until(
        driver,
        cfg,
        EC.visibility_of_element_located(locator),
        what=f"visibility of {locator}",
        timeout=timeout,
    )


def clickable(
    driver: WebDriver, cfg: RunConfig, locator: Locator, *, timeout: float | None = None
) -> WebElement:
    """Element is visible and enabled."""
    return wait_until(
        driver,
        cfg,
        EC.element_to_be_clickable(locator),
        what=f"clickability of {locator}",
        timeout=timeout,
    )


def all_visible(
    driver: WebDriver, cfg: RunConfig, locator: Locator, *, timeout: float | None = None
) -> list[WebElement]:
    """At least one matching element is visible; returns every visible match."""
    return wait_until(
        driver,
        cfg,
        EC.visibility_of_all_elements_located(locator),
        what=f"visibility of all {locator}",
        timeout=timeout,
    )


def gone(
    driver: WebDriver, cfg: RunConfig, locator: Locator, *, timeout: float | None = None
) -> bool:
    """Element is invisible or absent - the usual 'spinner finished' signal."""
    return wait_until(
        driver,
        cfg,
        EC.invisibility_of_element_located(locator),
        what=f"disappearance of {locator}",
        timeout=timeout,
    )


def click_when_ready(
    driver: WebDriver, cfg: RunConfig, locator: Locator, *, timeout: float | None = None
) -> WebElement:
    """Click an element once it is genuinely actionable.

    One scroll-and-retry covers sticky headers and late layout shifts. It never
    falls back to a JavaScript click: an interception that survives the retry is
    a real defect (overlay, wrong frame, disabled control) and must surface.
    """
    element = clickable(driver, cfg, locator, timeout=timeout)
    try:
        element.click()
        return element
    except (ElementClickInterceptedException, ElementNotInteractableException) as first:
        log.info(
            "click.retry_after_scroll",
            extra={"locator": str(locator), "reason": type(first).__name__},
        )
        element = clickable(driver, cfg, locator, timeout=timeout)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        element = clickable(driver, cfg, locator, timeout=timeout)
        element.click()
        return element


def type_text(
    driver: WebDriver,
    cfg: RunConfig,
    locator: Locator,
    value: str,
    *,
    verify: bool = True,
    timeout: float | None = None,
) -> WebElement:
    """Clear a field, type into it, and confirm the committed value.

    Use `verify=False` for masked or auto-formatted inputs whose DOM value is
    intentionally different from what was typed. Never log `value`.
    """
    field = visible(driver, cfg, locator, timeout=timeout)
    field.clear()
    field.send_keys(value)
    if verify:
        actual = field.get_property("value")
        if actual != value:
            raise AssertionError(
                f"field {locator} did not accept the typed value "
                f"(expected {len(value)} chars, got {len(actual or '')})"
            )
    return field


def wait_until_stale(
    driver: WebDriver, cfg: RunConfig, element: WebElement, *, timeout: float | None = None
) -> bool:
    """Wait for a captured element to be detached - the AJAX re-render signal."""
    return wait_until(
        driver,
        cfg,
        EC.staleness_of(element),
        what="the previous DOM node to be replaced",
        timeout=timeout,
    )


def replaced_after(
    driver: WebDriver,
    cfg: RunConfig,
    anchor: WebElement,
    locator: Locator,
    action: Callable[[], Any],
    *,
    timeout: float | None = None,
) -> WebElement:
    """Run an action that rebuilds the DOM, then re-locate safely.

    Capture the old node, act, wait for staleness, wait for the replacement.
    This is the correct cure for StaleElementReferenceException.
    """
    action()
    wait_until_stale(driver, cfg, anchor, timeout=timeout)
    return visible(driver, cfg, locator, timeout=timeout)


def text_of(
    driver: WebDriver, cfg: RunConfig, locator: Locator, *, timeout: float | None = None
) -> str:
    """Visible, non-empty text of an element."""

    def condition(browser: WebDriver) -> str | bool:
        try:
            element = browser.find_element(*locator)
        except Exception:  # noqa: BLE001 - transient lookup while the view renders
            return False
        value = (element.text or "").strip()
        return value or False

    return wait_until(
        driver, cfg, condition, what=f"non-empty text in {locator}", timeout=timeout
    )


def count_at_least(
    driver: WebDriver,
    cfg: RunConfig,
    locator: Locator,
    minimum: int,
    *,
    timeout: float | None = None,
) -> list[WebElement]:
    """Wait until a result set has at least `minimum` rows, then return them."""

    def condition(browser: WebDriver) -> list[WebElement] | bool:
        found = browser.find_elements(*locator)
        return found if len(found) >= minimum else False

    return wait_until(
        driver, cfg, condition, what=f"at least {minimum} matches for {locator}", timeout=timeout
    )


def any_located(
    driver: WebDriver, cfg: RunConfig, locators: Sequence[Locator], *, timeout: float | None = None
) -> Locator:
    """Wait for whichever of several outcomes happens first.

    Use it for success-or-error races: it returns the locator that matched, so
    the caller branches on the real outcome instead of assuming success.
    """

    def condition(browser: WebDriver) -> Locator | bool:
        for locator in locators:
            if browser.find_elements(*locator):
                return locator
        return False

    return wait_until(driver, cfg, condition, what=f"any of {list(locators)}", timeout=timeout)


@contextmanager
def inside_frame(
    driver: WebDriver, cfg: RunConfig, locator: Locator, *, timeout: float | None = None
) -> Iterator[None]:
    """Switch into a frame for the block and always return to the top document."""
    wait_until(
        driver,
        cfg,
        EC.frame_to_be_available_and_switch_to_it(locator),
        what=f"frame {locator}",
        timeout=timeout,
    )
    try:
        yield
    finally:
        driver.switch_to.default_content()


@contextmanager
def new_window_from(
    driver: WebDriver,
    cfg: RunConfig,
    action: Callable[[], Any],
    *,
    close_after: bool = True,
    timeout: float | None = None,
) -> Iterator[str]:
    """Run an action that opens a window, work inside it, then come back.

    Handles are compared against the set known before the action, so nothing
    depends on `window_handles` ordering.
    """
    original = driver.current_window_handle
    known = set(driver.window_handles)
    action()

    def condition(browser: WebDriver) -> str | bool:
        extra = set(browser.window_handles) - known
        return next(iter(extra), False) if extra else False

    handle: str = wait_until(driver, cfg, condition, what="a new browser window", timeout=timeout)
    driver.switch_to.window(handle)
    try:
        yield handle
    finally:
        if close_after and handle in driver.window_handles:
            driver.close()
        driver.switch_to.window(original)


def accept_alert(driver: WebDriver, cfg: RunConfig, *, timeout: float | None = None) -> str:
    """Wait for an alert, return its text, and accept it."""
    alert = wait_until(driver, cfg, EC.alert_is_present(), what="a browser alert", timeout=timeout)
    message = alert.text
    alert.accept()
    return message
