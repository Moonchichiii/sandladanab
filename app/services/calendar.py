from __future__ import annotations

import time
from datetime import datetime, timedelta

import httpx
from dateutil import tz
from icalendar import Calendar

from app.config import settings


class CalendarService:
    _cache_text: str = settings.lediga_text
    _cache_ts: float = 0.0

    @classmethod
    async def get_status_text(cls) -> str:
        if settings.calendar_mode != "ics" or not settings.calendar_ics_url:
            return settings.lediga_text

        now = time.monotonic()
        if now - cls._cache_ts < settings.status_cache_ttl and cls._cache_text:
            return cls._cache_text

        try:
            text = await cls._fetch_availability()
            cls._cache_text = text
            cls._cache_ts = now
            return text
        except Exception:
            return cls._cache_text or settings.lediga_text

    @classmethod
    async def _fetch_availability(cls) -> str:
        tzinfo = tz.gettz(settings.timezone)
        horizon = datetime.now(tzinfo) + timedelta(
            weeks=settings.availability_weeks_ahead,
        )

        async with httpx.AsyncClient(timeout=4.0, http2=True) as client:
            resp = await client.get(
                settings.calendar_ics_url,
                headers={"User-Agent": "sandladan/1.0"},
            )
            resp.raise_for_status()
            cal = Calendar.from_ical(resp.content)

        busy_weeks: set[int] = set()
        for comp in cal.walk("VEVENT"):
            dtstart = comp.get("DTSTART")
            if not dtstart:
                continue
            dtend = comp.get("DTEND") or dtstart

            s, e = dtstart.dt, dtend.dt
            if hasattr(s, "astimezone"):
                s = s.astimezone(tzinfo)
            if hasattr(e, "astimezone"):
                e = e.astimezone(tzinfo)
            if s > horizon:
                continue

            d = s
            while d <= e:
                busy_weeks.add(d.isocalendar().week)
                d += timedelta(days=1)

        today = datetime.now(tzinfo).date()
        start_week = today.isocalendar().week
        free: list[int] = []
        for offset in range(settings.availability_weeks_ahead + 1):
            w = ((start_week - 1 + offset) % 52) + 1
            if w not in busy_weeks:
                free.append(w)
                if len(free) >= 2:
                    break

        if free:
            weeks_str = str(free[0]) if len(free) == 1 else f"{free[0]}–{free[1]}"
            return f"Lediga v. {weeks_str} • Snabbt platsbesök i Göteborg med omnejd"
        return settings.lediga_text
