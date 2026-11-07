# Niche Selection (Prompt 1): Decision Analysis

Status: **CONFIRMED 2026-11-07.** Owner chose "all application software"; the remaining open
questions were delegated and are resolved in docs/decisions.md (2026-11-07). The questions list at
the end is kept for the record.
Date: 2026-11-07

## Scoring scale
Every criterion is scored 1 to 5, where **5 is always best for the project**. For "cost of a false
positive", 5 means a false positive is cheap and 1 means it is damaging.

Two totals are reported:
- **Unweighted**: simple sum, max 35.
- **Feasibility-weighted**: ground truth, data history, event count and point-in-time are doubled, max 55.
  Reason: those four decide whether a valid backtest can exist at all. Edge, buyer and false-positive
  cost decide whether a valid result is worth having. A niche that fails feasibility cannot be
  rescued by edge.

**Gate rule:** any niche scoring 2 or lower on ground truth, event count, or point-in-time is
disqualified as a *prototype* regardless of total, because it would break CLAUDE.md rules 1 to 3.

Event counts and data claims below are desk estimates from known public sources. They have **not**
been verified against data. Verifying them is the first task in week 1.

---

## 1. Public small and mid-cap enterprise software (HCM, payroll, fintech-adjacent)

| Criterion | Score | Justification |
|---|---|---|
| Ground truth | 3 | Bankruptcy (8-K Item 1.03), involuntary delisting (8-K Item 3.01, Form 25), first going-concern opinion are dated and public. But software firms usually get *sold* rather than fail, and a "distressed sale" is ambiguous. |
| Data history | 4 | SEC EDGAR filings index (free, includes dead filers, 1994+); XBRL financials (free, 2009 to 2011+ by filer size); SEC Financial Statement Data Sets (free, as filed). Survivorship bias: free price data (Yahoo and similar) drops delisted tickers. Survivorship-free prices need a paid source (CRSP via WRDS, Sharadar, EODHD). |
| Event count | 3 | All US-listed application software with a public-float floor: rough estimate 80 to 200 events, 2012 to 2024. **HCM and payroll alone: likely under 20, which fails.** Only viable if the niche is broadened to all application software. |
| Point-in-time | 5 | Every EDGAR filing has an acceptance timestamp. XBRL company facts carry a `filed` date per value, so as-of reconstruction is exact and amendments are separately identifiable. Best of all five niches. |
| My edge | 4 | You can read NRR and churn language, RPO and deferred revenue quality, customer concentration, partner-ecosystem standing, and exec turnover (8-K Item 5.02) better than a generalist. Public-market signals are more crowded than private ones. |
| Buyer | 4 | Enterprise procurement and third-party-risk teams (am I betting a 7-year HCM or payroll contract on this vendor?), HR tech buyers, credit investors, M&A advisors. Incumbents exist (RapidRatings, D&B, S&P), but they are not specialized in software or HCM. |
| Cost of false positive | 4 | Inputs are public disclosures and a flag is an opinion on public data. Cost is a missed relationship or bad investment call, not harm to the entity. |
| **Unweighted / Weighted** | **27 / 42** | |

## 2. Private HR tech and Workday ecosystem vendors

| Criterion | Score | Justification |
|---|---|---|
| Ground truth | 2 | Private vendors fade rather than fail on a date: quiet shutdowns, acqui-hires, asset sales. WARN notices only cover larger employers. Dates are usually fuzzy within months. |
| Data history | 2 | Crunchbase and PitchBook (paid, backfilled, dead companies under-represented). LinkedIn headcount (no API, ToS issues). Job postings via Revelio or LinkUp (paid). Wayback Machine (free, patchy). Workday partner directory (no history except Wayback). Heavy survivorship bias throughout. |
| Event count | 3 | Many failures exist in reality (hundreds of HR tech startups), but few can be dated and verified to label quality. |
| Point-in-time | 1 | Commercial private-company databases silently overwrite and backfill history. Effectively impossible to reconstruct what was knowable on a past date. |
| My edge | 5 | Your home turf: partner tiers, implementation quality, customer chatter, talent flows. |
| Buyer | 4 | CHROs and HRIS leaders selecting point solutions, Workday partners, VCs, PE. Real pain, since a vendor dying mid-implementation is costly. |
| Cost of false positive | 2 | Flagging a small private company as failing can become self-fulfilling and carries legal risk (defamation, tortious interference). |
| **Unweighted / Weighted** | **19 / 27** | **Disqualified as prototype** (fails ground truth and point-in-time gates). |

## 3. Regional banks

| Criterion | Score | Justification |
|---|---|---|
| Ground truth | 5 | The FDIC Failed Bank List is official, dated and unambiguous: about 570 failures since October 2000. Secondary events: published enforcement actions (FDIC, OCC, Fed) and assisted mergers. |
| Data history | 5 | FFIEC Call Reports (free, quarterly, every insured bank, bulk from 2001) and FDIC BankFind API (free, historical financials, includes inactive institutions). Failed banks remain in the data, so there is no survivorship bias. |
| Event count | 5 | About 570 total, but **about 507 fall in 2008 to 2014** and only about 40 since 2015. Strictly "regional" banks ($10 to $100B) have very few failures, so the universe must widen to all FDIC-insured banks. |
| Point-in-time | 4 | Call reports are publicly available about 30 to 45 days after quarter end, so the lag is easy to model. Amendments overwrite in the bulk files, so first-published values need care. |
| My edge | 1 | No banking domain advantage. Signals are textbook (capital, NPLs, CRE concentration, brokered and uninsured deposits). |
| Buyer | 3 | Corporate and municipal treasurers placing deposits (post-SVB), fintechs choosing BaaS sponsor banks. Crowded: regulators, rating agencies, free star ratings (Bauer, Bankrate). |
| Cost of false positive | 3 | A published flag on a bank can contribute to a run. Privately delivered, cost is moderate. |
| **Unweighted / Weighted** | **26 / 45** | Highest feasibility; weakest edge. Events heavily clustered in one crisis. |

## 4. Multi-unit restaurant and franchise brands

| Criterion | Score | Justification |
|---|---|---|
| Ground truth | 4 | Chain Chapter 11 filings are dated court records, and there are frequent waves (2020, 2023 to 2025). Brand-level "collapse" vs reorganization vs franchisor sale needs definition. |
| Data history | 3 | Franchise Disclosure Documents in state archives (WI, MN, CA; free, annual; Item 20 unit closures, Item 21 financials) are PDFs and need heavy extraction, and archive retention needs verifying. SBA 7(a) loan FOIA data (free, 1990s+) has franchise codes and charge-offs. EDGAR for public chains. Placer.ai foot traffic is paid with short history. |
| Event count | 4 | Brand-level failures and chain bankruptcies likely 100+ over 10 years. Franchisee-level charge-offs number in the thousands via SBA. |
| Point-in-time | 3 | FDDs carry issuance dates (good PIT) but are annual only. SBA data is updated in place for outcomes, though approval dates are fixed. |
| My edge | 1 | No domain advantage. |
| Buyer | 3 | SBA and franchise lenders, landlords and REITs, prospective franchisees. FRANdata already sells franchise-brand risk scores to lenders. |
| Cost of false positive | 3 | Franchisors are litigious, and a flag can deter franchisee sales. |
| **Unweighted / Weighted** | **21 / 35** | |

## 5. Hospital systems and physician groups

| Criterion | Score | Justification |
|---|---|---|
| Ground truth | 4 | Hospital closures (UNC Sheps Center rural closure list, about 180 to 200 since 2005), bankruptcies (Steward, Prospect), muni bond defaults on EMMA. Physician groups: private, poor ground truth. Narrow to hospitals. |
| Data history | 4 | CMS HCRIS cost reports (free, 1996+, closed hospitals retained; form schema break in 2010), IRS Form 990 e-file (free, 2011+), MSRB EMMA continuing disclosures (free, 2009+, PDFs). |
| Event count | 3 | About 100 to 200 hospital-level events since 2010, many rural and small. |
| Point-in-time | 2 | HCRIS files are republished as reports are amended and settled, and vintage snapshots aren't systematically kept. Reports lag 5 to 18 months. Hard to know what was knowable when. |
| My edge | 2 | Some adjacency through Workday's healthcare clients (labor cost, staffing), but the core signals are reimbursement and payer mix. |
| Buyer | 3 | Muni bond investors, GPOs and suppliers, staffing firms, state agencies. Rating agencies are incumbent. |
| Cost of false positive | 3 | Public flags can affect bond pricing, recruiting and community trust. |
| **Unweighted / Weighted** | **21 / 34** | Point-in-time is borderline. |

---

## Scoring table

| Niche | Ground truth | Data | Events | PIT | Edge | Buyer | FP cost | **Unweighted (/35)** | **Weighted (/55)** | Gate |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. Public SMID software | 3 | 4 | 3 | 5 | 4 | 4 | 4 | **27** | **42** | Pass (event count conditional) |
| 2. Private HR tech | 2 | 2 | 3 | 1 | 5 | 4 | 2 | 19 | 27 | **Fail** |
| 3. Regional banks | 5 | 5 | 5 | 4 | 1 | 3 | 3 | 26 | **45** | Pass |
| 4. Restaurants / franchise | 4 | 3 | 4 | 3 | 1 | 3 | 3 | 21 | 35 | Pass |
| 5. Hospitals / physician groups | 4 | 4 | 3 | 2 | 2 | 3 | 3 | 21 | 34 | Borderline (PIT) |

## Recommendation

**Prototype: Niche 1, public software, broadened to all US-listed application software**
(SIC 7372/7373 plus named fintech-adjacent names), not HCM and payroll alone.

**Second iteration: Niche 3, banks** (all FDIC-insured institutions).

### The tradeoff
Banks win on feasibility (45 vs 42 weighted); software wins on overall value (27 vs 26 unweighted).
The two are close to a tie, so the choice comes down to what the prototype is for.

- Choosing banks optimizes for **proving the method works**. Labels are clean and plentiful, and
  published academic bank-failure models give a known benchmark. The cost: the result has little
  commercial use for you (no edge, crowded buyers), and about 90% of events sit in one crisis
  (2008 to 2014). A walk-forward test on post-2015 years would have only a handful of positives.
- Choosing software optimizes for **a result that matters to you**. It has the best point-in-time
  data of all five (EDGAR timestamps make rule 1 enforceable, not aspirational), it is where your
  edge sharpens signal choice and interpretation, and it has a buyer you understand. The cost:
  labels are fuzzier and the event count is unverified.

I chose software because its weakness (label count and ambiguity) **can be tested cheaply in week 1
before any modeling**, while banks' weakness (no edge, crowded market) cannot be fixed by any amount
of work. That is the honest counter to "you picked the one that matches your resume": the choice
comes with a hard kill gate. If the frozen taxonomy yields fewer than 50 events with a float floor,
switch to banks with no sunk cost beyond the taxonomy.

Banks are the second iteration because they are the only other niche that clears every gate. They
also make a clean out-of-domain test: if the engine's signals and pipeline generalize there, the
method is real rather than overfit to software.

**Private HR tech (Niche 2)** is the commercial end state but cannot be backtested on its own.
The realistic path is later: validate signals on public software that are also observable for
private companies (headcount trend, job postings, exec departures, partner-tier changes), then carry
them over with lower confidence. That is a scope expansion and needs separate approval under rule 7.

## Top 3 risks for the recommended niche, and week-1 de-risking

1. **Too few or ambiguous labels.** Software companies get acquired instead of failing, HCM-only is
   too small, and micro-cap shells dominate raw failure counts.
   *Week 1:* draft the event taxonomy (bankruptcy, involuntary delisting, first going-concern
   opinion; distressed sale only with an explicit, pre-registered price rule or excluded). Count
   events from EDGAR 8-K items and Form 25 only, with a public-float floor taken from the 10-K cover
   page (`dei:EntityPublicFloat`, itself point-in-time). Hand-review 20 edge cases. **Go/no-go:**
   at least 50 events (target 100+), otherwise fall back to banks. Counting labels is not looking at
   signal data, so this respects rule 2.

2. **Survivorship bias in universe and prices.** Free price sources silently drop dead tickers.
   *Week 1:* build the universe only from EDGAR's full filer history (dead filers included). Spot-check
   10 known delisted or bankrupt software names to confirm they're present. Decide between a paid
   survivorship-free price source and no price-based signals in v1 (fundamentals and filing events
   only).

3. **Regime and size confounds.** The 2021 de-SPAC wave and the 2022 SaaS drawdown cluster events.
   The model may learn "small, de-SPAC, 2022" rather than fragility.
   *Week 1:* using the label table alone, compute base rates by year, float bucket and listing route
   (IPO vs de-SPAC). Pre-register the walk-forward folds and report every metric against
   size- and year-stratified base rates (rule 4). Decide explicitly whether de-SPACs are in the
   universe.

## What I need from you before data sourcing

1. **Confirm the niche and boundary:** all US-listed application software (recommended) vs HCM and
   payroll only (likely too few events). Include fintech-adjacent names? Include foreign filers
   (20-F)?
2. **The v1 buyer:** procurement and vendor risk, or investors. This changes what "collapse" means:
   a procurement buyer also cares about acquire-and-sunset of the product, while an investor cares
   about equity wipeout. It has to be settled before the taxonomy is frozen.
3. **Paid data budget:** yes or no for a survivorship-free price source. If no, v1 uses no price
   signals.
4. **Window and history:** confirm the 12-month forward window and a start year (2012 suggested,
   once XBRL covers small filers).
5. **Size floor and exclusions:** public-float floor (e.g. $50M or $100M), and whether to include
   de-SPACs and shells.
6. **A list of collapses you know of** from your career, used only to test the label pipeline's
   recall, never for training or signal design.
7. **SEC contact identity:** SEC EDGAR requires a User-Agent with a contact name and email on every
   request. Tell me what to use. I won't use your email unless you say so.
8. **Network access:** this cloud environment may need `sec.gov` hosts allowed. I'll check when
   sourcing starts and propose the change then.
