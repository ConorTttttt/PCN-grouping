"""Deterministic component evidence checks; not a complete eligibility evaluator."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from pcn_grouping.models import (
    Component,
    ComponentKind,
    ConcentrationInterval,
    ConcentrationValue,
    Evidence,
    EvidenceStatus,
    Formulation,
    RuleResult,
    RuleStatus,
)
from pcn_grouping.validation import KNOWN_HAZARD_CLASSES

from .contracts import (
    Bounds,
    ComponentAnalysis,
    ComponentRow,
    EvidenceCatalog,
    IdentityKey,
    LineEvidence,
    LineRef,
    PerfumeTotal,
    RepresentationApproval,
    Revision,
)
from .identity import normalise_identifier, resolve_identity
from .rules import ComponentRules, sum_bounds, verified

_HEALTH = frozenset(
    {
        "Acute Tox.",
        "Skin Corr.",
        "Skin Irrit.",
        "Eye Dam.",
        "Eye Irrit.",
        "Resp. Sens.",
        "Skin Sens.",
        "Muta.",
        "Carc.",
        "Repr.",
        "Lact.",
        "STOT SE",
        "STOT RE",
        "Asp. Tox.",
        "ED HH",
    }
)
_SECTIONS = {
    "REG-SUBSTANCE-ID": "B.3.2.1",
    "REG-MIM": "B.3.2.2; B.3.8",
    "REG-COMPONENTS": "A.4.2; B.3.3",
    "REG-PERFUME-IDENTITY": "A.4.3",
    "REG-PERFUME-CAP": "A.4.3",
    "REG-PERFUME-MAP": "B.3.1; B.3.8",
    "REG-GCI": "B.3.2.3",
    "REG-ICG": "B.3.5",
    "REG-PERFUME-OMISSION": "B.3.4.2",
}


def _status(results: Sequence[RuleResult]) -> RuleStatus:
    statuses = {r.status for r in results}
    if RuleStatus.FAIL in statuses:
        return RuleStatus.FAIL
    if RuleStatus.REVIEW in statuses:
        return RuleStatus.REVIEW
    return RuleStatus.PASS


class _Results:
    def __init__(self) -> None:
        self.items: list[RuleResult] = []

    def add(
        self,
        rule: str,
        status: RuleStatus,
        code: str,
        *,
        line: LineRef | None = None,
        revision: Revision | None = None,
        evidence: tuple[Evidence | None, ...] = (),
        scope: str = "components",
        values: tuple[tuple[str, str], ...] = (),
    ) -> None:
        fields = [("code", code), ("scope", scope), *values]
        if line:
            fields.extend(zip(("formulation_id", "revision", "line_id"), line, strict=True))
        elif revision:
            fields.extend(zip(("formulation_id", "revision"), revision, strict=True))
        self.items.append(
            RuleResult(
                rule,
                status,
                code.replace("_", " ").lower(),
                tuple(sorted({e.evidence_id for e in evidence if e})),
                (_SECTIONS.get(rule, "Integration rule approval gate"),),
                tuple(sorted(fields)),
            )
        )


def _bounds(component: Component) -> Bounds:
    actual = component.actual
    if isinstance(actual, ConcentrationValue):
        return Bounds(actual.value, actual.value)
    if isinstance(actual, ConcentrationInterval):
        return Bounds(actual.lower, actual.upper)
    return Bounds(None, None)


def _valid_bounds(bounds: Bounds) -> bool:
    lo, hi = bounds.lower, bounds.upper
    return (
        lo is not None
        and hi is not None
        and lo.is_finite()
        and hi.is_finite()
        and Decimal(0) <= lo <= hi <= Decimal(100)
    )


def _role(component: Component) -> str:
    return (component.technical_function or "").strip().upper()


def _class_complete(c: Component, e: LineEvidence) -> bool:
    return verified(e.classification_complete) and all(
        h.status is EvidenceStatus.VERIFIED
        and h.source_document_ids
        and h.hazard_class in KNOWN_HAZARD_CLASSES
        and h.category
        and h.h_code
        for h in c.classifications
    )


def _class_signature(c: Component) -> tuple[tuple[str, str, str, str, str], ...]:
    return tuple(
        sorted(
            (h.hazard_class, h.category, h.h_code, h.route or "", h.qualifier or "")
            for h in c.classifications
        )
    )


def _evidence(c: Component, e: LineEvidence, catalog: EvidenceCatalog) -> tuple[Evidence, ...]:
    values = [
        c.identity_evidence,
        c.perfume_role_evidence,
        e.classification_complete,
        e.function,
        e.notification_evidence,
    ]
    values.extend(
        a.evidence
        for a in catalog.aliases
        if a.input_id == c.identity_id
        and a.kind == c.kind
        and a.supplier_id == (c.mim.supplier_id if c.mim else None)
    )
    if e.mim:
        values.extend(
            (
                e.mim.evidence,
                e.mim.ufi_validation,
                e.mim.sds_composition,
                e.mim.other_known_components,
                e.mim.supplier_contact,
            )
        )
        values.extend(p for _, p in e.mim.prior_recipients)
    return tuple(p for p in values if p is not None)


def _mim_ok(c: Component, e: LineEvidence, f: Formulation) -> tuple[bool, str]:
    mim, route = c.mim, e.mim
    if not mim or not route or not verified(route.evidence):
        return False, "MIM_ROUTE_MISSING"
    if mim.composition_known is True or route.route == "FULL_COMPOSITION":
        return False, "FULL_MIM_REQUIRES_UPSTREAM_CONSTITUENT_EXPANSION"
    if mim.composition_known is not False:
        return False, "MIM_COMPOSITION_KNOWLEDGE_UNKNOWN"
    if not _role(c) or not verified(e.function):
        return False, "MIM_FUNCTION_UNKNOWN"
    if not _class_complete(c, e) or not _valid_bounds(_bounds(c)):
        return False, "MIM_CLASSIFICATION_OR_CONCENTRATION_UNKNOWN"
    if route.route in {"UFI_PRIOR", "UFI_SDS"}:
        try:
            normalise_identifier("UFI", mim.ufi or "")
        except ValueError:
            return False, "MIM_UFI_INVALID"
        if not verified(route.ufi_validation):
            return False, "MIM_UFI_VALIDATION_MISSING"
    elif route.route != "NO_UFI_SDS" or mim.ufi:
        return False, "MIM_ROUTE_INCONSISTENT"
    if route.route == "UFI_PRIOR":
        recipients = dict(route.prior_recipients)
        if (
            len(recipients) != len(route.prior_recipients)
            or not f.market_countries
            or any(not verified(recipients.get(country)) for country in f.market_countries)
        ):
            return False, "MIM_PRIOR_RECIPIENT_EVIDENCE_MISSING"
    elif not (
        mim.sds_document_id
        and verified(route.sds_composition)
        and route.sds_composition
        and mim.sds_document_id in route.sds_composition.source_document_ids
        and verified(route.other_known_components)
        and verified(route.supplier_contact)
        and route.supplier_name
        and route.supplier_name.strip()
        and route.supplier_email
        and route.supplier_email.strip()
        and route.supplier_phone
        and route.supplier_phone.strip()
    ):
        return False, "MIM_SDS_KNOWN_COMPONENTS_OR_SUPPLIER_MISSING"
    return True, "MIM_ROUTE_EVIDENCED"


@dataclass(frozen=True)
class _Line:
    component: Component
    evidence: LineEvidence
    row: ComponentRow


def _prepare(f: Formulation, catalog: EvidenceCatalog, results: _Results) -> list[_Line]:
    output: list[_Line] = []
    raw_ids = [r.source_line_id for r in f.raw_bom]
    component_ids = [c.line_id for c in f.components]
    if (
        not f.components
        or len(set(raw_ids)) != len(raw_ids)
        or len(set(component_ids)) != len(component_ids)
        or any(not s.strip() for s in component_ids)
    ):
        results.add(
            "REG-COMPONENTS",
            RuleStatus.REVIEW,
            "EMPTY_OR_DUPLICATE_BOM_IDS",
            revision=(f.formulation_id, f.revision),
        )
    for c in sorted(f.components, key=lambda x: x.line_id):
        ref = (f.formulation_id, f.revision, c.line_id)
        found = [e for e in catalog.lines if e.line == ref]
        e = found[0] if len(found) == 1 else LineEvidence(ref)
        if len(found) != 1:
            results.add(
                "REG-COMPONENTS", RuleStatus.REVIEW, "LINE_EVIDENCE_MISSING_OR_DUPLICATE", line=ref
            )
        key, record, code = resolve_identity(c, catalog)
        evidence = (
            *_evidence(c, e, catalog),
            *((record.evidence,) if record and record.evidence else ()),
        )
        identity_ok = key is not None
        results.add(
            "REG-MIM" if c.kind is ComponentKind.MIM else "REG-SUBSTANCE-ID",
            RuleStatus.PASS if identity_ok else RuleStatus.REVIEW,
            code,
            line=ref,
            evidence=evidence,
        )
        if c.kind is ComponentKind.MIM:
            ok, code = _mim_ok(c, e, f)
            results.add(
                "REG-MIM",
                RuleStatus.PASS if ok else RuleStatus.REVIEW,
                code,
                line=ref,
                evidence=(e.mim.evidence if e.mim else None,),
            )
            identity_ok = identity_ok and ok
        if (
            not c.source_line_ids
            or not c.source_document_ids
            or any(s not in raw_ids for s in c.source_line_ids)
            or any(
                r.source_document_id not in c.source_document_ids
                for r in f.raw_bom
                if r.source_line_id in c.source_line_ids
            )
        ):
            results.add("REG-COMPONENTS", RuleStatus.REVIEW, "RAW_BOM_TRACE_MISSING", line=ref)
        actual = _bounds(c)
        if not _valid_bounds(actual):
            results.add(
                "REG-COMPONENTS", RuleStatus.REVIEW, "ACTUAL_BOUNDS_INVALID_OR_UNKNOWN", line=ref
            )
            actual = Bounds(None, None)
        elif actual.lower == 0 and actual.upper != 0:
            results.add("REG-COMPONENTS", RuleStatus.REVIEW, "PRESENCE_UNCERTAIN", line=ref)
        if not _class_complete(c, e):
            results.add(
                "REG-PERFUME-MAP",
                RuleStatus.REVIEW,
                "CLASSIFICATION_INCOMPLETE",
                line=ref,
                scope="disclosure",
                evidence=(e.classification_complete,),
            )
            results.add("REG-COMPONENTS", RuleStatus.REVIEW, "CLASSIFICATION_INCOMPLETE", line=ref)
        perfume = (
            _role(c) == "PERFUME" and verified(c.perfume_role_evidence) and verified(e.function)
        )
        row = ComponentRow(
            ref,
            key,
            key,
            actual,
            tuple(sorted(c.source_line_ids)),
            tuple(
                sorted(
                    set(c.source_document_ids)
                    | {s for p in evidence for s in p.source_document_ids}
                    | {s for h in c.classifications for s in h.source_document_ids}
                )
            ),
            tuple(
                sorted(
                    c.classifications,
                    key=lambda h: (
                        h.hazard_class,
                        h.category,
                        h.h_code,
                        h.route or "",
                        h.qualifier or "",
                    ),
                )
            ),
            perfume,
            identity_ok,
            False,
            None,
            tuple(sorted({p.evidence_id for p in evidence})),
        )
        output.append(_Line(c, e, row))
    covered = {s for c in f.components for s in c.source_line_ids}
    if set(raw_ids) - covered:
        results.add(
            "REG-COMPONENTS",
            RuleStatus.REVIEW,
            "RAW_BOM_LINES_UNACCOUNTED",
            revision=(f.formulation_id, f.revision),
        )
    return output


def _approval_ok(
    a: RepresentationApproval,
    lines: list[_Line],
    revision: Revision,
    rules: ComponentRules,
    catalog: EvidenceCatalog,
) -> bool:
    members = {line.row.raw_identity_key[1] for line in lines if line.row.raw_identity_key}
    for identity in a.member_identity_ids:
        records = [record for record in catalog.identities if record.identity_id == identity]
        if len(records) != 1 or not verified(records[0].evidence):
            return False
        try:
            normalise_identifier(records[0].identifier_scheme, records[0].identifier)
        except ValueError:
            return False
    return bool(
        verified(a.evidence)
        and a.ruleset_sha256 == rules.version.sha256
        and revision in a.revisions
        and a.member_identity_ids
        and len(set(a.member_identity_ids)) == len(a.member_identity_ids)
        and members <= set(a.member_identity_ids)
        and all(line.row.identity_verified for line in lines)
    )


def _representation(
    a: RepresentationApproval,
    lines: list[_Line],
    revision: Revision,
    rules: ComponentRules,
    results: _Results,
    catalog: EvidenceCatalog,
) -> bool:
    rule = "REG-GCI" if a.kind == "GCI" else "REG-ICG"
    if a.kind not in {"GCI", "ICG"} or not _approval_ok(a, lines, revision, rules, catalog):
        results.add(
            rule,
            RuleStatus.REVIEW,
            "REPRESENTATION_APPROVAL_SCOPE_MISSING",
            revision=revision,
            evidence=(a.evidence,),
        )
        return False
    if a.kind == "GCI":
        if a.function not in {"PERFUME", "COLOURANT"}:
            results.add(rule, RuleStatus.REVIEW, "GCI_FUNCTION_UNKNOWN", revision=revision)
            return False
        ok = True
        for line in lines:
            c, e = line.component, line.evidence
            if (
                not _class_complete(c, e)
                or not verified(e.function)
                or e.exclusive_function is None
            ):
                status, code = RuleStatus.REVIEW, "GCI_FUNCTION_OR_CLASSIFICATION_UNVERIFIED"
            elif (
                _role(c) != a.function
                or e.exclusive_function is not True
                or any(h.hazard_class in _HEALTH for h in c.classifications)
            ):
                status, code = RuleStatus.FAIL, "GCI_EXCLUSIVE_FUNCTION_OR_HEALTH_CONDITION_FAILED"
            elif a.function == "PERFUME" and not line.row.perfume_verified:
                status, code = RuleStatus.REVIEW, "GCI_PERFUME_ROLE_UNVERIFIED"
            else:
                status, code = RuleStatus.PASS, "GCI_MEMBER_EVIDENCED"
            results.add(
                rule,
                status,
                code,
                line=line.row.line,
                evidence=(a.evidence, e.function, e.classification_complete),
            )
            ok = ok and status is RuleStatus.PASS
        return ok
    required = {
        "component_identification",
        "concentration_data",
        "identical_classification",
        "combination_invariance",
    }
    if a.icg_pathway == "GENERAL":
        required |= {"same_function", "same_toxicology"}
    elif a.icg_pathway == "ALTERNATIVE":
        required |= {"allowed_hazards", "ph_band"}
        if len(a.member_identity_ids) > 5:
            results.add(rule, RuleStatus.FAIL, "ICG_ALTERNATIVE_MORE_THAN_FIVE", revision=revision)
            return False
    else:
        required.add("unknown_pathway")
    criteria = dict(a.criteria)
    if (
        not a.pre_existing
        or len(criteria) != len(a.criteria)
        or not all(verified(criteria.get(k)) for k in required)
    ):
        results.add(
            rule,
            RuleStatus.REVIEW,
            "ICG_PREEXISTING_VALIDATION_MISSING",
            revision=revision,
            evidence=(a.evidence,),
        )
        return False
    if any(not _class_complete(line.component, line.evidence) for line in lines):
        results.add(rule, RuleStatus.REVIEW, "ICG_CLASSIFICATION_UNKNOWN", revision=revision)
        return False
    if a.icg_pathway == "GENERAL" and any(
        not _role(line.component) or not verified(line.evidence.function) for line in lines
    ):
        results.add(rule, RuleStatus.REVIEW, "ICG_FUNCTION_UNKNOWN", revision=revision)
        return False
    if a.icg_pathway == "ALTERNATIVE" and any(
        h.hazard_class
        not in {
            "Skin Corr.",
            "Skin Irrit.",
            "Eye Dam.",
            "Eye Irrit.",
            "Asp. Tox.",
            "Resp. Sens.",
            "Skin Sens.",
        }
        for line in lines
        for h in line.component.classifications
    ):
        results.add(
            rule, RuleStatus.FAIL, "ICG_ALTERNATIVE_HAZARDS_NOT_PERMITTED", revision=revision
        )
        return False
    results.add(
        rule,
        RuleStatus.PASS,
        "ICG_EXISTING_SCOPED_VALIDATION_RECORDED",
        revision=revision,
        evidence=(a.evidence, *criteria.values()),
    )
    return True


def _cap(bounds: Bounds, cap: Decimal) -> RuleStatus:
    if bounds.lower is not None and bounds.lower > cap:
        return RuleStatus.FAIL
    if bounds.upper is not None and bounds.upper <= cap:
        return RuleStatus.PASS
    return RuleStatus.REVIEW


def _cap_result(
    results: _Results,
    rule: str,
    bounds: Bounds,
    cap: Decimal,
    revision: Revision,
    *,
    reliable: bool = True,
    code: str = "CAP_CHECK",
) -> None:
    results.add(
        rule,
        _cap(bounds, cap) if reliable else RuleStatus.REVIEW,
        code,
        revision=revision,
        values=(("lower", str(bounds.lower)), ("upper", str(bounds.upper)), ("limit", str(cap))),
    )


def _notified(
    f: Formulation,
    lines: list[_Line],
    catalog: EvidenceCatalog,
    rules: ComponentRules,
    results: _Results,
) -> list[_Line]:
    revision = (f.formulation_id, f.revision)
    gci: dict[str, list[Bounds]] = {}
    covered: set[str] = set()
    declaration_ids: set[str] = set()
    for d in sorted(f.notified_components, key=lambda x: x.declaration_id):
        members = [line for line in lines if line.component.line_id in d.source_component_line_ids]
        member_ids = {line.component.line_id for line in members}
        if (
            not members
            or len(members) != len(member_ids)
            or len(member_ids) != len(d.source_component_line_ids)
            or member_ids & covered
            or d.declaration_id in declaration_ids
        ):
            results.add(
                "REG-COMPONENTS",
                RuleStatus.REVIEW,
                "DECLARATION_PARTITION_INVALID",
                revision=revision,
            )
            continue
        covered |= member_ids
        declaration_ids.add(d.declaration_id)
        key: IdentityKey | None = None
        approval_evidence: tuple[Evidence, ...] = ()
        raw_keys = {line.row.raw_identity_key for line in members}
        if len(raw_keys) == 1 and None not in raw_keys:
            candidate = members[0].row.raw_identity_key
            if candidate and d.declared_identity_id == candidate[1]:
                key = candidate
        if key is None:
            approvals = [
                a
                for a in catalog.representations
                if a.declared_identity_id == d.declared_identity_id
            ]
            if len(approvals) != 1:
                results.add(
                    "REG-COMPONENTS",
                    RuleStatus.REVIEW,
                    "REPRESENTATION_APPROVAL_MISSING",
                    revision=revision,
                )
            else:
                a = approvals[0]
                approval_evidence = tuple(p for p in (a.evidence, *(p for _, p in a.criteria)) if p)
                if a.kind == "GCI" and a.function in {"PERFUME", "COLOURANT"}:
                    gci.setdefault(a.function, []).extend(line.row.actual for line in members)
                if _representation(a, members, revision, rules, results, catalog):
                    key = (a.kind, a.declared_identity_id)
        for i, line in enumerate(lines):
            if line.component.line_id not in member_ids:
                continue
            omitted = d.concentration is None or (
                isinstance(d.concentration, ConcentrationValue) and d.concentration.value is None
            )
            if omitted:
                allowed = (
                    line.row.perfume_verified
                    and _class_complete(line.component, line.evidence)
                    and all(
                        (
                            f"{h.hazard_class} {h.category}" in rules.omission_categories
                            or h.hazard_class == "Asp. Tox."
                            and "Asp. Tox." in rules.omission_categories
                        )
                        for h in line.component.classifications
                    )
                )
                if d.declaration_exemption_code != "PERFUME_CONCENTRATION_OMISSION":
                    status, code = RuleStatus.REVIEW, "CONCENTRATION_OMISSION_BASIS_MISSING"
                elif (
                    not _class_complete(line.component, line.evidence)
                    or not line.row.perfume_verified
                ):
                    status, code = RuleStatus.REVIEW, "PERFUME_OMISSION_EVIDENCE_MISSING"
                elif not allowed:
                    status, code = RuleStatus.FAIL, "PERFUME_OMISSION_HAZARDS_NOT_PERMITTED"
                else:
                    status, code = RuleStatus.PASS, "PERFUME_DISCLOSURE_ONLY_OMISSION"
                results.add(
                    "REG-PERFUME-OMISSION",
                    status,
                    code,
                    line=line.row.line,
                    scope="disclosure",
                    evidence=(line.evidence.classification_complete,),
                )
            lines[i] = replace(
                line,
                row=replace(
                    line.row,
                    notified_identity_key=key,
                    declared_concentration_omitted=omitted,
                    declaration_id=d.declaration_id,
                    evidence_ids=tuple(
                        sorted(
                            set(line.row.evidence_ids) | {p.evidence_id for p in approval_evidence}
                        )
                    ),
                    source_document_ids=tuple(
                        sorted(
                            set(line.row.source_document_ids)
                            | {s for p in approval_evidence for s in p.source_document_ids}
                        )
                    ),
                ),
            )
    if f.notified_components and covered != {line.component.line_id for line in lines}:
        results.add(
            "REG-COMPONENTS",
            RuleStatus.REVIEW,
            "DECLARATION_COVERAGE_INCOMPLETE",
            revision=revision,
        )
    for function, values in sorted(gci.items()):
        cap = rules.perfume_gci_cap if function == "PERFUME" else rules.colourant_gci_cap
        _cap_result(
            results,
            "REG-GCI",
            sum_bounds(tuple(values)),
            cap,
            revision,
            code=f"GCI_{function}_AGGREGATE_CAP",
        )
    return lines


def _sets(
    groups: list[list[_Line]], notified: bool
) -> tuple[tuple[IdentityKey, ...], tuple[IdentityKey, ...]]:
    sets: list[set[IdentityKey]] = []
    for lines in groups:
        keys = set()
        for line in lines:
            key = line.row.notified_identity_key if notified else line.row.raw_identity_key
            if key is not None and line.row.actual.upper != 0:
                keys.add(key)
        sets.append(keys)
    common = set.intersection(*sets) if sets else set()
    union = set.union(*sets) if sets else set()
    return tuple(sorted(common)), tuple(sorted(union - common))


def analyse_components(
    formulations: Sequence[Formulation], catalog: EvidenceCatalog, rules: ComponentRules
) -> ComponentAnalysis:
    """Evaluate the entire proposed group, preserving every source BOM line.

    Caller must still run B input checks and C/E full eligibility rules. Results
    include a disclosure status separate from component comparison. Missing
    evidence never confers identity equivalence or approval.
    """
    results = _Results()
    revisions = [(f.formulation_id, f.revision) for f in formulations]
    if (
        not revisions
        or len(set(revisions)) != len(revisions)
        or any(not all(part.strip() for part in rev) for rev in revisions)
    ):
        results.add("REG-COMPONENTS", RuleStatus.REVIEW, "EMPTY_OR_DUPLICATE_REVISIONS")
        return ComponentAnalysis(
            RuleStatus.REVIEW,
            RuleStatus.REVIEW,
            rules.version,
            (),
            (),
            (),
            (),
            (),
            (),
            tuple(results.items),
        )
    if not rules.approved:
        results.add(
            "COMP-RULESET-APPROVAL",
            RuleStatus.REVIEW,
            "RULESET_NOT_APPROVED",
            evidence=(rules.approval,),
        )
    bases = {f.composition_basis for f in formulations}
    basis_ok = len(bases) == 1 and None not in bases
    if not basis_ok:
        results.add("REG-COMPONENTS", RuleStatus.REVIEW, "PERCENTAGE_BASIS_UNVERIFIED")
    ordered = sorted(formulations, key=lambda f: (f.formulation_id, f.revision))
    groups = [_notified(f, _prepare(f, catalog, results), catalog, rules, results) for f in ordered]
    raw_common, raw_varying = _sets(groups, False)
    common, varying = _sets(groups, True)
    reliable = all(
        f.components and len({c.line_id for c in f.components}) == len(f.components)
        for f in ordered
    ) and all(
        line.row.identity_verified
        and _valid_bounds(line.row.actual)
        and (line.row.actual.lower != 0 or line.row.actual.upper == 0)
        for lines in groups
        for line in lines
    )
    # Conflicting authoritative records cannot make the same key safely common.
    by_key: dict[IdentityKey, list[_Line]] = {}
    for lines in groups:
        for line in lines:
            if line.row.raw_identity_key:
                by_key.setdefault(line.row.raw_identity_key, []).append(line)
    for same in by_key.values():
        if (
            len({_class_signature(line.component) for line in same}) > 1
            or len({_role(line.component) for line in same}) > 1
        ):
            results.add(
                "REG-COMPONENTS",
                RuleStatus.REVIEW,
                "IDENTITY_EVIDENCE_CONFLICT",
                line=same[0].row.line,
            )
            reliable = False
        if (
            len(
                {
                    line.component.mim.ufi.replace("-", "").replace(" ", "").upper()
                    if line.component.mim and line.component.mim.ufi
                    else None
                    for line in same
                }
            )
            > 1
        ):
            results.add(
                "REG-MIM", RuleStatus.REVIEW, "MIM_UFI_IDENTITY_CONFLICT", line=same[0].row.line
            )
            reliable = False
    by_rep: dict[IdentityKey, list[_Line]] = {}
    for lines in groups:
        for line in lines:
            if line.row.notified_identity_key:
                by_rep.setdefault(line.row.notified_identity_key, []).append(line)
    for key, same in sorted(by_rep.items()):
        if key[0] not in {"GCI", "ICG"}:
            continue
        if len({_class_signature(line.component) for line in same}) > 1:
            results.add(
                "REG-ICG" if key[0] == "ICG" else "REG-GCI",
                RuleStatus.REVIEW,
                "REPRESENTATION_CLASSIFICATION_CONFLICT",
                line=same[0].row.line,
            )
        if key[0] == "ICG" and len({_role(line.component) for line in same}) > 1:
            results.add(
                "REG-ICG", RuleStatus.REVIEW, "ICG_FUNCTION_CONFLICT", line=same[0].row.line
            )
    # Common raw identities still require a consistent notified representation.
    for lines in groups:
        for line in lines:
            if (
                line.row.raw_identity_key in raw_common
                and line.row.notified_identity_key in varying
            ):
                results.add(
                    "REG-COMPONENTS",
                    RuleStatus.REVIEW,
                    "COMMON_RAW_DECLARATION_IDENTITY_MISMATCH",
                    line=line.row.line,
                )
    totals = []
    for f, lines in zip(ordered, groups, strict=True):
        perfume_lines = []
        role_complete = True
        for line in lines:
            row, c, e = line.row, line.component, line.evidence
            if row.actual.upper == 0:
                continue  # exact absence is preserved in matrix/raw BOM
            if row.raw_identity_key not in raw_varying:
                continue
            if (
                row.notified_identity_key in common
                and row.notified_identity_key
                and row.notified_identity_key[0] == "ICG"
            ):
                # A previously validated common ICG is the notified identity;
                # these substitutions do not rely on the A.4.3 exception.
                results.add(
                    "REG-COMPONENTS",
                    RuleStatus.PASS,
                    "COMMON_APPROVED_ICG_REPRESENTATION",
                    line=row.line,
                )
            elif row.perfume_verified:
                perfume_lines.append(line)
                results.add(
                    "REG-PERFUME-IDENTITY",
                    RuleStatus.PASS,
                    "VARYING_PERFUME_FUNCTION_VERIFIED",
                    line=row.line,
                    evidence=(c.perfume_role_evidence, e.function),
                )
            elif (
                row.notified_identity_key in common
                and row.notified_identity_key != row.raw_identity_key
            ):
                results.add(
                    "REG-COMPONENTS",
                    RuleStatus.PASS,
                    "COMMON_APPROVED_REPRESENTATION",
                    line=row.line,
                )
            elif (
                row.notified_identity_key is None
                or not reliable
                or not verified(e.function)
                or not _role(c)
                or _role(c) == "PERFUME"
            ):
                role_complete = False
                results.add(
                    "REG-PERFUME-IDENTITY",
                    RuleStatus.REVIEW,
                    "VARYING_FUNCTION_OR_IDENTITY_UNVERIFIED",
                    line=row.line,
                )
            elif (e.notification_required is True and verified(e.notification_evidence)) or (
                row.actual.lower is not None and row.actual.lower >= Decimal(1)
            ):
                results.add("REG-COMPONENTS", RuleStatus.FAIL, "VARYING_NON_PERFUME", line=row.line)
            else:
                results.add(
                    "REG-COMPONENTS",
                    RuleStatus.REVIEW,
                    "TRACE_NOTIFIABILITY_REQUIRES_REVIEW",
                    line=row.line,
                )
        total = sum_bounds(tuple(line.row.actual for line in perfume_lines))
        if not reliable or not role_complete:
            total = Bounds(None, None)
        revision = (f.formulation_id, f.revision)
        totals.append(
            PerfumeTotal(
                revision,
                tuple(line.component.line_id for line in perfume_lines),
                total,
                reliable and role_complete,
            )
        )
        _cap_result(
            results,
            "REG-PERFUME-CAP",
            total,
            rules.varying_perfume_cap,
            revision,
            reliable=reliable and role_complete and basis_ok,
        )
    items = tuple(
        sorted(results.items, key=lambda r: (r.rule_id, r.values, r.status.value, r.evidence_ids))
    )
    return ComponentAnalysis(
        _status([r for r in items if ("scope", "components") in r.values]),
        _status([r for r in items if ("scope", "disclosure") in r.values]),
        rules.version,
        raw_common,
        raw_varying,
        common,
        varying,
        tuple(line.row for lines in groups for line in lines),
        tuple(totals),
        items,
    )
