-- Phase 2D: backend-only, versioned official US evidence. No operational mutations.
CREATE EXTENSION IF NOT EXISTS vector;
SET LOCAL search_path = public, extensions, pg_catalog;

CREATE TABLE IF NOT EXISTS public.knowledge_documents (
    knowledge_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_url TEXT NOT NULL CHECK (source_url ~ '^https://(www\.)?zara\.com/us/en/'),
    source_name TEXT NOT NULL CHECK (source_name = 'zara_official_us'),
    market TEXT NOT NULL CHECK (market = 'US'),
    locale TEXT NOT NULL CHECK (locale = 'en'),
    policy_type TEXT NOT NULL,
    document_title TEXT NOT NULL,
    effective_date TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL,
    source_hash TEXT NOT NULL CHECK (source_hash ~ '^[0-9a-f]{64}$'),
    raw_text TEXT NOT NULL,
    clean_text TEXT NOT NULL,
    normalization_version TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, source_hash, normalization_version)
);
CREATE UNIQUE INDEX IF NOT EXISTS knowledge_active_source ON public.knowledge_documents(source_id) WHERE active;
CREATE INDEX IF NOT EXISTS knowledge_policy_market_locale ON public.knowledge_documents(policy_type, market, locale);

CREATE TABLE IF NOT EXISTS public.knowledge_chunks (
    chunk_id TEXT PRIMARY KEY,
    knowledge_id TEXT NOT NULL REFERENCES public.knowledge_documents(knowledge_id),
    section_title TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL CHECK (token_count > 0),
    token_count_method TEXT NOT NULL,
    chunking_version TEXT NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', section_title), 'A') ||
        setweight(to_tsvector('english', chunk_text), 'B')) STORED,
    -- Dimension is intentionally not chosen without a configured embedding model.
    -- Exact cosine search suits this small corpus; model/dimension filters are mandatory.
    embedding VECTOR,
    embedding_provider TEXT,
    embedding_model TEXT,
    embedding_dimension INTEGER,
    embedding_version TEXT,
    generated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (knowledge_id, chunk_index),
    CHECK ((embedding IS NULL AND embedding_provider IS NULL AND embedding_model IS NULL
         AND embedding_dimension IS NULL AND embedding_version IS NULL AND generated_at IS NULL)
        OR (embedding IS NOT NULL AND embedding_provider IS NOT NULL AND embedding_model IS NOT NULL
         AND embedding_dimension IS NOT NULL AND embedding_version IS NOT NULL AND generated_at IS NOT NULL
         AND vector_dims(embedding) = embedding_dimension AND vector_norm(embedding) > 0))
);
CREATE INDEX IF NOT EXISTS knowledge_chunk_document ON public.knowledge_chunks(knowledge_id);
CREATE INDEX IF NOT EXISTS knowledge_chunk_fts ON public.knowledge_chunks USING gin(search_vector);
ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.knowledge_documents, public.knowledge_chunks FROM PUBLIC;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON public.knowledge_documents, public.knowledge_chunks FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.knowledge_documents, public.knowledge_chunks FROM authenticated;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT SELECT, INSERT, UPDATE ON public.knowledge_documents, public.knowledge_chunks TO service_role;
    END IF;
END $$;
