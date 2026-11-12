# Integration verification ledger — 12 November 2026

**Owner:** Agent J, issue #11. **Status:** BLOCKED; candidate integration branch only. No production approval, regulatory sign-off, filing, merge, or verified end-to-end release. This file is evidence of what was assembled and of the checks that did **not** complete.

## Pinned repository snapshot

- Repository: `ConorTttttt/PCN-grouping`; main baseline: `8531f9640cfe8a4d0850ef46b55c2e741c19d37e`.
- Integration branch: `agent/mvp-integration-2026-11-12`; initial verified assembled tree: `f84243d570adfced4fe7b39b5ea8d6faa755a4d3` (commit `45d345dee4b23f4c97a116ceb8f239c651fb03e6`).
- Initial integration parent is E head `6f0e620e32240dd536f8cafb62c027b6bb3ea738`, which contains D `7cc2658ad4ef1a7c768c03a2444e535357a0701d` stacked on B `7b89fd320096993ffc0beb1acf342057940ad92f`.
- Grafted unchanged by source-object SHA: C #17 solver/tree; F #15 CI and independent acceptance fixtures; A #13 regulatory docs, draft rules and audit cases; J #12 governance files. New J-owned `tests/integration/test_real_solver_and_evaluator.py` exercises real B/C/D/E, not a mocked solver.
- Regulatory data source: `rulesets/annex_viii_2026_07_01.research-draft.json`, status `RESEARCH_DRAFT_NOT_EXECUTABLE_NOT_LEGAL_APPROVAL`, effective baseline 2026-07-01. No real-world production approval may be inferred from this file.
- **No source upstream PRs were merged**, rebased, modified, or marked approved by this integration work.

## PR dependencies and review disposition

| PR | Agent | Source branch | Dependency / interface | Review gate |
| --- | --- | --- | --- | --- |
| #13 | A | `agent/regulatory-audit` | D/C/E versioned regulatory contract; ECHA and current Annex VIII | Independent regulatory SME review; SME-01 through SME-09 |
| #14 | B | `agent/core-schema` | Foundation: `Formulation`, `Component`, Decimal, `GroupDecision` | Independent code review, CI; downstream confirmation |
| #15 | F | `agent/regulatory-qa` | E real evaluator plus `tests/fixtures/engine_adapter.py`; Python 3.12 CI | Missing bridge and runnable CI |
| #17 | C | `agent/concentration-solver` | `find_common_declaration(actuals, class, full_rule_mapping)` | B-compatible actuals, E end-to-end and numeric SME |
| #18 | D | `agent/component-evidence` | Stacked B; `EvidenceCatalog`, `ComponentRules` / `ComponentAnalysis` | Identity, MiM, GCI/ICG, perfume review and integrated CI |
| #19 | E | `agent/eligibility-engine` | Stacked D/B; imports C at runtime; `evaluate_group(formulations, EligibilityContext)` | C present, independent F fixtures, full CI, regulatory reviewer |
| #16 | G | `agent/portfolio-optimizer` | Stacked E/D/B; whole-set evaluator; C still separate | **Not yet added**: E integrated tests must pass first |
| #20 | I | `agent/audit-reporting` | Stacked E/D/B; immutable eligibility-report ABI | **Not yet added**: E integrated tests must pass first |
| #12 | J | `agent/integration-plan` | Governance test and review gates | This integration branch carries docs/tests unchanged |

All PRs above were observed open and draft at the time of integration inventory. No PR is authorised for merge by this ledger. H #9 has no implementation within this integration branch; live spreadsheet mapping is deferred.

## Test inventory, commands and observed evidence

Source PR descriptions report these **isolated, author-reported** local observations: B #14 11 passed; C #17 53 passed; D #18 70 passed in its B/D checkout; G #16 74 passed in its own optimizer checkout; I #20 10 passed reporting tests. These counts **are not additive** and are **not** integrated CI evidence. E #19 explicitly did not claim a combined execution.

The integration-owned real-solver test adds:
1. common major-component range 9.7–10.5 PASS versus 9–11 FAIL using C;
2. B/D/E real synthetic 2-member eligible outcome with exact common declarations and reproducible hash;
3. 5.0001% varying perfume ineligible outcome;
4. missing CLP-completeness and unapproved production ruleset REVIEW outcomes;
5. pairwise 2-member permissibility but 3-member whole-group 8% varying perfume rejection.

Test-only rule branches explicitly replace the status with `APPROVED` **only for synthetic control-flow test execution**; production calls always load the actual draft source, which must return REVIEW.

Intended reproduction, once a runner is executing and F's bridge is independently approved:

```bash
python -V  # CI uses Python 3.12
python -m pip install -e . pytest hypothesis ruff mypy
python -m ruff check .
python -m mypy src/pcn_grouping tests/test_acceptance_*.py
python -m pytest -q tests/schema tests/concentration tests/components tests/eligibility tests/integration
python -m pytest -q
```

**Observed GitHub Actions, not inferred:** workflow `PCN deterministic QA`, push commit `45d345dee4b23f4c97a116ceb8f239c651fb03e6`, run [#22](https://github.com/ConorTttttt/PCN-grouping/actions/runs/43287078080): `completed/failure`; commit `298febc844cb8ce68b94ad51ade8047464fc5cde`, run [#23](https://github.com/ConorTttttt/PCN-grouping/actions/runs/43287279508): `completed/failure`. Run #23 reported **0 ms billed runner execution, no job steps, and no retrievable logs** from the GitHub API, so the cause is **not established** and there is no executed pytest result, pass count or validated Python version. Previous F standalone workflow runs also reported 0 ms runner execution. Inspect GitHub Actions UI/repo permissions/runners/billing and YAML diagnostics before interpreting this as a code test failure. A subsequent clean, logged run is mandatory.

**Independent fixture blocker:** F's `tests/test_acceptance_engine.py` deliberately fails closed when E is present without F's `tests/fixtures/engine_adapter.py`. Agent J has notified F in PR #15. Do not disable/skip/mislabel these tests, hard-code expected outcomes, or make up attestation to obtain green CI. F owns fixture mapping; legal ambiguities must be raised for review.

**Executed integrated pytest results:** **not available** (0 observed executed, no passing gate). No synthetic outcome has yet been observed from running the integrated branch; the test source asserts expected outcomes but is not independent execution evidence.

## Legal, security and release blockers

- A's ruleset remains unapproved; unresolved SME-01..09 and independent guidance/source review prohibit a legal-use PASS.
- Statutory maintenance: the future fifth B.4.1 general emergency-response trigger takes effect in 2027 rather than the 2026 baseline, pending reviewer confirmation; do not apply future law as an active 2026 gate.
- Real MiM chain expansion, new ICG approvals, nonstandard submissions, lifecycle/UFI handling and ECHA format exports are deferred or REVIEW-gated.
- F independent fixture adapter and true ECHA examples 23–24 reviewer-validated replay are unverified.
- G optimiser and I reporting not yet added; end-to-end B→C/D→E→G→I and replay bytes are **NOT VERIFIED**.
- H input adapter / live Sheets credentials and real spreadsheet schema are not supplied; no live customer data or supplier SDS used.
- Source-object graft and synthetic test additions contain no intentional production mixtures, SDS or secrets. A **limited read-only regex secret scan** of all **47 text files** in the integration tree at commit `4477292c54fda2a5bc20011bb1ba9c3ce7f53c93` completed: **47 readable, 0 matching strings** for GitHub classic/fine-grained PATs, common AWS access-key IDs, PEM private-key headers, Google API keys and Slack tokens; **0** `.env`, `.pem`, `.key`, `.p12` or `.pfx` filenames. This is **not** a comprehensive secrets/PII/chemical-data scan; independent privacy/security audit remains open.
- Independent code owner reviews, regulatory SME signoff and a reproducible full Python 3.12 CI run remain mandatory.

## Stop/go decision

**NO-GO / DRAFT REVIEW ONLY.** Do not merge this or upstream PRs, call it legally compliant, certify a dossier or claim ECHA submission. Next required evidence: Agent F fixture bridge + runnable CI; pass all B/C/D/E integrated tests; resolve genuine implementation failures before incorporating G and I; rerun all suites and export stable synthetic status/reason reports; obtain independent technical and regulatory reviews.
