"""Pagination strategies with hard bounds.

Every strategy terminates: a page budget, an end condition, and a guard against
the same page being harvested twice. No `while True`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import Any

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from . import waits
from .config import RunConfig
from .pipeline import Throttle

log = logging.getLogger("sentinel.pagination")

Locator = tuple[str, str]


def paginate_by_click(
    driver: WebDriver,
    cfg: RunConfig,
    *,
    rows_locator: Locator,
    next_locator: Locator,
    max_pages: int,
    throttle: Throttle | None = None,
    stop_when: Callable[[list[WebElement]], bool] | None = None,
) -> Iterator[tuple[int, list[WebElement]]]:
    """Yield (page_number, row_elements) for a "Next" button that re-renders rows.

    The anchor row is captured before the click and its staleness proves the new
    page actually rendered - the reliable alternative to sleeping after a click.
    """
    for page in range(1, max_pages + 1):
        rows = waits.count_at_least(driver, cfg, rows_locator, 1)
        yield page, rows

        if stop_when is not None and stop_when(rows):
            log.info("pagination.stop_condition", extra={"page": page})
            return
        if page == max_pages:
            log.warning("pagination.budget_exhausted", extra={"pages": max_pages})
            return

        next_buttons = driver.find_elements(*next_locator)
        if not next_buttons or not next_buttons[0].is_enabled():
            log.info("pagination.last_page", extra={"page": page})
            return

        anchor = rows[0]
        try:
            waits.click_when_ready(driver, cfg, next_locator)
            waits.wait_until_stale(driver, cfg, anchor)
        except TimeoutException:
            log.info("pagination.no_rerender", extra={"page": page})
            return
        if throttle is not None:
            throttle.wait()


def paginate_by_url(
    driver: WebDriver,
    cfg: RunConfig,
    *,
    url_for_page: Callable[[int], str],
    rows_locator: Locator,
    max_pages: int,
    first_page: int = 1,
    throttle: Throttle | None = None,
) -> Iterator[tuple[int, list[WebElement]]]:
    """Yield (page_number, rows) for a paginated URL scheme.

    Stops on the first page that renders no rows, and never exceeds max_pages.
    Prefer this over clicking when the site exposes stable page URLs: it is
    restartable and each page is independently reproducible.
    """
    for page in range(first_page, first_page + max_pages):
        url = url_for_page(page)
        driver.get(url)
        try:
            rows = waits.count_at_least(driver, cfg, rows_locator, 1)
        except TimeoutException:
            log.info("pagination.empty_page", extra={"page": page, "url": url})
            return
        yield page, rows
        if throttle is not None:
            throttle.wait()
    log.warning("pagination.budget_exhausted", extra={"pages": max_pages})


def scroll_until_loaded(
    driver: WebDriver,
    cfg: RunConfig,
    *,
    rows_locator: Locator,
    max_scrolls: int = 50,
    expected_total: int | None = None,
) -> list[WebElement]:
    """Drive an infinite-scroll list until the row count stops growing.

    Bounded by max_scrolls and by an optional expected_total from the page's own
    "N results" label, which is the authoritative completeness check.
    """
    previous = 0
    for attempt in range(1, max_scrolls + 1):
        rows = driver.find_elements(*rows_locator)
        current = len(rows)
        if expected_total is not None and current >= expected_total:
            log.info("scroll.complete", extra={"rows": current, "expected": expected_total})
            return rows
        if current == previous and attempt > 1:
            log.info("scroll.settled", extra={"rows": current, "scrolls": attempt})
            return rows
        previous = current
        if rows:
            driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", rows[-1])
        try:
            waits.count_at_least(driver, cfg, rows_locator, current + 1, timeout=cfg.default_timeout / 2)
        except TimeoutException:
            log.info("scroll.no_growth", extra={"rows": current})
            return driver.find_elements(*rows_locator)
    log.warning("scroll.budget_exhausted", extra={"scrolls": max_scrolls})
    return driver.find_elements(*rows_locator)


def total_from_label(text: str) -> int | None:
    """Pull the record count out of a 'Showing 1-20 of 348 results' label."""
    import re

    numbers = [int(match.replace(".", "").replace(",", "")) for match in re.findall(r"[\d.,]+", text)]
    return max(numbers) if numbers else None


def harvest(
    pages: Iterator[tuple[int, list[WebElement]]],
    extract_page: Callable[[int, list[WebElement]], list[dict[str, Any]]],
    *,
    on_page: Callable[[int, list[dict[str, Any]]], None] | None = None,
) -> list[dict[str, Any]]:
    """Run an extractor over a page iterator, persisting incrementally.

    `on_page` is where the sink write and checkpoint mark belong: results are
    durable page by page, so an interruption never loses the whole run.
    """
    collected: list[dict[str, Any]] = []
    for page, rows in pages:
        records = extract_page(page, rows)
        collected.extend(records)
        log.info("pagination.page_harvested", extra={"page": page, "records": len(records)})
        if on_page is not None:
            on_page(page, records)
    return collected
