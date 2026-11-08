"""Ingest: SEC XBRL companyconcept API (one concept per company, every value with its filing).

Source: https://data.sec.gov/api/xbrl/companyconcept/CIK##########/{taxonomy}/{tag}.json
Every value carries the accession (accn), form and filing date (filed), so the value known on
any past date is reconstructable, and the first-published value for a period is the one with
the earliest `filed`. Raw JSON is cached under data/raw/concept/ (float: data/raw/float/).
The API excludes dimensional facts (e.g. per share class).

Outputs
    data/interim/public_float.csv   dei:EntityPublicFloat (universe size floor)
    data/interim/concepts.csv       the CONCEPTS below
Schema (both): cik, taxonomy, tag, accn, form, filed (date), end (date), val, unit
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.ingest.sec_http import ROOT, get

URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{tax}/{tag}.json"
FLOAT_OUT = ROOT / "data" / "interim" / "public_float.csv"
CONCEPTS_OUT = ROOT / "data" / "interim" / "concepts.csv"
CONCEPTS = [
    ("dei", "EntityCommonStockSharesOutstanding"),                                 # F5
    ("us-gaap", "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"),  # F2
    ("us-gaap", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"),           # F2
]
COLS = ["cik", "taxonomy", "tag", "accn", "form", "filed", "end", "val", "unit"]


def fetch(cik: str, tax: str, tag: str, subdir: str = "concept") -> list[dict]:
    raw = get(URL.format(cik=cik, tax=tax, tag=tag), subdir=subdir)
    if raw is None:
        return []
    d = json.loads(raw)
    return [{"cik": cik, "taxonomy": tax, "tag": tag, "accn": v["accn"], "form": v.get("form"),
             "filed": v["filed"], "end": v.get("end"), "val": v["val"], "unit": unit}
            for unit, vals in d.get("units", {}).items() for v in vals]


def _run(jobs, subdir):
    with ThreadPoolExecutor(4) as ex:
        return [r for rs in ex.map(lambda j: fetch(*j, subdir=subdir), jobs) for r in rs]


def main_float(ciks: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(_run([(c, "dei", "EntityPublicFloat") for c in ciks], "float"), columns=COLS)
    df = df[df.unit == "USD"]
    df.to_csv(FLOAT_OUT, index=False)
    print(f"public float: {len(df)} values for {df.cik.nunique()} of {len(ciks)} companies")
    return df


def main_concepts(ciks: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(_run([(c, t, g) for c in ciks for t, g in CONCEPTS], "concept"), columns=COLS)
    df.to_csv(CONCEPTS_OUT, index=False)
    for (t, g), n in df.groupby(["taxonomy", "tag"]).cik.nunique().items():
        print(f"{g}: {n} of {len(ciks)} companies")
    return df


main = main_float  # backward compatible name
