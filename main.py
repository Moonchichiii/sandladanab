"""Entry point. Run: uvicorn main:app --reload"""

import sys
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app import create_app

# Create app
app = create_app()

# Mount static files with absolute path
STATIC_DIR = Path(__file__).resolve().parent / "static"
print(f"🔍 STATIC_DIR resolved to: {STATIC_DIR}", file=sys.stderr)
print(f"🔍 STATIC_DIR exists: {STATIC_DIR.exists()}", file=sys.stderr)

if not STATIC_DIR.exists():
    raise RuntimeError(f"❌ Static directory not found: {STATIC_DIR}")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
print("✅ Static files mounted successfully", file=sys.stderr)

# Debug endpoint to verify filesystem
@app.get("/debug/static")
async def debug_static():
    return {
        "static_dir": str(STATIC_DIR),
        "exists": STATIC_DIR.exists(),
        "files": [str(p.relative_to(STATIC_DIR)) for p in STATIC_DIR.rglob("*") if p.is_file()]
    }

# Debug endpoint to check routes
@app.get("/debug/routes")
async def debug_routes():
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": getattr(route, "methods", None)
        })
    return routes