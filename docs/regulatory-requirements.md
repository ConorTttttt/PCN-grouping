# Regulatory requirements for EU PCN finished-mixture grouping

**Audit status:** **RESEARCH-DRAFT; independent regulatory SME approval pending.** [Direct ECHA v6.1 PDF check and provenance](regulatory-guidance-v6-1-evidence.md) is now available; see [rule traceability matrix](rule-traceability-matrix.md) for rule IDs, legal/effective dates, PASS/FAIL/REVIEW cases and unresolved issues.

**Research date:** 12 November 2026. **Rules baseline:** CLP Annex VIII consolidated text of 1 July 2026; ECHA Guidance v6.1 (August 2026). The detailed grouping interpretation in v6.0 (October 2025), §5.4, remains relevant: ECHA describes v6.1 as a corrigendum to §4.2.6 regarding UFI labelling by an EU importer. This is a technical requirements analysis, not a legal opinion.

## Primary sources (read these before changing a rule)

1. CLP 1272/2008 consolidated (current as checked): https://eur-lex.europa.eu/eli/reg/2008/1272/2026-07-01/eng — especially Annex VIII Parts A and B. EURLex may show a large-document fallback; legal wording of Annex VIII can be read at https://regelex.com/legislation/02008R1272-20260701/anx_VIII (secondary display).
2. Commission Delegated Regulation (EU) 2020/1677 (replaced Annex VIII wording): https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32020R1677
3. ECHA guidance landing page, latest release v6.1 August 2026: https://echa.europa.eu/-/guidance-on-annex-viii-to-clp
4. Guidance v6.0 October 2025, specifically §5.4 and examples 23–24 (copy hosted by third party): https://www.certifico.com/component/attachments/download/45822
5. ECHA submission information and tools: https://poisoncentres.echa.europa.eu/gather-the-required-information ; https://poisoncentres.echa.europa.eu/prepare-your-submission
6. ECHA XML/PCN data model (format v8, updated 27 April 2026): https://echa.europa.eu/web/poisoncentres/poison-centres-notification-format
7. EU Regulation 2024/2865 as amended (future distributor obligations apply from **1 January 2027**, not November 2026): https://eur-lex.europa.eu/eli/reg/2024/2865/2025-12-23/eng
8. ECHA explanation of concentration changes/UFI: https://poisoncentres.echa.europa.eu/changes-in-composition-and-the-effect-on-the-ufi

**Do not use the original 2017/542 Annex VIII §A.4.1 wording as current law.** The original required the same product category; the wording replaced by 2020/1677 no longer includes that requirement. Record EuPCS per mixture, but do **not** automatically reject a group solely because EuPCS categories differ. Confirm practical payload handling when exporting to a specific PCN format.

## A. Applicability before grouping

- Article 45/Annex VIII principally concerns mixtures placed on the EU/EEA market and classified hazardous for **health or physical** effects. Environmental-only mixtures are not mandatory PCNs under this criterion; other notifications may be voluntary.
- Exclusions/special regimes include R&D/PPORD, mixtures classified *only* for gases under pressure and/or the listed explosives categories, and optional bespoke-paint exemption. Determine scope explicitly; never call a mixture “eligible” merely because it does not need mandatory PCN.
- Consumer, professional and industrial-only use regimes, and industrial/other limited submissions, have distinct information requirements. In a first release, evaluate only standard full-composition submissions; route special regimes to review until implemented.
- Notifications must be sent to the relevant appointed bodies before placing mixtures on the relevant Member State markets. Per-country languages and market coverage are dossier requirements, not proxies for chemical grouping.
- Each group submission has **one legal submitter** (same importer or downstream user, plus its distributors as applicable), per ECHA **guidance** §5.4 read with current Article 45 and Annex VIII A.2.1/B.1.2. This is a guidance interpretation of a single duty-holder submission, not an additional verbatim sentence in A.4.1–4.4. The 2024/2865 changes that introduce specified distributor submission duties are **future-effective from 1 January 2027**. Do not merge mixtures under different responsible submitters without reviewing their legal roles.

## B. Finished-mixture group eligibility (Annex VIII Part A §§4.1–4.4)

| Rule | Deterministic interpretation | Evidence |
| --- | --- | --- |
| A4.1 identical hazard classifications | Every finished mixture has the same verified **health AND physical** CLP classification, including class, category, relevant statement/route distinctions. Different environmental classifications alone need not prevent grouping. | Approved CLP classification, revision/date |
| A4.2 same identified components | Every mixture contains the same chemical substances/MiMs (or an explicitly validated permitted GCI/ICG representation), aside from the A4.3 perfume exception. | Resolved component IDs, MiM composition/UFI, BOM |
| A4.2 same declared concentration ranges | For each shared component, choose one *valid* concentration declaration (exact value only if identical, or a legally allowable shared range) covering **all** member mixtures. Do not require actual percentages to be identical where a common compliant range can be declared. | Actual percentages and computed common interval |
| A4.3 varying perfumes | All components that differ in identity/presence across group members must be **substantiated perfume components**. For **each** mixture, the sum of actual concentrations of perfumes not common to every mixture is <= 5.0%. | Perfume function and identity evidence; real percentages |
| B3.1 variable perfume disclosure | Provide a list mapping each mixture to the perfumes it contains and those perfumes' classifications; perfume components included in a group must occur in at least one member. | Per-mixture component/classification matrix |
| A4.4 individual dossier data | Keep all required mixture/product-specific data available even where included in one group: product/trade names, UFI(s), colour, physical state, pH, packaging, uses/EuPCS, market data, toxicology differences. | Product and submission metadata |
| Same legal submitter (ECHA §5.4) | Only one duty holder identified in each group. | Legal-entity identifier |

**The 5% group exception counts only the varying perfumes**, not perfumes common to every group member. Common perfume components still need a common valid concentration declaration where one is required. This is different from the separate 5% allowance for a generic product identifier (see below). A perfume identified with a GCI may be included in the varying set where appropriate.

For group perfume ingredients not classified for human-health hazards, or classified only for Skin Sens. 1/1A/1B and/or Asp. Tox., the submitted concentration may be omitted under B3.4.2, **but actual concentration remains mandatory internally** to prove the 5% threshold (ECHA §5.4.2).

ECHA §5.4 explicitly states that a difference in environmental hazard classification is allowed, group members may have different trade names and UFIs, and toxicological differences must be clearly attributed to the correct mixtures.

## C. Declared concentrations (Part B §§3.3–3.4)

**Notifiable components:**
- Health-/physical-hazardous components at **>=0.1%**, plus identified hazardous components below 0.1% unless their irrelevance for emergency response can be demonstrated.
- Identified components not hazardous for health/physical effects at **>=1%**.
- Do not silently discard known minor ingredients from the underlying BOM when comparing actual formulations. Some exceptions to declaration exist; retain traceability and a documented legal basis.

A component is of **major concern** when classified for at least one of: Acute Tox. 1–3; STOT SE 1–2; STOT RE 1–2; Skin Corr. 1/1A/1B/1C; Eye Dam. 1. Otherwise it follows the **other/non-classified** band. Classifications of components/MiMs must be available.

### Table 1 (major concern)

| Concentration zone (%) | Maximum declared range width (percentage points) |
| --- | ---: |
| 25 <= c < 100 | 5 |
| 10 <= c < 25 | 3 |
| 1 <= c < 10 | 1 |
| 0.1 <= c < 1 | 0.3 |
| 0 < c < 0.1 | 0.1 |

### Table 2 (other hazardous or non-classified)

| Concentration zone (%) | Maximum declared range width (percentage points) |
| --- | ---: |
| 25 <= c < 100 | 20 |
| 10 <= c < 25 | 10 |
| 1 <= c < 10 | 3 |
| 0 < c < 1 | 1 |

A shared range must contain every actual concentration (or every point of every evidenced actual interval) and be legal **at every possible value in that range**, including when the range crosses concentration-band boundaries (**ECHA guidance** §5.3.3.3, example 19). A lawful narrower range is always preferable to rounding into an invalid band.

Illustration: 26% of a major-concern ingredient cannot be declared at 24–29% because the interval reaches below 25%, where the width is limited to 3 points. 25–30% (five points) is valid; 23–26% (three points) is also valid. These are **percentage points**, not relative percentages. Interpret statutory band edges exactly: Table 1 uses `(0,0.1)`, `[0.1,1)`, `[1,10)`, `[10,25)`, `[25,100)`; Table 2 uses `(0,1)`, `[1,10)`, `[10,25)`, `[25,100)`. Zero indicates *absence*, never a positive concentration; the printed width bands do not cover an exact 100% value, so review the mixture/scope and declaration type rather than inventing an interval at that edge.

Treat **exact concentration** and **declared range** as different data types. The later Table 4 tolerance regime applies to a prior declaration by exact percentage; it is not an alternative Table 1/2 grouping rule.

## D. Component identification, MiMs, GCIs and ICGs (Part B §§3.2, 3.5)

### Substances and mixtures in mixture (MiM)

A component can be a substance or MiM. Prefer a stable, verified substance identity (not merely a commercial name). Under B.3.2.1, an INCI, colour index or other internationally accepted chemical name may be used only when it unequivocally identifies the substance. For a fully known MiM, use its disclosed underlying constituents where required. For an incompletely known MiM, support the legal identification paths:
- registered/previously notified MiM UFI + product identifier + concentration, if the relevant appointed body has information;
- other UFI scenarios need the MiM's available SDS composition, supplier details and additional known components;
- no UFI also requires specified SDS and supplier information.
- B.3.8 additionally requires component health/physical CLP hazard class, category and statements, including MiM health/physical classification where the submitter does not have access to the full composition. The mere presence of a MiM UFI without proof of the applicable prior-submission route is not enough.

Never assume two supplier blends are identical solely because their names resemble each other, or treat a missing MiM UFI as a harmless blank.

### Generic component identifiers (GCI)

Under B3.2.3 the identifiers **“perfumes”** and **“colouring agents”** may be used if the components are used exclusively for that function, **are not classified for any health hazard**, and the total identified under the applicable generic identifier is no more than **5% for perfumes** or **25% for colouring agents**. Relevant classifications and separate identifier representation may still need disclosure.

Colouring-agent variants that meet GCI rules and share a valid aggregate range may potentially be captured as the *same notified component representation*. ECHA guidance **example 22, p.72**, illustrates three differently coloured products under one **single submission** where actual total colourants of 18%, 21% and 16% are represented by one verified “colouring agents” GCI and a common 14–22% declaration. This does **not** create a general exemption allowing all different non-perfume ingredients to be grouped. Do not promote unverified colourants into a common GCI.

### Interchangeable component groups (ICG)

ICG is a **component-level** exception, not the same as a **finished-mixture group submission**. Annex VIII B3.5 has two alternative rule sets:
1. same technical function, identical health/physical classification and equivalent toxicological properties, with all final mixture combinations yielding the same hazard identification and additional information; OR
2. limited specified irritation/corrosion, eye, aspiration and sensitisation hazards, identical component health/physical classification, compatible pH band where applicable, no more than five components, and invariant final mixture hazard/additional information.

Only validated pre-existing ICGs should pass through Phase 1. Building or approving ICGs requires separate evidence, classification data and combinatorial verification.

### Other special regimes

Standard formulas (Part D), fuels (B3.7), industrial limited submission (A2.3/B3.1), and exemptions require dedicated paths. Do not import their relaxed disclosure requirements into an ordinary full-composition group without proving applicability.

## E. Data for a valid group dossier (Part B §§1–3; Part C)

At a minimum the downstream dossier workflow needs:
- duty holder/contact point, and 24/7 emergency contact where a limited submission applies;
- all trade names/variants and UFI(s), with correct per-mixture mapping;
- verified final mixture health/physical classification, label elements, and the tox. narrative corresponding to SDS §11;
- all legally required ingredient identities/concentrations/classifications and MiM disclosures;
- individual physical state, colour, **pH or reason absent (which may be reported as a valid group-wide pH range under ECHA §5.4.1)**, packaging types/sizes for consumer/professional products, EuPCS, use type and destinations/languages;
- the group-specific mixture -> perfume -> classification mapping.

**ECHA guidance §5.4.1 reporting nuance (non-statutory elaboration):** a group-wide pH range may be supplied instead of a separately stated per-mixture pH. For extreme acidic/alkaline cases (pH below 3 or above 10), the reported range should not exceed **one pH unit**. Where toxicological data differ, they must be unambiguously attributable to each member. Distinct pH or packaging by itself is not a new A.4.1 chemical-grouping prohibition.

Multiple UFIs can be present in a group. Under A5.1, the varying-perfume group exception can avoid a new UFI when the **only** change is perfume/addition of perfume, but the group and legal conditions must remain satisfied. Do not auto-share a UFI without explicit governance.

## F. Updates and lifecycle (Part B §4.1, A5.1)

A submission update is required before placing the changed mixture on the market when the product identifier/UFI changes, health/physical hazard classification changes, relevant new toxicological information becomes available, or specified formulation changes occur:
- addition/substitution/deletion of a notifiable component;
- component concentration exits its **previously declared range**;
- where previously declared exactly, concentration changes beyond Table 4 tolerances: >25% (±5% relative), >10–25% (±10%), >2.5–10% (±20%), <=2.5% (±30%). These are relative variations, not points.

Part B §4.1 additionally triggers an update when **other changes to a marketed mixture are relevant to emergency health response**; the list above is **not exhaustive**. Special rules for standard formulas or fuels may modify component-update triggers.

Perfume changes within groups require maintaining/updating the mixture-perfume list, even where a new UFI is not required. ICG, standard formula and fuel exceptions have special change rules. For this engine, group selection and ongoing submission maintenance should be separate modules.

## G. Explicit non-rules / safeguards

- Do **not** apply the obsolete 2017 wording requiring identical EuPCS categories.
- Do **not** reject solely because environmental hazards differ.
- Do **not** interpret 5% as *all perfumes* for A4.3; distinguish it from the 5% **GCI perfume** ceiling.
- Do **not** replace actual concentrations with SDS Section 3 ranges when calculating the perfume threshold unless the evidence proves compliance for all possible values.
- Do **not** infer CLP mixture classification from list of ingredients or hazard statement overlap; classification is an authoritative input until a separate validated classification engine exists.
- Do **not** treat pairwise compatibility as proof that three or more formulations can be grouped: assess the **whole proposed group**.
- Do **not** assert official ECHA validation or submission success from this engine alone.

## H. Regulatory ambiguities requiring explicit policy

1. Canonical substance/MiM identity, confidentiality and whether supplied mixture data is truly sufficient.
2. Distinguish actual batch variability, ingredient upper bounds, and declared ranges without rounding compliance into existence.
3. Conservatively confirm perfume function, source evidence and component identity (including MiMs with partial composition).
4. Decide which notified and previously assigned UFIs to reuse, and whether changes require a new dossier.
5. Check any country-specific destination, language, fee and PCN-format validation rules separately from chemistry.

Every hard rule should carry a source section, date/version, test fixture and a reviewer-approved change history.

## I. Agent A source audit and reviewer hand-off — 12 November 2026

**Status: legal verification research, not professional approval.** The complete rule-by-rule matrix, case IDs, source links and the open issue queue are in [docs/rule-traceability-matrix.md](rule-traceability-matrix.md). Reference 2020/1677 Annex VIII wording was checked against the 1 July 2026 consolidated version. The **ECHA v6.1 August 2026 original uploaded PDF** has now been inspected directly, including §§4.5/5.4, Tables 1–2, examples 19–24, §7.4.6 and the example tables (printed pp. 69, 72–73, 77–80, 113–115). The [PDF evidence log](regulatory-guidance-v6-1-evidence.md) records its SHA-256, page crosswalk and source qualifications. ECHA's document history says v6.1 changes §4.2.6 on EU-importer UFI label responsibility. **Independent regulatory SME validation and formal v6.0–v6.1 comparative sign-off remain outstanding.**

**Confirmed interpretations** (statute first; guidance separately):

- **A.4.1–4.4:** same health/physical classification and notified common components/concentration declarations; perfume identity variations only when their *per-mixture differing total* is ≤5%; retain each member's Part B data. Differing EuPCS, environmental-only classification, trade names, Member State markets, packaging or UFIs are not additional chemical-grouping prohibitions by themselves. ECHA §5.4 clarifies the single legal submitter.
- **B.3.1–3.4:** proper identity/presence/disclosure, verified MiM route and B.3.8 classifications; do not confuse the ≤5% A.4.3 varying-perfume allowance with B.3.2.3's independent ≤5% **generic identifier** perfume limit or ≤25% colourant GCI allowance. Group perfume disclosure omission under B.3.4.2 leaves the *internal actual concentration evidence* requirement intact.
- **B.3.4 Tables 1–2:** percentage-point range width, cross-zone constraint and exact decimal endpoints. B.4.1 **Table 4 relative tolerances apply only to updates from a previously declared exact concentration**, not eligibility ranges.
- **B.3.5:** interchangeable component groups are a separate *component* representation pathway. Phase 1 must not automatically create or approve an ICG.
- **B.4.1/A.5.1:** composition change, classification and toxicological update governance is separate from initial grouping, and Part B §4.1 includes a final response-relevance catch-all. Any new-UFI/PCN filing decision requires specific filing history.

**Findings requiring changes or caution:** (1) former draft update summary omitted the Part B §4.1 general emergency-response relevance catch-all; now added. (2) Distinguish ECHA one-submitter guidance from the explicit A.4 wording. (3) Do not apply future 1 January 2027 distributor provisions in the 2026 ruleset. (4) ECHA example 24 does not disclose all exact underlying formulation values: any machine-readable fixture must mark synthetic completions as synthetic, never represent them as regulator-provided values. (5) Exact 100% declarations, unidentified traces, non-standard MiM/ICG/GCI representations, and destination-specific payload validation remain review gates.

**Decision on sign-off:** unresolved matters must give **REVIEW_REQUIRED** (or a *separate* dossier/applicability outcome). Agents B–F should consume the stable rule IDs in the matrix, not interpret prose using AI. Agent F owns the test catalog and fixture implementation, and a regulatory SME must approve boundary interpretation and all golden-reference cases before these rules become production-executable.

### Revision history

| Date | Change | Approval |
| --- | --- | --- |
| 2026-11-12 | Agent A first independent source audit: traceability matrix and effective-date cautions; added exact boundary policy, MiM B.3.8, ECHA example 22 and §4.1 catch-all | **PENDING regulatory SME review** |

| 2026-11-12 | Direct primary ECHA Guidance **v6.1** PDF verified: version change (importer UFI labelling), group submission §§4.5/5.4, examples 19–24, group pH reporting, and §7.4.6 update exceptions; see evidence log and PDF SHA-256 | **PENDING independent regulatory SME review** |
