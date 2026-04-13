from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

from app.middleware import register_middleware
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
DIST_DIR = STATIC_DIR / "dist"

_CACHE = {"Cache-Control": "public, max-age=31536000, immutable"}
_MIME = {".css": "text/css", ".js": "application/javascript"}


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)
    register_middleware(app)

    # ── Explicit dist route FIRST ────────────────
    @app.get("/static/dist/{filename:path}")
    async def serve_dist(filename: str):
        filepath = DIST_DIR / filename
        if not filepath.is_file():
            return Response("Not found", status_code=404)
        media = _MIME.get(filepath.suffix.lower(), "application/octet-stream")
        return Response(
            content=filepath.read_bytes(),
            media_type=media,
            headers=_CACHE,
        )

    # ── Page and API routers ─────────────────────
    app.include_router(pages_router)
    app.include_router(api_router)

    # ── StaticFiles mount LAST ───────────────────
    if not STATIC_DIR.exists():
        raise RuntimeError(f"Static dir not found: {STATIC_DIR}")

    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR, follow_symlink=True),
        name="static",
    )

    return app