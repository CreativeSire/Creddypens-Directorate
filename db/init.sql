-- CreddyPens v1 schema (minimal, MVP-focused)
-- Postgres required.

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

create table if not exists agent_catalog (
  agent_id text primary key,
  code text not null unique,
  name text not null,
  human_name text,
  tagline text,
  description text not null,
  profile text not null default '',
  capabilities jsonb not null default '[]'::jsonb,
  operational_sections jsonb not null default '[]'::jsonb,
  ideal_for text,
  personality text,
  communication_style text,
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
alter table agent_catalog add column if not exists human_name text;
alter table agent_catalog add column if not exists tagline text;
alter table agent_catalog add column if not exists profile text not null default '';
alter table agent_catalog add column if not exists capabilities jsonb not null default '[]'::jsonb;
alter table agent_catalog add column if not exists operational_sections jsonb not null default '[]'::jsonb;
alter table agent_catalog add column if not exists ideal_for text;
alter table agent_catalog add column if not exists personality text;
alter table agent_catalog add column if not exists communication_style text;

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
  tokens_used integer not null default 0,
  quality_score double precision,
  trace_id text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_interaction_logs_org_created on interaction_logs(org_id, created_at desc);
create index if not exists idx_interaction_logs_agent_created on interaction_logs(agent_code, created_at desc);
alter table interaction_logs add column if not exists tokens_used integer not null default 0;
alter table interaction_logs add column if not exists quality_score double precision;

create table if not exists response_evaluations (
  evaluation_id uuid primary key default gen_random_uuid(),
  interaction_id uuid,
  org_id text not null references organizations(org_id) on delete cascade,
  agent_code text not null references agent_catalog(code) on delete restrict,
  quality_score double precision not null,
  evaluation_criteria jsonb not null default '{}'::jsonb,
  evaluated_by text not null default 'auto',
  notes text,
  evaluated_at timestamptz not null default now()
);
create index if not exists idx_response_eval_org_agent on response_evaluations(org_id, agent_code, evaluated_at desc);

create table if not exists agent_prompt_versions (
  prompt_version_id uuid primary key default gen_random_uuid(),
  agent_code text not null references agent_catalog(code) on delete restrict,
  version integer not null,
  system_prompt text not null,
  changes_description text not null default '',
  performance_metrics jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(agent_code, version)
);

create table if not exists training_scenarios (
  scenario_id uuid primary key default gen_random_uuid(),
  agent_code text not null references agent_catalog(code) on delete restrict,
  scenario_name text not null,
  user_message text not null,
  expected_capabilities jsonb not null default '[]'::jsonb,
  difficulty text not null default 'medium',
  created_at timestamptz not null default now()
);
create index if not exists idx_training_scenarios_agent on training_scenarios(agent_code);

create table if not exists training_runs (
  training_run_id uuid primary key default gen_random_uuid(),
  org_id text references organizations(org_id) on delete cascade,
  agent_code text not null references agent_catalog(code) on delete restrict,
  run_type text not null default 'synthetic',
  status text not null default 'running',
  scenarios_tested integer not null default 0,
  avg_quality_score double precision,
  improvements_identified jsonb not null default '{}'::jsonb,
  passed boolean not null default true,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);
create index if not exists idx_training_runs_org_created on training_runs(org_id, started_at desc);
create index if not exists idx_training_runs_agent_created on training_runs(agent_code, started_at desc);

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
