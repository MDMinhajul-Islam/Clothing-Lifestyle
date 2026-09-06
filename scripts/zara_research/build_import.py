"""Generate a reviewable PostgreSQL import from normalized data. Does not connect.

Run after normalize.py: python scripts/zara_research/build_import.py
Uses a research-only schema to avoid implying production inventory ownership.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/normalized/zara'


def quote(value):
    if value is None:
        return 'NULL'
    return "'" + str(value).replace("'", "''") + "'"


def build():
    products = json.loads((DATA / 'products.json').read_text(encoding='utf-8'))
    variants = json.loads((DATA / 'product_variants.json').read_text(encoding='utf-8'))
    images = json.loads((DATA / 'product_images.json').read_text(encoding='utf-8'))
    sql = ["BEGIN;", "SET LOCAL standard_conforming_strings = on;",
           "CREATE SCHEMA IF NOT EXISTS zara_research;",
           "CREATE TABLE IF NOT EXISTS zara_research.products (product_id text PRIMARY KEY, document jsonb NOT NULL);",
           "CREATE TABLE IF NOT EXISTS zara_research.variants (variant_id text PRIMARY KEY, product_id text NOT NULL REFERENCES zara_research.products(product_id), document jsonb NOT NULL, UNIQUE(variant_id, product_id));",
           "CREATE TABLE IF NOT EXISTS zara_research.images (product_id text NOT NULL REFERENCES zara_research.products(product_id), variant_id text, image_url text NOT NULL, document jsonb NOT NULL, FOREIGN KEY(variant_id, product_id) REFERENCES zara_research.variants(variant_id, product_id));",
           "CREATE UNIQUE INDEX IF NOT EXISTS images_gallery_unique ON zara_research.images(product_id, image_url) WHERE variant_id IS NULL;",
           "CREATE UNIQUE INDEX IF NOT EXISTS images_variant_unique ON zara_research.images(product_id, variant_id, image_url) WHERE variant_id IS NOT NULL;"]
    for p in products:
        sql.append('INSERT INTO zara_research.products VALUES (' + quote(p['product_id']) + ', ' + quote(json.dumps(p, ensure_ascii=False)) + '::jsonb) ON CONFLICT(product_id) DO UPDATE SET document=EXCLUDED.document;')
    for v in variants:
        sql.append('INSERT INTO zara_research.variants VALUES (' + ', '.join(quote(x) for x in [v['variant_id'], v['product_id'], json.dumps(v, ensure_ascii=False)]) + '::jsonb) ON CONFLICT(variant_id) DO UPDATE SET document=EXCLUDED.document;')
    for i in images:
        sql.append('INSERT INTO zara_research.images VALUES (' + ', '.join(quote(x) for x in [i['product_id'], i['variant_id'], i['image_url'], json.dumps(i, ensure_ascii=False)]) + '::jsonb) ON CONFLICT DO NOTHING;')
    sql.append('COMMIT;')
    destination = ROOT / 'database/zara_research_sample.sql'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text('\n'.join(sql) + '\n', encoding='utf-8')
    print(f'Generated {destination}; no database connection was made.')


if __name__ == '__main__':
    build()
