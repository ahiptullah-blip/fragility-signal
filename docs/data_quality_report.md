# Data Quality Report: Signals

Panel: 11388 entity-quarters, 532 entities, 2012-06-30 to 2026-09-30 (quarter-end scoring dates, universe only).
Rows with a computation error: 0.

## Missing-value rates

| signal | missing % | entities with any value | note |
|---|---|---|---|
| F1_cash_runway | 1.2 | 527 | Capped at 40 quarters; companies with positive operating cash flow sit at the cap. |
| F2_refinancing_wall | 0.5 | 529 | Basis varies: 24-month maturity schedule where tagged, else current debt (12 months). See basis table. |
| F4_dso_change | 13.5 | 451 | None when quarterly revenue < $1M or DSO > 730 days. |
| F5_share_dilution | 20.9 | 432 | Not split-adjusted (splits show as outliers). None when the ratio is beyond 50x (unit mismatch). |
| S1_customer_concentration | 0.0 | 532 | Text-extracted. 0 = no customer at or above 10% disclosed. |
| S2_gross_margin_trend | 19.9 | 421 | None when TTM revenue < $5M or margin outside [-100%, 100%]. |
| B2_ceo_cfo_departures | 0.0 | 532 | Text-classified 8-K 5.02; spot-check precision about 75% (biographies, officers leaving for CEO roles elsewhere). |
| B3_auditor_change | 0.0 | 532 |  |
| B5_late_filings | 0.0 | 532 |  |
| O1_revenue_growth_decel | 17.9 | 450 | None when the revenue base < $5M. |
| O3_headcount_trend | 18.6 | 434 | Text-extracted from 10-K employee counts; annual. None when the year-over-year ratio is outside 0.2-5x (parse error). |
| N4_mda_specificity_change | 17.4 | 469 | Text-extracted from 10-K MD&A; None when MD&A < 1,000 words, not found, or its length changes more than 2x. |

## Coverage per signal per year (% of universe entity-quarters with a value)

| year | entity-quarters | F1_cash_runway | F2_refinancing_wall | F4_dso_change | F5_share_dilution | S1_customer_concentration | S2_gross_margin_trend | B2_ceo_cfo_departures | B3_auditor_change | B5_late_filings | O1_revenue_growth_decel | O3_headcount_trend | N4_mda_specificity_change |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2012 | 459 | 99 | 100 | 73 | 73 | 100 | 68 | 100 | 100 | 100 | 34 | 82 | 88 |
| 2013 | 631 | 99 | 100 | 90 | 90 | 100 | 82 | 100 | 100 | 100 | 73 | 84 | 89 |
| 2014 | 656 | 100 | 100 | 89 | 90 | 100 | 81 | 100 | 100 | 100 | 86 | 80 | 88 |
| 2015 | 753 | 99 | 100 | 88 | 91 | 100 | 80 | 100 | 100 | 100 | 83 | 80 | 82 |
| 2016 | 727 | 98 | 99 | 90 | 91 | 100 | 81 | 100 | 100 | 100 | 86 | 85 | 85 |
| 2017 | 649 | 98 | 99 | 87 | 86 | 100 | 84 | 100 | 100 | 100 | 88 | 88 | 84 |
| 2018 | 677 | 99 | 99 | 86 | 84 | 100 | 81 | 100 | 100 | 100 | 86 | 83 | 79 |
| 2019 | 717 | 99 | 100 | 86 | 81 | 100 | 80 | 100 | 100 | 100 | 82 | 78 | 80 |
| 2020 | 710 | 99 | 100 | 88 | 78 | 100 | 82 | 100 | 100 | 100 | 85 | 81 | 79 |
| 2021 | 766 | 98 | 99 | 87 | 77 | 100 | 80 | 100 | 100 | 100 | 85 | 80 | 85 |
| 2022 | 1075 | 98 | 100 | 80 | 69 | 100 | 74 | 100 | 100 | 100 | 71 | 68 | 70 |
| 2023 | 1047 | 99 | 100 | 87 | 72 | 100 | 81 | 100 | 100 | 100 | 80 | 81 | 82 |
| 2024 | 958 | 98 | 99 | 89 | 72 | 100 | 82 | 100 | 100 | 100 | 91 | 85 | 84 |
| 2025 | 907 | 99 | 99 | 88 | 72 | 100 | 82 | 100 | 100 | 100 | 92 | 85 | 84 |
| 2026 | 656 | 99 | 99 | 87 | 72 | 100 | 81 | 100 | 100 | 100 | 92 | 89 | 87 |

## Refinancing wall basis

| F2 basis | entity-quarters |
|---|---|
| no_debt | 5501 |
| current_debt_12m | 3196 |
| schedule_24m | 2691 |

## Distributions

| signal | min | p1 | p5 | median | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| F1_cash_runway | 0.0 | 0.29 | 5.2 | 40.0 | 40.0 | 40.0 | 40.0 |
| F2_refinancing_wall | 0.0 | 0.0 | 0.0 | 0.0 | 0.96 | 7.37 | 100.0 |
| F4_dso_change | -601.75 | -38.48 | -17.98 | 0.0 | 18.31 | 49.28 | 568.35 |
| F5_share_dilution | -97.4 | -49.06 | -5.96 | 1.61 | 25.93 | 293.18 | 2682.92 |
| S1_customer_concentration | 0.0 | 0.0 | 0.0 | 0.0 | 16.0 | 46.13 | 99.0 |
| S2_gross_margin_trend | -172.26 | -13.42 | -5.51 | 0.15 | 5.77 | 14.06 | 148.85 |
| B2_ceo_cfo_departures | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 5.0 |
| B3_auditor_change | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 2.0 |
| B5_late_filings | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 8.0 |
| O1_revenue_growth_decel | -2062.19 | -89.72 | -38.15 | -2.45 | 26.0 | 74.21 | 580.43 |
| O3_headcount_trend | -78.22 | -46.03 | -18.1 | 7.47 | 54.25 | 170.0 | 400.0 |
| N4_mda_specificity_change | -99.43 | -41.39 | -19.19 | -0.43 | 15.01 | 31.57 | 84.77 |

## Outliers (outside plausibility bounds; flagged for review, not removed)

| signal | bounds | flagged | flagged % |
|---|---|---|---|
| F1_cash_runway | [0, 40] | 0 | 0.0 |
| F2_refinancing_wall | [0, 10] | 83 | 0.73 |
| F4_dso_change | [-180, 180] | 22 | 0.22 |
| F5_share_dilution | [-50, 200] | 204 | 2.27 |
| S1_customer_concentration | [0, 60] | 87 | 0.76 |
| S2_gross_margin_trend | [-30, 30] | 25 | 0.27 |
| B2_ceo_cfo_departures | [0, 2] | 93 | 0.82 |
| B3_auditor_change | [0, 2] | 0 | 0.0 |
| B5_late_filings | [0, 4] | 103 | 0.9 |
| O1_revenue_growth_decel | [-100, 100] | 138 | 1.48 |
| O3_headcount_trend | [-60, 200] | 125 | 1.35 |
| N4_mda_specificity_change | [-30, 30] | 318 | 3.38 |

**F2_refinancing_wall**, most extreme (one row per entity):

- Dynamics Research Corp (CIK 0000030822), 2012-06-30: 100.00
- MEDASSETS INC (CIK 0001254419), 2015-12-31: 100.00
- Global System Dynamics, Inc. (CIK 0001843248), 2024-03-31: 100.00
- REGO PAYMENT ARCHITECTURES, INC. (CIK 0001437283), 2026-06-30: 100.00
- Sysorex, Inc. (CIK 0001737372), 2022-12-31: 100.00

**F4_dso_change**, most extreme (one row per entity):

- TAKE TWO INTERACTIVE SOFTWARE INC (CIK 0000946581), 2014-12-31: -601.75
- MAGNITE, INC. (CIK 0001595974), 2018-09-30: 429.68
- FingerMotion, Inc. (CIK 0001602409), 2026-03-31: 414.45
- Clear Secure, Inc. (CIK 0001856314), 2025-06-30: -323.06
- Eva Live Inc (CIK 0001983736), 2026-06-30: 282.70

**F5_share_dilution**, most extreme (one row per entity):

- Cyngn Inc. (CIK 0001874097), 2022-03-31: 2682.92
- SKYTECH ORION GLOBAL CORP. (CIK 0001498067), 2020-12-31: 2558.91
- AvePoint, Inc. (CIK 0001777921), 2022-06-30: 1989.27
- Alphabet Inc. (CIK 0001652044), 2022-09-30: 1858.85
- CHANNELADVISOR CORP (CIK 0001169652), 2014-03-31: 1806.47

**S1_customer_concentration**, most extreme (one row per entity):

- VEEA INC. (CIK 0001840317), 2026-03-31: 99.00
- CACI INTERNATIONAL INC /DE/ (CIK 0000016058), 2025-09-30: 95.70
- CSRA Inc. (CIK 0001646383), 2017-09-30: 94.00
- DATASEA INC. (CIK 0001631282), 2019-12-31: 85.10
- CONCENTRIX CVG Corp (CIK 0001062047), 2012-12-31: 85.00

**S2_gross_margin_trend**, most extreme (one row per entity):

- UNITED ONLINE INC (CIK 0001142701), 2014-06-30: -172.26
- Hortonworks, Inc. (CIK 0001610532), 2016-03-31: 130.40
- Sabre Corp (CIK 0001597033), 2021-06-30: 68.36
- RUM Group Inc. (CIK 0001830081), 2025-09-30: 64.30
- CLEANSPARK, INC. (CIK 0000827876), 2021-12-31: 50.61

**B2_ceo_cfo_departures**, most extreme (one row per entity):

- Sports Entertainment Gaming Global Corp (CIK 0001673481), 2022-12-31: 5.00
- DOCUSIGN, INC. (CIK 0001261333), 2023-03-31: 5.00
- 3D SYSTEMS CORP (CIK 0000910638), 2020-06-30: 5.00
- SYNCHRONOSS TECHNOLOGIES INC (CIK 0001131554), 2017-12-31: 5.00
- ServiceNow, Inc. (CIK 0001373715), 2019-12-31: 4.00

**B5_late_filings**, most extreme (one row per entity):

- Friendable, Inc. (CIK 0001414043), 2012-12-31: 8.00
- IRONCLAD ENCRYPTION Corp (CIK 0001455926), 2019-06-30: 8.00
- Red Cat Holdings, Inc. (CIK 0000748268), 2021-09-30: 8.00
- Leader Capital Holdings Corp. (CIK 0001715433), 2022-12-31: 8.00
- REALLOYS INC. (CIK 0001567900), 2020-03-31: 8.00

**O1_revenue_growth_decel**, most extreme (one row per entity):

- RideNow Group, Inc. (CIK 0001596961), 2020-09-30: -2062.19
- FAB Universal Corp. (CIK 0001074909), 2014-09-30: -846.66
- Forest Investments, Inc. (CIK 0001082506), 2020-09-30: -737.10
- CLEANSPARK, INC. (CIK 0000827876), 2023-06-30: -675.61
- CoreWeave, Inc. (CIK 0001769628), 2026-03-31: -568.31

**O3_headcount_trend**, most extreme (one row per entity):

- Red Cat Holdings, Inc. (CIK 0000748268), 2023-06-30: 400.00
- SOUNDTHINKING, INC. (CIK 0001351636), 2026-09-30: 376.56
- Veradigm Inc. (CIK 0001124804), 2012-12-31: 363.24
- Sonus, Inc. (CIK 0001105472), 2014-06-30: 362.45
- LIVE VENTURES Inc (CIK 0001045742), 2015-12-31: 333.33

**N4_mda_specificity_change**, most extreme (one row per entity):

- EPAM Systems, Inc. (CIK 0001352010), 2021-12-31: -99.43
- Upland Software, Inc. (CIK 0001505155), 2022-06-30: -93.91
- OPEN TEXT CORP (CIK 0001002638), 2012-12-31: 84.77
- Match Group Holdings II, LLC (CIK 0001575189), 2020-03-31: -82.24
- Snap Inc (CIK 0001564408), 2022-12-31: -72.96

