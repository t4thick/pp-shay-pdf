"""FastAPI app for Vercel — merge & compress PDFs in memory only.

The UI is server-rendered with Jinja2 templates. No JavaScript required.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pdf.service import process_pdfs

app = FastAPI(title="PDF Merge", docs_url=None, redoc_url=None)

templates = Jinja2Templates(directory=ROOT / "templates")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

MAX_UPLOAD_BYTES = 4 * 1024 * 1024
VALID_COMPRESSION = {"light", "medium", "strong"}


def _sanitize_filename(name: str) -> str:
    name = (name or "").strip() or "merged.pdf"
    name = re.sub(r"[\\/\r\n\"]+", "", name)
    name = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    if not name:
        name = "merged.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name


async def _process_uploads(
    files: list[UploadFile],
    compression: str,
) -> tuple[bytes, int]:
    if not files:
        raise ValueError("Upload at least one PDF.")

    if compression not in VALID_COMPRESSION:
        raise ValueError("Invalid compression level.")

    sources: list[bytes] = []
    total_size = 0

    try:
        for upload in files:
            if not upload.filename or not upload.filename.lower().endswith(".pdf"):
                raise ValueError("Only PDF files are allowed.")

            data = await upload.read()
            await upload.close()
            total_size += len(data)

            if total_size > MAX_UPLOAD_BYTES:
                raise ValueError("Total upload exceeds 4 MB. Please use smaller PDFs.")

            sources.append(data)

        return process_pdfs(sources, compression=compression)
    finally:
        sources.clear()


def _form_context(
    request: Request,
    *,
    error: str | None = None,
    compression: str = "medium",
    filename: str = "merged.pdf",
) -> dict:
    return {
        "request": request,
        "error": error,
        "compression": compression,
        "filename": filename,
        "compression_options": [
            ("light", "Light — best quality"),
            ("medium", "Medium — balanced"),
            ("strong", "Strong — smallest file"),
        ],
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index(request: Request) -> object:
    return templates.TemplateResponse(
        request,
        "index.html",
        _form_context(request),
    )


@app.post("/merge")
async def merge_form(
    request: Request,
    files: list[UploadFile] = File(...),
    compression: str = Form("medium"),
    filename: str = Form("merged.pdf"),
) -> object:
    try:
        result, page_count = await _process_uploads(files, compression)
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
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "index.html",
            _form_context(request, error=str(exc), compression=compression, filename=filename),
            status_code=400,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Could not process the PDFs.") from exc


@app.post("/api/merge")
async def merge_api(
    files: list[UploadFile] = File(...),
    compression: str = Form("medium"),
    filename: str = Form("merged.pdf"),
) -> Response:
    try:
        result, page_count = await _process_uploads(files, compression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Could not process the PDFs.") from exc

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


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)
