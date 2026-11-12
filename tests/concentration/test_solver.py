"""Synthetic decimal audit of Annex VIII B.3.4 Table 1/2 boundaries.

The fixture uses Agent A's 2026-07-01 audited draft *numeric values*, with
an explicitly artificial approval flag to test the calculation path. It does
NOT confer regulatory approval on the real research-draft ruleset.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext

import pytest

from pcn_grouping.concentration import find_common_declaration


RULESET = {
    "ruleset_id": "SYNTHETIC_APPROVED_ARITHMETIC_TEST_ONLY",
    "status": "APPROVED",
    "maximum_concentration_range_width_percentage_points": {
        "major_concern": [
            {"min_inclusive": "25", "max_exclusive": "100", "max_width": "5"},
            {"min_inclusive": "10", "max_exclusive": "25", "max_width": "3"},
            {"min_inclusive": "1", "max_exclusive": "10", "max_width": "1"},
            {"min_inclusive": "0.1", "max_exclusive": "1", "max_width": "0.3"},
            {"min_exclusive": "0", "max_exclusive": "0.1", "max_width": "0.1"},
        ],
        "other": [
            {"min_inclusive": "25", "max_exclusive": "100", "max_width": "20"},
            {"min_inclusive": "10", "max_exclusive": "25", "max_width": "10"},
            {"min_inclusive": "1", "max_exclusive": "10", "max_width": "3"},
            {"min_exclusive": "0", "max_exclusive": "1", "max_width": "1"},
        ],
    },
}


def solve(values, component_class="major_concern", ruleset=RULESET):
    return find_common_declaration(values, component_class, ruleset)


@pytest.mark.parametrize(
    "values,expected",
    [
        (("9.7", "10.5"), "PASS"),  # Agent A A-M01
        (("9", "11"), "FAIL"),  # A-M02
        (("23", "26"), "PASS"),  # ECHA example 19
        (("24", "29"), "FAIL"),
        (("25", "30"), "PASS"),
        (("0.05", "0.15"), "PASS"),
        (("0.0500", "0.1501"), "FAIL"),
        (("0.1", "0.4"), "PASS"),
        (("0.1", "0.4001"), "FAIL"),
        (("0.9", "1.2"), "PASS"),
        (("0.8", "1.2"), "FAIL"),
        (("99", "100"), "REVIEW"),
        (("0", "0.2"), "REVIEW"),
    ],
)
def test_agent_a_major_concern_cases(values, expected):
    assert solve(values).status == expected


@pytest.mark.parametrize(
    "values,expected",
    [
        (("4", "6"), "PASS"),  # Agent A A-O01
        (("3", "7"), "FAIL"),
        (("9.7", "10.5"), "PASS"),
        (("0.1", "1.0"), "PASS"),
        (("0", "0.2"), "REVIEW"),
        (("1", "4.0001"), "FAIL"),
    ],
)
def test_agent_a_other_cases(values, expected):
    assert solve(values, "other").status == expected


@pytest.mark.parametrize(
    "component_class,lower,upper,max_width,point_below,point_above",
    [
        ("major_concern", "25", "30", "5", "24.9999", "25.0001"),
        ("major_concern", "10", "13", "3", "9.9999", "10.0001"),
        ("major_concern", "1", "2", "1", "0.9999", "1.0001"),
        ("major_concern", "0.1", "0.4", "0.3", "0.0999", "0.1001"),
        ("other", "25", "45", "20", "24.9999", "25.0001"),
        ("other", "10", "20", "10", "9.9999", "10.0001"),
        ("other", "1", "4", "3", "0.9999", "1.0001"),
    ],
)
def test_each_band_lower_boundary_exact_width_and_above(
    component_class, lower, upper, max_width, point_below, point_above
):
    passed = solve((lower, upper), component_class)
    assert passed.status == "PASS"
    assert passed.declaration.lower == Decimal(lower)
    assert passed.declaration.upper == Decimal(upper)
    assert passed.applied_zones[0].maximum_width == Decimal(max_width)
    assert solve((lower, str(Decimal(upper) + Decimal("0.0001"))), component_class).status == "FAIL"
    assert solve((point_below, upper), component_class).status == "FAIL"
    assert solve((point_above, upper), component_class).status == "PASS"


@pytest.mark.parametrize("value,expected_band", [
    ("0.0999999", "(0,0.1)"), ("0.1", "[0.1,1)"),
    ("0.999999", "[0.1,1)"), ("1", "[1,10)"),
    ("9.999999", "[1,10)"), ("10", "[10,25)"),
    ("24.999999", "[10,25)"), ("25", "[25,100)"),
    ("99.999", "[25,100)"),
])
def test_exact_singleton_endpoint_zone(value, expected_band):
    result = solve((value, value))
    assert result.status == "PASS"
    assert result.declaration.exact
    assert [z.label for z in result.applied_zones] == [expected_band]


def test_other_table_1pct_lower_and_upper_semantics():
    assert [z.label for z in solve(("1", "1"), "other").applied_zones] == ["[1,10)"]
    assert [z.label for z in solve(("0.999", "0.999"), "other").applied_zones] == ["(0,1)"]


@pytest.mark.parametrize("values,expected", [
    ((("9.7", "9.9"), ("10.1", "10.5")), "PASS"),
    ((("9", "9.5"), ("10.5", "11")), "REVIEW"),
    ((("9", "9.2"), ("10.5", "11")), "FAIL"),
    ((("9", "10"), ("10", "11")), "REVIEW"),
    ((("9", "11"),), "REVIEW"),
    ((("1", "1"), ("3", "3")), "FAIL"),
    ((("5", "5"), ("5", "5")), "PASS"),
])
def test_bounded_actual_uncertainty(values, expected):
    assert solve(values).status == expected


@dataclass(frozen=True)
class AgentBConcentrationValue:
    value: Decimal | None


@dataclass(frozen=True)
class AgentBConcentrationInterval:
    lower: Decimal | None
    upper: Decimal | None


def test_agent_b_models_compatible_and_unknown_distinct_from_zero():
    result = solve((AgentBConcentrationValue(Decimal("9.7")),
                    AgentBConcentrationInterval(Decimal("10.2"), Decimal("10.5"))))
    assert result.status == "PASS"
    assert solve((AgentBConcentrationValue(None),)).status == "REVIEW"
    assert solve((AgentBConcentrationValue(Decimal(0)),)).status == "REVIEW"
    assert solve((AgentBConcentrationInterval(None, Decimal("0.1")),)).status == "REVIEW"


def test_determinism_ignores_member_order():
    values = ("12.1", ("12.0", "12.3"), "12.2")
    assert solve(values) == solve(tuple(reversed(values)))


def test_arbitrary_decimal_precision_regardless_of_context():
    tiny = "0." + "0" * 99 + "1"
    twice_tiny = "0." + "0" * 99 + "2"
    with localcontext() as ctx:
        ctx.prec = 5
        result = solve((tiny, twice_tiny))
        failing = solve((tiny, "1"))
    assert result.status == "PASS"
    assert result.applied_zones[0].candidate_width == Decimal(tiny)
    assert result.declaration.lower == Decimal(tiny)
    assert failing.status == "FAIL"
    assert failing.applied_zones[0].candidate_width > Decimal("0.999999999999999999999")


def test_no_binary_float_or_rounding_acceptance():
    for values in ((1.0, 1.0), ("NaN", "1"), ("Infinity", "1"),
                   ("1e-1", "1"), ("9", object()), ("-1", "0.1")):
        assert solve(values).status == "REVIEW"
    assert solve(("0.1000", "0.4000000000000000000001")).status == "FAIL"


def test_missing_unknown_class_invalid_bounds_and_ruleset():
    assert solve((), "other").reason_codes == ("MISSING_ACTUAL_CONCENTRATION",)
    assert solve(("1",), "unknown").reason_codes == ("UNKNOWN_COMPONENT_CLASS",)
    assert solve((("2", "1"),)).reason_codes == ("INVALID_ACTUAL_BOUNDS",)
    assert solve(("101",)).reason_codes == ("INVALID_ACTUAL_BOUNDS",)
    assert solve(("100",)).reason_codes == ("ZERO_OR_100_ENDPOINT_REQUIRES_REVIEW",)
    assert solve(("1",), ruleset={}).reason_codes == ("MISSING_RULESET",)
    bad = {**RULESET, "maximum_concentration_range_width_percentage_points": {}}
    assert solve(("1",), ruleset=bad).reason_codes == ("INVALID_OR_MISSING_BAND_RULES",)


def test_research_draft_is_never_approved_legal_decision():
    draft = {**RULESET, "status": "RESEARCH_DRAFT_NOT_EXECUTABLE_NOT_LEGAL_APPROVAL"}
    assert solve(("9.7", "10.5"), ruleset=draft).reason_codes == (
        "RULESET_NOT_REGULATORY_APPROVED",)
    assert solve(("9", "11"), ruleset=draft).status == "REVIEW"


def test_ruleset_missing_middle_band_or_overlapping_endpoint_fails_closed():
    rows = RULESET["maximum_concentration_range_width_percentage_points"]["major_concern"]
    for edited in (rows[:2] + rows[3:], [*rows[:3], {**rows[3], "min_inclusive": "0.1", "max_inclusive": "1", "max_exclusive": "1"}, rows[4]]):
        fake = {**RULESET, "maximum_concentration_range_width_percentage_points": {
            **RULESET["maximum_concentration_range_width_percentage_points"],
            "major_concern": edited,
        }}
        assert solve(("10", "10"), ruleset=fake).status == "REVIEW"


def test_evidence_contains_precise_blocker_and_ruleset_version():
    result = solve(("9", "11"))
    assert result.status == "FAIL"
    assert result.rule_id == "REG-MAJOR-BAND"
    assert result.ruleset_id == RULESET["ruleset_id"]
    assert result.declaration is None
    assert result.candidate.lower == Decimal("9")
    assert result.candidate.upper == Decimal("11")
    assert any("max_width_percentage_points=1" in item for item in result.evidence)
    assert any("required_width_percentage_points=2" in item for item in result.evidence)
