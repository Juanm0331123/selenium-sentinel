# Browser, Options, and Environment Matrix

Browser configuration is environment configuration. Keep it in one place, give
every non-default flag an operational reason, and test the browser you actually
deploy.

## Options by browser

| Concern | Chrome / Edge (Chromium) | Firefox |
| --- | --- | --- |
| Headless | `--headless=new` | `-headless` |
| Window size | `--window-size=W,H` | `driver.set_window_size(W, H)` after launch |
| Isolated profile | `--user-data-dir=<per-run path>` | a fresh profile is created per session by default |
| Language | `--lang=es-ES` | pref `intl.accept_languages` |
| Downloads | `prefs`: `download.default_directory`, `download.prompt_for_download=False` | prefs `browser.download.folderList=2`, `browser.download.dir`, `browser.helperApps.neverAsk.saveToDisk` |
| PDF inline vs. download | `plugins.always_open_pdf_externally=True` | `pdfjs.disabled=True` |
| Driver log | `Service(log_output=...)` | `Service(log_output=...)` |
| Console logs | `driver.get_log("browser")` | not supported — use BiDi |

`sentinel/driver.py` implements all of the above from one `RunConfig`.

## Flags that are usually wrong

| Flag | Why people add it | What to do instead |
| --- | --- | --- |
| `--no-sandbox` | Chrome fails to start in a container | Fix the container (run as a non-root user with proper caps); use it only when the image genuinely cannot provide a sandbox, and document that |
| `--disable-dev-shm-usage` | Chrome crashes in Docker | Correct in Docker with a small `/dev/shm`; better, run the container with `--shm-size=2g` |
| `--disable-gpu` | Legacy headless requirement | Not needed with `--headless=new` |
| `--disable-blink-features=AutomationControlled`, custom user agents, `excludeSwitches: enable-automation` | To look less like automation | Out of scope. If a site does not want automated access, that is an authorization question, not a flag question |
| `--ignore-certificate-errors` | A test environment has a self-signed cert | `options.accept_insecure_certs = True`, only in that environment |
| `--start-maximized` | Reproducing a local view | Set an explicit window size; maximized is non-deterministic across machines |

## Page load strategy

| Strategy | `driver.get()` returns when | Use when |
| --- | --- | --- |
| `normal` (default) | `load` event fired | Default; correct for nearly everything |
| `eager` | DOM ready, subresources may still load | Heavy pages whose images/ads you do not need — you already wait for content markers explicitly |
| `none` | Immediately after navigation starts | Only with a fully explicit readiness model; easy to get wrong |

`eager` and `none` are safe **only** because you wait for a content marker
afterwards. Without explicit waits they just move the race.

## Windows notes

- Use `Path` and `.resolve()`; pass `str(path)` to Selenium. Backslashes in raw
  strings, never hand-built `"a\\b"` concatenation.
- Antivirus scans downloaded files; a file can appear with its final name before
  scanning completes. The size-stability check in `downloads.wait_for_download`
  covers this — do not reduce `stable_for` below ~1s on Windows.
- `--user-data-dir` under a OneDrive-synced folder causes profile-lock and
  performance problems. Keep `SENTINEL_ARTIFACTS` on a local, non-synced path.
- Chrome and Edge auto-update silently. When a job breaks overnight with
  `SessionNotCreatedException`, check the browser version first.
- Long paths: keep the artifacts root short (`C:\runs\...`) for deep download
  trees.
- Set env vars for one run in PowerShell with `$env:SENTINEL_HEADLESS="false"`.

## Linux containers

Minimum viable image checklist:

- The browser and its runtime libraries (fonts included — missing fonts change
  layout and break text assertions).
- A non-root user with a writable home, profile, and download directory.
- `--shm-size=2g` (or `--disable-dev-shm-usage` if you cannot change the run).
- A `HEALTHCHECK` that runs `selenium_doctor.py --launch`.
- Time zone and locale set explicitly; both affect rendered dates and numbers.

Pin the browser version in the image. "Latest" is a moving dependency that will
break a scheduled job at an unpredictable moment.

## Headless vs. headed

Headless is not a different browser, but it is a different environment: no
window manager, a default viewport, different device pixel ratio, and some
permission prompts behave differently. Rules:

- Develop and debug headed, run scheduled jobs headless.
- Set the window size explicitly in both, to the same value.
- If a workflow only passes headed, that is a finding (usually a viewport or
  timing dependency), not a reason to stop using headless.

## Selenium Manager

Selenium Manager resolves the driver automatically; no `webdriver-manager`
dependency is needed or wanted. It is version-sensitive, so verify behaviour
against the installed Selenium release.

Relevant environment variables:

| Variable | Purpose |
| --- | --- |
| `SE_AVOID_STATS=true` | Disables its usage-statistics request |
| `SE_CACHE_PATH` | Relocate the driver cache (useful in CI) |
| `SE_OFFLINE=true` | Forbid downloads; use only the cache |
| `SE_CHROMEDRIVER` / `SE_GECKODRIVER` / `SE_EDGEDRIVER` | Point at a pre-provisioned driver binary |
| `HTTPS_PROXY` | Required when a corporate proxy sits in front of the download |

In an air-gapped or locked-down environment, pre-provision drivers in the image,
set `SE_OFFLINE=true`, and pin both browser and driver.

## Timeouts worth setting explicitly

| Setting | Default | When to change |
| --- | --- | --- |
| `set_page_load_timeout` | 300s | Almost always lower it (30–60s) so a hung navigation fails fast |
| `set_script_timeout` | 30s | Raise only for a genuinely long async script |
| `implicitly_wait` | 0 | Keep at 0. Mixing implicit and explicit waits produces undefined combined behaviour |
| `WebDriverWait` timeout | per call | Per-condition budget; tune the specific one, not the global default |
