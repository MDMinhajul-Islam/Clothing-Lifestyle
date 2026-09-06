"""Rebuild persistent registry, category graph, coverage and validation from evidence.

Offline only. Discovery is not enumeration; a visited page is never marked complete.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/zara'
STATE = ROOT / 'data/zara'
NORMAL = ROOT / 'data/normalized/zara'
REPORTS = ROOT / 'reports'


def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def export(directory, name, rows, fields):
    write(directory / (name + '.json'), rows)
    with (directory / (name + '.csv')).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                          for k, v in row.items() if k in fields} for row in rows)


def dept(url):
    # Inference only: URL route labels, never a claim about unseen navigation.
    if '/woman-' in url:
        return 'WOMAN'
    if '/man-' in url:
        return 'MAN'
    return 'UNCLASSIFIED'


def cid(url):
    return 'category:' + hashlib.sha256(url.encode()).hexdigest()[:16]


def build():
    if (STATE / 'category_graph.json').exists():
        raise SystemExit('The graph has been repaired. Use repair_graph.py; this legacy report builder would overwrite repaired categories.')
    now = datetime.now(timezone.utc).isoformat()
    STATE.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    categories, edges, registry, errors = {}, {}, {}, read(STATE / 'browser_errors.json', [])
    previous = {r['product_id']: r for r in read(STATE / 'unique_products.json', [])}

    def category(url, name=None):
        if url not in categories:
            match = re.search(r'-l(\d+)\.html', url)
            categories[url] = dict(category_id=cid(url), category_url=url, category=name,
                                   source_category_identifier=match[1] if match else None,
                                   identifier_semantics='URL token; internal semantics NOT VERIFIED',
                                   department=dept(url), department_classification='INFERRED from route',
                                   parent_category=None, parent_status='NOT VERIFIED',
                                   discovery_status='DISCOVERED', enumeration_status='PENDING',
                                   first_scan_product_count=None, final_scan_product_count=None,
                                   number_of_scroll_iterations=0, duplicate_count=None,
                                   new_products_last_iteration=None, completion_reason=None,
                                   unique_products_discovered=0)
        if name and not categories[url]['category']:
            categories[url]['category'] = name
        return categories[url]

    for file in sorted((RAW / 'discovery').glob('*.json')):
        raw = read(file)
        if 'homepage-menu' in file.name:
            errors.append(dict(scope='GLOBAL_NAVIGATION', url=raw['url'], error=raw['error'], timestamp=raw['captured_at']))
            continue
        parent = category(raw['url'], raw.get('title'))
        parent['discovery_status'] = raw.get('error') or 'LINKS_INSPECTED'
        if raw.get('error'):
            errors.append(dict(scope='CATEGORY_DISCOVERY', url=raw['url'], error=raw['error'], timestamp=raw['captured_at']))
        for link in raw.get('links', []):
            child = category(link['url'], re.sub(r'^\d+', '', link.get('name', '')))
            if child['category_id'] != parent['category_id']:
                key = (parent['category_id'], child['category_id'], link['relation'])
                edges[key] = dict(source_category_id=key[0], target_category_id=key[1],
                                  relation=key[2], parent_child_verified=False)

    for file in sorted(RAW.glob('*listing.json')):
        raw = read(file)
        cat = category(raw['url'])
        for card in raw.get('cards', []):
            url = card.get('url')
            match = re.search(r'-p(\d+)\.html', url or '')
            if not match:
                continue
            pid = 'zara-us:' + match[1]
            if pid not in registry:
                old = previous.get(pid, {})
                registry[pid] = dict(product_id=pid, source_product_id=match[1], product_group_id=None,
                                     identity_basis='URL reference pending JSON-LD reconciliation', product_url=url,
                                     first_seen_category=old.get('first_seen_category', raw['url']), categories_seen_in=[],
                                     first_seen_at=old.get('first_seen_at', raw['captured_at']), last_seen_at=raw['captured_at'],
                                     extraction_status='PENDING', missing_detail_fields=[], public_card_ids=[])
            rec = registry[pid]
            if raw['url'] not in rec['categories_seen_in']:
                rec['categories_seen_in'].append(raw['url'])
            if card.get('source_product_id') and card['source_product_id'] not in rec['public_card_ids']:
                rec['public_card_ids'].append(card['source_product_id'])

    products = read(NORMAL / 'products.json', [])
    variants = read(NORMAL / 'product_variants.json', [])
    images = read(NORMAL / 'product_images.json', [])
    relationships, materials = [], []
    for p in products:
        pid = p['product_id']
        rec = registry.setdefault(pid, dict(product_id=pid, source_product_id=p['source_product_id'],
                 product_url=p['product_url'], categories_seen_in=p.get('category_urls', []),
                 first_seen_category=next(iter(p.get('category_urls', [])), None),
                 first_seen_at=p['source_last_seen_at'], public_card_ids=[]))
        rec.update(product_group_id=p['source_product_id'], identity_basis='JSON-LD productGroupID',
                   last_seen_at=p['source_last_seen_at'], extraction_status='CORE_EXTRACTED',
                   missing_detail_fields=['care'] if not p.get('care') else [])
        # Core metadata is reusable; do not pretend all color galleries/care were inspected.
        rec['full_detail_extraction_status'] = 'PARTIAL: full public fields and color galleries not audited'
        for url in rec['categories_seen_in']:
            cat = category(url)
            relationships.append(dict(product_id=pid, category_id=cat['category_id'], category_url=url))
        for position, m in enumerate(p.get('composition') or []):
            materials.append(dict(product_id=pid, position=position, property_id=m.get('propertyID'),
                                  section=m.get('name'), material_text=m.get('value'), source='JSON-LD additionalProperty'))

    scans = read(STATE / 'category_scans.json', [])
    for scan in scans:
        category(scan['category_url']).update(scan)
    for cat in categories.values():
        cat['unique_products_discovered'] = sum(cat['category_url'] in r['categories_seen_in'] for r in registry.values())
    fields = list(next(iter(categories.values()))) if categories else ['category_id', 'category_url']
    for directory in [STATE, NORMAL]:
        export(directory, 'categories', list(categories.values()), fields)
    export(STATE, 'category_edges', list(edges.values()), ['source_category_id', 'target_category_id', 'relation', 'parent_child_verified'])
    export(NORMAL, 'product_categories', relationships, ['product_id', 'category_id', 'category_url'])
    export(NORMAL, 'product_materials', materials, ['product_id', 'position', 'property_id', 'section', 'material_text', 'source'])
    write(STATE / 'unique_products.json', list(registry.values()))
    write(STATE / 'errors.json', errors)
    write(STATE / 'checkpoints/latest.json', dict(updated_at=now, phase='CATEGORY_DISCOVERY',
          registry_file='data/zara/unique_products.json', discovered_products=len(registry),
          core_extracted_products=len(products), categories_discovered=len(categories),
          category_tree_complete=False, category_tree_blocker='Global navigation opens blank',
          no_product_count_limit=True, discovery_checkpoint='data/zara/checkpoints/discovery.json',
          run_status=read(STATE / 'checkpoints/discovery.json', {}).get('run_status', 'IN_PROGRESS')))

    departments = {}
    for d in sorted({c['department'] for c in categories.values()}):
        cs = [c for c in categories.values() if c['department'] == d]
        ps = {r['product_id'] for r in registry.values() if any(dept(u) == d for u in r['categories_seen_in'])}
        departments[d] = dict(categories_discovered=len(cs), categories_completed=sum(c['enumeration_status']=='COMPLETE' for c in cs),
                              unique_products_discovered=len(ps), products_core_extracted=sum(p['product_id'] in ps for p in products),
                              variants=sum(v['product_id'] in ps for v in variants), unique_image_urls=len({i['image_url'] for i in images if i['product_id'] in ps}))
    coverage = dict(updated_at=now, status='INCOMPLETE', tree_complete=False, departments=departments,
                    unverified_departments=['KIDS and its branches', 'ZARA HOME', 'BEAUTY', 'other global navigation branches'],
                    total_unique_products_discovered=len(registry), total_products_core_extracted=len(products),
                    total_variants=len(variants), total_product_category_relationships=len(relationships),
                    total_unique_image_urls=len({i['image_url'] for i in images}),
                    products_without_full_detail_extraction=len(registry), products_pending_core_extraction=sum(r['extraction_status']=='PENDING' for r in registry.values()),
                    products_blocked_by_technical_restriction=0, discovery_errors=errors)
    write(REPORTS / 'zara_catalogue_coverage.json', coverage)
    (REPORTS / 'zara_catalogue_coverage.md').write_text('# Zara catalogue coverage\n\n**INCOMPLETE.** Global category menu opens blank. Unseen departments are unknown, not empty.\n\n' +
        '| Department (route-inferred) | Categories discovered | Enumerated | Products discovered | Core extracted | Variants | Unique images |\n|---|---:|---:|---:|---:|---:|---:|\n' +
        '\n'.join('| '+d+' | '+' | '.join(str(x) for x in v.values())+' |' for d,v in departments.items()) +
        '\n\nNo category has been certified from its first viewport. Existing pilot records are preserved, with supplemental detail coverage still partial. JSON-LD stock is an observation, not authoritative inventory.\n\nCounts differ from visible cards because categories repeat products and colors can share a group. Only US pages are included. Lazy loading, regional availability, campaigns and changing listings can affect totals; their quantitative impact is not established.\n', encoding='utf-8')
    (REPORTS / 'zara_category_tree.md').write_text('# Discovered category graph — incomplete tree\n\nThe global menu is blank. Parent hierarchy is NOT VERIFIED. Related links must not be relabeled as parent-child links. Product counts are observed so far, not category totals.\n\n| Department | Parent | Category | URL | Unique products discovered |\n|---|---|---|---|---:|\n'+
        '\n'.join('| '+c['department']+' | NOT VERIFIED | '+str(c['category'] or 'Unlabeled').replace('|','/')+' | '+c['category_url']+' | '+str(c['unique_products_discovered'])+' |' for c in categories.values()), encoding='utf-8')
    pids = {p['product_id'] for p in products}
    vc, ic = Counter(v['product_id'] for v in variants), Counter(i['product_id'] for i in images)
    validation = dict(status='INCOMPLETE_CATALOGUE', duplicate_product_ids=[k for k,v in Counter(p['product_id'] for p in products).items() if v>1],
                      duplicate_urls=[k for k,v in Counter(p['product_url'] for p in products).items() if v>1],
                      orphan_variants=[v['variant_id'] for v in variants if v['product_id'] not in pids],
                      orphan_images=[i['image_url'] for i in images if i['product_id'] not in pids],
                      products_with_zero_variants=[p for p in pids if not vc[p]], products_with_zero_images=[p for p in pids if not ic[p]],
                      missing_prices=[p['product_id'] for p in products if p['base_price'] is None],
                      malformed_currency=[p['product_id'] for p in products if not re.fullmatch('[A-Z]{3}', p.get('currency') or '')],
                      missing_categories=[p['product_id'] for p in products if not p['category_urls']],
                      products_partially_extracted=list(registry),
                      categories_not_completed=[c['category_id'] for c in categories.values() if c['enumeration_status']!='COMPLETE'],
                      image_http_validation='NOT RUN', full_tree_validation='FAILED: global navigation unavailable')
    write(REPORTS / 'zara_full_catalogue_validation.json', validation)
    (REPORTS / 'zara_full_catalogue_validation.md').write_text('# Full catalogue validation\n\n**INCOMPLETE; not a full-catalogue pass.**\n\n'+
        '\n'.join('- '+k+': '+str(len(v) if isinstance(v,list) else v) for k,v in validation.items()), encoding='utf-8')
    print(json.dumps({k: v for k,v in coverage.items() if k not in ['discovery_errors']}, indent=2))


if __name__ == '__main__':
    build()
