# Selenium Sentinel

[![skills.sh](https://skills.sh/b/Juanm0331123/selenium-sentinel)](https://skills.sh/Juanm0331123/selenium-sentinel)

`selenium-sentinel` is a reusable skills.sh package for agents that design, implement, debug, review, and harden authorized Python Selenium WebDriver automation. It turns established Selenium guidance into practical guardrails for reliable browser tests, data extraction, and UI workflows.

## What It Does

The skill helps an agent make deliberate, version-aware choices across the Selenium Python surface:

- Build and clean up local, remote, and Grid WebDriver sessions.
- Choose stable locators and explicit waits; diagnose timing, stale-element, context, and interaction failures.
- Work with forms, frames, windows, alerts, shadow DOM, uploads, downloads, cookies, browser actions, and diagnostics.
- Use browser-specific options, Selenium Manager, WebDriver BiDi, CDP boundaries, Grid, WebAuthn virtual authenticators, FedCM, and request contexts only when appropriate and supported.
- Keep retries bounded and idempotent, isolate browser state, verify meaningful outcomes, and protect diagnostic artifacts.
- Review automation changes for lifecycle, synchronization, portability, observability, and safety risks.

The package includes a reference index of public Selenium Python APIs and official documentation families. It is a guide, not a Selenium replacement: always confirm the installed Selenium package, browser, driver, Grid, and operating environment before using version-sensitive features.

## Safety Boundaries

Selenium Sentinel is for authorized automation and testing. It does not provide guidance for bypassing CAPTCHAs, bot detection, MFA, rate limits, paywalls, authentication, authorization, or other security controls.

It also treats state-changing actions carefully. Do not use automation to submit, upload, issue, pay, delete, or invoke an external integration merely to validate code unless the action has explicit authorization. Keep credentials, cookies, tokens, private profiles, sensitive screenshots, and raw private page content out of source control and logs.

## Install

Install the package with the Skills CLI:

```bash
npx skills add Juanm0331123/selenium-sentinel
```

For a new installation, the CLI fetches the GitHub-hosted skill and places it where supported coding agents can discover it. Restart the agent if it does not load newly installed skills during the current session.

> [!IMPORTANT]
> skills.sh discovers GitHub skills after they are installed through its CLI. It is not a manual upload portal, so maintainers publish this repository through normal Git and GitHub releases rather than uploading a package to skills.sh.

## Update

Update all installed skills:

```bash
npx skills update
```

To update only this skill, use the CLI's single-skill form:

```bash
npx skills update selenium-sentinel
```

After an update, restart the coding agent when needed so it reloads the installed skill files. Consult the Skills CLI help if your installed CLI version uses a different selector syntax.

## Compatibility

- **Agents:** Designed for coding agents that support the skills.sh installation layout and Markdown skill instructions.
- **Python:** The included API reference uses Python 3.10+ as its baseline.
- **Selenium:** The reference baseline is Selenium Python 4.49.0. APIs may differ in earlier or later releases.
- **Browsers and drivers:** Chrome, Edge, Firefox, Safari, WebKitGTK, WPEWebKit, and Remote WebDriver are covered where the installed Selenium binding and browser/driver implementation provide the required capability.
- **Advanced features:** Selenium Manager, downloads, browser options, Grid, BiDi, CDP, WebAuthn, FedCM, and request contexts vary by Selenium version, browser, driver, operating system, and remote provider. Detect support and test the exact deployment matrix.

## Repository Structure

```text
.
├── README.md
│   Public package documentation, installation, updates, and maintenance policy.
├── CHANGELOG.md
│   User-visible release history following Keep a Changelog-style categories.
├── LICENSE
│   MIT license terms.
├── .gitignore
│   Repository exclusions for local and generated files.
└── skills/
    └── selenium-sentinel/
        ├── SKILL.md
        │   Agent-facing Selenium operating guidance and safety requirements.
        └── references/
            └── official-python-api-coverage.md
                Coverage map for public Selenium Python APIs and official sources.
```

`SKILL.md` is the operational entry point. Its reference file expands coverage for unfamiliar or version-sensitive Selenium features; it does not promise universal browser support.

## Versioning And Releases

This repository follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: incompatible changes to the skill's instructions, safety contract, or expected agent behavior.
- **MINOR**: backward-compatible new Selenium coverage, workflows, or significant guidance.
- **PATCH**: backward-compatible corrections, clarifications, source updates, and documentation fixes.

Release notes belong in `CHANGELOG.md`. Keep an `Unreleased` section for changes that have not been tagged. Version tags use `vX.Y.Z`; the matching release version is `X.Y.Z`.

### Maintainer Release Process

1. Review the intended change, update `CHANGELOG.md`, and confirm every example is generic, authorized, and based on official Selenium sources.
2. Run the applicable quality checks. At minimum, inspect the documentation and run:

   ```bash
   git diff --check
   ```

   Run any configured Markdown linting or repository checks as well. Do not run browser workflows that could cause external side effects solely as a release check.

3. Commit the release with a Conventional Commit message, for example:

   ```bash
   git commit -m "chore(release): vX.Y.Z"
   ```

4. Create an annotated tag and push the release commit and tag:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin HEAD
   git push origin vX.Y.Z
   ```

5. Create a GitHub Release from `vX.Y.Z`. Its notes should summarize user-visible changes, compatibility implications, upgrade steps, and any known limitations.

Once the tag and release are available on GitHub, skills.sh users obtain the package and later updates through the Skills CLI. No manual upload to skills.sh is required or expected.

## Upgrading As A User

1. Review `CHANGELOG.md` for the target version, especially MAJOR-release migration notes.
2. Run `npx skills update` or `npx skills update selenium-sentinel`.
3. Restart the coding agent if it does not reload installed skills automatically.
4. For version-sensitive Selenium work, confirm the agent's project uses compatible Selenium and browser versions before relying on changed guidance.

## Official Selenium Sources

- [Selenium Python API](https://www.selenium.dev/selenium/docs/api/py/api.html)
- [Selenium Python package guide](https://www.selenium.dev/selenium/docs/api/py/)
- [Selenium WebDriver documentation](https://www.selenium.dev/documentation/webdriver/)
- [Selenium Manager documentation](https://www.selenium.dev/documentation/selenium_manager/)
- [WebDriver BiDi documentation](https://www.selenium.dev/documentation/webdriver/bidi/)
- [Selenium Grid documentation](https://www.selenium.dev/documentation/grid/)
- [Selenium Python source](https://github.com/SeleniumHQ/selenium/tree/trunk/py)

This project is available under the [MIT License](LICENSE). Contributions must remain generic, source-backed, and free of credentials, private URLs, customer data, proprietary selectors, or security-bypass instructions.
