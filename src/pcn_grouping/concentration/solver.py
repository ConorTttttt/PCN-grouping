"""Deterministic common-component declaration solver (Annex VIII B.3.4).

Inputs are exact Decimal percentages, Decimal text, (lower, upper) pairs,
or Agent B's ConcentrationValue/ConcentrationInterval objects. An interval
means *uncertainty about the actual value*, not a legally declared interval.
Closed actual bounds are mandatory. Binary floats are NEVER accepted.

The version-controlled rulebook supplies widths and endpoint semantics;
research-draft rulesets must never produce PASS/FAIL regulatory decisions.
The independent whole-formulation evaluator owns hazard classification,
component identities, percentage basis and rulebook-approval verification.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

_DECIMAL_TEXT = re.compile(r"(?:0|[0-9]+)(?:\.[0-9]+)?\Z")
_ALLOWED_CLASSES = {"major_concern": "REG-MAJOR-BAND", "other": "REG-OTHER-BAND"}
_APPROVED_STATUSES = frozenset({"APPROVED", "REGULATORY_APPROVED"})


@dataclass(frozen=True, slots=True)
class ConcentrationDeclaration:
    lower: Decimal
    upper: Decimal
    exact: bool


@dataclass(frozen=True, slots=True)
class ZoneCheck:
    """An intersected statutory band and its permitted percentage-point width."""

    lower: Decimal
    upper: Decimal
    lower_inclusive: bool
    upper_inclusive: bool
    maximum_width: Decimal
    candidate_width: Decimal
    within_limit: bool

    @property
    def label(self) -> str:
        left = "[" if self.lower_inclusive else "("
        right = "]" if self.upper_inclusive else ")"
        return f"{left}{self.lower},{self.upper}{right}"


@dataclass(frozen=True, slots=True)
class DeclarationDecision:
    status: str  # PASS | FAIL | REVIEW: numerical component-level status only
    declaration: ConcentrationDeclaration | None
    candidate: ConcentrationDeclaration | None
    applied_zones: tuple[ZoneCheck, ...]
    reason_codes: tuple[str, ...]
    evidence: tuple[str, ...]
    ruleset_id: str | None
    rule_id: str | None


@dataclass(frozen=True, slots=True)
class _Zone:
    lower: Decimal
    upper: Decimal
    lower_inclusive: bool
    upper_inclusive: bool
    maximum_width: Decimal

    def intersects(self, low: Decimal, high: Decimal) -> bool:
        return (high >= self.lower if self.lower_inclusive else high > self.lower) and (
            low <= self.upper if self.upper_inclusive else low < self.upper
        )


def _decimal(raw: Any) -> Decimal | None:
    if type(raw) is Decimal:
        return raw if raw.is_finite() else None
    if isinstance(raw, str) and _DECIMAL_TEXT.fullmatch(raw):
        value = Decimal(raw)
        return value if value.is_finite() else None
    return None


def _actual_interval(raw: Any) -> tuple[Decimal, Decimal] | None:
    """Duck-types Agent B's immutable models, without importing an unmerged PR."""
    if raw is None:
        return None
    if type(raw) is Decimal or isinstance(raw, str):
        val = _decimal(raw)
        return (val, val) if val is not None else None
    if hasattr(raw, "value"):
        val = _decimal(raw.value)
        return (val, val) if val is not None else None
    if hasattr(raw, "lower") and hasattr(raw, "upper"):
        low, high = _decimal(raw.lower), _decimal(raw.upper)
    elif isinstance(raw, (tuple, list)) and len(raw) == 2:
        low, high = _decimal(raw[0]), _decimal(raw[1])
    else:
        return None
    return (low, high) if low is not None and high is not None else None


def _exact_width(low: Decimal, high: Decimal) -> Decimal:
    """Decimal subtraction using integer coefficients; ignores ambient precision.

    decimal.Decimal arithmetic ordinarily rounds to the active context.
    E.g. subtracting 1e-100 from 1 with default precision silently rounds.
    Construct a Decimal tuple instead, preserving every supplied decimal place.
    """
    scale = max(0, -low.as_tuple().exponent, -high.as_tuple().exponent)

    def integer_at_scale(value: Decimal) -> int:
        parts = value.as_tuple()
        coefficient = 0
        for digit in parts.digits:
            coefficient = coefficient * 10 + digit
        return (-1 if parts.sign else 1) * coefficient * 10 ** (parts.exponent + scale)

    diff = integer_at_scale(high) - integer_at_scale(low)
    if diff < 0:
        raise ValueError("range endpoints are reversed")
    digits = tuple(int(char) for char in str(diff))
    return Decimal((0, digits, -scale))


def _zones(ruleset: Mapping[str, Any], component_class: str) -> tuple[_Zone, ...] | None:
    table = ruleset.get("maximum_concentration_range_width_percentage_points")
    rows = table.get(component_class) if isinstance(table, Mapping) else None
    if not isinstance(rows, (list, tuple)) or not rows:
        return None
    zones: list[_Zone] = []
    for row in rows:
        if not isinstance(row, Mapping):
            return None
        keys = set(row)
        if not ({"max_width"} <= keys and len(keys & {"min_inclusive", "min_exclusive"}) == 1
                and len(keys & {"max_inclusive", "max_exclusive"}) == 1):
            return None
        lower_inclusive = "min_inclusive" in row
        upper_inclusive = "max_inclusive" in row
        low = _decimal(row["min_inclusive"] if lower_inclusive else row["min_exclusive"])
        high = _decimal(row["max_inclusive"] if upper_inclusive else row["max_exclusive"])
        width = _decimal(row["max_width"])
        if low is None or high is None or width is None or not (0 <= low < high <= 100 and width > 0):
            return None
        zones.append(_Zone(low, high, lower_inclusive, upper_inclusive, width))
    zones.sort(key=lambda z: z.lower)
    # Complete, non-overlapping partition of the positive <100 domain.
    if zones[0].lower != 0 or zones[0].lower_inclusive:
        return None
    if zones[-1].upper != 100 or zones[-1].upper_inclusive:
        return None
    for before, after in zip(zones, zones[1:]):
        if before.upper != after.lower or before.upper_inclusive == after.lower_inclusive:
            return None
    return tuple(zones)


def _zone_checks(low: Decimal, high: Decimal, zones: tuple[_Zone, ...]) -> tuple[ZoneCheck, ...]:
    width = _exact_width(low, high)
    return tuple(
        ZoneCheck(z.lower, z.upper, z.lower_inclusive, z.upper_inclusive,
                  z.maximum_width, width, width <= z.maximum_width)
        for z in zones if z.intersects(low, high)
    )


def find_common_declaration(
    member_intervals: Sequence[Any], component_class: str, ruleset: Mapping[str, Any]
) -> DeclarationDecision:
    """Return a minimal valid common declaration, or structured FAIL/REVIEW.

    'ruleset' is the full versioned ruleset JSON mapping, **not** Agent B's
    metadata-only RulesetVersion. Only independently regulatory-approved
    rulebook statuses may return numerical PASS/FAIL. A repository research
    draft returns REVIEW. Treat a PASS as *one component's numerical check*,
    never as PCN grouping eligibility or a legal approval.

    Bounded uncertain inputs: if their *entire hull* is legal, PASS. If even
    the narrowest achievable span between one actual per member is illegal,
    FAIL. Otherwise REVIEW (an exact value may change the answer).
    """
    rule_id = _ALLOWED_CLASSES.get(component_class) if isinstance(component_class, str) else None
    ruleset_id = ruleset.get("ruleset_id") if isinstance(ruleset, Mapping) else None

    def decision(status: str, code: str, evidence: tuple[str, ...] = (),
                 candidate: ConcentrationDeclaration | None = None,
                 checks: tuple[ZoneCheck, ...] = (),
                 declaration: ConcentrationDeclaration | None = None) -> DeclarationDecision:
        return DeclarationDecision(status, declaration, candidate, checks, (code,), evidence,
                                   ruleset_id if isinstance(ruleset_id, str) else None, rule_id)

    if rule_id is None:
        return decision("REVIEW", "UNKNOWN_COMPONENT_CLASS")
    if not isinstance(ruleset, Mapping) or not isinstance(ruleset_id, str) or not ruleset_id:
        return decision("REVIEW", "MISSING_RULESET")
    if not isinstance(member_intervals, (tuple, list)) or not member_intervals:
        return decision("REVIEW", "MISSING_ACTUAL_CONCENTRATION")
    values = tuple(_actual_interval(item) for item in member_intervals)
    if any(value is None for value in values):
        return decision("REVIEW", "MISSING_OR_INVALID_CONCENTRATION")
    intervals = tuple(value for value in values if value is not None)
    if any(low < 0 or high > 100 or low > high for low, high in intervals):
        return decision("REVIEW", "INVALID_ACTUAL_BOUNDS")
    if any(low == 0 or high == 100 for low, high in intervals):
        return decision("REVIEW", "ZERO_OR_100_ENDPOINT_REQUIRES_REVIEW")
    zones = _zones(ruleset, component_class)
    if zones is None:
        return decision("REVIEW", "INVALID_OR_MISSING_BAND_RULES")
    if ruleset.get("status") not in _APPROVED_STATUSES:
        return decision("REVIEW", "RULESET_NOT_REGULATORY_APPROVED",
                        (f"ruleset_id={ruleset_id}", f"status={ruleset.get('status')!s}"))

    low = min(value[0] for value in intervals)
    high = max(value[1] for value in intervals)
    candidate = ConcentrationDeclaration(low, high, low == high)
    checks = _zone_checks(low, high, zones)
    evidence = (f"required_actual_hull=[{low},{high}]",
                f"required_width_percentage_points={_exact_width(low, high)}",
                f"rule_id={rule_id}",
                *(f"zone={check.label} max_width_percentage_points={check.maximum_width} "
                  f"width={check.candidate_width} result={'PASS' if check.within_limit else 'FAIL'}"
                  for check in checks))
    if checks and all(check.within_limit for check in checks):
        return decision("PASS", "COMMON_DECLARATION_FEASIBLE", evidence, candidate, checks, candidate)

    # For bounded uncertainty, a failing hull is not automatically a
    # conclusive violation. A possible realization can be narrower.
    possible_low = min(value[1] for value in intervals)
    possible_high = max(value[0] for value in intervals)
    if possible_high <= possible_low:
        # Intervals overlap: an equal actual is possible for all members.
        # The union is nevertheless too wide to certify the declaration.
        return decision("REVIEW", "UNCERTAINTY_STRADDLES_BAND_LIMIT", evidence,
                        candidate, checks)
    possible_checks = _zone_checks(possible_low, possible_high, zones)
    possible_evidence = evidence + (
        f"narrowest_possible_actual_span=[{possible_low},{possible_high}]",
        f"narrowest_possible_width_percentage_points={_exact_width(possible_low, possible_high)}",
    )
    if possible_checks and all(c.within_limit for c in possible_checks):
        return decision("REVIEW", "UNCERTAINTY_STRADDLES_BAND_LIMIT", possible_evidence,
                        candidate, checks)
    return decision("FAIL", "COMMON_RANGE_EXCEEDS_BAND_WIDTH", possible_evidence,
                    candidate, checks)
