from __future__ import annotations

import mimetypes
import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.middleware import register_middleware
from app.routes import register_routes

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent


def _register_mimetypes() -> None:
    """Ensure correct MIME types on all platforms."""
    for ext, mime in {
        ".js": "text/javascript",
        ".woff2": "font/woff2",
        ".webp": "image/webp",
        ".avif": "image/avif",
        ".svg": "image/svg+xml",
    }.items():
        mimetypes.add_type(mime, ext)


def create_app() -> FastAPI:
    _register_mimetypes()

    app = FastAPI(
        title="Sandlådan AB",
        docs_url=None,
        redoc_url=None,
        openapi_url=None if not settings.debug else "/openapi.json",
    )

    app.mount(
        "/static",
        StaticFiles(directory=str(BASE_DIR / "static")),
        name="static",
    )

    register_middleware(app)
    register_routes(app)

    return app
