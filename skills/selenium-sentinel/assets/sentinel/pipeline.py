"""Run mechanics for long scrapes: output sinks, resume, pacing, bounded retry.

These are the pieces that decide whether a 4-hour job survives a restart, and
whether a failed page costs one page or the whole dataset.
"""

from __future__ import annotations

import csv
import json
import logging
import random
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

log = logging.getLogger("sentinel.pipeline")

T = TypeVar("T")


class JsonlSink:
    """Append-only JSON Lines output: crash-safe and resumable by construction."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")
        self.written = 0

    def write(self, record: Mapping[str, Any]) -> None:
        self._handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self.written += 1

    def write_all(self, records: Iterable[Mapping[str, Any]]) -> int:
        count = 0
        for record in records:
            self.write(record)
            count += 1
        self.flush()
        return count

    def flush(self) -> None:
        self._handle.flush()

    def close(self) -> None:
        self.flush()
        self._handle.close()

    def __enter__(self) -> "JsonlSink":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class CsvSink:
    """CSV output with a fixed header, written with UTF-8 BOM for Excel."""

    def __init__(self, path: Path, fieldnames: Sequence[str], *, excel_bom: bool = True) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self.path.exists() or self.path.stat().st_size == 0
        encoding = "utf-8-sig" if excel_bom else "utf-8"
        self._handle = self.path.open("a", encoding=encoding, newline="")
        self._writer = csv.DictWriter(self._handle, fieldnames=list(fieldnames), extrasaction="ignore")
        if is_new:
            self._writer.writeheader()
        self.written = 0

    def write(self, record: Mapping[str, Any]) -> None:
        self._writer.writerow(record)
        self.written += 1

    def write_all(self, records: Iterable[Mapping[str, Any]]) -> int:
        count = 0
        for record in records:
            self.write(record)
            count += 1
        self.flush()
        return count

    def flush(self) -> None:
        self._handle.flush()

    def close(self) -> None:
        self.flush()
        self._handle.close()

    def __enter__(self) -> "CsvSink":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class Checkpoint:
    """Durable set of completed work-item ids, so a restart resumes instead of repeating.

    The file is flushed after every mark, which is what makes an interrupted run
    safe to re-launch against a non-idempotent target.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.done: set[str] = set()
        if self.path.exists():
            self.done = {
                line.strip()
                for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
        self._handle = self.path.open("a", encoding="utf-8")

    def is_done(self, item_id: str) -> bool:
        return item_id in self.done

    def mark(self, item_id: str) -> None:
        if item_id in self.done:
            return
        self.done.add(item_id)
        self._handle.write(f"{item_id}\n")
        self._handle.flush()

    def pending(self, items: Iterable[T], key: Callable[[T], str]) -> Iterator[T]:
        """Yield only the items this run has not already completed."""
        for item in items:
            if not self.is_done(key(item)):
                yield item

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "Checkpoint":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class Throttle:
    """Politeness pacing between page requests.

    This is deliberate rate limiting to stay within what a target can absorb -
    not an evasion technique. Keep the delays at or above what the site's terms
    and your authorization allow, and stop entirely on 403/429-style responses.
    """

    def __init__(self, min_delay: float, max_delay: float) -> None:
        if min_delay > max_delay:
            raise ValueError("min_delay must not exceed max_delay")
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last: float | None = None

    def wait(self) -> None:
        target = random.uniform(self.min_delay, self.max_delay)
        if self._last is not None:
            elapsed = time.monotonic() - self._last
            remaining = target - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last = time.monotonic()

    def back_off(self, attempt: int, *, base: float = 2.0, cap: float = 60.0) -> None:
        """Exponential backoff with jitter after a transient failure."""
        delay = min(cap, self.max_delay * (base ** max(0, attempt - 1)))
        delay = random.uniform(delay / 2, delay)
        log.info("throttle.backoff", extra={"attempt": attempt, "delay_s": round(delay, 2)})
        time.sleep(delay)


def retry_transient(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    retry_on: tuple[type[BaseException], ...],
    throttle: Throttle | None = None,
    label: str = "operation",
) -> T:
    """Retry an *idempotent* operation a bounded number of times.

    Never wrap a submit, payment, upload, creation or deletion in this: for a
    non-idempotent action, query the authoritative state first and decide.
    """
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retry_on as exc:
            last = exc
            log.warning(
                "retry.transient_failure",
                extra={
                    "label": label,
                    "attempt": attempt,
                    "attempts": attempts,
                    "error_type": type(exc).__name__,
                },
            )
            if attempt == attempts:
                break
            if throttle is not None:
                throttle.back_off(attempt)
    assert last is not None
    raise last


@contextmanager
def step(name: str, **fields: Any) -> Iterator[None]:
    """Log the start, duration and outcome of one named workflow step."""
    started = time.monotonic()
    log.info("step.start", extra={"step": name, **fields})
    try:
        yield
    except BaseException as exc:
        log.error(
            "step.failed",
            extra={
                "step": name,
                "duration_s": round(time.monotonic() - started, 3),
                "error_type": type(exc).__name__,
                **fields,
            },
        )
        raise
    else:
        log.info(
            "step.ok",
            extra={"step": name, "duration_s": round(time.monotonic() - started, 3), **fields},
        )
