# Security policy

Sandlådan AB's website is a small FastAPI application with no accounts, no database and no
third-party requests. It still takes security seriously: every response carries a strict
Content-Security-Policy (no `unsafe-inline`), COOP/COEP/CORP, HSTS with preload, Subresource
Integrity on its own assets, and uploads are validated by their bytes. The full list is tested
in `tests/test_site.py`.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository:
**Security → Advisories → Report a vulnerability**. Do not open a public issue for security
problems. You will get an acknowledgement within 5 working days and a fix or a plan within 30.

## What is in scope

- The application code in `app/`, the templates, `static/js/site.js` and the build/CI configuration.
- The quote form endpoint (`/api/offert`) and the availability endpoint (`/api/status`).

## What is not in scope

- The hosting provider's infrastructure and TLS termination.
- Volumetric denial of service.

## Supported versions

Only the `main` branch is supported; fixes ship as new releases, never as backports.
