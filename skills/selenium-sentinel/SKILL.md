---
name: selenium-sentinel
description: Design, implement, debug, review, and harden authorized Python Selenium WebDriver automation and browser tests. Use for Selenium scraping, form workflows, browser interaction, WebDriver errors, waits, locators, downloads, uploads, sessions, Grid, Remote WebDriver, BiDi, or browser diagnostics.
---

# Selenium Sentinel

Build Selenium Python automation that is observable, deterministic, secure, and safe to operate. Favor the smallest correct WebDriver workflow over abstractions, retries, or browser workarounds.

For a complete index of public Selenium Python feature families and their limits, read `references/official-python-api-coverage.md` before using an unfamiliar API, browser-specific capability, BiDi, CDP, Grid, FedCM, virtual authenticator, or download feature.

This skill applies to authorized browser automation and testing only. Never bypass CAPTCHAs, bot-detection systems, MFA, rate limits, paywalls, access controls, authentication, or authorization boundaries. Do not automate a state-changing production action, upload, payment, submission, deletion, or external integration merely to validate code unless the user explicitly authorizes that action.

## Authority And Scope

1. Read the repository instructions and existing Selenium configuration before proposing or changing code.
2. Identify the installed `selenium` version from the dependency manifest or environment. Match code to that version, not to a remembered API.
3. Prefer the official Selenium Python API and official Selenium documentation. Treat blogs, Stack Overflow snippets, and unofficial driver managers as non-authoritative.
4. Preserve the repository's architecture, logging, configuration, test framework, and deployment model. Do not introduce Page Objects, pytest, Grid, helpers, retries, or third-party packages unless the project needs them.
5. Inspect the target application's DOM and actual browser behavior before changing selectors or timing logic. Do not guess selectors from screenshots or text alone.
6. Use a non-production environment, read-only account, test record, or dry-run path whenever one exists.

Official references:

- Python API: <https://www.selenium.dev/selenium/docs/api/py/api.html>
- Python package guide: <https://www.selenium.dev/selenium/docs/api/py/>
- WebDriver documentation: <https://www.selenium.dev/documentation/webdriver/>
- Selenium Manager: <https://www.selenium.dev/documentation/selenium_manager/>
- WebDriver BiDi: <https://www.selenium.dev/documentation/webdriver/bidi/>
- Grid: <https://www.selenium.dev/documentation/grid/>
- Source: <https://github.com/SeleniumHQ/selenium/tree/trunk/py>

## First Response Protocol

Before implementation, establish all applicable facts:

| Area            | Determine                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------- |
| Intent          | Scraping, read-only data extraction, UI test, authorized workflow, regression, or defect diagnosis                  |
| Risk            | Whether any path can submit, issue, upload, delete, pay, alter data, or expose personal/confidential data           |
| Runtime         | Python, Selenium, browser, browser version, OS, container/CI/VM, local versus remote session                        |
| Target          | URL/environment, authentication method, current page state, dynamic rendering, iframes, shadow DOM, windows, alerts |
| Existing design | Driver creation, selectors, wait policy, error handling, artifacts, logging, test runner, secrets source            |
| Success         | Exact observable condition that proves the operation completed                                                      |
| Constraints     | Authorization, terms, rate limits, account scope, allowed data, output retention, deployment limitations            |

Use the smallest safe inspection that resolves uncertainty. If a choice could affect production data or security, ask the user using closed options before proceeding.

## Required Operating Principles

- Use a fresh, isolated browser profile and driver session for each independent unit of work.
- Create exactly one owner for every driver and guarantee `quit()` through `finally`, fixture teardown, or an equivalent lifecycle boundary.
- Prefer explicit waits for a specific state. Do not use `time.sleep()` as synchronization.
- Do not mix implicit and explicit waits. Set implicit wait to zero unless inherited code cannot be changed safely.
- Wait for the state needed by the next action, not merely for DOM presence.
- Keep locators centralized near the page or feature they describe. Keep workflows expressed as business-level operations.
- Re-locate elements after navigation, refreshes, AJAX replacements, frame/window changes, or any action that can rebuild the DOM.
- Treat each browser context as distinct: current window, active frame, active alert, and open shadow root all affect element lookup.
- Bound every wait and retry. Never loop until success without a timeout, evidence, and safe exit.
- Retry only a demonstrably transient and idempotent operation. Never blindly retry a submission, payment, creation, deletion, upload, or status change.
- Capture redacted diagnostic evidence at failure boundaries. Never log credentials, cookies, tokens, complete sensitive page source, or private form values.
- Prefer standard WebDriver. Use JavaScript, CDP, and BiDi only for a documented, browser-supported need that standard WebDriver cannot meet.

## Architecture Selection

Choose the least complex structure that makes the automation clear and maintainable.

| Situation                                   | Preferred structure                                                                                                        |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| One small, stable read-only task            | One focused workflow with local selectors and explicit waits                                                               |
| Several flows on one application            | Feature/page modules with selectors and named operations                                                                   |
| UI test suite                               | Test framework fixtures plus page/feature objects where reuse justifies them                                               |
| Production browser bot                      | Separate configuration, driver lifecycle, workflow operations, persistence/integration boundaries, and artifact management |
| Multiple browsers, OSs, or parallel workers | Capability-driven driver factory plus isolated Remote/Grid sessions                                                        |

Do not force a Page Object Model into a small bot. If Page Objects exist, they should expose meaningful application operations and state checks, not duplicate every WebElement method.

For scraper projects, first determine whether an authorized direct API, export, or static HTTP response is available. Selenium is appropriate when browser rendering, authenticated UI behavior, or user interactions are required. Do not use it solely because it is familiar.

## Session Construction

Modern Selenium normally uses Selenium Manager to resolve a compatible driver and browser. Do not add `webdriver-manager` unless the deployment specifically needs it. Pin browser and Selenium versions in controlled environments when reproducibility matters.

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,1200")
options.page_load_strategy = "normal"

driver = webdriver.Chrome(options=options)
try:
    driver.get("https://example.test")
finally:
    driver.quit()
```

Configure only arguments required by the environment. Do not cargo-cult `--no-sandbox`, `--disable-dev-shm-usage`, anti-detection flags, custom user agents, or insecure flags. Document an operational reason for every non-default browser argument.

Use browser-specific `Options` and, when needed, `Service`:

```python
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

driver_log = Path("logs") / "chromedriver.log"
options = Options()
options.add_argument("--headless=new")
service = Service(log_output=str(driver_log))
driver = webdriver.Chrome(options=options, service=service)
```

Supportable construction concerns:

- Choose `webdriver.Chrome`, `webdriver.Firefox`, `webdriver.Edge`, or `webdriver.Safari` deliberately.
- Use `options.binary_location` only for a known browser binary.
- Set `accept_insecure_certs` only in controlled environments where it is justified.
- Set `page_load_strategy` only when the workflow defines readiness separately.
- Set `unhandled_prompt_behavior` deliberately when alerts may occur.
- Configure browser and page-load timeouts explicitly where a default is unsuitable.
- Keep driver logs outside source control and redact/retain them according to policy.
- Use a unique profile and download directory per session/worker. Never share profiles among concurrent drivers.
- In Linux containers, ensure the browser, its runtime dependencies, writable profile/download paths, and sandbox policy are configured in the image rather than patched at runtime.

For controlled Selenium Manager environments, use its documented TOML configuration and environment variables. Account for proxy, cache, offline, mirror, version, and telemetry policy there. `SE_AVOID_STATS=true` disables its plausible-usage-statistics request when policy requires it. Verify Manager behavior with the actual Selenium release because its capabilities are version-sensitive.

## Driver Lifecycle

Treat browser setup and teardown as resource management, not incidental code.

```python
from selenium import webdriver

driver = webdriver.Firefox()
try:
    driver.get("https://example.test")
finally:
    driver.quit()
```

Use `quit()` to end the WebDriver session and close all associated windows. Use `close()` only when the workflow intentionally closes the current tab/window and knows which context remains. A failed operation must not leak a browser, profile lock, download directory, or remote session.

For pytest, keep setup/teardown in a fixture and make fixture scope match isolation requirements:

```python
import pytest
from selenium import webdriver

@pytest.fixture
def driver():
    session = webdriver.Chrome()
    yield session
    session.quit()
```

Do not share one driver across parallel workers. Each worker needs an independent session, profile, download directory, credentials/session state, target work item, and artifact path.

## Locator Discipline

Use Selenium's standard locator strategies through `By`:

```python
from selenium.webdriver.common.by import By

USERNAME = (By.NAME, "username")
SUBMIT = (By.CSS_SELECTOR, "form[data-flow='sign-in'] button[type='submit']")
STATUS = (By.XPATH, "//section[@aria-label='Result']//span[@data-status]")
```

Preference order, subject to target stability:

1. Stable, unique application-owned semantic attribute such as `data-testid`, `data-qa`, `name`, `aria-label`, or an ID.
2. Short CSS selector anchored to a stable semantic container.
3. Concise XPath for relationships CSS cannot express.
4. Link text only when the text is stable, unique, and intentionally part of the contract.
5. Relative locators only as a last resort because layout changes affect them.

Avoid:

- Absolute XPath and position-only selectors.
- Long chains of anonymous `div` elements.
- Dynamically generated CSS classes, randomized IDs, presentation-only classes, and translated display text unless no stable contract exists.
- Finding elements with JavaScript when an ordinary locator can express the target.
- Duplicating locator tuples across modules.

Inspect a selector against realistic states: empty/loading state, validation error, modal open, permissions variation, pagination, responsive layout, and localized text where relevant.

`find_element` raises `NoSuchElementException`; `find_elements` returns an empty list. Do not use `find_elements()[0]` unless an explicit prior condition proves at least one match.

## Synchronization And Readiness

Use `WebDriverWait` plus an expected condition or focused predicate. The condition should represent the precise precondition of the next operation.

```python
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

wait = WebDriverWait(driver, 15, poll_frequency=0.2)
button = wait.until(EC.element_to_be_clickable(SUBMIT))
button.click()
wait.until(EC.url_contains("/dashboard"))
```

Choose the condition deliberately:

| Need                              | Appropriate condition                                                                         |
| --------------------------------- | --------------------------------------------------------------------------------------------- |
| Element exists in DOM only        | `presence_of_element_located`                                                                 |
| User-visible element              | `visibility_of_element_located`                                                               |
| Visible and enabled element       | `element_to_be_clickable`                                                                     |
| Existing element removed/replaced | `staleness_of`                                                                                |
| Frame ready and selected          | `frame_to_be_available_and_switch_to_it`                                                      |
| Alert available                   | `alert_is_present`                                                                            |
| Expected text/value/state         | `text_to_be_present_in_element`, `text_to_be_present_in_element_value`, or a narrow predicate |
| Navigation complete enough        | `url_is`, `url_contains`, `title_is`, `title_contains`, plus a page-specific ready marker     |
| Result list loaded                | Visibility/count/content condition that proves data is ready                                  |

For a custom condition, return the useful object when successful and `False` otherwise. Catch only the expected transient lookup exception. Keep the predicate side-effect free.

```python
from selenium.common.exceptions import StaleElementReferenceException

def result_count_is(expected_count):
    def condition(browser):
        try:
            return len(browser.find_elements(*RESULT_ROWS)) == expected_count
        except StaleElementReferenceException:
            return False
    return condition
```

Before adding a custom condition, verify that official `expected_conditions` does not already model the state. Do not wait solely for `document.readyState == 'complete'` when the application loads data after that event. Do not use arbitrary sleeps to hide a missing readiness signal.

When a click triggers an AJAX re-render, capture the old element and wait for `staleness_of(old_element)` before locating its replacement. This avoids acting on stale DOM references.

## Element Interaction

Locate immediately before use when the interface is dynamic.

```python
field = wait.until(EC.visibility_of_element_located(USERNAME))
field.clear()
field.send_keys(username)
wait.until(EC.element_to_be_clickable(SUBMIT)).click()
```

Validate the outcome of every significant interaction. A click returning without exception does not prove that the intended action took effect. Assert/verify a state transition: URL, success alert, modal closure, saved row, status text, generated document, or API-visible result.

Interaction guidance:

- Scroll only when necessary to bring the target into usable view; then wait for its actionable state.
- If a click is intercepted, inspect overlays, animations, sticky headers, disabled state, wrong frame/window, and stale references. Do not immediately replace the click with JavaScript.
- Use `clear()` and `send_keys()` for editable controls. Verify the value if masking, auto-formatting, or reactive validation can change it.
- Use `Select` only for a genuine HTML `<select>` element. Custom dropdowns require their actual UI controls.
- Prefer `get_attribute()` for HTML attributes and `get_property()` for DOM properties when the distinction matters.
- Use `is_displayed()` and `is_enabled()` as checks, not substitutes for a wait when state changes asynchronously.
- Use `element.screenshot()` for a targeted diagnostic or `driver.save_screenshot()` for page-level evidence.

## Keyboard, Pointer, Wheel, And Drag Actions

Use `ActionChains` when the application requires real composite user input such as hover menus, modifier keys, drag-and-drop, or wheel scrolling. Always call `perform()`.

```python
from selenium.webdriver import ActionChains

menu = wait.until(EC.visibility_of_element_located(MENU))
ActionChains(driver).move_to_element(menu).perform()
wait.until(EC.element_to_be_clickable(MENU_ITEM)).click()
```

After a failed or interrupted compound action, clear persistent input-device state through the relevant Actions API before continuing. Do not use actions to simulate interactions the target does not actually require.

For file and native OS dialogs, Selenium can interact only with browser-exposed DOM. Do not use fragile desktop automation to control browser chrome unless the user explicitly accepts that platform dependency and no supported WebDriver path exists.

## Forms And Validation

Model a form workflow as: open known state, fill each control, wait for dependent control readiness, submit once, verify the authoritative result.

- Use business-meaningful operations such as `completar_formulario` or `confirmar_solicitud`, not a generic sequence of element calls spread through an orchestrator.
- Preserve server-side constraints and UI validation. Do not bypass frontend controls through JavaScript to force invalid or unauthorized input.
- Account for input masks, date controls, autocomplete, debouncing, dependent dropdowns, and validation messages.
- When a workflow has a non-idempotent final action, require an explicit pre-submit check and an authoritative post-submit confirmation. On timeout after submission, investigate state before any retry.
- Keep input values and screenshots out of logs when they contain personal, financial, medical, contractual, or authentication data.

## Frames, Windows, Tabs, And Alerts

Always know the active context. Element lookup happens inside the current window and selected frame.

Frames:

```python
wait.until(EC.frame_to_be_available_and_switch_to_it(FRAME))
wait.until(EC.visibility_of_element_located(FRAME_CONTENT))
driver.switch_to.default_content()
```

- Wait for the frame and switch to it before locating its content.
- Use `parent_frame()` when returning one level and `default_content()` when returning to the top document.
- Re-locate frame content after switching contexts.

Windows and tabs:

```python
from selenium.webdriver.support import expected_conditions as EC

original = driver.current_window_handle
wait.until(EC.element_to_be_clickable(OPEN_REPORT)).click()
wait.until(EC.number_of_windows_to_be(2))
report_handle = next(handle for handle in driver.window_handles if handle != original)
driver.switch_to.window(report_handle)
wait.until(EC.url_contains("/report"))
```

- Record known handles before the triggering action.
- Wait for the expected handle count or the specific expected context.
- Select the intended handle deterministically; do not assume ordering.
- Close only a known secondary context, then switch back to a known remaining handle.
- Use `switch_to.new_window(WindowType.TAB)` or `WindowType.WINDOW` only when the workflow explicitly needs a new context.

Alerts:

```python
alert = wait.until(EC.alert_is_present())
message = alert.text
alert.accept()
```

- Wait for an alert, inspect it when it is meaningful, then `accept()`, `dismiss()`, or `send_keys()` as the authorized workflow requires.
- Set prompt behavior intentionally if unexpected alerts are possible.
- Do not suppress confirmation dialogs to bypass a safety boundary.

## Shadow DOM

For an open shadow root, use Selenium's shadow-root support rather than JavaScript traversal:

```python
host = wait.until(EC.presence_of_element_located(SHADOW_HOST))
root = host.shadow_root
button = root.find_element(*SHADOW_BUTTON)
button.click()
```

Closed shadow roots are intentionally not accessible to WebDriver. Do not attempt to bypass their encapsulation. Re-locate shadow hosts after DOM replacement.

## JavaScript

`execute_script()` and `execute_async_script()` are escape hatches, not the default interaction API. Use them only when standard WebDriver cannot express an authorized operation or when collecting controlled diagnostics.

```python
visible = driver.execute_script(
    "return arguments[0].getClientRects().length > 0;",
    element,
)
```

- Pass data through script arguments; never interpolate untrusted values into JavaScript source.
- Do not use JavaScript clicks to mask overlay, timing, disabled, or context defects.
- Do not mutate application state outside the supported UI flow merely to make a test pass.
- Define and wait for the specific completion callback when using asynchronous scripts.
- Keep scripts short, browser-neutral where possible, and covered by the target browser matrix.

## Authentication, Cookies, And Sensitive State

Authenticate only through approved credentials and legitimate site flows. Never weaken or work around MFA, CAPTCHA, SSO, or authorization controls.

Cookie rules:

```python
driver.get("https://example.test")
driver.add_cookie({"name": "preference", "value": "compact"})
cookie = driver.get_cookie("preference")
```

- Navigate to the cookie's matching domain before adding it.
- Treat cookies, local storage, profile directories, exported session files, and authentication headers as secrets.
- Never commit, print, attach, or casually retain them.
- Prefer a fresh authorized login when practical. Reusing a session requires explicit secure storage, expiry handling, access controls, and a documented reason.
- Call `delete_all_cookies()` only when clearing the current session is intended; it is not a substitute for a new profile when state isolation matters.

Use secrets from the project's secret manager or environment configuration. Do not place credentials in source, test fixtures, selectors, URLs, command lines, screenshots, or logs.

## Files: Uploads And Downloads

Upload through an actual file input using an absolute local path:

```python
from pathlib import Path

upload = wait.until(EC.presence_of_element_located(FILE_INPUT))
upload.send_keys(str(Path("data") / "document.pdf"))
```

For a remote driver, use Selenium's supported remote file detector path where required by the Grid/provider. Do not assume a file path exists on the remote node.

Downloads are browser-specific and are not a portable WebDriver completion event. Establish an isolated, writable download directory before the session. Then verify the completed artifact deliberately:

1. Trigger an authorized download once.
2. Wait for the expected output to appear and for browser partial-download files to disappear, using the browser's known behavior.
3. Confirm its expected name/pattern, extension, non-zero size, and type/content signature when appropriate.
4. Move or persist it only after verification.
5. Record a redacted artifact reference and checksum if the business process requires traceability.

Never treat a visible download button, a changed URL, or the absence of an exception as proof that a file finished downloading. Do not upload the artifact to another system as a test unless explicitly authorized.

## Data Extraction

Extract only data within the user's authorization, terms, legal obligations, and retention policy.

- Wait for a completed content state, not just the table/shell container.
- Extract stable row/cell relationships rather than scraping visual coordinates.
- Normalize whitespace, locale-specific dates/numbers, null values, pagination, and repeated headers deliberately.
- Validate row count, unique identifiers, required fields, and pagination completion before persisting results.
- Use idempotency keys or source identifiers where data may be retried or resumed.
- Store only necessary fields. Redact or minimize personal/confidential data in logs and debugging artifacts.
- Rate-limit conservatively, respect published terms and robots directives where applicable, and stop on authorization or access errors.
- Capture provenance: target, retrieval time, applied filters, page/record identifiers, and parsing version when the output has operational value.

Do not use Selenium to evade an API's access controls, bot protection, request limits, or paywall. Escalate access issues to the system owner.

## Errors, Recovery, And Diagnostics

Classify the failure before changing code. The usual categories are:

| Exception or symptom               | Investigate first                                                                                                    |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `TimeoutException`                 | Wrong readiness condition, wrong context, slow dependency, overlay, failed navigation, or target state never reached |
| `NoSuchElementException`           | Incorrect locator, wrong frame/window, DOM not loaded, feature flag, permission, or page changed                     |
| `StaleElementReferenceException`   | DOM replacement after render/navigation; re-locate after waiting for the new state                                   |
| `ElementClickInterceptedException` | Overlay, animation, sticky UI, off-screen target, or wrong element                                                   |
| `ElementNotInteractableException`  | Hidden, disabled, covered, wrong control, or incomplete state                                                        |
| `InvalidSelectorException`         | Invalid or unsupported locator syntax                                                                                |
| `UnexpectedAlertPresentException`  | Unexpected prompt or unhandled confirmation                                                                          |
| `SessionNotCreatedException`       | Browser/driver/Selenium mismatch, inaccessible binary, profile lock, or container dependency                         |
| `InvalidSessionIdException`        | Driver already quit, crashed browser, expired remote session, or incorrect lifecycle ownership                       |
| Browser disconnect/crash           | Browser logs, driver logs, resource limits, profile/download paths, sandbox, browser binary/version                  |

At a meaningful failure boundary, collect only policy-safe evidence:

- Operation name and sanitized locator.
- Current URL, title, current window handle, known handles, and frame path where available.
- Timestamp, Selenium version, browser capabilities, browser version, driver/Service log location.
- Screenshot with a safe retention location.
- Redacted page source only when policy permits it.
- Browser console/network/driver logs where browser support and data policy permit.
- Previous and expected state, actual observed state, and the triggering exception with traceback.

Do not catch broad `Exception` merely to continue. Add context, preserve the original exception chain, clean up the driver, and propagate or return a structured failure according to the project's error contract.

Use retries only when all conditions are true: the failure is known transient, the action is idempotent, the retry count is small and bounded, the wait/retry is observable, and the final failure contains diagnostics. For non-idempotent operations, query the authoritative system state before deciding whether recovery is safe.

## Logging And Artifact Hygiene

Log operations and outcomes, not secrets or raw sensitive payloads. Prefer structured fields for run ID, account alias, target name, operation, selector label, duration, attempt, outcome, artifact path, and sanitized error category.

Never log:

- Passwords, MFA codes, tokens, cookie values, connection strings, complete authorization headers, or private keys.
- Full account/identity numbers, financial/medical details, or entire form payloads unless policy explicitly allows protected logging.
- Raw page source or screenshots to shared locations without sensitivity review.

Store artifacts in session-specific directories, restrict access, set a retention policy, and exclude generated diagnostics, profiles, downloads, reports, and secrets from version control.

## Browser Differences And Headless Runs

Browser behavior differs, especially for downloads, permission prompts, certificates, fonts, window geometry, headless rendering, CDP, and BiDi. Test the deployment browser rather than assuming Chrome behavior transfers to Firefox, Edge, Safari, Grid, or a cloud provider.

- Use current headless modes supported by the target browser and set explicit window size when responsive layout matters.
- Avoid viewport-dependent selectors and coordinate-based actions.
- Keep browser-specific preferences/capabilities isolated from portable workflow code.
- Run a visible browser locally for diagnosis when the deployment path permits it; preserve the same version and profile constraints where possible.
- Treat `accept_insecure_certs`, proxy configuration, download preferences, and browser binary paths as environment configuration.

## Remote WebDriver And Selenium Grid

Use Remote WebDriver or Grid for legitimate remote execution, browser/OS coverage, or parallel capacity. Do not use it to evade access restrictions.

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")
driver = webdriver.Remote(
    command_executor="https://grid.example.test/wd/hub",
    options=options,
)
```

Remote execution requirements:

- Use a trusted, authenticated, encrypted endpoint and keep its credentials out of source/logs.
- Send W3C browser options rather than legacy desired-capability dictionaries unless the provider requires a documented adapter.
- Ensure profile, download, upload, artifact, and file-system semantics work on the remote node.
- Configure `LocalFileDetector` when supported and required for uploads from the client machine.
- Assign each worker a unique driver/session, data item, account/session state, download directory, and artifact namespace.
- Bound parallelism to site capacity, account limits, and infrastructure resources.
- Capture remote session IDs and node diagnostics securely for incident investigation.

## BiDi And CDP

Default to standard WebDriver. Use WebDriver BiDi for supported event-driven browser capabilities when an authorized diagnostic or workflow genuinely needs them. Enable and use the high-level public API supported by the installed Selenium version.

```python
from selenium.webdriver.chrome.options import Options

options = Options()
options.enable_bidi = True
```

BiDi, CDP, and browser-devtools APIs are version- and browser-sensitive:

- Capability-detect and test them on the exact Selenium, browser, driver/Grid, and CI matrix.
- Prefer Selenium's documented high-level interfaces over internal modules.
- Isolate Chromium-specific CDP code from portable WebDriver workflows.
- Do not depend on undocumented protocol commands or brittle internal Selenium APIs.
- Do not use network interception to collect secrets, bypass authorization, alter protections, or evade rate limits.

## Testing Strategy

Use a layered strategy. UI automation should cover user-visible, cross-component behavior; unit and API tests should cover logic that does not require a browser.

For each Selenium test/workflow, make prerequisites and assertions explicit:

1. Start a fresh authorized session and known page state.
2. Execute a narrowly scoped behavior.
3. Wait for and verify the authoritative observable outcome.
4. Capture evidence only on failure.
5. Clean up driver, created test data, and temporary artifacts safely.

Design independent tests. Do not rely on test order, shared browser state, shared accounts without isolation, prior records, local machine setup, or an earlier test's cleanup. Mark and separate smoke, regression, integration, destructive, and environment-dependent suites.

For a state-changing test, prefer a disposable account/data fixture and a verified cleanup operation. If cleanup cannot be guaranteed, do not run against production without explicit approval.

## Review Checklist

Review Selenium changes against this list:

- Is the automation authorized, safe for the target environment, and non-evasive?
- Does every driver lifecycle path reach `quit()`?
- Does every non-trivial interaction have an explicit readiness condition and outcome verification?
- Are implicit waits absent and fixed sleeps removed?
- Are locators stable, concise, centralized, and verified against target states?
- Are window, frame, alert, shadow-root, and stale-element contexts handled deliberately?
- Are retries bounded, observable, and limited to idempotent transient operations?
- Are final submissions/uploads/deletions protected from duplicate execution?
- Are downloads/uploads verified using isolated paths and artifact checks?
- Are secrets and sensitive data excluded from code, logs, screenshots, page source, profiles, and version control?
- Are browser-specific code, Grid, BiDi, and CDP paths capability-checked and version-tested?
- Does failure output contain enough sanitized evidence to diagnose the problem?
- Has the code avoided unneeded abstractions, dependencies, browser flags, JavaScript, and framework changes?

## Delivery Checklist

Before reporting completion:

1. Run the narrowest safe static checks, unit tests, and non-destructive browser tests available.
2. Do not execute an action that can change real records or external systems without explicit user authorization.
3. State exactly what was verified, including browser/runtime if a browser test ran.
4. State any validation not run and why.
5. Note environment-specific or version-sensitive behavior, residual risks, and required configuration without exposing secrets.

## Anti-Patterns

Reject or replace these patterns:

- `time.sleep()` used as the primary wait mechanism.
- Mixing implicit and explicit waits.
- Unbounded `while True`, retries, polling, or refresh loops.
- Broad exception swallowing that converts failures into apparent success.
- JavaScript clicks used to conceal interaction failures.
- Reusing a stale element after a DOM-changing action.
- Selecting a window by index or assuming `window_handles` order.
- Hard-coding credentials, session cookies, local browser profiles, driver paths, or OS-specific paths.
- Sharing browser drivers/profiles/download folders across concurrent jobs.
- Treating click success as business-operation success.
- Retrying a non-idempotent operation without checking authoritative state.
- Capturing unredacted screenshots, page source, console logs, cookies, or network data by default.
- Adding anti-detection, CAPTCHA-solving, fingerprint-spoofing, access-bypass, or rate-limit-evasion techniques.
- Testing production by issuing, submitting, uploading, paying, deleting, or changing data without explicit approval.

## Version Sensitivity

The Selenium documentation navigation may use broad version labels while the Python API is released independently. Selenium Manager, headless flags, browser options, downloads, Grid behavior, BiDi, CDP, and low-level implementation modules can change across Selenium and browser versions. Confirm the installed package and deployment browser before using version-sensitive features, pin and test the supported matrix for production, and consult release notes/source when public documentation is incomplete.
