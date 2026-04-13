from __future__ import annotations

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
_ALLOWED_MIME = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/avif"}
)
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
    return HTMLResponse(
        f'<div class="notice notice--{css}" role="{role}">{body}</div>'
    )


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
    website: Annotated[str | None, Form()] = None,
    bild: UploadFile | None = None,
) -> HTMLResponse:
    ip = request.client.host if request.client else "unknown"

    # ── Rate limit ───────────────────────────────
    if RateLimiter.is_limited(ip):
        return HTMLResponse(
            _html(
                "err",
                "alert",
                "<p><strong>För många förfrågningar.</strong> "
                "Vänta en stund och försök igen.</p>",
            ).body.decode(),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # ── Honeypot ─────────────────────────────────
    if website:
        return _html(
            "ok",
            "status",
            "<p><strong>Tack!</strong> Din förfrågan är mottagen.</p>",
        )

    # ── Validation ───────────────────────────────
    errors: list[str] = []
    namn_clean = namn.strip()
    telefon_clean = telefon.strip()

    if not namn_clean:
        errors.append("Ange ditt namn.")
    if not telefon_clean:
        errors.append("Ange ditt telefonnummer.")

    if bild and bild.filename:
        if bild.content_type not in _ALLOWED_MIME:
            errors.append("Bara bilder (JPEG, PNG, WebP, AVIF).")
        if bild.size and bild.size > _MAX_UPLOAD_BYTES:
            errors.append("Bilden får vara max 10 MB.")

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

    subject = f"[Sandladan AB] Ny förfrågan från {safe['namn']}"
    body_html = (
        "<h2>Ny förfrågan</h2>"
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
        f"<p>Vi återkommer på {safe['tel']}.</p>",
    )


@router.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}