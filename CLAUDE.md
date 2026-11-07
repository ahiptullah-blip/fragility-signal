# Fragility Signal Engine

## What this project is
A system that scores entities in a defined niche on their probability of a "collapse event" within a forward window, using a weighted combination of observable signals. The thesis: fragility is easier to detect than future success because it leaves measurable evidence before the break.

## What it is not
- Not a trading system. No position sizing, no execution, no return claims.
- Not a prediction of timing. Output is a ranked fragility score with a confidence band, not a date.
- Not a black box. Every score must decompose into its contributing signals.

## Core definitions (do not drift from these without logging the change in docs/decisions.md)
- Entity: the unit being scored (one company, one brand, one fund).
- Universe: the full set of entities eligible for scoring at a point in time, defined so it has no survivorship bias.
- Collapse event: a dated, verifiable outcome from the event taxonomy in src/labels/. Must be defined BEFORE looking at signal data.
- Signal: one observable feature computed from data available as of the scoring date. Point-in-time only. No look-ahead.
- Forward window: 12 months by default. A positive label means an event occurred inside the window after the scoring date.
- Baseline model: the first weighted-signal model that passes the backtest acceptance criteria. All future versions are compared to it.

## Non-negotiable rules
1. Point-in-time discipline. A feature may only use data that was publicly available on the scoring date. If a data source restates history, use the first-published value or drop the feature.
2. Labels before features. The event table is finalized and frozen before any model is fit.
3. Walk-forward only. Train on years 1 to N, test on year N+1, roll forward. Never random train/test splits on time series.
4. Report base rates. Every metric is shown next to the naive base rate so improvement is visible.
5. Every weight change is logged with the metric before, the metric after, and the reason.
6. Prefer fewer, explainable signals over many weak ones. Start with 8 to 12.
7. When in doubt, ask me before expanding scope. Do not add a second niche, a new data source, or a new model type without confirmation.

## Conventions
- Python 3.11, pandas, scikit-learn, duckdb for local storage. No cloud dependencies in the prototype.
- One script per data source in src/ingest/, one function per signal in src/features/.
- `make backtest` runs the full pipeline end to end and writes reports/backtest_<date>.md.
- Keep docs/decisions.md current. It is the memory of this project.

## Current status
- Niche: US-listed application software (SIC 7370–7373), 10-K filers, public float $50M or more, scoring from 2012. Kill gate: at least 50 labeled events or switch to banks. See docs/decisions.md (2026-11-07).
- Event taxonomy: [fill after Prompt 3]
- Baseline model: not yet established
