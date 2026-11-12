# Offline test evidence for Agent G #8

Local verification carried out **2026-11-12** with **Python 3.13.5** and
`pytest 9.0.2`. The tested three source files were checked against their
GitHub blob SHA-1 hashes; these are **byte-for-byte identical** to the
`agent/portfolio-optimizer` branch:

| Repository file | Git blob SHA |
| --- | --- |
| `src/pcn_grouping/optimizer/planner.py` | `2b77b270c51ace0be68db4064bd3f640e47197a9` |
| `src/pcn_grouping/optimizer/__init__.py` | `23329fe13ca92024c83826a0f1be2fd7dafe2a5d` |
| `tests/optimizer/test_planner.py` | `d46d31ebb45ed92e342c2830734313536e866218` |

Commands run on the isolated local copy:

```sh
PYTHONHASHSEED=0 python -m pytest -q tests/optimizer/test_planner.py
# 36 passed in 0.06s

PYTHONHASHSEED=123 python -m pytest -q tests/optimizer/test_planner.py
# 36 passed in 0.05s

python -m compileall -q src/pcn_grouping/optimizer tests/optimizer
# success (no errors)
```

The 36 tests include 24 permutation orders, fail-closed unknown data,
non-blocking EuPCS/environment changes, deterministic CLP ordering, duplicate
revision isolation, a pairwise-but-not-whole-group failure, and a **second
fresh evaluator call** before final grouping.

**Limitations:** The tests use synthetic injected evaluator *doubles*,
not Agent E's regulatory evaluator, which is not yet integrated. Python 3.12,
ruff, mypy and repository-wide CI are **not yet independently verified**.
Agent F's separate CI workflow PR #15 has currently failed before runner
assignment (`runner_id=0`, no job steps), so no CI pass is claimed.
Neither these results nor an optimiser grouping constitute legal approval.
