# MVP integration plan — Agent J (issue #11)

**Snapshot:** 2026-11-12; base `main` at `8531f9640cfe8a4d0850ef46b55c2e741c19d37e` when this plan began. **State: PLAN ONLY; no integrated engine, passing CI, legal approval, or end-to-end demo yet.** This plan is a coordination contract; it does not change or approve regulatory rules.


## Execution update — 12 November 2026 (not an approval)

The original plan below is retained as a historical contract. Current live PR/dependency and observed CI evidence are pinned in [mvp-verification-2026-11-12.md](mvp-verification-2026-11-12.md). PRs #13–#20 now exist and remain draft. The integration branch `agent/mvp-integration-2026-11-12` is stacked on E #19 (which contains B/D); C, A, F and J source trees were incorporated as unchanged Git objects. No PR merged. Integration source tests using real C/D/E were added, but **no integrated test execution has been verified**. GitHub Actions run #23 failed without executing job steps (0 ms runner time). The F-owned independent fixture bridge is still missing; no acceptance gate may be waived. **G #16 and I #20 will be staged only after executable green integrated eligibility tests.**

## Ownership, dependencies and merge order

| Stage | Issue / agent | Owned work | Required dependency and integration gate |
| --- | --- | --- | --- |
| 0 | #2 A | `docs/regulatory-*.md`, `docs/rule-traceability-matrix.md`, `rulesets/*.json` | Audit statutory provisions against primary sources, identify policy gaps, request independent regulatory sign-off. A research draft is **not** an executable, approved ruleset. |
| 0 | #3 B | `pyproject.toml`, `src/pcn_grouping/models/**`, `src/pcn_grouping/validation/**`, scaffold | Publish stable canonical models, serialization, hashing, Decimal conventions and error contract; get C/D/E/G/H/I acknowledgements. |
| 0 | #7 F | `.github/workflows/ci.yml`, `tests/fixtures/**`, `tests/test_acceptance_*.py` | Establish offline lint, type-check, pytest, traceable positive/negative/edge/review fixtures. Coordinate test catalogue with A. |
| 1 | #4 C | `src/pcn_grouping/concentration/**`, `tests/concentration/**` | Depends on A/B; agree `find_common_declaration(member_intervals, component_class, ruleset)` and exact boundaries. |
| 1 | #5 D | `src/pcn_grouping/components/**`, `tests/components/**` | Depends on A/B; agree evidence-backed identity key, MiM/GCI/ICG handling and whole-group varying perfumes. |
| 2 | #6 E | `src/pcn_grouping/eligibility/**`, `tests/eligibility/**` | Depends on A/B/C/D; single authoritative `evaluate_group(formulation_revisions, ruleset) -> GroupDecision`. |
| 3 | #8 G | `src/pcn_grouping/optimizer/**`, `tests/optimizer/**` | Depends on E; inject full-group evaluator, re-evaluate each proposed group, deterministic order, never claim greedy global optimality. |
| 3 | #10 I | `src/pcn_grouping/reporting/**`, `src/pcn_grouping/cli/**`, `tests/reporting/**` | Depends on E output and B models; separate eligibility from dossier readiness, stable exports, review audit. |
| 4 | #9 H | `src/pcn_grouping/adapters/**`, `tests/adapters/**`, `docs/google-sheets-data-contract.md` | Depends on B and #1; **offline** CSV/JSON first. Real Sheets mapping/access blocked pending source schema and explicit authority. |
| Cross-cutting | #1 data owner | Anonymised input examples / source-field approval | No production formulation data, supplier SDS or real spreadsheet credentials in source, PRs, fixtures, logs or CI artifacts. |
| Cross-cutting | #11 J | `docs/integration-plan.md`, `docs/definition-of-done.md`; **integration-specific** checks/PRs only | Coordinate contracts, review staged PRs, verify full replay and release readiness; **do not self-merge** or modify feature-owned paths. |

**Required merge order:** (A audit + B schema + F CI) → (C/D) → (E) → (G/I) → (H adapter). Parallel PR drafting is fine; a stage cannot be merged until upstream contracts and gates land. Rebase/update each dependent branch onto the then-current `main`; rerun its full test suite. Any shared-file conflict gets **one named responsible owner** and a reviewed resolution; no last-write-wins merge. Agent J reviews, coordinates, and opens a separate integration PR if needed; an independent maintainer makes merge decisions.

**PR state at plan creation:** no open pull requests returned. Record each new PR link, exact head SHA, upstream API version and CI run in its PR description. This table maps issue responsibilities, not evidence that any task is complete.

## Proposed shared contracts (pending owner confirmation)

These are integration requirements derived from `docs/engine-design.md` and issues #2–#10, **not** pre-emptive choices of Python class names or fields belonging to Agent B. Disagreements are resolved by a documented review with B/E and affected consumers before dependencies merge.

1. **Canonical inputs (B):** immutable `Formulation` revisions with stable ID, source provenance, legal submitter, notification mode, verified full health/physical CLP signature and optional separate environmental CLP data, composition basis and raw BOM. Component records preserve exact actual `Decimal` values or bounded `Decimal` intervals, explicit unknown versus zero, supplier MiM/UFI evidence and verified perfume role. A separate notified-component representation preserves raw-line provenance. No float coercion, inferred classification or name-based identity equivalence. Stable canonical JSON and SHA-256 input digest are insensitive to input ordering but sensitive to meaningful revisions.
2. **Rulebook (A/B/E):** immutable ruleset ID, effective date, approved status, source section and content hash. `rulesets/annex_viii_2026_07_01.research-draft.json` says `RESEARCH_DRAFT_NOT_EXECUTABLE_NOT_LEGAL_APPROVAL`: it is blocked from production PASS paths until audited and independently signed off. A change in rules or effective date creates a new version; old decisions remain reproducible.
3. **Concentration (C):** `find_common_declaration(member_intervals, component_class, ruleset)` uses exact `Decimal` arithmetic and inclusive/exclusive band rules. Returns `PASS|FAIL|REVIEW`, the legal interval/exact declaration if any, rule citation, data-gap or blocking reason; must evaluate every point of cross-band ranges. Unknown inputs yield REVIEW, not zero.
4. **Components (D):** return verified notified identity keys, per-member common/varying matrix, exact varying-perfume sum **per mixture over the whole group**, identity/role/MiM evidence and `PASS|FAIL|REVIEW` reasons. Distinguish A4.3 varying-perfume 5% from B3.2.3 generic perfume 5% and colouring-agent 25%; never infer ICG or supplier identity.
5. **Eligibility (E):** `evaluate_group(formulation_revisions, ruleset) -> GroupDecision`; statuses `ELIGIBLE|INELIGIBLE|REVIEW_REQUIRED`, with per-rule `PASS|FAIL|REVIEW` and statutory/guidance source, evidence IDs, missing-data reasons, candidate declaration ranges, member/revision list, input hash and ruleset hash. **FAIL takes precedence over REVIEW; otherwise REVIEW before PASS.** Chemical eligibility and dossier/submission readiness are separate outputs. `OUT_OF_SCOPE` belongs to separately evidenced applicability, not an eligibility shortcut. Results must not depend on ordering or event timestamps.
6. **Downstream (G/I/H):** G accepts formulation revisions plus an **injected** whole-group evaluator and validates each final group including 3+ members. I consumes the E decision without recomputing law and exports stable, explainable JSON/CSV/HTML; reviewer approval cannot turn a statutory FAIL into PASS. H maps external rows into B's canonical representation with row-level provenance and explicit unknowns; it is read-only by default and no credential dependency is permitted in the core.

**Interface handshake before implementation is considered stable:** B publishes a sample canonical JSON record with decimal **strings**, a concrete serialization/hash policy, unknown-value representation and validation shape. C/D publish function inputs/outputs and rule/error structures. E publishes one minimal `GroupDecision` fixture for each outcome. F adds fixtures for those contracts. G/H/I confirm the formats in their PRs. Record agreements or unresolved differences in the PR conversation; do not silently change a public interface.

## Cross-agent review protocol

- **A ↔ C/D/E/F:** each hard rule ID maps to primary law, effective date, documented interpretation, one PASS, one FAIL, boundary and one missing-evidence REVIEW test. Flag guidance examples as guidance, not statute. Resolve Table 1/2 boundary, trace ingredients and MiM policy before executable eligibility is accepted.
- **B ↔ C/D/E/G/H/I:** stable IDs, canonical hash, `Decimal`/interval types, source identifiers, immutable ordering, classification signature, model/ruleset version and serialisation must agree. No feature agent edits B-owned models without explicit coordination.
- **E ↔ F/G/I:** return deterministic whole-group verdict plus structured reason trace; G must call E again for every final group and I must preserve all failed/review codes. Treat environmental classification and EuPCS changes according to the audited current matrix, not obsolete grouping rules.
- **J:** review PR diffs for ownership, dependency/version drift, security and test evidence; note blockers via PR/issue comments; never approve own legal conclusions or merge own PR.

## Synthetic end-to-end replay gate (NOT YET RUN)

Once A/B/C/D/E/F/G/I are available, build a **fully synthetic, offline** replay from version-pinned inputs and the signed-off ruleset: raw import → B normalization/validation → E whole-group evaluator (using C/D) → G partition → I audit report. H CSV/JSON adapter can be exercised as a separately versioned input path when ready. Pin fixture bytes/hash, canonical model version, ruleset ID/hash, code commit SHA and command line in test artifacts. Exclude volatile review timestamps from deterministic decision digests; preserve timestamps in separate immutable audit events.

Minimum independent cases from `docs/acceptance-tests.md`:

| Fixture | Expected | Replay assertion |
| --- | --- | --- |
| P02 (or P01) | `ELIGIBLE` | Same submitter, approved CLP, verified permitted composition; complete PASS/reason trail. |
| N01 | `INELIGIBLE` | A varying perfume = `5.0001` exceeds `5.0000`; specific failing statutory rule. |
| R03 (or R04) | `REVIEW_REQUIRED` | Missing supplier MiM identity/classification evidence is explicit; never silently PASS. |
| P12 | Full A/B/C group `INELIGIBLE` | Pairwise compatibility must not override 8% varying perfumes in mixture C. |
| M03 / M04 | Stable replay and rule versioning | Reordered source rows/members produce identical decision/hash; changed approved ruleset yields a separately traceable decision. |

Acceptance requires **two independent runs** of the same version-pinned inputs producing byte-identical canonical decision payloads and report content (or a documented separation of immutable audit timestamps), plus stable ordering under shuffled input. Every optimized group of 3+ must have a **fresh full-group** decision record, not just pairwise edges. Capture exact commands, Python/runtime version, complete test count, failed/skipped tests, CI URL and hash comparison in the integration PR. If a package or workflow has not yet landed, mark this gate **BLOCKED**, never passed by assertion.

## Blockers and release note

**As of this snapshot:** B schema/packaging absent; A ruleset is research draft awaiting verification/sign-off; F CI and independent golden ECHA examples not present; C/D/E/G/I/H implementations absent; #1 production source sheet mapping/consent not supplied; no executable MVP, synthetic replay or validated PR exists. Do not say tests pass or that the engine is ready for actual PCN use.

**Implemented in repository at this stage:** research rulebook, proposed architecture, acceptance catalogue and draft machine-readable regulatory research rules. **This PR adds integration planning and governance checks only.**

**Deferred:** executable eligibility and portfolio optimizer, audited rule implementation, full CI, end-to-end replay, read-only Sheets mapping to an actual authorised source, live supplier MiM/ICG exception approval, industrial/standard-formula/fuel special regimes, IUCLID/PCN format validation, legal submission and UFI lifecycle integration. These are not claimed as working or legally approved.

**Release gate for actual use:** independent regulatory subject-matter expert signs the current rule traceability matrix and boundary interpretations; independent code reviewer approves, CI passes offline tests and golden examples, security/privacy review clears inputs/artifacts, and product owner accepts synthetic and authorised redacted real-data UAT. Official PCN submission/validation remains outside the engine and requires human responsibility. See `docs/definition-of-done.md`.
