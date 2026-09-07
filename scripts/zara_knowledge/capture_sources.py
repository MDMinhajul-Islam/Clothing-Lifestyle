"""Register a normal public-page research-tool extraction, without altering it.

Usage: python -m scripts.zara_knowledge.capture_sources SourceId extracted.txt
Discovery must precede capture. No browser identity/cookie or challenge bypass.
"""
import argparse
from pathlib import Path
from .common import CORPUS, RAW, digest, now, official_url, read, write

def capture(source, raw_text):
    if not official_url(source['source_url']):
        raise ValueError('Only official public US English URLs are accepted')
    h = digest(raw_text)
    path = RAW / source['source_id'] / (h + '-web-extract.json')
    if path.exists():
        return path
    write(path, dict(source_url=source['source_url'], retrieved_at=now(), market='US',
          locale='en', page_title=source['title'], raw_text=raw_text, source_hash=h,
          capture_method='web.run official-page text extraction', http_status=None,
          effective_date=source.get('effective_date')), immutable=True)
    return path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source_id'); p.add_argument('text_file', type=Path)
    args = p.parse_args()
    source = next(s for s in read(CORPUS / 'source_manifest.json')['sources'] if s['source_id'] == args.source_id)
    print(capture(source, args.text_file.read_text(encoding='utf-8')))

if __name__ == '__main__':
    main()
