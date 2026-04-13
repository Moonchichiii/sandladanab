"""Entry point. Run: uvicorn main:app --reload"""

import sys
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


# ── Debug endpoints (only when DEBUG=true) ───────────
if settings.debug:

    @app.get("/debug/static")
    async def debug_static():
        return {
            "static_dir": str(STATIC_DIR),
            "exists": STATIC_DIR.exists(),
            "files": [
                str(p.relative_to(STATIC_DIR))
                for p in STATIC_DIR.rglob("*")
                if p.is_file()
            ],
        }

    @app.get("/debug/routes")
    async def debug_routes():
        return [
            {
                "path": route.path,
                "name": route.name,
                "methods": getattr(route, "methods", None),
            }
            for route in app.routes
        ]

    print(f"🔍 STATIC_DIR: {STATIC_DIR}", file=sys.stderr)
    print("✅ Debug endpoints enabled at /debug/static and /debug/routes", file=sys.stderr)