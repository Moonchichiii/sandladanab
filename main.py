"""Entry point. Run: uvicorn main:app --reload"""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from app import create_app
from app.config import settings

app = create_app()

# ── Static files ─────────────────────────────────────
STATIC_DIR = Path(__file__).resolve().parent / "static"

if not STATIC_DIR.exists():
    raise RuntimeError(f"Static directory not found: {STATIC_DIR}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
