-- CreddyPens v1 schema (minimal, MVP-focused)
-- Postgres required.

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

create table if not exists agent_catalog (
  agent_id text primary key,
  code text not null unique,
  name text not null,
  description text not null,
  department text not null,
  price_cents integer not null,
  status text not null default 'coming_soon',
  llm_profile jsonb not null default '{}'::jsonb,
  llm_provider text,
  llm_model text,
  system_prompt text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_agent_catalog_status on agent_catalog(status);

-- For existing DBs where agent_catalog already exists, apply additive columns:
alter table agent_catalog add column if not exists llm_provider text;
alter table agent_catalog add column if not exists llm_model text;
alter table agent_catalog add column if not exists system_prompt text not null default '';

create table if not exists organizations (
  org_id text primary key,
  name text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists users (
  user_id text primary key,
  org_id text not null references organizations(org_id) on delete cascade,
  email text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_users_org on users(org_id);

create table if not exists interaction_logs (
  interaction_id uuid primary key default gen_random_uuid(),
  org_id text not null references organizations(org_id) on delete cascade,
  agent_code text not null references agent_catalog(code) on delete restrict,
  session_id text not null default '',
  message text not null default '',
  response text not null default '',
  model_used text not null default '',
  latency_ms integer not null default 0,
  trace_id text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_interaction_logs_org_created on interaction_logs(org_id, created_at desc);
create index if not exists idx_interaction_logs_agent_created on interaction_logs(agent_code, created_at desc);

create table if not exists hired_agents (
  hired_agent_id uuid primary key default gen_random_uuid(),
  org_id text not null references organizations(org_id) on delete cascade,
  agent_code text not null references agent_catalog(code) on delete restrict,
  status text not null default 'active',
  configuration jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(org_id, agent_code)
);

create index if not exists idx_hired_agents_org on hired_agents(org_id);
create index if not exists idx_hired_agents_status on hired_agents(status);
