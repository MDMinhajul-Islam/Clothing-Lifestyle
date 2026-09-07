"""Generate real vectors only with complete explicit provider configuration."""
from backend.app.config import settings  # load ignored environment, never print it
from backend.app.rag.embeddings import EmbeddingUnavailable, get_embedding_client
from .common import CORPUS, digest, now, read, write

def main():
    try:
        client = get_embedding_client()
    except EmbeddingUnavailable:
        print('EMBEDDINGS_NOT_CONFIGURED: no vectors generated')
        return
    records = read(CORPUS / 'embeddings.json') if (CORPUS / 'embeddings.json').exists() else []
    cached = {r['chunk_id']:r for r in records}
    output = []
    for chunk in read(CORPUS / 'chunks.json'):
        record = cached.get(chunk['chunk_id'])
        metadata = dict(embedding_provider=client.provider, embedding_model=client.model,
            embedding_dimension=client.dimension, embedding_version=client.version,
            chunk_hash=digest(chunk['chunk_text']))
        if not record or any(record.get(k) != v for k,v in metadata.items()):
            record = dict(chunk_id=chunk['chunk_id'], **metadata,
                          generated_at=now(), embedding=client.embed([chunk['chunk_text']])[0])
        output.append(record)
    write(CORPUS / 'embeddings.json', output)
    print({'embedded_chunks': len(output), 'model':client.model, 'version':client.version,
           'dimension':client.dimension, 'device':getattr(client, 'device', 'remote')})

if __name__ == '__main__':
    main()
