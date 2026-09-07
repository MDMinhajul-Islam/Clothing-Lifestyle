"""Explicitly configured JSON embedding endpoint; no default provider or model.

Protocol: POST {model, input: [text]} -> {data: [{index, embedding: [float]}]}.
Provider credentials are only sent to the configured HTTPS endpoint; redirects denied.
"""
import json
import math
import os
from dataclasses import dataclass, field
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

class EmbeddingUnavailable(RuntimeError):
    pass

def validate_vector(vector, dimension):
    if (not isinstance(vector, list) or len(vector) != dimension
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector)
            or not any(v != 0 for v in vector)):
        raise ValueError('Invalid embedding: expected finite nonzero vector of configured dimension')
    return vector

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

@dataclass
class EmbeddingClient:
    provider: str
    model: str
    dimension: int
    version: str
    endpoint: str = field(repr=False)
    key: str = field(repr=False)

    @classmethod
    def from_environment(cls):
        names = ['PROVIDER', 'MODEL', 'DIMENSION', 'VERSION', 'URL', 'API_KEY']
        values = [os.getenv('RAG_EMBEDDING_' + n) for n in names]
        if not all(values):
            raise EmbeddingUnavailable('Embedding configuration is incomplete')
        provider, model, dim, version, endpoint, key = values
        p = urlparse(endpoint)
        if p.scheme != 'https' or not p.hostname or p.username or p.password or p.query or p.fragment:
            raise EmbeddingUnavailable('Embedding endpoint must be a credential-free HTTPS URL')
        try:
            dimension = int(dim)
        except ValueError:
            raise EmbeddingUnavailable('Embedding dimension must be an integer') from None
        if not 1 <= dimension <= 16000:
            raise EmbeddingUnavailable('Embedding dimension is outside supported bounds')
        return cls(provider, model, dimension, version, endpoint, key)

    def embed(self, texts):
        if not texts:
            return []
        req = Request(self.endpoint, data=json.dumps({'model':self.model, 'input':texts}).encode(),
            headers={'Content-Type':'application/json', 'Authorization':'Bearer ' + self.key}, method='POST')
        try:
            with build_opener(NoRedirect).open(req, timeout=30) as response:
                data = json.load(response)['data']
            data = sorted(data, key=lambda d:d['index'])
            if [d['index'] for d in data] != list(range(len(texts))):
                raise ValueError('Embedding response indexes mismatch')
            return [validate_vector(d['embedding'], self.dimension) for d in data]
        except Exception:
            # Never propagate provider bodies, request headers or credentials.
            raise EmbeddingUnavailable('Embedding provider request failed') from None
