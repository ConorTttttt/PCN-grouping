# QA evidence and pending checks — 12 November 2026

## Independent fixture/oracle audit (PASS)

An automated independent verification of the committed JSON source records
used **integer-scaled decimal arithmetic** (no binary-float percentages).
The following assertions succeeded against the live
`agent/regulatory-qa` GitHub branch after the R09 expected-total correction:

- **40** uniquely identified requirements-level cases, **79** formulation
  records and **139** component records.
- **77** formulation records containing all exact concentrations had expected
  exact totals; R09 mixture A intentionally totals **99%** and remains REVIEW.
  Two other formulation records include explicit unknown or bounded values.
- The rule-traceability coverage matches the fixture verdicts for **20**
  draft rule IDs; core gates for submitter, classification, identity, reported
  range, varying perfume and GCI have positive and negative cases.
- **14** concentration-zone cutoff oracles and **12** cross-zone range
  oracles matched the independent research-draft Table 1/2 interpretation.
- ECHA v6.0 Example 23 independently sums varying perfume actuals to **2.8%**
  and **3.2%**. Example 24 remains a **partial excerpt**, with missing actual
  perfume concentrations classified REVIEW, not accepted as a full legal golden.

These checks establish the fixture ledger's internal consistency, **not**
that the real eligibility evaluator has passed its tests.

## Actions / full regression gate (NOT YET PASSING)

QA PR #15 triggered GitHub Actions workflow run
`43174069331`: conclusion **failure**. Its job
`131033952989` had `runner_id=0`, **zero steps**, and ended within
seconds. The GitHub logs endpoint returned 404/BlobNotFound. This is
consistent with a failure **before a runner was assigned**; the exact
GitHub-side cause is not available. **No Python lint, type or pytest pass**
can be claimed from that run. Investigate Actions provisioning/limits and
rerun the workflow.

`tests/test_acceptance_engine.py` intentionally skips while Agent E's
runtime module is absent, and blocks if the module appears without a
reviewed `tests/fixtures/engine_adapter.py` bridge. Agent A's legal audit
and B/E/J interface reviews remain outstanding.

**No legal-compliance, ECHA-submission or merge approval implied.**
