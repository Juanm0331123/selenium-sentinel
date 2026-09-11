# Sentinel Toolkit

Drop-in Python package that makes the correct Selenium defaults the easy ones.
It wraps nothing: the object you get is the real `selenium.webdriver` driver,
so every official API stays available.

## Install into a project

```bash
cp -r skills/selenium-sentinel/assets/sentinel <project>/src/sentinel
cp skills/selenium-sentinel/assets/scraper_template.py <project>/scrape_<target>.py
```

On Windows PowerShell:

```powershell
Copy-Item -Recurse skills\selenium-sentinel\assets\sentinel <project>\src\sentinel
```

Requires `selenium>=4.30` and Python 3.10+. Nothing else.

Copy only what the project needs. A one-page read-only scrape may need just
`config.py`, `driver.py` and `waits.py`; do not import the whole package to use
two helpers.

## Modules

| Module | Responsibility |
| --- | --- |
| `config.py` | `RunConfig`: one immutable description of a run, `from_env()`, per-run directory tree (profile, downloads, logs, evidence, data). |
| `driver.py` | `build_options`, `build_driver`, `driver_session` context manager with guaranteed `quit()`. Chrome, Edge, Firefox, and Remote/Grid. |
| `waits.py` | Explicit waits only: `visible`, `clickable`, `gone`, `click_when_ready`, `type_text`, `wait_until_stale`, `replaced_after`, `any_located`, `count_at_least`, `inside_frame`, `new_window_from`, `accept_alert`. |
| `pagination.py` | Bounded `paginate_by_click`, `paginate_by_url`, `scroll_until_loaded`, `harvest`. No unbounded loops. |
| `extract.py` | Column contracts, localized number/date parsing, dataset validation, provenance stamping. |
| `downloads.py` | Filesystem-level proof that a download actually completed: partial-file wait, size stability, magic bytes, SHA-256. |
| `artifacts.py` | `ArtifactStore.failure_bundle()`: screenshot + sanitized context JSON, with `redact()` applied to everything written. |
| `logging_setup.py` | Redacting JSON-lines logging, one file per run. |
| `pipeline.py` | `JsonlSink`, `CsvSink`, `Checkpoint` (resume), `Throttle` (politeness + backoff), `retry_transient`, `step`. |

## Environment variables

Every `SENTINEL_*` variable maps to a `RunConfig` field, so the same code runs
headed locally and headless in CI without edits:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SENTINEL_BROWSER` | `chrome` | `chrome`, `firefox`, or `edge` |
| `SENTINEL_HEADLESS` | `true` | `false` to watch the run while debugging |
| `SENTINEL_WINDOW_SIZE` | `1440x1200` | Deterministic viewport for responsive layouts |
| `SENTINEL_TIMEOUT` | `15` | Default explicit-wait budget, seconds |
| `SENTINEL_POLL` | `0.25` | Wait poll frequency |
| `SENTINEL_PAGE_LOAD_TIMEOUT` | `45` | `set_page_load_timeout` |
| `SENTINEL_DOWNLOAD_TIMEOUT` | `120` | Download completion budget |
| `SENTINEL_MIN_DELAY` / `SENTINEL_MAX_DELAY` | `0.8` / `2.0` | Throttle window between pages |
| `SENTINEL_ARTIFACTS` | `artifacts` | Root of the per-run directory tree |
| `SENTINEL_REMOTE_URL` | unset | Grid / remote endpoint |
| `SENTINEL_LOCAL_FILE_DETECTOR` | `false` | Uploads from the client to a remote node |
| `SENTINEL_CAPTURE_PAGE_SOURCE` | `false` | Opt-in only: page source often carries private data |
| `SENTINEL_DRIVER_LOG` | `true` | Write the driver log under the run's `logs/` |

## Files

- `scraper_template.py` — end-to-end paginated listing scrape: locator contract,
  column contract, validation, JSONL + CSV sinks, checkpoint, failure evidence.
- `conftest.py` — pytest fixtures: isolated driver per test, per-test artifact
  namespace, automatic evidence bundle on failure, `--browser/--headed/--base-url`.
- `requirements.txt` — the only dependency is Selenium.

## Output layout

```text
artifacts/<run_id>/
├── data/        records.jsonl, records.csv, pages.done (checkpoint)
├── downloads/   isolated per run; never shared between workers
├── evidence/    failure screenshots + sanitized context JSON
├── logs/        run.jsonl (structured, redacted) + <browser>driver.log
└── profile/     fresh browser profile; deleted with the run
```

Add `artifacts/` to `.gitignore`. Evidence and downloads are potentially
sensitive: apply the project's retention policy to the whole tree.

## Boundaries

The toolkit contains no anti-detection, fingerprint-spoofing, CAPTCHA-solving,
or rate-limit-evasion code, and it will not be extended with any. `Throttle`
exists to stay **within** a target's limits, not to slip past them.
