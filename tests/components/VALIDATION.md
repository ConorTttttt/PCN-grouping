# Agent D validation evidence — 12 November 2026

Dependency snapshot: Agent B PR #14, commit
`7b89fd320096993ffc0beb1acf342057940ad92f`, tree
`8434058acb01ebb4acd22df6cce976fc681252ff`.
All 12 upstream files were fetched through GitHub and verified against their
Git blob SHAs; the reconstructed dependency tree matched that tree exactly.
Only `src/pcn_grouping/components/**` and `tests/components/**` are changed.

Observed local environment: Python 3.12.14, pytest 9.2.0, Ruff 0.17.4,
Mypy 2.4.1. Tool dependencies were installed outside the repository; no package
or CI configuration owned by another agent was modified.

From the repository root, with the installed dev tools on `PYTHONPATH`:

```text
$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
......................................................................   [100%]
70 passed in 0.11s

$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 10 source files
```

The total comprises **59 component tests and 11 unchanged schema tests**.
Disabling pytest plugin autoload avoids unrelated host plugins; these tests need
no additional pytest plugin. The entire available B+D snapshot was checked, not
only the new files. No GitHub Actions pass, independent QA approval, completed
end-to-end engine replay, or regulatory compliance is asserted by these results.

Coverage includes explicit aliases versus similar names; CAS/EC/UFI formatting;
missing/confidential identity; exact 5%/25% boundaries; precision beyond the
ambient Decimal context; shared perfume exclusion; whole-group versus pairwise
failure; unknown actuals and interval bounds; retained trace and zero lines;
MiM prior-recipient, UFI+SDS and no-UFI evidence gaps; unknown MiM function;
unexpanded fully known MiMs; approved versus merely claimed GCI/ICG; split GCI
declaration aggregation; ICG evidence and alternative member limit; scoped
rule/source hash validation; raw-to-notified mapping; lawful and unlawful perfume
concentration omission; duplicate IDs/coverage; evidence trace and order invariance.

The common pre-existing ICG precedence test uses an artificial, explicitly
approved test-only ruleset and reviewed synthetic evidence. A/SME confirmation of
that interpretation is requested in issue #2. The example-23 arithmetic test uses
synthetic completion of the base/shared quantities; it is not an independently
approved ECHA golden fixture. F owns independent regulatory QA.

Release remains blocked on independent A/SME regulatory review, B/J/E interface
acknowledgement, F CI/independent testing, upstream review/merge and complete C/E
integration. This PR must not be self-merged.
