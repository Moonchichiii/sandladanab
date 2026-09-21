"""Signed timestamp for the quote form (second spam layer after the honeypot).

The page renders a hidden field ``ts`` = ``"<unix seconds>.<HMAC-SHA256 hex>"``.
On submit the server checks the signature and the age of the token:

- ``fast``    submitted less than FORM_MIN_SECONDS after the page was rendered
              (a human cannot fill the form that quickly) -> treated as a bot
- ``missing`` no token at all (a real browser always posts the hidden field) -> bot
- ``invalid`` signature does not match (tampered, or the process restarted with an
              ephemeral secret) -> friendly "reload and try again" error
- ``expired`` older than FORM_MAX_SECONDS (a tab left open) -> same friendly error

No cookie, no JavaScript and no third-party service is involved, so the CSP and
the privacy page are unaffected. The token carries only a timestamp.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from typing import Literal

from app.config import settings

logger = logging.getLogger("sandladan")

Verdict = Literal["ok", "missing", "invalid", "fast", "expired"]

_SIG_HEX = 32  # 128 bits of the HMAC is plenty for a form token
_EPHEMERAL: list[bytes] = []  # filled on first use when FORM_SECRET is empty


def _secret() -> bytes:
    if settings.form_secret:
        return settings.form_secret.encode()
    if not _EPHEMERAL:
        _EPHEMERAL.append(secrets.token_bytes(32))
        logger.warning(
            "FORM_SECRET is not set; form tokens will not survive a restart "
            "(visitors get a 'reload and try again' message after a deploy)."
        )
    return _EPHEMERAL[0]


def _sign(stamp: str) -> str:
    return hmac.new(_secret(), stamp.encode(), hashlib.sha256).hexdigest()[:_SIG_HEX]


def mint(now: float | None = None) -> str:
    """Token for a page rendered at ``now`` (default: current time)."""
    stamp = str(int(now if now is not None else time.time()))
    return f"{stamp}.{_sign(stamp)}"


def verify(token: str | None, now: float | None = None) -> Verdict:
    if not token:
        return "missing"
    stamp, _, sig = token.partition(".")
    if not stamp.isdigit() or len(sig) != _SIG_HEX:
        return "invalid"
    if not hmac.compare_digest(_sign(stamp), sig):
        return "invalid"
    age = (now if now is not None else time.time()) - int(stamp)
    if age < settings.form_min_seconds:
        return "fast"
    if age > settings.form_max_seconds:
        return "expired"
    return "ok"
