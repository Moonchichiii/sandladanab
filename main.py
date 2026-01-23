from __future__ import annotations

import os
import pathlib
import smtplib
import ssl
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional

import httpx
from dateutil import tz
from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from icalendar import Calendar
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware


def _csv_env(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() == "true"


# ---------------------------------------------------------------------------
# App / paths
# ---------------------------------------------------------------------------
BASE_DIR = pathlib.Path(__file__).parent
app = FastAPI(title="Sandlådan AB")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

ROBOT_PATH = BASE_DIR / "robots.txt"


# ---------------------------------------------------------------------------
# Env (Render-friendly)
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("BASE_URL", "").strip()

ALLOWED_HOSTS = _csv_env("ALLOWED_HOSTS", "")
DISABLE_TRUSTED_HOST = _env_bool("DISABLE_TRUSTED_HOST", "false")

CORS_ORIGINS = _csv_env(
    "CORS_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
)

DEBUG_STATIC = _env_bool("DEBUG_STATIC", "false")
HSTS_ENABLE = _env_bool("HSTS_ENABLE", "false")

templates.env.globals.update(BASE_URL=BASE_URL)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
if DEBUG_STATIC:

    @app.middleware("http")
    async def _debug_static(request: Request, call_next):
        if request.url.path.startswith("/static/"):
            print(
                "STATIC REQ",
                "HOST:", request.headers.get("host"),
                "PATH:", request.url.path,
                "DISABLE_TRUSTED_HOST:", os.getenv("DISABLE_TRUSTED_HOST"),
                "ALLOWED_HOSTS:", os.getenv("ALLOWED_HOSTS"),
            )
        return await call_next(request)


# Only enable TrustedHost when we actually have host rules AND not disabled
if (not DISABLE_TRUSTED_HOST) and ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=500)


SEC_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        # NOTE: JSON-LD is inline <script>. If you see it blocked, add 'unsafe-inline' here.
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
        resp.headers.setdefault(k, v)
    return resp


@app.middleware("http")
async def _static_cache_control(request: Request, call_next):
    resp: Response = await call_next(request)
    if request.url.path.startswith("/static/"):
        resp.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    return resp


# ---------------------------------------------------------------------------
# Mail
# ---------------------------------------------------------------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_STARTTLS = _env_bool("SMTP_STARTTLS", "true")

MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER or "no-reply@sandladan.se")
MAIL_TO = os.environ.get("MAIL_TO", "")

OWNER_PHONE = os.environ.get("OWNER_PHONE", "+46XXXXXXXX")
PUBLIC_EMAIL = os.environ.get("PUBLIC_EMAIL", "info@sandladan.se")


# Rate limit (simple in-memory token bucket)
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


def send_email_message(msg: EmailMessage) -> None:
    # Quietly no-op if not configured
    if not (SMTP_HOST and SMTP_PORT and MAIL_TO and MAIL_FROM):
        return

    if SMTP_PORT == 465 and not SMTP_STARTTLS:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            if SMTP_USER and SMTP_PASS:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if SMTP_STARTTLS:
            server.starttls(context=ssl.create_default_context())
        if SMTP_USER and SMTP_PASS:
            server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# ---------------------------------------------------------------------------
# Availability (ICS)
# ---------------------------------------------------------------------------
LEDIGA_TEXT = os.getenv(
    "LEDIGA_TEXT",
    "Lediga v. 42–43 • Snabbt platsbesök i Göteborg med omnejd",
)

CALENDAR_MODE = os.getenv("CALENDAR_MODE", "ics").lower().strip()
CALENDAR_ICS_URL = os.getenv("CALENDAR_ICS_URL", "").strip()
TIMEZONE = os.getenv("TIMEZONE", "Europe/Stockholm").strip()
AVAILABILITY_WEEKS_AHEAD = int(os.getenv("AVAILABILITY_WEEKS_AHEAD", "6"))
STATUS_CACHE_TTL = int(os.getenv("STATUS_CACHE_TTL", "1800"))

_status_cache = {"text": LEDIGA_TEXT, "ts": 0.0}


async def availability_text_from_ics() -> str:
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

            s = dtstart.dt
            e = dtend.dt if dtend else s

            # normalize tz if possible
            if hasattr(s, "astimezone"):
                s = s.astimezone(tzinfo)
            if hasattr(e, "astimezone"):
                e = e.astimezone(tzinfo)

            if s > end:
                continue

            d = s
            while d <= e:
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
    return LEDIGA_TEXT


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_year": time.gmtime().tm_year,
            "owner_phone": OWNER_PHONE,
            "mail_from": MAIL_FROM or "info@sandladan.se",
            "public_email": PUBLIC_EMAIL,
        },
    )


@app.get("/status", response_class=HTMLResponse)
async def status_snippet():
    text = await availability_text()
    html = (
        f'<span class="inline-flex items-center gap-2">'
        f'<span class="w-2 h-2 rounded-full" style="background:#22c55e" aria-hidden="true"></span>'
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
            <div class="notice notice--err">
              <p class="font-semibold">För många förfrågningar just nu.</p>
              <p class="text-sm notice__muted">Vänta en liten stund och försök igen.</p>
            </div>
            """,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if website:
        return HTMLResponse(
            """
            <div class="notice notice--ok">
              <p class="font-semibold">Tack! Din förfrågan är mottagen.</p>
              <p class="text-sm notice__muted">Vi återkommer samma dag.</p>
            </div>
            """
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
            <div class="notice notice--err">
              <p class="font-semibold">Kunde inte skicka – kontrollera följande:</p>
              <ul class="list-disc notice__list">{lis}</ul>
            </div>
            """,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def esc(s: Optional[str]) -> str:
        return s.replace("<", "&lt;").replace(">", "&gt;") if s else ""

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

    attachments: list[tuple[str, bytes, str]] = []
    if bild and bild.filename:
        data = await bild.read()
        mime = bild.content_type or "application/octet-stream"
        attachments.append((bild.filename, data, mime))

    msg = build_email(subject, body_html, body_text, attachments)
    background.add_task(send_email_message, msg)

    return HTMLResponse(
        f"""
        <div class="notice notice--ok">
          <p class="font-semibold">Tack {esc(namn)}! Din förfrågan är mottagen.</p>
          <p class="text-sm notice__muted">Vi återkommer samma dag på {esc(telefon)}.</p>
        </div>
        """
    )


@app.get("/robots.txt")
def robots():
    if ROBOT_PATH.exists():
        return FileResponse(str(ROBOT_PATH), media_type="text/plain; charset=utf-8")
    return PlainTextResponse("User-agent: *\nAllow: /\n")


@app.get("/site.webmanifest")
def manifest():
    return FileResponse(
        str(BASE_DIR / "static" / "site.webmanifest"),
        media_type="application/manifest+json",
    )
