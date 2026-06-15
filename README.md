# PDF Merge

A small, private web app to **merge** and **compress** PDFs.

- Upload several PDFs, set the order, merge into one file, download.
- Every page is auto-scaled to the **largest page size** in the upload, so nothing
  ends up thin or tiny when files of different sizes are combined.
- **Nothing is stored.** Files are processed in memory and discarded when the
  request finishes. There is no database and no disk writes.

## Project layout

```
merge/
├── api/index.py     FastAPI app + Jinja2 templates (Vercel entrypoint)
├── pdf/
│   ├── merge.py     merge + full-screen page normalization
│   ├── compress.py  image/structure compression
│   └── service.py   merge → compress pipeline
├── templates/       server-rendered HTML (no JavaScript)
├── static/          CSS
├── requirements.txt
└── vercel.json
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn api.index:app --reload
```

Then open http://127.0.0.1:8000

## Deploy to Vercel

```bash
npm i -g vercel
vercel login
vercel          # preview deploy
vercel --prod   # production deploy
```

Or push to GitHub and import the repo at https://vercel.com/new.

## Notes

- **Upload limit: ~4 MB total.** Vercel caps the request body at ~4.5 MB, so this
  app is sized for normal documents and scanned pages, not very large photo PDFs.
  For bigger files, host the same FastAPI app on a platform without that limit
  (e.g. Render, Railway, Fly.io) — no code changes needed.
- Compression levels: **light** (lossless cleanup), **medium** (balanced),
  **strong** (smallest, more aggressive image downscaling).
