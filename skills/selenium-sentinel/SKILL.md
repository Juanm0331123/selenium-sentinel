---
name: selenium-sentinel
description: Design, implement, debug, review, and harden authorized Python Selenium WebDriver automation, scraping, and browser tests. Ships a drop-in toolkit (isolated sessions, explicit waits, bounded pagination, verified downloads, resumable output, redacted evidence), an environment doctor, and playbooks. Use for Selenium scraping, form workflows, browser interaction, WebDriver errors, flaky waits, locators, downloads, uploads, sessions, Grid, Remote WebDriver, BiDi, or browser diagnostics.
---

# Selenium Sentinel

Build Selenium Python automation that is observable, deterministic, secure, and
safe to operate. Favor the smallest correct WebDriver workflow over
abstractions, retries, or browser workarounds.

This skill applies to authorized browser automation and testing only. Never
bypass CAPTCHAs, bot detection, MFA, rate limits, paywalls, access controls,
authentication, or authorization boundaries. Do not automate a state-changing
production action — submission, payment, upload, deletion, external integration
— merely to validate code unless the user explicitly authorizes it.

## Bundled Resources

Load a reference when the work reaches it; do not read them all up front.

| Resource | Use it for |
| --- | --- |
| `scripts/selenium_doctor.py` | **Run first on any Selenium task.** Reports Python, Selenium, Selenium Manager, installed browsers/versions, proxy and `SE_*` env. `--launch` starts and quits a real headless session. |
| `assets/sentinel/` | Drop-in toolkit: `RunConfig`, `driver_session`, `waits`, `pagination`, `extract`, `downloads`, `artifacts`, `pipeline` (sinks, checkpoint, throttle, bounded retry). See `assets/README.md`. |
| `assets/scraper_template.py` | Working paginated-scrape skeleton: locator contract, column contract, validation, JSONL+CSV, checkpoint, failure evidence. |
| `assets/conftest.py` | pytest fixtures: isolated driver per test, per-test artifacts, automatic evidence bundle on failure. |
| `references/recipes.md` | Verified patterns: staleness after click, outcome races, iframes, new tabs, shadow DOM, uploads, downloads, hover, drag, login, screenshots, PDF. |
| `references/scraping-playbook.md` | End-to-end scrape procedure: tool choice, authorization, recon, data contract, pagination strategies, completeness verification, maintenance. |
| `references/troubleshooting.md` | Exception-by-exception diagnosis: cause, discriminating check, real fix. |
| `references/browser-environments.md` | Options/prefs per browser, flags that are usually wrong, page load strategy, Windows and container notes, Selenium Manager env vars, timeouts. |
| `references/scale-and-remote.md` | Parallelism isolation rules, xdist, Remote/Grid, session recycling, BiDi vs CDP, scheduled-job observability. |
| `references/official-python-api-coverage.md` | Coverage map of the public Selenium Python API. Read before using an unfamiliar API, browser-specific capability, BiDi, CDP, Grid, FedCM, virtual authenticator, or download feature. |

Official sources: [Python API](https://www.selenium.dev/selenium/docs/api/py/api.html) ·
[package guide](https://www.selenium.dev/selenium/docs/api/py/) ·
[WebDriver docs](https://www.selenium.dev/documentation/webdriver/) ·
[Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/) ·
[BiDi](https://www.selenium.dev/documentation/webdriver/bidi/) ·
[Grid](https://www.selenium.dev/documentation/grid/) ·
[source](https://github.com/SeleniumHQ/selenium/tree/trunk/py)

## Operating Loop

Work through these phases in order. Skipping recon is the single most common
cause of a broken Selenium change.

### 0. Triage

Establish the facts that change the design. Resolve them from the repository and
environment where possible; ask only what you genuinely cannot determine.

| Area | Determine |
| --- | --- |
| Intent | Scraping, read-only extraction, UI test, authorized workflow, regression, or defect diagnosis |
| Risk | Whether any path can submit, issue, upload, delete, pay, alter data, or expose personal/confidential data |
| Runtime | Python, Selenium, browser and version, OS, container/CI/VM, local vs. remote |
| Target | URL/environment, auth method, dynamic rendering, iframes, shadow DOM, windows, alerts |
| Existing design | Driver creation, selectors, wait policy, error handling, artifacts, logging, test runner, secrets source |
| Success | The exact observable condition that proves the operation completed |
| Constraints | Authorization, terms, rate limits, account scope, allowed data, retention, deployment limits |

Then: read the repository instructions and existing Selenium configuration;
identify the installed `selenium` version from the manifest or environment and
match the code to **that** version; run `scripts/selenium_doctor.py`. Prefer a
non-production environment, read-only account, test record, or dry-run path
whenever one exists.

### 1. Reconnaissance

Inspect the real DOM and real behavior before writing or changing selectors and
timing. Never infer selectors from a screenshot or from prose alone. Run headed
while investigating. Settle: what proves readiness, where the iframes and shadow
roots are, how pagination works, which selectors are stable, what the failure
states look like. Details in `references/scraping-playbook.md` (Phase 2).

### 2. Contracts

Write down, in one module: the **locator contract** (named locators) and — for
extraction — the **column contract** (field → locator), required fields, unique
key, locale parsing rules, and the completeness oracle. A contract turns a
silent site change into a loud failure.

### 3. Build

Smallest structure that is clear and maintainable (see the architecture table
below). Use the toolkit when it fits; use plain Selenium when three helpers is
all the project needs.

### 4. Verify

Verify the **outcome**, not the absence of an exception. A click that returned is
not a saved record; a finished run is not a complete dataset. Check the
authoritative signal: URL, confirmation element, persisted row, downloaded file's
bytes, record count against the announced total.

### 5. Report

State exactly what was verified and on which browser/runtime, what was not run
and why, and any version-sensitive or environment-specific behavior — without
exposing secrets.

## Non-Negotiables

- Fresh, isolated browser profile and driver session per independent unit of work.
- Exactly one owner per driver, with `quit()` guaranteed by `finally`, a fixture,
  or a context manager.
- Explicit waits for a specific state. `time.sleep()` is never synchronization.
- Implicit wait stays at `0`. Never mix implicit and explicit waits.
- Wait for the state the **next action** needs, not merely for DOM presence.
- Re-locate elements after navigation, refresh, AJAX replacement, or frame/window
  change. Never hold a WebElement across a DOM rebuild.
- Every wait, retry, loop, and pagination run has a hard bound.
- Retry only demonstrably transient **and idempotent** operations. Never retry a
  submission, payment, creation, deletion, or upload blindly.
- Capture redacted evidence at failure boundaries; never log credentials,
  cookies, tokens, full sensitive page source, or private form values.
- Prefer standard WebDriver. JavaScript, CDP, and BiDi require a documented,
  browser-supported need that standard WebDriver cannot meet.

## Quick Start

With the toolkit (recommended for anything beyond a one-off):

```python
from selenium.webdriver.common.by import By
from sentinel import RunConfig, configure_logging, driver_session, waits

RESULTS = (By.CSS_SELECTOR, "[data-testid='results'] [data-testid='row']")

cfg = RunConfig.from_env(headless=True).prepare_dirs()
configure_logging(cfg)

with driver_session(cfg) as driver:
    driver.get("https://example.test/listing")
    rows = waits.count_at_least(driver, cfg, RESULTS, 1)
    data = [row.text for row in rows]
```

Plain Selenium, same discipline:

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,1200")

driver = webdriver.Chrome(options=options)
try:
    driver.implicitly_wait(0)
    driver.set_page_load_timeout(45)
    driver.get("https://example.test/listing")
    wait = WebDriverWait(driver, 15, poll_frequency=0.25)
    rows = wait.until(EC.visibility_of_all_elements_located(
        (By.CSS_SELECTOR, "[data-testid='row']")
    ))
finally:
    driver.quit()
```

## Architecture Selection

| Situation | Preferred structure |
| --- | --- |
| One small, stable read-only task | One focused workflow with local selectors and explicit waits |
| Several flows on one application | Feature/page modules with selectors and named operations |
| UI test suite | Test-framework fixtures plus page/feature objects where reuse justifies them |
| Production browser bot | Separate config, driver lifecycle, workflow operations, persistence boundary, artifact management |
| Multiple browsers/OSs or parallel workers | Capability-driven driver factory plus isolated Remote/Grid sessions |

Do not force a Page Object Model into a small bot. Where Page Objects exist, they
expose meaningful application operations and state checks — not a wrapper around
every WebElement method. Preserve the repository's architecture, logging,
configuration, test framework, and deployment model; do not introduce Page
Objects, pytest, Grid, helpers, retries, or third-party packages the project does
not need.

For scrapers, first determine whether an authorized API, export, or static HTTP
response is available. Selenium is appropriate when browser rendering,
authenticated UI behavior, or real interaction is required — not because it is
familiar. See `references/scraping-playbook.md` Phase 0.

## Session And Lifecycle

Selenium Manager resolves a compatible driver automatically; do not add
`webdriver-manager` unless the deployment specifically needs it. Pin browser and
Selenium versions where reproducibility matters.

Configure only what the environment requires. Do not cargo-cult `--no-sandbox`,
`--disable-dev-shm-usage`, anti-detection flags, custom user agents, or insecure
flags — every non-default argument needs an operational reason. Give each
session a unique profile and download directory; never share them between
concurrent drivers. Keep driver logs out of source control.

`quit()` ends the session and closes every window. Use `close()` only when the
workflow deliberately closes the current tab and knows which context remains. A
failure must not leak a browser, profile lock, download directory, or remote
session.

`assets/sentinel/driver.py` implements this for Chrome, Edge, Firefox, and
Remote. Per-browser options, container and Windows specifics, page load
strategy, and Selenium Manager configuration: `references/browser-environments.md`.

## Locators

```python
from selenium.webdriver.common.by import By

USERNAME = (By.NAME, "username")
SUBMIT = (By.CSS_SELECTOR, "form[data-flow='sign-in'] button[type='submit']")
STATUS = (By.XPATH, "//section[@aria-label='Result']//span[@data-status]")
```

Preference order, subject to target stability:

1. Stable application-owned semantic attribute: `data-testid`, `data-qa`, `name`,
   `aria-label`, a non-generated id.
2. Short CSS anchored to a stable semantic container.
3. Concise XPath for relationships CSS cannot express.
4. Link text only when the text is stable, unique, and part of the contract.
5. Relative locators last — layout changes break them.

Avoid absolute/positional XPath, chains of anonymous `div`s, generated class
names and randomized ids, translated display text, and JavaScript lookups where
an ordinary locator works. Do not duplicate locator tuples across modules.
Validate selectors against realistic states: empty, loading, validation error,
modal open, paginated, responsive, localized.

`find_element` raises `NoSuchElementException`; `find_elements` returns `[]`.
Never use `find_elements()[0]` without a prior condition proving a match exists.

## Synchronization

```python
wait = WebDriverWait(driver, 15, poll_frequency=0.25)
wait.until(EC.element_to_be_clickable(SUBMIT)).click()
wait.until(EC.url_contains("/dashboard"))
```

| Need | Condition |
| --- | --- |
| Exists in the DOM only | `presence_of_element_located` |
| User-visible | `visibility_of_element_located` |
| Visible and enabled | `element_to_be_clickable` |
| Old node removed/replaced | `staleness_of` |
| Loader finished | `invisibility_of_element_located` |
| Frame ready and selected | `frame_to_be_available_and_switch_to_it` |
| Alert available | `alert_is_present` |
| Expected text/value | `text_to_be_present_in_element`, `..._in_element_value`, or a narrow predicate |
| Navigation complete enough | `url_is` / `url_contains` / `title_contains` **plus** a page-specific ready marker |
| Result list loaded | Visibility/count/content condition proving data is ready |
| Several conditions | `all_of`, `any_of`, `none_of` |

Before writing a custom condition, check that `expected_conditions` does not
already model the state. A custom predicate returns the useful object on success
and `False` otherwise, catches only the expected transient lookup exception, and
stays side-effect free.

Do not wait solely for `document.readyState == 'complete'` when the application
loads data afterwards. When a click triggers a re-render, capture the old
element and wait for `staleness_of(old)` before locating its replacement.

## Interaction

Locate immediately before use on a dynamic interface. Validate the outcome of
every significant interaction: a click returning without exception does not prove
the action took effect. Assert a state transition — URL, confirmation, modal
closure, saved row, status text, generated document, or API-visible result.

- Scroll only to bring a target into usable view, then wait for its actionable
  state.
- On an intercepted click, inspect overlays, animations, sticky headers, disabled
  state, wrong frame/window, and stale references. Do not swap in a JavaScript
  click — that hides the defect.
- `clear()` + `send_keys()` for editable controls; verify the value when masking,
  auto-formatting, or reactive validation can change it.
- `Select` only for a real `<select>`. Custom dropdowns need their own controls.
- `get_attribute()` for HTML attributes, `get_property()` for DOM properties.
- `is_displayed()`/`is_enabled()` are checks, not substitutes for a wait.
- `ActionChains` for genuine composite input (hover, modifiers, drag, wheel);
  always `perform()`, and `clear_actions()` after an interrupted compound action.

Patterns for all of the above: `references/recipes.md`.

## Forms

Model a form as: open a known state → fill each control → wait for dependent
control readiness → submit once → verify the authoritative result.

Express the workflow as business operations, not a flat sequence of element
calls. Preserve UI and server-side validation; never force invalid or
unauthorized input through JavaScript. Account for masks, date pickers,
autocomplete, debouncing, dependent dropdowns, and validation messages.

Where the final action is non-idempotent, require an explicit pre-submit check
and an authoritative post-submit confirmation. On a timeout after submission,
investigate the real state before any retry. Keep input values and screenshots
out of logs when they carry personal, financial, medical, contractual, or
authentication data.

## Contexts: Frames, Windows, Alerts, Shadow DOM

Element lookup happens inside the current window and selected frame — always know
which. Wait for a frame before switching into it, re-locate content after every
switch, and return with `parent_frame()` or `default_content()`.

For windows: record the known handles before the triggering action, wait for the
expected count or the new handle, select deterministically (never by index or
assumed order), close only a known secondary context, then switch back to a known
handle.

For alerts: wait with `alert_is_present`, inspect when meaningful, then `accept()`,
`dismiss()`, or `send_keys()` as the authorized workflow requires. Set
`unhandled_prompt_behavior` deliberately when prompts are possible. Never
suppress a confirmation to bypass a safety boundary.

For an open shadow root use `host.shadow_root` and its CSS lookups. Closed roots
are intentionally inaccessible — do not attempt to bypass the encapsulation.

Scoped helpers: `waits.inside_frame`, `waits.new_window_from`, `waits.accept_alert`.

## JavaScript

`execute_script()` and `execute_async_script()` are escape hatches. Use them only
when standard WebDriver cannot express an authorized operation, or for controlled
diagnostics.

Pass data through script arguments; never interpolate untrusted values into
source. Do not use JS clicks to mask overlay, timing, disabled-state, or context
defects. Do not mutate application state outside the supported UI flow to make a
test pass. For async scripts, define and wait for the specific completion
callback. Keep scripts short and covered by the browser matrix.

## Authentication And Sensitive State

Authenticate only through approved credentials and legitimate site flows. Never
weaken or work around MFA, CAPTCHA, SSO, or authorization controls.

Navigate to the cookie's domain before `add_cookie`. Treat cookies, local
storage, profile directories, exported session files, and auth headers as
secrets: never commit, print, attach, or casually retain them. Prefer a fresh
authorized login; reusing a session requires secure storage, expiry handling,
access control, and a documented reason. `delete_all_cookies()` clears the
current session — it is not a substitute for a fresh profile when isolation
matters.

Secrets come from the project's secret manager or environment configuration —
never from source, fixtures, selectors, URLs, command lines, screenshots, or logs.

## Files

Upload through a real file input with an absolute path; `send_keys` works even
when the input is visually hidden. For a remote driver, configure
`LocalFileDetector` when the file lives on the client.

Downloads are browser-specific and have no portable completion event. Use an
isolated, writable download directory per session, then prove completion on the
filesystem: partial files (`.crdownload`, `.part`) gone, size stable, expected
name/extension, non-zero size, and content signature where applicable. Only then
move or persist it, recording a redacted reference and checksum if traceability
is required. A visible button, a changed URL, and the absence of an exception
prove nothing. `sentinel.wait_for_download()` implements the full check.

## Data Extraction

Extract only data within the user's authorization, the site's terms, legal
obligations, and retention policy.

Wait for a completed content state, not the shell. Read stable row/cell
relationships by **named column**, never by positional index. Normalize
whitespace, locale-specific dates and numbers, nulls, pagination, and repeated
headers deliberately. Validate row count, unique identifiers, required fields,
and pagination completeness before persisting. Persist incrementally with a
checkpoint so an interruption costs one page, not the run. Capture provenance:
target, retrieval time, filters, page/record identifiers, parser version.

Rate-limit conservatively, respect published terms and robots directives, and
stop on authorization or access errors — never use Selenium to evade an API's
access controls, bot protection, request limits, or paywall. Escalate access
issues to the system owner.

Full procedure: `references/scraping-playbook.md`. Implementation:
`assets/sentinel/extract.py`, `pagination.py`, `pipeline.py`.

## Errors And Diagnostics

Classify before changing code.

| Symptom | Investigate first |
| --- | --- |
| `TimeoutException` | Wrong readiness condition, wrong context, overlay, failed navigation, or a state never reached |
| `NoSuchElementException` | Wrong locator, wrong frame/window, not rendered yet, feature flag, permission, or an error/empty state |
| `StaleElementReferenceException` | DOM replaced after render/navigation; re-locate after waiting for the new state |
| `ElementClickInterceptedException` | Overlay, animation, sticky UI, off-screen target, or wrong element |
| `ElementNotInteractableException` | Hidden, disabled, covered, wrong control, or incomplete state |
| `InvalidSelectorException` | Invalid or unsupported locator syntax |
| `UnexpectedAlertPresentException` | Unexpected prompt or unhandled confirmation |
| `SessionNotCreatedException` | Browser/driver/Selenium mismatch, inaccessible binary, profile lock, container dependency, proxy |
| `InvalidSessionIdException` | Driver already quit, crashed browser, expired remote session, wrong lifecycle ownership |
| Browser disconnect/crash | Browser and driver logs, resource limits, `/dev/shm`, profile/download paths, sandbox, binary version |

Cause-by-cause diagnosis: `references/troubleshooting.md`.

At a failure boundary collect only policy-safe evidence: operation name and
sanitized locator; current URL, title, window handle, known handles, frame path;
timestamp, Selenium version, browser capabilities and version, driver log
location; screenshot; redacted page source only when policy permits; console and
network logs where supported and permitted; expected vs. observed state and the
exception with traceback. `ArtifactStore.failure_bundle()` produces exactly this.

Do not catch broad `Exception` to continue. Add context, preserve the exception
chain, clean up the driver, and propagate or return a structured failure per the
project's error contract.

## Logging Hygiene

Log operations and outcomes with structured fields: run id, account alias, target,
operation, selector label, duration, attempt, outcome, artifact path, sanitized
error category.

Never log passwords, MFA codes, tokens, cookie values, connection strings,
authorization headers, or private keys; nor full account/identity numbers,
financial or medical details, or entire form payloads unless policy explicitly
allows protected logging; nor raw page source or screenshots to shared locations
without a sensitivity review. Store artifacts in session-specific directories,
restrict access, set retention, and exclude generated diagnostics, profiles,
downloads, reports, and secrets from version control.

## Testing Strategy

UI automation covers user-visible, cross-component behavior; unit and API tests
cover logic that does not need a browser.

Each Selenium test: fresh authorized session and known page state → one narrowly
scoped behavior → wait for and verify the authoritative outcome → evidence only
on failure → clean up driver, test data, and artifacts.

Design independent tests. Do not depend on test order, shared browser state,
shared accounts without isolation, prior records, local machine setup, or an
earlier test's cleanup. Separate smoke, regression, integration, destructive, and
environment-dependent suites. For a state-changing test, prefer a disposable
account/data fixture with verified cleanup; if cleanup cannot be guaranteed, do
not run against production without explicit approval.

Isolation rules for parallel runs and Grid: `references/scale-and-remote.md`.

## Review Checklist

- Authorized, safe for the target environment, and non-evasive?
- Does every lifecycle path reach `quit()`?
- Does every non-trivial interaction have an explicit readiness condition **and**
  outcome verification?
- Implicit waits absent, fixed sleeps removed?
- Locators stable, concise, centralized, verified against real states?
- Window, frame, alert, shadow-root, and stale-element contexts handled deliberately?
- Retries bounded, observable, idempotent-only?
- Final submissions/uploads/deletions protected from duplicate execution?
- Downloads and uploads verified with isolated paths and artifact checks?
- Pagination and loops hard-bounded; output persisted incrementally?
- Secrets excluded from code, logs, screenshots, page source, profiles, and VCS?
- Browser-specific, Grid, BiDi, and CDP paths capability-checked and version-tested?
- Does failure output carry enough sanitized evidence to diagnose the problem?
- Avoided unneeded abstractions, dependencies, browser flags, JavaScript, and
  framework changes?

## Delivery Checklist

1. Run the narrowest safe static checks, unit tests, and non-destructive browser
   tests available.
2. Do not execute anything that changes real records or external systems without
   explicit authorization.
3. State exactly what was verified, including browser and runtime if a browser
   test ran.
4. State what was not validated and why.
5. Note environment-specific or version-sensitive behavior, residual risks, and
   required configuration — without exposing secrets.

## Anti-Patterns

- `time.sleep()` as the primary wait mechanism.
- Mixing implicit and explicit waits.
- Unbounded `while True`, retries, polling, pagination, or refresh loops.
- Broad exception swallowing that converts failure into apparent success.
- JavaScript clicks used to conceal interaction failures.
- Reusing a stale element after a DOM-changing action.
- Selecting a window by index or assuming `window_handles` order.
- Positional cell indexes instead of named columns.
- Collecting an entire dataset in memory and writing once at the end.
- Hard-coded credentials, session cookies, local profiles, driver paths, or
  OS-specific paths.
- Sharing drivers, profiles, or download folders across concurrent jobs.
- Treating click success as business-operation success.
- Retrying a non-idempotent operation without checking authoritative state.
- Capturing unredacted screenshots, page source, console logs, cookies, or
  network data by default.
- Anti-detection, CAPTCHA-solving, fingerprint-spoofing, access-bypass, or
  rate-limit-evasion techniques.
- Testing production by issuing, submitting, uploading, paying, deleting, or
  changing data without explicit approval.

## Version Sensitivity

Selenium's documentation navigation uses broad version labels while the Python
package is released independently. Selenium Manager, headless flags, browser
options, downloads, Grid behavior, BiDi, CDP, and low-level modules change across
Selenium and browser versions. Confirm the installed package and deployment
browser before using version-sensitive features, pin and test the supported
matrix for production, and consult release notes and source when the public
documentation is incomplete.
