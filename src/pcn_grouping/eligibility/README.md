# Whole-group eligibility evaluator — Agent E / #6

**Draft implementation, not legal approval.** This is the sole proposed
whole-finished-mixture group decision API. It never infers eligibility with an
LLM, calculates mixture CLP classifications, approves GCI/ICG representations,
converts concentration bases, builds dossiers, or determines Article 45
applicability from the mixture composition.

## Dependencies and public interface

This PR is **stacked on D's component-evidence PR #18**, which itself depends
on B's canonical-schema PR #14. C's concentration-solver PR #17 is separate.

```python
from pcn_grouping.components import ComponentRules, EvidenceCatalog
from pcn_grouping.eligibility import (
    ApplicabilityEvidence, EligibilityContext, ReviewedClassification,
    evaluate_group,
)

context = EligibilityContext(
    component_rules=ComponentRules.from_json(
        checked_in_rule_bytes,
        approval=reviewed_rulebook_approval,
    ),
    evidence_catalog=versioned_component_evidence_catalog,
    classifications=tuple_of_complete_classification_attestations,
    applicability=tuple_of_separate_mandatory_pcn_attestations,
    evaluation_date="2026-11-12",
)
decision = evaluate_group(formulation_revisions, context)
# decision.status: GroupStatus.ELIGIBLE | INELIGIBLE | REVIEW_REQUIRED
# decision.rule_results: immutable RuleResult(PASS|FAIL|REVIEW, sections, evidence, values)
```

The API deliberately requires **reviewed sidecar evidence** not contained in B's
initial Formulation dataclass. The input hash binds formulation revisions,
identity/role/classification evidence, applicability assertions, rule file SHA,
approval evidence and explicit evaluation date. Input order does not change
the decision or hash. Nothing is modified in B/D/C modules.

### Aggregation and interpretation

- Same duty holder; standard-full comparable mode; *verified complete* identical
  finished health-and-physical CLP signatures. Environmental-only differences,
  EuPCS differences, market, names and packaging are not compatibility failures.
- D's whole-group raw/notified identity comparison, approved GCI/ICG evidence,
  mixture->perfume mapping and exact A.4.3 per-member perfume totals are consumed;
  D's detailed RuleResults and trace matrix are preserved.
- For every **common notified identity**, E sums D's exact raw-member bounds and
  calls C's published `find_common_declaration(actual_bounds, class, rulebook)`
  once across all formulations. The statutory major-concern classification is
  selected from the versioned rulebook; numeric legality stays in C.
- Importing the C solver is an *integration dependency*. Until it is merged in
  the runtime environment, every common range returns REVIEW with
  `RANGE_SOLVER_UNAVAILABLE`. This is intentional and must never be bypassed
  with guessed percentages.
- A proven FAIL takes precedence over REVIEW. All hard checks must PASS for the
  chemical `ELIGIBLE` status. The actual repository rulebook is a
  `RESEARCH_DRAFT_NOT_EXECUTABLE_NOT_LEGAL_APPROVAL` and **cannot return a
  chemical PASS**. Tests use explicitly synthetic mocked `APPROVED` rule bytes
  only to exercise the control flow, not to assert real legal approval.
- Separate `applicability_status` and `dossier_status` are returned.
  Missing/negative applicability cannot silently create an ELIGIBLE result.
  `dossier_status` is only a field-presence/disclosure diagnostic, **not**
  submission-ready status or ECHA format validation.
- Rule results have a code in their values, source sections and evidence IDs.
  The decision also holds full D component rows, per-member perfume totals,
  disclosed perfume/classification rows, exact proposed common ranges, review
  gaps, version and canonical input hash. Every output is immutable.

## Tests and release gates

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/eligibility
python -m ruff check src/pcn_grouping/eligibility tests/eligibility
python -m mypy src
```

`tests/eligibility/test_engine.py` exercises two and three or more members,
order and hash reproducibility, exact 5%/5.0001%, nonperfume differences, separate
dossier and mandatory-PCN applicability, unapproved rules, missing solver and
classification evidence, and pairwise-vs-triple failures on perfume and range.

**Testing limitation:** orchestration tests monkeypatch the *C numeric solver*
with an explicitly named deterministic stub. They are not a replacement for
Agent C's actual band tests, Agent F's independent legal fixture adapter, or
ECHA examples 23–24 regulatory signoff. Full-stacked tests and CI must run
after B/C/D dependencies are available together; the integration team owns
that cross-branch assembly, and this PR is intentionally **draft**.

## Coordination/review

- Agent J (#11): confirm `evaluate_group(formulations, EligibilityContext)`,
  extension of B's GroupDecision and GroupStatus API, and dependency order.
- Agent B (#3): no shared-model modifications.
- Agent C (#4): adopt `find_common_declaration`; no numeric duplication.
- Agent D (#5): consume existing ComponentAnalysis and source-pinned ComponentRules.
- Agent A (#2): verify Annex VIII A.4.1–4.4 and ECHA interpretation, including
  GCI/ICG representation scope and unapproved rules.
- Agent F (#7): independent unit/QA fixtures and offline CI, signed-off golden
  examples 23–24.
- No self-merge, no production use and no legal-compliance claim without
  reviewer approvals and full integrated green checks.
