"""python -m pcn_grouping.cli report|review; never sends an ECHA submission."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pcn_grouping.reporting import (append_review, build_report, read_snapshot,
                                    render_csv, render_html, render_json)
from pcn_grouping.reporting.review import attach_review


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_audit(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("audit file is not a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline grouping decision reports; not PCN filing")
    commands = parser.add_subparsers(dest="command", required=True)
    report_p = commands.add_parser("report", help="Render a pre-evaluated B/E JSON snapshot")
    report_p.add_argument("--input", type=Path, required=True)
    report_p.add_argument("--output-dir", type=Path, required=True)
    report_p.add_argument("--audit", type=Path, help="Optional matching reviewer log")
    review_p = commands.add_parser("review", help="Append a human review audit event")
    review_p.add_argument("--input", type=Path, required=True)
    review_p.add_argument("--audit", type=Path, required=True)
    review_p.add_argument("--status", required=True, choices=["PENDING", "APPROVED", "REJECTED"])
    review_p.add_argument("--reviewer", required=True)
    review_p.add_argument("--reason", required=True)
    review_p.add_argument("--timestamp", help="Explicit ISO-8601 offset time for replay")
    arguments = parser.parse_args(argv)
    try:
        report = build_report(read_snapshot(arguments.input))
        if arguments.command == "report":
            if arguments.audit is not None:
                audit = _read_audit(arguments.audit)
                if audit is None:
                    raise ValueError("specified audit file does not exist")
                report = attach_review(report, audit)
            output = arguments.output_dir
            for filename, content in (("decision.json", render_json(report)),
                                      ("decision.csv", render_csv(report)),
                                      ("decision.html", render_html(report))):
                _write_atomic(output / filename, content)
            print(f"Generated offline audit reports in {output}; no PCN was submitted")
        elif arguments.command == "review":
            timestamp = arguments.timestamp or datetime.now(timezone.utc).isoformat()
            audit = append_review(report, _read_audit(arguments.audit),
                                  status=arguments.status, reviewer_id=arguments.reviewer,
                                  reason=arguments.reason, timestamp=timestamp)
            _write_atomic(arguments.audit, json.dumps(audit, sort_keys=True, indent=2)
                          + "\n")
            print(f"Recorded {arguments.status} reviewer event; eligibility unchanged")
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
