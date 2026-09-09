import unittest

from backend.app.notifications.customer_communication import CustomerCommunicationService


class FakeRepo:
    def get_auth_session(self, _token_hash):
        return {"customer_id": "customer-1"}
    def verified_destinations(self, _customer_id):
        return {"email": "customer@example.com", "phone": None}


class FakeProvider:
    def __init__(self): self.message = None
    def send(self, message): self.message = message; return "accepted"


class CustomerCommunicationTests(unittest.TestCase):
    def test_uses_verified_email_and_escapes_html(self):
        provider = FakeProvider()
        service = CustomerCommunicationService(None, provider=provider)
        service.repo = FakeRepo()
        result = service.send(access_token="token", subject="Selections",
                              lines=["Silk <Dress>"])
        self.assertEqual(result, "accepted")
        self.assertEqual(provider.message.recipient, "customer@example.com")
        self.assertIn("Silk &lt;Dress&gt;", provider.message.html)
        self.assertNotIn("Silk <Dress>", provider.message.html)


if __name__ == "__main__": unittest.main()
