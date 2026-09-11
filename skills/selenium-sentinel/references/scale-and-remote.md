# Scale, Remote Execution, and BiDi

How to run more than one browser at a time without turning isolation bugs into
data-corruption bugs, and how to use the event-driven APIs when standard
WebDriver genuinely cannot answer the question.

## Before adding parallelism

Parallelism multiplies load on the target. Confirm first that the target's
owner, terms, and rate limits allow concurrent sessions. For scraping, the
default answer is **one session**: a slower single worker is almost always the
right trade against being rate-limited or blocked.

Parallelism is justified for test suites, multi-browser coverage, and jobs
against systems you operate.

## What must be unique per worker

| Resource | Why |
| --- | --- |
| Driver session | Two workers on one driver corrupt each other's context |
| Browser profile (`--user-data-dir`) | Shared profiles cause lock errors and cross-run state |
| Download directory | Otherwise workers steal each other's files |
| Artifact/evidence namespace | Otherwise the failing run's screenshot is overwritten |
| Output sink and checkpoint file | Otherwise interleaved writes corrupt the dataset |
| Account or test data partition | Otherwise tests race on the same records |

`RunConfig` derives all of these from `run_id`, so a per-worker config is the
whole isolation story.

## pytest with xdist

```bash
pytest -n 4 --browser chrome --base-url https://staging.example.test
```

With the provided `conftest.py`, every test gets a function-scoped driver and its
own `RunConfig`, which means its own profile, downloads, and evidence directory.
Do not widen the driver fixture to session scope to "speed things up" — the
saved seconds return as unreproducible failures.

## Remote WebDriver and Grid

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")
options.set_capability("se:name", "checkout-regression")      # shows in the Grid UI
options.set_capability("se:recordVideo", False)

driver = webdriver.Remote(command_executor="https://grid.example.test", options=options)
```

Or with the toolkit: `SENTINEL_REMOTE_URL=https://grid.example.test`.

Requirements:

- HTTPS and authentication on the endpoint; credentials from a secret manager,
  never in source or logs.
- W3C `Options`, not legacy `DesiredCapabilities` dictionaries.
- `driver.file_detector = LocalFileDetector()` when uploading files that exist on
  the client rather than the node (`SENTINEL_LOCAL_FILE_DETECTOR=true`).
- Downloads land **on the node**. Either use the Grid's downloadable-files API
  where the provider supports it, or design the workflow so the artifact is
  retrievable another way.
- Record `driver.session_id` in the log; it is how a node-side incident gets
  correlated afterwards.
- Bound concurrency to the Grid's capacity and the target's limits, not to your
  CPU count.

A local Grid for development:

```bash
docker run -d -p 4444:4444 --shm-size=2g selenium/standalone-chrome:latest
SENTINEL_REMOTE_URL=http://localhost:4444 python scrape_target.py --url ...
```

## Recycling long-running sessions

Browsers grow over thousands of navigations. For a job that runs for hours:

```python
for batch in batches(items, size=200):
    with driver_session(cfg) as driver:
        for item in checkpoint.pending(batch, key=lambda i: i["id"]):
            process(driver, item)
            checkpoint.mark(item["id"])
```

The checkpoint makes restarting the browser free, and it bounds the blast radius
of a crash to one batch.

## WebDriver BiDi

BiDi is the standard, cross-browser, event-driven channel. Prefer it over CDP.
It is version-sensitive: capability-detect and test on the exact matrix.

```python
options.enable_bidi = True
driver = webdriver.Chrome(options=options)
```

Legitimate uses:

- **Console and JS errors** during a run, as diagnostics attached to a failure.
- **Network observation** to confirm which request produced the data you parsed,
  or to prove a request never fired.
- **Browsing-context events** to know a navigation actually started.

Boundaries that do not move: do not intercept traffic to harvest secrets, do not
rewrite responses to bypass a client-side control, do not block requests to evade
rate limiting or metering, and do not use it to defeat bot detection.

Check whether the installed Selenium exposes the API you plan to use before
designing around it — the high-level surfaces (`script`, `network`,
`browsing_context`, `storage`, `permissions`, `emulation`, `input`) have landed
at different releases.

## CDP

Chromium-only, tied to a protocol version, and deprecated as the recommended
path. Use it only when no standard WebDriver and no BiDi route exists, isolate
it behind one module, pin Selenium and the browser, and provide a fallback that
fails clearly rather than silently.

Commonly reached for and usually unnecessary:

| CDP use | Standard alternative |
| --- | --- |
| `Page.setDownloadBehavior` | Browser download preferences in `Options` |
| `Emulation.setDeviceMetricsOverride` | `--window-size` plus a mobile emulation option |
| `Network.setExtraHTTPHeaders` | A proxy you control, or the application's own mechanism |
| `Runtime.evaluate` | `driver.execute_script` |

## Observability for scheduled jobs

A job nobody watches needs to report for itself:

- One structured line per page/item: run id, item id, duration, record count,
  outcome.
- A summary event at the end: totals, expected vs. collected, duration, exit code.
- Non-zero exit on incompleteness, not just on exceptions — a run that silently
  collected 3 of 300 records is a failure.
- Alert on the shape of the data, not only on crashes: record-count drop,
  null-rate jump, duplicate keys.
- Retain evidence bundles for failed runs only, under a retention policy, with
  access restricted — they contain screenshots of real pages.
