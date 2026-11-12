# Direct ECHA Annex VIII Guidance v6.1 evidence check

**Agent:** A — Regulatory expert · **Checked:** 12 November 2026 · **Status:** RESEARCH EVIDENCE; NOT SME-APPROVED.  
**Source:** User-provided ECHA *Guidance on harmonised information relating to emergency health response — Annex VIII to CLP*, **Version 6.1, August 2026**, ECHA-26-G-08-EN, DOI **10.2823/8043435**, **118 PDF pages**. Local source PDF SHA-256: `a6e9f336e8ee170a58fdc11e0575ff99ce375f2e1f0932bdda70f438b0a07e4d`. The source PDF is **not committed** to this repository. Public guidance landing page: https://echa.europa.eu/-/guidance-on-annex-viii-to-clp.

**Page-number convention:** “Printed page” means the number shown in the guidance page header, and “PDF page” counts the cover as 1; e.g. printed page 77 = PDF page 78. Although the cover and document history clearly identify **version 6.1 (August 2026)**, internal running headers on many pages still state **“Version 6.0 – October 2025”**. Preserve cover/history metadata and do not treat that running header alone as evidence that a different PDF was supplied.

## Provenance and version-change check

- **Document history, PDF p. 3:** v6.1 is a *corrigendum to §4.2.6*, clarifying that the **EU importer** is responsible for placing the UFI on the label while the non-EU supplier may pre-label using the EU importer's UFI. Direct wording appears at **printed p. 47 / PDF p. 48**. This does **not** alter group eligibility under §§4.5/5.4.
- The document history lists the more extensive **v6.0 October 2025** overhaul. The substantive §§4.5, 5.3.3.3 and 5.4 relevant to grouping are directly inspected in this uploaded v6.1 PDF; **we have not produced a machine-driven page-by-page comparison against an independent v6.0 PDF**. Independent SME review still required.
- **Printed pp. 20–21 / PDF pp. 21–22:** Article 45(1c) distributor submission rules introduced for **1 January 2027**; separate **Article 4(11)** EU-established supplier obligations for non-EU distance/online sales apply **1 July 2026**. These are applicability/duty-holder matters, not new group-composition gates.

## Direct page-to-rule reconciliation

| Source pages (printed; PDF) | Rule IDs / topic | Verified source facts and implementation implication |
| --- | --- | --- |
| §4.5, p. 58; PDF 59 | REG-CLASS, REG-COMPONENTS, REG-COMMON-RANGE | Group criteria: equal health/physical classifications and the same notified components with the same reported exact concentrations or valid ranges; perfume exceptions are narrow. |
| §5.4, pp. 74–75; PDF 75–76 | REG-SUBMITTER, REG-CLASS, REG-COMPONENTS | Environment-only hazard differences are permitted; an actual group notification can name only one legal submitter; the same importer/downstream user may cover its distributors. |
| §5.4.1, pp. 75–76; PDF 76–77 | REG-DOSSIER | Names, UFI, colour, packaging and use types can differ by member and require correct member mapping. **Group pH can be a single whole-group range** rather than requiring a distinct pH declaration for every member; when pH is very low (<3) or high (>10), ECHA guidance says the reported range should be no wider than **one pH unit**. Toxicological differences must identify the relevant member. This is guidance as to reporting; do not introduce a chemical-grouping rejection based only on pH. |
| §5.4.2, p. 76; PDF 77 | REG-PERFUME-CAP, REG-PERFUME-MAP | Only perfumes **not common to every group member** count in the per-member actual **≤5%** rule; the classifications and mixture-specific membership of *all* perfumes are disclosed. Where permissible perfume concentrations can be withheld from the notification, the submitter must still internally know actual concentrations to verify the cap. |
| §5.3.3.3 / Example 19, pp. 68–69; PDF 69–70 | REG-MAJOR-BAND | A reportable range is lawful only if its width respects each band it covers. At exact 26% major-concern, 23–26 and 25–30 are examples of valid declarations, but 24–29 is **not** valid because it intersects the stricter <25% zone. Source's printed table edges are precise. |
| §5.3.3.3 / Example 20, p. 70; PDF 71 | REG-OTHER-BAND | At exactly 6% other concern, 3–6, 4–7, 5–8 or 6–9 can be used. All are width ≤3 percentage points. |
| §5.3.3.4 / Example 21, pp. 70–72; PDF 71–73 | REG-GCI | GCI perfume components may be aggregated only within the statutory 5% limit and cannot carry health hazards. Multiple appearances of “perfumes” GCI may be required for differing physical classifications. This is **separate** from the group varying-perfume cap. |
| Example 22, pp. 72–73; PDF 73–74 | REG-GCI | A **single submission** covers different non-hazardous colourant blends at actual 18%, 21%, 16%, using a verified “colouring agents” GCI declared 14–22%. This is not a blanket authorisation of arbitrary non-perfume differences in a finished-mixture group. |
| Example 23, pp. 77–78; PDF 78–79 | REG-PERFUME-CAP, REG-PERFUME-MAP, REG-MIM | Trade name 1 varying perfume actuals 1.2%, 0.6%, 1.0% => **2.8%**. Trade name 2 varying actuals 0.4%, 1.4%, 1.4% => **3.2%**. “Perfume chemical name 5” is **present in both** and excluded from the varying total. An identified perfume MiM UFI must be linked to valid information received by relevant appointed body. |
| Example 24, pp. 79–80; PDF 80–81 | REG-PERFUME-IDENTITY, REG-PERFUME-CAP, REG-PERFUME-MAP, REG-MIM | ABC contains “perfume mixture a” (UFI-backed) and “perfume mixture b” (SDS-based without UFI), BCD contains perfume GCI, CDE contains “perfume mixture b” and GCI. MiM b is not group-common because it is absent from BCD. Actual concentration of MiM a in ABC is **not disclosed** (“Not needed” for the filed concentration), so a complete numerical internal cap check requires independently verified actual values. For CDE, b is stated 0.5–0.9 and GCI 0.1–1.1 (reported intervals); do **not** invent exact actuals for either. |
| §7.4.6 / Example 34, pp. 113–115; PDF 114–116 | REG-UPDATE, REG-UFI-CHANGE | Perfume changes under a valid group generally need updated member–perfume mapping but **need not** cause a new UFI; adding a perfume already represented by an existing GCI can sometimes require **no update** when the identifier's reported concentration range remains valid. Crossing the varying perfume 5% limit prevents continued coverage of that mixture within the group and requires a separate notification. Distinguish update, UFI change and group eligibility. |

## Required corrections to the existing audit

1. The prior audit matrix's example page numbers were off by one relative to **printed page** numbering; the source-backed printed and PDF pages are now documented above. (Example 19 is printed **69**, example 23 printed **77–78**, and example 24 printed **79–80**.)
2. The REG-DOSSIER trace had suggested per-member pH as the only route. §5.4.1 explicitly allows a **group-wide pH range** (with a recommended narrow width for acidic/alkaline extremes). Product-specific mapping is still required for the other named attributes.
3. The original “v6.1 PDF still to be directly inspected” open item is now **closed as an Agent A source-access task**, using the SHA-256 above. **Independent** regulatory SME approval and full v6.0/v6.1 comparator sign-off are **not** closed.
4. Example 24 is **illustrative**, not an exact set of all internals; distinguish “dossier concentration not needed” from “actual concentration unknown to the engine”. The latter cannot produce a deterministic eligibility PASS.

## Non-discretionary QA and sign-off gates

- **Agent F** must independently build runnable golden fixtures for examples 19–24 and group update Example 34 where relevant, distinguish source-provided values from synthetic completions, and run them against the evaluator. Agent A's decimal arithmetic self-checks alone do not constitute this.
- **Regulatory SME** must confirm interpretation of pH range guidance, component identity and GCI distinctions, MiM evidence, legal duty-holder exceptions, and update exemptions before allowing an executable ruleset to be marked approved.
- Do not commit proprietary formulation/SDS data or this externally sourced PDF as a repository attachment without explicit licensing review.

**Status:** The relevant v6.1 PDF pages were directly read and rendered for inspection. The binding legal baseline remains the CLP Annex VIII text, not this guidance; no compliance certification or official ECHA dossier validation has been performed.
