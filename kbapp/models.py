"""Database models for harvested URLs and their content chunks.

Two models:
  - HarvestedURL: one row per URL found in an uploaded CSV. Stores the raw
    scraped HTML, HTTP status, and metadata.
  - ContentChunk: a semantically-meaningful slice of the harvested text,
    used as the unit of embedding and retrieval.
"""
from __future__ import annotations

from django.db import models


class HarvestedURL(models.Model):
    """A URL harvested from an uploaded CSV, plus its scraped content."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SCRAPING = "scraping", "Scraping"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    url = models.URLField(max_length=2000, db_index=True)
    source_file = models.CharField(max_length=255, blank=True)
    http_status = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    title = models.CharField(max_length=500, blank=True)
    meta_description = models.TextField(blank=True)
    raw_html = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["url"], name="unique_url"),
        ]

    def __str__(self) -> str:
        return self.url


class ContentChunk(models.Model):
    """A chunk of text extracted from a HarvestedURL, used for retrieval."""

    url = models.ForeignKey(
        HarvestedURL, related_name="chunks", on_delete=models.CASCADE
    )
    chunk_index = models.IntegerField(default=0)
    text = models.TextField()
    token_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["url_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["url", "chunk_index"], name="unique_url_chunk"
            ),
        ]

    def __str__(self) -> str:
        return f"chunk {self.chunk_index} of {self.url_id}"
