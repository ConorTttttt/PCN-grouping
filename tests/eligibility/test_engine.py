"""Synthetic whole-group regression cases, with deterministic numerical stub.

The stub tests Agent E orchestration only; C's legal band implementation has
its own independently reviewed tests and is required for integration.
"""
import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from pcn_grouping.components import (
    ComponentRules, EvidenceCatalog, IdentityRecord, LineEvidence,
)
from pcn_grouping.components.rules import exact_sum
from pcn_grouping.eligibility import (
    ApplicabilityEvidence, EligibilityContext, ReviewedClassification,
    evaluate_group,
)
from pcn_grouping.models import (
    CLPClassification, Component, ComponentKind, ConcentrationValue,
    Evidence, EvidenceStatus, Formulation, GroupDecision, GroupStatus,
    NotificationMode, PercentageBasis, RawBOMLine, RuleStatus,
)


def proof(identifier="reviewed"):
    return Evidence(identifier, EvidenceStatus.VERIFIED, ("synthetic-source",),
                    "synthetic-reviewer", "2026-11-12")


def rules(*, draft=False):
    data = {
        "ruleset_id": "SYNTHETIC_ELIGIBILITY_TEST_ONLY",
        "status": "RESEARCH_DRAFT_NOT_EXECUTABLE_NOT_LEGAL_APPROVAL" if draft else "APPROVED",
        "legal_effective_consolidation": "2026-07-01",
        "group_finished_mixture": {
            "different_components_must_be_verified_perfumes": True,
            "maximum_differing_perfume_pct_per_mixture": "5",
        },
        "generic_component_identifiers": {
            "permitted": ["perfumes", "colouring agents"],
            "requires_exclusive_function": True,
            "prohibits_health_hazard_classification": True,
            "max_total_perfume_gci_pct": "5",
            "max_total_colouring_agents_gci_pct": "25",
        },
        "perfume_concentration_omission_in_group": {
            "if_not_classified_or_only": [
                "Skin Sens. 1", "Skin Sens. 1A", "Skin Sens. 1B", "Asp. Tox.",
            ],
        },
        "major_concern_component_hazard_categories": ["Acute Tox. 1", "Skin Corr. 1"],
        "maximum_concentration_range_width_percentage_points": {
            "major_concern": [
                {"min_exclusive": "0", "max_exclusive": "1", "max_width": "0.3"},
                {"min_inclusive": "1", "max_exclusive": "10", "max_width": "1"},
                {"min_inclusive": "10", "max_exclusive": "25", "max_width": "3"},
                {"min_inclusive": "25", "max_exclusive": "100", "max_width": "5"},
            ],
            "other": [
                {"min_exclusive": "0", "max_exclusive": "1", "max_width": "1"},
                {"min_inclusive": "1", "max_exclusive": "10", "max_width": "3"},
                {"min_inclusive": "10", "max_exclusive": "25", "max_width": "10"},
                {"min_inclusive": "25", "max_exclusive": "100", "max_width": "20"},
            ],
        },
    }
    return ComponentRules.from_json(json.dumps(data, sort_keys=True).encode(), proof())


def ingredient(identity, amount, role="PERFUME", hazards=()):
    return Component(
        identity, identity, ComponentKind.SUBSTANCE,
        ConcentrationValue(Decimal(amount)) if amount is not None else ConcentrationValue(None),
        (identity,), ("synthetic-source",), hazards,
        proof("id:" + identity), None, role,
        proof("role:" + identity) if role == "PERFUME" else None,
        EvidenceStatus.VERIFIED,
    )


MIXTURE_HAZARD = CLPClassification(
    "Skin Irrit.", "2", "H315", status=EvidenceStatus.VERIFIED,
    source_document_ids=("synthetic-source",),
)
MAJOR = CLPClassification(
    "Skin Corr.", "1", "H314", status=EvidenceStatus.VERIFIED,
    source_document_ids=("synthetic-source",),
)


def formula(name, *parts, submitter="duty-holder", hazard=(MIXTURE_HAZARD,),
            eu="PC-DET", environment=()):
    values = tuple(p.actual.value for p in parts if p.actual.value is not None)
    remaining = exact_sum((Decimal(100), *(v.copy_negate() for v in values)))
    components = (ingredient("base", str(remaining), role="SOLVENT"), *parts)
    return Formulation(
        name, "v1", submitter, NotificationMode.STANDARD_FULL,
        PercentageBasis.MASS_PERCENT, components,
        approved_health_physical_classification=hazard,
        approved_environment_classification=environment,
        raw_bom=tuple(RawBOMLine(c.line_id, "synthetic-source",
                                 (("name", c.identity_id),)) for c in components),
        product_names=(name,), market_countries=("IE",), use_types=("CONSUMER",),
        eupcs_codes=(eu,), ufis=("0000-0000-0000-0000",),
        physical_state="liquid", colour="clear", ph="7",
        packaging=("bottle",), sds_section_11="synthetic section 11",
    )


def catalog_for(*forms):
    identities = {}
    lines = []
    for f in forms:
        for c in f.components:
            identities[c.identity_id] = IdentityRecord(
                c.identity_id, ComponentKind.SUBSTANCE, "CLP_ART18", c.identity_id,
                proof("registry:" + c.identity_id),
            )
            lines.append(LineEvidence(
                (f.formulation_id, f.revision, c.line_id),
                proof("complete:" + f.formulation_id + c.line_id),
                proof("function:" + f.formulation_id + c.line_id),
                True,
            ))
    return EvidenceCatalog(tuple(identities.values()), lines=tuple(lines))


def mock_solver(actuals, component_class, source):
    """Deliberately synthetic numeric stub; real B.3.4 solver is Agent C."""
    low = min(x.lower for x in actuals)
    high = max(x.upper for x in actuals)
    width = exact_sum((high, low.copy_negate()))
    max_width = Decimal("1") if component_class == "major_concern" and low < 10 else Decimal("20")
    status = "PASS" if width <= max_width else "FAIL"
    return SimpleNamespace(
        status=status,
        reason_codes=(("MOCK_WIDTH_FEASIBLE" if status == "PASS"
                       else "MOCK_WIDTH_IMPOSSIBLE"),),
        declaration=(SimpleNamespace(lower=low, upper=high, exact=low == high)
                     if status == "PASS" else None),
        evidence=(f"synthetic_width={width}",),
    )


def context(forms, *, rulebook=None, complete=True, mandatory=True):
    return EligibilityContext(
        rulebook or rules(),
        catalog_for(*forms),
        tuple(ReviewedClassification((f.formulation_id, f.revision),
                                     proof("class:" + f.formulation_id))
              for f in forms) if complete else (),
        tuple(ApplicabilityEvidence((f.formulation_id, f.revision),
                                    mandatory, proof("scope:" + f.formulation_id))
              for f in forms),
        "2026-11-12",
    )


@pytest.fixture(autouse=True)
def deterministic_solver_stub(monkeypatch):
    monkeypatch.setattr("pcn_grouping.eligibility.engine._load_solver",
                        lambda: mock_solver)


def codes(decision):
    return {dict(r.values).get("code") for r in decision.rule_results}


def verdict(decision, rule):
    return [r.status for r in decision.rule_results if r.rule_id == rule]


def test_two_member_eligible_with_different_eupcs_and_environment():
    a = formula("A", ingredient("PX", "2"), eu="PC-DET")
    env = CLPClassification("Aquatic Chronic", "2", "H411",
                            status=EvidenceStatus.VERIFIED,
                            source_document_ids=("synthetic-source",))
    b = formula("B", ingredient("PY", "2"), eu="PC-CLN", environment=(env,))
    decision = evaluate_group([a, b], context([a, b]))
    assert isinstance(decision, GroupDecision)
    assert decision.status is GroupStatus.ELIGIBLE
    assert decision.applicability_status == "IN_SCOPE"
    assert {t.actual.upper for t in decision.varying_perfume_totals} == {Decimal(2)}
    assert len(decision.perfume_classification_matrix) == 2
    assert verdict(decision, "REG-CLASS") == [RuleStatus.PASS]
    assert verdict(decision, "REG-COMMON-RANGE") == [RuleStatus.PASS]


def test_three_member_perfume_failure_even_when_pairs_pass():
    a = formula("A", ingredient("PX", "4"))
    b = formula("B", ingredient("PY", "4"))
    c = formula("C", ingredient("PX", "4"), ingredient("PY", "4"))
    assert evaluate_group([a, b], context([a, b])).status is GroupStatus.ELIGIBLE
    assert evaluate_group([b, c], context([b, c])).status is GroupStatus.ELIGIBLE
    decision = evaluate_group([a, b, c], context([a, b, c]))
    assert decision.status is GroupStatus.INELIGIBLE
    assert any(t.revision == ("C", "v1") and t.actual.lower == Decimal(8)
               for t in decision.varying_perfume_totals)
    assert RuleStatus.FAIL in verdict(decision, "REG-PERFUME-CAP")


def test_exact_five_passes_and_tiny_excess_fails():
    a = formula("A", ingredient("PX", "5.0000"))
    b = formula("B", ingredient("PY", "5.0000"))
    assert evaluate_group([a, b], context([a, b])).status is GroupStatus.ELIGIBLE
    c = formula("C", ingredient("PX", "5.0001"))
    decision = evaluate_group([c, b], context([c, b]))
    assert decision.status is GroupStatus.INELIGIBLE
    assert RuleStatus.FAIL in verdict(decision, "REG-PERFUME-CAP")


def test_nonperfume_fail_outweighs_unknown_clp():
    a = formula("A", ingredient("PX", "2"))
    b = formula("B", ingredient("ADD", "2", role="SOLVENT"))
    decision = evaluate_group([a, b], context([a, b], complete=False))
    assert decision.status is GroupStatus.INELIGIBLE
    assert RuleStatus.FAIL in verdict(decision, "REG-COMPONENTS")
    assert RuleStatus.REVIEW in verdict(decision, "REG-CLASS")


def test_different_duty_holders_and_finished_hazards_fail():
    a = formula("A", ingredient("PX", "2"))
    hazard = CLPClassification(
        "Eye Irrit.", "2", "H319", status=EvidenceStatus.VERIFIED,
        source_document_ids=("synthetic-source",),
    )
    b = formula("B", ingredient("PY", "2"), submitter="another", hazard=(hazard,))
    decision = evaluate_group([a, b], context([a, b]))
    assert decision.status is GroupStatus.INELIGIBLE
    assert verdict(decision, "REG-SUBMITTER") == [RuleStatus.FAIL]
    assert verdict(decision, "REG-CLASS") == [RuleStatus.FAIL]


def test_missing_classification_or_scope_remains_review():
    a, b = formula("A", ingredient("PX", "2")), formula("B", ingredient("PY", "2"))
    missing = replace(context([a, b], complete=False), applicability=())
    decision = evaluate_group([a, b], missing)
    assert decision.status is GroupStatus.REVIEW_REQUIRED
    assert decision.applicability_status == "REVIEW"
    assert decision.missing_data_flags
    assert "CLASSIFICATION_COMPLETENESS_UNVERIFIED" in codes(decision)


def test_draft_rulebook_never_grants_eligibility():
    a, b = formula("A", ingredient("PX", "2")), formula("B", ingredient("PY", "2"))
    decision = evaluate_group([a, b], context([a, b], rulebook=rules(draft=True)))
    assert decision.status is GroupStatus.REVIEW_REQUIRED
    assert "RULESET_NOT_APPROVED" in codes(decision)


def test_unmerged_concentration_dependency_fails_closed(monkeypatch):
    monkeypatch.setattr("pcn_grouping.eligibility.engine._load_solver", lambda: None)
    a, b = formula("A", ingredient("PX", "2")), formula("B", ingredient("PY", "2"))
    decision = evaluate_group([a, b], context([a, b]))
    assert decision.status is GroupStatus.REVIEW_REQUIRED
    assert "RANGE_SOLVER_UNAVAILABLE" in codes(decision)


def test_whole_decision_and_hash_are_order_invariant():
    a, b = formula("A", ingredient("PX", "2")), formula("B", ingredient("PY", "2"))
    first_ctx = context([a, b])
    first = evaluate_group([a, b], first_ctx)
    shuffled = replace(
        first_ctx,
        evidence_catalog=replace(
            first_ctx.evidence_catalog,
            identities=tuple(reversed(first_ctx.evidence_catalog.identities)),
            lines=tuple(reversed(first_ctx.evidence_catalog.lines)),
        ),
        classifications=tuple(reversed(first_ctx.classifications)),
        applicability=tuple(reversed(first_ctx.applicability)),
    )
    reverse_a = replace(a, components=tuple(reversed(a.components)),
                        raw_bom=tuple(reversed(a.raw_bom)))
    reverse_b = replace(b, components=tuple(reversed(b.components)),
                        raw_bom=tuple(reversed(b.raw_bom)))
    second = evaluate_group([reverse_b, reverse_a], shuffled)
    assert first == second
    assert first.canonical_input_hash == second.canonical_input_hash


def test_dossier_gaps_do_not_block_chemical_grouping():
    a = formula("A", ingredient("PX", "2"))
    b = replace(formula("B", ingredient("PY", "2")), ufis=(), ph=None)
    decision = evaluate_group([a, b], context([a, b]))
    assert decision.status is GroupStatus.ELIGIBLE
    assert decision.dossier_status is RuleStatus.REVIEW


def test_out_of_scope_does_not_become_eligible():
    a, b = formula("A", ingredient("PX", "2")), formula("B", ingredient("PY", "2"))
    decision = evaluate_group([a, b], context([a, b], mandatory=False))
    assert decision.applicability_status == "OUT_OF_SCOPE"
    assert decision.status is GroupStatus.REVIEW_REQUIRED


def test_three_member_major_concern_range_not_pairwise_transitive():
    a = formula("A", ingredient("MAJOR", "9.0", role="OTHER", hazards=(MAJOR,)))
    b = formula("B", ingredient("MAJOR", "9.8", role="OTHER", hazards=(MAJOR,)))
    c = formula("C", ingredient("MAJOR", "10.4", role="OTHER", hazards=(MAJOR,)))
    assert evaluate_group([a, b], context([a, b])).status is GroupStatus.ELIGIBLE
    assert evaluate_group([b, c], context([b, c])).status is GroupStatus.ELIGIBLE
    decision = evaluate_group([a, b, c], context([a, b, c]))
    assert decision.status is GroupStatus.INELIGIBLE
    assert RuleStatus.FAIL in verdict(decision, "REG-MAJOR-BAND")


def test_versioned_hash_changes_with_attestation_evidence():
    a, b = formula("A", ingredient("PX", "2")), formula("B", ingredient("PY", "2"))
    ctx = context([a, b])
    decision = evaluate_group([a, b], ctx)
    changed = replace(ctx, classifications=(
        replace(ctx.classifications[0], complete=proof("new-source")),
        *ctx.classifications[1:],
    ))
    assert decision.canonical_input_hash != evaluate_group([a, b], changed).canonical_input_hash
