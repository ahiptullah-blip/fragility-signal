"""The 12 approved signals (docs/signal_library.md, approved 2026-11-08).

One function per signal. Each takes (entity_id, as_of_date) and returns a float or None using
only filings accepted before as_of_date (see src/features/_data.py for the point-in-time and
first-published rules). Direction: the value listed under "Fragile if" in the signal library.
"""
from __future__ import annotations

import pandas as pd

from src.features import _data as D

RUNWAY_CAP = 40.0  # quarters; companies with positive operating cash flow get the cap
RATIO_CAP = 100.0
MIN_QTR_REVENUE = 1e6   # below this, ratios on revenue are dominated by noise
MIN_TTM_REVENUE = 5e6


def _latest(entity_id, as_of):
    fx, per = D.facts_known(entity_id, as_of), D.periodic_known(entity_id, as_of)
    return fx, per, (per.iloc[-1] if len(per) else None)


def _year_ago(per, filing):
    """The filing for the same fiscal period a year earlier if it exists; otherwise a stand-in
    with that period, so flows can come from the current filing's comparatives."""
    if filing is None:
        return None
    real = D.filing_for_period(per, filing.period - pd.DateOffset(years=1))
    if real is not None:
        return real
    return pd.Series({"period": filing.period - pd.DateOffset(years=1), "fp": filing.fp,
                      "form": filing.form, "adsh": None})


# ------------------------------------------------------------------ Financial
def cash_runway(entity_id: str, as_of_date) -> float | None:
    """F1. Quarters of cash at the current burn: (cash + ST investments) / (-TTM operating CF / 4)."""
    fx, per, f = _latest(entity_id, as_of_date)
    if f is None:
        return None
    cash, ocf = D.cash_and_sti(fx, f.period), D.ttm(fx, per, f, D.OCF)
    if cash is None or ocf is None:
        return None
    burn = max(-ocf / 4.0, 0.0)
    return RUNWAY_CAP if burn == 0 else min(max(cash, 0.0) / burn, RUNWAY_CAP)


def refinancing_wall(entity_id: str, as_of_date) -> float | None:
    """F2. Debt principal due within 24 months (latest 10-K maturity schedule) / (cash + ST
    investments). Where the company tags no maturity schedule, falls back to the balance-sheet
    current portion of debt (12 months only); see refinancing_wall_basis. 0 when no debt."""
    fx, per, f = _latest(entity_id, as_of_date)
    tenk = per[per.form.isin(["10-K", "10-KT"])]
    if f is None or not len(tenk):
        return None
    k = tenk.iloc[-1]
    due = 0.0
    found = False
    for tag in ("LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
                "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"):
        c = D.concepts_known(entity_id, as_of_date, tag)
        c = c[(c.end - k.period).abs() <= pd.Timedelta(days=10)]
        if len(c):
            due += float(c.iloc[0].val)
            found = True
    if not found:
        has_debt = any((D.value(fx, [t], k.period, 0) or 0) > 0 for t in D.DEBT)
        if has_debt:
            # No current-debt line on the balance sheet means nothing is due within 12 months.
            # Known limitation: debt due in months 13-24 is invisible under this fallback.
            due = D.current_debt(fx, f.period) or 0.0
    cash = D.cash_and_sti(fx, f.period)
    if cash is None:
        return None
    if due == 0:
        return 0.0
    return RATIO_CAP if cash <= 0 else min(due / cash, RATIO_CAP)


def _dso(fx, per, filing):
    if filing is None:
        return None
    ar = D.value(fx, D.AR, filing.period, 0)
    rev = D.quarter_flow(fx, per, filing, D.REV)
    if ar is None or not rev or rev < MIN_QTR_REVENUE:
        return None
    dso = ar / rev * 91.25
    return dso if dso <= 730 else None  # beyond two years = mismatched or near-zero revenue


def dso_change(entity_id: str, as_of_date) -> float | None:
    """F4. DSO now minus DSO four quarters earlier, in days."""
    fx, per, f = _latest(entity_id, as_of_date)
    now, before = _dso(fx, per, f), _dso(fx, per, _year_ago(per, f))
    return None if now is None or before is None else now - before


def _shares(entity_id, as_of, fx, filing):
    c = D.concepts_known(entity_id, as_of, "EntityCommonStockSharesOutstanding")
    c = c[c.accn == filing.adsh] if filing.adsh else c.iloc[0:0]
    if len(c):
        return float(c.val.sum()), "dei"  # one undimensioned value per class when reported
    v = D.value(fx, D.SHARES, filing.period, 0, uom="shares")
    return (v, "bs") if v is not None else (None, None)


def share_dilution(entity_id: str, as_of_date) -> float | None:
    """F5. Year-over-year % change in shares outstanding (same source at both dates)."""
    fx, per, f = _latest(entity_id, as_of_date)
    prev = _year_ago(per, f)
    if f is None or prev is None:
        return None
    (s1, src1), (s0, src0) = _shares(entity_id, as_of_date, fx, f), _shares(entity_id, as_of_date, fx, prev)
    if src1 != src0 or not s0 or s1 is None:
        v1 = D.value(fx, D.SHARES, f.period, 0, uom="shares")
        v0 = D.value(fx, D.SHARES, prev.period, 0, uom="shares")
        s1, s0 = v1, v0
    if not s0 or s1 is None or s0 <= 0 or s1 <= 0:
        return None
    ratio = s1 / s0
    if not 1 / 50 <= ratio <= 50:
        return None  # unit/scale mismatch between filings (e.g. thousands vs units)
    return (ratio - 1) * 100


# ------------------------------------------------------------------ Structural
def refinancing_wall_basis(entity_id: str, as_of_date) -> str | None:
    """Diagnostic for F2 (not a signal): 'schedule_24m', 'current_debt_12m', 'no_debt' or None."""
    fx, per, f = _latest(entity_id, as_of_date)
    tenk = per[per.form.isin(["10-K", "10-KT"])]
    if f is None or not len(tenk):
        return None
    k = tenk.iloc[-1]
    for tag in ("LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
                "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"):
        c = D.concepts_known(entity_id, as_of_date, tag)
        if len(c[(c.end - k.period).abs() <= pd.Timedelta(days=10)]):
            return "schedule_24m"
    if any((D.value(fx, [t], k.period, 0) or 0) > 0 for t in D.DEBT):
        return "current_debt_12m"
    return "no_debt"


def customer_concentration(entity_id: str, as_of_date) -> float | None:
    """S1. Largest single-customer share of revenue (%) stated in the latest 10-K.
    0 when no customer at or above 10% is disclosed (ASC 280 requires disclosure at 10%)."""
    t = D.tenk_known(entity_id, as_of_date)
    if not len(t):
        return None
    r = t.iloc[-1]
    return 0.0 if pd.isna(r.cust_max_pct) else float(r.cust_max_pct)


def _gm(fx, per, filing):
    rev = D.ttm(fx, per, filing, D.REV)
    if not rev or rev < MIN_TTM_REVENUE:
        return None
    gp = D.ttm(fx, per, filing, D.GP)
    if gp is None:
        cogs = D.ttm(fx, per, filing, D.COGS)
        gp = None if cogs is None else rev - cogs
    gm = None if gp is None else gp / rev * 100
    return gm if gm is not None and -100 <= gm <= 100 else None


def gross_margin_trend(entity_id: str, as_of_date) -> float | None:
    """S2. TTM gross margin now minus four quarters earlier, in percentage points."""
    fx, per, f = _latest(entity_id, as_of_date)
    now, before = _gm(fx, per, f), _gm(fx, per, _year_ago(per, f))
    return None if now is None or before is None else now - before


# ------------------------------------------------------------------ Behavioral
def ceo_cfo_departures(entity_id: str, as_of_date) -> float | None:
    """B2. Number of 8-K Item 5.02 filings reporting a CEO or CFO departure, trailing 12 months."""
    e = D.eightk_known(entity_id, as_of_date, 365)
    return float(e.ceo_cfo_departure.sum()) if len(e) else 0.0


def auditor_change(entity_id: str, as_of_date) -> float | None:
    """B3. 8-K Item 4.01 in the trailing 24 months: 0 none, 1 auditor dismissed or replaced,
    2 auditor resigned or declined to stand for re-election."""
    e = D.eightk_known(entity_id, as_of_date, 730)
    if not len(e) or not e.auditor_change.any():
        return 0.0
    return 2.0 if e[e.auditor_change].auditor_resigned.any() else 1.0


def late_filings(entity_id: str, as_of_date) -> float | None:
    """B5. Count of NT 10-K and NT 10-Q filings in the trailing 24 months."""
    f = D.filings_known(entity_id, as_of_date, days=730)
    return float(f.form.isin(["NT 10-K", "NT 10-Q"]).sum())


# ------------------------------------------------------------------ Operational
def _growth(fx, per, filing):
    prev = _year_ago(per, filing)
    a, b = D.ttm(fx, per, filing, D.REV), D.ttm(fx, per, prev, D.REV)
    return None if a is None or not b or b < MIN_TTM_REVENUE else (a / b - 1) * 100


def revenue_growth_decel(entity_id: str, as_of_date) -> float | None:
    """O1. TTM revenue growth now minus the same measure four quarters earlier (pp)."""
    fx, per, f = _latest(entity_id, as_of_date)
    if f is None:
        return None
    g1, g0 = _growth(fx, per, f), _growth(fx, per, _year_ago(per, f))
    return None if g1 is None or g0 is None else g1 - g0


def headcount_trend(entity_id: str, as_of_date) -> float | None:
    """O3. Year-over-year % change in employees reported in the latest two 10-Ks."""
    t = D.tenk_known(entity_id, as_of_date)
    t = t[t.employees.notna()]
    if len(t) < 2:
        return None
    a, b = t.iloc[-1], t.iloc[-2]
    gap = (a.filing_date - b.filing_date).days
    if not 300 <= gap <= 430 or b.employees <= 0:
        return None
    ratio = a.employees / b.employees
    return None if not 0.2 <= ratio <= 5 else (ratio - 1) * 100  # outside = extraction error


# ------------------------------------------------------------------ Narrative
def _density(r):
    return None if r.mda_words < 1000 else r.mda_numeric_tokens / r.mda_words * 1000


def mda_specificity_change(entity_id: str, as_of_date) -> float | None:
    """N4. Numeric tokens per 1,000 words in 10-K MD&A, latest minus prior 10-K."""
    t = D.tenk_known(entity_id, as_of_date)
    if len(t) < 2:
        return None
    a, b = t.iloc[-1], t.iloc[-2]
    if not 300 <= (a.filing_date - b.filing_date).days <= 430:
        return None
    if not 0.5 <= a.mda_words / max(b.mda_words, 1) <= 2:
        return None  # MD&A boundaries found inconsistently between the two years
    da, db = _density(a), _density(b)
    return None if da is None or db is None else da - db


SIGNALS = {
    "F1_cash_runway": cash_runway,
    "F2_refinancing_wall": refinancing_wall,
    "F4_dso_change": dso_change,
    "F5_share_dilution": share_dilution,
    "S1_customer_concentration": customer_concentration,
    "S2_gross_margin_trend": gross_margin_trend,
    "B2_ceo_cfo_departures": ceo_cfo_departures,
    "B3_auditor_change": auditor_change,
    "B5_late_filings": late_filings,
    "O1_revenue_growth_decel": revenue_growth_decel,
    "O3_headcount_trend": headcount_trend,
    "N4_mda_specificity_change": mda_specificity_change,
}
