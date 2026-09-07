"""Conservative semantic chunking: whole help articles preserve cross-section exceptions.

Small articles are kept intact. Oversized articles fail for editorial segmentation,
never silently split conditions. Token count is an explicitly labelled estimate.
"""
import math
from .common import CORPUS, digest, read, write

def chunk_document(doc):
    text = doc['clean_text']
    count = math.ceil(len(text) / 4)
    if count > 2200:
        raise ValueError('Article exceeds conservative chunk limit; reviewed semantic segmentation required')
    fields = ['knowledge_id', 'source_id', 'source_url', 'policy_type', 'section_title',
              'market', 'locale', 'effective_date', 'retrieved_at', 'source_hash']
    return [dict(**{k:doc[k] for k in fields}, chunk_id=doc['knowledge_id'] + '-c0-' + digest(text)[:12],
        chunk_index=0, chunk_text=text, token_count=count, token_count_method='ceil_characters_div_4',
        chunking_version='whole-article-1', chunking_note='Whole article preserves clauses and exceptions; target 500-1000 tokens is soft.')]

def main():
    chunks = [c for doc in read(CORPUS / 'documents.json') for c in chunk_document(doc)]
    write(CORPUS / 'chunks.json', chunks)
    print({'chunks':len(chunks), 'estimated_tokens':[c['token_count'] for c in chunks]})

if __name__ == '__main__':
    main()
