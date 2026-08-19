#!/usr/bin/env python3
"""
Real browser-use verification pass over all 100 evidence URLs in apps.py.

WHAT THIS IS FOR
-----------------
check_evidence_links.py only does a raw HTTP GET and checks the status code.
That misses two real failure modes:
  1. JS-rendered docs/pricing pages that return HTTP 200 but show a blank
     shell (or a paywall / cookie-consent screen) until JavaScript runs.
  2. Pages that load fine but no longer actually say what our claim says
     (e.g. we recorded "OAuth2" but the page now only mentions API keys).

This script opens every evidence URL in a real headless Chromium browser
(via Playwright), waits for it to render, and checks whether the terms
implied by that app's recorded `auth` / `mcp` fields actually appear in the
rendered page text. It is a genuine "browser-use" verification loop, not
just a link checker -- and it needs no API key, since it does keyword
matching rather than LLM judgement.

SETUP (one-time)
-----------------
    pip install playwright
    playwright install chromium

USAGE
-----
    python browser_use_check.py --out browser_use_report.json

Options:
    --concurrency N   how many pages to check in parallel (default 6)
    --timeout MS      per-page render timeout in ms (default 20000)
    --limit N         only check the first N apps (useful for a quick test run)

OUTPUT
------
A JSON report (browser_use_report.json by default) with one record per app:
    { app, url, status: "verified" | "partial" | "no_match" |
                          "no_keywords_to_check" | "blocked",
      expected_claims, satisfied_claims, missing_claims, note }
plus a summary count by status. Each "claim" (e.g. oauth, api_key, mcp) is
satisfied if ANY ONE of its synonym phrases is found on the rendered page --
a page that says "API key" once is not penalized for not also saying
"apikey" or "api token". "blocked" means the page didn't render (timeout,
bot-block, JS crash) -- reported separately from "no_match", which means
the page rendered fine but didn't say what we expected.
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from apps import APPS

ROOT = Path(__file__).parent

# Each entry: (pattern to detect this auth type in app['auth'], list of
# synonym phrases that would satisfy it on a rendered page). A CLAIM is
# satisfied if ANY ONE synonym in its group is found -- a docs page that
# says "API key" once should not be marked wrong for not also saying
# "apikey" or "api token", since those are the same fact, not separate ones.
AUTH_KEYWORD_GROUPS = [
    (r"oauth", "oauth", ["oauth"]),
    (r"api key", "api_key", ["api key", "apikey", "api token", "access token", "api credentials"]),
    (r"basic", "basic_auth", ["basic auth", "basic authentication", "username and password"]),
    (r"bearer", "bearer", ["bearer", "bearer token"]),
    (r"\btoken\b", "token", ["token"]),
    (r"webhook", "webhook", ["webhook"]),
    (r"saml", "saml", ["saml"]),
    (r"jwt", "jwt", ["jwt"]),
    (r"client.credentials", "client_credentials", ["client credentials", "client id", "client secret"]),
]


def expected_groups_for(app: dict) -> dict[str, list[str]]:
    """Return {claim_name: [synonym, synonym, ...]} -- ANY synonym present
    satisfies that claim."""
    groups: dict[str, list[str]] = {}
    auth_list = app.get("auth") or []
    auth_text = " ".join(auth_list).lower()
    for pattern, name, synonyms in AUTH_KEYWORD_GROUPS:
        if re.search(pattern, auth_text):
            groups[name] = synonyms

    mcp = (app.get("mcp") or "").strip().lower()
    if mcp and "none found" not in mcp and mcp != "none":
        groups["mcp"] = ["mcp"]

    return groups


async def check_one(browser, app: dict, timeout_ms: int, sem: asyncio.Semaphore) -> dict:
    url = app["evidence"]
    groups = expected_groups_for(app)
    record = {
        "app": app["app"],
        "url": url,
        "expected_claims": sorted(groups.keys()),
    }

    if not groups:
        record["status"] = "no_keywords_to_check"
        record["satisfied_claims"] = []
        record["missing_claims"] = []
        record["note"] = "No auth/MCP claim strong enough to derive a keyword check."
        return record

    async with sem:
        page = None
        try:
            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            )
            await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            # give client-rendered docs sites (Docusaurus/Mintlify/etc.) a beat to hydrate
            try:
                await page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except Exception:
                pass
            # extra fixed settle time -- some sites never reach networkidle
            # (analytics beacons, websockets) but are fully rendered well before that
            await page.wait_for_timeout(1500)
            # Use the full rendered HTML rather than inner_text(): inner_text only
            # returns *visible* text, and many docs sites keep sidebar/accordion
            # content in the DOM with display:none until clicked, which inner_text
            # would wrongly treat as "not present". Raw HTML catches that.
            html = await page.content()
            text = re.sub(r"<[^>]+>", " ", html).lower()
            text = re.sub(r"\s+", " ", text)
        except Exception as exc:
            record["status"] = "blocked"
            record["satisfied_claims"] = []
            record["missing_claims"] = sorted(groups.keys())
            record["note"] = f"Page did not render: {exc.__class__.__name__}: {exc}"[:300]
            return record
        finally:
            if page is not None:
                await page.close()

    satisfied = []
    missing = []
    for claim, synonyms in groups.items():
        if any(s in text for s in synonyms):
            satisfied.append(claim)
        else:
            missing.append(claim)

    if not missing:
        record["status"] = "verified"
        record["note"] = "Every recorded auth/MCP claim has a matching term on the rendered page."
    elif satisfied:
        record["status"] = "partial"
        record["note"] = "Some claims confirmed on the page; others not found -- worth a manual look."
    else:
        record["status"] = "no_match"
        record["note"] = "None of the recorded claims were found on the rendered page -- possible drift."

    record["satisfied_claims"] = sorted(satisfied)
    record["missing_claims"] = sorted(missing)
    return record


async def run(out_path: Path, concurrency: int, timeout_ms: int, limit: int | None) -> None:
    from playwright.async_api import async_playwright

    apps = APPS[:limit] if limit else APPS
    sem = asyncio.Semaphore(concurrency)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            tasks = [check_one(browser, app, timeout_ms, sem) for app in apps]
            results = []
            for i, coro in enumerate(asyncio.as_completed(tasks), 1):
                result = await coro
                results.append(result)
                print(f"[{i}/{len(tasks)}] {result['app']:<30} {result['status']}")
        finally:
            await browser.close()

    # keep output in the same order as apps.py regardless of completion order
    order = {a["app"]: i for i, a in enumerate(apps)}
    results.sort(key=lambda r: order.get(r["app"], 10_000))

    summary: dict[str, int] = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1

    report = {
        "checker": "browser_use_check.py (Playwright, headless Chromium)",
        "total": len(results),
        "summary": summary,
        "results": results,
    }
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("\nSummary:", json.dumps(summary, indent=2))
    print(f"\nWrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="browser_use_report.json")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=20000, help="per-page timeout in ms")
    parser.add_argument("--limit", type=int, default=None, help="only check first N apps")
    args = parser.parse_args()

    try:
        import playwright  # noqa: F401
    except ImportError:
        print("Playwright is not installed. Run:\n  pip install playwright\n  playwright install chromium")
        sys.exit(1)

    asyncio.run(run(ROOT / args.out, args.concurrency, args.timeout, args.limit))


if __name__ == "__main__":
    main()