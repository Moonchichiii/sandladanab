from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────
    base_url: str = ""
    debug: bool = False
    maintenance_mode: bool = False

    # ── Security ─────────────────────────────────────
    allowed_hosts: str = ""
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    hsts_enable: bool = False
    disable_trusted_host: bool = False

    # ── Contact ──────────────────────────────────────
    owner_phone: str = "+46XXXXXXXX"
    public_email: str = "info@sandladan.se"

    # ── SMTP ─────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_starttls: bool = True
    mail_from: str = ""
    mail_to: str = ""

    # ── Rate Limit ───────────────────────────────────
    rate_window: int = 60
    rate_max: int = 5

    # ── Calendar ─────────────────────────────────────
    calendar_mode: str = "ics"
    calendar_ics_url: str = ""
    timezone: str = "Europe/Stockholm"
    availability_weeks_ahead: int = 6
    status_cache_ttl: int = 1800
    lediga_text: str = (
        "Tillgänglig för uppdrag \u2022 Snabbt platsbesök i Göteborg med omnejd"
    )

    # ── Google Calendar (optional) ───────────────────
    gcal_service_account_json_path: str = ""
    gcal_calendar_id: str = ""

    # ── Cloudinary ───────────────────────────────────
    cloudinary_cloud: str = ""  # e.g. "dxxxxxx"

    # ── Parsed properties ────────────────────────────

    @property
    def allowed_hosts_list(self) -> list[str]:
        if not self.allowed_hosts:
            return []
        result: list[str] = []
        for item in self.allowed_hosts.split(","):
            item = item.strip()
            if not item:
                continue
            item = (
                item.replace("https://", "")
                .replace("http://", "")
                .split("/")[0]
                .split(":")[0]
            )
            result.append(item)
        return result

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        result: list[str] = []
        for origin in self.cors_origins.split(","):
            origin = origin.strip()
            if not origin:
                continue
            if not origin.startswith(("http://", "https://")):
                origin = f"https://{origin}"
            result.append(origin)
        return result

    @property
    def effective_mail_from(self) -> str:
        return self.mail_from or self.smtp_user or "no-reply@sandladan.se"

    @property
    def smtp_ready(self) -> bool:
        return bool(self.smtp_host and self.smtp_port and self.mail_to)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
