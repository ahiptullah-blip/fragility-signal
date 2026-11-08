"""NOT USED for the universe (kept as a survivorship cross-check). See docs/decisions.md 2026-11-08.

Ingest: every EDGAR registrant currently assigned SIC 7370-7373.

Source: EDGAR company browse by SIC (Atom output). It lists registrants with that SIC
regardless of whether they still file, so failed and deregistered companies are included.
Limitation: SIC is the *current* assignment, not the one in force on a past date.

Output schema (data/interim/sic_companies.csv):
    cik (str, 10-digit), sic (int), state (str), name (str)
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from src.ingest.sec_http import ROOT, get

SICS = [7370, 7371, 7372, 7373]
NS = {"a": "http://www.w3.org/2005/Atom"}
OUT = ROOT / "data" / "interim" / "sic_companies.csv"


def fetch_sic(sic: int) -> list[dict]:
    rows, start = [], 0
    while True:
        url = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&SIC={sic}"
               f"&owner=include&count=100&start={start}&output=atom")
        raw = get(url, subdir="sic_browse")
        root = ET.fromstring(raw)
        entries = root.findall("a:entry", NS)
        for e in entries:
            ci = e.find("a:content/a:company-info", NS)
            cik = ci.findtext("a:cik", default="", namespaces=NS).strip()
            title = e.findtext("a:title", default="", namespaces=NS)
            rows.append({"cik": cik.zfill(10), "sic": sic,
                         "state": ci.findtext("a:state", default="", namespaces=NS)})
        if len(entries) < 100:
            break
        start += 100
    return rows


def main() -> pd.DataFrame:
    rows = []
    for sic in SICS:
        r = fetch_sic(sic)
        print(f"SIC {sic}: {len(r)} registrants")
        rows += r
    df = pd.DataFrame(rows).drop_duplicates("cik")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    return df


if __name__ == "__main__":
    main()
