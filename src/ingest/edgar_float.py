"""Ingest: public float (dei:EntityPublicFloat) per company, with filing dates.

Source: SEC XBRL companyconcept API
    https://data.sec.gov/api/xbrl/companyconcept/CIK##########/dei/EntityPublicFloat.json
Every value carries the accession (accn) and filing date (filed) of the filing that reported
it, so the float known on any past date can be reconstructed. Raw JSON is cached under
data/raw/float/.

Output schema (data/interim/public_float.csv):
    cik (10-digit str), accn, form, filed (date), end (float measurement date), val (USD)
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.ingest.sec_http import ROOT, get

OUT = ROOT / "data" / "interim" / "public_float.csv"
URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/dei/EntityPublicFloat.json"


def fetch(cik: str) -> list[dict]:
    raw = get(URL.format(cik=cik), subdir="float")
    if raw is None:
        return []
    d = json.loads(raw)
    rows = []
    for unit, vals in d.get("units", {}).items():
        if unit != "USD":
            continue
        for v in vals:
            rows.append({"cik": cik, "accn": v["accn"], "form": v.get("form"),
                         "filed": v["filed"], "end": v.get("end"), "val": v["val"]})
    return rows


def main(ciks: list[str]) -> pd.DataFrame:
    with ThreadPoolExecutor(4) as ex:
        rows = [r for rs in ex.map(fetch, ciks) for r in rs]
    df = pd.DataFrame(rows, columns=["cik", "accn", "form", "filed", "end", "val"])
    df.to_csv(OUT, index=False)
    print(f"public float: {len(df)} values for {df.cik.nunique()} of {len(ciks)} companies")
    return df
