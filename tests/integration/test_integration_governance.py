"""Offline governance regression checks for integration issue #11.

These test only the integration contract and research-ruleset safeguard.
They DO NOT exercise the future eligibility engine or establish PCN compliance.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class IntegrationGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = (ROOT / "docs/integration-plan.md").read_text(encoding="utf-8")
        cls.done = (ROOT / "docs/definition-of-done.md").read_text(encoding="utf-8")
        cls.ruleset = json.loads(
            (ROOT / "rulesets/annex_viii_2026_07_01.research-draft.json").read_text(
                encoding="utf-8"
            )
        )

    def test_research_ruleset_cannot_be_mistaken_for_approved(self) -> None:
        self.assertEqual(
            self.ruleset["status"], "RESEARCH_DRAFT_NOT_EXECUTABLE_NOT_LEGAL_APPROVAL"
        )
        self.assertIn("research draft", self.plan.lower())
        self.assertIn("an approved executable rule version", self.done.lower())

    def test_owners_and_staged_dependency_sequence_are_recorded(self) -> None:
        for issue in range(1, 12):
            self.assertIn(f"#{issue}", self.plan)
        order = ["(A audit + B schema + F CI)", "(C/D)", "(E)", "(G/I)", "(H adapter)"]
        positions = [self.plan.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("one named responsible owner", self.plan)
        self.assertIn("independent", self.done.lower())

    def test_eligibility_not_equated_to_submitting_or_dossier_readiness(self) -> None:
        for status in ("ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED"):
            self.assertIn(status, self.plan)
            self.assertIn(status, self.done)
        self.assertIn("dossier/submission readiness", self.plan)
        self.assertIn("no code or report says a PCN was submitted", self.done)
        self.assertIn("FAIL takes precedence over REVIEW", self.plan)

    def test_replay_gate_is_explicitly_unverified(self) -> None:
        for case in ("P02", "N01", "R03", "P12"):
            self.assertIn(case, self.plan)
            self.assertIn(case, self.done)
        self.assertIn("NOT YET RUN", self.plan)
        self.assertIn("two independent runs", self.plan)
        self.assertIn("NOT READY", self.done)

    def test_no_live_secrets_or_production_data_in_pipeline(self) -> None:
        for term in ("production formulation", "supplier SDS", "read-only"):
            self.assertIn(term.lower(), self.plan.lower())
        self.assertIn("no production/customer formulations", self.done.lower())
        self.assertIn("no live Sheets access", self.done)


if __name__ == "__main__":
    unittest.main()
