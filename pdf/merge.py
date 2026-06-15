"""Merge PDFs and normalize every page to the same full-screen size."""

from __future__ import annotations

import fitz


def _cover_rect(src: fitz.Rect, dst: fitz.Rect) -> fitz.Rect:
    """Scale source page to cover the destination without letterboxing."""
    scale = max(dst.width / src.width, dst.height / src.height)
    w = src.width * scale
    h = src.height * scale
    x0 = dst.x0 + (dst.width - w) / 2
    y0 = dst.y0 + (dst.height - h) / 2
    return fitz.Rect(x0, y0, x0 + w, y0 + h)


def _largest_page_size(docs: list[fitz.Document]) -> tuple[float, float]:
    width = 0.0
    height = 0.0
    for doc in docs:
        for page in doc:
            width = max(width, page.rect.width)
            height = max(height, page.rect.height)
    return width, height


def _add_normalized_page(
    out: fitz.Document,
    src_doc: fitz.Document,
    page_no: int,
    target_w: float,
    target_h: float,
) -> None:
    src_page = src_doc[page_no]
    target = fitz.Rect(0, 0, target_w, target_h)
    new_page = out.new_page(width=target_w, height=target_h)
    place = _cover_rect(src_page.rect, target)
    new_page.show_pdf_page(place, src_doc, page_no)


def merge_pdfs(sources: list[bytes]) -> tuple[bytes, int]:
    """
    Merge PDF byte streams in order.

    All pages are auto-scaled to the largest page size found across every
    uploaded file so nothing ends up thin or tiny after merging.
    """
    if not sources:
        raise ValueError("Upload at least one PDF.")

    opened: list[fitz.Document] = []
    try:
        for data in sources:
            try:
                doc = fitz.open(stream=data, filetype="pdf")
            except Exception as exc:  # noqa: BLE001
                raise ValueError("One of the files is not a valid PDF.") from exc

            if doc.needs_pass:
                doc.close()
                raise ValueError("A password-protected PDF can't be merged. Remove the password first.")

            opened.append(doc)

        total_pages = sum(doc.page_count for doc in opened)
        if total_pages == 0:
            raise ValueError("The uploaded PDFs have no pages.")

        out = fitz.open()
        target_w, target_h = _largest_page_size(opened)

        for doc in opened:
            for page_no in range(doc.page_count):
                _add_normalized_page(out, doc, page_no, target_w, target_h)

        page_count = out.page_count
        result = out.tobytes(garbage=4, deflate=True)
        out.close()
        return result, page_count
    finally:
        for doc in opened:
            doc.close()
