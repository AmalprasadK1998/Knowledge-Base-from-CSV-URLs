"""CSV parsing helpers.

Accepts a CSV with a URL column (case-insensitive header) or a bare list of
URLs (one per line). Returns a de-duplicated list of URL strings.
"""
from __future__ import annotations

import csv
import io
import logging
from typing import Iterable

logger = logging.getLogger(__name__)

# Candidate header names we recognise as "the URL column".
_URL_HEADERS = ("url", "urls", "link", "links", "website", "page")


def _looks_like_url(value: str) -> bool:
    value = value.strip()
    return value.lower().startswith(("http://", "https://"))


def parse_csv(file_bytes: bytes) -> list[str]:
    """Parse uploaded CSV bytes into a de-duplicated list of URLs."""
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))

    rows = list(reader)
    if not rows:
        return []

    # Detect a header row with a URL-like column name.
    header = [h.strip().lower() for h in rows[0]]
    url_col_idx = None
    for idx, name in enumerate(header):
        if name in _URL_HEADERS:
            url_col_idx = idx
            break

    urls: list[str] = []
    if url_col_idx is not None:
        data_rows = rows[1:]
        for row in data_rows:
            if len(row) > url_col_idx and row[url_col_idx].strip():
                urls.append(row[url_col_idx].strip())
    else:
        # No recognised header: treat every non-empty cell that looks like a
        # URL as a candidate.
        for row in rows:
            for cell in row:
                cell = cell.strip()
                if cell and _looks_like_url(cell):
                    urls.append(cell)

    return _dedupe(urls)


def _dedupe(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out
