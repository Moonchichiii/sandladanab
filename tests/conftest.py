"""Isolate the test suite from the developer's local `.env`.

pydantic-settings gives real environment variables priority over `.env`, and
`app.config` builds its cached Settings at import time - so these are set here,
before any test module imports `app`. Without this, a production `.env`
(ALLOWED_HOSTS=sandladan.se, an ICS calendar URL, SMTP credentials, a stricter
rate limit) makes every TestClient request a 400 from TrustedHostMiddleware,
tries to fetch the calendar, or sends real e-mail from the tests.
"""

from __future__ import annotations

import os

os.environ.update(
    {
        "DISABLE_TRUSTED_HOST": "true",  # TestClient's host is "testserver"
        "ALLOWED_HOSTS": "",
        "MAINTENANCE_MODE": "false",
        "BASE_URL": "",  # canonical/schema use the request URL
        "CALENDAR_MODE": "off",  # no network from /api/status
        "CALENDAR_ICS_URL": "",
        "SMTP_HOST": "",  # EmailService.send becomes a no-op
        "MAIL_TO": "",
        "RATE_WINDOW": "60",
        "RATE_MAX": "5",  # test_offert_rate_limited counts on 5
        "HSTS_ENABLE": "false",
        "FORM_SECRET": "test-secret-not-for-production",  # stable form tokens
        "FORM_MIN_SECONDS": "3",  # the timing tests count on 3 s / 2 h
        "FORM_MAX_SECONDS": "7200",
    }
)
