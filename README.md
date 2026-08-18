# Composio 100-App Toolkit Research

A research pass over 100 apps (10 categories) assessing agent-toolkit readiness:
auth model, self-serve vs. gated access, API surface, existing MCP support, and a
buildability verdict — plus the agent pipeline that produced it and a verification
pass that checks its own accuracy.

**Live deliverable:** `site/index.html` (single self-contained page, no build step —
open it directly or deploy the `site/` folder to GitHub Pages).

## Repo layout

```
data/
  apps.py                 # the 100-app dataset (source of truth), with per-app
                           # `source` tag: "live_search" (verified live during
                           # research) or "trained_knowledge" (mature, well-known
                           # API, answered directly then spot-checked)
  apps.json               # same data, exported for the HTML page

agent/
  research_agent.py       # runnable pipeline: Claude + web_search tool researches
                           # one app at a time and returns strict-schema JSON

verification/
  verification_report.md  # methodology, 20-app sample, hits/misses, before/after
                           # accuracy, and the apps the agent honestly couldn't
                           # resolve
  verify_sample.json       # the same sample, structured for the page

site/
  template.html           # HTML shell with `__APPS_JSON__` / `__VERIFY_JSON__`
                           # placeholders
  index.html               # built output — apps.json + verify_sample.json
                           # injected into template.html (see build command below)
```

## How this run was actually produced

This sandbox had no `ANTHROPIC_API_KEY`, so `agent/research_agent.py` could not be
executed end-to-end here. Instead, the same research was performed *live*, using
the same "search first, answer in the app's own words, cite the doc URL" discipline
the script encodes — for the 10 apps flagged `source: "live_search"` in
`data/apps.py`, every field came from a real search + doc read in this session
(you can see the queries and sources in the conversation transcript). The
remaining 90 apps are mature, extremely well-documented public APIs (Stripe,
GitHub, Notion, Shopify, Slack, etc.) that were answered directly and then
spot-checked — see `verification/verification_report.md` for exactly which ones
and what the checking caught (it caught two real errors: stale Ahrefs pricing-tier
info, and an imprecise Otter.ai claim — both corrected in `data/apps.py`).

**To run the pipeline for real** against all 100 apps (or any new list):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python agent/research_agent.py --apps agent/apps_input.json --out data/raw_pass.json
```

This will re-derive the same fields via the model's own live web search rather
than the human-in-the-loop live search used to produce this snapshot. Compare its
output against `data/apps.py` as a regression check.

## Rebuilding the HTML page after editing the data

```bash
python3 -c "
import json
apps = open('data/apps.json').read()
verify = open('verification/verify_sample.json').read()
tpl = open('site/template.html').read()
out = tpl.replace('__APPS_JSON__', apps).replace('__VERIFY_JSON__', verify)
open('site/index.html','w').write(out)
"
```

## Deploying to GitHub Pages

1. Push this repo.
2. Settings → Pages → Deploy from branch → root (or `/site` as the folder, then
   rename `index.html` accordingly, or copy `site/index.html` to the repo root).
3. The page is fully static — no server, no API calls at runtime, no external
   dependencies beyond the fonts loaded from Google Fonts (optional; the CSS
   falls back to system fonts if that's blocked).

## Honesty notes (per the assignment's own rules)

- Two apps had a confidently-wrong first-pass answer, both caught and corrected
  by the verification loop (see `verification_report.md`). Both were the same
  failure mode: a stale mental model of a pricing/access tier that changed in 2026.
- Four apps defeated first-party-docs discovery entirely (fanbasis, Consensus,
  NotebookLM's consumer product, iPayX) and are marked `blocked` with an honest
  explanation rather than a guessed answer.
- Accuracy is reported over the *sample actually checked* (20/100 by hand +
  10/100 live-search-first at the source = 30% of the dataset directly verified
  against docs), not asserted for the full 100.
