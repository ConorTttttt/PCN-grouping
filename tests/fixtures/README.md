# Independent PCN grouping QA fixtures

These records are **synthetic**: no customer formulation data, credentials,
supplier SDS documents, or production UFIs have been imported. The source
of the expectations is \`docs/acceptance-tests.md\`, not any evaluator output.
Current draft expectations are **not** a legal sign-off.

- \`acceptance_cases.json\`: 40 requirements-level scenarios. Every record has
  full synthetic formulation/revision IDs, exact **decimal strings** or explicit
  unknown/bounded values, expected overall status, and at least one expected
  rule-level status.
- \`concentration_boundaries.json\`: Annex VIII Table 1/2 research-draft
  boundary and cross-zone oracles, pending Agent A's statutory audit.
- \`echa_guidance_examples_23_24.json\`: separately source-checked **ECHA
  Guidance v6.0**, printed pp. **76–79**, §5.4.2. Example 23 includes actual
  variable perfume sums **2.8%** and **3.2%**. Example 24 gives membership
  mappings and disclosed ranges but **does not provide enough exact actual
  perfume percentages to independently establish the cap for all mixtures**.
  Both are only **partial excerpts**, not fabricated full-BOM eligibility
  goldens. Missing data must remain REVIEW in a full evaluator.
- \`rule_traceability.json\`: fixture IDs by draft rule ID and expected
  PASS/FAIL/REVIEW, with identified omissions and review conditions.

## Proposed fixture interface for Agents B, E and J

\`formulations[]\` is an **interim, deliberately non-normative** JSON shape.
\`components[]\` represents unmodified raw synthetic BOM records with
\`canonical_identity_id\`, \`declared_identity_id\`, \`kind\`,
\`actual_min_pct\`/\`actual_max_pct\` decimal strings, identification evidence,
classification, and verified perfume evidence. Explicit \`null\` means unknown.

The authoritative model is Agent B's immutable canonical formulation model;
the only legal verdict is Agent E's \`evaluate_group(formulations, ruleset)\`.
**Do not parse the expected verdict inside the evaluator**. A bridge owned
by QA must transform test records to B's validated models, invoke E's full-group
evaluator, and normalize output to:

\`\`\`python
def evaluate(case: dict) -> dict:
    return {
        "status": "ELIGIBLE|INELIGIBLE|REVIEW_REQUIRED",
        "rules": {"A4.1_CLASSIFICATION": "PASS|FAIL|REVIEW", ...},
    }
\`\`\`

Put that bridge in \`tests/fixtures/engine_adapter.py\` when the B/E contracts
are available. \`tests/test_acceptance_engine.py\` **skips** the evaluator
comparison while no \`pcn_grouping.eligibility\` module exists, and **fails CI**
if the module appears without the QA bridge. Thus the present QA-only green
suite is **fixture and research-oracle verification, not engine verification**.
Do not claim completion of the issue's engine-regression acceptance until the
real adapter is connected and all case oracles pass.

### Local offline commands

\`\`\`sh
python -m pip install pytest hypothesis ruff mypy
# After Agent B adds pyproject.toml: python -m pip install -e .
python -m ruff check .
python -m mypy tests/test_acceptance_*.py
python -m pytest -q tests/test_acceptance_*.py
\`\`\`

The workflow requires no network at **test runtime**, Google Sheets
credentials, OAuth tokens, or customer data; pip installation in CI is the
only package download phase. CI runs lint, type check and pytest on Python 3.12.

### Review gate

Agent A must sign off uncertain concentration-boundary semantics, GCI
representation (notably P10), under-threshold non-perfume trace differences
(R10), MiM and ICG classifications, and excerpts versus statutory rules.
The runtime evaluator, optimizer and integration agent must validate whole
sets, not just pairwise relations. No grouping is legally approved by these tests.
