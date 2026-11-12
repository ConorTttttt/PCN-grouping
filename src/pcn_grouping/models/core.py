"""Versioned, immutable input and decision contracts, not legal rule implementations."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class PercentageBasis(str, Enum):
    MASS_PERCENT = "MASS_PERCENT"
    VOLUME_PERCENT = "VOLUME_PERCENT"


class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"


class ComponentKind(str, Enum):
    SUBSTANCE = "SUBSTANCE"
    MIM = "MIM"
    APPROVED_GCI = "APPROVED_GCI"
    APPROVED_ICG = "APPROVED_ICG"


class NotificationMode(str, Enum):
    STANDARD_FULL = "STANDARD_FULL"
    INDUSTRIAL_LIMITED = "INDUSTRIAL_LIMITED"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class GroupStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass(frozen=True, slots=True)
class ConcentrationValue:
    """Known exact actual percentage; None is unknown, not zero."""

    value: Decimal | None

    def __post_init__(self) -> None:
        if self.value is not None and type(self.value) is not Decimal:
            raise TypeError("concentration requires Decimal or None; never binary float")


@dataclass(frozen=True, slots=True)
class ConcentrationInterval:
    """Inclusive actual percentage bounds; None indicates an unknown endpoint."""

    lower: Decimal | None
    upper: Decimal | None

    def __post_init__(self) -> None:
        if any(x is not None and type(x) is not Decimal for x in (self.lower, self.upper)):
            raise TypeError("concentration bounds require Decimal or None")


ActualConcentration = ConcentrationValue | ConcentrationInterval


@dataclass(frozen=True, slots=True)
class SourceReference:
    document_id: str
    location: str | None = None  # source tab/row/page, not an adapter-specific field
    revision: str | None = None


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    status: EvidenceStatus = EvidenceStatus.UNKNOWN
    source_document_ids: tuple[str, ...] = ()
    verified_by: str | None = None
    verified_at: str | None = None  # ISO timestamp supplied by source; no implicit clock
    note: str | None = None


@dataclass(frozen=True, slots=True)
class MiMIdentifiers:
    supplier_id: str | None = None
    supplier_product_id: str | None = None
    ufi: str | None = None
    sds_document_id: str | None = None
    composition_known: bool | None = None


@dataclass(frozen=True, slots=True)
class CLPClassification:
    hazard_class: str
    category: str
    h_code: str
    route: str | None = None
    qualifier: str | None = None
    status: EvidenceStatus = EvidenceStatus.UNKNOWN
    source_document_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RawBOMLine:
    """Unmodified source fields; keep order and text (including blanks)."""

    source_line_id: str
    source_document_id: str
    fields: tuple[tuple[str, str | None], ...] = ()


@dataclass(frozen=True, slots=True)
class Component:
    """Normalized actual ingredient record; source BOM is never overwritten."""

    line_id: str
    identity_id: str | None
    kind: ComponentKind
    actual: ActualConcentration | None
    source_line_ids: tuple[str, ...] = ()
    source_document_ids: tuple[str, ...] = ()
    classifications: tuple[CLPClassification, ...] = ()
    identity_evidence: Evidence | None = None
    mim: MiMIdentifiers | None = None
    technical_function: str | None = None
    perfume_role_evidence: Evidence | None = None
    confidence: EvidenceStatus = EvidenceStatus.UNKNOWN


@dataclass(frozen=True, slots=True)
class NotifiedComponent:
    """Separate *proposed* notified view; its legality is checked elsewhere."""

    declaration_id: str
    declared_identity_id: str | None
    concentration: ActualConcentration | None
    source_component_line_ids: tuple[str, ...] = ()
    declaration_exemption_code: str | None = None
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Formulation:
    formulation_id: str
    revision: str
    legal_submitter_id: str | None
    notification_mode: NotificationMode
    composition_basis: PercentageBasis | None
    components: tuple[Component, ...]
    approved_health_physical_classification: tuple[CLPClassification, ...] = ()
    approved_environment_classification: tuple[CLPClassification, ...] = ()
    notified_components: tuple[NotifiedComponent, ...] = ()
    raw_bom: tuple[RawBOMLine, ...] = ()
    source_references: tuple[SourceReference, ...] = ()
    product_names: tuple[str, ...] = ()
    market_countries: tuple[str, ...] = ()
    use_types: tuple[str, ...] = ()
    eupcs_codes: tuple[str, ...] = ()
    ufis: tuple[str, ...] = ()
    physical_state: str | None = None
    colour: str | None = None
    ph: str | None = None  # source decimal text until evidence / unit contract agreed
    packaging: tuple[str, ...] = ()
    sds_section_11: str | None = None
    confidence: EvidenceStatus = EvidenceStatus.UNKNOWN

    @property
    def revision_id(self) -> str:
        return f"{self.formulation_id}@{self.revision}"


@dataclass(frozen=True, slots=True)
class RulesetVersion:
    ruleset_id: str
    effective_date: str
    sha256: str
    status: str  # draft is not regulatory approval


@dataclass(frozen=True, slots=True)
class RuleResult:
    rule_id: str
    status: RuleStatus
    explanation: str
    evidence_ids: tuple[str, ...] = ()
    source_sections: tuple[str, ...] = ()
    values: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class GroupDecision:
    status: GroupStatus
    formulation_revision_ids: tuple[str, ...]
    ruleset: RulesetVersion
    canonical_input_hash: str
    rule_results: tuple[RuleResult, ...] = field(default_factory=tuple)
    # Reviewer decisions and event timestamps belong to the audit workflow.
