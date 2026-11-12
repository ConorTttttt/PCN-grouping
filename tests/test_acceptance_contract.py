"""Requirements-level QA contract tests. No runtime legal verdict is inferred here."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DOC_CASE_IDS = {
    "P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09",
    "P10", "P11", "P12", "P13",
    "N01", "N02", "N03", "N04", "N05", "N06", "N07",
    "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10",
    "S01", "S02", "M01", "M02", "M03", "M04",
}
RULE_OUTCOMES = {"PASS", "FAIL", "REVIEW", "OUT_OF_SCOPE", "UPDATE"}
CASE_STATUSES = {
    "ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED", "OUT_OF_SCOPE",
    "UPDATE", "SAME", "VERSIONED",
}


def load_json(filename: str) -> dict[str, Any]:
    value = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def decimal_string(value: object) -> Decimal:
    assert isinstance(value, str), "No binary float/int concentrations in source fixtures"
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise AssertionError(f"Not an exact decimal: {value}") from exc
    assert number.is_finite()
    assert Decimal("0") <= number <= Decimal("100")
    return number


def cases() -> list[dict[str, Any]]:
    return load_json("acceptance_cases.json")["cases"]


def test_fixture_provenance_and_catalogue_completeness() -> None:
    data = load_json("acceptance_cases.json")
    assert data["synthetic_only"] is True
    assert data["status"] == "RESEARCH_DRAFT_NOT_LEGAL_APPROVAL"
    assert data["requirements"] == "docs/acceptance-tests.md"
    observed = [case["id"] for case in data["cases"]]
    assert len(observed) == len(set(observed))
    assert DOC_CASE_IDS <= set(observed), "A required catalogue case is missing"
    assert len(observed) >= 36, "Guard against a truncated fixture suite"


@pytest.mark.parametrize("case", cases(), ids=lambda c: str(c["id"]))
def test_synthetic_record_contract(case: dict[str, Any]) -> None:
    assert case["expected_status"] in CASE_STATUSES
    assert case["expected_rules"]
    assert case["kind"] in {"positive", "negative", "edge", "review", "scope", "lifecycle", "property"}
    assert set(case["expected_rules"].values()) <= RULE_OUTCOMES
    ids: set[tuple[str, str]] = set()
    for formula in case["formulations"]:
        assert formula["id"] and formula["revision"]
        key = (formula["id"], formula["revision"])
        assert key not in ids
        ids.add(key)
        component_ids: set[str] = set()
        all_exact = True
        total = Decimal("0")
        for component in formula["components"]:
            component_id = component["canonical_identity_id"]
            assert component_id and component_id not in component_ids
            component_ids.add(component_id)
            assert component["composition_evidence"] == "SYNTHETIC"
            lo, hi = component["actual_min_pct"], component["actual_max_pct"]
            if lo is None or hi is None:
                assert case["expected_status"] == "REVIEW_REQUIRED"
                all_exact = False
                continue
            lower, upper = decimal_string(lo), decimal_string(hi)
            assert lower <= upper
            all_exact &= lower == upper
            total += lower
            assert not (component["verified_perfume"] and component["perfume_role_evidence"] is None and case["expected_status"] == "ELIGIBLE")
        if all_exact:
            if case["id"] == "R09" and formula["id"] == "A":
                assert total == Decimal("99")
            else:
                assert total == Decimal("100"), f"{case['id']}:{formula['id']} sums to {total}"


def test_threshold_is_exact_and_inclusive() -> None:
    lookup = {case["id"]: case for case in cases()}
    pass_pct = lookup["P04"]["formulations"][0]["components"][1]["actual_min_pct"]
    fail_pct = lookup["N01"]["formulations"][0]["components"][1]["actual_min_pct"]
    assert decimal_string(pass_pct) == Decimal("5.0000")
    assert decimal_string(fail_pct) == Decimal("5.0001")
    assert decimal_string(pass_pct) <= Decimal("5") < decimal_string(fail_pct)
    assert lookup["P04"]["expected_rules"]["A4.3_VARYING_PERFUMES"] == "PASS"
    assert lookup["N01"]["expected_rules"]["A4.3_VARYING_PERFUMES"] == "FAIL"


def test_pairwise_but_not_whole_group_counterexample() -> None:
    case = next(c for c in cases() if c["id"] == "P12")
    amounts = {
        f["id"]: {
            c["canonical_identity_id"]: decimal_string(c["actual_min_pct"])
            for c in f["components"] if c["verified_perfume"]
        }
        for f in case["formulations"]
    }

    def varies_above_five(members: tuple[str, ...]) -> bool:
        common = set.intersection(*(set(amounts[m]) for m in members))
        return any(
            sum((pct for key, pct in amounts[m].items() if key not in common), Decimal("0"))
            > Decimal("5")
            for m in members
        )

    from itertools import combinations

    assert all(not varies_above_five(pair) for pair in combinations(("A", "B", "C"), 2))
    assert varies_above_five(("A", "B", "C"))
    assert case["expected_status"] == "INELIGIBLE"


def test_ambiguous_requirements_are_not_promoted_to_gold() -> None:
    lookup = {case["id"]: case for case in cases()}
    for case_id in ("P10", "R10"):
        assert lookup[case_id]["regulatory_review"], "Unresolved interpretation must be flagged"
    assert lookup["R05"]["expected_status"] == "REVIEW_REQUIRED"
    assert lookup["R06"]["expected_status"] == "REVIEW_REQUIRED"
    assert lookup["R09"]["expected_status"] == "REVIEW_REQUIRED"


def test_echa_example_23_verified_exact_differing_totals() -> None:
    guidance = load_json("echa_guidance_examples_23_24.json")
    example = next(e for e in guidance["examples"] if e["id"] == "ECHA-23")
    assert example["pages"] == [76, 77]
    assert example["evidence_completeness"] == "PARTIAL_EXCERPT"
    assert example["full_evaluator_expected_without_synthetic_completion"] == "REVIEW_REQUIRED"
    for product in example["products"]:
        total = sum(
            (decimal_string(p["actual_pct"]) for p in product["varying_perfumes"]),
            Decimal("0"),
        )
        assert total == decimal_string(product["varying_perfume_sum_expected_pct"])
        assert total <= Decimal("5")
    assert {p["name"]: p["varying_perfume_sum_expected_pct"] for p in example["products"]} == {
        "Trade name 1": "2.8", "Trade name 2": "3.2",
    }


def test_echa_example_24_group_membership_is_verified_but_actuals_absent() -> None:
    guidance = load_json("echa_guidance_examples_23_24.json")
    example = next(e for e in guidance["examples"] if e["id"] == "ECHA-24")
    assert example["pages"] == [78, 79]
    assert example["full_evaluator_expected_without_synthetic_completion"] == "REVIEW_REQUIRED"
    memberships = example["varying_perfume_ids_by_product"]
    assert memberships == {
        "ABC": ["Perfume mixture a", "Perfume mixture b"],
        "BCD": ["Perfume (GCI)"],
        "CDE": ["Perfume mixture b", "Perfume (GCI)"],
    }
    assert all("actual_pct" not in perfume for perfume in example["variable_perfumes"])
    assert example["missing_from_excerpt"], "No fabricated full-data golden eligibility result"


def _max_width_at(concern: str, point: Decimal) -> Decimal:
    """Independent *research-draft* table oracle (not an engine implementation)."""
    assert Decimal("0") < point < Decimal("100")
    if concern == "MAJOR":
        table = [
            ("0.1", "0.1"), ("1", "0.3"), ("10", "1"),
            ("25", "3"), ("100", "5"),
        ]
    else:
        table = [("1", "1"), ("10", "3"), ("25", "10"), ("100", "20")]
    return next(Decimal(width) for upper, width in table if point < Decimal(upper))


def _range_possible(concern: str, lower: Decimal, upper: Decimal) -> bool:
    width = upper - lower
    if lower == upper:
        return True
    points = {lower, upper}
    for boundary in ("0.1", "1", "10", "25"):
        candidate = Decimal(boundary)
        if lower < candidate < upper:
            points.add(candidate)
    # A segment crossing a boundary must satisfy the stricter adjacent zone.
    for point in points:
        if not Decimal("0") < point < Decimal("100"):
            return False
        if width > _max_width_at(concern, point):
            return False
    return True


@pytest.mark.parametrize("datum", load_json("concentration_boundaries.json")["zones"])
def test_research_draft_table_zone_edges(datum: dict[str, str]) -> None:
    assert _max_width_at(datum["class"], Decimal(datum["at"])) == Decimal(datum["expected_width"])


@pytest.mark.parametrize("datum", load_json("concentration_boundaries.json")["intervals"])
def test_research_draft_cross_zone_examples(datum: dict[str, str]) -> None:
    result = _range_possible(datum["class"], Decimal(datum["lo"]), Decimal(datum["hi"]))
    assert result == (datum["expected"] == "PASS")
