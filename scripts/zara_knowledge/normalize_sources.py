"""Normalize complete article extracts; preserve original source and exact clauses."""
import json
from .common import CORPUS, ROOT, VERSION, clean_extraction, digest, official_url, read, write

def main():
    documents = []
    for source in read(CORPUS / 'source_manifest.json')['sources']:
        path = ROOT / source['captures'][-1]
        raw = read(path)
        if not official_url(raw['source_url']):
            raise ValueError('Non-US source')
        text = clean_extraction(raw['raw_text'])
        h = digest(raw['raw_text'])
        # Sidecar supplements the initial immutable capture without rewriting it.
        write(path.with_suffix('.metadata.json'), dict(source_hash=h,
              page_title=text.splitlines()[0][2:], source_id=source['source_id'],
              raw_artifact_hash=digest(path.read_text(encoding='utf-8'))), immutable=True)
        write(path.with_suffix('.access-metadata.json'), dict(
            direct_http_status=403 if source['source_id'] == 'HowToReturn' else None,
            direct_probe_url='https://www.zara.com/us/en/help-center/HowToReturn',
            note='Only HowToReturn was directly probed. The initial envelope field on other sources is not a per-page observation.',
            capture_status='TOOL_EXTRACT_CAPTURED', upstream_freshness='UNKNOWN'), immutable=True)
        kid = source['source_id'] + '-' + digest(h + VERSION)[:20]
        doc = dict(knowledge_id=kid, source_id=source['source_id'], source='zara_official_us',
            source_url=raw['source_url'], market='US', locale='en', policy_type=source['policy_type'],
            document_title=text.splitlines()[0][2:], section_title=text.splitlines()[0][2:],
            effective_date=raw.get('effective_date'), retrieved_at=raw['retrieved_at'], source_hash=h,
            raw_text=raw['raw_text'], clean_text=text, normalization_version=VERSION,
            raw_path=source['captures'][-1], capture_method=raw['capture_method'])
        doc_path = CORPUS / 'documents' / (kid + '.json')
        if doc_path.exists():
            previous = read(doc_path)
            if previous['source_hash'] != h or previous['clean_text'] != text:
                raise ValueError('Immutable document identity conflict')
            doc = previous  # identical evidence keeps its original provenance timestamp
        write(doc_path, doc, immutable=True)
        md = CORPUS / 'documents' / (kid + '.md')
        metadata = {k:v for k,v in doc.items() if k not in ('raw_text', 'clean_text')}
        body = '---\n' + '\n'.join(k + ': ' + json.dumps(v, ensure_ascii=False) for k,v in metadata.items()) + '\n---\n\n' + text + '\n'
        if md.exists() and md.read_text(encoding='utf-8') != body:
            raise ValueError('Immutable normalized version conflict')
        if not md.exists():
            md.write_text(body, encoding='utf-8', newline='\n')
        documents.append(doc)
    write(CORPUS / 'documents.json', documents)
    print({'documents': len(documents)})

if __name__ == '__main__':
    main()
