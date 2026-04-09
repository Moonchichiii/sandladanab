from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse

from app.services.calendar import CalendarService
from app.services.email import EmailService
from app.services.rate_limit import RateLimiter

router = APIRouter()


def _esc(s: str | None) -> str:
    if not s:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── Status pill (HTMX partial) ──────────────────────


@router.get("/status", response_class=HTMLResponse)
async def status_pill():
    text = await CalendarService.get_status_text()
    return HTMLResponse(
        '<span class="pill__inner">'
        '<span class="pill__dot pill__dot--live" aria-hidden="true"></span>'
        f'<span class="pill__text">{_esc(text)}</span>'
        "</span>"
    )


# ── Quote form (HTMX POST) ──────────────────────────


@router.post("/offert", response_class=HTMLResponse)
async def offert(
    request: Request,
    background: BackgroundTasks,
    namn: str = Form(...),
    telefon: str = Form(...),
    epost: str | None = Form(None),
    beskrivning: str | None = Form(None),
    website: str | None = Form(None),  # honeypot
    bild: UploadFile | None = File(None),
):
    ip = request.client.host if request.client else "unknown"

    if RateLimiter.is_limited(ip):
        return HTMLResponse(
            '<div class="notice notice--err" role="alert">'
            "<p><strong>För många förfrågningar.</strong> "
            "Vänta en stund och försök igen.</p></div>",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Honeypot filled → fake success
    if website:
        return HTMLResponse(
            '<div class="notice notice--ok" role="status">'
            "<p><strong>Tack!</strong> Din förfrågan är mottagen.</p>"
            "</div>"
        )

    # Validation
    errors: list[str] = []
    if not namn.strip():
        errors.append("Ange ditt namn.")
    if not telefon.strip():
        errors.append("Ange ditt telefonnummer.")
    if errors:
        lis = "".join(f"<li>{e}</li>" for e in errors)
        return HTMLResponse(
            '<div class="notice notice--err" role="alert">'
            "<p><strong>Kontrollera:</strong></p>"
            f'<ul class="notice__list">{lis}</ul></div>',
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Build & queue email
    safe_namn = _esc(namn)
    safe_tel = _esc(telefon)
    safe_epost = _esc(epost) or "–"
    safe_desc = _esc(beskrivning) or "–"

    subject = f"[Sandlådan AB] Ny förfrågan från {safe_namn}"
    body_html = (
        f"<h2>Ny förfrågan</h2>"
        f"<p><strong>Namn:</strong> {safe_namn}</p>"
        f"<p><strong>Tel:</strong> {safe_tel}</p>"
        f"<p><strong>E-post:</strong> {safe_epost}</p>"
        f"<p><strong>Beskrivning:</strong><br>{safe_desc}</p>"
    )
    body_text = (
        f"Namn: {namn}\n"
        f"Tel: {telefon}\n"
        f"E-post: {epost or '–'}\n"
        f"Beskrivning:\n{beskrivning or '–'}"
    )

    attachments: list[tuple[str, bytes, str]] = []
    if bild and bild.filename:
        data = await bild.read()
        mime = bild.content_type or "application/octet-stream"
        attachments.append((bild.filename, data, mime))

    msg = EmailService.build(subject, body_html, body_text, attachments)
    background.add_task(EmailService.send, msg)

    return HTMLResponse(
        '<div class="notice notice--ok" role="status">'
        f"<p><strong>Tack {safe_namn}!</strong></p>"
        f"<p>Vi återkommer på {safe_tel}.</p></div>"
    )
