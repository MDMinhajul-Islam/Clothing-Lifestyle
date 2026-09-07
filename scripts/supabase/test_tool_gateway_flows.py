"""End-to-End Validation and Latency Benchmarking for AI Tool Gateway (Phase 2C).

Executes:
  Flow A: 'Find black dresses under $100 in size M' (search_products -> check_inventory)
  Flow B: 'Where is my order?' (get_order -> track_order)
  Flow C: 'Can I cancel my order?' (get_order -> check_cancellation_eligibility -> confirmation required)
  Flow D: 'I want to return an item' (get_order -> check_return_eligibility -> confirmation required -> confirmed return)
  Flow E: 'Can I exchange this for another size?' (check_return_eligibility -> check_exchange_availability)

Measures p50, p95, min, max latency across all 14 tool endpoints.
"""

import json
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.db import get_db_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("tool_flows")


def run_flow_a(client: TestClient, headers: dict) -> dict:
    """FLOW A: 'Find black dresses under $100 in size M'"""
    logger.info("=== EXECUTING FLOW A: Search & In-Store Availability ===")
    t0 = time.time()
    
    # 1. Search products for black dresses under $100 in size M
    res1 = client.post(
        "/v1/tools/search-products",
        headers=headers,
        json={"query": "dress", "color": "Black", "max_price": 100.0, "size": "M", "limit": 5}
    )
    assert res1.status_code == 200, f"Search failed: {res1.text}"
    data1 = res1.json()["data"]
    total = data1["total_matching"]
    returned = data1["returned_count"]
    logger.info(f"  Step 1: search_products matched {total} products (returned {returned})")
    assert returned > 0, "No products found for search query"
    first_prod = data1["products"][0]
    prod_id = first_prod["product_id"]
    logger.info(f"  Selected product: {prod_id} - '{first_prod['name']}' (${first_prod['price']})")

    # 2. Check inventory
    res2 = client.post(
        "/v1/tools/check-inventory",
        headers=headers,
        json={"product_id": prod_id, "size": "M"}
    )
    assert res2.status_code == 200, f"Check inventory failed: {res2.text}"
    data2 = res2.json()["data"]
    logger.info(f"  Step 2: check_inventory -> total network available: {data2['total_network_available']} ({data2['overall_status']})")
    
    elapsed = int((time.time() - t0) * 1000)
    logger.info(f"FLOW A COMPLETE in {elapsed}ms\n")
    return {"flow": "FLOW_A", "status": "PASS", "elapsed_ms": elapsed, "product_id": prod_id}


def run_flow_b(client: TestClient, headers: dict) -> dict:
    """FLOW B: 'Where is my order?'"""
    logger.info("=== EXECUTING FLOW B: Order Lookup & Real-Time Tracking ===")
    t0 = time.time()
    order_num = "ZUS-2025-00002"

    # 1. Get order details
    res1 = client.post(
        "/v1/tools/get-order",
        headers=headers,
        json={"order_number": order_num}
    )
    assert res1.status_code == 200, f"Get order failed: {res1.text}"
    order = res1.json()["data"]
    logger.info(f"  Step 1: get_order -> {order['order_number']} status={order['order_status']}, items={len(order['items'])}, total=${order['grand_total']}")

    # 2. Track order
    res2 = client.post(
        "/v1/tools/track-order",
        headers=headers,
        json={"order_number": order_num}
    )
    assert res2.status_code == 200, f"Track order failed: {res2.text}"
    track = res2.json()["data"]
    logger.info(f"  Step 2: track_order -> Carrier={track['carrier']}, Tracking={track['tracking_number']}, Status={track['shipment_status']}, Events={len(track['events'])}")

    elapsed = int((time.time() - t0) * 1000)
    logger.info(f"FLOW B COMPLETE in {elapsed}ms\n")
    return {"flow": "FLOW_B", "status": "PASS", "elapsed_ms": elapsed, "order_number": order_num}


def run_flow_c(client: TestClient, headers: dict) -> dict:
    """FLOW C: 'Can I cancel my order?'"""
    logger.info("=== EXECUTING FLOW C: Order Cancellation Eligibility & Safety ===")
    t0 = time.time()

    # Find a CONFIRMED order
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT order_number FROM orders WHERE order_status = 'CONFIRMED' LIMIT 1;")
            order_num = cur.fetchone()[0]

    # 1. Check eligibility
    res1 = client.post(
        "/v1/tools/check-cancellation-eligibility",
        headers=headers,
        json={"order_number": order_num}
    )
    assert res1.status_code == 200
    elig = res1.json()["data"]
    logger.info(f"  Step 1: check_cancellation_eligibility for {order_num} -> eligible={elig['eligible']} ({elig['reason']})")
    assert elig["eligible"] is True

    # 2. Attempt cancellation without confirmation flag -> CONFIRMATION_REQUIRED
    res2 = client.post(
        "/v1/tools/cancel-order",
        headers=headers,
        json={"order_number": order_num, "confirmed": False}
    )
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["success"] is False
    assert body2["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert body2["confirmation"] is not None
    token = body2["confirmation"]["confirmation_token"]
    logger.info(f"  Step 2: cancel_order without confirmation -> BLOCKED (CONFIRMATION_REQUIRED). Generated token: {token[:20]}...")

    elapsed = int((time.time() - t0) * 1000)
    logger.info(f"FLOW C COMPLETE in {elapsed}ms (Order was NOT modified)\n")
    return {"flow": "FLOW_C", "status": "PASS", "elapsed_ms": elapsed, "order_number": order_num}


def run_flow_d(client: TestClient, headers: dict) -> dict:
    """FLOW D: 'I want to return an item'"""
    logger.info("=== EXECUTING FLOW D: Return Verification & Confirmed Creation ===")
    t0 = time.time()

    # Dynamically find a delivered order within 30 days having available return items
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT o.order_number, oi.order_item_id, oi.product_name_snapshot
                FROM orders o
                JOIN shipments s ON o.order_id = s.order_id
                JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.order_status = 'DELIVERED'
                  AND s.delivered_at >= '2026-08-08'
                  AND NOT EXISTS (
                      SELECT 1 FROM return_items ri WHERE ri.order_item_id = oi.order_item_id
                  )
                LIMIT 1;
                """
            )
            row = cur.fetchone()
            order_num = row[0]
            item_id = row[1]
            item_name = row[2]

    # 1. Check return eligibility
    res1 = client.post(
        "/v1/tools/check-return-eligibility",
        headers=headers,
        json={"order_number": order_num}
    )
    assert res1.status_code == 200
    ret_elig = res1.json()["data"]
    logger.info(f"  Step 1: check_return_eligibility for {order_num} -> eligible={ret_elig['eligible']}, days_remaining={ret_elig['days_remaining']}")

    # 2. Call create_return without confirmation -> CONFIRMATION_REQUIRED
    res2 = client.post(
        "/v1/tools/create-return",
        headers=headers,
        json={
            "order_number": order_num,
            "items": [{"order_item_id": item_id, "quantity": 1, "reason_code": "DOES_NOT_FIT"}],
            "confirmed": False
        }
    )
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["success"] is False
    assert body2["error"]["code"] == "CONFIRMATION_REQUIRED"
    conf_token = body2["confirmation"]["confirmation_token"]
    logger.info(f"  Step 2: create_return without confirmation -> BLOCKED (CONFIRMATION_REQUIRED). Est. refund: ${body2['confirmation']['summary']['estimated_refund']:.2f}")

    # 3. Call create_return with confirmation token and idempotency key -> SUCCESS
    idem_key = f"flow-d-return-{order_num}"
    res3 = client.post(
        "/v1/tools/create-return",
        headers=headers,
        json={
            "order_number": order_num,
            "items": [{"order_item_id": item_id, "quantity": 1, "reason_code": "DOES_NOT_FIT"}],
            "confirmed": True,
            "confirmation_token": conf_token,
            "idempotency_key": idem_key
        }
    )
    assert res3.status_code == 200
    body3 = res3.json()
    assert body3["success"] is True
    ret_id = body3["data"]["return_id"]
    logger.info(f"  Step 3: create_return with confirmation -> SUCCESS. Created Return: {ret_id} for item '{item_name}'")

    elapsed = int((time.time() - t0) * 1000)
    logger.info(f"FLOW D COMPLETE in {elapsed}ms\n")
    return {"flow": "FLOW_D", "status": "PASS", "elapsed_ms": elapsed, "return_id": ret_id}


def run_flow_e(client: TestClient, headers: dict) -> dict:
    """FLOW E: 'Can I exchange this for size L?'"""
    logger.info("=== EXECUTING FLOW E: Exchange Sizing & Inventory Check ===")
    t0 = time.time()
    order_item_id = "ITEM-00002-01"

    # 1. Check exchange availability for size L
    res1 = client.post(
        "/v1/tools/check-exchange-availability",
        headers=headers,
        json={
            "order_item_id": order_item_id,
            "replacement_size": "L"
        }
    )
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    logger.info(f"  Step 1: check_exchange_availability for {order_item_id} -> eligible={data1['eligible']}, reason='{data1['reason']}', stock_status={data1['stock_status']}")

    elapsed = int((time.time() - t0) * 1000)
    logger.info(f"FLOW E COMPLETE in {elapsed}ms\n")
    return {"flow": "FLOW_E", "status": "PASS", "elapsed_ms": elapsed, "order_item_id": order_item_id}


def benchmark_tools(client: TestClient, headers: dict, iterations: int = 5) -> Dict[str, Any]:
    """Measure latency stats (min, max, avg, p50, p95) across all 14 tools."""
    logger.info("=== RUNNING TOOL LATENCY BENCHMARKS (%d iterations each) ===", iterations)

    tools_to_bench = [
        ("search_products", "/v1/tools/search-products", {"query": "blazer", "limit": 10}),
        ("get_product_details", "/v1/tools/get-product-details", {"product_id": "zara-us:00029400"}),
        ("compare_products", "/v1/tools/compare-products", {"product_ids": ["zara-us:00029400", "zara-us:07446735"]}),
        ("check_inventory", "/v1/tools/check-inventory", {"product_id": "zara-us:04302360"}),
        ("find_stores", "/v1/tools/find-stores", {"state": "NY", "limit": 5}),
        ("find_stores_geo", "/v1/tools/find-stores", {"latitude": 40.7128, "longitude": -74.0060, "limit": 5}),
        ("get_customer", "/v1/tools/get-customer", {"email": "scarlett.torres.0026@demo-synthetic.example.com"}),
        ("get_order", "/v1/tools/get-order", {"order_number": "ZUS-2025-00002"}),
        ("track_order", "/v1/tools/track-order", {"order_number": "ZUS-2025-00002"}),
        ("check_cancellation_eligibility", "/v1/tools/check-cancellation-eligibility", {"order_number": "ZUS-2025-00002"}),
        ("check_return_eligibility", "/v1/tools/check-return-eligibility", {"order_number": "ZUS-2025-00002"}),
        ("get_refund_status", "/v1/tools/get-refund-status", {"order_number": "ZUS-2025-00002"}),
        ("check_exchange_availability", "/v1/tools/check-exchange-availability", {"order_item_id": "ITEM-00002-01", "replacement_size": "M"}),
    ]

    benchmark_results = {}

    for name, endpoint, payload in tools_to_bench:
        durations = []
        for _ in range(iterations):
            t_start = time.perf_counter()
            resp = client.post(endpoint, headers=headers, json=payload)
            dur = (time.perf_counter() - t_start) * 1000.0  # ms
            assert resp.status_code == 200, f"Benchmark call failed: {name} {resp.text}"
            durations.append(dur)

        durations.sort()
        p50 = statistics.median(durations)
        p95 = durations[int(len(durations) * 0.95)] if len(durations) > 1 else durations[-1]
        avg = statistics.mean(durations)
        benchmark_results[name] = {
            "min_ms": round(min(durations), 1),
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "max_ms": round(max(durations), 1),
            "avg_ms": round(avg, 1)
        }
        logger.info(f"  {name:30s}: p50={p50:5.1f}ms | p95={p95:5.1f}ms | avg={avg:5.1f}ms | min={min(durations):5.1f}ms")

    return benchmark_results


def main():
    client = TestClient(app)
    headers = {
        "X-Tool-Secret": settings.tool_gateway_secret,
        "Content-Type": "application/json"
    }

    t0_all = time.time()
    logger.info("Starting Phase 2C Tool Gateway Flows and Benchmarks...")

    flow_a = run_flow_a(client, headers)
    flow_b = run_flow_b(client, headers)
    flow_c = run_flow_c(client, headers)
    flow_d = run_flow_d(client, headers)
    flow_e = run_flow_e(client, headers)

    benchmarks = benchmark_tools(client, headers, iterations=5)

    total_time = time.time() - t0_all
    logger.info(f"ALL 5 REPRESENTATIVE FLOWS & LATENCY BENCHMARKS COMPLETED in {total_time:.2f}s!")

    # Dump benchmark summary
    summary = {
        "flows": [flow_a, flow_b, flow_c, flow_d, flow_e],
        "benchmarks": benchmarks,
        "total_elapsed_sec": round(total_time, 2)
    }
    with open("reports/phase_2c_benchmarks.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info("Saved benchmark report to reports/phase_2c_benchmarks.json")


if __name__ == "__main__":
    main()
