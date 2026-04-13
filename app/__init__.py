from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

from app.middleware import register_middleware
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router

logger = logging.getLogger("sandladan")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
DIST_DIR = STATIC_DIR / "dist"

_CACHE = {"Cache-Control": "public, max-age=31536000, immutable"}
_MIME = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".map": "application/json",
}


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)
    register_middleware(app)

    # ── Dist on /dist/ — OUTSIDE the /static/ mount ──
    @app.get("/dist/{filename:path}")
    async def serve_dist(filename: str) -> Response:
        filepath = (DIST_DIR / filename).resolve()
        if not str(filepath).startswith(str(DIST_DIR.resolve())):
            return Response("Forbidden", status_code=403)
        if not filepath.is_file():
            logger.error(
                "serve_dist 404: %s exists=%s dir=%s",
                filepath,
                filepath.exists(),
                list(DIST_DIR.iterdir()) if DIST_DIR.is_dir() else "NO DIR",
            )
            return Response("Not found", status_code=404)
        media = _MIME.get(
            filepath.suffix.lower(), "application/octet-stream"
        )
        return Response(
            content=filepath.read_bytes(),
            media_type=media,
            headers=_CACHE,
        )

    # ── Routers ──────────────────────────────────
    app.include_router(pages_router)
    app.include_router(api_router)

    # ── StaticFiles for everything else ──────────
    if not STATIC_DIR.exists():
        raise RuntimeError(f"Static dir not found: {STATIC_DIR}")

    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR, follow_symlink=True),
        name="static",
    )

    return app