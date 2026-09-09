"""Authenticated customer-requested email communication over the existing SMTP transport."""

import hashlib
from html import escape

from backend.app.notifications.email import EmailMessage, SmtpEmailProvider
from backend.app.repositories.capability_repo import CapabilityRepository


class CustomerCommunicationService:
    def __init__(self, conn, provider=None):
        self.repo = CapabilityRepository(conn)
        self.provider = provider or SmtpEmailProvider()

    def send(self, *, access_token: str, subject: str, lines: list[str]) -> str:
        token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        auth = self.repo.get_auth_session(token_hash)
        if not auth:
            raise PermissionError("Verified access is required.")
        destinations = self.repo.verified_destinations(auth["customer_id"])
        recipient = (destinations or {}).get("email")
        if not recipient:
            raise ValueError("No verified email address is available.")
        safe_lines = [str(line).strip() for line in lines if str(line).strip()]
        text = "NexGen\n\n" + "\n".join(safe_lines)
        html = ("<!doctype html><html><body><main style='max-width:640px;margin:auto;"
                "font-family:Arial,sans-serif;color:#171717'><p style='letter-spacing:.25em;"
                "font-weight:700'>NEXGEN</p>" +
                "".join(f"<p>{escape(line)}</p>" for line in safe_lines) +
                "</main></body></html>")
        return self.provider.send(EmailMessage(recipient=recipient, subject=subject,
                                               html=html, text=text))
