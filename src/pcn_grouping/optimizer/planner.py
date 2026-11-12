"""Deterministic, conservative greedy portfolio grouping.

The injected whole-group evaluator is the sole eligibility authority. No
regulatory thresholds or chemical identity assumptions exist in this module.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from decimal import Decimal
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
    """Auditable, non-optimal grouping proposal; NOT a PCN submission decision."""

    groups: tuple[tuple[T, ...], ...]
    singletons: tuple[T, ...]
    unresolved: tuple[ReviewItem[T], ...]
    trials: tuple[Trial, ...]
    singleton_reasons: tuple[ReviewItem[T], ...] = ()
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
    """Agent B uses formulation_id; legacy adapters sometimes supply id."""
    canonical_id = _field(formulation, "formulation_id")
    old_id = _field(formulation, "id")
    if canonical_id is not None and old_id is not None and canonical_id != old_id:
        return None
    form_id = canonical_id if canonical_id is not None else old_id
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
    """Stable record sorting only; NOT chemical alias/classification inference."""
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite decimal in record")
        return str(value)
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(asdict(value))
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("Canonical record keys must be strings")
        return {k: _canonical_value(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_canonical_value(v) for v in value]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    raise ValueError(f"Unsupported input type: {type(value).__name__}")


def _verified_evidence(evidence: object) -> bool:
    """Mirror E/D proof prerequisites, without manufacturing attestations."""
    status = _field(evidence, "status")
    if isinstance(status, Enum):
        status = status.value
    sources = _field(evidence, "source_document_ids")
    return bool(
        status == "VERIFIED"
        and isinstance(_field(evidence, "evidence_id"), str)
        and _field(evidence, "evidence_id").strip()
        and isinstance(sources, (list, tuple))
        and sources
        and all(isinstance(x, str) and x.strip() for x in sources)
        and isinstance(_field(evidence, "verified_by"), str)
        and _field(evidence, "verified_by").strip()
        and isinstance(_field(evidence, "verified_at"), str)
        and _field(evidence, "verified_at").strip()
    )


def _approved_signature(formulation: object, context: object) -> str | None:
    """Use E's reviewed-completeness records when canonical B models are passed."""
    classes = _field(formulation, "approved_health_physical_classification")
    if not isinstance(classes, (tuple, list, set, frozenset)) or not classes:
        return None
    # An explicit legacy flag is kept ONLY for adapters supplying test doubles.
    legacy_approved = _field(formulation, "classification_approved") is True
    if _field(formulation, "classification_approved") is False:
        return None
    ident = _identifier(formulation)
    records = _field(context, "classifications")
    matches = (
        [a for a in records if _field(a, "revision") == ident]
        if isinstance(records, (list, tuple)) and ident is not None else []
    )
    complete = len(matches) == 1 and _verified_evidence(_field(matches[0], "complete"))
    if not (complete or legacy_approved):
        return None
    signature: list[tuple[str, str, str, str, str]] = []
    for item in classes:
        if isinstance(item, str):
            if not legacy_approved or not item.strip():
                return None
            signature.append(("LEGACY_TEST_CLASSIFICATION", item, "", "", ""))
            continue
        parts = tuple(_field(item, key) for key in
                      ("hazard_class", "category", "h_code", "route", "qualifier"))
        status = _field(item, "status")
        if isinstance(status, Enum):
            status = status.value
        sources = _field(item, "source_document_ids")
        if (status != "VERIFIED" or not isinstance(sources, (tuple, list))
                or not sources or not all(isinstance(s, str) and s.strip() for s in sources)
                or not all(isinstance(s, str) and s.strip() for s in parts[:3])
                or any(s is not None and not isinstance(s, str) for s in parts[3:])):
            return None
        signature.append(tuple(part or "" for part in parts))  # type: ignore[arg-type]
    return json.dumps(sorted(signature), separators=(",", ":"), ensure_ascii=True)


def _prefilter_key(formulation: object, context: object) -> tuple[str, str, str] | None:
    submitter = _field(formulation, "legal_submitter_id")
    mode = _field(formulation, "notification_mode")
    if isinstance(mode, Enum):
        mode = mode.value
    if not isinstance(submitter, str) or not submitter.strip() or mode != "STANDARD_FULL":
        return None
    signature = _approved_signature(formulation, context)
    if signature is None:
        return None
    return submitter, mode, signature


def _result(decision: object) -> tuple[str, str]:
    status = _field(decision, "status")
    reason = _field(decision, "reason")
    if isinstance(status, Enum):
        status = status.value
    if status not in {"ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED"}:
        return "REVIEW_REQUIRED", "Evaluator returned unsupported or missing group status"
    if not isinstance(reason, str):
        reason = ""
    if not reason:
        reasons: list[str] = []
        rules = _field(decision, "rule_results")
        if isinstance(rules, (tuple, list)):
            for rule in rules:
                state = _field(rule, "status")
                if isinstance(state, Enum):
                    state = state.value
                if state not in {"FAIL", "REVIEW"}:
                    continue
                code = _field(rule, "rule_id")
                values = _field(rule, "values")
                if isinstance(values, (tuple, list)):
                    detail = dict(v for v in values if isinstance(v, tuple) and len(v) == 2).get("code")
                    if isinstance(detail, str):
                        code = f"{code}:{detail}"
                if isinstance(code, str):
                    reasons.append(code)
        reason = "; ".join(sorted(set(reasons)))
    return status, reason


def _evaluate(members: Sequence[T], context: object,
              evaluator: GroupEvaluator[T]) -> tuple[str, str]:
    try:
        return _result(evaluator(list(members), context))
    except Exception as exc:
        return "REVIEW_REQUIRED", f"Evaluator error: {type(exc).__name__}"


def _stable_record(value: object) -> str:
    try:
        return json.dumps(_canonical_value(value), sort_keys=True,
                          separators=(",", ":"), ensure_ascii=True)
    except (ValueError, TypeError):
        return f"<{type(value).__module__}.{type(value).__qualname__}>"


def optimise_portfolio(formulations: Sequence[T], ruleset: object,
                       evaluate_group: GroupEvaluator[T]) -> PortfolioPlan[T]:
    """Deterministic greedy grouping. globally_optimal is *always* False.

    Only final full-group ELIGIBLE decisions make groups. REVIEW and failures
    are exposed, not silently converted to approvals. Input is never mutated.
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
            unresolved.append(ReviewItem(item, "DUPLICATE_REVISION", "Duplicate ID/revision"))
            continue
        key = _prefilter_key(item, ruleset)
        if key is None:
            unresolved.append(ReviewItem(
                item, "PREFILTER_EVIDENCE_MISSING",
                "Verified submitter, STANDARD_FULL mode, reviewed completeness and "
                "verified health/physical CLP signature required",
            ))
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
            final_status, reason = _evaluate(current, ruleset, evaluate_group)
            trials.append(Trial(tuple(_display_key(m) for m in current),
                                final_status, reason, True))
            if final_status == "ELIGIBLE":
                groups.append(tuple(current))
            else:
                for item in current:
                    unresolved.append(ReviewItem(
                        item, "POST_VALIDATION_NOT_ELIGIBLE",
                        f"Final whole-group status: {final_status}; {reason}",
                    ))
    groups.sort(key=lambda group: tuple(_display_key(f) for f in group))
    singletons.sort(key=_display_key)
    unresolved.sort(key=lambda item: (_display_key(item.formulation),
                                      item.code, _stable_record(item.formulation)))
    singleton_reasons: list[ReviewItem[T]] = []
    for item in singletons:
        relevant = [t for t in trials if not t.post_validation and
                    _display_key(item) in t.members]
        if not relevant:
            singleton_reasons.append(ReviewItem(
                item, "NO_PREFILTER_MATCH",
                "No other formulation shares the verified submitter, regime and CLP signature",
            ))
        elif any(t.status == "REVIEW_REQUIRED" for t in relevant):
            singleton_reasons.append(ReviewItem(
                item, "CANDIDATE_REQUIRES_REVIEW",
                "; ".join(sorted({t.reason or "Evaluator requires review"
                                  for t in relevant if t.status == "REVIEW_REQUIRED"})),
            ))
        else:
            singleton_reasons.append(ReviewItem(
                item, "NO_ELIGIBLE_COMBINATION",
                "; ".join(sorted({t.reason or t.status for t in relevant})),
            ))
    return PortfolioPlan(
        groups=tuple(groups), singletons=tuple(singletons),
        unresolved=tuple(unresolved), trials=tuple(trials),
        singleton_reasons=tuple(singleton_reasons),
    )


optimize_portfolio = optimise_portfolio
