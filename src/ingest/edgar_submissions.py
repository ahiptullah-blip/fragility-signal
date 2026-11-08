"""Ingest: complete EDGAR filing history per company (forms, dates, 8-K item codes).

Source: https://data.sec.gov/submissions/CIK##########.json plus its overflow pages
(filings.files). Raw JSON is cached under data/raw/submissions/. The filing index is
append-only: EDGAR does not rewrite a filing's form type, dates or item codes, so this is
point-in-time by construction (a filing is knowable from its acceptanceDateTime).

Output schema (data/interim/filings.csv.gz):
    cik, accession, form, filing_date, report_date, accepted (UTC timestamp),
    items (comma-separated 8-K item codes), primary_document
Also writes data/interim/companies.csv: cik, name, current_sic, tickers, exchanges,
former_names (for reference only; never used as a point-in-time field).
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.ingest.sec_http import ROOT, get

OUT = ROOT / "data" / "interim" / "filings.csv.gz"
OUT_CO = ROOT / "data" / "interim" / "companies.csv"
BASE = "https://data.sec.gov/submissions/"
MAP = {"accessionNumber": "accession", "form": "form", "filingDate": "filing_date",
       "reportDate": "report_date", "acceptanceDateTime": "accepted", "items": "items",
       "primaryDocument": "primary_document"}


def _block(cik: str, block: dict) -> pd.DataFrame:
    df = pd.DataFrame({k: block.get(k, []) for k in MAP}).rename(columns=MAP)
    df.insert(0, "cik", cik)
    return df


def fetch(cik: str):
    raw = get(f"{BASE}CIK{cik}.json", subdir="submissions")
    if raw is None:
        return None, None
    d = json.loads(raw)
    parts = [_block(cik, d["filings"]["recent"])]
    for f in d["filings"].get("files", []):
        extra = get(BASE + f["name"], subdir="submissions")
        if extra:
            parts.append(_block(cik, json.loads(extra)))
    co = {"cik": cik, "name": d.get("name"), "current_sic": d.get("sic"),
          "tickers": ",".join(d.get("tickers") or []),
          "exchanges": ",".join(x or "" for x in (d.get("exchanges") or [])),
          "former_names": "; ".join(x["name"] for x in d.get("formerNames") or [])}
    return pd.concat(parts, ignore_index=True), co


def main(ciks: list[str]) -> pd.DataFrame:
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(fetch, ciks))
    filings = pd.concat([r[0] for r in res if r[0] is not None], ignore_index=True)
    filings.to_csv(OUT, index=False)
    pd.DataFrame([r[1] for r in res if r[1]]).to_csv(OUT_CO, index=False)
    print(f"filings: {len(filings)} rows for {filings.cik.nunique()} companies")
    return filings
