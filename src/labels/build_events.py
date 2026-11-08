"""Build the labeled event table src/labels/events.csv from SEC EDGAR.

Implements the taxonomy in src/labels/TAXONOMY.md. Inputs (built by src/ingest/):
    data/interim/filings.csv.gz   complete filing index per company (forms, dates, 8-K items)
Documents needed to confirm an event (25-NSE forms, 8-K Item 2.05 texts, going-concern and
liquidation candidates) are fetched from EDGAR and cached under data/raw/docs/.

Output columns: entity_id, event_type, tier, event_date, source_url, confidence, notes,
plus date_uncertainty_days (spread between candidate dates for the same event).
Auxiliary output: data/interim/going_concern_filings.csv (every 10-K with a going-concern
finding, used to tell onsets from continuations and by the universe builder).
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.ingest.sec_http import ROOT, get

INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "src" / "labels" / "events.csv"
GC_OUT = INTERIM / "going_concern_filings.csv"
EVENT_START = pd.Timestamp("2009-01-01")

MERGER_FORMS = {"DEFM14A", "PREM14A", "SC 14D9", "SC TO-T", "SC 13E3", "DEFM14C", "PREM14C"}
FORM15 = {"15-12B", "15-12G", "15-15D"}
DATA_CUTOFF_FOR_EXIT_CHECK = pd.Timestamp("2026-10-31")


# ---------------------------------------------------------------- helpers
def acc_url(cik: str, acc: str, doc: str | None = None) -> str:
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}"
    return f"{base}/{doc}" if doc else f"{base}/{acc}-index.htm"


def fetch_text(url: str) -> str:
    raw = get(url, subdir="docs")
    if raw is None:
        return ""
    t = raw.decode("utf-8", errors="ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ").replace("’", "'")
    return re.sub(r"\s+", " ", t)


def has_items(items: str, code: str) -> bool:
    return isinstance(items, str) and code in [x.strip() for x in items.split(",")]


def event_date(row) -> tuple[pd.Timestamp, int]:
    """8-K report date if 0-30 days before filing, else filing date. Returns (date, spread)."""
    fd, rd = row.filing_date, row.report_date
    if pd.notna(rd) and 0 <= (fd - rd).days <= 30:
        return rd, (fd - rd).days
    spread = abs((fd - rd).days) if pd.notna(rd) else 0
    return fd, spread


def in_merger_context(f: pd.DataFrame, cik: str, d: pd.Timestamp,
                      before: int = 365, after: int = 30) -> bool:
    g = f[(f.cik == cik) & (f.filing_date >= d - pd.Timedelta(days=before))
          & (f.filing_date <= d + pd.Timedelta(days=after))]
    if g.form.isin(MERGER_FORMS).any():
        return True
    eightk = g[g.form.str.startswith("8-K")]
    return bool(eightk["items"].apply(lambda s: has_items(s, "5.01") or has_items(s, "2.01")).any())


def onsets(df: pd.DataFrame, gap_days: int) -> pd.DataFrame:
    """Keep the first event per entity and type, plus any repeat after gap_days of quiet."""
    keep = []
    for _, g in df.sort_values("event_date").groupby(["entity_id", "event_type"]):
        last = None
        for idx, r in g.iterrows():
            if last is None or (r.event_date - last).days > gap_days:
                keep.append(idx)
            last = r.event_date
    return df.loc[keep]


def row(cik, etype, tier, date, url, conf, notes, spread=0):
    return {"entity_id": cik, "event_type": etype, "tier": tier,
            "event_date": pd.Timestamp(date), "source_url": url, "confidence": conf,
            "notes": notes, "date_uncertainty_days": int(spread)}


# ---------------------------------------------------------------- item-based events
def item_events(f: pd.DataFrame) -> list[dict]:
    out = []
    ek = f[f.form.isin(["8-K", "8-K/A"]) & f["items"].notna()]
    bk_dates = {}
    for r in ek[ek["items"].apply(lambda s: has_items(s, "1.03"))].itertuples():
        d, s = event_date(r)
        bk_dates.setdefault(r.cik, []).append(d)
        out.append(row(r.cik, "T1_BANKRUPTCY", 1, d, acc_url(r.cik, r.accession), "high",
                       f"8-K Item 1.03 ({r.form})", s))

    def near_bankruptcy(cik, d, days=30):
        return any(abs((d - b).days) <= days for b in bk_dates.get(cik, []))

    for r in ek[ek["items"].apply(lambda s: has_items(s, "2.04"))].itertuples():
        d, s = event_date(r)
        if near_bankruptcy(r.cik, d) or in_merger_context(f, r.cik, d, 90, 90):
            continue
        out.append(row(r.cik, "T2_DEBT_ACCELERATION", 2, d, acc_url(r.cik, r.accession),
                       "medium", "8-K Item 2.04, no merger context", s))

    for r in ek[ek["items"].apply(lambda s: has_items(s, "3.01"))].itertuples():
        d, s = event_date(r)
        if in_merger_context(f, r.cik, d) or any(0 <= (d - b).days <= 30 for b in bk_dates.get(r.cik, [])):
            continue
        out.append(row(r.cik, "T3_LISTING_DEFICIENCY", 3, d, acc_url(r.cik, r.accession),
                       "high", "8-K Item 3.01, no merger context", s))

    restate = ek[ek["items"].apply(lambda s: has_items(s, "4.02"))]
    depart = ek[ek["items"].apply(lambda s: has_items(s, "5.02"))]
    for r in restate.itertuples():
        rd, _ = event_date(r)
        later = depart[(depart.cik == r.cik) & (depart.filing_date > rd)
                       & (depart.filing_date <= rd + pd.Timedelta(days=365))]
        if len(later):
            x = later.iloc[0]
            d, s = event_date(x)
            out.append(row(r.cik, "T3_EXEC_EXIT_AFTER_RESTATEMENT", 3, d,
                           acc_url(r.cik, x.accession), "low",
                           f"8-K 5.02 after 4.02 filed {rd.date()}; CEO/CFO not verified", s))
    return out


# ---------------------------------------------------------------- delisting / deregistration
COMMON = re.compile(r"common|ordinary shares|class a|american depositary", re.I)
NON_COMMON = re.compile(r"\bwarrants?\b|\bunits?\b|\brights\b|\bnotes?\b|debentures?|preferred|"
                        r"depositary shares? each representing a fraction", re.I)
PERIODIC = {"10-K", "10-Q", "10-KT", "10-K/A", "10-Q/A"}


def _nse_fields(r) -> tuple[str, str, str]:
    """(rule provision, security class, url) from a Form 25-NSE. Uses the raw XML when the
    filing is structured (2010 onward); otherwise the text filing."""
    doc = r.primary_document if isinstance(r.primary_document, str) else ""
    if doc.endswith(".xml"):
        url = acc_url(r.cik, r.accession, doc.split("/")[-1])
        raw = (get(url, subdir="docs") or b"").decode("utf-8", "ignore")
        rule = re.search(r"<ruleProvision>(.*?)</ruleProvision>", raw, re.S)
        cls = re.search(r"<descriptionClassSecurity>(.*?)</descriptionClassSecurity>", raw, re.S)
        return (rule.group(1).strip() if rule else ""), (cls.group(1).strip() if cls else ""), url
    url = acc_url(r.cik, r.accession).replace("-index.htm", ".txt")
    t = fetch_text(url)
    rule = "12d2-2(b)" if re.search(r"12d2-2\(b\)", t) and not re.search(r"12d2-2\(a\)", t) else ""
    m = re.search(r"(?i)class of (registered )?securit(y|ies)\W{0,20}(.{0,120})", t)
    return rule, (m.group(3) if m else ""), url


def delisting_events(f: pd.DataFrame) -> list[dict]:
    """T1_DELISTING: exchange removal for failing listing standards (Rule 12d2-2(b)) of the
    common stock. Rule 12d2-2(a) removals (redemption, maturity, merger exchange) are exits."""
    out = []
    nse = f[f.form == "25-NSE"]
    with ThreadPoolExecutor(4) as ex:
        docs = list(ex.map(_nse_fields, nse.itertuples()))
    for r, (rule, cls, url) in zip(nse.itertuples(), docs):
        if "12d2-2(b)" not in rule.replace(" ", ""):
            continue
        if NON_COMMON.search(cls) and not COMMON.search(cls):
            continue
        if not cls:
            conf = "medium"
        elif NON_COMMON.search(cls):
            continue  # e.g. "Units, each consisting of one share of Class A common stock and ..."
        else:
            conf = "high"
        d = r.filing_date
        prior = f[(f.cik == r.cik) & f.form.str.startswith("8-K") & (f.filing_date <= d)
                  & (f.filing_date >= d - pd.Timedelta(days=180))]
        prior = prior[prior["items"].apply(lambda s: has_items(s, "3.01"))]
        spread = (d - prior.filing_date.max()).days if len(prior) else 0
        out.append(row(r.cik, "T1_DELISTING", 1, d, url, conf,
                       f"Form 25-NSE under Rule 12d2-2(b); class: {cls[:60] or 'not stated'}", spread))

    # T1_DEREGISTRATION: Form 15 outside a merger, after which the company files no further
    # 10-K or 10-Q within 18 months (i.e. it actually stopped reporting).
    for r in f[f.form.isin(FORM15)].itertuples():
        d = r.filing_date
        if d > DATA_CUTOFF_FOR_EXIT_CHECK or in_merger_context(f, r.cik, d):
            continue
        later = f[(f.cik == r.cik) & f.form.isin(PERIODIC) & (f.filing_date > d + pd.Timedelta(days=30))
                  & (f.filing_date <= d + pd.Timedelta(days=548))]
        if len(later):
            continue
        before = f[(f.cik == r.cik) & f.form.isin(PERIODIC) & (f.filing_date <= d)]
        gap = (d - before.filing_date.max()).days if len(before) else 0
        note = (f"{r.form} filed {d.date()}, no merger context, no 10-K/10-Q filed in the next "
                f"18 months; last periodic report {gap} days earlier")
        if gap > 180:  # company had already stopped reporting: date at the first missed report
            d = before.filing_date.max() + pd.Timedelta(days=105)
            note += "; dated at first missed periodic report"
        out.append(row(r.cik, "T1_DEREGISTRATION", 1, d, acc_url(r.cik, r.accession), "medium", note, gap))
    return out


def reporting_ceased_events(f: pd.DataFrame, t1: pd.DataFrame) -> list[dict]:
    """T1_REPORTING_CEASED: the company stops filing 10-K/10-Q for more than 18 months with no
    Form 15, no Tier 1 event, and no merger, acquisition or exchange-delisting filing around
    the exit. Dated at the first missed periodic report (last report + 105 days)."""
    out = []
    per = f[f.form.isin(PERIODIC)].groupby("cik").filing_date.max()
    exitish = f[f.form.isin(MERGER_FORMS | FORM15 | {"25-NSE", "25"})
                | f["items"].apply(lambda s: has_items(s, "5.01") or has_items(s, "2.01"))]
    for cik, last in per.items():
        if last > DATA_CUTOFF_FOR_EXIT_CHECK - pd.Timedelta(days=548):
            continue
        lo, hi = last - pd.Timedelta(days=400), last + pd.Timedelta(days=548)
        if ((exitish.cik == cik) & exitish.filing_date.between(lo, hi)).any():
            continue
        if ((t1.entity_id == cik) & t1.event_date.between(lo, hi)).any():
            continue
        d = last + pd.Timedelta(days=105)
        out.append(row(cik, "T1_REPORTING_CEASED", 1, d, acc_url(cik, f[(f.cik == cik) & (f.filing_date == last)
                       & f.form.isin(PERIODIC)].iloc[-1].accession), "low",
                       f"Last 10-K/10-Q filed {last.date()}; no periodic report, Form 15, merger or "
                       f"delisting filing in the following 18 months", 105))
    return out


# ---------------------------------------------------------------- layoffs and wind-downs (8-K 2.05)
PCT = re.compile(r"(?:approximately|about|roughly|nearly|over|more than)?\s*(\d{1,3}(?:\.\d)?)\s?%\s+of\s+"
                 r"(?:the company's |our |its |the |total |global |overall |current |full-time |)*"
                 r"(?:total |global |overall |current |full-time |)*"
                 r"(?:workforce|employees|headcount|employee base|staff)", re.I)
WIND = re.compile(r"wind(?:ing)?[- ]down (?:of )?(?:the company's|our|its) (?:business|operations)|"
                  r"cease (?:all )?(?:of )?(?:its|our) operations|ceasing (?:all )?operations", re.I)


def restructuring_events(f: pd.DataFrame) -> list[dict]:
    ek = f[f.form.isin(["8-K", "8-K/A"]) & f["items"].apply(lambda s: has_items(s, "2.05"))]
    rows = list(ek.itertuples())
    with ThreadPoolExecutor(4) as ex:
        texts = list(ex.map(lambda r: fetch_text(acc_url(r.cik, r.accession, r.primary_document))
                            if isinstance(r.primary_document, str) else "", rows))
    out = []
    for r, t in zip(rows, texts):
        d, s = event_date(r)
        url = acc_url(r.cik, r.accession)
        pcts = [float(x) for x in PCT.findall(t) if 0 < float(x) <= 100]
        if WIND.search(t):
            snippet = WIND.search(t).group(0)
            out.append(row(r.cik, "T1_LIQUIDATION", 1, d, url, "medium",
                           f"8-K Item 2.05 wind-down language: '{snippet}'", s))
        elif pcts and max(pcts) >= 30:
            out.append(row(r.cik, "T2_MASS_LAYOFF", 2, d, url, "medium",
                           f"8-K Item 2.05: {max(pcts):g}% of workforce", s))
    return out


# ---------------------------------------------------------------- full-text search helpers
def efts(query: str, ciks: list[str], forms: str) -> list[dict]:
    hits = []
    q = urllib.parse.quote(query)
    for i in range(0, len(ciks), 40):
        batch = ",".join(ciks[i:i + 40])
        start = 0
        while True:
            u = (f"https://efts.sec.gov/LATEST/search-index?q={q}&forms={forms}"
                 f"&startdt=2009-01-01&enddt=2026-12-31&ciks={batch}&from={start}")
            d = json.loads(get(u, subdir="efts"))
            hh = d["hits"]["hits"]
            for h in hh:
                s = h["_source"]
                hits.append({"id": h["_id"], "adsh": s["adsh"], "ciks": s["ciks"],
                             "form": s["form"], "root_form": (s.get("root_forms") or [""])[0],
                             "file_date": s["file_date"], "file_type": s.get("file_type")})
            start += len(hh)
            if not hh or start >= d["hits"]["total"]["value"] or start >= 10000:
                break
    return hits


def hit_url(h: dict, cik: str) -> str:
    acc, doc = h["id"].split(":", 1)
    return acc_url(cik, acc, doc)


# ---------------------------------------------------------------- going concern
GC_QUERIES = ['"raise substantial doubt about its ability to continue as a going concern"',
              '"raise substantial doubt about the Company\'s ability to continue as a going concern"',
              '"raises substantial doubt about its ability to continue as a going concern"',
              '"substantial doubt about the Company\'s ability to continue as a going concern"',
              '"explanatory paragraph" "going concern"',
              '"substantial doubt" "going concern"']  # broad recall pass; every hit is classified
GC_SENT = re.compile(r"[^.]{0,400}substantial doubt[^.]{0,200}going concern[^.]{0,200}\.", re.I)
GC_NEG = re.compile(r"\b(could|may|might|would|will|can|if|whether|no|not|alleviat\w*|absence|"
                    r"unless|risk|evaluat\w*|assess\w*)\b", re.I)


def gc_classify(text: str) -> tuple[bool, str]:
    """True if some sentence asserts (not hypothesizes or negates) substantial doubt."""
    for m in GC_SENT.finditer(text):
        s = m.group(0)
        pre = s[: s.lower().find("substantial doubt")]
        if re.search(r"(?i)alleviat|not probable|does not exist|not exist|no longer|"
                     r"not raise|no substantial doubt|other auditors|previously|prior year", s):
            continue
        if GC_NEG.search(pre[-120:]):
            continue
        return True, s.strip()[:300]
    if re.search(r"(?i)explanatory paragraph[^.]{0,250}going concern", text):
        return True, re.search(r"(?i)[^.]{0,200}explanatory paragraph[^.]{0,250}going concern[^.]*\.",
                               text).group(0).strip()[:300]
    return False, ""


def going_concern_events(ciks: list[str], f: pd.DataFrame) -> list[dict]:
    hits = []
    for q in GC_QUERIES:
        hits += efts(q, ciks, "10-K,10-KT")
    hits = [h for h in hits if h["root_form"] in ("10-K", "10-KT") and h["form"] in ("10-K", "10-KT")]
    uniq = {}
    for h in hits:
        cik = next((c for c in h["ciks"] if c in set(ciks)), None)
        if cik:
            uniq.setdefault((cik, h["id"]), h)
    items = list(uniq.items())
    with ThreadPoolExecutor(4) as ex:
        texts = list(ex.map(lambda kv: fetch_text(hit_url(kv[1], kv[0][0])), items))
    found = {}
    for ((cik, _), h), t in zip(items, texts):
        ok, snip = gc_classify(t)
        if ok:
            key = (cik, h["adsh"])
            conf = "high" if (h["file_type"] or "").upper().startswith("EX-23") or \
                re.search(r"(?i)report of independent registered public accounting firm", t) else "medium"
            if key not in found or conf == "high":
                found[key] = {"cik": cik, "adsh": h["adsh"], "filed": pd.Timestamp(h["file_date"]),
                              "doc": hit_url(h, cik), "confidence": conf, "snippet": snip}
    gc = pd.DataFrame(found.values())
    if gc.empty:
        return []
    gc.to_csv(GC_OUT, index=False)
    ev = pd.DataFrame([row(r.cik, "T2_GOING_CONCERN", 2, r.filed, acc_url(r.cik, r.adsh),
                           r.confidence, f"Going-concern finding: \"{r.snippet[:200]}\"")
                       for r in gc.itertuples()])
    ev = onsets(ev, 400)  # consecutive annual findings are one spell
    return ev.to_dict("records")


# ---------------------------------------------------------------- liquidation plans
LIQ_QUERIES = ['"plan of complete liquidation and dissolution"', '"plan of liquidation and dissolution"']


def liquidation_events(ciks: list[str]) -> list[dict]:
    hits = []
    for q in LIQ_QUERIES:
        hits += efts(q, ciks, "8-K,DEF 14A,PRE 14A,DEFA14A")
    best = {}
    for h in hits:
        cik = next((c for c in h["ciks"] if c in set(ciks)), None)
        if not cik:
            continue
        d = pd.Timestamp(h["file_date"])
        if cik not in best or d < best[cik][0]:
            best[cik] = (d, h)
    out = []
    for cik, (d, h) in best.items():
        out.append(row(cik, "T1_LIQUIDATION", 1, d, acc_url(cik, h["adsh"]), "medium",
                       f"First {h['root_form']} mentioning a plan of liquidation and dissolution"))
    return out


# ---------------------------------------------------------------- main
def build(ciks: list[str]) -> pd.DataFrame:
    f = pd.read_csv(INTERIM / "filings.csv.gz", dtype={"cik": str, "items": str},
                    parse_dates=["filing_date", "report_date"])
    f = f[f.cik.isin(set(ciks))]
    rows = []
    for name, fn in [("items", lambda: item_events(f)), ("delisting", lambda: delisting_events(f)),
                     ("restructuring", lambda: restructuring_events(f)),
                     ("going concern", lambda: going_concern_events(ciks, f)),
                     ("liquidation", lambda: liquidation_events(ciks))]:
        r = fn()
        print(f"{name}: {len(r)} candidate events")
        rows += r
    ev = pd.DataFrame(rows)
    rc = reporting_ceased_events(f, ev[ev.tier == 1])
    print(f"reporting ceased: {len(rc)} candidate events")
    ev = pd.concat([ev, pd.DataFrame(rc)], ignore_index=True)
    ev = ev[ev.event_date >= EVENT_START]
    # Deregistration within 365 days after another Tier 1 event is the same collapse.
    t1 = ev[(ev.tier == 1) & (ev.event_type != "T1_DEREGISTRATION")]
    def redundant(r):
        if r.event_type != "T1_DEREGISTRATION":
            return False
        p = t1[(t1.entity_id == r.entity_id) & (t1.event_date <= r.event_date)
               & (t1.event_date >= r.event_date - pd.Timedelta(days=365))]
        return len(p) > 0
    ev = ev[~ev.apply(redundant, axis=1)]
    gaps = {"T2_GOING_CONCERN": 400}
    parts = [onsets(g, gaps.get(t, 730)) for t, g in ev.groupby("event_type")]
    ev = pd.concat(parts).sort_values(["entity_id", "event_date", "tier"])
    ev = drop_spac_period(ev)
    ev = apply_adjudications(ev)
    ev["event_date"] = ev.event_date.dt.date
    ev.to_csv(OUT, index=False)
    return ev


from src.universe.universe import SPAC_NAME  # noqa: E402


def drop_spac_period(ev: pd.DataFrame) -> pd.DataFrame:
    """Drop events while the registrant was a blank-check company (SPAC), i.e. when its latest
    annual report on or before the event was filed under a SPAC name. Shells are excluded
    from the universe (decision 2026-11-07), so their events are not collapses of an
    operating software business."""
    sub = pd.read_csv(INTERIM / "fsds_sub.csv.gz", dtype={"cik": str},
                      usecols=["cik", "name", "form", "filed"], parse_dates=["filed"])
    tk = sub[sub.form.isin(["10-K", "10-KT"])].sort_values("filed")
    tk["spac"] = tk.name.str.contains(SPAC_NAME)
    keep = []
    for r in ev.itertuples():
        prior = tk[(tk.cik == r.entity_id) & (tk.filed <= r.event_date)]
        keep.append(not (len(prior) and prior.spac.iloc[-1]))
    return ev[keep]


def apply_adjudications(ev: pd.DataFrame) -> pd.DataFrame:
    """Apply src/labels/adjudications.csv (manual review decisions, each with a reason)."""
    adj = pd.read_csv(ROOT / "src" / "labels" / "adjudications.csv", dtype=str).fillna("")
    mask = pd.Series(False, index=ev.index)
    for a in adj.itertuples():
        m = (ev.entity_id == a.entity_id) & (ev.event_type == a.event_type)
        if a.event_date:
            m &= ev.event_date == pd.Timestamp(a.event_date)
        mask |= m & (a.decision == "drop")
    print(f"adjudications: dropped {int(mask.sum())} events")
    return ev[~mask]
