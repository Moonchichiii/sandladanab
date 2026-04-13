# main.py
"""Entry point. Run: uvicorn main:app --reload"""

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app import create_app

# Create app
app = create_app()

# Mount static files
STATIC_DIR = Path(__file__).resolve().parent / "static"

if not STATIC_DIR.exists():
    raise RuntimeError(f"Static directory not found: {STATIC_DIR}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
