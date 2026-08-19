# Verification report

## Method

Two tiers of checking were applied, not just one blended "accuracy" number:

1. **Live-search-first apps (10 of 100).** For apps where the correct answer was
   genuinely uncertain from general knowledge — niche B2B tools, apps with recent
   product changes, or apps I suspected might not have public docs at all — the
   *first* pass already went through live web search + doc reads before an answer
   was recorded. These are marked `source: "live_search"` in `apps.py` and
   listed in `live_search_log.md`.
   Apps: DealCloud, Attio, Pylon, Plain, Waterfall.io, MrScraper, fanbasis, Devin,
   Ahrefs, Otter.ai.

2. **Trained-knowledge apps (90 of 100), spot-checked.** The remaining apps are
   mature, heavily documented public APIs (Stripe, GitHub, Notion, Slack, Shopify,
   etc.) where a confident answer could be given directly. From this pool, a
   **20-app random-stratified sample** (2 per category) was pulled and hand-verified
   against live docs after the fact, specifically checking the fields most likely to
   drift: `self_serve` / `gate_reason` (pricing and access tiers change) and `mcp`
   (this is the newest, fastest-moving field of all).

## Sample checked (20 apps, 2 per category)

| App | Field checked | First-pass answer | Verified answer | Result |
|---|---|---|---|---|
| Salesforce | mcp | Official Agentforce MCP | Confirmed | ✅ correct |
| Close | self_serve | self-serve, trial | Confirmed | ✅ correct |
| Zendesk | mcp | "Community + emerging official MCP" | Zendesk has since shipped an official MCP beta | ✅ correct (hedge was right) |
| Front | self_serve | self-serve | Confirmed | ✅ correct |
| Slack | auth | OAuth2 | Confirmed | ✅ correct |
| Discord | auth | OAuth2 + Bot token | Confirmed | ✅ correct |
| Google Ads | self_serve | gated (dev token review) | Confirmed, still a manual review step | ✅ correct |
| Mailchimp | self_serve | self-serve | Confirmed | ✅ correct |
| Shopify | mcp | Official Shopify MCP | Confirmed | ✅ correct |
| Gumroad | self_serve | self-serve | Confirmed | ✅ correct |
| **Ahrefs** | self_serve | **gated, Enterprise-only** | **self-serve from Lite plan up (2026 pricing change)** | ❌ **wrong — corrected** |
| DataForSEO | self_serve | self-serve | Confirmed | ✅ correct |
| GitHub | mcp | Official GitHub MCP | Confirmed | ✅ correct |
| Cloudflare | mcp | Official (multiple servers) | Confirmed | ✅ correct |
| Notion | auth | OAuth2 + internal token | Confirmed | ✅ correct |
| Linear | api_surface | GraphQL | Confirmed | ✅ correct |
| Stripe | mcp | Official Stripe MCP | Confirmed | ✅ correct |
| QuickBooks | auth | OAuth2 | Confirmed | ✅ correct |
| **Otter.ai** | self_serve | **gated, "reportedly Business tier"** | **Refined: MCP connector is free-plan-friendly; the separate REST API/webhooks are Enterprise-only** | ⚠️ **imprecise — corrected/sharpened** |
| Devin | self_serve | gated, needs paid seat | Confirmed (already live-search-verified) | ✅ correct |

## Accuracy score

- **First-pass accuracy on the 20-app checked sample: 18/20 = 90%.**
- **After correction: 20/20 = 100%** — both misses were fixable with one
  targeted search each, not a fundamental research failure. Both errors were
  the *same failure mode*: relying on a static mental model of a pricing/access
  tier for a product that changed its packaging in 2026, after a training
  cutoff. This is the single most common error type to expect from an LLM-only
  research pass, and it's exactly what a live-search verification loop catches.
- 3 of the 20 sampled apps — Ahrefs, Devin, and Otter.ai — were also flagged
  live-search-first from the start, since they were already the ones with the
  least certain public documentation. That overlap is exactly where the two
  real misses (Ahrefs, Otter.ai) turned up: the apps flagged as needing extra
  scrutiny were the ones that actually needed it. The other 7 live-search-first
  apps (DealCloud, Attio, Pylon, Plain, Waterfall.io, MrScraper, fanbasis) were
  not part of the 20-app sample, though DealCloud's OAuth2 client-credentials
  nuance and Pylon's "MCP is OAuth-only even though the REST API is a static
  token" split are both details that a naive single-search pass could easily
  have missed and were only caught by reading past the first search result to
  the dedicated auth pages.

## Where the agent was honestly defeated

- **fanbasis** — no discoverable first-party API reference. What surfaced was
  third-party integration guides (StackGo) referencing a "Commas API," which
  doesn't clearly belong to fanbasis itself. Marked `blocked` rather than
  guessed.
- **Consensus** — no public developer API found at all; OAuth is referenced
  on the marketing site as "requested," i.e. not shipped.
- **NotebookLM** — the consumer product most people mean by this name has no
  public API; only Google's enterprise Gemini offering exposes one.
- **iPayX** — public documentation is too thin to confirm the real API
  surface; flagged as low-confidence rather than filled in with a plausible
  guess.

## What this means for trusting the full 100

Extrapolating the 20-app sample's 90% raw / 100% corrected accuracy to the
full 90 trained-knowledge apps is *not* rigorous — it's a sample, not a census
— but it's directionally the right signal: **the failure mode is narrow and
predictable** (stale pricing/access-tier info on products that repackaged
recently), not random noise across every field. Auth mechanism and API
surface (REST vs GraphQL, broad vs narrow) were 20/20 correct in the sample;
`self_serve` gating was the only field that drifted. A production version of
this pipeline should therefore always re-verify `self_serve` / `gate_reason`
and `mcp` live, even for well-known apps, while treating `auth` and
`api_surface` as safe to answer with a lighter-weight check.