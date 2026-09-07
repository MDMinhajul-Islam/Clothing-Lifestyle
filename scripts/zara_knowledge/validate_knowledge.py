"""Validate source-to-document-to-chunk integrity without network or database writes."""
from backend.app.rag.embeddings import validate_vector
from .common import CORPUS, ROOT, clean_extraction, digest, official_url, read

def validate(corpus=CORPUS):
    docs = read(corpus / 'documents.json')
    chunks = read(corpus / 'chunks.json')
    assert docs and chunks, 'Empty corpus'
    assert len({d['knowledge_id'] for d in docs}) == len(docs), 'Duplicate documents'
    assert len({c['chunk_id'] for c in chunks}) == len(chunks), 'Duplicate chunks'
    by_id = {d['knowledge_id']:d for d in docs}
    for doc in docs:
        raw = read(ROOT / doc['raw_path'])
        sidecar = read((ROOT / doc['raw_path']).with_suffix('.metadata.json'))
        assert sidecar['raw_artifact_hash'] == digest((ROOT / doc['raw_path']).read_text(encoding='utf-8'))
        assert digest(raw['raw_text']) == doc['source_hash'] == sidecar['source_hash'], 'Source hash mismatch'
        assert raw['raw_text'] == doc['raw_text'], 'Raw evidence changed'
        assert clean_extraction(doc['raw_text']) == doc['clean_text'], 'Unreviewed normalization change'
        assert doc['market'] == 'US' and doc['locale'] == 'en' and official_url(doc['source_url'])
        assert doc['source'] == 'zara_official_us'
    for c in chunks:
        doc = by_id[c['knowledge_id']]
        assert c['chunk_text'] == doc['clean_text'], 'Whole-article chunk changed'
        for key in ('source_id', 'source_hash', 'source_url', 'retrieved_at', 'effective_date', 'market', 'locale', 'policy_type'):
            assert c[key] == doc[key], 'Chunk provenance mismatch: ' + key
    if (corpus / 'embeddings.json').exists():
        by_chunk = {c['chunk_id']:c for c in chunks}
        records = read(corpus / 'embeddings.json')
        assert len({r['chunk_id'] for r in records}) == len(records)
        for r in records:
            assert r['chunk_hash'] == digest(by_chunk[r['chunk_id']]['chunk_text'])
            validate_vector(r['embedding'], r['embedding_dimension'])
            assert all(r[k] for k in ('embedding_provider','embedding_model','embedding_version','generated_at'))
    return {'documents':len(docs), 'chunks':len(chunks), 'provenance':'PASS'}

if __name__ == '__main__':
    print(validate())
