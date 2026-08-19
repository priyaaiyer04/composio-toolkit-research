#!/usr/bin/env python3
"""Validate that the runnable research and verification artifacts agree."""

import json
import re
from pathlib import Path

from apps import APPS


ROOT = Path(__file__).parent


def embedded_json(page: str, element_id: str) -> list[dict]:
    match = re.search(
        rf'<script id="{element_id}" type="application/json">(.*?)</script>',
        page,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError(f"Could not find #{element_id} in index.html")
    return json.loads(match.group(1))


def load_json(name: str) -> list[dict]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    inputs = load_json("apps_input.json")
    sample = load_json("verification_sample.json")
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    embedded_apps = embedded_json(page, "app-data")
    embedded_sample = embedded_json(page, "verify-data")

    assert len(APPS) == 100, "apps.py must contain 100 records"
    assert len(inputs) == 100, "apps_input.json must contain 100 records"
    assert [row["app"] for row in inputs] == [row["app"] for row in APPS], (
        "apps_input.json app order must match apps.py"
    )
    assert all(row.get("hint") for row in inputs), "every input needs a research hint"
    assert len(sample) == 20, "verification_sample.json must contain 20 records"
    assert len({row["app"] for row in sample}) == 20, "sample apps must be unique"
    assert all(row["evidence"].startswith("https://") for row in sample), (
        "every sample record needs an HTTPS evidence URL"
    )
    assert sum(row["result"] == "miss" for row in sample) == 2, (
        "sample must retain both documented first-pass misses"
    )
    assert embedded_apps == APPS, "embedded page dataset must match apps.py"

    sample_for_page = [{key: value for key, value in row.items() if key != "evidence"} for row in sample]
    assert embedded_sample == sample_for_page, (
        "embedded page verification sample must match verification_sample.json"
    )

    print("Validated 100 research inputs, 20 verification records, and page/data consistency.")


if __name__ == "__main__":
    main()
