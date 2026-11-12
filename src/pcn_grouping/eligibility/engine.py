"""Deterministic whole-group Annex VIII evaluator; legal approval remains external.

All regulatory evidence and classification completeness must come from reviewed,
versioned inputs. This module never creates chemical or legal attestations.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from importlib import import_module
from typing import Any, cast

from pcn_grouping.components import (
    ComponentAnalysis, ComponentRow, ComponentRules, EvidenceCatalog,
    PerfumeTotal, analyse_components,
)
from pcn_grouping.components.rules import exact_sum, sum_bounds, verified
from pcn_grouping.models import (
    CLPClassification, Evidence, EvidenceStatus, Formulation, GroupDecision,
    GroupStatus, NotificationMode, RuleResult, RuleStatus, canonical_sha256,
)
from pcn_grouping.validation import validate_formulation, validate_portfolio

Revision = tuple[str, str]
IdentityKey = tuple[str, str]
RangeSolver = Callable[[Sequence[Any], str, Mapping[str, Any]], Any]


@dataclass(frozen=True, slots=True)
class ReviewedClassification:
    revision: Revision
    complete: Evidence  # reviewed completeness of the entire health/physical signature


@dataclass(frozen=True, slots=True)
class ApplicabilityEvidence:
    revision: Revision
    mandatory_pcn: bool | None
    evidence: Evidence | None


@dataclass(frozen=True, slots=True)
class EligibilityContext:
    """Version-pinned inputs: never assume approval, identity or classification."""

    component_rules: ComponentRules
    evidence_catalog: EvidenceCatalog = field(default_factory=EvidenceCatalog)
    classifications: tuple[ReviewedClassification, ...] = ()
    applicability: tuple[ApplicabilityEvidence, ...] = ()
    evaluation_date: str | None = None  # caller supplied; no wall-clock dependence


@dataclass(frozen=True, slots=True)
class CommonRange:
    notified_identity: IdentityKey
    component_class: str | None
    member_bounds: tuple[tuple[str, str | None, str | None], ...]
    declared_lower: str | None
    declared_upper: str | None
    exact: bool | None
    status: RuleStatus
    reason_codes: tuple[str, ...]
    zone_evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EligibilityDecision(GroupDecision):
    """Extends the canonical decision without changing B-owned models.

    status is chemical grouping eligibility, NOT dossier readiness.
    Out-of-scope applicability never silently yields ELIGIBLE.
    """

    dossier_status: RuleStatus = RuleStatus.REVIEW
    applicability_status: str = "REVIEW"  # IN_SCOPE | OUT_OF_SCOPE | REVIEW
    component_matrix: tuple[ComponentRow, ...] = ()
    common_raw_keys: tuple[IdentityKey, ...] = ()
    varying_raw_keys: tuple[IdentityKey, ...] = ()
    common_notified_keys: tuple[IdentityKey, ...] = ()
    varying_notified_keys: tuple[IdentityKey, ...] = ()
    common_ranges: tuple[CommonRange, ...] = ()
    varying_perfume_totals: tuple[PerfumeTotal, ...] = ()
    perfume_classification_matrix: tuple[
        tuple[str, str, tuple[tuple[str, str, str, str, str], ...]], ...
    ] = ()
    missing_data_flags: tuple[str, ...] = ()


_SECTIONS: dict[str, tuple[str, ...]] = {
    "E-INPUT": ("B.3.1; B.3.3",),
    "E-RULESET": ("Annex VIII; version governance",),
    "REG-SCOPE": ("Article 45; A.2.2; A.2.2a; A.3.1",),
    "REG-SUBMITTER": ("A.2.1; B.1.2; ECHA guidance 5.4",),
    "REG-MODE": ("A.2.3; B.3.1; B.3.6; B.3.7",),
    "REG-CLASS": ("A.4.1; B.2.1",),
    "REG-COMMON-RANGE": ("A.4.2; B.3.4.1; B.3.4.2",),
    "REG-MAJOR-BAND": ("B.3.4.1; Table 1",),
    "REG-OTHER-BAND": ("B.3.4.2; Table 2",),
    "REG-DOSSIER": ("A.4.4; B.1; B.2; B.3",),
}


def _rule(rule_id: str, status: RuleStatus, code: str, *,
          evidence: tuple[str, ...] = (),
          values: tuple[tuple[str, str], ...] = ()) -> RuleResult:
    return RuleResult(
        rule_id, status, code.replace("_", " ").lower(),
        tuple(sorted(set(evidence))), _SECTIONS[rule_id],
        tuple(sorted((("code", code), *values))),
    )


def _aggregate(statuses: Sequence[RuleStatus]) -> RuleStatus:
    if RuleStatus.FAIL in statuses:
        return RuleStatus.FAIL
    if RuleStatus.REVIEW in statuses or not statuses:
        return RuleStatus.REVIEW
    return RuleStatus.PASS


def _group_status(statuses: Sequence[RuleStatus]) -> GroupStatus:
    return {
        RuleStatus.PASS: GroupStatus.ELIGIBLE,
        RuleStatus.FAIL: GroupStatus.INELIGIBLE,
        RuleStatus.REVIEW: GroupStatus.REVIEW_REQUIRED,
    }[_aggregate(statuses)]


def _signature(classes: Sequence[CLPClassification]
               ) -> tuple[tuple[str, str, str, str, str], ...]:
    return tuple(sorted(
        (c.hazard_class, c.category, c.h_code, c.route or "", c.qualifier or "")
        for c in classes
    ))


def _classifications(formulations: Sequence[Formulation],
                     attestations: Sequence[ReviewedClassification]) -> RuleResult:
    proofs: dict[Revision, list[Evidence]] = {}
    for item in attestations:
        proofs.setdefault(item.revision, []).append(item.complete)
    complete = all(
        len(proofs.get((f.formulation_id, f.revision), [])) == 1
        and verified(proofs[(f.formulation_id, f.revision)][0])
        and all(c.status is EvidenceStatus.VERIFIED and c.source_document_ids
                and c.hazard_class and c.category and c.h_code
                for c in f.approved_health_physical_classification)
        for f in formulations
    )
    ids = tuple(a.complete.evidence_id for a in attestations)
    if not complete:
        return _rule("REG-CLASS", RuleStatus.REVIEW,
                     "CLASSIFICATION_COMPLETENESS_UNVERIFIED", evidence=ids)
    if len({_signature(f.approved_health_physical_classification)
            for f in formulations}) != 1:
        return _rule("REG-CLASS", RuleStatus.FAIL,
                     "HEALTH_PHYSICAL_SIGNATURES_DIFFER", evidence=ids)
    return _rule("REG-CLASS", RuleStatus.PASS,
                 "VERIFIED_IDENTICAL_HEALTH_PHYSICAL_SIGNATURES", evidence=ids)


def _applicability(formulations: Sequence[Formulation],
                   attestations: Sequence[ApplicabilityEvidence]
                   ) -> tuple[str, RuleResult]:
    by_rev: dict[Revision, list[ApplicabilityEvidence]] = {}
    for item in attestations:
        by_rev.setdefault(item.revision, []).append(item)
    items = [by_rev.get((f.formulation_id, f.revision), []) for f in formulations]
    if not items or any(len(rows) != 1 or rows[0].mandatory_pcn is None
                        or not verified(rows[0].evidence) for rows in items):
        return "REVIEW", _rule("REG-SCOPE", RuleStatus.REVIEW,
                               "APPLICABILITY_EVIDENCE_MISSING")
    mandatory = {rows[0].mandatory_pcn for rows in items}
    if mandatory == {True}:
        return "IN_SCOPE", _rule("REG-SCOPE", RuleStatus.PASS, "MANDATORY_PCN_EVIDENCED")
    if mandatory == {False}:
        return "OUT_OF_SCOPE", _rule("REG-SCOPE", RuleStatus.REVIEW,
                                     "MANDATORY_PCN_NOT_APPLICABLE")
    return "REVIEW", _rule("REG-SCOPE", RuleStatus.REVIEW,
                           "MIXED_PCN_APPLICABILITY")


def _mode(formulations: Sequence[Formulation]) -> RuleResult:
    modes = {f.notification_mode for f in formulations}
    if modes == {NotificationMode.STANDARD_FULL}:
        return _rule("REG-MODE", RuleStatus.PASS, "STANDARD_FULL_COMPOSITION")
    if len(modes) > 1 and NotificationMode.UNKNOWN not in modes:
        return _rule("REG-MODE", RuleStatus.FAIL, "INCOMPATIBLE_NOTIFICATION_MODES")
    return _rule("REG-MODE", RuleStatus.REVIEW, "UNSUPPORTED_OR_UNKNOWN_MODE")


def _submitter(formulations: Sequence[Formulation]) -> RuleResult:
    submitters = {f.legal_submitter_id for f in formulations if f.legal_submitter_id}
    if len(submitters) > 1:
        return _rule("REG-SUBMITTER", RuleStatus.FAIL,
                     "DIFFERENT_LEGAL_DUTY_HOLDERS")
    if not submitters or any(not f.legal_submitter_id for f in formulations):
        return _rule("REG-SUBMITTER", RuleStatus.REVIEW,
                     "LEGAL_DUTY_HOLDER_MISSING")
    return _rule("REG-SUBMITTER", RuleStatus.PASS, "SAME_LEGAL_DUTY_HOLDER",
                 values=(("legal_submitter_id", next(iter(submitters))),))


def _input_checks(formulations: Sequence[Formulation]) -> list[RuleResult]:
    output: list[RuleResult] = []
    if len(formulations) < 2:
        output.append(_rule("E-INPUT", RuleStatus.REVIEW,
                            "AT_LEAST_TWO_REVISIONS_REQUIRED"))
    for issue in validate_portfolio(formulations):
        output.append(_rule("E-INPUT", RuleStatus.REVIEW, issue.code,
                            values=(("path", issue.path),)))
    for f in formulations:
        lower_values: list[Decimal] = []
        upper_values: list[Decimal] = []
        for component in f.components:
            actual = component.actual
            if hasattr(actual, "value") and actual.value is not None:
                lower_values.append(actual.value)
                upper_values.append(actual.value)
            elif (hasattr(actual, "lower") and hasattr(actual, "upper")
                  and actual.lower is not None and actual.upper is not None):
                lower_values.append(actual.lower)
                upper_values.append(actual.upper)
        if len(lower_values) == len(f.components) and f.components:
            low = exact_sum(tuple(lower_values))
            high = exact_sum(tuple(upper_values))
            if low > Decimal("100.01") or high < Decimal("99.99"):
                output.append(_rule("E-INPUT", RuleStatus.REVIEW,
                                    "EXACT_TOTAL_NOT_100",
                                    values=(("revision", f.revision_id),)))
        for issue in validate_formulation(f):
            output.append(_rule("E-INPUT", RuleStatus.REVIEW, issue.code,
                                values=(("revision", f.revision_id),
                                        ("path", issue.path))))
    bases = {f.composition_basis for f in formulations}
    if len(bases) != 1 or None in bases:
        output.append(_rule("E-INPUT", RuleStatus.REVIEW,
                            "PERCENTAGE_BASIS_MISMATCH"))
    if not output:
        output.append(_rule("E-INPUT", RuleStatus.PASS, "SCHEMA_VALID"))
    return output


def _load_solver() -> RangeSolver | None:
    try:
        module = import_module("pcn_grouping.concentration")
    except ModuleNotFoundError as exc:
        if exc.name != "pcn_grouping.concentration":
            raise
        return None
    return cast(RangeSolver, getattr(module, "find_common_declaration"))


def _ranges(analysis: ComponentAnalysis, formulations: Sequence[Formulation],
            rules: Mapping[str, Any], solver: RangeSolver | None
            ) -> tuple[list[RuleResult], tuple[CommonRange, ...]]:
    results: list[RuleResult] = []
    ranges: list[CommonRange] = []
    major_categories = rules.get("major_concern_component_hazard_categories")
    bands = rules.get("maximum_concentration_range_width_percentage_points")
    complete_book = (
        isinstance(major_categories, (list, tuple)) and bool(major_categories)
        and isinstance(bands, Mapping)
        and all(key in bands for key in ("major_concern", "other"))
    )
    major = set(major_categories) if isinstance(major_categories, (list, tuple)) else set()
    by_rev = {(f.formulation_id, f.revision): f for f in formulations}
    for key in analysis.common_notified_keys:
        per_member: list[tuple[str, str | None, str | None]] = []
        actuals: list[Any] = []
        classes: list[CLPClassification] = []
        missing = False
        refs: set[str] = set()
        for revision in sorted(by_rev):
            rows = [r for r in analysis.matrix if r.line[:2] == revision
                    and r.notified_identity_key == key and r.actual.upper != 0]
            if not rows:
                missing = True
                per_member.append((f"{revision[0]}@{revision[1]}", None, None))
                continue
            bounds = sum_bounds(tuple(row.actual for row in rows))
            per_member.append((f"{revision[0]}@{revision[1]}",
                               str(bounds.lower) if bounds.lower is not None else None,
                               str(bounds.upper) if bounds.upper is not None else None))
            actuals.append(bounds)
            for row in rows:
                refs.update(row.evidence_ids)
                classes.extend(row.classifications)
                if not row.identity_verified or bounds.lower is None or bounds.upper is None:
                    missing = True
        if not classes or any(c.status is not EvidenceStatus.VERIFIED
                              or not c.source_document_ids for c in classes):
            if not classes and not missing:
                component_class = "other"  # D separately attests class completeness
            else:
                component_class = None
                missing = True
        else:
            component_class = (
                "major_concern" if any(
                    f"{c.hazard_class} {c.category}" in major for c in classes
                ) else "other"
            )
        declaration = None
        zone_evidence: tuple[str, ...] = ()
        if not complete_book or solver is None or missing or component_class is None:
            status = RuleStatus.REVIEW
            code = (
                "RANGE_RULEBOOK_INCOMPLETE" if not complete_book else
                "RANGE_SOLVER_UNAVAILABLE" if solver is None else
                "RANGE_INPUT_EVIDENCE_MISSING"
            )
        else:
            declaration = solver(actuals, component_class, rules)
            try:
                status = RuleStatus(declaration.status)
            except (ValueError, AttributeError):
                status = RuleStatus.REVIEW
            code = (declaration.reason_codes[0] if declaration.reason_codes
                    else "RANGE_SOLVER_RESULT_MISSING")
            zone_evidence = tuple(declaration.evidence)
        declared = declaration.declaration if declaration is not None else None
        values_list = [("notified_identity", f"{key[0]}:{key[1]}"),
                       ("component_class", str(component_class))]
        values_list.extend((f"member_{i}", f"{member}:{lo}..{hi}")
                           for i, (member, lo, hi) in enumerate(per_member))
        if declared is not None:
            values_list.append(("declared_range", f"{declared.lower}..{declared.upper}"))
        values = tuple(values_list)
        results.append(_rule("REG-COMMON-RANGE", status, code,
                             evidence=tuple(refs), values=values))
        if component_class is not None:
            band_id = (
                "REG-MAJOR-BAND" if component_class == "major_concern"
                else "REG-OTHER-BAND"
            )
            results.append(_rule(band_id, status, code,
                                 evidence=tuple(refs), values=values))
        ranges.append(CommonRange(
            key, component_class, tuple(per_member),
            str(declared.lower) if declared is not None else None,
            str(declared.upper) if declared is not None else None,
            declared.exact if declared is not None else None,
            status, (code,), zone_evidence,
        ))
    if not analysis.common_notified_keys:
        results.append(_rule("REG-COMMON-RANGE", RuleStatus.PASS, "NO_SHARED_IDENTITIES"))
    return results, tuple(ranges)


def _dossier(formulations: Sequence[Formulation],
             analysis: ComponentAnalysis) -> RuleResult:
    gaps: list[str] = []
    for f in formulations:
        for name in ("product_names", "market_countries", "use_types", "eupcs_codes",
                     "ufis", "physical_state", "colour", "ph", "sds_section_11"):
            if not getattr(f, name):
                gaps.append(f"{f.revision_id}:{name}")
        if f.notification_mode is NotificationMode.STANDARD_FULL and not f.packaging:
            gaps.append(f"{f.revision_id}:packaging")
    if analysis.disclosure_status is not RuleStatus.PASS:
        gaps.append("group_perfume_disclosure")
    if gaps:
        return _rule("REG-DOSSIER", RuleStatus.REVIEW,
                     "DOSSIER_FIELDS_OR_DISCLOSURES_MISSING",
                     values=tuple((f"gap_{i}", gap) for i, gap in enumerate(sorted(gaps))))
    # No assertion of format/Member State/ECHA validation.
    return _rule("REG-DOSSIER", RuleStatus.PASS,
                 "REPORTED_FIELDS_PRESENT_FORMAT_UNVALIDATED")


def evaluate_group(formulation_revisions: Sequence[Formulation],
                   ruleset: EligibilityContext) -> EligibilityDecision:
    """Authoritative deterministic chemical grouping API; not a legal approval.

    A reviewed rules file, component evidence and verified finished CLP signatures
    are necessary to return ELIGIBLE. All conclusive FAILs outrank REVIEW.
    """
    formulations = tuple(sorted(
        formulation_revisions, key=lambda f: (f.formulation_id, f.revision)
    ))
    component_rules = ruleset.component_rules
    version = component_rules.version
    input_hash = canonical_sha256({
        "formulations": formulations,
        "component_catalog": ruleset.evidence_catalog,
        "classification_attestations": ruleset.classifications,
        "applicability_attestations": ruleset.applicability,
        "evaluation_date": ruleset.evaluation_date,
        "ruleset_sha256": version.sha256,
        "ruleset_approval": component_rules.approval,
    })
    results = _input_checks(formulations)
    if not component_rules.approved:
        results.append(_rule("E-RULESET", RuleStatus.REVIEW,
                             "RULESET_NOT_APPROVED"))
    elif not ruleset.evaluation_date:
        results.append(_rule("E-RULESET", RuleStatus.REVIEW,
                             "EVALUATION_DATE_MISSING"))
    else:
        try:
            effective = date.fromisoformat(version.effective_date)
            evaluated = date.fromisoformat(ruleset.evaluation_date)
        except ValueError:
            results.append(_rule("E-RULESET", RuleStatus.REVIEW,
                                 "RULESET_DATE_INVALID"))
        else:
            results.append(_rule(
                "E-RULESET",
                RuleStatus.REVIEW if effective > evaluated else RuleStatus.PASS,
                "RULESET_NOT_YET_EFFECTIVE" if effective > evaluated
                else "RULESET_APPROVED_AND_EFFECTIVE",
            ))
    results.extend((_submitter(formulations), _mode(formulations),
                    _classifications(formulations, ruleset.classifications)))
    applicability_status, applicable = _applicability(
        formulations, ruleset.applicability
    )
    analysis = analyse_components(formulations, ruleset.evidence_catalog, component_rules)
    results.extend(analysis.rule_results)
    rules_source = json.loads(component_rules.source_json)
    range_results, common_ranges = _ranges(
        analysis, formulations, rules_source, _load_solver()
    )
    results.extend(range_results)
    dossier = _dossier(formulations, analysis)
    results.extend((applicable, dossier))
    # Metadata and applicability do not establish chemistry eligibility. An
    # unproven or negative applicability can never be mislabeled ELIGIBLE.
    chemical = [
        r.status for r in results
        if r.rule_id not in {"REG-SCOPE", "REG-DOSSIER"}
        and ("scope", "disclosure") not in r.values
    ]
    if applicability_status != "IN_SCOPE":
        chemical.append(RuleStatus.REVIEW)
    perfume_matrix = tuple(sorted((
        (f"{row.line[0]}@{row.line[1]}",
         f"{row.raw_identity_key[0]}:{row.raw_identity_key[1]}"
         if row.raw_identity_key else "UNKNOWN",
         _signature(row.classifications))
        for row in analysis.matrix
        if row.raw_identity_key in analysis.varying_raw_keys
        and row.perfume_verified and row.actual.upper != 0
    )))
    missing = tuple(sorted({
        f"{r.rule_id}:{dict(r.values).get('code', r.explanation)}"
        for r in results if r.status is RuleStatus.REVIEW
    }))
    return EligibilityDecision(
        status=_group_status(chemical),
        formulation_revision_ids=tuple(f.revision_id for f in formulations),
        ruleset=version,
        canonical_input_hash=input_hash,
        rule_results=tuple(sorted(
            results, key=lambda r: (r.rule_id, r.values, r.status.value, r.evidence_ids)
        )),
        dossier_status=dossier.status,
        applicability_status=applicability_status,
        component_matrix=analysis.matrix,
        common_raw_keys=analysis.common_raw_keys,
        varying_raw_keys=analysis.varying_raw_keys,
        common_notified_keys=analysis.common_notified_keys,
        varying_notified_keys=analysis.varying_notified_keys,
        common_ranges=common_ranges,
        varying_perfume_totals=analysis.varying_perfume_totals,
        perfume_classification_matrix=perfume_matrix,
        missing_data_flags=missing,
    )
