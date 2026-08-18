-- Run once against the Supabase project's Postgres instance (SQL editor or psql).
-- Provisioned manually -- see infra/README.md for why this isn't in Terraform.

create extension if not exists vector;

create table if not exists law_chunks (
  id bigserial primary key,
  article_number text not null unique,
  chapter text,
  text text not null,
  embedding vector(768),
  created_at timestamptz default now()
);

create index if not exists law_chunks_embedding_idx
  on law_chunks using hnsw (embedding vector_cosine_ops);
