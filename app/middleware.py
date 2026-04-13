from __future__ import annotations

import secrets

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings


class CSPNonceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request.state.csp_nonce = secrets.token_urlsafe(16)
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    # 1. CSP nonce (outermost → runs first)
    app.add_middleware(CSPNonceMiddleware)

    # 2. Trusted hosts
    if not settings.disable_trusted_host and settings.allowed_hosts_list:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts_list,
        )

    # 3. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # 4. Gzip
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # 5. Security headers
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response: Response = await call_next(request)
        nonce = getattr(request.state, "csp_nonce", "")

        script_src = f"'self' 'nonce-{nonce}'" if nonce else "'self'"
        csp = "; ".join(
            [
                "default-src 'self'",
                "img-src 'self' data: blob:",
                "style-src 'self' 'unsafe-inline'",
                f"script-src {script_src}",
                "font-src 'self' data:",
                "connect-src 'self'",
                "form-action 'self'",
                "base-uri 'self'",
                "frame-ancestors 'none'",
                "upgrade-insecure-requests",
            ]
        )

        headers = {
            "Content-Security-Policy": csp,
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Permissions-Policy": ("geolocation=(), microphone=(), camera=()"),
        }
        if settings.hsts_enable:
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        for key, val in headers.items():
            response.headers.setdefault(key, val)

        return response

    # 6. Static cache control
    @app.middleware("http")
    async def static_cache(request: Request, call_next):
        response: Response = await call_next(request)
        path = request.url.path
        if (
            path.startswith("/static/") or path.startswith("/dist/")
        ) and response.status_code < 400:
            response.headers.setdefault(
                "Cache-Control",
                "public, max-age=31536000, immutable",
            )
        return response