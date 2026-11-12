# Acceptance test catalogue — EU PCN grouping

These are **requirements-level fixtures**, not implemented tests. Every fixture is expected to have complete, otherwise-valid formulation data, a common submitter, mass-percent basis, correct total composition and verified component hazard classifications **unless the case explicitly varies those conditions**.

For compactness, `B` means a non-classified base component; `P-X` etc are separately identified *verified perfume* components; classification defaults to the same full health-and-physical hazard signature; `MAJOR` means one of the B3.4.1 major-concern classes. `A / B / C` identify finished mixtures, not chemical components.

| ID | Test | Expected | Critical reason |
| --- | --- | --- | --- |
| P01 | Identical chemical composition, different trade names | ELIGIBLE for shared standard submission | No need to invoke the varying-perfume group exception |
| P02 | Base B=98, A:P-X=2, B:P-Y=2, same final CLP signature | ELIGIBLE for group submission | A4.3 varying perfumes <=5 each |
| P03 | B=94; A common perfume=2 + P-X=4; B common perfume=2 + P-Y=4 | ELIGIBLE | Only differing perfume total (4) counts for A4.3; shared perfume must be individually identified, not 6% GCI |
| P04 | A varying perfume=5.0000, B differing perfume=5.0000 | ELIGIBLE | Inclusive threshold |
| N01 | A varying perfume=5.0001, B differing perfume=5 | INELIGIBLE | Strict threshold >5 in A |
| N02 | A B=98 + P-X=2; B B=98 + unrelated non-perfume ingredient=2 | INELIGIBLE | A4.2 component identity mismatch, no A4.3 exception |
| N03 | Same BOM/perfumes but different finished health classification (e.g. Skin Sens. 1 vs no Skin Sens.) | INELIGIBLE | A4.1 |
| N04 | Identical chemistry/classification but different legal submitter | INELIGIBLE | One group submission = one duty holder (ECHA §5.4) |
| P05 | Same BOM/classification; one mixture has different environmental hazard classification only | ELIGIBLE | Environmental classification is not A4.1 blocker |
| P06 | Same BOM/classification; EuPCS differs, but all per-product metadata supplied | ELIGIBLE chemistry; verify dossier format | No same-EuPCS gate in current A4.1 |
| P07 | Common MAJOR component 9.7% in A, 10.5% in B; shared 9.7–10.5% range | ELIGIBLE for this component | Width 0.8 <=1 at below-10 region and <=3 above |
| N05 | Common MAJOR component 9% in A, 11% in B | INELIGIBLE | No range covering both can respect 1-point lower-band width |
| P08 | Common MAJOR component 24% in A, 26% in B | ELIGIBLE for this component | 24–26% width 2 <=3 below 25 and <=5 above |
| N06 | Common MAJOR component 23% in A, 29% in B | INELIGIBLE | Width 6 crosses stricter 3-point band |
| P09 | Common OTHER component 4% and 6% | ELIGIBLE for this component | Shared 4–6% width 2 <=3 |
| N07 | Common OTHER component 3% and 7% | INELIGIBLE | Width 4 >3 |
| P10 | Different actual colourants validated as same approved GCI; no health hazards, <=25% aggregate, valid shared declared range | ELIGIBLE under GCI path if other grouping rules pass | GCI exception, not blanket change of non-perfume substances |
| R01 | Colourants differ but GCI approval / hazard information unavailable | REVIEW_REQUIRED | Cannot assume colourants interchangeable |
| R02 | Named perfume functional role not evidenced | REVIEW_REQUIRED | A4.3 cannot be asserted from a trade name |
| R03 | Supplier MiM referenced, identity/composition/UFI and required supplier/SDS fields insufficient | REVIEW_REQUIRED | B3.2.2 |
| R04 | Finished mixture health/physical classification missing or not approved | REVIEW_REQUIRED | No authoritative A4.1 evidence |
| R05 | A varying-perfume actual concentration known only as 4.8–5.2% | REVIEW_REQUIRED | Cannot safely assert <=5 or >5 |
| P11 | Perfume is only Skin Sens. 1, submitted concentration lawfully omitted but actual value 3% known internally | ELIGIBLE if other conditions pass | Disclosure exemption does not waive 5% calculation |
| R06 | Same perfume-only-Skin Sens. ingredient, concentration omitted both from dossier and internal input | REVIEW_REQUIRED | 5% cannot be established |
| P12 | A:B=96,P-X=4; B:B=96,P-Y=4; C:B=92,P-X=4,P-Y=4 — pairwise tests pass | A-B-C whole group INELIGIBLE | In C both varying perfume IDs total 8%; do not use union-find |
| R10 | A:B=99,P-X=1; B:B=98.99,P-X=1, plus 0.01% non-hazardous trace ingredient only in B | REVIEW_REQUIRED until regulatory treatment is confirmed | An undeclared trace difference must not be silently ignored or asserted a definitive legal fail without checking the applicable identification threshold |
| R07 | Interchangeable component group claimed without technical/tox/final-mixture evidence | REVIEW_REQUIRED | B3.5 separate eligibility criteria |
| R08 | % basis differs (mass vs volume) without density/source data | REVIEW_REQUIRED | Incomparable percentages |
| R09 | Formulation components do not total 100% within approved tolerance | REVIEW_REQUIRED | Invalid data, not a legal grouping fail |
| P13 | Different Member State destinations / packaging / names but legally complete individual data | ELIGIBLE chemistry | Store per-product market/dossier metadata |
| S01 | Only environmental hazard classified mixture | OUT_OF_SCOPE for mandatory Article 45 PCN | Applicability module, not eligible grouping |
| S02 | Only gases-under-pressure or listed explosives classification | OUT_OF_SCOPE for mandatory Annex VIII regime | Applicability exception |
| M01 | Existing group later adds new variant perfume; sum<=5, CLP unchanged | UPDATE perfume/member list; UFI exemption potentially applicable | B4.1 and A5.1 lifecycle rule |
| M02 | Component previously declared as a range changes beyond that range | UPDATE and assess new UFI | B4.1; not Table 4 exact-declaration variation |
| M03 | Two runs with shuffled component rows and mixture order, same normalized input | SAME decision, canonical grouping, reason codes, hash | Reproducibility |
| M04 | Approved ruleset changes effective date | Preserve old result; produce separate new decision version | Regulatory auditability |

## Mandatory golden-reference tests

Recreate the composition and desired grouping conclusions in **ECHA Annex VIII Guidance v6.0, October 2025, examples 23 and 24 (§5.4.2)** as machine-readable fixtures, then have a regulatory reviewer compare results and disclosed perfume tables line by line. The v6.1 August 2026 corrigendum concerns the UFI labelling responsibility for EU importers, not those example rules.

Reference: https://www.certifico.com/component/attachments/download/45822 (pp. 76–79). Do not ship a production-compliant claim unless those fixtures and all applicable statutory boundary tests pass.

## Additional property-based / invariant tests

- **Order independence**: component row and formulation order never alter eligibility.
- **Numerical exactness**: no binary floats; threshold exactly 5.0000 passes and 5.0001 fails.
- **Set validity**: every proposed group is validated as an entire set after optimization.
- **Subset principle**: removing a member cannot make an otherwise valid whole-group perfume/membership condition invalid, with metadata held consistent.
- **Source traceability**: a decision references all source documents supporting ingredient identities, concentrations, hazards and perfume roles.
- **No unsupported shortcut**: different EuPCS and environmental hazard alone do not block; similar names alone do not approve.
- **Input immutability**: neither normalization nor grouping mutates the original BOM.
- **Versioned output**: same canonical input and ruleset produce identical decision data (excluding decision-event timestamp, if stored separately).
- **No unsafe inference**: an absent value is UNKNOWN, never zero and never a regulatory PASS.
