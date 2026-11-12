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
