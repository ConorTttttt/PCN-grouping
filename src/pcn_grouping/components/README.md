# Component evidence layer — Agent D / issue #5

This module implements deterministic **component-level** checks against Agent B's
immutable models. It does not decide overall grouping eligibility, approve legal
interpretations, create ICGs, calculate mixture classifications, or validate an
ECHA submission. Draft rule files cannot yield an overall component PASS.

## Integration contract

```python
from pcn_grouping.components import ComponentRules, analyse_components

rules = ComponentRules.from_json(rule_file_bytes, approval=existing_rule_approval)
analysis = analyse_components(formulation_revisions, evidence_catalog, rules)
```

Dependency: PR #14, `agent/core-schema`, commit
`7b89fd320096993ffc0beb1acf342057940ad92f`. No shared schema fields were changed.
`EvidenceCatalog` is an immutable D-owned sidecar. It must be versioned with the
input by the integration layer. Agent J/B/E interface acknowledgement is pending;
handoff is posted on issues #11 and #2. The PR is stacked on `agent/core-schema`;
retarget/rebase to main after the independently reviewed schema merges.

| Input | Contract |
| --- | --- |
| `IdentityRecord` | Explicit canonical ID, substance/MiM kind, permitted identifier scheme/value, reviewed source evidence. MiMs also bind exact supplier and product IDs. |
| `IdentityAlias` | One-hop exact ID mapping scoped by kind and supplier. No fuzzy matching, transitive alias chains, name equivalence, or cross-supplier/UFI guessing. |
| `LineEvidence` | Scoped by `(formulation_id, revision, line_id)`; complete classification evidence, verified function, exclusive-function flag for GCI, MiM route and optional notifiability evidence. |
| `MiMRouteEvidence` | `UFI_PRIOR`, `UFI_SDS`, `NO_UFI_SDS`, or `FULL_COMPOSITION`. Route evidence is supplied by a reviewer; UFI format alone is insufficient. |
| `RepresentationApproval` | Existing GCI/ICG identifier, canonical member IDs, exact formulation revisions, ruleset SHA-256 and reviewed approval/criteria evidence. Every named member must have a verified registry identity. |
| `ComponentRules` | Projection of A's version-controlled JSON bytes; exact file hash, ID, effective date and status retained. Percentages must be decimal strings. Approval requires explicit `APPROVED` source status and reviewer evidence; a supplied approval cannot override draft status. |

Evidence requires `VERIFIED`, a nonempty ID, source document IDs, reviewer and
verification date. These are assertions from a trusted review workflow, **not a
cryptographic signature or an authentication mechanism**. This module does not
generate or independently certify those assertions. Importers must verify them,
keep revision IDs immutable, and retain referenced records. Confidential SDS or
supplier contact data belongs in access-controlled storage, never test fixtures.

Technical functions `PERFUME` and `COLOURANT` are explicit canonical role labels
(case/outer whitespace are normalized). Arbitrary other role labels remain exact
technical functions; a perfume name is never used to infer a role. An empty CLP
list means non-classified only when the sidecar attests classification completeness.

## Output and downstream responsibilities

`ComponentAnalysis` exposes:

- `status`: component comparison `PASS|FAIL|REVIEW`; FAIL precedes REVIEW.
- `disclosure_status`: separate perfume classification/omission checks. Neither
  status is a full dossier-readiness or legal-compliance verdict.
- Raw and notified common/varying keys, computed across the **entire** group.
- One immutable matrix row per normalized input component with original BOM
  references, evidence IDs, source documents, classifications, actual bounds,
  declared identity and omission marker. Even zero/trace rows are retained.
- Per-revision varying-perfume totals and contributing line IDs. Unknown identity,
  presence or function gives unknown totals/REVIEW, not an apparent zero pass.
- Agent B `RuleResult` records with stable regulatory rule IDs, machine-readable
  `code` and `scope` in `values`, evidence IDs, section references and exact bounds.

Identity keys are `(kind, canonical_id)` tuples; they do not include display names,
row IDs or concentrations. Unresolved keys are `None`, never a shared "unknown"
identity. Common sets in a REVIEW result are provisional diagnostics and must not
be used to approve a group. Repeated valid BOM lines for the same identity sum;
duplicate line IDs instead require review. Input objects are never mutated.

B's structural validation and E's scope, submitter, classification, effective-date
selection and complete grouping checks remain mandatory. C/E must validate common
declaration ranges, including aggregated GCI/ICG concentrations. This module does
not validate the numerical contents of `NotifiedComponent.concentration`; its
disclosure check concerns omission and classification only. E must not interpret
component PASS as `ELIGIBLE`. I/reporting must preserve the separate disclosure
status and all evidence references. No global trace-deletion threshold is applied.

## MiM / identity handling

CAS and EC formatting/checksums are checked when supplied; missing CAS/EC can use
a reviewed unequivocal CLP Article 18, INCI, colour-index or international chemical
identifier. This validates evidence/format, not registry existence or chemical
equivalence. Unsupported/confidential identities require REVIEW; an unidentified
supplier blend is never considered equivalent to another blend.

For partial MiMs, identity and function must be known. `UFI_PRIOR` additionally
requires reviewed UFI validity and prior-recipient evidence for **every declared
destination country**. UFI-with-SDS and no-UFI routes require the exact SDS reference,
an attestation that SDS compositional information and other known components are
captured, supplier name/email/phone and contact evidence. Classification completeness
and actual concentration are mandatory. These references attest to a stored
composition; this module does not parse SDS documents. Conflicting UFI values for
the same canonical MiM trigger REVIEW.

A fully known MiM represented as one unexpanded blend returns
`FULL_MIM_REQUIRES_UPSTREAM_CONSTITUENT_EXPANSION`. The upstream normalizer must
provide constituent records and their original source provenance. Automated nested
MiM expansion is deferred because B's initial schema has no constituent tree. This
prevents silently accepting a full-composition route without the required detail.

## Representation and numerical semantics

The approved notified view must cover raw component line IDs exactly once. A
representation label, an `APPROVED_GCI`/`APPROVED_ICG` enum or a human-like name
alone provides no approval. Invalid/missing approval scopes remain REVIEW; a proven
violated GCI condition remains FAIL. Raw actual identities are retained separately.

GCI requires reviewed exclusive function and complete health-hazard-free component
classification. All GCI perfume lines in a mixture aggregate under the separate
5% cap; colouring-agent lines aggregate under 25%, even if declarations are split.
The A.4.3 calculation counts raw identity/presence-varying verified perfumes across
the whole group and excludes raw identities common to every member. A shared
notified GCI cannot hide differing actual perfume ingredients. Concentrations
omitted from a dossier still count internally. These semantics follow A's handoff;
independent SME review of GCI representation scope remains required.

Substitutions wholly covered by a common validated pre-existing ICG use that
permitted notified identity under A.4.2 rather than invoking A.4.3; their raw
members remain visible in the matrix but are excluded from the A.4.3 total.
This precedence was posted to A's issue #2 for explicit SME review.

ICG accepts only scoped **pre-existing** reviewed validation. General-path evidence
must cover component identification, concentration data, identical classification,
same function, same toxicology and all-combination invariance. Alternative-path
evidence must cover identification, concentrations, identical classification,
allowed hazards, pH band and all-combination invariance, with at most five members.
This is an evidence gate, not a toxicology/combinatorial engine or a new ICG approval.
Conflicting current classifications/functions require REVIEW even if prior approval
is asserted. Extended environmental/physical classification edge interpretations
remain subject to SME review; the implementation conservatively requires a
consistent declared representation.

Actuals are `Decimal` or inclusive intervals; missing is not zero. Sums use integer
coefficients and decimal exponents so ambient `Decimal` precision cannot round a
tiny excess down to 5%. For verified membership, an upper bound at/below the cap
passes, a lower bound above it fails, and a straddling interval requires REVIEW.
Mixed/unknown percentage bases require REVIEW; no implicit conversion is attempted.

## Regulatory and test provenance

Read before implementation: issue #5 and A's handoff, main README/engine design and
acceptance catalogue, B PR #14 models, J PR #12 integration plan, and A PR #13's
regulatory requirements, traceability matrix and current research JSON. Governing
IDs are `REG-SUBSTANCE-ID`, `REG-MIM`, `REG-COMPONENTS`, `REG-PERFUME-IDENTITY`,
`REG-PERFUME-CAP`, `REG-PERFUME-MAP`, `REG-GCI`, `REG-ICG`, `REG-PERFUME-OMISSION`.
`COMP-RULESET-APPROVAL` is an integration gate, not a statutory rule.

Primary-law cross-check: [Regulation 2020/1677, Annex VIII A.4.3 and B.3.2–3.5](https://eur-lex.europa.eu/eli/reg_del/2020/1677/oj)
and the [2026-07-01 consolidated baseline](https://eur-lex.europa.eu/eli/reg/2008/1272/2026-07-01/eng)
audited by A. Rules were not newly approved in this implementation. No future
lifecycle obligations were added. The repository research ruleset remains blocked
from overall PASS; tests explicitly verify that block.

`tests/components/test_components.py` uses synthetic chemicals and reviewer records.
The example-23 arithmetic test uses A's transcribed varying totals 2.8/3.2%; its
base/shared quantities are **synthetic completions**, not an independently validated
ECHA golden fixture. Example-24-style three-member membership is tested without
inventing authoritative concentrations. Independent F/regulatory review is pending.

Run from the repository root with its dev dependencies installed:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/components tests/schema
python -m ruff check src/pcn_grouping/components tests/components
python -m mypy src/pcn_grouping/components
```

Release gates: B/J/E contract acknowledgement, A/SME regulatory evidence and
interpretation review, F independent fixtures/CI, reviewed upstream merges and
complete C/E integration. Do not self-merge or claim legal compliance.
