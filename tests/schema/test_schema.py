"""Synthetic records only; these test the contract, not EU grouping eligibility."""

from copy import deepcopy
from decimal import Decimal

import pytest

from pcn_grouping.models import (
    ConcentrationInterval,
    ConcentrationValue,
    Formulation,
    canonical_input_hash,
    canonical_json,
    canonical_sha256,
)
from pcn_grouping.validation import (
    IssueSeverity,
    parse_concentration,
    parse_formulation,
    validate_portfolio,
)


def sample() -> dict:
    return {
        "formulation_id": "SYN-F001", "revision": "r1",
        "legal_submitter_id": "SYN-OWNER", "notification_mode": "STANDARD_FULL",
        "composition_basis": "MASS_PERCENT",
        "approved_health_physical_classification": [{
            "hazard_class": "Flam. Liq.", "category": "3", "h_code": "H226",
            "status": "VERIFIED", "source_document_ids": ["CLP-SYN"],
        }],
        "components": [
            {"line_id": "L1", "identity_id": "SYN-BASE", "kind": "SUBSTANCE",
             "actual": {"exact": "95.0000"}, "source_line_ids": ["RAW1"]},
            {"line_id": "L2", "identity_id": "SYN-PERFUME", "kind": "SUBSTANCE",
             "actual": {"exact": "5.0000"}, "technical_function": "PERFUME",
             "perfume_role_evidence": {"evidence_id": "SYN-PERFUME-EV",
                                       "status": "VERIFIED", "source_document_ids": ["SYN-EV"]},
             "source_line_ids": ["RAW2"]},
        ],
        "raw_bom": [
            {"source_line_id": "RAW1", "source_document_id": "DOC1",
             "fields": {"ingredient": "Raw Base", "percent": "95.0000", "blank": ""}},
            {"source_line_id": "RAW2", "source_document_id": "DOC1",
             "fields": {"ingredient": "Raw Perfume", "percent": "5.0000"}},
        ],
        "source_references": [{"document_id": "DOC1", "location": "Mock tab/3:4"}],
        "notified_components": [
            {"declaration_id": "N1", "declared_identity_id": "SYN-BASE",
             "concentration": {"exact": "95"}, "source_component_line_ids": ["L1"]},
            {"declaration_id": "N2", "declared_identity_id": "SYN-PERFUME",
             "concentration": {"exact": "5"}, "source_component_line_ids": ["L2"]},
        ],
        "product_names": ["SYN-Product"], "eupcs_codes": ["PC-TEST"],
        "market_countries": ["DE", "FR"],
    }


def codes(result) -> set[str]:
    return {item.code for item in result.issues}


def test_import_and_model_immutability() -> None:
    result = parse_formulation(sample())
    assert result.accepted
    assert isinstance(result.formulation, Formulation)
    assert result.formulation.components[1].actual == ConcentrationValue(Decimal("5"))
    assert result.formulation.raw_bom[0].fields[2] == ("blank", "")
    with pytest.raises(Exception):
        result.formulation.revision = "forbidden"


def test_permuted_records_and_decimal_scale_hash_identically() -> None:
    a = sample()
    b = deepcopy(a)
    b["components"].reverse()
    b["raw_bom"].reverse()
    b["notified_components"].reverse()
    b["components"][0]["actual"]["exact"] = "5.0"
    b["components"][1]["actual"]["exact"] = "95"
    b["market_countries"].reverse()
    first = parse_formulation(a)
    second = parse_formulation(b)
    assert first.accepted and second.accepted
    assert canonical_json(first.formulation) == canonical_json(second.formulation)
    assert canonical_sha256(first.formulation) == canonical_sha256(second.formulation)
    assert canonical_input_hash((first.formulation, second.formulation)) == canonical_input_hash(
        (second.formulation, first.formulation)
    )
    assert first.formulation.raw_bom[0].source_line_id != second.formulation.raw_bom[0].source_line_id


def test_float_never_accepted_as_concentration() -> None:
    for raw in (5.0, {"exact": 5.0}, {"lower": "0", "upper": 5.0}):
        concentration, errors = parse_concentration(raw)
        assert concentration is None or isinstance(concentration, ConcentrationInterval)
        assert any(issue.severity is IssueSeverity.ERROR for issue in errors)
    payload = sample()
    payload["components"][1]["actual"] = {"exact": 5.0}
    result = parse_formulation(payload)
    assert not result.accepted and result.formulation is None
    assert "INVALID_DECIMAL" in codes(result)
    with pytest.raises(TypeError):
        ConcentrationValue(5.0)


def test_unknown_stays_null_not_zero() -> None:
    payload = sample()
    payload["components"][1]["actual"] = {"exact": None}
    result = parse_formulation(payload)
    assert result.accepted
    assert "UNKNOWN_CONCENTRATION" in codes(result)
    assert result.formulation.components[1].actual == ConcentrationValue(None)
    assert '"value":null' in canonical_json(result.formulation)
    assert canonical_sha256(result.formulation) != canonical_sha256(parse_formulation(sample()).formulation)


def test_errors_are_structured_no_malformed_payload_exception() -> None:
    payload = sample()
    payload["formulation_id"] = ""
    payload["components"][1]["line_id"] = "L1"
    payload["components"][0]["actual"] = {"lower": "99", "upper": "98"}
    payload["raw_bom"][1]["fields"]["percent"] = 5.0
    result = parse_formulation(payload)
    assert result.formulation is None
    assert {"MISSING_ID", "DUPLICATE_OR_MISSING_COMPONENT_ID", "INVALID_BOUNDS",
            "INVALID_RAW_FIELDS"} <= codes(result)
    assert all(issue.path and issue.message for issue in result.issues)


def test_percent_boundaries_and_total_tolerance() -> None:
    good, issues = parse_concentration({"lower": "0", "upper": "100"})
    assert good == ConcentrationInterval(Decimal("0"), Decimal("100"))
    assert not issues
    for value in ("100.0001", "-0.01", "NaN", "1e-3", "0,4"):
        _, failures = parse_concentration({"exact": value})
        assert any(issue.severity is IssueSeverity.ERROR for issue in failures)
    payload = sample()
    payload["components"][0]["actual"] = {"exact": "94.9899"}
    assert "TOTAL_NOT_100" in codes(parse_formulation(payload))
    payload["components"][0]["actual"] = {"exact": "94.9900"}
    assert "TOTAL_NOT_100" not in codes(parse_formulation(payload))


def test_uncertainty_that_could_total_100_is_not_rejected() -> None:
    payload = sample()
    payload["components"][0]["actual"] = {"lower": "94", "upper": "96"}
    result = parse_formulation(payload)
    assert result.accepted
    assert "TOTAL_NOT_100" not in codes(result)


def test_unverified_hazards_and_perfume_are_review_not_pass() -> None:
    payload = sample()
    payload["approved_health_physical_classification"][0]["h_code"] = "H999"
    payload["components"][1]["perfume_role_evidence"]["status"] = "UNKNOWN"
    result = parse_formulation(payload)
    assert result.accepted
    assert {"UNRECOGNISED_HAZARD", "UNVERIFIED_PERFUME"} <= codes(result)


def test_mim_identity_insufficient_review() -> None:
    payload = sample()
    payload["components"][0]["kind"] = "MIM"
    result = parse_formulation(payload)
    assert result.accepted
    assert "INCOMPLETE_MIM" in codes(result)


def test_duplicate_formulation_revision() -> None:
    result = parse_formulation(sample())
    assert result.formulation is not None
    issues = validate_portfolio([result.formulation, result.formulation])
    assert issues[0].code == "DUPLICATE_FORMULATION_REVISION"


def test_no_network_import() -> None:
    import pcn_grouping

    assert pcn_grouping.__version__ == "0.1.0"
