# Deterministic PCN grouping engine — proposed design

**Status:** design proposal, 12 November 2026. The regulatory text and source mapping live in [regulatory-requirements.md](regulatory-requirements.md).

## 1. Product definition and boundaries

Build two separate deterministic services:

1. **Eligibility evaluator**: given a non-empty set of complete, normalized formulations and a versioned rulebook, return `ELIGIBLE`, `INELIGIBLE` or `REVIEW_REQUIRED`, with structured rule-by-rule evidence. Can check a pair or any number of mixtures.
2. **Portfolio grouping planner**: given a portfolio, propose a partition into valid groups by repeatedly invoking the group evaluator. Its recommendations are not approvals. Every proposed group must be revalidated against the group-level predicate before output.

A separate **PCN applicability** module can return `OUT_OF_SCOPE` based on evidence; a separate **dossier-builder** will eventually turn accepted group decisions into ECHA-compatible files. Never equate a grouping recommendation with a successful or legally valid filing.

Suggested implementation: **Python 3.12**, typed immutable models (Pydantic or dataclasses), `decimal.Decimal` for concentrations, `pytest` tests, CSV/XLSX/JSON adapters. Isolate rule logic from a later FastAPI service and web UI. A deterministic optimization library may be introduced after eligibility is reliable.

## 2. Minimal canonical data contract

Use revisioned, auditable records, not anonymous spreadsheet rows.

```text
Formulation
  id, revision, source_document_ids
  legal_submitter_id, notification_mode, market_countries
  approved_health_physical_classification[]  // class, category, H code, qualifiers/route
  approved_environment_classification[]      // stored but NOT eligibility blocker
  use_types[], euPCS[], product_names[], UFIs[]
  colour, physical_state, pH, packaging[], sds_section_11
  composition_basis: MASS_PERCENT | VOLUME_PERCENT
  components[]                              // underlying formulation and declared view

Component
  canonical_identity_id
  kind: SUBSTANCE | MIM | APPROVED_GCI | APPROVED_ICG
  verified_identification_method, UFI/supplier data if MiM
  min_actual_pct, max_actual_pct           // inclusive bounds, Decimal
  health_physical_hazards[]                 // determine major-concern rule
  technical_function
  perfume_role_evidence_id | null
  declared_identity_id | null              // canonical notified representation
  declaration_exemption_code | null
  source_document_ids, confidence/evidence_state

GroupingDecision
  status
  formulation_revision_ids[]
  ruleset_id, ruleset_effective_date, ruleset_hash
  canonical_input_hash
  rule_results[] {rule_id, PASS|FAIL|REVIEW, evidence_ids, values, explanation}
  declared_common_component_ranges[]
  varying_perfume_by_formulation[]
  product_to_perfume_classification_matrix[]
  reviewer_status, reviewer_id, decision_timestamp
```

If imported formulas are provided in mass and volume fractions, convert only using verified density information and a defined temperature/condition; otherwise `REVIEW_REQUIRED`. Inputs need a consistent denominator and sum to 100% within a documented measurement tolerance. Never convert percentages to binary floats.

Canonical identifiers must resolve synonym/CAS/EC ambiguity explicitly; distinct MiM products/UFI records cannot be silently collapsed. Component aggregation across multiple lines must be recorded and explained. Keep the raw BOM untouched and create a separate normalized notified-component representation.

## 3. Rule pipeline, in order

```text
a. Validate source completeness and input constraints
   -> missing ingredients, unknown classifications, MiM status, ppm conversion,
      inconsistent percentage basis, missing perfume evidence => REVIEW.

b. Check scope / legal submitter / submission mode
   -> out-of-scope is a separate applicability result.
   -> different legal submitters => INELIGIBLE.

c. Compare complete health + physical classification signatures
   -> unequal => INELIGIBLE. Environmental hazard difference alone is allowed.

d. Construct permitted declared-component representations
   -> verified substance/MiM identities or separately validated GCI/ICG.
   -> unapproved component aggregation => REVIEW, not a guessed PASS.

e. Compute group-level membership:
   common = intersection of component identities across ALL members.
   differing = union of component identities minus common.
   If any differing component is not a verified perfume => INELIGIBLE.
   For each member:
       sum ACTUAL upper bounds of its differing perfumes <= 5.0%
       else => INELIGIBLE or REVIEW if upper-bound uncertainty can be resolved.
   A varying component may be present in a subset, not necessarily only one mixture.

f. For every common component, find ONE legally permitted submitted range
   encompassing actual lower/upper bounds of ALL members.
   (Or one exact value if all member concentrations coincide.)
   Enforce correct Table 1/2 width at every point in the interval.
   If no range exists => INELIGIBLE.

g. Validate disclosure of differing perfumes per mixture:
   identities, classifications, legally required concentrations/exception,
   and per-product matrix.
   Check GCI 5% perfume/25% colouring ceilings as a DIFFERENT test.

h. Validate dossier metadata completeness separately from chemical
   eligibility (per-product trade names, UFI, colour, state, pH, packaging,
   use/EuPCS, language/destinations, toxicology).
   -> if incomplete, grouping may be chemically eligible but NOT export-ready.

i. Emit a deterministic explanation and a canonical reproducibility hash.
```

**Critical:** evaluate a *whole group*. A-B eligible and B-C eligible does not prove A-B-C eligible (shared concentration range or the differing-perfume union can fail).

## 4. Correct interval feasibility, not simple rounding

For all actual concentrations of a common component, define `lo=min(member_lower)`, `hi=max(member_upper)`. The narrowest candidate is `[lo, hi]`. It is feasible under Table 1 or 2 if for **every** value that interval could cover, its width `hi - lo` does not exceed the width legally allowed for that value's concentration band. If this candidate fails, widening cannot help. Output an explicit compliant declared range, optionally rounded *outward* only when that preserves legal width.

Example: major-concern component values 9.7% and 10.5% yield [9.7,10.5], width 0.8, which respects the lower band's 1-point maximum and upper band's 3-point maximum; possible. But 9% and 11% yield width 2, violating the lower band's 1-point maximum; not possible. Check other components in the same way.

If only an uncertain ingredient interval is known, a conservative upper bound permits eligibility only when **all** actual values are compliant. If the uncertainty interval straddles 5% for varying perfumes, return `REVIEW_REQUIRED` unless exact actual evidence can resolve it; do not declare a conclusive failure solely from uncertainty.

Consider declared component identity and classification as part of the data contract; a component-classification disagreement between sources is a data review issue, not something to guess.

## 5. Grouping candidate selection and optimization

Start with known compatible **standard submissions**: identical reportable composition can support multiple trade names even without invoking the perfume-variance group exception. Then explore fragrance-variant **group submissions**.

Candidate-block key (pre-filter only): legal_submitter_id + notification regime + complete health/physical CLP signature. Do NOT block just because environmental hazard, brand name, EuPCS or country differs.

Within a block:
- Stable-sort formulations by immutable IDs.
- Generate eligible group candidates using the **whole-group** eligibility evaluator.
- First implementation: deterministic, documented greedy partition and separate ungrouped list; report that the partition is *not proven minimal*.
- Later for manageable portfolio sizes: exact minimum-number-of-groups/set-partition optimization over eligible candidate groups with stable tie breaking. For large sets, bounded heuristic with clear optimization status and runtime cap.
- Secondary objectives can prefer current dossier membership and reduce rework/UFI churn. Never weaken legal conditions for fewer notifications.

Never use pairwise connected components / union-find as final groups.

## 6. Explainability, audit and revisioning

Each group decision must show:
- input formulation IDs/revisions and data source IDs;
- legal rules cited at precise Annex VIII section level;
- common/non-common component matrix and concentrations;
- planned declaration ranges and applicable Table 1/2 max widths;
- variable perfume sums, **including perfumes whose reported concentration is lawfully omitted**;
- passes, failed reasons, and review flags, with no hidden threshold or heuristic decisions;
- whether classification information was certified/approved;
- ruleset date/hash and immutable decision timestamp;
- which products still lack UFI/dossier fields.

Rule configurations must carry effective dates. Any future amendments, ECHA format updates or validation changes must create a **new rule version**, preserve prior decisions and trigger re-evaluation rather than rewrite decision history.

Store supplier ingredient data access-controlled. Log activity; avoid committing commercial formulations, secrets or supplier SDS files to GitHub.

## 7. Release plan and acceptance gates

| Phase | Deliverable | Acceptance gate |
| --- | --- | --- |
| 0: source/data discovery | real input column mappings, component identity standards, legal owner, sample anonymized formulations | representative fixtures approved |
| 1: eligibility core | standard + perfume group rules, legal range solver, MiM identity, GCI prevalidation, explanations, CLI, tests | fixture suite matches ECHA worked examples and edge cases |
| 2: portfolio grouping | reproducible candidate groups, stable ordering, invalid/unknown queues, exports | every output group revalidates; reproducible across runs |
| 3: workflow UI | CSV/XLSX ingestion, review decisions, side-by-side composition diff, Excel/JSON reports | regulatory user acceptance on real portfolio |
| 4: dossier integration | PCN format v8-compatible export and validation, submission status tracking and updates | ECHA validation against selected target format |
| 5: advanced exceptions | ICG reasoning, limited submissions, standard formulas, fuels, supplier MiM chains | independent domain review and exception-specific fixtures |

### Decisions required before production implementation

1. What is the source of truth for formulations (ERP/PLM/SDS database/CSV/XLSX) and do the files contain **full actual** ingredient compositions and classifications?
2. Are we grouping mainly cosmetic fragrance/detergent variants, industrial mixtures, or several sectors?
3. Is this a **planning** aid (identify possible groups) or must it also produce IUCLID/PCN dossiers, UFIs and submit updates?
4. How are supplier MiMs and confidential perfume blends identified (UFI, CAS constituents, supplier code, SDS)?
5. Who approves perfume function, GCI/ICG applicability, CLP classification and the final group before notification?

Recommendation: start with an independently tested **Python grouping library** and structured imports, then add a lightweight UI; do not begin with an LLM workflow or XML export.
