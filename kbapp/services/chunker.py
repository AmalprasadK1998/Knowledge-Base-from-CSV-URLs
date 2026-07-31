"""Chunk harvested text into semantically-meaningful units for retrieval.

Uses a simple recursive character splitter with sentence-aware boundaries,
mirroring the approach used by LangChain's RecursiveCharacterTextSplitter
but with no external dependency.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    text: str
    token_count: int


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    """Split text into overlapping chunks.

    `chunk_size` and `chunk_overlap` are measured in characters; `token_count`
    is a rough word-based estimate (whitespace tokens), which is good enough
    for logging and storage.
    """
    if not text:
        return []

    # Split on paragraph breaks first, then sentences, then words.
    separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]
    pieces = _recursive_split(text, separators, chunk_size)

    # Build overlapping chunks.
    chunks: list[Chunk] = []
    idx = 0
    i = 0
    while i < len(pieces):
        window = pieces[i : i + 1]
        joined = pieces[i]
        # Grow the window until we approach chunk_size.
        while (
            i + len(window) < len(pieces)
            and len(joined) + len(pieces[i + len(window)]) < chunk_size
        ):
            window.append(pieces[i + len(window)])
            joined = "".join(window)

        chunks.append(
            Chunk(index=idx, text=joined, token_count=len(joined.split()))
        )
        idx += 1
        if i + len(window) >= len(pieces):
            break
        # Step forward, keeping overlap.
        i = max(i + 1, i + len(window) - 1)

    return chunks


def _recursive_split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    for sep in separators:
        if sep and sep in text:
            parts = text.split(sep)
            out: list[str] = []
            buf = ""
            for part in parts:
                candidate = (buf + sep + part) if buf else part
                if len(candidate) <= chunk_size:
                    buf = candidate
                else:
                    if buf:
                        out.append(buf)
                        buf = ""
                    if len(part) > chunk_size:
                        out.extend(_recursive_split(part, separators[1:] or [""], chunk_size))
                    else:
                        buf = part
            if buf:
                out.append(buf)
            return [p for p in out if p.strip()]

    # No separator worked — hard split.
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
