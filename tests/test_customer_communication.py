import unittest

from backend.app.notifications.customer_communication import CustomerCommunicationService


class FakeRepo:
    def __init__(self): self.notifications=[]; self.conn=type('Conn',(),{'commit':lambda self:None})()
    def get_auth_session(self, _token_hash):
        return {"customer_id": "customer-1"}
    def verified_destinations(self, _customer_id):
        return {"email": "customer@example.com", "phone": None}
    def record_notification(self,*args,**kwargs): self.notifications.append((args,kwargs))


class FakeProvider:
    def __init__(self): self.message = None
    def send(self, message): self.message = message; return "accepted"

class FailingProvider:
    def send(self, _message): raise RuntimeError("SMTP unavailable")


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

    def test_order_email_records_delivery_without_storing_recipient(self):
        service=CustomerCommunicationService(None,provider=FakeProvider()); service.repo=FakeRepo()
        service.send(access_token='token',subject='Order',lines=['Status: PENDING_PAYMENT'],
                     order_id='order-1',event_type='ORDER_REQUEST_RECEIVED')
        args,_=service.repo.notifications[0]
        self.assertEqual((args[0],args[1],args[4]),('order-1','ORDER_REQUEST_RECEIVED','SENT'))
        self.assertNotEqual(args[3],'customer@example.com')

    def test_smtp_failure_is_recorded_and_does_not_hide_failure(self):
        service=CustomerCommunicationService(None,provider=FailingProvider()); service.repo=FakeRepo()
        with self.assertRaisesRegex(RuntimeError,'SMTP unavailable'):
            service.send(access_token='token',subject='Order',lines=['Order created'],
                         order_id='order-1',event_type='ORDER_REQUEST_RECEIVED')
        args,kwargs=service.repo.notifications[0]
        self.assertEqual(args[4],'FAILED'); self.assertEqual(kwargs['failure_code'],'RuntimeError')


if __name__ == "__main__": unittest.main()
