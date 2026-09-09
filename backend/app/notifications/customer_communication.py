"""Authenticated customer-requested email communication over the existing SMTP transport."""

import hashlib
from html import escape

from backend.app.notifications.email import EmailMessage, SmtpEmailProvider
from backend.app.repositories.capability_repo import CapabilityRepository


class CustomerCommunicationService:
    def __init__(self, conn, provider=None):
        self.repo = CapabilityRepository(conn)
        self.provider = provider or SmtpEmailProvider()

    def send(self, *, access_token: str, subject: str, lines: list[str],
             action_label: str | None = None, action_url: str | None = None,
             order_id: str | None = None, event_type: str | None = None) -> str:
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
        if action_label and action_url:
            text += f"\n\n{action_label}: {action_url}"
        action = (f"<p><a href='{escape(action_url, quote=True)}' style='display:inline-block;"
                  "background:#111;color:white;padding:14px 22px;text-decoration:none'>"
                  f"{escape(action_label)}</a></p>" if action_label and action_url else "")
        html = ("<!doctype html><html><body><main style='max-width:640px;margin:auto;"
                "font-family:Arial,sans-serif;color:#171717'><p style='letter-spacing:.25em;"
                "font-weight:700'>NEXGEN</p>" +
                "".join(f"<p>{escape(line)}</p>" for line in safe_lines) + action +
                "</main></body></html>")
        recipient_hash = hashlib.sha256(recipient.casefold().encode()).hexdigest()
        try:
            message_id = self.provider.send(EmailMessage(recipient=recipient, subject=subject,
                                                          html=html, text=text))
            if order_id and event_type:
                self.repo.record_notification(order_id,event_type,"smtp",recipient_hash,"SENT",message_id)
                self.repo.conn.commit()
            return message_id
        except Exception as exc:
            if order_id and event_type:
                self.repo.record_notification(order_id,event_type,"smtp",recipient_hash,"FAILED",
                                              failure_code=type(exc).__name__)
                self.repo.conn.commit()
            raise
