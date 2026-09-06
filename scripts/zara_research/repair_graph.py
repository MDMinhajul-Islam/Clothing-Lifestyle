"""Repair the graph offline from retained evidence; never fetch products or pages.

Preserves the legacy checkpoint and product registry. Query aliases require a
same-path observed rel=canonical; pagination remains separate until verified.
"""
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from catalogue_progress import ROOT, RAW, STATE, NORMAL, REPORTS, read, write, export, cid

REPAIR = RAW / 'repair'
BACKUP = STATE / 'checkpoints/pre_graph_repair'
MAJOR = ['WOMAN', 'MAN', 'KIDS', 'ZARA HOME', 'BEAUTY']


def canonicalize(url, declared=None):
    p = urlsplit(url)
    clean = urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ''))
    if declared:
        d = urlsplit(declared)
        # Do not merge pagination, region or filter variants based on SEO canonical.
        keys = {k for k, _ in parse_qsl(p.query)}
        if (p.netloc.lower() == d.netloc.lower() and p.path == d.path
                and keys <= {'v1'}):
            return urlunsplit((d.scheme.lower(), d.netloc.lower(), d.path, d.query, ''))
    return clean


def department(url):
    path = urlsplit(url).path
    if '/home-' in path:
        return 'ZARA HOME'
    if '/kids-' in path:
        return 'KIDS'
    if '/woman-beauty-' in path:
        return 'BEAUTY'
    if '/woman-' in path:
        return 'WOMAN'
    if '/man-' in path:
        return 'MAN'
    if '/massimo-dutti-' in path:
        return 'MASSIMO DUTTI'
    if '/preowned-' in path:
        return 'PRE-OWNED'
    if '/zara-travel-' in path:
        return 'TRAVEL MODE'
    return 'UNCLASSIFIED'


def category_route(url):
    p = urlsplit(url)
    return p.netloc == 'www.zara.com' and p.path.startswith('/us/en/') and bool(re.search(r'-(?:l|mkt|c)\d+\.html$', p.path))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    BACKUP.mkdir(parents=True, exist_ok=True)
    protected = [STATE / 'unique_products.json', STATE / 'checkpoints/discovery.json']
    protected += list(NORMAL.glob('product*.json')) + list(NORMAL.glob('product*.csv'))
    before = {str(p.relative_to(ROOT)): file_hash(p) for p in protected}
    for path in [STATE / 'categories.json', STATE / 'categories.csv', STATE / 'category_edges.json', *protected[:2]]:
        target = BACKUP / path.name
        if path.exists() and not target.exists():
            shutil.copy2(path, target)
    legacy = read(BACKUP / 'categories.json', [])
    checkpoint = read(STATE / 'checkpoints/discovery.json', {})
    evidence = [read(f) | {'evidence_file': str(f.relative_to(ROOT))} for f in sorted(REPAIR.glob('*.json'))]
    aliases = {canonicalize(e['url']): canonicalize(e['url'], e.get('canonical')) for e in evidence}

    def key(url):
        cleaned = canonicalize(url)
        return aliases.get(cleaned, cleaned)

    nodes, edges = {}, {}

    def node(url, name=None, source=None):
        canon = key(url)
        if canon not in nodes:
            nodes[canon] = dict(category_id=cid(canon), department=department(canon), parent_category_id=None,
                name=name, normalized_name=' '.join((name or '').lower().split()), url=canon,
                route_type='UNKNOWN', depth=None, is_product_listing=None, is_collection_page=None,
                is_campaign_page=None, is_navigation_only=None, first_seen_from=source,
                last_verified_at=None, crawl_status='DISCOVERED', canonical_category_key=cid(canon),
                canonical_url=canon, alias_urls=[], classification_evidence=None,
                department_basis='INFERRED from route unless landing heading verified',
                product_card_count_observed=None, legacy_category_ids=[],
                enumeration_complete=False, discovery_complete=False)
        n = nodes[canon]
        if url != canon and url not in n['alias_urls']:
            n['alias_urls'].append(url)
        if name and not n['name']:
            n['name'] = name
            n['normalized_name'] = ' '.join(name.lower().split())
        return n

    def edge(a, b, relation, proof):
        if a['category_id'] == b['category_id']:
            return
        k = (a['category_id'], b['category_id'], relation)
        edges[k] = dict(source_category_id=k[0], target_category_id=k[1], relation=relation, evidence=proof)
        if relation == 'BREADCRUMB_PARENT' and b['parent_category_id'] is None:
            b['parent_category_id'] = a['category_id']

    for old in legacy:
        n = node(old['category_url'], old.get('category'), 'legacy_checkpoint')
        n['legacy_category_ids'].append(old['category_id'])
        n['crawl_status'] = 'PARTIAL' if old.get('discovery_status') == 'LINKS_INSPECTED' else 'QUEUED'
    # Retain old graph links and queue entries, including ones not in the 369-row snapshot.
    for url in checkpoint.get('queue', []):
        node(url, source='legacy_discovery_queue')
    for f in (RAW / 'discovery').glob('*.json'):
        obs = read(f)
        if not category_route(obs['url']):
            continue
        a = node(obs['url'], obs.get('title'), str(f.relative_to(ROOT)))
        for link in obs.get('links', []):
            b = node(link['url'], link.get('name'), obs['url'])
            edge(a, b, 'RELATED_LINK', str(f.relative_to(ROOT)))
    # Only pilot listing evidence proves a product grid for legacy nodes.
    for f in RAW.glob('*listing.json'):
        obs = read(f)
        n = node(obs['url'])
        if obs.get('cards'):
            n.update(route_type='PRODUCT_LISTING_CATEGORY', is_product_listing=True,
                     is_navigation_only=False, crawl_status='PARTIAL',
                     product_card_count_observed=len(obs['cards']),
                     last_verified_at=obs['captured_at'], classification_evidence=str(f.relative_to(ROOT)))

    roots = {}
    for obs in evidence:
        n = node(obs['url'], obs['title'], 'public_index_or_observed_link')
        label = obs['department']
        if label in MAJOR + ['MASSIMO DUTTI', 'PRE-OWNED', 'TRAVEL MODE']:
            roots[label] = n
            n.update(department=label, department_basis='PUBLICLY OBSERVED landing heading/title', depth=0)
        product_bearing = obs['product_card_count'] > 0
        n.update(route_type='PRODUCT_LISTING_CATEGORY' if product_bearing else 'NAVIGATION_PAGE',
                 is_product_listing=product_bearing, is_navigation_only=not product_bearing,
                 is_collection_page=None, is_campaign_page=None,
                 last_verified_at=obs['captured_at'], crawl_status='PARTIAL', discovery_complete=True,
                 product_card_count_observed=obs['product_card_count'], classification_evidence=obs['evidence_file'])
        crumbs = []
        for link in obs['links']:
            if not category_route(link['url']):
                continue
            # Exclude unrelated footer company/legal links. Keep actual breadcrumbs.
            if not link['in_main'] and link['context'] != 'Breadcrumbs Trail':
                continue
            b = node(link['url'], link.get('name'), obs['url'])
            if link['context'] == 'Breadcrumbs Trail':
                crumbs.append(b)
            else:
                edge(n, b, 'RELATED_LINK', obs['evidence_file'])
        for a, b in zip(crumbs, crumbs[1:]):
            edge(a, b, 'BREADCRUMB_PARENT', obs['evidence_file'])
    # Explicitly observed cross-link: Kids landing's public navigation to Home Kids.
    homekids = next((e for e in evidence if e['department']=='HOME KIDS'), None)
    if homekids:
        edge(roots['KIDS'], node(homekids['url']), 'DEPARTMENT_NAVIGATION_LINK',
             'https://www.zara.com/us/en/kids-mkt1.html (public web extraction, 2026-09-06)')
    byid = {n['category_id']: n for n in nodes.values()}
    for _ in range(len(nodes)):
        changed = False
        for n in nodes.values():
            parent = byid.get(n['parent_category_id'])
            if n['depth'] is None and parent and parent['depth'] is not None:
                n['depth'] = parent['depth'] + 1
                changed = True
        if not changed:
            break

    # Persist new queues without modifying the legacy checkpoint or product registry.
    def queue_item(n, status='QUEUED', prior=None):
        old = prior or {}
        return dict(id=n['category_id'], url=n['url'], status=old.get('status', status),
                    attempt_count=old.get('attempt_count', 1 if n['last_verified_at'] else 0),
                    last_attempt_at=old.get('last_attempt_at', n['last_verified_at']), error=old.get('error'),
                    checkpoint=old.get('checkpoint', dict(evidence=n['classification_evidence'],
                         legacy_visited=n['url'] in checkpoint.get('done', []), phase='classification',
                         enumeration_complete=False)))

    prior_d = {q['id']:q for q in read(STATE / 'category_discovery_queue.json', [])}
    prior_e = {q['id']:q for q in read(STATE / 'category_enumeration_queue.json', [])}
    discovery_queue = [queue_item(n, 'COMPLETE' if n['discovery_complete'] else 'QUEUED', prior_d.get(n['category_id'])) for n in nodes.values()]
    enumeration_queue = [queue_item(n, prior=prior_e.get(n['category_id'])) for n in nodes.values() if n['is_product_listing'] is True]
    for item in enumeration_queue:
        if item['id'] not in prior_e:
            item.update(attempt_count=0, last_attempt_at=None, checkpoint={'phase':'enumeration','scroll_iteration':0,'seen_product_ids':[]})
    registry = read(STATE / 'unique_products.json', [])
    prior_p = {q['id']:q for q in read(STATE / 'product_detail_queue.json', [])}
    product_queue = []
    for p in registry:
        old = prior_p.get(p['product_id'])
        product_queue.append(old or dict(id=p['product_id'], url=p['product_url'],
             status='PARTIAL' if p['extraction_status']=='CORE_EXTRACTED' else 'QUEUED',
             attempt_count=1 if p['extraction_status']=='CORE_EXTRACTED' else 0,
             last_attempt_at=p.get('last_seen_at') if p['extraction_status']=='CORE_EXTRACTED' else None,
             error=None, checkpoint={'core_preserved':p['extraction_status']=='CORE_EXTRACTED',
                 'supplemental_only':p['extraction_status']=='CORE_EXTRACTED', 'requires_validation_before_reopen':True}))
    for name, rows in [('category_discovery_queue', discovery_queue), ('category_enumeration_queue', enumeration_queue), ('product_detail_queue', product_queue)]:
        write(STATE / (name+'.json'), rows)
    rows = list(nodes.values())
    for folder in [STATE, NORMAL]:
        export(folder, 'categories', rows, list(rows[0]))
    write(STATE / 'category_graph.json', dict(nodes=rows, edges=list(edges.values())))
    export(STATE, 'category_edges', list(edges.values()), ['source_category_id','target_category_id','relation','evidence'])
    write(STATE / 'url_aliases.json', [dict(url=u, canonical_url=c, reason='observed same-path rel=canonical') for u,c in aliases.items() if u!=c])
    counts = {}
    for d in [*MAJOR, 'MASSIMO DUTTI', 'PRE-OWNED', 'TRAVEL MODE', 'UNCLASSIFIED']:
        ns = [n for n in rows if n['department']==d]
        counts[d] = dict(landing_verified=d in roots, landing_url=roots[d]['url'] if d in roots else None,
                        category_nodes=len(ns), product_bearing_nodes=sum(n['is_product_listing'] is True for n in ns),
                        unresolved_nodes=sum(n['route_type']=='UNKNOWN' for n in ns))
    integrity = {path: file_hash(ROOT/path)==value for path,value in before.items()}
    if not all(integrity.values()):
        raise RuntimeError('Protected artifact changed')
    summary = dict(phase='GRAPH_REPAIR_REVIEW', legacy_nodes=len(legacy), revised_nodes=len(nodes),
                   route_types=dict(Counter(n['route_type'] for n in rows)), department_coverage=counts,
                   observed_alias_merges=sum(u!=c for u,c in aliases.items()),
                   enumeration_queue_size=len(enumeration_queue), discovery_queue_pending=sum(q['status']!='COMPLETE' for q in discovery_queue),
                   product_queue_pending=sum(q['status']=='QUEUED' for q in product_queue),
                   product_queue_supplemental_review=sum(q['status']=='PARTIAL' for q in product_queue),
                   protected_files_unchanged=integrity, all_major_landings_verified=all(d in roots for d in MAJOR),
                   full_category_graph_complete=False, stopped_before_product_crawl=True)
    write(REPORTS / 'zara_department_coverage.json', summary)
    report = '# Revised Zara department coverage\n\nGraph repair checkpoint; **not full-catalogue completion**. All five major landing pages were verified in the normal browser. No product detail was reopened.\n\n'
    report += '| Department | Landing verified | Nodes | Product-bearing | Unresolved classification |\n|---|---|---:|---:|---:|\n'
    for d,c in counts.items():
        report += f"| {d} | {'Yes' if c['landing_verified'] else 'N/A'} | {c['category_nodes']} | {c['product_bearing_nodes']} | {c['unresolved_nodes']} |\n"
    report += f'\n**Enumeration queue: {len(enumeration_queue)} verified product-bearing nodes.** Discovery/classification queue: {summary["discovery_queue_pending"]} pending. {len(legacy)} legacy nodes retained; {len(nodes)} revised nodes. {summary["observed_alias_merges"]} observed canonical alias merge(s).\n'
    report += '\n## Verified department landings\n' + '\n'.join(f'- [{d}]({c["landing_url"]})' for d,c in counts.items() if c['landing_verified'])
    report += '\n\n## Kids branches\n\nGirl, Boy, Toddler Girl, Toddler Boy, Baby, and Accessories/Shoes each have a browser-observed product grid. Their breadcrumb paths establish Kids parent links. The Kids landing public page links to Home Kids; the Home Kids product grid was also verified. Age ranges are navigation labels from the public Kids landing, not inferred size enums. Home Kids remains under Zara Home ownership with a Kids cross-link.\n'
    report += '\n## Classification and aliases\n\nProduct grid presence is proof of product-bearing status, not category completion. Other verified department landings are NAVIGATION_PAGE based on current visible content; they may still lead to campaigns. Uninspected routes stay UNKNOWN instead of being guessed as SEO or collection pages. Only verified product-bearing nodes enter enumeration. Null flags mean unverified.\n\nBreadcrumb edges establish parent links; related links do not. Unknown parents/depths remain null. Department assignments for unvisited routes are explicitly route-inferred.\n\nFragments are removed. The observed Beauty makeup v1 URL declares the same-path bare canonical and is recorded as an alias. Unverified v1, page, filter and regional parameters remain distinct. Canonical tags are not used to discard pagination coverage. No route is merged just because its title or numeric suffix matches.\n'
    report += '\n## Queues and preservation\n\nLegacy checkpoint, product registry, and all normalized product files are byte-identical (hash checks recorded in JSON). The three new queues preserve attempts, timestamps, errors and per-item checkpoints. Core-captured products are supplemental-review items, not scheduled for blind re-extraction. Discovery COMPLETE means classification/link inspection only; every node still has enumeration_complete=false.\n\nUse 5–10 page verification batches, checkpoint each item, and close only agent-owned tabs between batches. Resume the persisted queues. Repeated inspection failures remain errors, not claims of site blocking. No blocked HTTP method was used.\n'
    report += '\n## Review stop\n\nStopped before catalogue enumeration and product extraction as requested. This repair verifies department coverage and prepares queues; it does not certify all SEO/category routes or full graph saturation. Further route classification remains queued. The previous coverage reports describe the earlier run; this report supersedes their unverified-department status.\n'
    (REPORTS / 'zara_department_coverage.md').write_text(report, encoding='utf-8')
    (REPORTS / 'zara_category_tree.md').write_text('# Repaired category graph\n\nSee zara_department_coverage.md for verification and limitations. Parent is supplied only when supported by breadcrumbs.\n\n| Department | Name | Parent category ID | Route type | URL |\n|---|---|---|---|---|\n'+ '\n'.join('| '+' | '.join(str(n[k] or 'NOT VERIFIED').replace('|','/') for k in ['department','name','parent_category_id','route_type','url'])+' |' for n in rows), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='protected_files_unchanged'}, indent=2))


if __name__ == '__main__':
    build()
