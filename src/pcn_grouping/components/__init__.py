"""Evidence-backed identities and whole-group component analysis (Agent D)."""

from .analysis import analyse_components
from .contracts import (
    Bounds,
    ComponentAnalysis,
    ComponentRow,
    EvidenceCatalog,
    IdentityAlias,
    IdentityRecord,
    LineEvidence,
    MiMRouteEvidence,
    PerfumeTotal,
    RepresentationApproval,
)
from .identity import normalise_identifier, resolve_identity
from .rules import ComponentRules

__all__ = [
    "Bounds",
    "ComponentAnalysis",
    "ComponentRow",
    "ComponentRules",
    "EvidenceCatalog",
    "IdentityAlias",
    "IdentityRecord",
    "LineEvidence",
    "MiMRouteEvidence",
    "PerfumeTotal",
    "RepresentationApproval",
    "analyse_components",
    "normalise_identifier",
    "resolve_identity",
]
