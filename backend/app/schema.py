from __future__ import annotations

from sqlalchemy import Engine, text


def ensure_schema(engine: Engine) -> None:
    """
    Minimal, additive schema guard for local dev.

    Docker's `/docker-entrypoint-initdb.d` init scripts only run on first boot of the DB volume,
    so this ensures newly-added tables exist for existing local volumes.
    """
    ddl = """
    create extension if not exists "pgcrypto";
    alter table if exists agent_catalog add column if not exists human_name text;
    alter table if exists agent_catalog add column if not exists tagline text;
    alter table if exists agent_catalog add column if not exists profile text not null default '';
    alter table if exists agent_catalog add column if not exists capabilities jsonb not null default '[]'::jsonb;
    alter table if exists agent_catalog add column if not exists operational_sections jsonb not null default '[]'::jsonb;
    alter table if exists agent_catalog add column if not exists ideal_for text;
    alter table if exists agent_catalog add column if not exists personality text;
    alter table if exists agent_catalog add column if not exists communication_style text;
    alter table if exists interaction_logs add column if not exists tokens_used integer not null default 0;
    alter table if exists interaction_logs add column if not exists quality_score double precision;

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
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
