"""Point-in-time data access shared by the signal functions.

Every accessor takes an as_of date and returns only information from filings accepted
*before* that date (filing date < as_of; a filing made on the scoring date itself is not used).

Restatement rule (CLAUDE.md rule 1): for each (company, tag, period, duration) the value is the
one from the *first* filing that reported it. Later filings that restate the same period
(comparatives, amendments) never replace it. Amendments (10-K/A, 10-Q/A) are not loaded at all.
"""
from __future__ import annotations

from functools import lru_cache

import duckdb
import pandas as pd

from src.ingest.sec_http import ROOT

INTERIM = ROOT / "data" / "interim"
DB = ROOT / "data" / "fragility.duckdb"

CASH = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"]
STI = ["ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
       "AvailableForSaleSecuritiesCurrent", "HeldToMaturitySecuritiesCurrent"]
OCF = ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
AR = ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"]
REV = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
       "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueServicesNet",
       "SalesRevenueGoodsNet"]
GP = ["GrossProfit"]
COGS = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfServices", "CostOfGoodsSold"]
DEBT = ["LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtCurrent", "DebtCurrent", "ConvertibleNotesPayable",
        "ConvertibleDebtNoncurrent", "ConvertibleNotesPayableCurrent", "ConvertibleDebtCurrent",
        "LongTermNotesPayable", "SeniorNotes", "LineOfCredit"]
SHARES = ["CommonStockSharesOutstanding"]
FP_QTRS = {"Q1": 1, "Q2": 2, "Q3": 3, "FY": 4}


@lru_cache(maxsize=1)
def _facts() -> dict[str, pd.DataFrame]:
    con = duckdb.connect(str(DB), read_only=True)
    df = con.execute("SELECT cik, adsh, form, fp, period, filed, accepted, tag, ddate, qtrs, uom, value FROM facts").df()
    con.close()
    df["filed"] = pd.to_datetime(df.filed)
    df["ddate"] = pd.to_datetime(df.ddate.astype(str), format="%Y%m%d", errors="coerce")
    df["period"] = pd.to_datetime(df.period)
    df = df.sort_values(["filed", "accepted"])
    first = df.drop_duplicates(["cik", "tag", "ddate", "qtrs", "uom"], keep="first")
    return {c: g.reset_index(drop=True) for c, g in first.groupby("cik")}


@lru_cache(maxsize=1)
def _periodic() -> dict[str, pd.DataFrame]:
    """Original 10-K / 10-KT / 10-Q filings per company (from FSDS), with period and fiscal period."""
    sub = pd.read_csv(INTERIM / "fsds_sub.csv.gz", dtype={"cik": str},
                      usecols=["cik", "adsh", "form", "fp", "period", "filed"], parse_dates=["period", "filed"])
    sub = sub[sub.form.isin(["10-K", "10-KT", "10-Q"])].sort_values("filed")
    return {c: g.reset_index(drop=True) for c, g in sub.groupby("cik")}


@lru_cache(maxsize=1)
def _filings() -> dict[str, pd.DataFrame]:
    f = pd.read_csv(INTERIM / "filings.csv.gz", dtype={"cik": str, "items": str}, parse_dates=["filing_date"],
                    usecols=["cik", "accession", "form", "filing_date", "items"])
    return {c: g for c, g in f.groupby("cik")}


@lru_cache(maxsize=1)
def _concepts() -> dict[str, pd.DataFrame]:
    c = pd.read_csv(INTERIM / "concepts.csv", dtype={"cik": str}, parse_dates=["filed", "end"])
    c = c.sort_values("filed").drop_duplicates(["cik", "tag", "end", "accn"], keep="first")
    return {k: g for k, g in c.groupby("cik")}


@lru_cache(maxsize=1)
def _tenk_fields() -> dict[str, pd.DataFrame]:
    t = pd.read_csv(INTERIM / "tenk_fields.csv", dtype={"cik": str}, parse_dates=["filing_date"])
    return {c: g.sort_values("filing_date") for c, g in t.groupby("cik")}


@lru_cache(maxsize=1)
def _eightk_fields() -> dict[str, pd.DataFrame]:
    e = pd.read_csv(INTERIM / "eightk_fields.csv", dtype={"cik": str}, parse_dates=["filing_date"])
    return {c: g for c, g in e.groupby("cik")}


# ------------------------------------------------------------------ accessors
def facts_known(cik: str, as_of) -> pd.DataFrame:
    fx = _facts().get(cik)
    if fx is None:
        return pd.DataFrame(columns=["tag", "ddate", "qtrs", "uom", "value", "filed"])
    return fx[fx.filed < pd.Timestamp(as_of)]


def periodic_known(cik: str, as_of) -> pd.DataFrame:
    p = _periodic().get(cik)
    if p is None:
        return pd.DataFrame(columns=["adsh", "form", "fp", "period", "filed"])
    return p[p.filed < pd.Timestamp(as_of)]


def filings_known(cik: str, as_of, days: int | None = None) -> pd.DataFrame:
    f = _filings().get(cik)
    if f is None:
        return pd.DataFrame(columns=["form", "filing_date", "items"])
    as_of = pd.Timestamp(as_of)
    f = f[f.filing_date < as_of]
    return f if days is None else f[f.filing_date >= as_of - pd.Timedelta(days=days)]


def tenk_known(cik: str, as_of) -> pd.DataFrame:
    t = _tenk_fields().get(cik)
    return t[t.filing_date < pd.Timestamp(as_of)] if t is not None else pd.DataFrame()


def eightk_known(cik: str, as_of, days: int) -> pd.DataFrame:
    e = _eightk_fields().get(cik)
    if e is None:
        return pd.DataFrame(columns=["filing_date"])
    as_of = pd.Timestamp(as_of)
    return e[(e.filing_date < as_of) & (e.filing_date >= as_of - pd.Timedelta(days=days))]


def concepts_known(cik: str, as_of, tag: str) -> pd.DataFrame:
    c = _concepts().get(cik)
    if c is None:
        return pd.DataFrame({"tag": pd.Series(dtype=str), "end": pd.Series(dtype="datetime64[ns]"),
                             "val": pd.Series(dtype=float), "filed": pd.Series(dtype="datetime64[ns]"),
                             "accn": pd.Series(dtype=str)})
    return c[(c.tag == tag) & (c.filed < pd.Timestamp(as_of))]


def value(fx: pd.DataFrame, tags: list[str], ddate, qtrs: int, uom: str = "USD", tol_days: int = 10):
    """First tag (in priority order) with a value for this period end and duration."""
    ddate = pd.Timestamp(ddate)
    cand = fx[(fx.qtrs == qtrs) & (fx.uom == uom) & ((fx.ddate - ddate).abs() <= pd.Timedelta(days=tol_days))]
    for t in tags:
        v = cand[cand.tag == t]
        if len(v):
            return float(v.iloc[0].value)
    return None


def filing_for_period(per: pd.DataFrame, period, tol_days: int = 20):
    """The periodic filing whose period end is within tol_days of `period`."""
    m = per[(per.period - pd.Timestamp(period)).abs() <= pd.Timedelta(days=tol_days)]
    return m.iloc[0] if len(m) else None


def ttm(fx: pd.DataFrame, per: pd.DataFrame, filing, tags: list[str]):
    """Trailing-twelve-month flow ending at `filing`'s period, from first-published values.
    `filing` needs .period, .form and .fp (a real filing or a year-ago stand-in).
    Annual report: the annual value. Quarter: YTD + prior fiscal year - prior-year YTD, where the
    prior-year YTD may come from the comparative column of the current filing."""
    if filing is None:
        return None
    k = FP_QTRS.get(filing.fp)
    if filing.form in ("10-K", "10-KT") or k == 4:
        return value(fx, tags, filing.period, 4)
    if k is None:
        return None
    ytd = value(fx, tags, filing.period, k)
    prior_ytd = value(fx, tags, filing.period - pd.DateOffset(years=1), k)
    annual_rows = fx[fx.tag.isin(tags) & (fx.qtrs == 4) & (fx.ddate < filing.period)
                     & (fx.ddate > filing.period - pd.DateOffset(years=1))]
    if ytd is None or prior_ytd is None or not len(annual_rows):
        return None
    annual = value(fx, tags, annual_rows.ddate.max(), 4, tol_days=0)
    return None if annual is None else ytd + annual - prior_ytd


def current_debt(fx: pd.DataFrame, period):
    """Debt due within 12 months from the balance sheet (fallback for a missing maturity schedule)."""
    tags = ["LongTermDebtCurrent", "DebtCurrent", "ConvertibleNotesPayableCurrent", "ConvertibleDebtCurrent"]
    vals = [value(fx, [t], period, 0) for t in tags]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None  # tags overlap (DebtCurrent can include the others)


def quarter_flow(fx: pd.DataFrame, per: pd.DataFrame, filing, tags: list[str]):
    """Single-quarter flow ending at `filing`'s period (Q4 = annual - nine-month YTD)."""
    if filing is None:
        return None
    if filing.form == "10-Q":
        return value(fx, tags, filing.period, 1)
    annual = value(fx, tags, filing.period, 4)
    nine = value(fx, tags, filing.period - pd.DateOffset(months=3), 3, tol_days=20)
    return None if annual is None or nine is None else annual - nine


def cash_and_sti(fx: pd.DataFrame, period):
    cash = value(fx, CASH, period, 0)
    if cash is None:
        return None
    return cash + (value(fx, STI, period, 0) or 0.0)
