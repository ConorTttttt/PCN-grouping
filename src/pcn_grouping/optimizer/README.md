# Deterministic portfolio optimiser (Agent G, issue #8)

This module **does not decide legal grouping eligibility**. Call
\`optimise_portfolio(formulations, ruleset, evaluate_group)\` (US alias
\`optimize_portfolio\`) with Agent B's canonical formulations and Agent E's
authoritative \`evaluate_group(formulation_revisions, ruleset)\` implementation.
A returned group is a proposed grouping for regulatory review, never a legal
submission or validation decision.

The v1 greedy planner is **not globally optimal** and makes no claim to
minimise total PCN submissions. Formulations are sorted by immutable
\`(id, revision)\`. A candidate is appended only after a fresh **whole-group**
evaluator ELIGIBLE decision; **every final proposed group** undergoes a
separate full-set re-evaluation. A final FAIL or REVIEW moves all members to the
unresolved queue. Internal metadata pre-filter uses **only** verified submitter,
\`STANDARD_FULL\` notification mode and complete approved health+physical
classification. It never prefilters on EuPCS, environmental hazards, market
country, trade names, or product categories. Incomplete input, duplicate
revision, unsupported submission mode and evaluator failures fail closed into
review/singleton, never a PASS.

\`\`\`python
from pcn_grouping.optimizer import optimise_portfolio

plan = optimise_portfolio(formulations, ruleset, evaluate_group)
# plan.groups: tuple of member-tuples verified again as complete sets
# plan.singletons: valid prefilter records that cannot currently be grouped
# plan.unresolved: record-level unknown/duplicate/final-review items + explanations
# plan.trials: all attempted combinations, result and final-check marker
# plan.globally_optimal is always False
\`\`\`

## Integration dependency

Agent B must confirm \`Formulation.id\`, \`revision\`, \`legal_submitter_id\`,
\`notification_mode\`, and \`approved_health_physical_classification\` names
and classification evidence representation. Agent E must confirm the exact
\`GroupDecision.status\` API. The adapter currently accepts immutable objects,
dataclasses or mappings with the above attributes; anything unknown is
conservatively REVIEW. Only exact returned \`ELIGIBLE\` unlocks a grouping.

The tests under \`tests/optimizer/\` use synthetic evaluator **test doubles**,
not a real regulatory engine; they verify planning invariants rather than legal
eligibility. Once E is merged, integration must add real evaluator contract
tests. No source formulation data or Google credentials are required.

Future optimisation may enumerate all whole-group-eligible subsets, then solve
set partitioning with a verified deterministic exact solver. Until that exists,
\`globally_optimal=False\` is mandatory.
