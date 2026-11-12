"""Synthetic ABI and planner tests. Fake evaluator does NOT encode CLP law."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from enum import Enum
from types import SimpleNamespace

import pytest

from pcn_grouping.optimizer import optimise_portfolio


class Verdict(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class CLP:
    hazard_class: str = "Skin Irrit."
    category: str = "2"
    h_code: str = "H315"
    route: str | None = None
    qualifier: str | None = None
    status: str = "VERIFIED"
    source_document_ids: tuple[str, ...] = ("classification-sds",)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str = "complete"
    status: str = "VERIFIED"
    source_document_ids: tuple[str, ...] = ("reviewed-sds",)
    verified_by: str | None = "regulatory-reviewer"
    verified_at: str | None = "2026-11-12"


@dataclass(frozen=True)
class Formula:
    formulation_id: str
    revision: str = "1"
    legal_submitter_id: str | None = "submitter-a"
    notification_mode: str = "STANDARD_FULL"
    approved_health_physical_classification: tuple[CLP, ...] = (CLP(),)
    eupcs_codes: tuple[str, ...] = ("PC-DET",)
    market_countries: tuple[str, ...] = ("DE",)
    approved_environment_classification: tuple[str, ...] = ()


@dataclass(frozen=True)
class Attestation:
    revision: tuple[str, str]
    complete: Evidence = Evidence()


def context(*forms: Formula, omit: tuple[str, ...] = ()): 
    return SimpleNamespace(classifications=tuple(
        Attestation((f.formulation_id, f.revision)) for f in forms
        if f.formulation_id not in omit
    ))


def ids(plan):
    return tuple(tuple(x.formulation_id for x in group) for group in plan.groups)


def evaluator(members, _ctx):
    """Test-only oracle: all pairs pass; {A,B,C} fails."""
    return SimpleNamespace(
        status=Verdict.INELIGIBLE if {f.formulation_id for f in members} == {"A", "B", "C"}
        else Verdict.ELIGIBLE,
        rule_results=(),
    )


def test_canonical_formulation_id_and_e_approval_contract():
    a, b = Formula("A"), Formula("B")
    plan = optimise_portfolio([b, a], context(a, b), evaluator)
    assert ids(plan) == (("A", "B"),)
    assert len(plan.trials) == 2
    assert plan.trials[1].post_validation
    assert plan.globally_optimal is False


@pytest.mark.parametrize("order", itertools.permutations(range(4)))
def test_permutation_invariance_with_real_model_field_names(order):
    forms = tuple(Formula(ch) for ch in "ABCD")
    plan = optimise_portfolio([forms[i] for i in order], context(*forms), evaluator)
    assert ids(plan) == (("A", "B", "D"),)
    assert tuple(s.formulation_id for s in plan.singletons) == ("C",)
    assert plan.singleton_reasons[0].code == "NO_ELIGIBLE_COMBINATION"
    assert len(plan.unresolved) == 0


def test_evidence_source_ids_not_part_of_comparable_clp_hazard_signature():
    a = Formula("A")
    b = Formula("B", approved_health_physical_classification=(
        CLP(source_document_ids=("second-sds",)),
    ))
    assert ids(optimise_portfolio([a, b], context(a, b), evaluator)) == (("A", "B"),)


def test_complete_health_physical_signature_is_compared_including_route_and_qualifier():
    a = Formula("A")
    b = Formula("B", approved_health_physical_classification=(CLP(route="inhalation"),))
    plan = optimise_portfolio([a, b], context(a, b), evaluator)
    assert plan.groups == ()
    assert [x.code for x in plan.singleton_reasons] == ["NO_PREFILTER_MATCH"] * 2
    assert not plan.trials


def test_unknown_or_duplicate_attestation_cannot_authorize_grouping():
    a, b = Formula("A"), Formula("B")
    no_b = optimise_portfolio([a, b], context(a), evaluator)
    assert [x.formulation.formulation_id for x in no_b.unresolved] == ["B"]
    assert no_b.singletons == (a,)
    duplicated = SimpleNamespace(classifications=(
        Attestation(("A", "1")), Attestation(("A", "1")), Attestation(("B", "1")),
    ))
    plan = optimise_portfolio([a, b], duplicated, evaluator)
    assert plan.groups == ()
    assert {x.formulation.formulation_id for x in plan.unresolved} == {"A"}


def test_unverified_complete_attestation_cannot_authorize_grouping():
    a, b = Formula("A"), Formula("B")
    unverified = SimpleNamespace(classifications=(
        Attestation(("A", "1"), replace(Evidence(), status="UNKNOWN")),
        Attestation(("B", "1")),
    ))
    plan = optimise_portfolio([a, b], unverified, evaluator)
    assert {x.formulation.formulation_id for x in plan.unresolved} == {"A"}
    assert plan.groups == ()


def test_unverified_clp_row_not_authorized_even_if_complete_attestation_exists():
    a, b = Formula("A"), Formula("B", approved_health_physical_classification=(
        CLP(status="UNKNOWN"),
    ))
    plan = optimise_portfolio([a, b], context(a, b), evaluator)
    assert plan.groups == ()
    assert len(plan.unresolved) == 1
    assert plan.unresolved[0].formulation == b


def test_incomplete_metadata_is_review_not_zero_or_in_scope_guess():
    a, b = Formula("A"), replace(Formula("B"), legal_submitter_id=None)
    c = replace(Formula("C"), notification_mode="INDUSTRIAL_LIMITED")
    plan = optimise_portfolio([a, b, c], context(a, b, c), evaluator)
    assert plan.groups == ()
    assert [x.code for x in plan.unresolved] == ["PREFILTER_EVIDENCE_MISSING"] * 2


def test_env_eupcs_market_names_not_prefilter_reasons():
    a = Formula("A")
    b = Formula("B", eupcs_codes=("PC-CLN",), market_countries=("FR",),
                approved_environment_classification=("H411",))
    assert ids(optimise_portfolio([a, b], context(a, b), evaluator)) == (("A", "B"),)


def test_duplicate_revisions_are_isolated_and_canonically_sorted():
    a = Formula("A")
    distinct = replace(a, market_countries=("FR",))
    b = Formula("B")
    first = optimise_portfolio([distinct, b, a], context(a, distinct, b), evaluator)
    second = optimise_portfolio([a, distinct, b], context(a, distinct, b), evaluator)
    assert first == second
    assert len(first.unresolved) == 2
    assert tuple(r.code for r in first.unresolved) == ("DUPLICATE_REVISION",) * 2


def test_triple_counterexample_must_not_infer_transitive_eligibility():
    a, b, c = (Formula(ch) for ch in "ABC")
    plan = optimise_portfolio([c, b, a], context(a, b, c), evaluator)
    assert ids(plan) == (("A", "B"),)
    assert plan.singletons == (c,)
    assert any(len(t.members) == 3 and t.status == "INELIGIBLE" for t in plan.trials)


def test_rejected_review_reason_is_exposed_per_singleton():
    a, b = Formula("A"), Formula("B")
    decision = SimpleNamespace(status=Verdict.REVIEW_REQUIRED, rule_results=(
        SimpleNamespace(status="REVIEW", rule_id="REG-PERFUME", values=(("code", "MISSING_EVIDENCE"),)),
    ))
    plan = optimise_portfolio([a, b], context(a, b), lambda *_: decision)
    assert plan.groups == ()
    assert [s.code for s in plan.singleton_reasons] == ["CANDIDATE_REQUIRES_REVIEW"] * 2
    assert "REG-PERFUME:MISSING_EVIDENCE" in plan.trials[0].reason
    assert all("MISSING_EVIDENCE" in r.explanation for r in plan.singleton_reasons)


def test_fresh_postvalidation_failure_is_unresolved():
    a, b = Formula("A"), Formula("B")
    calls = 0
    def changing(*_args):
        nonlocal calls
        calls += 1
        return SimpleNamespace(status=(Verdict.ELIGIBLE if calls == 1 else Verdict.REVIEW_REQUIRED))
    plan = optimise_portfolio([a, b], context(a, b), changing)
    assert calls == 2
    assert plan.groups == ()
    assert plan.singletons == ()
    assert len(plan.unresolved) == 2
    assert all(r.code == "POST_VALIDATION_NOT_ELIGIBLE" for r in plan.unresolved)


def test_unrecognized_evaluator_result_or_exception_fails_closed():
    a, b = Formula("A"), Formula("B")
    for bad in (
        lambda *_: {"status": "PASS"},
        lambda *_: (_ for _ in ()).throw(RuntimeError("synthetic")),
    ):
        plan = optimise_portfolio([a, b], context(a, b), bad)
        assert plan.groups == ()
        assert {t.status for t in plan.trials} == {"REVIEW_REQUIRED"}


def test_empty_portfolio_and_no_mutation():
    assert optimise_portfolio([], None, evaluator).groups == ()
    a, b = Formula("A"), Formula("B")
    initial = (b, a)
    optimise_portfolio(initial, context(a, b), evaluator)
    assert initial == (b, a)
