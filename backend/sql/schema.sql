-- EduMap database schema
-- ---------------------------------------------------------------------
-- pgvector adds the 'vector' column type and distance 
-- operators like <=>.
-- ---------------------------------------------------------------------
create extension if not exists vector;

-- ---------------------------------------------------------------------
-- USERS: mirrors Supabase Auth users (auth.users) into our own table.
-- The id is the same UUID Supabase puts in the JWT's `sub` claim.
-- ---------------------------------------------------------------------
create table users (
    id           uuid primary key,
    email        varchar(255),
    display_name varchar(100),
    created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- WORKSPACES: a study group for a course.
-- ---------------------------------------------------------------------
create table workspaces (
    id          uuid primary key default gen_random_uuid(),
    name        varchar(100) not null,
    invite_code varchar(50)  not null unique,        -- unique = no two groups share a code
    created_by  uuid not null references users(id),
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- WORKSPACE_MEMBERS: many-to-many link between users and workspaces.
-- A user can be in many workspaces; a workspace has many users.
-- ---------------------------------------------------------------------
create table workspace_members (
    id           uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    user_id      uuid not null references users(id) on delete cascade,
    role         varchar(20) not null check (role in ('owner', 'member')),
    joined_at    timestamptz not null default now(),
    unique (workspace_id, user_id)                    -- can't join the same group twice
);
create index workspace_members_user_idx on workspace_members (user_id);

-- ---------------------------------------------------------------------
-- DOCUMENTS: one row per uploaded file.
-- ---------------------------------------------------------------------
create table documents (
    id            uuid primary key default gen_random_uuid(),
    workspace_id  uuid not null references workspaces(id) on delete cascade,
    uploaded_by   uuid references users(id) on delete set null,
    title         varchar(255) not null,
    file_type     varchar(20) not null
                  check (file_type in ('syllabus', 'slides', 'textbook', 'notes', 'other')),
    file_path     text,              -- original file in cloud storage (stretch goal; null in v1)
    status        varchar(20) not null default 'processing'
                  check (status in ('processing', 'ready', 'failed')),
    error_message text,
    page_count    int,
    chunk_count   int,
    created_at    timestamptz not null default now()
);
create index documents_workspace_idx on documents (workspace_id);

-- ---------------------------------------------------------------------
-- DOCUMENT_CHUNKS: the searchable pieces of each document + embeddings.
-- vector(768) must match EMBEDDING_DIMENSIONS in the backend config.
-- ---------------------------------------------------------------------
create table document_chunks (
    id           uuid primary key default gen_random_uuid(),
    document_id  uuid not null references documents(id) on delete cascade,
    workspace_id uuid not null references workspaces(id) on delete cascade,  -- denormalized for fast filtering
    chunk_index  int  not null,
    page_number  int  not null,
    content      text not null,
    embedding    vector(768) not null
);
create index document_chunks_workspace_idx on document_chunks (workspace_id);
create index document_chunks_document_idx  on document_chunks (document_id, chunk_index);

-- SCALE-UP NOTE: with a few thousand chunks per workspace, exact search
-- (no vector index) is fast and 100% accurate. At ~100k+ chunks, add an
-- approximate-nearest-neighbour index (see Part 7.6 before doing this):
-- create index document_chunks_embedding_idx
--     on document_chunks using hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------
-- ROADMAP_ITEMS: one row per week of the generated study roadmap.
-- ---------------------------------------------------------------------
create table roadmap_items (
    id                 uuid primary key default gen_random_uuid(),
    workspace_id       uuid not null references workspaces(id) on delete cascade,
    source_document_id uuid references documents(id) on delete set null,
    week_number        int not null,
    title              varchar(255) not null,
    summary            text not null,
    topics             jsonb not null default '[]',   -- JSON array of strings
    readings           jsonb not null default '[]',
    created_at         timestamptz not null default now()
);
create index roadmap_items_workspace_idx on roadmap_items (workspace_id, week_number);

-- ROADMAP_PROGRESS: which user has completed which week.
-- Composite primary key = a user can complete a given item only once.
create table roadmap_progress (
    user_id         uuid not null references users(id) on delete cascade,
    roadmap_item_id uuid not null references roadmap_items(id) on delete cascade,
    completed_at    timestamptz not null default now(),
    primary key (user_id, roadmap_item_id)
);

-- ---------------------------------------------------------------------
-- CHAT_SESSIONS: private conversations (owned by one user).
-- ---------------------------------------------------------------------
create table chat_sessions (
    id           uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    user_id      uuid not null references users(id) on delete cascade,
    title        varchar(255) not null default 'New chat',
    created_at   timestamptz not null default now()
);
create index chat_sessions_owner_idx on chat_sessions (workspace_id, user_id, created_at desc);

-- ---------------------------------------------------------------------
-- MESSAGES: each chat turn.
-- clock_timestamp() (not now()) because we insert the user message and
-- the assistant reply in ONE transaction, and now() returns the same
-- value for the whole transaction, which would make ordering ambiguous.
-- ---------------------------------------------------------------------
create table messages (
    id                 uuid primary key default gen_random_uuid(),
    session_id         uuid not null references chat_sessions(id) on delete cascade,
    sender             varchar(20) not null check (sender in ('user', 'assistant')),
    content            text not null,
    key_points         jsonb not null default '[]',
    citations          jsonb not null default '[]',
    found_in_materials boolean,                       -- null for user messages
    created_at         timestamptz not null default clock_timestamp()
);
create index messages_session_idx on messages (session_id, created_at);

-- ---------------------------------------------------------------------
-- SHARED_INSIGHTS: a snapshot copy of an answer a student chose to share.
-- A copy (not a pointer) so sharing one answer never exposes the rest of
-- the private chat session.
-- ---------------------------------------------------------------------
create table shared_insights (
    id                 uuid primary key default gen_random_uuid(),
    workspace_id       uuid not null references workspaces(id) on delete cascade,
    shared_by          uuid references users(id) on delete set null,
    source_message_id  uuid unique references messages(id) on delete set null,
    question           text not null,
    answer             text not null,
    key_points         jsonb not null default '[]',
    citations          jsonb not null default '[]',
    found_in_materials boolean,
    created_at         timestamptz not null default now()
);
create index shared_insights_workspace_idx on shared_insights (workspace_id, created_at desc);

-- ---------------------------------------------------------------------
-- USAGE_EVENTS: one row per AI-consuming action, for rate limiting.
-- ---------------------------------------------------------------------
create table usage_events (
    id         bigint generated always as identity primary key,
    user_id    uuid not null references users(id) on delete cascade,
    kind       varchar(20) not null check (kind in ('chat', 'upload', 'roadmap')),
    created_at timestamptz not null default now()
);
create index usage_events_recent_idx on usage_events (created_at, user_id, kind);

-- =====================================================================
-- SECURITY: lock the tables away from Supabase's public Data API.
-- Supabase automatically exposes tables in the `public` schema over a
-- REST API that the publishable key can reach. Our browser never uses
-- that API (it only talks to our FastAPI backend), so we enable Row
-- Level Security with NO policies = deny everything via that API.
-- Our backend connects as the `postgres` role, which bypasses RLS.
-- =====================================================================
alter table users             enable row level security;
alter table workspaces        enable row level security;
alter table workspace_members enable row level security;
alter table documents         enable row level security;
alter table document_chunks   enable row level security;
alter table roadmap_items     enable row level security;
alter table roadmap_progress  enable row level security;
alter table chat_sessions     enable row level security;
alter table messages          enable row level security;
alter table shared_insights   enable row level security;
alter table usage_events      enable row level security;