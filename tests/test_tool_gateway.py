"""Unit and Integration Tests for AI Tool Gateway (Phase 2C)."""

import os
import unittest
from fastapi.testclient import TestClient
import psycopg2

from backend.app.config import settings
from backend.app.main import app
from backend.app.db import get_db_connection
from backend.app.rules.cancellation import CancellationRules
from backend.app.rules.returns import ReturnRules
from backend.app.rules.inventory import InventoryRules
from backend.app.rules.exchanges import ExchangeRules
from backend.app.utils.security import (
    generate_confirmation_token,
    verify_confirmation_token,
    hash_request_payload,
)
from backend.app.utils.geo import haversine_distance_miles


class TestToolGatewaySecurity(unittest.TestCase):
    """Test security, HMAC confirmation tokens, and request hashing."""

    def test_confirmation_token_lifecycle(self):
        token = generate_confirmation_token("cancel_order", "ZUS-2025-99999")
        self.assertTrue(bool(token))
        self.assertIn(".", token)

        # Valid verification
        valid = verify_confirmation_token(token, "cancel_order", "ZUS-2025-99999")
        self.assertTrue(valid)

        # Mismatched action
        invalid_action = verify_confirmation_token(token, "create_return", "ZUS-2025-99999")
        self.assertFalse(invalid_action)

        # Mismatched entity
        invalid_entity = verify_confirmation_token(token, "cancel_order", "ZUS-2025-00001")
        self.assertFalse(invalid_entity)

        # Tampered token
        tampered = token[:-4] + "abcd"
        self.assertFalse(verify_confirmation_token(tampered, "cancel_order", "ZUS-2025-99999"))

    def test_haversine_distance(self):
        # Distance between NYC (40.7128, -74.0060) and LA (34.0522, -118.2437) ~ 2445 miles
        dist = haversine_distance_miles(40.7128, -74.0060, 34.0522, -118.2437)
        self.assertGreater(dist, 2400)
        self.assertLess(dist, 2500)

    def test_request_payload_hashing(self):
        payload_1 = {"order_number": "ZUS-2025-00001", "reason": "Size issue"}
        payload_2 = {"reason": "Size issue", "order_number": "ZUS-2025-00001"}
        # Hash should be deterministic and order-independent
        self.assertEqual(hash_request_payload(payload_1), hash_request_payload(payload_2))


class TestBusinessRules(unittest.TestCase):
    """Test deterministic business rule evaluations."""

    def test_cancellation_rules(self):
        # Pending and confirmed orders are cancellable
        eligible, reason, act = CancellationRules.evaluate_cancellation_eligibility({"order_status": "CONFIRMED"})
        self.assertTrue(eligible)
        self.assertEqual(act, "CANCEL_ORDER")

        # Shipped and delivered orders are NOT cancellable
        eligible, reason, act = CancellationRules.evaluate_cancellation_eligibility({"order_status": "SHIPPED"})
        self.assertFalse(eligible)
        self.assertEqual(act, "TRACK_ORDER_OR_RETURN_AFTER_DELIVERY")

        eligible, reason, act = CancellationRules.evaluate_cancellation_eligibility({"order_status": "DELIVERED"})
        self.assertFalse(eligible)
        self.assertEqual(act, "INITIATE_RETURN")

    def test_inventory_rules(self):
        # Out of stock
        avail, status = InventoryRules.calculate_availability(10, 10)
        self.assertEqual(avail, 0)
        self.assertEqual(status, "OUT_OF_STOCK")

        # Low stock
        avail, status = InventoryRules.calculate_availability(10, 7)
        self.assertEqual(avail, 3)
        self.assertEqual(status, "LOW_STOCK")

        # In stock
        avail, status = InventoryRules.calculate_availability(20, 5)
        self.assertEqual(avail, 15)
        self.assertEqual(status, "IN_STOCK")


class TestToolGatewayAPI(unittest.TestCase):
    """Integration tests running against the FastAPI test client and live database."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.secret = settings.tool_gateway_secret
        cls.headers = {
            "X-Tool-Secret": cls.secret,
            "Content-Type": "application/json"
        }

    def test_authentication_protection(self):
        # Missing header -> 401
        res = self.client.post("/v1/tools/search-products", json={"limit": 5})
        self.assertEqual(res.status_code, 401)

        # Invalid secret -> 401
        res = self.client.post(
            "/v1/tools/search-products",
            headers={"X-Tool-Secret": "wrong-secret"},
            json={"limit": 5}
        )
        self.assertEqual(res.status_code, 401)

        # Valid secret -> 200
        res = self.client.post(
            "/v1/tools/search-products",
            headers=self.headers,
            json={"limit": 5}
        )
        self.assertEqual(res.status_code, 200)

    def test_search_products_tool(self):
        # 1. Text search with filters
        res = self.client.post(
            "/v1/tools/search-products",
            headers=self.headers,
            json={"query": "linen", "department": "MAN", "limit": 5}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertGreaterEqual(body["data"]["total_matching"], 1)
        self.assertLessEqual(body["data"]["returned_count"], 5)
        first_product = body["data"]["products"][0]
        self.assertIn("product_id", first_product)
        self.assertIn("name", first_product)
        self.assertIn("price", first_product)

    def test_get_product_details_tool(self):
        # Fetch known product details
        res = self.client.post(
            "/v1/tools/get-product-details",
            headers=self.headers,
            json={"product_id": "zara-us:00029400"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["product_id"], "zara-us:00029400")
        self.assertGreater(len(body["data"]["variants"]), 0)
        self.assertGreater(len(body["data"]["colors"]), 0)
        self.assertGreater(len(body["data"]["images"]), 0)

        # Product not found error
        res = self.client.post(
            "/v1/tools/get-product-details",
            headers=self.headers,
            json={"product_id": "zara-us:99999999"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "PRODUCT_NOT_FOUND")

    def test_compare_products_tool(self):
        res = self.client.post(
            "/v1/tools/compare-products",
            headers=self.headers,
            json={"product_ids": ["zara-us:00029400", "zara-us:07446735"]}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["compared_count"], 2)

    def test_check_inventory_tool(self):
        res = self.client.post(
            "/v1/tools/check-inventory",
            headers=self.headers,
            json={"product_id": "zara-us:04302360"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertGreater(len(body["data"]["matching_variants"]), 0)

    def test_find_stores_tool(self):
        # By city/state
        res = self.client.post(
            "/v1/tools/find-stores",
            headers=self.headers,
            json={"state": "CA", "limit": 5}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertGreater(body["data"]["total_matching"], 0)
        self.assertTrue(body["data"]["stores"][0]["is_synthetic"])

        # By coordinates (Chicago area: 41.8781, -87.6298)
        res = self.client.post(
            "/v1/tools/find-stores",
            headers=self.headers,
            json={"latitude": 41.8781, "longitude": -87.6298, "limit": 3}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertIsNotNone(body["data"]["stores"][0]["distance_miles"])

    def test_get_customer_tool(self):
        # By email
        res = self.client.post(
            "/v1/tools/get-customer",
            headers=self.headers,
            json={"email": "scarlett.torres.0026@demo-synthetic.example.com"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["first_name"], "Scarlett")
        self.assertEqual(body["data"]["last_name"], "Torres")

        # Empty identifier error
        res = self.client.post(
            "/v1/tools/get-customer",
            headers=self.headers,
            json={}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "CUSTOMER_NOT_FOUND")

    def test_get_order_and_tracking_tool(self):
        # Order details
        res = self.client.post(
            "/v1/tools/get-order",
            headers=self.headers,
            json={"order_number": "ZUS-2025-00002"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["order_number"], "ZUS-2025-00002")
        self.assertEqual(len(body["data"]["items"]), 3)

        # Tracking
        res = self.client.post(
            "/v1/tools/track-order",
            headers=self.headers,
            json={"order_number": "ZUS-2025-00002"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["carrier"], "USPS")
        self.assertGreater(len(body["data"]["events"]), 0)

    def test_check_cancellation_eligibility_tool(self):
        # Delivered order -> Not cancellable
        res = self.client.post(
            "/v1/tools/check-cancellation-eligibility",
            headers=self.headers,
            json={"order_number": "ZUS-2025-00002"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertFalse(body["data"]["eligible"])

    def test_cancellation_confirmation_and_idempotency_flow(self):
        # Find a CONFIRMED synthetic order from DB
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT order_number FROM orders WHERE order_status = 'CONFIRMED' LIMIT 1;")
                row = cur.fetchone()
                test_order = row[0]

        # STEP 1: Attempt cancellation without confirmation
        res1 = self.client.post(
            "/v1/tools/cancel-order",
            headers=self.headers,
            json={"order_number": test_order, "confirmed": False}
        )
        self.assertEqual(res1.status_code, 200)
        body1 = res1.json()
        self.assertFalse(body1["success"])
        self.assertEqual(body1["error"]["code"], "CONFIRMATION_REQUIRED")
        self.assertIsNotNone(body1["confirmation"])
        conf_token = body1["confirmation"]["confirmation_token"]

        # STEP 2: Cancel with valid confirmation token and idempotency key
        test_idempotency_key = f"test-cancel-{test_order}-key-01"
        res2 = self.client.post(
            "/v1/tools/cancel-order",
            headers=self.headers,
            json={
                "order_number": test_order,
                "confirmed": True,
                "confirmation_token": conf_token,
                "idempotency_key": test_idempotency_key
            }
        )
        self.assertEqual(res2.status_code, 200)
        body2 = res2.json()
        self.assertTrue(body2["success"])
        self.assertEqual(body2["data"]["order_status"], "CANCELLED")
        self.assertFalse(body2["meta"]["cached"])

        # STEP 3: Replay with same idempotency key and same payload -> returns cached response
        res3 = self.client.post(
            "/v1/tools/cancel-order",
            headers=self.headers,
            json={
                "order_number": test_order,
                "confirmed": True,
                "confirmation_token": conf_token,
                "idempotency_key": test_idempotency_key
            }
        )
        self.assertEqual(res3.status_code, 200)
        body3 = res3.json()
        self.assertTrue(body3["success"])
        self.assertTrue(body3["meta"]["cached"])

        # STEP 4: Replay with same key but DIFFERENT payload -> returns IDEMPOTENCY_CONFLICT
        res4 = self.client.post(
            "/v1/tools/cancel-order",
            headers=self.headers,
            json={
                "order_number": test_order,
                "reason": "Completely different reason here",
                "confirmed": True,
                "confirmation_token": conf_token,
                "idempotency_key": test_idempotency_key
            }
        )
        self.assertEqual(res4.status_code, 200)
        body4 = res4.json()
        self.assertFalse(body4["success"])
        self.assertEqual(body4["error"]["code"], "IDEMPOTENCY_CONFLICT")

    def test_return_eligibility_and_refund_status(self):
        # Check return eligibility
        res = self.client.post(
            "/v1/tools/check-return-eligibility",
            headers=self.headers,
            json={"order_number": "ZUS-2025-00002"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])

        # Check refund status
        res = self.client.post(
            "/v1/tools/get-refund-status",
            headers=self.headers,
            json={"order_number": "ZUS-2025-00002"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertGreater(body["data"]["total_refunds"], 0)

    def test_create_return_confirmation_and_execution(self):
        # Dynamically find an eligible delivered order within the 30-day window
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT o.order_number, oi.order_item_id
                    FROM orders o
                    JOIN shipments s ON o.order_id = s.order_id
                    JOIN order_items oi ON o.order_id = oi.order_id
                    WHERE o.order_status = 'DELIVERED'
                      AND s.shipped_at + interval '30 days' >= now()
                      AND NOT EXISTS (
                          SELECT 1 FROM return_items ri WHERE ri.order_item_id = oi.order_item_id
                      )
                    LIMIT 1;
                    """
                )
                row = cur.fetchone()
                order_num = row[0]
                item_id = row[1]

        # Step 1: Call without confirmation -> CONFIRMATION_REQUIRED
        res1 = self.client.post(
            "/v1/tools/create-return",
            headers=self.headers,
            json={
                "order_number": order_num,
                "items": [{"order_item_id": item_id, "quantity": 1, "reason_code": "DOES_NOT_FIT"}],
                "return_method": "STORE",
                "confirmed": False
            }
        )
        self.assertEqual(res1.status_code, 200)
        body1 = res1.json()
        self.assertFalse(body1["success"])
        self.assertEqual(body1["error"]["code"], "CONFIRMATION_REQUIRED")
        self.assertIsNotNone(body1["confirmation"])
        conf_token = body1["confirmation"]["confirmation_token"]

        # Step 2: Call with valid confirmation and idempotency key
        idem_key = f"test-return-{order_num}-key-01"
        res2 = self.client.post(
            "/v1/tools/create-return",
            headers=self.headers,
            json={
                "order_number": order_num,
                "items": [{"order_item_id": item_id, "quantity": 1, "reason_code": "DOES_NOT_FIT"}],
                "return_method": "STORE",
                "confirmed": True,
                "confirmation_token": conf_token,
                "idempotency_key": idem_key
            }
        )
        self.assertEqual(res2.status_code, 200)
        body2 = res2.json()
        self.assertTrue(body2["success"])
        self.assertEqual(body2["data"]["return_status"], "REQUESTED")
        self.assertIn("RET-", body2["data"]["return_id"])

        # Step 3: Replay same idempotency key -> cached result
        res3 = self.client.post(
            "/v1/tools/create-return",
            headers=self.headers,
            json={
                "order_number": order_num,
                "items": [{"order_item_id": item_id, "quantity": 1, "reason_code": "DOES_NOT_FIT"}],
                "return_method": "STORE",
                "confirmed": True,
                "confirmation_token": conf_token,
                "idempotency_key": idem_key
            }
        )
        self.assertEqual(res3.status_code, 200)
        body3 = res3.json()
        self.assertTrue(body3["success"])
        self.assertTrue(body3["meta"]["cached"])

    def test_check_exchange_availability(self):
        # Query exchange availability for order item
        res = self.client.post(
            "/v1/tools/check-exchange-availability",
            headers=self.headers,
            json={
                "order_item_id": "ITEM-00002-01",
                "replacement_size": "M"
            }
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertIn("eligible", body["data"])
        self.assertIn("stock_status", body["data"])

    def test_invalid_inputs_and_bounds(self):
        # Out of bounds search limit
        res = self.client.post(
            "/v1/tools/search-products",
            headers=self.headers,
            json={"limit": 999}
        )
        self.assertEqual(res.status_code, 422)  # Pydantic validation error

        # Negative price filter
        res2 = self.client.post(
            "/v1/tools/search-products",
            headers=self.headers,
            json={"min_price": -50.0}
        )
        self.assertEqual(res2.status_code, 422)

    def test_tool_audit_logging_persistence(self):
        # Call a tool with custom request ID
        req_id = "test-audit-verify-req-999"
        res = self.client.post(
            "/v1/tools/find-stores",
            headers={**self.headers, "X-Request-ID": req_id},
            json={"limit": 2}
        )
        self.assertEqual(res.status_code, 200)

        # Check if row was inserted in tool_audit_log
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tool_name, result_status FROM tool_audit_log WHERE request_id = %s;", (req_id,))
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], "find_stores")
                self.assertEqual(row[1], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
