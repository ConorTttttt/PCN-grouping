"""Offline, deterministic rendering of pre-evaluated grouping decisions.

This code NEVER evaluates or upgrades legal eligibility. The JSON input is a
snapshot of B/E model data, not a source of regulatory truth or an ECHA dossier.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from html import escape
from pathlib import Path
from typing import Any, Mapping

VERSION = "1"
DISCLAIMER = (
    "Decision support only. Not an official PCN filing, dossier validation, "
    "regulatory approval or confirmation of compliance."
)


def to_wire(value: Any) -> Any:
    """Convert B/E dataclasses without introducing floats or losing decimals."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite decimal")
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_wire(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): to_wire(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_wire(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise TypeError(f"unsupported or binary-float value: {type(value).__name__}")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def read_snapshot(path: str | Path) -> dict[str, Any]:
    """Read a plain canonical JSON snapshot, rejecting binary-float tokens."""
    def no_floats(value: str) -> None:
        raise ValueError(f"JSON numbers with decimals are forbidden: {value}")

    with Path(path).open("r", encoding="utf-8") as stream:
        data = json.load(stream, parse_float=no_floats,
                         parse_constant=lambda x: no_floats(x))
    if not isinstance(data, dict):
        raise ValueError("snapshot root must be an object")
    return data


def _records(raw: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(raw, (tuple, list)):
        raise ValueError(f"{name} must be a list")
    values = [to_wire(value) for value in raw]
    if any(not isinstance(item, dict) for item in values):
        raise ValueError(f"{name} entries must be objects")
    return sorted(values, key=_json)


def _text(value: Any) -> str:
    return "Not provided" if value is None or value == "" or value == [] else str(value)


def _status(value: Any, allowed: set[str], field: str) -> str:
    value = to_wire(value)
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"invalid {field}: {value!r}")
    return value


def build_report(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Project an immutable evaluator snapshot into deterministic audit tables.

    E's output is consumed as-is; absent fields are surfaced as gaps. No
    concentration or classification is recalculated or inferred here.
    """
    raw = to_wire(snapshot)
    if not isinstance(raw, dict) or raw.get("schema_version") != VERSION:
        raise ValueError("expected schema_version '1' snapshot")
    decision = raw.get("decision")
    if not isinstance(decision, dict):
        raise ValueError("snapshot.decision must be an object")
    ruleset = decision.get("ruleset")
    if not isinstance(ruleset, dict):
        raise ValueError("decision.ruleset must be an object")
    for key in ("ruleset_id", "effective_date", "sha256", "status"):
        if not isinstance(ruleset.get(key), str) or not ruleset[key]:
            raise ValueError(f"missing ruleset.{key}")
    input_hash = decision.get("canonical_input_hash")
    if not isinstance(input_hash, str) or not input_hash:
        raise ValueError("decision.canonical_input_hash is required")
    chemical = _status(decision.get("status"),
                       {"ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED", "OUT_OF_SCOPE"},
                       "chemical status")
    dossier = _status(decision.get("dossier_status", "REVIEW"),
                      {"PASS", "FAIL", "REVIEW"}, "dossier field check")
    applicability = _status(decision.get("applicability_status", "REVIEW"),
                            {"IN_SCOPE", "OUT_OF_SCOPE", "REVIEW"}, "applicability")
    rules = _records(decision.get("rule_results", []), "decision.rule_results")
    if not rules:
        raise ValueError("rule_results missing: cannot display a traceable decision")
    for rule in rules:
        if not isinstance(rule.get("rule_id"), str) or not rule["rule_id"]:
            raise ValueError("rule_id required")
        _status(rule.get("status"), {"PASS", "FAIL", "REVIEW"}, "rule status")
    if chemical == "ELIGIBLE" and any(r["status"] == "FAIL" for r in rules):
        raise ValueError("inconsistent eligible decision contains failed rule")
    if chemical == "INELIGIBLE" and not any(r["status"] == "FAIL" for r in rules):
        raise ValueError("ineligible decision missing failed rule evidence")

    formulations = _records(raw.get("formulations", []), "formulations")
    by_revision: dict[str, dict[str, Any]] = {}
    for form in formulations:
        fid, revision = form.get("formulation_id"), form.get("revision")
        if not isinstance(fid, str) or not fid or not isinstance(revision, str) or not revision:
            raise ValueError("formulation_id and revision required")
        key = f"{fid}@{revision}"
        if key in by_revision:
            raise ValueError(f"duplicate formulation revision: {key}")
        by_revision[key] = form
    requested = decision.get("formulation_revision_ids")
    if not isinstance(requested, list) or not requested or any(
        not isinstance(item, str) for item in requested
    ) or len(set(requested)) != len(requested):
        raise ValueError("decision.formulation_revision_ids required and unique")
    if set(requested) != set(by_revision):
        raise ValueError("formulations must match decision member revisions exactly")

    gaps: set[str] = set(str(item) for item in decision.get("missing_data_flags", []))
    members: list[dict[str, Any]] = []
    for revision_id in sorted(requested):
        form = by_revision[revision_id]
        sources = sorted(_records(form.get("source_references", []), "source_references"),
                         key=_json)
        if not sources:
            gaps.add(f"SOURCE_REFERENCES_MISSING:{revision_id}")
        fields_to_show = (
            "legal_submitter_id", "product_names", "ufis", "market_countries",
            "use_types", "eupcs_codes", "physical_state", "colour", "ph",
            "packaging", "sds_section_11", "notification_mode",
        )
        metadata = {field: form.get(field) for field in fields_to_show}
        members.append({
            "revision_id": revision_id,
            "legal_submitter_id": form.get("legal_submitter_id"),
            "classification": sorted(
                _records(form.get("approved_health_physical_classification", []),
                         "classification"), key=_json),
            "environment_classification": _records(
                form.get("approved_environment_classification", []),
                "environment_classification"),
            "metadata": metadata,
            "source_references": sources,
        })
        for required in ("legal_submitter_id", "product_names", "ufis", "physical_state",
                         "colour", "packaging", "use_types", "eupcs_codes", "sds_section_11"):
            if not metadata.get(required):
                gaps.add(f"DOSSIER_FIELD_MISSING:{revision_id}:{required}")
        # pH may be declared for the whole group. Absence per-member is NOT a hard
        # grouping blocker or automatically a missing dossier field (ECHA 5.4.1).

    for rule in rules:
        if rule["status"] == "REVIEW" and not rule.get("evidence_ids"):
            gaps.add(f"REVIEW_WITHOUT_LINKED_EVIDENCE:{rule['rule_id']}")
        if not rule.get("source_sections"):
            gaps.add(f"RULE_SOURCE_SECTION_MISSING:{rule['rule_id']}")
    if ruleset["status"] != "APPROVED":
        gaps.add("RULESET_NOT_INDEPENDENTLY_APPROVED")
    if not any(item["rule_id"] == "REG-DOSSIER" for item in rules):
        gaps.add("DOSSIER_FIELD_CHECK_NOT_PRESENT_IN_RULE_TRACE")

    result = {
        "schema_version": VERSION,
        "report_type": "OFFLINE_PCN_GROUPING_DECISION_SUPPORT",
        "disclaimer": DISCLAIMER,
        "summary": {
            "chemical_eligibility": chemical,
            "dossier_field_check": dossier,
            "submission_readiness": "NOT_VERIFIED",
            "applicability": applicability,
            "legal_submitters": sorted({m["legal_submitter_id"] for m in members
                                       if m["legal_submitter_id"] is not None}),
            "member_count": len(members),
        },
        "provenance": {"ruleset": ruleset,
                       "canonical_input_hash": input_hash},
        "members": members,
        "rule_results": rules,
        "common_component_ranges": _records(
            decision.get("common_ranges", []), "common_ranges"),
        "varying_perfume_totals": _records(
            decision.get("varying_perfume_totals", []), "varying_perfume_totals"),
        "perfume_classification_matrix": sorted(
            to_wire(decision.get("perfume_classification_matrix", [])), key=_json),
        "component_source_matrix": _records(
            decision.get("component_matrix", []), "component_matrix"),
        "data_gaps": sorted(gaps),
        "review_workflow": {"status": "PENDING", "events": []},
    }
    return result


def render_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False,
                      allow_nan=False) + "\n"


def render_csv(report: Mapping[str, Any]) -> str:
    """Lossless per-section CSV rows: details are canonical compact JSON text."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["section", "reference", "status", "details_json"])
    for key in ("summary", "provenance"):
        writer.writerow([key, "", "", _json(report[key])])
    sections = (
        ("member", "members", "revision_id", ""),
        ("rule", "rule_results", "rule_id", "status"),
        ("common_range", "common_component_ranges", "notified_identity", "status"),
        ("perfume_total", "varying_perfume_totals", "revision", ""),
        ("component_source", "component_source_matrix", "line", ""),
    )
    for label, key, reference_key, status_key in sections:
        for item in report[key]:
            reference = item.get(reference_key, "")
            writer.writerow([label, _json(reference) if isinstance(reference, list)
                             else reference, item.get(status_key, "") if status_key else "",
                             _json(item)])
    for item in report["perfume_classification_matrix"]:
        writer.writerow(["perfume_classification", "", "", _json(item)])
    for gap in report["data_gaps"]:
        writer.writerow(["data_gap", gap, "REVIEW", ""])
    for item in report["review_workflow"]["events"]:
        writer.writerow(["review_event", item["reviewer_id"], item["status"], _json(item)])
    return stream.getvalue()


def render_html(report: Mapping[str, Any]) -> str:
    """Standalone, escaped HTML; never fetches fonts, JS or third-party assets."""
    def cell(value: Any) -> str:
        if isinstance(value, (dict, list)):
            value = _json(value)
        return escape(_text(value), quote=True)

    def table(title: str, rows: list[Any], columns: tuple[tuple[str, str], ...]) -> str:
        if not rows:
            return f"<section><h2>{escape(title)}</h2><p>Not provided</p></section>"
        head = "".join(f"<th>{escape(label)}</th>" for label, _ in columns)
        body = "".join("<tr>" + "".join(
            f"<td><pre>{cell(row.get(key))}</pre></td>" for _, key in columns
        ) + "</tr>" for row in rows)
        return f"<section><h2>{escape(title)}</h2><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></section>"

    summary = report["summary"]
    result = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
        "<title>PCN grouping decision support</title><style>",
        ":root{font-family:system-ui,sans-serif;color:#173147;background:#f4f7fb}",
        "body{max-width:1240px;margin:auto;padding:22px}header,section{background:white;",
        "padding:18px 22px;margin:0 0 18px;border:1px solid #dce5ef;border-radius:12px}",
        "h1{margin:0 0 8px}h2{margin:0 0 12px;font-size:1.15rem}",
        ".notice{background:#fff7e8;border-left:5px solid #a76713;padding:12px}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}",
        ".card{border:1px solid #ccd9e5;border-radius:8px;padding:12px}",
        ".label{font-size:.79rem;color:#506477;text-transform:uppercase}",
        "table{border-collapse:collapse;width:100%;font-size:.88rem;display:block;overflow-x:auto}",
        "th,td{border:1px solid #dce5ef;text-align:left;vertical-align:top;padding:9px}",
        "th{background:#eaf0f8}tr:nth-child(even){background:#f8fafc}",
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;font:inherit}",
        "</style></head><body><header><h1>Grouping decision audit</h1>",
        f"<p class=\"notice\">{cell(report['disclaimer'])}</p>",
        "<div class=\"grid\">",
    ]
    for label, key in (("Chemical eligibility", "chemical_eligibility"),
                       ("Dossier field check", "dossier_field_check"),
                       ("Submission readiness", "submission_readiness"),
                       ("PCN applicability", "applicability"),
                       ("Members", "member_count")):
        result.append(f"<div class=\"card\"><div class=\"label\">{escape(label)}</div>"
                      f"<strong>{cell(summary[key])}</strong></div>")
    result.append("</div></header>")
    prov = report["provenance"]
    result.append("<section><h2>Provenance</h2><p>Rulebook: "
                  f"{cell(prov['ruleset'])}</p><p>Input hash: "
                  f"<code>{cell(prov['canonical_input_hash'])}</code></p></section>")
    result.append(table("Formulation revisions and classifications", report["members"],
                        (("Revision", "revision_id"), ("Submitter", "legal_submitter_id"),
                         ("Health/physical CLP", "classification"),
                         ("Product/dossier fields", "metadata"),
                         ("Source evidence", "source_references"))))
    result.append(table("Regulatory rule trace", report["rule_results"],
                        (("Rule", "rule_id"), ("Result", "status"),
                         ("Explanation", "explanation"), ("Sources", "source_sections"),
                         ("Evidence IDs", "evidence_ids"), ("Values/reasons", "values"))))
    result.append(table("Shared declaration ranges", report["common_component_ranges"],
                        (("Identity", "notified_identity"), ("Member values", "member_bounds"),
                         ("Lower", "declared_lower"), ("Upper", "declared_upper"),
                         ("Result", "status"), ("Reason codes", "reason_codes"))))
    result.append(table("Varying perfume totals (actual % per mixture)",
                        report["varying_perfume_totals"],
                        (("Revision", "revision"), ("Actual bounds", "actual"),
                         ("Component lines", "line_ids"), ("Identity verified", "membership_verified"))))
    result.append(table("Component source and evidence matrix",
                        report["component_source_matrix"],
                        (("Line", "line"), ("Raw identity", "raw_identity_key"),
                         ("Notified identity", "notified_identity_key"),
                         ("Actual bounds", "actual"), ("Source docs", "source_document_ids"),
                         ("Evidence IDs", "evidence_ids"))))
    result.append("<section><h2>Mixture ↔ varying-perfume ↔ classification</h2><pre>"
                  + cell(report["perfume_classification_matrix"]) + "</pre></section>")
    result.append(table("Human reviewer event history", report["review_workflow"]["events"],
                        (("Reviewer", "reviewer_id"), ("Status", "status"),
                         ("Reason", "reason"), ("Recorded at", "timestamp"),
                         ("Event digest", "event_hash"))))
    result.append("<section><h2>Actionable data gaps / reviewer queue</h2>"
                  + ("<ul>" + "".join(f"<li>{cell(x)}</li>" for x in report["data_gaps"])
                     + "</ul>" if report["data_gaps"] else "<p>No gaps flagged in this snapshot; "
                     "external dossier validation is still required.</p>")
                  + "</section></body></html>\n")
    return "".join(result)
