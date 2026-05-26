-- RAG ingestion pipeline tables/functions for Ollama nomic-embed-text.
-- nomic-embed-text returns 768-dimensional embeddings.

create extension if not exists vector;

drop index if exists public.idx_questions_embedding_hnsw;
drop index if exists public.idx_ai_memories_embedding_hnsw;
drop index if exists public.idx_sat_knowledge_chunks_embedding_hnsw;

alter table public.questions
add column if not exists embedding vector(768);

alter table public.questions
add column if not exists embedding_model text;

alter table public.questions
add column if not exists embedding_updated_at timestamptz;

create table if not exists public.ai_memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  student_id uuid references public.students(id) on delete cascade,
  memory_type text not null check (
    memory_type in ('preference', 'goal', 'weakness', 'strength', 'strategy', 'context')
  ),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  source_type text check (
    source_type in ('chat', 'test_session', 'test_answer', 'question', 'todo', 'manual')
  ),
  source_id text,
  importance smallint not null default 3 check (importance between 1 and 5),
  embedding vector(768),
  embedding_model text,
  last_used_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sat_knowledge_sources (
  id uuid primary key default gen_random_uuid(),
  uploaded_by uuid references public.profiles(id) on delete set null,
  title text not null,
  source_type text not null default 'upload' check (source_type in ('upload', 'url', 'manual')),
  file_name text,
  file_mime_type text,
  storage_bucket text,
  storage_path text,
  url text,
  subject text,
  topic text,
  sat_band text check (sat_band in ('1000-1200', '1200-1400', '1400+')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (storage_bucket, storage_path)
);

create table if not exists public.sat_knowledge_chunks (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sat_knowledge_sources(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  subject text,
  topic text,
  sat_band text check (sat_band in ('1000-1200', '1200-1400', '1400+')),
  page_number integer,
  token_count integer,
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(768) not null,
  embedding_model text not null,
  created_at timestamptz not null default now(),
  unique (source_id, chunk_index)
);

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'questions'
      and column_name = 'embedding'
      and udt_name = 'vector'
  ) then
    alter table public.questions
    alter column embedding type vector(768)
    using null;
  end if;

  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'ai_memories'
      and column_name = 'embedding'
      and udt_name = 'vector'
  ) then
    alter table public.ai_memories
    alter column embedding type vector(768)
    using null;
  end if;

  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'sat_knowledge_chunks'
      and column_name = 'embedding'
      and udt_name = 'vector'
  ) then
    alter table public.sat_knowledge_chunks
    alter column embedding drop not null;

    alter table public.sat_knowledge_chunks
    alter column embedding type vector(768)
    using null;
  end if;
end $$;

create index if not exists idx_questions_subject_topic
on public.questions(subject, topic);

create index if not exists idx_ai_memories_user_type
on public.ai_memories(user_id, memory_type);

create index if not exists idx_ai_memories_student
on public.ai_memories(student_id);

create index if not exists idx_sat_knowledge_sources_subject_topic
on public.sat_knowledge_sources(subject, topic);

create index if not exists idx_sat_knowledge_chunks_source
on public.sat_knowledge_chunks(source_id, chunk_index);

create index if not exists idx_sat_knowledge_chunks_subject_topic
on public.sat_knowledge_chunks(subject, topic);

create index if not exists idx_questions_embedding_hnsw
on public.questions
using hnsw (embedding vector_cosine_ops);

create index if not exists idx_ai_memories_embedding_hnsw
on public.ai_memories
using hnsw (embedding vector_cosine_ops);

create index if not exists idx_sat_knowledge_chunks_embedding_hnsw
on public.sat_knowledge_chunks
using hnsw (embedding vector_cosine_ops);

create or replace function public.match_sat_knowledge(
  query_embedding vector(768),
  match_count integer default 8,
  filter_subject text default null,
  filter_topic text default null
)
returns table (
  chunk_id uuid,
  source_id uuid,
  title text,
  content text,
  subject text,
  topic text,
  sat_band text,
  page_number integer,
  similarity double precision
)
language sql
stable
as $$
  select
    c.id as chunk_id,
    c.source_id,
    s.title,
    c.content,
    coalesce(c.subject, s.subject) as subject,
    coalesce(c.topic, s.topic) as topic,
    coalesce(c.sat_band, s.sat_band) as sat_band,
    c.page_number,
    1 - (c.embedding <=> query_embedding) as similarity
  from public.sat_knowledge_chunks c
  join public.sat_knowledge_sources s on s.id = c.source_id
  where (filter_subject is null or coalesce(c.subject, s.subject) = filter_subject)
    and (filter_topic is null or coalesce(c.topic, s.topic) = filter_topic)
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

create or replace function public.match_ai_memories(
  query_embedding vector(768),
  match_user_id uuid,
  match_count integer default 6,
  filter_memory_type text default null
)
returns table (
  id uuid,
  memory_type text,
  content text,
  metadata jsonb,
  importance smallint,
  similarity double precision
)
language sql
stable
as $$
  select
    m.id,
    m.memory_type,
    m.content,
    m.metadata,
    m.importance,
    1 - (m.embedding <=> query_embedding) as similarity
  from public.ai_memories m
  where m.user_id = match_user_id
    and m.embedding is not null
    and (m.expires_at is null or m.expires_at > now())
    and (filter_memory_type is null or m.memory_type = filter_memory_type)
  order by (m.embedding <=> query_embedding), m.importance desc
  limit match_count;
$$;
