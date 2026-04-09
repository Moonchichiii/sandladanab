from __future__ import annotations

from fastapi import FastAPI

from app.routes.api import router as api_router
from app.routes.pages import router as pages_router


def register_routes(app: FastAPI) -> None:
    app.include_router(pages_router)
    app.include_router(api_router)
