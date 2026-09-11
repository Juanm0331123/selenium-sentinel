"""Download verification.

WebDriver has no portable "download finished" event, so completion is proven on
the filesystem: the partial file disappears, the final file stops growing, and
its name, size and (optionally) magic bytes match what was expected.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("sentinel.downloads")

# Partial-download markers by browser family.
PARTIAL_SUFFIXES = (".crdownload", ".part", ".tmp", ".partial", ".download")

# Magic bytes for the file types a scraper usually receives.
MAGIC = {
    ".pdf": b"%PDF-",
    ".zip": b"PK\x03\x04",
    ".xlsx": b"PK\x03\x04",
    ".docx": b"PK\x03\x04",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".gz": b"\x1f\x8b",
}


@dataclass(frozen=True)
class DownloadedFile:
    path: Path
    size: int
    sha256: str


def _candidates(download_dir: Path, pattern: str, known: frozenset[Path]) -> list[Path]:
    matches = []
    for entry in download_dir.iterdir():
        if not entry.is_file() or entry in known:
            continue
        if entry.suffix.lower() in PARTIAL_SUFFIXES:
            continue
        if fnmatch.fnmatch(entry.name, pattern):
            matches.append(entry)
    return matches


def snapshot(download_dir: Path) -> frozenset[Path]:
    """Record the files present before triggering a download."""
    download_dir.mkdir(parents=True, exist_ok=True)
    return frozenset(entry for entry in download_dir.iterdir() if entry.is_file())


def sha256_of(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wait_for_download(
    download_dir: Path,
    *,
    pattern: str = "*",
    timeout: float = 120.0,
    poll: float = 0.5,
    stable_for: float = 1.0,
    before: frozenset[Path] | None = None,
    min_size: int = 1,
    check_magic: bool = True,
) -> DownloadedFile:
    """Block until exactly one new, complete file matching `pattern` exists.

    `before` is the snapshot() taken prior to the trigger; it keeps files from
    earlier runs out of the result. Raises TimeoutError with the directory
    listing when nothing completes in time.
    """
    download_dir = Path(download_dir)
    known = before if before is not None else frozenset()
    deadline = time.monotonic() + timeout
    stable_since: float | None = None
    last_size = -1
    chosen: Path | None = None

    while time.monotonic() < deadline:
        partials = [
            entry
            for entry in download_dir.iterdir()
            if entry.is_file() and entry.suffix.lower() in PARTIAL_SUFFIXES
        ]
        matches = _candidates(download_dir, pattern, known)

        if matches and not partials:
            chosen = max(matches, key=lambda item: item.stat().st_mtime)
            size = chosen.stat().st_size
            if size >= min_size and size == last_size:
                stable_since = stable_since or time.monotonic()
                if time.monotonic() - stable_since >= stable_for:
                    break
            else:
                stable_since = None
            last_size = size
        time.sleep(poll)  # filesystem polling, not UI synchronization
    else:
        listing = sorted(entry.name for entry in download_dir.iterdir())
        raise TimeoutError(
            f"no completed download matching {pattern!r} in {download_dir} after {timeout}s; "
            f"directory currently holds {listing}"
        )

    assert chosen is not None
    if check_magic:
        expected = MAGIC.get(chosen.suffix.lower())
        if expected:
            with chosen.open("rb") as handle:
                head = handle.read(len(expected))
            if head != expected:
                raise ValueError(
                    f"{chosen.name} does not start with the expected {chosen.suffix} signature; "
                    "the server may have returned an HTML error page"
                )

    result = DownloadedFile(path=chosen, size=chosen.stat().st_size, sha256=sha256_of(chosen))
    log.info(
        "download.verified",
        extra={"file": chosen.name, "size": result.size, "sha256": result.sha256},
    )
    return result
