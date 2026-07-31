"""Embedding service.

Strategy:
  1. If Google AI Studio credentials are configured, use Gemini embeddings.
  2. Otherwise try `sentence-transformers` for high-quality dense embeddings.
  3. Finally fall back to a deterministic TF-IDF embedding so FAISS indexing
     continues to work with zero model downloads.

All implementations expose the same interface: `embed(texts) -> np.ndarray`
and `dim -> int`.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from functools import lru_cache

import numpy as np
import requests

logger = logging.getLogger(__name__)

# Fixed dimension for the TF-IDF fallback so the FAISS index is stable.
_FALLBACK_DIM = 384


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class TFIDFHashEmbedder:
    """Deterministic hashed-bag-of-words embedder (no model download)."""

    def __init__(self, dim: int = _FALLBACK_DIM):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = np.zeros((len(texts), self.dim), dtype="float32")
        for i, text in enumerate(texts):
            tokens = _word_tokens(text)
            if not tokens:
                continue
            counts: dict[int, float] = {}
            for tok in tokens:
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dim
                counts[h] = counts.get(h, 0.0) + 1.0
            for idx, cnt in counts.items():
                vecs[i, idx] = cnt
            norm = np.linalg.norm(vecs[i])
            if norm > 0:
                vecs[i] /= norm
        return vecs


class GoogleEmbedder:
    """Embedding provider for Google AI Studio (Gemini)."""

    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001"):
        self.api_key = api_key
        self.model_name = model_name
        self.dim = 768

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype="float32")

        vectors: list[list[float]] = []
        for text in texts:
            vectors.append(self._embed_one(text))
        arr = np.asarray(vectors, dtype="float32")
        self.dim = int(arr.shape[1])
        return arr

    def _embed_one(self, text: str) -> list[float]:
        endpoint = os.getenv(
            "GOOGLE_EMBEDDING_ENDPOINT",
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
        ).replace("{model}", self.model_name)
        payload = {
            "model": f"models/{self.model_name}",
            "content": {"parts": [{"text": text}]},
        }
        response = requests.post(
            endpoint,
            params={"key": self.api_key},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]["values"]


@lru_cache(maxsize=1)
def get_embedder():
    """Return a singleton embedder with Google, sentence-transformers, or fallback."""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if api_key:
        model_name = os.getenv("GOOGLE_EMBEDDING_MODEL", "gemini-embedding-001").strip()
        try:
            emb = GoogleEmbedder(api_key=api_key, model_name=model_name)
            emb.embed(["sample text"])
            logger.info("Google embedding provider ready (model=%s, dim=%d)", model_name, emb.dim)
            return emb
        except Exception as exc:
            logger.warning("Google embeddings unavailable (%s); falling back", exc)

    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        logger.info("loading sentence-transformers model: %s", model_name)
        model = SentenceTransformer(model_name)

        class STEmbedder:
            def __init__(self, m):
                self.m = m
                self.dim = int(m.get_sentence_embedding_dimension())

            def embed(self, texts):
                return self.m.encode(
                    texts, convert_to_numpy=True, show_progress_bar=False
                ).astype("float32")

        emb = STEmbedder(model)
        logger.info("embedder ready (dim=%d)", emb.dim)
        return emb
    except Exception as exc:
        logger.warning(
            "sentence-transformers unavailable (%s); using TF-IDF fallback embedder",
            exc,
        )
        return TFIDFHashEmbedder()
