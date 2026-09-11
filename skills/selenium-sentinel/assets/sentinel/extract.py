"""Data extraction and normalization.

Reads structure, not pixels: rows are mapped through explicit column contracts
so a layout change fails loudly instead of silently shifting every value.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

Locator = tuple[str, str]

_WHITESPACE = re.compile(r"\s+")


def clean(value: str | None) -> str:
    """Collapse whitespace, including the non-breaking spaces tables love."""
    if not value:
        return ""
    return _WHITESPACE.sub(" ", value.replace("\xa0", " ")).strip()


def text_or_none(scope: WebElement, locator: Locator) -> str | None:
    """Text of an optional child - None when the cell is genuinely absent."""
    found = scope.find_elements(*locator)
    return clean(found[0].text) if found else None


def attr_or_none(scope: WebElement, locator: Locator, attribute: str) -> str | None:
    found = scope.find_elements(*locator)
    return found[0].get_attribute(attribute) if found else None


def required_text(scope: WebElement, locator: Locator, *, field: str) -> str:
    """Text of a child that the data contract says must exist."""
    try:
        value = clean(scope.find_element(*locator).text)
    except NoSuchElementException as exc:
        raise NoSuchElementException(
            f"required field {field!r} not found with {locator}; the row layout changed"
        ) from exc
    if not value:
        raise ValueError(f"required field {field!r} is present but empty")
    return value


def absolute(base_url: str, href: str | None) -> str | None:
    """Resolve a possibly relative href against the page URL."""
    return urljoin(base_url, href) if href else None


def to_decimal(
    value: str | None, *, decimal_sep: str = ",", thousands_sep: str = "."
) -> Decimal | None:
    """Parse a localized number. Defaults match es-ES formatting (1.234,56)."""
    if value is None:
        return None
    cleaned = clean(value)
    if not cleaned:
        return None
    cleaned = re.sub(r"[^\d\-,.\s]", "", cleaned).strip()
    if thousands_sep:
        cleaned = cleaned.replace(thousands_sep, "")
    if decimal_sep != ".":
        cleaned = cleaned.replace(decimal_sep, ".")
    cleaned = cleaned.replace(" ", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def to_date(value: str | None, *formats: str) -> date | None:
    """Parse a date against explicit formats. Never guesses day/month order."""
    if not value:
        return None
    cleaned = clean(value)
    for fmt in formats or ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def rows_to_records(
    rows: Iterable[WebElement],
    columns: Mapping[str, Locator],
    *,
    required: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Map row elements to dicts using one locator per named column.

    Columns are addressed by name, never by positional index, so an inserted
    column does not silently corrupt the dataset.
    """
    required_fields = set(required)
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        record: dict[str, Any] = {}
        for name, locator in columns.items():
            if name in required_fields:
                record[name] = required_text(row, locator, field=f"{name}[row {index}]")
            else:
                record[name] = text_or_none(row, locator)
        records.append(record)
    return records


def validate_records(
    records: list[dict[str, Any]],
    *,
    required: Iterable[str] = (),
    unique_key: str | None = None,
    minimum: int = 0,
) -> list[dict[str, Any]]:
    """Assert the dataset contract before anything is persisted downstream."""
    if len(records) < minimum:
        raise ValueError(f"expected at least {minimum} records, extracted {len(records)}")
    required_fields = list(required)
    for index, record in enumerate(records):
        missing = [field for field in required_fields if not record.get(field)]
        if missing:
            raise ValueError(f"record {index} is missing required fields: {missing}")
    if unique_key:
        keys = [record.get(unique_key) for record in records]
        duplicates = {key for key in keys if keys.count(key) > 1}
        if duplicates:
            raise ValueError(
                f"{len(duplicates)} duplicate values for {unique_key!r}; "
                "pagination probably repeated a page"
            )
    return records


def with_provenance(
    records: list[dict[str, Any]],
    *,
    source_url: str,
    run_id: str,
    extracted_at: datetime | None = None,
    parser_version: str = "1",
    extra: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Stamp each record with where, when and how it was obtained."""
    stamp = (extracted_at or datetime.now()).astimezone().isoformat()
    meta = dict(extra or {})
    return [
        {
            **record,
            "_source_url": source_url,
            "_run_id": run_id,
            "_extracted_at": stamp,
            "_parser_version": parser_version,
            **meta,
        }
        for record in records
    ]
