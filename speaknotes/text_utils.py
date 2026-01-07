from __future__ import annotations


def split_into_paragraphs(text: str) -> list[str]:
    """
    Splits text into paragraph chunks using blank lines as separators.
    Empty chunks are removed.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = [chunk.strip() for chunk in normalized.split("\n\n") if chunk.strip()]
    return chunks
