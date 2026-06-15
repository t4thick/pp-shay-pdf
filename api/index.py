"""FastAPI app for Vercel — merge & compress PDFs in memory only.

The frontend in ``web/`` is served by this same app so the project behaves
identically when run locally (``uvicorn api.index:app``) and on Vercel.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pdf.service import process_pdfs

app = FastAPI(title="PDF Merge", docs_url=None, redoc_url=None)

# Keep this under Vercel's ~4.5 MB request body limit so uploads fail
# gracefully in the browser instead of being cut off by the platform.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
VALID_COMPRESSION = {"light", "medium", "strong"}


def _sanitize_filename(name: str) -> str:
    name = (name or "").strip() or "merged.pdf"
    # Strip any path components and characters unsafe for a header value.
    name = re.sub(r"[\\/\r\n\"]+", "", name)
    name = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    if not name:
        name = "merged.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/merge")
async def merge_endpoint(
    files: list[UploadFile] = File(...),
    compression: str = Form("medium"),
    filename: str = Form("merged.pdf"),
) -> Response:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one PDF.")

    if compression not in VALID_COMPRESSION:
        raise HTTPException(status_code=400, detail="Invalid compression level.")

    sources: list[bytes] = []
    total_size = 0

    try:
        for upload in files:
            if not upload.filename or not upload.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

            data = await upload.read()
            await upload.close()
            total_size += len(data)

            if total_size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Total upload exceeds 4 MB. Please use smaller PDFs.",
                )

            sources.append(data)

        try:
            result, page_count = process_pdfs(sources, compression=compression)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail="Could not process the PDFs.") from exc
    finally:
        # Drop the uploaded bytes from memory as soon as we are done.
        sources.clear()

    safe_name = _sanitize_filename(filename)

    return Response(
        content=result,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Page-Count": str(page_count),
            "Cache-Control": "no-store",
        },
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", media_type="text/html")


@app.get("/styles.css")
def styles() -> FileResponse:
    return FileResponse(WEB_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
def script() -> FileResponse:
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)
