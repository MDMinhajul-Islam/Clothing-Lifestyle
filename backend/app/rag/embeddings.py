"""Explicitly configured JSON embedding endpoint; no default provider or model.

Protocol: POST {model, input: [text]} -> {data: [{index, embedding: [float]}]}.
Provider credentials are only sent to the configured HTTPS endpoint; redirects denied.
"""
import json
import math
import os
import time
from threading import Lock
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from backend.app.retell.timing import timed

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
        started = time.perf_counter()
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
        finally:
            timed("external_http_request", started, service="embedding_provider")


@dataclass
class LocalSentenceTransformerClient:
    provider: str = 'local_sentence_transformers'
    model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    dimension: int = 384
    version: str = 'v1'
    device: str = field(init=False)
    _encoder: object = field(init=False, repr=False)
    _encode_lock: object = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self):
        started = time.perf_counter()
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self._encoder = SentenceTransformer(self.model, device=self.device, local_files_only=True)
            if self._encoder.get_embedding_dimension() != self.dimension:
                raise EmbeddingUnavailable('Local model dimension does not match configuration')
        except EmbeddingUnavailable:
            raise
        except Exception:
            raise EmbeddingUnavailable('Local SentenceTransformer model could not be loaded') from None
        finally:
            timed("local_embedding_model_load", started, model="all-MiniLM-L6-v2")

    def embed(self, texts):
        if not texts:
            return []
        started = time.perf_counter()
        try:
            with self._encode_lock:
                vectors = self._encoder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        finally:
            timed("local_embedding_encode", started, count=len(texts))
        return [validate_vector(vector.tolist(), self.dimension) for vector in vectors]


@lru_cache(maxsize=1)
def get_embedding_client():
    """Use the free local model unless an explicit legacy provider is configured."""
    provider = os.getenv('RAG_EMBEDDING_PROVIDER', 'local_sentence_transformers')
    if provider == 'local_sentence_transformers':
        return LocalSentenceTransformerClient()
    return EmbeddingClient.from_environment()


def initialize_embedding_client():
    """Load and cache the process-wide embedding client during application startup."""
    return get_embedding_client()
