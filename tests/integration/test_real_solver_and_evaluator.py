"""Cross-branch integration smoke tests: B + C + D + E, without numeric mocks.

All data and APPROVED rule evidence created here are SYNTHETIC TEST-ONLY.
The actual checked-in regulatory ruleset remains unapproved and must fail closed.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from pcn_grouping.components import ComponentRules, EvidenceCatalog, IdentityRecord, LineEvidence
from pcn_grouping.concentration import find_common_declaration
from pcn_grouping.eligibility import (
    ApplicabilityEvidence, EligibilityContext, EligibilityDecision, ReviewedClassification,
    evaluate_group,
)
from pcn_grouping.models import (
    CLPClassification, Component, ComponentKind, ConcentrationValue, Evidence,
    EvidenceStatus, Formulation, GroupStatus, NotificationMode, PercentageBasis,
    RawBOMLine, RuleStatus,
)

RULE_FILE = (
    Path(__file__).resolve().parents[2]
    / "rulesets/annex_viii_2026_07_01.research-draft.json"
)


def _verified(label: str) -> Evidence:
    return Evidence(label, EvidenceStatus.VERIFIED, ("SYNTHETIC-SOURCE",),
                    "SYNTHETIC-TEST-REVIEWER", "2026-11-12")


def _rules(*, synthetic_approved: bool) -> ComponentRules:
    source = RULE_FILE.read_bytes()
    if synthetic_approved:
        data = json.loads(source)
        data["status"] = "APPROVED"
        data["ruleset_id"] = "SYNTHETIC_TEST_ONLY_NOT_A_LEGAL_RULESET"
        source = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return ComponentRules.from_json(
        source, _verified("SYNTHETIC-RULE-ATTESTATION") if synthetic_approved else None,
    )


def _ingredient(name: str, concentration: str, *, perfume: bool = False) -> Component:
    return Component(
        line_id=name,
        identity_id=name,
        kind=ComponentKind.SUBSTANCE,
        actual=ConcentrationValue(Decimal(concentration)),
        source_line_ids=(name,),
        source_document_ids=("SYNTHETIC-SOURCE",),
        identity_evidence=_verified("id:" + name),
        technical_function="PERFUME" if perfume else "SOLVENT",
        perfume_role_evidence=_verified("role:" + name) if perfume else None,
        confidence=EvidenceStatus.VERIFIED,
    )


CLP = CLPClassification(
    "Skin Irrit.", "2", "H315",
    status=EvidenceStatus.VERIFIED,
    source_document_ids=("SYNTHETIC-SOURCE",),
)


def _formula(name: str, base: str, *perfumes: tuple[str, str]) -> Formulation:
    ingredients = (_ingredient("BASE", base), *(
        _ingredient(key, value, perfume=True) for key, value in perfumes
    ))
    return Formulation(
        formulation_id=name,
        revision="v1",
        legal_submitter_id="SYNTHETIC-HOLDER",
        notification_mode=NotificationMode.STANDARD_FULL,
        composition_basis=PercentageBasis.MASS_PERCENT,
        components=ingredients,
        approved_health_physical_classification=(CLP,),
        raw_bom=tuple(
            RawBOMLine(c.line_id, "SYNTHETIC-SOURCE", (("identity", c.identity_id),))
            for c in ingredients
        ),
        product_names=(name,),
        market_countries=("IE",),
        use_types=("CONSUMER",),
        eupcs_codes=("PC-DET",),
        ufis=("0000-0000-0000-0000",),
        physical_state="liquid",
        colour="clear",
        ph="7",
        packaging=("bottle",),
        sds_section_11="synthetic disclosure",
    )


def _context(forms: tuple[Formulation, ...], *, approved: bool = True,
             classification_complete: bool = True) -> EligibilityContext:
    identities = {}
    lines = []
    for f in forms:
        for component in f.components:
            key = component.identity_id
            if key is None:
                raise ValueError("synthetic integration fixtures require known identities")
            identities[key] = IdentityRecord(
                key, ComponentKind.SUBSTANCE, "CLP_ART18", key,
                _verified("registry:" + key),
            )
            lines.append(LineEvidence(
                (f.formulation_id, f.revision, component.line_id),
                _verified("complete:" + f.formulation_id + component.line_id),
                _verified("function:" + f.formulation_id + component.line_id),
                True,
            ))
    return EligibilityContext(
        component_rules=_rules(synthetic_approved=approved),
        evidence_catalog=EvidenceCatalog(tuple(identities.values()), lines=tuple(lines)),
        classifications=tuple(
            ReviewedClassification(
                (f.formulation_id, f.revision),
                _verified("class:" + f.formulation_id),
            )
            for f in forms
        ) if classification_complete else (),
        applicability=tuple(
            ApplicabilityEvidence(
                (f.formulation_id, f.revision), True,
                _verified("applicability:" + f.formulation_id),
            )
            for f in forms
        ),
        evaluation_date="2026-11-12",
    )


def _code_for(decision: EligibilityDecision, rule_id: str) -> tuple[str, ...]:
    return tuple(
        dict(item.values).get("code", "")
        for item in decision.rule_results
        if item.rule_id == rule_id
    )


def test_real_c_solver_consumes_version_pinned_decimal_bands() -> None:
    rules = json.loads(_rules(synthetic_approved=True).source_json)
    feasible = find_common_declaration(
        [ConcentrationValue(Decimal("9.7")), ConcentrationValue(Decimal("10.5"))],
        "major_concern", rules,
    )
    impossible = find_common_declaration(
        [ConcentrationValue(Decimal("9")), ConcentrationValue(Decimal("11"))],
        "major_concern", rules,
    )
    assert feasible.status == "PASS"
    assert feasible.declaration.lower == Decimal("9.7")
    assert feasible.declaration.upper == Decimal("10.5")
    assert impossible.status == "FAIL"


def test_real_end_to_end_eligible_ineligible_and_review() -> None:
    first = _formula("A", "98", ("P-X", "2"))
    second = _formula("B", "98", ("P-Y", "2"))
    members = (first, second)
    eligible = evaluate_group(members, _context(members))
    assert eligible.status is GroupStatus.ELIGIBLE
    assert eligible.common_ranges and all(
        r.status is RuleStatus.PASS for r in eligible.common_ranges
    )
    assert _code_for(eligible, "REG-COMMON-RANGE")
    assert eligible.canonical_input_hash == evaluate_group(
        tuple(reversed(members)), _context(members),
    ).canonical_input_hash

    excess = _formula("C", "94.9999", ("P-X", "5.0001"))
    invalid = evaluate_group((excess, second), _context((excess, second)))
    assert invalid.status is GroupStatus.INELIGIBLE
    assert _code_for(invalid, "REG-PERFUME-CAP")

    missing = evaluate_group(
        members, _context(members, classification_complete=False),
    )
    assert missing.status is GroupStatus.REVIEW_REQUIRED

    unapproved = evaluate_group(members, _context(members, approved=False))
    assert unapproved.status is GroupStatus.REVIEW_REQUIRED
    assert "RULESET_NOT_APPROVED" in _code_for(unapproved, "E-RULESET")


def test_three_members_rejected_as_a_whole_despite_pairwise_passes() -> None:
    a = _formula("A", "96", ("P-X", "4"))
    b = _formula("B", "96", ("P-Y", "4"))
    c = _formula("C", "92", ("P-X", "4"), ("P-Y", "4"))
    assert evaluate_group((a, b), _context((a, b))).status is GroupStatus.ELIGIBLE
    assert evaluate_group((b, c), _context((b, c))).status is GroupStatus.ELIGIBLE
    result = evaluate_group((a, b, c), _context((a, b, c)))
    assert result.status is GroupStatus.INELIGIBLE
    assert any(t.actual.upper == Decimal("8") for t in result.varying_perfume_totals)
