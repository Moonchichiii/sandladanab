# sandladanab

Sandlådan AB – grävmaskinsjobb och anläggning i Göteborg. FastAPI + Jinja2, Tailwind 4.1 CLI
(tokens + layers, no utility classes), one 1.7 KB script, self-hosted fonts, pre-rendered
AVIF/WebP photos. v2 (2026-09-21): editorial refresh, real photos, /integritet, verifiability
facts, no third-party requests.

## Run

    uv sync
    bun install
    bun run build            # static/dist/styles.css + site.js
    uv run uvicorn main:app --reload

## Test

    uv run pytest -q
    uv run ruff check . && uv run ruff format --check .

## Security chain (network; run before a release)

    uv export --quiet --locked --all-extras --no-emit-project --format requirements-txt -o requirements-audit.txt
    uvx pip-audit --strict -r requirements-audit.txt
    bun audit
    uvx zizmor --offline --persona pedantic .github/workflows

CI runs the same plus CodeQL, OpenSSF Scorecard, dependency review and gitleaks (`.github/workflows/`).

## Content

- Copy and image slots: `app/content.py`
- Company facts (org.nr, owner, LinkedIn…): `.env` → `app/config.py` (empty = row hidden)
- Form spam protection: honeypot + HMAC-signed timestamp (`app/services/form_token.py`).
  Set `FORM_SECRET` in the production `.env` (`openssl rand -hex 32`); `FORM_MIN_SECONDS=3`,
  `FORM_MAX_SECONDS=7200` are the defaults. Rate limit: `RATE_MAX` per `RATE_WINDOW` seconds per IP.
- Photos: put originals in `assets-src/`, run `python scripts/render_images.py`
- Design system (tokens, components, guidelines): the "Sandlådan Design System" artifact
