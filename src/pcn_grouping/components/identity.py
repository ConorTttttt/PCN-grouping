"""Exact registry lookup and identifier-format validation, never chemical inference."""

import re

from pcn_grouping.models import Component, ComponentKind

from .contracts import EvidenceCatalog, IdentityKey, IdentityRecord
from .rules import verified


def normalise_identifier(scheme: str, value: str) -> str:
    """Only explicit identifier formatting; no trade-name normalization/matching.

    UFI checks format only. A separate reviewed validation record is mandatory.
    CAS/EC checksums do not establish chemical identity or supplier equivalence.
    """
    value = value.strip()
    if scheme == "CAS":
        if not re.fullmatch(r"[1-9][0-9]{1,6}-[0-9]{2}-[0-9]", value):
            raise ValueError("invalid CAS format")
        digits = value.replace("-", "")
        if sum(i * int(n) for i, n in enumerate(reversed(digits[:-1]), 1)) % 10 != int(digits[-1]):
            raise ValueError("invalid CAS checksum")
    elif scheme == "EC":
        if not re.fullmatch(r"[0-9]{3}-[0-9]{3}-[0-9]", value):
            raise ValueError("invalid EC format")
        digits = value.replace("-", "")
        if sum(i * int(n) for i, n in enumerate(digits[:-1], 1)) % 11 != int(digits[-1]):
            raise ValueError("invalid EC checksum")
    elif scheme == "UFI":
        value = value.upper().replace("-", "").replace(" ", "")
        if not re.fullmatch(r"[0-9ACDEFGHJKLMNPQRSTUVWXY]{16}", value):
            raise ValueError("invalid UFI format")
        value = "-".join(value[i : i + 4] for i in range(0, 16, 4))
    elif scheme not in {
        "CLP_ART18",
        "INCI",
        "COLOUR_INDEX",
        "INTERNATIONAL_NAME",
        "SUPPLIER_PRODUCT",
    }:
        raise ValueError("unsupported or confidential identifier needs review")
    if not value:
        raise ValueError("empty identifier")
    return value


def resolve_identity(
    component: Component, catalog: EvidenceCatalog
) -> tuple[IdentityKey | None, IdentityRecord | None, str]:
    if not component.identity_id or not verified(component.identity_evidence):
        return None, None, "IDENTITY_EVIDENCE_MISSING"
    if component.kind not in {ComponentKind.SUBSTANCE, ComponentKind.MIM}:
        return None, None, "RAW_REPRESENTATION_WITHOUT_MEMBERS"
    supplier = component.mim.supplier_id if component.mim else None
    aliases = [
        a
        for a in catalog.aliases
        if a.input_id == component.identity_id
        and a.kind == component.kind
        and a.supplier_id == supplier
    ]
    records = [
        r
        for r in catalog.identities
        if r.identity_id == component.identity_id and r.kind == component.kind
    ]
    if aliases:
        if len(aliases) != 1 or records or not verified(aliases[0].evidence):
            return None, None, "AMBIGUOUS_OR_UNVERIFIED_ALIAS"
        records = [
            r
            for r in catalog.identities
            if r.identity_id == aliases[0].canonical_id and r.kind == component.kind
        ]
    if len(records) != 1 or not verified(records[0].evidence):
        return None, None, "IDENTITY_REGISTRY_UNVERIFIED"
    record = records[0]
    try:
        normalise_identifier(record.identifier_scheme, record.identifier)
    except ValueError:
        return None, record, "IDENTIFIER_INVALID_OR_CONFIDENTIAL"
    if component.kind is ComponentKind.MIM:
        mim = component.mim
        if (
            not mim
            or not record.supplier_id
            or not record.supplier_product_id
            or record.identifier_scheme != "SUPPLIER_PRODUCT"
            or (mim.supplier_id, mim.supplier_product_id)
            != (record.supplier_id, record.supplier_product_id)
        ):
            return None, record, "MIM_SUPPLIER_IDENTITY_UNVERIFIED"
    elif record.identifier_scheme == "SUPPLIER_PRODUCT":
        return None, record, "SUBSTANCE_IDENTIFIER_UNVERIFIED"
    return (component.kind.value, record.identity_id), record, "IDENTITY_VERIFIED"
