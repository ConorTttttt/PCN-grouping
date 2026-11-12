"""Single deterministic whole-group eligibility public API (issue #6)."""
from .engine import (
    ApplicabilityEvidence,
    CommonRange,
    EligibilityContext,
    EligibilityDecision,
    ReviewedClassification,
    evaluate_group,
)

__all__ = [
    "ApplicabilityEvidence",
    "CommonRange",
    "EligibilityContext",
    "EligibilityDecision",
    "ReviewedClassification",
    "evaluate_group",
]
