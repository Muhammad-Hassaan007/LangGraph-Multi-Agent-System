-- ==============================================================================
-- Supabase PostgreSQL + pgvector Schema Setup (Configured for Google Gemini)
-- Run this in your Supabase Dashboard -> SQL Editor (Click 'New Query' -> 'Run')
-- ==============================================================================

-- 1. Enable the pgvector extension for vector storage and similarity searches
create extension if not exists vector;

-- Optional: If you previously created the table with a different dimension, run:
-- drop table if exists documents cascade;

-- 2. Create the documents table
-- Note: embedding uses vector(768) to match Google Gemini text-embedding-004
create table if not exists documents (
    id bigserial primary key,
    document_id text not null,               -- Dedicated column for strict isolation
    content text not null,                   -- Text chunk
    metadata jsonb default '{}'::jsonb,      -- JSON metadata (filename, page, chunk_index)
    embedding vector(768),                   -- 768 dimensions for Gemini text-embedding-004
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. Create index on document_id for fast isolation filtering
create index if not exists idx_documents_document_id on documents (document_id);

-- 4. Create GIN index on metadata JSON
create index if not exists idx_documents_metadata on documents using gin (metadata);

-- 5. Create HNSW index on vector embedding for high-speed approximate nearest neighbor search
create index if not exists idx_documents_embedding on documents 
using hnsw (embedding vector_cosine_ops);

-- 6. Create RPC match_documents function for strict document-isolated vector retrieval
create or replace function match_documents (
    query_embedding vector(768),
    match_count int default 4,
    filter_document_id text default null
) returns table (
    id bigint,
    document_id text,
    content text,
    metadata jsonb,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        documents.id,
        documents.document_id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) as similarity
    from documents
    where (filter_document_id is null or documents.document_id = filter_document_id)
    order by documents.embedding <=> query_embedding
    limit match_count;
end;
$$;
