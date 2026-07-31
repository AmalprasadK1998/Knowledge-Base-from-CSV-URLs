"""HTTP scraper that fetches a URL and extracts clean text + metadata.

Designed for "listing pages of people" (e.g. executive bios). Uses
BeautifulSoup with lxml to pull the title, meta description, and a readable
text dump. No JS rendering — these pages are server-rendered.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from playwright_scraper import get_page_html

logger = logging.getLogger(__name__)

# Tags whose text is noise for a knowledge base.
_SKIP_TAGS = (
    "script", "style", "noscript", "iframe", "svg", "nav", "footer",
    "header", "form", "button",
)


@dataclass
class ScrapeResult:
    url: str
    http_status: int | None
    title: str
    meta_description: str
    raw_html: str
    extracted_text: str
    error: str = ""


def scrape_url(url: str, timeout: int = 20, user_agent: str = "") -> ScrapeResult:
    """Fetch and parse a single URL. Never raises — returns an error result."""
    headers = {
        "User-Agent": user_agent or "Mozilla/5.0 (compatible; KnowledgeBaseBot/1.0)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        logger.warning("scrape failed for %s: %s", url, exc)
        
        return ScrapeResult(
            url=url, http_status=None, title="", meta_description="",
            raw_html="", extracted_text="", error=str(exc),
        )

    raw_html = resp.text or ""
    soup = BeautifulSoup(raw_html, "lxml")

    title = _clean(soup.title.string) if soup.title else ""
    meta_desc = _meta_description(soup)
    extracted = _extract_text(soup)

    logger.info("scraped %s -> %s (%d chars)", url, resp.status_code, len(extracted))
    return ScrapeResult(
        url=url,
        http_status=resp.status_code,
        title=title[:500],
        meta_description=meta_desc,
        raw_html=raw_html,
        extracted_text=extracted,
    )


def _meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if tag and tag.get("content"):
        return _clean(tag["content"])
    return ""


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(_SKIP_TAGS):
        tag.decompose()

    # Prefer main/article content when available.
    container = soup.find("main") or soup.find("article") or soup.body or soup
    text = container.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _clean(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()
