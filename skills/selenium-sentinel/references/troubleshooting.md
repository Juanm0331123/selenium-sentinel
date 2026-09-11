# Troubleshooting Playbook

Diagnose before changing code. Each entry gives the real causes in likelihood
order, the check that discriminates between them, and the fix that is not a
workaround.

## Universal first four checks

Before investigating any specific exception, confirm:

1. **Context** — `driver.current_url`, `driver.title`, `driver.current_window_handle`,
   and which frame is selected. Most "the element does not exist" reports are a
   wrong frame, a wrong window, or a page that never navigated.
2. **Reality** — run headed (`SENTINEL_HEADLESS=false`) and watch. Ten seconds
   of watching beats an hour of guessing.
3. **Selector** — paste it into the DevTools console:
   `document.querySelectorAll("<css>")` or `$x("<xpath>")`. Zero matches is a
   locator bug; many matches is an ambiguity bug.
4. **Versions** — `python scripts/selenium_doctor.py --launch`. A browser that
   auto-updated past the pinned driver explains a whole class of sudden failures.

## `TimeoutException`

| Likely cause | Discriminator | Fix |
| --- | --- | --- |
| Waiting for the wrong state | Element is in the DOM but hidden, or visible but disabled | Match the condition to the next action: `element_to_be_clickable` before a click, not `presence_of_element_located` |
| Wrong frame/window | `driver.page_source` lacks the markup you see on screen | Switch into the iframe (`inside_frame`) or the new handle first |
| Overlay/spinner still up | Screenshot at the timeout shows a loader | Wait for `invisibility_of_element_located(SPINNER)` before the target |
| Data loads after `readyState == complete` | Network tab shows a late XHR | Wait for a content marker, never for readiness of the document |
| App really is slow | Same op succeeds with a larger budget | Raise the specific budget with a reason; do not raise the global default |
| Navigation never happened | URL unchanged in the evidence bundle | Verify the click landed and check for a blocking validation message |

Never fix a timeout by adding `time.sleep()` or by raising every timeout globally.

## `NoSuchElementException`

Causes in order: wrong frame; content not rendered yet (you used `find_element`
where a wait belongs); locator broken by a site change; element only exists for
another role/feature flag/locale; the page rendered an error or empty state
instead of content.

Fix: use a wait; assert the context; and race the real outcomes with
`waits.any_located([SUCCESS, EMPTY, ERROR])` so an error state is reported as an
error state rather than a missing element.

## `StaleElementReferenceException`

The node you held was detached — the framework re-rendered the list, the page
navigated, or a filter rebuilt the table.

Fix: re-locate immediately before use. For an action that triggers the rebuild,
use the capture/act/staleness/re-locate sequence (`waits.replaced_after`). Do not
"fix" it by catching the exception and retrying blindly in a loop, and do not
hold WebElement references across navigations.

## `ElementClickInterceptedException`

Something is on top of the target: cookie banner, sticky header, modal backdrop,
toast, or an animation still running.

Check the screenshot from the evidence bundle, and ask the browser what is
actually on top:

```python
blocker = driver.execute_script(
    "const r = arguments[0].getBoundingClientRect();"
    "const e = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);"
    "return e ? e.outerHTML.slice(0, 200) : null;",
    element,
)
```

Fix the real blocker: dismiss the banner through its own control, wait for the
animation to finish, scroll the element to the centre of the viewport. A
JavaScript click hides the defect and produces a test that passes while the user
cannot click the button.

## `ElementNotInteractableException`

Element is present but hidden (`display:none`, zero size, `visibility:hidden`),
disabled, behind a `pointer-events` rule, or you are targeting a wrapper instead
of the real control (very common with custom selects, file inputs, and rich text
editors).

Fix: target the actual interactive node; wait for the enabling condition (often a
prior field being filled); for a styled file input, `send_keys` to the underlying
`input[type=file]` even when it is visually hidden.

## `SessionNotCreatedException`

Browser/driver mismatch, browser not installed where expected, profile locked by
another session, missing container dependency, or a corporate proxy blocking
Selenium Manager's driver download.

Checks: `selenium_doctor.py --launch`; `SE_*` environment variables; whether the
`--user-data-dir` path is already in use; whether the machine is offline or
behind a proxy that needs `HTTPS_PROXY` set for Selenium Manager.

## `InvalidSessionIdException` / browser crash

The session ended before the call: something already called `quit()`, the browser
crashed, or a remote session timed out.

Checks: the driver log under `logs/`, the container's memory limits (Chrome dies
quietly when `/dev/shm` is exhausted), and lifecycle ownership — two owners
calling `quit()` is a design bug, not a flake.

## `UnexpectedAlertPresentException`

A native dialog appeared and blocked everything. Handle it deliberately
(`waits.accept_alert`), or set `options.unhandled_prompt_behavior` if the
workflow genuinely should ignore prompts. Never suppress a confirmation to get
past a safety boundary.

## `MoveTargetOutOfBoundsException`

An ActionChains move landed outside the viewport. Scroll the element into view
first (`ActionChains(driver).scroll_to_element(el)`) and avoid absolute
coordinate offsets, which break at every other viewport size.

## Downloads that "worked" but produced nothing

Symptoms: the click succeeded, no file appears, or the file is 1 KB of HTML.

Checks: is the configured download directory the one the browser actually used
(headless Chrome ignores prefs when `--user-data-dir` points at a profile
configured otherwise); did a partial file (`.crdownload`, `.part`) appear at all;
is the "file" an HTML error page (check the magic bytes — `downloads.wait_for_download`
does this); did a native save dialog open (Firefox needs the MIME type in
`browser.helperApps.neverAsk.saveToDisk`).

## Flaky-only-in-CI failures

Order of suspicion:

1. Viewport — CI runs headless at a different size; responsive DOM differs. Set
   `--window-size` explicitly.
2. Speed — CI machines are slower **and** sometimes faster than local, which
   changes race outcomes in both directions.
3. Shared state — a reused profile, a shared account, or tests that depend on
   each other's data.
4. Fonts/locale — missing fonts change layout and text; a different locale
   changes date and number formats and therefore parsing.
5. Time zone — assert on parsed dates, never on rendered strings.

## Escalate, do not engineer around

Stop and ask a human when you see: a CAPTCHA, a bot-detection interstitial, an
MFA prompt outside the approved flow, a sudden `403`/`429`, a licence or terms
banner, or a page that says automated access is prohibited. None of these are
technical problems to solve.
