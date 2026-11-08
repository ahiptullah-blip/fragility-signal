"""Ingest: filing documents (10-K primary documents and selected 8-Ks) and structured fields
extracted from them.

Source: EDGAR archives (https://www.sec.gov/Archives/edgar/data/...). Raw documents are stored
gzipped under data/raw/docs10k/ and data/raw/docs8k/ (the raw snapshot). Each document is
public from its filing date, so every extracted field is point-in-time by construction.

Outputs
  data/interim/tenk_fields.csv      one row per 10-K / 10-KT
      cik, accession, form, filing_date, period (report date), employees,
      mda_words, mda_numeric_tokens, cust_max_pct, cust_none_stated, text_chars
  data/interim/eightk_fields.csv    one row per 8-K with Item 4.01 or 5.02
      cik, accession, filing_date, report_date, items, auditor_change, auditor_resigned,
      ceo_cfo_departure, departure_snippet
"""
from __future__ import annotations

import html
import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.ingest.sec_http import ROOT, get

INTERIM = ROOT / "data" / "interim"
START = pd.Timestamp("2010-07-01")


def doc_url(cik: str, acc: str, doc: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}"


def to_text(raw: bytes | None) -> str:
    if not raw:
        return ""
    t = raw.decode("utf-8", errors="ignore")
    t = re.sub(r"(?is)<(script|style|ix:header).*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ").replace("’", "'").replace("—", "-")
    return re.sub(r"\s+", " ", t)


# ---------------------------------------------------------------- 10-K extraction
EMP = re.compile(
    r"(?:had|employ(?:ed|s)?|have|has|there were|consisted of|workforce of|total of)\s+"
    r"(?:a total of\s+|a workforce of\s+)?(?:approximately|about|over|more than|nearly|roughly|"
    r"around|close to|in excess of)?\s*(\d{1,3}(?:,\d{3})+|\d{1,6})\s+"
    r"(?:(?:full[- ]time|total|global|regular|permanent|active)\s+(?:and\s+part[- ]time\s+)?)*"
    r"(?:employees|people|team members|full[- ]time equivalent|persons|individuals|staff)", re.I)
MDA_START = re.compile(r"i\s?tem\s*7\s*[.:\-\u2013\u2014]*\s*management'?s?\s+discussion", re.I)
MDA_END = re.compile(r"i\s?tem\s*7a\s*[.:\-\u2013\u2014]*\s*quantitative|"
                     r"i\s?tem\s*8\s*[.:\-\u2013\u2014]*\s*(?:consolidated\s+)?financial\s+statements", re.I)
NUMTOK = re.compile(r"\$?\(?\d[\d,]*(?:\.\d+)?\)?%?")
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")
# Single customer only (no plural "customers", which are top-N group totals).
CUST = re.compile(
    r"\b(?:customer|client|distributor|reseller|partner)\b(?!s|'s)[^.%]{0,220}?"
    r"(\d{1,2}(?:\.\d+)?)\s?%\s+(?:and\s+\d{1,2}(?:\.\d+)?\s?%\s+)?(?:,\s*respectively,\s*)?of\s+"
    r"(?:our\s+|its\s+|the\s+company'?s\s+|total\s+|consolidated\s+|net\s+|gross\s+)*"
    r"(?:revenues?|net revenues?|sales|net sales)", re.I)
CUST_NONE = re.compile(r"no\s+(?:single\s+|one\s+|individual\s+)?(?:customer|client)s?\s+(?:accounted|represented|comprised)"
                       r"[^.]{0,80}(?:10|ten)\s?(?:%|percent)", re.I)
GEO = re.compile(r"international|united states|united kingdom|located|outside|geograph|region|countr|domestic|"
                 r"americas|europe|emea|asia|canada|china|japan|germany|subscription|recurring|growth|increase|"
                 r"decrease|margin|retention|renewal|receivable", re.I)
NEG = re.compile(r"\bno\b|\bnone\b|\bnot\b|\bneither\b|major customers are|defined as|threshold|"
                 r"\bcustomers\b|\bclients\b|over time|point in time|recogni|remaining|intangible|"
                 r"ability|payment history|total operating", re.I)
THRESHOLD = re.compile(r"(?:more than|greater than|in excess of|exceed\w*|at least|over)\s*$", re.I)


def customer_concentration(t: str) -> tuple[float | None, bool]:
    """Largest single-customer % of revenue stated in the text; threshold and negative
    statements ("no customer accounted for more than 10%") are not values."""
    pcts = []
    for m in CUST.finditer(t):
        ctx = m.group(0)
        if GEO.search(ctx) or NEG.search(ctx) or len(re.findall(r"\d[\d,]*", ctx)) > 6:
            continue  # geography, negation, or a financial-table row
        if THRESHOLD.search(ctx[: m.start(1) - m.start()]):
            continue
        p = float(m.group(1))
        if 10 <= p < 100:
            pcts.append(p)
    return (max(pcts) if pcts else None), bool(CUST_NONE.search(t))


def mda_section(t: str) -> str:
    best = ""
    for m in MDA_START.finditer(t):
        e = MDA_END.search(t, m.end())
        span = t[m.start(): e.start() if e else min(len(t), m.start() + 400_000)]
        if len(span) > len(best):
            best = span
    return best


def employees(t: str) -> float | None:
    vals = []
    for m in EMP.finditer(t):
        v = int(m.group(1).replace(",", ""))
        if 5 <= v <= 2_000_000 and not (1990 <= v <= 2035):
            vals.append(v)
    return float(vals[0]) if vals else None  # first statement is normally Item 1 Human Capital / Employees


def parse_10k(row) -> dict:
    raw = get(doc_url(row.cik, row.accession, row.primary_document), subdir="docs10k", compress=True)
    t = to_text(raw)
    mda = mda_section(t)
    cmax, cnone = customer_concentration(t)
    return {"cik": row.cik, "accession": row.accession, "form": row.form,
            "filing_date": row.filing_date.date(), "period": row.report_date,
            "employees": employees(t), "mda_words": len(WORD.findall(mda)),
            "mda_numeric_tokens": len(NUMTOK.findall(mda)), "cust_max_pct": cmax,
            "cust_none_stated": cnone, "text_chars": len(t)}


# ---------------------------------------------------------------- 8-K extraction
OFFICER = re.compile(r"chief\s+executive\s+officer|chief\s+financial\s+officer|principal\s+executive\s+officer|"
                     r"principal\s+financial\s+officer|\bCEO\b|\bCFO\b", re.I)
LEAVE = re.compile(r"\bresign(?:ed|s|ing|ation)?\b|\bretire(?:d|s|ment)?\b|\bretiring\b|"
                   r"step(?:s|ped|ping)?\s+down|\bdepart(?:ed|ing|ure)\b|will\s+depart|\bremoved\b|"
                   r"terminated\s+(?:the\s+|his\s+|her\s+)?employment|no\s+longer\s+serv|"
                   r"cease[sd]?\s+to\s+serve|will\s+leave|\bleaving\b", re.I)
NOT_DEPARTURE = re.compile(r"severance|qualifying termination|in the event|policy|\bplan\b|until terminated|"
                           r"term of employment|separated the positions|will receive|entitled|lump sum|"
                           r"payment|award|bonus|equity|options?\b|vesting|appointed as|elected as|"
                           r"succeed\w*\s+(?:mr|ms|dr)\.?\s+\w+\s+who|chief accounting officer", re.I)


def item_section(t: str, code: str) -> str:
    starts = [m.start() for m in re.finditer(rf"item\s*{re.escape(code)}", t, re.I)]
    if not starts:
        return t[:6000]
    s = starts[-1] if len(starts) > 1 and starts[-1] - starts[0] < 3000 else starts[0]
    nxt = re.search(r"item\s*\d\.\d\d", t[s + 10:], re.I)
    return t[s: s + 10 + (nxt.start() if nxt else 6000)]


def parse_8k(row) -> dict:
    raw = get(doc_url(row.cik, row.accession, row.primary_document), subdir="docs8k", compress=True)
    t = to_text(raw)
    items = [x.strip() for x in str(row.items).split(",")]
    out = {"cik": row.cik, "accession": row.accession, "filing_date": row.filing_date.date(),
           "report_date": row.report_date, "items": row.items, "auditor_change": "4.01" in items,
           "auditor_resigned": False, "ceo_cfo_departure": False, "departure_snippet": ""}
    if "4.01" in items:
        sec = item_section(t, "4.01")
        out["auditor_resigned"] = bool(re.search(r"resign|declin\w+\s+to\s+stand", sec, re.I))
    if "5.02" in items:
        sec = item_section(t, "5.02")
        for s in re.split(r"(?<=[.;])\s", sec):
            if (OFFICER.search(s) and LEAVE.search(s) and not NOT_DEPARTURE.search(s)
                    and not re.search(r"interim\s+(?:chief|ceo|cfo)", s, re.I)):
                out["ceo_cfo_departure"] = True
                out["departure_snippet"] = s[:240]
                break
    return out


def main(ciks: list[str]) -> None:
    f = pd.read_csv(INTERIM / "filings.csv.gz", dtype={"cik": str, "items": str},
                    parse_dates=["filing_date"])
    f = f[f.cik.isin(set(ciks)) & (f.filing_date >= START) & f.primary_document.notna()]
    tenk = f[f.form.isin(["10-K", "10-KT"])]
    ek = f[(f.form == "8-K") & f["items"].fillna("").str.contains(r"4\.01|5\.02")]
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(parse_10k, tenk.itertuples()))
    pd.DataFrame(rows).to_csv(INTERIM / "tenk_fields.csv", index=False)
    print(f"10-K fields: {len(rows)}", flush=True)
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(parse_8k, ek.itertuples()))
    pd.DataFrame(rows).to_csv(INTERIM / "eightk_fields.csv", index=False)
    print(f"8-K fields: {len(rows)}", flush=True)


if __name__ == "__main__":
    main(pd.read_csv(INTERIM / "ever_eligible.csv", dtype=str).cik.tolist())


def reparse_10k_fields() -> None:
    """Re-extract 10-K fields from stored snapshots (no network)."""
    t = pd.read_csv(INTERIM / "tenk_fields.csv", dtype={"cik": str})
    f = pd.read_csv(INTERIM / "filings.csv.gz", dtype={"cik": str, "items": str}, parse_dates=["filing_date"])
    f = f[f.accession.isin(set(t.accession))]
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(parse_10k, f.itertuples()))
    pd.DataFrame(rows).to_csv(INTERIM / "tenk_fields.csv", index=False)
    print(f"10-K fields re-extracted: {len(rows)}")


def reparse_8k_fields() -> None:
    """Re-extract 8-K fields from stored snapshots (no network)."""
    e = pd.read_csv(INTERIM / "eightk_fields.csv", dtype={"cik": str})
    f = pd.read_csv(INTERIM / "filings.csv.gz", dtype={"cik": str, "items": str}, parse_dates=["filing_date"])
    f = f[f.accession.isin(set(e.accession))]
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(parse_8k, f.itertuples()))
    pd.DataFrame(rows).to_csv(INTERIM / "eightk_fields.csv", index=False)
    print(f"8-K fields re-extracted: {len(rows)}")
