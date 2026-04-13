from __future__ import annotations
import pathlib
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Form,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse

from app.services.calendar import CalendarService
from app.services.email import EmailService
from app.services.rate_limit import RateLimiter

router = APIRouter(prefix="/api", tags=["api"])

# ── Constants ────────────────────────────────────────
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_MIME = frozenset({"image/jpeg", "image/png", "image/webp", "image/avif"})
_FALLBACK_DASH = "-"


def _esc(s: str | None) -> str:
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _html(css: str, role: str, body: str) -> HTMLResponse:
    """Tiny helper to avoid repeating notice markup."""
    return HTMLResponse(f'<div class="notice notice--{css}" role="{role}">{body}</div>')


# ── Status pill (HTMX partial) ──────────────────────


@router.get("/status", response_class=HTMLResponse)
async def status_pill() -> HTMLResponse:
    text = await CalendarService.get_status_text()
    return HTMLResponse(
        '<span class="pill__inner">'
        '<span class="pill__dot pill__dot--live" aria-hidden="true">'
        "</span>"
        f'<span class="pill__text">{_esc(text)}</span>'
        "</span>"
    )


# ── Quote form (HTMX POST) ──────────────────────────


@router.post("/offert", response_class=HTMLResponse)
async def offert(
    request: Request,
    background: BackgroundTasks,
    namn: Annotated[str, Form()],
    telefon: Annotated[str, Form()],
    epost: Annotated[str | None, Form()] = None,
    beskrivning: Annotated[str | None, Form()] = None,
    website: Annotated[str | None, Form()] = None,  # honeypot
    bild: UploadFile | None = None,
) -> HTMLResponse:
    ip = request.client.host if request.client else "unknown"

    # ── Rate limit ───────────────────────────────
    if RateLimiter.is_limited(ip):
        return HTMLResponse(
            _html(
                "err",
                "alert",
                "<p><strong>For manga forfragningar.</strong> "
                "Vanta en stund och forsok igen.</p>",
            ).body.decode(),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # ── Honeypot ─────────────────────────────────
    if website:
        return _html(
            "ok",
            "status",
            "<p><strong>Tack!</strong> Din forfragan ar mottagen.</p>",
        )

    # ── Validation ───────────────────────────────
    errors: list[str] = []
    namn_clean = namn.strip()
    telefon_clean = telefon.strip()

    if not namn_clean:
        errors.append("Ange ditt namn.")
    if not telefon_clean:
        errors.append("Ange ditt telefonnummer.")

    # Validate upload before reading into memory
    if bild and bild.filename:
        if bild.content_type not in _ALLOWED_MIME:
            errors.append("Bara bilder (JPEG, PNG, WebP, AVIF).")
        if bild.size and bild.size > _MAX_UPLOAD_BYTES:
            errors.append("Bilden far vara max 10 MB.")

    if errors:
        lis = "".join(f"<li>{e}</li>" for e in errors)
        return HTMLResponse(
            _html(
                "err",
                "alert",
                "<p><strong>Kontrollera:</strong></p>"
                f'<ul class="notice__list">{lis}</ul>',
            ).body.decode(),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # ── Build email ──────────────────────────────
    safe = {
        "namn": _esc(namn_clean),
        "tel": _esc(telefon_clean),
        "epost": _esc(epost) or _FALLBACK_DASH,
        "desc": _esc(beskrivning) or _FALLBACK_DASH,
    }

    subject = f"[Sandladan AB] Ny forfragan fran {safe['namn']}"
    body_html = (
        "<h2>Ny forfragan</h2>"
        f"<p><strong>Namn:</strong> {safe['namn']}</p>"
        f"<p><strong>Tel:</strong> {safe['tel']}</p>"
        f"<p><strong>E-post:</strong> {safe['epost']}</p>"
        f"<p><strong>Beskrivning:</strong><br>{safe['desc']}</p>"
    )
    body_text = (
        f"Namn: {namn_clean}\n"
        f"Tel: {telefon_clean}\n"
        f"E-post: {epost or _FALLBACK_DASH}\n"
        f"Beskrivning:\n{beskrivning or _FALLBACK_DASH}"
    )

    attachments: list[tuple[str, bytes, str]] = []
    if bild and bild.filename:
        data = await bild.read()
        mime = bild.content_type or "application/octet-stream"
        attachments.append((bild.filename, data, mime))

    msg = EmailService.build(subject, body_html, body_text, attachments)
    background.add_task(EmailService.send, msg)

    return _html(
        "ok",
        "status",
        f"<p><strong>Tack {safe['namn']}!</strong></p>"
        f"<p>Vi aterkommer pa {safe['tel']}.</p>",
    )

@router.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@router.get("/debug/static")
async def debug_static():
    import os
    from pathlib import Path

    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    result = {
        "static_dir": str(static_dir),
        "exists": static_dir.exists(),
        "dist_exists": (static_dir / "dist").exists(),
        "files": [],
    }
    if static_dir.exists():
        for root, dirs, files in os.walk(static_dir):
            for f in files:
                full = os.path.join(root, f)
                result["files"].append(
                    {
                        "path": os.path.relpath(full, static_dir),
                        "size": os.path.getsize(full),
                    }
                )
    return result


@router.get("/debug/routes")
async def debug_routes(request: Request):
    routes_info = []
    for route in request.app.routes:
        info = {
            "type": type(route).__name__,
            "path": getattr(route, "path", "N/A"),
        }
        if hasattr(route, "app"):
            info["app_type"] = type(route.app).__name__
            if hasattr(route.app, "directory"):
                info["directory"] = str(route.app.directory)
        if hasattr(route, "name"):
            info["name"] = route.name
        routes_info.append(info)
    return {"routes": routes_info}


@router.get("/debug/serve-css")
async def debug_serve_css():
    from pathlib import Path

    from fastapi.responses import Response

    css_path = (
        Path(__file__).resolve().parent.parent.parent
        / "static"
        / "dist"
        / "styles.css"
    )
    if css_path.exists():
        return Response(
            content=css_path.read_bytes(), media_type="text/css"
        )
    return {"error": "not found", "path": str(css_path)}


@router.get("/debug/dist")
async def debug_dist():
    import os
    from pathlib import Path

    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    dist_dir = static_dir / "dist"

    files = {}
    if dist_dir.exists():
        for f in dist_dir.iterdir():
            files[f.name] = {
                "size": f.stat().st_size,
                "is_file": f.is_file(),
                "is_symlink": f.is_symlink(),
                "readable": os.access(f, os.R_OK),
                "mode": oct(f.stat().st_mode),
            }

    return {
        "dist_dir": str(dist_dir),
        "exists": dist_dir.exists(),
        "is_dir": dist_dir.is_dir(),
        "is_symlink": dist_dir.is_symlink(),
        "parent_is_symlink": static_dir.is_symlink(),
        "files": files,
    }



@router.get("/debug/static-check")
async def debug_static_check():
    import os

    static_dir = str(
        pathlib.Path(__file__).resolve().parent.parent.parent / "static"
    )
    target = os.path.join(static_dir, "dist", "styles.css")

    return {
        "static_dir": static_dir,
        "static_dir_realpath": os.path.realpath(static_dir),
        "static_dir_abspath": os.path.abspath(static_dir),
        "target_exists": os.path.exists(target),
        "target_realpath": os.path.realpath(target),
        "target_abspath": os.path.abspath(target),
        "realpath_starts_with_realpath": os.path.realpath(target).startswith(
            os.path.realpath(static_dir)
        ),
        "abspath_starts_with_abspath": os.path.abspath(target).startswith(
            os.path.abspath(static_dir)
        ),
        "dist_is_symlink": os.path.islink(
            os.path.join(static_dir, "dist")
        ),
        "static_is_symlink": os.path.islink(static_dir),
        "parent_dirs_symlinks": {
            "/opt/render": os.path.islink("/opt/render"),
            "/opt/render/project": os.path.islink("/opt/render/project"),
            "/opt/render/project/src": os.path.islink(
                "/opt/render/project/src"
            ),
        },
        "dist_contents": os.listdir(
            os.path.join(static_dir, "dist")
        )
        if os.path.isdir(os.path.join(static_dir, "dist"))
        else "NOT A DIR",
    }



@router.get("/debug/lookup")
async def debug_lookup(request: Request):
    from starlette.staticfiles import StaticFiles

    for route in request.app.routes:
        if hasattr(route, "app") and isinstance(route.app, StaticFiles):
            static_app = route.app
            path = "dist/styles.css"
            full_path, stat_result = await static_app.lookup_path(path)
            return {
                "lookup_result": {
                    "full_path": full_path,
                    "stat_found": stat_result is not None,
                },
                "instance_info": {
                    "directory": str(static_app.directory),
                    "all_directories": [
                        str(d) for d in static_app.all_directories
                    ],
                    "follow_symlink": static_app.follow_symlink,
                },
                "comparison": {
                    "css_lookup": str(
                        await static_app.lookup_path("css/app.css")
                    ),
                    "dist_lookup": str(
                        await static_app.lookup_path("dist/styles.css")
                    ),
                },
            }
    return {"error": "StaticFiles mount not found"}