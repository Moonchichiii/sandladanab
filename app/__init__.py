from __future__ import annotations

from fastapi import FastAPI

from app.middleware import register_middleware
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)
    register_middleware(app)
    app.include_router(pages_router)
    app.include_router(api_router)
    return app