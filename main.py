from __future__ import annotations

import json
import mimetypes
import os
import pathlib
import secrets
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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

# ---------------------------------------------------------------------------
# 1. Configuration & Constants
# ---------------------------------------------------------------------------

# --- Mimetypes ---
# Register these manually to ensure Render/Linux serves them correctly
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/jpeg", ".jpeg")

# --- Base Paths ---
BASE_DIR = pathlib.Path(__file__).parent
ROBOT_PATH = BASE_DIR / "robots.txt"

# --- Env Helpers ---
def _csv_env(name: str, default: str = "") -> list[str]:
    """Parses comma-separated list, stripping ports and protocols (safe for ALLOWED_HOSTS)."""
    raw = [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]
    cleaned: list[str] = []
    for item in raw:
        # allow either "https://x" or "x" but store origin/host cleanly
        item = item.replace("https://", "").replace("http://", "")
        item = item.split("/")[0]
        item = item.split(":")[0]  # strip ports (e.g. :443)
        cleaned.append(item)
    return cleaned

def _csv_origins(name: str, default: str = "") -> list[str]:
    """Parses comma-separated list, ensuring https:// prefix (required for CORS)."""
    raw = [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]
    out: list[str] = []
    for o in raw:
        if o.startswith("http://") or o.startswith("https://"):
            out.append(o)
        else:
            out.append(f"https://{o}")
    return out

def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() == "true"

# --- App Config ---
BASE_URL = os.getenv("BASE_URL", "").strip()
DEBUG_STATIC = _env_bool("DEBUG_STATIC", "false")

ALLOWED_HOSTS = _csv_env("ALLOWED_HOSTS", "")
DISABLE_TRUSTED_HOST = _env_bool("DISABLE_TRUSTED_HOST", "false")

CORS_ORIGINS = _csv_origins(
    "CORS_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
)

# --- Security Config ---
HSTS_ENABLE = _env_bool("HSTS_ENABLE", "false")

# --- Contact / Owner ---
OWNER_PHONE = os.environ.get("OWNER_PHONE", "+46XXXXXXXX")
PUBLIC_EMAIL = os.environ.get("PUBLIC_EMAIL", "info@sandladan.se")

# --- Email Config ---
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_STARTTLS = _env_bool("SMTP_STARTTLS", "true")
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER or "no-reply@sandladan.se")
MAIL_TO = os.environ.get("MAIL_TO", "")

# --- Rate Limit Config ---
RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))
RATE_MAX = int(os.getenv("RATE_MAX", "5"))

# --- Calendar Config ---
LEDIGA_TEXT = os.getenv("LEDIGA_TEXT", "Lediga v. 42–43 • Snabbt platsbesök i Göteborg med omnejd")
CALENDAR_MODE = os.getenv("CALENDAR_MODE", "ics").lower().strip()
CALENDAR_ICS_URL = os.getenv("CALENDAR_ICS_URL", "").strip()
TIMEZONE = os.getenv("TIMEZONE", "Europe/Stockholm").strip()
AVAILABILITY_WEEKS_AHEAD = int(os.getenv("AVAILABILITY_WEEKS_AHEAD", "6"))
STATUS_CACHE_TTL = int(os.getenv("STATUS_CACHE_TTL", "1800"))

# ---------------------------------------------------------------------------
# 2. Services & Helper Classes
# ---------------------------------------------------------------------------

class CSPNonceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate a unique nonce for this request (used in base.html for scripts)
        request.state.csp_nonce = secrets.token_urlsafe(16)
        return await call_next(request)

class RateLimiter:
    """Simple in-memory token bucket rate limiter."""
    bucket: dict[str, list[float]] = {}

    @classmethod
    def is_rate_limited(cls, ip: str) -> bool:
        now = time.time()
        bucket = cls.bucket.setdefault(ip, [])
        cls.bucket[ip] = [t for t in bucket if now - t < RATE_WINDOW]

        if len(cls.bucket[ip]) >= RATE_MAX:
            return True

        cls.bucket[ip].append(now)
        return False

class EmailService:
    @staticmethod
    def build_message(subject, body_html, body_text, attachments=None):
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

    @staticmethod
    def send(msg: EmailMessage) -> None:
        if not (SMTP_HOST and SMTP_PORT and MAIL_TO and MAIL_FROM):
            return
        try:
            if SMTP_PORT == 465 and not SMTP_STARTTLS:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                    if SMTP_USER and SMTP_PASS: server.login(SMTP_USER, SMTP_PASS)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                    if SMTP_STARTTLS: server.starttls(context=ssl.create_default_context())
                    if SMTP_USER and SMTP_PASS: server.login(SMTP_USER, SMTP_PASS)
                    server.send_message(msg)
        except Exception as e:
            print(f"Error sending email: {e}")

class CalendarService:
    _cache = {"text": LEDIGA_TEXT, "ts": 0.0}

    @classmethod
    async def get_text(cls) -> str:
        if CALENDAR_MODE != "ics" or not CALENDAR_ICS_URL:
            return LEDIGA_TEXT

        now = time.time()
        if now - cls._cache["ts"] < STATUS_CACHE_TTL and cls._cache["text"]:
            return cls._cache["text"]

        try:
            text = await cls._fetch_and_parse_ics()
            cls._cache.update({"text": text, "ts": now})
            return text
        except Exception:
            return LEDIGA_TEXT

    @classmethod
    async def _fetch_and_parse_ics(cls) -> str:
        tzinfo = tz.gettz(TIMEZONE)
        end = datetime.now(tzinfo) + timedelta(weeks=AVAILABILITY_WEEKS_AHEAD)

        async with httpx.AsyncClient(timeout=4.0, http2=True) as client:
            r = await client.get(CALENDAR_ICS_URL, headers={"User-Agent": "sandladan/1.0"})
            r.raise_for_status()
            cal = Calendar.from_ical(r.content)

        busy_weeks = set()
        for comp in cal.walk("VEVENT"):
            dtstart = comp.get("DTSTART")
            dtend = comp.get("DTEND") or comp.get("DTSTART")
            if not dtstart: continue

            s, e = dtstart.dt, (dtend.dt if dtend else dtstart.dt)
            if hasattr(s, "astimezone"): s = s.astimezone(tzinfo)
            if hasattr(e, "astimezone"): e = e.astimezone(tzinfo)

            if s > end: continue
            d = s
            while d <= e:
                busy_weeks.add(int(d.isocalendar().week))
                d += timedelta(days=1)

        today = datetime.now(tzinfo).date()
        start_week = today.isocalendar().week
        weeks = []
        for woffset in range(0, AVAILABILITY_WEEKS_AHEAD + 1):
            w = ((start_week - 1 + woffset) % 52) + 1
            if w not in busy_weeks:
                weeks.append(w)
                if len(weeks) >= 2: break

        if weeks:
            weeks_str = f"{weeks[0]}" if len(weeks) == 1 else f"{weeks[0]}–{weeks[1]}"
            return f"Lediga v. {weeks_str} • Snabbt platsbesök i Göteborg med omnejd"
        return LEDIGA_TEXT

# ---------------------------------------------------------------------------
# 3. Application Setup & Middleware
# ---------------------------------------------------------------------------

app = FastAPI(title="Sandlådan AB")

# Template & Static Setup
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates.env.globals.update(BASE_URL=BASE_URL)

def csp_nonce(request: Request) -> str:
    """Helper for templates to access nonce."""
    return getattr(request.state, "csp_nonce", "")
templates.env.globals["csp_nonce"] = csp_nonce

# -- Middlewares (Order Matters) --

# 1. Nonce (MUST be first so it's ready for responses)
app.add_middleware(CSPNonceMiddleware)

# 2. Trusted Host (Render-safe: only enabled if config says so)
if (not DISABLE_TRUSTED_HOST) and ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# 3. Standard
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

if DEBUG_STATIC:
    @app.middleware("http")
    async def _debug_static(request: Request, call_next):
        if request.url.path.startswith("/static/"):
            print(f"STATIC REQ | HOST: {request.headers.get('host')} | PATH: {request.url.path}")
        return await call_next(request)

@app.middleware("http")
async def _security_headers(request: Request, call_next):
    """Applies CSP, HSTS, and other security headers."""
    response: Response = await call_next(request)
    nonce = getattr(request.state, "csp_nonce", "")

    # CSP: Strict but practical
    csp_directives = [
        "default-src 'self'",
        "img-src 'self' data: blob:", # 'blob:' required for image upload previews
        "style-src 'self' 'unsafe-inline'", # 'unsafe-inline' required for base.html style block
        f"script-src 'self' 'nonce-{nonce}'" if nonce else "script-src 'self'",
        "font-src 'self' data:",
        "connect-src 'self'",
        "form-action 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests"
    ]

    response.headers.setdefault("Content-Security-Policy", "; ".join(csp_directives))
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

    if HSTS_ENABLE:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")

    return response

@app.middleware("http")
async def _static_cache_control(request: Request, call_next):
    """Aggressive caching for static assets."""
    response: Response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    return response

# ---------------------------------------------------------------------------
# 4. Routes
# ---------------------------------------------------------------------------

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def index(request: Request):
    """Main index route. Generates Schema.org JSON and serves index.html."""
    base = (BASE_URL or f"{request.url.scheme}://{request.url.netloc}").rstrip("/")
    schema = {
        "@context": "https://schema.org",
        "@type": "GeneralContractor",
        "name": "Sandlådan AB",
        "image": f"{base}/static/assets/images/hero-excavator-1280.webp",
        "url": base,
        "telephone": OWNER_PHONE,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Göteborg",
            "addressRegion": "Västra Götaland",
            "addressCountry": "SE",
        },
        "priceRange": "$$",
        "openingHoursSpecification": {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "opens": "07:00",
            "closes": "16:00",
        },
    }
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_year": time.gmtime().tm_year,
        "owner_phone": OWNER_PHONE,
        "mail_from": MAIL_FROM or "info@sandladan.se",
        "public_email": PUBLIC_EMAIL,
        "schema_json": json.dumps(schema, ensure_ascii=False),
    })

@app.get("/status", response_class=HTMLResponse)
async def status_snippet():
    text = await CalendarService.get_text()
    return HTMLResponse(
        f'<span class="inline-flex items-center gap-2">'
        f'<span class="w-2 h-2 rounded-full" style="background:#22c55e" aria-hidden="true"></span>'
        f'<span class="font-medium">Tillgänglighet:</span><span>{text}</span></span>'
    )

@app.post("/offert", response_class=HTMLResponse)
async def offert(
    request: Request,
    background: BackgroundTasks,
    namn: str = Form(...),
    telefon: str = Form(...),
    epost: Optional[str] = Form(None),
    beskrivning: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    bild: Optional[UploadFile] = File(None),
):
    ip = request.client.host if request.client else "unknown"
    if RateLimiter.is_rate_limited(ip):
        return HTMLResponse('<div class="notice notice--err"><p class="font-semibold">För många förfrågningar just nu.</p></div>', status.HTTP_429_TOO_MANY_REQUESTS)
    if website: return HTMLResponse('<div class="notice notice--ok"><p class="font-semibold">Tack! Din förfrågan är mottagen.</p></div>')

    errors = []
    if not namn.strip(): errors.append("Ange ditt namn.")
    if not telefon.strip(): errors.append("Ange ditt telefonnummer.")
    if errors:
        lis = "".join(f"<li>{e}</li>" for e in errors)
        return HTMLResponse(f'<div class="notice notice--err"><p class="font-semibold">Kontrollera:</p><ul class="list-disc notice__list">{lis}</ul></div>', status.HTTP_400_BAD_REQUEST)

    def esc(s): return s.replace("<", "&lt;").replace(">", "&gt;") if s else ""
    subject = f"[Sandlådan AB] Ny förfrågan från {esc(namn)}"
    body_html = f"<h2>Ny förfrågan</h2><p><strong>Namn:</strong> {esc(namn)}</p><p><strong>Tel:</strong> {esc(telefon)}</p><p><strong>E-post:</strong> {esc(epost) or '-'}</p><p><strong>Beskrivning:</strong><br>{esc(beskrivning) or '-'}</p>"
    body_text = f"Namn: {namn}\nTel: {telefon}\nE-post: {epost or '-'}\nBeskrivning:\n{beskrivning or '-'}"

    attachments = []
    if bild and bild.filename:
        data = await bild.read()
        mime = bild.content_type or "application/octet-stream"
        attachments.append((bild.filename, data, mime))

    msg = EmailService.build_message(subject, body_html, body_text, attachments)
    background.add_task(EmailService.send, msg)

    return HTMLResponse(f'<div class="notice notice--ok"><p class="font-semibold">Tack {esc(namn)}!</p><p class="text-sm notice__muted">Vi återkommer på {esc(telefon)}.</p></div>')

@app.get("/robots.txt")
def robots():
    content = "User-agent: *\nAllow: /\n"
    return PlainTextResponse(content)

@app.get("/site.webmanifest")
def manifest():
    return FileResponse(str(BASE_DIR / "static" / "site.webmanifest"), media_type="application/manifest+json")