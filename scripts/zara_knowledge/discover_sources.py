"""Build the manifest from reviewed official-source captures; never guesses URLs."""
from .common import CORPUS, RAW, ROOT, TOPICS, digest, read, write

def main():
    records = []
    for key, topic in TOPICS.items():
        captures = sorted((RAW / key).glob('*web-extract.json'), key=lambda p:read(p)['retrieved_at'])
        if not captures:
            continue
        capture = read(captures[-1])
        title = capture['raw_text'].split(' | Help |')[0]
        records.append(dict(source_id=key, policy_type=topic, title=title,
            source_url=capture['source_url'], market='US', locale='en',
            discovered_at=capture['retrieved_at'], retrieval_status='CAPTURED_TOOL_TEXT',
            http_status=None, effective_date=None,
            captures=[str(p.relative_to(ROOT)).replace('\\', '/') for p in captures],
            notes='Official-page research-tool extraction; upstream freshness unverified. Direct HTTP probe on HowToReturn returned 403; no bypass attempted.'))
    write(CORPUS / 'source_manifest.json', {'sources': records, 'coverage_gaps': [
        {'policy_type': 'legal', 'retrieval_status': 'NOT_CAPTURED', 'source_url': None,
         'notes': 'Conditions-of-use link discovered on HowToReturn; legal PDF not ingested or audited.'},
        {'policy_type': 'customer_service', 'retrieval_status': 'PARTIAL', 'source_url': None,
         'notes': 'Warranty assistance covered; dedicated contact channels, fitting rooms and store-service terms not captured.'},
        {'policy_type': 'care', 'retrieval_status': 'PARTIAL', 'source_url': None,
         'notes': 'Care overview captured; linked detailed garment-care guide not captured.'}]})
    print({'sources': len(records)})

if __name__ == '__main__':
    main()
