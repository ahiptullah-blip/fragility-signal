"""Universe builder: every entity eligible for scoring on a given date.

Definition (docs/decisions.md, 2026-11-07):
    An entity (SEC registrant, identified by 10-digit CIK) is in the universe on as_of if
    1. it has a 10-K or 10-KT whose EDGAR filing date is before as_of and no more than
       455 days earlier (the latest annual report must be current);
    2. the SIC code recorded on that 10-K *as filed* is 7370, 7371, 7372 or 7373, and the
       registrant was not a blank-check company (SPAC) when it filed it;
    3. the public float reported on that 10-K's cover page is at least $50M;
    4. it has not had a Tier 1 (terminal) collapse event on or before as_of.

How survivorship bias is avoided
    - Membership is built from the SEC Financial Statement Data Sets (sub.txt), which list
      every XBRL filing made in each quarter since 2009. Companies that later went bankrupt,
      were delisted, deregistered or acquired remain in those historical files. Nothing is
      sourced from a current list of companies.
    - SIC is taken from each filing as filed, not from the company's current SIC, so a
      company that was software in 2014 but reclassified later is still in the 2014 universe
      (and vice versa). A test against the current-SIC browse list found 10-14% of historical
      software filers missing from it, which is why that list is not used.
    - Public float is taken from the filing that reported it (accession match), with the
      filing date as the availability date, so a later restatement cannot leak backwards.
    - An entity leaves the universe only through rules 1 to 4 on dates *after* they happen.

Known limitations
    - FSDS covers XBRL filings only. Smaller reporting companies began XBRL with fiscal
      periods ending after 2011-06-15, so some small companies enter the universe only
      at their first XBRL 10-K (typically early 2012). Scoring from 2012-06-30 avoids most of this.
    - A 10-K with no tagged EntityPublicFloat cannot pass rule 3 and is excluded. The share of
      such filings is reported by the data quality report.
"""
from __future__ import annotations

import pandas as pd

from src.ingest.sec_http import ROOT

import re

SICS = {7370, 7371, 7372, 7373}
# Blank-check companies (SPACs) are shells, excluded per decision 2026-11-07. Identified by
# the registrant name on the 10-K as filed (a de-SPACed company files under its new name).
SPAC_NAME = re.compile(r"acquisition\s+(?:corp|co\b|company|inc|ltd|limited|holdings)|merger\s+corp|"
                       r"\bspac\b|capital\s+acquisition|growth\s+corp", re.I)
FLOAT_FLOOR = 50_000_000
MAX_10K_AGE_DAYS = 455
INTERIM = ROOT / "data" / "interim"


def load_10k_table() -> pd.DataFrame:
    """One row per original annual report (10-K / 10-KT) in FSDS, with float as filed."""
    sub = pd.read_csv(INTERIM / "fsds_sub.csv.gz", dtype={"cik": str, "adsh": str},
                      parse_dates=["filed", "period", "accepted"])
    tk = sub[sub.form.isin(["10-K", "10-KT"])].copy()
    fl = pd.read_csv(INTERIM / "public_float.csv", dtype={"cik": str})
    fl = fl.sort_values("val").drop_duplicates("accn", keep="last")  # one value per filing
    tk = tk.merge(fl[["accn", "val"]].rename(columns={"accn": "adsh", "val": "public_float"}),
                  on="adsh", how="left")
    tk["is_spac"] = tk.name.str.contains(SPAC_NAME)
    tk["in_niche"] = tk.sic.isin(SICS) & ~tk.is_spac
    tk["float_ok"] = tk.public_float >= FLOAT_FLOOR
    return tk.sort_values(["cik", "filed"]).reset_index(drop=True)


def universe_as_of(as_of, tenk: pd.DataFrame, terminal_events: pd.DataFrame | None = None
                   ) -> pd.DataFrame:
    """Entities eligible on as_of. terminal_events: columns cik, event_date (Tier 1 only)."""
    as_of = pd.Timestamp(as_of)
    known = tenk[tenk.filed < as_of]
    latest = known.groupby("cik").tail(1)
    latest = latest[(as_of - latest.filed).dt.days <= MAX_10K_AGE_DAYS]
    elig = latest[latest.in_niche & latest.float_ok]
    if terminal_events is not None and len(terminal_events):
        dead = terminal_events[terminal_events.event_date <= as_of].cik.unique()
        elig = elig[~elig.cik.isin(dead)]
    return elig[["cik", "name", "sic", "adsh", "filed", "public_float"]].reset_index(drop=True)


def ever_eligible(tenk: pd.DataFrame, start="2011-01-01") -> pd.Series:
    """CIKs that pass rules 2 and 3 on at least one 10-K filed on or after start."""
    t = tenk[(tenk.filed >= start) & tenk.in_niche & tenk.float_ok]
    return pd.Series(sorted(t.cik.unique()), name="cik")
