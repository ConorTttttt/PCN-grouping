"""Append-only-in-application SHA-256 linked reviewer decisions.

Files are not tamper-proof against privileged rewriting; retain external backups
and access controls for production audit integrity. Review never changes law.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

STATUSES = frozenset({"PENDING", "APPROVED", "REJECTED"})


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _report_digest(report: Mapping[str, Any]) -> str:
    # Review events are deliberately excluded: the underlying immutable E
    # chemical decision and input provenance cannot be revised by a reviewer.
    return _digest({key: val for key, val in report.items() if key != "review_workflow"})


def _validate_event(event: Mapping[str, Any]) -> None:
    if event.get("status") not in STATUSES:
        raise ValueError("invalid reviewer status")
    if not isinstance(event.get("reviewer_id"), str) or not event["reviewer_id"].strip():
        raise ValueError("reviewer identity required")
    if not isinstance(event.get("reason"), str) or not event["reason"].strip():
        raise ValueError("reason required for every reviewer decision")
    timestamp = event.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError("timestamp required")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone offset")


def _can_approve(report: Mapping[str, Any]) -> bool:
    summary = report["summary"]
    return (
        summary["chemical_eligibility"] == "ELIGIBLE"
        and summary["applicability"] == "IN_SCOPE"
        and report["provenance"]["ruleset"]["status"] == "APPROVED"
        and not any(row["status"] in {"FAIL", "REVIEW"} and row["rule_id"] != "REG-DOSSIER"
                    for row in report["rule_results"])
        and "RULESET_NOT_INDEPENDENTLY_APPROVED" not in report["data_gaps"]
    )


def verify_audit(report: Mapping[str, Any], audit: Mapping[str, Any]) -> None:
    """Validate input binding and all event links before using an audit log."""
    if audit.get("schema_version") != "1" or audit.get("report_sha256") != _report_digest(report):
        raise ValueError("audit log does not match this evaluator snapshot")
    events = audit.get("events")
    if not isinstance(events, list):
        raise ValueError("audit.events must be an array")
    previous = audit["report_sha256"]
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("audit event must be an object")
        _validate_event(event)
        if event.get("previous_hash") != previous:
            raise ValueError("broken audit event chain")
        payload = {key: value for key, value in event.items() if key != "event_hash"}
        current = _digest(payload)
        if event.get("event_hash") != current:
            raise ValueError("reviewer event was altered")
        if event["status"] == "APPROVED" and not _can_approve(report):
            raise ValueError("an approval cannot override failed/unverified eligibility")
        previous = current


def audit_status(audit: Mapping[str, Any]) -> str:
    events = audit.get("events", [])
    return events[-1]["status"] if events else "PENDING"


def append_review(report: Mapping[str, Any], audit: Mapping[str, Any] | None, *,
                  status: str, reviewer_id: str, reason: str,
                  timestamp: str) -> dict[str, Any]:
    """Return a NEW chain with one event. No mutation of existing records."""
    if status not in STATUSES:
        raise ValueError("status must be PENDING, APPROVED or REJECTED")
    if status == "APPROVED" and not _can_approve(report):
        raise ValueError("cannot approve an ineligible or unverified chemical grouping")
    base = {"schema_version": "1", "report_sha256": _report_digest(report), "events": []}
    if audit is not None:
        verify_audit(report, audit)
        base["events"] = [dict(event) for event in audit["events"]]
    events: list[dict[str, Any]] = base["events"]
    previous = events[-1]["event_hash"] if events else base["report_sha256"]
    event = {"status": status, "reviewer_id": reviewer_id, "reason": reason,
             "timestamp": timestamp, "previous_hash": previous}
    _validate_event(event)
    event["event_hash"] = _digest(event)
    if any(existing["event_hash"] == event["event_hash"] for existing in events):
        raise ValueError("duplicate review event")
    if any(all(existing[key] == event[key] for key in
               ("status", "reviewer_id", "reason", "timestamp")) for existing in events):
        raise ValueError("duplicate review event")
    events.append(event)
    return base


def attach_review(report: Mapping[str, Any], audit: Mapping[str, Any]) -> dict[str, Any]:
    verify_audit(report, audit)
    result = dict(report)
    result["review_workflow"] = {"status": audit_status(audit),
                                 "events": [dict(event) for event in audit["events"]]}
    return result
