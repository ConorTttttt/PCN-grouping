"""Offline structural checks. REVIEW is missing evidence, never legal eligibility."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, TypeVar

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
    SourceReference,
)

# Data-quality check only: NOT a statutory rounding or concentration-band tolerance.
DEFAULT_TOTAL_TOLERANCE = Decimal("0.01")  # percentage points, explicit/overridable
_DECIMAL_RE = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
_H_CODE_RE = re.compile(r"^H\d{3}[A-Z]?$|^EUH\d{3}$")
# Vocabulary is an input sanity check, not an official classification engine.
KNOWN_HAZARD_CLASSES = frozenset({
    "Expl.", "Desens. Expl.", "Flam. Gas", "Aerosol", "Ox. Gas", "Press. Gas",
    "Flam. Liq.", "Flam. Sol.", "Self-react.", "Pyr. Liq.", "Pyr. Sol.",
    "Self-heat.", "Water-react.", "Ox. Liq.", "Ox. Sol.", "Org. Perox.",
    "Met. Corr.", "Acute Tox.", "Skin Corr.", "Skin Irrit.", "Eye Dam.",
    "Eye Irrit.", "Resp. Sens.", "Skin Sens.", "Muta.", "Carc.", "Repr.",
    "Lact.", "STOT SE", "STOT RE", "Asp. Tox.", "Aquatic Acute",
    "Aquatic Chronic", "Ozone", "ED HH", "ED ENV", "PBT", "vPvB", "PMT", "vPvM",
})
# H and EUH require a recognised numeric family; atypical/new values remain REVIEW.
KNOWN_H_CODES = frozenset({
    *[f"H{i}" for i in range(200, 206)],
    *[f"H{i}" for i in range(220, 232)],
    *[f"H{i}" for i in range(240, 243)],
    *[f"H{i}" for i in range(250, 253)],
    *[f"H{i}" for i in range(260, 262)],
    *[f"H{i}" for i in range(270, 273)],
    *[f"H{i}" for i in range(280, 282)],
    "H290", "H300", "H301", "H302", "H304", "H310", "H311", "H312",
    "H314", "H315", "H317", "H318", "H319", "H330", "H331", "H332",
    "H334", "H335", "H336", "H340", "H341", "H350", "H351", "H360",
    "H361", "H362", "H370", "H371", "H372", "H373", "H400", "H410",
    "H411", "H412", "H413", "H420", "EUH001", "EUH006", "EUH014",
    "EUH018", "EUH019", "EUH029", "EUH031", "EUH032", "EUH044",
    "EUH066", "EUH070", "EUH071", "EUH201", "EUH202", "EUH204",
    "EUH205", "EUH206", "EUH207", "EUH208", "EUH209", "EUH210",
    "EUH401",
})


class IssueSeverity(str, Enum):
    ERROR = "ERROR"  # invalid contract/data; reject import
    REVIEW = "REVIEW"  # structurally acceptable but evidence still missing


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: IssueSeverity
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ParseResult:
    formulation: Formulation | None
    issues: tuple[ValidationIssue, ...]

    @property
    def accepted(self) -> bool:
        return self.formulation is not None and not any(
            issue.severity is IssueSeverity.ERROR for issue in self.issues
        )


def _issue(issues: list[ValidationIssue], code: str, severity: IssueSeverity,
           path: str, message: str) -> None:
    issues.append(ValidationIssue(code, severity, path, message))


def _text(value: Any, issues: list[ValidationIssue], path: str,
          *, required: bool = False) -> str | None:
    if value is None or value == "":
        if required:
            _issue(issues, "MISSING_ID", IssueSeverity.ERROR, path, "Required identifier absent")
        return None
    if not isinstance(value, str):
        _issue(issues, "INVALID_TYPE", IssueSeverity.ERROR, path, "Expected text")
        return None
    if value != value.strip():
        _issue(issues, "UNNORMALIZED_ID", IssueSeverity.REVIEW, path,
               "Whitespace may alter an identifier; verify source")
    return value


TEnum = TypeVar("TEnum", bound=Enum)


def _enum(value: Any, enum_type: type[TEnum], fallback: TEnum,
          issues: list[ValidationIssue], path: str) -> TEnum:
    try:
        return enum_type(value)
    except (ValueError, TypeError):
        _issue(issues, "UNKNOWN_ENUM", IssueSeverity.REVIEW, path,
               f"Unrecognised {enum_type.__name__}: {value!r}")
        return fallback


def _string_tuple(value: Any, issues: list[ValidationIssue], path: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        _issue(issues, "INVALID_TYPE", IssueSeverity.ERROR, path,
               "Expected an array of strings")
        return ()
    return tuple(value)


def _records(value: Any, issues: list[ValidationIssue], path: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        _issue(issues, "INVALID_TYPE", IssueSeverity.ERROR, path, "Expected an array")
        return []
    output: list[Mapping[str, Any]] = []
    for i, item in enumerate(value):
        if not isinstance(item, Mapping):
            _issue(issues, "INVALID_TYPE", IssueSeverity.ERROR, f"{path}[{i}]",
                   "Expected an object")
        else:
            output.append(item)
    return output


def _decimal(value: Any, issues: list[ValidationIssue], path: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is Decimal:
        number = value
    elif isinstance(value, str) and _DECIMAL_RE.fullmatch(value):
        try:
            number = Decimal(value)
        except InvalidOperation:
            number = Decimal("NaN")
    else:
        _issue(issues, "INVALID_DECIMAL", IssueSeverity.ERROR, path,
               "Use Decimal or a plain decimal string; floats, numbers and exponents forbidden")
        return None
    if not number.is_finite() or not (Decimal(0) <= number <= Decimal(100)):
        _issue(issues, "PERCENT_OUT_OF_RANGE", IssueSeverity.ERROR, path,
               "Percentage must be finite and within 0..100 inclusive")
        return None
    return number


def parse_concentration(value: Any, path: str = "actual") -> tuple[
    ConcentrationValue | ConcentrationInterval | None, tuple[ValidationIssue, ...]
]:
    """Value schema: {\"exact\": \"5.0000\"} or {\"lower\": ..., \"upper\": ...}."""
    issues: list[ValidationIssue] = []
    if value is None:
        _issue(issues, "UNKNOWN_CONCENTRATION", IssueSeverity.REVIEW, path,
               "Actual concentration absent; never interpret as zero")
        return None, tuple(issues)
    if not isinstance(value, Mapping):
        _issue(issues, "INVALID_TYPE", IssueSeverity.ERROR, path,
               "Expected exact or lower/upper concentration object")
        return None, tuple(issues)
    if "exact" in value and len(value) == 1:
        if value["exact"] is None:
            _issue(issues, "UNKNOWN_CONCENTRATION", IssueSeverity.REVIEW, path,
                   "Actual exact percentage unknown")
            return ConcentrationValue(None), tuple(issues)
        number = _decimal(value["exact"], issues, f"{path}.exact")
        return (ConcentrationValue(number) if number is not None else None, tuple(issues))
    if set(value) == {"lower", "upper"}:
        lower = _decimal(value["lower"], issues, f"{path}.lower")
        upper = _decimal(value["upper"], issues, f"{path}.upper")
        if lower is not None and upper is not None and lower > upper:
            _issue(issues, "INVALID_BOUNDS", IssueSeverity.ERROR, path,
                   "Inclusive lower bound exceeds upper bound")
        if lower is None or upper is None:
            _issue(issues, "UNKNOWN_CONCENTRATION", IssueSeverity.REVIEW, path,
                   "At least one concentration endpoint unknown")
        return ConcentrationInterval(lower, upper), tuple(issues)
    _issue(issues, "INVALID_CONCENTRATION_SHAPE", IssueSeverity.ERROR, path,
           "Supply exactly 'exact' or both 'lower' and 'upper'")
    return None, tuple(issues)


def _classification(row: Mapping[str, Any], path: str,
                    issues: list[ValidationIssue]) -> CLPClassification:
    hazard_class = _text(row.get("hazard_class"), issues, f"{path}.hazard_class") or ""
    category = _text(row.get("category"), issues, f"{path}.category") or ""
    h_code = _text(row.get("h_code"), issues, f"{path}.h_code") or ""
    return CLPClassification(
        hazard_class=hazard_class, category=category, h_code=h_code,
        route=_text(row.get("route"), issues, f"{path}.route"),
        qualifier=_text(row.get("qualifier"), issues, f"{path}.qualifier"),
        status=_enum(row.get("status", "UNKNOWN"), EvidenceStatus,
                     EvidenceStatus.UNKNOWN, issues, f"{path}.status"),
        source_document_ids=_string_tuple(row.get("source_document_ids"), issues,
                                          f"{path}.source_document_ids"),
    )


def _evidence(value: Any, path: str, issues: list[ValidationIssue]) -> Evidence | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        _issue(issues, "INVALID_TYPE", IssueSeverity.ERROR, path, "Expected evidence object")
        return None
    return Evidence(
        evidence_id=_text(value.get("evidence_id"), issues,
                          f"{path}.evidence_id", required=True) or "",
        status=_enum(value.get("status", "UNKNOWN"), EvidenceStatus,
                     EvidenceStatus.UNKNOWN, issues, f"{path}.status"),
        source_document_ids=_string_tuple(value.get("source_document_ids"), issues,
                                          f"{path}.source_document_ids"),
        verified_by=_text(value.get("verified_by"), issues, f"{path}.verified_by"),
        verified_at=_text(value.get("verified_at"), issues, f"{path}.verified_at"),
        note=_text(value.get("note"), issues, f"{path}.note"),
    )


def _mim(value: Any, path: str, issues: list[ValidationIssue]) -> MiMIdentifiers | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        _issue(issues, "INVALID_TYPE", IssueSeverity.ERROR, path, "Expected MiM object")
        return None
    known = value.get("composition_known")
    if known is not None and type(known) is not bool:
        _issue(issues, "INVALID_TYPE", IssueSeverity.ERROR,
               f"{path}.composition_known", "Expected true, false or null")
        known = None
    return MiMIdentifiers(
        supplier_id=_text(value.get("supplier_id"), issues, f"{path}.supplier_id"),
        supplier_product_id=_text(value.get("supplier_product_id"), issues,
                                  f"{path}.supplier_product_id"),
        ufi=_text(value.get("ufi"), issues, f"{path}.ufi"),
        sds_document_id=_text(value.get("sds_document_id"), issues,
                              f"{path}.sds_document_id"),
        composition_known=known,
    )


def _component(row: Mapping[str, Any], path: str,
               issues: list[ValidationIssue]) -> Component:
    actual, problems = parse_concentration(row.get("actual"), f"{path}.actual")
    issues.extend(problems)
    classifications = tuple(_classification(item, f"{path}.classifications[{i}]", issues)
                            for i, item in enumerate(_records(row.get("classifications"), issues,
                                                              f"{path}.classifications")))
    return Component(
        line_id=_text(row.get("line_id"), issues, f"{path}.line_id", required=True) or "",
        identity_id=_text(row.get("identity_id"), issues, f"{path}.identity_id"),
        kind=_enum(row.get("kind"), ComponentKind, ComponentKind.SUBSTANCE,
                   issues, f"{path}.kind"),
        actual=actual,
        source_line_ids=_string_tuple(row.get("source_line_ids"), issues,
                                      f"{path}.source_line_ids"),
        source_document_ids=_string_tuple(row.get("source_document_ids"), issues,
                                          f"{path}.source_document_ids"),
        classifications=classifications,
        identity_evidence=_evidence(row.get("identity_evidence"),
                                    f"{path}.identity_evidence", issues),
        mim=_mim(row.get("mim"), f"{path}.mim", issues),
        technical_function=_text(row.get("technical_function"), issues,
                                 f"{path}.technical_function"),
        perfume_role_evidence=_evidence(row.get("perfume_role_evidence"),
                                        f"{path}.perfume_role_evidence", issues),
        confidence=_enum(row.get("confidence", "UNKNOWN"), EvidenceStatus,
                         EvidenceStatus.UNKNOWN, issues, f"{path}.confidence"),
    )


def validate_formulation(formulation: Formulation,
                         *, total_tolerance: Decimal = DEFAULT_TOTAL_TOLERANCE
                         ) -> tuple[ValidationIssue, ...]:
    """Reject corrupt input, mark incomplete evidence REVIEW; no grouping verdict."""
    if type(total_tolerance) is not Decimal or not total_tolerance.is_finite() or total_tolerance < 0:
        raise ValueError("total_tolerance must be a finite nonnegative Decimal")
    issues: list[ValidationIssue] = []
    if not formulation.formulation_id:
        _issue(issues, "MISSING_ID", IssueSeverity.ERROR, "formulation_id", "Missing stable ID")
    if not formulation.revision:
        _issue(issues, "MISSING_ID", IssueSeverity.ERROR, "revision", "Missing revision")
    if not formulation.legal_submitter_id:
        _issue(issues, "MISSING_SUBMITTER", IssueSeverity.REVIEW, "legal_submitter_id",
               "Legal submitter evidence required")
    if formulation.composition_basis is None:
        _issue(issues, "UNKNOWN_BASIS", IssueSeverity.REVIEW, "composition_basis",
               "Mass/volume denominator required; do not assume conversion")
    if formulation.notification_mode is NotificationMode.UNKNOWN:
        _issue(issues, "UNKNOWN_NOTIFICATION_MODE", IssueSeverity.REVIEW, "notification_mode",
               "Determine submission regime independently")
    if not formulation.approved_health_physical_classification:
        _issue(issues, "MISSING_CLASSIFICATION", IssueSeverity.REVIEW,
               "approved_health_physical_classification", "Approved CLP signature required")
    for collection_name, classes in (
        ("approved_health_physical_classification", formulation.approved_health_physical_classification),
        ("approved_environment_classification", formulation.approved_environment_classification),
    ):
        for i, hazard in enumerate(classes):
            path = f"{collection_name}[{i}]"
            if (hazard.hazard_class not in KNOWN_HAZARD_CLASSES or
                    not _H_CODE_RE.fullmatch(hazard.h_code) or
                    hazard.h_code not in KNOWN_H_CODES or not hazard.category):
                _issue(issues, "UNRECOGNISED_HAZARD", IssueSeverity.REVIEW, path,
                       "Class/category/H code requires CLP vocabulary verification")
            if hazard.status is not EvidenceStatus.VERIFIED:
                _issue(issues, "UNAPPROVED_CLASSIFICATION", IssueSeverity.REVIEW, path,
                       "Authoritative source classification not verified")
    ids: set[str] = set()
    lower_total = Decimal(0)
    upper_total = Decimal(0)
    all_bounded = True
    for i, component in enumerate(formulation.components):
        path = f"components[{i}]"
        if not component.line_id or component.line_id in ids:
            _issue(issues, "DUPLICATE_OR_MISSING_COMPONENT_ID", IssueSeverity.ERROR,
                   f"{path}.line_id", "Component line IDs must be unique and nonempty")
        ids.add(component.line_id)
        if not component.identity_id:
            _issue(issues, "UNKNOWN_COMPONENT_IDENTITY", IssueSeverity.REVIEW,
                   f"{path}.identity_id", "Do not resolve substances by name similarity")
        if component.kind is ComponentKind.MIM and (
            component.mim is None or
            not (component.mim.ufi or (component.mim.supplier_id and
                                     component.mim.supplier_product_id))
        ):
            _issue(issues, "INCOMPLETE_MIM", IssueSeverity.REVIEW,
                   f"{path}.mim", "MiM requires verifiable supplier identity / UFI")
        if component.technical_function == "PERFUME" and (
            component.perfume_role_evidence is None or
            component.perfume_role_evidence.status is not EvidenceStatus.VERIFIED
        ):
            _issue(issues, "UNVERIFIED_PERFUME", IssueSeverity.REVIEW, path,
                   "Perfume function needs approved evidence")
        if component.kind in (ComponentKind.APPROVED_GCI, ComponentKind.APPROVED_ICG) and (
            component.identity_evidence is None or
            component.identity_evidence.status is not EvidenceStatus.VERIFIED
        ):
            _issue(issues, "UNAPPROVED_REPRESENTATION", IssueSeverity.REVIEW, path,
                   "GCI/ICG claim not supported by approved evidence")
        for j, hazard in enumerate(component.classifications):
            if (hazard.hazard_class not in KNOWN_HAZARD_CLASSES or
                    hazard.h_code not in KNOWN_H_CODES or not hazard.category):
                _issue(issues, "UNRECOGNISED_HAZARD", IssueSeverity.REVIEW,
                       f"{path}.classifications[{j}]", "Verify component CLP designation")
        actual = component.actual
        if isinstance(actual, ConcentrationValue):
            low = high = actual.value
        elif isinstance(actual, ConcentrationInterval):
            low, high = actual.lower, actual.upper
        else:
            low = high = None
        for label, part in (("lower", low), ("upper", high)):
            if part is not None and (not part.is_finite() or part < 0 or part > 100):
                _issue(issues, "PERCENT_OUT_OF_RANGE", IssueSeverity.ERROR,
                       f"{path}.actual.{label}", "Percentage must be between 0 and 100")
        if low is not None and high is not None and low > high:
            _issue(issues, "INVALID_BOUNDS", IssueSeverity.ERROR,
                   f"{path}.actual", "Lower bound exceeds upper bound")
        if low is None or high is None:
            all_bounded = False
            _issue(issues, "UNKNOWN_CONCENTRATION", IssueSeverity.REVIEW,
                   f"{path}.actual", "Unknown actual concentration is not zero")
        else:
            lower_total += low
            upper_total += high
    if not formulation.components:
        _issue(issues, "EMPTY_COMPOSITION", IssueSeverity.REVIEW, "components",
               "No canonical components supplied")
    elif all_bounded and (lower_total > 100 + total_tolerance or
                          upper_total < 100 - total_tolerance):
        _issue(issues, "TOTAL_NOT_100", IssueSeverity.REVIEW, "components",
               f"Feasible total [{lower_total}, {upper_total}] excludes 100 ± {total_tolerance}"
               " percentage points")
    declared_ids: set[str] = set()
    for i, declared in enumerate(formulation.notified_components):
        if not declared.declaration_id or declared.declaration_id in declared_ids:
            _issue(issues, "DUPLICATE_OR_MISSING_DECLARATION_ID", IssueSeverity.ERROR,
                   f"notified_components[{i}].declaration_id", "Declaration IDs must be unique")
        declared_ids.add(declared.declaration_id)
    raw_ids: set[str] = set()
    for i, raw in enumerate(formulation.raw_bom):
        if not raw.source_line_id or raw.source_line_id in raw_ids:
            _issue(issues, "DUPLICATE_OR_MISSING_RAW_ID", IssueSeverity.ERROR,
                   f"raw_bom[{i}].source_line_id", "Source line IDs must be unique")
        raw_ids.add(raw.source_line_id)
    return tuple(issues)


def validate_portfolio(formulations: Sequence[Formulation]) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    for i, formulation in enumerate(formulations):
        if formulation.revision_id in seen:
            _issue(issues, "DUPLICATE_FORMULATION_REVISION", IssueSeverity.ERROR,
                   f"formulations[{i}]", "Same formulation ID and revision appears twice")
        seen.add(formulation.revision_id)
    return tuple(issues)


def parse_formulation(payload: Mapping[str, Any],
                      *, total_tolerance: Decimal = DEFAULT_TOTAL_TOLERANCE) -> ParseResult:
    """Safe JSON boundary. Invalid input yields issues, not partially trusted chemistry."""
    issues: list[ValidationIssue] = []
    components = tuple(_component(row, f"components[{i}]", issues)
                       for i, row in enumerate(_records(payload.get("components"), issues,
                                                        "components")))
    classifications = tuple(_classification(row,
                                             f"approved_health_physical_classification[{i}]",
                                             issues)
                            for i, row in enumerate(_records(
                                payload.get("approved_health_physical_classification"), issues,
                                "approved_health_physical_classification")))
    environment = tuple(_classification(row, f"approved_environment_classification[{i}]", issues)
                        for i, row in enumerate(_records(
                            payload.get("approved_environment_classification"), issues,
                            "approved_environment_classification")))
    raw: list[RawBOMLine] = []
    for i, row in enumerate(_records(payload.get("raw_bom"), issues, "raw_bom")):
        path = f"raw_bom[{i}]"
        source_fields = row.get("fields", {})
        if not isinstance(source_fields, Mapping) or any(
            not isinstance(k, str) or (v is not None and not isinstance(v, str))
            for k, v in source_fields.items()
        ):
            _issue(issues, "INVALID_RAW_FIELDS", IssueSeverity.ERROR, f"{path}.fields",
                   "Raw fields must map text keys to unchanged text or null")
            source_fields = {}
        raw.append(RawBOMLine(
            source_line_id=_text(row.get("source_line_id"), issues,
                                 f"{path}.source_line_id", required=True) or "",
            source_document_id=_text(row.get("source_document_id"), issues,
                                     f"{path}.source_document_id", required=True) or "",
            fields=tuple(source_fields.items()),
        ))
    notified: list[NotifiedComponent] = []
    for i, row in enumerate(_records(payload.get("notified_components"), issues,
                                     "notified_components")):
        path = f"notified_components[{i}]"
        concentration, problems = parse_concentration(row.get("concentration"),
                                                      f"{path}.concentration")
        issues.extend(problems)
        notified.append(NotifiedComponent(
            declaration_id=_text(row.get("declaration_id"), issues,
                                 f"{path}.declaration_id", required=True) or "",
            declared_identity_id=_text(row.get("declared_identity_id"), issues,
                                       f"{path}.declared_identity_id"),
            concentration=concentration,
            source_component_line_ids=_string_tuple(row.get("source_component_line_ids"), issues,
                                                    f"{path}.source_component_line_ids"),
            declaration_exemption_code=_text(row.get("declaration_exemption_code"), issues,
                                             f"{path}.declaration_exemption_code"),
            evidence_ids=_string_tuple(row.get("evidence_ids"), issues,
                                       f"{path}.evidence_ids"),
        ))
    sources = tuple(SourceReference(
        document_id=_text(row.get("document_id"), issues,
                          f"source_references[{i}].document_id", required=True) or "",
        location=_text(row.get("location"), issues, f"source_references[{i}].location"),
        revision=_text(row.get("revision"), issues, f"source_references[{i}].revision"),
    ) for i, row in enumerate(_records(payload.get("source_references"), issues,
                                      "source_references")))
    basis = payload.get("composition_basis")
    if basis is None:
        parsed_basis = None
    else:
        try:
            parsed_basis = PercentageBasis(basis)
        except (ValueError, TypeError):
            _issue(issues, "UNKNOWN_BASIS", IssueSeverity.REVIEW, "composition_basis",
                   "Unrecognised concentration basis; cannot convert without evidence")
            parsed_basis = None
    formulation = Formulation(
        formulation_id=_text(payload.get("formulation_id"), issues,
                             "formulation_id", required=True) or "",
        revision=_text(payload.get("revision"), issues, "revision", required=True) or "",
        legal_submitter_id=_text(payload.get("legal_submitter_id"), issues,
                                 "legal_submitter_id"),
        notification_mode=_enum(payload.get("notification_mode", "UNKNOWN"),
                                NotificationMode, NotificationMode.UNKNOWN,
                                issues, "notification_mode"),
        composition_basis=parsed_basis, components=components,
        approved_health_physical_classification=classifications,
        approved_environment_classification=environment,
        notified_components=tuple(notified), raw_bom=tuple(raw), source_references=sources,
        product_names=_string_tuple(payload.get("product_names"), issues, "product_names"),
        market_countries=_string_tuple(payload.get("market_countries"), issues,
                                       "market_countries"),
        use_types=_string_tuple(payload.get("use_types"), issues, "use_types"),
        eupcs_codes=_string_tuple(payload.get("eupcs_codes"), issues, "eupcs_codes"),
        ufis=_string_tuple(payload.get("ufis"), issues, "ufis"),
        physical_state=_text(payload.get("physical_state"), issues, "physical_state"),
        colour=_text(payload.get("colour"), issues, "colour"),
        ph=_text(payload.get("ph"), issues, "ph"),
        packaging=_string_tuple(payload.get("packaging"), issues, "packaging"),
        sds_section_11=_text(payload.get("sds_section_11"), issues, "sds_section_11"),
        confidence=_enum(payload.get("confidence", "UNKNOWN"), EvidenceStatus,
                         EvidenceStatus.UNKNOWN, issues, "confidence"),
    )
    issues.extend(validate_formulation(formulation, total_tolerance=total_tolerance))
    if any(item.severity is IssueSeverity.ERROR for item in issues):
        return ParseResult(None, tuple(issues))
    return ParseResult(formulation, tuple(issues))
