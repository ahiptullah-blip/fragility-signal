"""Label construction.

label(entity_id, as_of_date, window_months) returns 1 if a qualifying collapse event has an
event_date strictly after as_of_date and on or before as_of_date + window_months, else 0.

Qualifying events (baseline, pending freeze): Tier 1 and Tier 2 from src/labels/events.csv.
The event must also have been scorable: callers should only label (entity, as_of) pairs that are
in the universe on as_of (src/universe/universe.py), which label_panel() enforces.

censored is True when the window end falls after DATA_END, the last date the event data
covers. A censored 0 is not a confirmed negative, because an event may still occur inside the
unobserved part of the window. A censored 1 is a confirmed positive (the event was observed).
Censored rows with label 0 must be dropped from training and evaluation, not treated as
negatives.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from src.ingest.sec_http import ROOT

EVENTS = ROOT / "src" / "labels" / "events.csv"
DATA_END = pd.Timestamp("2026-11-07")  # filing index pulled 2026-11-08; last complete day
POSITIVE_TIERS = (1, 2)
# Taxonomy v1.0 frozen 2026-11-08. Changing events.csv requires a logged decision and a new hash.
FROZEN_SHA256 = "cbeb3f4615f76742b09cb5dae24e7c25aec95011a447a2080a2fa1ceb4fe96f9"
WINDOWS = (6, 12, 24)


@dataclass(frozen=True)
class Label:
    label: int
    censored: bool
    event_type: str | None = None
    event_date: pd.Timestamp | None = None


@lru_cache(maxsize=2)
def load_events(path: str = str(EVENTS), allow_unfrozen: bool = False) -> pd.DataFrame:
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if digest != FROZEN_SHA256 and not allow_unfrozen:
        raise RuntimeError(f"{path} does not match the frozen event table (taxonomy v1.0). "
                           "Log the change in docs/decisions.md and update FROZEN_SHA256.")
    ev = pd.read_csv(path, dtype={"entity_id": str}, parse_dates=["event_date"])
    return ev.sort_values("event_date")


def label(entity_id: str, as_of_date, window_months: int = 12,
          tiers: tuple[int, ...] = POSITIVE_TIERS, events: pd.DataFrame | None = None) -> Label:
    ev = load_events() if events is None else events
    start = pd.Timestamp(as_of_date)
    end = start + pd.DateOffset(months=window_months)
    hit = ev[(ev.entity_id == entity_id) & ev.tier.isin(tiers)
             & (ev.event_date > start) & (ev.event_date <= end)]
    censored = bool(end > DATA_END)
    if len(hit):
        h = hit.iloc[0]
        return Label(1, censored, h.event_type, h.event_date)
    return Label(0, censored)


def label_panel(as_of_dates, universe_fn, windows=WINDOWS, tiers=POSITIVE_TIERS,
                events: pd.DataFrame | None = None) -> pd.DataFrame:
    """Universe x as_of panel with labels for each window.

    universe_fn(as_of) must return a DataFrame with a cik column (src.universe.universe_as_of).
    Vectorised equivalent of calling label() for every row.
    """
    ev = load_events() if events is None else events
    ev = ev[ev.tier.isin(tiers)][["entity_id", "event_date", "event_type"]]
    rows = []
    for d in as_of_dates:
        d = pd.Timestamp(d)
        u = universe_fn(d)[["cik"]].rename(columns={"cik": "entity_id"})
        u["as_of"] = d
        m = u.merge(ev, on="entity_id", how="left")
        m = m[m.event_date > d]
        first = m.sort_values("event_date").groupby("entity_id").head(1)
        u = u.merge(first[["entity_id", "event_date", "event_type"]], on="entity_id", how="left")
        for w in windows:
            end = d + pd.DateOffset(months=w)
            u[f"label_{w}m"] = ((u.event_date > d) & (u.event_date <= end)).astype(int)
            u[f"censored_{w}m"] = bool(end > DATA_END)
        rows.append(u.rename(columns={"event_date": "next_event_date",
                                      "event_type": "next_event_type"}))
    return pd.concat(rows, ignore_index=True)
