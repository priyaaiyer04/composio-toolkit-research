#!/usr/bin/env python3
"""
Composio 100-app research agent.

WHAT THIS DOES
--------------
For each app in APP_LIST, it asks Claude (via the Anthropic Messages API)
to research the app's developer docs using the server-side `web_search`
tool, then return a single strict-JSON object matching our schema:

  category, one_liner, auth, self_serve, gate_reason, api_surface,
  mcp, verdict, blocker, evidence

The model is instructed to search first, read the actual docs pages, and
only then answer -- it is not allowed to answer from parametric memory
alone. Every claim must carry the URL it came from in `evidence`.

WHERE A HUMAN WAS NEEDED
-------------------------
This script automates the *first pass*. A human (or a second verification
agent, see /verification/verify_sample.py) is still required to:
  1. Spot-check a sample against the docs by hand (auth flows and gating
     rules change -- e.g. Ahrefs opened its API to all paid plans in 2026,
     which a stale training cutoff would get wrong).
  2. Judge ambiguous cases (e.g. "is a local CLI tool like Sherlock or
     Mermaid CLI a 'toolkit' at all?").
  3. Resolve apps with no discoverable first-party docs (the agent should
     say so honestly, e.g. fanbasis in this run) rather than guessing.
  4. Sign off on the final buildability verdict, since that's a product
     call, not just a factual one.

USAGE
-----
    export ANTHROPIC_API_KEY=sk-ant-...
    python research_agent.py --apps apps_input.json --out ../data/raw_pass.json

`apps_input.json` is a flat list of {"app": "...", "hint": "..."} objects,
one per row of the assignment's 100-app table.
"""
import os
import json
import time
import argparse
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a toolkit-research agent for Composio. For the given app, use \
web_search (and follow-up searches as needed) to find its FIRST-PARTY developer \
documentation. Do not answer from memory alone -- search, open the docs, then answer.

Return ONLY a JSON object (no markdown fences, no prose) with exactly these keys:
{
  "category": string,
  "one_liner": string (<=15 words, what the app does),
  "auth": [string, ...]  // e.g. ["OAuth2"], ["API key"], ["Basic"], ["Bearer token"]
  "self_serve": "self-serve" | "gated" | "partial",
  "gate_reason": string,  // why it's self-serve/gated -- be specific
  "api_surface": string,  // REST/GraphQL/gRPC, roughly how broad
  "mcp": string,          // "None found" | "Official ... MCP" | "Community MCP servers"
  "verdict": "ready" | "partial" | "blocked",  // could this be an agent toolkit today
  "blocker": string | null,  // the MAIN blocker if not fully ready
  "evidence": string      // the single best doc URL backing this
}

If you cannot find first-party public documentation after searching, say so honestly:
set self_serve to "gated", verdict to "blocked", and blocker explaining that no public
docs were found -- do NOT fabricate an answer."""


def research_one(app_name: str, hint: str, api_key: str) -> dict:
    body = {
        "model": MODEL,
        "max_tokens": 1000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": f"App: {app_name}\nHint: {hint}\n\nResearch this app's developer API."}
        ],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    raw = "\n".join(text_blocks).strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"error": "unparseable_response", "raw": raw}
    parsed["_app"] = app_name
    return parsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps", required=True, help="JSON list of {app, hint}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY first.")

    with open(args.apps) as f:
        apps = json.load(f)

    results = []
    for i, a in enumerate(apps, 1):
        print(f"[{i}/{len(apps)}] researching {a['app']}...")
        try:
            results.append(research_one(a["app"], a.get("hint", ""), api_key))
        except Exception as e:
            results.append({"_app": a["app"], "error": str(e)})
        time.sleep(args.sleep)

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {len(results)} results to {args.out}")


if __name__ == "__main__":
    main()
