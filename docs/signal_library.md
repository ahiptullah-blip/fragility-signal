# Signal Library (Prompt 2, Steps 1 and 2)

Status: **Shortlist PROPOSED, awaiting owner review.** No data ingested, no code written.
Date: 2026-11-07
Niche: US-listed application software (SIC 7370–7373), 10-K filers, public float $50M or more,
scoring from 2012. See docs/decisions.md.

## Conventions used below
- **Point-in-time (PIT):** *yes* means every input carries a public filing or acceptance timestamp,
  so the value can be rebuilt exactly as of any past date. *partial* means coverage or timestamps
  are incomplete. *no* means history is overwritten or not retained.
- **XBRL as-filed:** values are taken from the SEC Financial Statement Data Sets (or company facts
  filtered on the `filed` date), always the **first-filed** value for a period. Later amendments
  and comparative-period restatements are ignored, per CLAUDE.md rule 1.
- **XBRL start:** large accelerated filers from 2009; all other filers from fiscal periods ending
  after 2011-06-15. Notes with dimensions (for example customer concentration) are only in the SEC
  *Financial Statement and Notes* Data Sets, not the company facts API.
- **Quarterly flows:** 10-Q cash-flow figures are year-to-date, so quarters are de-cumulated and Q4 is
  derived as annual minus nine-month year-to-date. TTM means the trailing four quarters.
- **Available date:** a value is usable from the filing's EDGAR acceptance timestamp, never from the
  period end.
- **Fragile if:** the direction of the hypothesis.
- **Paid:** a signal needing a paid source is marked **DEFERRED** and will not be implemented.

---

## Step 1: Candidate signals (30)

### Financial fragility

| # | Signal | Definition | Computation | Source | Freq. | Earliest | PIT | Fragile if |
|---|---|---|---|---|---|---|---|---|
| F1 | Cash runway | Quarters of cash left at the current burn rate | (Cash and equivalents + short-term investments) / max(−TTM operating cash flow / 4, 0). If operating cash flow is positive, cap at 40 quarters | XBRL as-filed | Quarterly | 2009 / 2011 | yes | Lower |
| F2 | Refinancing wall | Debt principal due in the next 24 months relative to cash | (Maturities due in year 1 + year 2 from the latest 10-K debt schedule, including convertibles) / (cash + short-term investments) | XBRL as-filed (`LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths`, `...InYearTwo`) | Annual | 2009 / 2011 | yes | Higher |
| F3 | Net debt to revenue | Leverage scaled by revenue, since EBITDA is often negative | (Total debt, including convertibles − cash − short-term investments) / TTM revenue | XBRL as-filed | Quarterly | 2009 / 2011 | yes | Higher |
| F4 | DSO change | Customers taking longer to pay, year over year | DSO = accounts receivable / quarterly revenue × 91.25. Signal = DSO now − DSO four quarters earlier | XBRL as-filed | Quarterly | 2009 / 2011 | yes | Rising |
| F5 | Share dilution | Growth in shares outstanding, i.e. reliance on equity to fund operations | Year-over-year % change in cover-page shares outstanding (`dei:EntityCommonStockSharesOutstanding`, summed across classes) | XBRL as-filed (cover page) | Quarterly | 2009 / 2011 | yes | Higher |

### Structural fragility

| # | Signal | Definition | Computation | Source | Freq. | Earliest | PIT | Fragile if |
|---|---|---|---|---|---|---|---|---|
| S1 | Customer concentration | Share of revenue from the largest single customer | Max `ConcentrationRiskPercentage1` with revenue benchmark and customer concentration type, from the latest 10-K. Not disclosed means no customer at 10% or more (ASC 280 requires disclosure at that level); recorded as "<10%" with a flag | SEC Financial Statement and Notes Data Sets; 10-K note text as fallback | Annual | 2010 / 2012 (detail tagging) | yes | Higher |
| S2 | Gross margin trend | Erosion of pricing power or rising delivery cost | TTM gross margin − TTM gross margin four quarters earlier, in percentage points | XBRL as-filed | Quarterly | 2009 / 2011 | yes | Falling |
| S3 | Platform dependence | Reliance on a single distribution or infrastructure platform | Count of risk-factor (Item 1A) paragraphs that name a dependence on a platform from a fixed list (app stores, hyperscalers, Salesforce, Workday, Shopify and so on) | 10-K full text | Annual | FY2005 | yes | Higher |
| S4 | Single-regulator dependence | Reliance on one license or regulator (mainly the fintech subset) | Count of Item 1A paragraphs naming dependence on a specific license or regulator (money transmitter, CFPB, OCC, a sponsor bank) | 10-K full text | Annual | FY2005 | yes | Higher |

### Behavioral and institutional

| # | Signal | Definition | Computation | Source | Freq. | Earliest | PIT | Fragile if |
|---|---|---|---|---|---|---|---|---|
| B1 | Net insider selling | Officers and directors selling more than they buy | (Open-market shares sold − bought, Form 4 codes S and P) / shares outstanding, trailing 6 months | SEC Form 4 / Insider Transactions Data Sets | Event | 2003 (XML) / 2006 (data sets) | yes | Higher |
| B2 | CEO/CFO departure | The top executive or finance chief leaves | Count of 8-K Item 5.02 filings in the trailing 12 months whose text reports a CEO or CFO (or principal executive or financial officer) resigning, being terminated, or stepping down | EDGAR 8-K item index + text | Event | 2004-08 | yes | Higher |
| B3 | Auditor change | The company changes auditor | 1 if an 8-K Item 4.01 was filed in the trailing 24 months, else 0. Sub-flag: auditor resigned vs was dismissed | EDGAR 8-K item index + text | Event | 2004-08 | yes | 1 (resignation worse) |
| B4 | Restatement / non-reliance | Prior financials declared unreliable | 1 if an 8-K Item 4.02 was filed in the trailing 24 months | EDGAR 8-K item index | Event | 2004-08 | yes | 1 |
| B5 | Late filing | The company cannot file its 10-K or 10-Q on time | Count of NT 10-K and NT 10-Q (Form 12b-25) filings in the trailing 24 months | EDGAR filing index | Event | 1996 | yes | Higher |
| B6 | Material weakness | Internal controls over financial reporting declared deficient | 1 if the latest 10-K Item 9A or 10-Q Item 4 reports a material weakness (text match) | 10-K / 10-Q text | Quarterly | 2004 / 2007 | yes | 1 |
| B7 | Going-concern language | Management or auditor states substantial doubt the company can continue | 1 if the latest 10-K or 10-Q contains "substantial doubt" together with "going concern" | 10-K / 10-Q text | Quarterly | 1996 (auditor) / 2016 (management, ASU 2014-15) | yes | 1 |
| B8 | Guidance cut or withdrawn | Forward guidance lowered or pulled | Text match in 8-K Item 2.02 exhibit 99.1 for lowering or withdrawing guidance vs the prior release | 8-K exhibit text | Quarterly | 2003 | partial | 1 |

### Operational and demand

| # | Signal | Definition | Computation | Source | Freq. | Earliest | PIT | Fragile if |
|---|---|---|---|---|---|---|---|---|
| O1 | Revenue growth deceleration | Growth slowing year over year | (TTM revenue growth year over year now) − (same measure four quarters earlier), in percentage points | XBRL as-filed | Quarterly | 2010 / 2012 (needs two years) | yes | Negative |
| O2 | Billings growth deceleration | Forward demand slowing | Billings = quarterly revenue + Δ(current + noncurrent deferred revenue). Same deceleration formula as O1 | XBRL as-filed | Quarterly | 2010 / 2012 | yes | Negative |
| O3 | Headcount trend | Workforce shrinking | Year-over-year % change in employees reported in 10-K Item 1 (always required under Reg S-K 101), from text, or `dei:EntityNumberOfEmployees` where tagged | 10-K full text | Annual | 1996 | yes | Negative |
| O4 | Job posting velocity | Hiring freezes before they show in headcount | 90-day change in active job postings | LinkUp / Revelio / Lightcast (paid); Wayback careers pages (patchy) | Daily | 2007+ (paid) | partial | Falling | 
| O5 | Employee review sentiment | Employee morale falling | Rolling change in average employer rating | Glassdoor / Indeed | Continuous | n/a | no | Falling |
| O6 | Customer review sentiment | Product satisfaction falling | Rolling change in average product rating and review volume | G2 / Capterra / TrustRadius | Continuous | n/a | no | Falling |
| O7 | Product release cadence | Shipping slows | Count of release or changelog entries per quarter | Company changelogs via Wayback; newswire archives (paid) | Irregular | Patchy | partial | Falling |
| O8 | Support complaint volume | Customer complaints rising | Complaints per quarter, matched to the company | CFPB Consumer Complaint Database (free; consumer fintech only) | Daily | 2011-12 | yes (receipt date is fixed) | Rising |

### Narrative

| # | Signal | Definition | Computation | Source | Freq. | Earliest | PIT | Fragile if |
|---|---|---|---|---|---|---|---|---|
| N1 | Press volume vs specifics | Media attention rising while concrete content falls | Change in article count mentioning the company / change in numeric density of those articles | GDELT 2.0 (free; counts and metadata, no full text) | Daily | 2015-02 | partial | Ratio rising |
| N2 | Promotional tone | Earnings releases becoming more upbeat | Share of positive-dictionary words in 8-K Item 2.02 exhibit 99.1, change year over year | 8-K exhibit text + sentiment word list (license to check) | Quarterly | 2003 | yes | Rising |
| N3 | Story vs numbers divergence | Tone improves while results weaken | z-score of N2 tone − z-score of TTM revenue growth, within the universe on the scoring date | N2 + XBRL | Quarterly | 2010 / 2012 | yes | Higher |
| N4 | MD&A specificity decline | Management uses fewer concrete figures | Numeric tokens (digits, %, $) per 1,000 words in 10-K Item 7, minus the same in the prior 10-K | 10-K full text | Annual | 2001 | yes | Falling |
| N5 | Risk-factor expansion | Risk disclosures growing quickly | Year-over-year % change in the word count of 10-K Item 1A | 10-K full text | Annual | FY2005 | yes | Higher |

---

## Step 2: Shortlist (12)

Rules applied: point-in-time must be *yes*; at least 8 years of history; explainable in one sentence;
every family contributes at least one. Additional cuts for redundancy, overlap with likely collapse
labels, and subjectivity.

| # | Signal | One-sentence reading | Freq. | Family |
|---|---|---|---|---|
| F1 | Cash runway | "At the current burn, cash lasts N quarters." | Q | Financial |
| F2 | Refinancing wall | "Debt due in the next 2 years is X times cash on hand." | A | Financial |
| F4 | DSO change | "Customers are taking N more days to pay than a year ago." | Q | Financial |
| F5 | Share dilution | "Share count grew X% in a year to fund the business." | Q | Financial |
| S1 | Customer concentration | "One customer is X% of revenue." | A | Structural |
| S2 | Gross margin trend | "Gross margin fell N points in a year." | Q | Structural |
| B2 | CEO/CFO departure | "The CEO or CFO left in the last 12 months." | Event | Behavioral |
| B3 | Auditor change | "The auditor changed (or resigned) in the last 24 months." | Event | Behavioral |
| B5 | Late filing | "The company missed N filing deadlines in 2 years." | Event | Behavioral |
| O1 | Revenue growth deceleration | "Growth slowed from X% to Y% in a year." | Q | Operational |
| O3 | Headcount trend | "Headcount fell X% year over year." | A | Operational |
| N4 | MD&A specificity decline | "Management uses fewer hard numbers than last year." | A | Narrative |

Families: Financial 4, Structural 2, Behavioral 3, Operational 2, Narrative 1. All 12 are point-in-time *yes* and
all have 12+ years of history by 2026.

### Every cut, in one sentence
- **F3 Net debt to revenue:** most of the universe carries little debt beyond convertibles, so the refinancing wall captures the debt risk that actually bites, without redundancy.
- **S3 Platform dependence:** needs a hand-built list of platforms, which is subjective and invites hindsight about which names to include.
- **S4 Single-regulator dependence:** relevant only to the fintech subset and needs the same subjective list.
- **B1 Net insider selling:** software executives sell routinely for tax and diversification on stock compensation, and the 10b5-1 plan flag only exists from 2023, so the signal is noisy.
- **B4 Restatement:** rare in this universe and mostly co-occurs with late filings and auditor changes, which are kept.
- **B6 Material weakness:** overlaps heavily with late filing and auditor change. Held as the first substitute.
- **B7 Going-concern language:** likely to be a collapse event in the Prompt 3 taxonomy, so using it as a signal would predict the label with itself.
- **B8 Guidance cut:** no standard format and many small caps never give guidance, so it is only partially reconstructable.
- **O2 Billings growth deceleration:** redundant with revenue deceleration and distorted by changes in billing terms (annual vs multi-year upfront).
- **O4 Job posting velocity:** needs a paid source. **DEFERRED.**
- **O5 Employee review sentiment:** no point-in-time history (ratings are recomputed, pages change) and collection breaks the site's terms. Not reconstructable.
- **O6 Customer review sentiment:** same problem as O5, and history is only available from paid vendors. **DEFERRED.**
- **O7 Product release cadence:** no consistent free archive; Wayback coverage of changelogs is too patchy.
- **O8 Support complaint volume:** the CFPB database covers only consumer-facing fintech, a small slice of the universe.
- **N1 Press volume vs specifics:** GDELT has counts but not article text, and company-name matching is noisy.
- **N2 Promotional tone:** relies on a sentiment word list whose commercial license must be checked first. Held as the substitute for N4.
- **N3 Story vs numbers divergence:** a compound of N2 and growth, so it inherits N2's license question and is harder to read than its parts.
- **N5 Risk-factor expansion:** length is driven mostly by SEC rule changes (for example the 2020 risk-factor summary requirement) and legal boilerplate, not by the company.

### Points for owner review
1. **Order vs rule 2.** Step 3 ingests signal data and produces a data quality report (outliers,
   coverage) before Prompt 3 freezes the event taxonomy. CLAUDE.md says collapse events must be
   defined before looking at signal data. Recommendation: run Prompt 3 (taxonomy) before Step 3,
   or at minimum never join signals to outcomes until the taxonomy is frozen.
2. **Late filing vs delisting labels.** Exchanges delist companies for chronic late filing, so B5
   could mechanically predict a "delisting" label. The taxonomy should decide whether
   delisting-for-late-filing counts as a collapse, or B5 must be read with that in mind.
3. **Staleness of annual signals.** F2, S1, O3 and N4 update only with the 10-K, so they can be up to
   about 15 months old on a given scoring date. The value will always come from the latest filing
   accepted before the scoring date.
4. **Single source.** All 12 signals come from SEC EDGAR (filing index, XBRL as-filed, filing text).
   That means three ingestion scripts, no licensing, and clean timestamps. The cost is that there's
   no independent alternative-data signal. The operational family relies on filings, because job
   postings and reviews are paid or not reconstructable.
