"""Entry point. Run: uvicorn main:app --reload"""

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app import create_app

app = create_app()

# Mount static files for Render
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
