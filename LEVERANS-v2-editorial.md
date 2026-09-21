# LEVERANS v2 – editorial refresh (2026-09-21)

Canon zip: `sandladanab-20260921-<HHMM>-v2-editorial.zip` (whole tree, `sandladanab/` kept). Base: `sandladanab-20260921-1311.zip`. Machine diff in `DIFF.txt`. Nothing here is committed or tagged - that is yours.

## Drop-in check - ONE chain, everything must be green

The chain must run in a folder that holds THIS zip's tree (`Test-Path tests\conftest.py` → `True`). Either a fresh folder:
```pwsh
Expand-Archive .\sandladanab-20260921-<HHMM>-v2-editorial.zip -DestinationPath .\v2-drop && Set-Location .\v2-drop\sandladanab
```
or mirrored into your repo working copy (robocopy deletes what the zip no longer has - see DIFF.txt DELETED - and leaves .git, .venv, node_modules and .env alone; robocopy exits 1-3 on success, so run it on its own line, not in the && chain):
```pwsh
Expand-Archive .\sandladanab-20260921-<HHMM>-v2-editorial.zip -DestinationPath $env:TEMP\v2-drop -Force
```
```pwsh
robocopy $env:TEMP\v2-drop\sandladanab C:\SandladanAB\sandladanab /MIR /XD .git .venv node_modules /XF .env
```
```pwsh
uv sync --all-extras && bun install && bun run build && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && Write-Host 'ALL GREEN'
```
Expected: `34 passed` (2 upstream deprecation warnings from starlette's test client are expected), `All checks passed!`, `… files already formatted`, `ALL GREEN`. If any link in the chain fails the chain stops there - send me the output. Run here before packaging from a clean unzip: green with no `.env`, with a production-like `.env` (ALLOWED_HOSTS, ICS URL, SMTP, RATE_MAX=3) and with `MAINTENANCE_MODE=true`.


## Security chain (network - run before you commit; CI runs the same)

```pwsh
uv export --quiet --locked --all-extras --no-emit-project --format requirements-txt -o requirements-audit.txt && uvx pip-audit --strict -r requirements-audit.txt && bun audit && uvx zizmor --offline --persona pedantic .github/workflows && Write-Host 'SECURITY GREEN'
```
Expected: `No known vulnerabilities found` · `No vulnerabilities found` · `No findings to report. Good job!` · `SECURITY GREEN`. (`requirements-audit.txt` is gitignored.)

## What was done

**Design (per the "Sandlådan Design System" artifact)**
- Editorial layout: hairline rows instead of cards, section eyebrows + display headings, more air (sections 96/48 px), three surface steps (asfalt → grafit → skiffer), photos as the depth. No gradients, no glows, no glass/blur, no text-shadow.
- Tokens fixed: `betong` defined (was referenced, never declared → muted text rendered white); the four oranges and `#0E1113` residue consolidated; one accent `maskin #ff7b2a` (your call: the flat `#ff5c00` read red), `maskin-deep #ff5c00` hover, `maskin-dark #e65100` pressed, black text on orange.
- Author-Variable.woff2 has wght **200–700** only; `@font-face` now declares `200 700` and all display weights are 700 (v1's 800/900 were clamped/faux-bolded by browsers).
- Buttons: flat, pill, two fills (`btn--primary`, `btn--ghost`), two sizes (`btn--sm`), `btn--block`. Header CTA and footer CTA use the same classes - no inline overrides anywhere (CSP no longer allows `style=` either).
- Hero: split layout, text left, real photo right (4:5 desktop, 3:2 mobile-first). Status pill → plain status line with a green dot, ONE state, rendered server-side from `LEDIGA_TEXT` (no "Kontrollerar tillgänglighet…" flash). Only when `CALENDAR_MODE=ics` + `CALENDAR_ICS_URL` are set does `site.js` refresh it from `/api/status`; otherwise no request at all.
- Services as a hairline list; gallery as an asymmetric grid (lead 2×2, squares, one 2:1 wide) with captions below; new **Om Sandlådan** band with portrait slot + company facts; quote form without the box; footer with legal bar (org.nr, säte) and LinkedIn link.
- `.container` → `.wrap` (avoids Tailwind 4's `container` utility silently overriding the max-width).

**Real photos, same pipeline**
- Six photos in `assets-src/` (chat-compressed 2048 px copies - ask Jeffery for the originals and re-run).
- `scripts/render_images.py` (Pillow): per-slot ratio + focal point → `static/assets/images/<slot>-<w>.avif` and `.webp`. Templates use `<picture>` AVIF-first via `macros/picture.html`; `width`/`height` on every `<img>`; hero AVIF set preloaded with `imagesrcset`.
- Slots: `hero-rorlaggning` (768/1280/1920), `galleri-isolering` lead (768/1024/1536), `galleri-maskinstyrning` + `galleri-kabelror` squares (480/768/1024), `galleri-avloppsror` wide 2:1 (768/1152/1536), `om-hytten` 4:5 (480/768/960).
- Stock/AI images deleted (34 files).

**Phone hidden for now (your call 2026-09-21 15:40)**
- `SHOW_PHONE=false` (default): no `tel:` link, no "Ring direkt", no Telefon row in the facts, no `telephone` in schema.org, /integritet points to the form only. Header + mobile sheet CTA = "Begär offert"; hero = "Begär offert" (primary) + "Se våra arbeten" (ghost → #galleri); footer Kontakt = "Begär offert" with the copy "Beskriv jobbet i formuläret så ringer vi upp dig." The form still asks for the CUSTOMER's phone - that is how Jeffery calls back.
- `SHOW_PHONE=true` + `OWNER_PHONE` brings every phone element back exactly as designed (tested both ways: `test_phone_hidden_by_default`, `test_phone_shown_with_flag`). `OWNER_PHONE` default is now empty (was `+46XXXXXXXX`).
- `.stack > .btn:only-child` spans both columns on mobile so a lone button is full width.

**Verifiability**
- New settings (`.env`): `ORG_NUMBER`, `SEAT` (default Göteborg), `POSTAL_ADDRESS`, `OWNER_NAME`, `OWNER_TITLE`, `LINKEDIN_URL`, `OWNER_PHONE_DISPLAY`. Empty value = row hidden, never a placeholder.
- `_facts()` in `pages.py` feeds the About list; footer bar repeats org.nr + säte; schema.org rebuilt (`GeneralContractor`+`LocalBusiness`, `legalName`, `identifier`, `founder` Person with `jobTitle`, `sameAs` LinkedIn, `areaServed`, `logo`). **No e-mail anywhere** - not in the page, not in schema. `public_email` stays only as `mail_from` fallback.
- New route `/integritet` (personuppgiftsansvarig, vad/varför/hur länge, inga kakor, säkerhet, rättigheter, IMY). Footer "Integritet & GDPR" and the form consent line link to it. `PRIVACY_UPDATED` in `content.py`.
- Nav gets "Om oss"; links are `/#…` so they work from `/integritet`.

**Security / GDPR hardening**
- CSP: `style-src 'self' 'nonce-…'` (dropped `'unsafe-inline'`), `object-src 'none'`, `manifest-src 'self'`, `font-src 'self'`; new `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Resource-Policy: same-origin` (Lighthouse's COOP note).
- Upload: bytes are sniffed (JPEG/PNG/WebP/AVIF magic), the browser's Content-Type is not trusted, bounded read (10 MB + 1), original filename not forwarded (`bild.<ext>`). Text fields capped (120/40/4000). API responses `Cache-Control: no-store`. The unused `epost` form param removed.
- Zero third-party requests (fonts, scripts, images all same-origin); no cookies, no analytics - stated on `/integritet`.

**HTMX → fetch (your "kör")**
- `static/vendor/htmx.min.js` (48 KB) removed. `static/js/site.js` (1.7 KB minified) does menu + `GET /api/status` swap + form `POST` as `FormData` with the server's HTML notice swapped into `#form-response`; native validation first; submit disabled while sending; graceful fallback without JS (plain form POST still works). `api.py` responses unchanged in content; `/api/status` now returns the `.status__dot` markup.
- `menu.js` + dead `file-input.js` replaced by `site.js`; `package.json` `js:build` updated.

**Security grade - Mozilla HTTP Observatory (sandladan.se today: A+ 110/100) stays A+ and picks up the last three items**
- CSP `style-src` without `'unsafe-inline'` (the one thing Observatory flagged), `img-src 'self'` (no `data:` either), `object-src 'none'`.
- `Cross-Origin-Embedder-Policy: require-corp` and `Cross-Origin-Resource-Policy: same-origin` added (COEP/CORP were "not implemented"); COOP `same-origin`. Safe because every resource is same-origin - verified in Chromium that all images, the stylesheet and the script still load.
- Subresource Integrity ("add SRI for bonus points"): `/dist/styles.css` and `/dist/site.js` carry `integrity="sha384-…"`, computed once at startup from the built file; the same hash is the `?v=` cache-buster, which also fixes a latent v1 bug - `/dist` is served `Cache-Control: immutable, max-age=1y`, so without a version in the URL a deploy could serve last year's CSS. In `DEBUG=true` (css:watch) integrity is skipped so a rebuilt file is never blocked.
- HSTS with `preload`/`includeSubDomains`/1 year is already what the app sends when `HSTS_ENABLE=true` - Observatory's "consider preloading" is then only the submission at hstspreload.org (your call).
- Open Graph + Twitter card meta (title, description, url, locale, 1200×630 `og:image` rendered from the hero photo as JPEG in `static/assets/brand/og-image.jpg`) so the LinkedIn → site hop shows a real preview card.
- `test_security_headers_keep_observatory_a_plus`, `test_dist_assets_have_sri_and_cache_buster` (fetches the CSS and re-hashes it) and `test_open_graph_preview_tags` pin all of this.

**GitHub + package security to the max (your ask 2026-09-21 15:50)**
- **28 known vulnerabilities were in your lock.** `pip-audit` on the old `uv.lock` (fastapi 0.135.3 / starlette 1.0.0 era) reported 28 advisories in 7 packages: starlette (PYSEC-2026-248/249/2280/2281), python-multipart (5), anyio (2 CVEs), pydantic-settings (CVE-2026-58203), click, h2, idna. `uv lock --upgrade` → fastapi 0.141.1, starlette 1.6.0, python-multipart 0.0.32, pydantic-settings 2.15.0, anyio 4.15.1, uvicorn 0.53.0, ruff 0.16.8 … → `No known vulnerabilities found`. All 34 tests pass on the new set. Floors raised in `pyproject.toml` (`fastapi>=0.141`, `python-multipart>=0.0.31`, `pydantic-settings>=2.14.2`) plus `[tool.uv] constraint-dependencies` for the transitive ones (starlette, anyio, click, h2, idna) so `uv lock` can never resolve below the fixed versions again.
- `bun audit`: no vulnerabilities. `bunfig.toml`: `minimumReleaseAge = 604800` (bun will not resolve an npm version younger than 7 days - the freshly-published-malware guard) and `exact = true`.
- `ruff` now runs the Bandit rule set (`S`) on every lint - the codebase passes it as-is; `tests/*` may use `assert` and fake credentials.
- `.github/workflows/ci.yml`: **build-test** (the LEVERANS chain with `uv sync --locked` and `bun install --frozen-lockfile`, so a stale lock fails CI), **audit** (pip-audit --strict on the exported lock + bun audit), **workflow-lint** (zizmor, pedantic persona - the workflows pass it with zero findings), **secrets** (gitleaks over the full history).
- `.github/workflows/codeql.yml`: CodeQL for Python + JavaScript with the `security-extended` query pack, on push/PR/weekly.
- `.github/workflows/scorecard.yml`: OpenSSF Scorecard weekly + on push, SARIF into code scanning; results are published to the OpenSSF API only if the repo is public.
- `.github/workflows/dependency-review.yml`: PRs that introduce a vulnerable (any severity) or GPL/AGPL/SSPL dependency are blocked.
- Every action is pinned to a full commit SHA (with the version as a comment; resolved from the tags on 2026-09-21), every workflow declares least-privilege `permissions` with a comment per grant, `persist-credentials: false` on every checkout, concurrency limits on every workflow. `tests/test_repo_policy.py` (8 tests) enforces all of that plus the Dependabot coverage and the presence of SECURITY.md/lockfiles - a workflow that drifts fails the test suite locally.
- `.github/dependabot.yml`: weekly grouped updates for **uv** (uv.lock), **bun** (bun.lock) and **github-actions** (it bumps the SHA pins). If your GitHub plan does not know the `uv`/`bun` ecosystems yet, change them to `pip`/`npm`.
- `SECURITY.md`: private vulnerability reporting via GitHub (no e-mail, consistent with the site), scope, response times.
- Not code, **your clicks** (Settings → Code security & analysis): Dependabot alerts ON, Dependabot security updates ON, grouped security updates ON, Secret scanning ON + Push protection ON, Private vulnerability reporting ON, Code scanning = the CodeQL workflow (turn OFF "default setup" so the two don't collide). Settings → Rules → New ruleset for `main`: require a PR, require status checks `Build, test, lint`, `Dependency audit`, `Workflow security lint`, `Secret scan`, `Analyze (python)`, `Analyze (javascript-typescript)`; require signed commits; block force pushes and deletions. Settings → Actions → General: "Allow actions by GitHub and verified creators" and **"Require actions to be pinned to a full-length commit SHA"**; Workflow permissions = "Read repository contents" and untick "Allow GitHub Actions to create and approve pull requests". Account: 2FA with a passkey/security key.
- Note: `gitleaks-action` is free for personal accounts; an organisation account needs a `GITLEAKS_LICENSE` secret. `dependency-review` and code scanning on a **private** repo need GitHub Advanced Security - on a free private repo those two workflows will report as skipped/failed; delete them or make the repo public.

**Cleanup**
- Deleted: orphan `templates/partials/header.html`, dead `static/js/file-input.js`, unused `app/services/cloudinary.py` (+ `cloudinary_cloud` setting), stock images, htmx.
- `maintenance.html`: asfalt/ink/betong, nonce on its `<style>`, fixed the `maintenance.avif` → `Maintenance.avif` case bug.
- Manifest: `#000000`, real icons (192/512 PNG + SVG). Favicon: `static/assets/brand/favicon.svg` (the proposed mark - S in Author 700 on maskin; **Jeffery's OK pending**, revert to the old inline SVG in `base.html` if not).
- **1435 → 1441 fix**: your run returned 400 on every request because your `.env` sets `ALLOWED_HOSTS=sandladan.se…` and TrustedHostMiddleware rejected the TestClient host `testserver` (my sandbox had no `.env`). `tests/conftest.py` now pins the test environment before `app` is imported (env vars beat `.env` in pydantic-settings): trusted-host off, maintenance off, `BASE_URL` empty, calendar off (no network), SMTP empty (no real e-mail from tests), `RATE_MAX=5`. The suite is independent of whatever your `.env` says.
- Tests (34): `tests/test_site.py` - pages render, every referenced `/static/...` asset exists on disk, no mailto/htmx/third-party, CSP + COOP headers, `/integritet`, status markup, form validation/honeypot/rate limit/byte-sniffing/escaping; `tests/test_render_images.py` - the crop math, every slot renders in both formats from a synthetic source, and every image record in `content.py` has all its renditions on disk.
- `pyproject.toml`: `pillow>=11.2` added to the `dev` extra (for the render script + its test), `pythonpath`/`testpaths` for pytest so `uv run pytest` works from the repo root, version 2.0.0. `uv.lock` re-locked with `uv lock` (adds pillow only).
- `main.py` and `app/__init__.py`: ruff-format only (so `ruff format --check .` is green in the chain) - no logic change.
- Line endings: CRLF kept as in base for every text file (LF only where the base had LF: `uv.lock`, `bun.lock`, `robots.txt`).

## Verified on the merged tree

- The drop-in chain above, run here from a clean unzip with `uv 0.8.17` + `bun`, three times (no `.env` / production-like `.env` / maintenance `.env`): `uv sync --all-extras` → `bun run build` (`styles.css` 22.4 KB, `site.js` 1.7 KB) → `pytest` 34 passed → `ruff check` clean → `ruff format --check` clean.
- Rendered in Chromium at 320/360/390/768/900/1024/1440 px: no horizontal overflow (two grid min-content bugs found and fixed: facts list and hero grid), all 6 images load, fonts load as `Satoshi 300 900` / `Author 200 700`, h1 renders at weight 700, status line swaps in, form posts via fetch and shows the notice, mobile menu opens/closes, zero console errors, CSP headers present.
- `static/dist/` is included as a convenience build; your `bun run build` overwrites it.

## Dev loop (after the chain is green)

```pwsh
uv run uvicorn main:app --reload
```
Then http://127.0.0.1:8000 and /integritet. To see the About facts locally, add to `.env`:
```
OWNER_PHONE=+46701234567
OWNER_PHONE_DISPLAY=070-123 45 67
ORG_NUMBER=5XXXXX-XXXX
OWNER_NAME=Jeffery Efternamn
OWNER_TITLE=Agare och gravmaskinist
LINKEDIN_URL=https://www.linkedin.com/company/sandladan-ab
```

Re-render photos after dropping originals into `assets-src/` (Pillow is in the dev extra now):
```pwsh
uv run python scripts/render_images.py && uv run pytest -q
```

## NOT done / needs you or Jeffery

1. **Facts**: org.nr, säte/adress, Jeffery's registered title (check Bolagsverket - "Ägare och grävmaskinist" vs "VD"), LinkedIn URL → `.env`. Until set, those rows are hidden. Phone stays hidden until you set `SHOW_PHONE=true` + `OWNER_PHONE`.
2. **Copy marked (förslag)** in `app/content.py`: services/gallery/about headlines and the About paragraph ("Du pratar direkt med den som kör maskinen." - only if literally true).
3. **Mark/favicon** approval; **photo originals** from Jeffery (2048 px copies are borderline for the 1920 hero rendition); a **portrait of Jeffery** for the `om` slot (then move `om-hytten` into the gallery as a `square` - one line in `content.py`).
4. **LinkedIn company page** - brief and profile-linking steps are in the design system (`guidelines/verifiability.md`); I cannot create it.
5. **Lighthouse re-run** on the deployed build - expected ≥ v1 (94) with htmx gone; the hero AVIF is heavier than the old stock hero (68 KB vs 17 KB at 768 px) because real gravel compresses worse - if LCP slips, drop `QUALITY_AVIF` to 50 or add a 640 rendition.
6. Not touched: `email.py`, `rate_limit.py`, deploy config, `.env` handling, Google Calendar mode.
7. Two pytest warnings come from starlette 1.6's test client (it now prefers `httpx2`); harmless, upstream, not ours. `uv sync --locked` is what CI runs - if you change `pyproject.toml`, run `uv lock` and commit `uv.lock` with it.

## Machine diff vs base (ADDED / MODIFIED / DELETED / UNCHANGED)

`DIFF.txt` beside this file, generated by sha256-hashing both trees (caches excluded; rendition sets collapsed to one line each).
