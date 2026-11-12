"""Synthetic evidence tests, not regulatory certification or real supplier data."""

import hashlib
import itertools
import json
from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from pcn_grouping.components import (
    ComponentRules,
    EvidenceCatalog,
    IdentityAlias,
    IdentityRecord,
    LineEvidence,
    MiMRouteEvidence,
    RepresentationApproval,
    analyse_components,
    normalise_identifier,
    resolve_identity,
)
from pcn_grouping.components.rules import exact_sum
from pcn_grouping.models import (
    CLPClassification,
    Component,
    ComponentKind,
    ConcentrationInterval,
    ConcentrationValue,
    Evidence,
    EvidenceStatus,
    Formulation,
    MiMIdentifiers,
    NotificationMode,
    NotifiedComponent,
    PercentageBasis,
    RawBOMLine,
    RuleStatus,
)


def proof(name="synthetic-review", documents=("synthetic-source",)):
    return Evidence(name, EvidenceStatus.VERIFIED, documents, "synthetic-reviewer", "2026-11-12")


def rules_json():
    return json.dumps(
        {
            "ruleset_id": "SYNTHETIC_COMPONENT_TEST_ONLY",
            "status": "APPROVED",
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
                    "Skin Sens. 1",
                    "Skin Sens. 1A",
                    "Skin Sens. 1B",
                    "Asp. Tox.",
                ],
            },
        }
    ).encode()


@pytest.fixture
def rules():
    return ComponentRules.from_json(rules_json(), proof("synthetic-rule-approval"))


def ingredient(identity, percent="2", role="PERFUME", *, line_id=None, hazards=(), mim=None):
    return Component(
        line_id or identity,
        identity,
        ComponentKind.MIM if mim else ComponentKind.SUBSTANCE,
        ConcentrationValue(None if percent is None else Decimal(percent)),
        (line_id or identity,),
        ("synthetic-source",),
        hazards,
        proof("identity-" + identity),
        mim,
        role,
        proof("perfume-" + identity) if role == "PERFUME" else None,
        EvidenceStatus.VERIFIED,
    )


def formula(name, *components):
    # Synthetic residual base; sums stay exact and never use binary floats.
    known = tuple(
        c.actual.value
        for c in components
        if isinstance(c.actual, ConcentrationValue) and c.actual.value is not None
    )
    residual = exact_sum((Decimal(100), *(v.copy_negate() for v in known)))
    base = ingredient("base", str(residual), "SOLVENT")
    all_components = (base, *components)
    return Formulation(
        name,
        "v1",
        "synthetic-duty-holder",
        NotificationMode.STANDARD_FULL,
        PercentageBasis.MASS_PERCENT,
        all_components,
        raw_bom=tuple(
            RawBOMLine(c.line_id, "synthetic-source", (("identity", c.identity_id),))
            for c in all_components
        ),
        market_countries=("IE",),
    )


def catalog_for(*forms):
    records = {}
    lines = []
    for f in forms:
        for c in f.components:
            records[c.identity_id] = IdentityRecord(
                c.identity_id,
                c.kind,
                "SUPPLIER_PRODUCT" if c.mim else "CLP_ART18",
                c.identity_id,
                proof("registry-" + c.identity_id),
                c.mim.supplier_id if c.mim else None,
                c.mim.supplier_product_id if c.mim else None,
            )
            lines.append(
                LineEvidence(
                    (f.formulation_id, f.revision, c.line_id),
                    proof("complete-classification"),
                    proof("technical-function"),
                    True,
                )
            )
    return EvidenceCatalog(tuple(records.values()), lines=tuple(lines))


def run(*forms, rules, catalog=None):
    return analyse_components(forms, catalog or catalog_for(*forms), rules)


def codes(result):
    return {dict(r.values)["code"] for r in result.rule_results}


def verdicts(result, rule):
    return [r.status for r in result.rule_results if r.rule_id == rule]


def change_line(catalog, ref, **changes):
    return replace(
        catalog, lines=tuple(replace(e, **changes) if e.line == ref else e for e in catalog.lines)
    )


def declared(f, *ids, name="approved-representation", omitted=False):
    declarations = [
        NotifiedComponent("declaration-base", "base", ConcentrationValue(Decimal(90)), ("base",))
    ]
    declarations.append(
        NotifiedComponent(
            "declaration",
            name,
            None if omitted else ConcentrationValue(Decimal(2)),
            tuple(ids),
            "PERFUME_CONCENTRATION_OMISSION" if omitted else None,
        )
    )
    return replace(f, notified_components=tuple(declarations))


def representation(
    catalog,
    rules,
    forms,
    members,
    *,
    kind="GCI",
    function="COLOURANT",
    name="approved-representation",
    **changes,
):
    a = RepresentationApproval(
        name,
        kind,
        tuple(members),
        tuple((f.formulation_id, f.revision) for f in forms),
        rules.version.sha256,
        proof("scoped-prior-approval"),
        function,
    )
    return replace(catalog, representations=(replace(a, **changes),))


def test_similar_names_never_merge(rules):
    a = formula("A", ingredient("Lemon blend 1", role="SOLVENT"))
    b = formula("B", ingredient("Lemon blend I", role="SOLVENT"))
    result = run(a, b, rules=rules)
    assert result.status is RuleStatus.FAIL
    assert result.common_raw_keys == (("SUBSTANCE", "base"),)
    assert "VARYING_NON_PERFUME" in codes(result)


def test_canonical_identity_and_explicit_alias(rules):
    a = formula("A", ingredient("approved-id"))
    b = formula("B", ingredient("supplier-alias"))
    catalog = catalog_for(a, b)
    catalog = replace(
        catalog,
        identities=tuple(i for i in catalog.identities if i.identity_id != "supplier-alias"),
        aliases=(IdentityAlias("supplier-alias", "approved-id", ComponentKind.SUBSTANCE, proof()),),
    )
    result = run(a, b, rules=rules, catalog=catalog)
    assert result.status is RuleStatus.PASS
    assert result.varying_raw_keys == ()
    assert result.matrix[-1].source_line_ids == ("supplier-alias",)
    invalid = replace(catalog, aliases=(replace(catalog.aliases[0], evidence=None),))
    assert run(a, b, rules=rules, catalog=invalid).status is RuleStatus.REVIEW


@pytest.mark.parametrize(
    "scheme,raw,expected",
    [
        ("CAS", " 64-17-5 ", "64-17-5"),
        ("EC", "200-578-6", "200-578-6"),
        ("UFI", "0000000000000000", "0000-0000-0000-0000"),
    ],
)
def test_identifier_formats(scheme, raw, expected):
    assert normalise_identifier(scheme, raw) == expected


@pytest.mark.parametrize(
    "scheme,raw",
    [
        ("CAS", "64-17-6"),
        ("EC", "200-578-7"),
        ("UFI", "IIII-OOOO-BBBB-ZZZZ"),
        ("CONFIDENTIAL", "secret"),
    ],
)
def test_bad_identifier_requires_review(scheme, raw):
    with pytest.raises(ValueError):
        normalise_identifier(scheme, raw)


def test_no_cas_ec_allowed_only_with_unequivocal_reviewed_identity(rules):
    f = formula("A", ingredient("international-chemical-name"))
    assert run(f, rules=rules).status is RuleStatus.PASS
    catalog = catalog_for(f)
    catalog = replace(
        catalog,
        identities=tuple(
            replace(i, identifier_scheme="CONFIDENTIAL") if i.identity_id != "base" else i
            for i in catalog.identities
        ),
    )
    assert run(f, rules=rules, catalog=catalog).status is RuleStatus.REVIEW


@pytest.mark.parametrize(
    "amount,status",
    [("4.9999", RuleStatus.PASS), ("5.0000", RuleStatus.PASS), ("5.0001", RuleStatus.FAIL)],
)
def test_varying_cap_exact_edges(rules, amount, status):
    a, b = formula("A", ingredient("p", amount)), formula("B", ingredient("q", "5"))
    result = run(a, b, rules=rules)
    assert result.status is status
    assert result.varying_perfume_totals[0].actual.exact == Decimal(amount)


def test_shared_perfume_excluded_even_above_five_total(rules):
    a = formula("A", ingredient("shared", "2"), ingredient("p", "4"))
    b = formula("B", ingredient("shared", "2"), ingredient("q", "4"))
    result = run(a, b, rules=rules)
    assert result.status is RuleStatus.PASS
    assert [t.actual.exact for t in result.varying_perfume_totals] == [Decimal(4), Decimal(4)]


def test_whole_group_pairwise_counterexample(rules):
    a = formula("A", ingredient("p", "4"))
    b = formula("B", ingredient("q", "4"))
    c = formula("C", ingredient("p", "4"), ingredient("q", "4"))
    for pair in itertools.combinations((a, b, c), 2):
        assert run(*pair, rules=rules).status is RuleStatus.PASS
    whole = run(a, b, c, rules=rules)
    assert whole.status is RuleStatus.FAIL
    assert whole.varying_perfume_totals[2].actual.exact == Decimal(8)


def test_example_23_arithmetic_synthetic_completion(rules):
    # The 2.8/3.2 varying totals come from A's guidance transcription.
    # Base and shared amounts here are synthetic, not asserted ECHA inputs.
    a = formula(
        "A",
        ingredient("p1", "1.2"),
        ingredient("p2", "0.6"),
        ingredient("p3", "1.0"),
        ingredient("shared5", "2"),
    )
    b = formula(
        "B",
        ingredient("p4", "0.4"),
        ingredient("p6", "1.4"),
        ingredient("p7", "1.4"),
        ingredient("shared5", "2"),
    )
    result = run(a, b, rules=rules)
    assert [t.actual.exact for t in result.varying_perfume_totals] == [
        Decimal("2.8"),
        Decimal("3.2"),
    ]


@pytest.mark.parametrize(
    "actual,status",
    [
        (None, RuleStatus.REVIEW),
        (ConcentrationInterval(Decimal("4.8"), Decimal("5.2")), RuleStatus.REVIEW),
        (ConcentrationInterval(Decimal("5.1"), Decimal("5.2")), RuleStatus.FAIL),
        (ConcentrationInterval(Decimal("4.8"), Decimal("5")), RuleStatus.PASS),
    ],
)
def test_intervals_and_unknowns(rules, actual, status):
    a = formula("A", replace(ingredient("p"), actual=actual))
    b = formula("B", ingredient("q"))
    result = run(a, b, rules=rules)
    assert result.status is status


def test_unverified_perfume_function_is_review(rules):
    a = formula("A", replace(ingredient("p"), perfume_role_evidence=None))
    b = formula("B", ingredient("q"))
    result = run(a, b, rules=rules)
    assert result.status is RuleStatus.REVIEW
    assert "VARYING_FUNCTION_OR_IDENTITY_UNVERIFIED" in codes(result)
    assert result.varying_perfume_totals[0].actual.exact is None
    assert result.varying_perfume_totals[0].membership_verified is False


def test_unknown_identity_is_not_a_pass(rules):
    a = formula("A", replace(ingredient("p"), identity_id=None))
    catalog = catalog_for(formula("A", ingredient("p")))
    result = run(a, rules=rules, catalog=catalog)
    assert result.status is RuleStatus.REVIEW
    assert result.matrix[-1].raw_identity_key is None


def test_exact_arithmetic_is_independent_of_decimal_context(rules):
    a = formula("A", ingredient("p", "5"), ingredient("tiny", "0.000000000000000000000000000001"))
    b = formula("B", ingredient("q", "5"))
    with localcontext() as context:
        context.prec = 2
        result = run(a, b, rules=rules)
    assert result.status is RuleStatus.FAIL
    assert result.varying_perfume_totals[0].actual.exact == Decimal(
        "5.000000000000000000000000000001"
    )


def test_duplicate_lines_of_same_identity_are_aggregated(rules):
    a = formula("A", ingredient("p", "3", line_id="p1"), ingredient("p", "3", line_id="p2"))
    b = formula("B", ingredient("q"))
    result = run(a, b, rules=rules)
    assert result.status is RuleStatus.FAIL
    assert result.varying_perfume_totals[0].line_ids == ("p1", "p2")
    assert result.varying_perfume_totals[0].actual.exact == Decimal(6)


def test_trace_bom_is_preserved_and_notifiability_reviewed(rules):
    a = formula("A", ingredient("p", "1"))
    b = formula("B", ingredient("p", "1"), ingredient("trace", "0.01", "OTHER"))
    before = b.raw_bom
    result = run(a, b, rules=rules)
    assert result.status is RuleStatus.REVIEW
    assert "TRACE_NOTIFIABILITY_REQUIRES_REVIEW" in codes(result)
    assert b.raw_bom == before
    assert any(row.line[2] == "trace" for row in result.matrix)


def test_zero_line_is_retained_but_does_not_make_component_common(rules):
    a = formula("A", ingredient("p", "0"))
    b = formula("B", ingredient("p", "6"))
    result = run(a, b, rules=rules)
    assert result.status is RuleStatus.FAIL
    assert ("SUBSTANCE", "p") in result.varying_raw_keys
    assert len(result.matrix) == 4


def test_uncertain_presence_cannot_prove_failure(rules):
    a = formula("A", replace(ingredient("p"), actual=ConcentrationInterval(Decimal(0), Decimal(1))))
    b = formula("B", ingredient("p", "6"))
    assert run(a, b, rules=rules).status is RuleStatus.REVIEW


def test_order_invariance(rules):
    forms = (
        formula("A", ingredient("p", "4")),
        formula("B", ingredient("q", "4")),
        formula("C", ingredient("p", "4"), ingredient("q", "4")),
    )
    catalog = catalog_for(*forms)
    expected = run(*forms, rules=rules, catalog=catalog)
    for ordering in itertools.permutations(forms):
        shuffled = tuple(
            replace(f, components=tuple(reversed(f.components)), raw_bom=tuple(reversed(f.raw_bom)))
            for f in ordering
        )
        assert (
            run(
                *shuffled,
                rules=rules,
                catalog=replace(
                    catalog,
                    identities=tuple(reversed(catalog.identities)),
                    lines=tuple(reversed(catalog.lines)),
                ),
            )
            == expected
        )


def test_mim_partial_ufi_prior_route(rules):
    mim = MiMIdentifiers("supplier", "product", "0000-0000-0000-0000", composition_known=False)
    a, b = formula("A", ingredient("blend", mim=mim)), formula("B", ingredient("q"))
    catalog = catalog_for(a, b)
    assert run(a, b, rules=rules, catalog=catalog).status is RuleStatus.REVIEW
    route = MiMRouteEvidence("UFI_PRIOR", proof(), proof(), (("IE", proof()),))
    catalog = change_line(catalog, ("A", "v1", "blend"), mim=route)
    assert run(a, b, rules=rules, catalog=catalog).status is RuleStatus.PASS
    for broken in (replace(route, prior_recipients=()), replace(route, ufi_validation=None)):
        assert (
            run(
                a, b, rules=rules, catalog=change_line(catalog, ("A", "v1", "blend"), mim=broken)
            ).status
            is RuleStatus.REVIEW
        )
    assert (
        run(replace(a, market_countries=("IE", "FR")), b, rules=rules, catalog=catalog).status
        is RuleStatus.REVIEW
    )


def test_mim_no_ufi_requires_sds_contact_and_other_known_components(rules):
    mim = MiMIdentifiers(
        "supplier", "product", sds_document_id="synthetic-sds", composition_known=False
    )
    a, b = formula("A", ingredient("blend", mim=mim)), formula("B", ingredient("q"))
    route = MiMRouteEvidence(
        "NO_UFI_SDS",
        proof(),
        sds_composition=proof(documents=("synthetic-sds",)),
        other_known_components=proof(),
        supplier_contact=proof(),
        supplier_name="Synthetic Supplier",
        supplier_email="example@example.invalid",
        supplier_phone="synthetic-phone",
    )
    catalog = change_line(catalog_for(a, b), ("A", "v1", "blend"), mim=route)
    assert run(a, b, rules=rules, catalog=catalog).status is RuleStatus.PASS
    for field in (
        "sds_composition",
        "other_known_components",
        "supplier_contact",
        "supplier_phone",
    ):
        broken = change_line(catalog, ("A", "v1", "blend"), mim=replace(route, **{field: None}))
        assert run(a, b, rules=rules, catalog=broken).status is RuleStatus.REVIEW


def test_unknown_mim_function_and_unidentified_blend_review(rules):
    mim = MiMIdentifiers("supplier", "product", "0000-0000-0000-0000", composition_known=False)
    a = formula("A", ingredient("blend", role=None, mim=mim))
    route = MiMRouteEvidence("UFI_PRIOR", proof(), proof(), (("IE", proof()),))
    catalog = change_line(catalog_for(a), ("A", "v1", "blend"), mim=route)
    assert "MIM_FUNCTION_UNKNOWN" in codes(run(a, rules=rules, catalog=catalog))
    unknown = replace(
        a, components=(a.components[0], replace(a.components[1], mim=MiMIdentifiers()))
    )
    assert run(unknown, rules=rules, catalog=catalog).status is RuleStatus.REVIEW


def test_gci_colourant_differences_use_only_scoped_approved_representation(rules):
    a = declared(formula("A", ingredient("red", "18", "COLOURANT")), "red")
    b = declared(formula("B", ingredient("blue", "21", "COLOURANT")), "blue")
    c = catalog_for(a, b)
    assert run(a, b, rules=rules, catalog=c).status is not RuleStatus.PASS
    c = representation(c, rules, (a, b), ("red", "blue"))
    result = run(a, b, rules=rules, catalog=c)
    assert result.status is RuleStatus.PASS
    assert ("GCI", "approved-representation") in result.common_notified_keys
    assert ("SUBSTANCE", "red") in result.varying_raw_keys
    bad = replace(c, representations=(replace(c.representations[0], ruleset_sha256="wrong"),))
    assert run(a, b, rules=rules, catalog=bad).status is not RuleStatus.PASS


@pytest.mark.parametrize("amount,status", [("25", RuleStatus.PASS), ("25.0001", RuleStatus.FAIL)])
def test_colourant_gci_cap(rules, amount, status):
    f = declared(formula("A", ingredient("red", amount, "COLOURANT")), "red")
    c = representation(catalog_for(f), rules, (f,), ("red",))
    assert run(f, rules=rules, catalog=c).status is status


def test_perfume_gci_cap_is_separate_even_when_all_raw_perfumes_are_common(rules):
    f = declared(formula("A", ingredient("shared", "6")), "shared")
    c = representation(catalog_for(f), rules, (f,), ("shared",), function="PERFUME")
    result = run(f, rules=rules, catalog=c)
    assert result.status is RuleStatus.FAIL
    assert result.varying_perfume_totals[0].actual.exact == Decimal(0)
    assert RuleStatus.FAIL in verdicts(result, "REG-GCI")
    assert verdicts(result, "REG-PERFUME-CAP") == [RuleStatus.PASS]


def test_gci_cannot_hide_identity_varying_perfume_totals(rules):
    a = declared(formula("A", ingredient("p", "4")), "p")
    b = declared(formula("B", ingredient("q", "4")), "q")
    catalog = representation(catalog_for(a, b), rules, (a, b), ("p", "q"), function="PERFUME")
    result = run(a, b, rules=rules, catalog=catalog)
    assert [t.actual.exact for t in result.varying_perfume_totals] == [Decimal(4), Decimal(4)]


def test_gci_health_and_exclusive_function_failures(rules):
    h = CLPClassification(
        "Skin Sens.",
        "1",
        "H317",
        status=EvidenceStatus.VERIFIED,
        source_document_ids=("synthetic-source",),
    )
    f = declared(formula("A", ingredient("p", hazards=(h,))), "p")
    c = representation(catalog_for(f), rules, (f,), ("p",), function="PERFUME")
    assert run(f, rules=rules, catalog=c).status is RuleStatus.FAIL
    f = declared(formula("A", ingredient("p")), "p")
    c = representation(catalog_for(f), rules, (f,), ("p",), function="PERFUME")
    c = change_line(c, ("A", "v1", "p"), exclusive_function=False)
    assert run(f, rules=rules, catalog=c).status is RuleStatus.FAIL
    c = change_line(c, ("A", "v1", "p"), exclusive_function=None)
    assert run(f, rules=rules, catalog=c).status is RuleStatus.REVIEW


def test_claimed_icg_is_review_until_all_prior_evidence_is_supplied(rules):
    a = declared(formula("A", ingredient("x", role="SOLVENT")), "x")
    b = declared(formula("B", ingredient("y", role="SOLVENT")), "y")
    c = representation(catalog_for(a, b), rules, (a, b), ("x", "y"), kind="ICG", function=None)
    result = run(a, b, rules=rules, catalog=c)
    assert result.status is RuleStatus.REVIEW
    assert "ICG_PREEXISTING_VALIDATION_MISSING" in codes(result)
    criteria = tuple(
        (name, proof(name))
        for name in (
            "component_identification",
            "concentration_data",
            "identical_classification",
            "combination_invariance",
            "same_function",
            "same_toxicology",
        )
    )
    c = replace(
        c,
        representations=(
            replace(
                c.representations[0], pre_existing=True, icg_pathway="GENERAL", criteria=criteria
            ),
        ),
    )
    assert run(a, b, rules=rules, catalog=c).status is RuleStatus.PASS
    c = replace(c, representations=(replace(c.representations[0], criteria=criteria[:-1]),))
    assert run(a, b, rules=rules, catalog=c).status is RuleStatus.REVIEW


def test_missing_gci_approval_is_review_not_assumed_nonperfume_failure(rules):
    a = declared(formula("A", ingredient("red", "18", "COLOURANT")), "red")
    b = declared(formula("B", ingredient("blue", "21", "COLOURANT")), "blue")
    assert run(a, b, rules=rules).status is RuleStatus.REVIEW


def test_common_validated_icg_does_not_invoke_perfume_exception(rules):
    a = declared(formula("A", ingredient("x", "6")), "x")
    b = declared(formula("B", ingredient("y", "6")), "y")
    criteria = tuple(
        (name, proof(name))
        for name in (
            "component_identification",
            "concentration_data",
            "identical_classification",
            "combination_invariance",
            "same_function",
            "same_toxicology",
        )
    )
    catalog = representation(
        catalog_for(a, b),
        rules,
        (a, b),
        ("x", "y"),
        kind="ICG",
        function=None,
        pre_existing=True,
        icg_pathway="GENERAL",
        criteria=criteria,
    )
    result = run(a, b, rules=rules, catalog=catalog)
    assert result.status is RuleStatus.PASS
    assert result.varying_raw_keys == (("SUBSTANCE", "x"), ("SUBSTANCE", "y"))
    assert [t.actual.exact for t in result.varying_perfume_totals] == [Decimal(0), Decimal(0)]


def test_gci_cap_cannot_be_evaded_by_splitting_declarations(rules):
    f = formula("A", ingredient("p", "3"), ingredient("q", "3"))
    f = replace(
        f,
        notified_components=(
            NotifiedComponent("base", "base", ConcentrationValue(Decimal(94)), ("base",)),
            NotifiedComponent("p", "gci-p", ConcentrationValue(Decimal(3)), ("p",)),
            NotifiedComponent("q", "gci-q", ConcentrationValue(Decimal(3)), ("q",)),
        ),
    )
    catalog = catalog_for(f)
    p = representation(catalog, rules, (f,), ("p",), name="gci-p", function="PERFUME")
    q = representation(catalog, rules, (f,), ("q",), name="gci-q", function="PERFUME")
    result = run(
        f,
        rules=rules,
        catalog=replace(catalog, representations=p.representations + q.representations),
    )
    assert result.status is RuleStatus.FAIL
    aggregate = [
        r for r in result.rule_results if dict(r.values)["code"] == "GCI_PERFUME_AGGREGATE_CAP"
    ]
    assert len(aggregate) == 1 and dict(aggregate[0].values)["upper"] == "6"


def test_raw_common_but_different_notified_representation_requires_review(rules):
    a = declared(formula("A", ingredient("red", "2", "COLOURANT")), "red")
    b = formula("B", ingredient("red", "2", "COLOURANT"))
    catalog = representation(catalog_for(a, b), rules, (a, b), ("red",))
    result = run(a, b, rules=rules, catalog=catalog)
    assert result.status is RuleStatus.REVIEW
    assert "COMMON_RAW_DECLARATION_IDENTITY_MISMATCH" in codes(result)


def test_mim_ufi_change_cannot_be_hidden_by_same_supplier_product_id(rules):
    mim = MiMIdentifiers("supplier", "product", "0000-0000-0000-0000", composition_known=False)
    a = formula("A", ingredient("blend", mim=mim))
    b = formula("B", ingredient("blend", mim=replace(mim, ufi="1111-1111-1111-1111")))
    route = MiMRouteEvidence("UFI_PRIOR", proof(), proof(), (("IE", proof()),))
    catalog = catalog_for(a, b)
    for f in (a, b):
        catalog = change_line(catalog, (f.formulation_id, "v1", "blend"), mim=route)
    result = run(a, b, rules=rules, catalog=catalog)
    assert result.status is RuleStatus.REVIEW
    assert "MIM_UFI_IDENTITY_CONFLICT" in codes(result)


def test_full_mim_requires_upstream_expansion(rules):
    mim = MiMIdentifiers("supplier", "product", composition_known=True)
    f = formula("A", ingredient("blend", mim=mim))
    catalog = change_line(
        catalog_for(f), ("A", "v1", "blend"), mim=MiMRouteEvidence("FULL_COMPOSITION", proof())
    )
    result = run(f, rules=rules, catalog=catalog)
    assert result.status is RuleStatus.REVIEW
    assert "FULL_MIM_REQUIRES_UPSTREAM_CONSTITUENT_EXPANSION" in codes(result)


def test_ufi_without_prior_submission_can_use_complete_sds_route(rules):
    mim = MiMIdentifiers("supplier", "product", "0000-0000-0000-0000", "synthetic-sds", False)
    f = formula("A", ingredient("blend", mim=mim))
    route = MiMRouteEvidence(
        "UFI_SDS",
        proof(),
        proof(),
        sds_composition=proof(documents=("synthetic-sds",)),
        other_known_components=proof(),
        supplier_contact=proof(),
        supplier_name="Synthetic",
        supplier_email="synthetic@example.invalid",
        supplier_phone="synthetic-phone",
    )
    catalog = change_line(catalog_for(f), ("A", "v1", "blend"), mim=route)
    assert run(f, rules=rules, catalog=catalog).status is RuleStatus.PASS


def test_approval_evidence_and_raw_sources_remain_in_matrix(rules):
    f = declared(formula("A", ingredient("red", "2", "COLOURANT")), "red")
    catalog = representation(catalog_for(f), rules, (f,), ("red",))
    row = next(r for r in run(f, rules=rules, catalog=catalog).matrix if r.line[2] == "red")
    assert "scoped-prior-approval" in row.evidence_ids
    assert "registry-red" in row.evidence_ids
    assert row.source_line_ids == ("red",)
    assert "synthetic-source" in row.source_document_ids


def test_rule_projection_cannot_silently_change_with_same_hash(rules):
    with pytest.raises(ValueError, match="projection"):
        replace(rules, varying_perfume_cap=Decimal(6))
    with pytest.raises(ValueError, match="source bytes"):
        replace(rules, source_json=rules.source_json + b" ")
    with pytest.raises(ValueError, match="projection"):
        replace(rules, version=replace(rules.version, status="FAKE_APPROVAL"))


def test_icg_alternative_max_five_and_missing_combination_evidence(rules):
    f = declared(formula("A", ingredient("x", role="SOLVENT")), "x")
    catalog = representation(
        catalog_for(f),
        rules,
        (f,),
        ("x", "a", "b", "c", "d", "e"),
        kind="ICG",
        function=None,
        pre_existing=True,
        icg_pathway="ALTERNATIVE",
    )
    catalog = replace(
        catalog,
        identities=(
            *catalog.identities,
            *(
                IdentityRecord(name, ComponentKind.SUBSTANCE, "CLP_ART18", name, proof())
                for name in ("a", "b", "c", "d", "e")
            ),
        ),
    )
    assert "ICG_ALTERNATIVE_MORE_THAN_FIVE" in codes(run(f, rules=rules, catalog=catalog))


def test_duplicate_declaration_coverage_is_review(rules):
    f = declared(formula("A", ingredient("p")), "p", name="p")
    f = replace(f, notified_components=(*f.notified_components, f.notified_components[-1]))
    assert "DECLARATION_PARTITION_INVALID" in codes(run(f, rules=rules))


def test_duplicate_component_lines_cannot_manufacture_cap_failure(rules):
    a = formula("A", ingredient("p", "3"), ingredient("p", "3"))
    b = formula("B", ingredient("q"))
    assert run(a, b, rules=rules).status is RuleStatus.REVIEW


def test_supplied_repository_draft_never_yields_component_pass():
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "rulesets"
        / "annex_viii_2026_07_01.research-draft.json"
    )
    rules = ComponentRules.from_json(path.read_bytes(), proof())
    assert run(formula("A", ingredient("p")), rules=rules).status is RuleStatus.REVIEW


def test_omitted_perfume_still_counts_actual_and_keeps_classification_matrix(rules):
    h = CLPClassification(
        "Skin Sens.",
        "1A",
        "H317",
        status=EvidenceStatus.VERIFIED,
        source_document_ids=("synthetic-source",),
    )
    a = declared(formula("A", ingredient("p", "5.0001", hazards=(h,))), "p", name="p", omitted=True)
    b = formula("B", ingredient("q"))
    result = run(a, b, rules=rules)
    assert result.status is RuleStatus.FAIL
    assert result.disclosure_status is RuleStatus.PASS
    row = next(row for row in result.matrix if row.line == ("A", "v1", "p"))
    assert row.declared_concentration_omitted and row.classifications == (h,)
    assert row.actual.exact == Decimal("5.0001")
    a = declared(formula("A", ingredient("p", None, hazards=(h,))), "p", name="p", omitted=True)
    assert run(a, b, rules=rules).status is RuleStatus.REVIEW


def test_disclosure_failure_is_separate_from_component_comparison(rules):
    h = CLPClassification(
        "Eye Dam.",
        "1",
        "H318",
        status=EvidenceStatus.VERIFIED,
        source_document_ids=("synthetic-source",),
    )
    a = declared(formula("A", ingredient("p", hazards=(h,))), "p", name="p", omitted=True)
    b = formula("B", ingredient("q"))
    result = run(a, b, rules=rules)
    assert result.status is RuleStatus.PASS
    assert result.disclosure_status is RuleStatus.FAIL


def test_rule_approval_cannot_be_inferred_from_name_or_reviewed_inputs(rules):
    raw = rules_json().replace(b'"APPROVED"', b'"RESEARCH_DRAFT_NOT_EXECUTABLE_NOT_LEGAL_APPROVAL"')
    draft = ComponentRules.from_json(raw, proof())
    f = formula("A", ingredient("p"))
    result = run(f, rules=draft)
    assert result.status is RuleStatus.REVIEW
    assert result.ruleset.sha256 == hashlib.sha256(raw).hexdigest()
    assert "RULESET_NOT_APPROVED" in codes(result)
    assert run(f, rules=replace(rules, approval=None)).status is RuleStatus.REVIEW


def test_rule_hash_and_float_rejection():
    raw = rules_json()
    assert (
        ComponentRules.from_json(raw).version.sha256
        != ComponentRules.from_json(raw + b"\n").version.sha256
    )
    with pytest.raises(TypeError):
        ComponentRules.from_json(raw.replace(b'"5"', b"5.0"))
    with pytest.raises(ValueError):
        ComponentRules.from_json(raw[:-1] + b', "status": "APPROVED"}')


def test_empty_duplicate_revisions_and_basis_review(rules):
    f = formula("A", ingredient("p"))
    assert analyse_components((), EvidenceCatalog(), rules).status is RuleStatus.REVIEW
    assert run(f, f, rules=rules).status is RuleStatus.REVIEW
    other = replace(formula("B", ingredient("q")), composition_basis=PercentageBasis.VOLUME_PERCENT)
    assert run(f, other, rules=rules).status is RuleStatus.REVIEW


def test_unverified_classification_and_dangling_raw_line_review(rules):
    f = formula("A", ingredient("p"))
    c = change_line(catalog_for(f), ("A", "v1", "p"), classification_complete=None)
    assert run(f, rules=rules, catalog=c).status is RuleStatus.REVIEW
    f = replace(f, raw_bom=(*f.raw_bom, RawBOMLine("unmapped", "synthetic-source")))
    assert "RAW_BOM_LINES_UNACCOUNTED" in codes(run(f, rules=rules))


def test_approved_component_kind_is_not_itself_an_approval(rules):
    f = formula("A", replace(ingredient("claimed-icg"), kind=ComponentKind.APPROVED_ICG))
    result = run(f, rules=rules)
    assert result.status is RuleStatus.REVIEW
    assert "RAW_REPRESENTATION_WITHOUT_MEMBERS" in codes(result)


def test_ambiguous_alias_is_not_followed():
    c = ingredient("input")
    f = formula("A", c)
    catalog = replace(catalog_for(f), aliases=(IdentityAlias("input", "base", c.kind, proof()),))
    assert resolve_identity(c, catalog)[0] is None
