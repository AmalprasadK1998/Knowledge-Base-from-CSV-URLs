"""FAISS-backed vector store.

Persists a FAISS index to disk alongside a JSON sidecar mapping FAISS row
ids to (url, chunk_id) for retrieval. Rebuilt on demand from the database
so it is always consistent with the SQLite content.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from .embedder import get_embedder

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    url: str
    chunk_id: int
    chunk_text: str
    score: float


class VectorStore:
    """Thin wrapper around a FAISS L2 index with a JSON id map."""

    def __init__(self, store_dir: str | os.PathLike):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.store_dir / "index.faiss"
        self.meta_path = self.store_dir / "index_meta.json"
        self.embedder = get_embedder()
        self.dim = self.embedder.dim
        self.index: faiss.Index | None = None
        self.meta: list[dict] = []  # row id -> {url, chunk_id, chunk_text}

    # --- build / load -------------------------------------------------------
    def build(self, chunks: list[dict]) -> int:
        """Build the index from a list of {url, chunk_id, text} dicts.

        Returns the number of vectors indexed.
        """
        if not chunks:
            self.index = None
            self.meta = []
            self._save()
            return 0

        texts = [c["text"] for c in chunks]
        logger.info("embedding %d chunks (dim=%d)", len(texts), self.dim)
        vectors = self.embedder.embed(texts).astype("float32")

        index = faiss.IndexFlatL2(self.dim)
        index.add(vectors)

        self.index = index
        self.meta = [
            {"url": c["url"], "chunk_id": c["chunk_id"], "chunk_text": c["text"]}
            for c in chunks
        ]
        self._save()
        logger.info("vector store built with %d vectors", index.ntotal)
        return index.ntotal

    def load(self) -> bool:
        if self.index_path.exists() and self.meta_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            self.meta = json.loads(self.meta_path.read_text("utf-8"))
            logger.info("loaded vector store (%d vectors)", self.index.ntotal)
            return True
        return False

    def _save(self) -> None:
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
        else:
            if self.index_path.exists():
                self.index_path.unlink()
        self.meta_path.write_text(json.dumps(self.meta), "utf-8")

    # --- query --------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        if self.index is None or self.index.ntotal == 0 or not self.meta:
            return []

        qvec = self.embedder.embed([query]).astype("float32")
        k = min(top_k, self.index.ntotal)
        distances, ids = self.index.search(qvec, k)

        hits: list[SearchHit] = []
        for dist, row_id in zip(distances[0], ids[0]):
            if row_id < 0 or row_id >= len(self.meta):
                continue
            m = self.meta[row_id]
            hits.append(
                SearchHit(
                    url=m["url"],
                    chunk_id=m["chunk_id"],
                    chunk_text=m["chunk_text"],
                    score=float(dist),
                )
            )
        return hits

    def size(self) -> int:
        return int(self.index.ntotal) if self.index is not None else 0


# Module-level singleton lazily created on first use.
_store: VectorStore | None = None


def get_vector_store(store_dir: str | os.PathLike | None = None) -> VectorStore:
    global _store
    if _store is None:
        from django.conf import settings

        _store = VectorStore(store_dir or settings.VECTOR_STORE_DIR)
        _store.load()
    return _store
