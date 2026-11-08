"""Compute every approved signal for every (entity, scoring date) in the universe.

Run: python3 -m src.features.panel
Output: data/interim/features.csv.gz with entity_id, as_of, one column per signal, and
F2_basis (which definition the refinancing wall used). Labels are NOT joined here; signals and
outcomes are only combined in the backtest step, after the taxonomy freeze.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from src.features.signals import SIGNALS, refinancing_wall_basis
from src.ingest.sec_http import ROOT
from src.labels.labels import DATA_END, load_events
from src.universe.universe import load_10k_table, universe_as_of

OUT = ROOT / "data" / "interim" / "features.csv.gz"


def _row(args):
    cik, d = args
    r = {"entity_id": cik, "as_of": d}
    for name, fn in SIGNALS.items():
        try:
            r[name] = fn(cik, d)
        except Exception as e:  # recorded, never silently dropped
            r[name] = None
            r.setdefault("errors", []).append(f"{name}: {type(e).__name__}: {e}")
    try:
        r["F2_basis"] = refinancing_wall_basis(cik, d)
    except Exception as e:
        r["F2_basis"] = None
        r.setdefault("errors", []).append(f"F2_basis: {type(e).__name__}: {e}")
    r["errors"] = "; ".join(r.get("errors", []))
    return r


def build(dates=None) -> pd.DataFrame:
    tk = load_10k_table()
    ev = load_events()
    t1 = ev[ev.tier == 1].rename(columns={"entity_id": "cik"})[["cik", "event_date"]]
    dates = dates if dates is not None else pd.date_range("2012-06-30", DATA_END, freq="QE")
    pairs = [(c, d) for d in dates for c in universe_as_of(d, tk, t1).cik]
    with ProcessPoolExecutor(4) as ex:
        rows = list(ex.map(_row, pairs, chunksize=50))
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"features: {len(df)} entity-quarters, errors in {(df.errors != '').sum()} rows")
    return df


if __name__ == "__main__":
    build()
