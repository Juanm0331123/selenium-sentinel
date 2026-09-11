# Official Selenium Python API Coverage

This reference indexes the public Selenium Python API and the official Selenium documentation represented by `selenium-sentinel`. It is an operational coverage map, not a copy of Selenium's source or a promise that every browser implements every capability.

Baseline: Selenium Python 4.49.0 documentation, Python 3.10+, consulted September 2026. Confirm the installed Selenium package, browser, driver, Grid, and OS before using version-sensitive features. Prefer the installed package API and release notes when they conflict with this reference.

Primary sources:

- <https://www.selenium.dev/selenium/docs/api/py/api.html>
- <https://www.selenium.dev/selenium/docs/api/py/>
- <https://www.selenium.dev/documentation/webdriver/>
- <https://github.com/SeleniumHQ/selenium/tree/trunk/py>

## Supported Runtimes And Driver Resolution

Selenium supports Python 3.10+ and Chrome, Edge, Firefox, Safari, WebKitGTK, WPEWebKit, and Remote WebDriver where the browser/driver provides the needed capability. Selenium Manager normally discovers compatible browsers and drivers when a local WebDriver is created without an explicit executable.

Use Selenium Manager first. Its browser management, cache, proxy, mirror, offline, TTL, telemetry, version, and configuration behavior changes by Selenium release. Its official guide is <https://www.selenium.dev/documentation/selenium_manager/>. Use a manually configured `Service` only for an operationally justified driver path or log configuration. Do not introduce a separate driver-manager package by default.

Public setup families:

- `webdriver.Chrome`, `webdriver.Edge`, `webdriver.Firefox`, `webdriver.Safari`, `webdriver.WebKitGTK`, `webdriver.WPEWebKit`.
- `webdriver.Remote(command_executor, options=...)` for a trusted remote/Grid endpoint.
- Browser `Options`, `Service`, `Proxy`, `ClientConfig`, and W3C capabilities.
- `SeleniumManager` only through supported configuration, not by depending on implementation details.

## WebDriver Session And Navigation

Use the WebDriver public lifecycle and navigation surface:

- `get(url)`, `back()`, `forward()`, `refresh()`.
- `quit()` for final session termination; `close()` only to close a known current context.
- `current_url`, `title`, `page_source`, `name`, `session_id`, and `capabilities` for controlled verification and diagnostics.
- `start_client()` and `stop_client()` are lifecycle hooks; do not override them unless maintaining a supported custom driver implementation.
- `get_screenshot_as_png()`, `get_screenshot_as_base64()`, `get_screenshot_as_file()`, and `save_screenshot()` for redacted failure evidence.
- `print_page(PrintOptions)` for browser-supported print output. Treat the returned output as sensitive if it contains private page data.

Do not call the low-level `execute(command, params)` as a general escape hatch. It exposes protocol internals, is harder to make portable, and should be confined to a version-pinned integration with a documented reason.

Official source: <https://www.selenium.dev/selenium/docs/api/py/selenium_webdriver_remote/selenium.webdriver.remote.webdriver.html>

## Timeouts And Waits

Public timeout methods are `implicitly_wait(time_to_wait)`, `set_page_load_timeout(time_to_wait)`, and `set_script_timeout(time_to_wait)`. `driver.timeouts` exposes the active timeout configuration.

Use an explicit `WebDriverWait(driver, timeout, poll_frequency, ignored_exceptions)` and `until` or `until_not` for asynchronous state. Do not mix implicit and explicit waits because Selenium documents unpredictable combined timeouts. Do not use `time.sleep()` for normal synchronization.

Official expected conditions include:

- Alerts: `alert_is_present`.
- Element presence/visibility: `presence_of_element_located`, `presence_of_all_elements_located`, `visibility_of_element_located`, `visibility_of`, `visibility_of_all_elements_located`.
- Invisibility: `invisibility_of_element_located`, `invisibility_of_element`.
- Clickability and selection: `element_to_be_clickable`, `element_to_be_selected`, `element_located_to_be_selected`, `element_selection_state_to_be`.
- DOM replacement: `staleness_of`.
- Frames: `frame_to_be_available_and_switch_to_it`.
- Text/value: `text_to_be_present_in_element`, `text_to_be_present_in_element_value`, `text_to_be_present_in_element_attribute`.
- URLs/titles: `url_to_be`, `url_contains`, `url_matches`, `url_changes`, `title_is`, `title_contains`.
- Window counts: `number_of_windows_to_be`, `new_window_is_opened`.
- Compound conditions: `all_of`, `any_of`, `none_of`.

Use a narrow custom predicate only when these conditions cannot express the authoritative state. It must be side-effect free, bounded by the wait, and tolerate only expected transient exceptions.

Sources: <https://www.selenium.dev/documentation/webdriver/waits/> and <https://www.selenium.dev/documentation/webdriver/support_features/expected_conditions/>.

## Element Discovery And Locators

`By` supports `ID`, `NAME`, `XPATH`, `LINK_TEXT`, `PARTIAL_LINK_TEXT`, `TAG_NAME`, `CLASS_NAME`, and `CSS_SELECTOR`. Use `driver.find_element(s)` or `element.find_element(s)` only in the known active window/frame/shadow context.

Public element identity/data surfaces:

- Content/state: `text`, `tag_name`, `accessible_name`, `aria_role`, `is_displayed()`, `is_enabled()`, `is_selected()`.
- Attributes/properties: `get_attribute()`, `get_dom_attribute()`, `get_property()`, `value_of_css_property()`.
- Geometry: `rect`, `location`, `size`, `location_once_scrolled_into_view`.
- Interaction: `click()`, `clear()`, `send_keys()`, `submit()`.
- Evidence: `screenshot()`, `get_screenshot_as_png()`, `get_screenshot_as_base64()`, `get_screenshot_as_file()`.

Use standard locators before relative locators. The relative-locator API (`locate_with`, `with_tag_name`, `above`, `below`, `to_left_of`, `to_right_of`, `near`) depends on rendered layout and can be unstable with responsive designs, overlapping elements, or virtualized content.

Sources: <https://www.selenium.dev/documentation/webdriver/elements/locators/>, <https://www.selenium.dev/documentation/webdriver/elements/finders/>, and <https://www.selenium.dev/documentation/webdriver/elements/information/>.

## Standard Element Interaction

Use `click`, `clear`, and `send_keys` for normal controls, and verify a business-observable result afterward. Selenium's interactability model can scroll elements into view and checks visible size/viewport conditions; an intercepted or non-interactable click is diagnostic information, not a reason to bypass the UI with JavaScript.

Use `Select` only for a native HTML `<select>`. Its supported operations are `select_by_index`, `select_by_value`, `select_by_visible_text`, `deselect_all`, `deselect_by_index`, `deselect_by_value`, `deselect_by_visible_text`, `options`, `all_selected_options`, `first_selected_option`, and `is_multiple`. Custom dropdowns require normal WebDriver interaction with their real controls.

Source: <https://www.selenium.dev/documentation/webdriver/elements/interactions/> and <https://www.selenium.dev/documentation/webdriver/support_features/select_lists/>.

## Actions API

Use `ActionChains` for genuine keyboard, pointer, wheel, hover, drag, modifier, and context-menu workflows. Call `perform()` to dispatch queued actions.

Main `ActionChains` operations: `click`, `click_and_hold`, `context_click`, `double_click`, `drag_and_drop`, `drag_and_drop_by_offset`, `key_down`, `key_up`, `move_by_offset`, `move_to_element`, `move_to_element_with_offset`, `pause`, `release`, `reset_actions`, `scroll_by_amount`, `scroll_from_origin`, `scroll_to_element`, and `send_keys`/`send_keys_to_element`.

For lower-level devices use `ActionBuilder`, `KeyInput`, `PointerInput`, `WheelInput`, and `PointerActions`; keep such code isolated and call `clear_actions()` if an interrupted action may leave input state active. Use `Keys` for defined keyboard values, not hard-coded platform scan codes.

Source: <https://www.selenium.dev/documentation/webdriver/actions_api/>.

## Browsing Contexts

`driver.switch_to` provides `active_element`, `alert`, `default_content()`, `frame(frame_reference)`, `parent_frame()`, `window(window_name)`, and `new_window(type_hint)`.

- Frames: wait with `frame_to_be_available_and_switch_to_it`; use `parent_frame` or `default_content` before looking outside the selected frame.
- Windows/tabs: use `current_window_handle`, `window_handles`, wait for the handle count/change, then select a deterministic handle. `WindowTypes.TAB` and `WindowTypes.WINDOW` request a new context.
- Alerts: use `alert_is_present`, then inspect `text`, `accept()`, `dismiss()`, or `send_keys()` only as the authorized flow requires.
- Configure `unhandled_prompt_behavior` in options when appropriate; never suppress a confirmation to defeat a safety boundary.

Sources: <https://www.selenium.dev/documentation/webdriver/interactions/frames/>, <https://www.selenium.dev/documentation/webdriver/interactions/windows/>, and <https://www.selenium.dev/documentation/webdriver/interactions/alerts/>.

## Shadow DOM And JavaScript

For an open root, use `element.shadow_root`, then `ShadowRoot.find_element(s)`. Closed roots cannot be traversed by WebDriver and must not be bypassed.

Use `execute_script(script, *args)` and `execute_async_script(script, *args)` only if standard WebDriver has no suitable operation or for controlled diagnostics. Pass values through arguments rather than interpolating strings. Do not use script clicks to hide timing, overlay, or authorization defects.

Sources: <https://www.selenium.dev/documentation/webdriver/elements/finders/> and <https://www.selenium.dev/documentation/webdriver/interactions/>

## Windows, Display, Permissions, And Cookies

Public window management: `get_window_rect`, `set_window_rect`, `get_window_position`, `set_window_position`, `get_window_size`, `set_window_size`, `maximize_window`, `minimize_window`, and `fullscreen_window`. Set deterministic dimensions where responsive layout changes the tested workflow; avoid coordinate-dependent assertions.

Public cookie operations: `get_cookies`, `get_cookie`, `add_cookie`, `delete_cookie`, and `delete_all_cookies`. Navigate to the matching domain before adding a cookie. Cookies and browser profiles are secrets.

Use browser options for permission prompts and certificate policy. Do not use permissions or cookies to bypass authentication, user consent, or access control.

Source: <https://www.selenium.dev/documentation/webdriver/interactions/cookies/>.

## Files And Downloads

Upload using an actual `input[type=file]` and `send_keys` with an absolute path. For a remote session, configure the documented `LocalFileDetector` path when files originate on the client rather than the node.

Some remote implementations expose `get_downloadable_files`, `download_file`, and `delete_downloadable_files`. They are not a portable replacement for browser download configuration. Downloads need a unique configured directory, a wait for completed bytes rather than partial browser files, and verification of expected name/type/size before use.

Sources: <https://www.selenium.dev/documentation/webdriver/elements/file_upload/> and <https://www.selenium.dev/documentation/test_practices/discouraged/>.

## Options, Capabilities, Services, And Proxy

All browser options inherit common capability support such as `browser_version`, `platform_name`, `accept_insecure_certs`, `page_load_strategy`, `proxy`, `timeouts`, `unhandled_prompt_behavior`, `strict_file_interactability`, `web_socket_url`, and `enable_bidi` where supported.

`BaseOptions.enable_mobile()` is driver-specific emulation/configuration, not native mobile-app automation. `ignore_local_proxy_environment_variables()` is available, but newer code should prefer an explicit `ProxyType.DIRECT` configuration where the API documents the older path as deprecated.

Browser-specific options, extensions, profiles, preferences, binary paths, debugger addresses, Chromium experimental options, Firefox profile/log options, and Safari behavior are not portable. Put them in environment-specific configuration and test the exact browser matrix. Use `Service` for supported executable/log settings. Use `Proxy` only for an approved network route.

Do not rely on legacy `DesiredCapabilities` dictionaries when `Options` can express W3C capabilities. For Remote, `options` can be one `BaseOptions` object or a list for capability matching. `ClientConfig` controls remote transport details such as endpoint security; protect remote credentials and use TLS.

Sources: <https://www.selenium.dev/documentation/webdriver/drivers/options/>, <https://www.selenium.dev/documentation/webdriver/drivers/service/>, <https://www.selenium.dev/documentation/webdriver/drivers/remote_webdriver/>, and <https://www.selenium.dev/documentation/webdriver/browsers/>.

## Remote WebDriver And Grid

Use `webdriver.Remote` for authorized remote browser execution. Grid adds deployment concerns: trusted endpoints, session isolation, artifacts on nodes, file detectors, capacity, browser version matching, and unique profile/download/account/data paths per worker.

Grid also documents observability, GraphQL, HTTP endpoints, node customization, and external datastores. `fire_session_event(event_type, payload)` is a Grid-side event utility, not a browser event system. Use advanced Grid APIs only when operating Grid intentionally.

Sources: <https://www.selenium.dev/documentation/grid/>, <https://www.selenium.dev/documentation/grid/advanced_features/>, and <https://www.selenium.dev/documentation/grid/architecture/>.

## WebDriver BiDi And CDP

WebDriver BiDi is the preferred event-driven extension when standard WebDriver is insufficient and the installed binding/browser/Grid negotiate support. Enable it with `options.enable_bidi = True`, then use the documented public surfaces exposed by the driver: `browser`, `browsing_context`, `script`, `network`, `storage`, `permissions`, `webextension`, `emulation`, and `input`.

Use BiDi for authorized diagnostics, events, scripts, browsing contexts, and supported network behavior. Capability-detect and version-test every use. Do not use it to intercept secrets, alter protections, evade limits, or bypass controls.

`start_devtools()`, `import_cdp()`, raw CDP commands, and modules marked internal are Chromium-specific or implementation-sensitive. Prefer standard WebDriver, then public BiDi, then an isolated, pinned CDP integration only if no public alternative exists. Deprecated `pin_script`, `unpin`, and `get_pinned_scripts` should not be used in new code; use public BiDi script APIs where available.

Sources: <https://www.selenium.dev/documentation/webdriver/bidi/>, <https://www.selenium.dev/documentation/webdriver/bidi/network/>, <https://www.selenium.dev/documentation/warnings/bidi-implementation/>, and <https://www.selenium.dev/documentation/webdriver/browsers/chrome/>.

## WebAuthn Virtual Authenticators And FedCM

Virtual authenticators are for owned WebAuthn/passkey tests and are Chromium-based in the Python binding. The public operations include `add_virtual_authenticator`, `remove_virtual_authenticator`, `virtual_authenticator_id`, `add_credential`, `get_credentials`, `remove_credential`, `remove_all_credentials`, and `set_user_verified`. Configure `VirtualAuthenticatorOptions` with supported `Protocol` values (`CTAP2`, `U2F`) and `Transport` values (`USB`, `NFC`, `BLE`, `INTERNAL`). Do not use these facilities against third-party identity systems or to defeat MFA.

FedCM support is browser/version dependent. Its public dialog operations include account selection, dialog title/type/account inspection, delay configuration, cooldown reset, cancel, and dialog-button clicks. Use it only in controlled identity-provider and relying-party tests owned by the team; protect account data and never automate consent deceptively.

Sources: <https://www.selenium.dev/selenium/docs/api/py/selenium_webdriver_common/selenium.webdriver.common.virtual_authenticator.html> and <https://www.selenium.dev/documentation/webdriver/interactions/fedcm/>.

## HTTP Request Context

`WebDriver.request` exposes an `APIRequestContext` synchronized with browser cookies. It can support controlled test setup or verification when it complements, rather than replaces, required UI coverage. Do not use it as a way to circumvent UI authorization, security controls, rate limits, or a service's intended access model. Protect response data, request bodies, and cookies.

Source: <https://www.selenium.dev/selenium/docs/api/py/selenium_webdriver_remote/selenium.webdriver.remote.webdriver.html>

## Logging, Errors, And Debugging

Relevant public exception classes include `NoSuchElementException`, `TimeoutException`, `StaleElementReferenceException`, `ElementClickInterceptedException`, `ElementNotInteractableException`, `InvalidSelectorException`, `UnexpectedAlertPresentException`, `NoAlertPresentException`, `NoSuchFrameException`, `NoSuchWindowException`, `InvalidSessionIdException`, `SessionNotCreatedException`, `WebDriverException`, `JavascriptException`, `MoveTargetOutOfBoundsException`, and `InvalidArgumentException`.

Diagnose root state, context, selector, browser/driver compatibility, and infrastructure before adding waits or retries. Capture sanitized URL/title/window/frame information, screenshot, permitted page source, service/browser logs, versions, and traceback. Do not expose secrets or sensitive content in artifacts.

The legacy EventFiringWebDriver/EventListener approach is not a default observability design. Prefer the project's structured logs and supported BiDi/browser logging where available. Browser `get_log`/`log_types` support varies and should be capability-checked.

Sources: <https://www.selenium.dev/documentation/webdriver/troubleshooting/errors/>, <https://www.selenium.dev/documentation/webdriver/troubleshooting/logging/>, and <https://www.selenium.dev/documentation/webdriver/troubleshooting/>

## Test Practice And Safety

Use fresh sessions, independent tests, explicit assertions, deterministic test data, and cleanup. Prefer unit/API tests for non-browser logic. Selenium specifically discourages CAPTCHAs, two-factor authentication, link-spidering, and performance testing as WebDriver automation targets.

Never automate or validate a real state-changing workflow, integration, upload, payment, issuance, deletion, or external side effect without explicit authorization. Never implement CAPTCHA/MFA/bot-detection/access-control bypasses. Keep credentials, cookies, tokens, profiles, downloads, screenshots, and private DOM captures out of source control.

Sources: <https://www.selenium.dev/documentation/test_practices/>, <https://www.selenium.dev/documentation/test_practices/encouraged/fresh_browser_per_test/>, and <https://www.selenium.dev/documentation/test_practices/discouraged/>.

## Public Versus Internal Boundary

Use documented WebDriver, WebElement, `By`, waits, expected conditions, options/services, actions, `Select`, Remote/Grid, and high-level BiDi APIs. Treat package-private modules, low-level command executors, raw protocol payloads, generated devtools bindings, Selenium Manager internals, and undocumented browser preferences as unstable. If one is unavoidable, isolate it, pin Selenium/browser versions, capability-test it, document the reason, and provide a safe failure path.
