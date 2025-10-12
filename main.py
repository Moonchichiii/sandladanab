from __future__ import annotations
from starlette.middleware.gzip import GZipMiddleware
from fastapi import FastAPI, Request, Form, UploadFile, File, status, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from typing import Optional
import os
import time
import pathlib
import smtplib
import ssl
from email.message import EmailMessage

# NEW: calendar / time deps
import httpx
from icalendar import Calendar
from dateutil import tz
from datetime import datetime, timedelta

# --------------------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------------------
app = FastAPI(title="Sandlådan AB")

BASE_DIR = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# --------------------------------------------------------------------------------------
# Env & security config
# --------------------------------------------------------------------------------------
# Domains
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]
BASE_URL = os.getenv("BASE_URL", "").strip()

# CORS (only needed if you call the API from another origin; otherwise keep tight)
CORS_ORIGINS = [BASE_URL] if BASE_URL else ["http://localhost", "http://127.0.0.1"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Trusted hosts (protect Host header)
if ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# Security headers (HSTS toggle via env)
HSTS_ENABLE = os.getenv("HSTS_ENABLE", "false").lower() == "true"
SEC_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "upgrade-insecure-requests"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}
if HSTS_ENABLE:
    SEC_HEADERS["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    resp: Response = await call_next(request)
    for k, v in SEC_HEADERS.items():
        # don't overwrite if already set
        if k not in resp.headers:
            resp.headers[k] = v
    return resp


# --------------------------------------------------------------------------------------
# SMTP / mail
# --------------------------------------------------------------------------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_STARTTLS = os.environ.get("SMTP_STARTTLS", "true").lower() == "true"
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER or "no-reply@sandladan.se")
MAIL_TO = os.environ.get("MAIL_TO", "")
OWNER_PHONE = os.environ.get("OWNER_PHONE", "+46XXXXXXXX")

# Rate limit
RATE_BUCKET: dict[str, list[float]] = {}
RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))
RATE_MAX = int(os.getenv("RATE_MAX", "5"))


def too_many_requests(ip: str) -> bool:
    now = time.time()
    bucket = RATE_BUCKET.setdefault(ip, [])
    RATE_BUCKET[ip] = [t for t in bucket if now - t < RATE_WINDOW]
    if len(RATE_BUCKET[ip]) >= RATE_MAX:
        return True
    RATE_BUCKET[ip].append(now)
    return False


def build_email(
    subject: str,
    body_html: str,
    body_text: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")
    for filename, data, mime in attachments or []:
        maintype, _, subtype = mime.partition("/")
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
    return msg


def send_email_message(msg: EmailMessage):
    if not (SMTP_HOST and SMTP_PORT and MAIL_TO and MAIL_FROM):
        return
    if SMTP_PORT == 465 and not SMTP_STARTTLS:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            if SMTP_USER and SMTP_PASS:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_STARTTLS:
                server.starttls(context=ssl.create_default_context())
            if SMTP_USER and SMTP_PASS:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)


# --------------------------------------------------------------------------------------
# Calendar-driven availability
# --------------------------------------------------------------------------------------
LEDIGA_TEXT = os.getenv(
    "LEDIGA_TEXT",
    "Lediga v. 42–43 • Snabbt platsbesök i Göteborg med omnejd",
)

CALENDAR_MODE = os.getenv("CALENDAR_MODE", "ics").lower()
CALENDAR_ICS_URL = os.getenv("CALENDAR_ICS_URL", "").strip()
GCAL_SERVICE_ACCOUNT_JSON_PATH = os.getenv("GCAL_SERVICE_ACCOUNT_JSON_PATH", "").strip()
GCAL_CALENDAR_ID = os.getenv("GCAL_CALENDAR_ID", "").strip()
TIMEZONE = os.getenv("TIMEZONE", "Europe/Stockholm")
AVAILABILITY_WEEKS_AHEAD = int(os.getenv("AVAILABILITY_WEEKS_AHEAD", "6"))
STATUS_CACHE_TTL = int(os.getenv("STATUS_CACHE_TTL", "1800"))

_status_cache = {"text": LEDIGA_TEXT, "ts": 0.0}


async def availability_text_from_ics() -> str:
    """Compute a short availability string from an ICS feed; cached."""
    if not CALENDAR_ICS_URL:
        return LEDIGA_TEXT

    now = time.time()
    if now - _status_cache["ts"] < STATUS_CACHE_TTL and _status_cache["text"]:
        return _status_cache["text"]

    try:
        tzinfo = tz.gettz(TIMEZONE)
        end = datetime.now(tzinfo) + timedelta(weeks=AVAILABILITY_WEEKS_AHEAD)

        async with httpx.AsyncClient(timeout=4.0, http2=True) as client:
            r = await client.get(
                CALENDAR_ICS_URL, headers={"User-Agent": "sandladan/1.0"}
            )
            r.raise_for_status()
            cal = Calendar.from_ical(r.content)

        busy_weeks: set[int] = set()
        for comp in cal.walk("VEVENT"):
            dtstart = comp.get("DTSTART")
            dtend = comp.get("DTEND") or comp.get("DTSTART")
            if not dtstart:
                continue

            s = (
                getattr(dtstart.dt, "astimezone", lambda _: dtstart.dt)(tzinfo)
                if hasattr(dtstart, "dt")
                else None
            )
            e = (
                getattr(dtend.dt, "astimezone", lambda _: dtend.dt)(tzinfo)
                if hasattr(dtend, "dt")
                else s
            )
            if not s:
                continue
            if s > end:
                continue

            d = s
            while d <= (e or s):
                busy_weeks.add(int(d.isocalendar().week))
                d += timedelta(days=1)

        today = datetime.now(tzinfo).date()
        start_week = today.isocalendar().week
        weeks: list[int] = []
        for woffset in range(0, AVAILABILITY_WEEKS_AHEAD + 1):
            w = ((start_week - 1 + woffset) % 52) + 1
            if w not in busy_weeks:
                weeks.append(w)
                if len(weeks) >= 2:
                    break

        if weeks:
            weeks_str = f"{weeks[0]}" if len(weeks) == 1 else f"{weeks[0]}–{weeks[1]}"
            text = f"Lediga v. {weeks_str} • Snabbt platsbesök i Göteborg med omnejd"
        else:
            text = LEDIGA_TEXT

        _status_cache.update({"text": text, "ts": now})
        return text
    except Exception:
        return LEDIGA_TEXT


async def availability_text() -> str:
    if CALENDAR_MODE == "ics":
        return await availability_text_from_ics()
    # elif CALENDAR_MODE == "google":
    #     # Implement service-account freebusy/events listing here when ready.
    return LEDIGA_TEXT


# gzip responses for bigger payloads (>500B)
app.add_middleware(GZipMiddleware, minimum_size=500)


# small helper to set long cache headers for /static/*
@app.middleware("http")
async def _static_cache_control(request: Request, call_next):
    resp: Response = await call_next(request)
    if request.url.path.startswith("/static/"):
        # 1 year immutable cache for hashed assets/images
        resp.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    return resp


# --------------------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_year": time.gmtime().tm_year,
            "owner_phone": OWNER_PHONE,
        },
    )


@app.get("/status", response_class=HTMLResponse)
async def status_snippet():
    text = await availability_text()
    html = (
        f'<span class="inline-flex items-center gap-2">'
        f'<span class="w-2 h-2 rounded-full bg-green-500 animate-pulse" aria-hidden="true"></span>'
        f'<span class="font-medium">Tillgänglighet:</span>'
        f"<span>{text}</span>"
        f"</span>"
    )
    return HTMLResponse(html)


@app.post("/offert", response_class=HTMLResponse)
async def offert(
    request: Request,
    background: BackgroundTasks,
    namn: str = Form(...),
    telefon: str = Form(...),
    epost: Optional[str] = Form(None),
    beskrivning: Optional[str] = Form(None),
    website: Optional[str] = Form(None),  # honeypot
    bild: Optional[UploadFile] = File(None),
):
    ip = request.client.host if request.client else "unknown"
    if too_many_requests(ip):
        return HTMLResponse(
            """
            <div class="rounded-lg border border-red-500/40 bg-red-500/10 p-4">
              <p class="font-semibold">För många förfrågningar just nu.</p>
              <p class="text-sm opacity-80">Vänta en liten stund och försök igen.</p>
            </div>
            """,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Honeypot hit -> pretend success
    if website:
        return HTMLResponse(
            """
            <div class="rounded-lg border border-green-500/40 bg-green-500/10 p-4">
              <p class="font-semibold">Tack! Din förfrågan är mottagen.</p>
              <p class="text-sm opacity-80">Vi återkommer samma dag.</p>
            </div>
            """,
        )

    errors = []
    if not namn.strip():
        errors.append("Ange ditt namn.")
    if not telefon.strip():
        errors.append("Ange ditt telefonnummer.")
    if errors:
        lis = "".join(f"<li>{e}</li>" for e in errors)
        return HTMLResponse(
            f"""
            <div class="rounded-lg border border-red-500/40 bg-red-500/10 p-4">
              <p class="font-semibold">Kunde inte skicka – kontrollera följande:</p>
              <ul class="list-disc pl-5 mt-2">{lis}</ul>
            </div>
            """,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def esc(s: Optional[str]) -> str:
        if s:
            return s.replace("<", "&lt;").replace(">", "&gt;")
        return ""

    subject = f"[Sandlådan AB] Ny förfrågan från {esc(namn)}"
    body_html = f"""
    <h2>Ny förfrågan via webbplatsen</h2>
    <p><strong>Namn:</strong> {esc(namn)}</p>
    <p><strong>Telefon:</strong> {esc(telefon)}</p>
    <p><strong>E-post:</strong> {esc(epost) or "-"}</p>
    <p><strong>Beskrivning:</strong><br>{esc(beskrivning) or "-"}</p>
    """
    body_text = (
        "Ny förfrågan via webbplatsen\n"
        f"Namn: {namn}\nTelefon: {telefon}\nE-post: {epost or '-'}\n"
        f"Beskrivning:\n{beskrivning or '-'}\n"
    )

    attachments = []
    if bild and bild.filename:
        data = await bild.read()
        mime = bild.content_type or "application/octet-stream"
        attachments.append((bild.filename, data, mime))

    msg = build_email(subject, body_html, body_text, attachments)
    background.add_task(send_email_message, msg)

    return HTMLResponse(
        f"""
        <div class="rounded-lg border border-green-500/40 bg-green-500/10 p-4">
          <p class="font-semibold">Tack {esc(namn)}! Din förfrågan är mottagen.</p>
          <p class="text-sm opacity-80">Vi återkommer samma dag på {esc(telefon)}.</p>
        </div>
        """
    )


ROBOT_PATH = BASE_DIR / "robots.txt"


@app.get("/robots.txt")
def robots():
    if ROBOT_PATH.exists():
        return FileResponse(
            path=str(ROBOT_PATH), media_type="text/plain; charset=utf-8"
        )
    return PlainTextResponse("User-agent: *\nAllow: /\n")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(str(BASE_DIR / "static" / "favicon.ico"))
