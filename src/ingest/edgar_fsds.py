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
