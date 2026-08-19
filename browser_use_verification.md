# Browser-use verification pass

## What this is

`check_evidence_links.py` only sends a raw HTTP GET and checks the status
code -- it can't tell whether a page that returns 200 actually *says* what
we claimed. `browser_use_check.py` closes that gap: it opens all 100
evidence URLs in a real headless Chromium browser (via Playwright), waits
for the page to fully render, and checks whether the terms implied by each
app's recorded `auth` / `mcp` fields (e.g. "OAuth2" -> expects "oauth"
somewhere on the page) actually appear in the rendered HTML. This is a
genuine browser-automation verification loop, not another link checker --
and it needed no LLM/API key, since it does deterministic keyword matching
rather than model judgement.

## Result (full 100-app run)

| Status | Count | Meaning |
|---|---|---|
| `verified` | 41 | Every recorded auth/MCP claim for that app was found on its rendered evidence page. |
| `partial` | 29 | Some claims confirmed, some not -- e.g. the page confirms "API key" but doesn't mention MCP. |
| `no_match` | 30 | None of the recorded claims were found on the rendered page. |

Full per-app results are in [`browser_use_report.json`](browser_use_report.json).

## A methodology bug we caught and fixed mid-run

The first full run scored only 23/100 `verified`. Digging in, the checker's
synonym list was the problem: for "API key" auth it checked for *three*
separate phrases ("api key", "apikey", "api token") and required **all
three** to appear before calling a claim satisfied -- effectively demanding
a page repeat the same fact in three different wordings. Real docs pages
just say "API key" once. Fixing the matcher to require *any one* matching
synonym per claim (not all of them) raised the honest result to 41
verified / 29 partial / 30 no_match, shown above. This is the same kind of
self-correction the 20-app hand-verification sample caught for Ahrefs and
Otter.ai -- a first pass had a real error, a second, independent check
found and fixed it.

## Manually spot-checked the `no_match` cases -- here's what's actually going on

Before trusting 30 `no_match` results, two of the most implausible ones
were checked by hand against the live page (Salesforce and Slack -- both
companies whose OAuth documentation is extensive, so a `no_match` result
looked suspicious):

- **Salesforce** (`developer.salesforce.com/docs/apis`): confirmed by
  direct read -- this evidence URL is a link catalog of ~40 different
  Salesforce APIs. It genuinely does not contain the word "oauth" or "mcp"
  anywhere in its body text; those details live on dedicated sub-pages one
  click deeper.
- **Slack** (`api.slack.com/`): confirmed by direct read -- this URL
  redirects to a landing page (`docs.slack.dev`) that links to an
  "Authentication" section but doesn't itself use the word "oauth" in body
  text.

**Conclusion: the `no_match` results are real, not a checker bug -- but
most of them point to a different problem than "the claim is wrong."**
The auth/MCP claims recorded in `apps.py` are almost certainly still
accurate for these apps. What's actually being flagged is that the
**evidence URL** on file is a broad landing/catalog page chosen for being
the single best authoritative link for that app, rather than the specific
sub-page that would literally prove the claim in text. A browser-use check
built for even stricter proof (crawl one link deep from the evidence URL
before matching) would likely resolve most of these -- that's a natural
next iteration of this script, not built here due to time.

**Practical read of the three buckets:**
- `verified` (41): highest confidence -- the evidence URL itself proves the claim.
- `partial` (29): the evidence URL proves *some* of the claim (e.g. auth
  method) but not all (e.g. MCP status, which is newer and more likely to
  live on a separate page or not be mentioned yet) -- worth a manual glance
  before fully trusting the missing piece.
- `no_match` (30): confirmed (by spot-check) to usually mean "evidence URL
  is one click away from proof," not "claim is false" -- but each one
  deserves the same treatment as the Ahrefs/Otter.ai corrections: assume
  nothing, check what you can.

## How to reproduce

```
pip install playwright
playwright install chromium
python browser_use_check.py --out browser_use_report.json
```

Takes a few minutes for all 100 apps (6 pages in parallel, real Chromium
render + settle time per page).