# Definition of done — PCN grouping MVP integration (issue #11)

**Status: gate specification only, not a compliance certification or assertion that a gate passed.** The MVP is decision support for a human regulatory reviewer, not an official PCN submission or approval service. All gates are **fail closed**: an unverified requirement remains BLOCKED/REVIEW rather than being treated as passed.

## 1. Per-PR code and ownership gate

- [ ] PR references its assigned GitHub issue, scope, owned paths, exact base/head SHA, relevant upstream contract/ruleset version, risk, and user-facing limitations. No agent directly commits to `main` or merges its own PR.
- [ ] Changes are confined to the owner paths listed in `docs/integration-plan.md`. If a cross-owned change is unavoidable, both owners agree and **one** named owner resolves the shared-file conflict before review.
- [ ] PR has at least one independent, qualified code review; regulatory changes require a separate regulatory reviewer. Reviews identify whether the code is a correct implementation of a **signed-off** rule, not a new legal interpretation by a model.
- [ ] Every public interface change has consumer acknowledgement, migration/compatibility note, and adjusted tests. Dependent PRs rebase/update to the latest merged `main`; tests are rerun after changes.
- [ ] PR states implemented versus deferred functionality and provides deterministic reproduction commands, failures, skipped tests and CI link. Approval does not imply legal compliance or permission to submit.

## 2. Regulatory traceability and fail-closed behaviour

- [ ] A's independently verified rule matrix maps each implemented hard gate to exact Annex VIII section, legal URL, effective date, source/guidance distinction, interpretation, evidence requirements, rule version/hash and positive/negative/boundary/REVIEW fixtures.
- [ ] A's `rulesets/*.json` executable version has explicit independent SME sign-off. `RESEARCH_DRAFT_NOT_EXECUTABLE_NOT_LEGAL_APPROVAL` is **not** an approved executable rule version. Historic decisions retain their original ruleset hash and source revision.
- [ ] Eligibility uses deterministic statutory evidence: `FAIL` overrides `REVIEW`, `REVIEW` overrides `PASS`; missing CLP, concentration, identity, perfume role or MiM evidence cannot silently PASS. `OUT_OF_SCOPE` requires separately verified applicability evidence.
- [ ] Group comparison checks one legal submitter, compatible submission regime, complete identical approved health/physical CLP classifications, component identities, one lawful common declared range for every shared component, and permitted varying perfumes capped at **5.0000% per member over the whole group**, including lawfully omitted submitted concentrations. It does not reject a group merely because EuPCS or environmental hazard classifications differ.
- [ ] Table 1/2 feasibility uses only exact `Decimal`, explicit endpoint inclusivity, legally permitted percentage-point widths **across** every crossed band. It does not confuse this with the relative update tolerances for previously exact declarations.
- [ ] Verified GCI/ICG/MiM representations use evidence and distinct statutory tests: varying perfume 5%, generic perfume 5% and generic colouring 25% are **not** interchangeable. No fuzzy identity matches, blanket ingredient filtering, guessed CLP classification or AI/LLM eligibility verdicts.
- [ ] Chemistry eligibility, dossier/market readiness, UFI/update requirements and any out-of-scope applicability result are separate, plainly labelled outputs; no code or report says a PCN was submitted, validated or legally approved.

## 3. Automated test and CI gate

- [ ] F's GitHub Actions workflow installs the pinned Python toolchain, dependencies and project; runs repository lint, type checking and **all** offline `pytest` suites; CI exits nonzero for a failed requirement or missing mandatory core test. State the exact working local commands once B/F publish them.
- [ ] B model/validation tests cover numeric strings versus binary floats, explicit blanks vs zero, bounds/denominator, revision identity, immutability, canonical row-order independence, source provenance and stable SHA-256 digests.
- [ ] C boundary tests cover every Table 1/2 band edge, `0.1/1/10/25` thresholds, exact/legal and just-too-wide ranges, cross-band cases, interval uncertainty, no unsafe rounding and unknown components.
- [ ] D/E tests cover identity evidence, MiMs, GCI/ICG gating, perfume function and `5.0000` versus `5.0001`, pass/fail/review precedence, whole-group 3+ counterexample, CLP classification mismatch, EuPCS/environment non-rules, reproducible citations and full reason traces.
- [ ] F's independent synthetic acceptance and ECHA guidance examples 23–24 have source page and **reviewer verified** expectations; rule-ID coverage table includes PASS, FAIL, threshold/edge and missing-evidence REVIEW. Tests are not copied solely from the implementation.
- [ ] G tests shuffle portfolio order, prove every final group is freshly re-evaluated as a whole, isolate incomplete inputs, retain singletons/review reasons and label greedy as non-optimal. I/H tests cover deterministic report export and offline read-only provenance-preserving ingestion; core CI must not depend on external Sheets.
- [ ] CI and local evidence record exit code, Python version, SHA, number passed/failed/skipped, command, relevant fixture/ruleset digests, and a link to the immutable GitHub check run. **No CI workflow or passing test claim may be inferred merely from a created PR.**

## 4. End-to-end synthetic replay gate

- [ ] Pin an entirely synthetic input snapshot, canonical schema version, legal ruleset ID/effective date/hash, code commit SHA, and verified classification/evidence records. Preserve the raw BOM and original imported source IDs.
- [ ] Replay fixture P02/P01 (`ELIGIBLE`), N01 (`INELIGIBLE`), R03/R04 (`REVIEW_REQUIRED`), and P12 (whole-group **FAIL** despite pairwise compatibility), through input normalization → validation → C/D/E → G → I report. Any unsupported data is a visible REVIEW.
- [ ] Repeat with reordered members/components and on two independent executions: canonical input hash, versioned rule decisions, groups and deterministic report bytes match. Store review/event timestamps separately from canonical decision digests.
- [ ] Verify every final G proposal with the authoritative E evaluator; the report contains each member revision, verified component/classification and concentration ranges, varying perfume totals, `PASS|FAIL|REVIEW` codes, provenance IDs, missing-data questions and both chemical eligibility and dossier readiness.
- [ ] Record the exact replay commands, expected/observed SHA-256 hashes, test and CI logs in a reviewed integration PR. An incomplete replay means **BLOCKED**, not `DONE`.

## 5. Security, privacy and operational hygiene

- [ ] Repository, commit diffs and all fixtures contain only synthetic or specifically authorised anonymised data; **no production/customer formulations, supplier SDS, trade secrets, API keys, auth tokens, passwords or credential files**.
- [ ] Code, CLI and CI logs never dump full supplier compositions, sheet contents, private SDS text or secrets; artifact retention/access is restricted and redaction reviewed. Run a secret scan and check diffs/artifacts before merging.
- [ ] Core algorithms and tests run without network, spreadsheet credentials or LLM inference. Adapter is **read-only** by default; no live Sheets access until data owner supplies mapping, scoped consent and minimal-permission service access.
- [ ] Third-party dependencies and provenance are reviewed, pinned where appropriate and covered by license/security checks. No output automatically files, updates or acknowledges an official ECHA PCN.

## 6. Staged promotion and release decision

1. **Foundation:** A (#2) regulatory audit + B (#3) canonical contract + F (#7) independent CI reviewed; hard-rule ambiguities tracked and signed off before an executable PASS.
2. **Deterministic core:** C (#4) and D (#5) against B/A, then E (#6) whole-group composition. B/C/D/E tests + traceability green.
3. **Portfolio and audit:** G (#8) and I (#10) against E; no claims of global optimum, legal approval or submission; audit/report semantics reviewed.
4. **Adapter:** H (#9) offline path and eventual explicitly authorised sheet mapping; #1 provenance/completeness fulfilled before real dataset ingestion.
5. **MVP release candidate:** independent code and regulatory sign-offs, clean required CI, completed synthetic replay, redacted authorised UAT where available, secret/privacy gate, release notes with all deferred legal features. If any required stage is missing, the status remains **NOT READY**.

**Release-note template (fill with actual evidence, never assumed status):** `base SHA / merge SHA; PR links; implemented ruleset ID+hash+effective date and SME sign-off; test commands+pass/fail/skip+CI links; canonical fixture/input digest; replay results for ELIGIBLE, INELIGIBLE, REVIEW_REQUIRED and P12; security/privacy review; deferred scope; unresolved legal questions; named independent approvers and date.`

**Legal-use boundary:** even a green CI and signed-off decision-support tool does not certify compliance. A qualified regulatory professional must review classifications, supplier evidence, applicable law, dossier data and appointed-body submission obligations for each real notification; ECHA/Member State acceptance is external to this project. Agent J never self-merges or declares legal compliance.
