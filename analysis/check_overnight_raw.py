#!/usr/bin/env python3
"""Verify that every exported overnight run has its untouched COSMA record.

This checks provenance coverage; it does not recompute Grid performance.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

CAMPAIGN = "20261022T224854Z"


def main(root: Path) -> int:
    export = root / "analysis" / f"overnight-{CAMPAIGN}" / "runs.csv"
    if not export.is_file():
        print(f"ERROR: missing overnight export {export}", file=sys.stderr)
        return 2

    counts = Counter()
    states = Counter()
    failures: list[str] = []
    seen: set[str] = set()
    with export.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            source = row.get("source", "")
            if source in seen:
                failures.append(f"Duplicate exported source: {source}")
                continue
            seen.add(source)
            path = Path(source)
            parts = path.parts
            # Fail closed if a CSV row references anything outside the campaign.
            if (
                len(parts) != 4
                or parts[0] != "results"
                or parts[1] not in {"dine", "dine2"}
                or parts[2] != f"grid-overnight-{CAMPAIGN}"
                or path.is_absolute()
                or ".." in parts
            ):
                failures.append(f"Unexpected source path: {source!r}")
                continue
            record_path = root / path / "record.json"
            if not record_path.is_file():
                failures.append(f"Missing: {record_path.relative_to(root)}")
                continue
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                failures.append(f"Invalid JSON: {source}: {error}")
                continue

            if record.get("campaign_id") != CAMPAIGN:
                failures.append(f"Wrong campaign ID: {source}")
            if record.get("node") != parts[1] or str(record.get("job")) != parts[3]:
                failures.append(f"Node/job mismatch: {source}")
            exported_ok = row.get("status") == "ok"
            recorded_ok = record.get("status") == "ok"
            if exported_ok != recorded_ok:
                failures.append(f"Status mismatch: {source} (CSV={row.get('status')}, raw={record.get('status')})")
            if exported_ok and row.get("mode") in {"scaling", "extended", "smoke"}:
                if not (root / path / "result.json").is_file():
                    failures.append(f"Successful Grid run missing result.json: {source}")
            counts[parts[1]] += 1
            states[row.get("status", "unknown")] += 1

    total = sum(counts.values())
    print(f"Overnight raw records checked: {total} (DINE={counts['dine']}, DINE2={counts['dine2']})")
    print(f"Exported run statuses: ok={states['ok']}, failed={states['failed']}")
    for issue in failures[:25]:
        print(f"ERROR: {issue}", file=sys.stderr)
    if len(failures) > 25:
        print(f"... and {len(failures) - 25} further issues", file=sys.stderr)
    if failures:
        print("Raw import is incomplete or inconsistent; do not claim full verification.", file=sys.stderr)
        return 1
    print("PASS: every exported run has a matching COSMA record (including failed runs).")
    return 0


if __name__ == "__main__":
    root_arg = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
    raise SystemExit(main(root_arg.resolve()))
