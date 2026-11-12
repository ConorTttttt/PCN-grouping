# Agent G issue #8 — reproducible optimiser test evidence

## Previously recorded on the original draft branch

The prior `agent/portfolio-optimizer` implementation was tested on
2026-11-12 in isolation with Python 3.13.5 / pytest 9.0.2: 36 synthetic
planner tests passed with PYTHONHASHSEED=0 and again with 123. The original
source hashes and commands are preserved in PR #16 history. Those tests
were run **before** the Agent B/E ABI compatibility revision.

## Verified locally for the ABI compatibility revision (2026-11-12)

Development environment: Python 3.13.5, pytest 9.0.2.

```console
$ cd <checkout>
$ PYTHONHASHSEED=0 PYTHONPATH=src pytest -q tests/optimizer
........................................................................ [ 97%]
..                                                                       [100%]
74 passed in 0.14s

$ PYTHONHASHSEED=123 PYTHONPATH=src pytest -q tests/optimizer
# 74 passed in 0.09s

$ python -m compileall -q src/pcn_grouping/optimizer
# success
```

The tested files are byte-identical to the GitHub uploaded blobs
(`git hash-object` verified):

- `src/pcn_grouping/optimizer/planner.py` —
  `e27eb563ebd0d1ddbc6e78c88c646aea5af62d56`
- `tests/optimizer/test_contract.py` —
  `b49031fd2485f7d90aed5a4aa036657f00faf0f1`
- `tests/optimizer/test_planner.py` (original legacy suite) —
  `d46d31ebb45ed92e342c2830734313536e866218`

Both locally re-run suites, totaling 74 tests, pass at two hash seeds.
The new suite includes **24 input-order permutations**, checked canonical
`formulation_id` mapping, reviewed evidence isolation, full CLP signature
comparison (excluding unrelated evidence source IDs), verified flags,
duplicate-revision canonical ordering, whole-set triple counterexample,
non-blocking environmental/EuPCS/market metadata, singleton audit reasons
and mandatory fresh post-validation. The injected oracle is explicitly
synthetic and never determines legal eligibility.

**Not yet verified:** full-stack tests against merged B+D+C+E, Python 3.12,
Ruff/Mypy CI, and any regulatory SME sign-off. Agent E's API was read and
consumed structurally but its unmerged implementation was not run in the
local optimiser-only test environment. The current ruleset is a
research draft. No production data or supplier SDS were used.

**This evidence proves only planner invariants; not CLP/PCN compliance.**
