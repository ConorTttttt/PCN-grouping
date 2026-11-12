"""D-owned evidence sidecars for the immutable Agent B schema.

Evidence is supplied by a responsible reviewer, never created by this module.
Identifiers and revision scopes are exact, case-sensitive registry values.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pcn_grouping.models import (
    CLPClassification,
    ComponentKind,
    Evidence,
    RuleResult,
    RulesetVersion,
    RuleStatus,
)

Revision = tuple[str, str]
LineRef = tuple[str, str, str]
IdentityKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class IdentityRecord:
    identity_id: str
    kind: ComponentKind
    identifier_scheme: str
    identifier: str
    evidence: Evidence | None = None
    supplier_id: str | None = None
    supplier_product_id: str | None = None


@dataclass(frozen=True, slots=True)
class IdentityAlias:
    """An explicit one-hop registry mapping; no names/synonyms are inferred."""

    input_id: str
    canonical_id: str
    kind: ComponentKind
    evidence: Evidence | None = None
    supplier_id: str | None = None


@dataclass(frozen=True, slots=True)
class MiMRouteEvidence:
    route: Literal["UFI_PRIOR", "UFI_SDS", "NO_UFI_SDS", "FULL_COMPOSITION"]
    evidence: Evidence | None = None
    ufi_validation: Evidence | None = None
    prior_recipients: tuple[tuple[str, Evidence], ...] = ()
    sds_composition: Evidence | None = None
    other_known_components: Evidence | None = None
    supplier_contact: Evidence | None = None
    supplier_name: str | None = None
    supplier_email: str | None = None
    supplier_phone: str | None = None


@dataclass(frozen=True, slots=True)
class LineEvidence:
    line: LineRef
    classification_complete: Evidence | None = None
    function: Evidence | None = None
    exclusive_function: bool | None = None
    mim: MiMRouteEvidence | None = None
    notification_required: bool | None = None
    notification_evidence: Evidence | None = None


@dataclass(frozen=True, slots=True)
class RepresentationApproval:
    """Review of an existing representation, scoped to revisions and rule bytes.

    An APPROVED_* ComponentKind or a declaration label alone grants nothing.
    ICG criteria attest to prior expert validation; no new ICG is approved here.
    """

    declared_identity_id: str
    kind: Literal["GCI", "ICG"]
    member_identity_ids: tuple[str, ...]
    revisions: tuple[Revision, ...]
    ruleset_sha256: str
    evidence: Evidence | None = None
    function: Literal["PERFUME", "COLOURANT"] | None = None
    pre_existing: bool = False
    icg_pathway: Literal["GENERAL", "ALTERNATIVE"] | None = None
    criteria: tuple[tuple[str, Evidence], ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceCatalog:
    identities: tuple[IdentityRecord, ...] = ()
    aliases: tuple[IdentityAlias, ...] = ()
    lines: tuple[LineEvidence, ...] = ()
    representations: tuple[RepresentationApproval, ...] = ()


@dataclass(frozen=True, slots=True)
class Bounds:
    lower: Decimal | None
    upper: Decimal | None

    @property
    def exact(self) -> Decimal | None:
        return self.lower if self.lower == self.upper else None


@dataclass(frozen=True, slots=True)
class ComponentRow:
    line: LineRef
    raw_identity_key: IdentityKey | None
    notified_identity_key: IdentityKey | None
    actual: Bounds
    source_line_ids: tuple[str, ...]
    source_document_ids: tuple[str, ...]
    classifications: tuple[CLPClassification, ...]
    perfume_verified: bool
    identity_verified: bool
    declared_concentration_omitted: bool
    declaration_id: str | None
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PerfumeTotal:
    revision: Revision
    line_ids: tuple[str, ...]
    actual: Bounds
    membership_verified: bool


@dataclass(frozen=True, slots=True)
class ComponentAnalysis:
    """Component-only result. PASS never certifies whole-group eligibility."""

    status: RuleStatus
    disclosure_status: RuleStatus
    ruleset: RulesetVersion
    common_raw_keys: tuple[IdentityKey, ...]
    varying_raw_keys: tuple[IdentityKey, ...]
    common_notified_keys: tuple[IdentityKey, ...]
    varying_notified_keys: tuple[IdentityKey, ...]
    matrix: tuple[ComponentRow, ...]
    varying_perfume_totals: tuple[PerfumeTotal, ...]
    rule_results: tuple[RuleResult, ...]
