# Selenium Sentinel

[![skills.sh](https://skills.sh/b/Juanm0331123/selenium-sentinel)](https://skills.sh/Juanm0331123/selenium-sentinel)

A comprehensive, safety-first Selenium Python skill for building reliable WebDriver automation, testing, scraping, diagnostics, Grid, and BiDi workflows.

## Install

Install with the Skills CLI:

```bash
npx skills add Juanm0331123/selenium-sentinel
```

Restart your coding agent after installation so it discovers the new skill.

## What It Covers

- Selenium Manager, browser options, services, capabilities, proxies, and driver lifecycle.
- Stable locators, explicit waits, expected conditions, stale elements, and synchronization.
- Forms, keyboard/pointer/wheel actions, frames, windows, tabs, alerts, shadow DOM, and JavaScript.
- Cookies, sessions, authorized authentication flows, uploads, downloads, and data extraction.
- Screenshots, logs, diagnostics, exception classification, bounded recovery, and artifact hygiene.
- Remote WebDriver, Selenium Grid, WebDriver BiDi, CDP boundaries, WebAuthn virtual authenticators, FedCM, and request contexts.
- Browser differences, testing strategy, code-review checks, and production-safe delivery practices.

The skill includes an indexed reference of the public Selenium Python API and official documentation feature families. It is versioned against Selenium Python 4.49.0 and requires agents to verify the installed Selenium and browser versions before using version-sensitive capabilities.

## Safety Boundaries

Selenium Sentinel is for authorized automation only. It explicitly rejects CAPTCHA solving, bot-detection evasion, MFA bypasses, access-control bypasses, rate-limit evasion, and unapproved production side effects. It also requires secret redaction and verification before non-idempotent actions are retried.

## Repository Layout

```text
skills/
  selenium-sentinel/
    SKILL.md
    references/
      official-python-api-coverage.md
```

## Sources

- [Selenium Python API](https://www.selenium.dev/selenium/docs/api/py/api.html)
- [Selenium WebDriver documentation](https://www.selenium.dev/documentation/webdriver/)
- [Selenium Python source](https://github.com/SeleniumHQ/selenium/tree/trunk/py)

## Contributing

Keep all guidance generic and reusable. Do not add organization names, credentials, private URLs, customer workflows, proprietary selectors, or instructions that circumvent security controls. Update version-sensitive guidance only after checking the official Selenium documentation and source.

## License

[MIT](LICENSE)
