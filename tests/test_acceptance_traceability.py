"""Audit requirements-to-fixture coverage without treating gaps as passes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent / "fixtures"


def read(filename: str) -> dict[str, Any]:
    return json.loads((ROOT / filename).read_text(encoding="utf-8"))


def test_traceability_report_matches_case_oracles() -> None:
    cases = read("acceptance_cases.json")["cases"]
    report = read("rule_traceability.json")
    assert report["legal_review"] == "PENDING_AGENT_A"
    expected: dict[str, dict[str, list[str]]] = {}
    for case in cases:
        for rule, verdict in case["expected_rules"].items():
            expected.setdefault(rule, {
                "PASS": [], "FAIL": [], "REVIEW": [],
                "OUT_OF_SCOPE": [], "UPDATE": [],
            })[verdict].append(case["id"])
    for statuses in expected.values():
        for ids in statuses.values():
            ids.sort()
    assert report["rule_coverage"] == expected


def test_primary_hard_gates_have_passing_and_failing_cases() -> None:
    coverage = read("rule_traceability.json")["rule_coverage"]
    hard_gates = [
        "ECHA5.4_LEGAL_SUBMITTER", "A4.1_CLASSIFICATION",
        "A4.2_COMPONENT_IDENTITY", "A4.2_DECLARED_RANGE",
        "A4.3_VARYING_PERFUMES", "B3.2.3_GCI",
    ]
    for rule in hard_gates:
        assert coverage[rule]["PASS"], f"Missing positive for {rule}"
        assert coverage[rule]["FAIL"], f"Missing negative for {rule}"
    for rule in (
        "ECHA5.4_LEGAL_SUBMITTER", "A4.1_CLASSIFICATION",
        "A4.3_VARYING_PERFUMES", "B3.2.3_GCI",
    ):
        assert coverage[rule]["REVIEW"], f"Missing missing-evidence case for {rule}"


def test_guidance_examples_are_not_mistaken_for_complete_golden_dossiers() -> None:
    guidance = read("echa_guidance_examples_23_24.json")
    assert {x["id"] for x in guidance["examples"]} == {"ECHA-23", "ECHA-24"}
    for example in guidance["examples"]:
        assert example["evidence_completeness"] == "PARTIAL_EXCERPT"
        assert example["missing_from_excerpt"]
        assert example["full_evaluator_expected_without_synthetic_completion"] == "REVIEW_REQUIRED"
