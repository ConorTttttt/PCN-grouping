"""Synthetic non-regulatory tests of the offline report presentation layer."""
from __future__ import annotations

import copy
import csv
import io
import json
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from pcn_grouping.reporting import (append_review, attach_review, audit_status,
                                    build_report, read_snapshot, render_csv,
                                    render_html, render_json, to_wire, verify_audit)

FIXTURE = Path(__file__).resolve().parents[2] / "src/pcn_grouping/reporting/examples/synthetic_demo_snapshot.json"


def snapshot() -> dict[str, Any]:
    return read_snapshot(FIXTURE)


def test_fixture_shows_all_required_views_and_exact_decimal() -> None:
    report = build_report(snapshot())
    assert report["summary"]["chemical_eligibility"] == "INELIGIBLE"
    assert report["summary"]["dossier_field_check"] == "REVIEW"
    assert report["summary"]["submission_readiness"] == "NOT_VERIFIED"
    assert report["summary"]["legal_submitters"] == ["SYNTH-DUTY-HOLDER"]
    assert [m["revision_id"] for m in report["members"]] == ["SYNTH-ALPHA@r1", "SYNTH-BETA@r2"]
    assert report["common_component_ranges"][0]["declared_lower"] == "94.9999"
    assert any(r["status"] == "FAIL" for r in report["rule_results"])
    assert any(r["status"] == "REVIEW" for r in report["rule_results"])
    assert any(r["status"] == "PASS" for r in report["rule_results"])
    assert len(report["component_source_matrix"]) == 4
    assert len(report["perfume_classification_matrix"]) == 2
    assert len(report["varying_perfume_totals"]) == 2
    assert any("SOURCE" not in gap for gap in report["data_gaps"])
    assert "REVIEW_WITHOUT_LINKED_EVIDENCE:REG-DOSSIER" in report["data_gaps"]
    assert "DOSSIER_FIELD_MISSING:SYNTH-ALPHA@r1:sds_section_11" in report["data_gaps"]
    assert "RULESET_NOT_INDEPENDENTLY_APPROVED" in report["data_gaps"]
    assert "5.0001" in render_json(report)


def test_permutations_stable_across_all_three_exports() -> None:
    original = snapshot()
    shuffled = copy.deepcopy(original)
    for name in ("formulations",):
        shuffled[name].reverse()
    d = shuffled["decision"]
    for name in ("formulation_revision_ids", "rule_results", "common_ranges",
                 "varying_perfume_totals", "component_matrix", "perfume_classification_matrix",
                 "missing_data_flags"):
        d[name].reverse()
    for a, b in zip((render_json, render_csv, render_html),
                    (render_json, render_csv, render_html)):
        assert a(build_report(original)) == b(build_report(shuffled))


def test_csv_is_readable_and_preserves_evidence() -> None:
    report = build_report(snapshot())
    rows = list(csv.DictReader(io.StringIO(render_csv(report))))
    assert any(row["section"] == "rule" and row["reference"] == "REG-PERFUME-CAP"
               and row["status"] == "FAIL" for row in rows)
    assert any(row["section"] == "data_gap" for row in rows)
    assert any(row["section"] == "perfume_classification" for row in rows)
    assert any(row["section"] == "component_source" and "SYNTH-DOC-A" in row["details_json"]
               for row in rows)


def test_html_escapes_untrusted_source_and_stays_offline() -> None:
    data = snapshot()
    data["formulations"][0]["product_names"] = ["<img src=x onerror=alert(1)>"]
    html = render_html(build_report(data))
    assert "<img" not in html
    assert "&lt;img" in html
    assert "http://" not in html and "https://" not in html
    assert "Not an official PCN filing" in html


def test_inconsistent_legal_snapshot_rejected_and_missing_data_not_suppressed() -> None:
    data = snapshot()
    data["decision"]["status"] = "ELIGIBLE"
    with pytest.raises(ValueError, match="failed rule"):
        build_report(data)
    data["decision"]["status"] = "REVIEW_REQUIRED"
    data["formulations"][1]["source_references"] = []
    report = build_report(data)
    assert "SOURCE_REFERENCES_MISSING:SYNTH-BETA@r2" in report["data_gaps"]
    data["decision"]["rule_results"] = []
    with pytest.raises(ValueError, match="rule_results missing"):
        build_report(data)


def test_malformed_and_decimal_json_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"concentration":5.0001}', encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden"):
        read_snapshot(bad)
    @dataclass(frozen=True)
    class Value:
        actual: Decimal
    assert to_wire(Value(Decimal("5.000100"))) == {"actual": "5.000100"}
    with pytest.raises(TypeError, match="binary-float"):
        to_wire(5.0001)


def test_reviewer_never_overrides_failed_or_draft_rulebook() -> None:
    report = build_report(snapshot())
    with pytest.raises(ValueError, match="cannot approve"):
        append_review(report, None, status="APPROVED", reviewer_id="audit-user",
                      reason="I approve anyway", timestamp="2026-11-12T18:00:00+00:00")
    rejection = append_review(report, None, status="REJECTED", reviewer_id="audit-user",
                              reason="Known 5.0001 failure", timestamp="2026-11-12T18:00:00Z")
    assert audit_status(rejection) == "REJECTED"
    assert report["summary"]["chemical_eligibility"] == "INELIGIBLE"
    assert attach_review(report, rejection)["review_workflow"]["status"] == "REJECTED"
    assert "review_event" in render_csv(attach_review(report, rejection))
    assert "Known 5.0001 failure" in render_html(attach_review(report, rejection))


def test_review_events_chained_timestamp_immutable_and_tamper_detected() -> None:
    report = build_report(snapshot())
    first = append_review(report, None, status="PENDING", reviewer_id="r1",
                          reason="awaiting regulator", timestamp="2026-11-12T18:00:00+00:00")
    second = append_review(report, first, status="REJECTED", reviewer_id="r2",
                           reason="failed limit", timestamp="2026-11-12T19:00:00+01:00")
    assert len(first["events"]) == 1  # original record not mutated
    assert len(second["events"]) == 2
    assert second["events"][1]["previous_hash"] == first["events"][0]["event_hash"]
    verify_audit(report, second)
    for key in ("timestamp", "reason", "status", "previous_hash"):
        modified = copy.deepcopy(second)
        modified["events"][0][key] = "tampered"
        with pytest.raises(ValueError):
            verify_audit(report, modified)
    changed_report = copy.deepcopy(report)
    changed_report["provenance"]["ruleset"]["sha256"] = "2" * 64
    with pytest.raises(ValueError, match="does not match"):
        verify_audit(changed_report, second)
    with pytest.raises(ValueError, match="timezone"):
        append_review(report, None, status="PENDING", reviewer_id="r1",
                      reason="missing offset", timestamp="2026-11-12T18:00:00")
    with pytest.raises(ValueError, match="duplicate"):
        append_review(report, first, status="PENDING", reviewer_id="r1",
                      reason="awaiting regulator", timestamp="2026-11-12T18:00:00+00:00")


def test_approved_review_is_not_pcn_approval() -> None:
    data = snapshot()
    data["decision"]["ruleset"]["status"] = "APPROVED"
    data["decision"]["status"] = "ELIGIBLE"
    data["decision"]["dossier_status"] = "REVIEW"  # dossier still incomplete
    data["decision"]["rule_results"] = [
        {"rule_id": "REG-CLASS", "status": "PASS", "explanation": "synthetic only",
         "source_sections": ["Annex VIII A.4.1"], "evidence_ids": ["EXAMPLE"], "values": []},
        {"rule_id": "REG-DOSSIER", "status": "REVIEW", "explanation": "not complete",
         "source_sections": ["Annex VIII A.4.4"], "evidence_ids": [], "values": []},
    ]
    data["decision"]["missing_data_flags"] = []
    report = build_report(data)
    audit = append_review(report, None, status="APPROVED", reviewer_id="r1",
                          reason="Reviewed display only", timestamp="2026-11-12T19:00:00Z")
    signed = attach_review(report, audit)
    assert signed["summary"]["submission_readiness"] == "NOT_VERIFIED"
    assert "Not an official PCN filing" in signed["disclaimer"]
    assert signed["review_workflow"]["status"] == "APPROVED"


def test_cli_generates_reproducible_files_and_review_log(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2] / "src"
    env = dict(__import__("os").environ, PYTHONPATH=str(root))
    out = tmp_path / "output"
    cmd = [sys.executable, "-m", "pcn_grouping.cli", "report", "--input", str(FIXTURE),
           "--output-dir", str(out)]
    first = subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
    assert "no PCN was submitted" in first.stdout
    before = {name: (out / name).read_bytes() for name in
              ("decision.json", "decision.csv", "decision.html")}
    subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
    assert before == {name: (out / name).read_bytes() for name in before}
    audit = tmp_path / "review.json"
    review_cmd = [sys.executable, "-m", "pcn_grouping.cli", "review", "--input",
                  str(FIXTURE), "--audit", str(audit), "--status", "REJECTED",
                  "--reviewer", "synthetic-reviewer", "--reason", "synthetic failure",
                  "--timestamp", "2026-11-12T18:00:00Z"]
    subprocess.run(review_cmd, capture_output=True, text=True, env=env, check=True)
    subprocess.run(cmd + ["--audit", str(audit)], capture_output=True,
                   text=True, env=env, check=True)
    assert json.loads((out / "decision.json").read_text())["review_workflow"]["status"] == "REJECTED"
    illegal = review_cmd.copy()
    illegal[illegal.index("REJECTED")] = "APPROVED"
    result = subprocess.run(illegal, capture_output=True, text=True, env=env)
    assert result.returncode != 0
    assert "cannot approve" in result.stderr
    assert len(json.loads(audit.read_text())["events"]) == 1
