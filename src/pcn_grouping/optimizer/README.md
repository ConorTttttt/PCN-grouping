# Deterministic portfolio optimiser (Agent G, issue #8)

The optimiser is a deterministic **proposal generator**, not a CLP
eligibility authority, dossier checker, or PCN submission tool. It makes no
chemical inference. Every candidate extension and every final group with two
or more members is independently checked by the caller-injected whole-group
evaluator. Only a final exact `ELIGIBLE` decision allows a proposal.

## Contract aligned with Agents B and E

```python
from pcn_grouping.eligibility import EligibilityContext, evaluate_group
from pcn_grouping.optimizer import optimise_portfolio  # or optimize_portfolio

plan = optimise_portfolio(formulations, eligibility_context, evaluate_group)
```

- Inputs: a sequence of B `Formulation` records (`formulation_id`, `revision`).
  Legacy `id` is accepted for compatible synthetic adapters, but inconsistent
  `id` and `formulation_id` are isolated for review.
- `EligibilityContext` must provide per-revision `ReviewedClassification`
  attestations; the planner checks uniqueness and independently documented
  verification before using a finished health/physical CLP signature as a
  candidate key. Each CLP row also needs `VERIFIED` status and source IDs.
  The comparison includes hazard class, category, H-code, route and qualifier,
  **not** reviewer IDs, evidence sources, EuPCS, environmental hazard classes,
  market countries or product names.
- Legal submitter must be a non-empty authoritative ID and mode must be
  `STANDARD_FULL`. The identifier is **not itself a verified legal-duty-holder
  attestation**; the evaluator and regulatory review remain responsible for
  establishing that the source ID is authentic and corresponds to the duty
  holder. Missing/unknown regimes or evidence are isolated as unresolved.
- Passed evaluator decisions may use E's `GroupStatus` enumeration. Reasons
  include structured failed/review rule codes from `EligibilityDecision`.
- `plan.groups` contains only freshly re-evaluated full groups;
  `plan.singletons` contains records with no selected partner;
  `plan.singleton_reasons` explains each singleton (including candidate
  evaluations needing review);
  `plan.unresolved` contains incomplete inputs, duplicates and failed final
  validations; `plan.trials` records each attempted combination.
- Every input record is in exactly one of groups, singletons or unresolved.
  `singleton_reasons` is supplementary metadata for singletons.
- The evaluator's independent dossier and applicability checks are not
  replaced. An out-of-scope or research-draft result must never be promoted.

## Algorithm and limitations

Version `stable_greedy_v1` sorts by immutable formulation ID/revision. It
forms preliminary candidate blocks by legal submitter, standard-full regime
and complete health/physical hazard signature. It walks each block in stable
lexical order, tentatively appending a member **only if the whole new set**
passes the injected evaluator. Each output group is then evaluated a second
time. A post-check failing or requiring review moves the whole group to
`unresolved`; a pairwise-compatibility graph is never accepted as proof of
a valid three-or-more-member group.

The algorithm is intentionally **greedy and not globally optimal**:
`plan.globally_optimal` is always `False`. It does not establish the minimum
number of submissions. A future exact set-partition solver could enumerate
only fully evaluator-approved subsets, use integer decision variables with
one selected subset per formulation and minimise subset count, then
revalidate every selected set; it would require an explicit optimality
certificate or an honest timeout/unknown result.

No percentages are computed or rounded in this module. Exact-Decimal
concentration constraints, perfume caps, identity resolution and all legal
rules belong to C/D/E, backed by approved, version-controlled rulesets.

## Validation and release gates

Existing `tests/optimizer/test_planner.py` is a legacy synthetic evaluator
contract. The additional `test_contract.py` checks Agent B's canonical
`formulation_id` shape, Agent E's evidence/enum shape, permutation
invariance, whole-set counterexamples, duplicates, reasons and fail-closed
behavior. **These are planning tests, not independent regulatory golden
tests.** Full-stack B+D+C+E+G CI and independent regulatory and integration
reviews are still required before any real PCN use. In particular the
concentration solver is on a separate feature PR, and current production
rules remain a research draft.
