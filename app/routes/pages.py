from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import time
from functools import lru_cache

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.content import (
    ABOUT_IMAGE,
    ABOUT_SIZES,
    COPY,
    GALLERY_ITEMS,
    GALLERY_SIZES,
    HERO_IMAGE,
    HERO_SIZES,
    NAV_LINKS,
    PRIVACY_UPDATED,
    SERVICES,
)
from app.services import form_token

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
DIST_DIR = BASE_DIR / "static" / "dist"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@lru_cache(maxsize=8)
def _dist_asset(name: str) -> dict[str, str]:
    """URL + Subresource Integrity for a built file in static/dist.

    The hash doubles as a cache-buster (?v=) so the immutable Cache-Control on
    /dist never serves a stale build. Cached for the process lifetime in
    production; in debug (css:watch) the hash is skipped so a rebuilt file is
    never blocked by a stale integrity value."""
    path = DIST_DIR / name
    if settings.debug or not path.is_file():
        return {"url": f"/dist/{name}", "integrity": ""}
    digest = hashlib.sha384(path.read_bytes())
    b64 = base64.b64encode(digest.digest()).decode()
    version = digest.hexdigest()[:12]  # URL-safe cache-buster
    return {"url": f"/dist/{name}?v={version}", "integrity": f"sha384-{b64}"}


def _csp_nonce(request: Request) -> str:
    return getattr(request.state, "csp_nonce", "")


templates.env.globals.update(
    BASE_URL=settings.base_url,
    csp_nonce=_csp_nonce,
)

router = APIRouter()


def _base_url(request: Request) -> str:
    return (settings.base_url or f"{request.url.scheme}://{request.url.netloc}").rstrip(
        "/"
    )


def _facts() -> list[dict]:
    """Company facts for the About list. Rows without a value are left out —
    never a placeholder in production."""
    rows: list[dict] = [{"label": "Företag", "value": "Sandlådan AB"}]
    if settings.org_number:
        rows.append({"label": "Org.nr", "value": settings.org_number})
    rows.append({"label": "Säte", "value": settings.seat})
    rows.append({"label": "Arbetsområde", "value": "Göteborg med omnejd · västkusten"})
    if settings.owner_name:
        who = settings.owner_name
        if settings.owner_title:
            who = f"{who}, {settings.owner_title}"
        rows.append({"label": "Ansvarig", "value": who})
    if settings.phone_public:
        rows.append(
            {
                "label": "Telefon",
                "value": settings.phone_display,
                "href": f"tel:{settings.owner_phone}",
            }
        )
    if settings.linkedin_url:
        rows.append(
            {
                "label": "LinkedIn",
                "value": "Sandlådan AB på LinkedIn",
                "href": settings.linkedin_url,
                "external": True,
            }
        )
    return rows


def _base_context(request: Request, path: str = "/") -> dict:
    """Shared template context for all pages."""
    return {
        "request": request,
        "current_year": time.gmtime().tm_year,
        "canonical_url": _base_url(request) + path,
        "show_phone": settings.phone_public,
        "owner_phone": settings.owner_phone,
        "owner_phone_display": settings.phone_display,
        "org_number": settings.org_number,
        "seat": settings.seat,
        "postal_address": settings.postal_address,
        "linkedin_url": settings.linkedin_url,
        "nav_links": NAV_LINKS,
        "copy": COPY,
        "schema_json": "",
        "css": _dist_asset("styles.css"),
        "js": _dist_asset("site.js"),
        "og_image": _base_url(request) + "/static/assets/brand/og-image.jpg",
    }


def _build_schema(base: str) -> str:
    """schema.org for the homepage.

    Same facts as the About list; no e-mail (decision 2026-09-21)."""
    data: dict = {
        "@context": "https://schema.org",
        "@type": ["GeneralContractor", "LocalBusiness"],
        "name": "Sandlådan AB",
        "legalName": "Sandlådan AB",
        "url": base,
        "image": f"{base}/static/assets/images/{HERO_IMAGE['file']}-1280.webp",
        "logo": f"{base}/static/assets/brand/icon-512.png",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": settings.seat,
            "addressRegion": "Västra Götaland",
            "addressCountry": "SE",
        },
        "areaServed": "Göteborg med omnejd",
        "priceRange": "$$",
        "openingHoursSpecification": {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "opens": "07:00",
            "closes": "16:00",
        },
    }
    if settings.phone_public:
        data["telephone"] = settings.owner_phone
    if settings.org_number:
        data["identifier"] = settings.org_number
    if settings.postal_address:
        data["address"]["streetAddress"] = settings.postal_address
    if settings.owner_name:
        founder: dict = {"@type": "Person", "name": settings.owner_name}
        if settings.owner_title:
            founder["jobTitle"] = settings.owner_title
        data["founder"] = founder
    if settings.linkedin_url:
        data["sameAs"] = [settings.linkedin_url]
    return json.dumps(data, ensure_ascii=False)


@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def index(request: Request):
    if settings.maintenance_mode:
        return templates.TemplateResponse(
            request=request, name="maintenance.html", context={"request": request}
        )

    ctx = {
        **_base_context(request, "/"),
        "schema_json": _build_schema(_base_url(request)),
        "services": SERVICES,
        "hero_image": HERO_IMAGE,
        "hero_sizes": HERO_SIZES,
        "gallery_items": GALLERY_ITEMS,
        "gallery_sizes": GALLERY_SIZES,
        "about_image": ABOUT_IMAGE,
        "about_sizes": ABOUT_SIZES,
        "facts": _facts(),
        "form_token": form_token.mint(),
        "lediga_text": settings.lediga_text,
        "status_url": (
            "/api/status"
            if settings.calendar_mode == "ics" and settings.calendar_ics_url
            else ""
        ),
    }
    return templates.TemplateResponse(request=request, name="index.html", context=ctx)


@router.api_route("/integritet", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def integritet(request: Request):
    ctx = {
        **_base_context(request, "/integritet"),
        "privacy_updated": PRIVACY_UPDATED,
    }
    return templates.TemplateResponse(
        request=request, name="integritet.html", context=ctx
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
