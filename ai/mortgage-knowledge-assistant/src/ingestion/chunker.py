"""Word-count chunking (documented approximation of token count — ~1.3 tokens/word for English
prose, so CHUNK_SIZE_WORDS=400 approximates the 512-token default from the capstone spec without
a tokenizer dependency). Overlap is a sliding window measured in words for the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.loader import DocumentSection


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    section: str
    text: str


def chunk_sections(sections: list[DocumentSection], *, size_words: int, overlap_words: int) -> list[Chunk]:
    if overlap_words >= size_words:
        raise ValueError("chunk overlap must be smaller than chunk size")

    chunks: list[Chunk] = []
    counter = 0
    step = size_words - overlap_words

    for section in sections:
        words = section.text.split()
        if not words:
            continue
        start = 0
        while start < len(words):
            piece = words[start : start + size_words]
            counter += 1
            chunks.append(
                Chunk(
                    chunk_id=f"c-{counter}",
                    document_id=section.document_id,
                    title=section.title,
                    section=section.section,
                    text=" ".join(piece),
                )
            )
            if start + size_words >= len(words):
                break
            start += step

    return chunks
