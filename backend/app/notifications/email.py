"""Replaceable transactional email transport with an SMTP implementation."""

from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr
import smtplib
from typing import Protocol

from backend.app.config import settings


@dataclass(frozen=True)
class EmailMessage:
    recipient: str
    subject: str
    html: str
    text: str


class EmailProvider(Protocol):
    def send(self, message: EmailMessage) -> str: ...


class SmtpEmailProvider:
    """Send an email without logging credentials or recipient content."""

    def send(self, message: EmailMessage) -> str:
        if not all((settings.email_from_address, settings.smtp_username, settings.smtp_password)):
            raise RuntimeError("Transactional email is not configured.")
        mime = MimeMessage()
        mime["From"] = formataddr((settings.email_from_name, settings.email_from_address))
        mime["To"] = message.recipient
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        mime.add_alternative(message.html, subtype="html")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
            if settings.smtp_use_tls:
                client.starttls()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(mime)
        return mime["Message-ID"] or "accepted"
