# Changelog

All notable changes to Selenium Sentinel are documented in this file.

The project follows [Semantic Versioning](https://semver.org/) and uses the format described by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.1.0] - 2026-09-11

### Added

- `sentinel/` drop-in toolkit: `RunConfig` with per-run isolated directories, `driver_session()` with guaranteed teardown, explicit-wait helpers, bounded pagination strategies, column-contract extraction with validation and provenance, filesystem-verified downloads, redacting structured logging, failure evidence bundles, JSONL/CSV sinks, resumable checkpoints, politeness throttling, and bounded retry for idempotent operations.
- `scripts/selenium_doctor.py` environment diagnostics with an optional real headless launch check.
- `assets/scraper_template.py` runnable paginated-scrape skeleton and `assets/conftest.py` pytest fixtures with automatic failure evidence.
- References: `recipes.md`, `scraping-playbook.md`, `troubleshooting.md`, `browser-environments.md`, and `scale-and-remote.md`.

### Changed

- `SKILL.md` restructured around an explicit operating loop (triage, reconnaissance, contracts, build, verify, report), a non-negotiables list, quick-start code, and routing to the bundled toolkit, scripts, and references.
- README documents the toolkit, the environment doctor, and the expanded repository structure.

### Fixed

- Removed a stray non-pattern line from `.gitignore` and added run-output exclusions.

## [1.0.0] - 2026-09-10

### Added

- Initial public release of the Selenium Sentinel skills.sh package.
- Authorized Selenium Python WebDriver guidance for implementation, debugging, review, diagnostics, remote execution, Grid, and version-sensitive features.
- Safety boundaries for security controls, sensitive data, retries, and state-changing external actions.
- Official Selenium Python API coverage reference.

[Unreleased]: https://github.com/Juanm0331123/selenium-sentinel/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Juanm0331123/selenium-sentinel/releases/tag/v1.1.0
[1.0.0]: https://github.com/Juanm0331123/selenium-sentinel/releases/tag/v1.0.0
