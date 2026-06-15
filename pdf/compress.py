"""In-memory PDF compression."""

from __future__ import annotations

import fitz

CompressionLevel = str  # "light" | "medium" | "strong"


def compress_pdf(data: bytes, level: CompressionLevel = "medium") -> bytes:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        if level in ("medium", "strong"):
            try:
                if level == "medium":
                    doc.rewrite_images(dpi_threshold=150, dpi_target=120, quality=75)
                else:
                    doc.rewrite_images(dpi_threshold=120, dpi_target=96, quality=55)
            except Exception:
                # Image recompression is best-effort; fall back to structural
                # compression only if it fails on an unusual image.
                pass

        return doc.tobytes(garbage=4, deflate=True, clean=True)
    finally:
        doc.close()
