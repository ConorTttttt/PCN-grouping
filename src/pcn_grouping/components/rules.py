"""Version-pinned rule projection and context-independent decimal arithmetic."""

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal

from pcn_grouping.models import Evidence, EvidenceStatus, RulesetVersion

from .contracts import Bounds


def verified(evidence: Evidence | None) -> bool:
    return bool(
        evidence
        and evidence.status is EvidenceStatus.VERIFIED
        and evidence.evidence_id.strip()
        and evidence.source_document_ids
        and all(item.strip() for item in evidence.source_document_ids)
        and evidence.verified_by
        and evidence.verified_by.strip()
        and evidence.verified_at
        and evidence.verified_at.strip()
    )


def exact_sum(values: tuple[Decimal, ...]) -> Decimal:
    """Integer coefficients avoid Decimal context rounding (even at a 5% edge)."""
    if not values:
        return Decimal(0)
    if any(not value.is_finite() for value in values):
        raise ValueError("non-finite percentage")
    exponent = min(int(value.as_tuple().exponent) for value in values)
    coefficient = 0
    for value in values:
        sign, digits, exp = value.as_tuple()
        integer = 0
        for digit in digits:
            integer = integer * 10 + digit
        coefficient += (-1 if sign else 1) * integer * 10 ** (int(exp) - exponent)
    digits = tuple(int(char) for char in str(abs(coefficient)))
    return Decimal((int(coefficient < 0), digits, exponent))


def sum_bounds(values: tuple[Bounds, ...]) -> Bounds:
    def endpoint(upper: bool) -> Decimal | None:
        items = tuple(v.upper if upper else v.lower for v in values)
        if any(v is None for v in items):
            return None
        return exact_sum(tuple(v for v in items if v is not None))

    return Bounds(endpoint(False), endpoint(True))


@dataclass(frozen=True, slots=True)
class ComponentRules:
    version: RulesetVersion
    varying_perfume_cap: Decimal
    perfume_gci_cap: Decimal
    colourant_gci_cap: Decimal
    omission_categories: tuple[str, ...]
    approval: Evidence | None = None
    source_json: bytes = field(default=b"", repr=False)

    def __post_init__(self) -> None:
        for value in (self.varying_perfume_cap, self.perfume_gci_cap, self.colourant_gci_cap):
            if type(value) is not Decimal:
                raise TypeError("rule thresholds must be Decimal")
            if not value.is_finite() or not Decimal(0) <= value <= Decimal(100):
                raise ValueError("invalid rule threshold")
        if (
            not self.source_json
            or hashlib.sha256(self.source_json).hexdigest() != self.version.sha256
        ):
            raise ValueError("rules must retain matching source bytes and SHA-256")
        data = json.loads(self.source_json)
        expected = (
            Decimal(data["group_finished_mixture"]["maximum_differing_perfume_pct_per_mixture"]),
            Decimal(data["generic_component_identifiers"]["max_total_perfume_gci_pct"]),
            Decimal(data["generic_component_identifiers"]["max_total_colouring_agents_gci_pct"]),
            tuple(data["perfume_concentration_omission_in_group"]["if_not_classified_or_only"]),
            data["status"],
            data["ruleset_id"],
            data["legal_effective_consolidation"],
        )
        if expected != (
            self.varying_perfume_cap,
            self.perfume_gci_cap,
            self.colourant_gci_cap,
            self.omission_categories,
            self.version.status,
            self.version.ruleset_id,
            self.version.effective_date,
        ):
            raise ValueError("rule projection differs from its versioned source")

    @property
    def approved(self) -> bool:
        return (
            self.version.status == "APPROVED"
            and verified(self.approval)
            and bool(self.version.ruleset_id and self.version.effective_date)
            and len(self.version.sha256) == 64
            and all(c in "0123456789abcdef" for c in self.version.sha256)
        )

    @classmethod
    def from_json(cls, raw: bytes, approval: Evidence | None = None) -> "ComponentRules":
        """Read Agent A's rule format; preserve exact file SHA and draft status.

        No default thresholds, silent coercions, or automatic approval. The caller
        selects the effective version; future-date selection belongs to E/J.
        """

        def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate ruleset key: {key}")
                result[key] = value
            return result

        data = json.loads(raw, object_pairs_hook=unique)
        group = data["group_finished_mixture"]
        gci = data["generic_component_identifiers"]
        if not (
            group["different_components_must_be_verified_perfumes"] is True
            and gci["requires_exclusive_function"] is True
            and gci["prohibits_health_hazard_classification"] is True
        ):
            raise ValueError("unsupported component rule semantics")
        if set(gci["permitted"]) != {"perfumes", "colouring agents"}:
            raise ValueError("unsupported GCI identifiers")

        def number(value: object) -> Decimal:
            if not isinstance(value, str):
                raise TypeError("ruleset percentages must be decimal strings")
            return Decimal(value)

        return cls(
            RulesetVersion(
                data["ruleset_id"],
                data["legal_effective_consolidation"],
                hashlib.sha256(raw).hexdigest(),
                data["status"],
            ),
            number(group["maximum_differing_perfume_pct_per_mixture"]),
            number(gci["max_total_perfume_gci_pct"]),
            number(gci["max_total_colouring_agents_gci_pct"]),
            tuple(data["perfume_concentration_omission_in_group"]["if_not_classified_or_only"]),
            approval,
            raw,
        )
