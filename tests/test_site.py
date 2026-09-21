"""Smoke tests for the v2 site: pages render, every referenced static asset exists,
the API keeps its contract, and the security decisions hold (no e-mail on the page,
no third-party scripts, strict CSP).

Run:  uv run pytest -q     (or: python -m pytest -q)
"""

from __future__ import annotations

import pathlib
import re

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.services.rate_limit import RateLimiter

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 1x1 PNG
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


@pytest.fixture()
def client() -> TestClient:
    RateLimiter.reset()
    return TestClient(create_app())


def _static_paths(html: str) -> set[str]:
    return set(re.findall(r'(?:src|href|srcset|imagesrcset)="([^"]*)"', html)) | set(
        re.findall(r"/static/[\w./-]+", html)
    )


def test_index_renders_and_every_static_asset_exists(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "Sandlådan AB" in html
    assert (
        'id="tjanster"' in html
        and 'id="galleri"' in html
        and 'id="om"' in html
        and 'id="offert"' in html
    )

    missing = []
    for ref in _static_paths(html):
        for url in re.findall(r"/static/[\w./-]+", ref):
            if not (ROOT / url.lstrip("/")).is_file():
                missing.append(url)
    assert not missing, f"referenced but missing on disk: {sorted(set(missing))}"


def test_no_email_no_htmx_no_third_party(client: TestClient) -> None:
    html = client.get("/").text
    assert (
        "@" not in re.sub(r"<[^>]+>", "", html).replace("&#64;", "@")
        or "mailto:" not in html
    )
    assert "mailto:" not in html
    assert "htmx" not in html.lower()
    # only same-origin scripts, styles and preloads (canonical is absolute on purpose)
    for src in re.findall(r'<script[^>]+src="([^"]+)"', html):
        assert src.startswith("/"), src
    for href in re.findall(r'<link[^>]+href="([^"]+)"', html):
        assert href.startswith("/") or href.startswith("http://testserver"), href


def test_security_headers_keep_observatory_a_plus(client: TestClient) -> None:
    """Mozilla HTTP Observatory: sandladan.se is A+ (110/100) and must stay there."""
    r = client.get("/")
    csp = r.headers["content-security-policy"]
    assert "'unsafe-inline'" not in csp and "data:" not in csp and "https:" not in csp
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp
    assert "base-uri 'self'" in csp
    assert r.headers["cross-origin-opener-policy"] == "same-origin"
    assert r.headers["cross-origin-resource-policy"] == "same-origin"
    assert r.headers["cross-origin-embedder-policy"] == "require-corp"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "set-cookie" not in r.headers


def test_dist_assets_have_sri_and_cache_buster(client: TestClient) -> None:
    html = client.get("/").text
    css = re.search(r'<link rel="stylesheet" href="([^"]+)"([^>]*)>', html)
    js = re.search(r'<script src="(/dist/site\.js[^"]*)"([^>]*)>', html)
    assert css and js
    if (ROOT / "static" / "dist" / "styles.css").is_file():
        assert "?v=" in css.group(1) and 'integrity="sha384-' in css.group(2)
        assert "?v=" in js.group(1) and 'integrity="sha384-' in js.group(2)
        # the served file must match the advertised hash
        r = client.get(css.group(1))
        assert r.status_code == 200
        import base64
        import hashlib

        want = re.search(r'integrity="sha384-([^"]+)"', css.group(2)).group(1)
        assert base64.b64encode(hashlib.sha384(r.content).digest()).decode() == want


def test_open_graph_preview_tags(client: TestClient) -> None:
    html = client.get("/").text
    for prop in (
        "og:type",
        "og:site_name",
        "og:url",
        "og:title",
        "og:description",
        "og:image",
    ):
        assert f'property="{prop}"' in html, prop
    og = re.search(r'property="og:image" content="([^"]+)"', html).group(1)
    assert og.endswith("/static/assets/brand/og-image.jpg")
    assert (ROOT / "static" / "assets" / "brand" / "og-image.jpg").is_file()


def test_phone_hidden_by_default(client: TestClient) -> None:
    """Decision 2026-09-21: the company phone is not published for now."""
    html = client.get("/").text
    assert "tel:" not in html
    assert "Ring direkt" not in html
    assert "<dt>Telefon</dt>" not in html
    assert '"telephone"' not in html
    assert html.count("Begär offert") >= 4  # header, sheet, hero, footer
    assert "tel:" not in client.get("/integritet").text


def test_phone_shown_with_flag(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "show_phone", True)
    monkeypatch.setattr(settings, "owner_phone", "+46701234567")
    monkeypatch.setattr(settings, "owner_phone_display", "070-123 45 67")
    html = client.get("/").text
    assert 'href="tel:+46701234567"' in html
    assert "Ring direkt" in html
    assert "<dt>Telefon</dt>" in html
    assert '"telephone": "+46701234567"' in html


def test_integritet_page(client: TestClient) -> None:
    r = client.get("/integritet")
    assert r.status_code == 200
    assert "Personuppgiftsansvarig" in r.text
    assert "imy.se" in r.text


def test_status_line_is_server_rendered(client: TestClient) -> None:
    html = client.get("/").text
    status = re.search(r'<p class="status" id="status"[^>]*>(.*?)</p>', html, re.S)
    assert status and "status__dot--live" in status.group(1)
    assert "Tillgänglig för uppdrag" in status.group(1)
    assert "Kontrollerar" not in html  # no loading state
    assert "data-status-url" not in html  # calendar mode off → no request


def test_status_line_markup(client: TestClient) -> None:
    r = client.get("/api/status")
    assert r.status_code == 200
    assert 'class="status__dot status__dot--live"' in r.text
    assert r.headers["cache-control"] == "no-store"


def test_offert_requires_phone(client: TestClient) -> None:
    r = client.post("/api/offert", data={"namn": "Anna", "telefon": " "})
    assert r.status_code == 422
    assert "Ange ditt telefonnummer." in r.text
    assert 'class="notice notice--err"' in r.text


def test_offert_honeypot_swallows_bots(client: TestClient) -> None:
    r = client.post(
        "/api/offert", data={"namn": "Bot", "telefon": "1", "website": "http://spam"}
    )
    assert r.status_code == 200
    assert "Tack!" in r.text


def test_offert_rejects_fake_image_by_bytes(client: TestClient) -> None:
    r = client.post(
        "/api/offert",
        data={"namn": "Anna", "telefon": "0701234567"},
        files={"bild": ("x.jpg", b"<html>not an image</html>", "image/jpeg")},
    )
    assert r.status_code == 422
    assert "Bara bilder" in r.text


def test_offert_accepts_real_png_and_echoes_phone(client: TestClient) -> None:
    r = client.post(
        "/api/offert",
        data={
            "namn": "Anna <b>Test</b>",
            "telefon": "0701234567",
            "beskrivning": "Dränering",
        },
        files={"bild": ("foto.png", PNG, "image/png")},
    )
    assert r.status_code == 200
    assert "Tack Anna &lt;b&gt;Test&lt;/b&gt;!" in r.text  # escaped
    assert "0701234567" in r.text


def test_offert_rate_limited(client: TestClient) -> None:
    for _ in range(5):
        client.post("/api/offert", data={"namn": "A", "telefon": "1"})
    r = client.post("/api/offert", data={"namn": "A", "telefon": "1"})
    assert r.status_code == 429


def test_sniff_image() -> None:
    from app.routes.api import _sniff_image

    assert _sniff_image(PNG) == "png"
    assert _sniff_image(b"\xff\xd8\xff\xe0" + b"\0" * 20) == "jpg"
    assert _sniff_image(b"RIFF\0\0\0\0WEBPVP8 ") == "webp"
    assert _sniff_image(b"\0\0\0\x1cftypavif\0\0\0\0avifmif1") == "avif"
    assert _sniff_image(b"GIF89a") is None
