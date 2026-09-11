# Scraping Playbook

End-to-end procedure for an authorized Selenium scrape. Follow the phases in
order; each one produces an artifact the next phase depends on.

## Phase 0 — Is Selenium the right tool?

Answer before writing code. In order of preference:

1. **Official API or bulk export.** Faster, stable, contractual. Ask the site
   owner or check the developer portal before assuming none exists.
2. **Static HTTP + parser** (`requests` + `selectolax`/`lxml`). Correct when the
   HTML arrives complete. Test: `curl -s <url> | grep <a value you need>`. If the
   value is in the response, a browser is unnecessary overhead.
3. **Internal JSON endpoint the page itself calls.** Open DevTools → Network →
   Fetch/XHR. If the listing is fed by a documented-shape JSON endpoint, and
   using it is within your authorization, it is cheaper and far more stable than
   DOM scraping. Do not use it to route around access control or rate limits.
4. **Selenium.** Justified when rendering, authenticated UI state, interaction
   (filters, wizards, canvas, file generation) or JS-built DOM is required.

Record the reason in the project. "Selenium because it is familiar" is not one.

## Phase 1 — Authorization and limits

Settle before the first request:

- Who authorized this scrape, and of what scope (accounts, data, volume)?
- What do the site's terms and `robots.txt` say about automated access?
- Which fields are personal data? What is the lawful basis, retention, and
  storage location for them?
- What request rate is acceptable? Default to conservative: 1 page per 1–3s,
  single session, no parallelism against one target unless explicitly cleared.
- What is the stop rule? `403`, `429`, a block page, a CAPTCHA appearing, or a
  terms change all mean **stop and escalate** — never work around them.

If a CAPTCHA, bot-detection interstitial, or MFA gate appears, the scrape is
over until a human resolves the access question. Do not add evasion.

## Phase 2 — Reconnaissance

Do this with a visible browser and DevTools before writing a line of workflow code.

| Question | How to settle it |
| --- | --- |
| Is content server-rendered or JS-built? | View source vs. Elements panel |
| What proves "the page is ready"? | The element the next action needs, not `readyState` |
| Are there iframes or shadow roots? | DevTools Elements: `#shadow-root`, `<iframe>` |
| What is the row/cell structure? | Pick per-column attribute selectors, never indexes |
| Does the site expose a total count? | "N results" label — the completeness oracle |
| How does pagination work? | URL parameter, Next button, infinite scroll, cursor |
| What are the failure states? | Empty results, error banner, session expiry, rate-limit page |
| Which selectors are stable? | `data-*`, `name`, `aria-label`, ids that are not hashed |
| Does content change per viewport? | Resize; mobile layouts often use different DOM |

Output of this phase: a **locator contract** (named locators) and a **column
contract** (field name → locator), both written down in one module.

## Phase 3 — Extraction contract

Define the dataset before extracting it:

- Field names, types, units, and which are required.
- The unique key per record (used to detect duplicate pages and to deduplicate
  on resume).
- Locale rules: `1.234,56` vs `1,234.56`, `dd/mm/yyyy` vs `mm/dd/yyyy`. Parse
  with explicit formats; never let a library guess.
- The completeness oracle: announced total, last-page marker, or known ID range.
- Provenance fields: source URL, run id, extraction timestamp, parser version.

`sentinel/extract.py` implements this: `rows_to_records`, `validate_records`,
`with_provenance`.

## Phase 4 — Navigation patterns

### Paginated URLs (preferred)

Restartable, independently reproducible, trivially resumable.
`pagination.paginate_by_url(url_for_page=lambda n: f"{base}?page={n}", ...)`

### Next-button pagination

Capture the first row, click Next, wait for `staleness_of(anchor)`, then wait for
the new rows. Never sleep after the click.
`pagination.paginate_by_click(...)`

### Infinite scroll

Scroll the last row into view, then wait for the row count to grow. Terminate on
the announced total, on a settled count, or on the scroll budget.
`pagination.scroll_until_loaded(...)`

### Detail pages behind a listing

Two passes beat one: collect all detail URLs first and persist them, then visit
them as independent work items with a checkpoint. A crash on item 400 then costs
one item, not the listing traversal.

### SPA route changes

The URL can change before the view does. Wait for a marker inside the new view
(a heading, a `data-view` attribute), not for `url_contains` alone.

## Phase 5 — Running it safely

- One driver, one owner, `driver_session()` — guaranteed `quit()`.
- Persist page by page (`JsonlSink` + `Checkpoint`), never only at the end.
- `Throttle` between pages; exponential `back_off()` after a transient failure.
- Hard budgets on everything: pages, scrolls, retries, wall-clock.
- Structured log line per page with count and duration, so a stall is visible.
- On failure: `ArtifactStore.failure_bundle()` then re-raise. Never swallow.

Long runs: check memory. A browser kept open for hours across thousands of
navigations grows. For very long jobs, recycle the driver every N items — the
checkpoint makes that free.

## Phase 6 — Verification before the data is used

A scrape is not done when it finishes without an exception. Check:

1. Record count vs. the announced total (or an explained difference).
2. No duplicate unique keys — duplicates mean a page was harvested twice.
3. Required fields non-empty on every record.
4. Type/shape sanity: dates inside a plausible range, numbers parsed (not `None`
   for a whole column — that is a silent locale or selector break).
5. Spot-check three records against the live page by hand.
6. Field-level null rate compared with the previous run. A column that jumped
   from 2% to 100% null is a layout change, not a data change.

## Phase 7 — Maintenance

Scrapers rot because sites change. Cheap insurance:

- Required-field validation turns a silent layout change into a loud failure.
- Log the per-column null rate each run and alert on a jump.
- Keep a `parser_version` in the output; bump it when selectors change.
- Keep one small "canary" run (page 1 only) that can be run on demand to check
  whether the contract still holds before launching a full job.
- Store the locator contract in one module so a site change is one diff.

## Anti-patterns specific to scraping

- Sleeping after a click instead of waiting for staleness or new content.
- `find_elements(...)[0]` without proving a match exists.
- Positional cell indexes (`row.find_elements(By.TAG_NAME, "td")[3]`).
- Collecting everything in a list and writing once at the end.
- `while True:` over pagination with no page budget.
- Re-scraping from page 1 after every crash instead of checkpointing.
- Treating an empty result set as success without checking for an error state.
- Hiding a `403`/`429` behind a retry loop.
- Rotating user agents, proxies, or fingerprints to avoid being identified as
  automation. Out of scope for this skill.
