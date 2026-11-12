# Agent I — offline grouping audit and reviewer workflow (#10)

**Not a PCN filing, legal determination, ECHA format validator, or dossier approval.** This module **displays** a previously evaluated `EligibilityDecision` supplied by the E engine. It never guesses chemical identity, compares concentrations for legality, upgrades a verdict or calls a network service. The checked-in example is fully synthetic and **illustrative only**, not an actual output of a signed-off regulatory engine.

## Source and ABI

Stacked on draft E PR #19 (`agent/eligibility-engine`), with B model PR #14 and D component PR #18 as dependencies. Reporter reads a **JSON snapshot**, not the research-draft ruleset:

```json
{
  "schema_version": "1",
  "formulations": ["B Formulation objects as dictionaries"],
  "decision": "E EligibilityDecision as a dictionary"
}
```

The illustrative placeholders above are **not** a valid snapshot. Use `synthetic_demo_snapshot.json` as the exact schema example. To capture a real E decision in an authorised offline caller, use `pcn_grouping.reporting.to_wire` on B `Formulation` / E `EligibilityDecision` dataclasses and `json.dumps(..., sort_keys=True, ensure_ascii=False)` to create `{"schema_version":"1", "formulations": [...], "decision": ...}`. Never pass floats: all concentration values and limits must be Decimal-derived **strings**. Avoid storing private source formulas in CI, tickets or PRs.

The reporter consumes:

- `status`, `dossier_status`, `applicability_status` separately; `dossier_status` is **only** E's field-presence diagnostic. The independent summary `submission_readiness=NOT_VERIFIED` is never changed to "ready" by this module.
- `ruleset.{ruleset_id,effective_date,sha256,status}` and `canonical_input_hash` for reproducibility and evidence context.
- Whole-group member revision IDs, `rule_results` (source sections, evidence IDs, `values`/reason codes), per-member names/UFI/colour/physical state/pH/packaging/uses, source document provenance and CLP signatures.
- `component_matrix`, `common_ranges`, `varying_perfume_totals` and `perfume_classification_matrix`. Concentration ranges are copied **verbatim**, not revalidated or rounded. Missing arrays are printed "Not provided"; missing source or dossier fields appear as data gaps.

**Important integration detail:** ECHA Guidance §5.4.1 permits a **group-wide pH range**, with a guidance recommendation about narrow ranges at extreme pH; absence of per-formulation pH must *not* be treated by this reporter as a chemical grouping failure or necessarily a dossier defect. Agent E's field-presence status is faithfully displayed, not overridden. Updates under B.4.1, including the fifth indent future-effective 2027-01-01, remain the regulatory/lifecycle team's responsibility, not a reporting rule.

## Offline commands

Run with an installed editable project or `PYTHONPATH=src`:

```bash
python -m pcn_grouping.cli report \
  --input src/pcn_grouping/reporting/examples/synthetic_demo_snapshot.json \
  --output-dir /tmp/pcn-demo

python -m pcn_grouping.cli review \
  --input src/pcn_grouping/reporting/examples/synthetic_demo_snapshot.json \
  --audit /tmp/pcn-demo/review.json \
  --status REJECTED --reviewer example-human-reviewer \
  --reason 'Illustrative hard perfume-cap failure' \
  --timestamp 2026-11-12T18:00:00Z

python -m pcn_grouping.cli report \
  --input src/pcn_grouping/reporting/examples/synthetic_demo_snapshot.json \
  --audit /tmp/pcn-demo/review.json --output-dir /tmp/pcn-demo
```

Outputs: `decision.json` (stable machine-readable schema), `decision.csv` (section/name/status/canonical JSON detail rows), `decision.html` (standalone, self-contained, HTML-escaped audit report). All export table and array order is stable under shuffled formulations/decision rows. No generated timestamp contaminates the deterministic decision exports. A reviewer event contains an **explicit ISO-8601 timezone-aware immutable timestamp** (or a UTC capture time from the CLI when omitted), reviewer ID, reason, review status and previous/event hashes.

## Reviewer safety and limitations

An absent audit file means `PENDING`. `PENDING`, `APPROVED`, and `REJECTED` are **human workflow statuses** and cannot alter `decision.status` or turn a statutory FAIL into PASS. `APPROVED` is blocked unless E says `ELIGIBLE`, applicability is evidenced in scope, the ruleset status is `APPROVED`, and there are no non-dossier FAIL/REVIEW rule rows. Even a reviewer-approved record is **not** automatically dossier-ready, ECHA-validated or legally approved. `REJECTED` and `PENDING` record review workflow without changing chemistry.

Every event is SHA-256 linked to the full *unreviewed* report digest and previous reviewer event, and every load checks the entire chain. The API returns a new log instead of mutating earlier in-memory events. **JSON files are not write-once audit storage**: a privileged editor could rewrite/recompute all hashes. For legal retention, add access control, external time attestation, write-once storage/backups and independent reviewer identity authentication at integration time. `--timestamp` supplied by a caller is a claim, not a trusted timestamp authority. No account login or identity validation occurs in this CLI.

## Synthetic demonstration and feedback

Open `examples/synthetic_demo_report.html` in a browser. It shows two fake mixture revisions, shared component range `94.9999–95`, a `5.0001%` varying-perfume **example FAIL**, a separate dossier **REVIEW**, source/evidence IDs, a draft ruleset flag, and the pending reviewer queue. This is a **UI/report-display test only**. It is not a tested conclusion from Agent E, a legal example, an ECHA notification, a UFI assignment or a submission-ready dossier. For feedback, check whether a reviewer can see *every* failure, source/evidence gap, trade-name/UFI mapping, per-member perfume total and the separate dossier status.

## Test gate

```bash
PYTHONPATH=src python -m pytest -q tests/reporting
PYTHONPATH=src python -m compileall -q src/pcn_grouping/reporting src/pcn_grouping/cli
```

These tests prove reporter behaviour only. The combined B/C/D/E/F/I integration suite and independent regulatory signoff are **not yet demonstrated** by this feature. Rebase/retarget onto `main` after upstream reviewed merges. Do not merge this draft PR until Agent J, E, F and a regulatory reviewer sign off.
