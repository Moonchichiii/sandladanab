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
    # 2026-09-21: the company phone is not published for now. SHOW_PHONE=true brings
    # back every "Ring direkt" button, the Telefon fact and schema.org telephone.
    show_phone: bool = False
    owner_phone: str = ""  # E.164, used in tel: links when show_phone is on
    owner_phone_display: str = (
        ""  # how it is printed ("070-123 45 67"); falls back to owner_phone
    )
    # NOT rendered anywhere (decision 2026-09-21); only the mail_from fallback
    public_email: str = "info@sandladan.se"

    # ── Verifiability (empty = the row is not rendered) ──
    org_number: str = ""  # "5XXXXX-XXXX" as registered at Bolagsverket
    seat: str = "Göteborg"  # säte / municipality
    postal_address: str = ""  # optional; only shown on /integritet if set
    owner_name: str = ""  # "Jeffery Efternamn"
    owner_title: str = (
        ""  # exactly as registered: e.g. "Ägare och grävmaskinist" or "VD"
    )
    linkedin_url: str = ""  # https://www.linkedin.com/company/sandladan-ab

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
        "Tillgänglig för uppdrag \u00b7 Snabbt platsbesök i Göteborg med omnejd"
    )

    # ── Google Calendar (optional) ───────────────────
    gcal_service_account_json_path: str = ""
    gcal_calendar_id: str = ""

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
    def phone_display(self) -> str:
        return self.owner_phone_display or self.owner_phone

    @property
    def phone_public(self) -> bool:
        return bool(self.show_phone and self.owner_phone)

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
