"""Additional order stability and very-long-decimal regression coverage."""

from decimal import Decimal

from test_solver import solve


def test_stable_evidence_for_equal_values_with_different_decimal_scales():
    values = (Decimal("5.00000"), Decimal("5.0"), Decimal("5"))
    assert solve(values) == solve(tuple(reversed(values)))
    result = solve(values)
    assert result.declaration.exact
    assert result.evidence[0] == "required_actual_hull=[5,5]"


def test_very_long_decimal_width_without_python_integer_string_conversion():
    small = "0." + "0" * 4500 + "1"
    large = "0." + "0" * 4500 + "2"
    result = solve((small, large))
    assert result.status == "PASS"
    assert result.applied_zones[0].candidate_width == Decimal(small)
