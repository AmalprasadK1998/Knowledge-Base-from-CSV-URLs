"""Answer synthesis service.

Tries Google AI Studio (if configured) to produce a natural-language answer
from retrieved chunks. If not available, it falls back to Groq or a local
extractive summarizer that picks the most query-relevant sentences.
"""
from __future__ import annotations

import logging
import os
import re

import requests

from .embedder import get_embedder

logger = logging.getLogger(__name__)


def synthesize_answer(query: str, chunks: list[str]) -> str:
    """Produce a readable answer from retrieved chunk texts."""
    if not chunks:
        return "No relevant information was found in the knowledge base."

    if os.getenv("GOOGLE_API_KEY"):
        try:
            return _google_answer(query, chunks)
        except Exception as exc:
            logger.warning("Google answer failed (%s); trying Groq/local fallback", exc)

    if os.getenv("GROQ_API_KEY"):
        try:
            return _groq_answer(query, chunks)
        except Exception as exc:
            logger.warning("Groq answer failed (%s); using local summarizer", exc)

    return _extractive_answer(query, chunks)


def _google_answer(query: str, chunks: list[str]) -> str:
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    model = os.getenv("GOOGLE_MODEL", "gemini-3.1-flash-lite").strip()
    endpoint = os.getenv(
        "GOOGLE_LLM_ENDPOINT",
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    ).replace("{model}", model)

    context = "\n\n---\n\n".join(chunks[:6])
    prompt = (
        "You are a research assistant. Using only the context below, answer "
        "the user's question about people (executives, roles, bios). If the "
        "context is insufficient, say so. Be concise and structured.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    )

    response = requests.post(
        endpoint,
        params={"key": key},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _groq_answer(query: str, chunks: list[str]) -> str:
    key = os.getenv("GROQ_API_KEY", "")
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    endpoint = os.getenv("GROQ_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")

    context = "\n\n---\n\n".join(chunks[:6])
    prompt = (
        "You are a research assistant. Using only the context below, answer "
        "the user's question about people (executives, roles, bios). If the "
        "context is insufficient, say so. Be concise and structured.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    )

    resp = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 512,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _extractive_answer(query: str, chunks: list[str], max_sentences: int = 5) -> str:
    """Local fallback: rank sentences by query overlap + embedding similarity."""
    sentences: list[str] = []
    for ch in chunks:
        sentences.extend(_split_sentences(ch))

    if not sentences:
        return chunks[0][:500]

    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    embedder = get_embedder()

    try:
        qv = embedder.embed([query])[0]
        sv = embedder.embed(sentences)
        sims = _cosine_batch(qv, sv)
    except Exception:
        sims = [0.0] * len(sentences)

    scored: list[tuple[float, int, str]] = []
    for i, sent in enumerate(sentences):
        sent_tokens = set(re.findall(r"[a-z0-9]+", sent.lower()))
        overlap = (
            len(query_tokens & sent_tokens) / max(len(query_tokens), 1)
            if query_tokens
            else 0.0
        )
        score = 0.5 * sims[i] + 0.5 * overlap
        scored.append((score, i, sent))

    scored.sort(key=lambda t: (-t[0], t[1]))
    top = [s for _, _, s in scored[:max_sentences]]
    top.sort(key=lambda s: sentences.index(s))
    return " ".join(top)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 30]


def _cosine_batch(q: "np.ndarray", m: "np.ndarray") -> list[float]:
    import numpy as np

    qn = q / (np.linalg.norm(q) + 1e-9)
    mn = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
    return list(mn @ qn)
