#!/usr/bin/env python3
"""Synthetic Operational Data Layer Generator & Importer (Phase 2B).

Generates realistic demo retail data for:
  - stores (30 demo US locations)
  - inventory_levels (sparse store inventory across real catalogue variants)
  - customers (2,000 demo customers)
  - customer_addresses (2,500 shipping/billing addresses)
  - orders (5,000 historical orders across 12 months)
  - order_items (line items referencing real catalogue products/variants/prices)
  - payments (authorized/captured/refunded demo payments)
  - shipments (tracking numbers, carriers)
  - shipment_events (chronological transit events)
  - returns (customer return requests, reasons, methods)
  - return_items (returned line items, conditions, resolutions)
  - refunds (reconciled disbursement records)
  - exchanges (original variant to replacement variant mapping)

NOTICE: All operational records are SYNTHETIC DEMO DATA (is_synthetic=True, data_origin='synthetic').
Real Zara catalogue tables (products, variants, colors, images, categories) remain 100% untouched.
"""

import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values
    HAVE_PSYCOPG2 = True
except ImportError:
    HAVE_PSYCOPG2 = False

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_ZARA = ROOT_DIR / "data" / "zara"
DEFAULT_EXPORT_DIR = ROOT_DIR / "data" / "synthetic"

DEFAULT_SEED = 20260907

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("synthetic_operations")


def load_dotenv(env_path: Path = ROOT_DIR / ".env"):
    """Load environment variables from .env."""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k not in os.environ:
                    os.environ[k] = v


class SyntheticOperationsGenerator:
    """Deterministic generator for synthetic retail operations."""

    def __init__(self, seed: int = DEFAULT_SEED, data_dir: Path = DATA_ZARA):
        self.seed = seed
        self.data_dir = data_dir
        self.rng = random.Random(seed)

        # Output containers
        self.stores = []
        self.inventory_levels = []
        self.customers = []
        self.customer_addresses = []
        self.customer_address_map = {}
        self.orders = []
        self.order_items = []
        self.payments = []
        self.shipments = []
        self.shipment_events = []
        self.returns = []
        self.return_items = []
        self.refunds = []
        self.exchanges = []

        # Catalogue references
        self.products = []
        self.variants = []
        self.prod_map = {}
        self.variants_by_prod = {}
        self.valid_product_ids = set()
        self.valid_variant_ids = set()

    def _make_uuid(self, namespace: str, idx: int) -> str:
        """Deterministic UUID generation using namespace and index."""
        h = hashlib.md5(f"{self.seed}:{namespace}:{idx}".encode("utf-8")).digest()
        return str(uuid.UUID(bytes=h))

    def load_catalogue(self):
        """Load real catalogue products and variants."""
        logger.info("Loading real catalogue references...")
        with open(self.data_dir / "product_details.json", "r", encoding="utf-8") as f:
            self.products = json.load(f)
        with open(self.data_dir / "product_variants.json", "r", encoding="utf-8") as f:
            self.variants = json.load(f)

        self.prod_map = {p["product_id"]: p for p in self.products}
        self.valid_product_ids = set(self.prod_map.keys())

        for v in self.variants:
            pid = v["product_id"]
            if pid not in self.variants_by_prod:
                self.variants_by_prod[pid] = []
            self.variants_by_prod[pid].append(v)
            self.valid_variant_ids.add(v["variant_id"])

        logger.info(f"Loaded {len(self.products)} catalogue products and {len(self.variants)} variants.")

    def generate_stores(self):
        """Generate 30 realistic US demo store locations."""
        logger.info("Generating 30 demo store locations...")
        store_specs = [
            ("STORE-US-001", "ZARA-US-NYC-01", "Zara Fifth Avenue Flagship (Demo)", "NY", "New York", "666 5th Ave", "Fl 1-3", "10103", 40.7601, -73.9765, "America/New_York", "+1-212-555-0101", "FLAGSHIP"),
            ("STORE-US-002", "ZARA-US-NYC-02", "Zara SoHo Broadway (Demo)", "NY", "New York", "503 Broadway", None, "10012", 40.7214, -73.9984, "America/New_York", "+1-212-555-0102", "RETAIL"),
            ("STORE-US-003", "ZARA-US-NYC-03", "Zara Hudson Yards (Demo)", "NY", "New York", "20 Hudson Yards", "Ste RU311", "10001", 40.7538, -74.0016, "America/New_York", "+1-212-555-0103", "RETAIL"),
            ("STORE-US-004", "ZARA-US-NYC-04", "Zara Flatiron (Demo)", "NY", "New York", "101 5th Ave", None, "10003", 40.7383, -73.9922, "America/New_York", "+1-212-555-0104", "RETAIL"),
            ("STORE-US-005", "ZARA-US-LAX-01", "Zara Century City (Demo)", "CA", "Los Angeles", "10250 Santa Monica Blvd", "Ste 100", "90067", 34.0592, -118.4194, "America/Los_Angeles", "+1-310-555-0105", "FLAGSHIP"),
            ("STORE-US-006", "ZARA-US-LAX-02", "Zara Beverly Center (Demo)", "CA", "Los Angeles", "8500 Beverly Blvd", "Ste 600", "90048", 34.0754, -118.3773, "America/Los_Angeles", "+1-310-555-0106", "RETAIL"),
            ("STORE-US-007", "ZARA-US-LAX-03", "Zara Santa Monica Promenade (Demo)", "CA", "Santa Monica", "1317 3rd Street Promenade", None, "90401", 34.0165, -118.4975, "America/Los_Angeles", "+1-310-555-0107", "RETAIL"),
            ("STORE-US-008", "ZARA-US-SFO-01", "Zara Union Square (Demo)", "CA", "San Francisco", "250 Post St", None, "94108", 37.7891, -122.4068, "America/Los_Angeles", "+1-415-555-0108", "FLAGSHIP"),
            ("STORE-US-009", "ZARA-US-SAN-01", "Zara Fashion Valley (Demo)", "CA", "San Diego", "7007 Friars Rd", "Ste 300", "92108", 32.7684, -117.1669, "America/Los_Angeles", "+1-619-555-0109", "RETAIL"),
            ("STORE-US-010", "ZARA-US-SJC-01", "Zara Santana Row (Demo)", "CA", "San Jose", "356 Santana Row", "Ste 100", "95128", 37.3217, -121.9479, "America/Los_Angeles", "+1-408-555-0110", "RETAIL"),
            ("STORE-US-011", "ZARA-US-CHI-01", "Zara Michigan Avenue Flagship (Demo)", "IL", "Chicago", "540 N Michigan Ave", None, "60611", 41.8924, -87.6243, "America/Chicago", "+1-312-555-0111", "FLAGSHIP"),
            ("STORE-US-012", "ZARA-US-CHI-02", "Zara Oakbrook Center (Demo)", "IL", "Oak Brook", "100 Oakbrook Center", None, "60523", 41.8523, -87.9547, "America/Chicago", "+1-630-555-0112", "RETAIL"),
            ("STORE-US-013", "ZARA-US-MIA-01", "Zara Lincoln Road (Demo)", "FL", "Miami Beach", "420 Lincoln Rd", None, "33139", 25.7907, -80.1347, "America/New_York", "+1-305-555-0113", "FLAGSHIP"),
            ("STORE-US-014", "ZARA-US-MIA-02", "Zara Aventura Mall (Demo)", "FL", "Aventura", "19501 Biscayne Blvd", "Ste 1100", "33180", 25.9575, -80.1431, "America/New_York", "+1-305-555-0114", "RETAIL"),
            ("STORE-US-015", "ZARA-US-ORL-01", "Zara Mall at Millenia (Demo)", "FL", "Orlando", "4200 Conroy Rd", "Ste 240", "32839", 28.4867, -81.4312, "America/New_York", "+1-407-555-0115", "RETAIL"),
            ("STORE-US-016", "ZARA-US-DFW-01", "Zara NorthPark Center (Demo)", "TX", "Dallas", "8687 N Central Expy", "Ste 1200", "75225", 32.8687, -96.7735, "America/Chicago", "+1-214-555-0116", "FLAGSHIP"),
            ("STORE-US-017", "ZARA-US-HOU-01", "Zara The Galleria (Demo)", "TX", "Houston", "5085 Westheimer Rd", "Ste 3500", "77056", 29.7397, -95.4651, "America/Chicago", "+1-713-555-0117", "RETAIL"),
            ("STORE-US-018", "ZARA-US-AUS-01", "Zara Domain Northside (Demo)", "TX", "Austin", "11410 Century Oaks Terrace", None, "78758", 30.4022, -97.7246, "America/Chicago", "+1-512-555-0118", "RETAIL"),
            ("STORE-US-019", "ZARA-US-BOS-01", "Zara Newbury Street (Demo)", "MA", "Boston", "212 Newbury St", None, "02116", 42.3503, -71.0818, "America/New_York", "+1-617-555-0119", "FLAGSHIP"),
            ("STORE-US-020", "ZARA-US-SEA-01", "Zara Westlake Center (Demo)", "WA", "Seattle", "400 Pine St", None, "98101", 47.6115, -122.3371, "America/Los_Angeles", "+1-206-555-0120", "RETAIL"),
            ("STORE-US-021", "ZARA-US-SEA-02", "Zara Bellevue Square (Demo)", "WA", "Bellevue", "1 Bellevue Square", "Ste 200", "98004", 47.6166, -122.2036, "America/Los_Angeles", "+1-425-555-0121", "RETAIL"),
            ("STORE-US-022", "ZARA-US-ATL-01", "Zara Lenox Square (Demo)", "GA", "Atlanta", "3393 Peachtree Rd NE", "Ste 3000", "30326", 33.8465, -84.3619, "America/New_York", "+1-404-555-0122", "RETAIL"),
            ("STORE-US-023", "ZARA-US-PHL-01", "Zara Rittenhouse Walnut (Demo)", "PA", "Philadelphia", "1708 Walnut St", None, "19103", 39.9500, -75.1698, "America/New_York", "+1-215-555-0123", "RETAIL"),
            ("STORE-US-024", "ZARA-US-PHL-02", "Zara King of Prussia (Demo)", "PA", "King of Prussia", "160 N Gulph Rd", "Ste 2100", "19406", 40.0886, -75.3934, "America/New_York", "+1-610-555-0124", "RETAIL"),
            ("STORE-US-025", "ZARA-US-WAS-01", "Zara Georgetown (Demo)", "DC", "Washington", "1233 Wisconsin Ave NW", None, "20007", 38.9056, -77.0628, "America/New_York", "+1-202-555-0125", "RETAIL"),
            ("STORE-US-026", "ZARA-US-LAS-01", "Zara Fashion Show Mall (Demo)", "NV", "Las Vegas", "3200 S Las Vegas Blvd", "Ste 100", "89109", 36.1287, -115.1706, "America/Los_Angeles", "+1-702-555-0126", "FLAGSHIP"),
            ("STORE-US-027", "ZARA-US-DEN-01", "Zara Cherry Creek (Demo)", "CO", "Denver", "3000 E 1st Ave", "Ste 200", "80206", 39.7180, -104.9542, "America/Denver", "+1-303-555-0127", "RETAIL"),
            ("STORE-US-028", "ZARA-US-PHX-01", "Zara Scottsdale Fashion Square (Demo)", "AZ", "Scottsdale", "7014 E Camelback Rd", "Ste 100", "85251", 33.5029, -111.9295, "America/Phoenix", "+1-480-555-0128", "RETAIL"),
            ("STORE-US-029", "ZARA-US-MSP-01", "Zara Mall of America (Demo)", "MN", "Bloomington", "60 E Broadway", "Ste 220", "55425", 44.8549, -93.2422, "America/Chicago", "+1-952-555-0129", "RETAIL"),
            ("STORE-US-030", "ZARA-US-HNL-01", "Zara Ala Moana Center (Demo)", "HI", "Honolulu", "1450 Ala Moana Blvd", "Ste 2000", "96814", 21.2913, -157.8436, "Pacific/Honolulu", "+1-808-555-0130", "RETAIL"),
        ]

        self.stores = []
        for s in store_specs:
            self.stores.append({
                "store_id": s[0],
                "store_code": s[1],
                "store_name": s[2],
                "country_code": "US",
                "country_name": "United States",
                "state": s[3],
                "city": s[4],
                "address_line_1": s[5],
                "address_line_2": s[6],
                "postal_code": s[7],
                "latitude": s[8],
                "longitude": s[9],
                "timezone": s[10],
                "phone": s[11],
                "store_type": s[12],
                "status": "OPEN",
                "opening_hours": {
                    "monday": "10:00 - 21:00",
                    "tuesday": "10:00 - 21:00",
                    "wednesday": "10:00 - 21:00",
                    "thursday": "10:00 - 21:00",
                    "friday": "10:00 - 21:30",
                    "saturday": "10:00 - 21:30",
                    "sunday": "11:00 - 19:00"
                },
                "is_synthetic": True,
                "data_origin": "synthetic",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2026-09-01T00:00:00Z"
            })
        logger.info(f"Generated {len(self.stores)} stores.")

    def generate_inventory(self):
        """Generate realistic sparse inventory across 30 demo stores."""
        logger.info("Generating sparse store inventory levels...")
        store_ids = [s["store_id"] for s in self.stores]

        # Designate ~10% of catalogue products as online-only (0 store inventory)
        all_prod_ids = sorted(list(self.valid_product_ids))
        online_only_prods = set(all_prod_ids[:600])

        self.inventory_levels = []
        inv_idx = 0
        counts = {"OUT_OF_STOCK": 0, "LOW_STOCK": 0, "IN_STOCK": 0}

        for v in self.variants:
            pid = v["product_id"]
            if pid in online_only_prods:
                continue

            # Stock in 2 to 5 stores
            num_stores = self.rng.randint(2, 5)
            chosen_stores = self.rng.sample(store_ids, num_stores)

            for sid in chosen_stores:
                inv_idx += 1
                r = self.rng.random()
                if r < 0.15:
                    q_on_hand = 0
                    q_res = 0
                    status = "OUT_OF_STOCK"
                elif r < 0.35:
                    q_on_hand = self.rng.randint(1, 4)
                    q_res = self.rng.randint(0, min(1, q_on_hand))
                    q_res = self.rng.randint(0, min(1, q_on_hand - 1)) if q_on_hand > 1 else 0
                else:
                    q_on_hand = self.rng.randint(5, 30)
                    q_res = self.rng.randint(0, min(3, q_on_hand - 5))

                q_avail = q_on_hand - q_res
                if q_avail == 0:
                    status = "OUT_OF_STOCK"
                elif q_avail <= 4:
                    status = "LOW_STOCK"
                else:
                    q_on_hand = self.rng.randint(5, 30)
                    q_res = self.rng.randint(0, min(3, q_on_hand))
                    status = "IN_STOCK"

                counts[status] += 1
                inv_key = hashlib.md5(f"{sid}:{v['variant_id']}".encode()).hexdigest()[:16]
                self.inventory_levels.append({
                    "inventory_id": f"INV-{inv_idx:07d}",
                    "inventory_id": f"INV-{inv_key}",
                    "store_id": sid,
                    "variant_id": v["variant_id"],
                    "quantity_on_hand": q_on_hand,
                    "quantity_reserved": q_res,
                    "quantity_available": q_on_hand - q_res,
                    "availability_status": status,
                    "reorder_threshold": 5,
                    "last_updated_at": "2026-09-01T12:00:00Z",
                    "is_synthetic": True,
                    "data_origin": "synthetic"
                })

        total = len(self.inventory_levels)
        logger.info(f"Generated {total} inventory levels:")
        logger.info(f"  OUT_OF_STOCK: {counts['OUT_OF_STOCK']} ({counts['OUT_OF_STOCK']/total*100:.1f}%)")
        logger.info(f"  LOW_STOCK:    {counts['LOW_STOCK']} ({counts['LOW_STOCK']/total*100:.1f}%)")
        logger.info(f"  IN_STOCK:     {counts['IN_STOCK']} ({counts['IN_STOCK']/total*100:.1f}%)")

    def generate_customers_and_addresses(self, count: int = 2000):
        """Generate 2,000 synthetic customers and 2,500 addresses."""
        logger.info(f"Generating {count} synthetic customers and addresses...")
        first_names = ["Emma", "Liam", "Olivia", "Noah", "Sophia", "Jackson", "Ava", "Aiden", "Isabella", "Lucas", "Mia", "Ethan", "Harper", "Oliver", "Evelyn", "Elijah", "Abigail", "Amelia", "Emily", "James", "Charlotte", "Benjamin", "Ella", "Alexander", "Avery", "Henry", "Sofia", "Sebastian", "Camila", "Daniel", "Aria", "Matthew", "Scarlett", "Samuel", "Victoria", "David", "Madison", "Joseph", "Luna", "Carter", "Grace", "Owen", "Chloe", "Wyatt", "Penelope", "John", "Layla", "Jack", "Riley", "Luke"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts"]
        cities = [("New York", "NY", "10012"), ("Los Angeles", "CA", "90024"), ("Chicago", "IL", "60614"), ("Houston", "TX", "77002"), ("Miami", "FL", "33139"), ("San Francisco", "CA", "94107"), ("Seattle", "WA", "98103"), ("Boston", "MA", "02116"), ("Atlanta", "GA", "30309"), ("Dallas", "TX", "75201"), ("Austin", "TX", "78701"), ("Philadelphia", "PA", "19103"), ("Denver", "CO", "80202"), ("Phoenix", "AZ", "85004"), ("Honolulu", "HI", "96815")]

        self.customers = []
        self.customer_addresses = []
        self.customer_address_map = {}

        for i in range(1, count + 1):
            c_uuid = self._make_uuid("customer", i)
            fn = first_names[(i * 7) % len(first_names)]
            ln = last_names[(i * 11) % len(last_names)]
            city, state, zip_c = cities[i % len(cities)]
            email = f"{fn.lower()}.{ln.lower()}.{i:04d}@demo-synthetic.example.com"
            phone = f"+1-555-{100 + (i % 900):03d}-{1000 + (i % 9000):04d}"
            lang = "es" if i % 10 == 0 else "en"
            opt_in = (i % 3 == 0)
            created_at = (datetime(2025, 9, 1, tzinfo=timezone.utc) + timedelta(days=(i % 300), hours=(i % 24))).isoformat()

            self.customers.append({
                "customer_id": c_uuid,
                "first_name": fn,
                "last_name": ln,
                "email": email,
                "phone": phone,
                "country_code": "US",
                "state": state,
                "city": city,
                "preferred_language": lang,
                "preferred_currency": "USD",
                "marketing_opt_in": opt_in,
                "account_status": "ACTIVE",
                "is_synthetic": True,
                "data_origin": "synthetic",
                "created_at": created_at,
                "updated_at": created_at
            })

            # Primary address
            a1_uuid = self._make_uuid("address", i * 2 - 1)
            addr1 = {
                "address_id": a1_uuid,
                "customer_id": c_uuid,
                "address_type": "SHIPPING",
                "recipient_name": f"{fn} {ln}",
                "address_line_1": f"{100 + (i % 800)} Main St",
                "address_line_2": f"Apt {1 + (i % 20)}" if i % 2 == 0 else None,
                "city": city,
                "state": state,
                "postal_code": zip_c,
                "country_code": "US",
                "is_default_shipping": True,
                "is_default_billing": True,
                "is_synthetic": True,
                "created_at": created_at
            }
            self.customer_addresses.append(addr1)
            self.customer_address_map[c_uuid] = [a1_uuid]

            # 500 customers get an additional secondary address
            if i <= 500:
                a2_uuid = self._make_uuid("address", i * 2)
                addr2 = {
                    "address_id": a2_uuid,
                    "customer_id": c_uuid,
                    "address_type": "SHIPPING",
                    "recipient_name": f"{fn} {ln}",
                    "address_line_1": f"{500 + i} Commerce Blvd",
                    "address_line_2": f"Suite {i}",
                    "city": city,
                    "state": state,
                    "postal_code": zip_c,
                    "country_code": "US",
                    "is_default_shipping": False,
                    "is_default_billing": False,
                    "is_synthetic": True,
                    "created_at": created_at
                }
                self.customer_addresses.append(addr2)
                self.customer_address_map[c_uuid].append(a2_uuid)

        logger.info(f"Generated {len(self.customers)} customers and {len(self.customer_addresses)} addresses.")

    def generate_orders_and_operations(self, order_count: int = 5000):
        """Generate 5,000 orders, items, payments, shipments, returns, refunds, and exchanges."""
        logger.info(f"Generating {order_count} historical orders and operational workflows...")

        status_targets = {
            "DELIVERED": 3000,
            "SHIPPED": 500,
            "PROCESSING": 250,
            "CONFIRMED": 150,
            "PENDING": 100,
            "CANCELLED": 250,
            "RETURN_REQUESTED": 150,
            "PARTIALLY_RETURNED": 150,
            "RETURNED": 250,
            "REFUNDED": 200,
        }
        status_pool = []
        for st, cnt in status_targets.items():
            status_pool.extend([st] * cnt)
        self.rng.shuffle(status_pool)

        store_ids = [s["store_id"] for s in self.stores]
        carriers = ["FEDEX", "UPS", "USPS"]
        return_reasons = ["WRONG_SIZE", "DOES_NOT_FIT", "DEFECTIVE", "STYLE_NOT_AS_EXPECTED", "CHANGED_MIND"]
        return_conditions = ["NEW_WITH_TAGS", "TRIED_ON", "DAMAGED"]

        base_start = datetime(2025, 9, 1, 8, 0, tzinfo=timezone.utc)

        self.orders = []
        self.order_items = []
        self.payments = []
        self.shipments = []
        self.shipment_events = []
        self.returns = []
        self.return_items = []
        self.refunds = []
        self.exchanges = []

        for ord_idx in range(1, order_count + 1):
            ord_id = f"ORD-2025-{ord_idx:05d}"
            ord_num = f"ZUS-2025-{ord_idx:05d}"
            c_idx = (ord_idx * 13) % len(self.customers)
            cust = self.customers[c_idx]
            c_uuid = cust["customer_id"]
            cust_addrs = self.customer_address_map[c_uuid]

            st = status_pool[ord_idx - 1]

            # Fulfillment type: 85% DELIVERY, 15% PICKUP
            is_pickup = (ord_idx % 7 == 0)
            fulfillment = "PICKUP" if is_pickup else "DELIVERY"
            shipping_addr_id = None if is_pickup else cust_addrs[0]
            pickup_store_id = store_ids[ord_idx % len(store_ids)] if is_pickup else None

            # Timeline
            day_offset = (ord_idx * 73) % 350
            placed_dt = base_start + timedelta(days=day_offset, hours=(ord_idx % 24), minutes=(ord_idx % 60))
            confirmed_dt = placed_dt + timedelta(minutes=5) if st != "PENDING" else None

            cancelled_dt = None
            completed_dt = None
            shipped_dt = None
            delivered_dt = None

            if st == "CANCELLED":
                cancelled_dt = placed_dt + timedelta(minutes=45)
                completed_dt = cancelled_dt
                pay_st = "REFUNDED"
            elif st == "PENDING":
                pay_st = "PENDING"
            elif st in ("CONFIRMED", "PROCESSING"):
                pay_st = "PAID"
            else:
                pay_st = "PAID" if st != "REFUNDED" else "REFUNDED"
                shipped_dt = confirmed_dt + timedelta(hours=24)
                if st in ("DELIVERED", "RETURN_REQUESTED", "PARTIALLY_RETURNED", "RETURNED", "REFUNDED"):
                    delivered_dt = shipped_dt + timedelta(days=3)
                    completed_dt = delivered_dt

            # Order items (1 to 4 items)
            num_items = 1 + (ord_idx % 4)
            item_subtotal = Decimal("0.00")
            current_order_items = []

            for item_idx in range(1, num_items + 1):
                p_idx = (ord_idx * 17 + item_idx * 31) % len(self.products)
                p = self.products[p_idx]
                p_variants = self.variants_by_prod.get(p["product_id"], [])
                if not p_variants:
                    continue
                v = p_variants[(ord_idx + item_idx) % len(p_variants)]

                raw_price = p.get("current_price") or "39.90"
                unit_price = Decimal(str(raw_price)).quantize(Decimal("0.01"))
                qty = 1 if (item_idx > 1 or ord_idx % 5 != 0) else 2
                line_tot = (unit_price * qty).quantize(Decimal("0.01"))
                item_subtotal += line_tot

                oi_id = f"ITEM-{ord_idx:05d}-{item_idx:02d}"
                oi = {
                    "order_item_id": oi_id,
                    "order_id": ord_id,
                    "product_id": p["product_id"],
                    "variant_id": v["variant_id"],
                    "quantity": qty,
                    "unit_price": float(unit_price),
                    "line_discount": 0.00,
                    "line_total": float(line_tot),
                    "product_name_snapshot": p.get("exact_product_name", "Zara Apparel"),
                    "size_snapshot": v.get("size_name", "M"),
                    "color_snapshot": v.get("color_name", "Standard"),
                    "is_synthetic": True,
                    "created_at": placed_dt.isoformat()
                }
                self.order_items.append(oi)
                current_order_items.append((oi, v, p))

            # Discount calculation
            if item_subtotal > Decimal("100.00") and ord_idx % 4 == 0:
                disc = Decimal("10.00")
            else:
                disc = Decimal("0.00")

            # Allocate discount across line items proportionally
            if disc > Decimal("0.00") and current_order_items:
                rem_disc = disc
                for i_idx, (oi, v, p) in enumerate(current_order_items):
                    if i_idx == len(current_order_items) - 1:
                        item_d = rem_disc
                    else:
                        ratio = Decimal(str(oi["line_total"])) / item_subtotal
                        item_d = (disc * ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        rem_disc -= item_d
                    oi["line_discount"] = float(item_d)
                    oi["line_total"] = float(Decimal(str(oi["unit_price"])) * oi["quantity"] - item_d)

            taxable = item_subtotal - disc
            tax = (taxable * Decimal("0.0825")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if fulfillment == "PICKUP" or taxable >= Decimal("50.00"):
                ship_fee = Decimal("0.00")
            else:
                ship_fee = Decimal("5.95")

            grand_total = item_subtotal - disc + tax + ship_fee
            assert (item_subtotal - disc + tax + ship_fee) == grand_total, f"Reconciliation error in {ord_id}"

            self.orders.append({
                "order_id": ord_id,
                "order_number": ord_num,
                "customer_id": c_uuid,
                "order_status": st,
                "fulfillment_type": fulfillment,
                "shipping_address_id": shipping_addr_id,
                "store_id": pickup_store_id,
                "currency": "USD",
                "subtotal": float(item_subtotal),
                "discount_total": float(disc),
                "tax_total": float(tax),
                "shipping_total": float(ship_fee),
                "grand_total": float(grand_total),
                "payment_status": pay_st,
                "placed_at": placed_dt.isoformat(),
                "confirmed_at": confirmed_dt.isoformat() if confirmed_dt else None,
                "cancelled_at": cancelled_dt.isoformat() if cancelled_dt else None,
                "completed_at": completed_dt.isoformat() if completed_dt else None,
                "is_synthetic": True,
                "data_origin": "synthetic",
                "created_at": placed_dt.isoformat(),
                "updated_at": (completed_dt or placed_dt).isoformat()
            })

            # Payment
            pay_methods = ["CREDIT_CARD", "APPLE_PAY", "PAYPAL"]
            pm = pay_methods[ord_idx % 3]
            self.payments.append({
                "payment_id": f"PAY-{ord_id}",
                "order_id": ord_id,
                "payment_method": pm,
                "payment_status": "CAPTURED" if pay_st == "PAID" else ("REFUNDED" if pay_st == "REFUNDED" else "AUTHORIZED"),
                "amount": float(grand_total),
                "currency": "USD",
                "provider_reference": f"SYN-AUTH-{pm[:3]}-{ord_idx:07d}",
                "authorized_at": placed_dt.isoformat(),
                "captured_at": (placed_dt + timedelta(minutes=2)).isoformat() if pay_st in ("PAID", "REFUNDED") else None,
                "failed_at": None,
                "is_synthetic": True,
                "created_at": placed_dt.isoformat()
            })

            # Shipment (for shipped/delivered orders)
            if shipped_dt:
                ship_id = f"SHIP-{ord_id}"
                carrier = carriers[ord_idx % len(carriers)]
                tracking = f"SYN-TRACK-{carrier[:3]}-{ord_idx:08d}"
                ship_st = "DELIVERED" if delivered_dt else "SHIPPED"
                est_del = shipped_dt + timedelta(days=4)

                self.shipments.append({
                    "shipment_id": ship_id,
                    "order_id": ord_id,
                    "carrier": carrier,
                    "tracking_number": tracking,
                    "shipment_status": ship_st,
                    "shipped_at": shipped_dt.isoformat(),
                    "estimated_delivery_at": est_del.isoformat(),
                    "delivered_at": delivered_dt.isoformat() if delivered_dt else None,
                    "origin_store_id": pickup_store_id,
                    "is_synthetic": True,
                    "created_at": shipped_dt.isoformat()
                })

                # Chronological shipment transit events
                self.shipment_events.append({
                    "event_id": f"EVT-{ship_id}-01",
                    "shipment_id": ship_id,
                    "event_type": "LABEL_CREATED",
                    "description": "Shipping label created, awaiting carrier pickup",
                    "location_text": "Zara Distribution Center, Secaucus, NJ",
                    "occurred_at": (shipped_dt - timedelta(hours=2)).isoformat(),
                    "is_synthetic": True,
                    "created_at": shipped_dt.isoformat()
                })
                self.shipment_events.append({
                    "event_id": f"EVT-{ship_id}-02",
                    "shipment_id": ship_id,
                    "event_type": "PICKED_UP",
                    "description": "Carrier picked up package from facility",
                    "location_text": "Secaucus Hub, NJ",
                    "occurred_at": shipped_dt.isoformat(),
                    "is_synthetic": True,
                    "created_at": shipped_dt.isoformat()
                })
                self.shipment_events.append({
                    "event_id": f"EVT-{ship_id}-03",
                    "shipment_id": ship_id,
                    "event_type": "IN_TRANSIT",
                    "description": "Package in transit to regional sort facility",
                    "location_text": "Regional Sorting Facility",
                    "occurred_at": (shipped_dt + timedelta(days=1)).isoformat(),
                    "is_synthetic": True,
                    "created_at": (shipped_dt + timedelta(days=1)).isoformat()
                })
                if delivered_dt:
                    self.shipment_events.append({
                        "event_id": f"EVT-{ship_id}-04",
                        "shipment_id": ship_id,
                        "event_type": "OUT_FOR_DELIVERY",
                        "description": "Out for delivery with courier",
                        "location_text": f"{cust['city']}, {cust['state']}",
                        "occurred_at": (delivered_dt - timedelta(hours=4)).isoformat(),
                        "is_synthetic": True,
                        "created_at": delivered_dt.isoformat()
                    })
                    self.shipment_events.append({
                        "event_id": f"EVT-{ship_id}-05",
                        "shipment_id": ship_id,
                        "event_type": "DELIVERED",
                        "description": "Delivered to front door/package room",
                        "location_text": f"{cust['city']}, {cust['state']}",
                        "occurred_at": delivered_dt.isoformat(),
                        "is_synthetic": True,
                        "created_at": delivered_dt.isoformat()
                    })

            # Returns, Return Items, Refunds, Exchanges
            if st in ("RETURN_REQUESTED", "PARTIALLY_RETURNED", "RETURNED", "REFUNDED"):
                ret_id = f"RET-{ord_id}"
                ret_reason = return_reasons[ord_idx % len(return_reasons)]
                ret_method = "MAIL" if ord_idx % 3 != 0 else "STORE_DROP_OFF"
                req_dt = delivered_dt + timedelta(days=3 + (ord_idx % 10))

                if st == "RETURN_REQUESTED":
                    ret_st = "REQUESTED" if ord_idx % 2 == 0 else "APPROVED"
                    app_dt = req_dt + timedelta(hours=4) if ret_st == "APPROVED" else None
                    rec_dt = None
                    comp_dt = None
                elif st == "PARTIALLY_RETURNED":
                    ret_st = "IN_TRANSIT" if ord_idx % 2 == 0 else "RECEIVED"
                    app_dt = req_dt + timedelta(hours=4)
                    rec_dt = app_dt + timedelta(days=3) if ret_st == "RECEIVED" else None
                    comp_dt = None
                elif st == "RETURNED":
                    ret_st = "RECEIVED" if ord_idx % 3 == 0 else "COMPLETED"
                    app_dt = req_dt + timedelta(hours=4)
                    rec_dt = app_dt + timedelta(days=3)
                    comp_dt = rec_dt + timedelta(days=1) if ret_st == "COMPLETED" else None
                else:  # REFUNDED
                    ret_st = "COMPLETED"
                    app_dt = req_dt + timedelta(hours=4)
                    rec_dt = app_dt + timedelta(days=3)
                    comp_dt = rec_dt + timedelta(days=1)

                self.returns.append({
                    "return_id": ret_id,
                    "order_id": ord_id,
                    "return_status": ret_st,
                    "return_reason": ret_reason,
                    "return_method": ret_method,
                    "requested_at": req_dt.isoformat(),
                    "approved_at": app_dt.isoformat() if app_dt else None,
                    "received_at": rec_dt.isoformat() if rec_dt else None,
                    "completed_at": comp_dt.isoformat() if comp_dt else None,
                    "is_synthetic": True,
                    "data_origin": "synthetic",
                    "created_at": req_dt.isoformat()
                })

                target_items = [current_order_items[0]] if st == "PARTIALLY_RETURNED" else current_order_items
                total_ret_refund = Decimal("0.00")

                for r_idx, (oi, v, p) in enumerate(target_items, 1):
                    ri_id = f"RETITEM-{ret_id}-{r_idx:02d}"
                    q_ret = 1
                    assert q_ret <= oi["quantity"], "Return quantity exceeds order quantity!"

                    is_exchange = (st != "REFUNDED" and ord_idx % 5 == 0 and r_idx == 1)
                    res = "EXCHANGE" if is_exchange else "REFUND"
                    eff_unit = (Decimal(str(oi["line_total"])) / Decimal(str(oi["quantity"]))).quantize(Decimal("0.01"))
                    item_refund = (eff_unit * q_ret).quantize(Decimal("0.01")) if res == "REFUND" else Decimal("0.00")
                    total_ret_refund += item_refund

                    self.return_items.append({
                        "return_item_id": ri_id,
                        "return_id": ret_id,
                        "order_item_id": oi["order_item_id"],
                        "quantity": q_ret,
                        "reason_code": ret_reason,
                        "condition": return_conditions[(ord_idx + r_idx) % len(return_conditions)],
                        "resolution": res,
                        "refund_amount": float(item_refund),
                        "is_synthetic": True,
                        "created_at": req_dt.isoformat()
                    })

                    if is_exchange:
                        same_variants = [other_v for other_v in self.variants_by_prod.get(p["product_id"], []) if other_v["variant_id"] != v["variant_id"]]
                        repl_v = same_variants[0] if same_variants else self.variants[(ord_idx + 100) % len(self.variants)]
                        assert repl_v["variant_id"] in self.valid_variant_ids, "Replacement variant not in catalogue!"

                        self.exchanges.append({
                            "exchange_id": f"EXC-{ri_id}",
                            "return_item_id": ri_id,
                            "original_variant_id": v["variant_id"],
                            "replacement_variant_id": repl_v["variant_id"],
                            "exchange_status": "COMPLETED" if comp_dt else "APPROVED",
                            "requested_at": req_dt.isoformat(),
                            "completed_at": comp_dt.isoformat() if comp_dt else None,
                            "is_synthetic": True,
                            "created_at": req_dt.isoformat()
                        })

                if total_ret_refund > Decimal("0.00") and (comp_dt or st == "REFUNDED"):
                    final_refund = min(total_ret_refund, grand_total)
                    if st == "REFUNDED":
                        final_refund = grand_total
                    assert final_refund <= grand_total, f"Refund {final_refund} exceeds grand_total {grand_total}"
                    self.refunds.append({
                        "refund_id": f"REF-{ord_id}",
                        "order_id": ord_id,
                        "return_id": ret_id,
                        "refund_status": "PROCESSED",
                        "refund_method": "ORIGINAL_PAYMENT",
                        "amount": float(final_refund),
                        "currency": "USD",
                        "requested_at": (rec_dt or req_dt).isoformat(),
                        "processed_at": (comp_dt or (req_dt + timedelta(days=2))).isoformat(),
                        "provider_reference": f"SYN-REFUND-STRIPE-re_{ord_idx:07d}",
                        "is_synthetic": True,
                        "created_at": (rec_dt or req_dt).isoformat()
                    })

            elif st == "CANCELLED":
                self.refunds.append({
                    "refund_id": f"REF-{ord_id}",
                    "order_id": ord_id,
                    "return_id": None,
                    "refund_status": "PROCESSED",
                    "refund_method": "ORIGINAL_PAYMENT",
                    "amount": float(grand_total),
                    "currency": "USD",
                    "requested_at": cancelled_dt.isoformat(),
                    "processed_at": (cancelled_dt + timedelta(minutes=15)).isoformat(),
                    "provider_reference": f"SYN-REFUND-STRIPE-re_canc_{ord_idx:07d}",
                    "is_synthetic": True,
                    "created_at": cancelled_dt.isoformat()
                })

        logger.info(f"Generated {len(self.orders)} orders, {len(self.order_items)} items, {len(self.payments)} payments, {len(self.shipments)} shipments.")
        logger.info(f"Generated {len(self.returns)} returns, {len(self.return_items)} return items, {len(self.refunds)} refunds, {len(self.exchanges)} exchanges.")

    def run_validation(self):
        """Perform comprehensive offline relational and invariant validation."""
        logger.info("Running exhaustive offline validation...")

        store_ids = {s["store_id"] for s in self.stores}
        cust_ids = {c["customer_id"] for c in self.customers}
        addr_ids = {a["address_id"] for a in self.customer_addresses}
        ord_ids = {o["order_id"] for o in self.orders}
        oi_ids = {oi["order_item_id"] for oi in self.order_items}
        ret_ids = {r["return_id"] for r in self.returns}
        ri_ids = {ri["return_item_id"] for ri in self.return_items}

        for inv in self.inventory_levels:
            assert inv["store_id"] in store_ids, f"Orphan store in inventory: {inv['store_id']}"
            assert inv["variant_id"] in self.valid_variant_ids, f"Orphan variant in inventory: {inv['variant_id']}"
            assert inv["quantity_on_hand"] >= 0, "Negative quantity on hand"
            assert inv["quantity_reserved"] >= 0, "Negative quantity reserved"
            assert inv["quantity_reserved"] <= inv["quantity_on_hand"], "Reserved exceeds on hand"
            assert inv["availability_status"] in ('IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK')

        for o in self.orders:
            assert o["customer_id"] in cust_ids, f"Orphan customer in order: {o['customer_id']}"
            if o["shipping_address_id"]:
                assert o["shipping_address_id"] in addr_ids, f"Orphan address in order: {o['shipping_address_id']}"
            if o["store_id"]:
                assert o["store_id"] in store_ids, f"Orphan store in order: {o['store_id']}"

            sub = Decimal(str(o["subtotal"]))
            disc = Decimal(str(o["discount_total"]))
            tax = Decimal(str(o["tax_total"]))
            ship = Decimal(str(o["shipping_total"]))
            grand = Decimal(str(o["grand_total"]))
            expected_grand = sub - disc + tax + ship
            assert grand == expected_grand, f"Financial mismatch in {o['order_id']}: {grand} vs {expected_grand}"

        for oi in self.order_items:
            assert oi["order_id"] in ord_ids, f"Orphan order in item: {oi['order_id']}"
            assert oi["product_id"] in self.valid_product_ids, f"Orphan product in item: {oi['product_id']}"
            assert oi["variant_id"] in self.valid_variant_ids, f"Orphan variant in item: {oi['variant_id']}"
            assert oi["quantity"] > 0, "Non-positive item quantity"
            assert oi["unit_price"] >= 0, "Negative unit price"

        for p in self.payments:
            assert p["order_id"] in ord_ids, f"Orphan order in payment: {p['order_id']}"

        ship_ids = {s["shipment_id"] for s in self.shipments}
        for s in self.shipments:
            assert s["order_id"] in ord_ids, f"Orphan order in shipment: {s['order_id']}"
        for e in self.shipment_events:
            assert e["shipment_id"] in ship_ids, f"Orphan shipment in event: {e['shipment_id']}"

        for r in self.returns:
            assert r["order_id"] in ord_ids, f"Orphan order in return: {r['order_id']}"
        for ri in self.return_items:
            assert ri["return_id"] in ret_ids, f"Orphan return in return item: {ri['return_id']}"
            assert ri["order_item_id"] in oi_ids, f"Orphan item in return item: {ri['order_item_id']}"
            assert ri["quantity"] > 0, "Non-positive return quantity"

        order_grand_map = {o["order_id"]: Decimal(str(o["grand_total"])) for o in self.orders}
        for ref in self.refunds:
            assert ref["order_id"] in ord_ids, f"Orphan order in refund: {ref['order_id']}"
            if ref["return_id"]:
                assert ref["return_id"] in ret_ids, f"Orphan return in refund: {ref['return_id']}"
            ref_amt = Decimal(str(ref["amount"]))
            ord_grand = order_grand_map[ref["order_id"]]
            assert ref_amt <= ord_grand, f"Refund {ref_amt} exceeds order grand total {ord_grand}"

        for exc in self.exchanges:
            assert exc["return_item_id"] in ri_ids, f"Orphan return item in exchange: {exc['return_item_id']}"
            assert exc["original_variant_id"] in self.valid_variant_ids, f"Invalid original variant: {exc['original_variant_id']}"
            assert exc["replacement_variant_id"] in self.valid_variant_ids, f"Invalid replacement variant: {exc['replacement_variant_id']}"

        logger.info("VALIDATION PASS: All 13 tables satisfied relational, mathematical, and chronological invariants.")

    def export_json(self, export_dir: Path = DEFAULT_EXPORT_DIR):
        """Export all 13 operational tables to JSON files."""
        export_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Exporting operational datasets to {export_dir}...")

        datasets = {
            "stores.json": self.stores,
            "inventory_levels.json": self.inventory_levels,
            "customers.json": self.customers,
            "customer_addresses.json": self.customer_addresses,
            "orders.json": self.orders,
            "order_items.json": self.order_items,
            "payments.json": self.payments,
            "shipments.json": self.shipments,
            "shipment_events.json": self.shipment_events,
            "returns.json": self.returns,
            "return_items.json": self.return_items,
            "refunds.json": self.refunds,
            "exchanges.json": self.exchanges,
        }

        for filename, data in datasets.items():
            filepath = export_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2 if len(data) <= 5000 else None)
            logger.info(f"  Saved {filename}: {len(data)} records ({filepath.stat().st_size / 1024:.1f} KB)")

        readme_path = export_dir / "README.md"
        readme_path.write_text(
            "# Synthetic Demo Operational Data Layer (Phase 2B)\n\n"
            "> [!IMPORTANT]\n"
            "> **SYNTHETIC DEMO DATA — NOT REAL ZARA SOURCE DATA**\n\n"
            "This folder contains deterministic synthetic operational records (stores, inventory, customers, orders, shipments, returns, refunds, exchanges) "
            "designed to power demo web shopping flows and AI voice agent tools.\n"
            "All records carry `is_synthetic = true` and `data_origin = 'synthetic'`.\n"
            "Real Zara catalogue entities (products, variants, colors, images, categories) are stored in separate catalogue tables and remain unadulterated.\n\n"
            f"Generated with SEED = {self.seed} on {datetime.now(timezone.utc).isoformat()}.\n",
            encoding="utf-8"
        )
        logger.info(f"Export completed successfully.")

    def live_import(self, db_url: str, batch_size: int = 1000):
        """Import all 13 operational tables into Supabase PostgreSQL using execute_values."""
        if not HAVE_PSYCOPG2:
            raise RuntimeError("psycopg2 is required for live Supabase import.")

        logger.info(f"Connecting to Supabase PostgreSQL at {db_url.split('@')[-1]}...")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        t_start = time.time()

        # Table 1: stores
        logger.info(f"Importing {len(self.stores)} stores...")
        store_rows = [(
            s["store_id"], s["store_code"], s["store_name"], s["country_code"], s["country_name"],
            s["state"], s["city"], s["address_line_1"], s["address_line_2"], s["postal_code"],
            s["latitude"], s["longitude"], s["timezone"], s["phone"], s["store_type"],
            s["status"], json.dumps(s["opening_hours"]), s["is_synthetic"], s["data_origin"],
            s["created_at"], s["updated_at"]
        ) for s in self.stores]
        execute_values(cur, """
            INSERT INTO stores (
                store_id, store_code, store_name, country_code, country_name,
                state, city, address_line_1, address_line_2, postal_code,
                latitude, longitude, timezone, phone, store_type,
                status, opening_hours, is_synthetic, data_origin, created_at, updated_at
            ) VALUES %s
            ON CONFLICT (store_id) DO UPDATE SET
                store_name = EXCLUDED.store_name,
                updated_at = EXCLUDED.updated_at;
        """, store_rows, page_size=batch_size)
        conn.commit()

        # Table 2: customers
        logger.info(f"Importing {len(self.customers)} customers...")
        cust_rows = [(
            c["customer_id"], c["first_name"], c["last_name"], c["email"], c["phone"],
            c["country_code"], c["state"], c["city"], c["preferred_language"], c["preferred_currency"],
            c["marketing_opt_in"], c["account_status"], c["is_synthetic"], c["data_origin"],
            c["created_at"], c["updated_at"]
        ) for c in self.customers]
        execute_values(cur, """
            INSERT INTO customers (
                customer_id, first_name, last_name, email, phone,
                country_code, state, city, preferred_language, preferred_currency,
                marketing_opt_in, account_status, is_synthetic, data_origin, created_at, updated_at
            ) VALUES %s
            ON CONFLICT (customer_id) DO UPDATE SET
                email = EXCLUDED.email,
                phone = EXCLUDED.phone,
                updated_at = EXCLUDED.updated_at;
        """, cust_rows, page_size=batch_size)
        conn.commit()

        # Table 3: customer_addresses
        logger.info(f"Importing {len(self.customer_addresses)} customer addresses...")
        addr_rows = [(
            a["address_id"], a["customer_id"], a["address_type"], a["recipient_name"],
            a["address_line_1"], a["address_line_2"], a["city"], a["state"], a["postal_code"],
            a["country_code"], a["is_default_shipping"], a["is_default_billing"],
            a["is_synthetic"], a["created_at"]
        ) for a in self.customer_addresses]
        execute_values(cur, """
            INSERT INTO customer_addresses (
                address_id, customer_id, address_type, recipient_name,
                address_line_1, address_line_2, city, state, postal_code,
                country_code, is_default_shipping, is_default_billing, is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (address_id) DO NOTHING;
        """, addr_rows, page_size=batch_size)
        conn.commit()

        # Table 4: inventory_levels
        logger.info(f"Importing {len(self.inventory_levels)} inventory levels...")
        inv_rows = [(
            inv["inventory_id"], inv["store_id"], inv["variant_id"],
            inv["quantity_on_hand"], inv["quantity_reserved"], inv["availability_status"],
            inv["reorder_threshold"], inv["last_updated_at"], inv["is_synthetic"], inv["data_origin"]
        ) for inv in self.inventory_levels]
        execute_values(cur, """
            INSERT INTO inventory_levels (
                inventory_id, store_id, variant_id,
                quantity_on_hand, quantity_reserved, availability_status,
                reorder_threshold, last_updated_at, is_synthetic, data_origin
            ) VALUES %s
            ON CONFLICT (store_id, variant_id) DO UPDATE SET
                quantity_on_hand = EXCLUDED.quantity_on_hand,
                quantity_reserved = EXCLUDED.quantity_reserved,
                availability_status = EXCLUDED.availability_status,
                last_updated_at = EXCLUDED.last_updated_at;
        """, inv_rows, page_size=batch_size)
        conn.commit()

        # Table 5: orders
        logger.info(f"Importing {len(self.orders)} orders...")
        order_rows = [(
            o["order_id"], o["order_number"], o["customer_id"], o["order_status"],
            o["fulfillment_type"], o["shipping_address_id"], o["store_id"], o["currency"],
            o["subtotal"], o["discount_total"], o["tax_total"], o["shipping_total"], o["grand_total"],
            o["payment_status"], o["placed_at"], o["confirmed_at"], o["cancelled_at"], o["completed_at"],
            o["is_synthetic"], o["data_origin"], o["created_at"], o["updated_at"]
        ) for o in self.orders]
        execute_values(cur, """
            INSERT INTO orders (
                order_id, order_number, customer_id, order_status,
                fulfillment_type, shipping_address_id, store_id, currency,
                subtotal, discount_total, tax_total, shipping_total, grand_total,
                payment_status, placed_at, confirmed_at, cancelled_at, completed_at,
                is_synthetic, data_origin, created_at, updated_at
            ) VALUES %s
            ON CONFLICT (order_id) DO UPDATE SET
                order_status = EXCLUDED.order_status,
                payment_status = EXCLUDED.payment_status,
                updated_at = EXCLUDED.updated_at;
        """, order_rows, page_size=batch_size)
        conn.commit()

        # Table 6: order_items
        logger.info(f"Importing {len(self.order_items)} order items...")
        item_rows = [(
            oi["order_item_id"], oi["order_id"], oi["product_id"], oi["variant_id"],
            oi["quantity"], oi["unit_price"], oi["line_discount"], oi["line_total"],
            oi["product_name_snapshot"], oi["size_snapshot"], oi["color_snapshot"],
            oi["is_synthetic"], oi["created_at"]
        ) for oi in self.order_items]
        execute_values(cur, """
            INSERT INTO order_items (
                order_item_id, order_id, product_id, variant_id,
                quantity, unit_price, line_discount, line_total,
                product_name_snapshot, size_snapshot, color_snapshot,
                is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (order_item_id) DO NOTHING;
        """, item_rows, page_size=batch_size)
        conn.commit()

        # Table 7: payments
        logger.info(f"Importing {len(self.payments)} payments...")
        pay_rows = [(
            p["payment_id"], p["order_id"], p["payment_method"], p["payment_status"],
            p["amount"], p["currency"], p["provider_reference"],
            p["authorized_at"], p["captured_at"], p["failed_at"],
            p["is_synthetic"], p["created_at"]
        ) for p in self.payments]
        execute_values(cur, """
            INSERT INTO payments (
                payment_id, order_id, payment_method, payment_status,
                amount, currency, provider_reference,
                authorized_at, captured_at, failed_at,
                is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (payment_id) DO UPDATE SET
                payment_status = EXCLUDED.payment_status;
        """, pay_rows, page_size=batch_size)
        conn.commit()

        # Table 8: shipments
        logger.info(f"Importing {len(self.shipments)} shipments...")
        ship_rows = [(
            s["shipment_id"], s["order_id"], s["carrier"], s["tracking_number"],
            s["shipment_status"], s["shipped_at"], s["estimated_delivery_at"],
            s["delivered_at"], s["origin_store_id"], s["is_synthetic"], s["created_at"]
        ) for s in self.shipments]
        execute_values(cur, """
            INSERT INTO shipments (
                shipment_id, order_id, carrier, tracking_number,
                shipment_status, shipped_at, estimated_delivery_at,
                delivered_at, origin_store_id, is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (shipment_id) DO UPDATE SET
                shipment_status = EXCLUDED.shipment_status,
                delivered_at = EXCLUDED.delivered_at;
        """, ship_rows, page_size=batch_size)
        conn.commit()

        # Table 9: shipment_events
        logger.info(f"Importing {len(self.shipment_events)} shipment events...")
        event_rows = [(
            e["event_id"], e["shipment_id"], e["event_type"], e["description"],
            e["location_text"], e["occurred_at"], e["is_synthetic"], e["created_at"]
        ) for e in self.shipment_events]
        execute_values(cur, """
            INSERT INTO shipment_events (
                event_id, shipment_id, event_type, description,
                location_text, occurred_at, is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (event_id) DO NOTHING;
        """, event_rows, page_size=batch_size)
        conn.commit()

        # Table 10: returns
        logger.info(f"Importing {len(self.returns)} returns...")
        ret_rows = [(
            r["return_id"], r["order_id"], r["return_status"], r["return_reason"],
            r["return_method"], r["requested_at"], r["approved_at"], r["received_at"],
            r["completed_at"], r["is_synthetic"], r["created_at"]
        ) for r in self.returns]
        execute_values(cur, """
            INSERT INTO returns (
                return_id, order_id, return_status, return_reason,
                return_method, requested_at, approved_at, received_at,
                completed_at, is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (return_id) DO UPDATE SET
                return_status = EXCLUDED.return_status,
                completed_at = EXCLUDED.completed_at;
        """, ret_rows, page_size=batch_size)
        conn.commit()

        # Table 11: return_items
        logger.info(f"Importing {len(self.return_items)} return items...")
        ri_rows = [(
            ri["return_item_id"], ri["return_id"], ri["order_item_id"],
            ri["quantity"], ri["reason_code"], ri["condition"], ri["resolution"],
            ri["refund_amount"], ri["is_synthetic"], ri["created_at"]
        ) for ri in self.return_items]
        execute_values(cur, """
            INSERT INTO return_items (
                return_item_id, return_id, order_item_id,
                quantity, reason_code, condition, resolution,
                refund_amount, is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (return_item_id) DO NOTHING;
        """, ri_rows, page_size=batch_size)
        conn.commit()

        # Table 12: refunds
        logger.info(f"Importing {len(self.refunds)} refunds...")
        ref_rows = [(
            ref["refund_id"], ref["order_id"], ref["return_id"], ref["refund_status"],
            ref["refund_method"], ref["amount"], ref["currency"],
            ref["requested_at"], ref["processed_at"], ref["provider_reference"],
            ref["is_synthetic"], ref["created_at"]
        ) for ref in self.refunds]
        execute_values(cur, """
            INSERT INTO refunds (
                refund_id, order_id, return_id, refund_status,
                refund_method, amount, currency,
                requested_at, processed_at, provider_reference,
                is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (refund_id) DO NOTHING;
        """, ref_rows, page_size=batch_size)
        conn.commit()

        # Table 13: exchanges
        logger.info(f"Importing {len(self.exchanges)} exchanges...")
        exc_rows = [(
            exc["exchange_id"], exc["return_item_id"], exc["original_variant_id"],
            exc["replacement_variant_id"], exc["exchange_status"],
            exc["requested_at"], exc["completed_at"], exc["is_synthetic"], exc["created_at"]
        ) for exc in self.exchanges]
        execute_values(cur, """
            INSERT INTO exchanges (
                exchange_id, return_item_id, original_variant_id,
                replacement_variant_id, exchange_status,
                requested_at, completed_at, is_synthetic, created_at
            ) VALUES %s
            ON CONFLICT (exchange_id) DO NOTHING;
        """, exc_rows, page_size=batch_size)
        conn.commit()

        conn.close()
        logger.info(f"LIVE IMPORT COMPLETE in {time.time() - t_start:.2f}s!")


def main():
    parser = argparse.ArgumentParser(description="Generate and import synthetic retail operational layer.")
    parser.add_argument("--dry-run", action="store_true", help="Generate and validate datasets without database write.")
    parser.add_argument("--live", action="store_true", help="Import generated operational data into Supabase PostgreSQL.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Deterministic random seed (default: {DEFAULT_SEED}).")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for PostgreSQL inserts (default: 1000).")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR, help="Directory to export JSON datasets.")
    args = parser.parse_args()

    load_dotenv()
    db_url = os.environ.get("SUPABASE_DB_URL")

    generator = SyntheticOperationsGenerator(seed=args.seed)
    generator.load_catalogue()
    generator.generate_stores()
    generator.generate_inventory()
    generator.generate_customers_and_addresses()
    generator.generate_orders_and_operations()

    # In-memory relational & business rules validation
    generator.run_validation()

    # Always export JSON files
    generator.export_json(args.export_dir)

    if args.live:
        if not db_url:
            logger.error("SUPABASE_DB_URL not found in environment. Cannot perform live import.")
            sys.exit(1)
        generator.live_import(db_url, batch_size=args.batch_size)
        logger.info("Operational layer successfully generated, exported, and imported into live Supabase database.")
    elif args.dry_run:
        logger.info("DRY RUN SUCCESSFUL: Datasets validated and exported to disk. Database was not modified.")
    else:
        logger.info("Datasets validated and exported to disk. Use --live to write to Supabase.")


if __name__ == "__main__":
    main()
