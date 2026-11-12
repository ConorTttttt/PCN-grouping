"""Gate the actual eligibility evaluator when Agent E's API becomes available.

A missing evaluator is a documented dependency, *not* a passing regulatory test.
As soon as the runtime module exists, CI requires the independently maintained
fixture bridge at tests/fixtures/engine_adapter.py and compares real verdicts.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))


def _adapter() -> Any:
    try:
        module_spec = importlib.util.find_spec("pcn_grouping.eligibility")
    except ModuleNotFoundError:
        module_spec = None
    if module_spec is None:
        pytest.skip("Agent E eligibility evaluator not merged; no legal test passes are claimed")
    adapter_path = FIXTURE_DIR / "engine_adapter.py"
    if not adapter_path.is_file():
        pytest.fail(
            "Evaluator now exists but independent QA bridge is missing: "
            "add tests/fixtures/engine_adapter.py with evaluate(case)->"
            "{status, rules: {rule_id: PASS|FAIL|REVIEW}}"
        )
    bridge_spec = importlib.util.spec_from_file_location("pcn_qa_adapter", adapter_path)
    assert bridge_spec is not None and bridge_spec.loader is not None
    bridge = importlib.util.module_from_spec(bridge_spec)
    bridge_spec.loader.exec_module(bridge)
    assert callable(getattr(bridge, "evaluate", None)), "Bridge must expose evaluate(case)"
    return bridge


def _cases() -> list[dict[str, Any]]:
    manifest = json.loads((FIXTURE_DIR / "acceptance_cases.json").read_text(encoding="utf-8"))
    return [
        case for case in manifest["cases"]
        if case["expected_status"] in {"ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED"}
    ]


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["id"])
def test_actual_evaluator_matches_independent_expectations(case: dict[str, Any]) -> None:
    adapter = _adapter()
    outcome = adapter.evaluate(copy.deepcopy(case))
    assert outcome["status"] == case["expected_status"], case["id"]
    for rule, verdict in case["expected_rules"].items():
        assert outcome["rules"].get(rule) == verdict, (
            case["id"], rule, verdict, outcome["rules"]
        )


@settings(max_examples=25, deadline=None)
@given(st.permutations((0, 1, 2)), st.permutations((0, 1, 2)))
def test_evaluator_whole_group_permutation_invariance(
    mixture_order: tuple[int, ...], component_order: tuple[int, ...]
) -> None:
    adapter = _adapter()
    case = next(case for case in _cases() if case["id"] == "P12")
    before = adapter.evaluate(copy.deepcopy(case))
    permuted = copy.deepcopy(case)
    permuted["formulations"] = [permuted["formulations"][i] for i in mixture_order]
    for formulation in permuted["formulations"]:
        parts = formulation["components"]
        if len(parts) == 3:
            formulation["components"] = [parts[i] for i in component_order]
        else:
            formulation["components"] = list(reversed(parts))
    after = adapter.evaluate(permuted)
    assert (before["status"], before["rules"]) == (after["status"], after["rules"])
    assert before["status"] == "INELIGIBLE"


@settings(max_examples=40, deadline=None)
@given(st.sampled_from(["P02", "P03", "P04"]), st.booleans())
def test_valid_subset_remains_valid_when_member_removed(
    case_id: str, reverse: bool
) -> None:
    adapter = _adapter()
    case = next(case for case in _cases() if case["id"] == case_id)
    if reverse:
        case = copy.deepcopy(case)
        case["formulations"] = list(reversed(case["formulations"]))
    result = adapter.evaluate(case)
    assert result["status"] == "ELIGIBLE"
    # A singleton is not a group submission; this checks that no subset produces
    # a contradictory hard rule from unrelated formulation data.
    assert len(case["formulations"]) >= 2
