import unittest

from backend.app.notifications.templates import EVENT_TITLES, OrderEmailItem, render_order_email


class EmailTemplateTests(unittest.TestCase):
    def test_every_supported_lifecycle_event_renders(self):
        for event in EVENT_TITLES:
            message = render_order_email(event=event, recipient="customer@example.com", order_id="NX-100", items=[OrderEmailItem("Silk Shirt", "M", "Black")], shipping_address="10 Main St", estimated_delivery="September 12", tracking_url="https://example.com/orders/NX-100")
            self.assertIn("NX-100", message.subject)
            self.assertIn("Track order", message.html)

    def test_customer_content_is_html_escaped(self):
        message = render_order_email(event="ORDER_CREATED", recipient="customer@example.com", order_id="<script>", items=[OrderEmailItem("<img>", "M", "Black")], shipping_address="<b>home</b>", estimated_delivery="Soon", tracking_url='https://example.com/?q="x"')
        self.assertNotIn("<script>", message.html)
        self.assertNotIn("<img>", message.html)
        self.assertNotIn("<b>home</b>", message.html)


if __name__ == "__main__":
    unittest.main()
