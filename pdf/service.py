"""Merge + compress pipeline. Everything stays in memory."""

from __future__ import annotations

from pdf.compress import compress_pdf
from pdf.merge import merge_pdfs


def process_pdfs(sources: list[bytes], compression: str = "medium") -> tuple[bytes, int]:
    merged, page_count = merge_pdfs(sources)
    compressed = compress_pdf(merged, level=compression)
    return compressed, page_count
