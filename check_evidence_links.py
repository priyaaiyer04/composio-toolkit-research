#!/usr/bin/env python3
"""Check that every evidence URL in apps.py can be reached reproducibly."""

import argparse
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from apps import APPS


USER_AGENT = "ComposioToolkitResearch/1.0 (+https://github.com/priyaaiyer04/composio-toolkit-research)"


def classify_http_status(status: int) -> tuple[str, bool]:
    if 200 <= status < 400:
        return "ok", True
    if status in {401, 403, 429}:
        return "restricted", True
    if status in {404, 410}:
        return "not_found", False
    if status >= 500:
        return "server_error", False
    return "http_error", True


def check_link(app: dict, timeout: float) -> dict:
    started = time.perf_counter()
    request = Request(
        app["evidence"],
        headers={"User-Agent": USER_AGENT, "Range": "bytes=0-1023"},
        method="GET",
    )
    result = {
        "id": app["id"],
        "app": app["app"],
        "evidence": app["evidence"],
    }
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            response.read(1024)
            classification, reachable = classify_http_status(status)
            result.update(
                classification=classification,
                reachable=reachable,
                status=status,
                final_url=response.url,
                content_type=response.headers.get_content_type(),
            )
    except HTTPError as error:
        classification, reachable = classify_http_status(error.code)
        result.update(
            classification=classification,
            reachable=reachable,
            status=error.code,
            final_url=error.url,
            content_type=error.headers.get_content_type() if error.headers else None,
        )
    except (URLError, socket.timeout, TimeoutError) as error:
        result.update(
            classification="network_error",
            reachable=False,
            status=None,
            final_url=None,
            content_type=None,
            error=str(error.reason if isinstance(error, URLError) else error),
        )
    except Exception as error:
        result.update(
            classification="unexpected_error",
            reachable=False,
            status=None,
            final_url=None,
            content_type=None,
            error=str(error),
        )
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="evidence_link_report.json", help="JSON report path")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent requests")
    parser.add_argument("--timeout", type=float, default=15, help="Per-request timeout in seconds")
    args = parser.parse_args()

    if args.workers < 1 or args.timeout <= 0:
        raise SystemExit("--workers must be at least 1 and --timeout must be positive.")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(check_link, app, args.timeout) for app in APPS]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda row: row["id"])
    summary = {}
    for result in results:
        summary[result["classification"]] = summary.get(result["classification"], 0) + 1

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checker": "check_evidence_links.py",
        "request": {"workers": args.workers, "timeout_seconds": args.timeout},
        "total": len(results),
        "summary": summary,
        "results": results,
    }
    destination = Path(args.out)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(results)} evidence URLs. Summary: {summary}. Wrote {destination}.")


if __name__ == "__main__":
    main()
