"""Entry point. Run: uvicorn main:app --reload"""

from pathlib import Path

from fastapi import Response
from fastapi.staticfiles import StaticFiles

from app import create_app

app = create_app()

# ── Static files ─────────────────────────────────────
STATIC_DIR = Path(__file__).resolve().parent / "static"
DIST_DIR = STATIC_DIR / "dist"

if not STATIC_DIR.exists():
    raise RuntimeError(f"Static directory not found: {STATIC_DIR}")

_CACHE_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable"}

_MIME_MAP = {
    ".css": "text/css",
    ".js": "application/javascript",
}


# ── Workaround: Starlette StaticFiles silently 404s on
#    files created during Render's build step.
#    Explicit routes are matched before mounts.
@app.get("/static/dist/{filename:path}")
async def serve_dist(filename: str):
    filepath = DIST_DIR / filename
    if not filepath.is_file():
        return Response(status_code=404)

    suffix = filepath.suffix.lower()
    media_type = _MIME_MAP.get(suffix, "application/octet-stream")

    return Response(
        content=filepath.read_bytes(),
        media_type=media_type,
        headers=_CACHE_HEADERS,
    )


# ── StaticFiles for everything else (git-committed) ─
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR, follow_symlink=True),
    name="static",
)