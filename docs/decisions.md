# Decisions Log

The memory of this project. Every change to a core definition, every weight change
(metric before, metric after, reason), and every scope decision goes here, newest first.

## 2026-11-07 — Niche selected (Prompt 1)
Full analysis: docs/niche_selection.md. Owner chose the boundary; owner delegated the remaining
choices to Claude "for the best outcome". Each is recorded with its reason and what would reopen it.

| Decision | Choice | Reason | Reopen if |
|---|---|---|---|
| Niche | US-listed application software | Best point-in-time data of five candidates (EDGAR timestamps), strongest owner edge, clear buyer | Week-1 kill gate fails |
| Universe boundary | SEC SIC codes 7370, 7371, 7372, 7373. Rule-based only, no hand-picked names | SaaS issuers are spread across 7370–7373. SIC 7374 (data processing, payment processors, data centers) excluded as a different business model. A hand-picked "fintech-adjacent" list would bring in hindsight bias | Fintech-adjacent names prove material and can be added by rule, not by name |
| Filer type | 10-K / 10-Q filers only (foreign-domiciled 10-K filers included); 20-F and 40-F excluded | Different cadence (annual / semiannual), IFRS, no comparable quarterly signals | v1 baseline established |
| v1 buyer | Procurement / third-party vendor risk | Matches owner edge; fits "not a trading system" | Owner changes target buyer |
| Effect on labels | Collapse = entity-level distress. Being acquired is a neutral exit (entity leaves the universe), not a positive label. Acquire-and-sunset of the product is out of scope for v1 (cannot be labeled from filings) | Keeps labels dated and verifiable | Taxonomy is finalized in Prompt 3; this is guidance, not the frozen taxonomy |
| Paid data | None in v1. No price-based signals | Free price sources drop delisted tickers (survivorship bias). Fundamentals plus filing events avoid it | Baseline established and a price signal is the clear next gain |
| Size floor | Public float of $50M or more, from the 10-K cover page (`dei:EntityPublicFloat`, as filed) | Removes micro-cap shells that dominate raw failure counts, keeps enough events. The float figure is itself point-in-time and needs no price data | Event count under the floor is below 50 (try $25M once, then fall back) |
| Shells | Excluded (SIC filter plus shell-company flag where reported) | Shells are not operating software businesses | — |
| De-SPACs | Included, with a listing-route flag (IPO / de-SPAC / other) | Real, buyer-relevant failure population. Excluding it would hide a major source of collapses. The flag lets base rates be split by route | Stratified results show de-SPACs alone drive performance |
| Forward window | 12 months (CLAUDE.md default) | — | — |
| History | Scoring dates from 2012 onward | XBRL covers smaller reporting companies from fiscal periods after mid-2011 | — |
| Kill gate | Under the Prompt 3 taxonomy and this universe, at least 50 labeled events (target 100+) or the prototype switches to banks (all FDIC-insured) | Label count is the main unverified assumption | — |
| Second iteration | Banks (all FDIC-insured institutions) | Only other niche passing every gate; out-of-domain test of the method | — |
| Private HR tech | Deferred; needs separate approval (rule 7) | Fails ground-truth and point-in-time gates as a standalone backtest | — |

SEC User-Agent (resolved 2026-11-07): owner approved using their email as the EDGAR contact. It is
read from `SEC_USER_AGENT` in a local, gitignored `.env`; `.env.example` holds the template. The
email is not committed to the repo.

## 2026-11-07 — Project initialized
- Created repo with CLAUDE.md as the project charter.
- Niche: not yet chosen.
- Event taxonomy: not yet defined.
- Baseline model: not yet established.
