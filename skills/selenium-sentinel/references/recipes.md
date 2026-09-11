# Recipes

Verified patterns for the situations that come up in almost every Selenium job.
Each one is written against the official API; the `sentinel/` toolkit wraps most
of them, and the raw form is shown so the mechanism stays visible.

Assume throughout:

```python
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

wait = WebDriverWait(driver, 15, poll_frequency=0.25)
```

## Wait for a click to actually change something

```python
rows = driver.find_elements(By.CSS_SELECTOR, "[data-testid='row']")
anchor = rows[0]
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='next']"))).click()
wait.until(EC.staleness_of(anchor))                       # the old DOM is gone
rows = wait.until(EC.visibility_of_all_elements_located(  # the new DOM is ready
    (By.CSS_SELECTOR, "[data-testid='row']")
))
```

## Race the real outcomes instead of assuming success

```python
SUCCESS = (By.CSS_SELECTOR, "[data-testid='confirmation']")
ERROR = (By.CSS_SELECTOR, "[role='alert']")

def first_of(*locators):
    def condition(browser):
        for locator in locators:
            if browser.find_elements(*locator):
                return locator
        return False
    return condition

matched = wait.until(first_of(SUCCESS, ERROR))
if matched == ERROR:
    raise RuntimeError(driver.find_element(*ERROR).text)
```

## Wait for a spinner to finish

```python
SPINNER = (By.CSS_SELECTOR, "[data-testid='loading']")
wait.until(EC.invisibility_of_element_located(SPINNER))
wait.until(EC.visibility_of_element_located(CONTENT))
```

Waiting for the spinner to *appear* first is a race; wait for the content and
the spinner's disappearance together with `EC.all_of(...)` when the spinner may
already be gone.

## Compound conditions

```python
wait.until(EC.all_of(
    EC.invisibility_of_element_located(SPINNER),
    EC.visibility_of_element_located(RESULTS),
))
wait.until(EC.any_of(EC.url_contains("/dashboard"), EC.visibility_of_element_located(MFA_PROMPT)))
```

## Native `<select>` vs. custom dropdown

```python
from selenium.webdriver.support.ui import Select

Select(wait.until(EC.visibility_of_element_located(COUNTRY))).select_by_value("ES")
```

`Select` works only on a real `<select>`. For a custom widget, use its actual
controls: open the trigger, wait for the option list, click the option by its
text or `data-value`, then verify the trigger now shows the chosen value.

## Dependent dropdowns

```python
Select(driver.find_element(*PROVINCE)).select_by_visible_text("Madrid")
wait.until(lambda d: len(Select(d.find_element(*CITY)).options) > 1)  # repopulated
Select(driver.find_element(*CITY)).select_by_visible_text("Alcalá de Henares")
```

## Table rows by named column

```python
row = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "tr[data-id='4711']")))
status = row.find_element(By.CSS_SELECTOR, "[data-field='status']").text
```

Never `row.find_elements(By.TAG_NAME, "td")[3]`: one inserted column silently
shifts every value in the dataset.

## Iframe, safely scoped

```python
from contextlib import contextmanager

@contextmanager
def inside(frame_locator):
    wait.until(EC.frame_to_be_available_and_switch_to_it(frame_locator))
    try:
        yield
    finally:
        driver.switch_to.default_content()

with inside((By.CSS_SELECTOR, "iframe[title='Payment']")):
    wait.until(EC.visibility_of_element_located(CARD_NUMBER)).send_keys(number)
```

## New tab without trusting handle order

```python
original = driver.current_window_handle
known = set(driver.window_handles)
wait.until(EC.element_to_be_clickable(OPEN_REPORT)).click()
handle = wait.until(lambda d: next(iter(set(d.window_handles) - known), False))
driver.switch_to.window(handle)
...
driver.close()
driver.switch_to.window(original)
```

## Open shadow root

```python
host = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "settings-panel")))
root = host.shadow_root
root.find_element(By.CSS_SELECTOR, "button.save").click()
```

`ShadowRoot` supports only `CSS_SELECTOR` lookups. Closed roots are inaccessible
by design — do not try to break them.

## File upload, including a visually hidden input

```python
from pathlib import Path

upload = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
upload.send_keys(str(Path("data/document.pdf").resolve()))
wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='upload-ok']")))
```

`send_keys` works on a hidden `input[type=file]`; you do not need to click the
styled button. For a remote session, set `driver.file_detector = LocalFileDetector()`.

## Multiple files

```python
upload.send_keys("\n".join(str(p.resolve()) for p in paths))  # input must have `multiple`
```

## Verified download

```python
before = {p for p in download_dir.iterdir() if p.is_file()}
wait.until(EC.element_to_be_clickable(EXPORT)).click()
# then poll the filesystem: no .crdownload/.part, size stable, magic bytes right
```

Use `sentinel.wait_for_download(download_dir, pattern="*.xlsx", before=before)`.
A click that returns without an exception proves nothing about the file.

## Hover menu

```python
from selenium.webdriver import ActionChains

menu = wait.until(EC.visibility_of_element_located(MENU))
ActionChains(driver).move_to_element(menu).perform()
wait.until(EC.element_to_be_clickable(MENU_ITEM)).click()
```

## Keyboard shortcuts and modifiers

```python
from selenium.webdriver import ActionChains, Keys

ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
driver.find_element(*SEARCH).send_keys("query", Keys.ENTER)
```

Use `Keys`, never raw scan codes. On macOS the modifier is `Keys.COMMAND`.

## Scroll

```python
ActionChains(driver).scroll_to_element(element).perform()      # preferred
ActionChains(driver).scroll_by_amount(0, 800).perform()
driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
```

## Drag and drop

```python
ActionChains(driver).drag_and_drop(source, target).perform()
```

HTML5 drag-and-drop implemented with custom pointer events often ignores this.
Fall back to `click_and_hold` → `move_to_element` → small `move_by_offset` →
`release`, and verify the resulting state rather than the gesture.

## Login through the real flow

```python
import os

driver.get(f"{base_url}/login")
wait.until(EC.visibility_of_element_located(USERNAME)).send_keys(os.environ["APP_USER"])
driver.find_element(*PASSWORD).send_keys(os.environ["APP_PASSWORD"])
wait.until(EC.element_to_be_clickable(SUBMIT)).click()
wait.until(EC.visibility_of_element_located(AUTHENTICATED_MARKER))
```

Credentials come from the environment or a secret manager. Never log them, never
put them in a URL, never screenshot the filled form. Wait for an authenticated
marker, not for the URL alone.

## Session reuse via cookies (only with a documented reason)

```python
driver.get(base_url)                       # must be on the cookie's domain first
for cookie in stored_cookies:
    driver.add_cookie(cookie)
driver.get(f"{base_url}/dashboard")
wait.until(EC.visibility_of_element_located(AUTHENTICATED_MARKER))
```

Stored cookies are credentials: encrypt at rest, restrict access, expire them,
and never commit them. Prefer a fresh login when it is practical.

## Screenshots as evidence

```python
driver.save_screenshot(str(evidence_dir / "checkout-failed.png"))   # viewport
element.screenshot(str(evidence_dir / "error-banner.png"))          # one element
```

Review sensitivity before storing anything shared. Use
`ArtifactStore.failure_bundle()` to get screenshot + sanitized context together.

## Print a page to PDF

```python
import base64
from selenium.webdriver.common.print_page_options import PrintOptions

options = PrintOptions()
options.page_ranges = ["1-2"]
pdf = driver.print_page(options)
Path("evidence/page.pdf").write_bytes(base64.b64decode(pdf))
```

## Read a value the DOM formats differently from the attribute

```python
element.get_attribute("value")       # the live property, falling back to the attribute
element.get_dom_attribute("value")   # the literal HTML attribute
element.get_property("value")        # the current DOM property
```

For an input the user has typed into, `get_property("value")` is the truth.

## Bounded retry of an idempotent navigation

```python
from selenium.common.exceptions import TimeoutException
from sentinel import retry_transient

page = retry_transient(
    lambda: open_listing(driver, cfg, url),
    attempts=3,
    retry_on=(TimeoutException,),
    throttle=throttle,
    label="open_listing",
)
```

Never wrap a submit, payment, upload, creation, or deletion this way. For those,
query the authoritative state first and decide whether recovery is safe.
