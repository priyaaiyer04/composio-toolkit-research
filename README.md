# Composio 100-App Toolkit Research

[View the live case study](https://priyaaiyer04.github.io/composio-toolkit-research/) | [View the source repository](https://github.com/priyaaiyer04/composio-toolkit-research)

A research pass over 100 apps across 10 categories, assessing agent-toolkit readiness: authentication model, self-serve versus gated access, API surface, existing MCP support, buildability verdict, and evidence. The single-page case study also presents the cross-app patterns, research-agent workflow, and verification results.

## Repository layout

```text
index.html               Single self-contained case-study page and final dataset
apps.py                  Python source dataset for all 100 apps
apps_input.json          100-app input list for a fresh agent run
research_agent.py        Runnable first-pass research pipeline (Anthropic + web search)
verification_report.md   20-app verification methodology, results, and corrections
verification_sample.json Machine-readable 20-app verification sample
live_search_log.md       Evidence log for the 10 live-search-first records
check_evidence_links.py  Concurrent HTTP evidence-link checker
evidence_link_report.json Generated report from the latest evidence-link run
verify_artifacts.py      Local data/page consistency validator
README.md                This guide
browser_use_check.py     Playwright browser-use verification pass over all 100 evidence URLs
browser_use_verification.md  Methodology, results, and honest findings from the browser-use pass
```

`index.html` is deployed directly from the repository root using GitHub Pages. It has no build step or runtime API calls.

## Research method

The pipeline asks a web-search-enabled model to find first-party developer documentation for each app and return a strict JSON record containing category, auth, access model, API surface, MCP status, buildability verdict, blocker, and an evidence URL.

The final dataset combines two research paths:

- 10 uncertain or niche apps were researched live first and tagged `source: "live_search"` in `apps.py`.
- 90 mature APIs were drafted from established knowledge, then a stratified 20-app sample was checked against current documentation.

The verification pass found and corrected two first-pass issues: stale Ahrefs access-tier information and an imprecise Otter.ai API/MCP access claim. See [verification_report.md](verification_report.md) for the full sample and methodology.

## Run the research agent

Requirements: Python 3.9+ and an `ANTHROPIC_API_KEY`. The script uses only the Python standard library.

Create an input JSON file containing app names and optional documentation hints:

```json
[
  {"app": "Salesforce", "hint": "salesforce.com"},
  {"app": "HubSpot", "hint": "hubspot.com"}
]
```

Then run:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python research_agent.py --apps apps_input.json --out raw_pass.json
```

The output is a JSON array of strict-schema research records. Review and verify the access-tier and MCP fields against current first-party docs before incorporating new results into the case study; these are the fields most likely to change.

`apps_input.json` contains the complete 100-app research set. Its `hint` values are the retained evidence URLs from the current dataset, so a rerun starts from the same documentation leads rather than an unspecified app list.

## Verification artifacts

The human-check sample is available in [verification_sample.json](verification_sample.json). Each of its 20 records contains the field tested, first-pass result, verified result, outcome, and evidence URL. The ten records researched live from the start are listed separately in [live_search_log.md](live_search_log.md).

You can verify the artifact counts without API credentials:

```powershell
python verify_artifacts.py
```

This verifies the 100-agent input list, the 20-record verification sample, the two documented misses, and that the data embedded in `index.html` matches the source artifacts.

Check the current reachability of all 100 evidence URLs:

```powershell
python check_evidence_links.py --out evidence_link_report.json
```

The report stores every HTTP status, redirect target, response type, elapsed time, and a summary by outcome. `restricted` means a page responded but blocks automated access; it is not treated as a missing source.

## Local viewing and deployment

Open `index.html` directly in a browser to review the page locally. The published version is available at:

<https://priyaaiyer04.github.io/composio-toolkit-research/>

GitHub Pages is configured to publish the repository root, so pushing changes to the configured publishing branch updates the page.

## Scope and limitations

- The reported accuracy is limited to the 20-app stratified sample: 18/20 (90%) before correction and 20/20 (100%) afterward.
- 3 of the 20 sampled apps — Ahrefs, Devin, and Otter.ai — were also flagged live-search-first from the start, since they were already the ones with the least certain public documentation. That overlap is exactly where the two real misses (Ahrefs, Otter.ai) turned up: the apps flagged as needing extra scrutiny were the ones that actually needed it.
- Of the 11 blocked apps, 3 (fanbasis, Consensus, NotebookLM) had no discoverable first-party API documentation at all and are marked blocked rather than guessed. A 4th, iPayX, is marked partial rather than blocked — its docs exist but are too thin to confirm the full API surface, so it's flagged low-confidence instead of filled in.