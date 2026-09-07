"""Shared deterministic evidence and artifact helpers."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/zara/help'
CORPUS = ROOT / 'data/knowledge/zara_us'
VERSION = '1.0.0'
TOPICS = {'HowToReturn': 'returns', 'Refund': 'refunds', 'HowToExchange': 'exchanges',
          'PaymentMethods': 'payment', 'DeliveryMethods': 'shipping',
          'ReturnSpecialConditions': 'returns', 'CareAndComposition': 'care',
          'MySize': 'sizing', 'EditOrder': 'cancellation', 'OrderStatus': 'orders',
          'FaultyItems': 'customer_service'}

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def official_url(url):
    p = urlparse(url)
    return (p.scheme == 'https' and p.hostname in {'www.zara.com', 'zara.com'}
            and p.port in (None, 443) and not p.username and not p.password
            and p.path.startswith('/us/en/') and not p.query and not p.fragment)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value, immutable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if path.exists() and path.read_text(encoding='utf-8') == body:
        return
    if immutable:
        with path.open('x', encoding='utf-8', newline='\n') as f:
            f.write(body)
    else:
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_text(body, encoding='utf-8', newline='\n')
        temporary.replace(path)

def clean_extraction(raw):
    # The stored tool response is immutable. Remove only tool markup and site chrome.
    text = re.sub(r'L\d+:\s?', '', raw)
    text = re.sub(r'cite[^†]*†([^†]+)(?:†[^]*)?', r'\1', text)
    match = re.search(r'(?m)^# ([^\n]+)', text)
    if not match:
        raise ValueError('Missing article heading; capture is not policy evidence')
    text = text[match.start():]
    end = re.search(r'Can[’\x27]t find what you[’\x27]re looking for\?', text)
    if not end:
        raise ValueError('Missing article end; capture may be truncated')
    text = text[:end.start()]
    text = re.sub(r'## In this article\s*.*?(?=### )', '', text, flags=re.S)
    text = '\n'.join(re.sub(r'[ \t\u00a0]+', ' ', line).strip() for line in text.splitlines())
    return re.sub(r'\n{3,}', '\n\n', text).strip()
