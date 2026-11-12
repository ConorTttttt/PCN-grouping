# PCN Grouping — deterministic EU poison-centre grouping engine

Status: **requirements and architecture discovery** (12 November 2026). No engine implementation or compliance certification yet.

## Purpose

Make reproducible, explainable decisions about whether formulations may be covered by one EU/EEA Poison Centre Notification (PCN) under Article 45 and Annex VIII of Regulation (EC) No 1272/2008 (CLP). Evaluate eligibility separately from finding a useful arrangement of groups.

Outputs must distinguish:
- `ELIGIBLE`: every required rule has been verified;
- `INELIGIBLE`: one or more rules conclusively fail;
- `REVIEW_REQUIRED`: incomplete evidence, ambiguity, unapproved derogation or unsupported inputs;
- `OUT_OF_SCOPE`: separate PCN applicability determination (never imply an exemption without evidence).

**Never use a language model to make regulatory pass/fail determinations.** An LLM, if added later, may help extract input data, but a human must confirm it before the deterministic core uses it.

## Start here

- [Regulatory rulebook](docs/regulatory-requirements.md) — statutory criteria, ECHA interpretation, exceptions, quantitative limits and source links.
- [Engine design](docs/engine-design.md) — data contracts, decision algorithm, range feasibility, versioning, auditability and roadmap.
- [Acceptance tests](docs/acceptance-tests.md) — falsifiable positive, negative and review cases.

## Initial scope recommendation

Phase 1: standard full-composition notifications, one legal submitter, approved CLP classification, substance and MiM components, validated concentration ranges, and the Annex VIII perfume-variant group submission. Reporting of generic component identifiers (GCIs) is permitted only if independently validated.

Phase 2: interchangeable component groups (ICGs), industrial-only limited submissions, standard formula and fuel exceptions, complex MiM chains, integration with ECHA's PCN/IUCLID XML schema.

**Important:** a group submission is not the same thing as an interchangeable component group. The former groups *finished mixtures*; the latter may group *components inside a finished mixture*.

## Regulatory baseline

The initial rulebook references the CLP consolidation effective **1 July 2026** and ECHA Annex VIII Guidance **version 6.1, August 2026** (its stated change from v6.0 relates to UFI labelling by EU importers). Version 6.0, October 2025, §5.4 contains the detailed group examples. Rule changes and their dates must be tracked explicitly.

This repository is a decision-support project, not an official ECHA service. A responsible regulatory professional must verify source data, legal interpretation and each submitted dossier. No dossier has been prepared or submitted.

## Python core schema (Agent B, proposed)

Python **3.12+**, offline, standard-library-only at runtime. Install for development with
`python -m pip install -e '.[dev]'`; run `python -m pytest -q`, `ruff check src tests` and
`mypy src`. These commands cover the data-contract package, not regulatory
eligibility or completed ECHA golden tests. No Google Sheets access or credentials are
required. CI ownership belongs to Agent F.

The public `pcn_grouping.models` API is frozen dataclasses for formulation
revision, composition and source evidence; `pcn_grouping.validation`
contains structured `ERROR` / `REVIEW` validation.
Example input shapes:

```json
{"actual":{"exact":"5.0000"}}
{"actual":{"lower":"4.8","upper":"5.2"}}
{"actual":{"exact":null}}
```

Use **strings or `Decimal`**, never JSON numbers/binary floats. `null` means
unknown, not zero. `MASS_PERCENT` and `VOLUME_PERCENT` are distinct bases;
conversion is not implicit. The default **0.01 percentage-point** sum-to-100 tolerance
is an *input data-quality check*, not a statutory range allowance. Hash and
serialization canonicalize sequence order and decimal scale without altering the
stored source BOM. A successful structural parse **does not mean group eligibility**;
downstream evaluators must treat every `REVIEW` issue as unresolved.

See [issue #3](https://github.com/ConorTttttt/PCN-grouping/issues/3)
for the initial shared data contract, subject to integration and regulatory review.
