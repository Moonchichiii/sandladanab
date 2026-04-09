from __future__ import annotations

import json
import pathlib
import time

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.content import GALLERY_ITEMS, NAV_LINKS, SERVICES

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _csp_nonce(request: Request) -> str:
    return getattr(request.state, "csp_nonce", "")


templates.env.globals.update(
    BASE_URL=settings.base_url,
    csp_nonce=_csp_nonce,
)

router = APIRouter()


def _base_context(request: Request) -> dict:
    """Shared template context for all pages."""
    return {
        "request": request,
        "current_year": time.gmtime().tm_year,
        "owner_phone": settings.owner_phone,
        "public_email": settings.public_email,
        "nav_links": NAV_LINKS,
    }


def _build_schema(base: str) -> str:
    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "GeneralContractor",
            "name": "Sandlådan AB",
            "image": (f"{base}/static/assets/images/hero-excavator-1280.webp"),
            "url": base,
            "telephone": settings.owner_phone,
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Göteborg",
                "addressRegion": "Västra Götaland",
                "addressCountry": "SE",
            },
            "priceRange": "$$",
            "openingHoursSpecification": {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                ],
                "opens": "07:00",
                "closes": "16:00",
            },
        },
        ensure_ascii=False,
    )


@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def index(request: Request):
    base = (settings.base_url or f"{request.url.scheme}://{request.url.netloc}").rstrip(
        "/"
    )

    ctx = {
        **_base_context(request),
        "schema_json": _build_schema(base),
        "services": SERVICES,
        "gallery_items": GALLERY_ITEMS,
    }

    template = "maintenance.html" if settings.maintenance_mode else "index.html"

    # Starlette 1.0+ API: request first, then name, then context
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=ctx,
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return PlainTextResponse("User-agent: *\nAllow: /\n")


@router.get("/site.webmanifest")
async def manifest():
    return FileResponse(
        str(BASE_DIR / "static" / "site.webmanifest"),
        media_type="application/manifest+json",
    )
