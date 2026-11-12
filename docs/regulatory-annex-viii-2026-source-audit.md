# CLP Annex VIII (1 July 2026) — primary-law PDF audit

**Agent A | Audit date: 12 November 2026 | Status: SOURCE-VERIFIED RESEARCH, NOT LEGAL APPROVAL.**

This audit examines the **two user-provided PDF excerpts** against the Agent A research rulebook and the separately uploaded ECHA **v6.1 August 2026** guidance. The legal text controls over guidance for the applicable effective date. **No automatic legal verdicts should be inferred from this documentation.**

## Primary-law source inventory / integrity

| Source label | Uploaded filename | PDF pages | EUR-Lex source-page markers | SHA-256 |
| --- | --- | ---: | --- | --- |
| `CLP_ANNEX_VIII_2026_EXTRACT` | `CLPAnnexVIIIPCN.pdf` | 14 | 02008R1272 — EN — **01.07.2026** — **031.001** — printed **1562–1575** | `50001b176326ee6dae56cc163c0f3b344ec850cd9c2a7527f8db0de6eb78d2a1` |
| `CLP_ANNEX_VIII_PARTIAL_PART_D_2026_EXTRACT` | `CLP_PCN_Full_Regulation.pdf` | 23 | Identical printed 1562–1575, then **1576–1584** | `8f7d3aad6ec44bad13127df49f464f64ca6effa6c716c20eacee625d2c97e8e7` |
| `ECHA_GUIDANCE_V6_1_2026` | `guidance_on_annex_viii_to_clp_en.PDF` | 118 | August 2026, DOI 10.2823/8043435; source distinctions separately documented | `a6e9f336e8ee170a58fdc11e0575ff99ce375f2e1f0932bdda70f438b0a07e4d` |

**Integrity comparison:** All **14** first pages of the two CLP PDF extracts yield byte-identical **extracted page text** in order (PyMuPDF, 2026-11-12). This does **not** assert that the PDFs are byte-identical or a complete EUR-Lex regulation. Key scanned-looking legal table pages were also visually rendered and inspected. The longer-named `CLP_PCN_Full_Regulation.pdf` is **NOT the entire CLP Regulation**: both files begin at Annex VIII printed page 1562; the 23-page document extends into **Part D standard formulas**, ending printed page 1584 mid-concrete schedules. Neither contains Article 45 or all subsequent standard formulas. Do not use its filename to imply otherwise.

Canonical EUR-Lex legal source: https://eur-lex.europa.eu/eli/reg/2008/1272/2026-07-01/eng. Full consolidated regulation/Article 45 and complete Part D must be obtained independently when required.

## Source-to-rule crosswalk — 2026 baseline

| Source PDF page; EU printed page | Clauses (2026-07-01) | Finding and rule interface |
| --- | --- | --- |
| 1–3; 1562–1564 | A.2.1–2.4, A.3.1–3.5 | Consumer/professional/industrial modes and exemptions; mandatory ordinary notification for health/physical hazard mixtures before market; Article 45 legal-entity analysis separately required. |
| **3; 1564** | **A.4.1–4.4** | Identical finished-mixture **health and physical classification**, same identified components/common valid declaration range, exception only differing **perfumes ≤5% per mixture**, preserve required per-member Part B information. No identical EuPCS condition. **REG-CLASS, REG-COMPONENTS, REG-COMMON-RANGE, REG-PERFUME-CAP**. |
| 3; 1564 | A.5.1 | New UFI rule and **perfume-only group derogation**. Does not automatically approve UFI sharing. REG-UFI-CHANGE. |
| **5–6; 1566–1567** | **B.2.1–2.4; B.3.1** | Mixture hazard, label, SDS §11 tox, packaging, state, colour, pH or reason unavailable, EuPCS/use reporting. Varying perfumes require **member → perfumes → classifications** list, perfumes present in at least one group member. REG-DOSSIER/PERFUME-MAP. ECHA §5.4.1 adds group-wide pH range reporting guidance; do not fabricate this as verbatim statutory wording. |
| 6; 1567 | B.3.2.1–3.2.2 | Substance identification and three MiM scenarios: full upstream composition, prior recipient+UFI, UFI without recipient disclosure, and no UFI. REG-SUBSTANCE-ID, REG-MIM. |
| **7; 1568** | **B.3.2.3; B.3.3** | GCI only for verified exclusively functioning and **no-health-hazard** perfume/colouring components, totals **5%** and **25%** respectively; notifiable thresholds ≥0.1% health/physical, known lower except irrelevant, ≥1% otherwise. **REG-GCI, REG-DECLARABLE**. |
| **8; 1569** | **B.3.4.1 Table 1 / B.3.4.2 Table 2** | Exact percentages or legally bounded concentration ranges, band widths **5/3/1/0.3/0.1** for major concern and **20/10/3/1** for others, in **percentage units**. Group perfume concentration-omission rule applies only for specified classifications, not to proof of underlying actual percentages. REG-MAJOR-BAND, REG-OTHER-BAND, REG-PERFUME-OMISSION. |
| 8–10; 1569–1571 | B.3.5, B.3.5.1–3.5.2; B.3.6–3.7 | ICG separate from finished-mixture grouping; standard-formula and fuel alternative reporting pathways. Standard Formula Part D is only **partially** supplied here. REG-ICG, REG-MODE. |
| 11; 1572 | B.3.8; B.4.1 opening | Classified component and partly known MiM CLP reporting; actual Part B update trigger list begins with identifiers, hazard classification. REG-MIM, REG-UPDATE. |
| **12; 1573** | **B.4.1 remainder and Table 4** | **Exactly FOUR top-level update-trigger indents**: identifier/UFI, finished health/physical classification, new SDS §11 tox, and specified composition changes. Relative Table 4: **5/10/20/30%** of prior exactly declared concentration. Perfume member-list update expressly required. **No fifth “other changes relevant to response” indent is present in this effective 2026 excerpt.** |
| 13–14; 1574–1575 | Part C 1.1–1.4; Part D starts | PCN submission data format mapping and first page of special standard formulas; continued only through 1584 in longer document. |

**Not within these PDFs:** Current Article 45 duty-holder wording, all other CLP annexes, later Part D formula tables, EU Member State reporting variations, and future 2027 amendments. Do **not** infer them from extract filenames.

## Critical legal effective-date correction: B.4.1 fifth indent

### (1) What the uploaded **binding 2026 legal text** says

In **both** legal PDF files, **B.4.1** across PDF pp. 11–12 / printed EU pp. 1572–1573 lists **four** classes of mandatory submission-update triggers: (i) changed product identifier or UFI, (ii) changed finished health/physical hazard classification, (iii) relevant new SDS §11 tox, (iv) listed composition changes (new/removed notifiable ingredient, concentration outside declared range, or changes outside the exact-concentration Table 4 tolerance). It also requires updating the **member–perfume list** where group perfumes change. The **fifth response-relevance catch-all is absent** from this consolidation.

### (2) What **future legislation** provides

**Regulation (EU) 2024/2865, Annex IV, Part B amendment to §4.1**, adds a fifth indent for other changes to a marketed mixture relevant to emergency health response. **Article 2(3)** of Regulation 2024/2865, as amended by **Regulation (EU) 2025/2439**, expressly provides for **Annex IV to apply from 1 January 2027**. Sources:

- Authoritative amending law and current consolidated amending-act dates: https://eur-lex.europa.eu/eli/reg/2024/2865/2025-12-23/eng
- Subsequent amendment: https://eur-lex.europa.eu/eli/reg/2025/2439/oj/eng
- Comparative future Annex VIII display, secondary only: https://regelex.com/legislation/02008R1272-20270101/anx_VIII

**Therefore this new fifth-indent rule must NOT be loaded as an unconditional 2026 B.4.1 statutory trigger**. Record `effective_from = 2027-01-01`, and assess legal scope/transition at the time of release.

### (3) Reconciling **ECHA v6.1 August 2026 guidance**

ECHA §7.4.3 (printed p. 109 / PDF p. 110) describes the fifth indent as already in B.4.1 and describes contact, product category, packaging and ingredient classification updates. ECHA's explanatory example is compatible with the **future 2027** text, but its reference to a current fifth B.4.1 indent **is not present in the 2026 consolidated law PDFs**. In a 2026 engine, these other factual changes may still need review/maintenance under obligations to keep submitted information accurate or under other rules, but **not a conclusive FAIL solely on a statutory fifth-indention basis**. Default to `REVIEW` for any unclassified change pending a reviewer/effective-date assessment. The issue is **not** a change to the core finished-mixture A.4 grouping criteria.

**Correction to earlier Agent A work:** Prior research draft incorrectly described this future 2027 fifth indent as existing B.4.1 legislation at the 2026 baseline. This source-audit corrects that attribution and records an SME review blocker.

## Deterministic implementation and regression handoff

- Continue using **versioned** rulesets, exact `Decimal` values and a separate lifecycle evaluator. Never make a product grouping FAIL based on B.4.1 lifecycle changes.
- `B.4.1_2026`: four enumerated mandatory triggers and group perfume member-list update. `B.4.1_OTHER_EMERGENCY_RELEVANT_CHANGE_2027`: **inactive** before `2027-01-01`; assess at/after that date with separate approved legal version. An unevidenced change type or exact effective date must yield **REVIEW**.
- **Proposed QA** (Agent F to implement, not asserted as engine tests): `A-DATE-2026` — 2026-11-12 contact-only change must **not** return `REG-UPDATE statutory fifth-indent FAIL`; `A-DATE-2027` — 2027-01-01 response-relevant change is an applicable fifth-indent trigger if independently validated; `A-DATE-OTHER` — missing effective date returns REVIEW; `A-DATE-PERFUME` — 2026 perfume membership change still requires group perfume-list update.
- Other rules (group equality, 5% perfume cap, numerical Table 1/2 boundary checks) do **not** change from this discovery.
- **Outstanding reviews:** independently verify Annex IV effective-date interpretation with regulatory counsel, re-check the specific change-type applicability, complete Agent F source-backed tests and obtain Agent J integration approval. No claim of EU/EEA regulatory compliance is made.

## Audit change log

- **2026-11-12:** Agent A examined both uploaded legal PDF extracts, their SHA-256 and identical overlap, inspected legal pages 3, 8, 12, and determined that the prior **2026 statutory B.4.1 catch-all attribution was incorrect**. Marked the fifth-indent rule **future-effective 2027-01-01**, pending SME review. These files were not committed to the public repository.
