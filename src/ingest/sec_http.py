"""Shared HTTP client for SEC EDGAR.

- Sends the User-Agent SEC requires (SEC_USER_AGENT env var or .env).
- Rate-limits below SEC's 10 requests/second fair-access ceiling.
- Caches every raw response under data/raw/ so each run has a stored raw snapshot
  and re-runs do not hit SEC again. Cache files are never overwritten unless refresh=True.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
_MIN_INTERVAL = 1 / 8  # 8 req/s, under SEC's 10 req/s limit
_lock = threading.Lock()
_last = [0.0]
_session = requests.Session()


def _user_agent() -> str:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("SEC_USER_AGENT="):
                    ua = line.split("=", 1)[1].strip().strip('"')
    if not ua:
        raise RuntimeError("Set SEC_USER_AGENT (see .env.example). SEC requires a contact.")
    return ua


def _throttle() -> None:
    with _lock:
        wait = _last[0] + _MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()


def cache_path(url: str, subdir: str) -> Path:
    name = url.split("?")[0].rstrip("/").split("/")[-1] or "index"
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    return RAW / subdir / f"{h}_{name}"[:150]


def get(url: str, subdir: str = "misc", refresh: bool = False, retries: int = 5) -> bytes | None:
    """Fetch url (cached). Returns None on 404."""
    path = cache_path(url, subdir)
    if path.exists() and not refresh:
        return path.read_bytes()
    headers = {"User-Agent": _user_agent(), "Accept-Encoding": "gzip, deflate"}
    for attempt in range(retries):
        _throttle()
        try:
            r = _session.get(url, headers=headers, timeout=60)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 404:
            return None
        if r.status_code in (429, 500, 502, 503, 504) or r.status_code == 403:
            time.sleep(2 ** attempt + 1)
            continue
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
        return r.content
    raise RuntimeError(f"Failed after {retries} attempts: {url}")
