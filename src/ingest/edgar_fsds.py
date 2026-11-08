"""Ingest: SEC Financial Statement Data Sets (quarterly, 2009q1 onward).

Source: https://www.sec.gov/dera/data/financial-statement-data-sets
Each quarterly zip is stored unmodified under data/raw/fsds/ (the raw snapshot; the
num.txt inside is the as-filed XBRL financials used later for signals).

This script extracts sub.txt (one row per XBRL submission) from every quarter.
sub.txt records the filer's SIC *as of that filing* and the EDGAR acceptance
timestamp, which makes it the point-in-time source for universe membership.

Output schema (data/interim/fsds_sub.csv.gz):
    adsh (accession), cik (10-digit str), name, sic (int, as filed), form, period (date),
    fy, fp, filed (date), accepted (timestamp), afs (filer status), countryinc, former
"""
from __future__ import annotations

import io
import zipfile
from datetime import date

import pandas as pd

from src.ingest.sec_http import ROOT, get

OUT = ROOT / "data" / "interim" / "fsds_sub.csv.gz"
BASE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{q}.zip"
COLS = ["adsh", "cik", "name", "sic", "form", "period", "fy", "fp", "filed", "accepted",
        "afs", "countryinc", "former"]


def quarters(start=2009, end: date | None = None):
    end = end or date.today()
    for y in range(start, end.year + 1):
        for q in range(1, 5):
            yield f"{y}q{q}"


def main() -> pd.DataFrame:
    frames = []
    for q in quarters():
        raw = get(BASE.format(q=q), subdir="fsds")
        if raw is None:
            print(f"{q}: not published (404), stopping")
            break
        z = zipfile.ZipFile(io.BytesIO(raw))
        sub = pd.read_csv(z.open("sub.txt"), sep="\t", dtype=str, usecols=COLS,
                          encoding="latin-1")
        sub["quarter"] = q
        frames.append(sub)
        print(f"{q}: {len(sub)} submissions")
    df = pd.concat(frames, ignore_index=True)
    df["cik"] = df["cik"].str.zfill(10)
    df["sic"] = pd.to_numeric(df["sic"], errors="coerce").astype("Int64")
    df["filed"] = pd.to_datetime(df["filed"], format="%Y%m%d")
    df["period"] = pd.to_datetime(df["period"], format="%Y%m%d", errors="coerce")
    df["accepted"] = pd.to_datetime(df["accepted"], errors="coerce")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    return df


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------- facts (num.txt)
# Tags needed by the approved signals (docs/signal_library.md). Only undimensioned,
# non-coregistrant values from original 10-K / 10-KT / 10-Q filings are kept.
FACT_TAGS = [
    # cash and short-term investments (F1, F2)
    "CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "Cash", "ShortTermInvestments", "MarketableSecuritiesCurrent",
    "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "AvailableForSaleSecuritiesCurrent",
    "HeldToMaturitySecuritiesCurrent",
    # operating cash flow (F1)
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    # receivables (F4)
    "AccountsReceivableNetCurrent", "ReceivablesNetCurrent",
    # revenue and gross profit (F4, S2, O1)
    "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet",
    "SalesRevenueServicesNet", "SalesRevenueGoodsNet", "GrossProfit", "CostOfRevenue",
    "CostOfGoodsAndServicesSold", "CostOfServices", "CostOfGoodsSold",
    # shares (F5 fallback)
    "CommonStockSharesOutstanding",
    # debt presence (F2: distinguishes "no debt" from "debt but no schedule")
    "LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtCurrent", "DebtCurrent",
    "ConvertibleNotesPayable", "ConvertibleDebtNoncurrent", "ConvertibleNotesPayableCurrent",
    "ConvertibleDebtCurrent", "LongTermNotesPayable", "SeniorNotes", "LineOfCredit",
]
FACTS_DB = ROOT / "data" / "fragility.duckdb"


def extract_facts(ciks: list[str]) -> None:
    """Load the needed facts for the given companies into duckdb table `facts`.

    Schema: cik, adsh, form, fp, fy, period, filed, accepted, tag, ddate (period date),
    qtrs (0 = instant, 1 = quarter, 2-4 = year-to-date / annual), uom, value.
    """
    import tempfile

    import duckdb

    sub = pd.read_csv(OUT, dtype={"cik": str, "adsh": str})
    sub = sub[sub.cik.isin(set(ciks)) & sub.form.isin(["10-K", "10-KT", "10-Q"])]
    con = duckdb.connect(str(FACTS_DB))
    con.execute("DROP TABLE IF EXISTS facts")
    con.register("subdf", sub[["adsh", "cik", "form", "fp", "fy", "period", "filed", "accepted"]])
    con.execute("CREATE TEMP TABLE subs AS SELECT * FROM subdf")
    tags = ",".join(f"'{t}'" for t in FACT_TAGS)
    first = True
    for q in sorted(sub.quarter.unique()):
        raw = get(BASE.format(q=q), subdir="fsds")
        with tempfile.TemporaryDirectory() as tmp:
            zipfile.ZipFile(io.BytesIO(raw)).extract("num.txt", tmp)
            sql = f"""
                SELECT s.cik, s.adsh, s.form, s.fp, s.fy, s.period, s.filed, s.accepted,
                       n.tag, n.ddate, CAST(n.qtrs AS INT) AS qtrs, n.uom, CAST(n.value AS DOUBLE) AS value
                FROM read_csv('{tmp}/num.txt', delim='\\t', header=true, all_varchar=true,
                              quote='', ignore_errors=true) n
                JOIN subs s ON s.adsh = n.adsh
                WHERE n.tag IN ({tags}) AND (n.segments IS NULL OR n.segments = '')
                  AND (n.coreg IS NULL OR n.coreg = '') AND n.value IS NOT NULL
            """
            if first:
                con.execute(f"CREATE TABLE facts AS {sql}")
                first = False
            else:
                con.execute(f"INSERT INTO facts {sql}")
        print(q, con.execute("SELECT count(*) FROM facts").fetchone()[0], flush=True)
    con.close()
