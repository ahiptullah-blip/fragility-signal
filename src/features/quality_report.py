"""Data quality report for the signal panel -> docs/data_quality_report.md.

Run: python3 -m src.features.quality_report  (after src.features.panel)
Covers coverage per signal per year, missing-value rates, distributions and outliers against
plausibility bounds. Uses signals only; no labels are read (outcomes stay out of feature QA).
"""
from __future__ import annotations

import pandas as pd

from src.features.signals import SIGNALS
from src.ingest.sec_http import ROOT

FEATURES = ROOT / "data" / "interim" / "features.csv.gz"
OUT = ROOT / "docs" / "data_quality_report.md"
COMPANIES = ROOT / "data" / "interim" / "companies.csv"

# (low, high): values outside are flagged for review, not removed.
BOUNDS = {
    "F1_cash_runway": (0, 40), "F2_refinancing_wall": (0, 10), "F4_dso_change": (-180, 180),
    "F5_share_dilution": (-50, 200), "S1_customer_concentration": (0, 60),
    "S2_gross_margin_trend": (-30, 30), "B2_ceo_cfo_departures": (0, 2), "B3_auditor_change": (0, 2),
    "B5_late_filings": (0, 4), "O1_revenue_growth_decel": (-100, 100), "O3_headcount_trend": (-60, 200),
    "N4_mda_specificity_change": (-30, 30),
}
NOTES = {
    "F1_cash_runway": "Capped at 40 quarters; companies with positive operating cash flow sit at the cap.",
    "F2_refinancing_wall": "Basis varies: 24-month maturity schedule where tagged, else current debt (12 months). See basis table.",
    "F4_dso_change": "None when quarterly revenue < $1M or DSO > 730 days.",
    "F5_share_dilution": "Not split-adjusted (splits show as outliers). None when the ratio is beyond 50x (unit mismatch).",
    "S2_gross_margin_trend": "None when TTM revenue < $5M or margin outside [-100%, 100%].",
    "O1_revenue_growth_decel": "None when the revenue base < $5M.",
    "S1_customer_concentration": "Text-extracted. 0 = no customer at or above 10% disclosed.",
    "O3_headcount_trend": "Text-extracted from 10-K employee counts; annual. None when the year-over-year ratio is outside 0.2-5x (parse error).",
    "N4_mda_specificity_change": "Text-extracted from 10-K MD&A; None when MD&A < 1,000 words, not found, or its length changes more than 2x.",
    "B2_ceo_cfo_departures": "Text-classified 8-K 5.02; spot-check precision about 75% (biographies, officers leaving for CEO roles elsewhere).",
}


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


def main() -> None:
    df = pd.read_csv(FEATURES, dtype={"entity_id": str}, parse_dates=["as_of"])
    names = pd.read_csv(COMPANIES, dtype={"cik": str}).set_index("cik")["name"]
    sig = list(SIGNALS)
    df["year"] = df.as_of.dt.year
    out = ["# Data Quality Report: Signals", "",
           f"Panel: {len(df)} entity-quarters, {df.entity_id.nunique()} entities, "
           f"{df.as_of.min().date()} to {df.as_of.max().date()} (quarter-end scoring dates, universe only).",
           f"Rows with a computation error: {(df.errors.fillna('') != '').sum()}.", ""]

    miss = pd.DataFrame({"signal": sig,
                         "missing %": [round(df[s].isna().mean() * 100, 1) for s in sig],
                         "entities with any value": [df.loc[df[s].notna(), "entity_id"].nunique() for s in sig],
                         "note": [NOTES.get(s, "") for s in sig]})
    out += ["## Missing-value rates", "", md(miss), ""]

    cov = df.groupby("year")[sig].apply(lambda g: (g.notna().mean() * 100).round(0).astype(int))
    cov.insert(0, "entity-quarters", df.groupby("year").size())
    out += ["## Coverage per signal per year (% of universe entity-quarters with a value)", "",
            md(cov.reset_index()), ""]

    basis = df.F2_basis.value_counts(dropna=False).rename_axis("F2 basis").reset_index(name="entity-quarters")
    out += ["## Refinancing wall basis", "", md(basis), ""]

    q = df[sig].quantile([0, .01, .05, .5, .95, .99, 1]).T.round(2)
    q.columns = ["min", "p1", "p5", "median", "p95", "p99", "max"]
    out += ["## Distributions", "", md(q.reset_index().rename(columns={"index": "signal"})), ""]

    out += ["## Outliers (outside plausibility bounds; flagged for review, not removed)", ""]
    rows = []
    for s in sig:
        lo, hi = BOUNDS[s]
        o = df[(df[s] < lo) | (df[s] > hi)]
        rows.append({"signal": s, "bounds": f"[{lo}, {hi}]", "flagged": len(o),
                     "flagged %": round(len(o) / max(df[s].notna().sum(), 1) * 100, 2)})
    out += [md(pd.DataFrame(rows)), ""]
    for s in sig:
        lo, hi = BOUNDS[s]
        o = df[(df[s] < lo) | (df[s] > hi)]
        if not len(o):
            continue
        top = o.reindex(o[s].abs().sort_values(ascending=False).index).drop_duplicates("entity_id").head(5)
        out += [f"**{s}**, most extreme (one row per entity):", ""]
        out += [f"- {names.get(r.entity_id, r.entity_id)} (CIK {r.entity_id}), {r.as_of.date()}: {getattr(r, s):.2f}"
                for r in top.itertuples()]
        out += [""]
    OUT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
