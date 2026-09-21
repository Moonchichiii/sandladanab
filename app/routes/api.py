from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Form,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse

from app.services.calendar import CalendarService
from app.services.email import EmailService
from app.services.rate_limit import RateLimiter

router = APIRouter(prefix="/api", tags=["api"])

# ── Constants ────────────────────────────────────────
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_TEXT = {"namn": 120, "telefon": 40, "beskrivning": 4000}
_FALLBACK_DASH = "-"
_NO_STORE = {"Cache-Control": "no-store"}


def _esc(s: str | None) -> str:
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _html(css: str, role: str, body: str, code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f'<div class="notice notice--{css}" role="{role}">{body}</div>',
        status_code=code,
        headers=_NO_STORE,
    )


def _sniff_image(data: bytes) -> str | None:
    """Return the file extension for a real JPEG/PNG/WebP/AVIF payload, else None.
    The browser's Content-Type header is not trusted — the bytes are checked."""
    head = data[:32]
    if head[:3] == b"\xff\xd8\xff":
        return "jpg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[4:8] == b"ftyp" and (b"avif" in head or b"avis" in head):
        return "avif"
    return None


# ── Status line (fetched by site.js) ────────────────


@router.get("/status", response_class=HTMLResponse)
async def status_line() -> HTMLResponse:
    text = await CalendarService.get_status_text()
    return HTMLResponse(
        '<span class="status__dot status__dot--live" aria-hidden="true"></span>'
        f"<span>{_esc(text)}</span>",
        headers=_NO_STORE,
    )


# ── Quote form (fetch POST or plain form POST) ──────


@router.post("/offert", response_class=HTMLResponse)
async def offert(
    request: Request,
    background: BackgroundTasks,
    namn: Annotated[str, Form()],
    telefon: Annotated[str, Form()],
    beskrivning: Annotated[str | None, Form()] = None,
    website: Annotated[str | None, Form()] = None,
    bild: UploadFile | None = None,
) -> HTMLResponse:
    ip = request.client.host if request.client else "unknown"

    # ── Rate limit (IP is used for the window only, never stored with the data) ──
    if RateLimiter.is_limited(ip):
        return _html(
            "err",
            "alert",
            "<p><strong>För många förfrågningar.</strong> "
            "Vänta en stund och försök igen.</p>",
            429,
        )

    # ── Honeypot ─────────────────────────────────
    if website:
        return _html(
            "ok", "status", "<p><strong>Tack!</strong> Din förfrågan är mottagen.</p>"
        )

    # ── Validation ───────────────────────────────
    errors: list[str] = []
    namn_clean = namn.strip()[: _MAX_TEXT["namn"]]
    telefon_clean = telefon.strip()[: _MAX_TEXT["telefon"]]
    beskrivning_clean = (beskrivning or "").strip()[: _MAX_TEXT["beskrivning"]]

    if not namn_clean:
        errors.append("Ange ditt namn.")
    if not telefon_clean:
        errors.append("Ange ditt telefonnummer.")

    attachments: list[tuple[str, bytes, str]] = []
    if bild and bild.filename:
        data = await bild.read(_MAX_UPLOAD_BYTES + 1)
        if len(data) > _MAX_UPLOAD_BYTES:
            errors.append("Bilden får vara max 10 MB.")
        else:
            ext = _sniff_image(data)
            if ext is None:
                errors.append("Bara bilder (JPEG, PNG, WebP, AVIF).")
            else:
                mime = {
                    "jpg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                    "avif": "image/avif",
                }[ext]
                attachments.append(
                    (f"bild.{ext}", data, mime)
                )  # original filename is not forwarded

    if errors:
        lis = "".join(f"<li>{e}</li>" for e in errors)
        return _html(
            "err",
            "alert",
            f'<p><strong>Kontrollera:</strong></p><ul class="notice__list">{lis}</ul>',
            422,
        )

    # ── Build email ──────────────────────────────
    safe = {
        "namn": _esc(namn_clean),
        "tel": _esc(telefon_clean),
        "desc": _esc(beskrivning_clean) or _FALLBACK_DASH,
    }

    subject = f"[Sandladan AB] Ny förfrågan från {namn_clean}"
    body_html = (
        "<h2>Ny förfrågan</h2>"
        f"<p><strong>Namn:</strong> {safe['namn']}</p>"
        f"<p><strong>Tel:</strong> {safe['tel']}</p>"
        "<p><strong>Beskrivning:</strong><br>"
        f"{safe['desc'].replace(chr(10), '<br>')}</p>"
    )
    body_text = (
        f"Namn: {namn_clean}\n"
        f"Tel: {telefon_clean}\n"
        f"Beskrivning:\n{beskrivning_clean or _FALLBACK_DASH}"
    )

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
    return {"status": "ok", "version": "2.0.0"}
