"""Synthetic planner tests; the evaluator below is a test double, NOT legal logic."""

from __future__ import annotations

import itertools
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pcn_grouping.optimizer import optimise_portfolio  # noqa: E402


@dataclass(frozen=True)
class Formula:
    id: str
    revision: str = "r1"
    legal_submitter_id: str | None = "SUBMITTER-A"
    notification_mode: str = "STANDARD_FULL"
    approved_health_physical_classification: tuple[str, ...] | None = ("Eye Dam. 1",)
    classification_approved: bool | None = True
    approved_environment_classification: tuple[str, ...] = ()
    eupcs: tuple[str, ...] = ("PC-CLN-1",)
    product_names: tuple[str, ...] = ("Synthetic",)
    market_countries: tuple[str, ...] = ("DE",)


def whole_set_test_double(members: list[Formula], _ruleset: object) -> dict[str, str]:
    ids = {m.id for m in members}
    # Synthetic counterexample: every pair permitted, A+B+C prohibited.
    return {"status": "INELIGIBLE" if ids == {"A", "B", "C"} else "ELIGIBLE"}


def group_ids(plan: Any) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(item.id for item in group) for group in plan.groups)


def test_pairwise_compatibility_does_not_create_an_invalid_triple() -> None:
    forms = [Formula("A"), Formula("B"), Formula("C")]
    plan = optimise_portfolio(forms, {}, whole_set_test_double)
    assert group_ids(plan) == (("A", "B"),)
    assert tuple(x.id for x in plan.singletons) == ("C",)
    assert plan.grouped_count == 2
    assert any(t.status == "INELIGIBLE" and len(t.members) == 3 for t in plan.trials)
    assert len([t for t in plan.trials if t.post_validation]) == 1
    assert plan.globally_optimal is False


@pytest.mark.parametrize("order", list(itertools.permutations(range(4))))
def test_stable_permutation_invariance(order: tuple[int, ...]) -> None:
    formulas = [Formula(k) for k in ("A", "B", "C", "D")]
    plan = optimise_portfolio([formulas[i] for i in order], {}, whole_set_test_double)
    assert group_ids(plan) == (("A", "B", "D"),)
    assert tuple(f.id for f in plan.singletons) == ("C",)
    assert plan.globally_optimal is False


def test_no_eupcs_environment_name_or_country_prefilter() -> None:
    forms = [
        Formula("A", eupcs=("PC-CLN-1",), market_countries=("DE",)),
        Formula(
            "B",
            eupcs=("PC-DET-7",),
            approved_environment_classification=("Aquatic Chronic 2",),
            product_names=("Different trade name",),
            market_countries=("FR",),
        ),
    ]
    calls: list[tuple[str, ...]] = []

    def evaluator(members: list[Formula], _: object) -> dict[str, str]:
        calls.append(tuple(x.id for x in members))
        return {"status": "ELIGIBLE"}

    plan = optimise_portfolio(forms, {}, evaluator)
    assert group_ids(plan) == (("A", "B"),)
    assert calls == [("A", "B"), ("A", "B")]


def test_classification_order_is_canonical_and_complete_signature_is_compared() -> None:
    forms = [
        Formula("A", approved_health_physical_classification=("Skin Sens. 1", "Eye Dam. 1")),
        Formula("B", approved_health_physical_classification=("Eye Dam. 1", "Skin Sens. 1")),
        Formula("C", approved_health_physical_classification=("Eye Dam. 1",)),
    ]
    plan = optimise_portfolio(forms, {}, whole_set_test_double)
    assert group_ids(plan) == (("A", "B"),)
    assert tuple(item.id for item in plan.singletons) == ("C",)


def test_never_group_across_different_legal_submitter() -> None:
    forms = [Formula("A"), Formula("B", legal_submitter_id="SUBMITTER-B")]
    def evaluator(_members: list[Formula], _ruleset: object) -> object:
        pytest.fail("Evaluator must not be called across blocked submitter identities")

    plan = optimise_portfolio(forms, {}, evaluator)
    assert plan.groups == ()
    assert tuple(x.id for x in plan.singletons) == ("A", "B")
    assert plan.trials == ()


def test_unknown_and_unapproved_information_is_review_not_assumed_zero() -> None:
    forms = [
        Formula("A", approved_health_physical_classification=None),
        Formula("B", legal_submitter_id=None),
        Formula("C", notification_mode="INDUSTRIAL_LIMITED"),
        Formula("D", classification_approved=False),
        Formula("E", approved_health_physical_classification=()),
    ]
    plan = optimise_portfolio(forms, {}, whole_set_test_double)
    assert plan.groups == ()
    assert plan.singletons == ()
    assert len(plan.unresolved) == len(forms)
    assert {r.code for r in plan.unresolved} == {"PREFILTER_EVIDENCE_MISSING"}
    assert plan.trials == ()


def test_duplicate_revision_is_never_assumed_unique() -> None:
    formulas = [Formula("A"), Formula("A"), Formula("B")]
    plan = optimise_portfolio(formulas, {}, whole_set_test_double)
    assert plan.groups == ()
    assert [x.id for x in plan.singletons] == ["B"]
    assert len(plan.unresolved) == 2
    assert all(r.code == "DUPLICATE_REVISION" for r in plan.unresolved)


def test_evaluator_review_is_audited_without_any_claim_of_eligibility() -> None:
    def unknown(_members: list[Formula], _ruleset: object) -> dict[str, str]:
        return {"status": "REVIEW_REQUIRED", "reason": "Missing perfume evidence"}

    plan = optimise_portfolio([Formula("A"), Formula("B")], {}, unknown)
    assert plan.groups == ()
    assert tuple(x.id for x in plan.singletons) == ("A", "B")
    assert len(plan.trials) == 1
    assert plan.trials[0].status == "REVIEW_REQUIRED"
    assert "Missing perfume evidence" in plan.trials[0].reason


def test_unrecognised_status_and_exception_both_fail_closed() -> None:
    def bad_status(_members: list[Formula], _ruleset: object) -> dict[str, str]:
        return {"status": "PASS"}  # Not a GroupDecision status

    def raise_error(_members: list[Formula], _ruleset: object) -> object:
        raise RuntimeError("synthetic evaluator unavailable")

    for evaluator in (bad_status, raise_error):
        plan = optimise_portfolio([Formula("A"), Formula("B")], {}, evaluator)
        assert plan.groups == ()
        assert {t.status for t in plan.trials} == {"REVIEW_REQUIRED"}
        assert {item.id for item in plan.singletons} == {"A", "B"}


def test_every_final_group_must_pass_independent_fresh_post_validation() -> None:
    calls = 0

    def volatile(_members: list[Formula], _ruleset: object) -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"status": "ELIGIBLE" if calls == 1 else "INELIGIBLE"}

    plan = optimise_portfolio([Formula("A"), Formula("B")], {}, volatile)
    assert calls == 2, "A fresh post-validation call is mandatory"
    assert plan.groups == ()
    assert plan.singletons == ()
    assert {item.code for item in plan.unresolved} == {"POST_VALIDATION_NOT_ELIGIBLE"}
    assert [trial.post_validation for trial in plan.trials] == [False, True]


def test_final_review_is_not_silently_swallowed() -> None:
    calls = 0

    def volatile(_members: list[Formula], _ruleset: object) -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"status": "ELIGIBLE" if calls == 1 else "REVIEW_REQUIRED"}

    plan = optimise_portfolio([Formula("A"), Formula("B")], {}, volatile)
    assert plan.groups == ()
    assert len(plan.unresolved) == 2
    assert all("REVIEW_REQUIRED" in item.explanation for item in plan.unresolved)


def test_empty_portfolio_has_reproducible_empty_partition() -> None:
    plan = optimise_portfolio([], {}, whole_set_test_double)
    assert plan.groups == plan.singletons == plan.unresolved == plan.trials == ()
    assert not plan.globally_optimal


def test_input_immutability_and_version_distinction() -> None:
    original: Sequence[Formula] = (
        Formula("A", revision="r1"),
        Formula("A", revision="r2"),
    )
    snapshot = tuple(original)
    plan = optimise_portfolio(original, {"id": "DRAFT-v1"}, whole_set_test_double)
    assert original == snapshot
    assert group_ids(plan) == (("A", "A"),)
    assert plan.globally_optimal is False
