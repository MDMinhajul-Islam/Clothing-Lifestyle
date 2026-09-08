"""Reusable, escaped HTML templates for order lifecycle email."""

from dataclasses import dataclass
from html import escape
from typing import Iterable

from backend.app.notifications.email import EmailMessage


EVENT_TITLES = {
    "ORDER_CREATED": "Confirm your NexGen order",
    "ORDER_CONFIRMED": "Your order is confirmed",
    "ORDER_PACKED": "Your order is packed",
    "ORDER_SHIPPED": "Your order is on its way",
    "DELIVERED": "Your order has arrived",
    "RETURN_REQUESTED": "We received your return request",
    "RETURN_APPROVED": "Your return is approved",
    "EXCHANGE_REQUESTED": "We received your exchange request",
    "EXCHANGE_APPROVED": "Your exchange is approved",
    "EXCHANGE_SHIPPED": "Your exchange is on its way",
    "ORDER_CANCELLED": "Your order is cancelled",
}


@dataclass(frozen=True)
class OrderEmailItem:
    name: str
    size: str
    color: str
    quantity: int = 1


def render_order_email(*, event: str, recipient: str, order_id: str, items: Iterable[OrderEmailItem], shipping_address: str, estimated_delivery: str, tracking_url: str) -> EmailMessage:
    title = EVENT_TITLES[event]
    rows = "".join(f"<tr><td>{escape(item.name)}</td><td>{escape(item.size)}</td><td>{escape(item.color)}</td><td>{item.quantity}</td></tr>" for item in items)
    safe_order = escape(order_id)
    html = f"""<!doctype html><html><body style="margin:0;background:#f5f3ee;font-family:Arial,sans-serif;color:#171717"><main style="max-width:640px;margin:auto;background:white;padding:40px"><p style="letter-spacing:.28em;font-weight:700">NEXGEN</p><h1>{escape(title)}</h1><p>Order <strong>{safe_order}</strong></p><table style="width:100%;border-collapse:collapse"><thead><tr><th align="left">Product</th><th align="left">Size</th><th align="left">Color</th><th align="left">Qty</th></tr></thead><tbody>{rows}</tbody></table><h2>Shipping address</h2><p>{escape(shipping_address)}</p><p>Estimated delivery: {escape(estimated_delivery)}</p><p><a href="{escape(tracking_url, quote=True)}" style="display:inline-block;background:#111;color:white;padding:14px 22px;text-decoration:none">Track order</a></p></main></body></html>"""
    text = f"{title}\nOrder {order_id}\nShipping address: {shipping_address}\nEstimated delivery: {estimated_delivery}\nTrack order: {tracking_url}"
    return EmailMessage(recipient=recipient, subject=f"{title} — {order_id}", html=html, text=text)
