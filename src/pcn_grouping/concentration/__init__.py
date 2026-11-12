"""Exact, research-rulebook-gated Annex VIII concentration declarations.

This module decides numerical *declaration feasibility*, not finished-mixture
eligibility, regulatory approval, or dossier readiness. See 'solver'.
"""

from .solver import (
    ConcentrationDeclaration,
    DeclarationDecision,
    ZoneCheck,
    find_common_declaration,
)

__all__ = [
    "ConcentrationDeclaration",
    "DeclarationDecision",
    "ZoneCheck",
    "find_common_declaration",
]
