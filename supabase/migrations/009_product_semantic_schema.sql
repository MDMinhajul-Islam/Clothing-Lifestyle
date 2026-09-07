-- Phase 2E: separate semantic index for the real public catalogue.
CREATE EXTENSION IF NOT EXISTS vector;
SET LOCAL search_path = public, extensions, pg_catalog;

CREATE TABLE IF NOT EXISTS public.product_embeddings (
    product_id TEXT PRIMARY KEY REFERENCES public.products(product_id) ON DELETE CASCADE,
    embedding_text TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    embedding_provider TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL CHECK (embedding_dimension = 384),
    embedding_version TEXT NOT NULL,
    source_content_hash TEXT NOT NULL CHECK (source_content_hash ~ '^[0-9a-f]{64}$'),
    embedded_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (vector_dims(embedding) = embedding_dimension AND vector_norm(embedding) > 0)
);

CREATE INDEX IF NOT EXISTS product_embeddings_cosine_hnsw
    ON public.product_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS product_embeddings_model
    ON public.product_embeddings (embedding_provider, embedding_model, embedding_version);

ALTER TABLE public.product_embeddings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.product_embeddings FROM PUBLIC;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON public.product_embeddings FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.product_embeddings FROM authenticated;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT SELECT, INSERT, UPDATE ON public.product_embeddings TO service_role;
    END IF;
END $$;
