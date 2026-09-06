"""Normalize browser-captured public JSON-LD; never fetch or infer variants.

Run: python scripts/zara_research/normalize.py
"""
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/zara'
OUT = ROOT / 'data/normalized/zara'


def objects(value):
    if isinstance(value, list):
        for child in value:
            yield from objects(child)
    elif isinstance(value, dict):
        yield value
        yield from objects(value.get('@graph', []))


def money(value):
    if value is None:
        return None
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError(f'Invalid price: {value}')
    return str(amount.quantize(Decimal('.01')))


def urls(value):
    if isinstance(value, str):
        return [value]
    return value if isinstance(value, list) else []


def normalize():
    products, variants, images, errors = [], [], [], []
    memberships = {}
    categories = {}
    for file in RAW.glob('*listing.json'):
        listing = json.loads(file.read_text(encoding='utf-8'))
        for link in listing.get('category_links', []):
            categories[link['url']] = dict(source_url=link['url'], name=link.get('name', '').strip(),
                                           classification='PUBLICLY OBSERVED', source_last_seen_at=listing['captured_at'])
        for card in listing.get('cards', []):
            memberships.setdefault(card.get('url'), set()).add(listing['url'])
    for file in sorted(RAW.glob('*.json')):
        if file.name.endswith('listing.json'):
            continue
        raw = json.loads(file.read_text(encoding='utf-8'))
        groups = []
        for script in raw.get('jsonld', []):
            groups.extend(g for g in objects(json.loads(script)) if g.get('@type') == 'ProductGroup')
        for group in groups:
            source_id = group.get('productGroupID')
            if not source_id:
                errors.append({'file': file.name, 'error': 'missing productGroupID'})
                continue
            pid = 'zara-us:' + str(source_id)
            pv = []
            for v in group.get('hasVariant', []):
                offer = v.get('offers', {})
                if isinstance(offer, list):
                    errors.append({'product': pid, 'error': 'multiple offers require explicit selection'})
                    continue
                sku = v.get('sku')
                if not sku:
                    errors.append({'product': pid, 'error': 'variant without explicit sku'})
                    continue
                vid = pid + ':' + str(sku)
                try:
                    price = money(offer.get('price'))
                except (ValueError, InvalidOperation) as exc:
                    errors.append({'variant': vid, 'error': str(exc)})
                    price = None
                row = dict(variant_id=vid, product_id=pid, source_variant_id=sku,
                           sku_or_reference=sku, color_name=v.get('color'), size_name=v.get('size'),
                           price=price, currency=offer.get('priceCurrency'), compare_at_price=None,
                           availability_status=offer.get('availability'), variant_url=offer.get('url'),
                           source_last_seen_at=raw['captured_at'], evidence_file=str(file.relative_to(ROOT)),
                           evidence_method='JSON-LD ProductGroup.hasVariant')
                variants.append(row)
                pv.append(row)
                for position, url in enumerate(urls(v.get('image'))):
                    images.append(dict(product_id=pid, variant_id=vid, image_url=url,
                                       position=position, image_type='variant', alt_text=None,
                                       source_last_seen_at=raw['captured_at'], http_validation='not_tested'))
            currencies = {v['currency'] for v in pv if v['currency']}
            prices = [Decimal(v['price']) for v in pv if v['price'] is not None]
            products.append(dict(product_id=pid, source='zara_us_public', source_product_id=source_id,
                                 name=group.get('name'), description=group.get('description'),
                                 composition=group.get('additionalProperty'), materials=group.get('material'),
                                 care=raw.get('care_panel'), product_url=group.get('url') or raw['url'],
                                 category_urls=sorted(memberships.get(group.get('url') or raw['url'], [])),
                                 department=('Woman' if any('/woman-' in u for u in memberships.get(group.get('url') or raw['url'], [])) else
                                             'Man' if any('/man-' in u for u in memberships.get(group.get('url') or raw['url'], [])) else None),
                                 base_price=str(min(prices)) if prices and len(currencies) == 1 else None,
                                 currency=next(iter(currencies)) if len(currencies) == 1 else None,
                                 colors=sorted({v['color_name'] for v in pv if v['color_name']}),
                                 sizes=sorted({v['size_name'] for v in pv if v['size_name']}),
                                 source_last_seen_at=raw['captured_at'], status='observed',
                                 evidence_file=str(file.relative_to(ROOT)), classification='PUBLICLY OBSERVED',
                                 completeness='captured JSON-LD only; not guaranteed exhaustive'))
            for position, url in enumerate(urls(group.get('image'))):
                images.append(dict(product_id=pid, variant_id=None, image_url=url, position=position,
                                   image_type='selected_color_gallery', alt_text=None,
                                   source_last_seen_at=raw['captured_at'], http_validation='not_tested'))
    # Deduplicate only exact associations. Shared variant images remain correctly associated.
    images = list({(r['product_id'], r['variant_id'], r['image_url']): r for r in images}.values())
    pids = {p['product_id'] for p in products}
    vids = {v['variant_id']: v['product_id'] for v in variants}
    if len(pids) != len(products):
        errors.append({'error': 'duplicate products'})
    if len(vids) != len(variants):
        errors.append({'error': 'duplicate variants'})
    for v in variants:
        if v['product_id'] not in pids:
            errors.append({'error': 'orphan variant', 'id': v['variant_id']})
        if v['currency'] and (len(v['currency']) != 3 or not v['currency'].isupper()):
            errors.append({'error': 'malformed currency', 'id': v['variant_id']})
    for i in images:
        if i['variant_id'] and vids.get(i['variant_id']) != i['product_id']:
            errors.append({'error': 'wrong product image association'})
        if urlsplit(i['image_url']).scheme != 'https' or 'transparent-background' in i['image_url']:
            errors.append({'error': 'invalid or placeholder image URL'})
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in [('products', products), ('product_variants', variants), ('product_images', images), ('categories', list(categories.values()))]:
        if name == 'categories' and (ROOT / 'data/zara/category_graph.json').exists():
            continue  # Repaired graph owns category exports; preserve its stable IDs.
        (OUT / (name + '.json')).write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
        with (OUT / (name + '.csv')).open('w', encoding='utf-8-sig', newline='') as handle:
            if rows:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                                  for k, v in row.items()} for row in rows)
    report = dict(products=len(products), variants=len(variants), image_associations=len(images),
                  unique_image_urls=len({i['image_url'] for i in images}), errors=errors,
                  products_without_images=[p['product_id'] for p in products if not any(i['product_id']==p['product_id'] for i in images)],
                  products_without_category=[p['product_id'] for p in products if not p['category_urls']],
                  network_validation='NOT RUN; stored URLs only',
                  catalogue_completeness='PARTIAL SAMPLE; no whole-site claim')
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    (reports / 'zara_research_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (reports / 'zara_research_validation.md').write_text('# Zara sample validation\n\n' +
        '\n'.join(f'- {k}: {v}' for k, v in report.items()) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    result = normalize()
    raise SystemExit(1 if result['errors'] else 0)
