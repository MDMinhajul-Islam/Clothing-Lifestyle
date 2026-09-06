#!/usr/bin/env python3
"""Bulk import pipeline for Zara US catalogue into Supabase / PostgreSQL.

Supports:
  1. Offline DRY RUN mode with full schema, constraint, FK, and sample query verification
     using an in-memory SQLite relational engine.
  2. Production Supabase direct PostgreSQL batched upserts via psycopg2 when configured.
  3. Production Supabase PostgREST batch upserts via Python standard library HTTP fallback.

Idempotent: Re-running against the same data safely merges updates without duplicates.
"""

import argparse
import datetime
import json
import logging
import os
import re
import sqlite3
import sys
import time
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request
import urllib.error

try:
    import psycopg2
    from psycopg2.extras import execute_batch
    HAVE_PSYCOPG2 = True
except ImportError:
    HAVE_PSYCOPG2 = False

# Project paths
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "zara"

# Expected row counts from Phase 1D audit
EXPECTED_COUNTS = {
    "products": 6018,
    "categories": 745,
    "product_variants": 38002,
    "product_colors": 7717,
    "product_images": 40228,
    "product_categories": 8200,  # 8,200 valid products (273 card-edges skipped)
    "product_price_history": 6018,
    "catalogue_sync_state": 6276,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("supabase_importer")


def load_dotenv(env_path: Path = ROOT_DIR / ".env"):
    """Lightweight .env parser using standard library."""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k not in os.environ:
                    os.environ[k] = v


def canonicalize_image_asset_key(url: str) -> str:
    """Extract clean CDN asset key without query params."""
    if not url:
        return ""
    p = urlsplit(url)
    return f"{p.netloc.lower()}{p.path.lower()}"


def slugify(text: str) -> str:
    """Generate url-safe slug from text."""
    if not text:
        return ""
    s = text.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[-\s]+", "-", s).strip("-")


def extract_category_slug(url: str, name: str) -> str:
    """Extract slug from category URL or fallback to slugified name."""
    if url:
        path = urlsplit(url).path.rstrip("/")
        filename = path.split("/")[-1]
        if filename.endswith(".html"):
            return filename[:-5]
        if filename:
            return filename
    return slugify(name)[:80]


def chunk_list(items: list, batch_size: int):
    """Yield successive batch_size chunks from items."""
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


class CatalogueDataLoader:
    """Loads and transforms normalized JSON files into DB-ready records."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.products = []
        self.categories = []
        self.variants = []
        self.colors = []
        self.images = []
        self.product_categories = []
        self.price_history = []
        self.sync_state = []
        self.valid_product_ids = set()
        self.valid_category_ids = set()
        self.skipped_card_category_edges = 0

    def load_all(self):
        logger.info(f"Loading raw datasets from {self.data_dir}...")

        # 1. Products
        with open(self.data_dir / "product_details.json", "r", encoding="utf-8") as f:
            raw_products = json.load(f)
        self.products = self._transform_products(raw_products)
        self.valid_product_ids = {p["product_id"] for p in self.products}
        logger.info(f"Loaded {len(self.products)} products")

        # 2. Categories
        with open(self.data_dir / "categories.json", "r", encoding="utf-8") as f:
            raw_cats = json.load(f)
        self.categories = self._transform_categories(raw_cats)
        self.valid_category_ids = {c["category_id"] for c in self.categories}
        logger.info(f"Loaded {len(self.categories)} categories (topologically sorted)")

        # 3. Product Variants
        with open(self.data_dir / "product_variants.json", "r", encoding="utf-8") as f:
            raw_vars = json.load(f)
        self.variants = self._transform_variants(raw_vars)
        logger.info(f"Loaded {len(self.variants)} product variants")

        # 4. Product Colors
        with open(self.data_dir / "product_colors.json", "r", encoding="utf-8") as f:
            raw_colors = json.load(f)
        self.colors = self._transform_colors(raw_colors)
        logger.info(f"Loaded {len(self.colors)} product colors (disambiguated casing duplicates)")

        # 5. Product Images
        with open(self.data_dir / "product_images.json", "r", encoding="utf-8") as f:
            raw_images = json.load(f)
        self.images = self._transform_images(raw_images)
        logger.info(f"Loaded {len(self.images)} product images")

        # 6. Product Categories (Many-to-Many)
        with open(self.data_dir / "product_categories.json", "r", encoding="utf-8") as f:
            raw_pc = json.load(f)
        self.product_categories = self._transform_product_categories(raw_pc)
        logger.info(f"Loaded {len(self.product_categories)} valid product_categories relationships (skipped {self.skipped_card_category_edges} unresolved card edges)")

        # 7. Product Price History
        with open(self.data_dir / "product_price_history.json", "r", encoding="utf-8") as f:
            raw_hist = json.load(f)
        self.price_history = self._transform_price_history(raw_hist)
        logger.info(f"Loaded {len(self.price_history)} product price history records")

        # 8. Catalogue Sync State
        with open(self.data_dir / "product_detail_queue.json", "r", encoding="utf-8") as f:
            raw_queue = json.load(f)
        self.sync_state = self._transform_sync_state(raw_queue)
        logger.info(f"Loaded {len(self.sync_state)} catalogue sync state records")

    def _transform_products(self, raw: list) -> list:
        records = []
        for p in raw:
            curr_p = float(Decimal(str(p["current_price"]))) if p.get("current_price") is not None else None
            orig_p = float(Decimal(str(p["original_price"]))) if p.get("original_price") is not None else None
            sale_p = float(Decimal(str(p["sale_price"]))) if p.get("sale_price") is not None else None
            records.append({
                "product_id": p["product_id"],
                "source_product_id": p.get("source_product_id"),
                "product_group_id": p.get("product_group_id"),
                "commercial_reference": p.get("commercial_reference"),
                "sku": p.get("sku"),
                "brand": p.get("brand") or "ZARA",
                "department": p.get("department"),
                "market": p.get("market") or "US",
                "locale": p.get("locale") or "en",
                "exact_product_name": p.get("exact_product_name"),
                "short_description": p.get("short_description"),
                "long_description": p.get("long_description"),
                "fit_information": p.get("fit_information"),
                "care_information": p.get("care_information"),
                "composition_text": p.get("composition_text"),
                "material_text": p.get("material_text"),
                "currency": p.get("currency") or "USD",
                "current_price": curr_p,
                "original_price": orig_p,
                "sale_price": sale_p,
                "is_on_sale": bool(p.get("is_on_sale", False)),
                "product_url": p.get("product_url"),
                "canonical_url": p.get("canonical_url"),
                "source_content_hash": p.get("source_content_hash"),
                "lifecycle_status": p.get("lifecycle_status") or "ACTIVE",
                "first_seen_at": p.get("first_seen_at"),
                "last_seen_at": p.get("last_seen_at"),
                "last_synced_at": p.get("last_synced_at"),
                "price_last_verified_at": p.get("price_last_verified_at") or p.get("last_seen_at"),
            })
        return records

    def _transform_categories(self, raw: list) -> list:
        cat_map = {c["category_id"]: c for c in raw}
        ordered = []
        visited = set()

        def visit(cid):
            if cid in visited or cid not in cat_map:
                return
            parent_id = cat_map[cid].get("parent_category_id")
            if parent_id and parent_id in cat_map:
                visit(parent_id)
            visited.add(cid)
            c = cat_map[cid]
            ordered.append({
                "category_id": c["category_id"],
                "parent_category_id": c.get("parent_category_id"),
                "department": c.get("department"),
                "name": c.get("name") or "Category",
                "slug": extract_category_slug(c.get("canonical_url") or c.get("url"), c.get("name") or ""),
                "source_url": c.get("canonical_url") or c.get("url"),
                "category_type": c.get("route_type"),
                "status": c.get("crawl_status"),
            })

        for c in raw:
            visit(c["category_id"])

        return ordered

    def _transform_variants(self, raw: list) -> list:
        records = []
        for v in raw:
            records.append({
                "variant_id": v["variant_id"],
                "product_id": v["product_id"],
                "source_product_id": v.get("source_product_id"),
                "commercial_reference": v.get("commercial_reference"),
                "sku": v.get("sku"),
                "color_name": v.get("color_name"),
                "color_code": v.get("color_code"),
                "size_name": v.get("size_name"),
                "size_code": v.get("size_code"),
                "size_label": v.get("size_label"),
                "public_availability_state": v.get("public_availability_state") or "UNKNOWN",
                "availability_last_verified_at": v.get("last_seen_at"),
                "variant_url": v.get("variant_url"),
                "first_seen_at": v.get("first_seen_at"),
                "last_seen_at": v.get("last_seen_at"),
            })
        return records

    def _transform_colors(self, raw: list) -> list:
        records = []
        seen_color_ids = set()
        for c in raw:
            cid = c["color_id"]
            if cid in seen_color_ids:
                disp = c.get("display_order", 1)
                cid = f"{cid}-{disp}"
            seen_color_ids.add(cid)

            records.append({
                "color_id": cid,
                "product_id": c["product_id"],
                "color_name": c.get("color_name"),
                "color_code": c.get("color_code"),
                "color_reference": c.get("color_reference"),
                "color_specific_url": c.get("color_specific_url"),
                "display_order": c.get("display_order", 0),
                "last_verified_at": c.get("last_verified_at"),
            })
        return records

    def _transform_images(self, raw: list) -> list:
        records = []
        for img in raw:
            records.append({
                "image_id": img["image_id"],
                "product_id": img["product_id"],
                "variant_id": img.get("variant_id"),
                "color_name": img.get("color_name"),
                "color_code": img.get("color_code"),
                "source_image_url": img["source_image_url"],
                "image_role": img.get("image_role"),
                "display_order": img.get("display_order", 0),
                "alt_text": img.get("alt_text"),
                "image_asset_key": canonicalize_image_asset_key(img["source_image_url"]),
                "image_last_verified_at": img.get("image_last_verified_at"),
            })
        return records

    def _transform_product_categories(self, raw: list) -> list:
        records = []
        skipped = 0
        seen_pairs = set()
        for pc in raw:
            pid = pc["product_id"]
            cid = pc["category_id"]
            if pid not in self.valid_product_ids:
                skipped += 1
                continue
            if (pid, cid) in seen_pairs:
                continue
            seen_pairs.add((pid, cid))
            records.append({
                "product_id": pid,
                "category_id": cid,
            })
        self.skipped_card_category_edges = skipped
        return records

    def _transform_price_history(self, raw: list) -> list:
        records = []
        for h in raw:
            curr_p = float(Decimal(str(h["current_price"]))) if h.get("current_price") is not None else None
            orig_p = float(Decimal(str(h["original_price"]))) if h.get("original_price") is not None else None
            sale_p = float(Decimal(str(h["sale_price"]))) if h.get("sale_price") is not None else None
            records.append({
                "history_id": f"{h['product_id']}:{h['observed_at']}",
                "product_id": h["product_id"],
                "observed_at": h["observed_at"],
                "currency": h.get("currency") or "USD",
                "original_price": orig_p,
                "current_price": curr_p,
                "sale_price": sale_p,
                "is_on_sale": bool(h.get("is_on_sale", False)),
            })
        return records

    def _transform_sync_state(self, raw: list) -> list:
        prod_map = {p["product_id"]: p for p in self.products}
        records = []
        for q in raw:
            qid = q["id"]
            matched_prod = prod_map.get(qid)
            canonical = matched_prod["canonical_url"] if matched_prod else None
            c_hash = q.get("checkpoint", {}).get("content_hash") if isinstance(q.get("checkpoint"), dict) else None
            synced_at = q.get("checkpoint", {}).get("enriched_at") if isinstance(q.get("checkpoint"), dict) else None
            status = q.get("status")

            records.append({
                "id": qid,
                "product_id": qid if status == "COMPLETE" else None,
                "status": status,
                "source_url": q.get("url"),
                "canonical_url": canonical,
                "attempt_count": q.get("attempt_count", 0),
                "last_error": q.get("error"),
                "first_seen_at": matched_prod["first_seen_at"] if matched_prod else q.get("last_attempt_at"),
                "last_seen_at": matched_prod["last_seen_at"] if matched_prod else q.get("last_attempt_at"),
                "last_attempt_at": q.get("last_attempt_at"),
                "last_synced_at": synced_at,
                "source_content_hash": c_hash,
                "lifecycle_status": "ACTIVE" if status == "COMPLETE" else "UNRESOLVED_TERMINAL",
            })
        return records


class DryRunRelationalValidator:
    """Executes full relational database import and query verification in-memory."""

    def __init__(self, loader: CatalogueDataLoader):
        self.loader = loader
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.results = {}

    def setup_schema(self):
        cur = self.conn.cursor()
        cur.executescript("""
        CREATE TABLE products (
            product_id TEXT PRIMARY KEY,
            source_product_id TEXT,
            product_group_id TEXT,
            commercial_reference TEXT,
            sku TEXT,
            brand TEXT NOT NULL DEFAULT 'ZARA',
            department TEXT NOT NULL,
            market TEXT NOT NULL DEFAULT 'US',
            locale TEXT NOT NULL DEFAULT 'en',
            exact_product_name TEXT NOT NULL,
            short_description TEXT,
            long_description TEXT,
            fit_information TEXT,
            care_information TEXT,
            composition_text TEXT,
            material_text TEXT,
            currency TEXT NOT NULL DEFAULT 'USD',
            current_price REAL NOT NULL,
            original_price REAL,
            sale_price REAL,
            is_on_sale INTEGER NOT NULL DEFAULT 0,
            product_url TEXT,
            canonical_url TEXT,
            source_content_hash TEXT,
            lifecycle_status TEXT NOT NULL DEFAULT 'ACTIVE',
            first_seen_at TEXT,
            last_seen_at TEXT,
            last_synced_at TEXT,
            price_last_verified_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            CHECK (current_price >= 0)
        );

        CREATE TABLE categories (
            category_id TEXT PRIMARY KEY,
            parent_category_id TEXT REFERENCES categories(category_id) ON DELETE SET NULL,
            department TEXT,
            name TEXT NOT NULL,
            slug TEXT,
            source_url TEXT,
            category_type TEXT,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE product_variants (
            variant_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
            source_product_id TEXT,
            commercial_reference TEXT,
            sku TEXT,
            color_name TEXT,
            color_code TEXT,
            size_name TEXT,
            size_code TEXT,
            size_label TEXT,
            public_availability_state TEXT NOT NULL DEFAULT 'UNKNOWN',
            availability_last_verified_at TEXT,
            variant_url TEXT,
            first_seen_at TEXT,
            last_seen_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            CHECK (public_availability_state IN ('IN_STOCK', 'OUT_OF_STOCK', 'UNKNOWN'))
        );

        CREATE TABLE product_colors (
            color_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
            color_name TEXT,
            color_code TEXT,
            color_reference TEXT,
            color_specific_url TEXT,
            display_order INTEGER NOT NULL DEFAULT 0,
            last_verified_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE product_images (
            image_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
            variant_id TEXT REFERENCES product_variants(variant_id) ON DELETE SET NULL,
            color_name TEXT,
            color_code TEXT,
            source_image_url TEXT NOT NULL,
            image_role TEXT,
            display_order INTEGER NOT NULL DEFAULT 0,
            alt_text TEXT,
            image_asset_key TEXT,
            image_last_verified_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE product_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
            category_id TEXT NOT NULL REFERENCES categories(category_id) ON DELETE CASCADE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (product_id, category_id)
        );

        CREATE TABLE product_price_history (
            history_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
            observed_at TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            original_price REAL,
            current_price REAL NOT NULL,
            sale_price REAL,
            is_on_sale INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            CHECK (current_price >= 0)
        );

        CREATE TABLE catalogue_sync_state (
            id TEXT PRIMARY KEY,
            product_id TEXT,
            status TEXT NOT NULL,
            source_url TEXT,
            canonical_url TEXT,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            first_seen_at TEXT,
            last_seen_at TEXT,
            last_attempt_at TEXT,
            last_synced_at TEXT,
            source_content_hash TEXT,
            lifecycle_status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        self.conn.commit()

    def run_import(self):
        cur = self.conn.cursor()

        # 1. products
        t0 = time.perf_counter()
        cur.executemany("""
        INSERT INTO products (
            product_id, source_product_id, product_group_id, commercial_reference, sku,
            brand, department, market, locale, exact_product_name, short_description,
            long_description, fit_information, care_information, composition_text,
            material_text, currency, current_price, original_price, sale_price,
            is_on_sale, product_url, canonical_url, source_content_hash, lifecycle_status,
            first_seen_at, last_seen_at, last_synced_at, price_last_verified_at
        ) VALUES (
            :product_id, :source_product_id, :product_group_id, :commercial_reference, :sku,
            :brand, :department, :market, :locale, :exact_product_name, :short_description,
            :long_description, :fit_information, :care_information, :composition_text,
            :material_text, :currency, :current_price, :original_price, :sale_price,
            :is_on_sale, :product_url, :canonical_url, :source_content_hash, :lifecycle_status,
            :first_seen_at, :last_seen_at, :last_synced_at, :price_last_verified_at
        );
        """, self.loader.products)

        # 2. categories
        cur.executemany("""
        INSERT INTO categories (
            category_id, parent_category_id, department, name, slug,
            source_url, category_type, status
        ) VALUES (
            :category_id, :parent_category_id, :department, :name, :slug,
            :source_url, :category_type, :status
        );
        """, self.loader.categories)

        # 3. product_variants
        cur.executemany("""
        INSERT INTO product_variants (
            variant_id, product_id, source_product_id, commercial_reference, sku,
            color_name, color_code, size_name, size_code, size_label,
            public_availability_state, availability_last_verified_at, variant_url,
            first_seen_at, last_seen_at
        ) VALUES (
            :variant_id, :product_id, :source_product_id, :commercial_reference, :sku,
            :color_name, :color_code, :size_name, :size_code, :size_label,
            :public_availability_state, :availability_last_verified_at, :variant_url,
            :first_seen_at, :last_seen_at
        );
        """, self.loader.variants)

        # 4. product_colors
        cur.executemany("""
        INSERT INTO product_colors (
            color_id, product_id, color_name, color_code, color_reference,
            color_specific_url, display_order, last_verified_at
        ) VALUES (
            :color_id, :product_id, :color_name, :color_code, :color_reference,
            :color_specific_url, :display_order, :last_verified_at
        );
        """, self.loader.colors)

        # 5. product_images
        cur.executemany("""
        INSERT INTO product_images (
            image_id, product_id, variant_id, color_name, color_code,
            source_image_url, image_role, display_order, alt_text,
            image_asset_key, image_last_verified_at
        ) VALUES (
            :image_id, :product_id, :variant_id, :color_name, :color_code,
            :source_image_url, :image_role, :display_order, :alt_text,
            :image_asset_key, :image_last_verified_at
        );
        """, self.loader.images)

        # 6. product_categories
        cur.executemany("""
        INSERT INTO product_categories (
            product_id, category_id
        ) VALUES (
            :product_id, :category_id
        );
        """, self.loader.product_categories)

        # 7. product_price_history
        cur.executemany("""
        INSERT INTO product_price_history (
            history_id, product_id, observed_at, currency, original_price,
            current_price, sale_price, is_on_sale
        ) VALUES (
            :history_id, :product_id, :observed_at, :currency, :original_price,
            :current_price, :sale_price, :is_on_sale
        );
        """, self.loader.price_history)

        # 8. catalogue_sync_state
        cur.executemany("""
        INSERT INTO catalogue_sync_state (
            id, product_id, status, source_url, canonical_url,
            attempt_count, last_error, first_seen_at, last_seen_at,
            last_attempt_at, last_synced_at, source_content_hash,
            lifecycle_status
        ) VALUES (
            :id, :product_id, :status, :source_url, :canonical_url,
            :attempt_count, :last_error, :first_seen_at, :last_seen_at,
            :last_attempt_at, :last_synced_at, :source_content_hash,
            :lifecycle_status
        );
        """, self.loader.sync_state)

        self.conn.commit()

        # Check foreign key violations
        fk_check = cur.execute("PRAGMA foreign_key_check;").fetchall()
        if fk_check:
            raise RuntimeError(f"Foreign key violations detected in Dry Run: {fk_check}")

        self.results = {
            "products": cur.execute("SELECT count(*) FROM products").fetchone()[0],
            "categories": cur.execute("SELECT count(*) FROM categories").fetchone()[0],
            "product_variants": cur.execute("SELECT count(*) FROM product_variants").fetchone()[0],
            "product_colors": cur.execute("SELECT count(*) FROM product_colors").fetchone()[0],
            "product_images": cur.execute("SELECT count(*) FROM product_images").fetchone()[0],
            "product_categories": cur.execute("SELECT count(*) FROM product_categories").fetchone()[0],
            "product_price_history": cur.execute("SELECT count(*) FROM product_price_history").fetchone()[0],
            "catalogue_sync_state": cur.execute("SELECT count(*) FROM catalogue_sync_state").fetchone()[0],
        }

    def validate_sample_queries(self):
        cur = self.conn.cursor()
        queries = {}

        # 1. Product lookup with variants, colors, images
        sample_pid = cur.execute("SELECT product_id FROM products LIMIT 1").fetchone()[0]
        prod_row = cur.execute("SELECT product_id, exact_product_name, current_price FROM products WHERE product_id = ?", (sample_pid,)).fetchone()
        vars_rows = cur.execute("SELECT count(*) FROM product_variants WHERE product_id = ?", (sample_pid,)).fetchone()[0]
        colors_rows = cur.execute("SELECT count(*) FROM product_colors WHERE product_id = ?", (sample_pid,)).fetchone()[0]
        images_rows = cur.execute("SELECT count(*) FROM product_images WHERE product_id = ?", (sample_pid,)).fetchone()[0]
        queries["product_detail_drilldown"] = {
            "product_id": prod_row[0],
            "name": prod_row[1],
            "price": prod_row[2],
            "variants_count": vars_rows,
            "colors_count": colors_rows,
            "images_count": images_rows,
        }

        # 2. Woman products under $100
        woman_under_100 = cur.execute("""
        SELECT count(*) FROM products 
        WHERE department = 'WOMAN' AND current_price < 100.0
        """).fetchone()[0]
        queries["woman_under_100_count"] = woman_under_100

        # 3. Products on sale
        on_sale_count = cur.execute("SELECT count(*) FROM products WHERE is_on_sale = 1").fetchone()[0]
        queries["on_sale_count"] = on_sale_count

        # 4. Products available in size 'M'
        size_m_products = cur.execute("""
        SELECT count(DISTINCT product_id) FROM product_variants 
        WHERE size_name = 'M' AND public_availability_state = 'IN_STOCK'
        """).fetchone()[0]
        queries["in_stock_size_m_products"] = size_m_products

        # 5. Products in top category
        top_cat_row = cur.execute("""
        SELECT c.category_id, c.name, c.department, count(pc.product_id) as prod_count
        FROM categories c
        JOIN product_categories pc ON c.category_id = pc.category_id
        GROUP BY c.category_id, c.name, c.department
        ORDER BY prod_count DESC LIMIT 1
        """).fetchone()
        if top_cat_row:
            queries["top_category_products"] = {
                "category_id": top_cat_row[0],
                "name": top_cat_row[1],
                "department": top_cat_row[2],
                "product_count": top_cat_row[3],
            }

        # 6. Price history lookup
        hist_count = cur.execute("SELECT count(*) FROM product_price_history WHERE product_id = ?", (sample_pid,)).fetchone()[0]
        queries["price_history_snapshots"] = hist_count

        return queries


class PostgresDirectClient:
    """Direct PostgreSQL client using psycopg2 for high-speed batched upserts."""

    def __init__(self, db_url: str):
        self.conn = psycopg2.connect(db_url)
        self.conn.autocommit = True

    def upsert_batch(self, table: str, records: list, conflict_col: str) -> int:
        if not records:
            return 0
        cols = list(records[0].keys())
        cols_str = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))

        conflicts = [c.strip() for c in conflict_col.split(",")]
        non_conflicts = [c for c in cols if c not in conflicts]
        if non_conflicts:
            update_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in non_conflicts])
            on_conflict_clause = f"ON CONFLICT ({conflict_col}) DO UPDATE SET {update_clause}"
        else:
            on_conflict_clause = f"ON CONFLICT ({conflict_col}) DO NOTHING"

        sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) {on_conflict_clause};"
        values = [[r[c] for c in cols] for r in records]
        cur = self.conn.cursor()
        execute_batch(cur, sql, values, page_size=len(records))
        return len(records)

    def close(self):
        self.conn.close()


class SupabasePostgrestClient:
    """Standard-library HTTP client for Supabase PostgREST batch upserts."""

    def __init__(self, url: str, service_role_key: str):
        self.url = url.rstrip("/")
        self.key = service_role_key

    def upsert_batch(self, table: str, records: list, on_conflict: str = None) -> int:
        endpoint = f"{self.url}/rest/v1/{table}"
        if on_conflict:
            endpoint += f"?on_conflict={on_conflict}"

        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal"
        }

        data = json.dumps(records).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status in (200, 201, 204):
                    return len(records)
                raise RuntimeError(f"Unexpected status {resp.status} from Supabase: {resp.read().decode('utf-8')}")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"Supabase PostgREST error on table {table} (HTTP {e.code}): {error_body}")

    def close(self):
        pass


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Zara US Catalogue Supabase Bulk Importer")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run validation in dry-run mode")
    parser.add_argument("--live", action="store_true", help="Execute real import against Supabase / PostgreSQL")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for upsert operations (default: 500)")
    args = parser.parse_args()

    # Default to dry-run unless --live is specified
    is_live = args.live
    is_dry_run = not is_live

    logger.info("====================================================================")
    logger.info("PHASE 2A - SUPABASE BULK IMPORT PIPELINE")
    logger.info(f"Mode: {'LIVE IMPORT' if is_live else 'DRY RUN VALIDATION'}")
    logger.info(f"Batch Size: {args.batch_size}")
    logger.info("====================================================================")

    # 1. Load and transform all data
    loader = CatalogueDataLoader()
    loader.load_all()

    # 2. Relational dry-run validation
    validator = DryRunRelationalValidator(loader)
    validator.setup_schema()
    validator.run_import()
    query_results = validator.validate_sample_queries()

    logger.info("====================================================================")
    logger.info("RELATIONAL DRY RUN VALIDATION RESULTS")
    logger.info("====================================================================")
    for table, count in validator.results.items():
        logger.info(f"  - {table:<25}: {count:>6} rows inserted")
    logger.info(f"  - Skipped unresolved card-category edges: {loader.skipped_card_category_edges}")
    logger.info("Foreign Key Validation: ZERO orphan relationships detected.")
    logger.info("Sample Query Verification:")
    for k, v in query_results.items():
        logger.info(f"  - {k}: {v}")

    if is_dry_run:
        logger.info("====================================================================")
        logger.info("SUPABASE_IMPORT_DRY_RUN_READY")
        logger.info("All 8 datasets passed schema mapping, data typing, foreign key trees,")
        logger.info("and constraint validations.")
        logger.info("To perform production import once credentials are configured:")
        logger.info("  python scripts/supabase/import_catalogue.py --live")
        logger.info("====================================================================")
        return

    # 3. Live import execution
    supabase_db_url = os.getenv("SUPABASE_DB_URL")
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not (supabase_db_url or (supabase_url and service_role_key)):
        logger.error("Neither SUPABASE_DB_URL nor (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY) are configured.")
        logger.error("Cannot proceed with live import without valid credentials.")
        sys.exit(1)

    if supabase_db_url and HAVE_PSYCOPG2:
        logger.info("Initializing direct PostgreSQL high-speed client (psycopg2)...")
        client = PostgresDirectClient(supabase_db_url)
    else:
        logger.info(f"Initializing Supabase PostgREST client at {supabase_url}...")
        client = SupabasePostgrestClient(supabase_url, service_role_key)

    import_sequence = [
        ("products", loader.products, "product_id"),
        ("categories", loader.categories, "category_id"),
        ("product_variants", loader.variants, "variant_id"),
        ("product_colors", loader.colors, "color_id"),
        ("product_images", loader.images, "image_id"),
        ("product_categories", loader.product_categories, "product_id,category_id"),
        ("product_price_history", loader.price_history, "history_id"),
        ("catalogue_sync_state", loader.sync_state, "id"),
    ]

    total_inserted = 0
    t_start = time.perf_counter()

    for table_name, records, conflict_col in import_sequence:
        logger.info(f"Importing {len(records)} rows into '{table_name}' in batches of {args.batch_size}...")
        table_count = 0
        t0 = time.perf_counter()
        for batch in chunk_list(records, args.batch_size):
            inserted = client.upsert_batch(table_name, batch, conflict_col)
            table_count += inserted
        t_tab = time.perf_counter() - t0
        logger.info(f"Successfully upserted {table_count} rows into '{table_name}' in {t_tab:.2f}s.")
        total_inserted += table_count

    client.close()
    elapsed = time.perf_counter() - t_start
    logger.info("====================================================================")
    logger.info("PRODUCTION SUPABASE IMPORT COMPLETED")
    logger.info(f"Total Rows Upserted: {total_inserted}")
    logger.info(f"Elapsed Time: {elapsed:.2f}s")
    logger.info("====================================================================")


if __name__ == "__main__":
    main()
