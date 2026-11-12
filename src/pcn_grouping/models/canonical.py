"""Canonical wire JSON and SHA-256: only syntactic equivalence, no chemistry inference."""

import hashlib
import json
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any


def _canonical_decimal(number: Decimal) -> str:
    if not number.is_finite():
        raise ValueError("non-finite Decimal cannot be canonicalized")
    if number == 0:
        return "0"
    plain = format(number, "f")
    return plain.rstrip("0").rstrip(".") if "." in plain else plain


def canonical_data(value: Any) -> Any:
    """Normalize nested dataclasses; all tuple members represent unordered records/tags."""
    if isinstance(value, Decimal):
        return _canonical_decimal(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: canonical_data(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): canonical_data(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        members = [canonical_data(member) for member in value]
        return sorted(members, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    if value is None or type(value) in (str, bool, int):
        return value
    raise TypeError(f"unsupported canonical input type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(canonical_data(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def canonical_input_hash(formulations: tuple[Any, ...]) -> str:
    return canonical_sha256(formulations)
