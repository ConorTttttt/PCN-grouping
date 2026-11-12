"""Deterministic, conservative greedy portfolio grouping.

The eligibility evaluator is injected and remains the *sole* authority for a
whole group's regulatory eligibility. This planner contains no legal heuristics.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")
GroupEvaluator = Callable[[list[T], object], object]


@dataclass(frozen=True)
class ReviewItem(Generic[T]):
    formulation: T
    code: str
    explanation: str


@dataclass(frozen=True)
class Trial:
    members: tuple[str, ...]
    status: str
    reason: str
    post_validation: bool = False


@dataclass(frozen=True)
class PortfolioPlan(Generic[T]):
    """Immutable partition and an audit trail; never a regulatory sign-off."""

    groups: tuple[tuple[T, ...], ...]
    singletons: tuple[T, ...]
    unresolved: tuple[ReviewItem[T], ...]
    trials: tuple[Trial, ...]
    algorithm: str = "stable_greedy_v1"
    globally_optimal: bool = False

    @property
    def grouped_count(self) -> int:
        return sum(len(group) for group in self.groups)


def _field(source: object, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _identifier(formulation: object) -> tuple[str, str] | None:
    form_id = _field(formulation, "id")
    revision = _field(formulation, "revision")
    if not isinstance(form_id, str) or not form_id.strip():
        return None
    if not isinstance(revision, str) or not revision.strip():
        return None
    return form_id, revision


def _display_key(formulation: object) -> str:
    ident = _identifier(formulation)
    if ident is None:
        return "<missing-id-or-revision>"
    return json.dumps([ident[0], ident[1]], ensure_ascii=True, separators=(",", ":"))


def _canonical_value(value: Any) -> Any:
    """Canonical comparison only for verified CLP signatures, never guess aliases."""
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(asdict(value))
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return _canonical_value(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("CLP signature mapping keys must be strings")
        return {k: _canonical_value(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_canonical_value(v) for v in value]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    raise ValueError(f"Unsupported CLP signature value type: {type(value).__name__}")


def _prefilter_key(formulation: object) -> tuple[str, str, str] | None:
    submitter = _field(formulation, "legal_submitter_id")
    mode = _field(formulation, "notification_mode")
    classification = _field(formulation, "approved_health_physical_classification")
    if not isinstance(submitter, str) or not submitter.strip():
        return None
    if isinstance(mode, Enum):
        mode = mode.value
    # Phase 1 only supports standard full-composition notifications.
    if mode != "STANDARD_FULL":
        return None
    approved = _field(formulation, "classification_approved")
    if approved is False:
        return None
    # Nonempty and approved input is required; unknown versus an approved empty
    # health/physical signature cannot be distinguished by this draft interface.
    if not isinstance(classification, (list, tuple, frozenset, set)) or not classification:
        return None
    try:
        signature = _canonical_value(classification)
        canonical = json.dumps(signature, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError):
        return None
    return str(submitter), str(mode), canonical


def _result(decision: object) -> tuple[str, str]:
    if isinstance(decision, Mapping):
        status = decision.get("status")
        reason = decision.get("reason", "")
    else:
        status = getattr(decision, "status", None)
        reason = getattr(decision, "reason", "")
    if isinstance(status, Enum):
        status = status.value
    if not isinstance(status, str):
        return "REVIEW_REQUIRED", "Evaluator returned no recognized status"
    if status not in {"ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED"}:
        return "REVIEW_REQUIRED", f"Unsupported evaluator status {status!r}"
    return status, reason if isinstance(reason, str) else ""


def _evaluate(
    members: Sequence[T], ruleset: object, evaluator: GroupEvaluator[T]
) -> tuple[str, str]:
    try:
        return _result(evaluator(list(members), ruleset))
    except Exception as exc:
        # Never turn a missing/failed evaluator call into an eligible group.
        return "REVIEW_REQUIRED", f"Evaluator error: {type(exc).__name__}"


def optimise_portfolio(
    formulations: Sequence[T], ruleset: object, evaluate_group: GroupEvaluator[T]
) -> PortfolioPlan[T]:
    """Produce a reproducible *non-optimal* greedy partition.

    Only submitted, complete standard full-composition items sharing a verified
    submitter and health+physical CLP signature are candidate-matched. All
    additions and every proposed final multi-member group call the injected
    **whole-group** evaluator; environmental hazard, EuPCS, trade name, and
    market metadata are never used as rejection keys.

    An evaluator FAIL/REVIEW rejects that candidate; REVIEW remains visible
    in trials. Missing prefilter evidence stays unresolved. The algorithm does
    not claim the minimum possible number of group submissions.
    """
    entries = list(formulations)
    id_counts = Counter(_identifier(f) for f in entries if _identifier(f) is not None)
    eligible: list[tuple[tuple[str, str], tuple[str, str, str], T]] = []
    unresolved: list[ReviewItem[T]] = []
    for item in entries:
        ident = _identifier(item)
        if ident is None:
            unresolved.append(ReviewItem(item, "MISSING_ID", "Stable ID and revision required"))
            continue
        if id_counts[ident] > 1:
            unresolved.append(ReviewItem(item, "DUPLICATE_REVISION", "Duplicate formulation ID/revision"))
            continue
        key = _prefilter_key(item)
        if key is None:
            unresolved.append(
                ReviewItem(item, "PREFILTER_EVIDENCE_MISSING",
                           "Verified submitter, STANDARD_FULL mode and complete approved health/physical CLP signature required")
            )
            continue
        eligible.append((ident, key, item))
    eligible.sort(key=lambda row: row[0])
    blocks: dict[tuple[str, str, str], list[T]] = {}
    for _ident, key, item in eligible:
        blocks.setdefault(key, []).append(item)

    groups: list[tuple[T, ...]] = []
    singletons: list[T] = []
    trials: list[Trial] = []
    for block_key in sorted(blocks):
        available = blocks[block_key][:]
        while available:
            current: list[T] = [available.pop(0)]
            remaining: list[T] = []
            for candidate in available:
                proposal = current + [candidate]
                status, reason = _evaluate(proposal, ruleset, evaluate_group)
                trials.append(Trial(tuple(_display_key(m) for m in proposal), status, reason))
                if status == "ELIGIBLE":
                    current.append(candidate)
                else:
                    remaining.append(candidate)
            available = remaining
            if len(current) == 1:
                singletons.append(current[0])
                continue
            # A fresh check is essential: an earlier pair result, memoization,
            # or a hypothetical future group-building strategy cannot suffice.
            final_status, reason = _evaluate(current, ruleset, evaluate_group)
            trials.append(Trial(tuple(_display_key(m) for m in current), final_status, reason, True))
            if final_status == "ELIGIBLE":
                groups.append(tuple(current))
            else:
                for item in current:
                    unresolved.append(
                        ReviewItem(item, "POST_VALIDATION_NOT_ELIGIBLE",
                                   f"Final whole-group status: {final_status}; {reason}")
                    )
    groups.sort(key=lambda group: tuple(_display_key(f) for f in group))
    singletons.sort(key=_display_key)
    unresolved.sort(key=lambda item: (_display_key(item.formulation), item.code))
    return PortfolioPlan(
        groups=tuple(groups),
        singletons=tuple(singletons),
        unresolved=tuple(unresolved),
        trials=tuple(trials),
    )


# US spelling alias for downstream APIs.
optimize_portfolio = optimise_portfolio
