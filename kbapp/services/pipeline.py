"""End-to-end pipeline: scrape -> store -> chunk -> embed -> index.

Exposes a single `run_pipeline(urls, source_file)` that is called from the
upload view (synchronously for small batches) and from the management
command (for bulk re-indexing).
"""
from __future__ import annotations

import hashlib
import logging

from django.conf import settings

from ..models import ContentChunk, HarvestedURL
from .chunker import chunk_text
from .scraper import scrape_url
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


def run_pipeline(urls: list[str], source_file: str = "") -> dict:
    """Scrape each URL, persist to SQLite, then rebuild the FAISS index.

    Returns a summary dict with counts.
    """
    timeout = settings.SCRAPER_TIMEOUT
    ua = settings.SCRAPER_USER_AGENT
    max_pages = settings.SCRAPER_MAX_PAGES

    scraped = 0
    failed = 0
    for i, url in enumerate(urls[:max_pages]):
        obj, _ = HarvestedURL.objects.get_or_create(
            url=url, defaults={"source_file": source_file}
        )
        if obj.status == HarvestedURL.Status.DONE and obj.extracted_text:
            scraped += 1
            continue

        obj.status = HarvestedURL.Status.SCRAPING
        obj.save(update_fields=["status"])

        result = scrape_url(url, timeout=timeout, user_agent=ua)
        obj.http_status = result.http_status
        obj.title = result.title
        obj.meta_description = result.meta_description
        obj.raw_html = result.raw_html
        obj.extracted_text = result.extracted_text
        obj.content_hash = hashlib.sha256(result.extracted_text.encode()).hexdigest()[:32]

        if (result.error or not result.extracted_text or result.http_status is None or result.http_status >= 400):
            obj.status = HarvestedURL.Status.FAILED
            obj.error_message = result.error or "No text extracted"
            failed += 1
        else:
            obj.status = HarvestedURL.Status.DONE
            obj.error_message = ""
            scraped += 1
        obj.save()

    logger.info("scraping done: %d ok, %d failed", scraped, failed)

    # Rebuild chunks + vector index from all successfully scraped URLs.
    _rebuild_index()
    return {"scraped": scraped, "failed": failed, "urls": len(urls)}


def _rebuild_index() -> int:
    """Rebuild ContentChunk rows and the FAISS index from scratch."""
    # Clear old chunks.
    ContentChunk.objects.all().delete()

    urls = HarvestedURL.objects.filter(status=HarvestedURL.Status.DONE)
    chunk_dicts: list[dict] = []
    for url_obj in urls:
        chunks = chunk_text(url_obj.extracted_text)
        for ch in chunks:
            ContentChunk.objects.create(
                url=url_obj, chunk_index=ch.index, text=ch.text, token_count=ch.token_count
            )
            chunk_dicts.append(
                {"url": url_obj.url, "chunk_id": ch.index, "text": ch.text}
            )

    store = get_vector_store()
    n = store.build(chunk_dicts)
    logger.info("index rebuilt: %d chunks across %d urls", n, urls.count())
    return n
