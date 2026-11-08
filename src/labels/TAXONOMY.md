# Collapse Event Taxonomy

Status: **v1.0 FROZEN 2026-11-08** (owner approved). Any change to this file, to
`events.csv` or to `adjudications.csv` is a logged decision in docs/decisions.md, never a quiet edit.
Frozen event table: `src/labels/events.csv`, SHA-256 `cbeb3f4615f76742b09cb5dae24e7c25aec95011a447a2080a2fa1ceb4fe96f9`. `src/labels/labels.py` refuses to
load a different file unless explicitly told to.
Niche: US-listed application software (see docs/decisions.md).
Implementation: `src/labels/build_events.py` → `src/labels/events.csv`.

Each event type must be dated and verifiable from a free public source (SEC EDGAR). Event
types that cannot meet that bar with free data are listed under "Not labelable in v1" and are
excluded rather than approximated.

## Shared rules
- **8-K report date:** the "date of earliest event reported" on the 8-K cover, as recorded in
  the EDGAR index. Used when it falls 0 to 30 days before the filing date; otherwise the filing
  date is used and the gap is recorded in `date_uncertainty_days`.
- **Merger context:** within 365 days before to 30 days after the event, the company filed any
  of: 8-K Item 5.01 (change in control), 8-K Item 2.01 (completion of acquisition), DEFM14A,
  PREM14A, DEFM14C, PREM14C, SC 14D9, SC TO-T, SC 13E3. M&A-driven exits are not collapses.
- **Onset rule:** a repeat of the same event type within 730 days of the previous one (400 days
  for going concern, i.e. consecutive annual reports) is a continuation, not a new event.
- **SPAC period excluded:** events dated while the registrant's latest 10-K was filed under a
  blank-check (SPAC) name are dropped. SPACs are shells, excluded from the universe.
- **Manual adjudications:** `src/labels/adjudications.csv` records every event dropped after
  reading the source filing, with the reason (17 at v0.2). Rules stay automatic; the file only
  removes verified false positives.

## Tier 1: Terminal

| Code | Definition | Proving source | Event date | Known ambiguities |
|---|---|---|---|---|
| T1_BANKRUPTCY | The registrant enters bankruptcy or receivership | 8-K Item 1.03 | 8-K report date (usually the petition date) | Item 1.03 also used for subsidiary-only cases and court final decrees (adjudicated out); prepackaged Chapter 11 where equity survives; foreign insolvency |
| T1_DELISTING | Exchange removes the common stock for failing listing standards | Form 25-NSE citing Rule 12d2-2(b), class = common / ordinary / Class A | 25-NSE filing date | Trading is often suspended weeks earlier (spread to the last 3.01 notice is recorded); a company can relist later (e.g. Avid 2014). Rule 12d2-2(a) removals (merger exchange, redemption, maturity) are excluded |
| T1_DEREGISTRATION | Company stops SEC reporting outside a merger | Form 15 (15-12B, 15-12G, 15-15D), no merger context, no 10-K/10-Q in the next 18 months, no other Tier 1 event in the prior 365 days | Form 15 date; if the last periodic report was more than 180 days earlier, the first missed report (last report + 105 days) | Some healthy small companies go dark to save costs; merger filings under a different CIK can be missed (one adjudicated) |
| T1_REPORTING_CEASED | Company stops filing 10-K/10-Q without a Form 15, merger, delisting or other Tier 1 event | EDGAR filing index: last 10-K/10-Q followed by 18 months of silence | Last periodic report + 105 days (first missed report) | Date is approximate by construction (low confidence); a company could resume filing |
| T1_LIQUIDATION | Plan of complete liquidation and dissolution, or wind-down and cessation of the business | 8-K Item 2.05 wind-down language; 8-K / proxy text, checked by reading the filing | 8-K report date or first filing announcing it | Liquidation after a fair-value sale of the business is a return of capital, not distress (Altaba adjudicated out) |

## Tier 2: Severe

| Code | Definition | Proving source | Event date | Known ambiguities |
|---|---|---|---|---|
| T2_GOING_CONCERN | First annual report stating that substantial doubt exists about the company's ability to continue as a going concern (auditor opinion, auditor consent, or management conclusion, not alleviated) | 10-K text and exhibits found by EDGAR full-text search, every candidate document classified sentence by sentence | 10-K filing date | Hypothetical risk-factor language ("could raise substantial doubt") and negations ("not probable", "alleviated") are filtered out. The underlying condition exists before the filing; the date is when it became public |
| T2_DEBT_ACCELERATION | A default or covenant breach accelerates a direct financial obligation | 8-K Item 2.04, no merger context, not within 30 days of a bankruptcy, and the text describes a default (redemptions, holder puts and tender offers adjudicated out) | 8-K report date | Technical defaults cured within days; defaults at a subsidiary under a parent-guaranteed facility |
| T2_MASS_LAYOFF | Restructuring that cuts 30% or more of the total workforce | 8-K Item 2.05 text stating a percentage of the workforce | 8-K report date | Percentages are approximate; layoffs disclosed only in press releases (8.01 / 7.01) are missed |

## Tier 3: Early stress (recorded, not counted as positive)

| Code | Definition | Proving source | Event date | Known ambiguities |
|---|---|---|---|---|
| T3_LISTING_DEFICIENCY | Exchange notice of failure to meet a listing rule, outside a merger | 8-K Item 3.01, no merger context, not within 30 days after a bankruptcy | 8-K report date | Includes cured, technical deficiencies (late filing, minimum bid price) |
| T3_EXEC_EXIT_AFTER_RESTATEMENT | An officer or director departure within 365 days after a non-reliance restatement | 8-K Item 5.02 within 365 days after an 8-K Item 4.02 | Date of the 5.02 | CEO/CFO not verified from text in v0.2 (low confidence) |

## Not labelable in v1 (excluded, not approximated)

| Proposed event | Why excluded | What would make it labelable |
|---|---|---|
| Distressed sale (below last round or below 50% of peak value) | Needs share prices that include delisted companies, a paid source (decision 2026-11-07) | Survivorship-free price data |
| Drawdown of 70% or more from peak | Same as above | Same as above |
| Regulatory action | No free, dated, company-mapped source with consistent severity for this niche | A curated enforcement dataset |
| Major customer loss | No standard filing item; free text only, low reliability | Manual review of 10-K customer disclosures |
| Covenant breach without acceleration | Waivers and amendments are not disclosed in a dated, itemized form | Text extraction from credit-agreement amendments |

## Positive label for the baseline (approved 2026-11-08)

**Positive = any Tier 1 or Tier 2 event inside the forward window. Tier 3 is recorded only.**

1. **Tier 1 alone fails the kill gate.** Only 33 universe entities have a scorable Tier 1 event,
   under the 50 minimum. Tier 1 + Tier 2 gives 77 scorable events at 70 entities.
2. **Tier 2 is what the buyer needs.** For a procurement or vendor-risk team, a going-concern
   opinion, a debt default or a 30%+ layoff is the point at which a vendor relationship has to
   be re-examined. Bankruptcy is often too late to act on.
3. **Tier 2 events are as verifiable as Tier 1.** Each comes from a specific filing with a date,
   and all were checked against document text.
4. **Tier 3 is excluded** because it overlaps with planned signals (late filing and exchange
   notices, executive departures), is noisy (most deficiency notices are cured), and would make
   the label partly a restatement of the features.

Sensitivity: the label function takes `tiers`, so every backtest can also report Tier 1 only.
