"""Reference scraper: paginated listing -> validated records -> JSONL + CSV.

Adapt the LOCATORS, COLUMNS and the two workflow functions. The surrounding
structure is the part worth keeping: one driver owner, explicit waits only,
a column contract, page-by-page persistence, a checkpoint, and evidence on
failure.

Run:
    python scraper_template.py --url https://example.test/listing --max-pages 5
    SENTINEL_HEADLESS=false python scraper_template.py --url ... --max-pages 1

Only run this against a target you are authorized to automate, at a rate the
target's terms allow.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

# Make `sentinel/` importable when this file sits next to it.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sentinel import (  # noqa: E402
    ArtifactStore,
    Checkpoint,
    CsvSink,
    JsonlSink,
    RunConfig,
    Throttle,
    configure_logging,
    driver_session,
    extract,
    pagination,
    waits,
)
from sentinel.pipeline import step  # noqa: E402

log = logging.getLogger("sentinel.scraper")

# --- Locator contract -------------------------------------------------------
# One place, named by meaning, anchored to stable application attributes.

COOKIE_BANNER = (By.CSS_SELECTOR, "[data-testid='cookie-banner']")
COOKIE_ACCEPT = (By.CSS_SELECTOR, "[data-testid='cookie-accept']")
RESULTS_REGION = (By.CSS_SELECTOR, "[data-testid='results']")
RESULT_ROW = (By.CSS_SELECTOR, "[data-testid='results'] [data-testid='result-row']")
RESULT_TOTAL = (By.CSS_SELECTOR, "[data-testid='result-total']")
NEXT_PAGE = (By.CSS_SELECTOR, "[data-testid='pagination-next']")
EMPTY_STATE = (By.CSS_SELECTOR, "[data-testid='results-empty']")
ERROR_STATE = (By.CSS_SELECTOR, "[role='alert']")

# --- Column contract --------------------------------------------------------
# Named columns, not positional indexes: an inserted column fails loudly.

COLUMNS: dict[str, tuple[str, str]] = {
    "reference": (By.CSS_SELECTOR, "[data-field='reference']"),
    "title": (By.CSS_SELECTOR, "[data-field='title']"),
    "status": (By.CSS_SELECTOR, "[data-field='status']"),
    "amount": (By.CSS_SELECTOR, "[data-field='amount']"),
    "updated": (By.CSS_SELECTOR, "[data-field='updated']"),
}
REQUIRED_FIELDS = ("reference", "title")


def open_listing(driver: WebDriver, cfg: RunConfig, url: str) -> None:
    """Navigate and wait for a state that proves the listing is really ready."""
    with step("open_listing", url=url):
        driver.get(url)

        # Consent banners block clicks; dismiss through the real control only.
        if driver.find_elements(*COOKIE_BANNER):
            waits.click_when_ready(driver, cfg, COOKIE_ACCEPT)
            waits.gone(driver, cfg, COOKIE_BANNER)

        # Race the three real outcomes instead of assuming success.
        outcome = waits.any_located(driver, cfg, [RESULT_ROW, EMPTY_STATE, ERROR_STATE])
        if outcome == ERROR_STATE:
            raise RuntimeError(f"listing returned an error state: {waits.text_of(driver, cfg, ERROR_STATE)}")
        if outcome == EMPTY_STATE:
            log.info("listing.empty", extra={"url": url})


def expected_total(driver: WebDriver, cfg: RunConfig) -> int | None:
    """Read the site's own record count - the completeness oracle for the run."""
    if not driver.find_elements(*RESULT_TOTAL):
        return None
    return pagination.total_from_label(waits.text_of(driver, cfg, RESULT_TOTAL))


def extract_page(driver: WebDriver, page: int, rows: list[WebElement]) -> list[dict[str, Any]]:
    """Map one page of row elements to validated, provenance-stamped records."""
    records = extract.rows_to_records(rows, COLUMNS, required=REQUIRED_FIELDS)
    for record in records:
        record["amount"] = extract.to_decimal(record.get("amount"))
        record["updated"] = extract.to_date(record.get("updated"), "%d/%m/%Y")
    extract.validate_records(records, required=REQUIRED_FIELDS, unique_key="reference", minimum=1)
    return extract.with_provenance(
        records,
        source_url=driver.current_url,
        run_id=RUN_ID,
        extra={"_page": page},
    )


def scrape(url: str, max_pages: int, cfg: RunConfig) -> int:
    """Harvest the listing into per-run JSONL and CSV. Returns the record count."""
    store = ArtifactStore(cfg)
    throttle = Throttle(cfg.min_delay, cfg.max_delay)
    jsonl_path = cfg.data_dir / "records.jsonl"
    csv_path = cfg.data_dir / "records.csv"
    fieldnames = [*COLUMNS, "_source_url", "_run_id", "_extracted_at", "_parser_version", "_page"]

    total_written = 0
    with driver_session(cfg) as driver:
        try:
            open_listing(driver, cfg, url)
            announced = expected_total(driver, cfg)
            log.info("listing.ready", extra={"expected_total": announced})

            pages = pagination.paginate_by_click(
                driver,
                cfg,
                rows_locator=RESULT_ROW,
                next_locator=NEXT_PAGE,
                max_pages=max_pages,
                throttle=throttle,
            )

            with JsonlSink(jsonl_path) as jsonl, CsvSink(csv_path, fieldnames) as csv_sink, Checkpoint(
                cfg.data_dir / "pages.done"
            ) as checkpoint:

                def persist(page: int, records: list[dict[str, Any]]) -> None:
                    nonlocal total_written
                    jsonl.write_all(records)
                    csv_sink.write_all(records)
                    checkpoint.mark(f"page:{page}")
                    total_written += len(records)

                pagination.harvest(
                    pages,
                    lambda page, rows: extract_page(driver, page, rows),
                    on_page=persist,
                )

            if announced is not None and total_written < announced:
                log.warning(
                    "listing.incomplete",
                    extra={"collected": total_written, "expected": announced},
                )
        except (TimeoutException, WebDriverException, AssertionError, ValueError) as exc:
            store.failure_bundle(driver, "scrape", exc)
            raise

    log.info(
        "scrape.finished",
        extra={"records": total_written, "jsonl": str(jsonl_path), "csv": str(csv_path)},
    )
    return total_written


def main() -> int:
    parser = argparse.ArgumentParser(description="Selenium Sentinel listing scraper template")
    parser.add_argument("--url", required=True, help="Listing URL you are authorized to scrape")
    parser.add_argument("--max-pages", type=int, default=10, help="Hard page budget for the run")
    parser.add_argument("--browser", default=None, choices=["chrome", "firefox", "edge"])
    args = parser.parse_args()

    overrides: dict[str, Any] = {}
    if args.browser:
        overrides["browser"] = args.browser
    cfg = RunConfig.from_env(**overrides).prepare_dirs()

    global RUN_ID
    RUN_ID = cfg.run_id
    configure_logging(cfg)
    log.info("run.start", extra={"url": args.url, "max_pages": args.max_pages, "artifacts": str(cfg.run_dir)})

    try:
        count = scrape(args.url, args.max_pages, cfg)
    except Exception as exc:  # noqa: BLE001 - top-level boundary: report, then fail
        log.error("run.failed", extra={"error_type": type(exc).__name__}, exc_info=True)
        return 1
    return 0 if count else 2


RUN_ID = ""

if __name__ == "__main__":
    raise SystemExit(main())
