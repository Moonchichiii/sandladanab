from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings


class EmailService:
    @staticmethod
    def build(
        subject: str,
        body_html: str,
        body_text: str,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.effective_mail_from
        msg["To"] = settings.mail_to
        msg.set_content(body_text)
        msg.add_alternative(body_html, subtype="html")

        for filename, data, mime in attachments or []:
            maintype, _, subtype = mime.partition("/")
            msg.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )
        return msg

    @staticmethod
    def send(msg: EmailMessage) -> None:
        if not settings.smtp_ready:
            return

        ctx = ssl.create_default_context()
        try:
            if settings.smtp_port == 465 and not settings.smtp_starttls:
                with smtplib.SMTP_SSL(
                    settings.smtp_host, settings.smtp_port, context=ctx
                ) as s:
                    if settings.smtp_user and settings.smtp_pass:
                        s.login(settings.smtp_user, settings.smtp_pass)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
                    if settings.smtp_starttls:
                        s.starttls(context=ctx)
                    if settings.smtp_user and settings.smtp_pass:
                        s.login(settings.smtp_user, settings.smtp_pass)
                    s.send_message(msg)
        except Exception as exc:
            # TODO: structured logging
            print(f"[EmailService] send failed: {exc}")
