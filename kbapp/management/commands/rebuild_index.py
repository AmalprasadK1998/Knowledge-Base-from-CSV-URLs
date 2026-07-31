"""Rebuild the FAISS vector index from all successfully scraped URLs.

Usage:
    python manage.py rebuild_index
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from kbapp.services.pipeline import _rebuild_index


class Command(BaseCommand):
    help = "Rebuild the FAISS vector index from harvested content in SQLite."

    def handle(self, *args, **options):
        n = _rebuild_index()
        self.stdout.write(self.style.SUCCESS(f"Vector index rebuilt with {n} chunks."))
